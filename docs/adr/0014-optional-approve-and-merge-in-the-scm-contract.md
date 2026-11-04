<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-14: Optional approve and merge in the SCM contract

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

A bot approve could satisfy branch protection, therefore never for agent PRs and for human PRs only as an option with default off; merge as an option follows from the project goal "autonomous run up to the optional merge"

## Decision

`approve` in the SCM contract only optional for human PRs, never for agent PRs: SHA-bound, only via the Effect Gateway, capability `APPROVE_HUMAN`, only with `services.reviewer.auto_approve` (platform default off, O24 decided) and the conditions from ADR-61; `merge` only optional, SHA-bound, only via the Effect Gateway after the merge gate (ADR-36); agent PRs as drafts with `agent-approval-check`

## Alternatives

Bot approve by policy for all PRs; no `approve` in the contract (version until O24); never merge

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-14.
