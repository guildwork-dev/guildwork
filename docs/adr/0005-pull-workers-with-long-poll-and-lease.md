<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-05: Pull workers with long poll and lease

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

Execution locations (CI networks, own hardware, home networks) are often behind NAT or a firewall without inbound connections (DERIVED); reference "only outbound HTTPS" ([an-managed-sh] VERIFIED)

## Decision

Pull workers with long poll and lease, outbound HTTPS only

## Alternatives

Push to workers; Actions as the core

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-05.
