# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/ci/check_workflows.py.

Fixture workflows live in tools/ci/tests/fixtures/workflows/<case>/ with the
policy fixtures/workflows/policy.toml. The case `clean` follows every rule;
each other case named after a rule id breaks exactly that rule (and, where
noted in EXTRA, a rule that the same violation necessarily also breaks).
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.ci import check_workflows

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path("tools/ci/tests/fixtures/workflows")
POLICY = FIXTURES / "policy.toml"

# Rules that a fixture also breaks because of the same violation.
EXTRA: dict[str, set[str]] = {"no-actions-write": {"job-permissions"}}


def run(*args: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = check_workflows.main(list(args))
    return code, out.getvalue(), err.getvalue()


def run_case(case: str, *args: str) -> tuple[int, str, str]:
    return run(
        "--root",
        str(REPO_ROOT),
        "--policy",
        POLICY.as_posix(),
        "--dir",
        (FIXTURES / case).as_posix(),
        *args,
    )


def rule_ids(out: str) -> set[str]:
    return {line.split()[1] for line in out.splitlines() if line.strip()}


class TestPolicy(unittest.TestCase):
    def assert_flags(self, rule: str) -> str:
        code, out, err = run_case(rule)
        self.assertEqual(code, 1, msg=out + err)
        self.assertEqual(rule_ids(out), {rule} | EXTRA.get(rule, set()), msg=out)
        for line in out.splitlines():
            location = line.split()[0]
            path, lineno, col = location.rsplit(":", 2)
            self.assertTrue(path.startswith(f"{FIXTURES.as_posix()}/{rule}/"), msg=line)
            self.assertGreater(int(lineno), 0, msg=line)
            self.assertGreater(int(col), 0, msg=line)
        return out

    def test_clean_fixture_passes(self) -> None:
        code, out, err = run_case("clean")
        self.assertEqual((code, out, err), (0, "", ""))

    def test_policy_file_missing_exits_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / ".github" / "workflows"
            shutil.copytree(REPO_ROOT / FIXTURES / "clean", target)
            code, out, err = run("--root", tmp)
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("workflows.config_invalid path=quality/ci/policy.toml", err)

    def test_repo_workflows_pass(self) -> None:
        code, out, err = run("--root", str(REPO_ROOT))
        self.assertEqual((code, out, err), (0, "", ""))

    def test_runner_label_flags_violation(self) -> None:
        out = self.assert_flags("runner-label")
        self.assertIn("ci.yml:19:14 runner-label", out)

    def test_action_pin_flags_violation(self) -> None:
        out = self.assert_flags("action-pin")
        self.assertIn("ci.yml:22:15 action-pin", out)

    def test_job_timeout_flags_violation(self) -> None:
        self.assert_flags("job-timeout")

    def test_top_permissions_flags_violation(self) -> None:
        self.assert_flags("top-permissions")

    def test_job_permissions_flags_violation(self) -> None:
        out = self.assert_flags("job-permissions")
        self.assertIn("pull-requests", out)

    def test_no_actions_write_flags_violation(self) -> None:
        self.assert_flags("no-actions-write")

    def test_no_dangerous_triggers_flags_violation(self) -> None:
        out = self.assert_flags("no-dangerous-triggers")
        self.assertIn("workflow_run", out)

    def test_push_main_only_flags_violation(self) -> None:
        out = self.assert_flags("push-main-only")
        self.assertIn("advisories.yml:", out)
        self.assertIn("ci.yml:", out)

    def test_no_expr_in_run_flags_violation(self) -> None:
        out = self.assert_flags("no-expr-in-run")
        # The line of the expression inside the block scalar, not of `run:`.
        self.assertIn("ci.yml:28:17 no-expr-in-run", out)

    def test_checkout_no_persist_flags_violation(self) -> None:
        self.assert_flags("checkout-no-persist")

    def test_secrets_need_environment_flags_violation(self) -> None:
        self.assert_flags("secrets-need-environment")

    def test_public_only_guard_flags_violation(self) -> None:
        out = self.assert_flags("public-only-guard")
        self.assertIn("GUILDWORK_VISIBILITY", out)

    def test_pr_concurrency_flags_violation(self) -> None:
        self.assert_flags("pr-concurrency")

    def test_max_jobs_flags_violation(self) -> None:
        out = self.assert_flags("max-jobs")
        self.assertIn("7", out)


class TestErrors(unittest.TestCase):
    def test_unsupported_yaml_exits_2(self) -> None:
        code, out, err = run_case("unsupported-yaml")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn(f"workflows.unparsable path={FIXTURES.as_posix()}/unsupported-yaml/", err)

    def test_runtime_errors_exit_2(self) -> None:
        # Backlog M169: deep nesting and huge numbers ended as a traceback.
        deep = "a: " + "[" * 5000 + "]" * 5000 + "\n"
        huge = CLEAN_JOB.replace("timeout-minutes: 10", "timeout-minutes: " + "9" * 5000)
        for name, text in (("deep", deep), ("huge", huge)):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "ci.yml").write_text(text, encoding="utf-8")
                code, out, err = run(
                    "--root", tmp, "--policy", str(REPO_ROOT / POLICY), "--dir", tmp
                )
                self.assertEqual((code, out), (2, ""), msg=err)
                self.assertIn("workflows.unparsable path=", err)

    def test_policy_with_actions_write_exits_2(self) -> None:
        text = (REPO_ROOT / POLICY).read_text(encoding="utf-8")
        text = text.replace('actions = "read"', 'actions = "write"')
        with tempfile.TemporaryDirectory() as tmp:
            policy = Path(tmp) / "policy.toml"
            policy.write_text(text, encoding="utf-8")
            code, _, err = run_case("clean", "--policy", str(policy))
        self.assertEqual(code, 2)
        self.assertIn("workflows.config_invalid", err)

    def test_json_report_lists_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "reports" / "workflows.json"
            code, out, _ = run_case("runner-label", "--json", str(report))
            data = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(code, 1)
        self.assertEqual(data["tool"], "check_workflows")
        self.assertEqual([f["rule"] for f in data["findings"]], ["runner-label"])
        self.assertEqual(data["findings"][0]["line"], 19)
        self.assertIn(data["findings"][0]["message"], out)

    def test_json_report_written_without_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "workflows.json"
            code, _, _ = run_case("clean", "--json", str(report))
            data = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual((code, data["findings"]), (0, []))


