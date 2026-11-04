# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for the workflows codeql.yml, scorecard.yml and advisories.yml.

The workflow policy itself is checked by check_workflows.py (`make
workflows`); these tests hold what the policy does not know: the triggers,
jobs and inputs of detailed design 00 section 2.11, the restrictions that
ossf/scorecard-action imposes on a workflow that publishes its results
(README of v2.5.0, section "Workflow Restrictions", read 2026-11-01), and the
call of `make scancode` with the container runner.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path
from typing import Any

from tools.ci import check_workflows

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

# The guard of the public-only jobs: scheduled runs carry no event payload and
# so no repository object (GitHub docs, "Events that trigger workflows",
# schedule: "Webhook event payload: Not applicable", read 2026-11-01); for
# them the repository variable decides.
PUBLIC_GUARD = (
    "github.event.repository.visibility == 'public' || "
    "(github.event_name == 'schedule' && vars.GUILDWORK_VISIBILITY == 'public')"
)
SCORECARD_ACTIONS = (
    "actions/checkout",
    "actions/upload-artifact",
    "github/codeql-action/upload-sarif",
    "ossf/scorecard-action",
    "step-security/harden-runner",
)
DAILY = re.compile(r"\d{1,2} \d{1,2} \* \* \*")
WEEKLY = re.compile(r"\d{1,2} \d{1,2} \* \* [0-6]")


def load(name: str) -> dict[str, Any]:
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    data = check_workflows.to_plain(check_workflows.parse_yaml(text))
    if not isinstance(data, dict):
        raise TypeError(f"{name} is not a mapping")
    return data


def normalized(expression: str) -> str:
    return re.sub(r"\s+", "", expression)


def crons(workflow: dict[str, Any]) -> list[str]:
    return [entry["cron"] for entry in workflow["on"]["schedule"]]


def action(uses: str) -> str:
    return uses.split("@", 1)[0]


