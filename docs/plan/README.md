<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# Guildwork work plan

This folder is the work plan by which the team (people and Claude Code agents) builds the platform. Before the first line of product code, it fixes **what** is built in **which order**, **what** it depends on and **when** it is done. The **how** in detail is in the detailed design ([../design/](../design/README.md)); the **why** is in the architecture ([../architecture/](../architecture/README.md)) with its decisions ([09](../architecture/09-decisions.md)).

Precedence in case of contradictions: architecture decisions (ADR, owner decisions in 09) before the detailed design before the work plan. Whoever finds a contradiction fixes it in the same change at the place with the lower rank or puts it as a question into the task (section 5).

## 1. Structure

| Path | Content | Who changes it |
|---|---|---|
| `tasks/stage-<stage>.toml` | Head of a stage: title and `depends_on_stages` (edges from [08](../architecture/08-roadmap.md) section 3) | only together with 08 |
| `tasks/stage-<stage>.<area>.toml` | Epics, tasks and subtasks of one area of the stage | the team, per task |
| `overview.md` | **generated**: stages, critical path, what is ready now, Epic graphs, order in waves | only `plan.py generate` |
| `tools/plan/plan.py` | Checking and generation (plan, component catalog, overview, build book) | with a test in `tools/plan/test_plan.py` |
| Issue sync (tool with configuration, not in this repo) | Mirror of the plan as GitHub Issues and the way back for the work state (section 8) | the maintainers, with its own test |
| `catalog-and-issues-draft.md` | Decisions on catalog, build book and Issues (KE, GE) | with the Owner |

The TOML files are the only source for the **content** of the plan. The overview, the [build book](../design/build-book.md) and the GitHub Issues are generated from them; `plan.py check` fails if the overview or the build book is not up to date. The **work state** (who works on what, what is done) lives in the Issues and is transferred into the field `status` with `pull` of the Issue sync (section 8).

Where a task docks on is stated in the component catalog ([../design/components/](../design/components/README.md)): each component names what it provides, what it uses and which tasks build it; `plan.py check` checks that every used interface exists and that the using task depends on the providing one.

## 2. Breakdown and IDs

- **Stage:** `R`, `0`, `0b`, `1` to `6`, `7a`, `7`, `8`, `9`, `10` as in [08](../architecture/08-roadmap.md). Core: R, 0, 1, 6, 7a.
- **Epic** `<stage>-Enn`: a self-contained result of a stage (for example "Effect Gateway"). The Epics of all stages are fixed; a new Epic needs a reason in the change.
- **Task** `<stage>-Enn-Tnn`: a unit that an agent builds, tests and submits as one PR in one run (guideline 2 to 16 hours). It has a result, done criteria, sources and dependencies.
- **Subtask** `<stage>-Enn-Tnn-Snn`: a checkable step within the task, as a rule one commit (test first, then code).

IDs are never renumbered or reused. If a task is dropped, it gets `status = "dropped"` with the reason in `note`.

## 3. Fields

```toml
stage = "0"                         # in every file

[[epic]]
id = "0-E09"
title = "Effect Gateway"
goal = "Single write path: ..."     # result in one sentence
sources = ["03 section 2.2", "ADR-11"]
depends_on = ["0-E06", "0-E08"]     # Epics or tasks, also from earlier stages

[[task]]
id = "0-E09-T03"
title = "Outbox with idempotency key"
description = """What exactly is built, with a reference to the detailed design."""
design = ["04-effects-audit-credentials.md#3-outbox"]   # optional
result = "apps/control-plane/src/effects/outbox.ts, migration 0007"
done = ["Test 'same key, one effect' green", "..."]   # checkable, with a command or test name
sources = ["03 section 2.2", "ADR-11"]
depends_on = ["0-E09-T01", "0-E02-T04"]
owner = "agent"                     # agent | owner | agent+owner
estimate_h = 8                      # estimate, unverified
status = "open"                     # open | in_progress | blocked | done | dropped
note = ""                           # optional: reason for blocked/dropped, open question, evidence

  [[task.part]]
  id = "0-E09-T03-S01"
  title = "Test: duplicate key produces one effect"
  done = "Test red because the outbox is missing"
  depends_on = []                   # optional, inside or outside the task
  status = "open"
```

A dependency on an Epic means: all tasks of the Epic. Dependencies may only point to the same stage or to stages that come before it in the stage graph; `plan.py` checks this as well as cycles, missing targets and duplicate IDs. References to the detailed design (the `design` list and mentions of the form `13-x.md section 2.1` in the text of a task) must not point to a section that consists only of "Detailed in" or "Moved to"; a directory `apps/<app>/src/<dir>` in the text of a task must not differ from the directory of a component only in spelling (for example `work-api` instead of `work`). The tool does not check other new directories.

