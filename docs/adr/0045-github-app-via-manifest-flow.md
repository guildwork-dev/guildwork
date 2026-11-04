<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-45: GitHub App via manifest flow

- Status: Accepted
- Group: ADR-37 to ADR-53 (third round, 2026-10-31)

## Context

Every operator needs their own app; the manifest flow exchanges a `code` for the app data within one hour ([gh-manifest] VERIFIED); an app permission applies to all repos the app is installed on, so a broker error could otherwise mint `actions:write` for a product repo (DERIVED, [gh-insttoken] VERIFIED)

## Decision

**GitHub App via manifest flow** per installation (admin UI or `guildwork github-app create`), permissions exactly from the profiles in [05](../architecture/05-security.md) section 2, `id`, key, and webhook secret directly into the `SecretStore`. For the backend `ci-dispatch` a **separate dispatch app** with `actions:write`, installed only on the runner repo; the main app never gets `actions:write`

## Alternatives

one central app of the project; app by hand following instructions; `actions:write` in the main app

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.2, row ADR-45; references: [11](../architecture/11-installation-and-hosting.md) section 2.3; [05](../architecture/05-security.md) section 2; [06](../architecture/06-operations-and-deployment.md) section 2a.
