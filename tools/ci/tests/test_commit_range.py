# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/ci/commit_range.py."""

from __future__ import annotations

import contextlib
import io
import unittest
from unittest import mock

from tools.ci import commit_range

BASE = "a" * 40
HEAD = "b" * 40
ZERO = "0" * 40


def run(env: dict[str, str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with (
        mock.patch.dict("os.environ", env, clear=True),
        contextlib.redirect_stdout(out),
        contextlib.redirect_stderr(err),
    ):
        code = commit_range.main()
    return code, out.getvalue(), err.getvalue()


class TestCommitRange(unittest.TestCase):
    def test_pull_request_checks_base_to_head(self) -> None:
        env = {"EVENT_NAME": "pull_request", "PR_BASE_SHA": BASE, "PR_HEAD_SHA": HEAD}
        self.assertEqual(run(env), (0, f"{BASE}..{HEAD}\n", ""))

    def test_push_checks_before_to_after(self) -> None:
        env = {"EVENT_NAME": "push", "PUSH_BEFORE": BASE, "PUSH_AFTER": HEAD}
        self.assertEqual(run(env), (0, f"{BASE}..{HEAD}\n", ""))

    def test_first_push_checks_every_commit_of_after(self) -> None:
        env = {"EVENT_NAME": "push", "PUSH_BEFORE": ZERO, "PUSH_AFTER": HEAD}
        self.assertEqual(run(env), (0, f"{HEAD}\n", ""))

    def test_other_event_checks_the_branch_against_origin_main(self) -> None:
        self.assertEqual(run({"EVENT_NAME": "workflow_dispatch"}), (0, "origin/main..HEAD\n", ""))

    def test_missing_value_exits_2(self) -> None:
        for env, variable in (
            ({"EVENT_NAME": "pull_request", "PR_BASE_SHA": BASE, "PR_HEAD_SHA": ""}, "PR_HEAD_SHA"),
            ({"EVENT_NAME": "push", "PUSH_AFTER": HEAD}, "PUSH_BEFORE"),
            ({}, "EVENT_NAME"),
        ):
            with self.subTest(variable):
                code, out, err = run(env)
                self.assertEqual((code, out), (2, ""))
                self.assertEqual(err, f"commit_range.env_missing variable={variable}\n")

    def test_value_that_is_no_commit_sha_exits_2(self) -> None:
        for value in ("--all", "main", "a" * 39, "A" * 40, f"{BASE}\n"):
            with self.subTest(value):
                env = {"EVENT_NAME": "push", "PUSH_BEFORE": value, "PUSH_AFTER": HEAD}
                code, out, err = run(env)
                self.assertEqual((code, out), (2, ""))
                self.assertEqual(err, "commit_range.sha_invalid variable=PUSH_BEFORE\n")


if __name__ == "__main__":
    unittest.main()
