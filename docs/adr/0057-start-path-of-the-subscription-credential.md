<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-57: Start path of the credential kind subscription

- Status: Accepted
- Group: ADR-54 to ADR-58 (Red Team on the overall idea, 2026-10-31)

## Context

Background: The basis is the rulings R-A to R-C of the project of 2026-10-31 (the owner handed all open points over to the project) and findings 1, 17, 18, and 19 of the Red Team on the overall idea; ADR-57 and ADR-58 come from findings 2 and 3 (package LLM runtime and subscription operation).

`setup-token` "does not save the token anywhere", it is set as `CLAUDE_CODE_OAUTH_TOKEN` ([cc-auth] VERIFIED); the earlier path reported "Not logged in" (Red Team on the overall idea finding 2, reproduced with CLI 2.1.288, VERIFIED); parallel copies of a token with refresh can invalidate each other (unverified); the relay would "intermediate" the token centrally ([cc-legal] VERIFIED, assessment DERIVED)

## Decision

**Start path of the credential kind `subscription`:** The operator creates the token with `claude setup-token` and stores it in a file on the worker host that only the worker user can read (path only in the local worker configuration). The worker reads it per item and sets the token only as `CLAUDE_CODE_OAUTH_TOKEN` in the environment of the `claude` process (allowlist), never in the DB, work item envelope, snapshot, log, or transcript; the control plane never sees it. `/login` is not a start path, so also never with `max_concurrency` above 1. Passing it through locally is an operator risk (reading "intermediate") alongside `acknowledge_terms`. Contract test "start with `subscription`" in stage 0, cases in S1 and S2

## Alternatives

Login via `/login` with `.credentials.json` in the config directory (version until 2026-10-31: empty config directory without a credential variable); copy of `.credentials.json` per sandbox; token via the credential relay

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.3, row ADR-57; references: [01](../architecture/01-plugin-interfaces.md) sections 6 and 11.4; [05](../architecture/05-security.md) section 6 conditions 4 and 8; ADR-51.
