# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/ci/gates.py.

The tests named `..._of_repository` and the first test read the real
quality/gates.toml, Makefile, .github/workflows/ci.yml and
docs/quality/gates.md of the repository; the others use fixture files in a
temporary directory.
"""

from __future__ import annotations

import contextlib
import io
import re
import sys
import tempfile
import textwrap
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from unittest import mock

from tools.ci import check_workflows, gates

REPO_ROOT = Path(__file__).resolve().parents[3]

GATES_TOML = """\
[[gate]]
name = "lint"
make = "lint"
ci_job = "ts"
in_check = true
fork = "same"
tool = "biome, eslint, ruff"
description = "Lint TypeScript and the Python tools"

[[gate]]
name = "test"
make = "test"
ci_job = "ts"
in_check = true
fork = "same"
tool = "vitest, unittest"
description = "Unit tests"

[[gate]]
name = "gates"
make = "gates"
ci_job = "tools"
in_check = true
fork = "same"
tool = "tools/ci/gates.py"
description = "Gate list matches the Makefile"

[[gate]]
name = "fmt"
make = "fmt"
ci_job = "none"
in_check = false
fork = "skip"
tool = "biome, ruff"
description = "Format all files in place"

[[target]]
name = "check"
description = "Run every gate of make check"

[[target]]
name = "help"
description = "List the make targets"
"""

MAKEFILE = """\
# comment line
PYTHON ?= python3
.PHONY: check help lint test gates fmt

check:
\t$(PYTHON) tools/ci/gates.py run --in-check

help:
\t@$(PYTHON) tools/ci/gates.py help

lint:
\t@echo lint

test:
\t@echo test

gates:
\t@echo gates

fmt:
\t@echo fmt
"""

CI_YML = """\
name: ci
on:
  pull_request:
jobs:
  ts:
    runs-on: ubuntu-24.04
    steps:
      - run: make bootstrap
      - name: Gates
        run: make check-ts
  tools:
    runs-on: ubuntu-24.04
    steps:
      - run: make bootstrap
      - run: |
          range="a..b"
          make check-tools COMMIT_RANGE="$range"
  ci-ok:
    if: always()
    needs: [ts, tools]
    runs-on: ubuntu-24.04
    steps:
      - run: python3 tools/ci/ci_ok.py
"""

DENYLIST_GATE = """
[[gate]]
name = "denylist"
make = "denylist"
ci_job = "denylist"
in_check = true
fork = "generic"
tool = "scan.py"
description = "Deny list"
"""

DENY_JOB = """\
  denylist:
    runs-on: ubuntu-24.04
    steps:
      - run: make denylist COMMIT_RANGE=a..b
"""

DENY_FORK_JOB = """\
  denylist-fork:
    runs-on: ubuntu-24.04
    steps:
      - run: make denylist DENYLIST_FLAGS=--allow-missing COMMIT_RANGE=a..b
"""

# A stand-in for make: logs each target it is asked to build, fails for the
# targets named in FAIL_TARGETS and, for the targets named in REPORT_TARGETS,
# writes a JUnit report with one passing and one failing test to
# .reports/junit/<target>.xml, as the gates with tests do.
FAKE_MAKE = """\
import os, sys
target = sys.argv[-1]
with open(os.environ["FAKE_MAKE_LOG"], "a", encoding="utf-8") as log:
    log.write(target + "\\n")
if target in os.environ.get("REPORT_TARGETS", "").split(","):
    os.makedirs(".reports/junit", exist_ok=True)
    with open(f".reports/junit/{target}.xml", "w", encoding="utf-8") as report:
        report.write(
            '<testsuites><testsuite name="vitest">'
            '<testcase classname="a.test.ts" name="a &gt; works"/>'
            + (
                ""
                if os.environ.get("REPORT_GREEN")
                else '<testcase classname="a.test.ts" name="a &gt; breaks">'
                '<failure message="x"/></testcase>'
            )
            + "</testsuite></testsuites>"
        )
