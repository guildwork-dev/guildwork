#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""The license gate (detailed design 00 section 2.10, FE-028, FE-029).

Checks, each reported as `path:line:col rule-id message`:

  license-file-modified        LICENSE is not byte for byte the text whose
                               SHA-256 is in quality/licenses/license.sha256
  spdx-header-missing          a handwritten file (a suffix or name with a
                               comment form in spdx_header.py) has neither the
                               project header nor an adopted header within the
                               first spdx_header.MAX_LINE lines
  adopted-license-not-allowed  an adopted header (SPDX-License-Identifier,
                               SPDX-FileCopyrightText and Origin) names a
                               license that is neither in allowed.txt nor
                               listed for exactly that path in header.toml
  runtime-license-not-allowed  a runtime dependency without a license whose
                               SPDX expression is satisfied by allowed.txt
                               (dev-exceptions.txt does not apply)
  dev-license-needs-exception  a development dependency whose license is not
                               allowed and that has no entry
                               `<name>@<version>` in dev-exceptions.txt
  license-text-missing         an SPDX identifier used in a header or by a
                               runtime dependency has no LICENSES/<id>.txt
                               (FE-029)
  forbidden-package            ADR-39: a package of FORBIDDEN_NPM or
                               FORBIDDEN_PYPI (Claude Code, its platform
                               packages, the Agent SDKs) in a lockfile
  notices-outdated             THIRD_PARTY_NOTICES differs from the output of
                               third_party_notices.py

Dependencies come from license_inventory.py (pnpm and uv.lock with .venv).
Files are the tracked and the untracked, not ignored files of git. Paths
matching a glob of [exempt] in quality/licenses/header.toml are skipped.

Standard library only (FE-004).

Exit codes:
  0  no finding
  1  findings on stdout; with --json <file> also written there as JSON
  2  configuration error on stderr: `licenses.config_invalid path=<path>
     line=<line> reason=<reason>` (also a dev exception without reason), or
     `licenses.inventory_failed path=<path> reason=<reason>` when pnpm,
     uv.lock or .venv cannot be read
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if not __package__:
    # Run as a script (make licenses): make the tools package importable.
    sys.path.insert(0, str(REPO_ROOT))

from tools.ci import spdx_header, third_party_notices  # noqa: E402
from tools.ci.check_layers import glob_to_regex  # noqa: E402
from tools.ci.license_inventory import (  # noqa: E402
    Dependency,
    InventoryError,
    collect_dependencies,
    tracked_files,
)

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_CONFIG = 2

LICENSE_PATH = "LICENSE"
LICENSE_SUM_PATH = "quality/licenses/license.sha256"
HEADER_PATH = "quality/licenses/header.toml"
ALLOWED_PATH = "quality/licenses/allowed.txt"
EXCEPTIONS_PATH = "quality/licenses/dev-exceptions.txt"
LICENSES_DIR = "LICENSES"

# Lockfiles searched for forbidden packages, at any depth.
LOCKFILE_NAMES = frozenset({"pnpm-lock.yaml", "uv.lock", "package-lock.json", "yarn.lock"})
# ADR-39: packages that ship the proprietary Claude Code binary must never enter
# a lockfile (06 section 8). Names read on 2026-11-01: npm @anthropic-ai/claude-code
# 2.1.316 and @anthropic-ai/claude-agent-sdk 0.3.316 list their platform packages
# (<name>-<platform>) as optionalDependencies; PyPI publishes claude-agent-sdk
# 0.2.176 (bundles the binary) and claude-code-sdk 0.0.25. A trailing `*` matches
# any rest of the name. PyPI names are in the normalized form of uv.lock.
FORBIDDEN_NPM = (
    "@anthropic-ai/claude-code",
    "@anthropic-ai/claude-code-*",
    "@anthropic-ai/claude-agent-sdk*",
)
FORBIDDEN_PYPI = ("claude-agent-sdk", "claude-code-sdk")


