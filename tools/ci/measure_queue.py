# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Measure the queue time and the concurrency of GitHub Actions runs.

Reads the workflow runs created in a period and their jobs through the Actions
REST API, with GET requests only (FE-025: "at most 2 concurrent PR runs" is
measured, not enforced):

  GET /repos/<owner>/<name>/actions/runs?created=<since>..<until>
  GET /repos/<owner>/<name>/actions/runs/<run_id>/jobs

Usage:

  measure_queue.py --repo <owner/name> --since <date> --until <date>
                   [--out-dir .reports]

<date> is YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ, both inclusive as in the
`created` filter of the API. A token in GITHUB_TOKEN is sent as a bearer token;
without it only public repositories can be read (60 requests per hour).

Outputs:

  <out-dir>/queue-runs.csv  run_id,workflow,event,pr,created_at,started_at,
                            completed_at,wait_s,duration_s,conclusion
  <out-dir>/queue-jobs.csv  run_id,job,runner_label,started_at,completed_at,
                            wait_s,duration_s,conclusion
  stdout                    three summary lines (period and counts; median
                            and maximum of the queue time of runs and jobs;
                            highest number of concurrent PR runs and jobs)

Definitions:

  run created_at    run_started_at of the API: when the counted attempt was
                    queued (equal to created_at for a first attempt)
  run started_at    earliest started_at of its jobs; completed_at the latest
                    completed_at (the API has no completion time of a run, and
                    updated_at changes later, for example on log deletion)
  job wait_s        started_at minus created_at of the job
  pr                pull request numbers (separated by ";") only for the
                    events pull_request and pull_request_target; the API also
                    lists pull requests for other events, and none for pull
                    requests from forks
  PR run            a run of the event pull_request or pull_request_target;
                    concurrent from created_at to completed_at, its jobs from
                    started_at to completed_at (half open, an end and a start
                    at the same second do not overlap)

Values without a time stamp (a run or job not yet started or completed) stay
empty in the CSV and do not count in the summary.

Standard library only (FE-004).

Exit codes:
  0  measured
  2  usage error, invalid period (`measure_queue.period_invalid`), invalid
     repository (`measure_queue.repo_invalid`), API error or unreadable answer
     (`measure_queue.api_error status=<n> path=<path>`, status 0 without an
     HTTP answer), more than 1000 runs in the period, which the API does not
     list (`measure_queue.period_too_large`); nothing is written then
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_CONFIG = 2

API = "https://api.github.com"
PER_PAGE = 100
# The API lists at most 1000 results of a filtered list of runs.
MAX_LISTED_RUNS = 1000
TIMEOUT_S = 30
PR_EVENTS = frozenset({"pull_request", "pull_request_target"})
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?")
RUN_COLUMNS = (
    "run_id",
    "workflow",
    "event",
    "pr",
    "created_at",
    "started_at",
    "completed_at",
    "wait_s",
    "duration_s",
    "conclusion",
)
JOB_COLUMNS = (
    "run_id",
    "job",
    "runner_label",
    "started_at",
    "completed_at",
    "wait_s",
    "duration_s",
    "conclusion",
)

Getter = Callable[[str], Any]


class ApiError(Exception):
    def __init__(self, status: int, url: str) -> None:
        super().__init__(
            f"measure_queue.api_error status={status} path={urllib.parse.urlsplit(url).path}"
        )


class UsageError(Exception):
    pass


def http_get(url: str) -> Any:
    """GET one URL of the API and return the parsed JSON body."""
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")  # noqa: S310 (https API URL)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:  # noqa: S310
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raise ApiError(exc.code, url) from None
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise ApiError(0, url) from None


