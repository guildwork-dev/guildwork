<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-63: Visibility rule across repo boundaries

- Status: Accepted
- Group: ADR-59 to ADR-65 (Red Team on the overall idea, package security of autonomous effects, 2026-10-31)

## Context

Background: The basis is findings 4, 5, 6, 7, 11, 12, and 13 of the Red Team on the overall idea and the ruling R-D of the project of 2026-10-31 (autonomous effects on public repos only once agent branches run like fork code and provenance and stale-approve conditions apply).

Triage runs on public repos for every human author, searches for duplicates in the KnowledgeStore, and quotes them; private issues or private code would thus end up in public comments even without injection (Red Team finding 11, DERIVED)

## Decision

**Visibility rule across repo boundaries:** A run reads only sources that every reader of the output target may see (order `public`, `internal`, `private`; private sources of other repos only with `CROSS_REPO` and only for private targets); visibility fresh from the provider per claim (`repoInfo`); the Effect Gateway checks every quote and every reference of an effect against the visibility of the target and otherwise blocks with an audit entry

## Alternatives

`CROSS_REPO` as a pure org switch (version until 2026-10-31); visibility rule only for Learnings

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.4, row ADR-63; references: [05](../architecture/05-security.md) sections 2 and 7; [02](../architecture/02-services.md) sections 0 and 9; [01](../architecture/01-plugin-interfaces.md) section 5; [07](../architecture/07-eval.md) S1.
