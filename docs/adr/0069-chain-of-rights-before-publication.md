<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-69: Chain of rights before publication

- Status: Accepted
- Group: ADR-66 to ADR-70 (Red Team on the overall idea, package architecture and law, 2026-10-31)

## Context

Background: The basis is findings 8, 9, 14, 15, and 16 of the Red Team on the overall idea and the ruling R-E of the project of 2026-10-31 (the chain of rights to the employer is an owner step, V0, and cannot be solved by the project).

Every sign-off confirms under DCO 1.1 (a) the right to submit; if it is missing, the sign-off is false, and without a CLA this can hardly be cured afterwards. Whether rights lie with the employer (for example § 69b UrhG) is unverified and not legal advice (Red Team finding 8)

## Decision

**Chain of rights before publication (V0, ruling R-E):** Before V1, the ops repo contains either a written release or waiver of rights by the founder's employer or a recorded proof that planning and code were created outside working hours and without the employer's resources. Owner step (O27). Until then no resources of the employer for the product and no public push; texts from the private preliminary work do not go verbatim into the product repo

## Alternatives

only a note in a private file (version until 2026-10-31); CLA instead of DCO

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.5, row ADR-69; references: [12](../architecture/12-open-source-and-project.md) sections 2.5, 4.4, 6, 9; [08](../architecture/08-roadmap.md) stage R.
