<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-12: pg-kb as the default KnowledgeStore

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

The control plane is reachable, one state store

## Decision

KnowledgeStore `pg-kb` as default, `sqlite-artifact` for offline eval

## Alternatives

Knowledge base only as a CI artifact

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-12.
