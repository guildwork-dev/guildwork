# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Print the git range of the commits a CI run checks (COMMIT_RANGE).

A CI clone has no local branch main, so the make default main..HEAD cannot be
used there. The jobs tools, denylist and denylist-fork of ci.yml and the job
scan of denylist-main.yml take the range from this script.

Input, from the environment only (values of the event reach run steps only
through env, FE-024):

  EVENT_NAME                 github.event_name
  PR_BASE_SHA, PR_HEAD_SHA   pull_request: base and head commit
  PUSH_BEFORE, PUSH_AFTER    push: old and new commit of the branch

Output on stdout, one line:

  pull_request  <base>..<head>
  push          <before>..<after>; <after> alone when before is all zeros (a
                push that creates the branch: every commit of after)
  other events  origin/main..HEAD (a manual run checks its branch against main)

Standard library only (FE-004).

Exit codes:
  0  range printed
  2  a needed value is empty (`commit_range.env_missing variable=<name>`) or
     no commit SHA (`commit_range.sha_invalid variable=<name>`) on stderr
"""

from __future__ import annotations

import os
import re
import sys

EXIT_OK = 0
EXIT_CONFIG = 2

# SHA-1 or SHA-256 object names as git prints them.
SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
ZERO = re.compile(r"0+")
DEFAULT_RANGE = "origin/main..HEAD"


class EnvError(Exception):
    def __init__(self, event: str, variable: str) -> None:
        super().__init__(f"{event} variable={variable}")


def _value(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise EnvError("commit_range.env_missing", name)
    return value


def _sha(name: str) -> str:
    value = _value(name)
    if not SHA.fullmatch(value):
        raise EnvError("commit_range.sha_invalid", name)
    return value


def commit_range() -> str:
    event = _value("EVENT_NAME")
    if event == "pull_request":
        return f"{_sha('PR_BASE_SHA')}..{_sha('PR_HEAD_SHA')}"
    if event == "push":
        before, after = _sha("PUSH_BEFORE"), _sha("PUSH_AFTER")
        return after if ZERO.fullmatch(before) else f"{before}..{after}"
    return DEFAULT_RANGE


def main() -> int:
    try:
        print(commit_range())
    except EnvError as exc:
        print(exc, file=sys.stderr)
        return EXIT_CONFIG
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
