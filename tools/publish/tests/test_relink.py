# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/publish/relink.py.

Each test builds a German source tree, an English checkout and a small linkmap
in temporary directories. German words appear only as path and heading data of
the fixtures, as in the real linkmap.
"""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from tools.publish import relink

LINKMAP = """\
[ordner]
"docs/feinentwurf" = "docs/design"
"docs/architektur" = "docs/architecture"
"docs/recherche" = "docs/research"

[dateien]
"docs/feinentwurf/01-datenmodell.md" = "docs/design/01-data-model.md"
"docs/feinentwurf/02-steuerzentrale.md" = "docs/design/02-control-plane.md"
"docs/feinentwurf/komponenten/README.md" = "docs/design/components/README.md"
"docs/architektur/05-sicherheit.md" = "docs/architecture/05-security.md"
"""

GERMAN_01 = "# 01 Datenmodell\n\n## 1. Zweck\n\n## 2. Tabellen\n\n### 2.1 Übersicht\n"
ENGLISH_01 = "# 01 Data model\n\n## 1. Purpose\n\n## 2. Tables\n\n### 2.1 Overview\n"
GERMAN_05 = "# 05 Sicherheit\n\n## 3. Geheimnisse\n\n## 3. Geheimnisse\n"
ENGLISH_05 = "# 05 Security\n\n## 3. Secrets\n\n## 3. Secrets\n"


class Fixture:
    def __init__(self, base: Path) -> None:
        self.german = base / "de"
        self.root = base / "en"
        self.peer = base / "peer"
        self.linkmap = base / "linkmap.toml"
        self.linkmap.write_text(LINKMAP, encoding="utf-8")
        self.de("docs/feinentwurf/01-datenmodell.md", GERMAN_01)
        self.de("docs/feinentwurf/02-steuerzentrale.md", "# 02\n\n## 4. Abläufe\n")
        self.de("docs/feinentwurf/komponenten/README.md", "# K\n\n## 2. Felder\n")
        self.de("docs/architektur/05-sicherheit.md", GERMAN_05)
        self.de("docs/recherche/ebene-review.md", "# Ebene\n\n## 2 Befunde\n")
        self.en("docs/design/01-data-model.md", ENGLISH_01)
        self.en("docs/design/components/README.md", "# C\n\n## 2. Fields\n")
        (self.peer / "docs/architecture").mkdir(parents=True)
        (self.peer / "docs/architecture/05-security.md").write_text(ENGLISH_05, encoding="utf-8")

    def de(self, path: str, text: str) -> None:
        self._write(self.german / path, text)

    def en(self, path: str, text: str) -> str:
        self._write(self.root / path, text)
        return path

    @staticmethod
    def _write(file: Path, text: str) -> None:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")

    def run(self, *paths: str, write: bool = True) -> relink.Result:
        return relink.run(
            self.root,
            relink.LinkMap.load(self.linkmap),
            self.german,
            [self.peer],
            list(paths),
            write=write,
        )

    def read(self, path: str) -> str:
        return (self.root / path).read_text(encoding="utf-8")


class RelinkTestCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.fx = Fixture(Path(tmp.name))

    def doc(self, body: str) -> str:
        """An English design 02 whose German source has one heading."""
        return self.fx.en("docs/design/02-control-plane.md", "# 02\n\n## 4. Flows\n\n" + body)


class TestMarkdown(RelinkTestCase):
    def test_rewrites_sibling_file_and_anchor(self) -> None:
        path = self.doc("See [tables](01-datenmodell.md#2-tabellen).\n")
        result = self.fx.run(path)
        self.assertEqual(result.findings, [])
        self.assertIn("See [tables](01-data-model.md#2-tables).", self.fx.read(path))

    def test_maps_anchor_with_umlaut_by_index(self) -> None:
        path = self.doc(
            "[x](01-datenmodell.md#21-übersicht) [y](01-datenmodell.md#21-%C3%BCbersicht)\n"
        )
        self.fx.run(path)
        self.assertIn(
            "[x](01-data-model.md#21-overview) [y](01-data-model.md#21-overview)",
            self.fx.read(path),
        )

    def test_rewrites_link_into_other_folder_found_in_peer(self) -> None:
        path = self.doc("[05](../architektur/05-sicherheit.md#3-geheimnisse-1)\n")
        result = self.fx.run(path)
        self.assertEqual(result.findings, [])
        self.assertIn("[05](../architecture/05-security.md#3-secrets-1)", self.fx.read(path))

    def test_rewrites_link_text_equal_to_german_name(self) -> None:
        path = self.doc(
            "[01-datenmodell.md](01-datenmodell.md) [`01-datenmodell.md`](01-datenmodell.md) "
            "[data model](01-datenmodell.md)\n"
        )
        self.fx.run(path)
        self.assertIn(
            "[01-data-model.md](01-data-model.md) [`01-data-model.md`](01-data-model.md) "
            "[data model](01-data-model.md)",
            self.fx.read(path),
        )

    def test_rewrites_own_anchor(self) -> None:
        path = self.doc("Back to [flows](#4-abläufe).\n")
        self.fx.run(path)
        self.assertIn("Back to [flows](#4-flows).", self.fx.read(path))

    def test_rewrites_folder_link_and_reference_and_html(self) -> None:
        path = self.doc(
            "[arch](../architektur/) [here](../feinentwurf/) and [ref].\n\n"
            "[ref]: komponenten/README.md#2-felder\n"
            '<a href="01-datenmodell.md#1-zweck">x</a>\n'
        )
        self.fx.run(path)
        text = self.fx.read(path)
        self.assertIn("[arch](../architecture/) [here](./)", text)
        self.assertIn("[ref]: components/README.md#2-fields", text)
        self.assertIn('<a href="01-data-model.md#1-purpose">x</a>', text)

    def test_leaves_code_and_external_links(self) -> None:
        body = (
            "`[a](01-datenmodell.md)` [web](https://example.org/01-datenmodell.md)\n\n"
            "```md\n[a](01-datenmodell.md)\n```\n"
        )
        path = self.doc(body)
        result = self.fx.run(path)
        self.assertEqual(result.changed_files, [])
        self.assertIn(body, self.fx.read(path))

    def test_untranslated_target_is_rewritten_and_anchor_noted(self) -> None:
        path = self.doc("[r](../recherche/ebene-review.md#2-befunde)\n")
        result = self.fx.run(path)
        self.assertEqual(result.findings, [])
        self.assertIn("[r](../research/ebene-review.md#2-befunde)", self.fx.read(path))
        self.assertEqual([n.rule for n in result.notes], ["relink.anchor-unchecked"])

    def test_reports_unknown_anchor_and_missing_target(self) -> None:
        path = self.doc("[a](01-datenmodell.md#9-fehlt) [b](99-fehlt.md)\n")
        result = self.fx.run(path)
        self.assertEqual(
            [(f.rule, f.target) for f in result.findings],
            [
                ("relink.unknown-anchor", "01-datenmodell.md#9-fehlt"),
                ("relink.missing-target", "99-fehlt.md"),
            ],
        )

    def test_reports_heading_count_mismatch(self) -> None:
        self.fx.en("docs/design/01-data-model.md", "# 01 Data model\n\n## 1. Purpose\n")
        path = self.doc("[a](01-datenmodell.md#1-zweck)\n")
        result = self.fx.run(path)
        self.assertEqual([f.rule for f in result.findings], ["relink.heading-count-mismatch"])

    def test_is_idempotent(self) -> None:
        path = self.doc("[a](01-datenmodell.md#2-tabellen) [b](../architektur/05-sicherheit.md)\n")
        self.fx.run(path)
        once = self.fx.read(path)
        second = self.fx.run(path)
        self.assertEqual(second.changed_files, [])
        self.assertEqual(self.fx.read(path), once)

    def test_new_file_without_german_source_resolves_from_its_own_folder(self) -> None:
        path = self.fx.en(
            "docs/adr/0001-x.md", "[05](../architektur/05-sicherheit.md#3-geheimnisse)\n"
        )
        self.fx.run(path)
        self.assertIn("[05](../architecture/05-security.md#3-secrets)", self.fx.read(path))


class TestToml(RelinkTestCase):
    def test_rewrites_design_and_defined_in(self) -> None:
        path = self.fx.en(
            "docs/design/components/x.toml",
            'id = "x"\n'
            'design = ["01-datenmodell.md#2-tabellen", "komponenten/README.md#2-felder"]\n'
            'purpose = "01-datenmodell.md#2-tabellen stays"\n'
            'design = [\n  "01-datenmodell.md#1-zweck",\n]\n'
            'defined_in = "01-datenmodell.md#21-übersicht"\n',
        )
        result = self.fx.run(path)
        self.assertEqual(result.findings, [])
        self.assertEqual(
            self.fx.read(path),
            'id = "x"\ndesign = ["01-data-model.md#2-tables", "components/README.md#2-fields"]\n'
            'purpose = "01-datenmodell.md#2-tabellen stays"\n'
            'design = [\n  "01-data-model.md#1-purpose",\n]\n'
            'defined_in = "01-data-model.md#21-overview"\n',
        )

    def test_other_toml_files_are_left_alone(self) -> None:
        path = self.fx.en("docs/other.toml", 'design = ["01-datenmodell.md"]\n')
        result = self.fx.run(path)
        self.assertEqual(result.changed_files, [])


class TestMain(RelinkTestCase):
    def call(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = relink.main(
                [
                    "--linkmap",
                    str(self.fx.linkmap),
                    "--german",
                    str(self.fx.german),
                    "--root",
                    str(self.fx.root),
                    "--peer",
                    str(self.fx.peer),
                    *args,
                ]
            )
        return code, out.getvalue()

    def test_check_reports_pending_and_writes_nothing(self) -> None:
        path = self.doc("[a](01-datenmodell.md)\n")
        before = self.fx.read(path)
        code, out = self.call("--check")
        self.assertEqual(code, 1)
        self.assertIn(f"{path}:1:1 relink.pending", out)
        self.assertEqual(self.fx.read(path), before)

    def test_write_then_check_is_clean(self) -> None:
        self.doc("[a](01-datenmodell.md)\n")
        self.assertEqual(self.call()[0], 0)
        code, out = self.call("--check")
        self.assertEqual(code, 0, out)
        self.assertIn("relink: 0 links pending in 0 files, 0 findings", out)

    def test_findings_fail(self) -> None:
        self.doc("[a](99-fehlt.md)\n")
        code, out = self.call()
        self.assertEqual(code, 1)
        self.assertIn("relink.missing-target 99-fehlt.md", out)

    def test_bad_linkmap_is_a_usage_error(self) -> None:
        self.fx.linkmap.write_text("[ordner]\n", encoding="utf-8")
        code, out = self.call()
        self.assertEqual(code, 2)
        self.assertIn("relink.config_invalid", out)


if __name__ == "__main__":
    unittest.main()
