<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-21: OTel SDK and collector with own required alerts

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

No foreign backend needed to get required alerts; Langfuse needs four more storage services ([langfuse] VERIFIED); Claude Code exports OTLP natively ([cc-monitoring] VERIFIED) ([06](../architecture/06-operations-and-deployment.md) sections 3 and 4)

## Decision

OTel SDK and collector, export via OTLP to any backend; the control plane computes required alerts itself and delivers them via `Notifier`; Compose bundle with a minimum stack (collector with Prometheus and file export); Langfuse later

## Alternatives

Langfuse immediately; alerts only via an existing backend of the operator

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-21.
