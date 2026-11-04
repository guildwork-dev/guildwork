# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/ci/new_package.py and tools/ci/spdx_header.py.

Each test copies the real quality/layers.toml, pnpm-workspace.yaml and the
root tsconfig.json into a temporary directory with a minimal packages/core,
runs the generator there and checks the result with check_layers.py and
spdx_header.has_header.
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.ci import check_layers, new_package, spdx_header

REPO_ROOT = Path(__file__).resolve().parents[3]
COPIED = ("quality/layers.toml", "pnpm-workspace.yaml", "tsconfig.json")


def run_generator(root: Path, *args: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = new_package.main(["--root", str(root), *args])
    return code, out.getvalue(), err.getvalue()


def run_layers(root: Path) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = check_layers.main(["--root", str(root)])
    return code, out.getvalue(), err.getvalue()


def snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


class TestNewPackage(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for path in COPIED:
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / path, self.root / path)
        core = self.root / "packages/core"
        (core / "src").mkdir(parents=True)
        (core / "package.json").write_text('{"name": "@guildwork/core"}\n', encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_generated_package_passes_layers_and_license_headers(self) -> None:
        code, out, err = run_generator(self.root, "packages/widget-kit")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("new_package.created path=packages/widget-kit", out)

        self.assertEqual(run_layers(self.root), (0, "", ""))

        package_dir = self.root / "packages/widget-kit"
        files = sorted(p for p in package_dir.rglob("*") if p.is_file())
        names = [p.relative_to(package_dir).as_posix() for p in files]
        self.assertEqual(
            names,
            ["README.md", "package.json", "src/index.test.ts", "src/index.ts", "tsconfig.json"],
        )
        for path in files:
            if path.suffix == ".json":
                continue  # JSON has no comments; exempt from the header rule
            text = path.read_text(encoding="utf-8")
            self.assertTrue(spdx_header.has_header(path, text), f"no SPDX header in {path}")

        manifest = json.loads((package_dir / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "@guildwork/widget-kit")
        self.assertEqual(manifest["exports"]["."]["@guildwork/source"], "./src/index.ts")

        layers = check_layers.load_layers(self.root / "quality/layers.toml")
        entry = [e for e in layers.entries if e.path == "packages/widget-kit"]
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry[0].may_import, ("@guildwork/core",))

        tsconfig = json.loads((self.root / "tsconfig.json").read_text(encoding="utf-8"))
        self.assertIn({"path": "./packages/widget-kit"}, tsconfig["references"])

    def test_location_prefix_and_glob_entry(self) -> None:
        before = (self.root / "quality/layers.toml").read_bytes()
        code, _, err = run_generator(self.root, "plugins/github")
        self.assertEqual((code, err), (0, ""))
        manifest = json.loads(
            (self.root / "plugins/github/package.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "@guildwork/plugin-github")
        # plugins/* already covers the package; layers.toml stays as it is.
        self.assertEqual((self.root / "quality/layers.toml").read_bytes(), before)
        tsconfig = (self.root / "plugins/github/tsconfig.json").read_text(encoding="utf-8")
        self.assertIn('"extends": "../../tsconfig.base.json"', tsconfig)
        self.assertEqual(run_layers(self.root), (0, "", ""))

    def test_nested_location_uses_relative_base_config(self) -> None:
        code, _, _ = run_generator(self.root, "eval/adapters/harbor")
        self.assertEqual(code, 0)
        tsconfig = (self.root / "eval/adapters/harbor/tsconfig.json").read_text(encoding="utf-8")
        self.assertIn('"extends": "../../../tsconfig.base.json"', tsconfig)
        manifest = json.loads(
            (self.root / "eval/adapters/harbor/package.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "@guildwork/eval-adapter-harbor")
        self.assertEqual(run_layers(self.root), (0, "", ""))

    def assert_refused(self, *args: str) -> str:
        before = snapshot(self.root)
        code, out, err = run_generator(self.root, *args)
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(snapshot(self.root), before, "nothing may be written")
        return err

    def test_invalid_name_exits_2(self) -> None:
        for target in ("packages/Widget", "packages/x", "packages/-a", "packages/a_b"):
            with self.subTest(target=target):
                self.assertIn("new_package.invalid", self.assert_refused(target))

    def test_unknown_location_exits_2(self) -> None:
        for target in ("lib/widget", "widget", "packages/core/inner", "../packages/escape"):
            with self.subTest(target=target):
                self.assertIn("new_package.invalid", self.assert_refused(target))

    def test_existing_directory_exits_2(self) -> None:
        self.assertIn("exists", self.assert_refused("packages/core"))


class TestSpdxHeader(unittest.TestCase):
    def test_render_and_detect(self) -> None:
        for name in ("a.ts", "b.py", "c.md", "Makefile", "d.sql"):
            with self.subTest(name=name):
                path = Path(name)
                text = spdx_header.render(path) + "\nbody\n"
                self.assertTrue(spdx_header.has_header(path, text))
                self.assertFalse(spdx_header.has_header(path, "body\n"))

    def test_header_after_max_line_is_missing(self) -> None:
        path = Path("a.ts")
        text = "\n" * spdx_header.MAX_LINE + spdx_header.render(path)
        self.assertFalse(spdx_header.has_header(path, text))

    def test_repository_tool_files_have_headers(self) -> None:
        for path in sorted((REPO_ROOT / "tools/ci").rglob("*.py")):
            with self.subTest(path=path.name):
                self.assertTrue(spdx_header.has_header(path, path.read_text(encoding="utf-8")))

    def test_unknown_suffix_raises(self) -> None:
        with self.assertRaises(ValueError):
            spdx_header.render(Path("a.unknown"))


if __name__ == "__main__":
    unittest.main()
