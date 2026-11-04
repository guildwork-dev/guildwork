#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Fetch the pinned tool binaries listed in tools.toml and verify their SHA-256.

Standard library only (FE-004). Binaries go to `.tools/bin/` of the repository
for the host platform; nothing is installed system wide and `sudo` is never
used (FE-005). A download whose SHA-256 differs from tools.toml is deleted and
the run stops with exit code 1.

Exit codes:
  0  every requested tool is installed and verified
  1  a download failed, a checksum did not match or an archive lacked the binary
  2  configuration error: unreadable or invalid tools.toml, unknown platform,
     platform not listed for a tool, unknown tool name

`--platform` forces a platform other than the host, for example to verify the
linux_x64 downloads on a macOS machine. Binaries of a foreign platform go to
`.tools/platforms/<platform>/bin/` unless `--dest` is given, so they never
replace the host binaries in `.tools/bin/`.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import http.client
import os
import platform
import re
import sys
import tarfile
import tempfile
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFIG = 2

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path(__file__).resolve().with_name("tools.toml")

OS_NAMES = {"Linux": "linux", "Darwin": "darwin"}
ARCH_NAMES = {"x86_64": "x64", "amd64": "x64", "arm64": "arm64", "aarch64": "arm64"}
KNOWN_PLATFORMS = frozenset(
    f"{os_}_{arch}" for os_ in OS_NAMES.values() for arch in ARCH_NAMES.values()
)

# https for real downloads; file only so that tests run the real path offline.
ALLOWED_SCHEMES = frozenset({"https", "file"})
TOOL_NAME = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_KEYS = ("version", "url", "target", "sha256", "source", "retrieved")
# Container images ([images.<name>], pinned by digest) share tools.toml but are
# not fetched here; tools/ci/scancode_policy.py reads [images.scancode].
IMAGES_KEY = "images"
DOWNLOAD_TIMEOUT_S = 120
CHUNK_BYTES = 1 << 16


class ConfigError(Exception):
    """tools.toml or the requested platform cannot be used."""


class FetchError(Exception):
    """A download or the verification of a download failed."""


@dataclass(frozen=True)
class Tool:
    name: str
    version: str
    url: str
    target: dict[str, str]
    sha256: dict[str, str]
    source: str
    retrieved: str
    member: str | None

    def _render(self, template: str, platform_id: str) -> str:
        return template.format(version=self.version, target=self.target[platform_id])

    def url_for(self, platform_id: str) -> str:
        return self._render(self.url, platform_id)

    def member_for(self, platform_id: str) -> str | None:
        return None if self.member is None else self._render(self.member, platform_id)


def detect_platform() -> str:
    os_name = OS_NAMES.get(platform.system())
    arch = ARCH_NAMES.get(platform.machine().lower())
    if os_name is None or arch is None:
        raise ConfigError(
            f"bootstrap.unknown_platform system={platform.system()} machine={platform.machine()}"
        )
    return f"{os_name}_{arch}"


def default_dest(platform_id: str, *, repo_root: Path = REPO_ROOT) -> Path:
    try:
        host = detect_platform()
    except ConfigError:
        host = None
    if platform_id == host:
        return repo_root / ".tools" / "bin"
    return repo_root / ".tools" / "platforms" / platform_id / "bin"


def _invalid(name: str, reason: str, *, key: str = "") -> ConfigError:
    where = f" key={key}" if key else ""
    return ConfigError(f"bootstrap.config_invalid tool={name}{where} reason={reason}")


def _string(entry: dict[str, object], name: str, key: str) -> str:
    value = entry[key]
    if not isinstance(value, str) or not value:
        raise _invalid(name, "not_a_string", key=key)
    return value


def _string_table(entry: dict[str, object], name: str, key: str) -> dict[str, str]:
    value = entry[key]
    if not isinstance(value, dict) or not value:
        raise _invalid(name, "not_a_table", key=key)
    table: dict[str, str] = {}
    for platform_id, item in value.items():
        if platform_id not in KNOWN_PLATFORMS or not isinstance(item, str) or not item:
            raise _invalid(name, "bad_entry", key=f"{key}.{platform_id}")
        table[platform_id] = item
    return table


def _check_url(name: str, url: str) -> None:
    scheme = urllib.parse.urlsplit(url).scheme
    if scheme not in ALLOWED_SCHEMES:
        raise _invalid(name, f"scheme_{scheme or 'missing'}")


def _parse_tool(name: str, entry: object) -> Tool:
    if not TOOL_NAME.match(name) or not isinstance(entry, dict):
        raise _invalid(name, "bad_table")
    missing = [key for key in REQUIRED_KEYS if key not in entry]
    if missing:
        raise _invalid(name, f"missing_{','.join(missing)}")
    unknown = sorted(set(entry) - set(REQUIRED_KEYS) - {"member"})
    if unknown:
        raise _invalid(name, f"unknown_{','.join(unknown)}")

    member = _string(entry, name, "member") if "member" in entry else None
    tool = Tool(
        name=name,
        version=_string(entry, name, "version"),
        url=_string(entry, name, "url"),
        target=_string_table(entry, name, "target"),
        sha256=_string_table(entry, name, "sha256"),
        source=_string(entry, name, "source"),
        retrieved=_string(entry, name, "retrieved"),
        member=member,
    )
    if set(tool.target) != set(tool.sha256):
        raise _invalid(name, "target_sha256_platforms_differ")
    for platform_id, digest in tool.sha256.items():
        if not SHA256_HEX.match(digest):
            raise _invalid(name, "not_hex64", key=f"sha256.{platform_id}")
    try:
        datetime.date.fromisoformat(tool.retrieved)
    except ValueError as exc:
        raise _invalid(name, "not_a_date", key="retrieved") from exc
    _check_url(name, tool.source)
    for platform_id in tool.target:
        try:
            url = tool.url_for(platform_id)
            tool.member_for(platform_id)
        except (KeyError, IndexError, ValueError) as exc:
            raise _invalid(name, "bad_placeholder") from exc
        _check_url(name, url)
        if url.endswith(".tar.gz") != (tool.member is not None):
            raise _invalid(name, "member_requires_tar_gz")
    return tool


