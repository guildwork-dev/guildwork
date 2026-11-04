#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Check the dependency rules between workspace packages (FE-007).

`quality/layers.toml` is the only place of the rules. Every directory below
apps/, packages/, plugins/, drivers/, services/ and eval/ that holds a
package.json is a workspace package (the search does not descend into a
package). The checker reports:

  forbidden-dependency             a workspace package in dependencies,
                                   devDependencies or peerDependencies that the
                                   entry's may_import does not allow
  forbidden-import                 the same for an import specifier in *.ts,
                                   *.tsx or *.mts (static, dynamic, export from,
                                   import type, typeof import)
  relative-import-across-packages  a relative or absolute specifier that leaves
                                   the package directory
  test-only-import                 a [test_only] package or subpath imported
                                   outside the test files of file_globs
  test-only-dependency             a [test_only] package outside devDependencies
  type-only-import                 a value import of a package in type_only;
                                   only `import type`, `export type` and
                                   `typeof import()` are type-only, because
                                   verbatimModuleSyntax keeps `import { type A }`
  dependency-cycle                 a cycle in the graph of dependencies and imports

Test-only packages may be used by every package, in test files and as a
devDependency. Specifiers are read with a small scanner that skips comments,
strings and template literals; a dynamic import without a string literal
argument is not checked. Rules inside a package are Opengrep's job.

Standard library only (FE-004).

Exit codes:
  0  no finding
  1  findings, printed as `path:line:col rule-id message` on stdout
  2  configuration error on stderr: `layers.config_invalid path=<path>
     reason=<reason>`, or `layers.unknown_package path=<dir>` for a package
     without entry in layers.toml
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
import tomllib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_CONFIG = 2

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYERS_PATH = Path("quality/layers.toml")

# Top-level directories that hold workspace packages (section 2.1).
PACKAGE_ROOTS = ("apps", "packages", "plugins", "drivers", "services", "eval")
SKIP_DIRS = frozenset({"node_modules", "dist", "coverage"})
SOURCE_SUFFIXES = (".ts", ".tsx", ".mts")
SCOPE = "@guildwork/"
GROUP_PREFIX = "group:"
DEPENDENCY_FIELDS = ("dependencies", "devDependencies", "peerDependencies")
PACKAGE_KEYS = frozenset({"path", "may_import", "type_only"})
TEST_ONLY_KEYS = frozenset({"packages", "subpaths", "file_globs"})
TOP_KEYS = frozenset({"groups", "package", "test_only"})


class ConfigError(Exception):
    """layers.toml, a package.json or the package set cannot be used."""

    def __init__(self, reason: str, path: str = LAYERS_PATH.as_posix()) -> None:
        super().__init__(reason)
        self.path = path


class UnknownPackageError(Exception):
    """A workspace package has no entry in layers.toml."""

    def __init__(self, path: str) -> None:
        super().__init__(path)
        self.path = path


@dataclass(frozen=True)
class Entry:
    path: str
    may_import: tuple[str, ...]
    type_only: tuple[str, ...]


@dataclass(frozen=True)
class Layers:
    groups: dict[str, tuple[str, ...]]
    entries: tuple[Entry, ...]
    test_packages: frozenset[str]
    test_subpaths: frozenset[str]
    test_globs: tuple[re.Pattern[str], ...]


@dataclass
class Package:
    path: str
    name: str
    manifest: dict[str, object]
    manifest_text: str
    entry: Entry | None = None
    allowed: frozenset[str] = frozenset()
    type_only: frozenset[str] = frozenset()
    edges: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class Specifier:
    value: str
    line: int
    col: int
    type_only: bool


# ---------------------------------------------------------------------------
# Configuration


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a path glob: `**/` any directories, `*` and `?` within one part."""
    out = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def _strings(value: object, where: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise ConfigError(f"{where} must be an array of non-empty strings")
    return tuple(value)


def load_layers(path: Path) -> Layers:
    """Read and validate layers.toml; raise ConfigError with the reason."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"unreadable: {exc}") from exc
    return parse_layers(text)


