<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-42: Installation ladder

- Status: Accepted
- Group: ADR-37 to ADR-53 (third round, 2026-10-31)

## Context

Industry pattern of a ladder of three paths ([`hosting-und-installation`](../research/hosting-und-installation.md) section 2.1); reference project bothy with installer, modules, and portability test ([bothy-repo] VERIFIED); a marketplace needs publisher accounts and contracts (DERIVED)

## Decision

**Installation ladder:** Compose bundle with installer CLI (`install`, `doctor`, `upgrade`, `backup`, `restore`, `worker register`, `github-app create`) and setup wizard in the admin UI (stage 0); OpenTofu modules `generic-vm` and `azure` (sub-stage 0b), `aws`, `gcp`, `hetzner` (stage 8); Helm chart (stage 8). A profile only counts as supported once it is in the test matrix (portability test amd64 and arm64)

## Alternatives

Helm only; docs only without an installer; marketplace listings of the clouds

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.2, row ADR-42; references: [11](../architecture/11-installation-and-hosting.md) sections 2, 3, 9, 10.
