<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-29: Hash-chained audit with daily anchor outside the database

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

Traceability, later changes visible; every base has a sink ([01](../architecture/01-plugin-interfaces.md) section 13 rule 2, [05](../architecture/05-security.md) section 8)

## Decision

Audit hash-chained with a daily anchor outside the database: into a `BlobStore` with capability `OBJECT_LOCK` or via `SCMProvider` as a commit into a repo of the operator; without a sink `doctor` reports "audit anchor missing"

## Alternatives

simple append-only table; anchor only in an internal repo

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-29.
