<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-22: Credential broker with SecretStore and CloudIdentity

- Status: Accepted
- Group: ADR-01 to ADR-36

## Context

few machine secrets; every base has a path without a cloud requirement (ADR-41); WIF with inline JWKS ([an-wif] VERIFIED); `--bare` does not read federation variables ([cc-auth] VERIFIED); an agent with a shell and foreign content must not see a long-lived credential ([05](../architecture/05-security.md) section 3)

## Decision

The credential broker reads and writes machine secrets via the driver `SecretStore` (`file`, `env` read only, `azure-keyvault`; later `aws-secretsmanager`, `gcp-secretmanager`, `openbao`); OIDC signing key via capability `SIGN` where available. LLM access without static keys via `CloudIdentity` (`self-issuer` as its own OIDC issuer for WIF, later cloud identities). WIF exchange in the worker, LLM credential only in the credential relay of the egress proxy, in the sandbox only a placeholder (exception subscription, only without a shell except profile `operator_test`)

## Alternatives

Vault immediately; federation variables directly to `claude` (does not work with `--bare`)

## Consequences

No separate list of affected documents is recorded for this decision; the affected documents are referenced in Context and Decision.

## Source

[09](../architecture/09-decisions.md) section 2.1, row ADR-22.
