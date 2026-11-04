#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""The list of quality gates: check it, document it, run it.

`quality/gates.toml` is the only list of gates (FE-006). Every other place
that names gates is either checked against it or generated from it:

  check      every gate and every other target of gates.toml has a rule in the
             Makefile, every Makefile target has an entry in gates.toml,
             docs/quality/gates.md equals the generated text, and
             .github/workflows/ci.yml calls every gate of make check (rules
             below).
  doc        print docs/quality/gates.md; with --write, write it.
  help       print every make target with its one-line description (make help).
  run        build the selected gates with make, in the order of gates.toml,
             stop at the first failure and print a summary (make check and the
             group targets check-ts, check-tools, check-security). Every
             selected gate needs a rule in the Makefile (a target that is only
             in .PHONY would pass without doing anything). With --junit FILE,
             also write a JUnit report (FE-062): a gate with tests writes its
             own report to .reports/junit/<target>.xml (JUNIT_DIR in the
             Makefile) and its test suites are copied; every other gate is one
             testcase `gates::<name>` that fails with the exit code; gates not
             run after a failure are skipped testcases.

Rules of the ci.yml check. A job calls a make target when a `run:` step has
the command `make <target>` at the start of a line or after `;`, `&`, `|` or
`(` (variable assignments and options are skipped; text such as
`echo make x` or a comment does not count):

  ci-missing       ci.yml does not exist
  ci-missing-gate  a gate of make check is not called in the job named by its
                   ci_job, neither directly nor through check-<ci_job>
  ci-missing-fork-gate
                   a gate of make check with fork = generic is not called in
                   the fork job <ci_job>-fork, which runs it with the generic
                   rules for pull requests from forks and bots
  ci-wrong-job     a job calls check-<x> or a gate whose ci_job is another job;
                   a fork job <x>-fork may call only the gates of ci_job x with
                   fork = generic
  ci-ok-missing    there is no job ci-ok
  ci-ok-needs      ci-ok does not need exactly every other job
  ci-ok-always     ci-ok has no `if:` with always()

Standard library only (FE-004).

Exit codes:
  0  no finding, or every selected gate passed
  1  findings (printed as `path:line:col rule-id message` on stdout), or a
     gate failed (`gates.failed gate=<name> exit=<code>` on stderr)
  2  configuration error: gates.toml, the Makefile or ci.yml unreadable or
     invalid, or a gate to run has no Makefile rule
     (`gates.config_invalid path=<path> reason=<reason>` on stderr)
