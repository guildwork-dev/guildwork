<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-02: Single control plane with Postgres as the only state

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

SCM independence, ticket systems as input, and limits across all runs require a central service; one state store is operable for a small team

## Decision

One control plane, Postgres as the only state plus object storage via the driver `BlobStore` (ADR-41)

## Alternatives

CI only without a server; multiple services

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-02.
