<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# Component catalog

One file `<id>.toml` per component. For each building block of Guildwork, the catalog states **what** it is, **where** it lives, **what it provides**, **where it connects** and **which tasks** of the work plan build it. `plan.py check` checks it against the plan and the detailed design; `plan.py generate` produces the [build book](../build-book.md) from it. Decisions on this: [draft](../../plan/catalog-and-issues-draft.md) KE-1 to KE-5.

Precedence as in the detailed design: architecture before detailed design before catalog. The catalog invents nothing; every interface points to the place in the detailed design that defines it. If that place is missing, the detailed design is extended first.

## 1. What a component is

A building block with its own path and its own responsibility that an agent must understand as a whole in order to build on it: a package under `packages/`, a program under `apps/` or a role within it (such as `control-plane-orchestrator`), a plugin, a driver, a service, a part of the eval package, a part of the delivery, a check tool of the repo, the admin UI or an area of it. In addition, components of kind `process` for work without its own code (Owner steps, acceptances, publication), so that every task has a home.

## 2. Fields

```toml
id = "control-plane-orchestrator"      # = file name without .toml; a-z, 0-9, '-'
title = "Orchestrator with run state machine"
kind = "role"                          # package | program | role | plugin | driver | service | eval
                                       # | delivery | tool | ui | process
path = "apps/control-plane/src/orchestrator/"
package = "@guildwork/control-plane"   # optional
stage = "0"                            # stage in which the component is created
purpose = "One sentence: what it exists for and what it does not."
design = ["02-control-plane.md#44-orchestrator-and-run-state-machine"]   # file#anchor, checked
built_by = ["0-E05-T01", "0-E05-T02"]  # all tasks that create or extend it

[[provides]]                           # what others may use
name = "run-automat"                   # interface ID is "<id>/<name>"; a-z, 0-9, '-', '.'
kind = "ts-api"                        # ts-api | http | mcp-tool | event | table | queue | cli | config
                                       # | contract | file | ui | prompt | metric
title = "RunMachine: start, advance, cancel"
defined_in = "02-control-plane.md#22-public-interfaces"   # place with type, schema or DDL
from_task = "0-E05-T03"                # task after which it is usable (listed in built_by)

[[uses]]                               # where the component connects
interface = "db/migrator"
from_task = "0-E05-T01"                # first own task that needs it (listed in built_by)
purpose = "Create tables runs and run_steps"
```

## 3. Rules

- **One provider per interface.** A table is provided by the component that writes it and whose migration creates it; others use it. An HTTP endpoint, an MCP tool, an event, a queue, a configuration section belongs to exactly one component.
- **Granularity:** everything that another component calls, reads, subscribes to or includes is an interface. Endpoints of a route family, tools of a namespace or columns of a table may be grouped together if they are created together.
- **Order:** in the plan, `uses.from_task` must depend on the provider's `provides.from_task` (also across Epics and intermediate steps). Otherwise `plan.py check` reports "does not depend on". This is fixed in the plan (missing dependency) or in the catalog (wrong task), never by omitting the use.
- **Coverage:** every task that is not `dropped` is listed in at least one `built_by`.
- **References:** `design` and `defined_in` point to a heading that exists (GitHub anchors: lowercase letters, punctuation removed, spaces to `-`, non-ASCII letters remain) and whose section contains more than a move notice ("Detailed in", "Moved to"); `plan.py check` reports both.
- New component, new interface or new use while building: into the catalog in the same PR, `plan.py generate`, `plan.py check` green.
