#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Dry run of the workflow set before it ever runs (step R4, make workflows-dry-run).

The workflows do not run before the first push (FE-031); the first CI run of
the predecessor project broke. This tool runs, locally and in this order:

  1. ci_ok.py against every fixture in tools/ci/tests/fixtures/needs: a file
     `pass-*.json` must exit 0, a file `fail-*.json` must exit 1.
  2. check_workflows.py --strict (known-workflow, make-target-exists,
     job-env-known).
  3. fetch.py for the platform of every runner label the workflows use
     (ubuntu-24.04 is linux_x64): the binaries make bootstrap downloads on
     the runner, checked against the SHA-256 of tools.toml.
  4. Every job of every workflow for the events in SCENARIOS, each in a fresh
     clone of the repository's HEAD made like actions/checkout makes it
     (shallow unless the checkout step sets fetch-depth: 0), with the `env:`
     of the workflow, the job and the step and with `${{ }}` replaced by the
     values of the event. `run:` steps run with `bash -e` like on a runner.

A job runs in an environment like a fresh GitHub-hosted runner, so that what
broke the predecessor's first run breaks here too: no git identity (empty
HOME, no global or system git config, user.useConfigOnly), CI=true,
GITHUB_ACTIONS=true, RUNNER_TEMP, PATH with python3 (the interpreter running
this tool), node, git, make and the system directories only.

Steps with `uses:` do not run. actions/checkout is the fresh clone;
actions/setup-node checks that node has the version of .node-version;
actions/cache restores the caches a previous job of this dry run saved (the
first job starts cold like the first CI run); actions/upload-artifact checks
that its paths exist (a missing path fails the job when if-no-files-found is
error); other actions (CodeQL, Scorecard) are listed as not run. A job
whose steps are all `uses:` is listed as such.

Values: pull requests and pushes use real commits of the clone: head is HEAD,
base is the merge base with main (HEAD^1 on main itself). push_first is the
first push of the release checklist: the all-zeros `before` of a push that
creates the branch, and as `after` one root commit with the tree of HEAD
(FE-031, V5), made by FIRST_PUSH_NAME, not the history of the build
repository. The deny list is an
invented term made at run time (never the real list); the allowed identities
are the authors and committers of the history, written to a file of mode 0600
by the job step itself, never printed.

Without a container runtime, the steps in SUBSTITUTES run instead of the
container step and say so (`dry_run.substituted`).

Output on stdout: one line per fixture, per job run (`dry_run.job`) and per
make call of a job run (`dry_run.make` with the variables the step hands to
make and the names of its env), then `dry_run.passed` or `dry_run.failed`.
Step output goes to <logs>/<workflow>-<job>-<event>.log. With `--json` a
summary is also written as JSON.

Standard library only (FE-004).

Exit codes:
  0  every fixture decided as named, no strict finding, every job succeeded
  1  otherwise
  2  configuration error (`dry_run.<reason>` on stderr): unknown expression,
     a workflow outside the YAML subset, no main branch, git failed
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

REPO_ROOT = Path(__file__).resolve().parents[2]
if __package__ in (None, ""):
    sys.path.insert(0, str(REPO_ROOT))

from tools.ci import check_workflows  # noqa: E402
from tools.ci.check_workflows import Mapping, Node, Scalar, Seq  # noqa: E402

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFIG = 2

NEEDS_FIXTURES = Path("tools/ci/tests/fixtures/needs")
CI_OK = Path("tools/ci/ci_ok.py")
FETCH = Path("tools/bootstrap/fetch.py")
# Platform of tools/bootstrap/tools.toml for each runner label of the policy.
RUNNER_PLATFORMS = {"ubuntu-24.04": "linux_x64", "ubuntu-24.04-arm": "linux_arm64"}
WORKFLOW_DIR = Path(".github/workflows")
LOG_DIR = Path(".reports/workflows-dry-run")
ZERO_SHA = "0" * 40
NEEDS_EXPRESSION = "toJSON(needs)"
SUCCESS, FAILURE, SKIPPED = "success", "failure", "skipped"
SYSTEM_PATH = ("/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin")


@dataclass(frozen=True)
class Scenario:
    """The jobs of a workflow that run for one event."""

    workflow: str
    event: str
    jobs: tuple[str, ...]


