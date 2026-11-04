# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/hooks/review_gate.py.

Every test runs main() against a temporary git repository with an isolated git
configuration and an environment that holds only what the test sets.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.hooks import review_gate


def git(root: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", "-C", str(root), *args],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


class TestReviewGate(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": tmp.name,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Ada Example",
            "GIT_AUTHOR_EMAIL": "ada@example.com",
            "GIT_COMMITTER_NAME": "Ada Example",
            "GIT_COMMITTER_EMAIL": "ada@example.com",
        }
        patcher = mock.patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "commit", "-q", "--allow-empty", "-m", "chore: first")
        self.first = git(self.root, "rev-parse", "HEAD")
        git(self.root, "commit", "-q", "--allow-empty", "-m", "chore: second")
        self.head = git(self.root, "rev-parse", "HEAD")

    def write_report(self, text: str, sha: str | None = None) -> Path:
        path = self.root / ".review" / f"{sha or self.head}.md"
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        return path

    def run_main(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = review_gate.main(["--root", str(self.root), *argv])
        return code, out.getvalue(), err.getvalue()

    def test_requires_exact_last_line(self) -> None:
        accepted = {
            "plain": "# Red team\n\nNo finding.\n\nUrteil: JA\n",
            "trailing blank lines": "Findings: none\nUrteil: JA\n\n   \n\t\n",
            "no final newline": "Findings: none\nUrteil: JA",
            "CRLF line endings": "Findings: none\r\nUrteil: JA\r\n",
            "earlier NEIN, final JA": "Urteil: NEIN first round\n\nFixed.\nUrteil: JA\n",
        }
        for case, text in accepted.items():
            with self.subTest(case=case):
                self.write_report(text)
                code, out, _ = self.run_main()
                self.assertEqual((code, out), (review_gate.EXIT_OK, ""))
        rejected = {
            "verdict NEIN": "Urteil: NEIN the gateway is bypassed\n",
            "JA with a remark": "Urteil: JA, with remarks\n",
            "lower case": "urteil: ja\n",
            "no space": "Urteil:JA\n",
            "leading space": " Urteil: JA\n",
            "trailing space": "Urteil: JA \n",
            "translated (FE-041)": "Verdict: YES\n",
            "JA not last": "Urteil: JA\nOne more note.\n",
            "empty report": "",
            "only blank lines": "\n\n  \n",
        }
        for case, text in rejected.items():
            with self.subTest(case=case):
                self.write_report(text)
                code, out, _ = self.run_main()
                self.assertEqual(code, review_gate.EXIT_FINDINGS)
                self.assertIn(f".review/{self.head}.md:", out)
                self.assertIn(" review-verdict ", out)

    def test_missing_report_fails(self) -> None:
        code, out, _ = self.run_main()
        self.assertEqual(code, review_gate.EXIT_FINDINGS)
        self.assertTrue(out.startswith(f".review/{self.head}.md:1:1 review-missing "), out)
        # A report for another commit does not count.
        self.write_report("Urteil: JA\n", sha=self.first)
        code, out, _ = self.run_main()
        self.assertEqual(code, review_gate.EXIT_FINDINGS)
        self.assertIn(" review-missing ", out)

    def test_review_skip_allows_push(self) -> None:
        with mock.patch.dict(os.environ, {"REVIEW_SKIP": "1"}):
            code, out, err = self.run_main()
        self.assertEqual((code, out), (review_gate.EXIT_OK, ""))
        self.assertIn("review_gate.skipped", err)
        # Only the exact value 1 skips; anything else keeps the gate.
        for value in ("", "0", "true", "yes", " 1"):
            with self.subTest(value=value), mock.patch.dict(os.environ, {"REVIEW_SKIP": value}):
                code, out, _ = self.run_main()
                self.assertEqual(code, review_gate.EXIT_FINDINGS)
                self.assertIn(" review-missing ", out)

    def test_pushed_commit_must_be_head(self) -> None:
        self.write_report("Urteil: JA\n")
        with mock.patch.dict(os.environ, {"PRE_COMMIT_TO_REF": self.head}):
            self.assertEqual(self.run_main()[0], review_gate.EXIT_OK)
        self.write_report("Urteil: JA\n", sha=self.first)
        with mock.patch.dict(os.environ, {"PRE_COMMIT_TO_REF": self.first}):
            code, out, _ = self.run_main()
        self.assertEqual(code, review_gate.EXIT_FINDINGS)
        self.assertIn(" review-not-head ", out)

    def test_json_report(self) -> None:
        report = self.root / ".reports" / "review_gate.json"
        code, _, _ = self.run_main("--json", str(report))
        self.assertEqual(code, review_gate.EXIT_FINDINGS)
        data = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual([item["rule"] for item in data["findings"]], ["review-missing"])
        self.assertEqual(data["findings"][0]["path"], f".review/{self.head}.md")

    def test_unreadable_report_is_a_usage_error(self) -> None:
        path = self.root / ".review" / f"{self.head}.md"
        path.parent.mkdir()
        path.write_bytes(b"\xff\xfeU\x00r\x00")
        code, out, err = self.run_main()
        self.assertEqual((code, out), (review_gate.EXIT_USAGE, ""))
        self.assertIn("review_gate.report_unreadable", err)

    def test_outside_a_repository_is_a_usage_error(self) -> None:
        with tempfile.TemporaryDirectory() as other:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = review_gate.main(["--root", other])
        self.assertEqual(code, review_gate.EXIT_USAGE)
        self.assertIn("review_gate.git_failed", err.getvalue())


if __name__ == "__main__":
    unittest.main()
