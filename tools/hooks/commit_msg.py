#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Check commit messages: Conventional Commits, DCO sign-off, Plan-Task (FE-020).

Two modes:

  commit_msg.py <message-file>   hook mode (git commit-msg hook): checks one
                                 message against the author git will record
                                 (`git var GIT_AUTHOR_IDENT`); comment lines
                                 starting with `#` and everything below the
                                 scissors line are ignored, as git drops them
  commit_msg.py --range <range>  every commit that `git rev-list <range>`
                                 lists, merge commits included, each against
                                 its own author

Rules (section 4.1 of the detailed design, FE-021):

  subject-not-conventional  the first line is not `<type>[(<scope>)][!]: <text>`
                            with a type from TYPES and a lower case scope
  subject-too-long          the first line is longer than subject_max_length
                            of quality/commits/limits.toml
  subject-trailing-period   the first line ends with a period
  body-no-blank-line        the second line is not empty
  signoff-missing           no `Signed-off-by:` line (DCO 1.1)
  signoff-author-mismatch   no `Signed-off-by: Name <mail>` line equal to the
                            author name and address of the commit
  plan-task-malformed       a `Plan-Task:` line whose value is not a task ID
  message-dash              a line holds one of the dash characters U+2012 to
                            U+2015 (FE-022, as the no-dash rule of
                            text_rules.py); one finding per line

The sign-off rules do not apply when the author address is exactly one of the
addresses in quality/commits/bots.txt (byte for byte, no case folding); every
other rule does. `Co-Authored-By:` lines are allowed and never count as a
sign-off. Trailer keys are matched without regard to case, as git does.
Whether a Plan-Task ID names an existing task is not checked.

Merge commits are checked like every other commit: in the local build
repository they are written by hand with a Conventional Commits subject and a
sign-off, and the DCO covers every commit that enters the history. A default
message such as "Merge branch 'topic'" fails.

Standard library only (FE-004).

Exit codes:
  0  no finding
  1  findings, printed as `<location>:<line>:1 rule-id message` on stdout; the
     location is the message file in hook mode and the first 12 characters of
     the commit SHA in range mode
  2  usage or configuration error on stderr: commitlint.config_invalid,
     commitlint.range_invalid, commitlint.message_unreadable,
     commitlint.author_unknown, commitlint.git_failed
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2

REPO_ROOT = Path(__file__).resolve().parents[2]
LIMITS_PATH = Path("quality/commits/limits.toml")
BOTS_PATH = Path("quality/commits/bots.txt")

# Commit types of section 4.1 of the detailed design.
TYPES = ("feat", "fix", "docs", "refactor", "test", "build", "ci", "chore", "perf", "revert")
SUBJECT_RE = re.compile(
    r"(?:" + "|".join(TYPES) + r")(?:\([a-z0-9][a-z0-9._/-]*\))?!?: \S.*",
)
# Task ID of the plan tool (FE-021): stage, epic, task.
PLAN_TASK_RE = re.compile(r"(?:R|0b|7a|10|[0-9])-E[0-9]{2}-T[0-9]{2}")
TRAILER_RE = re.compile(r"(?P<key>[A-Za-z][A-Za-z0-9-]*):(?P<value>.*)")
IDENTITY_RE = re.compile(r"(?P<name>[^<>]*?)\s*<(?P<email>[^<>]*)>")
ADDRESS_RE = re.compile(r"[^\s@<>]+@[^\s@<>]+")
SCISSORS = "# ------------------------ >8 ------------------------"
COMMENT_CHAR = "#"
SHA_LENGTH = 12
LIMIT_KEYS = frozenset({"subject_max_length"})
# The dash characters of FE-022: figure dash, en dash, em dash, horizontal bar.
DASH_RE = re.compile("[\u2012-\u2015]")


class UsageError(Exception):
    """The input, the configuration or git cannot be used (exit 2)."""

    def __init__(self, event: str, detail: str) -> None:
        super().__init__(f"{event} {detail}")
        self.event = event
        self.detail = detail


@dataclass(frozen=True)
class Limits:
    subject_max_length: int


@dataclass(frozen=True)
class Finding:
    location: str
    line: int
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.location}:{self.line}:1 {self.rule} {self.message}"


@dataclass(frozen=True)
class Commit:
    sha: str
    author_name: str
    author_email: str
    message: str


def load_limits(root: Path) -> Limits:
    path = root / LIMITS_PATH
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise UsageError("commitlint.config_invalid", f"path={LIMITS_PATH} reason={exc}") from exc
    unknown = sorted(set(data) - LIMIT_KEYS)
    if unknown:
        raise UsageError(
            "commitlint.config_invalid", f"path={LIMITS_PATH} reason=unknown keys {unknown}"
        )
    value = data.get("subject_max_length")
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise UsageError(
            "commitlint.config_invalid",
            f"path={LIMITS_PATH} reason=subject_max_length must be a positive integer",
        )
    return Limits(subject_max_length=value)


def load_bots(root: Path) -> frozenset[str]:
    path = root / BOTS_PATH
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise UsageError("commitlint.config_invalid", f"path={BOTS_PATH} reason={exc}") from exc
    bots: set[str] = set()
    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not ADDRESS_RE.fullmatch(line):
            raise UsageError(
                "commitlint.config_invalid",
                f"path={BOTS_PATH} line={number} reason=not a single mail address",
            )
        bots.add(line)
    return frozenset(bots)


