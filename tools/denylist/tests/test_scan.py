# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/denylist/scan.py.

Every test runs against a temporary git repository with invented terms and an
isolated environment: DENYLIST_FILE, ALLOW_AUTHORS_FILE, PR_TITLE and PR_BODY
of the calling shell are removed, so no test ever reads the private list.
Home paths and private addresses are assembled at run time, so this file does
not trip the generic rules of the repository scan itself.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.denylist import scan

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "tools" / "denylist" / "scan.py"

AUTHOR = "Ada Example <ada@example.com>"
BOT_EMAIL = "release-bot@example.com"

# Invented terms; none of them is on any real list.
LITERAL = "zorblaxcorp"
REGEX = r"re:qux[0-9]{3}vel"
WORD = "word:frobhost"
LIST_TEXT = f"# invented terms\n\n{LITERAL}\n{REGEX}\n{WORD}\n"
SECRET_FRAGMENTS = ("zorblax", "qux123vel", "frobhost")

HOME_MAC = "/" + "Users/alice/project"
HOME_LINUX = "/" + "home/bob/.config"
HOME_WINDOWS = "C:" + "\\Users\\carol\\Documents"
PRIVATE_IPS = ("10.42" + ".7.9", "172.20" + ".1.2", "192.168" + ".0.10", "100.64" + ".3.4")
PUBLIC_IPS = ("192.0.2.5", "198.51.100.7", "203.0.113.9", "8.8.8.8", "172.32.0.1")
# Mail addresses outside the example domains, also assembled at run time.
MAIL_DOMAIN = "@corp-mail.test"
OPS = "ops" + MAIL_DOMAIN
FORK = "Fork Person <fork" + MAIL_DOMAIN + ">"


def term_id(entry: str) -> str:
    return "term-" + hashlib.sha256(entry.encode("utf-8")).hexdigest()[:12]


