# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
"""Tests for tools/plan/plan.py.

Run: python -m unittest discover -s tools/plan (from the repository root).
Every test builds its plan, catalog and design files in a temporary directory.
"""

from __future__ import annotations

import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.plan import plan as p

REPO_ROOT = Path(__file__).resolve().parents[2]

ROADMAP = """
```mermaid
flowchart LR
  SR[R Repo] --> S0[0 Foundation]
  S0 --> S1[1 Reviewer]
```
"""

R = """
stage = "R"
title = "Repo"
depends_on_stages = []
[[epic]]
id = "R-E01"
title = "Scaffold"
goal = "Repo stands"
sources = ["12 section 6"]
[[task]]
id = "R-E01-T01"
title = "Scaffold"
description = "x"
result = "Makefile"
done = ["make check green"]
sources = ["12"]
estimate_h = 4
"""

ZERO = """
stage = "0"
title = "Foundation"
depends_on_stages = ["R"]
[[epic]]
id = "0-E01"
title = "DB"
goal = "Schema"
sources = ["08"]
depends_on = ["R-E01"]
[[task]]
id = "0-E01-T01"
title = "Schema"
description = "x"
result = "migrations/"
done = ["Migration runs"]
sources = ["08"]
estimate_h = 8
[[task.part]]
id = "0-E01-T01-S01"
title = "Tables"
done = "DDL there"
[[task]]
id = "0-E01-T02"
title = "Repos"
description = "x"
result = "db/"
done = ["Tests green"]
sources = ["08"]
estimate_h = 6
depends_on = ["0-E01-T01"]
"""

ONE = """
stage = "1"
title = "Reviewer"
depends_on_stages = ["0"]
[[epic]]
id = "1-E01"
title = "Reviewer"
goal = "Review"
sources = ["02"]
[[task]]
id = "1-E01-T01"
title = "Gate"
description = "x"
result = "gate.ts"
done = ["Test"]
sources = ["02"]
estimate_h = 5
depends_on = ["0-E01"]
"""

DB = """
id = "db"
title = "Database"
kind = "package"
path = "packages/db/"
stage = "0"
purpose = "Schema"
design = ["01-db.md#2-schema"]
built_by = ["0-E01-T01", "0-E01-T02"]
[[provides]]
name = "migrator"
kind = "ts-api"
title = "Migrator"
defined_in = "01-db.md#21-migrator"
from_task = "0-E01-T01"
"""

GATE = """
id = "gate"
title = "Gate"
kind = "service"
path = "services/reviewer/"
stage = "1"
purpose = "Gate"
design = ["01-db.md"]
built_by = ["1-E01-T01"]
[[uses]]
interface = "db/migrator"
from_task = "1-E01-T01"
purpose = "Tables"
"""

REPO = """
id = "repo"
title = "Repo"
kind = "tool"
path = "."
stage = "R"
purpose = "Scaffold"
design = ["01-db.md"]
built_by = ["R-E01-T01"]
"""

# The same plan and catalog with the German keys and values of the ops repo
# (detailed design 00 section 4.6), read by `compare --german`.
R_DE = """
stufe = "R"
titel = "Repo"
haengt_an = []
[[epic]]
id = "R-E01"
titel = "Geruest"
ziel = "Repo steht"
quellen = ["12 Abschnitt 6"]
[[aufgabe]]
id = "R-E01-T01"
titel = "Geruest"
beschreibung = "x"
ergebnis = "Makefile"
fertig = ["make check gruen"]
quellen = ["12"]
schaetzung_h = 4
status = "fertig"
"""