"""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
import time
import tomllib
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if __package__ in (None, ""):
    sys.path.insert(0, str(REPO_ROOT))

from tools.ci import check_workflows  # noqa: E402

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFIG = 2

GATES_PATH = Path("quality/gates.toml")
MAKEFILE_PATH = Path("Makefile")
DOC_PATH = Path("docs/quality/gates.md")
CI_PATH = Path(".github/workflows/ci.yml")
# Reports of the gates with tests, one file per make target; the Makefile
# writes them there (JUNIT_DIR).
JUNIT_DIR = Path(".reports/junit")

CI_JOBS = ("ts", "tools", "security", "denylist")
# The job <ci_job>-fork runs the gates with fork = generic of <ci_job> for pull
# requests from forks and bots, without secrets (FE-026).
FORK_JOB_SUFFIX = "-fork"
FORK_GENERIC = "generic"
CI_OK_JOB = "ci-ok"
GROUP_PREFIX = "check-"
MAKE_CALL = re.compile(r"(?:^|[;&|(])[ \t]*make[ \t]+([^;&|#)\n]*)", re.MULTILINE)
NO_CI_JOB = "none"
FORK_MODES = ("same", "generic", "skip")
GATE_KEYS = ("name", "make", "ci_job", "in_check", "fork", "tool", "description")
TARGET_KEYS = ("name", "description")
NAME = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
# Dashes U+2012 to U+2015 are not allowed in any text of the repository (FE-022).
FORBIDDEN_DASHES = re.compile("[\u2012-\u2015]")

ASSIGNMENT = re.compile(
    r"^\s*(?:(?:export|override|private)\s+)*[A-Za-z0-9_.-]+\s*(?::{1,3}=|[+?!]?=)"
)
RULE = re.compile(r"^([^:#=\t][^:#=]*?)\s*::?(?!=)")


class ConfigError(Exception):
    """gates.toml or the Makefile cannot be used."""

    def __init__(self, reason: str, path: Path = GATES_PATH) -> None:
        super().__init__(reason)
        self.path = path


@dataclass(frozen=True)
class Gate:
    name: str
    make: str
    ci_job: str
    in_check: bool
    fork: str
    tool: str
    description: str


@dataclass(frozen=True)
class Target:
    """A make target that is not a gate, such as bootstrap, check or help."""

    name: str
    description: str


@dataclass(frozen=True)
class Config:
    gates: tuple[Gate, ...]
    targets: tuple[Target, ...]

    def entries(self) -> list[tuple[str, str]]:
        """Every make target named in gates.toml with its description."""
        return [(t.name, t.description) for t in self.targets] + [
            (g.make, g.description) for g in self.gates
        ]


def _fail(reason: str) -> ConfigError:
    return ConfigError(reason)


def _text(entry: dict[str, object], where: str, key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _fail(f"{where}: {key} must be a non-empty string")
    if "\n" in value or FORBIDDEN_DASHES.search(value):
        raise _fail(f"{where}: {key} must be one line without dashes U+2012 to U+2015")
    return value


def _name(entry: dict[str, object], where: str, key: str) -> str:
    value = _text(entry, where, key)
    if not NAME.match(value):
        raise _fail(f"{where}: {key} {value!r} must match {NAME.pattern}")
    return value


def _keys(entry: object, allowed: tuple[str, ...], where: str) -> dict[str, object]:
    if not isinstance(entry, dict):
        raise _fail(f"{where}: must be a table")
    unknown = sorted(set(entry) - set(allowed))
    if unknown:
        raise _fail(f"{where}: unknown key {', '.join(unknown)}")
    missing = [key for key in allowed if key not in entry]
    if missing:
        raise _fail(f"{where}: missing key {', '.join(missing)}")
    return entry


def _parse_gate(raw: object, index: int) -> Gate:
    entry = _keys(raw, GATE_KEYS, f"gate[{index}]")
    name = _name(entry, f"gate[{index}]", "name")
    where = f"gate {name}"
    ci_job = _text(entry, where, "ci_job")
    if ci_job not in (*CI_JOBS, NO_CI_JOB):
        raise _fail(f"{where}: ci_job {ci_job!r} must be one of {', '.join((*CI_JOBS, NO_CI_JOB))}")
    in_check = entry["in_check"]
    if not isinstance(in_check, bool):
        raise _fail(f"{where}: in_check must be true or false")
    if in_check and ci_job == NO_CI_JOB:
        raise _fail(f"{where}: in_check gate needs a ci_job, make check must equal CI")
    fork = _text(entry, where, "fork")
    if fork not in FORK_MODES:
        raise _fail(f"{where}: fork {fork!r} must be one of {', '.join(FORK_MODES)}")
    return Gate(
        name=name,
        make=_name(entry, where, "make"),
        ci_job=ci_job,
        in_check=in_check,
        fork=fork,
        tool=_text(entry, where, "tool"),
        description=_text(entry, where, "description"),
    )


def _parse_target(raw: object, index: int) -> Target:
    entry = _keys(raw, TARGET_KEYS, f"target[{index}]")
    name = _name(entry, f"target[{index}]", "name")
    return Target(name=name, description=_text(entry, f"target {name}", "description"))


def _array(data: dict[str, object], key: str) -> list[object]:
    value = data.get(key, [])
    if not isinstance(value, list):
        raise _fail(f"{key} must be an array of tables")
    return value


def load_config(path: Path) -> Config:
    """Read and validate gates.toml; raise ConfigError with the reason."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise _fail(f"unreadable: {exc}") from exc
    unknown = sorted(set(data) - {"gate", "target"})
    if unknown:
        raise _fail(f"unknown key {', '.join(unknown)}")
    gates = tuple(_parse_gate(raw, i) for i, raw in enumerate(_array(data, "gate")))
    targets = tuple(_parse_target(raw, i) for i, raw in enumerate(_array(data, "target")))
    if not gates:
        raise _fail("no [[gate]] entry")
    seen: set[str] = set()
    for name in (
        [g.name for g in gates]
        + [g.make for g in gates if g.make != g.name]
        + [t.name for t in targets]
    ):
        if name in seen:
            raise _fail(f"duplicate name or make target {name!r}")
        seen.add(name)
    return Config(gates=gates, targets=targets)


