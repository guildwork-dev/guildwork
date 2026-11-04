<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-36: Optional auto-merge via a deterministic merge gate

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

Project goal "optionally autonomous merge"; the merge API with `sha` rejects with 409 when the head has moved ([gh-merge] VERIFIED)

## Decision

Auto-merge optional via a deterministic merge gate at the head SHA, executed by the Effect Gateway with profile `merge`; no `propose_merge`, no bypass, no bot approve; waiting window with `@agent hold`; revert PR and fallback to `human` via `repo_overrides` when the target branch is red; `auto` only after suite S7; condition "`quality-gate` green at the head SHA" as soon as analyzers run; every service that contributed content or approvals in the run (including PR fixer, planner with automatic plan approval, `triage` as starter, architect, `docs`) needs a qualified row, a deviation under ADR-47 never counts ([03](../architecture/03-flow-and-orchestration.md) section 1a condition 2); provenance condition and no `auto` for `external_code` under ADR-60

## Alternatives

Merge never by the platform; auto-merge of the hoster after bot approve

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-36.
