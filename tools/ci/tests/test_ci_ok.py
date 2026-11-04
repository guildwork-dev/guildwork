# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/ci/ci_ok.py, one per row of the table in section 4.2.

The fixtures in tools/ci/tests/fixtures/needs/ have the form of
`toJSON(needs)` in a workflow. The prefix of each file name is the expected
result: `pass-` exits 0, `fail-` exits 1. `make workflows-dry-run` (R-E03-T05)
runs ci_ok.py against the same files.
"""

from __future__ import annotations

import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest import mock

from tools.ci import ci_ok

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "needs"


def run_with(needs_json: str | None) -> tuple[int, str, str]:
    env = {} if needs_json is None else {"NEEDS_JSON": needs_json}
    out, err = io.StringIO(), io.StringIO()
    with (
        mock.patch.dict("os.environ", env, clear=True),
        contextlib.redirect_stdout(out),
        contextlib.redirect_stderr(err),
    ):
        code = ci_ok.main([])
    return code, out.getvalue(), err.getvalue()


def run_fixture(name: str) -> tuple[int, str, str]:
    return run_with((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


class TestCiOk(unittest.TestCase):
    def assert_red(self, name: str, reason: str) -> str:
        code, out, err = run_fixture(name)
        self.assertEqual(code, 1, out + err)
        self.assertIn("ci_ok.failed", err)
        self.assertIn(reason, err)
        self.assertNotIn("ci_ok.passed", out)
        return err

    # Row 1: ts, tools, security success, exactly one deny job success, the other skipped.
    def test_green_with_one_deny_variant(self) -> None:
        for name in ("pass-denylist", "pass-denylist-fork"):
            with self.subTest(name):
                code, out, err = run_fixture(name)
                self.assertEqual(code, 0, out + err)
                self.assertIn("ci_ok.passed", out)
                self.assertEqual(err, "")

    # Row 2: a job failed; the message names the job.
    def test_failed_job_is_red_and_named(self) -> None:
        err = self.assert_red("fail-job-failure", "job=tools result=failure")
        self.assertNotIn("job=ts ", err)

    # Row 3: a job was cancelled (superseded run).
    def test_cancelled_job_is_red(self) -> None:
        self.assert_red("fail-job-cancelled", "job=security result=cancelled")

    # Row 4: both deny jobs skipped, or both success.
    def test_deny_mode_not_decided_is_red(self) -> None:
        for name in ("fail-deny-both-skipped", "fail-deny-both-success"):
            with self.subTest(name):
                self.assert_red(name, "denylist mode not decided")

    # Row 4, also when the deny jobs are not in needs at all (before R-E03-T02).
    def test_missing_deny_jobs_are_red(self) -> None:
        self.assert_red("fail-deny-missing", "denylist mode not decided")

    # Row 5: ts, tools or security skipped.
    def test_skipped_core_job_is_red(self) -> None:
        self.assert_red("fail-core-skipped", "job=ts result=skipped")

    def test_missing_core_job_is_red(self) -> None:
        needs = json.loads((FIXTURES / "pass-denylist.json").read_text(encoding="utf-8"))
        del needs["security"]
        code, _, err = run_with(json.dumps(needs))
        self.assertEqual(code, 1)
        self.assertIn("job=security result=missing", err)

    def test_unknown_result_and_extra_job_are_red(self) -> None:
        needs = json.loads((FIXTURES / "pass-denylist.json").read_text(encoding="utf-8"))
        needs["extra"] = {"result": "neutral", "outputs": {}}
        code, _, err = run_with(json.dumps(needs))
        self.assertEqual(code, 1)
        self.assertIn("job=extra result=neutral", err)

    # Row 6: NEEDS_JSON missing or not JSON exits 2.
    def test_missing_or_invalid_needs_json_exits_2(self) -> None:
        for value in (None, "", "{not json", "[]", '{"ts": "success"}', '{"ts": {}}'):
            with self.subTest(value=value):
                code, out, err = run_with(value)
                self.assertEqual(code, 2, out + err)
                self.assertIn("ci_ok.needs_invalid", err)
                self.assertNotIn("ci_ok.passed", out)

    def test_prints_the_table_of_needs(self) -> None:
        code, out, _ = run_fixture("pass-denylist")
        self.assertEqual(code, 0)
        for job, result in (
            ("ts", "success"),
            ("tools", "success"),
            ("security", "success"),
            ("denylist", "success"),
            ("denylist-fork", "skipped"),
        ):
            self.assertIn(f"ci_ok.job job={job} result={result}\n", out)

    def test_every_fixture_matches_its_prefix(self) -> None:
        files = sorted(FIXTURES.glob("*.json"))
        self.assertGreaterEqual(len(files), 8)
        for path in files:
            with self.subTest(path.name):
                expected = {"pass": 0, "fail": 1}[path.name.split("-", 1)[0]]
                self.assertEqual(run_fixture(path.stem)[0], expected)


if __name__ == "__main__":
    unittest.main()
