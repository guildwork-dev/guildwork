#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Run Python unittest discovery and write the results as JUnit XML (FE-062).

  junit_unittest.py --output FILE [--start-dir DIR] [--top-level-dir DIR]
                    [--pattern GLOB]

Discovery works like `python -m unittest discover -s DIR -t DIR -p GLOB`
(defaults: tools, ., test_*.py, paths relative to the working directory). The
usual unittest output goes to stderr; FILE gets one `testsuites` element with
one `testsuite` named `unittest` and one `testcase` per test method.

Test names follow section 8.3 of the detailed design: `classname` is
`<file>::<Class>` with the file relative to the top level directory and `name`
is the method, so `classname::name` is the name that plan criteria cite
(`tools/ci/tests/test_ci_ok.py::TestCiOk::test_<case>`). A failed subtest marks
its test as failed. A module that cannot be imported, or a failing class or
module fixture, is one `testcase` with an `error`.

Standard library only (FE-004).

Exit codes:
  0  every test passed (skipped tests count as passed)
  1  a test failed or raised, or no test was found
     (`junit_unittest.no_tests` on stderr); FILE is written in both cases
  2  usage error: start directory missing or not importable
     (`junit_unittest.usage reason=<reason>` on stderr); FILE is not written
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
import unittest
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2

SUITE_NAME = "unittest"
# The longest message attribute; the full traceback is in the element text.
MAX_MESSAGE = 500

ErrInfo = tuple[type[BaseException], BaseException, TracebackType] | tuple[None, None, None]


@dataclass
class Record:
    classname: str
    name: str
    started: float
    seconds: float = 0.0
    # "passed", "failure", "error" or "skipped"
    outcome: str = "passed"
    message: str = ""
    details: list[str] = field(default_factory=list)


def _message(text: str) -> str:
    line = text.strip().splitlines()[-1] if text.strip() else ""
    return line[:MAX_MESSAGE]