def parse_layers(text: str) -> Layers:
    """Validate the text of layers.toml; raise ConfigError with the reason."""
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"unreadable: {exc}") from exc
    unknown = sorted(set(data) - TOP_KEYS)
    if unknown:
        raise ConfigError(f"unknown key {', '.join(unknown)}")

    raw_groups = data.get("groups", {})
    if not isinstance(raw_groups, dict):
        raise ConfigError("groups must be a table")
    groups = {name: _strings(v, f"groups.{name}") for name, v in raw_groups.items()}

    raw_entries = data.get("package", [])
    if not isinstance(raw_entries, list) or not raw_entries:
        raise ConfigError("no [[package]] entry")
    entries: list[Entry] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_entries):
        where = f"package[{index}]"
        if not isinstance(raw, dict):
            raise ConfigError(f"{where} must be a table")
        bad = sorted(set(raw) - PACKAGE_KEYS)
        if bad:
            raise ConfigError(f"{where}: unknown key {', '.join(bad)}")
        entry_path = raw.get("path")
        if not isinstance(entry_path, str) or not entry_path:
            raise ConfigError(f"{where}: path must be a non-empty string")
        if entry_path in seen:
            raise ConfigError(f"duplicate package path {entry_path!r}")
        seen.add(entry_path)
        where = f"package {entry_path}"
        may_import = _strings(raw.get("may_import"), f"{where}: may_import")
        type_only = _strings(raw.get("type_only", []), f"{where}: type_only")
        for item in may_import:
            if item.startswith(GROUP_PREFIX):
                if item[len(GROUP_PREFIX) :] not in groups:
                    raise ConfigError(f"{where}: unknown group {item!r}")
            elif not item.startswith(SCOPE):
                raise ConfigError(f"{where}: may_import {item!r} must start with {SCOPE} or group:")
        for item in type_only:
            if item not in may_import:
                raise ConfigError(f"{where}: type_only {item!r} is not in may_import")
        entries.append(Entry(entry_path, may_import, type_only))

    raw_test = data.get("test_only", {})
    if not isinstance(raw_test, dict):
        raise ConfigError("test_only must be a table")
    bad = sorted(set(raw_test) - TEST_ONLY_KEYS)
    if bad:
        raise ConfigError(f"test_only: unknown key {', '.join(bad)}")
    return Layers(
        groups=groups,
        entries=tuple(entries),
        test_packages=frozenset(_strings(raw_test.get("packages", []), "test_only.packages")),
        test_subpaths=frozenset(_strings(raw_test.get("subpaths", []), "test_only.subpaths")),
        test_globs=tuple(
            glob_to_regex(g) for g in _strings(raw_test.get("file_globs", []), "file_globs")
        ),
    )


# ---------------------------------------------------------------------------
# Workspace


def find_packages(root: Path) -> list[str]:
    """Directories (relative, posix) below PACKAGE_ROOTS that hold a package.json."""
    found: list[str] = []

    def walk(directory: Path) -> None:
        if (directory / "package.json").is_file():
            found.append(directory.relative_to(root).as_posix())
            return
        for child in sorted(directory.iterdir()):
            if child.is_dir() and child.name not in SKIP_DIRS and not child.name.startswith("."):
                walk(child)

    for top in PACKAGE_ROOTS:
        if (root / top).is_dir():
            walk(root / top)
    return found


def read_package(root: Path, path: str) -> Package:
    manifest_path = f"{path}/package.json"
    try:
        text = (root / manifest_path).read_text(encoding="utf-8")
        manifest = json.loads(text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"unreadable: {exc}", manifest_path) from exc
    if not isinstance(manifest, dict):
        raise ConfigError("must be a JSON object", manifest_path)
    name = manifest.get("name")
    if not isinstance(name, str) or not name.startswith(SCOPE):
        raise ConfigError(f"name must start with {SCOPE}", manifest_path)
    for key in DEPENDENCY_FIELDS:
        if not isinstance(manifest.get(key, {}), dict):
            raise ConfigError(f"{key} must be an object", manifest_path)
    return Package(path=path, name=name, manifest=manifest, manifest_text=text)


