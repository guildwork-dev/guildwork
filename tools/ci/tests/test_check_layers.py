# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/ci/check_layers.py.

Each test builds a small fixture workspace in a temporary directory: a
quality/layers.toml and a few packages with package.json and sources. The
fixture starts clean (exit 0) and each test adds exactly one violation. The
last test runs the checker on the real repository.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.ci import check_layers

REPO_ROOT = Path(__file__).resolve().parents[3]

LAYERS_TOML = """\
[groups]
plugins = ["plugins/*"]

[[package]]
path = "packages/core"
may_import = []

[[package]]
path = "packages/contracts"
may_import = ["@guildwork/core"]

[[package]]
path = "packages/db"
may_import = ["@guildwork/core", "@guildwork/contracts"]

[[package]]
path = "packages/testkit"
may_import = ["@guildwork/core", "@guildwork/contracts"]

[[package]]
path = "plugins/*"
may_import = ["@guildwork/core", "@guildwork/contracts"]

[[package]]
path = "apps/worker"
may_import = ["@guildwork/core", "@guildwork/contracts", "group:plugins"]

[[package]]
path = "apps/control-plane"
may_import = ["@guildwork/core", "@guildwork/contracts", "@guildwork/db", "group:plugins"]

[[package]]
path = "apps/admin-ui"
may_import = ["@guildwork/contracts"]
type_only = ["@guildwork/contracts"]

[test_only]
packages = ["@guildwork/testkit"]
subpaths = ["@guildwork/db/testing"]
file_globs = ["**/*.test.ts", "**/test/**", "eval/suites/**", "**/vitest.config.ts"]
"""

# path -> (package name, dependencies)
PACKAGES: dict[str, tuple[str, dict[str, str]]] = {
    "packages/core": ("@guildwork/core", {}),
    "packages/contracts": ("@guildwork/contracts", {"@guildwork/core": "workspace:*"}),
    "packages/db": (
        "@guildwork/db",
        {"@guildwork/core": "workspace:*", "@guildwork/contracts": "workspace:*"},
    ),
    "packages/testkit": ("@guildwork/testkit", {"@guildwork/core": "workspace:*"}),
    "plugins/github": ("@guildwork/plugin-github", {"@guildwork/core": "workspace:*"}),
    "apps/worker": (
        "@guildwork/worker",
        {"@guildwork/core": "workspace:*", "@guildwork/plugin-github": "workspace:*"},
    ),
    "apps/control-plane": (
        "@guildwork/control-plane",
        {"@guildwork/core": "workspace:*", "@guildwork/db": "workspace:*"},
    ),
    "apps/admin-ui": ("@guildwork/admin-ui", {}),
}

# Clean sources: every allowed form of import appears once.
SOURCES: dict[str, str] = {
    "packages/core/src/index.ts": 'export const VERSION = "0.0.0";\n',
    "packages/core/src/index.test.ts": 'import * as core from "@guildwork/core";\n',
    "packages/contracts/src/index.ts": 'export { VERSION } from "@guildwork/core";\n',
    "packages/db/src/index.ts": 'import type { VERSION } from "@guildwork/contracts";\n',
    "packages/db/src/testing.ts": 'export * from "./index.js";\n',
    "packages/testkit/src/index.ts": 'import "@guildwork/core";\n',
    "plugins/github/src/index.ts": 'const core = await import("@guildwork/core");\n',
    "apps/worker/src/main.ts": textwrap.dedent(
        """\
        // import { db } from "@guildwork/db"; comments do not count
        import { VERSION } from "@guildwork/core";
        import * as github from "@guildwork/plugin-github";
        import { helper } from "./helper.js";
        const text = "import('@guildwork/db')";
        """
    ),
    "apps/worker/src/helper.ts": 'export const helper = "ok";\n',
    "apps/worker/test/integration/run.int.test.ts": textwrap.dedent(
        """\
        import { startPostgres } from "@guildwork/testkit";
        """
    ),
    "apps/control-plane/src/main.ts": textwrap.dedent(
        """\
        import { migrate } from "@guildwork/db";
        export type { Plugin } from "@guildwork/plugin-github";
        """
    ),
    "apps/control-plane/src/db.test.ts": 'import { roleUrls } from "@guildwork/db/testing";\n',
    "apps/admin-ui/src/main.tsx": textwrap.dedent(
        """\
        import type { Manifest } from "@guildwork/contracts";
        export type { Event } from "@guildwork/contracts";
        type Api = typeof import("@guildwork/contracts");
        """
    ),
}


def write_workspace(root: Path) -> None:
    (root / "quality").mkdir(parents=True)
    (root / "quality/layers.toml").write_text(LAYERS_TOML, encoding="utf-8")
    for path, (name, deps) in PACKAGES.items():
        package = {"name": name, "version": "0.0.0", "private": True, "type": "module"}
        if deps:
            package["dependencies"] = deps
        if path == "apps/worker":
            package["devDependencies"] = {"@guildwork/testkit": "workspace:*"}
        (root / path).mkdir(parents=True)
        (root / path / "package.json").write_text(
            json.dumps(package, indent=2) + "\n", encoding="utf-8"
        )
    for path, text in SOURCES.items():
        write(root, path, text)


