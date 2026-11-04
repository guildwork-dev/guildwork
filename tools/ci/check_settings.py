#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Read the repository settings back and compare them with the expected state.

Usage: check_settings.py --expected <file> [--repo <owner/name>]

The expected-state file has the form of design 00 section 3.5: "version" 1,
"repository" (owner/name, overridden by --repo), the sections organization,
teams, repo, security, actions, variables, environments and rulesets, and
optional metadata (retrieved, note, sources, evidence) that is not compared.
Field names and values are those of the GET answers of the GitHub REST API
(version 2022-11-28); only the shape is condensed. It sets nothing: every
request is a GET through `gh api`, with the credentials of the calling `gh`.

Sections and the answers they are read from ({org} is the owner of the repo):

  organization   GET orgs/{org}; its part "actions" from
                 orgs/{org}/actions/permissions (part "permissions") and its
                 subpaths selected-actions, workflow,
                 fork-pr-contributor-approval (parts "selected_actions",
                 "workflow", "fork_pr_contributor_approval")
  teams          GET repos/{repo}/teams, per slug: privacy, and
                 repository_permission from the field "permission"
  repo           GET repos/{repo}
  security       GET repos/{repo}: each field except the one below is the
                 "status" of security_and_analysis.<field> (visible with admin
                 rights only); private_vulnerability_reporting is "enabled" of
                 GET repos/{repo}/private-vulnerability-reporting
  actions        like organization.actions, under repos/{repo}/actions/permissions
  variables      GET repos/{repo}/actions/variables: name and value
  environments   GET repos/{repo}/environments, per name:
                 secrets                     names from .../{env}/secrets
                 reviewers                   of the required_reviewers rule, as
                                             {type, slug} for teams and
                                             {type, login} for users; [] without
                 prevent_self_review         of that rule; false without
                 wait_timer                  of the wait_timer rule; 0 without
                 deployment_branch_policy    as answered (null or an object)
                 deployment_branch_policies  {name, type} from
                                             .../{env}/deployment-branch-policies
                                             if custom_branch_policies is true,
                                             else []
  rulesets       GET repos/{repo}/rulesets, per name the ruleset with that name,
                 then GET repos/{repo}/rulesets/{id}; its "rules" as an object
                 of "parameters" per rule "type" ({} without parameters)

Comparison: objects are compared field by field, only for the fields the file
names (further fields, teams, environments, variables, rulesets or rules at the
hoster are not findings); an empty object only needs to be present; every other
value must be equal, lists as sets. Only the parts a section names are read.

Output: `check_settings.checked key=<key> value=<actual>` per compared value on
stdout, then `check_settings.passed checks=<n> repo=<repo>`; per deviation
`check_settings.finding key=<key> expected=<json> actual=<json>` on stderr, then
`check_settings.failed findings=<n>`.

Standard library only (FE-004).

Exit codes:
  0  every value matches
  1  at least one deviation
  2  expected-state file invalid (`check_settings.expected_invalid`), a request
     failed (`check_settings.api_error`) or an answer has an unexpected form or
     more entries than one page holds (`check_settings.api_invalid`)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import quote

EXIT_OK = 0
EXIT_DEVIATION = 1
EXIT_INVALID = 2

API_VERSION = "2022-11-28"
FORM_VERSION = 1
PAGE = 100
VARIABLES_PAGE = 30  # maximum page size of the variables endpoint

Runner = Callable[..., "subprocess.CompletedProcess[str]"]

SECTIONS = (
    "organization",
    "teams",
    "repo",
    "security",
    "actions",
    "variables",
    "environments",
    "rulesets",
)
METADATA = ("version", "repository", "retrieved", "note", "sources", "evidence")
ACTIONS_PARTS = {
    "permissions": "",
    "selected_actions": "/selected-actions",
    "workflow": "/workflow",
    "fork_pr_contributor_approval": "/fork-pr-contributor-approval",
}
PVR = "private_vulnerability_reporting"
MISSING = object()


class ExpectedError(Exception):
    """The expected-state file cannot be used."""


