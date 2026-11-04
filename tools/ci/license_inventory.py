# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""What the license gate and THIRD_PARTY_NOTICES read: dependencies and adopted files.

npm: `pnpm --recursive licenses list --json` over the whole workspace, once
for all installed packages and once with --prod for the runtime ones (output
form of pnpm 12.16.1, recorded 2026-11-01: an object keyed by license
expression, each value a list of packages with name, versions, paths,
license, author). Workspace packages (@guildwork/) are
own code and left out. pnpm reads the installed node_modules, so `make
bootstrap` must have run.

Python: uv.lock lists the packages; runtime are those reachable from the
dependencies of the project itself (the tools use the standard library only,
FE-004, so today none), everything else is a development dependency. The
license comes from the installed metadata in .venv: License-Expression, else a
one-line License field; license classifiers are not mapped, a package without
an SPDX value needs an entry in dev-exceptions.txt.

Adopted files: tracked files with a header of their source and an Origin line
(architecture 12 section 2.4).

Standard library only (FE-004).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from email.parser import HeaderParser
from pathlib import Path

from tools.ci import spdx_header

LOCKFILES = {"npm": "pnpm-lock.yaml", "python": "uv.lock"}
OWN_SCOPE = "@guildwork/"
# Command that runs pnpm; the Makefile runs pnpm through Corepack.
PNPM_DEFAULT = "corepack pnpm"
VENV_SITE_GLOB = ".venv/lib/python*/site-packages"
LICENSE_FILE = re.compile(r"^(?:LICEN[CS]E|COPYING|NOTICE)(?:[.-].*)?$", re.IGNORECASE)
# A License field longer than this is a pasted license text, not an expression.
MAX_LICENSE_FIELD = 100


class InventoryError(Exception):
    """pnpm, uv.lock or the Python environment cannot be read."""

    def __init__(self, reason: str, path: str) -> None:
        super().__init__(reason)
        self.path = path


@dataclass(frozen=True)
class Dependency:
    ecosystem: str  # npm or python
    name: str
    version: str
    license: str | None  # SPDX expression as declared; None if the package declares none
    runtime: bool
    license_files: tuple[str, ...] = ()
    author: str | None = None

    @property
    def key(self) -> str:
        """`<name>@<version>`, the key of dev-exceptions.txt."""
        return f"{self.name}@{self.version}"

    @property
    def lockfile(self) -> str:
        return LOCKFILES[self.ecosystem]


@dataclass(frozen=True)
class AdoptedFile:
    path: str
    license: str
    copyrights: tuple[str, ...]
    origin: str


# ---------------------------------------------------------------------------
# Files


