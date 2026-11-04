#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""ScanCode over the committed tree of HEAD with a license policy (V6, `make scancode`).

Runs ScanCode Toolkit over the files of HEAD (archive_head: like `git archive
HEAD`, without export attributes) and checks its JSON output:
every license that ScanCode finds in a file (a license detection or a license
clue) must be satisfied by quality/licenses/allowed.txt, or be listed for
exactly that file and exactly that SPDX expression, with a reason, in
quality/licenses/scancode-exceptions.txt (detailed design 00 sections 2.10 and
3.5). That file is not checked itself: it consists of license expressions.
When scanning, both files are read from that tree, like the image pin
and the requirements, so the policy is the one of the scanned commit.

Findings, each as `path:line:col rule-id message`:

  scancode-license-not-allowed  a detected expression is neither allowed nor
                                an exception for that file
  scancode-exception-unused     an exception matches no detection (stale
                                entries are removed, not kept)
  scancode-scan-error           ScanCode reported an error for a file or the
                                whole scan; the file was not fully scanned
  scancode-file-not-scanned     a committed file is missing from the ScanCode
                                output (apart from the VCS files it skips)

Runners (`--runner`), both with the same ScanCode version and Python packages
(tools/bootstrap/scancode/requirements.txt, exact versions with hashes):

  container  the image pinned by digest in [images.scancode] of
             tools/bootstrap/tools.toml (CI); the packages are installed into
             the container with `pip --require-hashes` on every run
  local      the environment that `make scancode SCANCODE_RUNNER=local`
             installs with uv into .tools/scancode (no container runtime)

`--scan <file>` checks an existing ScanCode output instead of scanning.

Standard library only (FE-004).

Exit codes:
  0  no finding
  1  findings on stdout; with --json <file> also written there as JSON
  2  configuration or run error on stderr: `scancode.config_invalid path=<path>
     line=<line> reason=<reason>` (also an exception without reason),
     `scancode.output_invalid`, `scancode.env_missing`, `scancode.run_failed`
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if not __package__:
    # Run as a script (make scancode): make the tools package importable.
    sys.path.insert(0, str(REPO_ROOT))

from tools.ci.license_check import ConfigError, is_allowed, load_allowed  # noqa: E402

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_CONFIG = 2

EXCEPTIONS_PATH = "quality/licenses/scancode-exceptions.txt"
TOOLS_TOML_PATH = "tools/bootstrap/tools.toml"
REQUIREMENTS_DIR = "tools/bootstrap/scancode"
DEFAULT_ENV = ".tools/scancode"
DEFAULT_SCAN_OUTPUT = ".reports/scancode-scan.json"
IMAGE_KEYS = frozenset({"image", "tag", "digest", "source", "retrieved"})
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
GLOB_CHARS = frozenset("*?[]")
# Path parts that ScanCode always skips (commoncode.ignore.ignores_VCS of
# ScanCode 32.5.0); any other committed file missing from its output is a
# finding.
SCANCODE_SKIPS = frozenset(
    {
        ".bzr",
        ".bzrignore",
        ".cvsignore",
        ".git",
        ".gitattributes",
        ".gitignore",
        ".hg",
        ".hgignore",
        ".repo",
        ".svn",
        ".svnignore",
        ".tfignore",
        "CVS",
        "_MTN",
        "_darcs",
        "vssver.scc",
        "{arch}",
    }
)

# ScanCode options of both runners: license detection only, paths relative to
# the scanned root, no progress output.
SCANCODE_OPTIONS = ("--license", "--strip-root", "--quiet")

# Runs ScanCode in the Python of the ScanCode environment. ScanCode needs
# libmagic; the pinned package pylibmagic ships it for Linux and macOS (the
# libmagic plugin of ScanCode exists only for x86_64), so its paths are set
# before ScanCode starts.
LAUNCHER = """\
import os, sys
import pylibmagic
data = str(pylibmagic.data)
lib = "libmagic.dylib" if sys.platform == "darwin" else "libmagic.so"
os.environ["TYPECODE_LIBMAGIC_PATH"] = os.path.join(data, lib)
os.environ["TYPECODE_LIBMAGIC_DB_PATH"] = os.path.join(data, "magic.mgc")
from scancode.cli import scancode
sys.argv[0] = "scancode"
scancode()
"""

# Inside the container: install the hashed requirements into a fresh
# environment, then run the launcher. pip output goes to stderr.
CONTAINER_SCRIPT = (
    "python -m venv /tmp/venv"
    " && /tmp/venv/bin/pip install --quiet --disable-pip-version-check --no-deps"
    " --require-hashes --only-binary :all: -r /req/requirements.txt >&2"
    ' && exec /tmp/venv/bin/python -c "$SCANCODE_LAUNCHER" "$@"'
)