class ApiError(Exception):
    """A request failed or answered in an unexpected form."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


# Expected-state file


def _objects(where: str, value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ExpectedError(f"{where} is not an object")
    return value


def parse_expected(text: str) -> dict[str, Any]:
    """The expected state; raise ExpectedError."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExpectedError(f"not JSON: {exc.msg} at line {exc.lineno}") from None
    data = _objects("the file", data)
    for key in data:
        if key not in SECTIONS and key not in METADATA:
            raise ExpectedError(f"{key} is not a known section")
    if data.get("version") != FORM_VERSION:
        raise ExpectedError(f"version is not {FORM_VERSION}")
    repository = data.get("repository")
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise ExpectedError("repository is not owner/name")
    for section in SECTIONS:
        if section not in data:
            raise ExpectedError(f"section {section} is missing")
        _objects(section, data[section])
    for where, actions in (
        ("organization.actions", data["organization"].get("actions", {})),
        ("actions", data["actions"]),
    ):
        for part, value in _objects(where, actions).items():
            if part not in ACTIONS_PARTS:
                raise ExpectedError(f"{where}.{part} is not a known part")
            _objects(f"{where}.{part}", value)
    for section in ("teams", "environments", "rulesets"):
        for name, value in data[section].items():
            _objects(f"{section}.{name}", value)
    rulesets = data["rulesets"]
    for name, ruleset in rulesets.items():
        _objects(f"rulesets.{name}.rules", ruleset.get("rules", {}))
    if not all(isinstance(value, str) for value in data["variables"].values()):
        raise ExpectedError("variables is not an object of strings")
    return data


# Hoster API, GET only


class GhApi:
    """GET requests through `gh api`; nothing else is ever sent."""

    def __init__(self, repo: str, run: Runner) -> None:
        self.repo = repo
        self.org = repo.split("/", 1)[0]
        self.run = run

    def get(self, path: str, query: str = "") -> Any:
        cmd = [
            "gh",
            "api",
            "--method",
            "GET",
            "-H",
            "Accept: application/vnd.github+json",
            "-H",
            f"X-GitHub-Api-Version: {API_VERSION}",
            f"{path}?{query}" if query else path,
        ]
        try:
            result = self.run(cmd, capture_output=True, text=True, check=False)
        except OSError as exc:
            raise ApiError("api_error", f"path={path} gh not runnable: {exc}") from None
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip().splitlines()
            raise ApiError("api_error", f"path={path} {detail[0] if detail else 'no output'}")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            raise ApiError("api_invalid", f"path={path} answer is not JSON") from None

    def get_object(self, path: str) -> dict[str, Any]:
        data = self.get(path)
        if not isinstance(data, dict):
            raise ApiError("api_invalid", f"path={path} is not an object")
        return data

    def get_array(self, path: str) -> list[dict[str, Any]]:
        """Entries of a list endpoint that answers with a bare array; one page only."""
        data = self.get(path, f"per_page={PAGE}")
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            raise ApiError("api_invalid", f"path={path} is not a list of objects")
        if len(data) >= PAGE:
            raise ApiError("api_invalid", f"path={path} fills a whole page")
        return data

    def get_list(self, path: str, field: str, page: int = PAGE) -> list[dict[str, Any]]:
        """Entries of a list endpoint with total_count; one page only."""
        data = self.get(path, f"per_page={page}")
        items = data.get(field) if isinstance(data, dict) else None
        total = data.get("total_count") if isinstance(data, dict) else None
        if not isinstance(items, list) or not isinstance(total, int):
            raise ApiError("api_invalid", f"path={path} has no {field}")
        if total > len(items):
            raise ApiError(
                "api_invalid", f"path={path} has {total} entries, one page holds {len(items)}"
            )
        return [item for item in items if isinstance(item, dict)]


def read_actions(api: GhApi, base: str, wanted: Mapping[str, Any]) -> dict[str, Any]:
    return {part: api.get_object(f"{base}{ACTIONS_PARTS[part]}") for part in wanted}


