<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-03: TypeScript on Node 22+

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

Vercel AI SDK with official provider packages, pg-boss ([aisdk], [pg-boss] VERIFIED); reference projects in TS. The Agent SDK is no longer a reason: it is proprietary and not a dependency of the project, Claude Code is connected via `claude -p` (ADR-39, Red Team on the overall idea finding 10)

## Decision

TypeScript on Node 22+ for control plane and worker

## Alternatives

Python, Go

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-03.
