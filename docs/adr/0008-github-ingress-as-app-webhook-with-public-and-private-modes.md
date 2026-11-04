<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-08: GitHub ingress as app webhook with modes public and private

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

In `public` the control plane is reachable for the Work API anyway; `ci_event` occupies one runner slot per event; a webhook endpoint barely increases the attack surface (signature before parsing). `private` covers installations behind NAT ([11](../architecture/11-installation-and-hosting.md) section 1.1). Where the control plane runs is decided by the operator

## Decision

GitHub ingress as app webhook to the control plane, `reconcile` mandatory; `relay` and `ci_event` as modes. Two operating modes: `public` (public HTTPS address, default) and `private` (no public ingress, only `poll` and `reconcile`, workers in the same network; ingress plugin without `POLL` cannot be loaded)

## Alternatives

only `ci_event` (drafts); public ingress as a requirement

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-08.
