#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Check the work plan and the component catalog, generate overview and build book.

Sources: docs/plan/tasks/stage-<stage>.toml (head of a stage) and
stage-<stage>.<area>.toml (epics and tasks of one area), and the component
catalog docs/design/components/<id>.toml. Keys and values are the English
mapping of detailed design 00 section 4.6 (FE-037, FE-055).
Generated (never edit by hand): docs/plan/overview.md and docs/design/build-book.md.

Usage:

  plan.py [--root DIR] check             check; overview and build book must be up to date
  plan.py [--root DIR] generate          check and write overview and build book
  plan.py [--root DIR] generate --check  check and fail if a generated file differs
  plan.py [--root DIR] ready             tasks that may start now
  plan.py [--root DIR] check-partial     like check, but empty epics, missing catalog
                                         coverage and generated files do not count
                                         (only while the plan is written in parts)
  plan.py [--root DIR] compare --german DIR
                                         compare the counts of stages, epics, tasks,
                                         subtasks, components, provides and uses with the
                                         German version under DIR (docs/plan/aufgaben,
                                         docs/feinentwurf/komponenten), read through the
                                         fixed key mapping

--root is the repository root (default: the root of this file). Without
docs/plan/tasks every command except compare prints
`plan.skipped reason=no_tasks_dir` and exits 0; once the directory exists it is
checked in full. The stage graph is checked against the Mermaid graph of
docs/architecture/08-roadmap.md and the design references against the numbered
documents docs/design/NN-*.md; each check is left out with a `plan.note` line
while its files are missing.

Standard library only (FE-004); Python 3.11 or newer (tomllib).

Exit codes:
  0  no finding
  1  findings, on stderr after a line `ERROR`
  2  usage error
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if not __package__:
    # Run as a script (make plan): make the tools package importable.
    sys.path.insert(0, str(ROOT))

from tools.ci import spdx_header  # noqa: E402

TASKS_DIR = "docs/plan/tasks"
OVERVIEW_FILE = "docs/plan/overview.md"
ROADMAP_FILE = "docs/architecture/08-roadmap.md"
DESIGN_DIR = "docs/design"
CATALOG_DIR = "docs/design/components"
BUILD_BOOK_FILE = "docs/design/build-book.md"
# License header of the generated Markdown files, from its one source (FE-053).
MARKDOWN_HEADER = spdx_header.render(Path(OVERVIEW_FILE))
GERMAN_TASKS_DIR = "docs/plan/aufgaben"
GERMAN_CATALOG_DIR = "docs/feinentwurf/komponenten"

STAGES = ["R", "0", "0b", "1", "2", "3", "4", "5", "6", "7a", "7", "8", "9", "10"]
CORE = {"R", "0", "1", "6", "7a"}
STATUS = ["open", "in_progress", "blocked", "done", "dropped"]
FINISHED = ("done", "dropped")
OWNERS = ["agent", "owner", "agent+owner"]
# Mermaid nodes in 08-roadmap.md section 3 -> stage key
MERMAID_NODES = {
    "SR": "R", "S0": "0", "S0b": "0b", "S1": "1", "S2": "2", "S3": "3", "S4": "4",
    "S5": "5", "S6": "6", "S7a": "7a", "S7": "7", "S8": "8", "S9": "9", "S10": "10",
}  # fmt: skip
STAGE_RE = "(?:R|0b|7a|10|[0-9])"
EPIC_RE = re.compile(rf"^({STAGE_RE})-E(\d{{2}})$")
TASK_RE = re.compile(rf"^({STAGE_RE})-E(\d{{2}})-T(\d{{2}})$")
PART_RE = re.compile(rf"^({STAGE_RE})-E(\d{{2}})-T(\d{{2}})-S(\d{{2}})$")

Data = dict[str, Any]


class PlanError(Exception):
    pass


@dataclass
class Node:
    id: str
    kind: str  # epic | task | part
    stage: str
    title: str
    parent: str | None
    depends_on: list[str] = field(default_factory=list)
    status: str = "open"
    estimate_h: float = 0.0
    owner: str = "agent"
    file: str = ""
    design: list[str] = field(default_factory=list)
    text: str = ""  # description, result and done of a task (for section references)


@dataclass
class Plan:
    stages: dict[str, Data]
    nodes: dict[str, Node]


def _required(d: Data, key: str, where: str, kind: type = str) -> Any:
    if key not in d:
        raise PlanError(f"{where}: field '{key}' is missing")
    value = d[key]
    if kind is str and (not isinstance(value, str) or not value.strip()):
        raise PlanError(f"{where}: field '{key}' must be a non-empty text")
    if kind is list and (not isinstance(value, list) or not value):
        raise PlanError(f"{where}: field '{key}' must be a non-empty list")
    return value


def _read_toml(path: Path, errors: list[str]) -> Data | None:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        errors.append(f"{path.name}: invalid TOML: {e}")
        return None


def load(directory: Path) -> Plan:
    """Read every stage-*.toml of a directory."""
    errors: list[str] = []
    documents = []
    paths = sorted(directory.glob("stage-*.toml"))
    if not paths:
        raise PlanError(f"{directory}: no stage-*.toml")
    for path in paths:
        data = _read_toml(path, errors)
        if data is not None:
            documents.append((path.name, data))
    return build_plan(documents, errors)


def build_plan(documents: Iterable[tuple[str, Data]], errors: list[str] | None = None) -> Plan:
    stages: dict[str, Data] = {}
    nodes: dict[str, Node] = {}
    errors = list(errors or [])

    def add(n: Node) -> None:
        if n.id in nodes:
            errors.append(f"{n.file}: ID {n.id} duplicate (also in {nodes[n.id].file})")
        nodes[n.id] = n

    for name, data in documents:
        try:
            _build_file(name, data, stages, add)
        except PlanError as e:
            errors.append(str(e))

    for n in nodes.values():
        if n.stage not in stages:
            errors.append(f"{n.file}: stage {n.stage} has no file stage-{n.stage}.toml")
            break
    if errors:
        raise PlanError("\n".join(errors))
    return Plan(stages, nodes)