def check_message(
    message: str,
    *,
    author_name: str,
    author_email: str,
    bots: frozenset[str],
    limits: Limits,
    location: str,
) -> list[Finding]:
    """Return the findings of one commit message for the given author."""
    lines = message.splitlines()
    subject = lines[0] if lines else ""
    findings: list[Finding] = []

    def add(line: int, rule: str, text: str) -> None:
        findings.append(Finding(location, line, rule, text))

    if not SUBJECT_RE.fullmatch(subject):
        add(
            1,
            "subject-not-conventional",
            f"subject must be '<type>[(<scope>)]: <text>' with a type from {', '.join(TYPES)}",
        )
    if len(subject) > limits.subject_max_length:
        add(
            1,
            "subject-too-long",
            f"subject has {len(subject)} characters, at most {limits.subject_max_length}",
        )
    if subject.endswith("."):
        add(1, "subject-trailing-period", "subject must not end with a period")
    if len(lines) > 1 and lines[1].strip():
        add(2, "body-no-blank-line", "the line after the subject must be empty")

    for number, line in enumerate(lines, start=1):
        if DASH_RE.search(line):
            add(number, "message-dash", "replace the dash (U+2012 to U+2015) with a hyphen")

    signoffs: list[tuple[int, str]] = []
    for number, line in enumerate(lines[1:], start=2):
        match = TRAILER_RE.fullmatch(line)
        if match is None:
            continue
        key = match["key"].lower()
        value = match["value"].strip()
        if key == "plan-task" and not PLAN_TASK_RE.fullmatch(value):
            add(
                number,
                "plan-task-malformed",
                f"Plan-Task must be a task ID like R-E02-T02, got {value!r}",
            )
        elif key == "signed-off-by":
            signoffs.append((number, value))

    if author_email in bots:
        return findings
    if not signoffs:
        add(
            1,
            "signoff-missing",
            f"add 'Signed-off-by: {author_name} <{author_email}>' (git commit -s)",
        )
    elif not any(_is_author(value, author_name, author_email) for _, value in signoffs):
        add(
            signoffs[0][0],
            "signoff-author-mismatch",
            f"no Signed-off-by equals the author '{author_name} <{author_email}>'",
        )
    return findings


def _is_author(value: str, name: str, email: str) -> bool:
    match = IDENTITY_RE.fullmatch(value)
    return match is not None and match["name"] == name and match["email"] == email


def hook_text(raw: str) -> str:
    """The message as git stores it: no comment lines, nothing below the scissors."""
    kept: list[str] = []
    for line in raw.splitlines():
        if line == SCISSORS:
            break
        if line.startswith(COMMENT_CHAR):
            continue
        kept.append(line.rstrip())
    while kept and not kept[0]:
        kept.pop(0)
    return "\n".join(kept).rstrip("\n") + "\n"


def run_git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), *args],  # noqa: S607
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        raise UsageError("commitlint.git_failed", f"reason={exc}") from exc
    if result.returncode != 0:
        reason = result.stderr.strip().splitlines()[-1:] or ["no output"]
        raise UsageError("commitlint.git_failed", f"args={' '.join(args)} reason={reason[0]}")
    return result.stdout


def author_identity(root: Path) -> tuple[str, str]:
    try:
        ident = run_git(root, "var", "GIT_AUTHOR_IDENT").strip()
    except UsageError as exc:
        raise UsageError("commitlint.author_unknown", exc.detail) from exc
    match = re.fullmatch(r"(?P<name>.*?) <(?P<email>[^<>]*)> \d+ [+-]\d{4}", ident)
    if match is None:
        raise UsageError("commitlint.author_unknown", "reason=unexpected git var output")
    return match["name"], match["email"]


def range_commits(root: Path, commit_range: str) -> list[Commit]:
    if not commit_range.strip() or commit_range.startswith("-"):
        raise UsageError(
            "commitlint.range_invalid", f"range={commit_range!r} reason=empty or option"
        )
    try:
        shas = run_git(root, "rev-list", "--reverse", commit_range, "--").split()
    except UsageError as exc:
        raise UsageError(
            "commitlint.range_invalid", f"range={commit_range!r} {exc.detail}"
        ) from exc
    commits: list[Commit] = []
    for sha in shas:
        name, email, message = run_git(root, "show", "-s", "--format=%an%x00%ae%x00%B", sha).split(
            "\0", 2
        )
        commits.append(Commit(sha, name, email, message))
    return commits


def check_commits(commits: Iterable[Commit], bots: frozenset[str], limits: Limits) -> list[Finding]:
    findings: list[Finding] = []
    for commit in commits:
        findings.extend(
            check_message(
                commit.message,
                author_name=commit.author_name,
                author_email=commit.author_email,
                bots=bots,
                limits=limits,
                location=commit.sha[:SHA_LENGTH],
            )
        )
    return findings


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check commit messages (FE-020).")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("message_file", nargs="?", help="message file (commit-msg hook)")
    mode.add_argument("--range", dest="commit_range", help="git rev-list range, e.g. main..HEAD")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root: Path = args.root
    try:
        limits = load_limits(root)
        bots = load_bots(root)
        if args.commit_range is not None:
            commits = range_commits(root, args.commit_range)
            findings = check_commits(commits, bots, limits)
        else:
            try:
                raw = Path(args.message_file).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise UsageError(
                    "commitlint.message_unreadable", f"path={args.message_file} reason={exc}"
                ) from exc
            name, email = author_identity(root)
            findings = check_message(
                hook_text(raw),
                author_name=name,
                author_email=email,
                bots=bots,
                limits=limits,
                location=args.message_file,
            )
    except UsageError as exc:
        print(f"{exc.event} {exc.detail}", file=sys.stderr)
        return EXIT_USAGE
    for finding in findings:
        print(finding)
    if args.commit_range is not None:
        print(f"commitlint: checked {len(commits)} commits, {len(findings)} findings")
    return EXIT_FINDINGS if findings else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