class RunError(Exception):
    """ScanCode, git or the container runtime failed, or the output is unusable."""


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    col: int
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}:{self.col} {self.rule} {self.message}"


@dataclass(frozen=True)
class ScanException:
    path: str
    expression: str
    reason: str
    line: int


# ---------------------------------------------------------------------------
# Configuration


def load_exceptions(root: Path) -> dict[tuple[str, str], ScanException]:
    """scancode-exceptions.txt: `<path>`, SPDX expression, reason, tab separated."""
    try:
        text = (root / EXCEPTIONS_PATH).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"cannot read: {exc.__class__.__name__}", EXCEPTIONS_PATH) from exc
    exceptions: dict[tuple[str, str], ScanException] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        fields = raw.split("\t")
        if len(fields) != 3 or not all(field.strip() for field in fields):
            raise ConfigError(
                "expected three tab-separated fields <path>, SPDX expression, reason;"
                " the reason must not be empty",
                EXCEPTIONS_PATH,
                number,
            )
        path, expression, reason = (field.strip() for field in fields)
        parts = path.split("/")
        if path.startswith("/") or path.endswith("/") or GLOB_CHARS & set(path) or ".." in parts:
            raise ConfigError(
                "the path must name exactly one file, relative to the repository root",
                EXCEPTIONS_PATH,
                number,
            )
        key = (path, expression)
        if key in exceptions:
            raise ConfigError(f"duplicate entry {path} {expression}", EXCEPTIONS_PATH, number)
        exceptions[key] = ScanException(path, expression, reason, number)
    return exceptions


def load_image(root: Path) -> str:
    """The ScanCode image of tools.toml as `<image>@<digest>`."""
    try:
        data = tomllib.loads((root / TOOLS_TOML_PATH).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"cannot read: {exc.__class__.__name__}", TOOLS_TOML_PATH) from exc
    images = data.get("images")
    entry = images.get("scancode") if isinstance(images, dict) else None
    if not isinstance(entry, dict) or set(entry) != IMAGE_KEYS:
        raise ConfigError(
            f"[images.scancode] needs exactly {', '.join(sorted(IMAGE_KEYS))}", TOOLS_TOML_PATH
        )
    if not all(isinstance(value, str) and value for value in entry.values()):
        raise ConfigError("[images.scancode] values must be non-empty strings", TOOLS_TOML_PATH)
    if not DIGEST.match(entry["digest"]):
        raise ConfigError("images.scancode.digest must be sha256:<64 hex>", TOOLS_TOML_PATH)
    return f"{entry['image']}@{entry['digest']}"


# ---------------------------------------------------------------------------
# Policy


def _first_line(matches: object) -> int:
    lines = (
        [
            m["start_line"]
            for m in matches
            if isinstance(m, dict) and isinstance(m.get("start_line"), int)
        ]
        if isinstance(matches, list)
        else []
    )
    return min(lines, default=1)


def _expression(item: object, path: str) -> str:
    if isinstance(item, dict):
        value = item.get("license_expression_spdx")
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise RunError(f"scancode.output_invalid path={path} reason=detection_without_expression")


def detections(entry: dict[str, Any], path: str) -> dict[str, int]:
    """SPDX expression of each detection and clue of a file, with its first line."""
    found: dict[str, int] = {}

    def add(expression: str, line: int) -> None:
        found[expression] = min(line, found.get(expression, line))

    for item in entry.get("license_detections") or []:
        add(_expression(item, path), _first_line(item.get("matches")))
    for item in entry.get("license_clues") or []:
        start = item.get("start_line") if isinstance(item, dict) else None
        add(_expression(item, path), start if isinstance(start, int) else 1)
    return found