def _name_pattern(name: str) -> str:
    if name.endswith("*"):
        return re.escape(name[:-1]) + r"[\w.-]*"
    return re.escape(name)


# npm names anywhere in a lockfile line; PyPI names as `name = "<name>"` (uv.lock
# package entries and dependency references).
FORBIDDEN_PACKAGE = re.compile(
    r"(?:"
    + "|".join(_name_pattern(n) for n in FORBIDDEN_NPM)
    + r")(?![\w.-])"
    + r'|(?<=name = ")(?:'
    + "|".join(_name_pattern(n) for n in FORBIDDEN_PYPI)
    + r')(?=")'
)
SPDX_TOKEN = re.compile(r"\s*(\(|\)|[A-Za-z0-9.+:-]+)")
SPDX_OPERATORS = frozenset({"AND", "OR", "WITH"})

HEADER_KEYS = frozenset({"exempt", "adopted"})
EXEMPT_KEYS = frozenset({"paths"})
ADOPTED_KEYS = frozenset({"path", "license", "reason"})
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


class ConfigError(Exception):
    """A file of quality/licenses/ or the file list cannot be used."""

    def __init__(self, reason: str, path: str, line: int = 0) -> None:
        super().__init__(reason)
        self.path = path
        self.line = line


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
class Adopted:
    path: str
    license: str
    reason: str


@dataclass(frozen=True)
class HeaderConfig:
    exempt: tuple[re.Pattern[str], ...]
    adopted: dict[str, Adopted]


@dataclass(frozen=True)
class Exception_:
    key: str
    expression: str
    reason: str


@dataclass(frozen=True)
class Config:
    license_sha256: str
    header: HeaderConfig
    allowed: frozenset[str]
    exceptions: dict[str, Exception_]


# ---------------------------------------------------------------------------
# SPDX expressions


def _tokens(expression: str) -> list[str]:
    tokens = []
    position = 0
    stripped = expression.rstrip()
    while position < len(stripped):
        match = SPDX_TOKEN.match(stripped, position)
        if match is None:
            raise ValueError(f"unexpected text at {position}")
        tokens.append(match.group(1))
        position = match.end()
    return tokens


class _Parser:
    """SPDX license expressions: OR binds weaker than AND, WITH binds strongest."""

    def __init__(self, expression: str, allowed: frozenset[str]) -> None:
        self.tokens = _tokens(expression)
        self.position = 0
        self.allowed = allowed
        self.ids: list[str] = []

    def peek(self) -> str | None:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def take(self) -> str:
        token = self.peek()
        if token is None:
            raise ValueError("unexpected end")
        self.position += 1
        return token

    def parse(self) -> bool:
        if not self.tokens:
            raise ValueError("empty expression")
        value = self.or_expression()
        if self.peek() is not None:
            raise ValueError(f"unexpected {self.peek()}")
        return value

    def or_expression(self) -> bool:
        value = self.and_expression()
        while self.peek() == "OR":
            self.take()
            right = self.and_expression()
            value = value or right
        return value

    def and_expression(self) -> bool:
        value = self.with_expression()
        while self.peek() == "AND":
            self.take()
            right = self.with_expression()
            value = value and right
        return value

    def with_expression(self) -> bool:
        value = self.atom()
        if self.peek() == "WITH":
            self.take()
            # An exception only adds permissions; the license decides.
            self.ids.append(self.identifier())
        return value

    def atom(self) -> bool:
        if self.peek() == "(":
            self.take()
            value = self.or_expression()
            if self.take() != ")":
                raise ValueError("missing )")
            return value
        identifier = self.identifier()
        self.ids.append(identifier)
        return identifier in self.allowed

    def identifier(self) -> str:
        token = self.take()
        if token.upper() in SPDX_OPERATORS or token in {"(", ")"}:
            raise ValueError(f"expected an identifier, got {token}")
        return token


def is_allowed(expression: str, allowed: frozenset[str]) -> bool:
    """Whether the SPDX expression can be used under the identifiers in allowed."""
    try:
        return _Parser(expression, allowed).parse()
    except ValueError:
        return False


