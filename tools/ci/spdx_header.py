# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""The SPDX header of handwritten files, from one place (FE-053).

Text and comment form of the header live only here. The package generator
(new_package.py) writes headers with render(); the license gate (plan task
R-E02-T06) checks them with has_header() and reads the headers of adopted files
with header_tags(). Files whose suffix or name is not in
COMMENT_PREFIX (JSON, for instance) have no comment syntax and are not handled.

Standard library only (FE-004).
"""

from __future__ import annotations

from pathlib import Path

HEADER_LINES = (
    "SPDX-License-Identifier: Apache-2.0",
    "SPDX-FileCopyrightText: The Guildwork Authors",
)

# The header must end within the first MAX_LINE lines.
MAX_LINE = 5

BLOCK_COMMENT = "<!-- -->"

# Comment form by file suffix or, for files without suffix, by file name.
COMMENT_PREFIX: dict[str, str] = {
    ".ts": "//",
    ".tsx": "//",
    ".mts": "//",
    ".js": "//",
    ".mjs": "//",
    ".py": "#",
    ".sh": "#",
    ".toml": "#",
    ".yml": "#",
    ".yaml": "#",
    ".md": BLOCK_COMMENT,
    ".sql": "--",
    "Makefile": "#",
    "Dockerfile": "#",
}


def comment_prefix(path: Path) -> str:
    """The comment form for path; ValueError if the file type has none here."""
    prefix = COMMENT_PREFIX.get(path.name) or COMMENT_PREFIX.get(path.suffix)
    if prefix is None:
        raise ValueError(f"no SPDX comment form for {path.name}")
    return prefix


def _header_lines(path: Path) -> list[str]:
    prefix = comment_prefix(path)
    if prefix == BLOCK_COMMENT:
        return ["<!--", *HEADER_LINES, "-->"]
    return [f"{prefix} {line}" for line in HEADER_LINES]


def render(path: Path) -> str:
    """The header for path, ending with a newline."""
    return "\n".join(_header_lines(path)) + "\n"


LICENSE_TAG = "SPDX-License-Identifier"
COPYRIGHT_TAG = "SPDX-FileCopyrightText"
# Adopted files name their source in this line (architecture 12 section 2.4).
ORIGIN_TAG = "Origin"
TAGS = (LICENSE_TAG, COPYRIGHT_TAG, ORIGIN_TAG)


def header_tags(path: Path, text: str) -> list[tuple[int, str, str]]:
    """The tagged lines within MAX_LINE as (line number, tag, value).

    Reads the header of any source, including adopted files with a foreign
    license and an Origin line. The comment syntax of path is stripped; in
    Markdown the tags stand as plain lines inside the block comment.
    """
    prefix = comment_prefix(path)
    tags: list[tuple[int, str, str]] = []
    for number, raw in enumerate(text.splitlines()[:MAX_LINE], start=1):
        line = raw.strip()
        if prefix != BLOCK_COMMENT:
            if not line.startswith(prefix):
                continue
            line = line[len(prefix) :].strip()
        tag, separator, value = line.partition(":")
        if separator and tag in TAGS and value.strip():
            tags.append((number, tag, value.strip()))
    return tags


def has_header(path: Path, text: str) -> bool:
    """Whether text carries the header of path as consecutive lines within MAX_LINE.

    A shebang or other lines may come first, as long as the header ends within
    the first MAX_LINE lines.
    """
    expected = _header_lines(path)
    lines = [line.rstrip() for line in text.splitlines()[:MAX_LINE]]
    size = len(expected)
    return any(lines[i : i + size] == expected for i in range(len(lines) - size + 1))