# The trigger each event of SCENARIOS stands for.
EVENT_TRIGGERS = {
    "pull_request": "pull_request",
    "pull_request_fork": "pull_request",
    "push": "push",
    "push_first": "push",
    "workflow_dispatch": "workflow_dispatch",
    "schedule": "schedule",
}

_CI_CORE = ("ts", "tools", "security")
# Which jobs run for which event. Every job of every workflow must appear at
# least once (coverage()); the job conditions (`if:`) are not evaluated here.
SCENARIOS: tuple[Scenario, ...] = (
    Scenario("ci.yml", "pull_request", (*_CI_CORE, "denylist", "ci-ok")),
    Scenario("ci.yml", "pull_request_fork", (*_CI_CORE, "denylist-fork", "ci-ok")),
    Scenario("ci.yml", "push", (*_CI_CORE, "denylist", "ci-ok")),
    Scenario("ci.yml", "push_first", (*_CI_CORE, "denylist", "ci-ok")),
    Scenario("ci.yml", "workflow_dispatch", (*_CI_CORE, "denylist", "ci-ok")),
    Scenario("denylist-main.yml", "push", ("scan",)),
    Scenario("denylist-main.yml", "push_first", ("scan",)),
    Scenario("advisories.yml", "schedule", ("osv-full", "scancode")),
    Scenario("codeql.yml", "pull_request", ("analyze",)),
    Scenario("scorecard.yml", "schedule", ("analysis",)),
)

# Steps run instead of a step that needs a container runtime, when there is
# none: (workflow, job, command in the workflow) -> replacement script.
SUBSTITUTES: dict[tuple[str, str, str], str] = {
    ("advisories.yml", "scancode", "make scancode SCANCODE_RUNNER=container"): (
        "python3 tools/bootstrap/fetch.py --only uv\nmake scancode SCANCODE_RUNNER=local\n"
    ),
}


class DryRunError(Exception):
    """The dry run cannot be done (exit 2)."""


# ---------------------------------------------------------------------------
# 1. ci_ok.py against the fixtures


def ci_ok_fixtures(root: Path) -> tuple[list[str], list[str]]:
    """Output lines and problems of ci_ok.py on every NEEDS_JSON fixture."""
    lines: list[str] = []
    problems: list[str] = []
    for path in sorted((root / NEEDS_FIXTURES).glob("*.json")):
        name = path.name
        if name.startswith("pass-"):
            expected = 0
        elif name.startswith("fail-"):
            expected = 1
        else:
            problems.append(f"dry_run.ci_ok_fixture_unnamed fixture={name}")
            continue
        env = {**os.environ, "NEEDS_JSON": path.read_text(encoding="utf-8")}
        done = subprocess.run(  # noqa: S603
            [sys.executable, str(root / CI_OK)], env=env, capture_output=True, text=True
        )
        lines.append(f"dry_run.ci_ok fixture={name} exit={done.returncode} expected={expected}")
        if done.returncode != expected:
            problems.append(
                f"dry_run.ci_ok_mismatch fixture={name} exit={done.returncode} expected={expected}"
            )
    return lines, problems


# ---------------------------------------------------------------------------
# Workflows and scenarios


def load_workflows(root: Path, directory: Path = WORKFLOW_DIR) -> dict[str, Mapping]:
    """Every workflow file by name; raise DryRunError for a file outside the subset."""
    workflows: dict[str, Mapping] = {}
    for path in check_workflows.workflow_files(root, directory):
        try:
            doc = check_workflows.parse_yaml(path.read_text(encoding="utf-8-sig"))
        except check_workflows.YamlError as exc:
            raise DryRunError(f"dry_run.workflow_unparsable path={path.name}:{exc.line}") from exc
        if not isinstance(doc, Mapping):
            raise DryRunError(f"dry_run.workflow_unparsable path={path.name}")
        workflows[path.name] = doc
    return workflows


def _jobs(doc: Mapping) -> dict[str, Mapping]:
    jobs = doc.get("jobs")
    if not isinstance(jobs, Mapping):
        return {}
    return {k.value: v for k, v in jobs.items if isinstance(v, Mapping)}


