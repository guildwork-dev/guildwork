<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-59: CI on agent branches like fork code

- Status: Accepted
- Group: ADR-59 to ADR-65 (Red Team on the overall idea, package security of autonomous effects, 2026-10-31)

## Context

Background: The basis is findings 4, 5, 6, 7, 11, 12, and 13 of the Red Team on the overall idea and the ruling R-D of the project of 2026-10-31 (autonomous effects on public repos only once agent branches run like fork code and provenance and stale-approve conditions apply).

Sandbox protection only applies in the sandbox, the CI runs the agent's tests and build scripts with repo secrets and open network; an app installation token lets `pull_request` workflows run without approval (Red Team finding 4, GitHub docs read there, not retrieved again here); Copilot PRs only run after "Approve and run workflows" (VERIFIED according to [`ebene-pr-fix-und-ci`](../research/ebene-pr-fix-und-ci.md) section 2.2). Residual risk with `guarded_workflows`: jobs without secrets have open network

## Decision

**CI on agent branches like fork code:** Coder, QA, and PR fixer run in a repo only with `security.agent_ci`. Preferred `agent_fork`: The Effect Gateway pushes `agent/*` into an agent fork repo of a separate organization of the installation (only the app writes) and opens PRs from there, the hoster withholds secrets and requires approval according to its fork setting. Otherwise `guarded_workflows` as an installation prerequisite: jobs with secrets other than the `GITHUB_TOKEN` only in environments with a required reviewer or with `agent/**` excluded per event (for `pull_request` via a job condition on the head branch, [05](../architecture/05-security.md) section 3), no `pull_request_target` with checkout of the head. `doctor` checks per repo, the orchestrator per claim at the base SHA; without proof `no_safe_ci`

## Alternatives

CI on `agent/*` as on human branches (version until 2026-10-31); `forbidden_paths` also for tests and build scripts (the coder must write tests)

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.4, row ADR-59; references: [05](../architecture/05-security.md) section 3; [03](../architecture/03-flow-and-orchestration.md) sections 1a and 5; [04](../architecture/04-configuration-and-limits.md) section 3; [07](../architecture/07-eval.md) S1, S2.