def run_lines(job: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for step in job["steps"]:
        lines.extend(line.strip() for line in step.get("run", "").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


class TestCodeql(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = load("codeql.yml")
        self.job = self.workflow["jobs"]["analyze"]

    def test_triggers(self) -> None:
        on = self.workflow["on"]
        self.assertEqual(set(on), {"pull_request", "push", "schedule", "workflow_dispatch"})
        self.assertEqual(on["push"], {"branches": ["main"]})
        self.assertEqual(len(crons(self.workflow)), 1)
        self.assertRegex(crons(self.workflow)[0], WEEKLY)

    def test_single_job_runs_only_in_the_public_repository(self) -> None:
        self.assertEqual(list(self.workflow["jobs"]), ["analyze"])
        self.assertEqual(normalized(self.job["if"]), normalized(PUBLIC_GUARD))

    def test_languages_and_query_suite(self) -> None:
        matrix = self.job["strategy"]["matrix"]
        self.assertEqual(matrix, {"language": ["javascript-typescript", "actions", "python"]})
        steps = {action(s["uses"]): s for s in self.job["steps"] if "uses" in s}
        init = steps["github/codeql-action/init"]["with"]
        self.assertEqual(init["languages"], "${{ matrix.language }}")
        self.assertEqual(init["queries"], "security-extended")
        self.assertEqual(init["build-mode"], "none")
        self.assertIn("github/codeql-action/analyze", steps)

    def test_job_permissions(self) -> None:
        self.assertEqual(
            self.job["permissions"],
            {"contents": "read", "security-events": "write", "actions": "read"},
        )


class TestScorecard(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = load("scorecard.yml")
        self.job = self.workflow["jobs"]["analysis"]

    def test_triggers(self) -> None:
        on = self.workflow["on"]
        self.assertEqual(set(on), {"branch_protection_rule", "schedule", "workflow_dispatch"})
        self.assertEqual(len(crons(self.workflow)), 1)
        self.assertRegex(crons(self.workflow)[0], WEEKLY)

    def test_single_job_runs_only_in_the_public_repository(self) -> None:
        self.assertEqual(list(self.workflow["jobs"]), ["analysis"])
        self.assertEqual(normalized(self.job["if"]), normalized(PUBLIC_GUARD))

    def test_publishes_results(self) -> None:
        steps = {action(s["uses"]): s for s in self.job["steps"]}
        scorecard = steps["ossf/scorecard-action"]["with"]
        self.assertEqual(scorecard["publish_results"], "true")
        self.assertEqual(scorecard["results_format"], "sarif")
        upload = steps["github/codeql-action/upload-sarif"]["with"]
        self.assertEqual(upload["sarif_file"], scorecard["results_file"])

    # Restrictions of the action for publish_results: true.

    def test_no_workflow_env_or_defaults(self) -> None:
        self.assertNotIn("env", self.workflow)
        self.assertNotIn("defaults", self.workflow)

    def test_no_write_permission_at_workflow_level(self) -> None:
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})

    def test_job_has_no_env_defaults_container_or_services(self) -> None:
        for key in ("env", "defaults", "container", "services"):
            self.assertNotIn(key, self.job)
        self.assertTrue(self.job["runs-on"].startswith("ubuntu-"))

    def test_only_approved_actions_and_no_run_steps(self) -> None:
        for step in self.job["steps"]:
            self.assertNotIn("run", step)
            self.assertNotIn("env", step)
            self.assertIn(action(step["uses"]), SCORECARD_ACTIONS)

    def test_id_token_only_in_the_scorecard_job(self) -> None:
        self.assertEqual(self.job["permissions"].get("id-token"), "write")
        for name in ("codeql.yml", "advisories.yml", "ci.yml"):
            for job in load(name)["jobs"].values():
                self.assertNotIn("id-token", job.get("permissions", {}), msg=name)


class TestAdvisories(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = load("advisories.yml")
        self.jobs = self.workflow["jobs"]

    def test_daily_and_manual(self) -> None:
        self.assertEqual(set(self.workflow["on"]), {"schedule", "workflow_dispatch"})
        self.assertEqual(len(crons(self.workflow)), 1)
        self.assertRegex(crons(self.workflow)[0], DAILY)
        self.assertEqual(set(self.jobs), {"osv-full", "scancode"})

    def test_osv_full_scans_every_finding(self) -> None:
        lines = run_lines(self.jobs["osv-full"])
        self.assertIn("make osv", lines)
        self.assertNotIn("OSV_BASE", " ".join(lines))
        self.assertNotIn("env", self.jobs["osv-full"])

    def test_scancode_runs_in_the_container(self) -> None:
        job = self.jobs["scancode"]
        self.assertIn("make scancode SCANCODE_RUNNER=container", run_lines(job))
        self.assertNotIn("make bootstrap", run_lines(job))

    def test_scancode_reports_are_kept(self) -> None:
        uploads = [s for s in self.jobs["scancode"]["steps"] if "uses" in s]
        upload = next(s for s in uploads if action(s["uses"]) == "actions/upload-artifact")
        self.assertEqual(upload["if"], "always()")
        paths = upload["with"]["path"].split()
        self.assertEqual(paths, [".reports/scancode_policy.json", ".reports/scancode-scan.json"])

    def test_scancode_is_not_part_of_make_check(self) -> None:
        gates = tomllib.loads((REPO_ROOT / "quality/gates.toml").read_text(encoding="utf-8"))
        gate = next(g for g in gates["gate"] if g["name"] == "scancode")
        self.assertFalse(gate["in_check"])
        self.assertEqual(gate["ci_job"], "none")


@unittest.skipIf(shutil.which("make") is None, "make not installed")
class TestScancodeCall(unittest.TestCase):
    """The call of the CI job, with PYTHON and UV replaced by recording fakes.

    No container runtime is needed: the test checks what the Makefile hands
    to scancode_policy.py; test_scancode_policy.py checks the container
    command that scancode_policy.py builds from it.
    """

    def run_make(self, tmp: Path, *args: str) -> tuple[list[str], bool]:
        log = tmp / "calls"
        for name in ("python", "uv"):
            fake = tmp / name
            fake.write_text(f'#!/bin/sh\necho "{name} $*" >> "{log}"\n', encoding="utf-8")
            fake.chmod(0o755)
        subprocess.run(  # noqa: S603
            [  # noqa: S607
                "make",
                "--no-print-directory",
                "scancode",
                f"PYTHON={tmp / 'python'}",
                f"UV={tmp / 'uv'}",
                *args,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        calls = log.read_text(encoding="utf-8").splitlines()
        return calls, any(c.startswith("uv ") for c in calls)

    def test_container_runner_needs_no_local_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calls, used_uv = self.run_make(Path(tmp), "SCANCODE_RUNNER=container")
        self.assertFalse(used_uv, msg=calls)
        self.assertEqual(len(calls), 1, msg=calls)
        self.assertTrue(
            calls[0].startswith("python tools/ci/scancode_policy.py --runner container "),
            msg=calls,
        )

    def test_local_runner_installs_the_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            calls, used_uv = self.run_make(Path(tmp), "SCANCODE_RUNNER=local")
        self.assertTrue(used_uv, msg=calls)
        self.assertIn("python tools/ci/scancode_policy.py --runner local ", calls[-1] + " ")


if __name__ == "__main__":
    unittest.main()
