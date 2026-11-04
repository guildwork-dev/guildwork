<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-52: Public eval sets and reference qualification

- Status: Accepted
- Group: ADR-37 to ADR-53 (third round, 2026-10-31)

## Context

Third parties can only verify quality on public sets; without a reference qualification every service would remain `shadow` for third parties; benchmark repos are freely licensed, but the PRs they contain are code of the source repos (DERIVED)

## Decision

**Public, license-clean eval sets in the project** (adapters and download scripts with a pinned commit, own labels, no copies of third-party data), **private sets per installation** (never published, never in the reference qualification); the project publishes a **reference qualification** per release (matrix with logs, costs, and reference versions). `vendor_output` (CodeRabbit and SonarQube outputs) is permanently blocked (O18, O19 decided); noncommercial sets are never a required part

## Alternatives

Eval only on own private repos; third-party benchmarks as copies in the repo

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.2, row ADR-52; references: [07](../architecture/07-eval.md) sections 1, 2.1; [10](../architecture/10-standards-per-layer.md) section 1.5; CodeRabbit terms of use 4.2 (iv) ([12](../architecture/12-open-source-and-project.md) section 5.3); [sonar-aup] §5.