def license_ids(expression: str) -> list[str]:
    """License and exception identifiers of an expression; [] if it is malformed."""
    parser = _Parser(expression, frozenset())
    try:
        parser.parse()
    except ValueError:
        return []
    return parser.ids


# ---------------------------------------------------------------------------
# Configuration


def _read(root: Path, rel: str) -> str:
    try:
        return (root / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"cannot read: {exc.__class__.__name__}", rel) from exc


def config_lines(text: str) -> list[tuple[int, str]]:
    """Non-empty lines without `#` comments, with their line numbers."""
    lines = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if line:
            lines.append((number, line))
    return lines


def load_license_sha256(root: Path) -> str:
    lines = config_lines(_read(root, LICENSE_SUM_PATH))
    if len(lines) != 1:
        raise ConfigError("expected exactly one line `<sha256>  LICENSE`", LICENSE_SUM_PATH)
    number, line = lines[0]
    parts = line.split()
    if len(parts) != 2 or not SHA256_HEX.match(parts[0]) or parts[1] != LICENSE_PATH:
        raise ConfigError("expected `<sha256>  LICENSE`", LICENSE_SUM_PATH, number)
    return parts[0]


def load_allowed(root: Path) -> frozenset[str]:
    ids = set()
    for number, line in config_lines(_read(root, ALLOWED_PATH)):
        if len(line.split()) != 1:
            raise ConfigError("expected one SPDX identifier per line", ALLOWED_PATH, number)
        ids.add(line)
    return frozenset(ids)


