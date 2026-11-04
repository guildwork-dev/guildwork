#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Check the text of tracked files: dashes, English, glossary, instance data.

Usage:

  text_rules.py [--root DIR] [--json FILE] [PATH ...]

Without PATH every file that `git ls-files` lists is checked; with PATH (the
pre-commit hook passes the staged files) only those, relative to the root.
Binary files (NUL bytes) and symbolic links are skipped. A text file that is
not UTF-8 (cp1252, UTF-16 with or without byte order mark) is reported as
`text-encoding`, since no rule could read it. Named and numeric character
references (named, decimal and hexadecimal) count as the character they render
as; the column is that of the ampersand.

Rules:

  no-dash        the characters U+2012 to U+2015 (figure dash, en dash, em
                 dash, horizontal bar) anywhere in a file (FE-022)
  english-only   in public documentation (`paths` of
                 quality/text/english-only.toml, minus its `skip` globs, which
                 hold docs/research/ as ADR-53 keeps research untranslated):
                 a German letter (umlaut or sharp s) outside code, and a
                 paragraph with at least `max_per_paragraph` German marker
                 words (`markers`, whole words, any case). Fenced code blocks,
                 inline code spans and link destinations (paths such as the
                 German research file names) are not checked. A line listed in
                 quality/text/english-exceptions.toml (path and SHA-256 of the
                 exact line, with a reason) is left out of both checks.
  glossary       a superseded term of quality/text/glossary.toml (whole word,
                 any case); the message names the term to use instead. The
                 glossary file itself is not checked against its terms.
  text-encoding  a text file that is not UTF-8 (reported once, at 1:1)
  instance-data  a match of the generic rules of the deny-list scanner (home
                 paths, private IPv4 addresses, mail addresses), read through
                 tools/denylist/scan.py from quality/denylist/generic.toml, with
                 the exceptions of quality/denylist/exceptions.toml and the bot
                 addresses of quality/commits/bots.txt. As in the scanner, the
                 message names the rule id, never the matched text.

A path that matches a glob of quality/text/exempt-paths.txt is skipped by every
rule; that list is the only way to exempt a file (`**` spans directories, `*`
and `?` stay within one path part).

Standard library only (FE-004).

Exit codes:
  0  no finding
  1  findings, printed as `<path>:<line>:<column> <rule> <message>` on stdout;
     with --json also written to that file
  2  usage or configuration error on stderr: text_rules.config_invalid,
     text_rules.file_unreadable, text_rules.git_failed; no report is written
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if not __package__:
    # Run as a script (make text-rules): make the tools package importable.
    sys.path.insert(0, str(REPO_ROOT))

from tools.ci.check_layers import glob_to_regex  # noqa: E402
from tools.denylist import scan  # noqa: E402

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2

TEXT_DIR = Path("quality/text")
EXEMPT_PATH = TEXT_DIR / "exempt-paths.txt"
ENGLISH_PATH = TEXT_DIR / "english-only.toml"
EXCEPTIONS_PATH = TEXT_DIR / "english-exceptions.toml"
GLOSSARY_PATH = TEXT_DIR / "glossary.toml"

DASH_RE = re.compile("[\u2012-\u2015]")
GERMAN_LETTER_RE = re.compile("[\u00e4\u00f6\u00fc\u00c4\u00d6\u00dc\u00df\u1e9e]")
FENCE_RE = re.compile(r" {0,3}(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"(`+)(?!`)(.+?)(?<!`)\1(?!`)")
# Link destinations are paths, not prose: inline links `](target)`, reference
# definitions `[label]: target` and href or src attributes. Research files keep
# their German names (ADR-53), so their paths would read as German words.
LINK_DESTINATION_RE = re.compile(
    r"\]\(\s*(<[^>\n]*>|[^\s()]+(?:\([^\s()]*\)[^\s()]*)*)"
    r"|^ {0,3}\[(?!\^)[^\]]+\]:\s*(<[^>\n]*>|\S+)"
    r"|\s(?:href|src)\s*=\s*\"([^\"]*)\""
)
SHA256_RE = re.compile(r"[0-9a-f]{64}")
# Named and numeric character references; Markdown renders them as the character.
ENTITY_RE = re.compile(r"&(?:#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")
UTF16_BOMS = (b"\xff\xfe", b"\xfe\xff")
MARKER_RE = re.compile(r"[^\W\d_]+")


class ConfigError(Exception):
    """A configuration file of the text rules cannot be used (exit 2)."""


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
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}:{self.column} {self.rule} {self.message}"


