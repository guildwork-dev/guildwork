#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Create a workspace package: `pnpm new:package <location>/<name>` (FE-007).

Writes the package layout of the detailed design (package.json with exports,
tsconfig.json, README.md, src/index.ts and src/index.test.ts) with SPDX
headers from spdx_header.py, adds the package to the references of the root
tsconfig.json and, unless an entry of quality/layers.toml already covers the
directory (such as "plugins/*"), adds an entry with
may_import = ["@guildwork/core"].

The location is everything before the last slash and must be a pattern
`<location>/*` of pnpm-workspace.yaml. The package name gets the prefix of
its location: plugins/github becomes @guildwork/plugin-github.

Afterwards run `corepack pnpm install` to link the package into the workspace.

Standard library only (FE-004).

Exit codes:
  0  package created (`new_package.created path=<dir> name=<name>` on stdout)
  2  invalid name, unknown location, existing directory or unusable
     configuration (`new_package.invalid reason=<reason>` on stderr); nothing
     is written
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if not __package__:
    # Run as a script (pnpm new:package): make the tools package importable.
    sys.path.insert(0, str(REPO_ROOT))

from tools.ci import check_layers, spdx_header  # noqa: E402

EXIT_OK = 0
EXIT_INVALID = 2
WORKSPACE_PATH = Path("pnpm-workspace.yaml")
TSCONFIG_PATH = Path("tsconfig.json")

NAME = re.compile(r"^[a-z][a-z0-9-]{1,62}$")
SCOPE = "@guildwork/"
START_IMPORTS = ("@guildwork/core",)

# Prefix of the package name by location (naming used across the detailed design).
NAME_PREFIX: dict[str, str] = {
    "apps": "",
    "packages": "",
    "plugins": "plugin-",
    "drivers": "driver-",
    "services": "service-",
    "eval": "eval-",
    "eval/adapters": "eval-adapter-",
    "eval/scorers": "eval-scorer-",
}


class InvalidError(Exception):
    """The request cannot be carried out; nothing has been written."""


def workspace_locations(text: str) -> set[str]:
    """Locations `<dir>` of the patterns `<dir>/*` under `packages:` in pnpm-workspace.yaml."""
    locations: set[str] = set()
    in_packages = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line:
            continue
        if not line.startswith((" ", "-")):
            in_packages = line == "packages:"
            continue
        item = line.strip()
        if in_packages and item.startswith("- "):
            pattern = item[2:].strip().strip("'\"")
            if pattern.endswith("/*"):
                locations.add(pattern[:-2])
    return locations


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise InvalidError(f"cannot read {path.name}: {exc}") from exc


def parse_target(root: Path, target: str) -> tuple[str, str, str]:
    """Location, directory name and package name of `<location>/<name>`."""
    location, _, name = target.rpartition("/")
    if not location:
        raise InvalidError(f"target {target!r} must be <location>/<name>")
    if not NAME.match(name):
        raise InvalidError(f"name {name!r} must match {NAME.pattern}")
    known = workspace_locations(_read(root / WORKSPACE_PATH))
    if location not in NAME_PREFIX or location not in known:
        usable = ", ".join(sorted(set(NAME_PREFIX) & known))
        raise InvalidError(f"unknown location {location!r}; use one of {usable}")
    return location, name, SCOPE + NAME_PREFIX[location] + name


