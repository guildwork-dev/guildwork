#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Rewrite the links of translated documents from the German to the English paths.

Usage:

  relink.py --linkmap FILE --german DIR [--root DIR] [--peer DIR ...] [--check]
            [--json FILE] [PATH ...]

The translation step of detailed design 00 section 4.6 keeps every link target
of the German source as written. This run rewrites them deterministically:

  path       a relative link target that names a German file or folder of the
             ops repo becomes the relative path of its English counterpart, from
             the table `dateien` of the linkmap (one file each) or else the
             longest matching prefix of the table `ordner`. The target is read
             relative to the German source of the file first (the linkmap,
             read backwards, names it), then relative to the file itself.
  anchor     the fragment of a link into a Markdown file is a heading slug of
             the German file; it becomes the slug of the English heading with
             the same index in the English file (both counted outside fenced
             code, in the order of the file). A fragment that already is an
             anchor of the English file stays.
  link text  a link text that equals the German target, or its last path part,
             with or without backticks, is set to the English one.
  TOML       in docs/plan/tasks/*.toml and docs/design/components/*.toml the
             strings of the keys `design` and `defined_in` are rewritten the
             same way, read relative to docs/feinentwurf and written relative
             to docs/design.

Without PATH every Markdown and TOML file under docs/ of the root is processed.
Fenced code blocks and inline code stay as they are. --german is a tree with the
German sources at their ops repo paths; --peer names further checkouts whose
English files count as link targets (the design, architecture and plan
translations live on separate branches until they are merged). A target file
that exists in none of them keeps its fragment unchecked and is listed as a note.

The linkmap keys are German paths, so this script reads them but never writes
German text itself. Standard library only (FE-004).

Exit codes:
  0  done (or, with --check, nothing left to rewrite)
  1  findings (`<path>:<line>:<column> <rule> <target>`), or with --check at
     least one rewrite still pending (`relink.pending`)
  2  usage or configuration error on stderr: relink.config_invalid
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
import tomllib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parents[2]
if not __package__:
    # Run as a script: make the tools package importable.
    sys.path.insert(0, str(REPO_ROOT))

from tools.hooks.links import (  # noqa: E402
    ATX_RE,
    HTML_ANCHOR_RE,
    HTML_LINK_RE,
    INLINE_LINK_RE,
    NOT_SETEXT_RE,
    REFERENCE_RE,
    SCHEME_RE,
    SETEXT_RE,
    slug,
)
from tools.hooks.text_rules import prose_lines  # noqa: E402

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2

MARKDOWN_SUFFIXES = (".md", ".markdown")
GERMAN_DESIGN_DIR = "docs/feinentwurf"
ENGLISH_DESIGN_DIR = "docs/design"
TOML_DIRS = ("docs/plan/tasks/", "docs/design/components/")
TOML_KEY_RE = re.compile(r"\s*(design|defined_in)\s*=")
TOML_STRING_RE = re.compile(r'"([^"\\]*)"')


class ConfigError(Exception):
    """The linkmap or a directory cannot be used (exit 2)."""


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    column: int
    rule: str
    target: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}:{self.column} {self.rule} {self.target}"


@dataclass
class Result:
    rewritten: int = 0
    changed_files: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    notes: list[Finding] = field(default_factory=list)


# Linkmap ----------------------------------------------------------------------


@dataclass(frozen=True)
class LinkMap:
    files: dict[str, str]
    folders: dict[str, str]

    @classmethod
    def load(cls, path: Path) -> LinkMap:
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise ConfigError(f"path={path} reason={type(exc).__name__}") from None
        files, folders = data.get("dateien", {}), data.get("ordner", {})
        if not isinstance(files, dict) or not isinstance(folders, dict) or not files:
            raise ConfigError(f"path={path} reason=tables dateien and ordner expected")
        return cls(
            {str(k): str(v) for k, v in files.items()}, {str(k): str(v) for k, v in folders.items()}
        )

    def english(self, german: str) -> str | None:
        """The English path of a German file or folder path, or None."""
        german = german.rstrip("/")
        if german in self.files:
            return self.files[german]
        best = ""
        for prefix in self.folders:
            if (german == prefix or german.startswith(prefix + "/")) and len(prefix) > len(best):
                best = prefix
        if not best:
            return None
        return self.folders[best] + german[len(best) :]

    def german(self, english: str) -> str | None:
        """The German source path of an English file, or None (new files such as ADRs)."""
        for german, target in self.files.items():
            if target == english:
                return german
        best = ""
        for target in self.folders.values():
            if english.startswith(target + "/") and len(target) > len(best):
                best = target
        if not best:
            return None
        candidates = [g for g, t in self.folders.items() if t == best]
        return min(candidates) + english[len(best) :]


# Anchors ----------------------------------------------------------------------


def heading_anchors(text: str) -> list[str]:
    """The heading anchors of a Markdown text in order, as tools/hooks/links.py
    computes them (with `-1`, `-2` for repeated headings)."""
    lines = text.split("\n")
    found: list[str] = []
    counts: dict[str, int] = {}

    def add(title: str) -> None:
        base = slug(title)
        count = counts.get(base, 0)
        counts[base] = count + 1
        found.append(base if count == 0 else f"{base}-{count}")

    previous: str | None = None
    for raw, prose in zip(lines, prose_lines(lines), strict=True):
        line = raw.removesuffix("\r")
        if prose is None:
            previous = None
            continue
        atx = ATX_RE.match(line)
        if atx:
            add(atx.group(2) or "")
            previous = None
            continue
        if previous and SETEXT_RE.match(line):
            add(previous)
            previous = None
            continue
        stripped = line.strip()
        previous = None if not stripped or NOT_SETEXT_RE.match(stripped) else stripped
    return found


class Trees:
    """The German sources and the English checkouts, with cached anchors."""

    def __init__(self, german: Path, english: Sequence[Path]) -> None:
        self.german_root = german
        self.english_roots = tuple(english)
        self._cache: dict[tuple[str, str], tuple[list[str], set[str]] | None] = {}

    def _read(self, kind: str, path: str) -> tuple[list[str], set[str]] | None:
        key = (kind, path)
        if key not in self._cache:
            roots = (self.german_root,) if kind == "de" else self.english_roots
            self._cache[key] = None
            for root in roots:
                file = root / path
                if file.is_file():
                    text = file.read_text(encoding="utf-8")
                    self._cache[key] = (heading_anchors(text), set(HTML_ANCHOR_RE.findall(text)))
                    break
        return self._cache[key]

    def german_anchors(self, path: str) -> tuple[list[str], set[str]] | None:
        return self._read("de", path)

    def english_anchors(self, path: str) -> tuple[list[str], set[str]] | None:
        return self._read("en", path)

    def english_exists(self, path: str) -> bool:
        return any((root / path).exists() for root in self.english_roots) if path else True

    def german_exists(self, path: str | None) -> bool:
        return path is not None and (self.german_root / path).exists()


# Rewriting --------------------------------------------------------------------


@dataclass(frozen=True)
class Rewrite:
    target: str
    german_location: str | None
    english_location: str | None


class Relinker:
    def __init__(self, linkmap: LinkMap, trees: Trees) -> None:
        self.linkmap = linkmap
        self.trees = trees

    def resolve(
        self, location: str, german_base: str | None, english_base: str
    ) -> tuple[str | None, str | None]:
        """(German path, English path) of a link location, either may be None."""
        trailing = location.endswith("/")
        candidates = []
        if german_base is not None:
            candidates.append(posixpath.normpath(posixpath.join(german_base, location)))
        candidates.append(posixpath.normpath(posixpath.join(english_base, location)))
        for german in candidates:
            english = self.linkmap.english(german)
            if english is not None:
                return german, english + ("/" if trailing and not english.endswith("/") else "")
        english = candidates[-1]
        return self.linkmap.german(english), english + ("/" if trailing else "")

    def fragment(
        self, fragment: str, german: str | None, english: str
    ) -> tuple[str, str | None, bool]:
        """(new fragment, rule of a finding or None, checked)."""
        decoded = unquote(fragment)
        if not english.endswith(MARKDOWN_SUFFIXES):
            return fragment, None, True
        en = self.trees.english_anchors(english)
        if en is None:
            return fragment, None, False
        en_headings, en_ids = en
        de = self.trees.german_anchors(german) if german else None
        if de is not None and decoded in de[0]:
            if len(de[0]) != len(en_headings):
                return fragment, "relink.heading-count-mismatch", True
            return en_headings[de[0].index(decoded)], None, True
        if decoded in en_headings or decoded in en_ids:
            return fragment, None, True
        return fragment, "relink.unknown-anchor", True

    def target(
        self, target: str, german_base: str | None, english_base: str, own: tuple[str | None, str]
    ) -> tuple[str, str | None, bool, Rewrite]:
        """(new target, rule of a finding or None, checked, rewrite of the location)."""
        if SCHEME_RE.match(target) or target.startswith(("/", "//")):
            return target, None, True, Rewrite(target, None, None)
        location, hash_, fragment = target.partition("#")
        if not location:
            german, english = own
            new_location = ""
        else:
            german, english_path = self.resolve(unquote(location), german_base, english_base)
            if english_path is None:
                return target, "relink.unresolved", True, Rewrite(target, None, None)
            english = english_path.rstrip("/")
            if not self.trees.english_exists(english) and not self.trees.german_exists(german):
                return target, "relink.missing-target", True, Rewrite(target, None, None)
            new_location = (
                posixpath.relpath(english, english_base) if english != english_base else "."
            )
            if english_path.endswith("/") and not new_location.endswith("/"):
                new_location += "/"
            if new_location == unquote(location):
                new_location = location
        rule, checked, new_fragment = None, True, fragment
        if hash_ and fragment:
            new_fragment, rule, checked = self.fragment(fragment, german, english)
        new = new_location + (hash_ + new_fragment if hash_ else "")
        return new, rule, checked, Rewrite(target, location or None, new_location or None)


def _link_text_span(line: str, start: int, target_start: int) -> tuple[int, int] | None:
    """Start and end of the text of an inline link that starts at `start`."""
    open_at = line.find("[", start)
    close_at = line.rfind("](", start, target_start)
    if open_at < 0 or close_at < open_at:
        return None
    return open_at + 1, close_at


def _new_link_text(text: str, rewrite: Rewrite) -> str | None:
    if rewrite.german_location is None or rewrite.english_location is None:
        return None
    ticks = "`" if text.startswith("`") and text.endswith("`") and len(text) > 1 else ""
    bare = text[1:-1] if ticks else text
    old, new = rewrite.german_location, rewrite.english_location
    for german, english in (
        (old, new),
        (posixpath.basename(old.rstrip("/")), posixpath.basename(new.rstrip("/"))),
    ):
        if german and bare in (german, german.rstrip("/")) and bare != english.rstrip("/"):
            keep_slash = bare.endswith("/")
            return ticks + english.rstrip("/") + ("/" if keep_slash else "") + ticks
    return None


def relink_markdown(relinker: Relinker, path: str, text: str, result: Result) -> str:
    german_file = relinker.linkmap.german(path)
    german_base = posixpath.dirname(german_file) if german_file else None
    english_base = posixpath.dirname(path)
    own = (german_file, path)
    lines = text.split("\n")
    for number, prose in enumerate(prose_lines(lines), start=1):
        if prose is None:
            continue
        line = lines[number - 1]
        edits: list[tuple[int, int, str]] = []
        spans: list[tuple[re.Match[str], bool]] = []
        for regex in (INLINE_LINK_RE, REFERENCE_RE, HTML_LINK_RE):
            matches = [regex.match(prose)] if regex is REFERENCE_RE else regex.finditer(prose)
            spans.extend((m, regex is INLINE_LINK_RE) for m in matches if m is not None)
        for match, inline in spans:
            start, end = match.span(1)
            raw = line[start:end]
            bracketed = raw.startswith("<") and raw.endswith(">")
            target = raw[1:-1] if bracketed else raw
            new, rule, checked, rewrite = relinker.target(target, german_base, english_base, own)
            finding = Finding(path, number, match.start() + 1, rule or "", target)
            if rule is not None:
                result.findings.append(finding)
            elif not checked:
                result.notes.append(
                    Finding(path, number, match.start() + 1, "relink.anchor-unchecked", target)
                )
            if new != target:
                edits.append((start, end, f"<{new}>" if bracketed else new))
            if inline:
                text_span = _link_text_span(line, match.start(), start)
                if text_span is not None:
                    new_text = _new_link_text(line[text_span[0] : text_span[1]], rewrite)
                    if new_text is not None:
                        edits.append((text_span[0], text_span[1], new_text))
        if edits:
            for start, end, new in sorted(edits, reverse=True):
                line = line[:start] + new + line[end:]
            result.rewritten += len(edits)
            lines[number - 1] = line
    return "\n".join(lines)


def relink_toml(relinker: Relinker, path: str, text: str, result: Result) -> str:
    lines = text.split("\n")
    inside = False
    for number, line in enumerate(lines, start=1):
        key = TOML_KEY_RE.match(line)
        if key is None and not inside:
            continue
        if key is not None:
            inside = key.group(1) == "design" and "[" in line and "]" not in line
        elif "]" in line:
            inside = False
        edits: list[tuple[int, int, str]] = []
        for match in TOML_STRING_RE.finditer(line, key.end() if key else 0):
            value = match.group(1)
            new, rule, checked, _ = relinker.target(
                value, GERMAN_DESIGN_DIR, ENGLISH_DESIGN_DIR, (None, ENGLISH_DESIGN_DIR)
            )
            if rule is not None:
                result.findings.append(Finding(path, number, match.start() + 1, rule, value))
            elif not checked:
                result.notes.append(
                    Finding(path, number, match.start() + 1, "relink.anchor-unchecked", value)
                )
            if new != value:
                edits.append((match.start(1), match.end(1), new))
        if edits:
            for start, end, new in sorted(edits, reverse=True):
                line = line[:start] + new + line[end:]
            lines[number - 1] = line
            result.rewritten += len(edits)
    return "\n".join(lines)


def default_paths(root: Path) -> list[str]:
    docs = root / "docs"
    if not docs.is_dir():
        return []
    return sorted(
        p.relative_to(root).as_posix()
        for p in docs.rglob("*")
        if p.is_file() and p.suffix in (".md", ".markdown", ".toml")
    )


def run(
    root: Path,
    linkmap: LinkMap,
    german: Path,
    peers: Iterable[Path],
    paths: Sequence[str],
    *,
    write: bool,
) -> Result:
    relinker = Relinker(linkmap, Trees(german, (root, *peers)))
    result = Result()
    for path in paths:
        file = root / path
        text = file.read_text(encoding="utf-8")
        before = result.rewritten
        if path.endswith(MARKDOWN_SUFFIXES):
            new = relink_markdown(relinker, path, text, result)
        elif path.endswith(".toml") and path.startswith(TOML_DIRS):
            new = relink_toml(relinker, path, text, result)
        else:
            continue
        if new != text:
            result.changed_files.append(path)
            if write:
                file.write_text(new, encoding="utf-8")
        elif result.rewritten != before:
            result.rewritten = before
    result.findings.sort()
    result.notes.sort()
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rewrite German link targets to English ones.")
    parser.add_argument("--linkmap", type=Path, required=True, help="the linkmap TOML file")
    parser.add_argument("--german", type=Path, required=True, help="tree of the German sources")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    parser.add_argument(
        "--peer",
        type=Path,
        action="append",
        default=[],
        help="further checkout whose English files count as targets",
    )
    parser.add_argument("--check", action="store_true", help="change nothing; fail if pending")
    parser.add_argument("--json", type=Path, help="also write the result to this file")
    parser.add_argument("paths", nargs="*", help="files relative to the root (default: docs/)")
    args = parser.parse_args(argv)
    try:
        linkmap = LinkMap.load(args.linkmap)
        for directory in (args.german, args.root, *args.peer):
            if not directory.is_dir():
                raise ConfigError(f"path={directory} reason=not a directory")
    except ConfigError as exc:
        print(f"relink.config_invalid {exc}", file=sys.stderr)
        return EXIT_USAGE
    paths = list(args.paths) or default_paths(args.root)
    result = run(args.root, linkmap, args.german, args.peer, paths, write=not args.check)
    for finding in result.findings:
        print(finding)
    for note in result.notes:
        print(note)
    if args.check:
        for path in result.changed_files:
            print(f"{path}:1:1 relink.pending")
    if args.json is not None:
        report = {
            "tool": "relink",
            "rewritten": result.rewritten,
            "changed_files": result.changed_files,
            "findings": [str(f) for f in result.findings],
            "notes": [str(n) for n in result.notes],
        }
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    verb = "pending" if args.check else "rewritten"
    print(
        f"relink: {result.rewritten} links {verb} in {len(result.changed_files)} files, "
        f"{len(result.findings)} findings, {len(result.notes)} unchecked anchors"
    )
    failed = result.findings or (args.check and result.changed_files)
    return EXIT_FINDINGS if failed else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
