<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-56: Gate B as a measurement target with a statistics rule

- Status: Accepted
- Group: ADR-54 to ADR-58 (Red Team on the overall idea, 2026-10-31)

## Context

Background: The basis is the rulings R-A to R-C of the project of 2026-10-31 (the owner handed all open points over to the project) and findings 1, 17, 18, and 19 of the Red Team on the overall idea; ADR-57 and ADR-58 come from findings 2 and 3 (package LLM runtime and subscription operation).

The smaller and noisier a set, the easier the old gate turned green; the Opus 4.5 judge reduces the gap of Claude Code to CodeRabbit to 3.4 points against 10.8 and 8.0 respectively under the other judges (own recalculation from [mcr-repo], VERIFIED); Juliet names the solution in names and comments (Red Team finding 19); leave-producer-out values are not comparable with the leaderboard ([rb-judging] VERIFIED)

## Decision

**Gate B is a measurement target, not a build condition, with a statistics rule** (R-C): one-sided non-inferiority test with an explicit margin per part (Gate B 5, Gate A 10 percentage points, unless stated otherwise; fixed before the first run), minimum power (half interval width at most 0.7 times the margin), otherwise "not decidable"; intervals as cluster bootstrap over PRs or tasks; estimated thresholds binding only after the first run. Required parts only on sets that distinguish the level: not saturated, without solution leak (Juliet only cleaned and only as regression, real CVE pairs as mandatory), neutral judge (Martian under all three judges, ReviewBench with leave-producer-out diagnosis without producers of the candidate's family). Published as measured and honestly, including "red" or "not decidable"

## Alternatives

"no significant gap" without a margin (lenient with small sets); deviating rules per service in [02](../architecture/02-services.md); a single fixed judge

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.3, row ADR-56; references: [10](../architecture/10-standards-per-layer.md) sections 1.4, 1.5, 3, 4, 6, 13; [07](../architecture/07-eval.md) sections 1, 1.1, 3.1, 3.8.
