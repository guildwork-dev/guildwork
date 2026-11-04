<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-47: Live requires Gate A and Gate B or an adopted reference qualification

- Status: Accepted
- Group: ADR-37 to ADR-53 (third round, 2026-10-31)

## Context

The level of the standard should be mandatory, not a claim; the gap becomes visible instead of hidden; a PR must not be able to override the rule. Services without a current required part (for example `triage`, threat model, QA E2E) only go live with marking

## Decision

**`live` requires Gate A and Gate B or an adopted reference qualification.** Gate B consists of required parts (measurable, with a reference value) and report parts; the required parts must be green, per part or scope (for example QA `e2e`, PR fixer `merge_conflict`). Adoption of a reference qualification only with the same release and the same qualification profile (ADR-66), followed by remeasurement in shadow with automatic fallback to `shadow`. **Deviation** only via installation configuration (`qualification.allow_unproven_live`, never in repo files) with a mandatory justification; admin UI, status comment, check summary, and Run Record visibly carry "standard not proven", the audit records the switch; for the merge gate a deviation does not count, for no service that contributed to the run. Gate B decides only about `live` and the merge gate; whether an expansion stage is done is governed by ADR-55 (status green, red, not decidable, or open, [10](../architecture/10-standards-per-layer.md) section 1.2 item 6)

## Alternatives

`live` with Gate A alone if Gate B cannot be measured (earlier rule)

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.2, row ADR-47; references: [10](../architecture/10-standards-per-layer.md) section 1.2; [07](../architecture/07-eval.md) sections 2, 2.1; [04](../architecture/04-configuration-and-limits.md) section 7.
