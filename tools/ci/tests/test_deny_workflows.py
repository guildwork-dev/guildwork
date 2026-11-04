# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for the deny-list jobs of .github/workflows/ci.yml and denylist-main.yml.

The structure tests read the workflows of the repository. The run tests execute
the `run:` steps of a job with bash, in order, as the runner does: each step gets
the values of its `env:` keys from the test (an expression the event does not
fill is an empty string on GitHub, here too), RUNNER_TEMP is a temporary
directory, and `make` is a stand-in that records its arguments, the deny-list
variables and the files they name.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tools.ci import check_workflows

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"

BASE = "a" * 40
HEAD = "b" * 40
ZERO = "0" * 40
TITLE = "feat: a title with $(touch pwned) and `backticks`"
BODY = "body line\n${{ github.token }}"

FROM_REPO = (
    "github.event.pull_request.head.repo.full_name == github.repository"
    " && github.event.pull_request.user.type != 'Bot'"
)
DENY_IF = f"github.event_name != 'pull_request' || ({FROM_REPO})"
FORK_IF = (
    "github.event_name == 'pull_request' && "
    "(github.event.pull_request.head.repo.full_name != github.repository"
    " || github.event.pull_request.user.type == 'Bot')"
)

# The stand-in for make. Writes one JSON line per call to $FAKE_MAKE_LOG.
FAKE_MAKE = """\
#!/usr/bin/env python3
import json, os, stat, sys
record = {"args": sys.argv[1:]}
for name in ("DENYLIST_FILE", "ALLOW_AUTHORS_FILE", "DENYLIST_FLAGS", "PR_TITLE", "PR_BODY",
             "DENYLIST", "ALLOW_AUTHORS"):
    record[name] = os.environ.get(name)
for name in ("DENYLIST_FILE", "ALLOW_AUTHORS_FILE"):
    path = os.environ.get(name)
    if path:
        record[name + ":mode"] = oct(stat.S_IMODE(os.stat(path).st_mode))
        record[name + ":dir_mode"] = oct(stat.S_IMODE(os.stat(os.path.dirname(path)).st_mode))
        with open(path, encoding="utf-8") as handle:
            record[name + ":text"] = handle.read()
with open(os.environ["FAKE_MAKE_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(record) + "\\n")
"""


def load(name: str) -> dict[str, Any]:
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    plain = check_workflows.to_plain(check_workflows.parse_yaml(text))
    if not isinstance(plain, dict):
        raise TypeError(f"{name} is no mapping")
    return plain


