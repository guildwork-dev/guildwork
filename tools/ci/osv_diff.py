#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Scan the lockfiles with osv-scanner; with a base ref, fail only on new findings.

Runs the pinned osv-scanner (`scan source --format json`, form checked against
`--help` of 2.7.0) on pnpm-lock.yaml and uv.lock with the configuration
quality/osv/osv-scanner.toml. A finding is the pair of package (ecosystem, name,
version) and vulnerability id.

Without --base (OSV_BASE empty) every finding fails the gate: the full scan of
main. With --base <ref> the lockfiles of that ref are read with `git show`,
scanned the same way, and their findings are subtracted: a pull request fails
only on pairs it introduces (architecture 12 section 5.2). A lockfile missing at
the base ref is not scanned there, so all its findings count as new.

Ignore entries ([[IgnoredVulns]] in the configuration) need `reason` and
`ignoreUntil`, so that no exception is silent or permanent.

Standard library only (FE-004).

Exit codes:
  0  no new finding
  1  new findings, printed as `path:1:1 osv-vulnerability <id> in
     <name>@<version> (<ecosystem>)` on stdout
  2  error on stderr: `osv.scanner_error scan=<head|base> exit=<code>` (any
     scanner exit other than 0 and 1, among them 127 for a network error and
     128 for no packages), `osv.output_invalid`, `osv.base_invalid ref=<ref>`,
     `osv.config_missing`, `osv.config_invalid`
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path("quality/osv/osv-scanner.toml")
DEFAULT_SCANNER = ".tools/bin/osv-scanner"
LOCKFILES = ("pnpm-lock.yaml", "uv.lock")
# Scanner exit codes that mean a finished scan (0 none, 1 findings).
SCAN_OK_CODES = frozenset({0, 1})

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


class OsvError(Exception):
    """A scan, the base ref or the configuration cannot be used; exit 2."""


@dataclass(frozen=True, order=True)
class Finding:
    ecosystem: str
    name: str
    version: str
    vuln: str
    lockfile: str = ""

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.ecosystem, self.name, self.version, self.vuln)

    def __str__(self) -> str:
        return (
            f"{self.lockfile}:1:1 osv-vulnerability {self.vuln} in "
            f"{self.name}@{self.version} ({self.ecosystem})"
        )


def load_ignores(path: Path) -> list[dict[str, Any]]:
    """The [[IgnoredVulns]] entries; each needs id, reason and ignoreUntil."""
    if not path.is_file():
        raise OsvError(f"osv.config_missing path={path}")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise OsvError(f"osv.config_invalid path={path} reason={exc}") from exc
    entries = data.get("IgnoredVulns", [])
    if not isinstance(entries, list):
        raise OsvError(f"osv.config_invalid path={path} reason=IgnoredVulns is not a list")
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not str(entry.get("id", "")).strip():
            raise OsvError(f"osv.config_invalid path={path} entry={index} reason=id missing")
        if not str(entry.get("reason", "")).strip():
            raise OsvError(f"osv.config_invalid path={path} id={entry['id']} reason=no reason")
        if "ignoreUntil" not in entry:
            raise OsvError(f"osv.config_invalid path={path} id={entry['id']} reason=no ignoreUntil")
    return entries


def parse_output(text: str, scan: str) -> list[Finding]:
    """Findings of one JSON output of `osv-scanner scan source --format json`."""
    try:
        data = json.loads(text)
        findings = []
        for result in data["results"]:
            lockfile = Path(result["source"]["path"]).name
            for entry in result.get("packages") or []:
                package = entry["package"]
                for vuln in entry.get("vulnerabilities") or []:
                    findings.append(
                        Finding(
                            str(package["ecosystem"]),
                            str(package["name"]),
                            str(package["version"]),
                            str(vuln["id"]),
                            lockfile,
                        )
                    )
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise OsvError(f"osv.output_invalid scan={scan} reason={exc!r}") from exc
    return findings


def scan(
    run: Runner, scanner: str, config: Path, lockfiles: Sequence[Path], workdir: Path, name: str
) -> list[Finding]:
    output = workdir / f"osv-{name}.json"
    cmd = [scanner, "scan", "source", "--format", "json", "--config", str(config)]
    cmd += ["--output-file", str(output)]
    for lockfile in lockfiles:
        cmd += ["-L", str(lockfile)]
    try:
        result = run(cmd, check=False, capture_output=True, text=True)
    except OSError as exc:
        raise OsvError(f"osv.scanner_error scan={name} exit=none detail={exc}") from exc
    if result.returncode not in SCAN_OK_CODES:
        detail = (result.stderr or "").strip().splitlines()
        last = detail[-1] if detail else ""
        raise OsvError(f"osv.scanner_error scan={name} exit={result.returncode} detail={last}")
    try:
        text = output.read_text(encoding="utf-8")
    except OSError as exc:
        raise OsvError(f"osv.output_invalid scan={name} reason={exc}") from exc
    return parse_output(text, name)


def git_show(root: Path, ref: str, path: str) -> bytes | None:
    """Content of path at ref, or None if the file does not exist there."""
    result = subprocess.run(  # noqa: S603
        ["git", "cat-file", "-e", f"{ref}:{path}"],  # noqa: S607
        cwd=root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return subprocess.run(  # noqa: S603
            ["git", "show", f"{ref}:{path}"],  # noqa: S607
            cwd=root,
            capture_output=True,
            check=True,
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise OsvError(f"osv.base_invalid ref={ref} path={path}") from exc


def resolve_base(root: Path, ref: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],  # noqa: S607
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise OsvError(f"osv.base_invalid ref={ref}")
    return result.stdout.strip()


def new_findings(head: Sequence[Finding], base: Sequence[Finding]) -> list[Finding]:
    known = {finding.key for finding in base}
    seen: set[tuple[str, str, str, str]] = set()
    result = []
    for finding in sorted(head, key=lambda f: (f.lockfile, f.key)):
        if finding.key in known or finding.key in seen:
            continue
        seen.add(finding.key)
        result.append(finding)
    return result


def check(root: Path, scanner: str, base_ref: str, run: Runner) -> list[Finding]:
    config = root / CONFIG_PATH
    load_ignores(config)
    commit = resolve_base(root, base_ref) if base_ref else ""
    with tempfile.TemporaryDirectory(prefix="osv-") as tmp:
        workdir = Path(tmp)
        head = scan(run, scanner, config, [root / name for name in LOCKFILES], workdir, "head")
        base: list[Finding] = []
        if commit:
            base_dir = workdir / "base"
            base_dir.mkdir()
            lockfiles = []
            for name in LOCKFILES:
                content = git_show(root, commit, name)
                if content is not None:
                    (base_dir / name).write_bytes(content)
                    lockfiles.append(base_dir / name)
            if lockfiles:
                base = scan(run, scanner, config, lockfiles, workdir, "base")
    return new_findings(head, base)


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan the lockfiles with osv-scanner.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    parser.add_argument("--scanner", default=None, help="osv-scanner binary")
    parser.add_argument(
        "--base", default="", help="git ref of the base; only new findings fail (OSV_BASE)"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, run: Runner = subprocess.run) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    scanner = args.scanner or str(root / DEFAULT_SCANNER)
    try:
        findings = check(root, scanner, args.base.strip(), run)
    except OsvError as exc:
        print(exc, file=sys.stderr)
        return EXIT_ERROR
    for finding in findings:
        print(finding)
    return EXIT_FINDINGS if findings else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