def _triggers(doc: Mapping) -> set[str]:
    on = doc.get("on")
    if isinstance(on, Scalar):
        return {on.value}
    if isinstance(on, Seq):
        return {s.value for s in on.items if isinstance(s, Scalar)}
    if isinstance(on, Mapping):
        return {k.value for k, _ in on.items}
    return set()


def coverage(workflows: dict[str, Mapping], scenarios: Sequence[Scenario]) -> list[str]:
    """Problems: a job no scenario runs, a scenario naming an unknown job or
    workflow, or an event the workflow has no trigger for."""
    problems: list[str] = []
    covered: dict[str, set[str]] = {name: set() for name in workflows}
    for s in scenarios:
        doc = workflows.get(s.workflow)
        if doc is None:
            problems.append(f"dry_run.scenario_unknown_workflow workflow={s.workflow}")
            continue
        trigger = EVENT_TRIGGERS.get(s.event)
        if trigger is None or trigger not in _triggers(doc):
            problems.append(
                f"dry_run.scenario_event_not_triggered workflow={s.workflow} event={s.event}"
            )
        jobs = _jobs(doc)
        for job in s.jobs:
            if job not in jobs:
                problems.append(f"dry_run.scenario_unknown_job workflow={s.workflow} job={job}")
            covered[s.workflow].add(job)
    for name, doc in workflows.items():
        for job in sorted(set(_jobs(doc)) - covered[name]):
            problems.append(f"dry_run.job_without_scenario workflow={name} job={job}")
    return problems


# ---------------------------------------------------------------------------
# Event values


@dataclass(frozen=True)
class Shas:
    base: str
    head: str


def event_context(event: str, shas: Shas, secret_values: dict[str, str]) -> dict[str, str]:
    """Value of each expression the workflows use, for one event. Missing
    event values are empty strings, as in GitHub expressions."""
    pull = event in ("pull_request", "pull_request_fork")
    push = event in ("push", "push_first")
    context = {
        "github.event_name": EVENT_TRIGGERS[event],
        "github.event.pull_request.base.sha": shas.base if pull else "",
        "github.event.pull_request.head.sha": shas.head if pull else "",
        "github.event.pull_request.title": "feat: dry run of the workflows" if pull else "",
        "github.event.pull_request.body": "Dry run body.\n\nSecond paragraph." if pull else "",
        "github.event.before": (ZERO_SHA if event == "push_first" else shas.base) if push else "",
        "github.event.after": shas.head if push else "",
    }
    for name, value in secret_values.items():
        context[f"secrets.{name}"] = value
    return context


def substitute(text: str, context: dict[str, str]) -> str:
    """Replace every `${{ expr }}`; raise DryRunError for an unknown one."""

    def value(match: object) -> str:
        expr = match.group(1)  # type: ignore[attr-defined]
        key = "".join(expr.split())
        if key not in context:
            raise DryRunError(f"dry_run.expression_unknown expr={key}")
        return context[key]

    return check_workflows.EXPRESSION.sub(value, text)


def _env_items(node: Node | None) -> list[tuple[str, str]]:
    if not isinstance(node, Mapping):
        return []
    return [(k.value, v.value) for k, v in node.items if isinstance(v, Scalar)]


def env_values(doc: Mapping, job_id: str) -> Iterator[str]:
    """Every env value of the workflow, the job and its steps."""
    job = _jobs(doc)[job_id]
    for _, value in _env_items(doc.get("env")) + _env_items(job.get("env")):
        yield value
    steps = job.get("steps")
    for step in steps.items if isinstance(steps, Seq) else []:
        if isinstance(step, Mapping):
            for _, value in _env_items(step.get("env")):
                yield value


def needs_json(needs: Sequence[str], results: dict[str, str]) -> str:
    """`toJSON(needs)` for jobs with these results; a job that did not run is skipped."""
    return json.dumps(
        {job: {"result": results.get(job, SKIPPED), "outputs": {}} for job in needs}, indent=2
    )


# ---------------------------------------------------------------------------
# Running jobs


@dataclass
class JobRun:
    workflow: str
    event: str
    job: str
    result: str
    log: Path
    make_calls: list[str] = field(default_factory=list)
    seconds: float = 0.0


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)  # noqa: S603, S607
    if done.returncode != 0:
        raise DryRunError(f"dry_run.git_failed args={' '.join(args[:2])} exit={done.returncode}")
    return done.stdout.strip()


