<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-54: Roadmap as a dependency graph, core first

- Status: Accepted
- Group: ADR-54 to ADR-58 (Red Team on the overall idea, 2026-10-31)

## Context

Background: The basis is the rulings R-A to R-C of the project of 2026-10-31 (the owner handed all open points over to the project) and findings 1, 17, 18, and 19 of the Red Team on the overall idea; ADR-57 and ADR-58 come from findings 2 and 3 (package LLM runtime and subscription operation).

In the chain, the replacement of the review product only came after stage 5; companion features functionally depend only on the reviewer. A graph shows what really depends on what and allows parallel work (DERIVED)

## Decision

**Roadmap as a dependency graph, core first** (R-A): The first goal with real value is the reviewer including companion features (walkthrough, comments, chat, Learnings, optional auto-approve) on GitHub, `single-host`, with one credential path, that is stages R, 0 without sub-stage 0b, 1, 6, and sub-stage 7a. The stage numbers stay; a stage starts as soon as its predecessors in the graph are done. Stage 6 depends only on stage 1. New sub-stages: 0b (drivers `azure-blob`, `azure-keyvault`, OpenTofu modules) and 7a (Learnings without vector search)

## Alternatives

linear chain R, 0 to 10 (version until 2026-10-31)

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.3, row ADR-54; references: [08](../architecture/08-roadmap.md) sections 1 and 3; ADR-26.