def check_scan(
    scan: object,
    allowed: frozenset[str],
    exceptions: dict[tuple[str, str], ScanException],
    committed: Sequence[str] | None = None,
) -> list[Finding]:
    """Findings for a parsed ScanCode JSON output; RunError if it is not one.

    committed: the files of the scanned tree; each must be in the output.
    """
    files = scan.get("files") if isinstance(scan, dict) else None
    if not isinstance(files, list):
        raise RunError("scancode.output_invalid reason=no_files")
    findings: list[Finding] = []
    headers = scan.get("headers") if isinstance(scan, dict) else None
    for header in headers if isinstance(headers, list) else []:
        for error in (header.get("errors") or []) if isinstance(header, dict) else []:
            # An error of the whole scan has no file; "." stands for the tree.
            findings.append(Finding(".", 1, 1, "scancode-scan-error", str(error)))
    used: set[tuple[str, str]] = set()
    listed: set[str] = set()
    for entry in files:
        path = entry.get("path") if isinstance(entry, dict) else None
        if not isinstance(path, str) or not path:
            raise RunError("scancode.output_invalid reason=file_without_path")
        if entry.get("type") != "file":
            continue
        listed.add(path)
        if path == EXCEPTIONS_PATH:
            continue
        for error in entry.get("scan_errors") or []:
            findings.append(Finding(path, 1, 1, "scancode-scan-error", str(error)))
        for expression, line in sorted(detections(entry, path).items()):
            if is_allowed(expression, allowed):
                continue
            if (path, expression) in exceptions:
                used.add((path, expression))
                continue
            findings.append(
                Finding(
                    path,
                    line,
                    1,
                    "scancode-license-not-allowed",
                    f"{expression} is neither allowed nor an exception in {EXCEPTIONS_PATH}",
                )
            )
    for path in sorted(committed or []):
        if path not in listed and not SCANCODE_SKIPS & set(path.split("/")):
            message = "the committed file is missing from the ScanCode output"
            findings.append(Finding(path, 1, 1, "scancode-file-not-scanned", message))
    for key, exception in sorted(exceptions.items(), key=lambda item: item[1].line):
        if key not in used:
            findings.append(
                Finding(
                    EXCEPTIONS_PATH,
                    exception.line,
                    1,
                    "scancode-exception-unused",
                    f"{exception.path} {exception.expression} matches no ScanCode detection",
                )
            )
    return findings


def check(root: Path, scan: object) -> list[Finding]:
    """Findings for the repository at root; ConfigError or RunError on errors."""
    return check_scan(scan, load_allowed(root), load_exceptions(root))