def tracked_files(root: Path) -> list[str]:
    """Tracked and untracked, not ignored files (posix, relative), sorted."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],  # noqa: S607
            cwd=root,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise InventoryError("git ls-files failed; the root must be a git repository", ".") from exc
    names = {name for name in result.stdout.decode("utf-8").split("\0") if name}
    return sorted(name for name in names if (root / name).is_file())


def adopted_files(root: Path, files: Sequence[str]) -> list[AdoptedFile]:
    """Files whose header names a license, a copyright holder and an Origin."""
    parts = []
    for path in files:
        try:
            spdx_header.comment_prefix(Path(path))
            text = (root / path).read_text(encoding="utf-8")
        except (ValueError, OSError, UnicodeDecodeError):
            continue
        tags = spdx_header.header_tags(Path(path), text)
        values: dict[str, list[str]] = {}
        for _, tag, value in tags:
            values.setdefault(tag, []).append(value)
        licenses = values.get(spdx_header.LICENSE_TAG)
        origins = values.get(spdx_header.ORIGIN_TAG)
        copyrights = values.get(spdx_header.COPYRIGHT_TAG)
        if licenses and origins and copyrights:
            parts.append(AdoptedFile(path, licenses[0], tuple(copyrights), origins[0]))
    return parts


def license_files_in(directory: Path) -> tuple[str, ...]:
    """License, copying and notice files directly in directory, sorted."""
    if not directory.is_dir():
        return ()
    return tuple(
        str(child)
        for child in sorted(directory.iterdir())
        if child.is_file() and LICENSE_FILE.match(child.name)
    )


# ---------------------------------------------------------------------------
# npm


def _pnpm_packages(text: str, what: str) -> list[dict[str, object]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InventoryError(f"{what}: not JSON", LOCKFILES["npm"]) from exc
    if not isinstance(data, dict) or not all(isinstance(v, list) for v in data.values()):
        raise InventoryError(f"{what}: expected an object of lists", LOCKFILES["npm"])
    packages: list[dict[str, object]] = []
    for entries in data.values():
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
                raise InventoryError(f"{what}: package without name", LOCKFILES["npm"])
            packages.append(entry)
    return packages


def _versions(entry: dict[str, object]) -> list[tuple[str, str | None]]:
    versions = entry.get("versions")
    paths = entry.get("paths")
    if not isinstance(versions, list) or not all(isinstance(v, str) for v in versions):
        raise InventoryError(f"{entry['name']}: versions missing", LOCKFILES["npm"])
    path_list = paths if isinstance(paths, list) and len(paths) == len(versions) else []
    return [
        (version, path_list[i] if path_list and isinstance(path_list[i], str) else None)
        for i, version in enumerate(versions)
    ]


def parse_pnpm(all_json: str, prod_json: str) -> list[Dependency]:
    """Dependencies from the two outputs of `pnpm licenses list --json [--prod]`."""
    runtime = {
        (str(entry["name"]), version)
        for entry in _pnpm_packages(prod_json, "pnpm licenses list --prod")
        for version, _ in _versions(entry)
    }
    deps = []
    for entry in _pnpm_packages(all_json, "pnpm licenses list"):
        name = str(entry["name"])
        if name.startswith(OWN_SCOPE):
            continue
        license = entry.get("license")
        author = entry.get("author")
        for version, path in _versions(entry):
            deps.append(
                Dependency(
                    ecosystem="npm",
                    name=name,
                    version=version,
                    license=license if isinstance(license, str) and license else None,
                    runtime=(name, version) in runtime,
                    license_files=license_files_in(Path(path)) if path else (),
                    author=author if isinstance(author, str) and author else None,
                )
            )
    return sorted(deps, key=lambda d: (d.name, d.version))


def _run(command: Sequence[str], root: Path) -> str:
    try:
        result = subprocess.run(  # noqa: S603
            list(command), cwd=root, capture_output=True, text=True, check=False
        )
    except OSError as exc:
        raise InventoryError(f"cannot run {command[0]}: {exc}", LOCKFILES["npm"]) from exc
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1:] or ["no output"]
        raise InventoryError(
            f"`{' '.join(command)}` exited {result.returncode} ({detail[0]}); "
            "run make bootstrap first",
            LOCKFILES["npm"],
        )
    return result.stdout


def npm_dependencies(root: Path, pnpm: Sequence[str] | None = None) -> list[Dependency]:
    """npm dependencies of the installed workspace at root."""
    if pnpm is None:
        pnpm = shlex.split(os.environ.get("PNPM", PNPM_DEFAULT))
    # --recursive: without it pnpm reports only the root project, not packages/*.
    command = [*pnpm, "--recursive", "licenses", "list", "--json"]
    return parse_pnpm(_run(command, root), _run([*command, "--prod"], root))


# ---------------------------------------------------------------------------
# Python


def normalize(name: str) -> str:
    """Package name normalized as in PEP 503 (also the form of uv.lock)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _lock_packages(root: Path) -> list[dict[str, object]]:
    path = LOCKFILES["python"]
    try:
        data = tomllib.loads((root / path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise InventoryError(f"cannot read: {exc.__class__.__name__}", path) from exc
    packages = data.get("package", [])
    if not isinstance(packages, list) or not all(
        isinstance(p, dict) and isinstance(p.get("name"), str) for p in packages
    ):
        raise InventoryError("[[package]] entries need a name", path)
    return packages


def _dependency_names(package: dict[str, object]) -> list[str]:
    entries = package.get("dependencies", [])
    if not isinstance(entries, list):
        return []
    return [str(e["name"]) for e in entries if isinstance(e, dict) and "name" in e]


def _is_project(package: dict[str, object]) -> bool:
    source = package.get("source")
    return isinstance(source, dict) and ("virtual" in source or "editable" in source)


def _metadata(root: Path) -> dict[tuple[str, str], tuple[str | None, tuple[str, ...]]]:
    sites = sorted(root.glob(VENV_SITE_GLOB))
    if not sites:
        raise InventoryError(
            f"no Python environment ({VENV_SITE_GLOB}); run make bootstrap first",
            LOCKFILES["python"],
        )
    found: dict[tuple[str, str], tuple[str | None, tuple[str, ...]]] = {}
    for info in sorted(sites[0].glob("*.dist-info")):
        try:
            text = (info / "METADATA").read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        headers = HeaderParser().parsestr(text)
        name, version = headers.get("Name"), headers.get("Version")
        if not name or not version:
            continue
        license = headers.get("License-Expression")
        if not license:
            field = (headers.get("License") or "").strip()
            license = (
                field if field and "\n" not in field and len(field) <= MAX_LICENSE_FIELD else None
            )
        files = license_files_in(info / "licenses") + license_files_in(info)
        found[(normalize(name), version)] = (license.strip() if license else None, files)
    return found


def python_dependencies(root: Path) -> list[Dependency]:
    """Python dependencies of uv.lock with the license of the installed metadata."""
    packages = _lock_packages(root)
    by_name = {normalize(str(p["name"])): p for p in packages}
    runtime: set[str] = set()
    pending = [normalize(name) for p in packages if _is_project(p) for name in _dependency_names(p)]
    while pending:
        name = pending.pop()
        if name in runtime or name not in by_name:
            continue
        runtime.add(name)
        pending.extend(normalize(n) for n in _dependency_names(by_name[name]))
    metadata = _metadata(root)
    deps = []
    for package in packages:
        if _is_project(package):
            continue
        name = normalize(str(package["name"]))
        version = str(package.get("version", ""))
        license, files = metadata.get((name, version), (None, ()))
        deps.append(Dependency("python", name, version, license, name in runtime, files))
    return sorted(deps, key=lambda d: (d.name, d.version))


def collect_dependencies(root: Path) -> list[Dependency]:
    """All npm and Python dependencies of the repository at root."""
    return npm_dependencies(root) + python_dependencies(root)
