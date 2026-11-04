#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Scan the repository for private terms and instance data (FE-023).

Usage:

  scan.py [--allow-missing] [--json FILE] [--range RANGE] [--all] MODE [MODE ...]

Modes (several in one call give one report and one exit code):

  tree      tracked files of the working tree: content and path
  commits   the commits of --range (a `git rev-list` range such as main..HEAD):
            messages, author and committer identities, every file and directory
            name a commit adds or changes (renames included), the content of
            every file the range adds, and the names of all refs
  history   the same for every commit and object reachable from any ref; needs
            --all
  pr        pull request title and body, read only from the environment
            variables PR_TITLE and PR_BODY, never from arguments

Inputs:

  DENYLIST_FILE       path of the private deny list (environment). One entry per
                      line; `#` starts a comment line. An entry is a literal
                      matched without regard to case, `re:<python regex>` or
                      `word:<term>` (whole word, without regard to case).
  ALLOW_AUTHORS_FILE  path of the allowed identities (environment), one
                      `Name <mail>` per line. Author and committer of every
                      scanned commit must equal one line exactly.
  quality/denylist/generic.toml     generic rules: home paths, private IPv4
                                    addresses, mail addresses. They always apply.
  quality/denylist/exceptions.toml  exceptions per finding id, path and SHA-256
                                    of the exact line, each with a reason.
  quality/commits/bots.txt          bot addresses the mail rule allows.

--allow-missing lets DENYLIST_FILE and ALLOW_AUTHORS_FILE be unset: then the
generic rules run alone and identities are not checked (pull requests from
forks). A set variable that names no file is an error all the same.
ALLOW_AUTHORS_FILE is needed only by the modes commits and history.

Output never contains a term or the text it matched, since CI logs of a public
repository are public. A finding is

  <location>:<line>:<column> <id> <kind>

with id `term-<sha256(entry)[:12]>` for an entry of the private list (the hash
of the whole entry line as written, prefix included), `generic-<rule>` for a
generic rule and `identity-not-allowed` for an identity that is not in
ALLOW_AUTHORS_FILE. Locations: `<path>` for the tree, `<object>:<path>` for file
content in the commits or history modes and `<commit>:<path>` for a name there
(first 12 characters of the SHA), `<commit>:message`, `<commit>:author`, `<commit>:committer`,
`ref-<sha256(name)[:12]>`, `pr-title`, `pr-body`. A path that itself contains
a match is replaced by `path-<sha256(path)[:12]>`; line 0 marks a match in a
file or ref name. With --json the report holds the same findings and, for file
content, the `line_sha256` an exception needs.

Rulings of this tool:
  - The generic rules do not apply to author and committer identities, which
    ALLOW_AUTHORS_FILE covers, and the mail rule skips the trailer lines
    `Signed-off-by:` and `Co-authored-by:` of commit messages: they carry the
    identity of every contributor by design (DCO).
  - Exceptions apply to file content only (tree, commits, history).
  - An author, committer or `Signed-off-by:`/`Co-authored-by:` trailer whose
    identity equals a line of ALLOW_AUTHORS_FILE is not checked against the
    terms: the one allowed identity may hold listed terms itself. Any other
    identity is checked against the terms and reported as not allowed.

Standard library only (FE-004).

Exit codes:
  0  no finding
  1  findings on stdout
  2  usage or configuration error on stderr, with an event name and no content
     of the private files: denylist.list_missing, denylist.list_unreadable,
     denylist.list_invalid, denylist.authors_missing,
     denylist.authors_unreadable, denylist.authors_invalid,
     denylist.config_invalid, denylist.pr_env_missing, denylist.range_invalid,
     denylist.git_failed, denylist.usage_invalid, denylist.internal_error
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERIC_PATH = Path("quality/denylist/generic.toml")
EXCEPTIONS_PATH = Path("quality/denylist/exceptions.toml")
BOTS_PATH = Path("quality/commits/bots.txt")
LIST_VAR = "DENYLIST_FILE"
AUTHORS_VAR = "ALLOW_AUTHORS_FILE"
TITLE_VAR = "PR_TITLE"
BODY_VAR = "PR_BODY"