def _build_file(
    name: str, data: Data, stages: dict[str, Data], add: Callable[[Node], None]
) -> None:
    stage = _required(data, "stage", name)
    if stage not in STAGES:
        raise PlanError(f"{name}: unknown stage {stage}")
    if name == f"stage-{stage}.toml":
        _required(data, "title", name)
        depends = data.get("depends_on_stages", [])
        if not isinstance(depends, list):
            raise PlanError(f"{name}: depends_on_stages must be a list")
        stages[stage] = {"title": data["title"], "depends_on_stages": depends, "file": name}
    elif re.fullmatch(rf"stage-{re.escape(stage)}\.[a-z0-9-]+\.toml", name):
        if "depends_on_stages" in data or "title" in data:
            raise PlanError(f"{name}: title and depends_on_stages only in stage-{stage}.toml")
    else:
        raise PlanError(f"{name}: file name does not match stage = {stage}")

    for e in data.get("epic", []):
        where = f"{name} epic {e.get('id', '?')}"
        eid = _required(e, "id", where)
        m = EPIC_RE.match(eid)
        if not m or m.group(1) != stage:
            raise PlanError(f"{where}: ID must be '{stage}-Enn'")
        for f in ("title", "goal"):
            _required(e, f, where)
        _required(e, "sources", where, list)
        add(Node(eid, "epic", stage, e["title"], None, list(e.get("depends_on", [])), file=name))

    for t in data.get("task", []):
        where = f"{name} task {t.get('id', '?')}"
        tid = _required(t, "id", where)
        m = TASK_RE.match(tid)
        if not m or m.group(1) != stage:
            raise PlanError(f"{where}: ID must be '{stage}-Enn-Tnn'")
        epic = f"{m.group(1)}-E{m.group(2)}"
        for f in ("title", "description", "result"):
            _required(t, f, where)
        _required(t, "done", where, list)
        _required(t, "sources", where, list)
        owner = t.get("owner", "agent")
        if owner not in OWNERS:
            raise PlanError(f"{where}: owner = {owner} not in {OWNERS}")
        status = t.get("status", "open")
        if status not in STATUS:
            raise PlanError(f"{where}: status = {status} not in {STATUS}")
        h = t.get("estimate_h")
        if isinstance(h, bool) or not isinstance(h, int | float) or h <= 0:
            raise PlanError(f"{where}: estimate_h must be a number > 0")
        design = t.get("design", [])
        if not isinstance(design, list):
            raise PlanError(f"{where}: design must be a list")
        text = "\n".join([t["description"], t["result"], *map(str, t["done"])])
        add(
            Node(tid, "task", stage, t["title"], epic, list(t.get("depends_on", [])), status,
                 float(h), owner, name, list(design), text)
        )  # fmt: skip
        for part in t.get("part", []):
            pwhere = f"{where} part {part.get('id', '?')}"
            pid = _required(part, "id", pwhere)
            if not PART_RE.match(pid) or not pid.startswith(tid + "-"):
                raise PlanError(f"{pwhere}: ID must be '{tid}-Snn'")
            _required(part, "title", pwhere)
            _required(part, "done", pwhere)
            pstatus = part.get("status", "open")
            if pstatus not in STATUS:
                raise PlanError(f"{pwhere}: status = {pstatus} not in {STATUS}")
            add(
                Node(pid, "part", stage, part["title"], tid, list(part.get("depends_on", [])),
                     pstatus, 0.0, owner, name)
            )  # fmt: skip


def stage_ancestors(plan: Plan) -> dict[str, set[str]]:
    ancestors: dict[str, set[str]] = {}

    def visit(s: str, path: tuple[str, ...]) -> set[str]:
        if s in path:
            raise PlanError(f"stage graph has a cycle: {' -> '.join((*path, s))}")
        if s in ancestors:
            return ancestors[s]
        result: set[str] = set()
        for v in plan.stages.get(s, {}).get("depends_on_stages", []):
            result |= {v} | visit(v, (*path, s))
        ancestors[s] = result
        return result

    for s in plan.stages:
        visit(s, ())
    return ancestors


def roadmap_edges(text: str) -> set[tuple[str, str]]:
    """Read the edges of the Mermaid graph in 08-roadmap.md section 3."""
    block = re.search(r"```mermaid\n(.*?)```", text, re.S)
    if not block:
        raise PlanError("08-roadmap.md: Mermaid graph not found")
    edges = set()
    for left, right in re.findall(r"(\w+)(?:\[[^\]]*\])?\s*-->\s*(\w+)", block.group(1)):
        if left not in MERMAID_NODES or right not in MERMAID_NODES:
            raise PlanError(f"08-roadmap.md: unknown node in edge {left} --> {right}")
        edges.add((MERMAID_NODES[left], MERMAID_NODES[right]))
    return edges


def leaves(plan: Plan, nid: str) -> list[str]:
    """Tasks a node covers (epic -> all its tasks, task -> itself, part -> its task)."""
    n = plan.nodes[nid]
    if n.kind == "epic":
        return [t.id for t in plan.nodes.values() if t.kind == "task" and t.parent == nid]
    if n.kind == "part" and n.parent is not None:
        return [n.parent]
    return [nid]


def task_edges(plan: Plan) -> dict[str, set[str]]:
    """Dependencies between tasks; the dependencies of an epic hold for each of its tasks."""
    edges: dict[str, set[str]] = {t.id: set() for t in plan.nodes.values() if t.kind == "task"}
    for n in plan.nodes.values():
        if n.kind == "part":
            continue
        targets = leaves(plan, n.id)
        for dep in n.depends_on:
            for target in targets:
                edges[target] |= set(leaves(plan, dep))
    for n in plan.nodes.values():
        if n.kind == "part" and n.parent is not None:
            for dep in n.depends_on:
                edges[n.parent] |= {d for d in leaves(plan, dep) if d != n.parent}
    return edges