## 4. How the team works through the plan

1. **Choose the next task:** `python3 tools/plan/plan.py ready` lists all tasks whose dependencies are done (run `pull` of the Issue sync first so the status is current); in the project "Guildwork Arbeitsplan" these are the open Issues without open "blocked by". Core stages take precedence; within a stage, the task on the critical path ([overview.md](overview.md) section 2).
2. **Claim:** assign in the Issue and set the label `status: in-arbeit`, in the first comment who (agent run or person) and branch. At most one writer per task; parallel tasks in their own worktrees.
3. **Ready check (Definition of Ready):** sources, detailed design and the component sheets of the own components in the [build book](../design/build-book.md) part 2 read (what it must provide, where it docks on); open questions answered or recorded as a Ruling with a reason in `note`; done criteria checkable. If something essential is missing, label `status: blockiert` with the reason as a comment.
4. **Build:** per subtask, first the test for the desired behavior, then the code, and tick off the subtask in the Issue when its commit is in; decisions and intermediate states as a comment in the Issue; failure paths (what stays stored, audited, logged) with their own test. Fast checks locally as in CI (`make check`).
5. **Done (Definition of Done):** all done criteria with evidence (command and output in the PR description); affected docs adjusted in the same PR (follow-up list: every place that names a changed fact); one independent review; the PR closes the Issue (`Closes #<number>`); afterwards `pull` of the Issue sync and `plan.py generate`. New or changed interfaces and uses are in the catalog in the same PR.
6. **Complete a stage:** The acceptance Epics of each stage (for example `0-E22`, `1-E10`) collect the done criteria from [08](../architecture/08-roadmap.md); done means, per ADR-55: built, suites and Gate A green, Gate B measured and reported. Gate B does not block a following stage.
7. **Change the plan:** Findings while building (missing task, wrong dependency, different estimate, new interface) go as a change to the TOML file or the catalog into the PR that discovers them; `plan.py check` must be green; afterwards `push` of the Issue sync aligns the Issues. Never change content directly in the Issue: the generated block is overwritten on the next `push` (text outside the markers stays).

Minors from reviews are not created as tasks but collected in the backlog ([../architecture/backlog-minors.md](../architecture/backlog-minors.md)) and handled by the next run in the same area.

## 5. Owner tasks

Tasks with `owner = "owner"` concern accounts, money, secrets or steps with external effect (for example creating an organization, making the repo public, a real cloud apply). Agents prepare them (decision sheet with cost, effect, risks) and never carry them out themselves.

The project uses exclusively Claude through the Owner's subscription (owner decision O28 in [DECISIONS.md](../DECISIONS.md) section 3.2). No task requires an account with another model provider, an API key or console access. Functions for other providers, hosters and clouds of stages 8 to 10 are checked against cassettes from the public documentation (detailed design 05 FE-564, 13 FE-1366, 14 FE-1456); live runs with own accounts appear there only as an optional Owner run in the description of a task and are never a done criterion. The exception remains the Azure account of sub-stage 0b, because the control plane of the reference installation runs on Azure (owner decision O1).

## 6. Estimates

`estimate_h` is an estimate in working hours for an agent run with review, unverified. After each stage, the real effort is measured and the estimate of the following stages corrected. Sums and the critical path in the overview are calculated from it and are valid only as far as the estimates are.

## 7. Commands

```sh
python3 tools/plan/plan.py check      # check, also in every PR
python3 tools/plan/plan.py generate   # regenerate the overview
python3 tools/plan/plan.py ready      # what may start now
python3 -m unittest discover -s tools/plan   # tests of the tools
```

The Issue sync (section 8) is not in this repo; its commands are `vorschau` (view Issue texts, without GitHub), `plan` (show what `push` would write), `push` (align Issues, throttled and resumable) and `pull` (fetch the work state from the Issues).

Python 3.11 or newer (for `tomllib`), no further packages; for the sync, the GitHub CLI `gh` with the scopes `repo` and `project`.

## 8. GitHub Issues

The plan is kept as Issues in the product repo so that PRs, Actions and the work log hang in the same place. Decisions: [catalog-and-issues-draft.md](catalog-and-issues-draft.md) GE-1 to GE-10.