MODES = ("tree", "commits", "history", "pr")
HASH_LENGTH = 12
SHA_LENGTH = 12
# Commit message trailers that carry contributor identities (DCO).
IDENTITY_TRAILERS = ("signed-off-by:", "co-authored-by:")

TERM_ID_RE = re.compile(r"term-[0-9a-f]{12}")
GENERIC_ID_RE = re.compile(r"generic-[a-z0-9-]+")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
IDENTITY_RE = re.compile(r"[^<>]*\S <[^<>\s]+@[^<>\s]+>")
ADDRESS_RE = re.compile(r"[^\s@<>]+@[^\s@<>]+")
IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?!\.?\d)")
MAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)*"
    r"\.[A-Za-z]{2,}(?![A-Za-z0-9-])"
)

KIND_TERM = "term"
KIND_MAIL = "mail"


class UsageError(Exception):
    """Input, configuration or git cannot be used (exit 2). Never holds content."""

    def __init__(self, event: str, detail: str = "") -> None:
        super().__init__(event)
        self.event = event
        self.detail = detail

    def __str__(self) -> str:
        return f"{self.event} {self.detail}".rstrip()


def short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:HASH_LENGTH]


def _always(_: str) -> bool:
    return True


@dataclass(frozen=True)
class Rule:
    id: str
    pattern: re.Pattern[str]
    kind: str = KIND_TERM
    accept: Callable[[str], bool] = _always


@dataclass(frozen=True)
class GenericRules:
    rules: tuple[Rule, ...]


@dataclass(frozen=True)
class Match:
    line: int
    column: int
    rule: str
    line_text: str


@dataclass(frozen=True)
class Finding:
    location: str
    line: int
    column: int
    id: str
    kind: str
    line_sha256: str | None = None

    def __str__(self) -> str:
        return f"{self.location}:{self.line}:{self.column} {self.id} {self.kind}"

    def to_json(self) -> dict[str, object]:
        data: dict[str, object] = {
            "location": self.location,
            "line": self.line,
            "column": self.column,
            "id": self.id,
            "kind": self.kind,
        }
        if self.line_sha256 is not None:
            data["line_sha256"] = self.line_sha256
        return data


@dataclass
class Context:
    root: Path
    rules: tuple[Rule, ...]
    exceptions: frozenset[tuple[str, str, str]]
    identities: frozenset[str] | None
    private_list: bool
    findings: list[Finding] = field(default_factory=list)


# Configuration ----------------------------------------------------------------


def _config_error(path: Path, reason: str) -> UsageError:
    return UsageError("denylist.config_invalid", f"path={path} reason={reason}")


