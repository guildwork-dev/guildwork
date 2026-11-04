<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-38: Two repos: product repo and ops repo

- Status: Accepted
- Group: ADR-37 to ADR-53 (third round, 2026-10-31)

## Context

The product should be company-neutral, but every installation has private values; today's planning repo has no commit, the separation costs nothing now (VERIFIED, cross-check item 32); a hit in the deny scan is a red check

## Decision

**Two repos:** public product repo and private ops repo per installation; deny list scanner (private list) locally, in the required check `ci-ok`, after every push to `main`, and over the history before making public; public from the first push with **one** root commit without planning history (pattern of the reference project bothy)

## Alternatives

one repo, private first, made public later; company values in the product repo

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.2, row ADR-38; references: [12](../architecture/12-open-source-and-project.md) section 4; [`bothy-vorlage-projekt-setup`](../research/bothy-vorlage-projekt-setup.md) sections 2.10, 3.2.
