#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Run the rule tests of the own Opengrep rules (part of `make opengrep`).

Layout:

  .opengrep/rules/<rule-id>.yaml       one rule per file, the id equals the file name
  .opengrep/tests/<rule-id>/bad_*.ts   cases the rule must report: a comment
                                       `ruleid: <rule-id>` on the line before
  .opengrep/tests/<rule-id>/good_*.ts  cases the rule must not report (`ok: <rule-id>`)
  .opengrep/tests/<rule-id>/paths/**   cases that depend on the file's path; the
                                       path below paths/ is the repository path

Every rule needs at least one bad and one good file; a bad file has at least
one `ruleid:` annotation of its rule, a good file none. The bad and good files
run through the engine's test mode, `opengrep test`, once per rule (with
several rules at once each rule also checks the annotations of the others).
The test mode ignores the `paths:` filter of a rule, so the path cases are
copied into a scratch directory and scanned with `opengrep scan --json`; every
finding must sit on a line marked by `ruleid:` and every such line must have a
finding. The scratch directory has an empty `.semgrepignore`, which replaces
the engine's built-in ignore list (that list skips test/ and tests/).

Standard library only (FE-004).

Exit codes:
  0  every rule test passed
  1  a rule test failed: `opengrep_test.failed rule=<id>` with the engine output,
     and `path:line:col rule-id message` for a path case
  2  configuration error on stderr: `opengrep_test.config_invalid path=<path>
     reason=<reason>`, `opengrep_test.binary_missing path=<path>` or
     `opengrep_test.engine_error rule=<id> exit=<code>`
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_CONFIG = 2

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_DIR = Path(".opengrep/rules")
TESTS_DIR = Path(".opengrep/tests")
PATHS_DIR = "paths"
DEFAULT_OPENGREP = REPO_ROOT / ".tools" / "bin" / "opengrep"

# Exit codes of `opengrep test`: 0 passed, 1 a test failed; others are errors.
ENGINE_TEST_FAILED = 1

RULE_ID_LINE = re.compile(r"^\s*-\s*id:\s*(\S+)\s*$", re.MULTILINE)
ANNOTATION = re.compile(r"\b(ruleid|ok):\s*([\w-]+)")
SCAN_FLAGS = ("--json", "--quiet", "--disable-version-check", "--no-rewrite-rule-ids")
# The scratch copy of the path cases: no file is skipped by an ignore list.
SCRATCH_IGNORE = "# Nothing is ignored in the scratch copy of the path cases.\n"


class ConfigError(Exception):
    def __init__(self, path: Path | str, reason: str) -> None:
        super().__init__(reason)
        self.path = Path(path).as_posix()


class EngineError(Exception):
    def __init__(self, rule_id: str, code: int, output: str) -> None:
        super().__init__(output)
        self.rule_id = rule_id
        self.code = code


@dataclass(frozen=True)
class RuleTests:
    rule_id: str
    rule: Path
    bad: list[Path]
    good: list[Path]
    paths: Path | None


def _expected_lines(path: Path, rule_id: str) -> set[int]:
    """Lines that must carry a finding of rule_id.

    A `ruleid:` annotation in a line comment marks the next line; after code it
    marks its own line.
    """
    expected: set[int] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if ("ruleid", rule_id) in ANNOTATION.findall(line):
            expected.add(number + 1 if line.lstrip().startswith("//") else number)
    return expected


def _has_ruleid(path: Path, rule_id: str | None = None) -> bool:
    found = ANNOTATION.findall(path.read_text(encoding="utf-8"))
    return any(kind == "ruleid" and (rule_id is None or rid == rule_id) for kind, rid in found)


def discover(root: Path) -> list[RuleTests]:
    rules_dir, tests_dir = root / RULES_DIR, root / TESTS_DIR
    if not rules_dir.is_dir():
        raise ConfigError(RULES_DIR, "directory missing")
    rule_files = sorted(rules_dir.glob("*.yaml"))
    if not rule_files:
        raise ConfigError(RULES_DIR, "no rule files (*.yaml)")
    found: list[RuleTests] = []
    for rule in rule_files:
        rel = rule.relative_to(root)
        rule_id = rule.stem
        ids = RULE_ID_LINE.findall(rule.read_text(encoding="utf-8"))
        if ids != [rule_id]:
            raise ConfigError(rel, f"expected exactly one rule with id {rule_id}, found {ids}")
        case_dir = tests_dir / rule_id
        bad = sorted(case_dir.glob("bad_*.ts"))
        good = sorted(case_dir.glob("good_*.ts"))
        if not bad or not good:
            raise ConfigError(
                case_dir.relative_to(root), f"rule {rule_id} needs bad_*.ts and good_*.ts files"
            )
        for path in bad:
            if not _has_ruleid(path, rule_id):
                raise ConfigError(path.relative_to(root), f"no annotation 'ruleid: {rule_id}'")
        for path in good:
            if _has_ruleid(path):
                raise ConfigError(path.relative_to(root), "a good case has a ruleid annotation")
        paths = case_dir / PATHS_DIR
        found.append(RuleTests(rule_id, rule, bad, good, paths if paths.is_dir() else None))
    known = {r.rule_id for r in found}
    if tests_dir.is_dir():
        for case_dir in sorted(p for p in tests_dir.iterdir() if p.is_dir()):
            if case_dir.name not in known:
                raise ConfigError(case_dir.relative_to(root), "tests without a rule file")
    return found


def _run(cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    # The command is the pinned binary and paths of this repository, never file contents.
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)  # noqa: S603


def run_test_mode(opengrep: Path, root: Path, tests: RuleTests) -> str | None:
    """None if the bad and good cases pass, else the engine output."""
    files = [str(p.relative_to(root)) for p in tests.bad + tests.good]
    result = _run(
        [str(opengrep), "test", "--config", str(tests.rule.relative_to(root)), *files], root
    )
    output = (result.stdout + result.stderr).strip()
    if result.returncode == 0:
        return None
    if result.returncode == ENGINE_TEST_FAILED:
        return output
    raise EngineError(tests.rule_id, result.returncode, output)


def run_path_cases(opengrep: Path, root: Path, tests: RuleTests, cases: Path) -> list[str]:
    """Findings `path:line:col rule-id message` for each mismatch of the path cases."""
    with tempfile.TemporaryDirectory(prefix="opengrep-paths-") as tmp:
        scratch = Path(tmp) / "repo"
        shutil.copytree(cases, scratch)
        (scratch / ".semgrepignore").write_text(SCRATCH_IGNORE, encoding="utf-8")
        result = _run(
            [str(opengrep), "scan", "--config", str(tests.rule), *SCAN_FLAGS, "."], scratch
        )
        try:
            report = json.loads(result.stdout)
        except json.JSONDecodeError:
            report = None
        if result.returncode != 0 or not isinstance(report, dict) or report.get("errors"):
            raise EngineError(
                tests.rule_id, result.returncode, (result.stdout + result.stderr).strip()
            )
        reported: dict[str, set[int]] = {}
        for item in report.get("results", []):
            if item.get("check_id") == tests.rule_id:
                reported.setdefault(item["path"], set()).add(int(item["start"]["line"]))
        findings: list[str] = []
        shown = cases.relative_to(root).as_posix()
        for case in sorted(p for p in scratch.rglob("*.ts") if p.is_file()):
            rel = case.relative_to(scratch).as_posix()
            expected = _expected_lines(case, tests.rule_id)
            got = reported.pop(rel, set())
            for line in sorted(expected - got):
                findings.append(f"{shown}/{rel}:{line}:1 {tests.rule_id} missing finding")
            for line in sorted(got - expected):
                findings.append(f"{shown}/{rel}:{line}:1 {tests.rule_id} unexpected finding")
        for rel, lines in sorted(reported.items()):
            for line in sorted(lines):
                findings.append(f"{shown}/{rel}:{line}:1 {tests.rule_id} unexpected finding")
        return findings


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    parser.add_argument("--opengrep", type=Path, default=DEFAULT_OPENGREP, help="engine binary")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root: Path = args.root.resolve()
    opengrep: Path = args.opengrep.resolve()
    if not opengrep.is_file():
        print(f"opengrep_test.binary_missing path={opengrep} hint=make bootstrap", file=sys.stderr)
        return EXIT_CONFIG
    try:
        all_tests = discover(root)
        failed = False
        for tests in all_tests:
            output = run_test_mode(opengrep, root, tests)
            path_findings: list[str] = []
            cases = len(tests.bad) + len(tests.good)
            if tests.paths is not None:
                path_findings = run_path_cases(opengrep, root, tests, tests.paths)
                cases += sum(1 for p in tests.paths.rglob("*.ts") if p.is_file())
            if output is None and not path_findings:
                print(f"opengrep_test.passed rule={tests.rule_id} files={cases}")
                continue
            failed = True
            print(f"opengrep_test.failed rule={tests.rule_id}")
            if output is not None:
                print(output)
            for finding in path_findings:
                print(finding)
    except ConfigError as exc:
        print(f"opengrep_test.config_invalid path={exc.path} reason={exc}", file=sys.stderr)
        return EXIT_CONFIG
    except EngineError as exc:
        print(f"opengrep_test.engine_error rule={exc.rule_id} exit={exc.code}", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return EXIT_CONFIG
    return EXIT_FINDINGS if failed else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
