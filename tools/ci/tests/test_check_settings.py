# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/ci/check_settings.py.

`gh api` is replaced by a fake runner that answers each GET path with a JSON
file from tests/fixtures/settings/. The answers are derived from the response
schemas and examples of the GitHub REST API description
(github/rest-api-description, api.github.com.json, API version 2022-11-28),
filled with the expected state of the product repo:

  org.json                       GET orgs/{org}
  org-actions-permissions.json   GET orgs/{org}/actions/permissions
  actions-selected.json          GET .../actions/permissions/selected-actions (org and repo)
  actions-workflow.json          GET .../actions/permissions/workflow (org and repo)
  actions-fork-approval.json     GET .../actions/permissions/fork-pr-contributor-approval
  teams.json                     GET repos/{repo}/teams
  repo.json                      GET repos/{repo}
  actions-permissions.json       GET repos/{repo}/actions/permissions
  environments.json              GET repos/{repo}/environments
  env-denylist-secrets.json      GET repos/{repo}/environments/denylist/secrets
  env-release-secrets.json       GET repos/{repo}/environments/release/secrets
  env-release-policies.json      GET repos/{repo}/environments/release/deployment-branch-policies
  variables.json                 GET repos/{repo}/actions/variables
  pvr.json                       GET repos/{repo}/private-vulnerability-reporting
  rulesets.json                  GET repos/{repo}/rulesets
  ruleset-7.json                 GET repos/{repo}/rulesets/7
  expected.json                  the expected-state file of the settings sheet
                                 (design 00 section 3.5), without sources and evidence

No answer was recorded against a live repository: the product repo is empty
and private until its first push, so the run against it stays open.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import subprocess
import tempfile
import unittest
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from tools.ci import check_settings

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "settings"
REPO = "guildwork-dev/guildwork"
ORG = "guildwork-dev"

ANSWERS = {
    f"orgs/{ORG}": "org.json",
    f"orgs/{ORG}/actions/permissions": "org-actions-permissions.json",
    f"orgs/{ORG}/actions/permissions/selected-actions": "actions-selected.json",
    f"orgs/{ORG}/actions/permissions/workflow": "actions-workflow.json",
    f"orgs/{ORG}/actions/permissions/fork-pr-contributor-approval": "actions-fork-approval.json",
    f"repos/{REPO}/teams": "teams.json",
    f"repos/{REPO}": "repo.json",
    f"repos/{REPO}/private-vulnerability-reporting": "pvr.json",
    f"repos/{REPO}/actions/permissions": "actions-permissions.json",
    f"repos/{REPO}/actions/permissions/selected-actions": "actions-selected.json",
    f"repos/{REPO}/actions/permissions/workflow": "actions-workflow.json",
    f"repos/{REPO}/actions/permissions/fork-pr-contributor-approval": "actions-fork-approval.json",
    f"repos/{REPO}/actions/variables": "variables.json",
    f"repos/{REPO}/environments": "environments.json",
    f"repos/{REPO}/environments/denylist/secrets": "env-denylist-secrets.json",
    f"repos/{REPO}/environments/release/secrets": "env-release-secrets.json",
    f"repos/{REPO}/environments/release/deployment-branch-policies": "env-release-policies.json",
    f"repos/{REPO}/rulesets": "rulesets.json",
    f"repos/{REPO}/rulesets/7": "ruleset-7.json",
}


