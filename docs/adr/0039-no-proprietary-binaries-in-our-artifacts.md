<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-39: No proprietary binaries in our artifacts

- Status: Accepted
- Group: ADR-37 to ADR-53 (third round, 2026-10-31)

## Context

Source [cc-legal]: "preinstalling or running Claude Code in your products or services ... requires agreeing to our Commercial Terms of Service"; "The Claude Code binary must not be modified." (VERIFIED); npm packages "All rights reserved" ([cc-npm], [sdk-npm] VERIFIED); the SDK platform packages contain the native CLI (VERIFIED, cross-check item 7); the main package itself is "© Anthropic PBC. All rights reserved" (npm registry 0.3.316 "SEE LICENSE IN README.md", [sdk-npm] VERIFIED; Red Team on the overall idea finding 10). Gate test in the license gate: an image with the SDK package is red

## Decision

**No proprietary binaries** in our artifacts: neither Claude Code nor the Agent SDK `@anthropic-ai/claude-agent-sdk` nor its platform packages in the image. Forbidden are the packages npm `@anthropic-ai/claude-code`, `@anthropic-ai/claude-code-*` (platform packages with native binary), `@anthropic-ai/claude-agent-sdk*` and PyPI `claude-agent-sdk` (bundles the CLI) and `claude-code-sdk` (names checked 2026-11-01 in R-E02-T06; name lists `FORBIDDEN_NPM` and `FORBIDDEN_PYPI` in the license gate, detailed design 00 section 2.10); no package of the project depends on the Agent SDK, the adapter `claude-code` starts the CLI via `claude -p`; if an adapter needed the SDK, it is `operator_supplied` like the CLI; the worker installs the harness at the operator with a pinned version and checksum (in air-gap mode from the operator's mirror); `distribution: bundled` never for proprietary software

## Alternatives

Image with preinstalled `claude`; ship the SDK including platform packages

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.2, row ADR-39; references: [11](../architecture/11-installation-and-hosting.md) section 2.1; [06](../architecture/06-operations-and-deployment.md) section 8; [01](../architecture/01-plugin-interfaces.md) section 1.1 rule 7.