def read_organization(api: GhApi, wanted: Mapping[str, Any]) -> dict[str, Any]:
    observed: dict[str, Any] = {}
    if any(key != "actions" for key in wanted):
        observed = api.get_object(f"orgs/{api.org}")
    if "actions" in wanted:
        base = f"orgs/{api.org}/actions/permissions"
        observed = {**observed, "actions": read_actions(api, base, wanted["actions"])}
    return observed


def read_teams(api: GhApi) -> dict[str, Any]:
    return {
        str(team.get("slug")): {
            "privacy": team.get("privacy", MISSING),
            "repository_permission": team.get("permission", MISSING),
        }
        for team in api.get_array(f"repos/{api.repo}/teams")
    }


def read_security(
    api: GhApi, wanted: Mapping[str, Any], repo: Mapping[str, Any] | None
) -> dict[str, Any]:
    observed: dict[str, Any] = {}
    if PVR in wanted:
        reporting = api.get_object(f"repos/{api.repo}/private-vulnerability-reporting")
        observed[PVR] = reporting.get("enabled", MISSING)
    fields = [key for key in wanted if key != PVR]
    if fields:
        analysis = (repo or {}).get("security_and_analysis")
        if not isinstance(analysis, dict):
            raise ApiError(
                "api_invalid",
                f"path=repos/{api.repo} security_and_analysis not visible (needs admin rights)",
            )
        for key in fields:
            entry = analysis.get(key)
            observed[key] = entry.get("status", MISSING) if isinstance(entry, dict) else MISSING
    return observed


def _reviewer(entry: Mapping[str, Any]) -> dict[str, Any]:
    kind = entry.get("type")
    reviewer = entry.get("reviewer") or {}
    name = "slug" if kind == "Team" else "login"
    return {"type": kind, name: reviewer.get(name) if isinstance(reviewer, dict) else None}


def read_environment(
    api: GhApi, env: Mapping[str, Any], wanted: Mapping[str, Any]
) -> dict[str, Any]:
    base = f"repos/{api.repo}/environments/{quote(str(env.get('name')), safe='')}"
    rules = [rule for rule in env.get("protection_rules") or [] if isinstance(rule, dict)]
    reviewers = next((rule for rule in rules if rule.get("type") == "required_reviewers"), {})
    timer = next((rule for rule in rules if rule.get("type") == "wait_timer"), {})
    policy = env.get("deployment_branch_policy", MISSING)
    observed: dict[str, Any] = {
        "reviewers": [_reviewer(entry) for entry in reviewers.get("reviewers") or []],
        "prevent_self_review": reviewers.get("prevent_self_review", False),
        "wait_timer": timer.get("wait_timer", 0),
        "deployment_branch_policy": policy,
    }
    if "secrets" in wanted:
        secrets = api.get_list(f"{base}/secrets", "secrets")
        observed["secrets"] = [str(secret.get("name")) for secret in secrets]
    if "deployment_branch_policies" in wanted:
        policies: list[dict[str, Any]] = []
        if isinstance(policy, dict) and policy.get("custom_branch_policies") is True:
            listed = api.get_list(f"{base}/deployment-branch-policies", "branch_policies")
            policies = [{"name": p.get("name"), "type": p.get("type")} for p in listed]
        observed["deployment_branch_policies"] = policies
    return observed


def read_rulesets(api: GhApi, wanted: Mapping[str, Any]) -> dict[str, Any]:
    by_name: dict[str, list[dict[str, Any]]] = {}
    for summary in api.get_array(f"repos/{api.repo}/rulesets"):
        by_name.setdefault(str(summary.get("name")), []).append(summary)
    observed: dict[str, Any] = {}
    for name in wanted:
        found = by_name.get(name, [])
        if len(found) > 1:
            raise ApiError("api_invalid", f"path=repos/{api.repo}/rulesets has {name} twice")
        if not found:
            continue
        detail = api.get_object(f"repos/{api.repo}/rulesets/{found[0].get('id')}")
        rules = {
            str(rule.get("type")): rule.get("parameters") or {}
            for rule in detail.get("rules") or []
            if isinstance(rule, dict)
        }
        observed[name] = {**detail, "rules": rules}
    return observed


