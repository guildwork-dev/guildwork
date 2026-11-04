# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/ci/opengrep_test.py.

Each test builds a small `.opengrep/` tree in a temporary directory with one
rule and its test files and runs the pinned Opengrep binary from
`.tools/bin/` on it (`make bootstrap` fetches it). The fixture starts clean
(exit 0) and each test changes one thing.
"""

from __future__ import annotations

import contextlib
import io
import tempfile
import textwrap
import tomllib
import unittest
from pathlib import Path

from tools.ci import opengrep_test

REPO_ROOT = Path(__file__).resolve().parents[3]
OPENGREP = REPO_ROOT / ".tools" / "bin" / "opengrep"

RULE_ID = "t-no-forbidden"

# Rules whose allowlist contains the test files; they must name the same globs as
# [test_only].file_globs in quality/layers.toml.
RULES_ALLOWING_TESTS = ("gw-process-env-only-in-loaders", "gw-no-direct-clock")

RULE = f"""\
rules:
  - id: {RULE_ID}
    languages: [typescript]
    severity: ERROR
    message: forbidden() is not allowed here
    paths:
      exclude:
        - "allowed/**"
    pattern: forbidden()
"""

BAD = f"""\
// ruleid: {RULE_ID}
forbidden();
"""

GOOD = f"""\
// ok: {RULE_ID}
permitted();
"""


class OpengrepTestCase(unittest.TestCase):
    def setUp(self) -> None:
        if not OPENGREP.is_file():
            self.fail(f"{OPENGREP} is missing; run make bootstrap")
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.write(f".opengrep/rules/{RULE_ID}.yaml", RULE)
        self.write(f".opengrep/tests/{RULE_ID}/bad_call.ts", BAD)
        self.write(f".opengrep/tests/{RULE_ID}/good_call.ts", GOOD)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text), encoding="utf-8")

    def run_tool(self) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = opengrep_test.main(["--root", str(self.root), "--opengrep", str(OPENGREP)])
        return code, out.getvalue(), err.getvalue()


class TestOpengrepRuleTests(OpengrepTestCase):
    def test_passing_rule_exits_0(self) -> None:
        code, out, err = self.run_tool()
        self.assertEqual(code, 0, out + err)
        self.assertIn(f"opengrep_test.passed rule={RULE_ID}", out)

    def test_bad_case_without_finding_exits_1(self) -> None:
        self.write(
            f".opengrep/tests/{RULE_ID}/bad_call.ts", f"// ruleid: {RULE_ID}\npermitted();\n"
        )
        code, out, err = self.run_tool()
        self.assertEqual(code, 1, out + err)
        self.assertIn(f"opengrep_test.failed rule={RULE_ID}", out)

    def test_good_case_with_finding_exits_1(self) -> None:
        self.write(f".opengrep/tests/{RULE_ID}/good_call.ts", f"// ok: {RULE_ID}\nforbidden();\n")
        code, out, err = self.run_tool()
        self.assertEqual(code, 1, out + err)
        self.assertIn(f"opengrep_test.failed rule={RULE_ID}", out)

    def test_rule_without_good_case_exits_2(self) -> None:
        (self.root / f".opengrep/tests/{RULE_ID}/good_call.ts").unlink()
        code, _, err = self.run_tool()
        self.assertEqual(code, 2)
        self.assertIn("opengrep_test.config_invalid", err)
        self.assertIn("good_*.ts", err)

    def test_rule_without_tests_exits_2(self) -> None:
        self.write(".opengrep/rules/t-other.yaml", RULE.replace(RULE_ID, "t-other"))
        code, _, err = self.run_tool()
        self.assertEqual(code, 2)
        self.assertIn("t-other", err)

    def test_tests_without_rule_exits_2(self) -> None:
        self.write(".opengrep/tests/t-orphan/bad_x.ts", BAD.replace(RULE_ID, "t-orphan"))
        code, _, err = self.run_tool()
        self.assertEqual(code, 2)
        self.assertIn("t-orphan", err)

    def test_rule_id_differs_from_file_name_exits_2(self) -> None:
        self.write(
            f".opengrep/rules/{RULE_ID}.yaml", RULE.replace(f"id: {RULE_ID}", "id: t-renamed")
        )
        code, _, err = self.run_tool()
        self.assertEqual(code, 2)
        self.assertIn("t-renamed", err)

    def test_bad_case_without_ruleid_annotation_exits_2(self) -> None:
        self.write(f".opengrep/tests/{RULE_ID}/bad_call.ts", "forbidden();\n")
        code, _, err = self.run_tool()
        self.assertEqual(code, 2)
        self.assertIn(f"ruleid: {RULE_ID}", err)

    def test_good_case_with_ruleid_annotation_exits_2(self) -> None:
        self.write(f".opengrep/tests/{RULE_ID}/good_call.ts", BAD)
        code, _, err = self.run_tool()
        self.assertEqual(code, 2)
        self.assertIn("good_call.ts", err)

    def test_missing_binary_exits_2(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = opengrep_test.main(
                ["--root", str(self.root), "--opengrep", str(self.root / "no-such-binary")]
            )
        self.assertEqual(code, 2)
        self.assertIn("opengrep_test.binary_missing", err.getvalue())


class TestOpengrepPathCases(OpengrepTestCase):
    def test_allowed_path_passes(self) -> None:
        self.write(
            f".opengrep/tests/{RULE_ID}/paths/allowed/a.ts", GOOD.replace("permitted", "forbidden")
        )
        code, out, err = self.run_tool()
        self.assertEqual(code, 0, out + err)

    def test_finding_in_other_path_is_expected(self) -> None:
        self.write(f".opengrep/tests/{RULE_ID}/paths/other/a.ts", BAD)
        code, out, err = self.run_tool()
        self.assertEqual(code, 0, out + err)

    def test_unexpected_finding_exits_1(self) -> None:
        self.write(
            f".opengrep/tests/{RULE_ID}/paths/other/a.ts", GOOD.replace("permitted", "forbidden")
        )
        code, out, _ = self.run_tool()
        self.assertEqual(code, 1)
        self.assertIn("other/a.ts:2:1 " + RULE_ID + " unexpected finding", out)

    def test_missing_finding_exits_1(self) -> None:
        self.write(f".opengrep/tests/{RULE_ID}/paths/allowed/a.ts", BAD)
        code, out, _ = self.run_tool()
        self.assertEqual(code, 1)
        self.assertIn("allowed/a.ts:2:1 " + RULE_ID + " missing finding", out)

    def test_test_directories_are_scanned(self) -> None:
        # Opengrep's built-in ignore list skips test/ and tests/; the path cases must not.
        self.write(f".opengrep/tests/{RULE_ID}/paths/pkg/test/a.ts", BAD)
        self.write(f".opengrep/tests/{RULE_ID}/paths/pkg/tests/b.ts", BAD)
        code, out, err = self.run_tool()
        self.assertEqual(code, 0, out + err)


class TestRepositoryRules(unittest.TestCase):
    def test_test_file_globs_match_layers(self) -> None:
        """Rules that allow test files name exactly the test files of quality/layers.toml."""
        layers = tomllib.loads((REPO_ROOT / "quality/layers.toml").read_text(encoding="utf-8"))
        globs = layers["test_only"]["file_globs"]
        for rule_id in RULES_ALLOWING_TESTS:
            text = (REPO_ROOT / f".opengrep/rules/{rule_id}.yaml").read_text(encoding="utf-8")
            with self.subTest(rule=rule_id):
                for glob in globs:
                    self.assertIn(f'- "{glob}"', text)


if __name__ == "__main__":
    unittest.main()