def _main_sha(source: Path) -> str:
    for ref in ("refs/heads/main", "refs/remotes/origin/main"):
        done = subprocess.run(  # noqa: S603
            ["git", "rev-parse", "-q", "--verify", f"{ref}^{{commit}}"],  # noqa: S607
            cwd=source,
            capture_output=True,
            text=True,
        )
        if done.returncode == 0:
            return done.stdout.strip()
    raise DryRunError("dry_run.main_missing: the source repository has no branch main")


def source_shas(source: Path) -> tuple[Shas, str]:
    """Base and head of the pull request and push events, and main."""
    head = _git(source, "rev-parse", "HEAD")
    main = _main_sha(source)
    base = _git(source, "merge-base", head, main)
    if base == head:
        parents = _git(source, "rev-list", "--parents", "-n", "1", head).split()
        base = parents[1] if len(parents) > 1 else head
    return Shas(base=base, head=head), main


def identities(source: Path) -> str:
    """Authors and committers of the history, one `Name <mail>` per line."""
    text = _git(source, "log", "--all", "--format=%an <%ae>%n%cn <%ce>")
    return "\n".join(sorted(set(text.splitlines()))) + "\n"


# Identity of the root commit that stands for the first push (FE-031, V5);
# it is added to the allowed identities of the dry run.
FIRST_PUSH_NAME = "Guildwork Dry Run"
FIRST_PUSH_MAIL = "dry-run@example.com"
FIRST_PUSH_MESSAGE = (
    "chore: first public commit of the workflows dry run\n\n"
    f"Signed-off-by: {FIRST_PUSH_NAME} <{FIRST_PUSH_MAIL}>\n"
)


def first_push_source(source: Path, dest: Path) -> Path:
    """A repository whose main is one root commit with the tree of the
    source's HEAD: the first push of the release checklist, not the history
    of the build repository (FE-031)."""
    dest.mkdir(parents=True)
    _git(dest, "init", "-q")
    _git(dest, "fetch", "-q", "--depth=1", source.resolve().as_uri(), "HEAD")
    tree = _git(dest, "rev-parse", "FETCH_HEAD^{tree}")
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": FIRST_PUSH_NAME,
        "GIT_AUTHOR_EMAIL": FIRST_PUSH_MAIL,
        "GIT_COMMITTER_NAME": FIRST_PUSH_NAME,
        "GIT_COMMITTER_EMAIL": FIRST_PUSH_MAIL,
    }
    done = subprocess.run(  # noqa: S603
        ["git", "commit-tree", tree, "-F", "-"],  # noqa: S607
        cwd=dest,
        env=env,
        input=FIRST_PUSH_MESSAGE,
        capture_output=True,
        text=True,
    )
    if done.returncode != 0:
        raise DryRunError(f"dry_run.git_failed args=commit-tree exit={done.returncode}")
    _git(dest, "update-ref", "refs/heads/main", done.stdout.strip())
    _git(dest, "checkout", "-q", "main")
    return dest


def make_clone(source: Path, dest: Path, head: str, main: str, full: bool) -> None:
    """A clone like actions/checkout makes it: detached at head, shallow
    unless full, with origin/main (a full fetch fetches every branch)."""
    dest.mkdir(parents=True, exist_ok=True)
    _git(dest, "init", "-q")
    _git(dest, "remote", "add", "origin", source.resolve().as_uri())
    if full:
        _git(
            dest,
            "fetch",
            "-q",
            "--no-recurse-submodules",
            "origin",
            "+refs/heads/*:refs/remotes/origin/*",
            "+refs/tags/*:refs/tags/*",
        )
        _git(dest, "fetch", "-q", "origin", f"+{head}:refs/remotes/origin/dry-run-head")
        _git(dest, "update-ref", "refs/remotes/origin/main", main)
    else:
        _git(dest, "fetch", "-q", "--depth=1", "origin", f"+{head}:refs/remotes/origin/main")
    _git(dest, "checkout", "-q", "--detach", head)


