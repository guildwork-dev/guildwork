<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-70: Eval runner bound to the data path

- Status: Accepted
- Group: ADR-66 to ADR-70 (Red Team on the overall idea, package architecture and law, 2026-10-31)

## Context

Background: The basis is findings 8, 9, 14, 15, and 16 of the Red Team on the overall idea and the ruling R-E of the project of 2026-10-31 (the chain of rights to the employer is an owner step, V0, and cannot be solved by the project).

An eval run is a platform run and must not be a way around policy and data path; otherwise data of a third party, for example an employer, would go outward automatically via a consumer subscription (Consumer Terms §3, §11; Red Team finding 9)

## Decision

**Eval runner bound to the data path:** A private eval case inherits repo class and `data_policy` of its source repo and runs only via a runtime that would be permitted for this repo in operation; via `subscription` only cases from `operator_repos` of the runtime. Otherwise the runner rejects the case before the start, with an audit entry. S2 case with gate 0 runs

## Alternatives

Eval runs without a policy check of the data path (version until 2026-10-31)

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.5, row ADR-70; references: [07](../architecture/07-eval.md) section 1, S2; [05](../architecture/05-security.md) section 6 condition 10.