def run_job(job: dict[str, Any], values: dict[str, str]) -> tuple[int, list[dict[str, Any]], str]:
    """Run the run steps of a job until one fails; return its exit code and the make calls."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        make = bin_dir / "make"
        make.write_text(FAKE_MAKE, encoding="utf-8")
        make.chmod(0o755)
        runner_temp = root / "runner-temp"
        runner_temp.mkdir()
        log = root / "make.jsonl"
        log.touch()
        base_env = {
            "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
            "HOME": tmp,
            "RUNNER_TEMP": str(runner_temp),
            "FAKE_MAKE_LOG": str(log),
        }
        code, stderr = 0, ""
        for step in job["steps"]:
            if "run" not in step:
                continue
            env = dict(base_env)
            for key in step.get("env", {}):
                env[key] = values.get(key, "")
            done = subprocess.run(  # noqa: S603 - the run steps of the own workflows
                [shutil.which("bash") or "bash", "-e", "-c", step["run"]],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            stderr += done.stderr
            if done.returncode != 0:
                code = done.returncode
                break
        calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
    return code, calls, stderr


def pr_values(**extra: str) -> dict[str, str]:
    return {
        "EVENT_NAME": "pull_request",
        "PR_BASE_SHA": BASE,
        "PR_HEAD_SHA": HEAD,
        "PR_TITLE": TITLE,
        "PR_BODY": BODY,
        **extra,
    }


def push_values(before: str, **extra: str) -> dict[str, str]:
    return {"EVENT_NAME": "push", "PUSH_BEFORE": before, "PUSH_AFTER": HEAD, **extra}


SECRETS = {"DENYLIST": "term one\nword:two", "ALLOW_AUTHORS": "A Person <a@example.com>"}


class TestDenyJobsStructure(unittest.TestCase):
    def setUp(self) -> None:
        self.ci = load("ci.yml")
        self.jobs = self.ci["jobs"]

    def test_deny_jobs_run_on_complementary_conditions(self) -> None:
        self.assertEqual(self.jobs["denylist"]["if"], DENY_IF)
        self.assertEqual(self.jobs["denylist-fork"]["if"], FORK_IF)

    def test_only_the_deny_job_has_the_environment_and_secrets(self) -> None:
        self.assertEqual(self.jobs["denylist"]["environment"], "denylist")
        for name, job in self.jobs.items():
            if name == "denylist":
                continue
            with self.subTest(name):
                self.assertNotIn("environment", job)
                self.assertNotIn("secrets.", json.dumps(job).lower())
        write = [s for s in self.jobs["denylist"]["steps"] if "secrets." in json.dumps(s)]
        self.assertEqual(len(write), 1, write)
        self.assertEqual(
            write[0]["env"],
            {
                "DENYLIST": "${{ secrets.DENYLIST }}",
                "ALLOW_AUTHORS": "${{ secrets.ALLOW_AUTHORS }}",
            },
        )
        self.assertNotIn("make ", write[0]["run"])

    def test_deny_jobs_check_out_the_full_history_without_credentials(self) -> None:
        for name in ("denylist", "denylist-fork"):
            with self.subTest(name):
                steps = self.jobs[name]["steps"]
                checkout = [s for s in steps if str(s.get("uses", "")).startswith("actions/")]
                self.assertEqual(len(checkout), 1, "no cache, no setup action: stdlib only")
                self.assertTrue(checkout[0]["uses"].startswith("actions/checkout@"))
                self.assertEqual(checkout[0]["with"]["fetch-depth"], "0")
                self.assertEqual(checkout[0]["with"]["persist-credentials"], "false")

    def test_pull_request_text_reaches_the_jobs_only_through_env(self) -> None:
        for name in ("denylist", "denylist-fork"):
            with self.subTest(name):
                gate = self.jobs[name]["steps"][-1]
                self.assertEqual(gate["env"]["PR_TITLE"], "${{ github.event.pull_request.title }}")
                self.assertEqual(gate["env"]["PR_BODY"], "${{ github.event.pull_request.body }}")

    def test_ci_ok_needs_both_deny_jobs(self) -> None:
        self.assertEqual(
            self.jobs["ci-ok"]["needs"], ["ts", "tools", "security", "denylist", "denylist-fork"]
        )

    def test_ci_comments_make_no_stale_claims(self) -> None:
        text = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
        self.assertNotIn("red by design", text)
        self.assertNotIn("check against the hashes of the lockfiles", text)

    def test_denylist_main_runs_on_push_to_main_in_the_environment(self) -> None:
        main = load("denylist-main.yml")
        self.assertEqual(main["on"], {"push": {"branches": ["main"]}})
        self.assertEqual(list(main["jobs"]), ["scan"])
        self.assertEqual(main["jobs"]["scan"]["environment"], "denylist")


class TestDenyJobsRun(unittest.TestCase):
    def setUp(self) -> None:
        self.jobs = load("ci.yml")["jobs"]

    def assert_private_files(self, call: dict[str, Any]) -> None:
        for name, secret in (
            ("DENYLIST_FILE", "DENYLIST"),
            ("ALLOW_AUTHORS_FILE", "ALLOW_AUTHORS"),
        ):
            self.assertEqual(call[f"{name}:mode"], oct(0o600))
            self.assertEqual(call[f"{name}:dir_mode"], oct(0o700))
            self.assertEqual(call[f"{name}:text"], SECRETS[secret] + "\n")
            self.assertIsNone(call[secret], "the secret itself stays out of the make step")

    def test_deny_job_in_a_pull_request(self) -> None:
        code, calls, err = run_job(self.jobs["denylist"], pr_values(**SECRETS))

        self.assertEqual(code, 0, err)
        self.assertEqual(len(calls), 1, calls)
        self.assertEqual(calls[0]["args"], ["denylist", f"COMMIT_RANGE={BASE}..{HEAD}"])
        self.assertEqual((calls[0]["PR_TITLE"], calls[0]["PR_BODY"]), (TITLE, BODY))
        self.assertIsNone(calls[0]["DENYLIST_FLAGS"])
        self.assert_private_files(calls[0])

    def test_deny_job_on_push_has_no_pull_request_text(self) -> None:
        for before, expected in ((BASE, f"{BASE}..{HEAD}"), (ZERO, HEAD)):
            with self.subTest(before):
                code, calls, err = run_job(self.jobs["denylist"], push_values(before, **SECRETS))
                self.assertEqual(code, 0, err)
                self.assertEqual(calls[0]["args"], ["denylist", f"COMMIT_RANGE={expected}"])
                self.assertIsNone(calls[0]["PR_TITLE"])
                self.assertIsNone(calls[0]["PR_BODY"])
                self.assert_private_files(calls[0])

    def test_deny_job_without_secrets_fails_before_make(self) -> None:
        for missing in ("DENYLIST", "ALLOW_AUTHORS"):
            with self.subTest(missing):
                values = pr_values(**{**SECRETS, missing: ""})
                code, calls, err = run_job(self.jobs["denylist"], values)
                self.assertNotEqual(code, 0)
                self.assertEqual(calls, [])
                self.assertIn("denylist.secret_missing", err)

    def test_fork_job_runs_the_generic_rules(self) -> None:
        code, calls, err = run_job(self.jobs["denylist-fork"], pr_values())

        self.assertEqual(code, 0, err)
        self.assertEqual(
            calls[0]["args"],
            ["denylist", "DENYLIST_FLAGS=--allow-missing", f"COMMIT_RANGE={BASE}..{HEAD}"],
        )
        self.assertEqual((calls[0]["PR_TITLE"], calls[0]["PR_BODY"]), (TITLE, BODY))
        self.assertIsNone(calls[0]["DENYLIST_FILE"])
        self.assertIsNone(calls[0]["ALLOW_AUTHORS_FILE"])

    def test_denylist_main_scans_the_pushed_commits_or_the_history(self) -> None:
        scan = load("denylist-main.yml")["jobs"]["scan"]
        for before, args in (
            (BASE, ["denylist", f"COMMIT_RANGE={BASE}..{HEAD}"]),
            (ZERO, ["denylist-history"]),
        ):
            with self.subTest(before):
                code, calls, err = run_job(scan, push_values(before, **SECRETS))
                self.assertEqual(code, 0, err)
                self.assertEqual([c["args"] for c in calls], [args])
                self.assertIsNone(calls[0]["PR_TITLE"])
                self.assert_private_files(calls[0])


if __name__ == "__main__":
    unittest.main()