def load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeGh:
    """Stands in for subprocess.run; answers `gh api` GET calls from the fixtures."""

    def __init__(self) -> None:
        self.data: dict[str, Any] = {path: load(name) for path, name in ANSWERS.items()}
        self.errors: dict[str, tuple[int, str]] = {}
        self.calls: list[list[str]] = []

    def __call__(self, cmd: Sequence[str], **_: object) -> subprocess.CompletedProcess[str]:
        cmd = list(cmd)
        self.calls.append(cmd)
        path = cmd[-1].split("?", 1)[0]
        if path in self.errors:
            code, message = self.errors[path]
            return subprocess.CompletedProcess(cmd, code, json.dumps({"message": message}), "")
        if path not in self.data:
            raise AssertionError(f"unexpected request: {cmd}")
        return subprocess.CompletedProcess(cmd, 0, json.dumps(self.data[path]), "")

    def rules(self) -> list[dict[str, Any]]:
        rules: list[dict[str, Any]] = self.data[f"repos/{REPO}/rulesets/7"]["rules"]
        return rules

    def rule(self, rule_type: str) -> dict[str, Any]:
        return next(rule for rule in self.rules() if rule["type"] == rule_type)

    def environment(self, name: str) -> dict[str, Any]:
        envs = self.data[f"repos/{REPO}/environments"]["environments"]
        env: dict[str, Any] = next(env for env in envs if env["name"] == name)
        return env


RULES = "rulesets.main.rules"


