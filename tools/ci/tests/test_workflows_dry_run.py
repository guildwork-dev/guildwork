# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/ci/workflows_dry_run.py (make workflows-dry-run, R4)."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.ci import check_workflows, workflows_dry_run

REPO_ROOT = Path(__file__).resolve().parents[3]

# Fixture repositories carry their own identity, so that the tests never
# depend on the identity of the machine (a CI runner has none).
FIXTURE_IDENTITY = {
    "GIT_AUTHOR_NAME": "Fixture Author",
    "GIT_AUTHOR_EMAIL": "fixture@example.com",
    "GIT_COMMITTER_NAME": "Fixture Author",
    "GIT_COMMITTER_EMAIL": "fixture@example.com",
}
CHECKOUT = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1"
UPLOAD = "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9 # v7.0.2"

PROBE_WORKFLOW = f"""\
on:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  probe:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - uses: {CHECKOUT}
        with:
          persist-credentials: false
      - name: Values of the event reach the step through env
        env:
          EVENT_NAME: ${{{{ github.event_name }}}}
          AFTER: ${{{{ github.event.after }}}}
        run: |
          test "$EVENT_NAME" = push
          test "$AFTER" = "$(git rev-parse HEAD)"
          test "$(git rev-parse --is-shallow-repository)" = true
          test -d "$RUNNER_TEMP"
          make probe OUT="$RUNNER_TEMP/out"
          test "$(cat "$RUNNER_TEMP/out")" = probed
  identity:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - uses: {CHECKOUT}
        with:
          persist-credentials: false
          fetch-depth: 0
      - run: git commit --allow-empty -m "needs an identity"
  report:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - uses: {CHECKOUT}
        with:
          persist-credentials: false
      - run: echo nothing written
      - if: always()
        uses: {UPLOAD}
        with:
          name: missing
          path: .reports/missing.xml
          if-no-files-found: error
  root:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - uses: {CHECKOUT}
        with:
          persist-credentials: false
          fetch-depth: 0
      - env:
          BEFORE: ${{{{ github.event.before }}}}
          AFTER: ${{{{ github.event.after }}}}
        run: |
          test "$BEFORE" = 0000000000000000000000000000000000000000
          test "$AFTER" = "$(git rev-parse HEAD)"
          test "$(git rev-list --count HEAD)" = 1
          test -f Makefile
  nothing:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - run: test -f Makefile
"""

SECRETS = {"DENYLIST": "invented\n", "ALLOW_AUTHORS": "Fixture Author <fixture@example.com>\n"}

PROBE_MAKEFILE = "probe:\n\tprintf probed > $(OUT)\n"


def git(cwd: Path, *args: str) -> str:
    env = {**os.environ, **FIXTURE_IDENTITY}
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        env=env,
        check=True,
        capture_output=True,
        text=True,  # noqa: S607
    ).stdout.strip()


def make_repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "probe.yml").write_text(PROBE_WORKFLOW, encoding="utf-8")
    (repo / "Makefile").write_text(PROBE_MAKEFILE, encoding="utf-8")
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "first")
    git(repo, "commit", "-q", "--allow-empty", "-m", "second")
    return repo


class TestCiOkFixtures(unittest.TestCase):
    def test_repo_fixtures_decide_as_named(self) -> None:
        lines, problems = workflows_dry_run.ci_ok_fixtures(REPO_ROOT)
        self.assertEqual(problems, [])
        names = sorted(p.name for p in (REPO_ROOT / workflows_dry_run.NEEDS_FIXTURES).iterdir())
        self.assertEqual(len(lines), len(names))
        self.assertTrue(any("pass-denylist.json" in line and "exit=0" in line for line in lines))

    def test_fixture_with_other_outcome_is_a_problem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixtures = root / workflows_dry_run.NEEDS_FIXTURES
            fixtures.mkdir(parents=True)
            red = {"ts": {"result": "failure"}}
            (fixtures / "pass-red.json").write_text(json.dumps(red), encoding="utf-8")
            (fixtures / "other.json").write_text(json.dumps(red), encoding="utf-8")
            (root / "tools" / "ci" / "ci_ok.py").write_bytes(
                (REPO_ROOT / "tools" / "ci" / "ci_ok.py").read_bytes()
            )
            _, problems = workflows_dry_run.ci_ok_fixtures(root)
        self.assertEqual(len(problems), 2, msg=problems)
        self.assertTrue(any("pass-red.json" in p for p in problems))
        self.assertTrue(any("other.json" in p for p in problems))


