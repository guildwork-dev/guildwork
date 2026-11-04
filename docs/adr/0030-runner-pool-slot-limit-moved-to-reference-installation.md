<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-30: Runner pool slot limit moved to the reference installation

- Status: Moved to the reference installation (private)
- Group: ADR-01 to ADR-36

## Context

Decision of a specific installation, not a platform decision; see Decision.

## Decision

**Moved** to the reference installation (slot limit of a specific runner pool). Generically: a `ci-dispatch` pool has a fixed `max_concurrency` below the slot count, the CI wait time is measured ([06](../architecture/06-operations-and-deployment.md) section 2a)

## Alternatives

None recorded.

## Consequences

The installation-specific decision is kept in the private reference installation; the platform only keeps the generic rule stated under Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-30.