def check_plan(
    plan: Plan,
    roadmap_text: str | None = None,
    design: Path | None = None,
    allow_empty_epics: bool = False,
) -> list[str]:
    errors: list[str] = []
    ancestors = stage_ancestors(plan)

    if roadmap_text is not None:
        expected = roadmap_edges(roadmap_text)
        actual = {(v, s) for s, d in plan.stages.items() for v in d["depends_on_stages"]}
        for v, s in sorted(expected - actual):
            if s in plan.stages:
                errors.append(
                    f"stage-{s}.toml: depends_on_stages lacks {v} (edge in 08-roadmap.md)"
                )
        for v, s in sorted(actual - expected):
            errors.append(f"stage-{s}.toml: depends_on_stages {v} is not in 08-roadmap.md")

    for n in plan.nodes.values():
        if n.kind == "task" and n.parent not in plan.nodes:
            errors.append(f"{n.file}: {n.id} belongs to epic {n.parent}, which does not exist")
        for dep in n.depends_on:
            if dep not in plan.nodes:
                errors.append(f"{n.file}: {n.id} depends on {dep}, which does not exist")
                continue
            if dep == n.id:
                errors.append(f"{n.file}: {n.id} depends on itself")
                continue
            ds = plan.nodes[dep].stage
            if ds != n.stage and ds not in ancestors.get(n.stage, set()):
                errors.append(
                    f"{n.file}: {n.id} depends on {dep} of stage {ds}, "
                    f"which is not before stage {n.stage} in the stage graph"
                )
        if design is not None:
            for ref in n.design:
                reason = reference_error(design, ref)
                if reason:
                    errors.append(f"{n.file}: {n.id} refers to docs/design/{ref}, {reason}")
            for file, number in text_references(n.text):
                if (design / file).is_file() and is_move_notice(
                    section_by_number(design / file, number)
                ):
                    errors.append(f"{n.file}: {n.id} names {file} section {number}, {MOVE_REASON}")
    for e in (n for n in plan.nodes.values() if n.kind == "epic"):
        if not leaves(plan, e.id) and not allow_empty_epics:
            errors.append(f"{e.file}: epic {e.id} has no task")
    if errors:
        return errors

    edges = task_edges(plan)
    try:
        topological(edges)
    except PlanError as e:
        return [str(e)]

    for tid, deps in edges.items():
        t = plan.nodes[tid]
        if t.status in ("in_progress", "done"):
            unfinished = [d for d in deps if plan.nodes[d].status not in FINISHED]
            if unfinished:
                errors.append(
                    f"{t.file}: {tid} is {t.status}, but {', '.join(sorted(unfinished))} not done"
                )
    return errors


def anchor(heading: str) -> str:
    """Hoster anchor of a Markdown heading (without the counter suffix of duplicates)."""
    text = re.sub(r"^#+\s*", "", heading.strip())
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[^\w\- ]", "", text.lower())
    return text.replace(" ", "-")


_SECTION_CACHE: dict[Path, list[tuple[str, str, str]]] = {}


def anchors_of(file: Path) -> set[str]:
    return {a for a, _, _ in sections(file)}


def sections(file: Path) -> list[tuple[str, str, str]]:
    """(anchor, heading, text up to the next heading) per heading outside code blocks."""
    if file not in _SECTION_CACHE:
        _SECTION_CACHE[file] = _read_sections(file)
    return _SECTION_CACHE[file]


def _read_sections(file: Path) -> list[tuple[str, str, str]]:
    parts: list[tuple[str, str, list[str]]] = []
    counter: dict[str, int] = {}
    in_code = False
    for line in file.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
            if parts:
                parts[-1][2].append(line)
            continue
        if not in_code and re.match(r"^#{1,6}\s", line):
            a = anchor(line)
            n = counter.get(a, 0)
            counter[a] = n + 1
            parts.append((f"{a}-{n}" if n else a, re.sub(r"^#+\s*", "", line).strip(), []))
        elif parts:
            parts[-1][2].append(line)
    return [(a, h, "\n".join(lines).strip()) for a, h, lines in parts]


MOVE_RE = re.compile(r"^(Detailed in|Moved to)\b")
MOVE_REASON = (
    "the section is only a move notice (Detailed in/Moved to); point to the target section"
)
TEXT_REF_RE = re.compile(
    r"\b(\d\d-[a-z0-9-]+\.md)\)? [Ss]ections? (\d+(?:\.\d+)*(?:(?:,| and| to) \d+(?:\.\d+)*)*)"
)


def is_move_notice(text: str | None) -> bool:
    """A section that only points elsewhere ("Detailed in ...", "Moved to ...")."""
    return text is not None and bool(MOVE_RE.match(text))


def section_by_anchor(file: Path, target: str) -> str | None:
    return next((t for a, _, t in sections(file) if a == target), None)


def section_by_number(file: Path, number: str) -> str | None:
    for _, heading, t in sections(file):
        if re.match(rf"^{re.escape(number)}\.?\s", heading):
            return t
    return None


def text_references(text: str) -> list[tuple[str, str]]:
    """References like '13-x.md section 2.1' or 'sections 2.8 and 10' in a task text."""
    pairs = []
    for m in TEXT_REF_RE.finditer(text):
        for number in re.findall(r"\d+(?:\.\d+)*", m.group(2)):
            pairs.append((m.group(1), number))
    return pairs


def reference_error(design: Path, ref: str) -> str | None:
    """None if 'file.md' or 'file.md#anchor' exists and is not only a move notice,
    otherwise the reason."""
    file, _, target = ref.partition("#")
    path = design / file
    if not path.is_file():
        return "the file is missing"
    if target and target not in anchors_of(path):
        return "the anchor is missing"
    if target and is_move_notice(section_by_anchor(path, target)):
        return MOVE_REASON
    return None


