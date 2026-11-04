<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-18: Credential kind subscription only as a personal operator mode

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

[cc-legal] verbatim: "ordinary, individual usage", no routing "on behalf of their users", no "collect, store, or intermediate" (VERIFIED); token valid for one year ([cc-auth] VERIFIED); an agent with a shell can get past the egress allowlist without an inspection proxy via server tools and `mcp_servers` ([05](../architecture/05-security.md) section 3). Whether the inspection proxy is an "intermediate" is assessed by each operator

## Decision

Credential kind `subscription` only as a personal operator mode (ADR-51): pool `self-hosted` with `single_operator`, one operator, triggers only by the operator, token never in the control plane (start path ADR-57), only services without a shell and without file write rights (the token sits in the `claude` process of the sandbox). Exception profile `operator_test` for single operators with their own subscription (private repos of the operator, ticket author is the operator, egress without open internet): instead of the credential relay, a **inspection proxy** for the LLM endpoint on the operator's worker host applies there, which uses TLS termination to apply the same path and body filters as the relay and passes the auth header through unchanged, without storing, logging, or replacing it; without an inspection proxy `operator_test` is blocked ([05](../architecture/05-security.md) section 6 condition 9)

## Alternatives

Subscription as the org default; subscription token via the credential relay

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-18.
