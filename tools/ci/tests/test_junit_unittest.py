# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/ci/junit_unittest.py.

Each test writes a small test package into a temporary directory and runs the
runner there in a child process, so the sample modules never mix with the
modules of this test run.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

RUNNER = Path(__file__).resolve().parents[1] / "junit_unittest.py"

SAMPLE = """\
import unittest


class TestSample(unittest.TestCase):
    def test_passes(self):
        self.assertEqual(1, 1)

    def test_fails(self):
        self.assertEqual(1, 2, "one is not two")

    def test_raises(self):
        raise RuntimeError("boom")

    @unittest.skip("not today")
    def test_skipped(self):
        pass

    def test_subtest_fails(self):
        for value in (1, 2):
            with self.subTest(value=value):
                self.assertEqual(value, 1)


class TestOther(unittest.TestCase):
    def test_passes_too(self):
        pass
"""


class TestJunit(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.report = self.root / ".reports" / "junit" / "python.xml"

    def write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text), encoding="utf-8")

    def run_runner(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            [sys.executable, str(RUNNER), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def cases(self) -> dict[str, ET.Element]:
        root = ET.parse(self.report).getroot()  # noqa: S314
        self.assertEqual(root.tag, "testsuites")
        return {f"{c.get('classname')}::{c.get('name')}": c for c in root.iter("testcase")}

    def child(self, element: ET.Element, tag: str) -> ET.Element:
        found = element.find(tag)
        if found is None:
            self.fail(f"no <{tag}> in {ET.tostring(element, encoding='unicode')}")
        return found

    def test_writes_testcase_per_test_with_failure(self) -> None:
        self.write("pkg/__init__.py", "")
        self.write("pkg/tests/__init__.py", "")
        self.write("pkg/tests/test_sample.py", SAMPLE)

        result = self.run_runner("--start-dir", "pkg", "--output", str(self.report))

        self.assertEqual(result.returncode, 1, result.stderr)
        # The usual unittest output stays on stderr.
        self.assertIn("FAILED", result.stderr)
        cases = self.cases()
        prefix = "pkg/tests/test_sample.py::TestSample::"
        self.assertEqual(
            set(cases),
            {
                prefix + "test_passes",
                prefix + "test_fails",
                prefix + "test_raises",
                prefix + "test_skipped",
                prefix + "test_subtest_fails",
                "pkg/tests/test_sample.py::TestOther::test_passes_too",
            },
        )
        self.assertEqual(list(cases[prefix + "test_passes"]), [])
        failure = self.child(cases[prefix + "test_fails"], "failure")
        self.assertIn("one is not two", failure.get("message", ""))
        self.assertIn("AssertionError", failure.text or "")
        error = self.child(cases[prefix + "test_raises"], "error")
        self.assertIn("boom", error.get("message", ""))
        skipped = self.child(cases[prefix + "test_skipped"], "skipped")
        self.assertEqual(skipped.get("message"), "not today")
        subtest = self.child(cases[prefix + "test_subtest_fails"], "failure")
        self.assertIn("value=2", subtest.text or "")
        for case in cases.values():
            self.assertGreaterEqual(float(case.get("time", "-1")), 0.0)

        report = ET.parse(self.report).getroot()  # noqa: S314
        suite = self.child(report, "testsuite")
        self.assertEqual(
            {k: suite.get(k) for k in ("tests", "failures", "errors", "skipped")},
            {"tests": "6", "failures": "2", "errors": "1", "skipped": "1"},
        )

    def test_all_passing_exits_0(self) -> None:
        self.write("pkg/__init__.py", "")
        self.write(
            "pkg/test_ok.py",
            "import unittest\n\n\nclass TestOk(unittest.TestCase):\n"
            "    def test_ok(self):\n        pass\n",
        )

        result = self.run_runner("--start-dir", "pkg", "--output", str(self.report))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(self.cases()), ["pkg/test_ok.py::TestOk::test_ok"])

    def test_import_error_is_an_error_testcase(self) -> None:
        self.write("pkg/__init__.py", "")
        self.write("pkg/test_broken.py", "import does_not_exist_anywhere\n")

        result = self.run_runner("--start-dir", "pkg", "--output", str(self.report))

        self.assertEqual(result.returncode, 1, result.stderr)
        cases = self.cases()
        self.assertEqual(len(cases), 1, cases)
        (case,) = cases.values()
        error = self.child(case, "error")
        self.assertIn("does_not_exist_anywhere", error.text or "")

    def test_no_tests_found_exits_1(self) -> None:
        self.write("pkg/__init__.py", "")

        result = self.run_runner("--start-dir", "pkg", "--output", str(self.report))

        self.assertEqual(result.returncode, 1)
        self.assertIn("junit_unittest.no_tests", result.stderr)
        self.assertEqual(self.cases(), {})

    def test_missing_start_dir_exits_2_without_report(self) -> None:
        result = self.run_runner("--start-dir", "nowhere", "--output", str(self.report))

        self.assertEqual(result.returncode, 2)
        self.assertIn("junit_unittest.usage", result.stderr)
        self.assertFalse(self.report.exists())


if __name__ == "__main__":
    unittest.main()
