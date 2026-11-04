<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-65: Fail closed on an invalid config file

- Status: Accepted
- Group: ADR-59 to ADR-65 (Red Team on the overall idea, package security of autonomous effects, 2026-10-31)

## Context

Background: The basis is findings 4, 5, 6, 7, 11, 12, and 13 of the Red Team on the overall idea and the ruling R-D of the project of 2026-10-31 (autonomous effects on public repos only once agent branches run like fork code and provenance and stale-approve conditions apply).

The inner level carries the tightenings (`protected_paths`, `merge`, limits); a typo or an upgrade would otherwise silently lift them and make, for example, auto-merge on `src/billing/**` possible (Red Team finding 13)

## Decision

**Fail closed on an invalid config file:** If an org, repo group, or repo file is invalid (also after an upgrade due to unknown keys), the last valid version of this file continues to apply; if there is none, at most `shadow`, `merge.mode: human`, `autonomy: low` apply; notice until a valid file is at the base SHA, fallback recorded in the snapshot

## Alternatives

Omit the repo level, outer levels apply (version until 2026-10-31); discard only the faulty keys

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.4, row ADR-65; references: [04](../architecture/04-configuration-and-limits.md) section 1 rule 4; [03](../architecture/03-flow-and-orchestration.md) section 5; [07](../architecture/07-eval.md) S2.
