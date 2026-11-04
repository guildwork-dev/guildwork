<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-17: Configuration, rules, and agent files from the base SHA

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

Principle of Bugbot ([cursor-bugbot] VERIFIED); a PR cannot change its own review; Copilot reads instructions from the head ([copilot-instr], VERIFIED according to the research)

## Decision

Configuration, rules, and agent files (`CLAUDE.md`, `AGENTS.md`, `REVIEW.md`, analyzer rules) from the base SHA

## Alternatives

from the head (Copilot, CodeRabbit)

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-17.