def _read_toml(root: Path, path: Path) -> dict[str, object]:
    try:
        return tomllib.loads((root / path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise _config_error(path, type(exc).__name__) from None


def _keys(entry: object, allowed: set[str], path: Path, where: str) -> dict[str, object]:
    if not isinstance(entry, dict):
        raise _config_error(path, f"{where} must be a table")
    unknown = sorted(set(entry) - allowed)
    missing = sorted(allowed - set(entry))
    if unknown or missing:
        raise _config_error(path, f"{where} unknown keys {unknown} missing keys {missing}")
    return entry


def _text(entry: dict[str, object], key: str, path: Path, where: str) -> str:
    value = entry[key]
    if not isinstance(value, str) or not value.strip():
        raise _config_error(path, f"{where} {key} must be a non-empty string")
    return value


def _text_list(entry: dict[str, object], key: str, path: Path, where: str) -> list[str]:
    value = entry[key]
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        raise _config_error(path, f"{where} {key} must be a list of non-empty strings")
    return list(value)


def load_generic(root: Path, allowed_addresses: Iterable[str] = ()) -> GenericRules:
    """The generic rules of quality/denylist/generic.toml.

    The mail rule allows the domains of the file plus allowed_addresses (bot
    addresses and those of ALLOW_AUTHORS_FILE), compared without regard to case.
    """
    path = GENERIC_PATH
    data = _read_toml(root, path)
    if set(data) != {"rule"} or not isinstance(data["rule"], list):
        raise _config_error(path, "expected only [[rule]] tables")
    allowed = frozenset(address.lower() for address in allowed_addresses)
    rules: list[Rule] = []
    for index, raw in enumerate(data["rule"]):
        where = f"rule[{index}]"
        if not isinstance(raw, dict) or "kind" not in raw:
            raise _config_error(path, f"{where} needs a kind")
        kind = raw["kind"]
        if kind == "regex":
            entry = _keys(raw, {"id", "kind", "patterns"}, path, where)
            patterns = _text_list(entry, "patterns", path, where)
            try:
                pattern = re.compile("|".join(f"(?:{p})" for p in patterns))
            except re.error:
                raise _config_error(path, f"{where} invalid regex") from None
            rules.append(Rule(_rule_id(entry, path, where), pattern))
        elif kind == "ipv4":
            entry = _keys(raw, {"id", "kind", "networks", "allowed_networks"}, path, where)
            try:
                networks = [
                    ipaddress.IPv4Network(n) for n in _text_list(entry, "networks", path, where)
                ]
                exempt = [
                    ipaddress.IPv4Network(n)
                    for n in _text_list(entry, "allowed_networks", path, where)
                ]
            except ValueError:
                raise _config_error(path, f"{where} invalid network") from None
            rules.append(
                Rule(_rule_id(entry, path, where), IPV4_RE, accept=_ipv4_check(networks, exempt))
            )
        elif kind == "mail":
            entry = _keys(raw, {"id", "kind", "allowed_domains"}, path, where)
            domains = tuple(d.lower() for d in _text_list(entry, "allowed_domains", path, where))
            rules.append(
                Rule(
                    _rule_id(entry, path, where),
                    MAIL_RE,
                    kind=KIND_MAIL,
                    accept=_mail_check(domains, allowed),
                )
            )
        else:
            raise _config_error(path, f"{where} kind must be regex, ipv4 or mail")
    ids = [rule.id for rule in rules]
    if len(set(ids)) != len(ids):
        raise _config_error(path, "rule ids must be unique")
    return GenericRules(tuple(rules))


def _rule_id(entry: dict[str, object], path: Path, where: str) -> str:
    value = _text(entry, "id", path, where)
    if not GENERIC_ID_RE.fullmatch(value):
        raise _config_error(path, f"{where} id must match {GENERIC_ID_RE.pattern}")
    return value


def _ipv4_check(
    networks: Sequence[ipaddress.IPv4Network], exempt: Sequence[ipaddress.IPv4Network]
) -> Callable[[str], bool]:
    def accept(text: str) -> bool:
        try:
            address = ipaddress.IPv4Address(text)
        except ValueError:
            return False
        if any(address in network for network in exempt):
            return False
        return any(address in network for network in networks)

    return accept


def _mail_check(domains: tuple[str, ...], allowed: frozenset[str]) -> Callable[[str], bool]:
    def accept(text: str) -> bool:
        address = text.lower()
        if address in allowed:
            return False
        domain = address.rpartition("@")[2]
        return not any(domain == d or domain.endswith("." + d) for d in domains)

    return accept


def load_exceptions(root: Path) -> frozenset[tuple[str, str, str]]:
    """(finding id, path, line_sha256) of every [[exception]]."""
    path = EXCEPTIONS_PATH
    data = _read_toml(root, path)
    unknown = sorted(set(data) - {"exception"})
    if unknown:
        raise _config_error(path, f"unknown keys {unknown}")
    raw_entries = data.get("exception", [])
    if not isinstance(raw_entries, list):
        raise _config_error(path, "exception must be an array of tables")
    entries: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(raw_entries):
        where = f"exception[{index}]"
        entry = _keys(raw, {"term", "line_sha256", "path", "reason"}, path, where)
        term = _text(entry, "term", path, where)
        if not (TERM_ID_RE.fullmatch(term) or GENERIC_ID_RE.fullmatch(term)):
            raise _config_error(path, f"{where} term must be term-<12 hex> or generic-<rule>")
        line_sha = _text(entry, "line_sha256", path, where)
        if not SHA256_RE.fullmatch(line_sha):
            raise _config_error(path, f"{where} line_sha256 must be 64 lower case hex digits")
        _text(entry, "reason", path, where)
        entries.add((term, _text(entry, "path", path, where), line_sha))
    return frozenset(entries)


def load_bots(root: Path) -> frozenset[str]:
    try:
        lines = (root / BOTS_PATH).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise _config_error(BOTS_PATH, type(exc).__name__) from None
    bots = {line.strip() for line in lines if line.strip() and not line.startswith("#")}
    if not all(ADDRESS_RE.fullmatch(bot) for bot in bots):
        raise _config_error(BOTS_PATH, "not a single mail address per line")
    return frozenset(bots)


def _private_lines(variable: str, missing: str, unreadable: str) -> list[str] | None:
    """Lines of the file named by an environment variable; None when it is unset.

    A set variable naming no file is an error even with --allow-missing, which
    covers an unset variable only. Error details name the variable only, never
    the path or the content.
    """
    value = os.environ.get(variable, "")
    if not value:
        return None
    try:
        data = Path(value).read_bytes()
    except FileNotFoundError:
        raise UsageError(missing, f"variable={variable} reason=not_found") from None
    except OSError:
        raise UsageError(unreadable, f"variable={variable} reason=os_error") from None
    try:
        return data.decode("utf-8").splitlines()
    except UnicodeDecodeError:
        raise UsageError(unreadable, f"variable={variable} reason=not_utf8") from None


def parse_denylist(lines: Sequence[str]) -> list[Rule]:
    rules: list[Rule] = []
    for number, raw in enumerate(lines, start=1):
        entry = raw.strip()
        if not entry or entry.startswith("#"):
            continue

        def invalid(reason: str, number: int = number) -> UsageError:
            return UsageError(
                "denylist.list_invalid", f"variable={LIST_VAR} line={number} reason={reason}"
            )

        if entry.startswith("re:"):
            body = entry[3:]
            try:
                pattern = re.compile(body)
            except re.error:
                raise invalid("regex") from None
        elif entry.startswith("word:"):
            body = entry[5:]
            pattern = re.compile(rf"(?<!\w){re.escape(body)}(?!\w)", re.IGNORECASE)
        else:
            body = entry
            pattern = re.compile(re.escape(body), re.IGNORECASE)
        if not body.strip():
            raise invalid("empty")
        if pattern.search(""):
            raise invalid("matches_empty_text")
        rules.append(Rule(f"term-{short_hash(entry)}", pattern))
    return rules


def parse_identities(lines: Sequence[str]) -> frozenset[str]:
    identities: set[str] = set()
    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not IDENTITY_RE.fullmatch(line):
            raise UsageError(
                "denylist.authors_invalid", f"variable={AUTHORS_VAR} line={number} reason=format"
            )
        identities.add(line)
    return frozenset(identities)


# Matching ---------------------------------------------------------------------


def find_matches(
    text: str, rules: Sequence[Rule], *, skip_mail: Callable[[str], bool] | None = None
) -> list[Match]:
    """Every match in text, ordered by line, column and rule id."""
    matches: list[Match] = []
    for number, raw in enumerate(text.split("\n"), start=1):
        line = raw.removesuffix("\r")
        for rule in rules:
            if rule.kind == KIND_MAIL and skip_mail is not None and skip_mail(line):
                continue
            for match in rule.pattern.finditer(line):
                if match.group() and rule.accept(match.group()):
                    matches.append(Match(number, match.start() + 1, rule.id, line))
    matches.sort(key=lambda m: (m.line, m.column, m.rule))
    return matches


def _is_identity_trailer(line: str) -> bool:
    return line.lstrip().lower().startswith(IDENTITY_TRAILERS)


def _hidden(prefix: str, name: str) -> str:
    return f"{prefix}-{short_hash(name)}"


def safe_path(ctx: Context, path: str) -> str:
    """The path, or path-<hash> when the path itself contains a match."""
    return _hidden("path", path) if find_matches(path, ctx.rules) else path


def check_name(ctx: Context, location_prefix: str, path: str) -> str:
    """Report matches in a path; return the location to use for the path."""
    location = location_prefix + safe_path(ctx, path)
    for match in find_matches(path, ctx.rules):
        ctx.findings.append(Finding(location, 0, match.column, match.rule, "file-name"))
    return location


def check_content(ctx: Context, location: str, path: str, data: bytes) -> None:
    text = data.decode("utf-8", errors="replace")
    for match in find_matches(text, ctx.rules):
        line_sha = hashlib.sha256(match.line_text.encode("utf-8")).hexdigest()
        if (match.rule, path, line_sha) in ctx.exceptions:
            continue
        ctx.findings.append(
            Finding(location, match.line, match.column, match.rule, "content", line_sha)
        )


def check_text(
    ctx: Context,
    location: str,
    kind: str,
    text: str,
    rules: Sequence[Rule] | None = None,
    skip_mail: Callable[[str], bool] | None = None,
) -> None:
    for match in find_matches(text, ctx.rules if rules is None else rules, skip_mail=skip_mail):
        ctx.findings.append(Finding(location, match.line, match.column, match.rule, kind))


# Git --------------------------------------------------------------------------


def run_git(root: Path, *args: str, stdin: bytes | None = None, event: str = "") -> bytes:
    """Run git; failures name the git subcommand only, never its output."""
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), "-c", "log.showSignature=false", *args],  # noqa: S607
            input=stdin,
            check=False,
            capture_output=True,
        )
    except OSError:
        raise UsageError("denylist.git_failed", f"command={args[0]} reason=os_error") from None
    if result.returncode != 0:
        raise UsageError(event or "denylist.git_failed", f"command={args[0]}")
    return result.stdout


