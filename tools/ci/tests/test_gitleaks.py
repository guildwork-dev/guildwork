# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for .gitleaks.toml and quality/secrets/samples.txt.

The tests run the pinned gitleaks binary from .tools/bin (`make bootstrap`)
with `gitleaks dir` on copies of the samples in a temporary directory:

- with a copy of .gitleaks.toml whose allowlists are removed, every sample must
  be found by the rule named in samples.txt;
- with the real .gitleaks.toml, no sample is found, but a sample with one
  character changed is, so the allowlist holds exact values only.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG = REPO_ROOT / ".gitleaks.toml"
SAMPLES = REPO_ROOT / "quality" / "secrets" / "samples.txt"
GITLEAKS = REPO_ROOT / ".tools" / "bin" / "gitleaks"
SYNTHETIC_MARKER = "EXAMPLE"
TIMEOUT_S = 120

ALLOWLIST_KEYS = {"description", "regexTarget", "regexes"}


def load_samples() -> list[tuple[str, str, str]]:
    """Return (redaction pattern id, gitleaks rule id, value) per sample line."""
    samples = []
    for number, line in enumerate(SAMPLES.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 3:
            raise AssertionError(f"samples.txt:{number}: expected 3 fields, got {len(fields)}")
        samples.append((fields[0], fields[1], fields[2]))
    return samples


def strip_allowlists(text: str) -> str:
    """Remove every [[allowlists]] table (header up to the next header)."""
    out: list[str] = []
    skipping = False
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("["):
            skipping = stripped == "[[allowlists]]"
        if not skipping:
            out.append(line)
    return "".join(out)


def run_dir_scan(config: Path, target: Path, report: Path) -> tuple[int, list[dict[str, Any]]]:
    """Run `gitleaks dir` and return the exit code and the JSON findings."""
    result = subprocess.run(  # noqa: S603
        [
            str(GITLEAKS),
            "dir",
            "--no-banner",
            "--log-level",
            "error",
            "--config",
            str(config),
            "--report-format",
            "json",
            "--report-path",
            str(report),
            str(target),
        ],
        capture_output=True,
        text=True,
        timeout=TIMEOUT_S,
        check=False,
    )
    if result.returncode not in (0, 1) or not report.exists():
        raise AssertionError(f"gitleaks failed ({result.returncode}): {result.stderr}")
    findings: list[dict[str, Any]] = json.loads(report.read_text(encoding="utf-8"))
    return result.returncode, findings


def mutate(value: str) -> str:
    """Change one character of the synthetic marker, keeping the shape."""
    index = value.index(SYNTHETIC_MARKER) + len(SYNTHETIC_MARKER) - 1
    return value[:index] + "F" + value[index + 1 :]


class TestGitleaksRules(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(GITLEAKS.is_file(), "gitleaks binary missing; run `make bootstrap`")
        self.assertTrue(CONFIG.is_file(), ".gitleaks.toml missing")
        self.samples = load_samples()
        self.assertTrue(self.samples, "samples.txt has no samples")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def write_target(self, values: list[str]) -> Path:
        target = self.tmp / "target"
        target.mkdir()
        (target / "values.txt").write_text("\n".join(values) + "\n", encoding="utf-8")
        return target

    def test_samples_are_marked_synthetic(self) -> None:
        for _, _, value in self.samples:
            self.assertIn(SYNTHETIC_MARKER, value)

    def test_detects_every_sample(self) -> None:
        text = CONFIG.read_text(encoding="utf-8")
        stripped = strip_allowlists(text)
        expected = tomllib.loads(text)
        expected.pop("allowlists", None)
        self.assertEqual(tomllib.loads(stripped), expected, "only the allowlists may be removed")
        config = self.tmp / "no-allowlist.toml"
        config.write_text(stripped, encoding="utf-8")
        target = self.write_target([value for _, _, value in self.samples])

        code, findings = run_dir_scan(config, target, self.tmp / "report.json")

        self.assertEqual(code, 1)
        found = {(f["RuleID"], f["Secret"]) for f in findings}
        for _, rule, value in self.samples:
            self.assertIn((rule, value), found, f"rule {rule} did not find {value[:16]}...")

    def test_allowlist_is_exact_values_only(self) -> None:
        config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertNotIn("allowlist", config, "use [[allowlists]], not the legacy table")
        for rule in config.get("rules", []):
            self.assertNotIn("allowlists", rule, f"rule {rule.get('id')} has its own allowlist")
            self.assertNotIn("allowlist", rule, f"rule {rule.get('id')} has its own allowlist")
        allowlists = config.get("allowlists", [])
        self.assertTrue(allowlists, "no allowlist for the samples")
        regexes: list[str] = []
        for allowlist in allowlists:
            self.assertLessEqual(set(allowlist), ALLOWLIST_KEYS, "only exact values allowed")
            self.assertTrue(allowlist.get("description", "").strip(), "allowlist needs a reason")
            self.assertEqual(allowlist.get("regexTarget", "secret"), "secret")
            regexes.extend(allowlist["regexes"])
        expected = sorted("^" + re.escape(value) + "$" for _, _, value in self.samples)
        self.assertEqual(sorted(regexes), expected)

    def test_real_config_allows_samples_and_finds_near_values(self) -> None:
        values = [value for _, _, value in self.samples]
        code, findings = run_dir_scan(CONFIG, self.write_target(values), self.tmp / "allowed.json")
        self.assertEqual((code, findings), (0, []))

        near = self.tmp / "near"
        near.mkdir()
        near_values = [mutate(value) for value in values]
        (near / "values.txt").write_text("\n".join(near_values) + "\n", encoding="utf-8")
        code, findings = run_dir_scan(CONFIG, near, self.tmp / "near.json")
        self.assertEqual(code, 1)
        secrets = {f["Secret"] for f in findings}
        for value in near_values:
            self.assertIn(value, secrets)


if __name__ == "__main__":
    unittest.main()
