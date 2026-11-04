#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Check the GitHub Actions workflows against the workflow policy (FE-024, FE-025).

The values live only in `quality/ci/policy.toml`. Every `*.yml` and `*.yaml`
file in the workflow directory (default `.github/workflows`) is checked; a
missing directory has no findings. Policy lookups use the file name.

  runner-label              `runs-on` is a literal from allowed_runners: no
                            expression, no list, no self-hosted, no *-latest
  action-pin                `uses:` with a full 40 character commit SHA and a
                            comment `# v<version>`; local `./` actions are
                            allowed, `docker://` only with `@sha256:`
  job-timeout               every job has `timeout-minutes` from 1 to
                            max_timeout_minutes (jobs that call a reusable
                            workflow cannot set it and are skipped)
  top-permissions           top level `permissions` is exactly `contents: read`
  job-permissions           job permissions only `contents: read`, `none` or
                            what job_permissions.<workflow>.<job> grants
  no-actions-write          no `actions: write` and no `write-all` anywhere
  no-dangerous-triggers     no `pull_request_target`, no `workflow_run`
  push-main-only            `on.push` only in push_workflows and only with
                            `branches: [main]`
  no-expr-in-run            no `${{` in `run:`; values go through `env:`
  checkout-no-persist       `actions/checkout` with `persist-credentials: false`
  secrets-need-environment  `secrets.*` other than GITHUB_TOKEN, and
                            `secrets: inherit`, only in jobs with
                            `environment:`; a secret at workflow level
                            needs an environment in every job
  public-only-guard         jobs of public_only_workflows have an `if:` with
                            `github.event.repository.visibility == 'public'`,
                            with a `schedule` trigger also
                            `vars.GUILDWORK_VISIBILITY == 'public'`
  pr-concurrency            workflows with `pull_request` have a top level
                            `concurrency` with a group and `cancel-in-progress`
                            true or `${{ github.event_name == 'pull_request' }}`
  max-jobs                  workflows with `pull_request` have at most
                            max_jobs_per_run jobs; a literal matrix counts
                            its combinations (upper bound: product of the
                            axes plus the include entries; exclude is not
                            subtracted), a matrix from an expression cannot
                            be counted and is a finding

With `--strict` (make workflows-dry-run, R4) also:

  known-workflow            every workflow file is in known_workflows
  make-target-exists        every `make <target>` in a `run:` step names a
                            make target of quality/gates.toml (a gate or a
                            [[target]] such as the group targets)
  job-env-known             every variable a `run:` step sets as
                            `NAME=value` on the make command line is in
                            make_variables (the make variables of section 7
                            of the detailed design). Step `env:` values and
                            exported variables are not counted: they reach
                            the step's commands (such as commit_range.py)
                            through the environment, not as make variables.

A make call is the word `make` at the start of a line, after `;`, `&`, `|`,
`(` or `)`, or after `then`, `else` or `do`; options and variables are not
targets, and text such as `echo make x` or a comment does not count.

Workflows are read with a small YAML reader for the subset that workflows
use: block and flow collections, plain and quoted scalars, literal and folded
block scalars, comments. Anchors, aliases, tags, merge keys, several
documents and multi-line plain scalars are outside the subset and stop the
check (exit 2); actionlint and zizmor in `make workflows` check full YAML.

Standard library only (FE-004).

Exit codes:
  0  no finding
  1  findings, printed as `path:line:col rule-id message` on stdout
  2  configuration error on stderr: `workflows.config_invalid path=<path>
     reason=<reason>`, or `workflows.unparsable path=<path>:<line> reason=<reason>`
     for a workflow outside the YAML subset
With `--json <file>` the findings are also written as JSON (also when empty).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_CONFIG = 2

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = Path("quality/ci/policy.toml")
GATES_PATH = Path("quality/gates.toml")
WORKFLOW_DIR = Path(".github/workflows")
WORKFLOW_SUFFIXES = (".yml", ".yaml")

# Repository variable that marks the repository as public for scheduled runs,
# which carry no repository object (section 2.11).
VISIBILITY_VARIABLE = "GUILDWORK_VISIBILITY"
REPO_PUBLIC = "github.event.repository.visibility == 'public'"
VARS_PUBLIC = f"vars.{VISIBILITY_VARIABLE} == 'public'"
PR_CANCEL_EXPR = "github.event_name == 'pull_request'"
PUSH_BRANCH = "main"
DANGEROUS_TRIGGERS = ("pull_request_target", "workflow_run")
PERMISSION_LEVELS = ("read", "write", "none")
TOP_PERMISSIONS = {"contents": "read"}

POLICY_LISTS = (
    "allowed_runners",
    "public_only_workflows",
    "push_workflows",
    "known_workflows",
)
POLICY_INTS = ("max_timeout_minutes", "max_jobs_per_run")
# Optional list, used by --strict only.
MAKE_VARIABLES_KEY = "make_variables"
POLICY_KEYS = frozenset((*POLICY_LISTS, *POLICY_INTS, "job_permissions", MAKE_VARIABLES_KEY))

