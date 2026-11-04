<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-20: Egress proxy with allowlist per service

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

Exfiltration and supply chain; Codex pattern ([codex-cloud] VERIFIED)

## Decision

Egress proxy with allowlist per service; secrets only in the setup phase; in air-gap mode only configured targets (ADR-44)

## Alternatives

open network

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-20.