def check_text(text: str, name: str = "ci.yml", encoding: str = "utf-8") -> tuple[int, str]:
    """Run the checker on one workflow written to a temporary directory."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / name).write_text(text, encoding=encoding)
        code, out, _ = run("--root", str(REPO_ROOT), "--policy", POLICY.as_posix(), "--dir", tmp)
    return code, out


CLEAN_HEAD = (REPO_ROOT / FIXTURES / "runner-label" / "ci.yml").read_text(encoding="utf-8")
CLEAN_JOB = CLEAN_HEAD.replace("ubuntu-latest", "ubuntu-24.04")


class TestRuleDetails(unittest.TestCase):
    def test_secrets_context_is_case_insensitive(self) -> None:
        upper = CLEAN_JOB + "      - env:\n          A: ${{ Secrets.FOO }}\n        run: make x\n"
        token = (
            CLEAN_JOB + "      - env:\n          A: ${{ secrets.github_token }}\n        run: x\n"
        )
        self.assertEqual(rule_ids(check_text(upper)[1]), {"secrets-need-environment"})
        self.assertEqual(check_text(token), (0, ""))

    def test_byte_order_mark_does_not_hide_the_first_key(self) -> None:
        text = CLEAN_JOB.replace("on:\n  pull_request:\n", "on:\n  pull_request_target:\n", 1)
        # The workflow starts with the key `on`, right after the byte order mark.
        code, out = check_text(text[text.index("on:\n") :], encoding="utf-8-sig")
        self.assertEqual(code, 1)
        self.assertIn("no-dangerous-triggers", rule_ids(out))

    def test_cancel_in_progress_accepts_capitalized_true(self) -> None:
        self.assertEqual(check_text(CLEAN_JOB.replace(": true\n", ": True\n")), (0, ""))


STRICT_POLICY = (
    (REPO_ROOT / POLICY)
    .read_text(encoding="utf-8")
    .replace(
        "\n[job_permissions",
        '\nmake_variables = ["COMMIT_RANGE", "OSV_BASE"]\n\n[job_permissions',
        1,
    )
)


def check_strict(files: dict[str, str], *args: str) -> tuple[int, str, str]:
    """Run the checker on workflow files in a temporary directory, with a
    policy that knows the make variables COMMIT_RANGE and OSV_BASE and with
    the make targets of the repository's quality/gates.toml."""
    with tempfile.TemporaryDirectory() as tmp:
        policy = Path(tmp) / "policy.toml"
        policy.write_text(STRICT_POLICY, encoding="utf-8")
        workflows = Path(tmp) / "workflows"
        workflows.mkdir()
        for name, text in files.items():
            (workflows / name).write_text(text, encoding="utf-8")
        return run(
            "--root", str(REPO_ROOT), "--policy", str(policy), "--dir", str(workflows), *args
        )


