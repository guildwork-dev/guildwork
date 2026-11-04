<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-46: New services architect, triage, and docs

- Status: Accepted
- Group: ADR-37 to ADR-53 (third round, 2026-10-31)

## Context

Chain of specialized services (ADR-35): inputs, check methods, and qualification differ; triage protects public repos from outside noise; the indexer writes into the knowledge base, `docs` into the repo

## Decision

**New services** `architect` (specification in the EARS pattern, ADR drafts, design review against C4 and arc42 checkpoints, threat model per STRIDE, plan conformance), `triage` (duplicates, labels, assignees, spam and slop, without a shell, proposal instead of closing) and `docs` (docstrings, doc sync after merge, release notes deterministic plus readable text). This makes **ten services**. No separate service for static analysis (ADR-40), dependency updates, SRE (ADR-49)

## Alternatives

`architect` as a planner option; triage and docs in the indexer; service `analysis`

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.2, row ADR-46; references: [02](../architecture/02-services.md) sections 2, 9, 10; [10](../architecture/10-standards-per-layer.md) sections 5, 11, 12; [`ebenen-landkarte`](../research/ebenen-landkarte.md); [`ebene-planung-und-architektur`](../research/ebene-planung-und-architektur.md).
