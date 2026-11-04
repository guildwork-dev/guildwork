#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Decide the result of the job ci-ok, the only required check (FE-027).

Input is the environment variable NEEDS_JSON, set by the workflow to
`${{ toJSON(needs) }}`: an object that maps each job ci-ok needs to an object
with its `result` (success, failure, cancelled or skipped). The decision
follows the table in section 4.2 of the detailed design:

  green  ts, tools and security succeeded, exactly one of denylist and
         denylist-fork succeeded and the other was skipped, and every other
         job in needs succeeded
  red    any job failed, was cancelled or has an unknown result; ts, tools or
         security skipped or missing; both deny jobs skipped, both succeeded
         or either missing ("denylist mode not decided")

A skipped job never counts as success: GitHub treats a skipped required check
as passed, so ci-ok runs with `if: always()` and decides here.

Standard library only (FE-004).

Output: one line `ci_ok.job job=<name> result=<result>` per job on stdout, then
`ci_ok.passed`, or `ci_ok.failed reason=<reason>` per reason on stderr.

Exit codes:
  0  green
  1  red
  2  NEEDS_JSON missing, not JSON, or not of the form above
     (`ci_ok.needs_invalid reason=<reason>` on stderr)
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping, Sequence

EXIT_OK = 0
EXIT_RED = 1
EXIT_INVALID = 2

ENV_NAME = "NEEDS_JSON"
CORE_JOBS = ("ts", "tools", "security")
DENY_JOBS = ("denylist", "denylist-fork")
SUCCESS = "success"
SKIPPED = "skipped"
MISSING = "missing"


class NeedsError(Exception):
    """NEEDS_JSON cannot be read."""


def parse_needs(text: str | None) -> dict[str, str]:
    """The result of each job in NEEDS_JSON; raise NeedsError."""
    if text is None or not text.strip():
        raise NeedsError(f"{ENV_NAME} is not set")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise NeedsError(f"not JSON: {exc.msg} at line {exc.lineno}") from None
    if not isinstance(data, dict):
        raise NeedsError("not an object of jobs")
    results: dict[str, str] = {}
    for job, entry in data.items():
        result = entry.get("result") if isinstance(entry, dict) else None
        if not isinstance(result, str) or not result:
            raise NeedsError(f"job {job!r} has no result")
        results[str(job)] = result
    return results


def decide(results: Mapping[str, str]) -> list[str]:
    """Reasons why ci-ok is red; empty when it is green."""
    reasons: list[str] = []
    for job in CORE_JOBS:
        result = results.get(job, MISSING)
        if result != SUCCESS:
            reasons.append(f"job={job} result={result}")
    deny = [results.get(job, MISSING) for job in DENY_JOBS]
    for job, result in zip(DENY_JOBS, deny, strict=True):
        if result not in (SUCCESS, SKIPPED, MISSING):
            reasons.append(f"job={job} result={result}")
    if sorted(deny) != [SKIPPED, SUCCESS] and all(r in (SUCCESS, SKIPPED, MISSING) for r in deny):
        reasons.append(
            "denylist mode not decided: "
            + " ".join(f"{job}={r}" for job, r in zip(DENY_JOBS, deny, strict=True))
        )
    for job, result in results.items():
        if job not in (*CORE_JOBS, *DENY_JOBS) and result != SUCCESS:
            reasons.append(f"job={job} result={result}")
    return reasons


def main(argv: Sequence[str] | None = None) -> int:
    if argv:
        print("usage: ci_ok.py (input only through NEEDS_JSON)", file=sys.stderr)
        return EXIT_INVALID
    try:
        results = parse_needs(os.environ.get(ENV_NAME))
    except NeedsError as exc:
        print(f"ci_ok.needs_invalid reason={exc}", file=sys.stderr)
        return EXIT_INVALID
    for job, result in results.items():
        print(f"ci_ok.job job={job} result={result}")
    reasons = decide(results)
    if reasons:
        for reason in reasons:
            print(f"ci_ok.failed reason={reason}", file=sys.stderr)
        return EXIT_RED
    print("ci_ok.passed")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