@dataclass(frozen=True)
class EnglishConfig:
    markers: frozenset[str]
    max_per_paragraph: int
    paths: tuple[re.Pattern[str], ...]
    skip: tuple[re.Pattern[str], ...]
    marker_re: re.Pattern[str]


@dataclass(frozen=True)
class GlossaryTerm:
    term: str
    use: str
    pattern: re.Pattern[str]


@dataclass(frozen=True)
class Config:
    exempt: tuple[re.Pattern[str], ...]
    english: EnglishConfig
    english_exceptions: frozenset[tuple[str, str]]
    glossary: tuple[GlossaryTerm, ...]
    generic: tuple[scan.Rule, ...]
    generic_exceptions: frozenset[tuple[str, str, str]]


# Configuration ----------------------------------------------------------------


def _read(root: Path, path: Path) -> str:
    try:
        return (root / path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"path={path} reason={type(exc).__name__}") from None


def _toml(root: Path, path: Path) -> dict[str, object]:
    try:
        return tomllib.loads(_read(root, path))
    except tomllib.TOMLDecodeError:
        raise ConfigError(f"path={path} reason=TOMLDecodeError") from None


def _globs(value: object, path: Path, key: str) -> tuple[re.Pattern[str], ...]:
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise ConfigError(f"path={path} reason={key} must be a list of non-empty strings")
    return tuple(glob_to_regex(v.strip()) for v in value)


def _table_entries(
    data: dict[str, object], key: str, fields: set[str], path: Path
) -> list[dict[str, str]]:
    unknown = sorted(set(data) - {key})
    if unknown:
        raise ConfigError(f"path={path} reason=unknown keys {unknown}")
    raw = data.get(key, [])
    if not isinstance(raw, list):
        raise ConfigError(f"path={path} reason={key} must be an array of tables")
    entries: list[dict[str, str]] = []
    for index, entry in enumerate(raw):
        where = f"{key}[{index}]"
        if not isinstance(entry, dict) or set(entry) != fields:
            raise ConfigError(f"path={path} reason={where} needs exactly {sorted(fields)}")
        if not all(isinstance(v, str) and v.strip() for v in entry.values()):
            raise ConfigError(f"path={path} reason={where} values must be non-empty strings")
        entries.append(entry)
    return entries


def load_exempt(root: Path) -> tuple[re.Pattern[str], ...]:
    lines = _read(root, EXEMPT_PATH).splitlines()
    patterns = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
    return _globs(patterns, EXEMPT_PATH, "every line")


def load_english(root: Path) -> EnglishConfig:
    path = ENGLISH_PATH
    data = _toml(root, path)
    expected = {"markers", "max_per_paragraph", "paths", "skip"}
    if set(data) != expected:
        raise ConfigError(f"path={path} reason=needs exactly {sorted(expected)}")
    markers = data["markers"]
    if (
        not isinstance(markers, list)
        or not markers
        or not all(
            isinstance(m, str) and m == m.lower() and MARKER_RE.fullmatch(m) for m in markers
        )
    ):
        raise ConfigError(f"path={path} reason=markers must be lower case words")
    limit = data["max_per_paragraph"]
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ConfigError(f"path={path} reason=max_per_paragraph must be a positive integer")
    words = sorted(set(markers), key=len, reverse=True)
    return EnglishConfig(
        markers=frozenset(markers),
        max_per_paragraph=limit,
        paths=_globs(data["paths"], path, "paths"),
        skip=_globs(data["skip"], path, "skip"),
        marker_re=re.compile(
            r"(?<!\w)(?:" + "|".join(re.escape(w) for w in words) + r")(?!\w)", re.IGNORECASE
        ),
    )


def load_english_exceptions(root: Path) -> frozenset[tuple[str, str]]:
    path = EXCEPTIONS_PATH
    entries = _table_entries(
        _toml(root, path), "exception", {"path", "line_sha256", "reason"}, path
    )
    for index, entry in enumerate(entries):
        if not SHA256_RE.fullmatch(entry["line_sha256"]):
            raise ConfigError(
                f"path={path} reason=exception[{index}] line_sha256 must be 64 lower case hex"
            )
    return frozenset((entry["path"], entry["line_sha256"]) for entry in entries)


def load_glossary(root: Path) -> tuple[GlossaryTerm, ...]:
    path = GLOSSARY_PATH
    entries = _table_entries(_toml(root, path), "term", {"term", "use", "reason"}, path)
    return tuple(
        GlossaryTerm(
            term=entry["term"],
            use=entry["use"],
            pattern=re.compile(rf"(?<!\w){re.escape(entry['term'])}(?!\w)", re.IGNORECASE),
        )
        for entry in entries
    )


