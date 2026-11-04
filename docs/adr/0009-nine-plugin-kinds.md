<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-09: Nine plugin kinds

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

Reference projects do not cleanly separate ticket and SCM ([pr-agent], [kodus] VERIFIED). CI logs are read by the SCMProvider (`CI_LOGS`, [01](../architecture/01-plugin-interfaces.md) section 5); a tenth kind only when a CI system without a hoster API is needed

## Decision

Nine plugin kinds (TriggerSource, WorkItemProvider, SCMProvider, AgentRuntime, ModelProvider, ExecutionBackend, KnowledgeStore, Notifier, Analyzer); TriggerSource, WorkItemProvider, and SCMProvider separate; one package may implement several kinds. Drivers for the base are a separate class (ADR-41)

## Alternatives

Mixed types as in PR-Agent and Kodus; `CIProvider` as a separate kind (proposed in [`ebene-pr-fix-und-ci`](../research/ebene-pr-fix-und-ci.md) section 7)

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-09.
