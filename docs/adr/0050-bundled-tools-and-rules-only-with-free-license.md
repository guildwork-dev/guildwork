<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-50: Bundled third-party tools and rules only with a free license

- Status: Accepted
- Group: ADR-37 to ADR-53 (third round, 2026-10-31)

## Context

Semgrep Rules License: "only for your own internal business purposes" ([semgrep-rules] VERIFIED); Opengrep rules: Commons Clause forbids selling, including for hosting and support fees ([opengrep-rules] VERIFIED, cross-check item 24); CodeQL CLI only for OSI codebases and not as a hosted solution ([codeql-lic] VERIFIED); SonarSource AUP §5 and §6, SSALv1 (c) ([sonar-aup], [ssal] VERIFIED)

## Decision

**Bundled third-party tools and rules only with a free license** from the allowlist `bundled_licenses`: no Semgrep registry rules, no Opengrep rule collection (Commons Clause), no CodeQL CLI, no SonarQube in the product; their results at most as a SARIF or webhook import that the operator is responsible for (SonarQube with `llmUse: forbidden`); own rules under the project license

## Alternatives

Ship registry rules or CodeQL; offer a Sonar plugin

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.2, row ADR-50; references: [01](../architecture/01-plugin-interfaces.md) section 12; [12](../architecture/12-open-source-and-project.md) section 7; [06](../architecture/06-operations-and-deployment.md) section 8.
