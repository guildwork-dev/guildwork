# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/hooks/text_rules.py.

Every test builds a temporary repository with its own quality/text and
quality/denylist files and checks the files it writes there. Dashes, German
letters, home paths and private addresses are written as escapes or assembled
at run time, so this file passes the text rules and the deny-list scan itself.
TestRepoConfig reads the real configuration of the repository.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.hooks import text_rules

REPO_ROOT = Path(__file__).resolve().parents[3]

EN_DASH = "\u2013"
EM_DASH = "\u2014"
FIGURE_DASH = "\u2012"
HORIZONTAL_BAR = "\u2015"
U_UMLAUT = "\u00fc"
SHARP_S = "\u00df"
HOME_PATH = "/" + "Users/alice/project/notes.txt"
PRIVATE_IP = "10.42" + ".7.9"
# Entities are assembled at run time, so this file has none in its text.
AMP = "&"

MARKERS = ["und", "der", "das", "ist", "nicht", "auch", "werden", "wird", "oder"]
ENGLISH_ONLY = (
    f"markers = {json.dumps(MARKERS)}\n"
    "max_per_paragraph = 2\n"
    'paths = ["**/*.md"]\n'
    'skip = ["docs/research/**"]\n'
)
GLOSSARY = '[[term]]\nterm = "frobware"\nuse = "plugin"\nreason = "Old name"\n'
GERMAN_PARAGRAPH = "Das ist nicht der Fall, und die Regel wird auch\nnicht abgeschaltet.\n"