@dataclass
class Runner:
    """Shared state of the job runs: environment, caches, output."""

    source: Path
    work: Path
    logs: Path
    emit: Callable[[str], None]
    shas: Shas
    main: str
    secret_values: dict[str, str]
    docker: bool
    caches: dict[str, Path] = field(default_factory=dict)
    counter: int = 0

    def base_env(self, runner_temp: Path, workspace: Path, event: str) -> dict[str, str]:
        home = runner_temp / "home"
        home.mkdir()
        gitconfig = home / ".gitconfig"
        gitconfig.write_text("[user]\n\tuseConfigOnly = true\n", encoding="utf-8")
        shim = runner_temp / "bin"
        shim.mkdir()
        (shim / "python3").symlink_to(sys.executable)
        dirs = [str(shim)]
        for tool in ("node", "git", "make", "docker"):
            found = shutil.which(tool)
            if found and str(Path(found).parent) not in dirs:
                dirs.append(str(Path(found).parent))
        dirs += [d for d in SYSTEM_PATH if d not in dirs]
        env = {
            "PATH": os.pathsep.join(dirs),
            "HOME": str(home),
            "GIT_CONFIG_GLOBAL": str(gitconfig),
            "GIT_CONFIG_NOSYSTEM": "1",
            "CI": "true",
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": EVENT_TRIGGERS[event],
            "GITHUB_SHA": self.shas.head,
            "GITHUB_WORKSPACE": str(workspace),
            "RUNNER_TEMP": str(runner_temp),
            "LANG": "C.UTF-8",
        }
        if "TMPDIR" in os.environ:
            env["TMPDIR"] = os.environ["TMPDIR"]
        return env

    def run_job(
        self,
        workflow: str,
        doc: Mapping,
        event: str,
        job_id: str,
        context: dict[str, str],
    ) -> JobRun:
        job = _jobs(doc)[job_id]
        self.counter += 1
        base = self.work / f"{self.counter:02d}-{workflow.removesuffix('.yml')}-{job_id}"
        workspace = base / "workspace"
        runner_temp = base / "temp"
        runner_temp.mkdir(parents=True, mode=0o700)
        log_path = self.logs / f"{workflow.removesuffix('.yml')}-{job_id}-{event}.log"
        run = JobRun(workflow, event, job_id, SUCCESS, log_path)
        env = self.base_env(runner_temp, workspace, event)
        static_env = _env_items(doc.get("env")) + _env_items(job.get("env"))
        timeout = _timeout_seconds(job)
        started = time.monotonic()
        steps = job.get("steps")
        step_list = (
            [s for s in steps.items if isinstance(s, Mapping)] if isinstance(steps, Seq) else []
        )
        has_run = any(s.get("run") is not None for s in step_list)
        with log_path.open("w", encoding="utf-8") as log:
            if not has_run:
                names = [_str(s.get("uses")) or "?" for s in step_list]
                self.emit(
                    f"dry_run.uses_only workflow={workflow} job={job_id} "
                    f"actions={','.join(n.split('@')[0] for n in names)} (not run locally)"
                )
                run.result = SUCCESS
                return run
            workspace.mkdir()
            for index, step in enumerate(step_list, start=1):
                condition = _str(step.get("if"))
                if condition is not None and "".join(condition.split()) not in (
                    "always()",
                    "${{always()}}",
                ):
                    raise DryRunError(
                        f"dry_run.step_condition_unknown workflow={workflow} job={job_id}"
                    )
                if run.result == FAILURE and condition is None:
                    continue
                remaining = timeout - (time.monotonic() - started)
                ok = self.run_step(
                    workflow,
                    job_id,
                    index,
                    step,
                    workspace,
                    env,
                    static_env,
                    context,
                    log,
                    run,
                    remaining,
                )
                if not ok:
                    run.result = FAILURE
        self.save_caches(workspace)
        run.seconds = time.monotonic() - started
        return run

    def run_step(
        self,
        workflow: str,
        job_id: str,
        index: int,
        step: Mapping,
        workspace: Path,
        env: dict[str, str],
        static_env: list[tuple[str, str]],
        context: dict[str, str],
        out: TextIO,
        run: JobRun,
        remaining: float,
    ) -> bool:
        uses = _str(step.get("uses"))
        options = dict(_env_items(step.get("with")))
        write = out.write
        if uses is not None:
            action = uses.split("@")[0]
            write(f"## step {index}: uses {action}\n")
            if action == "actions/checkout":
                full = options.get("fetch-depth") == "0"
                make_clone(self.source, workspace, self.shas.head, self.main, full)
                write(f"clone of {self.shas.head} fetch-depth={'0' if full else '1'}\n")
                return True
            if action == "actions/setup-node":
                return self.check_node(workspace, options, env, write)
            if action == "actions/cache":
                for line in options.get("path", "").splitlines():
                    self.restore_cache(line.strip(), workspace, write)
                return True
            if action == "actions/upload-artifact":
                return self.check_artifact(workflow, job_id, workspace, options, write)
            write("not run locally\n")
            return True
        script = _str(step.get("run")) or ""
        step_env = static_env + _env_items(step.get("env"))
        values = {name: substitute(value, context) for name, value in step_env}
        key = (workflow, job_id, script.strip())
        if key in SUBSTITUTES and not self.docker:
            self.emit(
                f"dry_run.substituted workflow={workflow} job={job_id} "
                f"reason=no_container_runtime step={script.strip()!r}"
            )
            script = SUBSTITUTES[key]
        for call in _make_lines(script):
            calls = check_workflows.make_calls(call)
            exported = check_workflows.exported(script)
            for made in calls:
                variables = sorted(set(made.variables) | set(exported))
                text = " ".join(["make", *made.targets, *variables])
                run.make_calls.append(text)
                self.emit(
                    f"dry_run.make workflow={workflow} job={job_id} event={run.event} "
                    f"target={','.join(made.targets)} vars={','.join(variables) or '-'} "
                    f"env={','.join(sorted(values)) or '-'}"
                )
        script_path = Path(env["RUNNER_TEMP"]) / f"step-{index}.sh"
        script_path.write_text(script, encoding="utf-8")
        write(f"## step {index}: run\n{script}\n")
        out.flush()
        try:
            done = subprocess.run(  # noqa: S603
                ["bash", "-e", str(script_path)],  # noqa: S607
                cwd=workspace,
                env={**env, **values},
                stdout=out,
                stderr=subprocess.STDOUT,
                timeout=max(remaining, 1),
            )
        except subprocess.TimeoutExpired:
            write("## timeout-minutes exceeded\n")
            return False
        write(f"## exit {done.returncode}\n")
        return done.returncode == 0

    def check_node(
        self,
        workspace: Path,
        options: dict[str, str],
        env: dict[str, str],
        write: Callable[[str], object],
    ) -> bool:
        wanted_file = options.get("node-version-file")
        wanted = (
            (workspace / wanted_file).read_text(encoding="utf-8").strip() if wanted_file else ""
        )
        done = subprocess.run(["node", "--version"], env=env, capture_output=True, text=True)  # noqa: S607
        have = done.stdout.strip().removeprefix("v")
        write(f"node {have}, wanted {wanted or 'any'}\n")
        if wanted and have != wanted.removeprefix("v"):
            self.emit(f"dry_run.node_version have={have} wanted={wanted}")
            return False
        return True

    def restore_cache(self, path: str, workspace: Path, write: Callable[[str], object]) -> None:
        if not path:
            return
        cached = self.caches.get(path)
        if cached is not None and cached.is_dir():
            shutil.copytree(cached, workspace / path, symlinks=True, dirs_exist_ok=True)
            write(f"cache restored: {path}\n")
        else:
            write(f"cache miss: {path}\n")
        self.caches.setdefault(path, self.work / "cache" / path.replace("/", "_"))

    def save_caches(self, workspace: Path) -> None:
        for path, target in self.caches.items():
            if not target.exists() and (workspace / path).is_dir():
                shutil.copytree(workspace / path, target, symlinks=True)

    def check_artifact(
        self,
        workflow: str,
        job_id: str,
        workspace: Path,
        options: dict[str, str],
        write: Callable[[str], object],
    ) -> bool:
        paths = [p.strip() for p in options.get("path", "").splitlines() if p.strip()]
        missing = [p for p in paths if not (workspace / p).exists()]
        mode = options.get("if-no-files-found", "warn")
        write(f"artifact {options.get('name')}: missing={missing} if-no-files-found={mode}\n")
        if missing:
            self.emit(
                f"dry_run.artifact_missing workflow={workflow} job={job_id} "
                f"paths={','.join(missing)} if-no-files-found={mode}"
            )
        return not (missing and mode == "error" and len(missing) == len(paths))