def load_config(root: Path) -> Config:
    """Read and validate every input file; raise ConfigError with the reason."""
    try:
        generic = scan.load_generic(root, scan.load_bots(root)).rules
        generic_exceptions = scan.load_exceptions(root)
    except scan.UsageError as exc:
        raise ConfigError(exc.detail) from None
    return Config(
        exempt=load_exempt(root),
        english=load_english(root),
        english_exceptions=load_english_exceptions(root),
        glossary=load_glossary(root),
        generic=generic,
        generic_exceptions=generic_exceptions,
    )


def _matches_any(patterns: Iterable[re.Pattern[str]], path: str) -> bool:
    return any(pattern.match(path) for pattern in patterns)


def is_exempt(config: Config, path: str) -> bool:
    return _matches_any(config.exempt, path)


# Rules ------------------------------------------------------------------------


def decode_entities(line: str) -> tuple[str, list[int]]:
    """The line with character references resolved, and for each character of
    the result its 1-based column in the original line."""
    out: list[str] = []
    columns: list[int] = []
    last = 0
    for match in ENTITY_RE.finditer(line):
        value = html.unescape(match.group())
        if value == match.group():
            continue
        for index in range(last, match.start()):
            out.append(line[index])
            columns.append(index + 1)
        out.append(value)
        columns.extend([match.start() + 1] * len(value))
        last = match.end()
    for index in range(last, len(line)):
        out.append(line[index])
        columns.append(index + 1)
    return "".join(out), columns


def check_dashes(path: str, lines: Sequence[str]) -> list[Finding]:
    decoded = [decode_entities(line) for line in lines]
    return [
        Finding(
            path,
            number,
            columns[match.start()],
            "no-dash",
            f"U+{ord(match.group()):04X}: "
            "use a hyphen, comma, colon, parentheses or a new sentence",
        )
        for number, (line, columns) in enumerate(decoded, start=1)
        for match in DASH_RE.finditer(line)
    ]


def prose_lines(lines: Sequence[str]) -> list[str | None]:
    """Each line with inline code blanked; None for lines of fenced code blocks."""
    result: list[str | None] = []
    fence = ""
    for line in lines:
        opener = FENCE_RE.match(line)
        if fence:
            result.append(None)
            if (
                opener
                and opener.group(1)[0] == fence[0]
                and len(opener.group(1)) >= len(fence)
                and not line[opener.end() :].strip()
            ):
                fence = ""
            continue
        if opener:
            fence = opener.group(1)
            result.append(None)
            continue
        result.append(INLINE_CODE_RE.sub(lambda m: " " * len(m.group()), line))
    return result


def blank_link_destinations(line: str) -> str:
    """The line with every link destination replaced by spaces (columns kept)."""
    for match in LINK_DESTINATION_RE.finditer(line):
        group = next(g for g in (1, 2, 3) if match.group(g) is not None)
        start, end = match.span(group)
        line = line[:start] + " " * (end - start) + line[end:]
    return line


def check_english(config: Config, path: str, lines: Sequence[str]) -> list[Finding]:
    english = config.english
    if not _matches_any(english.paths, path) or _matches_any(english.skip, path):
        return []
    findings: list[Finding] = []
    paragraph: list[tuple[int, int]] = []  # (line, column) of each marker word

    def close() -> None:
        if len(paragraph) >= english.max_per_paragraph:
            line, column = paragraph[0]
            findings.append(
                Finding(
                    path,
                    line,
                    column,
                    "english-only",
                    f"{len(paragraph)} German marker words in one paragraph "
                    f"(limit {english.max_per_paragraph}); write English",
                )
            )
        paragraph.clear()

    for number, (raw, prose) in enumerate(zip(lines, prose_lines(lines), strict=True), start=1):
        if prose is None or not prose.strip():
            close()
            continue
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        if (path, digest) in config.english_exceptions:
            continue
        text, columns = decode_entities(blank_link_destinations(prose))
        for match in GERMAN_LETTER_RE.finditer(text):
            findings.append(
                Finding(
                    path,
                    number,
                    columns[match.start()],
                    "english-only",
                    f"German letter U+{ord(match.group()):04X} outside code; write English",
                )
            )
        paragraph.extend((number, columns[m.start()]) for m in english.marker_re.finditer(text))
    close()
    return findings


def check_glossary(config: Config, path: str, lines: Sequence[str]) -> list[Finding]:
    if path == GLOSSARY_PATH.as_posix():
        return []
    return [
        Finding(
            path,
            number,
            match.start() + 1,
            "glossary",
            f'superseded term "{term.term}": use "{term.use}"',
        )
        for number, line in enumerate(lines, start=1)
        for term in config.glossary
        for match in term.pattern.finditer(line)
    ]