# ---------------------------------------------------------------- component catalog

COMPONENT_KINDS = ["package", "program", "role", "plugin", "driver", "service", "eval",
                   "delivery", "tool", "ui", "process"]  # fmt: skip
INTERFACE_KINDS = ["ts-api", "http", "mcp-tool", "event", "table", "queue", "cli", "config",
                   "contract", "file", "ui", "prompt", "metric"]  # fmt: skip
COMPONENT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass
class Component:
    id: str
    title: str
    kind: str
    path: str
    stage: str
    purpose: str
    design: list[str]
    built_by: list[str]
    provides: list[Data]
    uses: list[Data]
    package: str = ""
    file: str = ""
    area: str = ""


def load_catalog(directory: Path) -> dict[str, Component]:
    if not directory.is_dir():
        raise PlanError(f"{directory}: catalog directory is missing")
    errors: list[str] = []
    documents = []
    for path in sorted(directory.glob("*.toml")):
        data = _read_toml(path, errors)
        if data is not None:
            documents.append((path.name, data))
    return build_catalog(documents, errors)


def build_catalog(
    documents: Iterable[tuple[str, Data]], errors: list[str] | None = None
) -> dict[str, Component]:
    catalog: dict[str, Component] = {}
    errors = list(errors or [])
    for name, d in documents:
        try:
            catalog[d.get("id", name)] = _build_component(name, d)
        except PlanError as e:
            errors.append(str(e))
    if errors:
        raise PlanError("\n".join(errors))
    return catalog


def _build_component(name: str, d: Data) -> Component:
    cid = _required(d, "id", name)
    if name != f"{cid}.toml" or not COMPONENT_ID_RE.match(cid):
        raise PlanError(f"{name}: file name must be '<id>.toml', id of a-z, 0-9 and '-'")
    for f in ("title", "kind", "path", "stage", "purpose"):
        _required(d, f, name)
    if d["kind"] not in COMPONENT_KINDS:
        raise PlanError(f"{name}: kind = {d['kind']} not in {COMPONENT_KINDS}")
    if d["stage"] not in STAGES:
        raise PlanError(f"{name}: unknown stage {d['stage']}")
    _required(d, "design", name, list)
    _required(d, "built_by", name, list)
    provides, uses = d.get("provides", []), d.get("uses", [])
    for p in provides:
        where = f"{name} provides {p.get('name', '?')}"
        for f in ("name", "kind", "title", "defined_in", "from_task"):
            _required(p, f, where)
        if p["kind"] not in INTERFACE_KINDS:
            raise PlanError(f"{where}: kind = {p['kind']} not in {INTERFACE_KINDS}")
        if not COMPONENT_ID_RE.match(p["name"].replace(".", "-")):
            raise PlanError(f"{where}: name of a-z, 0-9, '-' and '.'")
    for u in uses:
        where = f"{name} uses {u.get('interface', '?')}"
        for f in ("interface", "from_task", "purpose"):
            _required(u, f, where)
    return Component(
        cid, d["title"], d["kind"], d["path"], d["stage"], d["purpose"], list(d["design"]),
        list(d["built_by"]), provides, uses, d.get("package", ""), name, d.get("area", ""),
    )  # fmt: skip


def interfaces(catalog: dict[str, Component]) -> dict[str, tuple[Component, Data]]:
    return {f"{c.id}/{p['name']}": (c, p) for c in catalog.values() for p in c.provides}


def predecessors(edges: dict[str, set[str]]) -> dict[str, set[str]]:
    """All tasks a task depends on, transitively."""
    result: dict[str, set[str]] = {}
    for t in topological(edges):
        s: set[str] = set()
        for d in edges[t]:
            s |= {d} | result[d]
        result[t] = s
    return result


def check_catalog(
    plan: Plan,
    catalog: dict[str, Component],
    design: Path | None = None,
    coverage: bool = True,
) -> list[str]:
    errors: list[str] = []
    all_interfaces = interfaces(catalog)
    seen: set[str] = set()
    for c in catalog.values():
        for p in c.provides:
            sid = f"{c.id}/{p['name']}"
            if sid in seen:
                errors.append(f"{c.file}: interface {sid} duplicate")
            seen.add(sid)
    before = predecessors(task_edges(plan))
    for c in sorted(catalog.values(), key=lambda c: c.id):
        for t in c.built_by:
            if t not in plan.nodes or plan.nodes[t].kind != "task":
                errors.append(f"{c.file}: built_by {t}, the task does not exist")
        if design is not None:
            for ref in c.design:
                reason = reference_error(design, ref)
                if reason:
                    errors.append(f"{c.file}: design {ref}, {reason}")
        for p in c.provides:
            sid = f"{c.id}/{p['name']}"
            if p["from_task"] not in c.built_by:
                errors.append(f"{c.file}: {sid} from_task {p['from_task']} is not in built_by")
            if design is not None:
                reason = reference_error(design, p["defined_in"])
                if reason:
                    errors.append(f"{c.file}: {sid} defined_in {p['defined_in']}, {reason}")
        for u in c.uses:
            sid, at = u["interface"], u["from_task"]
            if sid not in all_interfaces:
                errors.append(f"{c.file}: uses {sid}, the interface does not exist")
                continue
            provider, p = all_interfaces[sid]
            if provider.id == c.id:
                errors.append(f"{c.file}: uses {sid}, its own interface")
                continue
            if at not in c.built_by:
                errors.append(f"{c.file}: uses {sid} from_task {at}, which is not in built_by")
                continue
            source = p["from_task"]
            if at in before and source in plan.nodes and at != source and source not in before[at]:
                errors.append(
                    f"{c.file}: uses {sid} in {at}, which does not depend on {source} "
                    "(provided there)"
                )
    errors += path_spellings(plan, catalog)
    if coverage:
        covered = {t for c in catalog.values() for t in c.built_by}
        tasks = sorted(
            (n for n in plan.nodes.values() if n.kind == "task"), key=lambda n: sort_key(n.id)
        )
        for task in tasks:
            if task.id not in covered and task.status != "dropped":
                errors.append(f"task {task.id} belongs to no component (built_by)")
    return errors


