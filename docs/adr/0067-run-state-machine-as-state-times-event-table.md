<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-67: Run state machine as a state times event table

- Status: Accepted
- Group: ADR-66 to ADR-70 (Red Team on the overall idea, package architecture and law, 2026-10-31)

## Context

Background: The basis is findings 8, 9, 14, 15, and 16 of the Red Team on the overall idea and the ruling R-E of the project of 2026-10-31 (the chain of rights to the employer is an owner step, V0, and cannot be solved by the project).

The diagram lacked error, budget, and abort paths from several states, `stop` had no effect in waiting states, `continue` lost the originating state, 409 appeared in two places differently, and review runs on long-open PRs would have blocked every upgrade after two releases (Red Team finding 15, VERIFIED on the diagram)

## Decision

**Run state machine as a table of state times event:** the only, machine-readable source; per non-final state an entry for the mandatory events `stop`, `budget_exhausted`, `error_after_retries`, and `deadline`; `paused_budget` remembers the originating state like `awaiting_input`; 409 on merge leads to `merge_gate`; single-service runs end in `done` after their last effect. **Upgrade lifts open runs:** Every release ships a mapping of all states of the previous version, the control plane lifts open runs onto it before the next migration; no upgrade block due to waiting runs. Completeness test in S6

## Alternatives

State diagram (version until 2026-10-31); upgrade block until the operator finishes runs of version N-1

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.5, row ADR-67; references: [03](../architecture/03-flow-and-orchestration.md) sections 2.1, 2.2, 5, 6; [07](../architecture/07-eval.md) S6.