def _pages(get: Getter, url: str, key: str, limit: int | None = None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page = 1
    separator = "&" if "?" in url else "?"
    while True:
        body = get(f"{url}{separator}per_page={PER_PAGE}&page={page}")
        if not isinstance(body, dict) or not isinstance(body.get(key), list):
            raise ApiError(0, url)
        total = body.get("total_count", 0)
        if limit is not None and total > limit:
            raise UsageError(f"measure_queue.period_too_large total={total}")
        items.extend(body[key])
        if not body[key] or len(items) >= total:
            return items
        page += 1


def _time(value: Any) -> dt.datetime | None:
    if not value:
        return None
    return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _stamp(value: dt.datetime | None) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value else ""


def _seconds(start: dt.datetime | None, end: dt.datetime | None) -> int | None:
    return int((end - start).total_seconds()) if start and end else None


def _cell(value: int | None) -> str:
    return "" if value is None else str(value)


def _max_overlap(intervals: Iterable[tuple[dt.datetime, dt.datetime]]) -> int:
    # An end sorts before a start at the same time (half-open intervals).
    events = sorted(point for start, end in intervals for point in ((start, 1), (end, -1)))
    current = highest = 0
    for _, step in events:
        current += step
        highest = max(highest, current)
    return highest


def _median(values: list[int]) -> str:
    if not values:
        return "-"
    median = statistics.median(values)
    return str(int(median)) if median == int(median) else f"{median:.1f}"


def _max(values: list[int]) -> str:
    return str(max(values)) if values else "-"


def measure(
    get: Getter, repo: str, since: str, until: str
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[str]]:
    base = f"{API}/repos/{repo}/actions/runs"
    runs = _pages(get, f"{base}?created={since}..{until}", "workflow_runs", MAX_LISTED_RUNS)
    run_rows: list[dict[str, str]] = []
    job_rows: list[dict[str, str]] = []
    run_waits: list[int] = []
    job_waits: list[int] = []
    pr_runs: list[tuple[dt.datetime, dt.datetime]] = []
    pr_jobs: list[tuple[dt.datetime, dt.datetime]] = []
    for run in runs:
        run_id = str(run["id"])
        is_pr = run.get("event") in PR_EVENTS
        jobs = _pages(get, f"{base}/{run_id}/jobs", "jobs")
        created = _time(run.get("run_started_at") or run.get("created_at"))
        starts = [t for t in (_time(job.get("started_at")) for job in jobs) if t]
        ends = [t for t in (_time(job.get("completed_at")) for job in jobs) if t]
        started = min(starts) if starts else None
        done = run.get("status") == "completed" and len(ends) == len(jobs) and bool(jobs)
        completed = max(ends) if done else None
        wait = _seconds(created, started)
        if wait is not None:
            run_waits.append(wait)
        if is_pr and created and completed:
            pr_runs.append((created, completed))
        prs = ";".join(str(pr["number"]) for pr in run.get("pull_requests") or []) if is_pr else ""
        run_rows.append(
            {
                "run_id": run_id,
                "workflow": str(run.get("name") or ""),
                "event": str(run.get("event") or ""),
                "pr": prs,
                "created_at": _stamp(created),
                "started_at": _stamp(started),
                "completed_at": _stamp(completed),
                "wait_s": _cell(wait),
                "duration_s": _cell(_seconds(started, completed)),
                "conclusion": str(run.get("conclusion") or ""),
            }
        )
        for job in jobs:
            job_created = _time(job.get("created_at"))
            job_started = _time(job.get("started_at"))
            job_completed = _time(job.get("completed_at"))
            job_wait = _seconds(job_created, job_started)
            if job_wait is not None:
                job_waits.append(job_wait)
            if is_pr and job_started and job_completed:
                pr_jobs.append((job_started, job_completed))
            job_rows.append(
                {
                    "run_id": run_id,
                    "job": str(job.get("name") or ""),
                    "runner_label": ";".join(job.get("labels") or []),
                    "started_at": _stamp(job_started),
                    "completed_at": _stamp(job_completed),
                    "wait_s": _cell(job_wait),
                    "duration_s": _cell(_seconds(job_started, job_completed)),
                    "conclusion": str(job.get("conclusion") or ""),
                }
            )
    summary = [
        f"measure_queue.period repo={repo} created={since}..{until}"
        f" runs={len(run_rows)} jobs={len(job_rows)}",
        f"measure_queue.wait run_median_s={_median(run_waits)} run_max_s={_max(run_waits)}"
        f" job_median_s={_median(job_waits)} job_max_s={_max(job_waits)}",
        f"measure_queue.concurrency pr_runs_max={_max_overlap(pr_runs)}"
        f" pr_jobs_max={_max_overlap(pr_jobs)}",
    ]
    return run_rows, job_rows, summary


def _write(path: Path, columns: Sequence[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--since", required=True, help="YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ")
    parser.add_argument("--until", required=True, help="YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ")
    parser.add_argument("--out-dir", default=".reports", type=Path)
    args = parser.parse_args(argv)
    if not REPO.fullmatch(args.repo):
        raise UsageError(f"measure_queue.repo_invalid value={args.repo}")
    for value in (args.since, args.until):
        if not DATE.fullmatch(value):
            raise UsageError(f"measure_queue.period_invalid value={value}")
    return args


def main(argv: Sequence[str] | None = None, get: Getter = http_get) -> int:
    try:
        args = _parse(argv)
        runs, jobs, summary = measure(get, args.repo, args.since, args.until)
    except (ApiError, UsageError) as exc:
        print(exc, file=sys.stderr)
        return EXIT_CONFIG
    _write(args.out_dir / "queue-runs.csv", RUN_COLUMNS, runs)
    _write(args.out_dir / "queue-jobs.csv", JOB_COLUMNS, jobs)
    print("\n".join(summary))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