def _string(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{where} must be a non-empty string", HEADER_PATH)
    return value.strip()


def load_header_config(root: Path) -> HeaderConfig:
    try:
        data = tomllib.loads(_read(root, HEADER_PATH))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML: {exc}", HEADER_PATH) from exc
    unknown = set(data) - HEADER_KEYS
    if unknown:
        raise ConfigError(f"unknown keys: {', '.join(sorted(unknown))}", HEADER_PATH)
    exempt = data.get("exempt", {})
    if not isinstance(exempt, dict) or set(exempt) - EXEMPT_KEYS:
        raise ConfigError("[exempt] may only hold `paths`", HEADER_PATH)
    paths = exempt.get("paths", [])
    if not isinstance(paths, list):
        raise ConfigError("exempt.paths must be a list", HEADER_PATH)
    patterns = tuple(glob_to_regex(_string(p, "exempt.paths entry")) for p in paths)
    adopted: dict[str, Adopted] = {}
    entries = data.get("adopted", [])
    if not isinstance(entries, list):
        raise ConfigError("[[adopted]] must be an array of tables", HEADER_PATH)
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != ADOPTED_KEYS:
            raise ConfigError("each [[adopted]] needs exactly path, license, reason", HEADER_PATH)
        item = Adopted(
            path=_string(entry["path"], "adopted.path"),
            license=_string(entry["license"], "adopted.license"),
            reason=_string(entry["reason"], f"adopted.reason of {entry['path']}"),
        )
        adopted[item.path] = item
    return HeaderConfig(exempt=patterns, adopted=adopted)


def load_exceptions(root: Path) -> dict[str, Exception_]:
    """dev-exceptions.txt: `<name>@<version>`, SPDX expression, reason, tab separated."""
    exceptions: dict[str, Exception_] = {}
    text = _read(root, EXCEPTIONS_PATH)
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        fields = raw.split("\t")
        if len(fields) != 3 or not all(field.strip() for field in fields):
            raise ConfigError(
                "expected three tab-separated fields <package>@<version>, SPDX expression, "
                "reason; the reason must not be empty",
                EXCEPTIONS_PATH,
                number,
            )
        key, expression, reason = (field.strip() for field in fields)
        if key in exceptions:
            raise ConfigError(f"duplicate entry {key}", EXCEPTIONS_PATH, number)
        exceptions[key] = Exception_(key, expression, reason)
    return exceptions


def load_config(root: Path) -> Config:
    return Config(
        license_sha256=load_license_sha256(root),
        header=load_header_config(root),
        allowed=load_allowed(root),
        exceptions=load_exceptions(root),
    )


def _lock_line(text: str, dep: Dependency) -> tuple[int, int]:
    """Line and column of the package in its lockfile text; (1, 1) if not found."""
    name, version = re.escape(dep.name), re.escape(dep.version)
    if dep.ecosystem == "npm":
        pattern = re.compile(rf"^\s+'?({name}@{version})(?:['(:])", re.MULTILINE)
    else:
        pattern = re.compile(rf'^(name = "{name}")\nversion = "{version}"$', re.MULTILINE)
    match = pattern.search(text)
    if match is None:
        return 1, 1
    start = match.start(1)
    line = text.count("\n", 0, start) + 1
    return line, start - (text.rfind("\n", 0, start) + 1) + 1


# ---------------------------------------------------------------------------
# Checks


class Checker:
    def __init__(
        self, root: Path, config: Config, files: Sequence[str], deps: Sequence[Dependency]
    ) -> None:
        self.root = root
        self.config = config
        self.files = files
        self.deps = deps
        self.findings: list[Finding] = []
        # SPDX identifier -> first place that uses it, for license-text-missing.
        self.used_ids: dict[str, tuple[str, int]] = {}
        self.lock_texts: dict[str, str] = {}

    def use(self, expression: str, path: str, line: int) -> None:
        for identifier in license_ids(expression):
            self.used_ids.setdefault(identifier, (path, line))

    def report(self, path: str, line: int, rule: str, message: str, col: int = 1) -> None:
        self.findings.append(Finding(path, line, col, rule, message))

    def check_license_file(self) -> None:
        try:
            data = (self.root / LICENSE_PATH).read_bytes()
        except OSError:
            self.report(LICENSE_PATH, 1, "license-file-modified", "LICENSE is missing")
            return
        if hashlib.sha256(data).hexdigest() != self.config.license_sha256:
            self.report(
                LICENSE_PATH,
                1,
                "license-file-modified",
                f"LICENSE is not the Apache-2.0 text whose SHA-256 is in {LICENSE_SUM_PATH}",
            )

    def is_exempt(self, path: str) -> bool:
        return any(pattern.match(path) for pattern in self.config.header.exempt)

    def check_headers(self) -> None:
        for path in self.files:
            if self.is_exempt(path):
                continue
            try:
                spdx_header.comment_prefix(Path(path))
            except ValueError:
                continue
            try:
                text = (self.root / path).read_text(encoding="utf-8")
            except UnicodeDecodeError:
                self.report(path, 1, "spdx-header-missing", "not UTF-8 text, header unreadable")
                continue
            if spdx_header.has_header(Path(path), text):
                self.use(spdx_header.HEADER_LINES[0].split(":", 1)[1].strip(), path, 1)
                continue
            self.check_adopted(path, text)

    def check_adopted(self, path: str, text: str) -> None:
        tags = spdx_header.header_tags(Path(path), text)
        by_tag: dict[str, list[tuple[int, str]]] = {}
        for number, tag, value in tags:
            by_tag.setdefault(tag, []).append((number, value))
        licenses = by_tag.get(spdx_header.LICENSE_TAG, [])
        if not (
            licenses and spdx_header.COPYRIGHT_TAG in by_tag and spdx_header.ORIGIN_TAG in by_tag
        ):
            self.report(
                path,
                1,
                "spdx-header-missing",
                f"no SPDX header in the first {spdx_header.MAX_LINE} lines: expected "
                "'SPDX-License-Identifier: Apache-2.0' and 'SPDX-FileCopyrightText: The "
                "Guildwork Authors', or for an adopted file the header of its source with "
                "an Origin line",
            )
            return
        number, expression = licenses[0]
        entry = self.config.header.adopted.get(path)
        if is_allowed(expression, self.config.allowed) or (
            entry is not None and entry.license == expression
        ):
            self.use(expression, path, number)
            return
        self.report(
            path,
            number,
            "adopted-license-not-allowed",
            f"license {expression} is not in {ALLOWED_PATH} and not listed for this path "
            f"in {HEADER_PATH}",
        )

    def lock_location(self, dep: Dependency) -> tuple[int, int]:
        if dep.lockfile not in self.lock_texts:
            try:
                text = (self.root / dep.lockfile).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                text = ""
            self.lock_texts[dep.lockfile] = text
        return _lock_line(self.lock_texts[dep.lockfile], dep)

    def check_dependencies(self) -> None:
        for dep in sorted(self.deps, key=lambda d: (d.ecosystem, d.name, d.version)):
            expression = dep.license
            allowed = expression is not None and is_allowed(expression, self.config.allowed)
            if dep.runtime:
                if allowed and expression is not None:
                    line, _ = self.lock_location(dep)
                    self.use(expression, dep.lockfile, line)
                    continue
                rule = "runtime-license-not-allowed"
                message = (
                    f"runtime dependency {dep.key} has license {expression or 'none declared'}, "
                    f"not allowed by {ALLOWED_PATH}"
                )
            else:
                if allowed or dep.key in self.config.exceptions:
                    continue
                rule = "dev-license-needs-exception"
                message = (
                    f"development dependency {dep.key} has license "
                    f"{expression or 'none declared'}; allow it or add `{dep.key}<TAB>"
                    f"<SPDX expression><TAB><reason>` to {EXCEPTIONS_PATH}"
                )
            line, col = self.lock_location(dep)
            self.report(dep.lockfile, line, rule, message, col)

    def check_license_texts(self) -> None:
        for identifier in sorted(self.used_ids):
            text = f"{LICENSES_DIR}/{identifier}.txt"
            if not (self.root / text).is_file():
                path, line = self.used_ids[identifier]
                self.report(path, line, "license-text-missing", f"{identifier} needs {text}")

    def check_lockfiles(self) -> None:
        for path in self.files:
            if Path(path).name not in LOCKFILE_NAMES:
                continue
            text = (self.root / path).read_text(encoding="utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), start=1):
                for match in FORBIDDEN_PACKAGE.finditer(line):
                    self.report(
                        path,
                        number,
                        "forbidden-package",
                        f"{match.group(0)} ships the proprietary Claude Code binary and "
                        "must not be a dependency (ADR-39)",
                        match.start() + 1,
                    )

    def check_notices(self) -> None:
        for finding in third_party_notices.check(self.root, self.deps):
            location, rule, message = finding.split(" ", 2)
            path, line, col = location.rsplit(":", 2)
            self.report(path, int(line), rule, message, int(col))

    def run(self) -> list[Finding]:
        self.check_license_file()
        self.check_headers()
        self.check_dependencies()
        self.check_license_texts()
        self.check_lockfiles()
        self.check_notices()
        return self.findings


def check(root: Path, deps: Sequence[Dependency] | None = None) -> list[Finding]:
    """Findings of the repository at root.

    deps None collects the dependencies with license_inventory.py. Raises
    ConfigError on configuration errors and InventoryError if the dependencies
    cannot be read; configuration is read first.
    """
    config = load_config(root)
    files = tracked_files(root)
    if deps is None:
        deps = collect_dependencies(root)
    return Checker(root, config, files, deps).run()


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check licenses, headers and dependencies.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    parser.add_argument("--json", type=Path, help="also write the findings as JSON to this file")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = load_config(args.root)
        files = tracked_files(args.root)
        deps = collect_dependencies(args.root)
    except ConfigError as exc:
        print(
            f"licenses.config_invalid path={exc.path} line={exc.line} reason={exc}",
            file=sys.stderr,
        )
        return EXIT_CONFIG
    except InventoryError as exc:
        print(f"licenses.inventory_failed path={exc.path} reason={exc}", file=sys.stderr)
        return EXIT_CONFIG
    findings = Checker(args.root, config, files, deps).run()
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
