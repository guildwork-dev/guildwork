<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-62: Zone separation on single-host

- Status: Accepted
- Group: ADR-59 to ADR-65 (Red Team on the overall idea, package security of autonomous effects, 2026-10-31)

## Context

Background: The basis is findings 4, 5, 6, 7, 11, 12, and 13 of the Red Team on the overall idea and the ruling R-D of the project of 2026-10-31 (autonomous effects on public repos only once agent branches run like fork code and provenance and stale-approve conditions apply).

On the standard path of stage 0, a sandbox escape via the Docker API would otherwise have reached `secrets/`, Postgres, and a subscription token; the promise "a compromised worker has no DB connection" would not hold (Red Team finding 7); the socket mount is named in the research as a counterexample ([`hosting-und-installation`](../research/hosting-und-installation.md) section 2.1); whether Sysbox runs with a rootless daemon is unverified

## Decision

**Zone separation on `single-host`:** The worker never gets the Docker socket of the control plane; the default is a socket proxy that only allows create, start, stop, and remove and on create checks a fixed runtime, only the sandbox network, no host paths, no `privileged`, no capabilities, no host network; alternatively a separate rootless daemon under its own user after a contract test. Worker without network access to Postgres and SeaweedFS, without `secrets/` and `.env`, access to the control plane only via the reverse proxy; sandbox networks `internal` with the egress proxy as the only exit. `doctor` checks this; residual risk as a separate paragraph in [05](../architecture/05-security.md) section 1; for `external_code` and multi-user operation, workers on a second VM recommended

## Alternatives

Docker socket in the worker container (OpenHands pattern); worker on the same Docker network as the control plane (version until 2026-10-31, not regulated)

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.4, row ADR-62; references: [05](../architecture/05-security.md) section 1; [06](../architecture/06-operations-and-deployment.md) section 2; [11](../architecture/11-installation-and-hosting.md) sections 2.2 and 2.4; [07](../architecture/07-eval.md) S6.
