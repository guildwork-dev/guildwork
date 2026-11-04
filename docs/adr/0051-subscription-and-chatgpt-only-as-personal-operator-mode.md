<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-51: Credential kinds subscription and chatgpt only as a personal operator mode

- Status: Accepted
- Group: ADR-37 to ADR-53 (third round, 2026-10-31)

## Context

Source [cc-legal]: "Developers building products or services ... including those using the Agent SDK, should use API key authentication"; no "offer Claude.ai login", no "collect, store, or intermediate" (VERIFIED); [codex-auth]: "Use API key authentication for programmatic Codex CLI workflows" (VERIFIED); Consumer Terms (EEA) §3 automated access only with an API key, §11 non-commercial ([an-consumer] VERIFIED)

## Decision

Credential kinds **`subscription`** (Claude subscription) and **`chatgpt`** (Codex with ChatGPT login) only as a **personal operator mode**: blocked by default, enabled in `installation.yaml` under `credentials.personal_modes` with `acknowledge_terms` (version and date of the terms read); the platform never implements a login, stores no token, and never passes one beyond the worker host; the operator creates the token on their worker host in the unmodified CLI themselves (`claude setup-token`), the worker binary passes it locally to the `claude` process, the control plane never sees it (ADR-57). Whether passing it through counts as "intermediate" is an operator risk alongside `acknowledge_terms`. For every autonomous operation the docs recommend an API key, WIF, or a cloud provider

## Alternatives

Subscription as a normal credential path; own login flow of the platform

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.2, row ADR-51; references: [05](../architecture/05-security.md) section 6; [12](../architecture/12-open-source-and-project.md) section 7; [04](../architecture/04-configuration-and-limits.md) section 7.
