<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-26: Roadmap stages

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

Every stage is measured on a freshly installed platform, so repo and installability come first; the reviewer remains the first functional stage, because self-review and merge gate build on it and public review benchmarks with a free license are available

## Decision

Roadmap: stage R (public repo with check tools), stage 0 (foundation and installability), stage 1 reviewer, then the chain up to auto-merge (stages 2 to 5), after that companion features, knowledge and triage, providers and bases, breadth and hardening, edge layers (stages 6 to 10). Connecting an organization to an installation is not a platform stage ([08](../architecture/08-roadmap.md)). Since ADR-54 maintained as a dependency graph with the reviewer core first

## Alternatives

Jira and providers before planner and coder (first round); org connection with Jira as platform stage 7 (second round)

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-26.