PATH_IN_TEXT_RE = re.compile(r"\bapps/([a-z0-9-]+)/src/([A-Za-z0-9_-]+)(?=[/.])")


def _path_norm(name: str) -> str:
    n = re.sub(r"[-_]", "", name.lower())
    return n[:-3] if n.endswith("api") and len(n) > 3 else n


def path_spellings(plan: Plan, catalog: dict[str, Component]) -> list[str]:
    """A directory apps/<app>/src/<dir> in a task text that differs from the directory of a
    component only in spelling (hyphen, underscore, suffix 'api'), such as work-api or
    workapi instead of work. Other new directories are not checked."""
    known: dict[tuple[str, str], str] = {}
    for c in catalog.values():
        m = re.match(r"^apps/([a-z0-9-]+)/src/([A-Za-z0-9_-]+)/", c.path)
        if m:
            known[(m.group(1), _path_norm(m.group(2)))] = m.group(2)
    errors = []
    tasks = sorted(
        (n for n in plan.nodes.values() if n.kind == "task"), key=lambda n: sort_key(n.id)
    )
    for t in tasks:
        for app, d in sorted(set(PATH_IN_TEXT_RE.findall(t.text))):
            expected = known.get((app, _path_norm(d)))
            if expected is not None and expected != d:
                errors.append(
                    f"{t.file}: {t.id} names apps/{app}/src/{d}/, "
                    f"the catalog writes apps/{app}/src/{expected}/"
                )
    return errors


def _link(ref: str) -> str:
    return f"[{ref}]({ref})"


def generate_build_book(plan: Plan, catalog: dict[str, Component]) -> str:
    edges = task_edges(plan)
    order = {t: i for i, t in enumerate(topological(edges))}
    all_interfaces = interfaces(catalog)
    users: dict[str, list[tuple[str, str]]] = {}
    for c in catalog.values():
        for u in c.uses:
            users.setdefault(u["interface"], []).append((c.id, u["from_task"]))

    def stage_of(t: str) -> str:
        return plan.nodes[t].stage if t in plan.nodes else "?"

    def ordering(c: Component) -> tuple[int, str]:
        return (STAGES.index(c.stage), c.id)

    def ref(cid: str) -> str:
        return f"[`{cid}`](#{anchor('k-' + cid)})"

    z = [
        "# Build book: Guildwork in build order",
        "",
        "**Generated** by `tools/plan/plan.py generate` from the component catalog "
        "(`docs/design/components/*.toml`) and the work plan (`docs/plan/tasks/*.toml`). "
        "Do not edit by hand; rules in [components/README.md](components/README.md).",
        "",
        "Part 1 describes the tool stage by stage as it comes into being: which components "
        "are added, which grow and which interfaces are ready from which task. Part 2 is the "
        "component sheet of each component: what it provides, where it docks and which "
        "tasks build it.",
        "",
        "## Part 1: Stage by stage",
        "",
    ]
    for s in (s for s in STAGES if s in plan.stages):
        new = sorted((c for c in catalog.values() if c.stage == s), key=ordering)
        grow = sorted(
            (c for c in catalog.values()
             if c.stage != s and any(stage_of(t) == s for t in c.built_by)),
            key=ordering,
        )  # fmt: skip
        z += [f"### Stage {s}: {plan.stages[s]['title']}", ""]
        if plan.stages[s]["depends_on_stages"]:
            z += [f"Builds on stage {', '.join(plan.stages[s]['depends_on_stages'])}.", ""]
        if new:
            z += ["**New:**", "", "| Component | Kind | Path | Purpose |", "|---|---|---|---|"]
            z += [f"| {ref(c.id)} | {c.kind} | `{c.path}` | {c.purpose} |" for c in new]
            z.append("")
        if grow:
            z += ["**Grows:** " + ", ".join(ref(c.id) for c in grow), ""]
        new_interfaces = sorted(
            ((sid, cp) for sid, cp in all_interfaces.items()
             if stage_of(cp[1]["from_task"]) == s),
            key=lambda x: (order.get(x[1][1]["from_task"], 0), x[0]),
        )  # fmt: skip
        if new_interfaces:
            z += [
                "**Ready from:**",
                "",
                "| Interface | Kind | from task | docked by |",
                "|---|---|---|---|",
            ]
            for sid, (_, p) in new_interfaces:
                by = ", ".join(sorted({f"`{n}` ({t})" for n, t in users.get(sid, [])})) or "-"
                z.append(f"| `{sid}` {p['title']} | {p['kind']} | {p['from_task']} | {by} |")
            z.append("")
    z += ["## Part 2: Component sheets", ""]
    for c in sorted(catalog.values(), key=ordering):
        z += [
            f"### K `{c.id}`",
            "",
            f"**{c.title}** ({c.kind}, from stage {c.stage}). {c.purpose}",
            "",
            f"- Path: `{c.path}`" + (f", package `{c.package}`" if c.package else ""),
            "- Design: " + ", ".join(_link(r) for r in c.design),
            "- Built by: " + ", ".join(sorted(c.built_by, key=lambda t: order.get(t, 0))),
            "",
        ]
        if c.provides:
            z += [
                "| provides | Kind | from task | defined in | used by |",
                "|---|---|---|---|---|",
            ]
            for p in c.provides:
                sid = f"{c.id}/{p['name']}"
                by = ", ".join(sorted({f"`{n}`" for n, _ in users.get(sid, [])})) or "-"
                z.append(
                    f"| `{sid}` {p['title']} | {p['kind']} | {p['from_task']} | "
                    f"{_link(p['defined_in'])} | {by} |"
                )
            z.append("")
        if c.uses:
            z += ["| uses | from | from task | purpose |", "|---|---|---|---|"]
            for u in sorted(c.uses, key=lambda u: (order.get(u["from_task"], 0), u["interface"])):
                origin = u["interface"].split("/", 1)[0]
                z.append(
                    f"| `{u['interface']}` | {ref(origin)} | {u['from_task']} | {u['purpose']} |"
                )
            z.append("")
    return MARKDOWN_HEADER + "\n".join(z)