def write(root: Path, path: str, text: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def add_dependency(root: Path, package_dir: str, field: str, name: str) -> None:
    path = root / package_dir / "package.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault(field, {})[name] = "workspace:*"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def run(root: Path) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = check_layers.main(["--root", str(root)])
    return code, out.getvalue(), err.getvalue()


class TestLayers(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        write_workspace(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def assert_finding(self, out: str, location: str, rule: str) -> None:
        lines = out.splitlines()
        self.assertTrue(
            any(line.startswith(f"{location} {rule} ") for line in lines),
            f"no finding '{location} {rule}' in:\n{out}",
        )

    def test_clean_fixture_passes(self) -> None:
        code, out, err = run(self.root)
        self.assertEqual((code, out, err), (0, "", ""))

    def test_worker_importing_db_fails(self) -> None:
        write(self.root, "apps/worker/src/store.ts", 'import { open } from "@guildwork/db";\n')
        code, out, _ = run(self.root)
        self.assertEqual(code, 1)
        self.assert_finding(out, "apps/worker/src/store.ts:1:22", "forbidden-import")

    def test_worker_dependency_on_db_fails(self) -> None:
        add_dependency(self.root, "apps/worker", "dependencies", "@guildwork/db")
        code, out, _ = run(self.root)
        self.assertEqual(code, 1)
        self.assertRegex(out, r"apps/worker/package\.json:\d+:\d+ forbidden-dependency ")

    def test_dynamic_import_and_export_from_are_checked(self) -> None:
        write(
            self.root,
            "apps/worker/src/late.ts",
            'export * from "@guildwork/db";\nconst db = await import(\n  "@guildwork/db"\n);\n',
        )
        code, out, _ = run(self.root)
        self.assertEqual(code, 1)
        self.assert_finding(out, "apps/worker/src/late.ts:1:15", "forbidden-import")
        self.assert_finding(out, "apps/worker/src/late.ts:3:3", "forbidden-import")

    def test_type_import_is_checked_too(self) -> None:
        write(
            self.root, "plugins/github/src/types.ts", 'import type { Row } from "@guildwork/db";\n'
        )
        code, out, _ = run(self.root)
        self.assertEqual(code, 1)
        self.assert_finding(out, "plugins/github/src/types.ts:1:26", "forbidden-import")

    def test_testkit_in_production_file_fails(self) -> None:
        write(self.root, "apps/worker/src/boot.ts", 'import { fake } from "@guildwork/testkit";\n')
        code, out, _ = run(self.root)
        self.assertEqual(code, 1)
        self.assert_finding(out, "apps/worker/src/boot.ts:1:22", "test-only-import")

    def test_testkit_as_runtime_dependency_fails(self) -> None:
        add_dependency(self.root, "apps/worker", "dependencies", "@guildwork/testkit")
        code, out, _ = run(self.root)
        self.assertEqual(code, 1)
        self.assertRegex(out, r"apps/worker/package\.json:\d+:\d+ test-only-dependency ")

    def test_db_testing_subpath_in_production_file_fails(self) -> None:
        write(
            self.root,
            "apps/control-plane/src/seed.ts",
            'import { roleUrls } from "@guildwork/db/testing";\n',
        )
        code, out, _ = run(self.root)
        self.assertEqual(code, 1)
        self.assert_finding(out, "apps/control-plane/src/seed.ts:1:26", "test-only-import")

    def test_relative_import_across_packages_fails(self) -> None:
        write(
            self.root,
            "apps/worker/src/sneak.ts",
            'import { migrate } from "../../../packages/db/src/index.js";\n',
        )
        code, out, _ = run(self.root)
        self.assertEqual(code, 1)
        self.assert_finding(out, "apps/worker/src/sneak.ts:1:25", "relative-import-across-packages")

    def test_admin_ui_value_import_from_contracts_fails(self) -> None:
        write(
            self.root,
            "apps/admin-ui/src/schema.ts",
            'import type { A } from "@guildwork/contracts";\n'
            'import { compileSchema } from "@guildwork/contracts";\n',
        )
        code, out, _ = run(self.root)
        self.assertEqual(code, 1)
        self.assert_finding(out, "apps/admin-ui/src/schema.ts:2:31", "type-only-import")
        self.assertNotIn("schema.ts:1:", out)

    def test_inline_type_modifier_is_a_value_import(self) -> None:
        # With verbatimModuleSyntax, `import { type A }` keeps the import at runtime.
        write(
            self.root,
            "apps/admin-ui/src/inline.ts",
            'import { type A } from "@guildwork/contracts";\n',
        )
        code, out, _ = run(self.root)
        self.assertEqual(code, 1)
        self.assert_finding(out, "apps/admin-ui/src/inline.ts:1:24", "type-only-import")

    def test_dependency_cycle_fails(self) -> None:
        layers = self.root / "quality/layers.toml"
        text = layers.read_text(encoding="utf-8").replace(
            'path = "packages/core"\nmay_import = []',
            'path = "packages/core"\nmay_import = ["@guildwork/contracts"]',
        )
        layers.write_text(text, encoding="utf-8")
        write(self.root, "packages/core/src/loop.ts", 'import "@guildwork/contracts";\n')
        code, out, _ = run(self.root)
        self.assertEqual(code, 1)
        self.assertIn("dependency-cycle", out)
        self.assertIn("@guildwork/contracts", out)

    def test_package_missing_in_layers_toml_exits_2(self) -> None:
        write(self.root, "services/dummy/package.json", '{"name": "@guildwork/service-dummy"}\n')
        code, out, err = run(self.root)
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("layers.unknown_package path=services/dummy", err)

    def test_unknown_group_exits_2(self) -> None:
        layers = self.root / "quality/layers.toml"
        text = layers.read_text(encoding="utf-8").replace("group:plugins", "group:nope", 1)
        layers.write_text(text, encoding="utf-8")
        code, _, err = run(self.root)
        self.assertEqual(code, 2)
        self.assertIn("layers.config_invalid", err)

    def test_repository_passes(self) -> None:
        code, out, err = run(REPO_ROOT)
        self.assertEqual((code, out, err), (0, "", ""))


if __name__ == "__main__":
    unittest.main()