def read_scan(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise RunError(
            f"scancode.output_invalid path={path} reason={exc.__class__.__name__}"
        ) from exc


# ---------------------------------------------------------------------------
# Scanning


def _git(root: Path, args: list[str], step: str, stdin: bytes | None = None) -> bytes:
    result = subprocess.run(  # noqa: S603
        ["git", "-C", str(root), *args],  # noqa: S607
        input=stdin,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RunError(f"scancode.run_failed step={step} exit={result.returncode}")
    return result.stdout


def archive_head(root: Path, dest: Path) -> list[str]:
    """Write every file of HEAD of root into dest, byte for byte as committed.

    Like `git archive HEAD`, but the blobs are written raw: git archive leaves
    out export-ignore files, rewrites export-subst files and, like
    checkout-index, converts content by attributes (working-tree-encoding, eol,
    filters), which could hide a license from ScanCode. Symbolic links and
    submodules are skipped; ScanCode lists neither. Returns the written paths.
    """
    entries: list[tuple[str, str]] = []
    for record in _git(root, ["ls-tree", "-r", "-z", "--full-tree", "HEAD"], "ls_tree").split(
        b"\0"
    ):
        if not record:
            continue
        meta, _, raw_path = record.partition(b"\t")
        mode, kind, sha = meta.decode().split()
        if kind == "blob" and mode in ("100644", "100755"):
            entries.append((sha, os.fsdecode(raw_path)))
    stdin = "".join(f"{sha}\n" for sha, _ in entries).encode()
    data = _git(root, ["cat-file", "--batch"], "cat_file", stdin)
    dest.mkdir(parents=True, exist_ok=True)
    base = dest.resolve()
    position = 0
    for sha, path in entries:
        header_end = data.index(b"\n", position)
        header = data[position:header_end].decode().split()
        if len(header) != 3 or header[0] != sha:
            raise RunError(
                f"scancode.run_failed step=cat_file reason=unexpected_output path={path}"
            )
        start = header_end + 1
        end = start + int(header[2])
        target = (base / path).resolve()
        if not target.is_relative_to(base):
            raise RunError(f"scancode.run_failed step=cat_file reason=path_outside path={path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data[start:end])
        position = end + 1
    return [path for _, path in entries]


def _run(command: list[str], runner: str, output: Path, env: dict[str, str] | None = None) -> None:
    """Run ScanCode; exit 1 with an output is a scan with file errors, left to the policy."""
    try:
        result = subprocess.run(command, check=False, env=env)  # noqa: S603
    except OSError as exc:
        hint = ""
        if runner == "container" and isinstance(exc, FileNotFoundError):
            hint = f" cli={command[0]}: no container CLI; without one use SCANCODE_RUNNER=local"
        raise RunError(
            f"scancode.run_failed runner={runner} reason={exc.__class__.__name__}{hint}"
        ) from exc
    if result.returncode == 0 or (result.returncode == 1 and output.is_file()):
        return
    raise RunError(f"scancode.run_failed runner={runner} exit={result.returncode}")


def scan_local(src: Path, output: Path, env_dir: Path, processes: int) -> None:
    python = env_dir / "bin" / "python"
    if not python.exists():
        raise RunError(
            f"scancode.env_missing path={env_dir}: run `make scancode SCANCODE_RUNNER=local`"
        )
    output.unlink(missing_ok=True)  # never read the output of an earlier run
    options = [*SCANCODE_OPTIONS, "--processes", str(processes), "--json", str(output)]
    _run([str(python), "-c", LAUNCHER, *options, str(src)], "local", output)


def scan_container(src: Path, out_dir: Path, docker: str, processes: int) -> Path:
    """Scan src in the pinned image; image and requirements come from src."""
    image = load_image(src)
    requirements = src / REQUIREMENTS_DIR
    options = [*SCANCODE_OPTIONS, "--processes", str(processes), "--json", "/out/scan.json"]
    command = [
        docker, "run", "--rm",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "-e", "HOME=/tmp",
        "-e", "SCANCODE_LAUNCHER",
        "-v", f"{src}:/scan:ro",
        "-v", f"{requirements}:/req:ro",
        "-v", f"{out_dir}:/out",
        image,
        "sh", "-c", CONTAINER_SCRIPT, "sh", *options, "/scan",
    ]  # fmt: skip
    output = out_dir / "scan.json"
    _run(command, "container", output, env={**os.environ, "SCANCODE_LAUNCHER": LAUNCHER})
    return output


def run_scan(args: argparse.Namespace, root: Path, output: Path) -> list[Finding]:
    """Scan the files of HEAD of root, keep the output at output, return findings.

    The policy files, the image pin and the requirements are read from the
    scanned tree, so scan and policy belong to the same commit.
    """
    with tempfile.TemporaryDirectory(prefix="scancode-") as tmp:
        src = Path(tmp) / "src"
        committed = archive_head(root, src)
        allowed, exceptions = load_allowed(src), load_exceptions(src)
        started = time.monotonic()
        if args.runner == "local":
            scan_local(src, output, args.env, args.processes)
        else:
            out_dir = Path(tmp) / "out"
            out_dir.mkdir()
            shutil.move(scan_container(src, out_dir, args.docker, args.processes), output)
        seconds = time.monotonic() - started
        print(
            f"scancode.done runner={args.runner} files={len(committed)} seconds={seconds:.1f}",
            file=sys.stderr,
        )
        return check_scan(read_scan(output), allowed, exceptions, committed)


# ---------------------------------------------------------------------------
# Command line


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ScanCode over HEAD and check its licenses.")
    add = parser.add_argument
    add("--root", type=Path, default=REPO_ROOT, help="repository root")
    add("--scan", type=Path, help="check this ScanCode JSON output instead of scanning")
    add("--runner", choices=("container", "local"), default="container")
    add("--env", type=Path, help=f"ScanCode environment of --runner local (default {DEFAULT_ENV})")
    add("--docker", default=os.environ.get("SCANCODE_DOCKER", "docker"), help="container CLI")
    add("--processes", type=int, default=os.cpu_count() or 1, help="ScanCode processes")
    add(
        "--scan-output", type=Path, help=f"keep the ScanCode output (default {DEFAULT_SCAN_OUTPUT})"
    )
    add("--json", type=Path, help="also write the findings as JSON to this file")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root: Path = args.root.resolve()
    if args.env is None:
        args.env = root / DEFAULT_ENV
    try:
        if args.scan is not None:
            findings = check(root, read_scan(args.scan))
        else:
            output = (args.scan_output or root / DEFAULT_SCAN_OUTPUT).resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            findings = run_scan(args, root, output)
    except ConfigError as exc:
        print(
            f"scancode.config_invalid path={exc.path} line={exc.line} reason={exc}",
            file=sys.stderr,
        )
        return EXIT_CONFIG
    except RunError as exc:
        print(exc, file=sys.stderr)
        return EXIT_CONFIG
    for finding in findings:
        print(finding)
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps([asdict(f) for f in findings], indent=2) + "\n", encoding="utf-8"
        )
    return EXIT_FINDINGS if findings else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
