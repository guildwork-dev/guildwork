<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-06: Effect Gateway as the single write point

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

Separation of rights against injection; lesson from the remote code execution at CodeRabbit via linter configuration in the PR (a `.rubocop.yml` in the PR made the linter execute code from the PR, [kudelski-cr] CLAIMED)

## Decision

Effect Gateway as the single write point; an effect only if the command covers it; deny by default

## Alternatives

Agent writes itself with a token (OpenHands pattern)

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-06.
