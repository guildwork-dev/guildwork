<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-04: Own versioned state machine in Postgres with pg-boss

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

no additional service; DBOS license unverified; Restate and Inngest are push and not freely licensed; BullMQ fairness only in Pro ([restate], [inngest], [bullmq] VERIFIED); migration path open, because work items sit behind our own interface

## Decision

Own versioned state machine in Postgres plus pg-boss

## Alternatives

DBOS, Hatchet, Temporal, Restate, Inngest, BullMQ

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-04.
