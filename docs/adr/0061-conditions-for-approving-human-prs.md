<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-61: Conditions for approving human PRs

- Status: Accepted
- Group: ADR-59 to ADR-65 (Red Team on the overall idea, package security of autonomous effects, 2026-10-31)

## Context

Background: The basis is findings 4, 5, 6, 7, 11, 12, and 13 of the Red Team on the overall idea and the ruling R-D of the project of 2026-10-31 (autonomous effects on public repos only once agent branches run like fork code and provenance and stale-approve conditions apply).

A SHA-bound approval stays in place on GitHub after a later push if "Dismiss stale pull request approvals" is off (default according to Red Team finding 6, not retrieved again here); the author could then push code onto `protected_paths` afterwards, the auto-pause would prevent the re-review, and a withdrawal via the author's own thread reply would lift the P0/P1 cap

## Decision

**Conditions for approving human PRs** (supplement to O24 and ADR-14): (a) branch protection dismisses stale approvals and requires an approval after the last push (`doctor` and `approvalProtection` check, not readable means not met), and the platform withdraws its approval on every new push (`withdrawApprove`); (b) author with write access, no fork PR; (c) full, unpaused review at the head; (d) a P0/P1 withdrawal only counts if another human with write access than the author triggers it. Otherwise `auto_approve` stays without effect, with a notice

## Alternatives

Approve only SHA-bound without withdrawal (version until 2026-10-31); withdrawal only on pushes of the Effect Gateway (proposal M84)

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.4, row ADR-61; references: [04](../architecture/04-configuration-and-limits.md) section 3; [01](../architecture/01-plugin-interfaces.md) section 5; [02](../architecture/02-services.md) section 4; [07](../architecture/07-eval.md) S1; backlog M84.