def _str(node: Node | None) -> str | None:
    return node.value if isinstance(node, Scalar) else None


def _timeout_seconds(job: Mapping) -> float:
    value = _str(job.get("timeout-minutes"))
    return float(value) * 60 if value and value.isdigit() else 360 * 60.0


def _make_lines(script: str) -> list[str]:
    return [line for line in script.splitlines() if check_workflows.make_calls(line)]


def run_scenarios(
    source: Path,
    workflows: dict[str, Mapping],
    scenarios: Sequence[Scenario],
    work: Path,
    logs: Path,
    emit: Callable[[str], None],
    secret_values: dict[str, str] | None = None,
) -> list[JobRun]:
    """Run the jobs of every scenario. A job whose env values are the same in
    two events runs once; jobs that need others (ci-ok) run last."""
    real = (source, *source_shas(source))
    first: tuple[Path, Shas, str] | None = None
    logs.mkdir(parents=True, exist_ok=True)
    # Logs of an earlier dry run would read like results of this one.
    for old in logs.glob("*.log"):
        old.unlink()
    work.mkdir(parents=True, exist_ok=True)
    values = dict(secret_values or {})
    if "ALLOW_AUTHORS" in values:
        values["ALLOW_AUTHORS"] += f"{FIRST_PUSH_NAME} <{FIRST_PUSH_MAIL}>\n"
    runner = Runner(
        source=source,
        work=work,
        logs=logs,
        emit=emit,
        shas=real[1],
        main=real[2],
        secret_values=values,
        docker=shutil.which("docker") is not None,
    )
    runs: list[JobRun] = []
    done: dict[tuple[str, str, str], JobRun] = {}
    for scenario in scenarios:
        doc = workflows[scenario.workflow]
        jobs = _jobs(doc)
        if scenario.event == "push_first":
            if first is None:
                root = first_push_source(source, work / "first-push")
                head = _git(root, "rev-parse", "HEAD")
                first = (root, Shas(base=ZERO_SHA, head=head), head)
                emit(f"dry_run.first_push root_commit={head} tree_of={real[1].head}")
            runner.source, runner.shas, runner.main = first
        else:
            runner.source, runner.shas, runner.main = real
        context = event_context(scenario.event, runner.shas, runner.secret_values)
        results: dict[str, str] = {}
        ordered = sorted(scenario.jobs, key=lambda j: jobs[j].get("needs") is not None)
        for job_id in ordered:
            needs = _needs(jobs[job_id])
            context[NEEDS_EXPRESSION] = needs_json(needs, results)
            signature = "\n".join(substitute(v, context) for v in env_values(doc, job_id))
            key = (scenario.workflow, job_id, runner.shas.head + "\n" + signature)
            if key in done:
                previous = done[key]
                emit(
                    f"dry_run.job workflow={scenario.workflow} event={scenario.event} "
                    f"job={job_id} result={previous.result} same_as={previous.event}"
                )
                results[job_id] = previous.result
                continue
            run = runner.run_job(scenario.workflow, doc, scenario.event, job_id, context)
            done[key] = run
            runs.append(run)
            results[job_id] = run.result
            emit(
                f"dry_run.job workflow={scenario.workflow} event={scenario.event} job={job_id} "
                f"result={run.result} seconds={run.seconds:.0f} log={run.log.as_posix()}"
            )
    return runs