def read_settings(api: GhApi, expected: Mapping[str, Any]) -> dict[str, Any]:
    """The actual settings, in the shape of the expected-state file."""
    observed: dict[str, Any] = {}
    if expected["organization"]:
        observed["organization"] = read_organization(api, expected["organization"])
    if expected["teams"]:
        observed["teams"] = read_teams(api)
    security = expected["security"]
    repo = None
    if expected["repo"] or any(key != PVR for key in security):
        repo = api.get_object(f"repos/{api.repo}")
        observed["repo"] = repo
    if security:
        observed["security"] = read_security(api, security, repo)
    if expected["actions"]:
        base = f"repos/{api.repo}/actions/permissions"
        observed["actions"] = read_actions(api, base, expected["actions"])
    variables = api.get_list(f"repos/{api.repo}/actions/variables", "variables", VARIABLES_PAGE)
    observed["variables"] = {str(var.get("name")): var.get("value") for var in variables}
    if expected["environments"]:
        environments = {
            str(env.get("name")): env
            for env in api.get_list(f"repos/{api.repo}/environments", "environments")
        }
        observed["environments"] = {
            name: read_environment(api, environments[name], wanted)
            for name, wanted in expected["environments"].items()
            if name in environments
        }
    if expected["rulesets"]:
        observed["rulesets"] = read_rulesets(api, expected["rulesets"])
    return observed


# Comparison


def _norm(value: Any) -> Any:
    if isinstance(value, list):
        return sorted((_norm(item) for item in value), key=lambda item: json.dumps(item))
    if isinstance(value, dict):
        return {key: _norm(item) for key, item in sorted(value.items())}
    return value


def compare(key: str, want: Any, have: Any) -> list[tuple[str, Any, Any, bool]]:
    """(key, expected, actual, matches) for every compared value, in file order."""
    if isinstance(want, dict) and want:
        if not isinstance(have, dict):
            return [(key, "present" if have is MISSING else want, have, False)]
        pairs: list[tuple[str, Any, Any, bool]] = []
        for name, value in want.items():
            pairs.extend(compare(f"{key}.{name}", value, have.get(name, MISSING)))
        return pairs
    if isinstance(want, dict):
        return [(key, want, have, isinstance(have, dict))]
    return [(key, want, have, have is not MISSING and _norm(want) == _norm(have))]


def _show(value: Any) -> str:
    if value is MISSING:
        return "missing"
    return json.dumps(_norm(value))


def main(argv: Sequence[str] | None = None, run: Runner = subprocess.run) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--expected", required=True, type=Path, help="expected-state JSON file")
    parser.add_argument("--repo", help="owner/name; default: repository of the file")
    args = parser.parse_args(argv)

    try:
        expected = parse_expected(args.expected.read_text(encoding="utf-8"))
    except (OSError, ExpectedError) as exc:
        print(f"check_settings.expected_invalid reason={exc}", file=sys.stderr)
        return EXIT_INVALID
    repo = args.repo or expected["repository"]

    try:
        observed = read_settings(GhApi(repo, run), expected)
    except ApiError as exc:
        print(f"check_settings.{exc.kind} {exc}", file=sys.stderr)
        return EXIT_INVALID

    pairs = [
        pair
        for section in SECTIONS
        for name, value in expected[section].items()
        for pair in compare(
            f"{section}.{name}", value, observed.get(section, {}).get(name, MISSING)
        )
    ]
    findings = 0
    for key, want, have, matches in pairs:
        if matches:
            print(f"check_settings.checked key={key} value={_show(have)}")
        else:
            findings += 1
            print(
                f"check_settings.finding key={key} expected={_show(want)} actual={_show(have)}",
                file=sys.stderr,
            )
    if findings:
        print(f"check_settings.failed findings={findings}", file=sys.stderr)
        return EXIT_DEVIATION
    print(f"check_settings.passed checks={len(pairs)} repo={repo}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
