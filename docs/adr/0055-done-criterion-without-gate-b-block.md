<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-55: Done criterion without a Gate B block

- Status: Accepted
- Group: ADR-54 to ADR-58 (Red Team on the overall idea, 2026-10-31)

## Context

Background: The basis is the rulings R-A to R-C of the project of 2026-10-31 (the owner handed all open points over to the project) and findings 1, 17, 18, and 19 of the Red Team on the overall idea; ADR-57 and ADR-58 come from findings 2 and 3 (package LLM runtime and subscription operation).

A red, unreachable, or unreadable required part would have halted all later stages permanently; example: planner B2 on the saturated SWE-Bench Pro V2 (98.00 and 99.40 % respectively) cannot be passed arithmetically (Red Team finding 1, VERIFIED via [`ebene-coding`](../research/ebene-coding.md) section 2.2)

## Decision

**Done criterion without a Gate B block** (R-B): A stage is done when it is built, its required suites (S1 to S8) and Gate A are green, and Gate B is measured and reported. Gate B decides only about `live` and the merge gate (ADR-47). Status per service and part: green, red ("done, Gate B red"), not decidable ("done, Gate B not decidable"), or open ("done with Gate B open"); none of them blocks a following stage

## Alternatives

every Gate B required part green as the done criterion (version until 2026-10-31)

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.3, row ADR-55; references: [10](../architecture/10-standards-per-layer.md) section 1.2 item 6; [08](../architecture/08-roadmap.md) principles 1 and 2.