ZERO_DE = """
stufe = "0"
titel = "Fundament"
haengt_an = ["R"]
[[epic]]
id = "0-E01"
titel = "DB"
ziel = "Schema"
quellen = ["08"]
abhaengig_von = ["R-E01"]
[[aufgabe]]
id = "0-E01-T01"
titel = "Schema"
beschreibung = "x"
ergebnis = "migrations/"
fertig = ["Migration laeuft"]
quellen = ["08"]
schaetzung_h = 8
feinentwurf = ["01-db.md"]
status = "in_arbeit"
notiz = "x"
[[aufgabe.teil]]
id = "0-E01-T01-S01"
titel = "Tabellen"
fertig = "DDL da"
status = "offen"
[[aufgabe]]
id = "0-E01-T02"
titel = "Repos"
beschreibung = "x"
ergebnis = "db/"
fertig = ["Tests gruen"]
quellen = ["08"]
schaetzung_h = 6
abhaengig_von = ["0-E01-T01"]
status = "entfällt"
"""

ONE_DE = """
stufe = "1"
titel = "Reviewer"
haengt_an = ["0"]
[[epic]]
id = "1-E01"
titel = "Reviewer"
ziel = "Review"
quellen = ["02"]
[[aufgabe]]
id = "1-E01-T01"
titel = "Gate"
beschreibung = "x"
ergebnis = "gate.ts"
fertig = ["Test"]
quellen = ["02"]
schaetzung_h = 5
abhaengig_von = ["0-E01"]
wer = "agent+owner"
status = "blockiert"
"""

DB_DE = """
id = "db"
titel = "Datenbank"
art = "paket"
pfad = "packages/db/"
paket = "@guildwork/db"
stufe = "0"
zweck = "Schema"
bereich = "Daten"
feinentwurf = ["01-db.md#2-schema"]
gebaut_von = ["0-E01-T01", "0-E01-T02"]
[[bietet]]
name = "migrator"
art = "tabelle"
titel = "Migrator"
definiert_in = "01-db.md#21-migrator"
ab_aufgabe = "0-E01-T01"
"""

GATE_DE = """
id = "gate"
titel = "Gate"
art = "service"
pfad = "services/reviewer/"
stufe = "1"
zweck = "Gate"
feinentwurf = ["01-db.md"]
gebaut_von = ["1-E01-T01"]
[[nutzt]]
schnittstelle = "db/migrator"
ab_aufgabe = "1-E01-T01"
wozu = "Tabellen"
"""

REPO_DE = """
id = "repo"
titel = "Repo"
art = "werkzeug"
pfad = "."
stufe = "R"
zweck = "Geruest"
feinentwurf = ["01-db.md"]
gebaut_von = ["R-E01-T01"]
"""


