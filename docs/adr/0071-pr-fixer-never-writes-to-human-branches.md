<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-71: PR fixer never writes to human branches

- Status: Accepted
- Group: ADR-71 (consistency run of the detailed design, 2026-11-01)

## Context

Background: The basis is the ruling FE-1127 of the detailed design ([11](../design/11-qa-prfix-automerge.md) section 9) and the contradiction between the reading of O9 ("commits of the PR fixer in watch mode") and ADR-59. The project decides; the owner has handed all open points over to the project.

The CI of a human branch runs with the secrets of the repo; agent code only runs like fork code under ADR-59 ([05](../architecture/05-security.md) section 2 item 4, section 3). A commit of the platform to the human branch would run agent code with these secrets

## Decision

**PR fixer never writes to human branches:** Also in watch mode on human PRs (opt-in per PR under O9), the PR fixer delivers every fix as a stacked PR from an `agent/*` branch; `allow_on_human_branches` only knows `never`. Pushes of the platform remain limited to `agent/*`; the only exception is the platform effect `audit_anchor` on the fixed anchor branch with its own permission profile (detailed design 04 FE-407)

## Alternatives

Commit to the human branch after the author's opt-in (reading of O9 until 2026-10-31)

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.6, row ADR-71; references: [01](../architecture/01-plugin-interfaces.md) section 5 (push check); [02](../architecture/02-services.md) section 6; [03](../architecture/03-flow-and-orchestration.md) section 1a; [04](../architecture/04-configuration-and-limits.md) sections 3 and 4; [08](../architecture/08-roadmap.md) stage 5; O9.
