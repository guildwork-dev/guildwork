<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-68: Object lock: at most one active run per object and service

- Status: Accepted
- Group: ADR-66 to ADR-70 (Red Team on the overall idea, package architecture and law, 2026-10-31)

## Context

Background: The basis is findings 8, 9, 14, 15, and 16 of the Red Team on the overall idea and the ruling R-E of the project of 2026-10-31 (the chain of rights to the employer is an owner step, V0, and cannot be solved by the project).

The route `pipeline.ci_failed` started a PR fixer run next to the fix round of the pipeline; double costs, competing pushes, overwritten status comments with only one `run_id`, and ambiguous control commands (Red Team finding 16, VERIFIED at [04](../architecture/04-configuration-and-limits.md) section 3)

## Decision

**Object lock:** per object (ticket, PR) and service at most one active run, enforced via a unique partial index in Postgres; events for an object that a running pipeline holds (for example `pipeline.ci_failed`, `@agent fix`) are delivered to it instead of being started as a new run; a second event for the same single service is merged into exactly one follow-up job; the status comment lists all active runs; control commands go to the matching run, with ambiguity a follow-up question with `run=<run_id>`, `stop` ends all

## Alternatives

parallel runs per route (version until 2026-10-31); dedupe only via the delivery ID

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.5, row ADR-68; references: [03](../architecture/03-flow-and-orchestration.md) sections 2.3, 2.5, 4; [04](../architecture/04-configuration-and-limits.md) section 3; [07](../architecture/07-eval.md) S5, S6; ADR-11.
