<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# Guildwork detailed design

The detailed design makes the architecture ([../architecture/](../architecture/README.md)) buildable: packages and modules, interfaces as TypeScript types, database schema, endpoints, state tables, failure paths, and test cases. An agent should be able to build a task of the work plan ([../plan/](../plan/README.md)) from the architecture, the detailed design, and the task, without re-deciding fundamental questions.

Precedence: architecture decisions (ADRs and owner decisions in [09](../architecture/09-decisions.md)) take precedence. The detailed design decides only what the architecture leaves open, and records each such decision as a **Ruling FE-nn** with its reason (section 4). Source keys and classifications (VERIFIED, DERIVED, unverified) as in the [architecture README](../architecture/README.md).

## 1. Documents

| File | Content | Stages |
|---|---|---|
| [00-codebase-and-conventions.md](00-codebase-and-conventions.md) | Monorepo, packages, toolchain, code conventions, errors, logging, tests, `make` targets, CI | R, 0 |
| [01-data-model.md](01-data-model.md) | Postgres schema of all tables with DDL, indexes, migrations, retention | 0 and later |
| [02-control-plane.md](02-control-plane.md) | Ingress, inbox, router, orchestrator with run state machine, config resolver, policy, limit ledger | 0 |
| [03-execution.md](03-execution.md) | Work API, platform MCP, worker, sandbox, socket proxy, egress proxy, credential relay | 0 |
| [04-effects-audit-credentials.md](04-effects-audit-credentials.md) | Effect gateway, outbox, audit chain, credential broker, drivers | 0 |
| [05-plugins-and-contracts.md](05-plugins-and-contracts.md) | Plugin framework, contracts `v1alpha1` as types, contract harness, GitHub plugin, `claude-code`, ModelProvider, credential paths | 0, 1 |
| [06-installation-operations-ui.md](06-installation-operations-ui.md) | Images, Compose bundle, installer CLI, admin UI, observability, release, OpenTofu | 0, 0b, 1 |
| [07-eval-and-qualification.md](07-eval-and-qualification.md) | Eval runner, adapters, statistics, gates A and B, qualification matrix, suites S1 to S8 | 0 and later |
| [08-reviewer.md](08-reviewer.md) | Reviewer: gate, context, finder, verifier, findings, increment, output, prompts | 1 |
| [09-reviewer-companion-features-and-learnings.md](09-reviewer-companion-features-and-learnings.md) | Walkthrough, pre-merge checks, chat, local review, analytics, auto-approve, Learnings | 6, 7a |
| [10-planner-architect-coder.md](10-planner-architect-coder.md) | Shared agent building blocks, planner, architect, coder, agent CI, `ticket-to-pr` | 2 |
| [11-qa-prfix-automerge.md](11-qa-prfix-automerge.md) | QA, PR fixer, merge gate, autonomous end-to-end run | 3, 4, 5 |
| [12-expansion.md](12-expansion.md) | Knowledge base, standards, triage; for stage 8 only references to 13, for stage 9 only references to 14, for stage 10 only references to 15 and the rulings FE-1236 to FE-1241, FE-1249 | 7 |
| [13-stage-8-providers-and-bases.md](13-stage-8-providers-and-bases.md) | Jira Cloud, identity linking, rights AND, providers `wif`, `bedrock`, `vertex`, `foundry`, harness `codex`, drivers, Helm with backend `k8s`, OpenTofu `aws`, `gcp`, `hetzner`, `ci-dispatch`, price tables, acceptance | 8 |
| [14-stage-9-breadth-and-hardening.md](14-stage-9-breadth-and-hardening.md) | Further code hosts, Linear and notifiers, harnesses, MicroVM and pen test, third-party plugins and services, handoff, child runs, best-of-N, injection detector, SARIF upload, Zoekt, Confluence, acceptance | 9 |
| [15-stage-10-edge-layers.md](15-stage-10-edge-layers.md) | Service `docs`, PR fixer modes `dependency_update` and `ci_doctor`, executor `issue`, intake `incident-handoff` and `sentry`, analyzers axe-core, Infracost and git-cliff, campaigns, acceptance | 10 |
| [components/](components/README.md) | Component catalog: one file `<id>.toml` per component with purpose, path, stage, provided interfaces, docking points (`uses`) and building tasks; `plan.py check` checks it against the plan and the detailed design (decisions KE-1 to KE-5 in the [draft](../plan/catalog-and-issues-draft.md)) | all |
| [build-book.md](build-book.md) | **Generated** by `plan.py generate`, never by hand: the whole tool in build order (per stage the components, from which task on which interface is available, who docks on) and per component the component sheet; `plan.py check` fails if it is not up to date | all |

## 2. Rules for all documents

These rules apply project-wide; [00](00-codebase-and-conventions.md) elaborates them. Licenses are checked in stage R together with the choice of tools (`toolchain.md`, [12](../architecture/12-open-source-and-project.md) section 5.2); if one fails the license gate, it is replaced there.

