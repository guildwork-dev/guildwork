#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Require a red team report with the verdict JA before a push (FE-040, FE-041).

Usage:

  review_gate.py [--root DIR] [--json FILE]

Run by the pre-push hook. The report of the checked-out commit is
`.review/<HEAD sha>.md` below the repository root (git-ignored, written by the
reviewer, see docs/quality/red-team-gate.md). Its last line that is not empty
or blank must be exactly `Urteil: JA` (FE-041: the line stays German in the
English repository, since the reviewer writes exactly this line). Only the
line ending (LF or CRLF) is ignored; any other difference fails, including
spaces, case and a translated verdict.

Environment:

  REVIEW_SKIP=1      skip the gate (fork contributors without a reviewer; a
                     maintainer reviews the pull request). Only the exact value
                     `1` skips.
  PRE_COMMIT_TO_REF  set by pre-commit to the commit being pushed when it knows
                     it. If that commit is not HEAD, the gate fails: the report
                     and `make check` both refer to the checked-out commit.

Rules:

  review-missing   no report for the commit
  review-verdict   the last non-empty line is not exactly `Urteil: JA`
  review-not-head  the pushed commit is not the checked-out commit

Standard library only (FE-004).

Exit codes:
  0  report present with verdict JA, or REVIEW_SKIP=1
  1  findings, printed as `<path>:<line>:<column> <rule> <message>` on stdout;
     with --json also written to that file
  2  usage error on stderr: review_gate.git_failed,
     review_gate.report_unreadable
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_DIR = ".review"
VERDICT = "Urteil: JA"
SKIP_VAR = "REVIEW_SKIP"
PUSHED_VAR = "PRE_COMMIT_TO_REF"


class UsageError(Exception):
    """git or the report cannot be used (exit 2)."""

    def __init__(self, event: str, detail: str) -> None:
        super().__init__(f"{event} {detail}")
        self.event = event
        self.detail = detail


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    column: int
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}:{self.column} {self.rule} {self.message}"


def rev_parse(root: Path, rev: str) -> str:
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(root), "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise UsageError("review_gate.git_failed", f"reason={exc}") from exc
    if result.returncode != 0:
        raise UsageError("review_gate.git_failed", f"rev={rev} exit={result.returncode}")
    return result.stdout.strip()


def check_verdict(text: str, path: str) -> list[Finding]:
    """Return a finding unless the last non-empty line is exactly VERDICT."""
    lines = text.splitlines()
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].strip():
            if lines[index] == VERDICT:
                return []
            return [
                Finding(
                    path,
                    index + 1,
                    1,
                    "review-verdict",
                    f"last non-empty line must be exactly '{VERDICT}'",
                )
            ]
    return [Finding(path, 1, 1, "review-verdict", f"report is empty; expected '{VERDICT}'")]


def check(root: Path, environ: dict[str, str]) -> list[Finding]:
    head = rev_parse(root, "HEAD")
    findings: list[Finding] = []
    pushed = environ.get(PUSHED_VAR, "")
    if pushed and rev_parse(root, pushed) != head:
        findings.append(
            Finding(
                ".",
                1,
                1,
                "review-not-head",
                f"pushed commit {pushed[:12]} is not HEAD {head[:12]}; check it out and push again",
            )
        )
    relative = f"{REVIEW_DIR}/{head}.md"
    report = root / relative
    if not report.is_file():
        findings.append(
            Finding(
                relative,
                1,
                1,
                "review-missing",
                "no red team report for HEAD (docs/quality/red-team-gate.md)",
            )
        )
        return findings
    try:
        text = report.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise UsageError("review_gate.report_unreadable", f"path={relative} reason={exc}") from exc
    findings.extend(check_verdict(text, relative))
    return findings


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    parser.add_argument("--json", type=Path, help="also write the findings to this file")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if os.environ.get(SKIP_VAR) == "1":
        print(f"review_gate.skipped reason={SKIP_VAR}=1", file=sys.stderr)
        return EXIT_OK
    try:
        findings = check(args.root, dict(os.environ))
    except UsageError as exc:
        print(f"{exc.event} {exc.detail}", file=sys.stderr)
        return EXIT_USAGE
    for finding in findings:
        print(finding)
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        payload = {"findings": [asdict(finding) for finding in findings]}
        args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return EXIT_FINDINGS if findings else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
