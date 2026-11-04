<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-35: Autonomous run as a chain of specialized services

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

Project goal (README section 1): every stage at the standard of its field; independent review, rights, and qualification per stage ([03](../architecture/03-flow-and-orchestration.md) section 1a)

## Decision

Autonomous run as a chain of specialized services, controlled by the deterministic orchestrator; handover only via typed artifacts; automatic plan approval only via `auto_if` with plan critique by a fresh model

## Alternatives

one overall agent that plans, codes, reviews, and merges

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-35.
