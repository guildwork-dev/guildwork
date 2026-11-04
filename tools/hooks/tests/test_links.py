# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/hooks/links.py.

Every test builds a temporary git repository with the real
quality/text/private-path-patterns.txt and the Markdown files it needs; only
tracked files count as link targets. Home paths are assembled at run time, so
this file passes the deny-list scan and the text rules itself.
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.hooks import links

REPO_ROOT = Path(__file__).resolve().parents[3]
PATTERNS = "quality/text/private-path-patterns.txt"
HOME_LINK = "/" + "Users/alice/notes.md"


class Repo:
    def __init__(self, base: Path) -> None:
        self.root = base
        target = self.root / PATTERNS
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO_ROOT / PATTERNS, target)
        self.git("init", "-q")

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.root), *args], check=True)  # noqa: S603, S607

    def write(self, path: str, text: str, *, track: bool = True) -> str:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        if track:
            self.git("add", path)
        return path

    def rules(self, *paths: str) -> list[str]:
        patterns = links.load_patterns(self.root)
        found = links.check_files(self.root, paths, patterns)
        return [f"{f.path}:{f.line}:{f.column} {f.rule}" for f in found]


class LinksTestCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Repo(Path(tmp.name))


class TestLinks(LinksTestCase):
    def test_accepts_existing_file_and_anchor(self) -> None:
        self.repo.write("docs/guide.md", "# Guide\n\n## Set up the tools\n")
        path = self.repo.write(
            "README.md",
            "See [guide](docs/guide.md), [setup](docs/guide.md#set-up-the-tools),\n"
            "[top](#readme) and [the docs](docs/).\n\n# Readme\n",
        )
        self.assertEqual(self.repo.rules(path), [])

    def test_flags_missing_file(self) -> None:
        path = self.repo.write("README.md", "See [guide](docs/missing.md).\n")
        self.assertEqual(self.repo.rules(path), ["README.md:1:5 link-missing-file"])

    def test_untracked_target_counts_as_missing(self) -> None:
        self.repo.write("docs/local.md", "# Local\n", track=False)
        path = self.repo.write("README.md", "See [local](docs/local.md).\n")
        self.assertEqual(self.repo.rules(path), ["README.md:1:5 link-missing-file"])

    def test_flags_missing_anchor(self) -> None:
        self.repo.write("docs/guide.md", "# Guide\n\n## Set up\n")
        path = self.repo.write(
            "docs/index.md",
            "# Index\n\n[a](guide.md#install) [b](#index) [c](#nothing-here)\n",
        )
        self.assertEqual(
            self.repo.rules(path),
            ["docs/index.md:3:1 link-missing-anchor", "docs/index.md:3:35 link-missing-anchor"],
        )

    def test_anchor_slugs_follow_the_hoster(self) -> None:
        self.repo.write(
            "docs/design.md",
            "# Design\n\n"
            "## 2.10 Check tools (`make check`)\n\n"
            "## Notes\n\n## Notes\n\n"
            "## [Linked](https://example.org) title\n\n"
            "Setext title\n------------\n\n"
            '<a id="custom-anchor"></a>\n\n'
            "```text\n# not a heading\n```\n",
        )
        good = self.repo.write(
            "a.md",
            "[1](docs/design.md#210-check-tools-make-check)\n"
            "[2](docs/design.md#notes-1)\n"
            "[3](docs/design.md#linked-title)\n"
            "[4](docs/design.md#setext-title)\n"
            "[5](docs/design.md#custom-anchor)\n",
        )
        bad = self.repo.write("b.md", "[6](docs/design.md#not-a-heading)\n")
        self.assertEqual(self.repo.rules(good, bad), ["b.md:1:1 link-missing-anchor"])

    def test_does_not_check_anchors_of_other_files(self) -> None:
        self.repo.write("tools/run.py", "print()\n")
        path = self.repo.write("a.md", "[line](tools/run.py#L1)\n")
        self.assertEqual(self.repo.rules(path), [])

    def test_flags_link_to_private_path(self) -> None:
        path = self.repo.write(
            "docs/a.md",
            f"[home]({HOME_LINK})\n"
            "[plan](../docs/architektur/README.md)\n"
            "[design](feinentwurf/00.md)\n"
            "[local](file:///tmp/x.md)\n",
        )
        self.assertEqual(
            self.repo.rules(path),
            [
                "docs/a.md:1:1 link-private-path",
                "docs/a.md:2:1 link-private-path",
                "docs/a.md:3:1 link-private-path",
                "docs/a.md:4:1 link-private-path",
            ],
        )

    def test_private_path_target_is_not_printed(self) -> None:
        path = self.repo.write("docs/a.md", f"[home]({HOME_LINK})\n")
        patterns = links.load_patterns(self.repo.root)
        found = links.check_files(self.repo.root, [path], patterns)
        self.assertEqual(len(found), 1)
        self.assertNotIn("alice", str(found[0]))
        self.assertRegex(str(found[0]), r"link-private-path target-[0-9a-f]{12}$")

    def test_flags_resolved_private_path(self) -> None:
        # The link reaches docs/feinentwurf/ through a relative path.
        path = self.repo.write("docs/b/a.md", "[design](../feinentwurf/00.md)\n")
        self.assertEqual(self.repo.rules(path), ["docs/b/a.md:1:1 link-private-path"])

    def test_flags_link_outside_repo(self) -> None:
        path = self.repo.write("a.md", "[up](../other-repo/README.md)\n")
        self.assertEqual(self.repo.rules(path), ["a.md:1:1 link-outside-repo"])

    def test_ignores_external_links_and_code(self) -> None:
        path = self.repo.write(
            "a.md",
            "[web](https://example.org/x.md) [mail](mailto:a@example.org)\n"
            "`[x](missing.md)`\n\n```md\n[y](missing.md)\n```\n",
        )
        self.assertEqual(self.repo.rules(path), [])

    def test_checks_reference_definitions_images_and_html(self) -> None:
        self.repo.write("logo.png", "png\n")
        path = self.repo.write(
            "a.md",
            "![logo](logo.png) ![gone](gone.png)\n\n"
            "[ref]: missing.md\n"
            '<a href="nowhere.md">x</a>\n',
        )
        self.assertEqual(
            self.repo.rules(path),
            [
                "a.md:1:19 link-missing-file",
                "a.md:3:1 link-missing-file",
                "a.md:4:1 link-missing-file",
            ],
        )

    def test_footnotes_are_no_links(self) -> None:
        path = self.repo.write("a.md", "Text.[^1]\n\n[^1]: See the docs.\n")
        self.assertEqual(self.repo.rules(path), [])

    def test_root_relative_and_encoded_links(self) -> None:
        self.repo.write("docs/my file.md", "# Title\n")
        path = self.repo.write(
            "docs/sub/a.md", "[1](/docs/my%20file.md#title) [2](<../my file.md>)\n"
        )
        self.assertEqual(self.repo.rules(path), [])


