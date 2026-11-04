# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/ci/osv_diff.py.

The scanner is replaced by a fake runner that answers with recorded JSON output
of osv-scanner 2.7.0 (`scan source --format json`) from tests/fixtures/osv/:

  base.json        minimatch 10.2.6 with GHSA-g3hv-75wg-m249 (recorded on main,
                   long free text fields dropped)
  base-older.json  the same advisory on minimatch 10.2.5
  head.json        base.json plus urllib3 2.8.0 with the synthetic advisory
                   OSV-TEST-0001 in uv.lock
  clean.json       no finding

Each test builds a small git repository with both lockfiles, so that OSV_BASE
is read with git like in CI.
"""

from __future__ import annotations

import contextlib
import io
import subprocess
import tempfile
import unittest
from collections.abc import Sequence
from pathlib import Path

from tools.ci import osv_diff

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "osv"


class FakeScanner:
    """Stands in for subprocess.run; answers per scan with a fixture and exit code."""

    def __init__(self, root: Path, head: tuple[str, int], base: tuple[str, int] | None = None):
        self.root = root
        self.head = head
        self.base = base
        self.calls: list[list[str]] = []

    def __call__(self, cmd: Sequence[str], **_: object) -> subprocess.CompletedProcess[str]:
        cmd = list(cmd)
        self.calls.append(cmd)
        lockfiles = [Path(cmd[i + 1]) for i, arg in enumerate(cmd) if arg == "-L"]
        is_head = all(path.parent == self.root for path in lockfiles)
        answer = self.head if is_head else self.base
        if answer is None:
            raise AssertionError(f"unexpected base scan: {cmd}")
        fixture, code = answer
        output = Path(cmd[cmd.index("--output-file") + 1])
        output.write_text((FIXTURES / fixture).read_text(encoding="utf-8"), encoding="utf-8")
        return subprocess.CompletedProcess(cmd, code, "", "")


def git(root: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],  # noqa: S607
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


class TestOsvDiff(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        git(self.root, "init", "-q", "-b", "main")
        (self.root / "quality" / "osv").mkdir(parents=True)
        (self.root / "quality" / "osv" / "osv-scanner.toml").write_text("", encoding="utf-8")
        (self.root / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
        (self.root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-q", "-m", "base")
        self.base = git(self.root, "rev-parse", "HEAD")

    def run_main(self, scanner: FakeScanner, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = osv_diff.main(
                ["--root", str(self.root), "--scanner", "osv-scanner", *args], run=scanner
            )
        return code, out.getvalue(), err.getvalue()

    def test_only_new_vulnerabilities_fail(self) -> None:
        scanner = FakeScanner(self.root, head=("head.json", 1), base=("base.json", 1))
        code, out, _ = self.run_main(scanner, "--base", self.base)
        self.assertEqual(code, 1)
        self.assertEqual(
            out.splitlines(),
            ["uv.lock:1:1 osv-vulnerability OSV-TEST-0001 in urllib3@2.8.0 (PyPI)"],
        )
        self.assertNotIn("minimatch", out)

    def test_only_known_vulnerabilities_pass(self) -> None:
        scanner = FakeScanner(self.root, head=("base.json", 1), base=("base.json", 1))
        code, out, _ = self.run_main(scanner, "--base", self.base)
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_same_advisory_on_new_version_fails(self) -> None:
        scanner = FakeScanner(self.root, head=("base.json", 1), base=("base-older.json", 1))
        code, out, _ = self.run_main(scanner, "--base", self.base)
        self.assertEqual(code, 1)
        self.assertIn("GHSA-g3hv-75wg-m249 in minimatch@10.2.6 (npm)", out)

    def test_without_base_every_finding_fails(self) -> None:
        scanner = FakeScanner(self.root, head=("head.json", 1))
        code, out, _ = self.run_main(scanner, "--base", "")
        self.assertEqual(code, 1)
        self.assertEqual(len(out.splitlines()), 2)
        self.assertEqual(len(scanner.calls), 1)

    def test_clean_scan_passes(self) -> None:
        scanner = FakeScanner(self.root, head=("clean.json", 0))
        code, out, _ = self.run_main(scanner)
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_scan_command_uses_config_and_both_lockfiles(self) -> None:
        scanner = FakeScanner(self.root, head=("clean.json", 0), base=("clean.json", 0))
        self.run_main(scanner, "--base", self.base)
        head, base = scanner.calls
        self.assertEqual(head[:5], ["osv-scanner", "scan", "source", "--format", "json"])
        config = str(self.root / "quality" / "osv" / "osv-scanner.toml")
        for cmd in (head, base):
            self.assertEqual(cmd[cmd.index("--config") + 1], config)
        self.assertEqual(
            [head[i + 1] for i, arg in enumerate(head) if arg == "-L"],
            [str(self.root / "pnpm-lock.yaml"), str(self.root / "uv.lock")],
        )
        base_lockfiles = [Path(base[i + 1]) for i, arg in enumerate(base) if arg == "-L"]
        self.assertEqual([path.name for path in base_lockfiles], ["pnpm-lock.yaml", "uv.lock"])

    def test_lockfile_missing_in_base_is_not_scanned_there(self) -> None:
        git(self.root, "rm", "-q", "--cached", "uv.lock")
        git(self.root, "commit", "-q", "-m", "drop uv.lock")
        base = git(self.root, "rev-parse", "HEAD")
        scanner = FakeScanner(self.root, head=("head.json", 1), base=("base.json", 1))
        code, out, _ = self.run_main(scanner, "--base", base)
        self.assertEqual(code, 1)
        base_cmd = scanner.calls[1]
        self.assertEqual([arg for arg in base_cmd if arg.endswith("uv.lock")], [])
        self.assertIn("OSV-TEST-0001", out)

    def test_scanner_error_exits_2(self) -> None:
        # Recorded: without network access 2.7.0 exits 127 and still writes a
        # JSON file without results. That must never count as a clean scan.
        scanner = FakeScanner(self.root, head=("clean.json", 127))
        code, out, err = self.run_main(scanner)
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("osv.scanner_error scan=head exit=127", err)

    def test_base_scanner_error_exits_2(self) -> None:
        scanner = FakeScanner(self.root, head=("head.json", 1), base=("clean.json", 128))
        code, _, err = self.run_main(scanner, "--base", self.base)
        self.assertEqual(code, 2)
        self.assertIn("osv.scanner_error scan=base exit=128", err)

    def test_unreadable_output_exits_2(self) -> None:
        scanner = FakeScanner(self.root, head=("clean.json", 0))
        broken = self.root / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        scanner.head = (str(broken), 0)
        code, _, err = self.run_main(scanner)
        self.assertEqual(code, 2)
        self.assertIn("osv.output_invalid scan=head", err)

    def test_unknown_base_ref_exits_2(self) -> None:
        scanner = FakeScanner(self.root, head=("head.json", 1))
        code, _, err = self.run_main(scanner, "--base", "no-such-ref")
        self.assertEqual(code, 2)
        self.assertIn("osv.base_invalid ref=no-such-ref", err)
        self.assertEqual(scanner.calls, [])

    def test_missing_config_exits_2(self) -> None:
        (self.root / "quality" / "osv" / "osv-scanner.toml").unlink()
        scanner = FakeScanner(self.root, head=("clean.json", 0))
        code, _, err = self.run_main(scanner)
        self.assertEqual(code, 2)
        self.assertIn("osv.config_missing", err)

    def test_ignore_without_reason_or_expiry_exits_2(self) -> None:
        config = self.root / "quality" / "osv" / "osv-scanner.toml"
        for entry in (
            '[[IgnoredVulns]]\nid = "GHSA-1"\nignoreUntil = 2026-12-01\n',
            '[[IgnoredVulns]]\nid = "GHSA-1"\nreason = "dev tool only"\n',
        ):
            with self.subTest(entry=entry):
                config.write_text(entry, encoding="utf-8")
                scanner = FakeScanner(self.root, head=("clean.json", 0))
                code, _, err = self.run_main(scanner)
                self.assertEqual(code, 2)
                self.assertIn("osv.config_invalid", err)
                self.assertEqual(scanner.calls, [])

    def test_ignore_with_reason_and_expiry_is_accepted(self) -> None:
        config = self.root / "quality" / "osv" / "osv-scanner.toml"
        config.write_text(
            '[[IgnoredVulns]]\nid = "GHSA-1"\nignoreUntil = 2026-12-01\nreason = "dev only"\n',
            encoding="utf-8",
        )
        scanner = FakeScanner(self.root, head=("clean.json", 0))
        code, _, _ = self.run_main(scanner)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