def makefile_targets(text: str) -> dict[str, int]:
    """Explicit targets of a Makefile with the line of their first rule.

    Variable assignments, recipe lines, special targets (`.PHONY`) and
    pattern rules are not targets in this sense.
    """
    targets: dict[str, int] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        if not line or line.startswith(("\t", "#")) or ASSIGNMENT.match(line):
            continue
        match = RULE.match(line)
        if not match:
            continue
        for name in match.group(1).split():
            if name.startswith(".") or "%" in name or "$" in name:
                continue
            targets.setdefault(name, number)
    return targets


def _entry_line(gates_text: str, name: str) -> int:
    pattern = re.compile(rf'^\s*name\s*=\s*"{re.escape(name)}"')
    for number, line in enumerate(gates_text.splitlines(), start=1):
        if pattern.match(line):
            return number
    return 1


def render_doc(config: Config) -> str:
    """The text of docs/quality/gates.md."""

    def cell(value: str) -> str:
        return value.replace("|", "\\|")

    lines = [
        "<!--",
        "SPDX-License-Identifier: Apache-2.0",
        "SPDX-FileCopyrightText: The Guildwork Authors",
        "-->",
        "",
        "# Quality gates",
        "",
        f"Generated from `{GATES_PATH.as_posix()}` by `python3 tools/ci/gates.py doc --write`;"
        " do not edit by hand. `make check` builds every gate marked yes in the column"
        " `make check`, in this order, and stops at the first failure. The group targets"
        " `check-ts`, `check-tools` and `check-security` build the gates of `make check`"
        " that run in that CI job. Fork PR: `same` runs unchanged for pull requests from"
        " forks, `generic` runs with the generic rules only, `skip` does not run.",
        "",
        "## Gates",
        "",
        "| Gate | Make target | CI job | `make check` | Fork PR | Tool | Description |",
        "|---|---|---|---|---|---|---|",
    ]
    lines += [
        f"| `{g.name}` | `make {g.make}` | {g.ci_job} | {'yes' if g.in_check else 'no'} "
        f"| {g.fork} | {cell(g.tool)} | {cell(g.description)} |"
        for g in config.gates
    ]
    lines += ["", "## Other targets", "", "| Target | Description |", "|---|---|"]
    lines += [f"| `make {t.name}` | {cell(t.description)} |" for t in config.targets]
    return "\n".join(lines) + "\n"


def check(root: Path, config: Config) -> list[str]:
    """Findings of gates.toml against the Makefile and docs/quality/gates.md."""
    try:
        makefile = (root / MAKEFILE_PATH).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"unreadable: {exc}", MAKEFILE_PATH) from exc
    gates_text = (root / GATES_PATH).read_text(encoding="utf-8")
    targets = makefile_targets(makefile)
    findings: list[str] = []

    named: list[tuple[str, str, str]] = [("gate", g.name, g.make) for g in config.gates]
    named += [("target", t.name, t.name) for t in config.targets]
    for kind, name, make in named:
        if make not in targets:
            line = _entry_line(gates_text, name)
            findings.append(
                f"{GATES_PATH.as_posix()}:{line}:1 missing-target {kind} '{name}' has no"
                f" rule for target '{make}' in {MAKEFILE_PATH.as_posix()}"
            )

    documented = {make for _, _, make in named}
    for name, line in targets.items():
        if name not in documented:
            findings.append(
                f"{MAKEFILE_PATH.as_posix()}:{line}:1 undocumented-target '{name}' has no"
                f" entry in {GATES_PATH.as_posix()}"
            )

    try:
        current = (root / DOC_PATH).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        current = None
    if current != render_doc(config):
        findings.append(
            f"{DOC_PATH.as_posix()}:1:1 doc-outdated differs from {GATES_PATH.as_posix()};"
            " run 'python3 tools/ci/gates.py doc --write'"
        )
    return findings + check_ci(root, config)