def with_run(script: str) -> str:
    """CLEAN_JOB with one more step that runs the given block script."""
    body = "".join(f"          {line}\n" for line in script.splitlines())
    return CLEAN_JOB + "      - run: |\n" + body


class TestStrict(unittest.TestCase):
    def test_repo_workflows_pass_strict(self) -> None:
        code, out, err = run("--root", str(REPO_ROOT), "--strict")
        self.assertEqual((code, out, err), (0, "", ""))

    def test_unknown_workflow_file_fails(self) -> None:
        code, out, _ = check_strict({"ci.yml": CLEAN_JOB, "extra.yml": CLEAN_JOB}, "--strict")
        self.assertEqual(code, 1, msg=out)
        self.assertEqual(rule_ids(out), {"known-workflow"})
        self.assertIn("extra.yml:1:1 known-workflow", out)

    def test_unknown_make_target_fails(self) -> None:
        text = with_run("make check-tools\nmake no-such-target COMMIT_RANGE=x")
        code, out, _ = check_strict({"ci.yml": text}, "--strict")
        self.assertEqual(code, 1, msg=out)
        self.assertEqual(rule_ids(out), {"make-target-exists"})
        self.assertIn("no-such-target", out)
        self.assertNotIn("check-tools", out)

    def test_unknown_job_env_fails(self) -> None:
        script = (
            'export UNKNOWN_EXPORTED="$RUNNER_TEMP/x"\n'
            'make osv OSV_BASE="$base" UNKNOWN_ARG=1\n'
            'make commitlint COMMIT_RANGE="$range"'
        )
        code, out, _ = check_strict({"ci.yml": with_run(script)}, "--strict")
        self.assertEqual(code, 1, msg=out)
        self.assertEqual(rule_ids(out), {"job-env-known"})
        # Only NAME=value on the make line counts (ruling 2026-11-01): an
        # exported variable or a step env value reaches make through the
        # environment of the step, not as a make variable.
        self.assertNotIn("UNKNOWN_EXPORTED", out)
        self.assertIn("UNKNOWN_ARG", out)
        self.assertNotIn("OSV_BASE", out)
        self.assertNotIn("COMMIT_RANGE", out)

    def test_strict_rules_need_strict(self) -> None:
        text = with_run("export UNKNOWN=1\nmake no-such-target")
        code, out, err = check_strict({"ci.yml": CLEAN_JOB, "extra.yml": text})
        self.assertEqual((code, out, err), (0, "", ""))

    def test_make_variables_must_be_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            policy = Path(tmp) / "policy.toml"
            policy.write_text(STRICT_POLICY.replace('"OSV_BASE"', "1"), encoding="utf-8")
            code, _, err = run_case("clean", "--policy", str(policy))
        self.assertEqual(code, 2)
        self.assertIn("make_variables", err)


class TestYaml(unittest.TestCase):
    def test_parses_block_flow_and_quoted_values(self) -> None:
        text = (
            "a: 'it''s'\n"
            'b: "x\\ty"\n'
            "c: [1, 'two', {d: e}]\n"
            "f:\n"
            "- g: h\n"
            "  i: |\n"
            "    line one\n"
            "\n"
            "    line two\n"
            "j: plain # comment\n"
        )
        doc = check_workflows.parse_yaml(text)
        self.assertEqual(
            check_workflows.to_plain(doc),
            {
                "a": "it's",
                "b": "x\ty",
                "c": ["1", "two", {"d": "e"}],
                "f": [{"g": "h", "i": "line one\n\nline two\n"}],
                "j": "plain",
            },
        )

    def test_folds_and_chomps_block_scalars_like_yaml(self) -> None:
        # Expected values are those of a full YAML 1.1 parser for the same text.
        text = (
            "a: >\n  one\n  two\n\n   more\n  last\n"
            "b: |+\n  keep\n\n"
            "c:\n  - |-\n    item\n  - after\n"
        )
        self.assertEqual(
            check_workflows.to_plain(check_workflows.parse_yaml(text)),
            {"a": "one two\n\n more\nlast\n", "b": "keep\n\n", "c": ["item", "after"]},
        )

    def test_rejects_invalid_flow_collections(self) -> None:
        # Invalid YAML that once made the flow reader loop forever.
        for text in ("a: [x, ${{ inputs.os }}]\n", "a: [x }]\n", "a: [}\n", "a: {x: ]}\n"):
            with self.subTest(text=text), self.assertRaises(check_workflows.YamlError):
                check_workflows.parse_yaml(text)

    def test_rejects_duplicate_keys(self) -> None:
        with self.assertRaises(check_workflows.YamlError):
            check_workflows.parse_yaml("a: 1\na: 2\n")


if __name__ == "__main__":
    unittest.main()