class TestSettings(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.expected = load("expected.json")
        self.gh = FakeGh()

    def run_main(self, expected: Any = None, *args: str) -> tuple[int, str, str]:
        path = self.dir / "expected.json"
        text = expected if isinstance(expected, str) else json.dumps(expected or self.expected)
        path.write_text(text, encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = check_settings.main(["--expected", str(path), *args], run=self.gh)
        return code, out.getvalue(), err.getvalue()

    def findings(self, err: str) -> list[str]:
        return [
            line.split()[1].removeprefix("key=")
            for line in err.splitlines()
            if line.startswith("check_settings.finding ")
        ]

    def assert_findings(self, keys: list[str]) -> str:
        code, _, err = self.run_main()
        self.assertEqual(code, 1, err)
        self.assertEqual(self.findings(err), keys)
        self.assertIn(f"check_settings.failed findings={len(keys)}", err)
        return err

    def test_matching_settings_pass(self) -> None:
        code, out, err = self.run_main()
        self.assertEqual(code, 0, err)
        self.assertEqual(err, "")
        self.assertIn("check_settings.passed checks=", out.splitlines()[-1])
        self.assertIn(f"repo={REPO}", out.splitlines()[-1])
        for key in (
            "organization.two_factor_requirement_enabled",
            "organization.actions.permissions.sha_pinning_required",
            "teams.maintainers.repository_permission",
            "repo.squash_merge_commit_message",
            "security.secret_scanning_push_protection",
            "actions.workflow.default_workflow_permissions",
            "variables.GUILDWORK_VISIBILITY",
            "environments.release.reviewers",
            "environments.release.deployment_branch_policies",
            "rulesets.main.bypass_actors",
            f"{RULES}.required_status_checks.required_status_checks",
            f"{RULES}.deletion",
        ):
            self.assertIn(f"check_settings.checked key={key} ", out)

    def test_missing_required_check_fails(self) -> None:
        self.rules_without("required_status_checks")
        self.assert_findings([f"{RULES}.required_status_checks"])

    def rules_without(self, rule_type: str) -> None:
        self.gh.rules().remove(self.gh.rule(rule_type))

    def test_other_required_check_fails(self) -> None:
        checks = self.gh.rule("required_status_checks")["parameters"]["required_status_checks"]
        checks[0]["context"] = "build"
        err = self.assert_findings([f"{RULES}.required_status_checks.required_status_checks"])
        self.assertIn('actual=[{"context": "build", "integration_id": 15368}]', err)

    def test_check_from_another_app_fails(self) -> None:
        checks = self.gh.rule("required_status_checks")["parameters"]["required_status_checks"]
        del checks[0]["integration_id"]
        self.assert_findings([f"{RULES}.required_status_checks.required_status_checks"])

    def test_extra_merge_method_fails(self) -> None:
        self.gh.rule("pull_request")["parameters"]["allowed_merge_methods"] = ["merge", "squash"]
        self.assert_findings([f"{RULES}.pull_request.allowed_merge_methods"])

    def test_each_missing_rule_fails(self) -> None:
        for rule_type in (
            "deletion",
            "non_fast_forward",
            "required_linear_history",
            "required_signatures",
            "pull_request",
        ):
            with self.subTest(rule=rule_type):
                self.gh = FakeGh()
                self.rules_without(rule_type)
                self.assert_findings([f"{RULES}.{rule_type}"])

    def test_extra_rule_at_the_hoster_is_not_a_finding(self) -> None:
        self.gh.rules().append({"type": "creation"})
        code, _, err = self.run_main()
        self.assertEqual(code, 0, err)

    def test_bypass_actor_fails(self) -> None:
        self.gh.data[f"repos/{REPO}/rulesets/7"]["bypass_actors"] = [
            {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
        ]
        self.assert_findings(["rulesets.main.bypass_actors"])

    def test_ruleset_in_evaluate_mode_fails(self) -> None:
        self.gh.data[f"repos/{REPO}/rulesets/7"]["enforcement"] = "evaluate"
        self.assert_findings(["rulesets.main.enforcement"])

    def test_missing_ruleset_fails_without_detail_request(self) -> None:
        self.gh.data[f"repos/{REPO}/rulesets"] = []
        self.assert_findings(["rulesets.main"])
        self.assertFalse(any("rulesets/7" in call[-1] for call in self.gh.calls))

    def test_two_rulesets_with_the_same_name_are_an_error(self) -> None:
        listing = self.gh.data[f"repos/{REPO}/rulesets"]
        listing.append({**listing[0], "id": 8})
        code, _, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("check_settings.api_invalid", err)

    def test_code_owner_review_and_review_count_compared(self) -> None:
        params = self.gh.rule("pull_request")["parameters"]
        params["require_code_owner_review"] = True
        params["required_approving_review_count"] = 1
        self.assert_findings(
            [
                f"{RULES}.pull_request.required_approving_review_count",
                f"{RULES}.pull_request.require_code_owner_review",
            ]
        )

    def test_sha_pinning_off_or_unknown_fails(self) -> None:
        for value in (False, None):
            with self.subTest(value=value):
                self.gh = FakeGh()
                permissions = self.gh.data[f"repos/{REPO}/actions/permissions"]
                if value is None:
                    del permissions["sha_pinning_required"]
                else:
                    permissions["sha_pinning_required"] = value
                err = self.assert_findings(["actions.permissions.sha_pinning_required"])
                if value is None:
                    self.assertIn("expected=true actual=missing", err)

    def test_organization_settings_compared(self) -> None:
        org = self.gh.data[f"orgs/{ORG}"]
        org["two_factor_requirement_enabled"] = False
        del org["default_repository_permission"]
        self.gh.data[f"orgs/{ORG}/actions/permissions/workflow"] = {
            "default_workflow_permissions": "write",
            "can_approve_pull_request_reviews": False,
        }
        self.assert_findings(
            [
                "organization.two_factor_requirement_enabled",
                "organization.default_repository_permission",
                "organization.actions.workflow.default_workflow_permissions",
            ]
        )

    def test_selected_actions_compared_as_set(self) -> None:
        selected = self.gh.data[f"repos/{REPO}/actions/permissions/selected-actions"]
        selected["patterns_allowed"] = ["ossf/scorecard-action@*", "some/action@*"]
        self.assert_findings(["actions.selected_actions.patterns_allowed"])

    def test_team_compared(self) -> None:
        self.gh.data[f"repos/{REPO}/teams"][0]["permission"] = "admin"
        self.assert_findings(["teams.maintainers.repository_permission"])

    def test_missing_team_fails(self) -> None:
        self.gh.data[f"repos/{REPO}/teams"] = []
        self.assert_findings(["teams.maintainers"])

    def test_repo_merge_settings_compared(self) -> None:
        repo = self.gh.data[f"repos/{REPO}"]
        repo["allow_merge_commit"] = True
        repo["squash_merge_commit_message"] = "PR_BODY"
        self.assert_findings(["repo.allow_merge_commit", "repo.squash_merge_commit_message"])

    def test_missing_environment_fails(self) -> None:
        envs = self.gh.data[f"repos/{REPO}/environments"]
        envs["environments"] = [e for e in envs["environments"] if e["name"] != "release"]
        envs["total_count"] = 1
        self.assert_findings(["environments.release"])
        self.assertFalse(any("release/" in call[-1] for call in self.gh.calls))

    def test_denylist_secret_names_compared(self) -> None:
        secrets = self.gh.data[f"repos/{REPO}/environments/denylist/secrets"]
        secrets["secrets"] = secrets["secrets"][:1]
        secrets["total_count"] = 1
        err = self.assert_findings(["environments.denylist.secrets"])
        self.assertIn('expected=["ALLOW_AUTHORS", "DENYLIST"] actual=["ALLOW_AUTHORS"]', err)

    def test_reviewer_on_denylist_fails(self) -> None:
        reviewers = self.gh.environment("release")["protection_rules"][0]
        self.gh.environment("denylist")["protection_rules"] = [copy.deepcopy(reviewers)]
        self.assert_findings(["environments.denylist.reviewers"])

    def test_release_without_reviewer_fails(self) -> None:
        self.gh.environment("release")["protection_rules"] = [{"id": 1, "type": "branch_policy"}]
        err = self.assert_findings(["environments.release.reviewers"])
        self.assertIn("actual=[]", err)

    def test_wait_timer_and_self_review_compared(self) -> None:
        rules = self.gh.environment("release")["protection_rules"]
        rules[0]["prevent_self_review"] = True
        rules.append({"id": 2, "type": "wait_timer", "wait_timer": 30})
        self.assert_findings(
            ["environments.release.prevent_self_review", "environments.release.wait_timer"]
        )

    def test_release_tag_policies_compared(self) -> None:
        path = f"repos/{REPO}/environments/release/deployment-branch-policies"
        policies = self.gh.data[path]["branch_policies"]
        cases: list[tuple[str, Any]] = [
            ("pattern", [{**policies[0], "name": "*"}]),
            ("branch type", [{**policies[0], "type": "branch"}]),
            ("extra branch", [*policies, {"id": 2, "name": "main", "type": "branch"}]),
        ]
        for label, value in cases:
            with self.subTest(case=label):
                self.gh = FakeGh()
                self.gh.data[path]["branch_policies"] = value
                self.gh.data[path]["total_count"] = len(value)
                self.assert_findings(["environments.release.deployment_branch_policies"])

    def test_release_open_to_all_branches_fails(self) -> None:
        self.gh.environment("release")["deployment_branch_policy"] = None
        self.assert_findings(
            [
                "environments.release.deployment_branch_policy",
                "environments.release.deployment_branch_policies",
            ]
        )
        self.assertFalse(any("deployment-branch-policies" in call[-1] for call in self.gh.calls))

    def test_branch_rule_on_denylist_fails(self) -> None:
        self.gh.environment("denylist")["deployment_branch_policy"] = {
            "protected_branches": True,
            "custom_branch_policies": False,
        }
        self.assert_findings(["environments.denylist.deployment_branch_policy"])

    def test_variable_compared_by_value(self) -> None:
        for value in ("private", None):
            with self.subTest(value=value):
                self.gh = FakeGh()
                variables = self.gh.data[f"repos/{REPO}/actions/variables"]
                if value is None:
                    variables["variables"] = []
                    variables["total_count"] = 0
                else:
                    variables["variables"][0]["value"] = value
                self.assert_findings(["variables.GUILDWORK_VISIBILITY"])

    def test_security_settings_compared(self) -> None:
        analysis = self.gh.data[f"repos/{REPO}"]["security_and_analysis"]
        analysis["secret_scanning_push_protection"]["status"] = "disabled"
        del analysis["secret_scanning"]
        self.gh.data[f"repos/{REPO}/private-vulnerability-reporting"]["enabled"] = False
        self.assert_findings(
            [
                "security.secret_scanning",
                "security.secret_scanning_push_protection",
                "security.private_vulnerability_reporting",
            ]
        )

    def test_hidden_security_settings_are_an_error(self) -> None:
        del self.gh.data[f"repos/{REPO}"]["security_and_analysis"]
        code, _, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("check_settings.api_invalid", err)
        self.assertIn("admin rights", err)

    def test_only_get_requests_through_gh_api(self) -> None:
        self.run_main()
        self.assertEqual(
            sorted({call[-1].split("?", 1)[0] for call in self.gh.calls}), sorted(ANSWERS)
        )
        for call in self.gh.calls:
            self.assertEqual(call[:4], ["gh", "api", "--method", "GET"])
            for flag in ("-f", "-F", "--field", "--raw-field", "--input"):
                self.assertNotIn(flag, call)

    def test_only_named_sections_are_read(self) -> None:
        for section in ("organization", "teams", "actions", "environments", "rulesets"):
            self.expected[section] = {}
        self.expected["security"] = {"private_vulnerability_reporting": True}
        code, _, err = self.run_main()
        self.assertEqual(code, 0, err)
        self.assertEqual(
            sorted({call[-1].split("?", 1)[0] for call in self.gh.calls}),
            sorted(
                [
                    f"repos/{REPO}",
                    f"repos/{REPO}/actions/variables",
                    f"repos/{REPO}/private-vulnerability-reporting",
                ]
            ),
        )

    def test_repo_argument_overrides_the_file(self) -> None:
        other = "someone/fork"
        self.gh.errors["orgs/someone"] = (1, "Not Found")
        code, _, err = self.run_main(None, "--repo", other)
        self.assertEqual(code, 2)
        self.assertIn("check_settings.api_error path=orgs/someone", err)

    def test_api_error_exits_2(self) -> None:
        self.gh.errors[f"repos/{REPO}/actions/permissions"] = (1, "Not Found")
        code, _, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("check_settings.api_error path=repos/guildwork-dev/guildwork/actions/", err)

    def test_missing_gh_exits_2(self) -> None:
        def no_gh(cmd: Sequence[str], **_: object) -> subprocess.CompletedProcess[str]:
            raise FileNotFoundError(2, "No such file or directory", "gh")

        self.gh = no_gh  # type: ignore[assignment]
        code, _, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("check_settings.api_error path=orgs/guildwork-dev gh not runnable", err)

    def test_more_pages_than_read_is_an_error(self) -> None:
        self.gh.data[f"repos/{REPO}/actions/variables"]["total_count"] = 31
        code, _, err = self.run_main()
        self.assertEqual(code, 2)
        self.assertIn("check_settings.api_invalid", err)

    def test_invalid_expected_file_exits_2(self) -> None:
        unknown = copy.deepcopy(self.expected)
        unknown["ruleset_main"] = {}
        missing = copy.deepcopy(self.expected)
        del missing["security"]
        version = copy.deepcopy(self.expected)
        version["version"] = 2
        sub = copy.deepcopy(self.expected)
        sub["actions"]["artifacts"] = {}
        not_object = copy.deepcopy(self.expected)
        not_object["environments"]["release"] = []
        no_repo = copy.deepcopy(self.expected)
        del no_repo["repository"]
        for label, value in (
            ("unknown section", unknown),
            ("missing section", missing),
            ("unknown version", version),
            ("unknown actions part", sub),
            ("environment not an object", not_object),
            ("no repository", no_repo),
            ("not json", "{"),
        ):
            with self.subTest(case=label):
                self.gh = FakeGh()
                code, _, err = self.run_main(value)
                self.assertEqual(code, 2)
                self.assertIn("check_settings.expected_invalid", err)
                self.assertEqual(self.gh.calls, [])

    def test_metadata_keys_are_allowed(self) -> None:
        self.expected["sources"] = {"x": {"url": "https://docs.github.com/", "retrieved": "d"}}
        self.expected["evidence"] = {"repo.visibility": {"sources": ["x"]}}
        code, _, err = self.run_main()
        self.assertEqual(code, 0, err)


if __name__ == "__main__":
    unittest.main()