def line_sha(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


class Repo:
    """A temporary repository root with the configuration the tool reads."""

    def __init__(self, base: Path) -> None:
        self.root = base
        self.write("quality/text/exempt-paths.txt", "# exempt\nLICENSES/**\n")
        self.write("quality/text/english-only.toml", ENGLISH_ONLY)
        self.write("quality/text/english-exceptions.toml", "")
        self.write("quality/text/glossary.toml", GLOSSARY)
        for name in ("quality/denylist/generic.toml", "quality/commits/bots.txt"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / name, target)
        self.write("quality/denylist/exceptions.toml", "")

    def write(self, path: str, text: str) -> str:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return path

    def check(self, *paths: str) -> list[text_rules.Finding]:
        config = text_rules.load_config(self.root)
        return text_rules.check_paths(self.root, paths, config)

    def rules(self, *paths: str) -> list[str]:
        return [f"{f.path}:{f.line}:{f.column} {f.rule}" for f in self.check(*paths)]


class RepoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Repo(Path(tmp.name))


class TestTextRulesDash(RepoTestCase):
    def test_flags_en_and_em_dash(self) -> None:
        path = self.repo.write("notes.txt", f"one {EN_DASH} two\nthree{EM_DASH}four\n")
        self.assertEqual(
            self.repo.rules(path),
            ["notes.txt:1:5 no-dash", "notes.txt:2:6 no-dash"],
        )

    def test_flags_figure_dash_and_horizontal_bar(self) -> None:
        path = self.repo.write("code.py", f"x = 1  # a{FIGURE_DASH}b{HORIZONTAL_BAR}c\n")
        self.assertEqual(self.repo.rules(path), ["code.py:1:11 no-dash", "code.py:1:13 no-dash"])

    def test_accepts_hyphen_and_minus(self) -> None:
        path = self.repo.write("notes.txt", "well-known, 3 - 2 and a \u2212 sign\n")
        self.assertEqual(self.repo.rules(path), [])

    def test_ignores_exempt_paths(self) -> None:
        text = f"Section 1 {EN_DASH} Definitions.\n"
        exempt = self.repo.write("LICENSES/CC-BY-4.0.txt", text)
        other = self.repo.write("LICENSE-NOTES.txt", text)
        self.assertEqual(self.repo.rules(exempt, other), ["LICENSE-NOTES.txt:1:11 no-dash"])

    def test_exempt_paths_come_only_from_the_list(self) -> None:
        # The same file is checked once the list no longer names its directory.
        path = self.repo.write("LICENSES/CC-BY-4.0.txt", f"a {EM_DASH} b\n")
        self.repo.write("quality/text/exempt-paths.txt", "fixtures/**\n")
        self.assertEqual(self.repo.rules(path), ["LICENSES/CC-BY-4.0.txt:1:3 no-dash"])

    def test_skips_binary_files(self) -> None:
        target = self.repo.root / "image.png"
        target.write_bytes(b"\x89PNG\x00\x00" + EM_DASH.encode("utf-8"))
        self.assertEqual(self.repo.rules("image.png"), [])


class TestTextRulesEnglish(RepoTestCase):
    def test_flags_german_paragraph_in_docs(self) -> None:
        path = self.repo.write("docs/guide.md", f"# Guide\n\n{GERMAN_PARAGRAPH}")
        self.assertEqual(self.repo.rules(path), ["docs/guide.md:3:1 english-only"])

    def test_flags_german_letters_outside_code(self) -> None:
        path = self.repo.write("README.md", f"Use the f{U_UMLAUT}r loop.\nGro{SHARP_S}\n")
        self.assertEqual(
            self.repo.rules(path), ["README.md:1:10 english-only", "README.md:2:4 english-only"]
        )

    def test_ignores_german_letters_in_code(self) -> None:
        text = f"Run `echo f{U_UMLAUT}r`.\n\n```text\nGro{SHARP_S} und das ist nicht\n```\n"
        path = self.repo.write("README.md", text)
        self.assertEqual(self.repo.rules(path), [])

    def test_accepts_single_marker_word(self) -> None:
        path = self.repo.write("README.md", "The der in the name is a placeholder.\n")
        self.assertEqual(self.repo.rules(path), [])

    def test_ignores_link_destinations(self) -> None:
        # Research files keep their German names (ADR-53); a link target is a path, not prose.
        text = (
            "See [layer](../research/ebene-planung-und-architektur.md#2-bewertung-der-ebene) "
            f"and [hosting](../research/hosting-und-installation.md#f{U_UMLAUT}r).\n\n"
            "[ref]: ../research/open-source-lizenz-und-recht.md\n"
        )
        path = self.repo.write("docs/design/links.md", text)
        self.assertEqual(self.repo.rules(path), [])

    def test_link_text_is_still_checked(self) -> None:
        text = "See [ebene-planung-und-architektur](a.md) and [lizenz-und-recht](b.md).\n"
        path = self.repo.write("docs/design/links.md", text)
        self.assertEqual(self.repo.rules(path), ["docs/design/links.md:1:20 english-only"])

    def test_research_dir_is_exempt(self) -> None:
        text = f"{GERMAN_PARAGRAPH}\nF{U_UMLAUT}r die Recherche.\n"
        research = self.repo.write("docs/research/layer-1.md", text)
        design = self.repo.write("docs/design/layer-1.md", text)
        found = self.repo.rules(research, design)
        self.assertTrue(found)
        self.assertTrue(all(item.startswith("docs/design/") for item in found), found)

    def test_applies_to_configured_paths_only(self) -> None:
        path = self.repo.write("tools/note.txt", GERMAN_PARAGRAPH)
        self.assertEqual(self.repo.rules(path), [])

    def test_exception_per_exact_line(self) -> None:
        line = "Reply with JA oder NEIN und nothing else."
        path = self.repo.write("docs/review.md", f"{line}\n\n{line} \n")
        self.repo.write(
            "quality/text/english-exceptions.toml",
            "[[exception]]\n"
            'path = "docs/review.md"\n'
            f'line_sha256 = "{line_sha(line)}"\n'
            'reason = "Verdict words of the review gate"\n',
        )
        # The second line differs by a trailing space and is still reported.
        self.assertEqual(self.repo.rules(path), ["docs/review.md:3:15 english-only"])

    def test_exception_needs_reason(self) -> None:
        self.repo.write(
            "quality/text/english-exceptions.toml",
            f'[[exception]]\npath = "a.md"\nline_sha256 = "{line_sha("x")}"\nreason = ""\n',
        )
        with self.assertRaises(text_rules.ConfigError):
            text_rules.load_config(self.repo.root)


class TestTextRulesEntities(RepoTestCase):
    """HTML entities render as the character itself, so they count as it."""

    def test_flags_named_dash_entities(self) -> None:
        text = f"a {AMP}ndash; b {AMP}mdash; c {AMP}horbar; d\n"
        path = self.repo.write("docs/a.md", text)
        self.assertEqual(
            self.repo.rules(path),
            ["docs/a.md:1:3 no-dash", "docs/a.md:1:13 no-dash", "docs/a.md:1:23 no-dash"],
        )

    def test_flags_numeric_dash_entities(self) -> None:
        path = self.repo.write("notes.txt", f"x{AMP}#8211;y{AMP}#x2014;z\n")
        self.assertEqual(self.repo.rules(path), ["notes.txt:1:2 no-dash", "notes.txt:1:10 no-dash"])

    def test_flags_german_letter_entities(self) -> None:
        path = self.repo.write("docs/a.md", f"Use {AMP}auml; and {AMP}#228;.\n")
        self.assertEqual(
            self.repo.rules(path), ["docs/a.md:1:5 english-only", "docs/a.md:1:16 english-only"]
        )

    def test_columns_count_in_the_original_line(self) -> None:
        path = self.repo.write("notes.txt", f"{AMP}amp; {AMP}mdash;\n")
        self.assertEqual(self.repo.rules(path), ["notes.txt:1:7 no-dash"])

    def test_escaped_entity_text_is_no_dash(self) -> None:
        path = self.repo.write("notes.txt", f"write {AMP}amp;mdash; for the entity\n")
        self.assertEqual(self.repo.rules(path), [])


class TestTextRulesEncoding(RepoTestCase):
    def test_flags_non_utf8_text(self) -> None:
        (self.repo.root / "cp1252.txt").write_bytes(b"caf\xe9 \x96 dash\n")
        self.assertEqual(self.repo.rules("cp1252.txt"), ["cp1252.txt:1:1 text-encoding"])

    def test_flags_utf16_text(self) -> None:
        (self.repo.root / "wide.md").write_bytes(f"a {EM_DASH} b\n".encode("utf-16"))
        (self.repo.root / "wide-le.txt").write_bytes(f"plain text {EN_DASH}\n".encode("utf-16-le"))
        self.assertEqual(
            self.repo.rules("wide.md", "wide-le.txt"),
            ["wide-le.txt:1:1 text-encoding", "wide.md:1:1 text-encoding"],
        )

    def test_exempt_paths_skip_encoding_check(self) -> None:
        (self.repo.root / "LICENSES").mkdir()
        (self.repo.root / "LICENSES/old.txt").write_bytes(b"caf\xe9\n")
        self.assertEqual(self.repo.rules("LICENSES/old.txt"), [])


class TestTextRulesGlossary(RepoTestCase):
    def test_flags_superseded_term(self) -> None:
        path = self.repo.write("docs/a.md", "Add the host to the Frobware.\n")
        findings = self.repo.check(path)
        self.assertEqual([f.rule for f in findings], ["glossary"])
        self.assertIn("plugin", findings[0].message)

    def test_matches_whole_words_only(self) -> None:
        path = self.repo.write("docs/a.md", "The frobwares flag stays.\n")
        self.assertEqual(self.repo.rules(path), [])

    def test_glossary_file_does_not_flag_itself(self) -> None:
        self.assertEqual(self.repo.rules("quality/text/glossary.toml"), [])


class TestTextRulesInstanceData(RepoTestCase):
    def test_flags_home_path_and_private_address(self) -> None:
        path = self.repo.write("docs/a.md", f"See {HOME_PATH}\nHost {PRIVATE_IP}\n")
        findings = self.repo.check(path)
        self.assertEqual(
            [(f.line, f.rule) for f in findings], [(1, "instance-data"), (2, "instance-data")]
        )
        # The finding names the generic rule, never the matched text.
        for finding in findings:
            self.assertNotIn("alice", str(finding))
            self.assertNotIn(PRIVATE_IP, str(finding))
        self.assertIn("generic-home-path", findings[0].message)

    def test_accepts_documentation_addresses(self) -> None:
        path = self.repo.write("docs/a.md", "Host 192.0.2.10, mail ops@example.org\n")
        self.assertEqual(self.repo.rules(path), [])

    def test_uses_denylist_exceptions(self) -> None:
        line = f"Host {PRIVATE_IP}"
        path = self.repo.write("docs/a.md", line + "\n")
        self.repo.write(
            "quality/denylist/exceptions.toml",
            "[[exception]]\n"
            'term = "generic-private-ipv4"\n'
            f'line_sha256 = "{line_sha(line)}"\n'
            'path = "docs/a.md"\n'
            'reason = "Test"\n',
        )
        self.assertEqual(self.repo.rules(path), [])

    def test_reads_generic_rules_from_denylist(self) -> None:
        # One source: a rule added to generic.toml applies to the text rules too.
        generic = self.repo.root / "quality/denylist/generic.toml"
        generic.write_text(
            generic.read_text(encoding="utf-8")
            + '\n[[rule]]\nid = "generic-test"\nkind = "regex"\npatterns = ["zorblax"]\n',
            encoding="utf-8",
        )
        path = self.repo.write("a.txt", "zorblax\n")
        findings = self.repo.check(path)
        self.assertEqual([f.rule for f in findings], ["instance-data"])
        self.assertIn("generic-test", findings[0].message)


class TestTextRulesMain(RepoTestCase):
    def run_main(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = text_rules.main(["--root", str(self.repo.root), *args])
        return code, out.getvalue(), err.getvalue()

    def test_prints_findings_and_writes_report(self) -> None:
        path = self.repo.write("a.txt", f"a {EM_DASH} b\n")
        report = self.repo.root / ".reports" / "text-rules.json"
        code, out, _ = self.run_main("--json", str(report), path)
        self.assertEqual(code, 1)
        self.assertIn("a.txt:1:3 no-dash", out)
        data = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(data["tool"], "text-rules")
        self.assertEqual([f["rule"] for f in data["findings"]], ["no-dash"])

    def test_clean_files_exit_zero(self) -> None:
        path = self.repo.write("a.txt", "plain text\n")
        code, out, _ = self.run_main(path)
        self.assertEqual(code, 0)
        self.assertIn("0 findings", out)

    def test_checks_tracked_files_without_arguments(self) -> None:
        self.repo.write("tracked.txt", f"a {EM_DASH} b\n")
        self.repo.write("untracked.txt", f"a {EM_DASH} b\n")
        git = ["git", "-C", str(self.repo.root)]
        subprocess.run([*git, "init", "-q"], check=True)  # noqa: S603
        subprocess.run([*git, "add", "tracked.txt"], check=True)  # noqa: S603
        code, out, _ = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("tracked.txt:1:3 no-dash", out)
        self.assertNotIn("untracked.txt", out)

    def test_config_error_exits_two_without_report(self) -> None:
        self.repo.write("quality/text/english-only.toml", "markers = 3\n")
        report = self.repo.root / ".reports" / "text-rules.json"
        code, out, err = self.run_main("--json", str(report), "a.txt")
        self.assertEqual(code, 2)
        self.assertIn("text_rules.config_invalid", err)
        self.assertEqual(out, "")
        self.assertFalse(report.exists())

    def test_missing_file_argument_exits_two(self) -> None:
        code, _, err = self.run_main("does-not-exist.txt")
        self.assertEqual(code, 2)
        self.assertIn("text_rules.file_unreadable", err)


class TestRepoConfig(unittest.TestCase):
    def test_real_config_loads(self) -> None:
        config = text_rules.load_config(REPO_ROOT)
        self.assertTrue(config.english.markers)
        self.assertEqual(config.english.max_per_paragraph, 2)

    def test_licenses_are_exempt(self) -> None:
        # The verbatim license texts contain en dashes (M161).
        config = text_rules.load_config(REPO_ROOT)
        self.assertTrue(text_rules.is_exempt(config, "LICENSES/CC-BY-SA-4.0.txt"))
        self.assertFalse(text_rules.is_exempt(config, "README.md"))


if __name__ == "__main__":
    unittest.main()