def _decode(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def scan_tree(ctx: Context) -> None:
    for raw in run_git(ctx.root, "ls-files", "-z").split(b"\0"):
        if not raw:
            continue
        path = _decode(raw)
        location = check_name(ctx, "", path)
        full = ctx.root / os.fsdecode(raw)
        try:
            if full.is_symlink():
                data = os.fsencode(os.readlink(full))
            elif full.is_file():
                data = full.read_bytes()
            else:
                continue
        except FileNotFoundError:
            continue
        check_content(ctx, location, path, data)


def _rev_args(revision: str) -> list[str]:
    return ["--all"] if revision == "--all" else [revision, "--"]


OBJECT_ID_RE = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")


def scan_objects(ctx: Context, revision: str) -> None:
    """Content of every blob that the revisions add, with one path that names it."""
    listing = run_git(
        ctx.root, "rev-list", "--objects", *_rev_args(revision), event="denylist.range_invalid"
    )
    paths: dict[str, str] = {}
    for line in _decode(listing).splitlines():
        sha, _, path = line.partition(" ")
        # A path with a line break continues on a line that is no object id.
        if path and OBJECT_ID_RE.fullmatch(sha):
            paths.setdefault(sha, path)
    if not paths:
        return
    request = "".join(f"{sha}\n" for sha in paths).encode("ascii")
    kinds = _decode(
        run_git(ctx.root, "cat-file", "--batch-check=%(objectname) %(objecttype)", stdin=request)
    )
    blobs = [
        sha
        for sha, _, kind in (line.partition(" ") for line in kinds.splitlines())
        if kind == "blob"
    ]
    if not blobs:
        return
    output = run_git(
        ctx.root, "cat-file", "--batch", stdin="".join(f"{s}\n" for s in blobs).encode("ascii")
    )
    offset = 0
    while offset < len(output):
        end = output.index(b"\n", offset)
        sha, _, size = _decode(output[offset:end]).split(" ")
        start = end + 1
        data = output[start : start + int(size)]
        offset = start + int(size) + 1
        path = paths[sha]
        location = f"{sha[:SHA_LENGTH]}:{safe_path(ctx, path)}"
        check_content(ctx, location, path, data)


def scan_names(ctx: Context, revision: str) -> None:
    """Every file and directory name that a commit of the revisions adds or changes.

    Read from the commits (renames as delete and add, merges against each
    parent), since a rename or a file with existing content adds no object.
    Each path is reported once, with the first commit that git log lists.
    """
    output = run_git(
        ctx.root,
        "log",
        "-z",
        "-m",
        "-t",
        "--raw",
        "--root",
        "--no-renames",
        "--no-abbrev",
        "--format=%H",
        *_rev_args(revision),
        event="denylist.range_invalid",
    )
    tokens = _decode(output).split("\0")
    seen: set[str] = set()
    commit = ""
    index = 0
    while index < len(tokens):
        token = tokens[index].lstrip("\n")
        index += 1
        if token.startswith(":"):
            path = tokens[index] if index < len(tokens) else ""
            index += 1
            if token.split(" ")[-1] != "D" and path and path not in seen:
                seen.add(path)
                check_name(ctx, f"{commit[:SHA_LENGTH]}:", path)
        elif token:
            commit = token


# Fields of `git log`: SHA, author name and mail, committer name and mail, body.
LOG_FORMAT = "%H%x1f%an%x1f%ae%x1f%cn%x1f%ce%x1f%B"


def scan_commits(ctx: Context, revision: str) -> None:
    log = run_git(
        ctx.root,
        "log",
        "-z",
        "--no-mailmap",
        f"--format={LOG_FORMAT}",
        *_rev_args(revision),
        event="denylist.range_invalid",
    )
    terms = [rule for rule in ctx.rules if rule.id.startswith("term-")]
    for record in _decode(log).split("\0"):
        if not record:
            continue
        sha, author_name, author_mail, committer_name, committer_mail, body = record.split(
            "\x1f", 5
        )
        prefix = sha[:SHA_LENGTH]
        allowed = ctx.identities or frozenset()
        # Identity trailers of an allowed identity are blanked (line numbers stay).
        lines = [
            "" if _is_identity_trailer(line) and line.split(":", 1)[1].strip() in allowed else line
            for line in body.split("\n")
        ]
        check_text(
            ctx,
            f"{prefix}:message",
            "commit-message",
            "\n".join(lines),
            skip_mail=_is_identity_trailer,
        )
        for role, identity in (
            ("author", f"{author_name} <{author_mail}>"),
            ("committer", f"{committer_name} <{committer_mail}>"),
        ):
            # The allowed identity may hold listed terms itself (name, account).
            if identity in allowed:
                continue
            check_text(ctx, f"{prefix}:{role}", role, identity, rules=terms)
            if ctx.identities is not None:
                ctx.findings.append(Finding(f"{prefix}:{role}", 1, 1, "identity-not-allowed", role))
    scan_names(ctx, revision)
    scan_objects(ctx, revision)
    scan_refs(ctx)


def scan_refs(ctx: Context) -> None:
    refs = _decode(run_git(ctx.root, "for-each-ref", "--format=%(refname)"))
    for ref in refs.splitlines():
        for match in find_matches(ref, ctx.rules):
            ctx.findings.append(
                Finding(_hidden("ref", ref), 0, match.column, match.rule, "ref-name")
            )


def scan_pr(ctx: Context) -> None:
    for variable, location in ((TITLE_VAR, "pr-title"), (BODY_VAR, "pr-body")):
        if variable not in os.environ:
            raise UsageError("denylist.pr_env_missing", f"variable={variable}")
        check_text(ctx, location, location, os.environ[variable])


# Command line -----------------------------------------------------------------


class Parser(argparse.ArgumentParser):
    """argparse that never echoes an argument in its error message."""

    def error(self, message: str) -> NoReturn:
        raise UsageError("denylist.usage_invalid", "reason=arguments (see --help)")


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = Parser(description="Scan for private terms and instance data (FE-023).")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    parser.add_argument("--json", type=Path, help="also write the findings to this file")
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="run the generic rules alone when DENYLIST_FILE or ALLOW_AUTHORS_FILE is absent",
    )
    parser.add_argument("--range", dest="commit_range", help="git range for the mode commits")
    parser.add_argument("--all", action="store_true", help="every ref, for the mode history")
    parser.add_argument("modes", nargs="*", help=f"one or more of {', '.join(MODES)}")
    args = parser.parse_intermixed_args(argv)
    modes: list[str] = args.modes
    if not modes or any(mode not in MODES for mode in modes):
        raise UsageError("denylist.usage_invalid", f"reason=modes must be from {'/'.join(MODES)}")
    if ("commits" in modes) != (args.commit_range is not None):
        raise UsageError("denylist.usage_invalid", "reason=--range goes with the mode commits")
    if ("history" in modes) != args.all:
        raise UsageError("denylist.usage_invalid", "reason=--all goes with the mode history")
    if args.commit_range is not None and (
        not args.commit_range.strip() or args.commit_range.startswith("-")
    ):
        raise UsageError("denylist.range_invalid", "reason=empty or option")
    args.modes = list(dict.fromkeys(modes))
    return args


