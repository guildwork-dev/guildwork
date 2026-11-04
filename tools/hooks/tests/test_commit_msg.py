# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/hooks/commit_msg.py.

TestCommitMsg checks single messages with check_message(). TestHookMode and
TestRangeMode run main() against a temporary git repository with its own
quality/commits files, so the global git configuration of the machine does
not take part. TestRepoConfig reads the real files of the repository.
"""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.hooks import commit_msg

REPO_ROOT = Path(__file__).resolve().parents[3]

AUTHOR_NAME = "Ada Example"
AUTHOR_EMAIL = "ada@example.com"
BOT_EMAIL = "release-bot@example.com"
BOTS = frozenset({BOT_EMAIL})
LIMITS = commit_msg.Limits(subject_max_length=72)

SIGNOFF = f"Signed-off-by: {AUTHOR_NAME} <{AUTHOR_EMAIL}>"


def message(subject: str, *trailers: str, body: str = "") -> str:
    parts = [subject]
    if body:
        parts.append(body)
    if trailers:
        parts.append("\n".join(trailers))
    return "\n\n".join(parts) + "\n"


def rules(text: str, email: str = AUTHOR_EMAIL, name: str = AUTHOR_NAME) -> list[str]:
    findings = commit_msg.check_message(
        text,
        author_name=name,
        author_email=email,
        bots=BOTS,
        limits=LIMITS,
        location="msg",
    )
    return [finding.rule for finding in findings]


class TestCommitMsg(unittest.TestCase):
    def test_accepts_valid_message(self) -> None:
        text = message(
            "feat(tools): check commit messages",
            "Plan-Task: R-E02-T02",
            "Co-Authored-By: Claude Code <noreply@anthropic.com>",
            SIGNOFF,
            body="Explain the change in a body paragraph.",
        )
        self.assertEqual(rules(text), [])

    def test_accepts_every_type_of_the_design(self) -> None:
        for kind in commit_msg.TYPES:
            with self.subTest(kind=kind):
                self.assertEqual(rules(message(f"{kind}: change one thing", SIGNOFF)), [])

    def test_accepts_scope_and_breaking_marker(self) -> None:
        for subject in ("feat(core)!: drop the old API", "fix(plugin-github): handle 404"):
            with self.subTest(subject=subject):
                self.assertEqual(rules(message(subject, SIGNOFF)), [])

    def test_rejects_missing_signoff(self) -> None:
        text = message(
            "fix: handle an empty range",
            "Co-Authored-By: Claude Code <noreply@anthropic.com>",
        )
        self.assertEqual(rules(text), ["signoff-missing"])

    def test_signoff_must_match_author(self) -> None:
        cases = {
            "other address": f"Signed-off-by: {AUTHOR_NAME} <someone@example.com>",
            "other name": f"Signed-off-by: Someone Else <{AUTHOR_EMAIL}>",
            "no address": f"Signed-off-by: {AUTHOR_NAME}",
        }
        for case, line in cases.items():
            with self.subTest(case=case):
                self.assertEqual(rules(message("fix: x", line)), ["signoff-author-mismatch"])

    def test_one_matching_signoff_is_enough(self) -> None:
        text = message("fix: x", "Signed-off-by: Someone Else <else@example.com>", SIGNOFF)
        self.assertEqual(rules(text), [])

    def test_co_authored_by_does_not_replace_signoff(self) -> None:
        text = message("fix: x", f"Co-Authored-By: {AUTHOR_NAME} <{AUTHOR_EMAIL}>")
        self.assertEqual(rules(text), ["signoff-missing"])

    def test_accepts_exact_bot_address_without_signoff(self) -> None:
        text = message("build(deps): update a dependency")
        self.assertEqual(rules(text, email=BOT_EMAIL, name="release-bot"), [])

    def test_rejects_bot_lookalike_address(self) -> None:
        lookalikes = (
            "Release-Bot@example.com",
            "release-bot@example.com.evil.example",
            "xrelease-bot@example.com",
            "release-bot+1@example.com",
            " release-bot@example.com",
        )
        for email in lookalikes:
            with self.subTest(email=email):
                text = message("build(deps): update a dependency")
                self.assertEqual(rules(text, email=email, name="release-bot"), ["signoff-missing"])

    def test_bot_exception_covers_only_the_signoff(self) -> None:
        text = message("Update dependency")
        self.assertEqual(rules(text, email=BOT_EMAIL), ["subject-not-conventional"])

    def test_rejects_non_conventional_subject(self) -> None:
        subjects = (
            "Add a checker",
            "feature: add a checker",
            "feat:add a checker",
            "feat: ",
            "feat(): add a checker",
            "feat(Core): add a checker",
            "Feat: add a checker",
            "Merge branch 'topic'",
            'Revert "feat: add a checker"',
            "",
        )
        for subject in subjects:
            with self.subTest(subject=subject):
                self.assertIn("subject-not-conventional", rules(message(subject, SIGNOFF)))

    def test_rejects_subject_over_the_limit(self) -> None:
        prefix = "docs: "
        exact = prefix + "a" * (72 - len(prefix))
        self.assertEqual(rules(message(exact, SIGNOFF)), [])
        self.assertEqual(rules(message(exact + "a", SIGNOFF)), ["subject-too-long"])

    def test_rejects_subject_with_trailing_period(self) -> None:
        self.assertEqual(rules(message("docs: fix a typo.", SIGNOFF)), ["subject-trailing-period"])

    def test_rejects_body_without_blank_line(self) -> None:
        text = f"fix: x\nbody starts here\n\n{SIGNOFF}\n"
        self.assertEqual(rules(text), ["body-no-blank-line"])

    def test_rejects_malformed_plan_task_trailer(self) -> None:
        malformed = (
            "Plan-Task: R-E2-T02",
            "Plan-Task: r-e02-t02",
            "Plan-Task: R-E02-T02-S01",
            "Plan-Task: R-E02-T02 and more",
            "Plan-Task: X-E02-T02",
            "Plan-Task: 11-E01-T01",
            "Plan-Task:",
            "plan-task: none",
        )
        for line in malformed:
            with self.subTest(line=line):
                self.assertEqual(rules(message("fix: x", line, SIGNOFF)), ["plan-task-malformed"])

    def test_accepts_every_plan_task_id_form(self) -> None:
        for task in ("R-E02-T02", "0b-E01-T03", "7a-E10-T01", "10-E02-T05", "3-E05-T07"):
            with self.subTest(task=task):
                self.assertEqual(rules(message("fix: x", f"Plan-Task: {task}", SIGNOFF)), [])

    def test_rejects_dashes_in_the_message(self) -> None:
        # FE-022: the dash characters U+2012 to U+2015, written as escapes here.
        for dash in ("\u2012", "\u2013", "\u2014", "\u2015"):
            with self.subTest(dash=f"U+{ord(dash):04X}"):
                subject = message(f"fix: one {dash} two", SIGNOFF)
                self.assertEqual(rules(subject), ["message-dash"])
                body = message("fix: x", SIGNOFF, body=f"Line one.\nA {dash} B {dash} C.")
                self.assertEqual(rules(body), ["message-dash"])

    def test_finding_names_location_and_line(self) -> None:
        findings = commit_msg.check_message(
            message("fix: x", "Plan-Task: R-E2-T02", SIGNOFF),
            author_name=AUTHOR_NAME,
            author_email=AUTHOR_EMAIL,
            bots=BOTS,
            limits=LIMITS,
            location="0123456789ab",
        )
        self.assertEqual(len(findings), 1)
        self.assertTrue(str(findings[0]).startswith("0123456789ab:3:1 plan-task-malformed "))


def git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", "-C", str(root), *args],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


class GitRepoCase(unittest.TestCase):
    """A temporary repository with quality/commits files and an isolated git."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": tmp.name,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": AUTHOR_NAME,
            "GIT_AUTHOR_EMAIL": AUTHOR_EMAIL,
            "GIT_COMMITTER_NAME": AUTHOR_NAME,
            "GIT_COMMITTER_EMAIL": AUTHOR_EMAIL,
        }
        patcher = mock.patch.dict(os.environ, self.env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        git(self.root, "init", "-q", "-b", "main")
        commits = self.root / "quality" / "commits"
        commits.mkdir(parents=True)
        (commits / "limits.toml").write_text("subject_max_length = 72\n", encoding="utf-8")
        (commits / "bots.txt").write_text(f"# bots\n{BOT_EMAIL}\n", encoding="utf-8")

    def commit(self, text: str, **identity: str) -> str:
        env = dict(self.env)
        env.update(identity)
        git(self.root, "commit", "-q", "--allow-empty", "-m", text, env=env)
        return git(self.root, "rev-parse", "HEAD")

    def run_main(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = commit_msg.main(["--root", str(self.root), *argv])
        return code, out.getvalue(), err.getvalue()


class TestHookMode(GitRepoCase):
    def write_message(self, text: str) -> str:
        path = self.root / "COMMIT_EDITMSG"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_accepts_message_of_the_current_author(self) -> None:
        code, out, _ = self.run_main(self.write_message(message("fix: x", SIGNOFF)))
        self.assertEqual((code, out), (0, ""))

    def test_reads_the_author_from_git(self) -> None:
        os.environ["GIT_AUTHOR_EMAIL"] = "other@example.com"
        code, out, _ = self.run_main(self.write_message(message("fix: x", SIGNOFF)))
        self.assertEqual(code, 1)
        self.assertIn("signoff-author-mismatch", out)

    def test_ignores_comment_lines_and_the_scissors_part(self) -> None:
        text = (
            "fix: x\n"
            "# Please enter the commit message for your changes.\n"
            "\n"
            f"{SIGNOFF}\n"
            "# ------------------------ >8 ------------------------\n"
            "Plan-Task: broken\n"
        )
        code, out, _ = self.run_main(self.write_message(text))
        self.assertEqual((code, out), (0, ""))

    def test_missing_message_file_is_a_usage_error(self) -> None:
        code, _, err = self.run_main(str(self.root / "missing"))
        self.assertEqual(code, 2)
        self.assertIn("commitlint.message_unreadable", err)


class TestRangeMode(GitRepoCase):
    def test_checks_every_commit_including_merges(self) -> None:
        first = self.commit(message("chore: start", SIGNOFF))
        git(self.root, "checkout", "-q", "-b", "task/R-E01-T01")
        self.commit(message("feat: add a part", "Plan-Task: R-E01-T01", SIGNOFF))
        git(self.root, "checkout", "-q", "main")
        self.commit(message("docs: describe the start", SIGNOFF))
        git(
            self.root,
            "merge",
            "-q",
            "--no-ff",
            "-m",
            message("chore: merge task R-E01-T01 part", "Plan-Task: R-E01-T01", SIGNOFF),
            "task/R-E01-T01",
            env=self.env,
        )
        code, out, _ = self.run_main("--range", f"{first}..HEAD")
        self.assertEqual(code, 0, out)
        self.assertIn("checked 3 commits", out)

    def test_reports_bad_commits_with_their_sha(self) -> None:
        first = self.commit(message("chore: start", SIGNOFF))
        bad = self.commit(message("Add a part"))
        self.commit(message("fix: x", SIGNOFF))
        code, out, _ = self.run_main("--range", f"{first}..HEAD")
        self.assertEqual(code, 1)
        self.assertIn(f"{bad[:12]}:1:1 subject-not-conventional", out)
        self.assertIn(f"{bad[:12]}:1:1 signoff-missing", out)
        self.assertIn("checked 2 commits", out)

    def test_default_merge_message_fails(self) -> None:
        first = self.commit(message("chore: start", SIGNOFF))
        git(self.root, "checkout", "-q", "-b", "topic")
        self.commit(message("feat: add a part", SIGNOFF))
        git(self.root, "checkout", "-q", "main")
        self.commit(message("docs: describe the start", SIGNOFF))
        git(self.root, "merge", "-q", "--no-ff", "--no-edit", "topic", env=self.env)
        code, out, _ = self.run_main("--range", f"{first}..HEAD")
        self.assertEqual(code, 1)
        self.assertIn("subject-not-conventional", out)
        self.assertIn("signoff-missing", out)

    def test_uses_the_author_of_each_commit(self) -> None:
        first = self.commit(message("chore: start", SIGNOFF))
        self.commit(
            message("build(deps): update a dependency"),
            GIT_AUTHOR_NAME="release-bot",
            GIT_AUTHOR_EMAIL=BOT_EMAIL,
        )
        code, out, _ = self.run_main("--range", f"{first}..HEAD")
        self.assertEqual(code, 0, out)

    def test_empty_range_passes(self) -> None:
        self.commit(message("chore: start", SIGNOFF))
        code, out, _ = self.run_main("--range", "HEAD..HEAD")
        self.assertEqual(code, 0)
        self.assertIn("checked 0 commits", out)

    def test_unknown_range_is_a_usage_error(self) -> None:
        self.commit(message("chore: start", SIGNOFF))
        for bad in ("nope..HEAD", "--all", ""):
            with self.subTest(range=bad):
                code, _, err = self.run_main(f"--range={bad}")
                self.assertEqual(code, 2)
                self.assertIn("commitlint.range_invalid", err)

    def test_invalid_limits_is_a_config_error(self) -> None:
        self.commit(message("chore: start", SIGNOFF))
        limits = self.root / "quality" / "commits" / "limits.toml"
        for text in ("", "subject_max_length = 0\n", 'subject_max_length = "72"\n', "x = ["):
            with self.subTest(text=text):
                limits.write_text(text, encoding="utf-8")
                code, _, err = self.run_main("--range", "HEAD")
                self.assertEqual(code, 2)
                self.assertIn("commitlint.config_invalid", err)


class TestRepoConfig(unittest.TestCase):
    def test_subject_limit_is_72(self) -> None:
        self.assertEqual(commit_msg.load_limits(REPO_ROOT), commit_msg.Limits(72))

    def test_bots_file_lists_addresses_only(self) -> None:
        for address in commit_msg.load_bots(REPO_ROOT):
            self.assertRegex(address, r"^[^\s@<>]+@[^\s@<>]+$")


if __name__ == "__main__":
    unittest.main()
