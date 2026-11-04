# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/ci/license_inventory.py.

The pnpm input follows the output of `pnpm licenses list --json` of pnpm
12.16.1, recorded on 2026-11-01: an object keyed by license expression, each
value a list of packages with name, versions, paths, license and author.
"""

from __future__ import annotations

import json
import tempfile
import textwrap
import unittest
import unittest.mock
from pathlib import Path

from tools.ci import license_inventory
from tools.ci.license_inventory import Dependency


def pnpm_entry(name: str, version: str, license: str, path: str) -> dict[str, object]:
    return {
        "name": name,
        "versions": [version],
        "paths": [path],
        "license": license,
        "author": "Example Author",
        "homepage": "https://example.org",
        "description": "Example",
    }


UV_LOCK = """\
version = 1
revision = 3
requires-python = ">=3.12, <3.13"

[[package]]
name = "guildwork-tools"
version = "0.0.0"
source = { virtual = "." }
dependencies = [
    { name = "run-lib" },
]

[package.dev-dependencies]
dev = [
    { name = "dev-tool" },
]

[[package]]
name = "run-lib"
version = "1.0.0"
source = { registry = "https://pypi.org/simple" }
dependencies = [
    { name = "deep-lib" },
]

[[package]]
name = "deep-lib"
version = "2.0.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "dev-tool"
version = "3.0.0"
source = { registry = "https://pypi.org/simple" }
dependencies = [
    { name = "deep-lib" },
]
"""


class TestNpm(unittest.TestCase):
    def test_parses_pnpm_licenses_json(self) -> None:
        all_json = json.dumps(
            {
                "MIT": [pnpm_entry("left-pad", "1.3.0", "MIT", "/x/left-pad")],
                "MIT OR Apache-2.0": [
                    pnpm_entry("@biomejs/biome", "2.6.4", "MIT OR Apache-2.0", "/x/biome")
                ],
                "Apache-2.0": [
                    pnpm_entry("@guildwork/core", "0.0.0", "Apache-2.0", "/x/core"),
                ],
            }
        )
        prod_json = json.dumps({"MIT": [pnpm_entry("left-pad", "1.3.0", "MIT", "/x/left-pad")]})
        deps = license_inventory.parse_pnpm(all_json, prod_json)
        self.assertEqual(
            [(d.name, d.version, d.license, d.runtime) for d in deps],
            [
                ("@biomejs/biome", "2.6.4", "MIT OR Apache-2.0", False),
                ("left-pad", "1.3.0", "MIT", True),
            ],
        )
        self.assertEqual(deps[1].author, "Example Author")

    def test_empty_prod_output(self) -> None:
        deps = license_inventory.parse_pnpm(
            json.dumps({"ISC": [pnpm_entry("semver", "7.8.5", "ISC", "/x/semver")]}), "{}"
        )
        self.assertEqual([d.runtime for d in deps], [False])

    def test_invalid_pnpm_output_is_a_config_error(self) -> None:
        with self.assertRaises(license_inventory.InventoryError):
            license_inventory.parse_pnpm("not json", "{}")

    def test_pnpm_runs_recursively_over_the_workspace(self) -> None:
        # Without --recursive pnpm lists only the root project, not packages/*.
        calls: list[list[str]] = []

        def run(command: list[str], root: Path) -> str:
            calls.append(command)
            return "{}"

        with unittest.mock.patch.object(license_inventory, "_run", side_effect=run):
            license_inventory.npm_dependencies(Path("."), pnpm=["pnpm"])
        self.assertEqual(
            calls,
            [
                ["pnpm", "--recursive", "licenses", "list", "--json"],
                ["pnpm", "--recursive", "licenses", "list", "--json", "--prod"],
            ],
        )

    def test_failing_pnpm_is_a_config_error(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            self.assertRaises(license_inventory.InventoryError),
        ):
            license_inventory.npm_dependencies(Path(tmp), pnpm=["false"])


class TestPython(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "uv.lock").write_text(UV_LOCK, encoding="utf-8")
        self.site = self.root / ".venv/lib/python3.12/site-packages"
        self.metadata("run_lib", "1.0.0", "License-Expression: MIT\n")
        self.metadata("deep_lib", "2.0.0", "License: BSD\nClassifier: License :: OSI Approved\n")
        self.metadata("dev_tool", "3.0.0", "")

    def metadata(self, name: str, version: str, fields: str) -> Path:
        info = self.site / f"{name}-{version}.dist-info"
        info.mkdir(parents=True)
        text = f"Metadata-Version: 2.4\nName: {name}\nVersion: {version}\n{fields}\nBody\n"
        (info / "METADATA").write_text(text, encoding="utf-8")
        return info

    def test_runtime_closure_from_uv_lock(self) -> None:
        deps = license_inventory.python_dependencies(self.root)
        self.assertEqual(
            [(d.name, d.version, d.runtime) for d in deps],
            [("deep-lib", "2.0.0", True), ("dev-tool", "3.0.0", False), ("run-lib", "1.0.0", True)],
        )

    def test_license_from_metadata(self) -> None:
        licenses = {d.name: d.license for d in license_inventory.python_dependencies(self.root)}
        self.assertEqual(licenses, {"run-lib": "MIT", "deep-lib": "BSD", "dev-tool": None})

    def test_license_files_from_dist_info(self) -> None:
        info = self.site / "run_lib-1.0.0.dist-info"
        (info / "licenses").mkdir()
        (info / "licenses/LICENSE").write_text("Copyright (c) Example\n", encoding="utf-8")
        deps = {d.name: d for d in license_inventory.python_dependencies(self.root)}
        self.assertEqual([Path(p).name for p in deps["run-lib"].license_files], ["LICENSE"])

    def test_missing_venv_is_a_config_error(self) -> None:
        for child in sorted(self.site.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink()
            else:
                child.rmdir()
        self.site.rmdir()
        with self.assertRaises(license_inventory.InventoryError):
            license_inventory.python_dependencies(self.root)


class TestAdopted(unittest.TestCase):
    def test_reads_adopted_headers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "doc.md").write_text(
                textwrap.dedent(
                    """\
                    <!--
                    SPDX-License-Identifier: CC-BY-SA-4.0
                    SPDX-FileCopyrightText: Original Authors
                    Origin: example/repo@0123456789abcdef0123456789abcdef01234567:a.md, modified
                    -->
                    """
                ),
                encoding="utf-8",
            )
            (root / "own.py").write_text(
                "# SPDX-License-Identifier: Apache-2.0\n"
                "# SPDX-FileCopyrightText: The Guildwork Authors\n",
                encoding="utf-8",
            )
            parts = license_inventory.adopted_files(root, ["doc.md", "own.py", "data.json"])
        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0].path, "doc.md")
        self.assertEqual(parts[0].license, "CC-BY-SA-4.0")
        self.assertEqual(parts[0].copyrights, ("Original Authors",))
        self.assertTrue(parts[0].origin.startswith("example/repo@"))


class TestDependency(unittest.TestCase):
    def test_key_and_lockfile(self) -> None:
        dep = Dependency("npm", "@scope/lib", "1.0.0", "MIT", True)
        self.assertEqual(dep.key, "@scope/lib@1.0.0")
        self.assertEqual(dep.lockfile, "pnpm-lock.yaml")
        self.assertEqual(Dependency("python", "x", "1", None, False).lockfile, "uv.lock")


if __name__ == "__main__":
    unittest.main()