def write(directory: Path, files: dict[str, str]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (directory / name).write_text(textwrap.dedent(content), encoding="utf-8")
    return directory


class TempMixin(unittest.TestCase):
    def tmp(self) -> Path:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        return d

    def load(self, **files: str) -> p.Plan:
        d = write(self.tmp(), {f"stage-{name}.toml": text for name, text in files.items()})
        return p.load(d)

    def catalog(self, **files: str) -> dict[str, p.Component]:
        d = write(self.tmp(), {f"{name}.toml": text for name, text in files.items()})
        return p.load_catalog(d)

    def design(self) -> Path:
        return write(self.tmp(), {"01-db.md": "## 2. Schema\n### 2.1 Migrator\n"})

    def full(self) -> p.Plan:
        return self.load(R=R, **{"0": ZERO, "1": ONE})


class PlanTest(TempMixin):
    def test_valid_plan(self) -> None:
        plan = self.full()
        self.assertEqual(p.check_plan(plan, ROADMAP), [])
        edges = p.task_edges(plan)
        self.assertEqual(edges["0-E01-T01"], {"R-E01-T01"})  # epic dependency inherited
        self.assertEqual(edges["1-E01-T01"], {"0-E01-T01", "0-E01-T02"})  # epic as target
        self.assertEqual(p.ready(plan, edges), ["R-E01-T01"])
        hours, path = p.critical_path(plan, edges, {"R", "0", "1"})
        self.assertEqual(
            (hours, path), (23.0, ["R-E01-T01", "0-E01-T01", "0-E01-T02", "1-E01-T01"])
        )
        text = p.generate_overview(plan)
        self.assertEqual(text, p.generate_overview(plan))
        self.assertIn("`R-E01-T01` Scaffold", text)

    def test_overview_structure(self) -> None:
        text = p.generate_overview(self.full())
        for heading in (
            "# Work plan: overview",
            "## 1. Stages",
            "## 2. Critical path",
            "## 3. Ready now",
            "## 4. Epics per stage",
            "### Stage 0: Foundation",
            "## 5. Order (topological, across all stages)",
        ):
            self.assertIn(heading + "\n", text)
        self.assertIn("`tools/plan/plan.py generate`", text)
        self.assertIn("| 0 | Foundation | R | yes | 1 | 2 | 1 | 14 | 0 of 2 |", text)
        self.assertIn("| 0-E01-T02 | Repos | 0-E01-T01 | agent | 6 | open |", text)
        self.assertIn("1. `R-E01-T01`", text)

    def test_generation_independent_of_hash_seed(self) -> None:
        code = (
            "import sys;from pathlib import Path;from tools.plan import plan as p;"
            "sys.stdout.write(p.generate_overview(p.load(Path(sys.argv[1]))))"
        )
        same = ZERO.replace('depends_on = ["0-E01-T01"]', "depends_on = []")
        same += (
            '[[task]]\nid = "0-E01-T03"\ntitle = "End"\ndescription = "x"\nresult = "x"\n'
            'done = ["x"]\nsources = ["08"]\nestimate_h = 1\n'
            'depends_on = ["0-E01-T01", "0-E01-T02"]\n'
        )
        same = same.replace("estimate_h = 6", "estimate_h = 8")
        d = write(self.tmp(), {"stage-R.toml": R, "stage-0.toml": same})
        outputs = {
            subprocess.run(  # noqa: S603
                [sys.executable, "-c", code, str(d)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
                env={**os.environ, "PYTHONHASHSEED": str(seed)},
            ).stdout
            for seed in range(6)
        }
        self.assertEqual(len(outputs), 1)

    def test_duplicate_id(self) -> None:
        with self.assertRaisesRegex(p.PlanError, "duplicate"):
            self.load(R=R + R.split("[[task]]")[1].join(["[[task]]", ""]))

    def test_missing_dependency(self) -> None:
        plan = self.load(R=R, **{"0": ZERO.replace('["0-E01-T01"]', '["0-E01-T09"]')})
        self.assertIn(
            "stage-0.toml: 0-E01-T02 depends on 0-E01-T09, which does not exist",
            p.check_plan(plan),
        )

    def test_cycle(self) -> None:
        cycle = ZERO.replace("estimate_h = 8", 'estimate_h = 8\ndepends_on = ["0-E01-T02"]')
        plan = self.load(R=R, **{"0": cycle})
        self.assertTrue(any("cycle" in f for f in p.check_plan(plan)))

    def test_dependency_against_stage_graph(self) -> None:
        # stage R must not depend on stage 0
        r = R.replace("estimate_h = 4", 'estimate_h = 4\ndepends_on = ["0-E01-T01"]')
        plan = self.load(R=r, **{"0": ZERO})
        self.assertTrue(any("not before stage R" in f for f in p.check_plan(plan)))

    def test_stage_graph_against_roadmap(self) -> None:
        plan = self.load(R=R, **{"0": ZERO, "1": ONE.replace('["0"]', '["R"]')})
        errors = p.check_plan(plan, ROADMAP)
        self.assertIn("stage-1.toml: depends_on_stages lacks 0 (edge in 08-roadmap.md)", errors)
        self.assertIn("stage-1.toml: depends_on_stages R is not in 08-roadmap.md", errors)

    def test_status_before_dependency(self) -> None:
        plan = self.load(
            R=R, **{"0": ZERO.replace("estimate_h = 6", 'estimate_h = 6\nstatus = "done"')}
        )
        self.assertTrue(any("is done, but" in f for f in p.check_plan(plan)))

    def test_status_values(self) -> None:
        with self.assertRaisesRegex(p.PlanError, "status = offen not in"):
            self.load(R=R.replace("estimate_h = 4", 'estimate_h = 4\nstatus = "offen"'))
        plan = self.load(R=R.replace("estimate_h = 4", 'estimate_h = 4\nstatus = "dropped"'))
        self.assertEqual(plan.nodes["R-E01-T01"].status, "dropped")

    def test_required_fields(self) -> None:
        with self.assertRaisesRegex(p.PlanError, "done"):
            self.load(R=R.replace('done = ["make check green"]', "done = []"))
        with self.assertRaisesRegex(p.PlanError, "estimate_h"):
            self.load(R=R.replace("estimate_h = 4", "estimate_h = 0"))
        with self.assertRaisesRegex(p.PlanError, "R-Enn-Tnn"):
            self.load(R=R.replace('id = "R-E01-T01"', 'id = "R-E1-T1"'))
        with self.assertRaisesRegex(p.PlanError, "owner = nobody not in"):
            self.load(R=R.replace("estimate_h = 4", 'estimate_h = 4\nowner = "nobody"'))

    def test_area_files(self) -> None:
        head = 'stage = "0"\ntitle = "Foundation"\ndepends_on_stages = ["R"]\n'
        part = ZERO.replace('title = "Foundation"\ndepends_on_stages = ["R"]\n', "")
        plan = self.load(R=R, **{"0": head, "0.db": part})
        self.assertEqual(p.check_plan(plan, None), [])
        self.assertEqual(plan.nodes["0-E01-T01"].file, "stage-0.db.toml")
        with self.assertRaisesRegex(p.PlanError, "only in stage-0.toml"):
            self.load(R=R, **{"0": head, "0.db": ZERO})
        with self.assertRaisesRegex(p.PlanError, "has no file stage-0.toml"):
            self.load(R=R, **{"0.db": part})

    def test_design_reference(self) -> None:
        design = write(self.tmp(), {"02-x.md": "## Section\n"})
        r = R.replace(
            "estimate_h = 4", 'estimate_h = 4\ndesign = ["02-x.md#section", "09-missing.md"]'
        )
        errors = p.check_plan(self.load(R=r), None, design)
        self.assertEqual(
            errors,
            ["stage-R.toml: R-E01-T01 refers to docs/design/09-missing.md, the file is missing"],
        )

    def test_epic_without_task(self) -> None:
        plan = self.load(
            R=R + '\n[[epic]]\nid = "R-E02"\ntitle = "empty"\ngoal = "x"\nsources = ["12"]\n'
        )
        self.assertIn("stage-R.toml: epic R-E02 has no task", p.check_plan(plan))
        self.assertEqual(p.check_plan(plan, allow_empty_epics=True), [])

    def test_anchor(self) -> None:
        self.assertEqual(
            p.anchor("### 4.4 Orchestrator and `Run` automaton"),
            "44-orchestrator-and-run-automaton",
        )
        self.assertEqual(
            p.anchor("## 2.14 Stage 9: Breadth and hardening (short)"),
            "214-stage-9-breadth-and-hardening-short",
        )
        self.assertEqual(p.anchor("### [Link](x.md) A/B"), "link-ab")
        design = write(
            self.tmp(),
            {"02-x.md": "# T\n## 1. Purpose\n## 1. Purpose\n```\n## no heading\n```\n"},
        )
        self.assertEqual(p.anchors_of(design / "02-x.md"), {"t", "1-purpose", "1-purpose-1"})
        r = R.replace(
            "estimate_h = 4",
            'estimate_h = 4\ndesign = ["02-x.md#1-purpose", "02-x.md#no-heading"]',
        )
        errors = p.check_plan(self.load(R=r), None, design)
        self.assertEqual(
            errors,
            [
                "stage-R.toml: R-E01-T01 refers to docs/design/02-x.md#no-heading, "
                "the anchor is missing"
            ],
        )

    def test_move_notice(self) -> None:
        design = write(
            self.tmp(),
            {
                "12-old.md": "## 2. Modules\n### 2.8 Jira\n\n"
                "Detailed in [13](13-new.md) section 2.1.\n"
                "### 2.9 Provider\n\nMoved to 13.\n### 2.10 Real\n\nContent.\n"
                "```\n## 2.11 in code\n```\n"
            },
        )
        r = R.replace(
            "estimate_h = 4",
            'estimate_h = 4\ndesign = ["12-old.md#28-jira", "12-old.md#210-real"]',
        )
        r = r.replace(
            'description = "x"',
            'description = "after 12-old.md sections 2.9 and 2.10, 12-old.md section 2"',
        )
        errors = p.check_plan(self.load(R=r), None, design)
        self.assertEqual(
            errors,
            [
                f"stage-R.toml: R-E01-T01 refers to docs/design/12-old.md#28-jira, {p.MOVE_REASON}",
                f"stage-R.toml: R-E01-T01 names 12-old.md section 2.9, {p.MOVE_REASON}",
            ],
        )

    def test_real_stage_ids(self) -> None:
        self.assertEqual(p.STAGES[0], "R")
        self.assertEqual(p.sort_key("7a-E02-T03"), (p.STAGES.index("7a"), [2, 3]))


class CatalogTest(TempMixin):
    def test_catalog_valid(self) -> None:
        plan = self.full()
        cat = self.catalog(db=DB, gate=GATE, repo=REPO)
        self.assertEqual(p.check_catalog(plan, cat, self.design()), [])
        text = p.generate_build_book(plan, cat)
        self.assertIn("db/migrator", text)
        self.assertEqual(text, p.generate_build_book(plan, cat))

    def test_generated_files_carry_the_spdx_header(self) -> None:
        # make licenses requires the header in the first lines of every Markdown file
        header = (
            "<!--\nSPDX-License-Identifier: Apache-2.0\n"
            "SPDX-FileCopyrightText: The Guildwork Authors\n-->\n"
        )
        plan = self.full()
        self.assertTrue(p.generate_overview(plan).startswith(header))
        cat = self.catalog(db=DB, gate=GATE, repo=REPO)
        self.assertTrue(p.generate_build_book(plan, cat).startswith(header))

    def test_build_book_structure(self) -> None:
        text = p.generate_build_book(self.full(), self.catalog(db=DB, gate=GATE, repo=REPO))
        for heading in (
            "# Build book: Guildwork in build order",
            "## Part 1: Stage by stage",
            "### Stage 0: Foundation",
            "## Part 2: Component sheets",
            "### K `db`",
        ):
            self.assertIn(heading + "\n", text)
        self.assertIn("**New:**", text)
        self.assertIn("**Ready from:**", text)
        self.assertIn("| [`db`](#k-db) | package | `packages/db/` | Schema |", text)
        self.assertIn("| `db/migrator` Migrator | ts-api | 0-E01-T01 | `gate` (1-E01-T01) |", text)
        self.assertIn("**Database** (package, from stage 0). Schema", text)
        self.assertIn("- Built by: 0-E01-T01, 0-E01-T02", text)
        self.assertIn("| `db/migrator` | [`db`](#k-db) | 1-E01-T01 | Tables |", text)

    def test_catalog_order(self) -> None:
        # gate uses the migrator in a task that does not depend on the providing task
        plan = self.load(R=R, **{"0": ZERO, "1": ONE.replace('depends_on = ["0-E01"]', "")})
        errors = p.check_catalog(plan, self.catalog(db=DB, gate=GATE, repo=REPO), self.design())
        self.assertIn(
            "gate.toml: uses db/migrator in 1-E01-T01, which does not depend on 0-E01-T01 "
            "(provided there)",
            errors,
        )

    def test_catalog_errors(self) -> None:
        plan = self.full()
        broken = GATE.replace('"db/migrator"', '"db/missing"')
        errors = p.check_catalog(plan, self.catalog(db=DB, gate=broken, repo=REPO), self.design())
        self.assertIn("gate.toml: uses db/missing, the interface does not exist", errors)
        without = DB.replace('"0-E01-T01", "0-E01-T02"', '"0-E01-T01"')
        errors = p.check_catalog(
            plan, self.catalog(db=without, gate=GATE, repo=REPO), self.design()
        )
        self.assertIn("task 0-E01-T02 belongs to no component (built_by)", errors)
        anchor = DB.replace("#21-migrator", "#99-gone")
        errors = p.check_catalog(plan, self.catalog(db=anchor, gate=GATE, repo=REPO), self.design())
        self.assertIn(
            "db.toml: db/migrator defined_in 01-db.md#99-gone, the anchor is missing", errors
        )
        foreign = DB.replace('from_task = "0-E01-T01"', 'from_task = "R-E01-T01"')
        errors = p.check_catalog(
            plan, self.catalog(db=foreign, gate=GATE, repo=REPO), self.design()
        )
        self.assertIn("db.toml: db/migrator from_task R-E01-T01 is not in built_by", errors)
        with self.assertRaisesRegex(p.PlanError, "file name"):
            self.catalog(other=DB)
        with self.assertRaisesRegex(p.PlanError, "kind = paket not in"):
            self.catalog(db=DB.replace('kind = "package"', 'kind = "paket"'))
        with self.assertRaisesRegex(p.PlanError, "kind = tabelle not in"):
            self.catalog(db=DB.replace('kind = "ts-api"', 'kind = "tabelle"'))

    def test_path_spelling(self) -> None:
        r = R.replace(
            'result = "Makefile"',
            'result = "apps/control-plane/src/work-api/x.ts, apps/control-plane/src/new/y.ts"',
        )
        plan = self.load(R=r, **{"0": ZERO, "1": ONE})
        work = REPO.replace('id = "repo"', 'id = "work"').replace(
            'path = "."', 'path = "apps/control-plane/src/work/"'
        )
        errors = p.check_catalog(
            plan, self.catalog(db=DB, gate=GATE, repo=REPO, work=work), self.design()
        )
        self.assertIn(
            "stage-R.toml: R-E01-T01 names apps/control-plane/src/work-api/, "
            "the catalog writes apps/control-plane/src/work/",
            errors,
        )
        self.assertFalse([f for f in errors if "src/new/" in f])


class GermanTest(TempMixin):
    """The German version of the ops repo, read through the fixed key mapping."""

    def german_root(self, **overrides: str) -> Path:
        root = self.tmp()
        plan = {"stufe-R.toml": R_DE, "stufe-0.toml": ZERO_DE, "stufe-1.toml": ONE_DE}
        cat = {"db.toml": DB_DE, "gate.toml": GATE_DE, "repo.toml": REPO_DE}
        for name, text in overrides.items():
            if name in plan:
                plan[name] = text
            else:
                cat[name] = text
        write(root / "docs/plan/aufgaben", plan)
        write(root / "docs/feinentwurf/komponenten", cat)
        return root

    def english_root(self) -> Path:
        root = self.tmp()
        write(
            root / "docs/plan/tasks",
            {"stage-R.toml": R, "stage-0.toml": ZERO, "stage-1.toml": ONE},
        )
        write(
            root / "docs/design/components", {"db.toml": DB, "gate.toml": GATE, "repo.toml": REPO}
        )
        return root

    def test_german_mapping(self) -> None:
        plan, cat = p.load_german(self.german_root())
        self.assertEqual(plan.stages["0"]["depends_on_stages"], ["R"])
        self.assertEqual(plan.nodes["R-E01-T01"].status, "done")
        self.assertEqual(plan.nodes["0-E01-T01"].status, "in_progress")
        self.assertEqual(plan.nodes["0-E01-T01"].design, ["01-db.md"])
        self.assertEqual(plan.nodes["0-E01-T01-S01"].status, "open")
        self.assertEqual(plan.nodes["0-E01-T02"].status, "dropped")
        self.assertEqual(plan.nodes["1-E01-T01"].status, "blocked")
        self.assertEqual(plan.nodes["1-E01-T01"].owner, "agent+owner")
        self.assertEqual(plan.nodes["0-E01"].depends_on, ["R-E01"])
        self.assertEqual(cat["db"].kind, "package")
        self.assertEqual(cat["db"].package, "@guildwork/db")
        self.assertEqual(cat["db"].area, "Daten")
        self.assertEqual(cat["db"].provides[0]["kind"], "table")
        self.assertEqual(cat["db"].provides[0]["defined_in"], "01-db.md#21-migrator")
        self.assertEqual(cat["gate"].uses[0]["interface"], "db/migrator")
        self.assertEqual(cat["repo"].kind, "tool")

    def test_german_value_maps_complete(self) -> None:
        self.assertEqual(sorted(p.GERMAN_STATUS.values()), sorted(p.STATUS))
        self.assertEqual(sorted(p.GERMAN_COMPONENT_KIND.values()), sorted(p.COMPONENT_KINDS))
        self.assertEqual(sorted(p.GERMAN_INTERFACE_KIND.values()), sorted(p.INTERFACE_KINDS))

    def test_german_unknown_key(self) -> None:
        root = self.german_root(**{"stufe-R.toml": R_DE + 'unbekannt = "x"\n'})
        with self.assertRaisesRegex(
            p.PlanError, "stufe-R.toml aufgabe R-E01-T01: unknown German key 'unbekannt'"
        ):
            p.load_german(root)

    def test_counts_equal(self) -> None:
        en = p.counts(*p.load_english(self.english_root()))
        de = p.counts(*p.load_german(self.german_root()))
        self.assertEqual(en, de)
        self.assertEqual(
            en,
            {
                "stages": 3,
                "epics": 3,
                "tasks": 4,
                "subtasks": 1,
                "components": 3,
                "provides": 1,
                "uses": 1,
            },
        )

    def test_counts_differ(self) -> None:
        extra = (
            GATE_DE
            + '[[nutzt]]\nschnittstelle = "db/migrator"\nab_aufgabe = "1-E01-T01"\nwozu = "y"\n'
        )
        de = p.counts(*p.load_german(self.german_root(**{"gate.toml": extra})))
        en = p.counts(*p.load_english(self.english_root()))
        self.assertEqual(p.count_differences(de, en), ["uses: German 2, English 1"])

    def test_compare_command(self) -> None:
        code, out, err = run_main(
            ["--root", str(self.english_root()), "compare", "--german", str(self.german_root())]
        )
        self.assertEqual((code, err), (0, ""))
        self.assertIn("ok: German and English versions have the same counts", out)
        self.assertIn("tasks 4", out)
        extra_epic = ONE_DE.replace(
            "[[aufgabe]]",
            '[[epic]]\nid = "1-E02"\ntitel = "x"\nziel = "x"\nquellen = ["x"]\n[[aufgabe]]',
            1,
        )
        code, out, err = run_main(
            [
                "--root",
                str(self.english_root()),
                "compare",
                "--german",
                str(self.german_root(**{"stufe-1.toml": extra_epic})),
            ]
        )
        self.assertEqual(code, 1)
        self.assertIn("epics: German 4, English 3", err)


def run_main(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = p.main(argv)
    return code, out.getvalue(), err.getvalue()


class MainTest(TempMixin):
    def root(self, with_design: bool = True) -> Path:
        root = self.tmp()
        write(
            root / "docs/plan/tasks",
            {"stage-R.toml": R, "stage-0.toml": ZERO, "stage-1.toml": ONE},
        )
        write(
            root / "docs/design/components", {"db.toml": DB, "gate.toml": GATE, "repo.toml": REPO}
        )
        if with_design:
            write(root / "docs/design", {"01-db.md": "## 2. Schema\n### 2.1 Migrator\n"})
        write(root / "docs/architecture", {"08-roadmap.md": ROADMAP})
        return root

    def test_no_tasks_directory(self) -> None:
        root = self.tmp()
        code, out, err = run_main(["--root", str(root), "check"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("plan.skipped reason=no_tasks_dir path=docs/plan/tasks", out)

    def test_empty_tasks_directory_fails(self) -> None:
        root = self.tmp()
        (root / "docs/plan/tasks").mkdir(parents=True)
        code, _, err = run_main(["--root", str(root), "check"])
        self.assertEqual(code, 1)
        self.assertIn("no stage-*.toml", err)

    def test_missing_catalog_fails(self) -> None:
        root = self.root()
        shutil.rmtree(root / "docs/design/components")
        code, _, err = run_main(["--root", str(root), "check"])
        self.assertEqual(code, 1)
        self.assertIn("docs/design/components", err)

    def test_generate_then_check(self) -> None:
        root = self.root()
        code, out, _ = run_main(["--root", str(root), "check"])
        self.assertEqual(code, 1)
        code, out, _ = run_main(["--root", str(root), "generate", "--check"])
        self.assertEqual(code, 1)
        self.assertFalse((root / "docs/plan/overview.md").exists())
        code, out, _ = run_main(["--root", str(root), "generate"])
        self.assertEqual(code, 0)
        self.assertIn("docs/plan/overview.md", out)
        self.assertTrue((root / "docs/design/build-book.md").is_file())
        code, out, err = run_main(["--root", str(root), "check"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("ok: 3 stages, 3 epics, 4 tasks, 1 subtasks", out)
        code, out, _ = run_main(["--root", str(root), "generate", "--check"])
        self.assertEqual(code, 0)
        (root / "docs/design/build-book.md").write_text("stale\n", encoding="utf-8")
        code, _, err = run_main(["--root", str(root), "check"])
        self.assertEqual(code, 1)
        self.assertIn("build-book.md is not up to date", err)

    def test_check_finds_design_reference(self) -> None:
        root = self.root()
        bad = DB.replace("#21-migrator", "#99-gone")
        write(root / "docs/design/components", {"db.toml": bad})
        code, _, err = run_main(["--root", str(root), "check"])
        self.assertEqual(code, 1)
        self.assertIn(
            "db.toml: db/migrator defined_in 01-db.md#99-gone, the anchor is missing", err
        )

    def test_design_references_skipped_without_design_docs(self) -> None:
        root = self.root(with_design=False)
        bad = DB.replace("#21-migrator", "#99-gone")
        write(root / "docs/design/components", {"db.toml": bad})
        run_main(["--root", str(root), "generate"])
        code, out, err = run_main(["--root", str(root), "check"])
        self.assertEqual((code, err), (0, ""))
        self.assertIn("plan.note design references not checked", out)

    def test_ready_and_partial(self) -> None:
        root = self.root()
        code, out, _ = run_main(["--root", str(root), "ready"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "R-E01-T01 Scaffold\n")
        code, out, _ = run_main(["--root", str(root), "check-partial"])
        self.assertEqual(code, 0)
        self.assertIn("ok (partial check)", out)

    def test_cli_runs_as_script(self) -> None:
        root = self.tmp()
        result = subprocess.run(  # noqa: S603
            [sys.executable, str(REPO_ROOT / "tools/plan/plan.py"), "--root", str(root), "check"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("plan.skipped", result.stdout)


if __name__ == "__main__":
    unittest.main()