def line_sha(line: str) -> str:
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def git(root: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", "-C", str(root), *args],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def identity_env(prefix: str, ident: str) -> dict[str, str]:
    name, _, rest = ident.partition(" <")
    return {f"GIT_{prefix}_NAME": name, f"GIT_{prefix}_EMAIL": rest.rstrip(">")}


class ScanCase(unittest.TestCase):
    """A temporary repository, a private list outside it, an isolated environment."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.root = base / "repo"
        self.private = base / "private"
        self.root.mkdir()
        self.private.mkdir()
        self.list_path = self.private / "denylist.txt"
        self.list_path.write_text(LIST_TEXT, encoding="utf-8")
        self.authors_path = self.private / "allow-authors.txt"
        self.authors_path.write_text(f"{AUTHOR}\n", encoding="utf-8")
        self.env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(base),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            **identity_env("AUTHOR", AUTHOR),
            **identity_env("COMMITTER", AUTHOR),
            "DENYLIST_FILE": str(self.list_path),
            "ALLOW_AUTHORS_FILE": str(self.authors_path),
        }
        patcher = mock.patch.dict(os.environ, self.env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        git(self.root, "init", "-q", "-b", "main")
        # Configuration stays untracked, so the scans below never see it.
        quality = self.root / "quality"
        (quality / "denylist").mkdir(parents=True)
        (quality / "commits").mkdir(parents=True)
        shutil.copy(REPO_ROOT / scan.GENERIC_PATH, quality / "denylist" / "generic.toml")
        self.write_exceptions("")
        (quality / "commits" / "bots.txt").write_text(f"# bots\n{BOT_EMAIL}\n", encoding="utf-8")
        self.base = self.commit("chore: start", {"README.md": "Clean start.\n"})

    def write_exceptions(self, text: str) -> None:
        path = self.root / scan.EXCEPTIONS_PATH
        path.write_text("# exceptions\n" + text, encoding="utf-8")

    def commit(
        self,
        message: str,
        files: dict[str, str] | None = None,
        *,
        author: str = AUTHOR,
        committer: str = AUTHOR,
    ) -> str:
        for name, text in (files or {}).items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            git(self.root, "add", "--", name)
        env = {
            **os.environ,
            **identity_env("AUTHOR", author),
            **identity_env("COMMITTER", committer),
        }
        subprocess.run(  # noqa: S603
            ["git", "-C", str(self.root), "commit", "-q", "--allow-empty", "-m", message],  # noqa: S607
            check=True,
            capture_output=True,
            env=env,
        )
        return git(self.root, "rev-parse", "HEAD")

    def run_main(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = scan.main(["--root", str(self.root), *argv])
        return code, out.getvalue(), err.getvalue()

    def findings(self, out: str) -> list[tuple[str, str]]:
        """(location, id) of every finding line."""
        pairs = []
        for line in out.splitlines():
            parts = line.split(" ")
            if len(parts) >= 2 and parts[0].count(":") >= 2:
                pairs.append((parts[0], parts[1]))
        return pairs

    def assert_no_secret(self, *texts: str) -> None:
        for text in texts:
            lowered = text.lower()
            for fragment in (*SECRET_FRAGMENTS, "contact", "alice", "10.42"):
                self.assertNotIn(fragment, lowered)


class TestDenylist(ScanCase):
    def test_finding_never_prints_term_or_text(self) -> None:
        content = (
            "Clean first line.\n"
            "Contact ZorblaxCorp about qux123vel on Frobhost today.\n"
            f"Contact alice at {HOME_MAC} or {PRIVATE_IPS[0]}.\n"
        )
        git(self.root, "checkout", "-q", "-b", "topic/zorblaxcorp")
        self.commit(
            "feat: add the qux123vel notes\n\nContact zorblaxcorp.",
            {"notes/zorblaxcorp-plan.md": content},
            author="Ada Frobhost <ada@example.com>",
        )
        report = self.root.parent / "report.json"
        env = {
            **os.environ,
            "PR_TITLE": "Add ZorblaxCorp notes",
            "PR_BODY": "Contact frobhost\nand qux123vel",
        }
        runs = (
            ["tree", "commits", "--range", f"{self.base}..HEAD", "pr"],
            ["history", "--all"],
        )
        for modes in runs:
            with self.subTest(modes=modes):
                result = subprocess.run(  # noqa: S603
                    [sys.executable, str(SCRIPT), "--root", str(self.root), "--json", str(report)]
                    + modes,
                    capture_output=True,
                    text=True,
                    env=env,
                    check=False,
                )
                self.assertEqual(result.returncode, 1, result.stderr)
                data = report.read_text(encoding="utf-8")
                self.assert_no_secret(result.stdout, result.stderr, data)
                for entry in (LITERAL, REGEX, WORD):
                    self.assertIn(term_id(entry), result.stdout)
                    self.assertIn(term_id(entry), data)
                self.assertIn("generic-home-path", result.stdout)
                self.assertIn("generic-private-ipv4", result.stdout)
                parsed = json.loads(data)
                self.assertEqual(len(parsed["findings"]), len(self.findings(result.stdout)))

    def test_checks_identities_against_allow_authors(self) -> None:
        self.commit("feat: allowed identity")
        eve = self.commit("feat: unknown author", author="Eve Example <eve@example.com>")
        mallory = self.commit("feat: unknown committer", committer="Mallory <mallory@example.com>")
        code, out, err = self.run_main("--range", f"{self.base}..HEAD", "commits")
        self.assertEqual(code, 1, err)
        self.assertCountEqual(
            self.findings(out),
            [
                (f"{eve[:12]}:author:1:1", "identity-not-allowed"),
                (f"{mallory[:12]}:committer:1:1", "identity-not-allowed"),
            ],
        )
        self.assertNotIn("eve@example.com", out + err)
        self.assertNotIn("Mallory", out + err)
        # A name that differs only in case is another identity.
        self.authors_path.write_text(AUTHOR.lower() + "\n", encoding="utf-8")
        code, out, _ = self.run_main("--all", "history")
        self.assertEqual(code, 1)
        self.assertIn(f"{self.base[:12]}:author:1:1 identity-not-allowed", out)
        # Generic mode: no private list, no identity file, identities unchecked.
        del os.environ["DENYLIST_FILE"]
        del os.environ["ALLOW_AUTHORS_FILE"]
        code, out, err = self.run_main(
            "--allow-missing", "--range", f"{self.base}..HEAD", "commits"
        )
        self.assertEqual((code, out.count("identity-not-allowed")), (0, 0), out + err)

    def test_pr_title_and_body_from_env_only(self) -> None:
        os.environ["PR_TITLE"] = "Update the ZorblaxCorp docs"
        os.environ["PR_BODY"] = "First line is clean.\nAsk qux123vel."
        code, out, err = self.run_main("pr")
        self.assertEqual(code, 1, err)
        self.assertCountEqual(
            self.findings(out),
            [("pr-title:1:12", term_id(LITERAL)), ("pr-body:2:5", term_id(REGEX))],
        )
        # Title and body are never read from arguments.
        for argv in (["pr", "--title", "x"], ["pr", LITERAL], ["--pr-body", LITERAL, "pr"]):
            with self.subTest(argv=argv):
                code, out, err = self.run_main(*argv)
                self.assertEqual(code, 2)
                self.assert_no_secret(out, err)
        # pr mode without PR_TITLE in the environment is a usage error.
        del os.environ["PR_TITLE"]
        code, out, err = self.run_main("pr")
        self.assertEqual(code, 2)
        self.assertIn("denylist.pr_env_missing", err)
        # An empty body is allowed, an unset body is not.
        os.environ["PR_TITLE"] = "docs: clean title"
        os.environ["PR_BODY"] = ""
        self.assertEqual(self.run_main("pr")[0], 0)
        del os.environ["PR_BODY"]
        self.assertEqual(self.run_main("pr")[0], 2)

    def test_missing_list_exits_2_without_allow_missing(self) -> None:
        del os.environ["DENYLIST_FILE"]
        code, out, err = self.run_main("tree")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("denylist.list_missing", err)
        # An empty value counts as missing.
        os.environ["DENYLIST_FILE"] = ""
        self.assertEqual(self.run_main("tree")[0], 2)
        # A path that does not exist: the message names the variable, not the path.
        os.environ["DENYLIST_FILE"] = str(self.private / "zorblaxcorp" / "list.txt")
        code, out, err = self.run_main("tree")
        self.assertEqual(code, 2)
        self.assertIn("denylist.list_missing", err)
        self.assertIn("DENYLIST_FILE", err)
        self.assert_no_secret(out, err)
        # --allow-missing covers an unset variable only, not a wrong path.
        code, out, err = self.run_main("--allow-missing", "tree")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("denylist.list_missing", err)
        self.assert_no_secret(err)
        # The identity file is required in the same way.
        os.environ["DENYLIST_FILE"] = str(self.list_path)
        del os.environ["ALLOW_AUTHORS_FILE"]
        code, _, err = self.run_main("--range", f"{self.base}..HEAD", "commits")
        self.assertEqual(code, 2)
        self.assertIn("ALLOW_AUTHORS_FILE", err)
        os.environ["ALLOW_AUTHORS_FILE"] = str(self.private / "absent.txt")
        code, _, err = self.run_main("--allow-missing", "tree")
        self.assertEqual(code, 2)
        self.assertIn("denylist.authors_missing", err)
        del os.environ["ALLOW_AUTHORS_FILE"]
        # --allow-missing runs the generic rules alone.
        del os.environ["DENYLIST_FILE"]
        code, out, err = self.run_main("--allow-missing", "tree")
        self.assertEqual(code, 0, out + err)

    def test_exception_matches_exact_line_only(self) -> None:
        first = "alpha zorblaxcorp"
        self.commit("docs: add terms", {"docs/a.md": f"{first}\nbeta zorblaxcorp\n"})
        entry = (
            "[[exception]]\n"
            f'term = "{term_id(LITERAL)}"\n'
            f'line_sha256 = "{line_sha(first)}"\n'
            'path = "docs/a.md"\n'
            'reason = "Invented term in a test"\n'
        )
        self.write_exceptions(entry)
        code, out, _ = self.run_main("tree")
        self.assertEqual(code, 1)
        self.assertEqual(self.findings(out), [("docs/a.md:2:6", term_id(LITERAL))])
        # One more character on the line: the exception no longer applies.
        (self.root / "docs" / "a.md").write_text(f"{first}!\n", encoding="utf-8")
        code, out, _ = self.run_main("tree")
        self.assertEqual(self.findings(out), [("docs/a.md:1:7", term_id(LITERAL))])
        # The same line in another file is not covered either.
        (self.root / "docs" / "a.md").write_text("clean\n", encoding="utf-8")
        self.commit("docs: move", {"docs/b.md": f"{first}\n"})
        code, out, _ = self.run_main("tree")
        self.assertEqual(self.findings(out), [("docs/b.md:1:7", term_id(LITERAL))])
        # The same line with another term id is not covered.
        self.write_exceptions(entry.replace(term_id(LITERAL), term_id(WORD)))
        (self.root / "docs" / "b.md").unlink()
        (self.root / "docs" / "a.md").write_text(f"{first}\n", encoding="utf-8")
        code, out, _ = self.run_main("tree")
        self.assertEqual(self.findings(out), [("docs/a.md:1:7", term_id(LITERAL))])
        # An exception without reason is a configuration error.
        self.write_exceptions(
            entry.replace('reason = "Invented term in a test"\n', 'reason = ""\n')
        )
        code, _, err = self.run_main("tree")
        self.assertEqual(code, 2)
        self.assertIn("denylist.config_invalid", err)

    def test_generic_rules_flag_home_paths_and_private_ips(self) -> None:
        del os.environ["DENYLIST_FILE"]
        del os.environ["ALLOW_AUTHORS_FILE"]
        flagged = [HOME_MAC, HOME_LINUX, HOME_WINDOWS, *PRIVATE_IPS, f"write to {OPS}"]
        clean = [
            *PUBLIC_IPS,
            "version 1.10.0 and 10.4",
            "mail ada@example.com, x@docs.example.org, y@example.net",
            f"bot {BOT_EMAIL}",
            "relative path Users/alice/ and home/bob without a leading slash",
        ]
        self.commit("docs: data", {"data.txt": "\n".join(flagged + clean) + "\n"})
        code, out, err = self.run_main("--allow-missing", "tree")
        self.assertEqual(code, 1, err)
        expected = [
            ("data.txt:1:1", "generic-home-path"),
            ("data.txt:2:1", "generic-home-path"),
            ("data.txt:3:1", "generic-home-path"),
            ("data.txt:4:1", "generic-private-ipv4"),
            ("data.txt:5:1", "generic-private-ipv4"),
            ("data.txt:6:1", "generic-private-ipv4"),
            ("data.txt:7:1", "generic-private-ipv4"),
            ("data.txt:8:10", "generic-mail-address"),
        ]
        self.assertEqual(self.findings(out), expected)
        self.assert_no_secret(out, err)
        # Addresses of ALLOW_AUTHORS_FILE are allowed by the mail rule as well.
        self.authors_path.write_text(f"Ops <{OPS}>\n", encoding="utf-8")
        os.environ["ALLOW_AUTHORS_FILE"] = str(self.authors_path)
        code, out, _ = self.run_main("--allow-missing", "tree")
        self.assertNotIn("generic-mail-address", out)

    def test_scans_file_names_and_refs(self) -> None:
        name = "docs/zorblaxcorp.md"
        self.commit("docs: add a page", {name: "Clean content.\n"})
        git(self.root, "branch", "feature/frobhost")
        git(self.root, "tag", "qux123vel-1")
        code, out, err = self.run_main("tree")
        self.assertEqual(code, 1, err)
        path_id = "path-" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
        self.assertEqual(self.findings(out), [(f"{path_id}:0:6", term_id(LITERAL))])
        code, out, err = self.run_main("--all", "history")
        self.assertEqual(code, 1, err)
        found = self.findings(out)
        refs = {
            "refs/heads/feature/frobhost": (term_id(WORD), 20),
            "refs/tags/qux123vel-1": (term_id(REGEX), 11),
        }
        for ref, (ident, column) in refs.items():
            ref_id = "ref-" + hashlib.sha256(ref.encode("utf-8")).hexdigest()[:12]
            self.assertIn((f"{ref_id}:0:{column}", ident), found)
        # In history, a name is reported with the commit that adds it.
        head = git(self.root, "rev-parse", "HEAD")
        self.assertIn((f"{head[:12]}:{path_id}:0:6", term_id(LITERAL)), found)
        self.assert_no_secret(out, err)


class TestDenylistList(ScanCase):
    def test_literal_is_case_insensitive_word_is_whole_word_regex_is_exact(self) -> None:
        text = "ZORBLAXCORP\nfrobhosts\n(frobhost)\nQUX123VEL\nqux123vel\n"
        self.commit("docs: cases", {"cases.txt": text})
        code, out, _ = self.run_main("tree")
        self.assertEqual(code, 1)
        self.assertEqual(
            self.findings(out),
            [
                ("cases.txt:1:1", term_id(LITERAL)),
                ("cases.txt:3:2", term_id(WORD)),
                ("cases.txt:5:1", term_id(REGEX)),
            ],
        )

    def test_invalid_entry_exits_2_without_its_text(self) -> None:
        for bad in ("re:zorblax(corp", "re:(zorblax)?", "word:", "re:"):
            with self.subTest(bad=bad):
                self.list_path.write_text(f"# list\n{bad}\n", encoding="utf-8")
                code, out, err = self.run_main("tree")
                self.assertEqual((code, out), (2, ""))
                self.assertIn("denylist.list_invalid", err)
                self.assertIn("line=2", err)
                self.assert_no_secret(err)

    def test_unreadable_list_names_no_content(self) -> None:
        self.list_path.write_bytes(b"zorblax\xffcorp\n")
        code, out, err = self.run_main("tree")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("denylist.list_unreadable", err)
        self.assert_no_secret(err)

    def test_clean_repository_exits_0(self) -> None:
        code, out, err = self.run_main(
            "--range", f"{self.base}..HEAD", "tree", "commits", "--all", "history"
        )
        self.assertEqual(code, 0, out + err)


class TestDenylistModes(ScanCase):
    def test_commits_range_scans_messages_identities_and_new_blobs_only(self) -> None:
        old = self.commit("docs: old", {"old.md": "zorblaxcorp before the range\n"})
        self.commit(
            "docs: drop and add\n\nMentions Frobhost.",
            {"old.md": "clean\n", "new.md": "a\nb qux123vel\n"},
        )
        code, out, err = self.run_main("--range", f"{old}..HEAD", "commits")
        self.assertEqual(code, 1, err)
        head = git(self.root, "rev-parse", "HEAD")
        blob = git(self.root, "rev-parse", "HEAD:new.md")
        self.assertCountEqual(
            self.findings(out),
            [
                (f"{head[:12]}:message:3:10", term_id(WORD)),
                (f"{blob[:12]}:new.md:2:3", term_id(REGEX)),
            ],
        )

    def test_commits_and_history_check_every_added_name(self) -> None:
        # Renamed files and directories and files whose content already exists
        # add no new object; their names must be checked all the same.
        self.commit("docs: base", {"a.txt": "a\n", "d/f": "f\n"})
        start = git(self.root, "rev-parse", "HEAD")
        git(self.root, "mv", "a.txt", "zorblaxcorp.txt")
        git(self.root, "mv", "d", "zorblaxcorp-dir")
        bad = self.commit(
            "docs: rename",
            {
                "copy-zorblaxcorp.txt": "Clean start.\n",
                "zorblaxcorp-empty": "",
                "a\nb zorblaxcorp": "x\n",
            },
        )
        git(self.root, "mv", "zorblaxcorp.txt", "a.txt")
        git(self.root, "mv", "zorblaxcorp-dir", "d")
        for name in ("copy-zorblaxcorp.txt", "zorblaxcorp-empty", "a\nb zorblaxcorp"):
            git(self.root, "rm", "-q", "--", name)
        self.commit("docs: rename back")
        names = (
            "zorblaxcorp.txt",
            "zorblaxcorp-dir",
            "zorblaxcorp-dir/f",
            "copy-zorblaxcorp.txt",
            "zorblaxcorp-empty",
            "a\nb zorblaxcorp",
        )
        for argv in (["--range", f"{start}..HEAD", "commits"], ["--all", "history"]):
            with self.subTest(argv=argv):
                code, out, err = self.run_main(*argv)
                self.assertEqual(code, 1, err)
                locations = {loc.rsplit(":", 2)[0] for loc, ident in self.findings(out)}
                for name in names:
                    path_id = "path-" + hashlib.sha256(name.encode("utf-8")).hexdigest()[:12]
                    self.assertIn(f"{bad[:12]}:{path_id}", locations, name)
                self.assert_no_secret(out, err)

    def test_history_finds_deleted_content(self) -> None:
        self.commit("docs: add", {"gone.md": "zorblaxcorp\n"})
        blob = git(self.root, "rev-parse", "HEAD:gone.md")
        git(self.root, "rm", "-q", "gone.md")
        self.commit("docs: remove")
        self.assertEqual(self.run_main("tree")[0], 0)
        code, out, _ = self.run_main("--all", "history")
        self.assertEqual(code, 1)
        self.assertIn((f"{blob[:12]}:gone.md:1:1", term_id(LITERAL)), self.findings(out))

    def test_allowed_identity_is_not_checked_against_terms(self) -> None:
        # The one allowed identity may itself hold listed terms (name, account).
        ada = "Ada Frobhost <ada@example.com>"
        self.authors_path.write_text(f"{ada}\n", encoding="utf-8")
        self.commit(
            f"feat: x\n\nSigned-off-by: {ada}\nCo-authored-by: {ada}",
            author=ada,
            committer=ada,
        )
        code, out, err = self.run_main("--range", f"{self.base}..HEAD", "commits")
        self.assertEqual((code, self.findings(out)), (0, []), out + err)

    def test_identity_not_allowed_is_checked_against_terms(self) -> None:
        eve = "Eve Frobhost <eve@example.com>"
        sha = self.commit(
            f"feat: x\n\nSigned-off-by: {eve}\nCo-authored-by: {AUTHOR}",
            author=eve,
        )
        code, out, _ = self.run_main("--range", f"{self.base}..HEAD", "commits")
        self.assertEqual(code, 1)
        self.assertCountEqual(
            self.findings(out),
            [
                (f"{sha[:12]}:message:3:20", term_id(WORD)),
                (f"{sha[:12]}:author:1:5", term_id(WORD)),
                (f"{sha[:12]}:author:1:1", "identity-not-allowed"),
            ],
        )
        self.assert_no_secret(out)

    def test_signoff_trailers_skip_the_generic_mail_rule(self) -> None:
        del os.environ["DENYLIST_FILE"]
        del os.environ["ALLOW_AUTHORS_FILE"]
        sha = self.commit(
            f"feat: x\n\nAsk {OPS}.\n\n"
            f"Signed-off-by: {FORK}\n"
            f"Co-authored-by: Helper <helper{MAIL_DOMAIN}>",
            author=FORK,
        )
        code, out, _ = self.run_main("--allow-missing", "--range", f"{self.base}..HEAD", "commits")
        self.assertEqual(code, 1)
        self.assertEqual(self.findings(out), [(f"{sha[:12]}:message:3:5", "generic-mail-address")])

    def test_range_and_all_must_match_the_modes(self) -> None:
        for argv in (["commits"], ["history"], ["--range", "HEAD", "tree"], ["--all", "tree"], []):
            with self.subTest(argv=argv):
                self.assertEqual(self.run_main(*argv)[0], 2)
        code, _, err = self.run_main("--range", "no-such-ref..HEAD", "commits")
        self.assertEqual(code, 2)
        self.assertIn("denylist.range_invalid", err)

    def test_internal_error_prints_no_text(self) -> None:
        with mock.patch.object(
            scan, "scan_tree", side_effect=ValueError("zorblaxcorp in a message")
        ):
            code, out, err = self.run_main("tree")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("denylist.internal_error type=ValueError", err)
        self.assert_no_secret(err)


class TestDenylistRepoConfig(unittest.TestCase):
    def test_repository_configuration_loads(self) -> None:
        rules = scan.load_generic(REPO_ROOT)
        self.assertEqual(
            sorted(rule.id for rule in rules.rules),
            ["generic-home-path", "generic-mail-address", "generic-private-ipv4"],
        )
        scan.load_exceptions(REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