def build_context(root: Path, modes: Sequence[str], allow_missing: bool) -> Context:
    list_lines = _private_lines(LIST_VAR, "denylist.list_missing", "denylist.list_unreadable")
    if list_lines is None and not allow_missing:
        raise UsageError("denylist.list_missing", f"variable={LIST_VAR}")
    author_lines = _private_lines(
        AUTHORS_VAR, "denylist.authors_missing", "denylist.authors_unreadable"
    )
    needs_identities = "commits" in modes or "history" in modes
    if author_lines is None and needs_identities and not allow_missing:
        raise UsageError("denylist.authors_missing", f"variable={AUTHORS_VAR}")
    identities = None if author_lines is None else parse_identities(author_lines)
    terms = parse_denylist(list_lines or [])
    addresses = set(load_bots(root))
    for identity in identities or ():
        addresses.add(identity.rpartition("<")[2].rstrip(">"))
    generic = load_generic(root, addresses)
    return Context(
        root=root,
        rules=(*terms, *generic.rules),
        exceptions=load_exceptions(root),
        identities=identities if needs_identities else None,
        private_list=list_lines is not None,
    )


def write_report(path: Path, modes: Sequence[str], findings: Sequence[Finding]) -> None:
    report = {
        "tool": "denylist",
        "modes": list(modes),
        "findings": [finding.to_json() for finding in findings],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def run(argv: Sequence[str] | None) -> int:
    args = parse_args(argv)
    root: Path = args.root
    ctx = build_context(root, args.modes, args.allow_missing)
    for mode in args.modes:
        if mode == "tree":
            scan_tree(ctx)
        elif mode == "commits":
            scan_commits(ctx, args.commit_range)
        elif mode == "history":
            scan_commits(ctx, "--all")
        else:
            scan_pr(ctx)
    for finding in ctx.findings:
        print(finding)
    if args.json is not None:
        write_report(args.json, args.modes, ctx.findings)
    private = "private list loaded" if ctx.private_list else "generic rules only"
    print(f"denylist: {len(ctx.findings)} findings ({' '.join(args.modes)}; {private})")
    return EXIT_FINDINGS if ctx.findings else EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(argv)
    except UsageError as exc:
        print(str(exc), file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        # Never print the message or a traceback: either may hold matched text.
        print(f"denylist.internal_error type={type(exc).__name__}", file=sys.stderr)
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
