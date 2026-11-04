<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-16: Own limit ledger with reservation

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

Subscription and Codex bypass every gateway, Codex delivers no USD, LiteLLM "fails open" without a DB ([litellm] VERIFIED)

## Decision

Own limit ledger with reservation as the source of truth

## Alternatives

LiteLLM proxy, provider limits alone

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-16.
