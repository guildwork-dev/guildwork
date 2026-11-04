<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-44: Product telemetry off by default and air-gap mode

- Status: Accepted
- Group: ADR-37 to ADR-53 (third round, 2026-10-31)

## Context

The platform processes code and tickets, trust weighs more than usage data (DERIVED); comparable products send by default ([lf-tel], [coder-tel], [n8n-iso] VERIFIED). With a cloud LLM no installation is fully offline

## Decision

**Product telemetry off by default**, update notice as a separate opt-in also off; content documented publicly, never code, tickets, prompts, names. **Air-gap mode** via the egress proxy: only configured SCM, ticket, and LLM targets plus mirrors of the operator, enforced in the proxy and by network rule, `doctor` checks actively

## Alternatives

Telemetry on with opt-out (like Langfuse, Coder, n8n)

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.2, row ADR-44; references: [11](../architecture/11-installation-and-hosting.md) section 8; [06](../architecture/06-operations-and-deployment.md) section 9.