SHA_USES = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[^@\s]+)?@[0-9a-f]{40}")
DOCKER_USES = re.compile(r"docker://[^@\s]+@sha256:[0-9a-f]{64}")
VERSION_COMMENT = re.compile(r"v\d[\w.+-]*(?:\s.*)?")
EXPRESSION = re.compile(r"\$\{\{(.*?)\}\}", re.DOTALL)
# Expression contexts and property names are case-insensitive.
MAKE_CALL = re.compile(
    r"(?:^|[;&|()]|\b(?:then|else|do)\b)[ \t]*make[ \t]+([^;&|#)\n]*)", re.MULTILINE
)
EXPORT = re.compile(
    r"(?:^|[;&|()]|\b(?:then|else|do)\b)[ \t]*export[ \t]+([^;&|#)\n]*)", re.MULTILINE
)
VARIABLE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
SECRET_REF = re.compile(
    r"\bsecrets\b(?!\s*(?:\.\s*GITHUB_TOKEN\b|\[\s*'GITHUB_TOKEN'\s*\]))",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# YAML subset


class YamlError(Exception):
    """A workflow is outside the supported YAML subset."""

    def __init__(self, reason: str, line: int) -> None:
        super().__init__(reason)
        self.line = line


@dataclass
class Node:
    line: int
    col: int


@dataclass
class Scalar(Node):
    value: str
    quoted: bool = False
    comment: str = ""
    # For block scalars: (line, col, text) of each content line.
    parts: tuple[tuple[int, int, str], ...] = ()


@dataclass
class Mapping(Node):
    items: list[tuple[Scalar, Node]] = field(default_factory=list)

    def get(self, key: str) -> Node | None:
        for k, v in self.items:
            if k.value == key:
                return v
        return None

    def key(self, key: str) -> Scalar | None:
        for k, _ in self.items:
            if k.value == key:
                return k
        return None


@dataclass
class Seq(Node):
    items: list[Node] = field(default_factory=list)


@dataclass
class _Line:
    number: int  # 1-based
    indent: int
    text: str  # content after the indentation, comment included
    raw: str


_PLAIN_KEY = re.compile(r"([^\s#'\"\[\]{},&*!|>%@`-]|-(?=\S))[^#]*?(?=:(?:\s|$))")
_QUOTED_KEY = re.compile(r"(\"(?:[^\"\\]|\\.)*\"|'(?:[^']|'')*')\s*(?=:(?:\s|$))")


def _split_comment(text: str) -> tuple[str, str]:
    """Content and comment of a line; `#` starts a comment after whitespace."""
    quote = ""
    i = 0
    while i < len(text):
        c = text[i]
        if quote:
            if quote == '"' and c == "\\":
                i += 2
                continue
            if c == quote:
                if quote == "'" and text.startswith("''", i):
                    i += 2
                    continue
                quote = ""
        elif c in "\"'" and (i == 0 or text[i - 1] in " \t[{,:"):
            quote = c
        elif c == "#" and (i == 0 or text[i - 1] in " \t"):
            return text[:i].rstrip(), text[i + 1 :].strip()
        i += 1
    return text.rstrip(), ""


_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", '"': '"', "/": "/", " ": " "}


def _unquote(text: str, line: int) -> str:
    if text[0] == "'":
        return text[1:-1].replace("''", "'")
    out: list[str] = []
    i = 1
    while i < len(text) - 1:
        c = text[i]
        if c == "\\":
            nxt = text[i + 1]
            if nxt in _ESCAPES:
                out.append(_ESCAPES[nxt])
                i += 2
            elif nxt in "xuU":
                size = {"x": 2, "u": 4, "U": 8}[nxt]
                try:
                    out.append(chr(int(text[i + 2 : i + 2 + size], 16)))
                except ValueError as exc:
                    raise YamlError("invalid escape in double quoted string", line) from exc
                i += 2 + size
            else:
                raise YamlError(f"unsupported escape \\{nxt}", line)
        else:
            out.append(c)
            i += 1
    return "".join(out)


class _Reader:
    def __init__(self, text: str) -> None:
        self.lines: list[_Line] = []
        for number, raw in enumerate(text.splitlines(), start=1):
            stripped = raw.lstrip(" ")
            self.lines.append(_Line(number, len(raw) - len(stripped), stripped, raw))
        self.i = 0

    # -- helpers

    def _significant(self) -> _Line | None:
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if line.text.startswith("\t"):
                raise YamlError("tab in indentation", line.number)
            if line.text.strip() and not line.text.startswith("#"):
                return line
            self.i += 1
        return None

    def parse_document(self) -> Node:
        first = self._significant()
        if first is None:
            return Mapping(1, 1)
        if first.text.startswith("%"):
            raise YamlError("directives are not supported", first.number)
        if first.text.rstrip() == "---" and first.indent == 0:
            self.i += 1
            first = self._significant()
            if first is None:
                return Mapping(1, 1)
        node = self._block(first.indent)
        rest = self._significant()
        if rest is not None:
            if rest.text.startswith(("---", "...")) and rest.indent == 0:
                raise YamlError("several documents are not supported", rest.number)
            raise YamlError("unexpected indentation", rest.number)
        return node

    def _next(self) -> _Line:
        line = self._significant()
        if line is None:
            raise YamlError("unexpected end of file", len(self.lines))
        return line

    def _block(self, indent: int) -> Node:
        line = self._next()
        if line.indent != indent:
            raise YamlError("unexpected indentation", line.number)
        content, _ = _split_comment(line.text)
        if content == "-" or content.startswith("- "):
            return self._seq(indent)
        if self._key_match(content) is not None:
            return self._map(indent)
        self.i += 1
        node = self._inline(content, line, line.indent + 1)
        nxt = self._significant()
        if nxt is not None and nxt.indent > indent:
            raise YamlError("multi-line plain scalars are not supported", nxt.number)
        return node

    @staticmethod
    def _key_match(content: str) -> re.Match[str] | None:
        return _QUOTED_KEY.match(content) or _PLAIN_KEY.match(content)

    def _map(self, indent: int) -> Mapping:
        first = self._next()
        mapping = Mapping(first.number, indent + 1)
        seen: set[str] = set()
        while True:
            line = self._significant()
            if line is None or line.indent < indent:
                return mapping
            if line.indent > indent:
                raise YamlError("unexpected indentation", line.number)
            content, comment = _split_comment(line.text)
            match = self._key_match(content)
            if match is None:
                if content == "-" or content.startswith("- "):
                    return mapping  # sequence of the parent at the same indentation
                raise YamlError("expected a mapping key", line.number)
            raw_key = match.group(0)
            key_text = raw_key.strip()
            if key_text[0] in "\"'":
                key = Scalar(line.number, indent + 1, _unquote(key_text, line.number), True)
            else:
                key = Scalar(line.number, indent + 1, key_text)
            if key.value == "<<":
                raise YamlError("merge keys are not supported", line.number)
            if key.value in seen:
                raise YamlError(f"duplicate key {key.value!r}", line.number)
            seen.add(key.value)
            after = match.end() + 1  # skip the colon
            rest = content[after:]
            value_col = indent + after + (len(rest) - len(rest.lstrip())) + 1
            rest = rest.strip()
            self.i += 1
            mapping.items.append((key, self._value(rest, comment, line, indent, value_col)))

    def _value(self, rest: str, comment: str, line: _Line, indent: int, col: int) -> Node:
        if rest and rest[0] in "|>":
            return self._block_scalar(rest, line, indent)
        if rest:
            node = self._inline(rest, line, col, comment)
            nxt = self._significant()
            if nxt is not None and nxt.indent > indent and not isinstance(node, (Mapping, Seq)):
                raise YamlError("multi-line plain scalars are not supported", nxt.number)
            return node
        nxt = self._significant()
        if nxt is not None and nxt.indent > indent:
            return self._block(nxt.indent)
        if nxt is not None and nxt.indent == indent:
            content, _ = _split_comment(nxt.text)
            if content == "-" or content.startswith("- "):
                return self._seq(indent)
        return Scalar(line.number, col, "")

    def _seq(self, indent: int) -> Seq:
        first = self._next()
        seq = Seq(first.number, indent + 1)
        while True:
            line = self._significant()
            if line is None or line.indent != indent:
                if line is not None and line.indent > indent:
                    raise YamlError("unexpected indentation", line.number)
                return seq
            content, _ = _split_comment(line.text)
            if not (content == "-" or content.startswith("- ")):
                return seq
            rest = line.text[1:]
            if not rest.strip() or rest.strip().startswith("#"):
                self.i += 1
                nxt = self._significant()
                if nxt is not None and nxt.indent > indent:
                    seq.items.append(self._block(nxt.indent))
                else:
                    seq.items.append(Scalar(line.number, indent + 2, ""))
                continue
            item, _ = _split_comment(rest.strip())
            if item[0] in "|>":
                self.i += 1
                seq.items.append(self._block_scalar(item, line, indent))
                continue
            # Re-read the rest of the line as a block at its own indentation.
            spaces = len(rest) - len(rest.lstrip(" "))
            line.indent = indent + 1 + spaces
            line.text = rest.lstrip(" ")
            seq.items.append(self._block(line.indent))

    def _block_scalar(self, header: str, line: _Line, indent: int) -> Scalar:
        match = re.fullmatch(r"([|>])([+-]?)([1-9]?)([+-]?)", header)
        if match is None:
            raise YamlError(f"invalid block scalar header {header!r}", line.number)
        style, chomp = match.group(1), match.group(2) or match.group(4)
        explicit = int(match.group(3)) if match.group(3) else 0
        content_indent = indent + explicit if explicit else 0
        parts: list[tuple[int, int, str]] = []
        while self.i < len(self.lines):
            cur = self.lines[self.i]
            if cur.raw.strip():
                if not content_indent:
                    if cur.indent <= indent:
                        break
                    content_indent = cur.indent
                if len(cur.raw) - len(cur.raw.lstrip(" ")) < content_indent:
                    break
                parts.append((cur.number, content_indent + 1, cur.raw[content_indent:]))
            else:
                parts.append((cur.number, 1, ""))
            self.i += 1
        trailing = 0
        while parts and not parts[-1][2]:
            parts.pop()
            trailing += 1
        texts = [p[2] for p in parts]
        value = "\n".join(texts) if style == "|" else _fold(texts)
        if chomp != "-" and value:
            value += "\n" * (1 + (trailing if chomp == "+" else 0))
        first = parts[0] if parts else (line.number, indent + 1, "")
        return Scalar(first[0], first[1], value, parts=tuple(parts))

    def _inline(self, text: str, line: _Line, col: int, comment: str = "") -> Node:
        if text[0] in "&*!":
            raise YamlError("anchors, aliases and tags are not supported", line.number)
        if text[0] in "[{":
            # The caller has consumed `line`; a flow collection may go on below.
            full = text
            while not _balanced(full):
                if self.i >= len(self.lines):
                    raise YamlError("unterminated flow collection", line.number)
                more, _ = _split_comment(self.lines[self.i].text)
                full += " " + more
                self.i += 1
            node, end = _Flow(full, line.number, col).parse(0)
            if full[end:].strip():
                raise YamlError("text after a flow collection", line.number)
            return node
        if text[0] in "\"'":
            if len(text) < 2 or text[-1] != text[0]:
                raise YamlError("unterminated or trailing text after quoted scalar", line.number)
            return Scalar(line.number, col, _unquote(text, line.number), True, comment)
        if text.startswith(("---", "...")) and col == 1:
            raise YamlError("several documents are not supported", line.number)
        return Scalar(line.number, col, text, False, comment)


def _fold(texts: list[str]) -> str:
    """Line folding of a `>` block scalar: breaks between normal lines become spaces."""
    if not texts:
        return ""
    out = texts[0]
    prev = texts[0]
    k = 1
    while k < len(texts):
        empty = 0
        while texts[k] == "":
            empty += 1
            k += 1
        cur = texts[k]
        normal = bool(prev) and not prev[0].isspace() and not cur[0].isspace()
        if empty:
            out += "\n" * (empty if normal else empty + 1) + cur
        else:
            out += (" " if normal else "\n") + cur
        prev = cur
        k += 1
    return out


def _balanced(text: str) -> bool:
    depth = 0
    quote = ""
    for c in text:
        if quote:
            if c == quote:
                quote = ""
        elif c in "\"'":
            quote = c
        elif c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
    return depth <= 0


class _Flow:
    """Reader of flow collections such as `[a, 'b', {c: d}]`."""

    def __init__(self, text: str, line: int, col: int) -> None:
        self.text = text
        self.line = line
        self.col = col

    def _skip(self, i: int) -> int:
        while i < len(self.text) and self.text[i] in " \t":
            i += 1
        return i

    def _after_item(self, i: int, close: str) -> int:
        """Position after the separator; anything but `,` or the closing bracket is an error."""
        i = self._skip(i)
        if i < len(self.text) and self.text[i] == ",":
            return self._skip(i + 1)
        if i < len(self.text) and self.text[i] != close:
            raise YamlError(f"expected ',' or {close!r} in flow collection", self.line)
        return i

    def parse(self, i: int) -> tuple[Node, int]:
        i = self._skip(i)
        c = self.text[i] if i < len(self.text) else ""
        if c == "[":
            seq = Seq(self.line, self.col + i)
            i = self._skip(i + 1)
            while i < len(self.text) and self.text[i] != "]":
                item, i = self.parse(i)
                seq.items.append(item)
                i = self._after_item(i, "]")
            if i >= len(self.text):
                raise YamlError("unterminated flow sequence", self.line)
            return seq, i + 1
        if c == "{":
            mapping = Mapping(self.line, self.col + i)
            i = self._skip(i + 1)
            seen: set[str] = set()
            while i < len(self.text) and self.text[i] != "}":
                key, i = self._scalar(i, key=True)
                i = self._skip(i)
                if i < len(self.text) and self.text[i] == ":":
                    value, i = self.parse(i + 1)
                else:
                    value = Scalar(self.line, self.col + i, "")
                if key.value in seen:
                    raise YamlError(f"duplicate key {key.value!r}", self.line)
                seen.add(key.value)
                mapping.items.append((key, value))
                i = self._after_item(i, "}")
            if i >= len(self.text):
                raise YamlError("unterminated flow mapping", self.line)
            return mapping, i + 1
        return self._scalar(i, key=False)

    def _scalar(self, i: int, key: bool) -> tuple[Scalar, int]:
        start = i
        if i < len(self.text) and self.text[i] in "&*!":
            raise YamlError("anchors, aliases and tags are not supported", self.line)
        if i < len(self.text) and self.text[i] in "\"'":
            quote = self.text[i]
            j = i + 1
            while j < len(self.text):
                if quote == '"' and self.text[j] == "\\":
                    j += 2
                    continue
                if self.text[j] == quote:
                    if quote == "'" and self.text.startswith("''", j):
                        j += 2
                        continue
                    break
                j += 1
            if j >= len(self.text):
                raise YamlError("unterminated quoted scalar", self.line)
            raw = self.text[i : j + 1]
            return Scalar(self.line, self.col + start, _unquote(raw, self.line), True), j + 1
        stops = ",]}" + (":" if key else "")
        j = i
        while j < len(self.text) and self.text[j] not in stops:
            if self.text[j] == ":" and (j + 1 >= len(self.text) or self.text[j + 1] in " ,]}"):
                break
            j += 1
        return Scalar(self.line, self.col + start, self.text[i:j].strip()), j


def parse_yaml(text: str) -> Node:
    """Parse a workflow; raise YamlError outside the supported subset."""
    return _Reader(text).parse_document()


def to_plain(node: Node) -> object:
    """The parsed node as plain dicts, lists and strings."""
    if isinstance(node, Mapping):
        return {k.value: to_plain(v) for k, v in node.items}
    if isinstance(node, Seq):
        return [to_plain(v) for v in node.items]
    return node.value if isinstance(node, Scalar) else None


# ---------------------------------------------------------------------------
# Policy


class ConfigError(Exception):
    """policy.toml cannot be used."""

    def __init__(self, reason: str, path: str) -> None:
        super().__init__(reason)
        self.path = path


@dataclass(frozen=True)
class Policy:
    allowed_runners: frozenset[str]
    max_timeout_minutes: int
    max_jobs_per_run: int
    public_only_workflows: frozenset[str]
    push_workflows: frozenset[str]
    known_workflows: frozenset[str]
    job_permissions: dict[str, dict[str, dict[str, str]]]
    make_variables: frozenset[str] = frozenset()


def load_policy(path: Path, shown: str) -> Policy:
    """Read and validate policy.toml; raise ConfigError with the reason."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"unreadable: {exc}", shown) from exc
    unknown = sorted(set(data) - POLICY_KEYS)
    if unknown:
        raise ConfigError(f"unknown key {', '.join(unknown)}", shown)
    lists: dict[str, frozenset[str]] = {}
    for key in POLICY_LISTS:
        value = data.get(key)
        if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
            raise ConfigError(f"{key} must be an array of non-empty strings", shown)
        lists[key] = frozenset(value)
    make_variables = data.get(MAKE_VARIABLES_KEY, [])
    if not isinstance(make_variables, list) or not all(
        isinstance(v, str) and VARIABLE.fullmatch(v) for v in make_variables
    ):
        raise ConfigError(f"{MAKE_VARIABLES_KEY} must be an array of variable names", shown)
    if not lists["allowed_runners"]:
        raise ConfigError("allowed_runners must not be empty", shown)
    ints: dict[str, int] = {}
    for key in POLICY_INTS:
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ConfigError(f"{key} must be a positive integer", shown)
        ints[key] = value
    raw = data.get("job_permissions", {})
    if not isinstance(raw, dict):
        raise ConfigError("job_permissions must be a table", shown)
    perms: dict[str, dict[str, dict[str, str]]] = {}
    for workflow, jobs in raw.items():
        if not isinstance(jobs, dict):
            raise ConfigError(f"job_permissions.{workflow} must be a table", shown)
        perms[workflow] = {}
        for job, scopes in jobs.items():
            where = f"job_permissions.{workflow}.{job}"
            if not isinstance(scopes, dict) or not all(
                isinstance(v, str) and v in PERMISSION_LEVELS for v in scopes.values()
            ):
                raise ConfigError(f"{where} must map scopes to read, write or none", shown)
            if scopes.get("actions") == "write":
                raise ConfigError(f"{where}: actions write is never allowed", shown)
            perms[workflow][job] = dict(scopes)
    return Policy(
        allowed_runners=lists["allowed_runners"],
        max_timeout_minutes=ints["max_timeout_minutes"],
        max_jobs_per_run=ints["max_jobs_per_run"],
        public_only_workflows=lists["public_only_workflows"],
        push_workflows=lists["push_workflows"],
        known_workflows=lists["known_workflows"],
        job_permissions=perms,
        make_variables=frozenset(make_variables),
    )


def load_make_targets(path: Path, shown: str) -> frozenset[str]:
    """Every make target that quality/gates.toml names (gates and targets)."""
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"unreadable: {exc}", shown) from exc
    names: set[str] = set()
    for table, key in (("gate", "make"), ("target", "name")):
        entries = data.get(table, [])
        if not isinstance(entries, list):
            raise ConfigError(f"{table} must be an array of tables", shown)
        for entry in entries:
            value = entry.get(key) if isinstance(entry, dict) else None
            if not isinstance(value, str) or not value:
                raise ConfigError(f"every {table} needs a string {key}", shown)
            names.add(value)
    return frozenset(names)


@dataclass(frozen=True)
class MakeCall:
    """A make call in a run script: its targets and the variables it sets."""

    targets: tuple[str, ...]
    variables: tuple[str, ...]


def _words(text: str) -> list[str]:
    # Quotes stay attached to their word: COMMIT_RANGE="$range" is one word.
    return text.split()


def make_calls(script: str) -> list[MakeCall]:
    """The make calls of one script line or script."""
    calls: list[MakeCall] = []
    for match in MAKE_CALL.finditer(script):
        targets: list[str] = []
        variables: list[str] = []
        for word in _words(match.group(1)):
            name, sep, _ = word.partition("=")
            if sep and VARIABLE.fullmatch(name):
                variables.append(name)
            elif not word.startswith(("-", "$", '"', "'")) and "=" not in word:
                targets.append(word)
        calls.append(MakeCall(tuple(targets), tuple(variables)))
    return calls


def exported(script: str) -> list[str]:
    """Variables a script exports with `export NAME` or `export NAME=value`."""
    names: list[str] = []
    for match in EXPORT.finditer(script):
        for word in _words(match.group(1)):
            name = word.partition("=")[0]
            if VARIABLE.fullmatch(name):
                names.append(name)
    return names


# ---------------------------------------------------------------------------
# Checks


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    col: int
    rule: str
    message: str

    def text(self) -> str:
        return f"{self.path}:{self.line}:{self.col} {self.rule} {self.message}"


def _str(node: Node | None) -> str | None:
    return node.value if isinstance(node, Scalar) else None


def _normalize(expression: str) -> str:
    """An expression without `${{ }}` and without whitespace."""
    text = expression.strip()
    if text.startswith("${{") and text.endswith("}}"):
        text = text[3:-2]
    return re.sub(r"\s+", "", text)


def _scalars(node: Node) -> Iterator[Scalar]:
    if isinstance(node, Scalar):
        yield node
    elif isinstance(node, Mapping):
        for _, value in node.items:
            yield from _scalars(value)
    elif isinstance(node, Seq):
        for item in node.items:
            yield from _scalars(item)


def _triggers(node: Node | None) -> dict[str, Node]:
    """Event name -> node that names it."""
    if isinstance(node, Scalar) and node.value:
        return {node.value: node}
    if isinstance(node, Seq):
        return {s.value: s for s in node.items if isinstance(s, Scalar)}
    if isinstance(node, Mapping):
        return {k.value: k for k, _ in node.items}
    return {}


class WorkflowChecker:
    def __init__(
        self,
        policy: Policy,
        path: str,
        name: str,
        doc: Mapping,
        make_targets: frozenset[str] | None = None,
    ) -> None:
        self.policy = policy
        # Set only with --strict.
        self.make_targets = make_targets
        self.path = path
        self.name = name
        self.doc = doc
        self.findings: list[Finding] = []
        on_node = doc.get("on")
        self.on = on_node
        self.triggers = _triggers(on_node)
        jobs = doc.get("jobs")
        self.jobs: list[tuple[Scalar, Mapping]] = []
        if isinstance(jobs, Mapping):
            self.jobs = [(k, v) for k, v in jobs.items if isinstance(v, Mapping)]

    def report(self, node: Node, rule: str, message: str) -> None:
        self.findings.append(Finding(self.path, node.line, node.col, rule, message))

    def run(self) -> list[Finding]:
        self.check_triggers()
        self.check_top_permissions()
        self.check_concurrency()
        self.check_max_jobs()
        self.check_workflow_secrets()
        for key, job in self.jobs:
            self.check_job(key, job)
        if self.make_targets is not None:
            self.check_strict()
        return self.findings

    # -- --strict

    def check_strict(self) -> None:
        if self.name not in self.policy.known_workflows:
            self.report(Node(1, 1), "known-workflow", f"{self.name} is not in known_workflows")
        for _, job in self.jobs:
            steps = job.get("steps")
            for step in steps.items if isinstance(steps, Seq) else []:
                run = step.get("run") if isinstance(step, Mapping) else None
                if isinstance(run, Scalar):
                    self.check_make_calls(run)

    def check_make_calls(self, run: Scalar) -> None:
        lines = list(run.parts) or [(run.line, run.col, run.value)]
        if not make_calls(run.value):
            return
        known = self.make_targets or frozenset()
        allowed = self.policy.make_variables
        for line, col, text in lines:
            where = Node(line, col)
            for call in make_calls(text):
                for target in call.targets:
                    if target not in known:
                        self.report(where, "make-target-exists", f"make {target}: no such target")
                for name in call.variables:
                    if name not in allowed:
                        self.report(where, "job-env-known", f"{name} is not in make_variables")

    # -- workflow level

    def check_triggers(self) -> None:
        for event in DANGEROUS_TRIGGERS:
            if event in self.triggers:
                self.report(self.triggers[event], "no-dangerous-triggers", f"trigger {event}")
        if "push" not in self.triggers:
            return
        node = self.triggers["push"]
        if self.name not in self.policy.push_workflows:
            self.report(node, "push-main-only", f"push trigger outside push_workflows: {self.name}")
            return
        config = self.on.get("push") if isinstance(self.on, Mapping) else None
        ok = False
        if isinstance(config, Mapping) and [k.value for k, _ in config.items] == ["branches"]:
            branches = config.get("branches")
            if isinstance(branches, Seq):
                ok = [_str(b) for b in branches.items] == [PUSH_BRANCH]
            else:
                ok = _str(branches) == PUSH_BRANCH
        if not ok:
            self.report(node, "push-main-only", f"push must be exactly branches: [{PUSH_BRANCH}]")

    def check_top_permissions(self) -> None:
        node = self.doc.get("permissions")
        key = self.doc.key("permissions")
        if node is None or key is None:
            self.report(self.doc, "top-permissions", "missing top level permissions")
            return
        self.check_actions_write(node)
        pairs = {k.value: _str(v) for k, v in node.items} if isinstance(node, Mapping) else {}
        if pairs != TOP_PERMISSIONS or len(pairs) != len(getattr(node, "items", ())):
            self.report(key, "top-permissions", "top level permissions must be contents: read")

    def check_actions_write(self, node: Node) -> None:
        if _str(node) == "write-all":
            self.report(node, "no-actions-write", "write-all grants actions: write")
        elif isinstance(node, Mapping):
            value = node.get("actions")
            if _str(value) == "write" and value is not None:
                self.report(value, "no-actions-write", "actions: write")

    def check_concurrency(self) -> None:
        if "pull_request" not in self.triggers:
            return
        node = self.doc.get("concurrency")
        if not isinstance(node, Mapping):
            where = node if node is not None else self.triggers["pull_request"]
            self.report(where, "pr-concurrency", "pull request workflow needs concurrency")
            return
        cancel = node.get("cancel-in-progress")
        value = _str(cancel)
        if value in ("True", "TRUE"):  # the YAML 1.2 spellings of true
            value = "true"
        if not _str(node.get("group")):
            self.report(node, "pr-concurrency", "concurrency needs a group")
        if value != "true" and (value is None or _normalize(value) != _normalize(PR_CANCEL_EXPR)):
            self.report(
                cancel or node,
                "pr-concurrency",
                "concurrency needs cancel-in-progress: true for pull requests",
            )

    def check_max_jobs(self) -> None:
        if "pull_request" not in self.triggers:
            return
        total = 0
        for key, job in self.jobs:
            size = self.matrix_size(job)
            if size is None:
                self.report(key, "max-jobs", "matrix size cannot be counted (not a literal)")
                return
            total += size
        if total > self.policy.max_jobs_per_run:
            jobs = self.doc.key("jobs") or self.doc
            self.report(
                jobs,
                "max-jobs",
                f"{total} jobs per pull request run, more than "
                f"max_jobs_per_run {self.policy.max_jobs_per_run}",
            )

    @staticmethod
    def matrix_size(job: Mapping) -> int | None:
        strategy = job.get("strategy")
        if strategy is None:
            return 1
        if not isinstance(strategy, Mapping):
            return None
        matrix = strategy.get("matrix")
        if matrix is None:
            return 1
        if not isinstance(matrix, Mapping):
            return None
        size = 1
        axes = 0
        extra = 0
        for key, value in matrix.items:
            if not isinstance(value, Seq):
                return None
            if key.value == "include":
                extra += len(value.items)
            elif key.value != "exclude":
                axes += 1
                size *= len(value.items)
        return max(1, (size if axes else 0) + extra)

    def check_workflow_secrets(self) -> None:
        if all(job.get("environment") is not None for _, job in self.jobs):
            return
        for key, value in self.doc.items:
            if key.value == "jobs":
                continue
            for scalar, _ in self.secret_refs(value):
                self.report(
                    scalar,
                    "secrets-need-environment",
                    "secret at workflow level, but a job has no environment",
                )

    # -- job level

    def check_job(self, key: Scalar, job: Mapping) -> None:
        job_id = key.value
        reusable = job.get("uses")
        if reusable is not None:
            self.check_uses(reusable)
        else:
            self.check_runner(key, job)
            self.check_timeout(key, job)
        self.check_job_permissions(job_id, job)
        self.check_secrets(key, job)
        self.check_public_guard(key, job)
        steps = job.get("steps")
        if isinstance(steps, Seq):
            for step in steps.items:
                if isinstance(step, Mapping):
                    self.check_step(step)

    def check_runner(self, key: Scalar, job: Mapping) -> None:
        node = job.get("runs-on")
        if node is None:
            self.report(key, "runner-label", "job has no runs-on")
            return
        value = _str(node)
        if value is None or "${{" in value or value not in self.policy.allowed_runners:
            shown = value if value is not None else "a list or mapping"
            allowed = ", ".join(sorted(self.policy.allowed_runners))
            self.report(node, "runner-label", f"runs-on {shown} is not one of {allowed}")

    def check_timeout(self, key: Scalar, job: Mapping) -> None:
        node = job.get("timeout-minutes")
        limit = self.policy.max_timeout_minutes
        value = _str(node)
        if node is None or value is None:
            self.report(key, "job-timeout", f"job has no timeout-minutes (at most {limit})")
        elif not value.isdigit() or not 1 <= int(value) <= limit:
            self.report(node, "job-timeout", f"timeout-minutes {value} is not from 1 to {limit}")

    def check_job_permissions(self, job_id: str, job: Mapping) -> None:
        node = job.get("permissions")
        if node is None:
            return
        self.check_actions_write(node)
        allowed = self.policy.job_permissions.get(self.name, {}).get(job_id, {})
        if not isinstance(node, Mapping):
            self.report(node, "job-permissions", f"job permissions {_str(node)!r} not allowed")
            return
        for scope, value in node.items:
            level = _str(value)
            if level == "none" or (scope.value, level) in TOP_PERMISSIONS.items():
                continue
            if allowed.get(scope.value) != level:
                self.report(
                    scope,
                    "job-permissions",
                    f"{scope.value}: {level} not in job_permissions.{self.name}.{job_id}",
                )

    @staticmethod
    def secret_refs(node: Node) -> Iterator[tuple[Scalar, str]]:
        for scalar in _scalars(node):
            for expr in EXPRESSION.finditer(scalar.value):
                if SECRET_REF.search(expr.group(1)):
                    yield scalar, expr.group(0)

    def check_secrets(self, key: Scalar, job: Mapping) -> None:
        if job.get("environment") is not None:
            return
        inherit = job.get("secrets")
        if _str(inherit) == "inherit" and inherit is not None:
            self.report(inherit, "secrets-need-environment", "secrets: inherit without environment")
        for _, value in job.items:
            for scalar, expr in self.secret_refs(value):
                self.report(
                    scalar, "secrets-need-environment", f"{expr} in a job without environment"
                )

    def check_public_guard(self, key: Scalar, job: Mapping) -> None:
        if self.name not in self.policy.public_only_workflows:
            return
        condition = _str(job.get("if"))
        needed = [REPO_PUBLIC] + ([VARS_PUBLIC] if "schedule" in self.triggers else [])
        normalized = _normalize(condition or "")
        missing = [n for n in needed if _normalize(n) not in normalized]
        if missing:
            self.report(
                job.get("if") or key,
                "public-only-guard",
                "public-only job needs if: with " + " and ".join(missing),
            )

    def check_step(self, step: Mapping) -> None:
        uses = step.get("uses")
        if uses is not None:
            self.check_uses(uses)
            value = (_str(uses) or "").lower()
            if value.startswith("actions/checkout@"):
                with_node = step.get("with")
                persist = (
                    with_node.get("persist-credentials") if isinstance(with_node, Mapping) else None
                )
                if (_str(persist) or "").lower() != "false":
                    self.report(
                        persist or uses,
                        "checkout-no-persist",
                        "actions/checkout needs persist-credentials: false",
                    )
        run = step.get("run")
        if isinstance(run, Scalar):
            self.check_run(run)

    def check_uses(self, node: Node) -> None:
        value = _str(node)
        if not isinstance(node, Scalar) or value is None:
            self.report(node, "action-pin", "uses must be a string")
            return
        if value.startswith("./"):
            return
        if value.startswith("docker://"):
            if not DOCKER_USES.fullmatch(value):
                self.report(node, "action-pin", f"{value} needs a digest @sha256:<64 hex>")
            return
        if not SHA_USES.fullmatch(value):
            self.report(node, "action-pin", f"{value} is not pinned to a full commit SHA")
        elif not VERSION_COMMENT.fullmatch(node.comment):
            self.report(node, "action-pin", f"{value} needs a comment # v<version>")

    def check_run(self, run: Scalar) -> None:
        if run.parts:
            for line, col, text in run.parts:
                index = text.find("${{")
                if index >= 0:
                    self.report(Node(line, col + index), "no-expr-in-run", "${{ in run; use env")
        else:
            index = run.value.find("${{")
            if index >= 0:
                where = Node(run.line, run.col + index + (1 if run.quoted else 0))
                self.report(where, "no-expr-in-run", "${{ in run; use env")


# ---------------------------------------------------------------------------
# Main


def workflow_files(root: Path, directory: Path) -> list[Path]:
    base = root / directory
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if p.is_file() and p.suffix in WORKFLOW_SUFFIXES)


def check(
    root: Path,
    policy_path: Path,
    directory: Path,
    strict: bool = False,
    gates_path: Path = GATES_PATH,
) -> list[Finding]:
    """Findings of all workflows; raise ConfigError or a located YamlError."""
    policy_file = policy_path if policy_path.is_absolute() else root / policy_path
    shown_policy = policy_path.as_posix()
    if not policy_file.is_file():
        raise ConfigError("file missing", shown_policy)
    policy = load_policy(policy_file, shown_policy)
    make_targets: frozenset[str] | None = None
    if strict:
        gates_file = gates_path if gates_path.is_absolute() else root / gates_path
        make_targets = load_make_targets(gates_file, gates_path.as_posix())
    findings: list[Finding] = []
    for path in workflow_files(root, directory):
        shown = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
        try:
            doc = parse_yaml(path.read_text(encoding="utf-8-sig"))
        except YamlError as exc:
            raise UnparsableError(shown, exc.line, str(exc)) from exc
        except (OSError, UnicodeDecodeError) as exc:
            raise UnparsableError(shown, 1, f"unreadable: {exc}") from exc
        except (RecursionError, OverflowError, ValueError) as exc:
            # Deep nesting or numbers beyond the interpreter's limits.
            raise UnparsableError(shown, 1, f"{type(exc).__name__}: {exc}") from exc
        if not isinstance(doc, Mapping):
            raise UnparsableError(shown, doc.line, "a workflow must be a mapping")
        try:
            findings.extend(WorkflowChecker(policy, shown, path.name, doc, make_targets).run())
        except (RecursionError, OverflowError, ValueError) as exc:
            raise UnparsableError(shown, 1, f"{type(exc).__name__}: {exc}") from exc
    return sorted(findings, key=lambda f: (f.path, f.line, f.col, f.rule))


class UnparsableError(Exception):
    def __init__(self, path: str, line: int, reason: str) -> None:
        super().__init__(reason)
        self.path = path
        self.line = line


def write_json(path: Path, findings: Sequence[Finding]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "tool": "check_workflows",
        "findings": [
            {"path": f.path, "line": f.line, "col": f.col, "rule": f.rule, "message": f.message}
            for f in findings
        ],
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check workflows against the workflow policy.")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root")
    parser.add_argument("--policy", type=Path, default=POLICY_PATH, help="policy, from root")
    parser.add_argument("--dir", type=Path, default=WORKFLOW_DIR, help="workflows, from root")
    parser.add_argument("--json", type=Path, help="also write the findings as JSON here")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="also known-workflow, make-target-exists, job-env-known",
    )
    parser.add_argument(
        "--gates", type=Path, default=GATES_PATH, help="make targets for --strict, from root"
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    try:
        findings = check(root, args.policy, args.dir, args.strict, args.gates)
    except ConfigError as exc:
        print(f"workflows.config_invalid path={exc.path} reason={exc}", file=sys.stderr)
        return EXIT_CONFIG
    except UnparsableError as exc:
        print(f"workflows.unparsable path={exc.path}:{exc.line} reason={exc}", file=sys.stderr)
        return EXIT_CONFIG
    if args.json is not None:
        write_json(args.json, findings)
    for finding in findings:
        print(finding.text())
    return EXIT_FINDINGS if findings else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