sys.exit(3 if target in os.environ.get("FAIL_TARGETS", "").split(",") else 0)
"""


class GatesCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "quality").mkdir()
        (self.root / "docs" / "quality").mkdir(parents=True)
        self.gates_toml = self.root / "quality" / "gates.toml"
        self.makefile = self.root / "Makefile"
        self.doc = self.root / "docs" / "quality" / "gates.md"
        self.ci_yml = self.root / ".github" / "workflows" / "ci.yml"
        self.ci_yml.parent.mkdir(parents=True)
        self.gates_toml.write_text(GATES_TOML, encoding="utf-8")
        self.makefile.write_text(MAKEFILE, encoding="utf-8")
        self.ci_yml.write_text(CI_YML, encoding="utf-8")

    def run_gates(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = gates.main(["--root", str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def write_doc(self) -> None:
        code, _, err = self.run_gates("doc", "--write")
        self.assertEqual(code, 0, err)


class TestGates(GatesCase):
    def test_gates_toml_matches_makefile_and_ci(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = gates.main(["--root", str(REPO_ROOT), "check"])

        self.assertEqual(code, 0, out.getvalue() + err.getvalue())
        self.assertEqual(out.getvalue(), "")
        config = gates.load_config(REPO_ROOT / "quality" / "gates.toml")
        names = {gate.name for gate in config.gates}
        self.assertTrue(
            {"fmt", "fmt-check", "lint", "typecheck", "test", "coverage"} <= names, names
        )
        targets = {target.name for target in config.targets}
        self.assertTrue(
            {"bootstrap", "check", "help", "check-ts", "check-tools", "check-security"} <= targets,
            targets,
        )
        # The check covers ci.yml: every gate of make check is called in its job.
        calls = gates.ci_calls(gates.load_ci(REPO_ROOT))
        self.assertFalse(hasattr(gates, "CI_JOBS_PENDING"), "every CI job exists")
        for gate in gates.select(config, None):
            self.assertTrue(
                {gate.make, f"check-{gate.ci_job}"} & calls.get(gate.ci_job, set()),
                (gate.name, calls),
            )
            # A gate that forks run with the generic rules also runs in the fork job.
            if gate.fork == "generic":
                self.assertIn(gate.make, calls.get(f"{gate.ci_job}-fork", set()), gate.name)

    def test_ci_uploads_junit_of_each_job_always_of_repository(self) -> None:
        workflow: Any = check_workflows.to_plain(gates.load_ci(REPO_ROOT))
        for job in ("ts", "tools", "security"):
            with self.subTest(job):
                plain = workflow["jobs"][job]
                uploads = [
                    step
                    for step in plain["steps"]
                    if str(step.get("uses", "")).startswith("actions/upload-artifact@")
                ]
                self.assertEqual(len(uploads), 1, uploads)
                self.assertEqual(uploads[0]["if"], "always()")
                self.assertEqual(uploads[0]["with"]["name"], f"junit-{job}")
                self.assertEqual(uploads[0]["with"]["path"], f".reports/junit-{job}.xml")
                runs = " ".join(str(step.get("run", "")) for step in plain["steps"])
                self.assertIn(f"make check-{job}", runs)
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        for job in ("ts", "tools", "security"):
            self.assertRegex(
                makefile, rf"\ncheck-{job}:\n\t.*--job {job} --junit \.reports/junit-{job}\.xml\n"
            )
        self.assertIn(f"JUNIT_DIR := {gates.JUNIT_DIR.as_posix()}\n", makefile)

    def test_missing_gate_in_makefile_fails(self) -> None:
        self.write_doc()
        self.makefile.write_text(MAKEFILE.replace("lint:\n\t@echo lint\n", ""), encoding="utf-8")

        code, out, _ = self.run_gates("check")

        self.assertEqual(code, 1)
        lines = out.splitlines()
        self.assertEqual(len(lines), 1, out)
        self.assertRegex(lines[0], r"^quality/gates\.toml:2:1 missing-target ")
        self.assertIn("'lint'", lines[0])

    def test_fixture_in_sync_passes(self) -> None:
        self.write_doc()

        code, out, err = self.run_gates("check")

        self.assertEqual((code, out, err), (0, "", ""))

    def test_gate_not_called_in_ci_fails(self) -> None:
        self.write_doc()
        self.ci_yml.write_text(CI_YML.replace("make check-tools", "make other"), encoding="utf-8")

        code, out, _ = self.run_gates("check")

        self.assertEqual(code, 1)
        lines = out.splitlines()
        self.assertEqual(len(lines), 1, out)
        self.assertRegex(lines[0], r"^\.github/workflows/ci\.yml:\d+:1 ci-missing-gate ")
        self.assertIn("'gates'", lines[0])
        self.assertIn("'tools'", lines[0])

    def test_gate_called_directly_in_its_job_passes(self) -> None:
        self.write_doc()
        self.ci_yml.write_text(
            CI_YML.replace("make check-tools", "make gates COMMIT_RANGE=x"), encoding="utf-8"
        )

        self.assertEqual(self.run_gates("check"), (0, "", ""))

    def test_make_only_counts_as_a_command(self) -> None:
        self.write_doc()
        for run in ("echo make check-tools", "# make check-tools", "true # make check-tools"):
            with self.subTest(run):
                self.ci_yml.write_text(
                    CI_YML.replace('make check-tools COMMIT_RANGE="$range"', run),
                    encoding="utf-8",
                )
                code, out, _ = self.run_gates("check")
                self.assertEqual(code, 1, run)
                self.assertIn("ci-missing-gate gate 'gates'", out)
        for run in ("true && make check-tools", "(make check-tools)", "  make check-tools"):
            with self.subTest(run):
                self.ci_yml.write_text(
                    CI_YML.replace('make check-tools COMMIT_RANGE="$range"', run),
                    encoding="utf-8",
                )
                self.assertEqual(self.run_gates("check"), (0, "", ""), run)

    def test_job_of_gate_missing_in_ci_fails(self) -> None:
        self.write_doc()
        self.ci_yml.write_text(
            CI_YML.replace("needs: [ts, tools]", "needs: [ts]").replace(
                "  tools:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: make bootstrap\n"
                '      - run: |\n          range="a..b"\n'
                '          make check-tools COMMIT_RANGE="$range"\n',
                "",
            ),
            encoding="utf-8",
        )

        code, out, _ = self.run_gates("check")

        self.assertEqual(code, 1)
        self.assertIn("ci-missing-gate gate 'gates' of ci_job 'tools'", out)

    def test_gate_or_group_in_wrong_job_fails(self) -> None:
        self.write_doc()
        self.ci_yml.write_text(
            CI_YML.replace("run: make check-ts", "run: make check-ts check-tools lint").replace(
                "make check-tools COMMIT", "make lint check-tools COMMIT"
            ),
            encoding="utf-8",
        )

        code, out, _ = self.run_gates("check")

        self.assertEqual(code, 1)
        self.assertIn("ci-wrong-job 'check-tools' runs in job 'ts'", out)
        self.assertIn("ci-wrong-job 'lint' runs in job 'tools'", out)
        self.assertEqual(len(out.splitlines()), 2, out)

    def test_ci_ok_must_need_every_job_and_run_always(self) -> None:
        self.write_doc()
        for text, rule in (
            (CI_YML.replace("needs: [ts, tools]", "needs: [ts]"), "ci-ok-needs"),
            (CI_YML.replace("    if: always()\n", ""), "ci-ok-always"),
            (CI_YML.replace("  ci-ok:", "  final:"), "ci-ok-missing"),
        ):
            with self.subTest(rule):
                self.ci_yml.write_text(text, encoding="utf-8")
                code, out, _ = self.run_gates("check")
                self.assertEqual(code, 1)
                self.assertIn(f" {rule} ", out)

    def test_missing_ci_yml_fails(self) -> None:
        self.write_doc()
        self.ci_yml.unlink()

        code, out, _ = self.run_gates("check")

        self.assertEqual(code, 1)
        self.assertRegex(out, r"^\.github/workflows/ci\.yml:1:1 ci-missing ")

    def test_unparsable_ci_yml_exits_2(self) -> None:
        self.write_doc()
        self.ci_yml.write_text("jobs: &anchor\n  ts: {}\n", encoding="utf-8")

        code, out, err = self.run_gates("check")

        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("gates.config_invalid path=.github/workflows/ci.yml", err)

    def deny_fixture(self, jobs: str) -> None:
        """gates.toml and Makefile with the deny gate, ci.yml with the given extra jobs."""
        self.gates_toml.write_text(GATES_TOML + DENYLIST_GATE, encoding="utf-8")
        self.makefile.write_text(MAKEFILE + "\ndenylist:\n\t@echo deny\n", encoding="utf-8")
        self.write_doc()
        names = re.findall(r"^  ([a-z-]+):$", jobs, re.MULTILINE)
        needs = ", ".join(["ts", "tools", *names])
        self.ci_yml.write_text(
            CI_YML.replace("needs: [ts, tools]", f"needs: [{needs}]") + jobs, encoding="utf-8"
        )

    def test_deny_job_and_fork_job_pass(self) -> None:
        self.deny_fixture(DENY_JOB + DENY_FORK_JOB)

        self.assertEqual(self.run_gates("check"), (0, "", ""))

    def test_missing_deny_job_fails(self) -> None:
        self.deny_fixture(DENY_FORK_JOB)

        code, out, _ = self.run_gates("check")

        self.assertEqual(code, 1)
        self.assertIn("ci-missing-gate gate 'denylist' of ci_job 'denylist'", out)
        self.assertEqual(len(out.splitlines()), 1, out)

    def test_generic_gate_missing_in_fork_job_fails(self) -> None:
        for jobs in (DENY_JOB, DENY_JOB + DENY_FORK_JOB.replace("make denylist", "make other")):
            with self.subTest(jobs):
                self.deny_fixture(jobs)
                code, out, _ = self.run_gates("check")
                self.assertEqual(code, 1)
                self.assertIn(
                    "ci-missing-fork-gate gate 'denylist' with fork = generic is not called"
                    " in job 'denylist-fork'",
                    out,
                )
                self.assertEqual(len(out.splitlines()), 1, out)

    def test_fork_job_runs_only_generic_gates_of_its_job(self) -> None:
        self.deny_fixture(DENY_JOB + DENY_FORK_JOB.replace("make denylist", "make denylist lint"))

        code, out, _ = self.run_gates("check")

        self.assertEqual(code, 1)
        self.assertIn("ci-wrong-job 'lint' runs in job 'denylist-fork'", out)
        self.assertEqual(len(out.splitlines()), 1, out)

    def test_makefile_target_missing_in_gates_toml_fails(self) -> None:
        self.write_doc()
        self.makefile.write_text(MAKEFILE + "\nextra:\n\t@echo extra\n", encoding="utf-8")

        code, out, _ = self.run_gates("check")

        self.assertEqual(code, 1)
        self.assertRegex(out, r"^Makefile:23:1 undocumented-target 'extra' ")

    def test_missing_meta_target_fails(self) -> None:
        self.write_doc()
        self.makefile.write_text(
            MAKEFILE.replace("help:\n\t@$(PYTHON) tools/ci/gates.py help\n", ""),
            encoding="utf-8",
        )

        code, out, _ = self.run_gates("check")

        self.assertEqual(code, 1)
        self.assertIn("missing-target", out)
        self.assertIn("'help'", out)

    def test_outdated_doc_fails_and_write_fixes_it(self) -> None:
        code, out, _ = self.run_gates("check")
        self.assertEqual(code, 1)
        self.assertRegex(out, r"^docs/quality/gates\.md:1:1 doc-outdated ")

        self.write_doc()
        text = self.doc.read_text(encoding="utf-8")
        self.assertIn("SPDX-License-Identifier: Apache-2.0", text.splitlines()[1])
        self.assertIn("| `lint` | `make lint` | ts | yes | same | biome, eslint, ruff |", text)
        self.assertIn("| `fmt` | `make fmt` | none | no | skip | biome, ruff |", text)
        self.assertIn("| `make help` | List the make targets |", text)
        self.assertEqual(self.run_gates("check")[0], 0)

        self.doc.write_text(text.replace("Unit tests", "Unit tests, edited"), encoding="utf-8")
        self.assertEqual(self.run_gates("check")[0], 1)

    def test_help_lists_every_target_with_its_description(self) -> None:
        code, out, _ = self.run_gates("help")

        self.assertEqual(code, 0)
        lines = out.splitlines()
        config = gates.load_config(self.gates_toml)
        entries = [(t.name, t.description) for t in config.targets] + [
            (g.make, g.description) for g in config.gates
        ]
        self.assertEqual(len(lines), len(entries) + 1)
        for name, description in entries:
            matching = [line for line in lines if line.split()[:1] == [name]]
            self.assertEqual(len(matching), 1, (name, out))
            self.assertTrue(matching[0].rstrip().endswith(description), matching[0])

    def test_help_of_repository_lists_every_makefile_target(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = gates.main(["--root", str(REPO_ROOT), "help"])
        self.assertEqual(code, 0)
        listed = {line.split()[0] for line in out.getvalue().splitlines()[1:]}
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertEqual(listed, set(gates.makefile_targets(makefile)))


class TestGatesConfig(GatesCase):
    def assert_config_error(self, toml: str, reason: str) -> None:
        self.gates_toml.write_text(toml, encoding="utf-8")
        code, out, err = self.run_gates("check")
        self.assertEqual(code, 2, err)
        self.assertEqual(out, "")
        self.assertIn("gates.config_invalid", err)
        self.assertIn(reason, err)

    def test_unknown_key_exits_2(self) -> None:
        self.assert_config_error(
            GATES_TOML.replace('fork = "skip"', 'fork = "skip"\ncolour = "red"'), "colour"
        )

    def test_unknown_ci_job_exits_2(self) -> None:
        self.assert_config_error(GATES_TOML.replace('ci_job = "tools"', 'ci_job = "x"'), "ci_job")

    def test_unknown_fork_mode_exits_2(self) -> None:
        self.assert_config_error(GATES_TOML.replace('fork = "skip"', 'fork = "maybe"'), "fork")

    def test_in_check_gate_without_ci_job_exits_2(self) -> None:
        self.assert_config_error(
            GATES_TOML.replace('ci_job = "tools"', 'ci_job = "none"'), "in_check"
        )

    def test_missing_description_exits_2(self) -> None:
        self.assert_config_error(
            GATES_TOML.replace('description = "Unit tests"\n', ""), "description"
        )

    def test_dash_in_description_exits_2(self) -> None:
        self.assert_config_error(
            GATES_TOML.replace("Unit tests", "Unit tests \u2014 fast"), "description"
        )

    def test_duplicate_target_exits_2(self) -> None:
        self.assert_config_error(GATES_TOML.replace('make = "test"', 'make = "lint"'), "duplicate")

    def test_unreadable_gates_toml_exits_2(self) -> None:
        self.assert_config_error("[[gate]\n", "quality/gates.toml")


class TestGatesRun(GatesCase):
    def setUp(self) -> None:
        super().setUp()
        script = self.root / "fake_make.py"
        script.write_text(FAKE_MAKE, encoding="utf-8")
        self.log = self.root / "make.log"
        self.make = f"{sys.executable} {script}"

    def run_with(
        self, *args: str, fail: str = "", report: str = ""
    ) -> tuple[int, str, str, list[str]]:
        env_patch = {"FAKE_MAKE_LOG": str(self.log), "FAIL_TARGETS": fail, "REPORT_TARGETS": report}
        with mock.patch.dict("os.environ", env_patch), contextlib.chdir(self.root):
            code, out, err = self.run_gates("run", "--make", self.make, *args)
        built = self.log.read_text(encoding="utf-8").split() if self.log.exists() else []
        return code, out, err, built

    def test_run_in_check_builds_every_in_check_gate_in_order(self) -> None:
        code, out, _, built = self.run_with("--in-check")

        self.assertEqual(code, 0)
        self.assertEqual(built, ["lint", "test", "gates"])
        self.assertIn("gates.passed gate=lint", out)
        self.assertIn("gates.summary passed=3 failed=0 skipped=0", out)

    def test_run_stops_at_first_failure_and_prints_summary(self) -> None:
        code, out, err, built = self.run_with("--in-check", fail="test")

        self.assertEqual(code, 1)
        self.assertEqual(built, ["lint", "test"])
        self.assertIn("gates.failed gate=test exit=3", err)
        self.assertIn("gates.summary passed=1 failed=1 skipped=1", out)

    def test_run_job_selects_gates_of_that_ci_job(self) -> None:
        code, _, _, built = self.run_with("--job", "tools")

        self.assertEqual(code, 0)
        self.assertEqual(built, ["gates"])

    def test_run_job_without_gates_passes(self) -> None:
        code, out, _, built = self.run_with("--job", "security")

        self.assertEqual(code, 0)
        self.assertEqual(built, [])
        self.assertIn("gates.summary passed=0 failed=0 skipped=0", out)

    def test_run_writes_junit_with_reports_and_one_testcase_per_other_gate(self) -> None:
        report = self.root / ".reports" / "junit-ts.xml"
        stale = self.root / ".reports" / "junit" / "lint.xml"
        stale.parent.mkdir(parents=True)
        stale.write_text("<testsuites/>", encoding="utf-8")

        code, _, _, built = self.run_with(
            "--in-check", "--junit", str(report), fail="test", report="test"
        )

        self.assertEqual((code, built), (1, ["lint", "test"]))
        self.assertFalse(stale.exists(), "a report of an earlier run must not count")
        root = ET.parse(report).getroot()  # noqa: S314
        self.assertEqual(root.tag, "testsuites")
        cases = {
            f"{case.get('classname')}::{case.get('name')}": [child.tag for child in case]
            for case in root.iter("testcase")
        }
        self.assertEqual(
            cases,
            {
                "gates::lint": [],
                "a.test.ts::a > works": [],
                "a.test.ts::a > breaks": ["failure"],
                "gates::gates": ["skipped"],
            },
        )
        self.assertEqual(
            {k: root.get(k) for k in ("tests", "failures", "errors", "skipped")},
            {"tests": "4", "failures": "1", "errors": "0", "skipped": "1"},
        )

    def junit_cases(self, report: Path) -> dict[str, list[tuple[str, str | None]]]:
        root = ET.parse(report).getroot()  # noqa: S314
        return {
            f"{case.get('classname')}::{case.get('name')}": [
                (child.tag, child.get("message")) for child in case
            ]
            for case in root.iter("testcase")
        }

    def test_run_junit_records_exit_code_when_gate_has_no_report(self) -> None:
        report = self.root / "junit.xml"

        code, _, _, _ = self.run_with("--job", "ts", "--junit", str(report), fail="lint")

        self.assertEqual(code, 1)
        self.assertEqual(
            self.junit_cases(report),
            {
                "gates::lint": [("failure", "exit 3")],
                "gates::test": [("skipped", "not run: an earlier gate failed")],
            },
        )

    def test_run_junit_records_exit_code_when_report_has_no_failure(self) -> None:
        report = self.root / "junit.xml"

        with mock.patch.dict("os.environ", {"REPORT_GREEN": "1"}):
            code, _, _, _ = self.run_with(
                "--job", "ts", "--junit", str(report), fail="test", report="test"
            )

        self.assertEqual(code, 1)
        self.assertEqual(
            self.junit_cases(report),
            {
                "gates::lint": [],
                "a.test.ts::a > works": [],
                "gates::test": [("failure", "exit 3")],
            },
        )

    def test_run_job_without_gates_writes_empty_junit(self) -> None:
        report = self.root / "junit.xml"

        code, _, _, _ = self.run_with("--job", "security", "--junit", str(report))

        self.assertEqual(code, 0)
        self.assertEqual(ET.parse(report).getroot().get("tests"), "0")  # noqa: S314

    def test_run_gate_without_make_rule_exits_2(self) -> None:
        self.makefile.write_text(MAKEFILE.replace("test:\n\t@echo test\n", ""), encoding="utf-8")

        code, _, err, built = self.run_with("--in-check")

        self.assertEqual((code, built), (2, []))
        self.assertIn("gates.config_invalid path=Makefile", err)
        self.assertIn("'test'", err)


class TestMakefileTargets(unittest.TestCase):
    def test_parses_rules_and_ignores_assignments_and_special_targets(self) -> None:
        text = textwrap.dedent(
            """\
            A := 1
            B ?= 2
            C::=3
            .PHONY: one two
            one two: dep
            \t@echo x:y
            three:
            \techo
            """
        )
        self.assertEqual(list(gates.makefile_targets(text)), ["one", "two", "three"])
        self.assertEqual(gates.makefile_targets(text)["three"], 7)


if __name__ == "__main__":
    unittest.main()
