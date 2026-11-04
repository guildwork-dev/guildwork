# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/ci/license_check.py.

Each test builds a small fixture repository in a temporary directory (a git
repository, because the header check reads the file list from git): LICENSE
with its checksum, the files of quality/licenses/, one license text and a few
source files. The fixture starts clean (no finding) and each test adds exactly
one violation. Dependencies are passed in as data, so no test runs pnpm.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import subprocess
import tempfile
import textwrap
import unittest
import unittest.mock
from pathlib import Path

from tools.ci import license_check, third_party_notices
from tools.ci.license_inventory import Dependency

LICENSE_TEXT = "Apache License\nVersion 2.0, January 2004\n"

HEADER_TOML = """\
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
[exempt]
paths = ["LICENSE", "LICENSES/**", "**/fixtures/**", "**/*.json", "**/pnpm-lock.yaml", "NOTICE"]

[[adopted]]
path = "docs/adopted.md"
license = "CC-BY-SA-4.0"
reason = "Text adopted from a third party under its own license."
"""

ALLOWED = """\
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
Apache-2.0
MIT
"""

DEV_EXCEPTIONS = """\
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""

ADOPTED_MD = """\
<!--
SPDX-License-Identifier: CC-BY-SA-4.0
SPDX-FileCopyrightText: Example Original Authors
Origin: example/project@0123456789abcdef0123456789abcdef01234567:doc.md, modified
-->

# Adopted text
"""

PNPM_LOCK = """\
lockfileVersion: '9.0'

importers:

  .:
    devDependencies:
      gpl-tool:
        specifier: 1.0.0
        version: 1.0.0

packages:

  gpl-tool@1.0.0:
    resolution: {integrity: sha512-AAAA}

  '@scope/lib@2.0.0':
    resolution: {integrity: sha512-BBBB}
"""

UV_LOCK = """\
version = 1
revision = 3
requires-python = ">=3.12"