def load_config(path: Path) -> dict[str, Tool]:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        reason = type(exc).__name__
        raise ConfigError(f"bootstrap.config_invalid path={path} reason={reason}") from exc
    if not raw:
        raise ConfigError(f"bootstrap.config_invalid path={path} reason=no_tools")
    return {name: _parse_tool(name, entry) for name, entry in raw.items() if name != IMAGES_KEY}


def _download(url: str, target: Path) -> str:
    """Write the body of `url` to `target` and return its SHA-256 hex digest."""
    digest = hashlib.sha256()
    try:
        # The scheme is restricted to https and file in _check_url.
        response = urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_S)  # noqa: S310
        with response, target.open("wb") as out:
            while chunk := response.read(CHUNK_BYTES):
                digest.update(chunk)
                out.write(chunk)
    except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
        reason = type(exc).__name__
        raise FetchError(f"bootstrap.download_failed url={url} reason={reason}") from exc
    return digest.hexdigest()


def _extract_member(archive: Path, member: str, target: Path) -> None:
    try:
        with tarfile.open(archive, mode="r:gz") as tar:
            try:
                info = tar.getmember(member)
            except KeyError:
                info = None
            source = tar.extractfile(info) if info is not None and info.isfile() else None
            if source is None:
                raise FetchError(f"bootstrap.archive_member_missing member={member}")
            with source, target.open("wb") as out:
                while chunk := source.read(CHUNK_BYTES):
                    out.write(chunk)
    except (tarfile.TarError, OSError) as exc:
        raise FetchError(f"bootstrap.archive_invalid reason={type(exc).__name__}") from exc


def _stamp(dest: Path, tool: Tool) -> Path:
    return dest / f".{tool.name}.sha256"


def is_current(tool: Tool, platform_id: str, dest: Path) -> bool:
    stamp = _stamp(dest, tool)
    if not (dest / tool.name).is_file() or not stamp.is_file():
        return False
    return stamp.read_text(encoding="utf-8").strip() == tool.sha256[platform_id]


def install(tool: Tool, platform_id: str, dest: Path) -> None:
    """Download, verify and install one tool. Leaves no partial file behind."""
    dest.mkdir(parents=True, exist_ok=True)
    expected = tool.sha256[platform_id]
    url = tool.url_for(platform_id)
    member = tool.member_for(platform_id)
    temp_paths: list[Path] = []

    def temp_file(suffix: str) -> Path:
        handle, name = tempfile.mkstemp(prefix=f".{tool.name}.", suffix=suffix, dir=dest)
        os.close(handle)
        temp_paths.append(Path(name))
        return Path(name)

    try:
        download = temp_file(".part")
        actual = _download(url, download)
        if actual != expected:
            raise FetchError(
                f"bootstrap.checksum_mismatch tool={tool.name} platform={platform_id} "
                f"expected={expected} actual={actual}"
            )
        binary = download
        if member is not None:
            binary = temp_file(".bin")
            try:
                _extract_member(download, member, binary)
            except FetchError as exc:
                raise FetchError(f"{exc} tool={tool.name} platform={platform_id}") from exc
        binary.chmod(0o755)
        os.replace(binary, dest / tool.name)
        _stamp(dest, tool).write_text(expected + "\n", encoding="utf-8")
    finally:
        for path in temp_paths:
            path.unlink(missing_ok=True)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch pinned tool binaries and verify SHA-256.")
    add = parser.add_argument
    add("--config", type=Path, default=DEFAULT_CONFIG, help="path of tools.toml")
    add("--platform", help="platform id such as linux_x64; default: the host")
    add("--dest", type=Path, help="target directory; default: .tools/bin for the host")
    add("--only", action="append", default=[], metavar="TOOL", help="fetch only this tool")
    add("--force", action="store_true", help="download even if the installed copy is current")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        platform_id: str = args.platform or detect_platform()
        if platform_id not in KNOWN_PLATFORMS:
            raise ConfigError(f"bootstrap.unknown_platform platform={platform_id}")
        tools = load_config(args.config)
        unknown = sorted(set(args.only) - set(tools))
        if unknown:
            raise ConfigError(f"bootstrap.unknown_tool tool={','.join(unknown)}")
        selected = [tools[name] for name in (args.only or tools)]
        for tool in selected:
            if platform_id not in tool.sha256:
                raise ConfigError(
                    f"bootstrap.platform_unsupported tool={tool.name} platform={platform_id}"
                )
    except ConfigError as exc:
        print(exc, file=sys.stderr)
        return EXIT_CONFIG

    dest: Path = args.dest or default_dest(platform_id)
    for tool in selected:
        if not args.force and is_current(tool, platform_id, dest):
            print(
                f"bootstrap.current tool={tool.name} version={tool.version} platform={platform_id}"
            )
            continue
        try:
            install(tool, platform_id, dest)
        except FetchError as exc:
            print(exc, file=sys.stderr)
            return EXIT_FAILED
        print(
            f"bootstrap.installed tool={tool.name} version={tool.version} platform={platform_id} "
            f"sha256={tool.sha256[platform_id]}"
        )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
