<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-11: Finding state in the database

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

SCM-neutral, supports noise filter, address rate, and cross-repo learning

## Decision

Finding state in the DB as the source, the PR marker carries only the `run_id`s of the active runs (ADR-68) and `last_reviewed_sha`

## Alternatives

State in the PR marker

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-11.