def runner_platforms(workflows: dict[str, Mapping]) -> list[tuple[str, str]]:
    """(runs-on label, tools.toml platform) of every label the workflows use."""
    labels = sorted(
        {
            label
            for doc in workflows.values()
            for job in _jobs(doc).values()
            if (label := _str(job.get("runs-on"))) is not None
        }
    )
    unknown = [label for label in labels if label not in RUNNER_PLATFORMS]
    if unknown:
        raise DryRunError(f"dry_run.runner_unknown runs_on={','.join(unknown)}")
    return [(label, RUNNER_PLATFORMS[label]) for label in labels]


def _needs(job: Mapping) -> list[str]:
    node = job.get("needs")
    if isinstance(node, Scalar):
        return [node.value]
    if isinstance(node, Seq):
        return [s.value for s in node.items if isinstance(s, Scalar)]
    return []


# ---------------------------------------------------------------------------
# Main


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dry run of the workflow set (R4).")
    add = parser.add_argument
    add("--root", type=Path, default=REPO_ROOT, help="repository whose HEAD is cloned")
    add("--logs", type=Path, default=LOG_DIR, help="step logs, from root")
    add("--json", type=Path, help="also write a summary as JSON here")
    add("--work", type=Path, help="directory for the clones (default: a new temporary one)")
    add("--keep", action="store_true", help="keep the clones")
    add(
        "--only",
        action="append",
        default=[],
        metavar="WORKFLOW[:JOB]",
        help="run only these workflows or jobs (fixtures and --strict always run)",
    )
    return parser.parse_args(argv)


