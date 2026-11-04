<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-24: Untrusted type for all foreign content

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

enforces the marking in the prompt

## Decision

`Untrusted<T>` for all foreign content, including SARIF messages of foreign analyzers

## Alternatives

only references

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-24.
