#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Check the relative links and anchors of the tracked Markdown files.

Usage:

  links.py [--root DIR] [--json FILE] [PATH ...]

Without PATH every Markdown file that `git ls-files` lists is checked; with
PATH only those, relative to the root. Links are inline links and images
(`[text](target)`), reference definitions (`[label]: target`) and the `href`
and `src` attributes of HTML tags, outside fenced code blocks and inline code.

Rules:

  link-private-path   the target as written, or resolved to a path from the
                      repository root, matches a pattern of
                      quality/text/private-path-patterns.txt (checked first,
                      also for links with a scheme such as file:); the
                      output names the target only as target-<sha256[:12]>
  link-outside-repo   a relative target resolves to a path above the root
  link-missing-file   the target is no tracked file and no directory that holds
                      one; a target starting with `/` counts from the root
  link-missing-anchor the fragment names no anchor of the target Markdown file
                      (or of the file itself for `#fragment`): headings, slugged
                      as the hoster does (lower case, punctuation removed, spaces
                      to hyphens, `-1`, `-2` for repeated headings), and the
                      `id` or `name` of HTML tags

Other links with a scheme (https:, mailto:) are not followed, and fragments of
non-Markdown targets (line anchors) are not checked. Only tracked files count as
targets, since a clean checkout in CI has nothing else.

Standard library only (FE-004).

Exit codes:
  0  no finding
  1  findings, printed as `<path>:<line>:<column> <rule> <target>` on stdout;
     with --json also written to that file
  2  usage or configuration error on stderr: links.config_invalid,
     links.file_unreadable, links.git_failed; no report is written