class JUnitResult(unittest.TextTestResult):
    """A text result that also records each test for the JUnit report."""

    top_level: Path = Path()

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.records: dict[str, Record] = {}
        self.order: list[str] = []

    def _names(self, test: unittest.TestCase) -> tuple[str, str]:
        cls = type(test)
        module = sys.modules.get(cls.__module__)
        file = getattr(module, "__file__", None)
        if cls.__module__ == "unittest.loader" or not isinstance(test, unittest.TestCase):
            return cls.__module__ + "." + cls.__qualname__, test.id().rsplit(".", 1)[-1]
        if file is not None:
            path = Path(file).resolve()
            if path.is_relative_to(self.top_level):
                where = path.relative_to(self.top_level).as_posix()
                return f"{where}::{cls.__qualname__}", test._testMethodName
        return f"{cls.__module__}.{cls.__qualname__}", test._testMethodName

    def _record(self, test: unittest.TestCase) -> Record:
        key = test.id()
        if key not in self.records:
            if isinstance(test, unittest.TestCase) and hasattr(test, "_testMethodName"):
                classname, name = self._names(test)
            else:  # class or module fixture errors arrive as _ErrorHolder
                classname, name = SUITE_NAME, str(test)
            self.records[key] = Record(classname, name, time.monotonic())
            self.order.append(key)
        return self.records[key]

    def _fail(self, test: unittest.TestCase, outcome: str, err: ErrInfo, prefix: str = "") -> None:
        record = self._record(test)
        if record.outcome != "error":
            record.outcome = outcome
        if err[1] is None:
            record.details.append(prefix + "no exception information")
            return
        record.message = record.message or _message(
            "".join(traceback.format_exception_only(err[1]))
        )
        record.details.append(prefix + "".join(traceback.format_exception(err[1])))

    def startTest(self, test: unittest.TestCase) -> None:
        super().startTest(test)
        self._record(test).started = time.monotonic()

    def stopTest(self, test: unittest.TestCase) -> None:
        super().stopTest(test)
        record = self._record(test)
        record.seconds = max(0.0, time.monotonic() - record.started)

    def addFailure(self, test: unittest.TestCase, err: ErrInfo) -> None:
        super().addFailure(test, err)
        self._fail(test, "failure", err)

    def addError(self, test: unittest.TestCase, err: ErrInfo) -> None:
        super().addError(test, err)
        self._fail(test, "error", err)

    def addSubTest(
        self,
        test: unittest.TestCase,
        subtest: unittest.TestCase,
        err: ErrInfo | None,
    ) -> None:
        super().addSubTest(test, subtest, err)
        if err is not None:
            failed = err[1] is not None and isinstance(err[1], test.failureException)
            self._fail(test, "failure" if failed else "error", err, prefix=f"{subtest}\n")

    def addSkip(self, test: unittest.TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        record = self._record(test)
        record.outcome = "skipped"
        record.message = reason

    def addUnexpectedSuccess(self, test: unittest.TestCase) -> None:
        super().addUnexpectedSuccess(test)
        record = self._record(test)
        record.outcome = "failure"
        record.message = "unexpected success of a test marked expectedFailure"


def build_xml(records: Sequence[Record], seconds: float) -> ET.ElementTree[ET.Element]:
    counts = {
        "tests": len(records),
        "failures": sum(r.outcome == "failure" for r in records),
        "errors": sum(r.outcome == "error" for r in records),
        "skipped": sum(r.outcome == "skipped" for r in records),
    }
    root = ET.Element("testsuites", {k: str(v) for k, v in counts.items()})
    root.set("time", f"{seconds:.3f}")
    suite = ET.SubElement(root, "testsuite", {"name": SUITE_NAME})
    for key, value in counts.items():
        suite.set(key, str(value))
    suite.set("time", f"{seconds:.3f}")
    for record in records:
        case = ET.SubElement(
            suite,
            "testcase",
            {"classname": record.classname, "name": record.name, "time": f"{record.seconds:.3f}"},
        )
        if record.outcome == "skipped":
            ET.SubElement(case, "skipped", {"message": record.message})
        elif record.outcome in ("failure", "error"):
            element = ET.SubElement(case, record.outcome, {"message": record.message})
            element.text = "\n".join(record.details)
    ET.indent(root)
    return ET.ElementTree(root)


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run unittest discovery, write JUnit XML.")
    parser.add_argument("--output", type=Path, required=True, help="JUnit XML file to write")
    parser.add_argument("--start-dir", default="tools", help="directory to discover from")
    parser.add_argument("--top-level-dir", default=".", help="top level of the imports")
    parser.add_argument("--pattern", default="test_*.py", help="file name pattern")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    top_level = Path(args.top_level_dir).resolve()
    if not Path(args.start_dir).is_dir():
        reason = f"reason=start_dir_missing dir={args.start_dir}"
        print(f"junit_unittest.usage {reason}", file=sys.stderr)
        return EXIT_USAGE
    try:
        suite = unittest.defaultTestLoader.discover(
            args.start_dir, pattern=args.pattern, top_level_dir=str(top_level)
        )
    except ImportError as exc:
        print(f"junit_unittest.usage reason=start_dir_not_importable {exc}", file=sys.stderr)
        return EXIT_USAGE

    JUnitResult.top_level = top_level
    runner = unittest.TextTestRunner(stream=sys.stderr, resultclass=JUnitResult)
    started = time.monotonic()
    result = runner.run(suite)
    seconds = time.monotonic() - started
    assert isinstance(result, JUnitResult)  # noqa: S101 (resultclass above)

    records = [result.records[key] for key in result.order]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    build_xml(records, seconds).write(args.output, encoding="utf-8", xml_declaration=True)
    if result.testsRun == 0:
        print("junit_unittest.no_tests reason=discovery found no test", file=sys.stderr)
        return EXIT_FAILED
    return EXIT_OK if result.wasSuccessful() else EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
