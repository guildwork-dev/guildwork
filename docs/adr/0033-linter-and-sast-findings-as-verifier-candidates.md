<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-33: Linter and SAST findings as verifier candidates

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

Common dedupe and verification reduces noise ([02](../architecture/02-services.md) section 4)

## Decision

Linter and SAST findings run as plugin kind `Analyzer` (ADR-40) and are candidates for the reviewer's verifier, deduplicated together with LLM findings; convention findings only with a verbatim quote at the base SHA; inline only P0 and P1; the verifier assigns the evidence level

## Alternatives

Linter as a separate workflow without relation to the review (version until 2026-10-31)

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-33.