def components_per_task(catalog: dict[str, Component]) -> dict[str, list[str]]:
    per: dict[str, list[str]] = {}
    for c in sorted(catalog.values(), key=lambda c: c.id):
        for t in c.built_by:
            per.setdefault(t, []).append(c.id)
    return per


def topological(edges: dict[str, set[str]]) -> list[str]:
    rest = {k: set(v) for k, v in edges.items()}
    result: list[str] = []
    while rest:
        free = sorted(k for k, v in rest.items() if not v)
        if not free:
            raise PlanError("dependencies have a cycle: " + " -> ".join(_find_cycle(rest)))
        for k in free:
            result.append(k)
            del rest[k]
        for v in rest.values():
            v.difference_update(free)
    return result


def _find_cycle(rest: dict[str, set[str]]) -> list[str]:
    path: list[str] = []
    k = sorted(rest)[0]
    while k not in path:
        path.append(k)
        k = sorted(rest[k])[0]
    return [*path[path.index(k) :], k]


def sort_key(nid: str) -> tuple[int, list[int]]:
    stage, rest = nid.split("-", 1)
    return (STAGES.index(stage), [int(x) for x in re.findall(r"\d+", rest)])


def critical_path(
    plan: Plan, edges: dict[str, set[str]], only: set[str]
) -> tuple[float, list[str]]:
    best: dict[str, tuple[float, list[str]]] = {}
    for tid in topological(edges):
        t = plan.nodes[tid]
        if t.stage not in only:
            continue
        before = [best[d] for d in sorted(edges[tid], key=sort_key) if d in best]
        h, path = max(before, key=lambda x: x[0]) if before else (0.0, [])
        best[tid] = (h + t.estimate_h, [*path, tid])
    if not best:
        return 0.0, []
    return max(best.values(), key=lambda x: x[0])


def ready(plan: Plan, edges: dict[str, set[str]]) -> list[str]:
    return sorted(
        (
            tid
            for tid, deps in edges.items()
            if plan.nodes[tid].status == "open"
            and all(plan.nodes[d].status in FINISHED for d in deps)
        ),
        key=sort_key,
    )