[[package]]
name = "pytool"
version = "3.1.0"
source = { registry = "https://pypi.org/simple" }
"""

FILES: dict[str, str] = {
    "LICENSE": LICENSE_TEXT,
    "LICENSES/Apache-2.0.txt": LICENSE_TEXT,
    "LICENSES/CC-BY-SA-4.0.txt": "Creative Commons Attribution-ShareAlike 4.0\n",
    "NOTICE": "Example\n",
    "quality/licenses/header.toml": HEADER_TOML,
    "quality/licenses/allowed.txt": ALLOWED,
    "quality/licenses/dev-exceptions.txt": DEV_EXCEPTIONS,
    "package.json": '{"name": "fixture"}\n',
    "packages/core/src/index.ts": textwrap.dedent(
        """\
        // SPDX-License-Identifier: Apache-2.0
        // SPDX-FileCopyrightText: The Guildwork Authors
        export const value = 1;
        """
    ),
    "tools/run.py": textwrap.dedent(
        """\
        #!/usr/bin/env python3
        # SPDX-License-Identifier: Apache-2.0
        # SPDX-FileCopyrightText: The Guildwork Authors
        print("ok")
        """
    ),
    "README.md": textwrap.dedent(
        """\
        <!--
        SPDX-License-Identifier: Apache-2.0
        SPDX-FileCopyrightText: The Guildwork Authors
        -->

        # Fixture
        """
    ),
    "docs/adopted.md": ADOPTED_MD,
    "tools/tests/fixtures/sample.ts": "export const fixture = 1;\n",
    "data/notes.txt": "no comment form, not checked\n",
    "pnpm-lock.yaml": PNPM_LOCK,
    "uv.lock": UV_LOCK,
}


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def rules(findings: list[license_check.Finding]) -> list[str]:
    return [finding.rule for finding in findings]


class Fixture(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)  # noqa: S607
        for rel, text in FILES.items():
            write(self.root, rel, text)
        digest = hashlib.sha256(LICENSE_TEXT.encode()).hexdigest()
        write(self.root, "quality/licenses/license.sha256", f"{digest}  LICENSE\n")
        third_party_notices.write(self.root, [])

    def check(
        self, deps: list[Dependency] | None = None, regenerate: bool = True
    ) -> list[license_check.Finding]:
        """Findings with deps; regenerate first writes THIRD_PARTY_NOTICES for them."""
        deps = deps or []
        if regenerate:
            third_party_notices.write(self.root, deps)
        return license_check.check(self.root, deps=deps)

    def main(self, *args: str) -> int:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return license_check.main(["--root", str(self.root), *args])

    def only(self, rule: str, deps: list[Dependency] | None = None) -> license_check.Finding:
        findings = self.check(deps)
        self.assertEqual(rules(findings), [rule], [str(f) for f in findings])
        return findings[0]


def npm(name: str, license: str | None, runtime: bool, version: str = "1.0.0") -> Dependency:
    return Dependency("npm", name, version, license, runtime)


class TestLicense(Fixture):
    """All tests share one class: the plan names them TestLicense::<test>."""

    def test_clean_fixture_passes(self) -> None:
        self.assertEqual([str(f) for f in self.check()], [])

    def test_modified_license_file_fails(self) -> None:
        write(self.root, "LICENSE", LICENSE_TEXT + "Extra line\n")
        finding = self.only("license-file-modified")
        self.assertEqual((finding.path, finding.line), ("LICENSE", 1))

    def test_missing_license_checksum_exits_2(self) -> None:
        (self.root / "quality/licenses/license.sha256").unlink()
        self.assertEqual(self.main(), 2)

    def test_missing_spdx_header_fails(self) -> None:
        write(self.root, "packages/core/src/new.ts", "export const other = 2;\n")
        finding = self.only("spdx-header-missing")
        self.assertEqual(str(finding).split()[0], "packages/core/src/new.ts:1:1")

    def test_header_after_line_five_fails(self) -> None:
        write(
            self.root,
            "tools/late.py",
            "\n\n\n\n# SPDX-License-Identifier: Apache-2.0\n"
            "# SPDX-FileCopyrightText: The Guildwork Authors\n",
        )
        self.only("spdx-header-missing")

    def test_untracked_file_is_checked(self) -> None:
        # New files are checked before they are committed (git ls-files -o).
        write(self.root, "apps/x/main.mjs", "export {};\n")
        self.only("spdx-header-missing")

    def test_ignored_and_exempt_files_are_skipped(self) -> None:
        write(
            self.root,
            ".gitignore",
            "# SPDX-License-Identifier: Apache-2.0\n"
            "# SPDX-FileCopyrightText: The Guildwork Authors\nbuild/\n",
        )
        write(self.root, "build/out.js", "no header\n")
        write(self.root, "src/fixtures/deep/case.ts", "no header\n")
        write(self.root, "config/settings.json", "{}\n")
        self.assertEqual([str(f) for f in self.check()], [])

    def test_md_header_needs_block_comment(self) -> None:
        write(
            self.root,
            "docs/plain.md",
            "SPDX-License-Identifier: Apache-2.0\nSPDX-FileCopyrightText: The Guildwork Authors\n",
        )
        self.only("spdx-header-missing")

    def test_adopted_header_with_listed_license_passes(self) -> None:
        # The fixture file docs/adopted.md is CC-BY-SA-4.0 and listed in header.toml.
        self.assertNotIn("adopted-license-not-allowed", rules(self.check()))

    def test_adopted_header_with_allowed_license_needs_no_entry(self) -> None:
        write(self.root, "LICENSES/MIT.txt", "MIT License\n")
        write(
            self.root,
            "tools/vendored.py",
            "# SPDX-License-Identifier: MIT\n"
            "# SPDX-FileCopyrightText: Example Original Authors\n"
            "# Origin: example/lib@0123456789abcdef0123456789abcdef01234567:lib.py, modified\n",
        )
        self.assertEqual([str(f) for f in self.check()], [])

    def test_adopted_header_with_other_license_fails(self) -> None:
        write(self.root, "docs/other.md", ADOPTED_MD)
        finding = self.only("adopted-license-not-allowed")
        self.assertEqual((finding.path, finding.line), ("docs/other.md", 2))

    def test_adopted_entry_with_other_license_fails(self) -> None:
        write(self.root, "docs/adopted.md", ADOPTED_MD.replace("CC-BY-SA-4.0", "GPL-3.0-only"))
        self.only("adopted-license-not-allowed")

    def test_foreign_header_without_origin_fails(self) -> None:
        write(
            self.root,
            "tools/foreign.py",
            "# SPDX-License-Identifier: MIT\n# SPDX-FileCopyrightText: Someone Else\n",
        )
        self.only("spdx-header-missing")

    def test_adopted_entry_without_reason_exits_2(self) -> None:
        header = HEADER_TOML.replace(
            'reason = "Text adopted from a third party under its own license."', 'reason = " "'
        )
        write(self.root, "quality/licenses/header.toml", header)
        self.assertEqual(self.main(), 2)

    def test_unknown_key_in_header_toml_exits_2(self) -> None:
        write(self.root, "quality/licenses/header.toml", "max_line = 5\n" + HEADER_TOML)
        self.assertEqual(self.main(), 2)

    def test_gpl_runtime_dependency_fails(self) -> None:
        finding = self.only(
            "runtime-license-not-allowed", [npm("gpl-tool", "GPL-3.0-only", runtime=True)]
        )
        self.assertEqual(str(finding).split()[0], "pnpm-lock.yaml:13:3")

    def test_dev_exception_does_not_cover_runtime_dependency(self) -> None:
        exception = "gpl-tool@1.0.0\tGPL-3.0-only\tUsed only to build the docs.\n"
        write(self.root, "quality/licenses/dev-exceptions.txt", DEV_EXCEPTIONS + exception)
        self.only("runtime-license-not-allowed", [npm("gpl-tool", "GPL-3.0-only", runtime=True)])

    def test_unknown_runtime_license_fails(self) -> None:
        self.only("runtime-license-not-allowed", [npm("gpl-tool", None, runtime=True)])

    def test_dev_dependency_needs_exception_with_reason(self) -> None:
        dev = [npm("gpl-tool", "GPL-3.0-only", runtime=False)]
        self.only("dev-license-needs-exception", dev)
        exception = "gpl-tool@1.0.0\tGPL-3.0-only\tUsed only to build the docs, never shipped.\n"
        write(self.root, "quality/licenses/dev-exceptions.txt", DEV_EXCEPTIONS + exception)
        self.assertEqual([str(f) for f in self.check(dev)], [])

    def test_exception_is_per_version(self) -> None:
        exception = "gpl-tool@0.9.0\tGPL-3.0-only\tOlder version only.\n"
        write(self.root, "quality/licenses/dev-exceptions.txt", DEV_EXCEPTIONS + exception)
        self.only("dev-license-needs-exception", [npm("gpl-tool", "GPL-3.0-only", runtime=False)])

    def test_exception_without_reason_exits_2(self) -> None:
        for line in ("gpl-tool@1.0.0\tGPL-3.0-only\n", "gpl-tool@1.0.0\tGPL-3.0-only\t  \n"):
            with self.subTest(line=line):
                write(self.root, "quality/licenses/dev-exceptions.txt", DEV_EXCEPTIONS + line)
                self.assertEqual(self.main(), 2)

    def test_allowed_dev_dependency_passes(self) -> None:
        deps = [
            npm("@scope/lib", "MIT", runtime=False, version="2.0.0"),
            Dependency("python", "pytool", "3.1.0", "Apache-2.0 OR BSD-2-Clause", False),
        ]
        self.assertEqual([str(f) for f in self.check(deps)], [])

    def test_python_dev_finding_points_at_uv_lock(self) -> None:
        dev = [Dependency("python", "pytool", "3.1.0", "BSD", False)]
        finding = self.only("dev-license-needs-exception", dev)
        self.assertEqual(str(finding).split()[0], "uv.lock:6:1")

    def test_spdx_expressions(self) -> None:
        allowed = frozenset({"MIT", "Apache-2.0"})
        cases = {
            "MIT": True,
            "MIT OR GPL-3.0-only": True,
            "(MIT OR GPL-3.0-only) AND Apache-2.0": True,
            "MIT AND GPL-3.0-only": False,
            "Apache-2.0 WITH LLVM-exception": True,
            "mit or apache-2.0": False,
            "MIT OR": False,
            "(MIT": False,
            "": False,
        }
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(license_check.is_allowed(expression, allowed), expected)

    def test_agent_sdk_in_lockfile_fails(self) -> None:
        # ADR-39: the proprietary Claude Code packages never enter a lockfile.
        lock = PNPM_LOCK + "\n  '@anthropic-ai/claude-agent-sdk-linux-x64@0.2.0':\n"
        write(self.root, "pnpm-lock.yaml", lock)
        finding = self.only("forbidden-package")
        self.assertEqual(str(finding).split()[0], "pnpm-lock.yaml:19:4")

    def test_claude_code_in_any_lockfile_fails(self) -> None:
        write(self.root, "apps/x/pnpm-lock.yaml", "      '@anthropic-ai/claude-code':\n")
        self.only("forbidden-package")

    def test_claude_code_platform_package_fails(self) -> None:
        # The platform packages carry the native binary (optionalDependencies of
        # @anthropic-ai/claude-code 2.1.316 on the npm registry, read 2026-11-01).
        lock = PNPM_LOCK + "\n  '@anthropic-ai/claude-code-darwin-arm64@2.1.316':\n"
        write(self.root, "pnpm-lock.yaml", lock)
        finding = self.only("forbidden-package")
        self.assertIn("@anthropic-ai/claude-code-darwin-arm64", finding.message)

    def test_python_agent_sdk_in_uv_lock_fails(self) -> None:
        # PyPI claude-agent-sdk bundles the Claude Code binary; uv.lock names it normalized.
        lock = UV_LOCK.replace(
            'source = { registry = "https://pypi.org/simple" }\n',
            'source = { registry = "https://pypi.org/simple" }\n'
            'dependencies = [\n    { name = "claude-agent-sdk" },\n]\n\n'
            '[[package]]\nname = "claude-agent-sdk"\nversion = "0.2.176"\n',
        )
        write(self.root, "uv.lock", lock)
        findings = self.check()
        self.assertEqual(rules(findings), ["forbidden-package", "forbidden-package"])
        self.assertEqual([str(f).split()[0] for f in findings], ["uv.lock:10:15", "uv.lock:14:9"])

    def test_python_claude_code_sdk_in_uv_lock_fails(self) -> None:
        write(self.root, "uv.lock", UV_LOCK + '\n[[package]]\nname = "claude-code-sdk"\n')
        self.only("forbidden-package")

    def test_forbidden_names_cover_npm_and_pypi(self) -> None:
        self.assertEqual(
            license_check.FORBIDDEN_NPM,
            (
                "@anthropic-ai/claude-code",
                "@anthropic-ai/claude-code-*",
                "@anthropic-ai/claude-agent-sdk*",
            ),
        )
        self.assertEqual(license_check.FORBIDDEN_PYPI, ("claude-agent-sdk", "claude-code-sdk"))

    def test_other_anthropic_packages_pass(self) -> None:
        lock = PNPM_LOCK + "\n  '@anthropic-ai/sdk@1.0.0':\n"
        write(self.root, "pnpm-lock.yaml", lock)
        write(self.root, "uv.lock", UV_LOCK + '\n[[package]]\nname = "anthropic"\n')
        self.assertEqual([str(f) for f in self.check()], [])

    def test_missing_licenses_text_fails(self) -> None:
        (self.root / "LICENSES/CC-BY-SA-4.0.txt").unlink()
        finding = self.only("license-text-missing")
        self.assertEqual(str(finding).split()[0], "docs/adopted.md:2:1")

    def test_runtime_dependency_license_needs_text(self) -> None:
        finding = self.only("license-text-missing", [npm("gpl-tool", "MIT", runtime=True)])
        self.assertIn("LICENSES/MIT.txt", finding.message)

    def test_dev_dependency_license_needs_no_text(self) -> None:
        self.assertEqual([str(f) for f in self.check([npm("gpl-tool", "MIT", False)])], [])

    def test_outdated_notices_fail(self) -> None:
        write(self.root, "LICENSES/MIT.txt", "MIT License\n")
        deps = [npm("gpl-tool", "MIT", runtime=True)]
        findings = self.check(deps, regenerate=False)
        self.assertEqual(rules(findings), ["notices-outdated"])

    def test_json_report(self) -> None:
        write(self.root, "LICENSE", "changed\n")
        report = self.root / ".reports/license_check.json"
        with unittest.mock.patch.object(license_check, "collect_dependencies", return_value=[]):
            self.assertEqual(self.main("--json", str(report)), 1)
        data = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual([item["rule"] for item in data], ["license-file-modified"])


if __name__ == "__main__":
    unittest.main()
