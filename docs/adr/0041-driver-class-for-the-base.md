<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-41: Driver class for the base

- Status: Accepted
- Group: ADR-37 to ADR-53 (third round, 2026-10-31)

## Context

The base must be interchangeable, and every installation runs with `fs`, `file`, and `self-issuer` without a cloud account (DERIVED); a queue port invites a second state store (ADR-02); OIDC is a standard, not a third-party system

## Decision

**Driver class** for the base: `BlobStore` (`fs`, `s3`, `azure-blob`, later `gcs`), `SecretStore` (`file`, `env`, `azure-keyvault`, later `aws-secretsmanager`, `gcp-secretmanager`, `openbao`), `CloudIdentity` (`self-issuer`, `azure-managed-identity`, later `aws`, `gcp`, `k8s-projected-token`); same framework as plugins (manifest, capabilities, contract suite), counted separately. **No queue port** (Postgres with pg-boss remains), **no database abstraction** (only PostgreSQL with pgvector); SSO of the admin UI via a generic OIDC client plus emergency admin, no plugin

## Alternatives

Storage and secrets as plugin kinds; cloud services directly in the core; queue or DB port for interchangeability

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.2, row ADR-41; references: [01](../architecture/01-plugin-interfaces.md) section 13; [11](../architecture/11-installation-and-hosting.md) section 4; [`hosting-und-installation`](../research/hosting-und-installation.md) section 3.1.