def load_ci(root: Path) -> check_workflows.Mapping:
    """Parse ci.yml; raise FileNotFoundError or ConfigError."""
    try:
        text = (root / CI_PATH).read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"unreadable: {exc}", CI_PATH) from exc
    try:
        doc = check_workflows.parse_yaml(text)
    except check_workflows.YamlError as exc:
        raise ConfigError(f"line {exc.line}: {exc}", CI_PATH) from exc
    if not isinstance(doc, check_workflows.Mapping) or not isinstance(
        doc.get("jobs"), check_workflows.Mapping
    ):
        raise ConfigError("a workflow with a mapping `jobs` is expected", CI_PATH)
    return doc


def _jobs(
    doc: check_workflows.Mapping,
) -> list[tuple[check_workflows.Scalar, check_workflows.Node]]:
    jobs = doc.get("jobs")
    return list(jobs.items) if isinstance(jobs, check_workflows.Mapping) else []


def _make_targets(script: str) -> list[str]:
    """The make targets that a run script calls."""
    targets: list[str] = []
    for match in MAKE_CALL.finditer(script):
        for word in match.group(1).split():
            if not word.startswith("-") and "=" not in word and not word.startswith(("$", '"')):
                targets.append(word)
    return targets


def _job_calls(job: check_workflows.Node) -> dict[str, int]:
    """Make targets called in the run steps of a job, with the line of the step."""
    calls: dict[str, int] = {}
    steps = job.get("steps") if isinstance(job, check_workflows.Mapping) else None
    if not isinstance(steps, check_workflows.Seq):
        return calls
    for step in steps.items:
        run = step.get("run") if isinstance(step, check_workflows.Mapping) else None
        if isinstance(run, check_workflows.Scalar):
            for target in _make_targets(run.value):
                calls.setdefault(target, run.line)
    return calls


def ci_calls(doc: check_workflows.Mapping) -> dict[str, set[str]]:
    """The make targets each job of ci.yml calls."""
    return {key.value: set(_job_calls(job)) for key, job in _jobs(doc)}