def match_entry(layers: Layers, path: str) -> Entry:
    """The exact entry for a package directory, else the only glob entry."""
    for entry in layers.entries:
        if entry.path == path:
            return entry
    globs = [e for e in layers.entries if glob_to_regex(e.path).match(path)]
    if len(globs) > 1:
        names = ", ".join(e.path for e in globs)
        raise ConfigError(f"package {path} matches several entries: {names}")
    if not globs:
        raise UnknownPackageError(path)
    return globs[0]


def resolve(layers: Layers, packages: Sequence[Package]) -> None:
    """Attach entries and expand may_import groups to package names."""
    by_name: dict[str, str] = {}
    for package in packages:
        if package.name in by_name:
            raise ConfigError(
                f"name {package.name} also used by {by_name[package.name]}",
                f"{package.path}/package.json",
            )
        by_name[package.name] = package.path
    for package in packages:
        entry = match_entry(layers, package.path)
        allowed = {package.name}
        for item in entry.may_import:
            if item.startswith(GROUP_PREFIX):
                members = [glob_to_regex(m) for m in layers.groups[item[len(GROUP_PREFIX) :]]]
                allowed.update(p.name for p in packages if any(m.match(p.path) for m in members))
            else:
                allowed.add(item)
        package.entry = entry
        package.allowed = frozenset(allowed)
        package.type_only = frozenset(entry.type_only)


# ---------------------------------------------------------------------------
# Source scanning

_REGEX_PRECEDERS = set("(,=:[!&|?{};+-*%<>~^")
_REGEX_KEYWORDS = ("return", "typeof", "case", "do", "else", "in", "of", "void", "yield", "await")


def mask_source(text: str) -> tuple[str, dict[int, str]]:
    """Blank out comments, string contents and template literals.

    Returns the masked text (same length, newlines kept, quote characters of
    string literals kept) and the value of each string literal by the offset
    of its opening quote.
    """
    out = list(text)
    literals: dict[int, str] = {}
    i, n = 0, len(text)
    last = ""  # last significant character outside comments and strings

    def blank(start: int, end: int) -> None:
        for k in range(start, end):
            if out[k] != "\n":
                out[k] = " "

    while i < n:
        c = text[i]
        if text.startswith("//", i):
            end = text.find("\n", i)
            end = n if end < 0 else end
            blank(i, end)
            i = end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            blank(i, end)
            i = end
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            literals[i] = text[i + 1 : j]
            blank(i + 1, j)
            i = j + 1
            last = c
        elif c == "`":
            j = i + 1
            depth = 0
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if depth == 0 and text[j] == "`":
                    break
                if text.startswith("${", j):
                    depth += 1
                    j += 2
                    continue
                if depth and text[j] == "}":
                    depth -= 1
                j += 1
            blank(i, min(j + 1, n))
            i = j + 1
            last = "`"
        elif c == "/" and _regex_allowed(text, i, last):
            j = i + 1
            in_class = False
            while j < n and text[j] != "\n":
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == "[":
                    in_class = True
                elif text[j] == "]":
                    in_class = False
                elif text[j] == "/" and not in_class:
                    break
                j += 1
            blank(i, min(j + 1, n))
            i = j + 1
            last = "/"
        else:
            if not c.isspace():
                last = c
            i += 1
    return "".join(out), literals


def _regex_allowed(text: str, i: int, last: str) -> bool:
    """Whether a slash at i starts a regular expression literal."""
    if last == "" or last in _REGEX_PRECEDERS:
        return True
    head = text[:i].rstrip()
    return any(re.search(rf"(?<![\w$.]){kw}\Z", head) for kw in _REGEX_KEYWORDS)


