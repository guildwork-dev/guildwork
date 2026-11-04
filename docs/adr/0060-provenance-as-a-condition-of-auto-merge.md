<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-60: Provenance as a condition of auto-merge

- Status: Accepted
- Group: ADR-59 to ADR-65 (Red Team on the overall idea, package security of autonomous effects, 2026-10-31)

## Context

Background: The basis is findings 4, 5, 6, 7, 11, 12, and 13 of the Red Team on the overall idea and the ruling R-D of the project of 2026-10-31 (autonomous effects on public repos only once agent branches run like fork code and provenance and stale-approve conditions apply).

The conditions "0 P0/P1" and "QA pass" are model judgments about the same inputs that also steer the coder; a foreign comment steers both at once, and a backdoor in an allowed push does not fall under "0 effects outside the command" (Red Team finding 5, DERIVED); principle of [05](../architecture/05-security.md): no model has to decide correctly for nothing bad to happen

## Decision

**Provenance as a condition of auto-merge** (R-D): merge gate condition 12: all `Untrusted` inputs from persons that a service of the run has seen come from persons with write access and from the state before the trigger, otherwise G2 and G3; Run Record with attribute `foreign_input_seen`. The resolver rejects `merge.mode: auto` for repos of the class `external_code`, that is for every public repo; the orchestrator rechecks the class per claim. A relaxation for public repos needs a new decision and at least ADR-59, condition 12, ADR-61, and its own S7 cases

## Alternatives

Merge gate only with conditions 1 to 11 (version until 2026-10-31); auto-merge on public repos after S7 as on private ones

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.4, row ADR-60; references: [03](../architecture/03-flow-and-orchestration.md) section 1a; [05](../architecture/05-security.md) sections 3 and 8; [04](../architecture/04-configuration-and-limits.md) section 3; [07](../architecture/07-eval.md) S2, S7.
