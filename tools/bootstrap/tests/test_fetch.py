# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/bootstrap/fetch.py.

Downloads use file:// URLs into a temporary directory, so the tests run
offline and still go through the real download, verify and install path.
"""

from __future__ import annotations

import contextlib
import hashlib
import http.client
import io
import re
import tarfile
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

from tools.bootstrap import fetch

REPO_TOOLS_TOML = Path(__file__).resolve().parents[1] / "tools.toml"
REQUIRED_TOOLS = {"uv", "gitleaks", "opengrep", "osv-scanner", "actionlint"}
REQUIRED_PLATFORMS = {"linux_x64", "darwin_arm64"}
WRONG_SHA256 = "0" * 64


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_tar_gz(path: Path, members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, payload in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(payload))
    data = buffer.getvalue()
    path.write_bytes(data)
    return data


class FetchCase(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.srv = self.root / "srv"
        self.srv.mkdir()
        self.dest = self.root / "bin"
        self.config = self.root / "tools.toml"

    def uri(self, name: str) -> str:
        # Path.as_uri() would percent-encode the {placeholders} of the template.
        return f"file://{self.srv.as_posix()}/{name}"

    def write_config(self, body: str) -> None:
        self.config.write_text(body, encoding="utf-8")

    def tool_entry(
        self,
        name: str,
        url: str,
        sha256: str,
        *,
        member: str | None = None,
        platform: str = "linux_x64",
        target: str = "linux-amd64",
    ) -> str:
        lines = [
            f"[{name}]",
            'version = "1.2.3"',
            f'url = "{url}"',
            f'target = {{ {platform} = "{target}" }}',
            f'sha256 = {{ {platform} = "{sha256}" }}',
            'source = "https://example.org/checksums.txt"',
            'retrieved = "2026-11-01"',
        ]
        if member is not None:
            lines.append(f'member = "{member}"')
        return "\n".join(lines) + "\n"

    def run_fetch(self, *args: str) -> tuple[int, str]:
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = fetch.main(["--config", str(self.config), "--dest", str(self.dest), *args])
        return code, err.getvalue()


class TestFetch(FetchCase):
    def test_checksum_mismatch_deletes_file_and_exits_1(self) -> None:
        payload = b"#!/bin/sh\necho tampered\n"
        (self.srv / "demo-linux-amd64").write_bytes(payload)
        url = self.uri("demo-{target}")
        self.write_config(self.tool_entry("demo", url, WRONG_SHA256))

        code, err = self.run_fetch("--platform", "linux_x64")

        self.assertEqual(code, 1)
        self.assertIn("bootstrap.checksum_mismatch", err)
        self.assertIn("tool=demo", err)
        self.assertIn(f"expected={WRONG_SHA256}", err)
        self.assertIn(f"actual={sha256_hex(payload)}", err)
        leftovers = list(self.dest.rglob("*")) if self.dest.exists() else []
        self.assertEqual(leftovers, [], "downloaded file must be deleted on mismatch")

    def test_checksum_mismatch_keeps_previous_binary_untouched(self) -> None:
        good = b"good binary\n"
        (self.srv / "demo-linux-amd64").write_bytes(good)
        url = self.uri("demo-{target}")
        self.write_config(self.tool_entry("demo", url, sha256_hex(good)))
        self.assertEqual(self.run_fetch("--platform", "linux_x64")[0], 0)

        (self.srv / "demo-linux-amd64").write_bytes(b"evil\n")
        self.write_config(self.tool_entry("demo", url, WRONG_SHA256))
        code, _ = self.run_fetch("--platform", "linux_x64", "--force")

        self.assertEqual(code, 1)
        self.assertEqual((self.dest / "demo").read_bytes(), good)
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), [".demo.sha256", "demo"])

    def test_unknown_platform_exits_2(self) -> None:
        self.write_config(self.tool_entry("demo", "https://example.org/demo", WRONG_SHA256))

        code, err = self.run_fetch("--platform", "plan9_mips")

        self.assertEqual(code, 2)
        self.assertIn("bootstrap.unknown_platform", err)
        self.assertFalse(self.dest.exists())

    def test_unknown_host_platform_exits_2(self) -> None:
        self.write_config(self.tool_entry("demo", "https://example.org/demo", WRONG_SHA256))

        with mock.patch("platform.system", return_value="Plan9"):
            code, err = self.run_fetch()

        self.assertEqual(code, 2)
        self.assertIn("bootstrap.unknown_platform", err)

    def test_platform_missing_for_tool_exits_2(self) -> None:
        self.write_config(
            self.tool_entry(
                "demo", "https://example.org/demo", WRONG_SHA256, platform="darwin_arm64"
            )
        )

        code, err = self.run_fetch("--platform", "linux_x64")

        self.assertEqual(code, 2)
        self.assertIn("bootstrap.platform_unsupported", err)
        self.assertIn("tool=demo", err)

    def test_images_table_is_not_a_tool(self) -> None:
        payload = b"#!/bin/sh\necho ok\n"
        (self.srv / "demo-linux-amd64").write_bytes(payload)
        tool = self.tool_entry("demo", self.uri("demo-{target}"), sha256_hex(payload))
        image = '[images.scancode]\nimage = "docker.io/library/python"\n'
        self.write_config(tool + image)

        code, err = self.run_fetch("--platform", "linux_x64")

        self.assertEqual((code, err), (0, ""))
        self.assertEqual(set(fetch.load_config(self.config)), {"demo"})

    def test_truncated_download_exits_1(self) -> None:
        # M164: a connection that ends early raised IncompleteRead as a traceback.
        self.write_config(self.tool_entry("demo", "https://example.org/demo", WRONG_SHA256))
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.side_effect = http.client.IncompleteRead(b"partial", 10)

        with mock.patch("urllib.request.urlopen", return_value=response):
            code, err = self.run_fetch("--platform", "linux_x64")

        self.assertEqual(code, 1)
        self.assertIn("bootstrap.download_failed", err)
        self.assertIn("reason=IncompleteRead", err)
        leftovers = list(self.dest.rglob("*")) if self.dest.exists() else []
        self.assertEqual(leftovers, [])

    def test_raw_binary_is_installed_executable(self) -> None:
        payload = b"#!/bin/sh\necho ok\n"
        (self.srv / "demo-linux-amd64").write_bytes(payload)
        url = self.uri("demo-{target}")
        self.write_config(self.tool_entry("demo", url, sha256_hex(payload)))

        code, _ = self.run_fetch("--platform", "linux_x64")

        self.assertEqual(code, 0)
        installed = self.dest / "demo"
        self.assertEqual(installed.read_bytes(), payload)
        self.assertTrue(installed.stat().st_mode & 0o111)

    def test_tar_gz_member_is_extracted(self) -> None:
        data = make_tar_gz(
            self.srv / "demo_1.2.3_linux-amd64.tar.gz",
            {"README.md": b"readme", "pkg-linux-amd64/demo": b"binary"},
        )
        url = self.uri("demo_{version}_{target}.tar.gz")
        self.write_config(
            self.tool_entry("demo", url, sha256_hex(data), member="pkg-{target}/demo")
        )

        code, _ = self.run_fetch("--platform", "linux_x64")

        self.assertEqual(code, 0)
        self.assertEqual((self.dest / "demo").read_bytes(), b"binary")
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), [".demo.sha256", "demo"])

    def test_missing_archive_member_exits_1(self) -> None:
        data = make_tar_gz(self.srv / "demo.tar.gz", {"other": b"x"})
        url = self.uri("demo.tar.gz")
        self.write_config(self.tool_entry("demo", url, sha256_hex(data), member="demo"))

        code, err = self.run_fetch("--platform", "linux_x64")

        self.assertEqual(code, 1)
        self.assertIn("bootstrap.archive_member_missing", err)
        self.assertFalse((self.dest / "demo").exists())

    def test_plain_http_url_is_a_config_error(self) -> None:
        self.write_config(self.tool_entry("demo", "http://example.org/demo", WRONG_SHA256))

        code, err = self.run_fetch("--platform", "linux_x64")

        self.assertEqual(code, 2)
        self.assertIn("bootstrap.config_invalid", err)

    def test_second_run_skips_download_when_stamp_matches(self) -> None:
        payload = b"binary"
        source = self.srv / "demo-linux-amd64"
        source.write_bytes(payload)
        self.write_config(self.tool_entry("demo", self.uri("demo-{target}"), sha256_hex(payload)))
        self.assertEqual(self.run_fetch("--platform", "linux_x64")[0], 0)

        source.unlink()
        code, _ = self.run_fetch("--platform", "linux_x64")

        self.assertEqual(code, 0)
        self.assertEqual((self.dest / "demo").read_bytes(), payload)

    def test_forced_foreign_platform_never_writes_default_bin(self) -> None:
        host = fetch.detect_platform()
        foreign = "linux_x64" if host != "linux_x64" else "darwin_arm64"
        self.assertEqual(
            fetch.default_dest(foreign, repo_root=self.root),
            self.root / ".tools" / "platforms" / foreign / "bin",
        )
        self.assertEqual(
            fetch.default_dest(host, repo_root=self.root), self.root / ".tools" / "bin"
        )


class TestToolsToml(unittest.TestCase):
    def test_lists_every_required_tool_for_required_platforms(self) -> None:
        tools = fetch.load_config(REPO_TOOLS_TOML)

        self.assertTrue(set(tools) >= REQUIRED_TOOLS, sorted(REQUIRED_TOOLS - set(tools)))
        for tool in tools.values():
            with self.subTest(tool=tool.name):
                self.assertTrue(set(tool.sha256) >= REQUIRED_PLATFORMS)
                self.assertTrue(tool.url.startswith("https://"))
                self.assertTrue(tool.source.startswith("https://"))
                self.assertRegex(tool.retrieved, r"^\d{4}-\d{2}-\d{2}$")
                for digest in tool.sha256.values():
                    self.assertRegex(digest, r"^[0-9a-f]{64}$")

    def test_versions_are_exact(self) -> None:
        raw = tomllib.loads(REPO_TOOLS_TOML.read_text(encoding="utf-8"))
        raw.pop("images", None)  # container images are pinned by digest, not version
        for name, entry in raw.items():
            with self.subTest(tool=name):
                self.assertTrue(re.fullmatch(r"\d+\.\d+\.\d+", entry["version"]))


if __name__ == "__main__":
    unittest.main()