def _selected(scenarios: Sequence[Scenario], only: Sequence[str]) -> list[Scenario]:
    if not only:
        return list(scenarios)
    picked: list[Scenario] = []
    for s in scenarios:
        jobs = tuple(j for j in s.jobs if s.workflow in only or f"{s.workflow}:{j}" in only)
        if jobs:
            picked.append(Scenario(s.workflow, s.event, jobs))
    return picked


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    logs = args.logs if args.logs.is_absolute() else root / args.logs
    summary: dict[str, object] = {"tool": "workflows_dry_run"}
    failed = False
    try:
        lines, problems = ci_ok_fixtures(root)
        for line in lines + problems:
            print(line)
        failed |= bool(problems)
        strict = subprocess.run(  # noqa: S603
            [
                sys.executable,
                str(root / "tools/ci/check_workflows.py"),
                "--root",
                str(root),
                "--strict",
            ],
            capture_output=True,
            text=True,
        )
        print(strict.stdout, end="")
        print(strict.stderr, end="", file=sys.stderr)
        print(f"dry_run.strict exit={strict.returncode}")
        if strict.returncode == EXIT_CONFIG:
            return EXIT_CONFIG
        failed |= strict.returncode != 0
        workflows = load_workflows(root)
        gaps = coverage(workflows, SCENARIOS)
        for gap in gaps:
            print(gap)
        failed |= bool(gaps)
        if gaps:
            raise DryRunError("dry_run.scenarios_incomplete")
        values = {
            "DENYLIST": f"gw-dry-run-{secrets.token_hex(8)}\n",
            "ALLOW_AUTHORS": identities(root),
        }
        work = args.work or Path(tempfile.mkdtemp(prefix="gw-dry-run-"))
        print(f"dry_run.source head={_git(root, 'rev-parse', 'HEAD')} work={work}")
        try:
            # The binaries the runners download in make bootstrap, checked
            # against the SHA-256 of tools.toml for the runner's platform.
            for label, platform in runner_platforms(workflows):
                fetched = subprocess.run(  # noqa: S603
                    [
                        sys.executable,
                        str(root / FETCH),
                        "--platform",
                        platform,
                        "--dest",
                        str(work / f"bin-{platform}"),
                    ],
                    capture_output=True,
                    text=True,
                )
                print(fetched.stdout + fetched.stderr, end="")
                print(
                    f"dry_run.runner_tools runs_on={label} platform={platform} "
                    f"exit={fetched.returncode}"
                )
                failed |= fetched.returncode != 0
            runs = run_scenarios(
                root,
                workflows,
                _selected(SCENARIOS, args.only),
                work,
                logs,
                lambda line: print(line, flush=True),
                values,
            )
        finally:
            if not args.keep and args.work is None:
                shutil.rmtree(work, ignore_errors=True)
    except DryRunError as exc:
        print(exc, file=sys.stderr)
        return EXIT_CONFIG
    failed_runs = [r for r in runs if r.result != SUCCESS]
    failed |= bool(failed_runs)
    summary.update(
        fixtures=lines,
        strict_exit=strict.returncode,
        runs=[
            {
                "workflow": r.workflow,
                "event": r.event,
                "job": r.job,
                "result": r.result,
                "make_calls": r.make_calls,
                "log": r.log.as_posix(),
            }
            for r in runs
        ],
    )
    if args.json is not None:
        target = args.json if args.json.is_absolute() else root / args.json
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for r in failed_runs:
        print(f"dry_run.failed workflow={r.workflow} event={r.event} job={r.job} log={r.log}")
    print("dry_run.failed" if failed else "dry_run.passed")
    return EXIT_FAILED if failed else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