"""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import subprocess
import sys
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parents[2]
if not __package__:
    # Run as a script (make links): make the tools package importable.
    sys.path.insert(0, str(REPO_ROOT))

from tools.hooks.text_rules import prose_lines  # noqa: E402

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2

PATTERNS_PATH = Path("quality/text/private-path-patterns.txt")
MARKDOWN_SUFFIXES = (".md", ".markdown")

INLINE_LINK_RE = re.compile(
    r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*(<[^>\n]*>|[^\s()]+(?:\([^\s()]*\)[^\s()]*)*)"
    r"(?:\s+\"[^\"]*\"|\s+'[^']*')?\s*\)"
)
# A label starting with ^ is a footnote, not a link definition.
REFERENCE_RE = re.compile(r" {0,3}\[(?!\^)[^\]]+\]:\s*(<[^>\n]*>|\S+)")
HTML_LINK_RE = re.compile(r"<[A-Za-z][^>]*?\s(?:href|src)\s*=\s*\"([^\"]*)\"")
HTML_ANCHOR_RE = re.compile(r"<[A-Za-z][^>]*?\s(?:id|name)\s*=\s*\"([^\"]+)\"")
SCHEME_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
ATX_RE = re.compile(r" {0,3}(#{1,6})(?:[ \t]+(.*?))?(?:[ \t]+#+)?[ \t]*$")
SETEXT_RE = re.compile(r" {0,3}(?:=+|-+)[ \t]*$")
# Lines that start a list item, quote, table row or HTML block.
NOT_SETEXT_RE = re.compile(r"(?:[-*+>|<]|\d+[.)])(?:\s|$)|[|<]")
HEADING_LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
HTML_TAG_RE = re.compile(r"<[^>]+>")


class ConfigError(Exception):
    """The pattern file cannot be used (exit 2)."""


class UsageError(Exception):
    """A file argument or git cannot be used (exit 2)."""

    def __init__(self, event: str, detail: str) -> None:
        super().__init__(f"{event} {detail}")


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    column: int
    rule: str
    target: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}:{self.column} {self.rule} {self.target}"


@dataclass(frozen=True)
class Link:
    line: int
    column: int
    target: str


def load_patterns(root: Path) -> tuple[re.Pattern[str], ...]:
    try:
        lines = (root / PATTERNS_PATH).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"path={PATTERNS_PATH} reason={type(exc).__name__}") from None
    patterns: list[re.Pattern[str]] = []
    for number, line in enumerate(lines, start=1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        try:
            patterns.append(re.compile(text))
        except re.error:
            raise ConfigError(f"path={PATTERNS_PATH} line={number} reason=invalid regex") from None
    if not patterns:
        raise ConfigError(f"path={PATTERNS_PATH} reason=no pattern")
    return tuple(patterns)


# Markdown ---------------------------------------------------------------------


def find_links(text: str) -> list[Link]:
    """Every link outside code, with its line and the column where it starts."""
    found: list[Link] = []
    lines = text.split("\n")
    for number, prose in enumerate(prose_lines(lines), start=1):
        if prose is None:
            continue
        for regex in (INLINE_LINK_RE, REFERENCE_RE, HTML_LINK_RE):
            matches = [regex.match(prose)] if regex is REFERENCE_RE else regex.finditer(prose)
            for match in matches:
                if match is not None:
                    found.append(Link(number, match.start() + 1, match.group(1).strip("<>")))
    found.sort(key=lambda link: (link.line, link.column))
    return found


def slug(heading: str) -> str:
    """The anchor the hoster gives a heading text."""
    text = HEADING_LINK_RE.sub(r"\1", heading)
    text = HTML_TAG_RE.sub("", text).strip().lower()
    kept = (
        char
        for char in text
        if char.isalnum() or char in "-_ " or unicodedata.category(char).startswith("M")
    )
    return "".join(kept).replace(" ", "-")


def anchors(text: str) -> frozenset[str]:
    """The heading slugs and HTML ids of a Markdown text."""
    lines = text.split("\n")
    found: set[str] = set()
    counts: dict[str, int] = {}

    def add_heading(title: str) -> None:
        base = slug(title)
        count = counts.get(base, 0)
        counts[base] = count + 1
        found.add(base if count == 0 else f"{base}-{count}")

    previous: str | None = None
    for raw, prose in zip(lines, prose_lines(lines), strict=True):
        line = raw.removesuffix("\r")
        if prose is None:
            previous = None
            continue
        found.update(HTML_ANCHOR_RE.findall(line))
        atx = ATX_RE.match(line)
        if atx:
            add_heading(atx.group(2) or "")
            previous = None
            continue
        if previous and SETEXT_RE.match(line):
            add_heading(previous)
            previous = None
            continue
        # Only a plain paragraph line can become a setext heading.
        stripped = line.strip()
        previous = None if not stripped or NOT_SETEXT_RE.match(stripped) else stripped
    return frozenset(found)


# Checks -----------------------------------------------------------------------


def tracked_files(root: Path) -> list[str]:
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), "ls-files", "-z"],  # noqa: S607
            check=False,
            capture_output=True,
        )
    except OSError:
        raise UsageError("links.git_failed", "reason=os_error") from None
    if result.returncode != 0:
        raise UsageError("links.git_failed", "command=ls-files")
    return [name for name in result.stdout.decode("utf-8").split("\0") if name]


class Checker:
    def __init__(self, root: Path, patterns: Sequence[re.Pattern[str]]) -> None:
        self.root = root
        self.patterns = tuple(patterns)
        self.files = frozenset(tracked_files(root))
        self.dirs = frozenset(parent for name in self.files for parent in _parents(name))
        self._anchors: dict[str, frozenset[str]] = {}

    def anchors_of(self, path: str) -> frozenset[str]:
        if path not in self._anchors:
            try:
                text = (self.root / path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                text = ""
            self._anchors[path] = anchors(text)
        return self._anchors[path]

    def private(self, *candidates: str) -> bool:
        return any(p.search(c) for p in self.patterns for c in candidates)

    def check_link(self, path: str, link: Link) -> str | None:
        """The rule a link breaks, or None."""
        target = link.target
        if SCHEME_RE.match(target) or target.startswith("//"):
            return "link-private-path" if self.private(target) else None
        location, _, fragment = target.partition("#")
        location = unquote(location.partition("?")[0])
        if not location:
            resolved = path
        elif location.startswith("/"):
            resolved = posixpath.normpath(location.lstrip("/") or ".")
        else:
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), location))
        if self.private(target, resolved):
            return "link-private-path"
        if resolved == ".." or resolved.startswith("../"):
            return "link-outside-repo"
        if resolved not in self.files and resolved not in self.dirs and resolved != ".":
            return "link-missing-file"
        if (
            fragment
            and resolved.endswith(MARKDOWN_SUFFIXES)
            and resolved in self.files
            and unquote(fragment) not in self.anchors_of(resolved)
        ):
            return "link-missing-anchor"
        return None

    def check_file(self, path: str) -> list[Finding]:
        try:
            text = (self.root / path).read_text(encoding="utf-8")
        except FileNotFoundError:
            raise UsageError("links.file_unreadable", f"path={path} reason=not_found") from None
        except (OSError, UnicodeDecodeError) as exc:
            raise UsageError(
                "links.file_unreadable", f"path={path} reason={type(exc).__name__}"
            ) from None
        findings: list[Finding] = []
        for link in find_links(text):
            rule = self.check_link(path, link)
            if rule is not None:
                findings.append(
                    Finding(path, link.line, link.column, rule, shown(rule, link.target))
                )
        return findings


def _parents(name: str) -> Iterable[str]:
    parent = posixpath.dirname(name)
    while parent:
        yield parent
        parent = posixpath.dirname(parent)


def shown(rule: str, target: str) -> str:
    """The target for the output; a private one only as target-<sha256[:12]>,
    since CI logs of a public repository are public (as in FE-023)."""
    if rule != "link-private-path":
        return target
    return "target-" + hashlib.sha256(target.encode("utf-8")).hexdigest()[:12]


def _relative(root: Path, argument: str) -> str:
    """A path argument relative to the root; absolute ones are made relative."""
    candidate = Path(argument)
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(root.resolve())
        except ValueError:
            raise UsageError(
                "links.file_unreadable", f"path={argument} reason=outside_root"
            ) from None
    return candidate.as_posix()


def check_files(
    root: Path, paths: Iterable[str], patterns: Sequence[re.Pattern[str]]
) -> list[Finding]:
    checker = Checker(root, patterns)
    findings: list[Finding] = []
    for path in paths:
        findings.extend(checker.check_file(path))
    return sorted(findings)


def write_report(path: Path, findings: Sequence[Finding]) -> None:
    report = {
        "tool": "links",
        "findings": [
            {"path": f.path, "line": f.line, "column": f.column, "rule": f.rule, "target": f.target}
            for f in findings
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check relative links and anchors in Markdown.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    parser.add_argument("--json", type=Path, help="also write the findings to this file")
    parser.add_argument("paths", nargs="*", help="Markdown files (default: all tracked ones)")
    args = parser.parse_args(argv)
    root: Path = args.root
    try:
        patterns = load_patterns(root)
        paths = [_relative(root, p) for p in args.paths] or [
            name for name in tracked_files(root) if name.endswith(MARKDOWN_SUFFIXES)
        ]
        findings = check_files(root, paths, patterns)
    except ConfigError as exc:
        print(f"links.config_invalid {exc}", file=sys.stderr)
        return EXIT_USAGE
    except UsageError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE
    for finding in findings:
        print(finding)
    if args.json is not None:
        write_report(args.json, findings)
    print(f"links: {len(findings)} findings in {len(paths)} files")
    return EXIT_FINDINGS if findings else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
