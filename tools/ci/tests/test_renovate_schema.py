# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for renovate.json and its schema check in `make workflows`.

The schema tests run the real make target (with an empty workflow directory,
so actionlint and zizmor are skipped) against the real renovate.json or a
broken copy of it. The other tests read renovate.json and
tools/bootstrap/tools.toml of the repository.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
RENOVATE = REPO_ROOT / "renovate.json"
TOOLS_TOML = REPO_ROOT / "tools/bootstrap/tools.toml"
TIMEOUT_S = 300

# Values of Feinentwurf 00 section 2.11 (taken from 12 section 5.2).
MINIMUM_RELEASE_AGE = "7 days"
MAX_OPEN_PRS = 5


def run_make_workflows(config: Path, workflows_dir: Path) -> subprocess.CompletedProcess[str]:
    """Run `make workflows` with the given Renovate config and workflow directory."""
    env = {k: v for k, v in os.environ.items() if k not in {"MAKEFLAGS", "MFLAGS", "MAKELEVEL"}}
    return subprocess.run(  # noqa: S603
        [  # noqa: S607
            "make",
            "--no-print-directory",
            "workflows",
            f"RENOVATE_CONFIG={config}",
            f"WORKFLOWS_DIR={workflows_dir}",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_S,
        check=False,
    )


def load_config() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(RENOVATE.read_text(encoding="utf-8"))
    return data


def custom_managers(config: dict[str, Any], file_name: str) -> list[dict[str, Any]]:
    """The custom regex managers whose managerFilePatterns name `file_name`."""
    found: list[dict[str, Any]] = [
        m
        for m in config.get("customManagers", [])
        if any(file_name in p.replace("\\", "") for p in m.get("managerFilePatterns", []))
    ]
    if not found:
        raise AssertionError(f"no custom manager for {file_name}")
    return found


def python_regex(renovate_regex: str) -> re.Pattern[str]:
    """Translate a Renovate matchString (named groups `(?<name>`) to Python."""
    return re.compile(renovate_regex.replace("(?<", "(?P<"))


def matches(managers: list[dict[str, Any]], text: str) -> list[dict[str, str]]:
    """Every match of every matchString, with the datasource of its manager."""
    found: list[dict[str, str]] = []
    for manager in managers:
        for pattern in manager["matchStrings"]:
            for m in python_regex(pattern).finditer(text):
                hit = {k: v for k, v in m.groupdict().items() if v is not None}
                hit["datasource"] = manager["datasourceTemplate"]
                found.append(hit)
    return found


class TestRenovate(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.empty_workflows = self.tmp / "workflows"
        self.empty_workflows.mkdir()

    def test_repository_config_passes(self) -> None:
        result = run_make_workflows(RENOVATE, self.empty_workflows)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("check-jsonschema --builtin-schema vendor.renovate", result.stdout)

    def test_invalid_config_fails(self) -> None:
        broken = load_config()
        broken["prConcurrentLimit"] = "five"
        copy = self.tmp / "renovate.json"
        copy.write_text(json.dumps(broken), encoding="utf-8")
        result = run_make_workflows(copy, self.empty_workflows)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("prConcurrentLimit", result.stdout + result.stderr)

    def test_values_of_the_design(self) -> None:
        config = load_config()
        self.assertIn("config:best-practices", config["extends"])
        self.assertTrue(config["schedule"], "schedule must not be empty")
        for entry in config["schedule"]:
            # cron with day of week 1 (Monday) and hours before 6.
            self.assertRegex(entry, r"^\* [0-5](-[0-5])? \* \* 1$")
        self.assertEqual(config["minimumReleaseAge"], MINIMUM_RELEASE_AGE)
        self.assertEqual(config["internalChecksFilter"], "strict")
        self.assertEqual(config["prConcurrentLimit"], MAX_OPEN_PRS)
        self.assertTrue(config["dependencyDashboard"])
        self.assertTrue(config["major"]["dependencyDashboardApproval"])
        # config:best-practices sets 3 days for npm and PyPI in a package rule,
        # which beats the top level value; a later rule restores 7 days.
        age_rules = [
            r
            for r in config["packageRules"]
            if r.get("minimumReleaseAge") == MINIMUM_RELEASE_AGE
            and r.get("matchPackageNames") == ["*"]
        ]
        self.assertEqual(len(age_rules), 1)
        self.assertEqual(age_rules[0]["matchUpdateTypes"], ["major", "minor", "patch"])
        # Lock file maintenance would bypass the waiting time.
        self.assertFalse(config["lockFileMaintenance"]["enabled"])

    def test_every_pinned_binary_is_matched(self) -> None:
        tools = tomllib.loads(TOOLS_TOML.read_text(encoding="utf-8"))
        binaries = {name: t for name, t in tools.items() if name != "images"}
        found = matches(
            custom_managers(load_config(), "tools/bootstrap/tools.toml"),
            TOOLS_TOML.read_text(encoding="utf-8"),
        )
        by_name = {f["depName"]: f for f in found if f["datasource"] == "github-releases"}
        self.assertEqual(set(by_name), set(binaries))
        for name, table in binaries.items():
            self.assertEqual(by_name[name]["currentValue"], table["version"], name)
            repo = re.match(r"https://github\.com/([^/]+/[^/]+)/releases/", table["url"])
            if repo is None:
                self.fail(f"{name}: url is not a GitHub release download")
            self.assertEqual(by_name[name]["packageName"], repo.group(1), name)

    def test_every_image_is_matched_with_digest(self) -> None:
        tools = tomllib.loads(TOOLS_TOML.read_text(encoding="utf-8"))
        images = tools.get("images", {})
        self.assertTrue(images)
        found = matches(
            custom_managers(load_config(), "tools/bootstrap/tools.toml"),
            TOOLS_TOML.read_text(encoding="utf-8"),
        )
        with_digest = [f for f in found if f["datasource"] == "docker"]
        self.assertEqual(len(with_digest), len(images))
        for image in images.values():
            hit = [f for f in with_digest if f["currentDigest"] == image["digest"]]
            self.assertEqual(len(hit), 1, image["image"])
            self.assertEqual(hit[0]["currentValue"], image["tag"])
            self.assertEqual(hit[0]["depName"], image["image"])

    def test_scancode_lock_is_not_updated_per_package(self) -> None:
        rules = [
            r
            for r in load_config()["packageRules"]
            if r.get("matchFileNames") == ["tools/bootstrap/scancode/requirements.txt"]
        ]
        self.assertEqual(len(rules), 1)
        self.assertFalse(rules[0]["enabled"])


if __name__ == "__main__":
    unittest.main()
