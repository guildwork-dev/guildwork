# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/ci/scancode_policy.py.

The policy tests feed a shortened real ScanCode output (fixtures/scancode/
scan.json, ScanCode Toolkit 32.5.0 over a small tree) into the policy, with
quality/licenses/ files in a temporary repository root. The runner tests
replace ScanCode and the container runtime with small fake programs that
record their arguments and write the fixture, so no test needs ScanCode, a
network or a container runtime. Two tests read the real pins of the
repository (image digest, hashed requirements).
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import re
import subprocess
import sys
import tempfile
import textwrap
import tomllib
import unittest
from pathlib import Path
from typing import Any

from tools.ci import scancode_policy

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "scancode" / "scan.json"
EXCEPTIONS = "quality/licenses/scancode-exceptions.txt"

ALLOWED = """\
# SPDX-License-Identifier: Apache-2.0
Apache-2.0
MIT
"""

EXCEPTIONS_HEADER = """\
# SPDX-License-Identifier: Apache-2.0
# <path>, SPDX expression, reason; tab separated
"""

DIGEST = "sha256:" + "ab" * 32

TOOLS_TOML = f"""\
[images.scancode]
image = "docker.io/library/python"
tag = "3.12.15-slim-trixie"
digest = "{DIGEST}"
source = "https://hub.docker.com/_/python"
retrieved = "2026-11-01"
"""

REQUIREMENTS = "scancode-toolkit-mini==32.5.0 --hash=sha256:" + "cd" * 32 + "\n"

# A fake program for both runners: it finds the output path (the value of
# --json, mapped from /out to the host directory for the container) and copies
# the fixture there. It records its arguments next to itself.
FAKE = """\
#!{python}
import json, pathlib, shutil, sys
args = sys.argv[1:]
here = pathlib.Path(__file__).resolve().parent
(here / "args.json").write_text(json.dumps(args))
out = args[args.index("--json") + 1]
for i, arg in enumerate(args):
    if arg == "-v" and args[i + 1].endswith(":/out"):
        out = out.replace("/out", args[i + 1][: -len(":/out")], 1)
shutil.copyfile({fixture!r}, out)
"""


def fixture_scan() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return data


def file_entry(scan: dict[str, Any], path: str) -> dict[str, Any]:
    for entry in scan["files"]:
        if entry["path"] == path:
            return entry  # type: ignore[no-any-return]
    raise AssertionError(f"{path} is not in the fixture")


class ScancodeCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        # The runner resolves paths; macOS's default TMPDIR sits under the /var symlink.
        self.root = Path(tmp.name).resolve()
        self.write("quality/licenses/allowed.txt", ALLOWED)
        self.write(EXCEPTIONS, EXCEPTIONS_HEADER)
        self.write("tools/bootstrap/tools.toml", TOOLS_TOML)
        self.write("tools/bootstrap/scancode/requirements.txt", REQUIREMENTS)

    def write(self, rel: str, text: str) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def exceptions(self, *lines: str) -> None:
        self.write(EXCEPTIONS, EXCEPTIONS_HEADER + "".join(line + "\n" for line in lines))

    def scan_file(self, scan: dict[str, Any] | None = None) -> Path:
        path = self.root / "scan.json"
        path.write_text(json.dumps(scan if scan is not None else fixture_scan()), "utf-8")
        return path

    def run_main(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = scancode_policy.main(["--root", str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def check(self, scan: dict[str, Any] | None = None) -> tuple[int, str, str]:
        return self.run_main("--scan", str(self.scan_file(scan)))


class TestScancode(ScancodeCase):
    def test_unexpected_license_fails(self) -> None:
        code, out, _ = self.check()

        self.assertEqual(code, 1)
        lines = out.splitlines()
        self.assertIn(
            "src/copied.py:1:1 scancode-license-not-allowed GPL-3.0-only is neither allowed"
            f" nor an exception in {EXCEPTIONS}",
            lines,
        )
        self.assertTrue(any(line.startswith("docs/notes.md:3:1 ") for line in lines), out)
        # Apache-2.0 and `MIT OR Apache-2.0` are allowed; directories have no license.
        self.assertEqual(len(lines), 2, out)

    def test_exception_needs_reason_and_exact_file(self) -> None:
        reason = "Copied with permission, see the file header."
        cases = {
            "no reason": "src/copied.py\tGPL-3.0-only\t",
            "blank reason": "src/copied.py\tGPL-3.0-only\t   ",
            "two fields": "src/copied.py\tGPL-3.0-only",
            "glob instead of a file": f"src/*.py\tGPL-3.0-only\t{reason}",
            "directory instead of a file": f"src/\tGPL-3.0-only\t{reason}",
            "absolute path": f"/src/copied.py\tGPL-3.0-only\t{reason}",
            "parent segment": f"docs/../src/copied.py\tGPL-3.0-only\t{reason}",
        }
        for name, line in cases.items():
            with self.subTest(name):
                self.exceptions(line)
                code, _, err = self.check()
                self.assertEqual(code, 2)
                self.assertIn(f"scancode.config_invalid path={EXCEPTIONS} line=3", err)

        not_covering = {
            "other file": f"src/dual.py\tGPL-3.0-only\t{reason}",
            "directory without slash": f"src\tGPL-3.0-only\t{reason}",
            "other expression": f"src/copied.py\tGPL-3.0-or-later\t{reason}",
        }
        for name, line in not_covering.items():
            with self.subTest(name):
                self.exceptions(line, f"docs/notes.md\tCC-BY-SA-4.0\t{reason}")
                code, out, _ = self.check()
                self.assertEqual(code, 1)
                self.assertIn("src/copied.py:1:1 scancode-license-not-allowed", out)
                self.assertIn(f"{EXCEPTIONS}:3:1 scancode-exception-unused", out)

        self.exceptions(
            f"src/copied.py\tGPL-3.0-only\t{reason}", f"docs/notes.md\tCC-BY-SA-4.0\t{reason}"
        )
        code, out, _ = self.check()
        self.assertEqual((code, out), (0, ""))

    def test_duplicate_exception_is_a_config_error(self) -> None:
        line = "src/copied.py\tGPL-3.0-only\tCopied with permission."
        self.exceptions(line, line)

        code, _, err = self.check()

        self.assertEqual(code, 2)
        self.assertIn("line=4", err)

    def test_unused_exception_fails(self) -> None:
        reason = "Copied with permission."
        self.exceptions(
            f"src/copied.py\tGPL-3.0-only\t{reason}",
            f"docs/notes.md\tCC-BY-SA-4.0\t{reason}",
            f"docs/gone.md\tCC-BY-SA-4.0\t{reason}",
        )

        code, out, _ = self.check()

        self.assertEqual(code, 1)
        self.assertEqual(
            out.splitlines(),
            [
                f"{EXCEPTIONS}:5:1 scancode-exception-unused docs/gone.md CC-BY-SA-4.0"
                " matches no ScanCode detection"
            ],
        )

    def test_license_clue_counts_like_a_detection(self) -> None:
        scan = fixture_scan()
        file_entry(scan, "src/ok.py")["license_clues"] = [
            {"license_expression_spdx": "LicenseRef-scancode-free-unknown", "start_line": 7}
        ]

        _, out, _ = self.check(scan)

        self.assertIn(
            "src/ok.py:7:1 scancode-license-not-allowed LicenseRef-scancode-free-unknown", out
        )

    def test_detection_line_is_the_first_match(self) -> None:
        scan = fixture_scan()
        matches = file_entry(scan, "src/copied.py")["license_detections"][0]["matches"]
        matches[:] = [dict(matches[0], start_line=9), dict(matches[0], start_line=4)]

        _, out, _ = self.check(scan)

        self.assertIn("src/copied.py:4:1 scancode-license-not-allowed", out)

    def test_scan_errors_fail(self) -> None:
        scan = fixture_scan()
        file_entry(scan, "src/ok.py")["scan_errors"] = ["ERROR: for scanner: licenses"]
        scan["headers"][0]["errors"] = ["Some files failed to scan properly"]

        code, out, _ = self.check(scan)

        self.assertEqual(code, 1)
        self.assertIn("src/ok.py:1:1 scancode-scan-error ERROR: for scanner: licenses", out)
        self.assertIn(":1:1 scancode-scan-error Some files failed to scan properly", out)

    def test_exceptions_file_itself_is_not_checked(self) -> None:
        scan = fixture_scan()
        reason = "Copied with permission."
        self.exceptions(
            f"src/copied.py\tGPL-3.0-only\t{reason}", f"docs/notes.md\tCC-BY-SA-4.0\t{reason}"
        )
        entry = copy.deepcopy(file_entry(scan, "src/copied.py"))
        entry["path"] = EXCEPTIONS
        scan["files"].append(entry)

        code, out, _ = self.check(scan)

        self.assertEqual((code, out), (0, ""))

    def test_invalid_scan_output_exits_2(self) -> None:
        invalid: dict[str, dict[str, Any]] = {
            "no files": {"headers": []},
            "file without path": {"headers": [], "files": [{"type": "file"}]},
            "detection without expression": {
                "headers": [],
                "files": [{"path": "a", "type": "file", "license_detections": [{}]}],
            },
        }
        for name, scan in invalid.items():
            with self.subTest(name):
                code, _, err = self.check(scan)
                self.assertEqual(code, 2)
                self.assertIn("scancode.output_invalid", err)

        path = self.root / "broken.json"
        path.write_text("{", encoding="utf-8")
        code, _, err = self.run_main("--scan", str(path))
        self.assertEqual(code, 2)
        self.assertIn("scancode.output_invalid", err)

    def test_json_report_lists_findings(self) -> None:
        report = self.root / ".reports" / "scancode_policy.json"

        code, _, _ = self.run_main("--scan", str(self.scan_file()), "--json", str(report))

        self.assertEqual(code, 1)
        findings = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(sorted(f["path"] for f in findings), ["docs/notes.md", "src/copied.py"])
        self.assertEqual({f["rule"] for f in findings}, {"scancode-license-not-allowed"})


class TestRunners(ScancodeCase):
    def fake(self, name: str) -> Path:
        path = self.root / "fake" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(FAKE.format(python=sys.executable, fixture=str(FIXTURE)), "utf-8")
        path.chmod(0o755)
        return path

    def recorded_args(self) -> list[str]:
        args: list[str] = json.loads((self.root / "fake" / "args.json").read_text("utf-8"))
        return args

    def git_repo(self) -> None:
        def git(*args: str) -> None:
            command = ["git", "-C", str(self.root), *args]
            subprocess.run(command, check=True, capture_output=True)  # noqa: S603

        git("init", "-q", "-b", "main")
        git("config", "user.email", "dev@example.com")
        git("config", "user.name", "Dev")
        self.write("src/committed.py", "print('committed')\n")
        git("add", ".")
        git("commit", "-q", "-m", "chore: fixture")
        self.write("src/untracked.py", "print('untracked')\n")
        self.write("src/committed.py", "print('changed, not committed')\n")

    def test_archive_holds_only_committed_files(self) -> None:
        self.git_repo()
        dest = self.root / "archive"

        scancode_policy.archive_head(self.root, dest)

        self.assertTrue((dest / "src" / "committed.py").is_file())
        self.assertFalse((dest / "src" / "untracked.py").exists())
        self.assertEqual((dest / "src" / "committed.py").read_text("utf-8"), "print('committed')\n")

    def test_archive_ignores_export_attributes(self) -> None:
        # export-ignore must not hide committed files from the license scan,
        # and export-subst must not rewrite them.
        self.write(".gitattributes", "src/** export-ignore\ndocs/** export-subst\n")
        self.write("docs/notes.md", "$Format:%H$\n")
        self.git_repo()
        dest = self.root / "archive"

        scancode_policy.archive_head(self.root, dest)

        self.assertTrue((dest / "src" / "committed.py").is_file())
        self.assertEqual((dest / "docs" / "notes.md").read_text("utf-8"), "$Format:%H$\n")

    def test_archive_writes_committed_bytes_whatever_the_attributes(self) -> None:
        # Attributes of the working tree (here uncommitted) must not convert the
        # scanned content; a UTF-16 copy would hide its license from ScanCode.
        self.git_repo()
        self.write(".gitattributes", "src/** working-tree-encoding=UTF-16 eol=crlf\n")
        dest = self.root / "archive"

        scancode_policy.archive_head(self.root, dest)

        self.assertEqual((dest / "src" / "committed.py").read_bytes(), b"print('committed')\n")
        self.assertFalse((dest / ".gitattributes").exists())

    def test_local_runner_scans_the_archive_with_the_pinned_env(self) -> None:
        self.git_repo()
        env = self.root / ".tools" / "scancode"
        python = self.fake("python")
        (env / "bin").mkdir(parents=True)
        (env / "bin" / "python").symlink_to(python)
        raw = self.root / ".reports" / "scancode-scan.json"

        code, out, err = self.run_main(
            "--runner", "local", "--env", str(env), "--scan-output", str(raw)
        )

        self.assertEqual(code, 1, err)
        self.assertIn("src/copied.py:1:1 scancode-license-not-allowed", out)
        args = self.recorded_args()
        self.assertEqual(args[0], "-c")
        self.assertIn("--license", args)
        self.assertEqual(args[args.index("--json") + 1], str(raw))
        self.assertIn("scancode.done runner=local", err)

    def test_policy_files_come_from_the_scanned_commit(self) -> None:
        self.git_repo()
        reason = "Copied with permission."
        self.exceptions(
            f"src/copied.py\tGPL-3.0-only\t{reason}", f"docs/notes.md\tCC-BY-SA-4.0\t{reason}"
        )

        code, out, _ = self.run_main("--runner", "container", "--docker", str(self.fake("d")))

        self.assertEqual(code, 1, "uncommitted exceptions must not count")
        self.assertIn("src/copied.py:1:1 scancode-license-not-allowed", out)

    def test_local_runner_without_env_exits_2(self) -> None:
        self.git_repo()

        code, _, err = self.run_main("--runner", "local", "--env", str(self.root / "missing"))

        self.assertEqual(code, 2)
        self.assertIn("scancode.env_missing", err)

    def test_container_runner_uses_the_pinned_digest(self) -> None:
        self.git_repo()
        docker = self.fake("docker")

        code, out, err = self.run_main("--runner", "container", "--docker", str(docker))

        self.assertEqual(code, 1, err)
        self.assertIn("src/copied.py:1:1 scancode-license-not-allowed", out)
        args = self.recorded_args()
        self.assertEqual(args[:2], ["run", "--rm"])
        self.assertIn(f"docker.io/library/python@{DIGEST}", args)
        mounts = [args[i + 1] for i, arg in enumerate(args) if arg == "-v"]
        self.assertTrue(any(m.endswith(":/scan:ro") for m in mounts), mounts)
        self.assertTrue(any(m.endswith("/tools/bootstrap/scancode:/req:ro") for m in mounts))
        script = args[args.index("-c") + 1]
        self.assertIn("--require-hashes", script)
        self.assertIn("--only-binary :all:", script)
        self.assertIn("-r /req/requirements.txt", script)

    def test_image_without_digest_exits_2(self) -> None:
        self.write("tools/bootstrap/tools.toml", TOOLS_TOML.replace(DIGEST, "latest"))
        self.git_repo()

        code, _, err = self.run_main("--runner", "container", "--docker", str(self.fake("d")))

        self.assertEqual(code, 2)
        self.assertIn("scancode.config_invalid path=tools/bootstrap/tools.toml", err)

    def test_failing_scanner_exits_2(self) -> None:
        self.git_repo()
        docker = self.root / "fake" / "docker"
        docker.parent.mkdir(parents=True)
        docker.write_text("#!/bin/sh\nexit 125\n", encoding="utf-8")
        docker.chmod(0o755)

        code, _, err = self.run_main("--runner", "container", "--docker", str(docker))

        self.assertEqual(code, 2)
        self.assertIn("scancode.run_failed runner=container exit=125", err)

    def test_scancode_exit_1_with_output_reaches_the_policy(self) -> None:
        # ScanCode exits 1 when a file had a scan error; its output still holds
        # every file, and the policy reports the errors as findings.
        self.git_repo()
        docker = self.fake("docker")
        docker.write_text(docker.read_text("utf-8") + "sys.exit(1)\n", encoding="utf-8")

        code, out, err = self.run_main("--runner", "container", "--docker", str(docker))

        self.assertEqual(code, 1, err)
        self.assertNotIn("scancode.run_failed", err)
        self.assertIn("src/copied.py:1:1 scancode-license-not-allowed", out)

    def test_committed_file_missing_from_the_output_fails(self) -> None:
        # The fixture output lists none of the files of this repository; only
        # the VCS files that ScanCode always skips may be missing.
        self.write(".gitignore", "*.log\n")
        self.git_repo()

        code, out, err = self.run_main("--runner", "container", "--docker", str(self.fake("d")))

        self.assertEqual(code, 1, err)
        self.assertIn(
            "src/committed.py:1:1 scancode-file-not-scanned the committed file is missing"
            " from the ScanCode output",
            out.splitlines(),
        )
        self.assertNotIn(".gitignore:", out)

    def test_missing_container_cli_exits_2(self) -> None:
        self.git_repo()

        code, _, err = self.run_main("--runner", "container", "--docker", str(self.root / "no"))

        self.assertEqual(code, 2)
        self.assertIn("scancode.run_failed runner=container reason=FileNotFoundError", err)
        # M180: point machines without a container runtime to the local runner.
        self.assertIn("SCANCODE_RUNNER=local", err)


class TestRepositoryPins(unittest.TestCase):
    def test_image_is_pinned_by_digest(self) -> None:
        raw = tomllib.loads((REPO_ROOT / "tools/bootstrap/tools.toml").read_text("utf-8"))
        image = raw["images"]["scancode"]

        self.assertRegex(image["digest"], r"^sha256:[0-9a-f]{64}$")
        self.assertTrue(image["source"].startswith("https://"))
        self.assertRegex(image["retrieved"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(
            scancode_policy.load_image(REPO_ROOT), f"{image['image']}@{image['digest']}"
        )

    def test_requirements_pin_exact_versions_with_hashes(self) -> None:
        text = (REPO_ROOT / "tools/bootstrap/scancode/requirements.txt").read_text("utf-8")
        requirements = re.split(r"\n(?=[a-z0-9])", textwrap.dedent(text).strip())
        packages = [r for r in requirements if not r.startswith("#")]

        self.assertTrue(any(r.startswith("scancode-toolkit-mini==32.5.0 ") for r in packages))
        for requirement in packages:
            with self.subTest(requirement.split()[0]):
                self.assertRegex(requirement, r"^[a-z0-9._-]+==[^ ;\\]+")
                self.assertRegex(requirement, r"--hash=sha256:[0-9a-f]{64}")


if __name__ == "__main__":
    unittest.main()
