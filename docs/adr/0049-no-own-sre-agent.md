<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-49: No own SRE agent

- Status: Accepted
- Group: ADR-37 to ADR-53 (third round, 2026-10-31)

## Context

The standard lies with vendors with access to production telemetry ([az-sre], [dd-bits], [sentry-fix] VERIFIED); the platform does not have this data

## Decision

**No own SRE agent**; only a handoff input (`sentry` for Sentry Seer, generic signed webhook `incident-handoff`), then `coder` or `prfixer` (stage 10)

## Alternatives

own incident or SRE service

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.2, row ADR-49; references: [10](../architecture/10-standards-per-layer.md) section 15; [02](../architecture/02-services.md) section 11.
