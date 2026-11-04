<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-73: Benchmark judges and re-measured reference tools via claude-cli

- Status: Accepted
- Group: ADR-72 and ADR-73 (sixth round, O28, 2026-11-01)

## Context

Background: The basis is the owner decision O28 ([DECISIONS](../DECISIONS.md) section 3.2): The project uses Claude exclusively, via the owner's subscription, including for eval and reference qualification. Without the two decisions the project could not measure services with a shell on public sets (condition 9 requires a private repo in `operator_repos`) and could not call the benchmark judges (the subscription token may only go into the `claude` process, ADR-57).

Only the unmodified `claude` process may use the subscription token (ADR-57; [cc-legal] "collect, store, or intermediate" VERIFIED); foreign code with the token would be a way around this rule

## Decision

**Benchmark judges and re-measured reference tools via `claude-cli` when the eval runtime is `subscription`:** prompt, answer format, and evaluation come unchanged from the pinned benchmark or tool code (judges of R2 and R4, open reference tools such as LocAgent and STRIDE GPT); only the model call goes via a model bridge of the worker that executes it with `claude -p` like the ModelProvider `claude-cli` (ADR-58), instead of via the library of the foreign code with an API key. Parameters that `claude -p` does not set (for example `temperature`) and the call path are listed as deviations in the eval report; before the first Gate B run, the reference tools are re-scored from the raw outputs of the benchmark with this path and compared against the published values of the file (unverified whether the raw outputs are available; 0-E20-T27)

## Alternatives

Benchmark code with an API key (rejected by the owner with O28); give the subscription token to the benchmark code

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.7, row ADR-73; references: detailed design 07 section 2.7 and FE-759; [10](../architecture/10-standards-per-layer.md) section 3; O28.