def generate_overview(plan: Plan) -> str:
    edges = task_edges(plan)
    z = [
        "# Work plan: overview",
        "",
        "**Generated** by `tools/plan/plan.py generate` from `docs/plan/tasks/stage-*.toml`. "
        "Do not edit by hand; rules in [README.md](README.md).",
        "",
        "Hours are estimates (unverified) and are measured again after each stage "
        "([README.md](README.md) section 6).",
        "",
        "## 1. Stages",
        "",
        "| Stage | Title | depends on | Core | Epics | Tasks | Subtasks | Estimate h | done |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for s in (s for s in STAGES if s in plan.stages):
        ns = [n for n in plan.nodes.values() if n.stage == s]
        tasks = [n for n in ns if n.kind == "task"]
        h = sum(n.estimate_h for n in tasks)
        finished = sum(1 for n in tasks if n.status in FINISHED)
        z.append(
            f"| {s} | {plan.stages[s]['title']} | "
            f"{', '.join(plan.stages[s]['depends_on_stages']) or '-'} | "
            f"{'yes' if s in CORE else 'no'} | {sum(1 for n in ns if n.kind == 'epic')} | "
            f"{len(tasks)} | {sum(1 for n in ns if n.kind == 'part')} | {h:g} | "
            f"{finished} of {len(tasks)} |"
        )
    h_core, path_core = critical_path(plan, edges, CORE)
    h_all, path_all = critical_path(plan, edges, set(STAGES))
    z += [
        "",
        "## 2. Critical path",
        "",
        f"- **Core** (stages {', '.join(s for s in STAGES if s in CORE)}): {h_core:g} h over "
        f"{len(path_core)} tasks, with unlimited parallelism; the real duration depends on "
        "the number of parallel agents.",
        f"- **All stages:** {h_all:g} h over {len(path_all)} tasks.",
        "",
        "Core path: " + " → ".join(f"`{t}`" for t in path_core),
        "",
        "## 3. Ready now",
        "",
        "Tasks with status `open` whose dependencies are all `done` or `dropped`:",
        "",
    ]
    for tid in ready(plan, edges):
        t = plan.nodes[tid]
        z.append(f"- `{tid}` {t.title} ({t.owner}, {t.estimate_h:g} h)")
    z += ["", "## 4. Epics per stage", ""]
    for s in (s for s in STAGES if s in plan.stages):
        z += [f"### Stage {s}: {plan.stages[s]['title']}", "", "```mermaid", "flowchart LR"]
        epics = sorted(
            (n for n in plan.nodes.values() if n.kind == "epic" and n.stage == s),
            key=lambda n: sort_key(n.id),
        )
        epic_edges = set()
        for e in epics:
            z.append(f'  {e.id.replace("-", "_")}["{e.id} {e.title}"]')
            for tid in leaves(plan, e.id):
                for d in edges[tid]:
                    de = plan.nodes[d].parent
                    if de is not None and de != e.id and plan.nodes[de].stage == s:
                        epic_edges.add((de, e.id))
        for v, n in sorted(epic_edges):
            z.append(f"  {v.replace('-', '_')} --> {n.replace('-', '_')}")
        z += [
            "```",
            "",
            "| ID | Task | depends on | owner | h | Status |",
            "|---|---|---|---|---|---|",
        ]
        for e in epics:
            z.append(f"| **{e.id}** | **{e.title}** | {', '.join(e.depends_on) or '-'} | | | |")
            for tid in sorted(leaves(plan, e.id), key=sort_key):
                t = plan.nodes[tid]
                z.append(
                    f"| {tid} | {t.title} | {', '.join(t.depends_on) or '-'} | {t.owner} | "
                    f"{t.estimate_h:g} | {t.status} |"
                )
        z.append("")
    z += [
        "## 5. Order (topological, across all stages)",
        "",
        "Each task comes after all tasks it depends on; within a wave the order is free.",
        "",
    ]
    rest = {k: set(v) for k, v in edges.items()}
    wave = 0
    while rest:
        wave += 1
        free = sorted((k for k, v in rest.items() if not v), key=sort_key)
        z.append(f"{wave}. " + ", ".join(f"`{k}`" for k in free))
        for k in free:
            del rest[k]
        for deps in rest.values():
            deps.difference_update(free)
    z.append("")
    return MARKDOWN_HEADER + "\n".join(z)


# ---------------------------------------------------------------- German version

# Fixed mapping of the German keys and values of the ops repo (detailed design 00
# section 4.6, FE-055). Only `compare --german` reads the German version.
GERMAN_STAGE_KEYS = {
    "stufe": "stage", "titel": "title", "haengt_an": "depends_on_stages",
    "epic": "epic", "aufgabe": "task",
}  # fmt: skip
GERMAN_EPIC_KEYS = {
    "id": "id", "titel": "title", "ziel": "goal", "quellen": "sources",
    "abhaengig_von": "depends_on",
}  # fmt: skip
GERMAN_TASK_KEYS = {
    "id": "id", "titel": "title", "beschreibung": "description", "feinentwurf": "design",
    "ergebnis": "result", "fertig": "done", "quellen": "sources",
    "abhaengig_von": "depends_on", "wer": "owner", "schaetzung_h": "estimate_h",
    "status": "status", "notiz": "note", "teil": "part",
}  # fmt: skip
GERMAN_PART_KEYS = {
    "id": "id", "titel": "title", "fertig": "done", "abhaengig_von": "depends_on",
    "status": "status", "notiz": "note",
}  # fmt: skip
GERMAN_COMPONENT_KEYS = {
    "id": "id", "titel": "title", "art": "kind", "pfad": "path", "paket": "package",
    "stufe": "stage", "zweck": "purpose", "feinentwurf": "design", "gebaut_von": "built_by",
    "bietet": "provides", "nutzt": "uses", "bereich": "area",
}  # fmt: skip
GERMAN_PROVIDES_KEYS = {
    "name": "name", "art": "kind", "titel": "title", "definiert_in": "defined_in",
    "ab_aufgabe": "from_task",
}  # fmt: skip
GERMAN_USES_KEYS = {"schnittstelle": "interface", "wozu": "purpose", "ab_aufgabe": "from_task"}
GERMAN_STATUS = {
    "offen": "open", "in_arbeit": "in_progress", "blockiert": "blocked", "fertig": "done",
    "entfällt": "dropped",
}  # fmt: skip
GERMAN_COMPONENT_KIND = {
    "paket": "package", "programm": "program", "rolle": "role", "plugin": "plugin",
    "treiber": "driver", "service": "service", "eval": "eval", "auslieferung": "delivery",
    "werkzeug": "tool", "ui": "ui", "prozess": "process",
}  # fmt: skip
GERMAN_INTERFACE_KIND = {
    "ts-api": "ts-api", "http": "http", "mcp-tool": "mcp-tool", "event": "event",
    "tabelle": "table", "queue": "queue", "cli": "cli", "konfig": "config",
    "vertrag": "contract", "datei": "file", "ui": "ui", "prompt": "prompt", "metrik": "metric",
}  # fmt: skip


def _rename(d: Data, keys: dict[str, str], where: str) -> Data:
    out: Data = {}
    for k, v in d.items():
        if k not in keys:
            raise PlanError(f"{where}: unknown German key '{k}'")
        out[keys[k]] = v
    return out


def _value(value: Any, values: dict[str, str]) -> Any:
    """The English value; an unknown value stays and is reported by the English check."""
    return values.get(value, value) if isinstance(value, str) else value


def translate_stage_file(name: str, d: Data) -> tuple[str, Data]:
    """A German stufe-*.toml as the English stage-*.toml it maps to."""
    out = _rename(d, GERMAN_STAGE_KEYS, name)
    out["epic"] = [_rename(e, GERMAN_EPIC_KEYS, f"{name} epic") for e in out.get("epic", [])]
    tasks = []
    for t in out.get("task", []):
        task = _rename(t, GERMAN_TASK_KEYS, f"{name} aufgabe {t.get('id', '?')}")
        if "status" in task:
            task["status"] = _value(task["status"], GERMAN_STATUS)
        parts = []
        for p in task.get("part", []):
            part = _rename(p, GERMAN_PART_KEYS, f"{name} teil {p.get('id', '?')}")
            if "status" in part:
                part["status"] = _value(part["status"], GERMAN_STATUS)
            parts.append(part)
        task["part"] = parts
        tasks.append(task)
    out["task"] = tasks
    return re.sub(r"^stufe-", "stage-", name), out


def translate_component(name: str, d: Data) -> Data:
    """A German component file with the English keys and values."""
    out = _rename(d, GERMAN_COMPONENT_KEYS, name)
    out["kind"] = _value(out.get("kind"), GERMAN_COMPONENT_KIND)
    provides = []
    for p in out.get("provides", []):
        item = _rename(p, GERMAN_PROVIDES_KEYS, f"{name} bietet {p.get('name', '?')}")
        item["kind"] = _value(item.get("kind"), GERMAN_INTERFACE_KIND)
        provides.append(item)
    out["provides"] = provides
    out["uses"] = [_rename(u, GERMAN_USES_KEYS, f"{name} nutzt") for u in out.get("uses", [])]
    return out


def load_german(root: Path) -> tuple[Plan, dict[str, Component]]:
    """Plan and catalog of a German version (docs/plan/aufgaben, docs/feinentwurf/komponenten)."""
    tasks_dir, catalog_dir = root / GERMAN_TASKS_DIR, root / GERMAN_CATALOG_DIR
    errors: list[str] = []
    stage_docs = []
    paths = sorted(tasks_dir.glob("stufe-*.toml"))
    if not paths:
        raise PlanError(f"{tasks_dir}: no stufe-*.toml")
    for path in paths:
        data = _read_toml(path, errors)
        if data is not None:
            try:
                stage_docs.append(translate_stage_file(path.name, data))
            except PlanError as e:
                errors.append(str(e))
    plan = build_plan(stage_docs, errors)
    if not catalog_dir.is_dir():
        raise PlanError(f"{catalog_dir}: catalog directory is missing")
    errors = []
    components = []
    for path in sorted(catalog_dir.glob("*.toml")):
        data = _read_toml(path, errors)
        if data is not None:
            try:
                components.append((path.name, translate_component(path.name, data)))
            except PlanError as e:
                errors.append(str(e))
    return plan, build_catalog(components, errors)


def load_english(root: Path) -> tuple[Plan, dict[str, Component]]:
    return load(root / TASKS_DIR), load_catalog(root / CATALOG_DIR)


def counts(plan: Plan, catalog: dict[str, Component]) -> dict[str, int]:
    kinds = [n.kind for n in plan.nodes.values()]
    return {
        "stages": len(plan.stages),
        "epics": kinds.count("epic"),
        "tasks": kinds.count("task"),
        "subtasks": kinds.count("part"),
        "components": len(catalog),
        "provides": sum(len(c.provides) for c in catalog.values()),
        "uses": sum(len(c.uses) for c in catalog.values()),
    }


def count_differences(german: dict[str, int], english: dict[str, int]) -> list[str]:
    return [
        f"{k}: German {german[k]}, English {english[k]}" for k in german if german[k] != english[k]
    ]


# ---------------------------------------------------------------- command line


def _fail(errors: Iterable[str]) -> int:
    print("ERROR\n" + "\n".join(errors), file=sys.stderr)
    return 1


DESCRIPTION = "Check the work plan and the component catalog, generate overview and build book."


def _parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="plan.py", description=DESCRIPTION)
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="check; generated files must be up to date")
    gen = sub.add_parser("generate", help="check and write overview and build book")
    gen.add_argument("--check", action="store_true", help="only check that they are current")
    sub.add_parser("ready", help="tasks that may start now")
    sub.add_parser("check-partial", help="check without empty epics, coverage, generated files")
    cmp = sub.add_parser("compare", help="compare the counts with a German version")
    cmp.add_argument("--german", type=Path, required=True, help="root of the German version")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse(sys.argv[1:] if argv is None else argv)
    root: Path = args.root.resolve()
    if args.command == "compare":
        return _compare(root, args.german.resolve())
    if not (root / TASKS_DIR).is_dir():
        print(f"plan.skipped reason=no_tasks_dir path={TASKS_DIR}")
        return 0
    partial = args.command == "check-partial"
    roadmap, design = root / ROADMAP_FILE, root / DESIGN_DIR
    roadmap_text = roadmap.read_text(encoding="utf-8") if roadmap.is_file() else None
    if roadmap_text is None:
        print(f"plan.note stage graph not checked against the roadmap: {ROADMAP_FILE} missing")
    design_docs = design if any(design.glob("[0-9][0-9]-*.md")) else None
    if design_docs is None:
        print(f"plan.note design references not checked: no {DESIGN_DIR}/NN-*.md")
    try:
        plan = load(root / TASKS_DIR)
        errors = check_plan(plan, roadmap_text, design_docs, allow_empty_epics=partial)
        catalog = load_catalog(root / CATALOG_DIR)
        if not errors:
            errors = check_catalog(plan, catalog, design_docs, coverage=not partial)
    except PlanError as e:
        return _fail([str(e)])
    if errors:
        return _fail(errors)
    if args.command == "ready":
        for tid in ready(plan, task_edges(plan)):
            print(tid, plan.nodes[tid].title)
        return 0
    if partial:
        print("ok (partial check): no findings apart from empty epics, coverage, generated files")
        return 0
    generated = {
        root / OVERVIEW_FILE: generate_overview(plan),
        root / BUILD_BOOK_FILE: generate_build_book(plan, catalog),
    }
    if args.command == "generate" and not args.check:
        for path, text in generated.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        print(f"ok: wrote {OVERVIEW_FILE} and {BUILD_BOOK_FILE}")
        return 0
    stale = [
        f"{path.relative_to(root)} is not up to date: run tools/plan/plan.py generate"
        for path, text in generated.items()
        if not path.is_file() or path.read_text(encoding="utf-8") != text
    ]
    if stale:
        return _fail(stale)
    if args.command == "generate":
        print(f"ok: {OVERVIEW_FILE} and {BUILD_BOOK_FILE} are up to date")
        return 0
    c = counts(plan, catalog)
    print(
        f"ok: {c['stages']} stages, {c['epics']} epics, {c['tasks']} tasks, "
        f"{c['subtasks']} subtasks, {c['components']} components"
    )
    return 0


def _compare(root: Path, german_root: Path) -> int:
    try:
        english = counts(*load_english(root))
        german = counts(*load_german(german_root))
    except PlanError as e:
        return _fail([str(e)])
    print("count German English")
    for k, v in german.items():
        print(f"{k} {v} {english[k]}")
    differences = count_differences(german, english)
    if differences:
        return _fail(differences)
    print("ok: German and English versions have the same counts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