class TestLinksMain(LinksTestCase):
    def run_main(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = links.main(["--root", str(self.repo.root), *args])
        return code, out.getvalue(), err.getvalue()

    def test_checks_tracked_markdown_and_writes_report(self) -> None:
        self.repo.write("a.md", "[x](missing.md)\n")
        self.repo.write("notes.txt", "[x](missing.md)\n")
        self.repo.write("b.md", "[x](missing.md)\n", track=False)
        report = self.repo.root / ".reports" / "links.json"
        code, out, _ = self.run_main("--json", str(report))
        self.assertEqual(code, 1)
        self.assertIn("a.md:1:1 link-missing-file", out)
        self.assertNotIn("notes.txt", out)
        self.assertNotIn("b.md", out)
        data = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(data["tool"], "links")
        self.assertEqual([f["rule"] for f in data["findings"]], ["link-missing-file"])

    def test_clean_repository_exits_zero(self) -> None:
        self.repo.write("a.md", "# A\n\n[self](#a)\n")
        code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("0 findings", out)

    def test_accepts_absolute_path_arguments(self) -> None:
        self.repo.write("CONTRIBUTING.md", "# Contributing\n")
        path = self.repo.write("docs/a.md", "[c](../CONTRIBUTING.md)\n")
        code, out, _ = self.run_main(str(self.repo.root / path))
        self.assertEqual(code, 0, out)

    def test_invalid_pattern_exits_two_without_report(self) -> None:
        self.repo.write(PATTERNS, "re(\n", track=False)
        report = self.repo.root / ".reports" / "links.json"
        code, out, err = self.run_main("--json", str(report))
        self.assertEqual(code, 2)
        self.assertIn("links.config_invalid", err)
        self.assertEqual(out, "")
        self.assertFalse(report.exists())


class TestRepoConfig(unittest.TestCase):
    def test_real_patterns_load(self) -> None:
        patterns = links.load_patterns(REPO_ROOT)
        self.assertTrue(patterns)


if __name__ == "__main__":
    unittest.main()