def check_instance_data(config: Config, path: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for match in scan.find_matches(text, config.generic):
        digest = hashlib.sha256(match.line_text.encode("utf-8")).hexdigest()
        if (match.rule, path, digest) in config.generic_exceptions:
            continue
        findings.append(
            Finding(
                path,
                match.line,
                match.column,
                "instance-data",
                f"{match.rule}: use a placeholder (example.org, 192.0.2.0/24)",
            )
        )
    return findings


def check_text(config: Config, path: str, text: str) -> list[Finding]:
    """Every finding of every rule in one file; nothing for exempt paths."""
    if is_exempt(config, path):
        return []
    lines = [line.removesuffix("\r") for line in text.split("\n")]
    return sorted(
        [
            *check_dashes(path, lines),
            *check_english(config, path, lines),
            *check_glossary(config, path, lines),
            *check_instance_data(config, path, text),
        ]
    )


# Files ------------------------------------------------------------------------


def tracked_files(root: Path) -> list[str]:
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), "ls-files", "-z"],  # noqa: S607
            check=False,
            capture_output=True,
        )
    except OSError:
        raise UsageError("text_rules.git_failed", "reason=os_error") from None
    if result.returncode != 0:
        raise UsageError("text_rules.git_failed", "command=ls-files")
    return [name for name in result.stdout.decode("utf-8").split("\0") if name]


class BadEncoding:
    """A text file that is not UTF-8 (cp1252, UTF-16): no rule could read it."""


BAD_ENCODING = BadEncoding()


def _looks_like_utf16(data: bytes) -> bool:
    """A byte order mark, or NUL bytes on one parity only, as ASCII text in UTF-16 has."""
    if data.startswith(UTF16_BOMS):
        return True
    even = data[0::2].count(0)
    odd = data[1::2].count(0)
    return len(data) % 2 == 0 and (even == 0) != (odd == 0) and even + odd >= len(data) // 4


def read_text(root: Path, path: str, *, required: bool) -> str | BadEncoding | None:
    """The text of a file; BAD_ENCODING for text that is not UTF-8; None for
    binary files, symbolic links and gone files."""
    full = root / path
    try:
        if full.is_symlink() or not full.is_file():
            if required and not full.is_symlink():
                raise UsageError("text_rules.file_unreadable", f"path={path} reason=not_a_file")
            return None
        data = full.read_bytes()
    except OSError:
        if required:
            raise UsageError("text_rules.file_unreadable", f"path={path} reason=os_error") from None
        return None
    if data.startswith(UTF16_BOMS) or (b"\0" in data and _looks_like_utf16(data)):
        return BAD_ENCODING
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return BAD_ENCODING


def check_paths(
    root: Path, paths: Iterable[str], config: Config, *, required: bool = True
) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        text = read_text(root, path, required=required)
        if isinstance(text, BadEncoding):
            if not is_exempt(config, path):
                findings.append(
                    Finding(path, 1, 1, "text-encoding", "not UTF-8; save the file as UTF-8")
                )
        elif text is not None:
            findings.extend(check_text(config, path, text))
    return sorted(findings)


def _relative(root: Path, argument: str) -> str:
    candidate = Path(argument)
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(root.resolve())
        except ValueError:
            raise UsageError(
                "text_rules.file_unreadable", f"path={argument} reason=outside_root"
            ) from None
    return candidate.as_posix()


def write_report(path: Path, findings: Sequence[Finding]) -> None:
    report = {
        "tool": "text-rules",
        "findings": [
            {
                "path": f.path,
                "line": f.line,
                "column": f.column,
                "rule": f.rule,
                "message": f.message,
            }
            for f in findings
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    parser.add_argument("--json", type=Path, help="also write the findings to this file")
    parser.add_argument("paths", nargs="*", help="files to check (default: all tracked files)")
    args = parser.parse_args(argv)
    root: Path = args.root
    try:
        config = load_config(root)
        if args.paths:
            paths = [_relative(root, p) for p in args.paths]
            findings = check_paths(root, paths, config)
        else:
            paths = tracked_files(root)
            findings = check_paths(root, paths, config, required=False)
    except ConfigError as exc:
        print(f"text_rules.config_invalid {exc}", file=sys.stderr)
        return EXIT_USAGE
    except UsageError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE
    for finding in findings:
        print(finding)
    if args.json is not None:
        write_report(args.json, findings)
    print(f"text-rules: {len(findings)} findings in {len(paths)} files")
    return EXIT_FINDINGS if findings else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
