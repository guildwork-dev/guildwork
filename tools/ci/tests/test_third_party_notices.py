# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/ci/third_party_notices.py.

The fixture is a git repository with one adopted file and one own file; the
dependencies are passed in as data, their license files live in the fixture.
"""

from __future__ import annotations

import contextlib
import io
import subprocess
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from tools.ci import third_party_notices
from tools.ci.license_inventory import Dependency

ADOPTED = """\
<!--
SPDX-License-Identifier: CC-BY-SA-4.0
SPDX-FileCopyrightText: Original Authors
SPDX-FileCopyrightText: The Guildwork Authors
Origin: example/repo@0123456789abcdef0123456789abcdef01234567:a.md, modified
-->
"""

OWN = "# SPDX-License-Identifier: Apache-2.0\n# SPDX-FileCopyrightText: The Guildwork Authors\n"


class TestNotices(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)  # noqa: S607
        (self.root / "CODE_OF_CONDUCT.md").write_text(ADOPTED, encoding="utf-8")
        (self.root / "tool.py").write_text(OWN, encoding="utf-8")
        package = self.root / "node_modules/left-pad"
        package.mkdir(parents=True)
        (package / "LICENSE").write_text(
            "MIT License\n\nCopyright (c) 2018 Example Author\n\nPermission is hereby granted\n",
            encoding="utf-8",
        )
        self.deps = [
            Dependency(
                "npm", "left-pad", "1.3.0", "MIT", True, (str(package / "LICENSE"),), "Someone"
            ),
            Dependency("npm", "no-file", "2.0.0", "ISC", True, (), "Jane Example"),
            Dependency("npm", "dev-only", "9.9.9", "MIT", False),
            Dependency("python", "py-lib", "0.1.0", "BSD-3-Clause", True),
        ]

    def test_lists_runtime_dependencies_and_adopted_files(self) -> None:
        text = third_party_notices.render(self.root, self.deps)
        self.assertIn(
            "npm left-pad 1.3.0\n  License: MIT\n  Copyright (c) 2018 Example Author", text
        )
        self.assertIn("npm no-file 2.0.0\n  License: ISC\n  Author: Jane Example", text)
        self.assertIn("python py-lib 0.1.0\n  License: BSD-3-Clause\n", text)
        self.assertNotIn("dev-only", text)
        self.assertIn(
            "CODE_OF_CONDUCT.md\n  License: CC-BY-SA-4.0\n"
            "  Copyright: Original Authors\n  Copyright: The Guildwork Authors\n"
            "  Origin: example/repo@",
            text,
        )
        self.assertNotIn("tool.py", text)
        self.assertNotIn(str(self.root), text)
        self.assertIsNone(third_party_notices.FORBIDDEN_DASHES.search(text))

    def test_without_runtime_dependencies_says_none(self) -> None:
        text = third_party_notices.render(self.root, [])
        self.assertIn("Runtime dependencies\n\nNone.\n", text)

    def test_order_does_not_depend_on_input(self) -> None:
        self.assertEqual(
            third_party_notices.render(self.root, self.deps),
            third_party_notices.render(self.root, list(reversed(self.deps))),
        )

    def test_check_fails_when_outdated(self) -> None:
        third_party_notices.write(self.root, self.deps[:1])
        self.assertEqual(third_party_notices.check(self.root, self.deps[:1]), [])
        findings = third_party_notices.check(self.root, self.deps)
        self.assertEqual(len(findings), 1)
        self.assertTrue(findings[0].startswith("THIRD_PARTY_NOTICES:1:1 notices-outdated "))

    def test_check_fails_when_missing(self) -> None:
        self.assertEqual(len(third_party_notices.check(self.root, [])), 1)

    def test_main_write_then_check(self) -> None:
        out = io.StringIO()
        with (
            unittest.mock.patch.object(
                third_party_notices, "collect_dependencies", return_value=self.deps
            ),
            contextlib.redirect_stdout(out),
        ):
            self.assertEqual(third_party_notices.main(["--root", str(self.root), "--check"]), 1)
            self.assertEqual(third_party_notices.main(["--root", str(self.root), "--write"]), 0)
            self.assertEqual(third_party_notices.main(["--root", str(self.root), "--check"]), 0)
        self.assertIn("notices-outdated", out.getvalue())


if __name__ == "__main__":
    unittest.main()
