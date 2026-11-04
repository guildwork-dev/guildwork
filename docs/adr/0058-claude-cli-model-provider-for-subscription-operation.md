<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-58: ModelProvider claude-cli for subscription operation

- Status: Accepted
- Group: ADR-54 to ADR-58 (Red Team on the overall idea, 2026-10-31)

## Context

Background: The basis is the rulings R-A to R-C of the project of 2026-10-31 (the owner handed all open points over to the project) and findings 1, 17, 18, and 19 of the Red Team on the overall idea; ADR-57 and ADR-58 come from findings 2 and 3 (package LLM runtime and subscription operation).

In the set test operation (O2), stage 1 would otherwise have lacked reviewer gate and verifier, stage 2 clarity gate and plan critique and thus automatic plan approval; moved into the harness run, Gate A would measure a different pipeline than the specified one (Red Team on the overall idea finding 3, DERIVED); only the worker reaches models ([11](../architecture/11-installation-and-hosting.md) section 1)

## Decision

**ModelProvider `claude-cli` for subscription operation:** Single calls (gate, clarity gate, plan critique, judge, triage classification) run on the subscription as a work item via worker and egress proxy: `claude -p` without tools with `--json-schema`, start path and conditions as for `subscription` (ADR-57, [05](../architecture/05-security.md) section 6), capability level `fallback`. **Resolver rule:** A service whose model references (`models.*`, `gate_model`, `notes_model`) point to no reachable ModelProvider is rejected at load time; a service with a mandatory single call without its own reference needs at least one reachable entry in `models`

## Alternatives

no ModelProvider in subscription operation (version until 2026-10-31); silently move single calls into the harness run; single calls in the control plane

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.3, row ADR-58; references: [01](../architecture/01-plugin-interfaces.md) section 7; [04](../architecture/04-configuration-and-limits.md) sections 3a and 5; [07](../architecture/07-eval.md) S2, S4.