def check_ci(root: Path, config: Config) -> list[str]:
    """Findings of gates.toml against .github/workflows/ci.yml."""
    where = CI_PATH.as_posix()
    try:
        doc = load_ci(root)
    except FileNotFoundError:
        return [f"{where}:1:1 ci-missing {where} does not exist; it must run every gate"]
    jobs = dict((key.value, (key, job)) for key, job in _jobs(doc))
    findings: list[str] = []
    gate_jobs = {g.make: g.ci_job for g in config.gates if g.ci_job != NO_CI_JOB}
    generic = {g.make for g in config.gates if g.fork == FORK_GENERIC}

    for name, (_, job) in jobs.items():
        for target, line in _job_calls(job).items():
            group = target.removeprefix(GROUP_PREFIX) if target.startswith(GROUP_PREFIX) else None
            expected = group if group in CI_JOBS else gate_jobs.get(target)
            if expected is None:
                continue
            allowed = {expected}
            if target in generic:
                allowed.add(expected + FORK_JOB_SUFFIX)
            if name not in allowed:
                findings.append(
                    f"{where}:{line}:1 ci-wrong-job '{target}' runs in job '{name}',"
                    f" its ci_job is '{expected}'"
                )

    for gate in select(config, None):
        key_job = jobs.get(gate.ci_job)
        called = set(_job_calls(key_job[1])) if key_job else set()
        if not {gate.make, GROUP_PREFIX + gate.ci_job} & called:
            line = key_job[0].line if key_job else 1
            findings.append(
                f"{where}:{line}:1 ci-missing-gate gate '{gate.name}' of ci_job '{gate.ci_job}'"
                f" is not called in job '{gate.ci_job}' (make {gate.make} or"
                f" make {GROUP_PREFIX}{gate.ci_job})"
            )
        if gate.fork == FORK_GENERIC:
            fork_job = gate.ci_job + FORK_JOB_SUFFIX
            key_fork = jobs.get(fork_job)
            if key_fork is None or gate.make not in _job_calls(key_fork[1]):
                findings.append(
                    f"{where}:{key_fork[0].line if key_fork else 1}:1 ci-missing-fork-gate gate"
                    f" '{gate.name}' with fork = generic is not called in job '{fork_job}'"
                    f" (make {gate.make} with the generic rules only)"
                )

    if CI_OK_JOB not in jobs:
        findings.append(f"{where}:1:1 ci-ok-missing no job '{CI_OK_JOB}', the required check")
        return findings
    key, ci_ok = jobs[CI_OK_JOB]
    needs = ci_ok.get("needs") if isinstance(ci_ok, check_workflows.Mapping) else None
    needed = {
        item.value
        for item in (needs.items if isinstance(needs, check_workflows.Seq) else [needs])
        if isinstance(item, check_workflows.Scalar)
    }
    others = set(jobs) - {CI_OK_JOB}
    if needed != others:
        findings.append(
            f"{where}:{key.line}:1 ci-ok-needs needs {sorted(needed)}, every other job is"
            f" {sorted(others)}"
        )
    condition = ci_ok.get("if") if isinstance(ci_ok, check_workflows.Mapping) else None
    if not isinstance(condition, check_workflows.Scalar) or "always()" not in condition.value:
        findings.append(
            f"{where}:{key.line}:1 ci-ok-always '{CI_OK_JOB}' needs `if: always()`; a skipped"
            " required check counts as passed"
        )
    return findings


def print_help(config: Config) -> None:
    entries = config.entries()
    width = max(len(name) for name, _ in entries)
    print(f"Make targets (descriptions from {GATES_PATH.as_posix()}):")
    for name, description in entries:
        print(f"  {name.ljust(width)}  {description}")


def select(config: Config, job: str | None) -> list[Gate]:
    """The gates of make check, optionally only those of one CI job."""
    return [g for g in config.gates if g.in_check and (job is None or g.ci_job == job)]


def _gate_suite(gate: Gate, outcome: str, message: str, seconds: float) -> ET.Element:
    """A test suite with the one testcase `gates::<name>` of a gate."""
    suite = ET.Element("testsuite", {"name": gate.name})
    case = ET.SubElement(
        suite, "testcase", {"classname": "gates", "name": gate.name, "time": f"{seconds:.3f}"}
    )
    if outcome != "passed":
        ET.SubElement(case, outcome, {"message": message})
    return suite


def _report_suites(path: Path) -> list[ET.Element] | None:
    """The test suites of a gate's own JUnit report; None if missing or unreadable."""
    try:
        root = ET.parse(path).getroot()  # noqa: S314 (written by our own tools in this run)
    except (OSError, ET.ParseError):
        return None
    if root.tag == "testsuite":
        return [root]
    if root.tag == "testsuites":
        return list(root.iter("testsuite"))
    return None


def _has_failure(suites: Iterable[ET.Element]) -> bool:
    return any(
        case.find("failure") is not None or case.find("error") is not None
        for suite in suites
        for case in suite.iter("testcase")
    )


