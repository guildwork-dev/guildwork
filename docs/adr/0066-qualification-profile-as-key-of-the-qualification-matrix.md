<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-66: Qualification profile as the key of the qualification matrix

- Status: Accepted
- Group: ADR-66 to ADR-70 (Red Team on the overall idea, package architecture and law, 2026-10-31)

## Context

Background: The basis is findings 8, 9, 14, 15, and 16 of the Red Team on the overall idea and the ruling R-E of the project of 2026-10-31 (the chain of rights to the employer is an owner step, V0, and cannot be solved by the project).

Reviewer and planner use several models per role, coder and reviewer call other services as a library; with a single `model`, a swapped gate or verifier model still hit the same row, and a never measured combination could contribute to auto-merge (Red Team finding 14, DERIVED)

## Decision

**Qualification profile as the key of the qualification matrix:** `qualification_key` is the hash of a canonical profile of service, harness with version, credential kind, provider, model of the runtime and all `models.*` per role, `prompt_v` per stage, plugin versions, and the config keys marked in the JSON Schema with `x-qualification: true`. Library calls of other services inherit the profile of the caller and are qualified with it. The config snapshot stores profile and key per service; policy, adoption of the reference qualification, and merge gate condition 2 compare only the hash (for the adoption without the field `credential_kind` within the same provider)

## Alternatives

Row `(service, harness, credential_kind, provider, model, prompt_v, plugin_versions)` with one model (version until 2026-10-31); `config_hash` only in `eval_runs`

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.5, row ADR-66; references: [07](../architecture/07-eval.md) sections 1, 2, 2.1, S2, S7; [10](../architecture/10-standards-per-layer.md) section 1.2; [03](../architecture/03-flow-and-orchestration.md) section 1a condition 2; [04](../architecture/04-configuration-and-limits.md) sections 1, 5, 7; [02](../architecture/02-services.md) section 0.
