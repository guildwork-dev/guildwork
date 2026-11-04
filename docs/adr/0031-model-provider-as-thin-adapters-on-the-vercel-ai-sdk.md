<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-31: ModelProvider as thin adapters on the Vercel AI SDK

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

official packages ([aisdk] VERIFIED); subscription token only for the CLI

## Decision

ModelProvider as our own thin adapters on the Vercel AI SDK; the subscription has no direct adapter, single calls on the subscription run via `claude-cli` (ADR-58)

## Alternatives

LiteLLM as a library

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-31.
