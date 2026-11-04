<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-72: Operator eval on public sets via subscription

- Status: Accepted
- Group: ADR-72 and ADR-73 (sixth round, O28, 2026-11-01)

## Context

Background: The basis is the owner decision O28 ([DECISIONS](../DECISIONS.md) section 3.2): The project uses Claude exclusively, via the owner's subscription, including for eval and reference qualification. Without the two decisions the project could not measure services with a shell on public sets (condition 9 requires a private repo in `operator_repos`) and could not call the benchmark judges (the subscription token may only go into the `claude` process, ADR-57).

A case run has no external effect (effects only in the eval log, fixture without a write path), and the trigger is the operator themselves; foreign inputs only come via the benchmark's code, as with `operator_test` via dependencies and tests. Exfiltration of the token remains blocked via inspection proxy and offline registry cache; the residual risk from [05](../architecture/05-security.md) section 6 condition 9 (misuse of the quota) applies equally (DERIVED)

## Decision

**Operator eval on public sets via `subscription`:** An eval case run with `effect_sink: record`, SCM and tickets only from the plugin `eval-fixture` (write methods `unsupported`), started via the admin session of the operator of this runtime, on a set with `origin` `public_benchmark`, `own_public`, or `human_labeled`, may run services with a shell in the profile `operator_test`. There it replaces only the two items "repo in `operator_repos` and private at the hoster" and "trigger and ticket author are the operator"; conditions 1 to 8, egress only to the LLM endpoint and registry cache, inspection proxy, and `acknowledge_risk` apply unchanged. The repo class of an eval run remains `external_code` (detailed design 07 FE-754), the isolation follows ADR-48. Private sets remain under ADR-70. S2 cases: a case run with a write method or with a trigger other than the operator yields 0 subscription runs

## Alternatives

Eval and reference qualification via an API account of the project (recommendation from backlog M127, rejected by the owner with O28); do not measure services with a shell in the project

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.7, row ADR-72; references: [05](../architecture/05-security.md) section 6 conditions 9 and 10; [07](../architecture/07-eval.md) section 1; detailed design 07 FE-758; O28.
