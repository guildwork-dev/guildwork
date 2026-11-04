# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/ci/measure_queue.py.

The Actions API is replaced by a replay of recorded exchanges in the format of
detailed design 00 section 2.7 ("Recordings"), under
tests/fixtures/recorded/github/actions-runs-one-day/:

  001.json         GET /repos/actions/checkout/actions/runs, created on
                   2026-10-17 (10 runs: 8 pull_request, 2 dynamic)
  002 to 011.json  GET .../actions/runs/<id>/jobs for each run (24 jobs)
  manifest.json    SHA-256 per file and the overall hash (SHA-256 over the
                   lines "<sha256>  <file>" sorted by file name)

Recorded with GET only and without a token from the public repository
actions/checkout on 2026-11-01; the responses keep only the fields the tool
reads (no person names, no mail addresses, no commit data).
"""

from __future__ import annotations

import contextlib
import csv
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tools.ci import measure_queue

RECORDED = (
    Path(__file__).resolve().parent / "fixtures" / "recorded" / "github" / "actions-runs-one-day"
)
ARGS = ["--repo", "actions/checkout", "--since", "2026-10-17", "--until", "2026-10-17"]
RUN_COLUMNS = (
    "run_id,workflow,event,pr,created_at,started_at,completed_at,wait_s,duration_s,conclusion"
)
JOB_COLUMNS = "run_id,job,runner_label,started_at,completed_at,wait_s,duration_s,conclusion"


class Replay:
    """Answers GET requests from the recorded exchanges; fails on anything else."""

    def __init__(self, directory: Path, status: int | None = None) -> None:
        self.exchanges: dict[str, dict[str, Any]] = {}
        for path in sorted(directory.glob("[0-9][0-9][0-9].json")):
            exchange = json.loads(path.read_text(encoding="utf-8"))
            self.exchanges[exchange["request"]["url"]] = exchange
        self.status = status
        self.used: list[str] = []

    def __call__(self, url: str) -> Any:
        if url not in self.exchanges:
            raise AssertionError(f"no recorded exchange for {url}")
        exchange = self.exchanges[url]
        if exchange["request"]["method"] != "GET":
            raise AssertionError("recording with a method other than GET")
        self.used.append(url)
        status = self.status or exchange["response"]["status"]
        if status != 200:
            raise measure_queue.ApiError(status, url)
        return exchange["response"]["body"]


def run(argv: list[str], replay: Replay) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = measure_queue.main(argv, get=replay)
    return code, out.getvalue(), err.getvalue()


def read_csv(path: Path) -> tuple[str, dict[str, dict[str, str]]]:
    text = path.read_text(encoding="utf-8")
    header = text.splitlines()[0]
    rows = list(csv.DictReader(io.StringIO(text)))
    return header, {f"{row['run_id']}/{row.get('job', '')}": row for row in rows}


class TestMeasure(unittest.TestCase):
    def test_computes_wait_from_recorded_runs(self) -> None:
        replay = Replay(RECORDED)
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = run([*ARGS, "--out-dir", tmp], replay)
            self.assertEqual((code, err), (0, ""))
            run_header, runs = read_csv(Path(tmp) / "queue-runs.csv")
            job_header, jobs = read_csv(Path(tmp) / "queue-jobs.csv")

        self.assertEqual(run_header, RUN_COLUMNS)
        self.assertEqual(job_header, JOB_COLUMNS)
        self.assertEqual((len(runs), len(jobs)), (10, 24))
        self.assertEqual(sorted(replay.used), sorted(replay.exchanges))

        # Build and Test of PR 2598: first job starts 3 s after the run was
        # created, the last one ends 129 s later.
        self.assertEqual(
            runs["39020211001/"],
            {
                "run_id": "39020211001",
                "workflow": "Build and Test",
                "event": "pull_request",
                "pr": "2598",
                "created_at": "2026-10-17T09:12:00Z",
                "started_at": "2026-10-17T09:12:03Z",
                "completed_at": "2026-10-17T09:14:12Z",
                "wait_s": "3",
                "duration_s": "129",
                "conclusion": "success",
            },
        )
        # A run of another event keeps no PR number, even though the API
        # lists pull requests for it.
        self.assertEqual(runs["39020143947/"]["pr"], "")
        self.assertEqual(runs["39020143947/"]["wait_s"], "4")
        self.assertEqual(
            jobs["39020211001/test (macos-latest)"],
            {
                "run_id": "39020211001",
                "job": "test (macos-latest)",
                "runner_label": "macos-latest",
                "started_at": "2026-10-17T09:12:08Z",
                "completed_at": "2026-10-17T09:12:50Z",
                "wait_s": "7",
                "duration_s": "42",
                "conclusion": "success",
            },
        )
        self.assertEqual(
            out.splitlines(),
            [
                "measure_queue.period repo=actions/checkout created=2026-10-17..2026-10-17"
                " runs=10 jobs=24",
                "measure_queue.wait run_median_s=4 run_max_s=5 job_median_s=3 job_max_s=7",
                "measure_queue.concurrency pr_runs_max=4 pr_jobs_max=11",
            ],
        )

    def test_api_error_exits_2_without_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = run([*ARGS, "--out-dir", tmp], Replay(RECORDED, status=403))
            self.assertEqual(list(Path(tmp).iterdir()), [])
        self.assertEqual((code, out), (2, ""))
        self.assertTrue(err.startswith("measure_queue.api_error status=403 path=/repos/"), err)

    def test_invalid_period_exits_2(self) -> None:
        argv = ["--repo", "actions/checkout", "--since", "yesterday", "--until", "2026-10-17"]
        code, out, err = run(argv, Replay(RECORDED))
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err, "measure_queue.period_invalid value=yesterday\n")

    def test_recordings_match_manifest(self) -> None:
        manifest = json.loads((RECORDED / "manifest.json").read_text(encoding="utf-8"))
        files = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(RECORDED.glob("[0-9][0-9][0-9].json"))
        }
        self.assertEqual(manifest["files"], files)
        lines = "".join(f"{digest}  {name}\n" for name, digest in sorted(files.items()))
        self.assertEqual(manifest["total"], hashlib.sha256(lines.encode()).hexdigest())


if __name__ == "__main__":
    unittest.main()