def write_junit(path: Path, suites: Sequence[ET.Element]) -> None:
    """Write the suites as one JUnit file with totals on the root."""
    root = ET.Element("testsuites")
    cases = [case for suite in suites for case in suite.iter("testcase")]
    counts = {
        "tests": len(cases),
        "failures": sum(case.find("failure") is not None for case in cases),
        "errors": sum(case.find("error") is not None for case in cases),
        "skipped": sum(case.find("skipped") is not None for case in cases),
    }
    for key, value in counts.items():
        root.set(key, str(value))
    root.extend(suites)
    ET.indent(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def run(gates: Iterable[Gate], make: Sequence[str], cwd: Path, junit: Path | None = None) -> int:
    """Build each gate with make; stop at the first failure."""
    selected = list(gates)
    passed = 0
    failed: Gate | None = None
    suites: list[ET.Element] = []
    for gate in selected:
        if failed is not None:
            suites.append(_gate_suite(gate, "skipped", "not run: an earlier gate failed", 0.0))
            continue
        report = cwd / JUNIT_DIR / f"{gate.make}.xml"
        report.unlink(missing_ok=True)
        print(f"gates.start gate={gate.name} target={gate.make}", flush=True)
        started = time.monotonic()
        # make comes from the Makefile ($(MAKE)) or the command line, never from file contents.
        result = subprocess.run([*make, gate.make], cwd=cwd, check=False)  # noqa: S603
        seconds = time.monotonic() - started
        own = _report_suites(report)
        if own is not None:
            suites.extend(own)
        if result.returncode != 0:
            failed = gate
            if own is None or not _has_failure(own):
                suites.append(_gate_suite(gate, "failure", f"exit {result.returncode}", seconds))
            print(
                f"gates.failed gate={gate.name} exit={result.returncode} seconds={seconds:.1f}",
                file=sys.stderr,
                flush=True,
            )
            continue
        if own is None:
            suites.append(_gate_suite(gate, "passed", "", seconds))
        passed += 1
        print(f"gates.passed gate={gate.name} seconds={seconds:.1f}", flush=True)
    skipped = len(selected) - passed - (1 if failed else 0)
    if junit is not None:
        write_junit(junit if junit.is_absolute() else cwd / junit, suites)
    print(f"gates.summary passed={passed} failed={1 if failed else 0} skipped={skipped}")
    return EXIT_FAILED if failed else EXIT_OK


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check, document and run the quality gates.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="check Makefile and docs against gates.toml")
    doc = commands.add_parser("doc", help="print or write docs/quality/gates.md")
    doc.add_argument("--write", action="store_true", help="write the file instead of printing")
    commands.add_parser("help", help="list make targets with their descriptions")
    runner = commands.add_parser("run", help="build gates with make")
    group = runner.add_mutually_exclusive_group(required=True)
    group.add_argument("--in-check", action="store_true", help="every gate of make check")
    group.add_argument("--job", choices=CI_JOBS, help="gates of make check in this CI job")
    runner.add_argument("--make", default="make", help="make command, split like a shell")
    runner.add_argument("--junit", type=Path, help="also write a JUnit report here")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root: Path = args.root
    try:
        config = load_config(root / GATES_PATH)
        if args.command == "check":
            findings = check(root, config)
            for finding in findings:
                print(finding)
            return EXIT_FAILED if findings else EXIT_OK
    except ConfigError as exc:
        print(
            f"gates.config_invalid path={exc.path.as_posix()} reason={exc}",
            file=sys.stderr,
        )
        return EXIT_CONFIG
    if args.command == "doc":
        text = render_doc(config)
        if args.write:
            (root / DOC_PATH).write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return EXIT_OK
    if args.command == "help":
        print_help(config)
        return EXIT_OK
    gates = select(config, args.job)
    try:
        makefile = (root / MAKEFILE_PATH).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"gates.config_invalid path={MAKEFILE_PATH.as_posix()} reason={exc}", file=sys.stderr)
        return EXIT_CONFIG
    targets = makefile_targets(makefile)
    missing = [g.make for g in gates if g.make not in targets]
    if missing:
        print(
            f"gates.config_invalid path={MAKEFILE_PATH.as_posix()} reason=no rule for"
            f" {', '.join(repr(m) for m in missing)}",
            file=sys.stderr,
        )
        return EXIT_CONFIG
    return run(gates, shlex.split(args.make), root, args.junit)


if __name__ == "__main__":
    sys.exit(main())