_Q = r"(?P<q>[\"'])"
_CLAUSE = r"[\w$\s{},*]*?"
_PATTERNS: tuple[tuple[re.Pattern[str], bool | None], ...] = (
    # import type X from "m", import type { X } from "m", export type { X } from "m"
    (
        re.compile(
            rf"(?<![\w$.])(?:import|export)\s+type\s+(?!from\s*[\"']){_CLAUSE}\bfrom\s*{_Q}"
        ),
        True,
    ),
    # import X from "m", import { X } from "m", export * from "m", export { X } from "m"
    (re.compile(rf"(?<![\w$.])(?:import|export)\s+{_CLAUSE}\bfrom\s*{_Q}"), False),
    # import "m"
    (re.compile(rf"(?<![\w$.])import\s*{_Q}"), False),
    # import("m"); typeof import("m") is type-only (decided below)
    (re.compile(rf"(?<![\w$.])import\s*\(\s*{_Q}"), None),
)
_TYPEOF_BEFORE = re.compile(r"(?<![\w$.])typeof\s*\Z")


def scan_specifiers(text: str) -> list[Specifier]:
    """Every module specifier of a TypeScript source with its position."""
    masked, literals = mask_source(text)
    found: dict[int, Specifier] = {}
    for pattern, type_only in _PATTERNS:
        for match in pattern.finditer(masked):
            quote = match.start("q")
            if quote in found or quote not in literals:
                continue
            if type_only is None:
                is_type = bool(_TYPEOF_BEFORE.search(masked, 0, match.start()))
            else:
                is_type = type_only
            line = masked.count("\n", 0, quote) + 1
            col = quote - (masked.rfind("\n", 0, quote) + 1) + 1
            found[quote] = Specifier(literals[quote], line, col, is_type)
    return [found[k] for k in sorted(found)]


def source_files(root: Path, package: str) -> Iterator[str]:
    def walk(directory: Path) -> Iterator[str]:
        for child in sorted(directory.iterdir()):
            if child.is_dir():
                if child.name in SKIP_DIRS or child.name.startswith("."):
                    continue
                if (child / "package.json").is_file():
                    continue
                yield from walk(child)
            elif child.name.endswith(SOURCE_SUFFIXES) and not child.name.endswith(".d.ts"):
                yield child.relative_to(root).as_posix()

    yield from walk(root / package)


# ---------------------------------------------------------------------------
# Checks


def package_name(specifier: str) -> str:
    """`@guildwork/db/testing` -> `@guildwork/db`."""
    parts = specifier.split("/")
    return "/".join(parts[:2])


def _key_position(text: str, field_name: str, key: str) -> tuple[int, int]:
    """Line and column of a dependency key in package.json text."""
    start = text.find(f'"{field_name}"')
    index = text.find(f'"{key}"', max(start, 0))
    if index < 0:
        return 1, 1
    line = text.count("\n", 0, index) + 1
    return line, index - (text.rfind("\n", 0, index) + 1) + 1