def render_files(directory: str, package_name: str) -> dict[str, str]:
    """Relative path in the package -> content."""
    depth = directory.count("/") + 1
    base = "../" * depth + "tsconfig.base.json"
    manifest = {
        "name": package_name,
        "version": "0.0.0",
        "private": True,
        "type": "module",
        "license": "Apache-2.0",
        "exports": {
            ".": {
                "@guildwork/source": "./src/index.ts",
                "types": "./dist/index.d.ts",
                "import": "./dist/index.js",
            }
        },
        "files": ["dist"],
        "scripts": {"build": "tsc -b"},
    }
    tsconfig = (
        "{\n"
        f'  "extends": "{base}",\n'
        '  "compilerOptions": {\n'
        '    "rootDir": "src",\n'
        '    "outDir": "dist"\n'
        "  },\n"
        '  "include": ["src"]\n'
        "}\n"
    )
    short = directory.rsplit("/", 1)[1]
    readme = (
        f"# {package_name}\n\n"
        "Describe the purpose of the package, its public API (the named exports of"
        " `src/index.ts`) and the section of the detailed design it implements.\n"
    )
    index = (
        "/** Name of the package. Placeholder until the package gets its modules. */\n"
        f'export const PACKAGE_NAME = "{package_name}";\n'
    )
    index_test = (
        'import { describe, expect, it } from "vitest";\n'
        'import { PACKAGE_NAME } from "./index.js";\n'
        "\n"
        f'describe("{short}/index", () => {{\n'
        '  it("names the package", () => {\n'
        f'    expect(PACKAGE_NAME).toBe("{package_name}");\n'
        "  });\n"
        "});\n"
    )

    def with_header(path: str, body: str) -> str:
        return spdx_header.render(Path(path)) + "\n" + body

    return {
        "package.json": json.dumps(manifest, indent=2) + "\n",
        "tsconfig.json": tsconfig,
        "README.md": with_header("README.md", readme),
        "src/index.ts": with_header("index.ts", index),
        "src/index.test.ts": with_header("index.test.ts", index_test),
    }


def layers_with_entry(text: str, directory: str) -> str | None:
    """New text of layers.toml with an entry for directory, or None if one covers it."""
    try:
        layers = check_layers.parse_layers(text)
        check_layers.match_entry(layers, directory)
        return None
    except check_layers.UnknownPackageError:
        pass
    except check_layers.ConfigError as exc:
        raise InvalidError(f"quality/layers.toml: {exc}") from exc
    imports = ", ".join(f'"{name}"' for name in START_IMPORTS)
    block = f'[[package]]\npath = "{directory}"\nmay_import = [{imports}]\n\n'
    marker = re.search(r"^\[test_only\]", text, re.MULTILINE)
    if marker:
        new = text[: marker.start()] + block + text[marker.start() :]
    else:
        new = text.rstrip("\n") + "\n\n" + block.rstrip("\n") + "\n"
    check_layers.match_entry(check_layers.parse_layers(new), directory)
    return new


def tsconfig_with_reference(text: str, directory: str) -> str:
    """New text of the root tsconfig.json with a reference to directory, appended last."""
    match = re.search(r'"references"\s*:\s*\[(?P<body>.*?)\]', text, re.DOTALL)
    if not match:
        raise InvalidError("tsconfig.json has no references array")
    body = match.group("body")
    reference = f'{{ "path": "./{directory}" }}'
    if body.strip():
        content = body.rstrip()
        new_body = f"{content},\n    {reference}{body[len(content) :]}"
    else:
        new_body = f"\n    {reference}\n  "
    new = text[: match.start("body")] + new_body + text[match.end("body") :]
    try:
        references = json.loads(new)["references"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise InvalidError(f"cannot add the reference to tsconfig.json: {exc}") from exc
    if {"path": f"./{directory}"} not in references:
        raise InvalidError("cannot add the reference to tsconfig.json")
    return new


def plan(root: Path, target: str) -> tuple[str, str, dict[Path, str]]:
    """Directory, package name and every file to write; raises InvalidError."""
    location, name, package_name = parse_target(root, target)
    directory = f"{location}/{name}"
    if (root / directory).exists():
        raise InvalidError(f"{directory} exists")
    writes = {
        root / directory / path: text
        for path, text in render_files(directory, package_name).items()
    }
    layers_path = root / check_layers.LAYERS_PATH
    layers = layers_with_entry(_read(layers_path), directory)
    if layers is not None:
        writes[layers_path] = layers
    tsconfig_path = root / TSCONFIG_PATH
    writes[tsconfig_path] = tsconfig_with_reference(_read(tsconfig_path), directory)
    return directory, package_name, writes


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a workspace package.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    parser.add_argument("target", help="<location>/<name>, for example plugins/github")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root: Path = args.root
    try:
        directory, package_name, writes = plan(root, args.target)
    except InvalidError as exc:
        print(f"new_package.invalid reason={exc}", file=sys.stderr)
        return EXIT_INVALID
    for path, text in writes.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(f"new_package.created path={directory} name={package_name}")
    print("new_package.next run 'corepack pnpm install' to link the package into the workspace")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
