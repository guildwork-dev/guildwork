<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-40: Analyzer plugin kind and platform gate on new code

- Status: Accepted
- Group: ADR-37 to ADR-53 (third round, 2026-10-31)

## Context

one form for reviewer, self-check, QA, and PR fixer that the hosters also accept ([sarif], [gh-sarif] VERIFIED); the value lies in the AI layer on top (verifier, fix with re-scan); the gate needs no agent phase, so no service

## Decision

**Plugin kind `Analyzer`** for third-party tools (SAST, dependencies, secrets, IaC, accessibility, cost); normal form **SARIF 2.1.0**; every `run` in the sandbox with egress allowlist; manifest with SPDX license, `rulesLicense` and `distribution: bundled | operator_supplied`; operating modes `ingest` (stage 1) and `run` (stage 2); findings are candidates for the verifier (ADR-33); no silent green (a crash yields `neutral`). The **platform gate on new code** is a deterministic core function with check `quality-gate`, not a separate service; checked against our own named values (`analysis.gate`, [10](../architecture/10-standards-per-layer.md) section 13 B1), not via parity with Sonar way

## Alternatives

Tool names hard-coded in service texts; own analysis engine; separate service `analysis` (proposal of the static analysis research)

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.2, row ADR-40; references: [01](../architecture/01-plugin-interfaces.md) section 12; [10](../architecture/10-standards-per-layer.md) section 13; [`ebene-statische-analyse-und-security`](../research/ebene-statische-analyse-und-security.md) sections 1, 3.2.
