<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-48: Isolation with a minimum per repo class

- Status: Accepted
- Group: ADR-37 to ADR-53 (third round, 2026-10-31)

## Context

Sysbox has "best effort" support, "not officially supported by Docker" ([sysbox] VERIFIED); gVisor `systrap` runs on any Linux VM without virtualization ([gvisor-plat] VERIFIED); Fargate and Container Apps do not allow privileged containers, Hetzner Cloud according to a third-party report offers no `/dev/kvm` ([fargate] VERIFIED, [aca-priv], [hz-kvm] CLAIMED)

## Decision

**Isolation:** gVisor equivalent to Sysbox for our own code; MicroVM (Firecracker or Kata) mandatory for repo code of the class with foreign code (stage 9); **minimum isolation per repo class** via the policy; at `claim` the pool reports its **self-checked** capabilities, the report takes precedence over the configuration; without a matching pool the item stays with reason `no_qualified_pool` and never falls back to a weaker level. Replaces ADR-19

## Alternatives

Sysbox as the only standard isolation; isolation according to configuration

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.2, row ADR-48; references: [01](../architecture/01-plugin-interfaces.md) section 8; [05](../architecture/05-security.md) section 3; [11](../architecture/11-installation-and-hosting.md) section 3; [`hosting-und-installation`](../research/hosting-und-installation.md) section 2.8.