class TestScenarios(unittest.TestCase):
    def test_scenarios_cover_every_job_of_the_repo_workflows(self) -> None:
        workflows = workflows_dry_run.load_workflows(REPO_ROOT)
        self.assertEqual(workflows_dry_run.coverage(workflows, workflows_dry_run.SCENARIOS), [])

    def test_job_without_scenario_and_unknown_job_are_reported(self) -> None:
        workflows = workflows_dry_run.load_workflows(REPO_ROOT)
        scenarios = [
            s
            for s in workflows_dry_run.SCENARIOS
            if not (s.workflow == "ci.yml" and "denylist-fork" in s.jobs)
        ]
        scenarios.append(workflows_dry_run.Scenario("ci.yml", "push", ("no-such-job",)))
        scenarios.append(workflows_dry_run.Scenario("scorecard.yml", "push", ("analysis",)))
        problems = workflows_dry_run.coverage(workflows, scenarios)
        self.assertTrue(any("denylist-fork" in p for p in problems), msg=problems)
        self.assertTrue(any("no-such-job" in p for p in problems), msg=problems)
        self.assertTrue(any("scorecard.yml" in p and "push" in p for p in problems), msg=problems)

    def test_runner_platforms_of_the_repo_workflows(self) -> None:
        workflows = workflows_dry_run.load_workflows(REPO_ROOT)
        self.assertEqual(
            workflows_dry_run.runner_platforms(workflows), [("ubuntu-24.04", "linux_x64")]
        )

    def test_new_workflow_needs_a_scenario(self) -> None:
        doc = check_workflows.parse_yaml(PROBE_WORKFLOW)
        self.assertIsInstance(doc, check_workflows.Mapping)
        assert isinstance(doc, check_workflows.Mapping)  # noqa: S101 (narrows the type)
        workflows = {"new.yml": doc}
        problems = workflows_dry_run.coverage(workflows, workflows_dry_run.SCENARIOS)
        self.assertTrue(any("new.yml" in p for p in problems), msg=problems)


class TestSubstitute(unittest.TestCase):
    def test_replaces_known_expressions(self) -> None:
        context = {"github.event_name": "push"}
        self.assertEqual(
            workflows_dry_run.substitute(
                "a-${{ github.event_name }}-${{github.event_name}}", context
            ),
            "a-push-push",
        )

    def test_unknown_expression_is_an_error(self) -> None:
        with self.assertRaises(workflows_dry_run.DryRunError) as caught:
            workflows_dry_run.substitute("${{ github.event.issue.title }}", {})
        self.assertIn("dry_run.expression_unknown", str(caught.exception))

    def test_event_contexts_know_every_expression_of_the_repo_workflows(self) -> None:
        workflows = workflows_dry_run.load_workflows(REPO_ROOT)
        shas = workflows_dry_run.Shas(base="a" * 40, head="b" * 40)
        for scenario in workflows_dry_run.SCENARIOS:
            context = workflows_dry_run.event_context(scenario.event, shas, SECRETS)
            context[workflows_dry_run.NEEDS_EXPRESSION] = "{}"
            doc = workflows[scenario.workflow]
            for job_id in scenario.jobs:
                with self.subTest(workflow=scenario.workflow, event=scenario.event, job=job_id):
                    for value in workflows_dry_run.env_values(doc, job_id):
                        workflows_dry_run.substitute(value, context)

    def test_push_first_has_zero_before(self) -> None:
        shas = workflows_dry_run.Shas(base="a" * 40, head="b" * 40)
        context = workflows_dry_run.event_context("push_first", shas, {})
        self.assertEqual(context["github.event.before"], "0" * 40)
        self.assertEqual(context["github.event.after"], "b" * 40)


class TestJobRuns(unittest.TestCase):
    def run_probe(
        self, jobs: tuple[str, ...], event: str = "push"
    ) -> dict[str, workflows_dry_run.JobRun]:
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            workflows = workflows_dry_run.load_workflows(repo)
            scenario = workflows_dry_run.Scenario("probe.yml", event, jobs)
            lines: list[str] = []
            runs = workflows_dry_run.run_scenarios(
                repo, workflows, [scenario], Path(tmp) / "work", Path(tmp) / "logs", lines.append
            )
            self.lines = lines
            return {run.job: run for run in runs}

    def test_logs_of_an_earlier_run_are_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp))
            logs = Path(tmp) / "logs"
            logs.mkdir()
            (logs / "stale-job-push.log").write_text("old\n", encoding="utf-8")
            workflows_dry_run.run_scenarios(
                repo, workflows_dry_run.load_workflows(repo), [], Path(tmp) / "work", logs, print
            )
            self.assertEqual(list(logs.iterdir()), [])

    def test_job_runs_in_a_fresh_shallow_clone_with_the_job_env(self) -> None:
        runs = self.run_probe(("probe",))
        self.assertEqual(runs["probe"].result, "success", msg="\n".join(self.lines))
        self.assertEqual(runs["probe"].make_calls, ["make probe OUT"])
        self.assertTrue(any("target=probe" in line for line in self.lines), msg=self.lines)

    def test_first_push_is_a_single_root_commit_of_the_tree(self) -> None:
        # The first push is one root commit made from the tree (FE-031, V5),
        # not the history of the build repository.
        runs = self.run_probe(("root",), event="push_first")
        self.assertEqual(runs["root"].result, "success", msg="\n".join(self.lines))

    def test_job_has_no_git_identity(self) -> None:
        runs = self.run_probe(("identity",))
        self.assertEqual(runs["identity"].result, "failure", msg="\n".join(self.lines))

    def test_missing_artifact_fails_the_job(self) -> None:
        runs = self.run_probe(("report",))
        self.assertEqual(runs["report"].result, "failure", msg="\n".join(self.lines))
        self.assertTrue(any("artifact_missing" in line for line in self.lines), msg=self.lines)

    def test_job_without_checkout_has_no_files(self) -> None:
        runs = self.run_probe(("nothing",))
        self.assertEqual(runs["nothing"].result, "failure", msg="\n".join(self.lines))

    def test_needs_json_marks_jobs_not_run_as_skipped(self) -> None:
        results = {"ts": "success"}
        needs = json.loads(workflows_dry_run.needs_json(["ts", "denylist-fork"], results))
        self.assertEqual(needs["ts"]["result"], "success")
        self.assertEqual(needs["denylist-fork"]["result"], "skipped")


if __name__ == "__main__":
    unittest.main()
