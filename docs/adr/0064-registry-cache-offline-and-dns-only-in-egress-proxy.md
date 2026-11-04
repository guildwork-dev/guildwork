<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-64: Registry cache offline, DNS only in the egress proxy

- Status: Accepted
- Group: ADR-59 to ADR-65 (Red Team on the overall idea, package security of autonomous effects, 2026-10-31)

## Context

Background: The basis is findings 4, 5, 6, 7, 11, 12, and 13 of the Red Team on the overall idea and the ruling R-D of the project of 2026-10-31 (autonomous effects on public repos only once agent branches run like fork code and provenance and stale-approve conditions apply).

A pull-through cache and free DNS resolution carry data outward via package, module, or host names, against the gate "0 exfiltration" (Red Team finding 12; Go proxy mechanism known, unverified for this setup)

## Decision

**Registry cache offline, DNS only in the egress proxy:** In the agent phase the cache only delivers artifacts that were loaded from the lockfile in the setup phase, and never resolves upstream; a new dependency is the write request `propose_dependency`, which the worker fulfills outside the sandbox only with a name allowlist (`security.dependencies.allow`) and a green osv check, otherwise a follow-up question; the sandbox has no DNS resolver

## Alternatives

Pull-through cache "read only" (version until 2026-10-31); loading on demand in the agent phase with osv check

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.4, row ADR-64; references: [05](../architecture/05-security.md) sections 3 and 6; [02](../architecture/02-services.md) section 0; [04](../architecture/04-configuration-and-limits.md) section 3; [07](../architecture/07-eval.md) S1.