| Topic | Rule | Reason |
|---|---|---|
| Language, runtime | TypeScript `strict`, ESM, Node 22 LTS (ADR-03) | Architecture |
| Monorepo | pnpm workspaces; packages under `packages/`, programs under `apps/`, plugins under `plugins/`, drivers under `drivers/`, services under `services/`, eval under `eval/`, delivery under `deploy/`, check tools under `tools/` | one repo, shared types, one `make check` |
| HTTP | Fastify | schemas as JSON Schema, fast, MIT |
| Schemas | TypeBox for types and JSON Schema, Ajv for validation; the same schema for API, configuration, manifests, and work item envelopes | one schema, two uses (type and validation) |
| Database | PostgreSQL 17 or newer with `pgvector` (minimum version FE-100, as in [11](../architecture/11-installation-and-hosting.md)); Kysely for typed SQL; migrations as SQL files with a custom migrator (forward only, expand/contract) | Architecture (stage 0), no ORM magic |
| Queue | pg-boss (ADR-03) | Architecture |
| Tests | Vitest; Postgres in tests as a real container (Testcontainers) or a local service, never mocked; third-party HTTP responses as recorded fixtures | behavior against the real artifact |
| Format and lint | Biome; `tsc --noEmit`; plus ESLint with only a few type-aware rules (FE-002) | one tool for format and style; floating promises are checked only by ESLint with type information (FE-002) |
| Logging | pino, structured, with redaction of secrets; OpenTelemetry SDK for traces and metrics (ADR-21) | Architecture |
| Admin UI | React with Vite as an SPA, served by the role `web` | widely used, easy to self-host |
| Check tools | Python 3.12 with ruff and mypy, standard library only where possible ([12](../architecture/12-open-source-and-project.md) section 5.2) | as in the reference project |

**Package names** (scope `@guildwork/`; packages under `packages/` and `apps/` are named after their directory, plugins `plugin-<name>` ([05](05-plugins-and-contracts.md) FE-533), drivers `driver-<name>`, services `service-<name>` ([10](10-planner-architect-coder.md) section 2.1), eval `eval-<name>` ([07](07-eval-and-qualification.md) FE-701)): `core` (IDs, errors, result types, time, hash and canonical JSON, logging facade), `contracts` (plugin contracts `v1alpha1`, manifest schema, event schema, work item envelope), `config` (schema and resolver of the configuration, qualification profile), `db` (Kysely types, migrator, migrations, repositories), `telemetry` (start of the OTel SDK per role, FE-008), `testkit` (fixtures, container helpers, contract harness), `sdk-service` (building blocks for services: step API, work item envelope, platform MCP client); from stage 2 `agent-step`, `blueprint`, `registry-cache`, `clarity`, `method-check`, `sarif`, `quality-gate`, `workflow-guard` (FE-1000); from stage 7 `kb`, `kb-indexer`, `guidelines` (extracted from `@guildwork/service-reviewer/guidelines`, [08](08-reviewer.md) FE-807); from stage 8 `adf`, `pricing`; from stage 9 `plugin-host` ([12](12-expansion.md) section 2.0) and `scm-common` (pure host helpers for all SCM plugins, [14](14-stage-9-breadth-and-hardening.md) FE-1402). Programs `apps/control-plane` (roles `web`, `orchestrator`, `migrate`), `apps/worker`, `apps/egress-proxy` (FE-301), `apps/cli` (command `guildwork`), `apps/admin-ui`; plugins `plugins/github`, `plugins/claude-code`, `plugins/model-anthropic`, `plugins/model-claude-cli`, `plugins/exec-docker` (FE-301), more later ([10](10-planner-architect-coder.md) section 2.1, [12](12-expansion.md) section 2.0); drivers `drivers/blob-fs`, `drivers/blob-s3`, `drivers/secret-file`, `drivers/secret-env`, `drivers/identity-self-issuer` (later `drivers/blob-azure`, `drivers/secret-azure-keyvault`, etc.); services `services/dummy`, `services/reviewer` (`@guildwork/service-reviewer`), later `services/planner` (`@guildwork/service-planner`), etc.; eval `eval/core` (`@guildwork/eval-core`), `eval/runner` (`@guildwork/eval-runner`), `eval/adapters/*` (`@guildwork/eval-adapter-<name>`), `eval/suites` (`@guildwork/eval-suites`) per FE-701; `deploy/compose`, `deploy/tofu/<module>`, later `deploy/helm`.

If a document deviates from this, the deviation is recorded as a ruling with its reason in the document and in [00](00-codebase-and-conventions.md).

## 3. Structure of each document

1. **Purpose and sources:** which architecture sections and ADRs it implements.
2. **Modules and responsibility:** package, directories, public interfaces (TypeScript types in a code block), who calls whom.
3. **Data:** tables and columns used (reference to [01](01-data-model.md)), message and envelope formats.
4. **Flows:** sequences (Mermaid), states and transitions as a table.
5. **Failure and abort paths:** for each failure, what is stored, audited, and logged, and what the user sees.
6. **Security:** trust boundaries, rights, secrets.
7. **Configuration:** keys with type, default, and effect (reference to [04](../architecture/04-configuration-and-limits.md)).
8. **Tests:** test cases per module with names that cite the done criteria of the work plan; contract and suite cases.
9. **Rulings:** decisions of this document (FE-nn), each with its reason and the rejected alternative.
10. **Open points:** what is clarified during the build, with the task that clarifies it.

## 4. Rulings

Rulings carry project-wide unique numbers in blocks per document: 00 has FE-001 to FE-099, 01 FE-100 to FE-199, 02 FE-200 to FE-299, and so on (document `nn` has FE-`nn`00 to FE-`nn`99).