| Plan | GitHub |
|---|---|
| Stage | Milestone `Stufe <s>: <title>` and label `stufe: <s>`; core stages additionally `kern` |
| Epic | Issue `[<id>] <title>` with label `typ: epic`; its tasks are sub-issues |
| Task | Issue `[<id>] <title>` with `typ: aufgabe`, `wer: <owner>`, `bereich: <plan file>`; text with description, result, done criteria, subtasks as checkboxes, dependencies, components and docking points, sources |
| Dependency | native dependency "blocked by" (only the transitive reduction) and a list in the text |
| Status `in_progress`, `blocked` | Label `status: in-arbeit` (or assigned), `status: blockiert` |
| Status `done`, `dropped` | Issue closed as completed or as not planned |
| everything | Project "Guildwork Arbeitsplan" in the organization `guildwork-dev` |

- The Issue numbers follow the build order: stages in graph order, per stage first the Epics, then the tasks.
- `push` writes only the block between the markers `plan:anfang` and `plan:ende`, the title, managed labels (`stufe:`, `typ:`, `wer:`, `bereich:`, `kern`), milestone, sub-issues, dependencies and project entries; state, assignment, comments, ticked subtasks and other labels stay; exceptions: a task with `status = "dropped"` in the plan is closed as not planned (and `pull` never takes `dropped` back), an Epic is closed as soon as all its tasks are done or dropped. It is resumable: a second run without a plan change writes nothing.
- Before each write, a leak gate checks all titles and texts against a private term list, local paths and email addresses; a hit aborts before anything is written. Reason: the product repo becomes public at V10, and with it all Issues; V7 therefore also checks Issues, comments and the project.
- Before stage R, the product repo is without a commit (until V10); tasks of stage R are therefore closed by hand with evidence in the comment, only afterwards do PRs close them.

## 9. Key mapping from the German plan

The plan in this repo is English: the keys and values of the TOML files map from the German plan by this fixed table; IDs (`R-E01-T03`, component IDs, interface names) and file name anchors stay unchanged, texts are translated. Source of the table: [design 00 section 4.6](../design/00-codebase-and-conventions.md#46-neutralization-and-translation) (R-E04-T06).

| Place | German | English |
|---|---|---|
| Files | `docs/plan/aufgaben/stufe-<s>[.<bereich>].toml`, `uebersicht.md`, `docs/feinentwurf/komponenten/`, `baubuch.md` | `docs/plan/tasks/stage-<s>[.<area>].toml`, `overview.md`, `docs/design/components/`, `build-book.md` |
| Stage | `stufe`, `titel`, `haengt_an` | `stage`, `title`, `depends_on_stages` |
| Epic | `epic`, `id`, `titel`, `ziel`, `quellen`, `abhaengig_von` | `epic`, `id`, `title`, `goal`, `sources`, `depends_on` |
| Task | `aufgabe`, `beschreibung`, `feinentwurf`, `ergebnis`, `fertig`, `wer`, `schaetzung_h`, `status`, `notiz`, `teil` | `task`, `description`, `design`, `result`, `done`, `owner`, `estimate_h`, `status`, `note`, `part` |
| Values `wer` | `agent`, `owner`, `agent+owner` | unchanged |
| Values `status` | `offen`, `in_arbeit`, `blockiert`, `fertig`, `entfällt` | `open`, `in_progress`, `blocked`, `done`, `dropped` |
| Component | `titel`, `art`, `pfad`, `paket`, `stufe`, `zweck`, `feinentwurf`, `gebaut_von`, `bietet`, `nutzt` | `title`, `kind`, `path`, `package`, `stage`, `purpose`, `design`, `built_by`, `provides`, `uses` |
| Interface | `name`, `art`, `titel`, `definiert_in`, `ab_aufgabe`; `schnittstelle`, `wozu` | `name`, `kind`, `title`, `defined_in`, `from_task`; `interface`, `purpose` |
| Values `art` (component) | `paket`, `programm`, `rolle`, `plugin`, `treiber`, `service`, `eval`, `auslieferung`, `werkzeug`, `ui`, `prozess` | `package`, `program`, `role`, `plugin`, `driver`, `service`, `eval`, `delivery`, `tool`, `ui`, `process` |
| Values `art` (interface) | `ts-api`, `http`, `mcp-tool`, `event`, `tabelle`, `queue`, `cli`, `konfig`, `vertrag`, `datei`, `ui`, `prompt`, `metrik` | `ts-api`, `http`, `mcp-tool`, `event`, `table`, `queue`, `cli`, `config`, `contract`, `file`, `ui`, `prompt`, `metric` |