class Checker:
    def __init__(self, root: Path, layers: Layers, packages: Sequence[Package]) -> None:
        self.root = root
        self.layers = layers
        self.packages = packages
        self.names = {p.name for p in packages}
        self.findings: list[str] = []

    def report(self, path: str, line: int, col: int, rule: str, message: str) -> None:
        self.findings.append(f"{path}:{line}:{col} {rule} {message}")

    def is_test_file(self, path: str) -> bool:
        return any(g.match(path) for g in self.layers.test_globs)

    def check_manifest(self, package: Package) -> None:
        location = f"{package.path}/package.json"
        for field_name in DEPENDENCY_FIELDS:
            deps = package.manifest.get(field_name, {})
            if not isinstance(deps, dict):  # rejected in read_package already
                continue
            for dep in deps:
                if not dep.startswith(SCOPE) or dep == package.name:
                    continue
                line, col = _key_position(package.manifest_text, field_name, dep)
                if dep in self.layers.test_packages:
                    if field_name != "devDependencies":
                        self.report(
                            location,
                            line,
                            col,
                            "test-only-dependency",
                            f"{dep} is test only and may appear only in devDependencies",
                        )
                elif dep not in package.allowed:
                    self.report(
                        location,
                        line,
                        col,
                        "forbidden-dependency",
                        f"{package.name} may not depend on {dep} (quality/layers.toml)",
                    )
                if dep in self.names:
                    package.edges.add(dep)

    def check_sources(self, package: Package) -> None:
        for path in source_files(self.root, package.path):
            try:
                text = (self.root / path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise ConfigError(f"unreadable: {exc}", path) from exc
            test_file = self.is_test_file(path)
            for spec in scan_specifiers(text):
                self.check_specifier(package, path, spec, test_file)

    def check_specifier(self, package: Package, path: str, spec: Specifier, test: bool) -> None:
        value = spec.value
        where = (path, spec.line, spec.col)
        if value.startswith((".", "/")):
            base = posixpath.dirname(path)
            target = posixpath.normpath(posixpath.join(base, value)) if value[0] == "." else value
            if not (target + "/").startswith(package.path + "/"):
                self.report(
                    *where,
                    "relative-import-across-packages",
                    f"{value!r} leaves {package.path}; import the package by name",
                )
            return
        if not value.startswith(SCOPE):
            return  # external packages are the license gate's job
        name = package_name(value)
        if name in self.names and name != package.name:
            package.edges.add(name)
        if name in self.layers.test_packages or value in self.layers.test_subpaths:
            if not test:
                self.report(
                    *where, "test-only-import", f"{value} may be imported only in test files"
                )
            if name in self.layers.test_packages:
                return
        if name not in package.allowed:
            self.report(
                *where,
                "forbidden-import",
                f"{package.name} may not import {name} (quality/layers.toml)",
            )
        elif name in package.type_only and not spec.type_only:
            self.report(
                *where,
                "type-only-import",
                f"{package.name} may import {name} only with 'import type'",
            )

    def check_cycles(self) -> None:
        graph = {p.name: sorted(p.edges) for p in self.packages}
        by_name = {p.name: p for p in self.packages}
        state: dict[str, int] = {}
        stack: list[str] = []
        reported: set[frozenset[str]] = set()

        def visit(node: str) -> None:
            state[node] = 1
            stack.append(node)
            for nxt in graph.get(node, []):
                if state.get(nxt) == 1:
                    cycle = stack[stack.index(nxt) :]
                    key = frozenset(cycle)
                    if key not in reported:
                        reported.add(key)
                        path = " -> ".join([*cycle, nxt])
                        self.report(
                            f"{by_name[nxt].path}/package.json",
                            1,
                            1,
                            "dependency-cycle",
                            f"workspace packages form a cycle: {path}",
                        )
                elif nxt not in state:
                    visit(nxt)
            stack.pop()
            state[node] = 2

        for name in sorted(graph):
            if name not in state:
                visit(name)

    def run(self) -> list[str]:
        for package in self.packages:
            self.check_manifest(package)
            self.check_sources(package)
        self.check_cycles()
        return self.findings


def check(root: Path) -> list[str]:
    """Findings of the workspace below root; raises on configuration errors."""
    layers = load_layers(root / LAYERS_PATH)
    packages = [read_package(root, path) for path in find_packages(root)]
    resolve(layers, packages)
    return Checker(root, layers, packages).run()


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check the workspace dependency rules.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        findings = check(args.root)
    except UnknownPackageError as exc:
        print(
            f"layers.unknown_package path={exc.path} reason=no entry in {LAYERS_PATH.as_posix()}",
            file=sys.stderr,
        )
        return EXIT_CONFIG
    except ConfigError as exc:
        print(f"layers.config_invalid path={exc.path} reason={exc}", file=sys.stderr)
        return EXIT_CONFIG
    for finding in findings:
        print(finding)
    return EXIT_FINDINGS if findings else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
