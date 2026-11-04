<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# Draft: component catalog, build book and work plan as GitHub Issues

As of 2026-11-01. Assignment from the Owner (voice messages 2026-10-31, paraphrased): every planned service fully written down, the whole tool described once in build order, every agent knows where it docks on, what it builds and what it must look like, so that in the end nothing is missing and nothing fails to fit together; in addition the whole plan with milestones, labels, dependencies and a project as GitHub Issues in the product repo, on which the team works and documents.

## 1. Goal and done criterion

| Goal | Done when |
|---|---|
| K1 Every component (package, program, role, plugin, driver, service, eval part, delivery, tool) has a component sheet: purpose, path, stage, what it provides, what it uses, who builds it | `components/*.toml` complete, `plan.py check` green |
| K2 Docking points fit together mechanically | `plan.py check` checks: every used interface exists; the using task depends (transitively) on the task that provides the interface; every interface points to an existing heading in the detailed design |
| K3 Nothing is missing | every task belongs to at least one component; every component has tasks; every reference to the detailed design (including anchors) exists |
| K4 The tool in build order | generated `docs/design/build-book.md`: per stage in graph order, which components are created, which interfaces are available from which task on, who docks on; in addition the component sheet per component |
| K5 All stages described at the same depth | the previously brief parts (stages 8 to 10) and every gap the catalog uncovers brought to the depth of stages 0 and 1 in the detailed design (the ten points from [README](../design/README.md) section 3) |
| G1 Plan as Issues | `push` of the Issue sync creates milestones, labels, Epic and task Issues with sub-issues, native dependencies and the project, idempotently; a second run changes nothing |
| G2 Work state comes back | `pull` of the Issue sync writes the status from the Issues into the TOML files; `plan.py generate` afterwards |

## 2. Decisions

| No. | Decision | Reason | Rejected |
|---|---|---|---|
| KE-1 | The catalog is machine-readable (`docs/design/components/<component>.toml`), one file per component | parallel work without conflicts; `plan.py` can check it | prose table: not checkable |
| KE-2 | Interfaces have a project-wide unique ID `<component>/<name>` and exactly one provider | one home per interface | interfaces only in prose |
| KE-3 | The check "fits together" is the dependency in the plan: whoever uses an interface in task X must depend on the task that provides it | this way every missing or wrongly ordered dependency surfaces before building | a second order next to the plan |
| KE-4 | The build book is generated, never written by hand | copies are generated, not rewritten | a handwritten overall description that goes stale |
| KE-5 | References to the detailed design are checked down to the anchor (GitHub anchor rule) | a dead anchor is a gap | file check only |
| GE-1 | The TOML files in the ops repo remain the only source for **content** (title, description, done criteria, dependencies); the Issues are generated from them | one source, checked with `plan.py` | maintaining content in Issues: no check for cycles and order |
| GE-2 | The **work state** lives in the Issues (open, assigned, label `status: in-arbeit` or `status: blockiert`, closed as completed or as not planned) and the work log in their comments; `pull` transfers it into the field `status`. Exceptions: `dropped` is a plan decision (`push` closes the Issue as not planned, `pull` never takes it back), and `push` closes an Epic as soon as all its tasks are done or dropped (Red Team 2026-11-01, Major 1) | the team works there, PRs and Actions link to each other there | maintaining the status twice by hand |
| GE-3 | Mapping: stage = milestone; Epic = Issue with the tasks as sub-issues; task = Issue; subtask = checkbox in the task Issue; dependency between tasks = native dependency "blocked by" (only the transitive reduction) and as a list in the text | subtasks are commits, not separate work units; the reduction keeps the dependencies readable and the write calls few | subtasks as Issues (around 2,300 additional Issues) |
| GE-4 | Labels: `stufe: <s>`, `typ: epic`, `typ: aufgabe`, `wer: agent`, `wer: owner`, `wer: agent+owner`, `kern`, `bereich: <area>`, `status: in-arbeit`, `status: blockiert` | filters in the project and in search | fields in the project per Issue (three more write calls each) |
| GE-5 | One project (GitHub Projects) "Guildwork Arbeitsplan" at the owner of the product repo (since 2026-11-01 the organization `guildwork-dev`) with all Issues; views by milestone and labels | overview across stages | custom fields: cost write calls without new information |
| GE-6 | The generated part of an Issue sits between markers; `push` changes only it, never comments and state | the work log stays untouched | creating the Issue anew on change |
| GE-7 | Before every write call, a leak gate runs over title and text (terms from the private list in the ops repo, local paths, email addresses); a hit aborts the run | the product repo becomes public at V10, and with it all Issues | Issues in the private ops repo: then PRs and Actions of the product repo do not link to them |
| GE-8 | Issues are created in build order (stages in graph order, per stage first the Epics, then the tasks by ID); the numbers are computed in advance and every created number is checked | cross-references `#n` already at creation, without a second pass | a second pass over all texts |
| GE-9 | Write calls throttled (pause per call, on a rate limit the wait time from the response, otherwise growing); the run is resumable because every step first looks at what already exists | GitHub limits content-creating calls; an abort must not create anything twice | unthrottled run |
| GE-10 | The publication checklist also checks Issues, comments and the project with the deny scan at V7 | they become public with the repo | checking only the tree |

## 3. What is not part of this assignment

- No product code; the product repo stays without a commit until V10 (Issues do not change the Git history).
- The organization `guildwork-dev` was not part of this assignment: github.com offers no API way; the Owner created it on 2026-11-01 in the web form (task R-E05-T02, done). Since 2026-11-01 it holds the product repo (Owner instruction, O17): the Issues moved with the repo; a project can only be linked with repos of the same owner, so the project was created anew in the organization and the old project on the Owner's account is closed.
