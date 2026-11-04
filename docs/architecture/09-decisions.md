<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# 09 Decisions

Source keys and classifications as in the [README](README.md). This file is the index of the platform's architecture decisions (ADR); each ADR is a separate file in MADR form under `docs/adr/` ([12](12-open-source-and-project.md) section 8). The owner decisions of the project are in `docs/DECISIONS.md`. Decisions of a specific installation are in the private ops repo of its operator (ADR-38); those of the reference installation are there as well (private, not part of the public repo).

Statements about contracts and licenses are not legal advice, but the reading of the quoted texts with references ([12](12-open-source-and-project.md) section 7).

## 1. Origin of the architecture

**Ruling on the base:** The two reviewers of the architecture round chose different winners (reviewer 1: plugin-core 82, ops-lean 78, secure-quality 74; reviewer 2: secure-quality 84, plugin-core 80, ops-lean 70). The base is **plugin-core** (highest sum, 162 against 158 and 148; both reviewers adopt its contracts, finding DB, and subscription rules). All grafts of both reviewers are incorporated.

**Grafts and where they are:**

| Graft | Source | File |
|---|---|---|
| `mode: off, shadow, live` and qualification matrix | secure-quality | 02 section 0, 07 section 2 |
| SCMProvider without `approve` and `merge`, write methods only with a gateway token, permission profiles per effect, effect bound to a command | secure-quality | 01 section 5, 05 section 2 |
| Cross-cutting suites (today S1 to S8), `data_policy` per repo class | secure-quality | 07 section 5, 04 section 3 |
| Sandbox lifecycle (create, exec with role, copyIn/copyOut, snapshot, destroy in the failure path, denyReadPaths) | ops-lean | 01 section 8 |
| `Untrusted<T>` as a type | ops-lean | 01 sections 1.1, 2, 4, 5 |
| Ticket-to-repo mapping | ops-lean | 04 section 3 |
| lean stage 0 with dummy service, weekly estimates | ops-lean | 08 |
| one status comment per ticket and PR, `stop` with lease revocation, `continue`, admin UI behind SSO, network outage of a pool, retention starting values | ops-lean | 03, 05, 06 |
| Manifest with trust, transport, egress, contractSuite; Result and PluginError; CapabilitySet native, fallback, none | plugin-core | 01 section 1 |
| Finding state in the DB, markers only anchors; `finding_feedback` | plugin-core | ADR-11 |
| `effects` with idempotency key and `provider_request_id`; `expectedOldSha` | plugin-core | 01, 03 |
| Subscription token never over the network; `identity_links` only via OAuth confirmation | plugin-core | 05 sections 6 and 7 |
| `on_disabled`, diff of the effective configuration for config PRs (G2 not switchable and `merge.allowed: false` superseded by `merge.mode` and merge gate, ADR-36) | plugin-core | 03, 04 |
| Rule version on every stored value, secret scan before storage, PITR test per stage | ops-lean | 02 section 0, 05, 06 |
| Gate B against the standard of the field | reviewer 2 (all drafts) | 10, ADR-47 |

**Blockers of the reviewers and their resolution:**

| Blocker | Resolution |
|---|---|
| Stage 0 overloaded | Stage 0 only core, drivers, installation package plus dummy service; only the named contracts binding ([08](08-roadmap.md)) |
| ExecutionBackend without sandbox lifecycle | Contract added, `destroy` in the failure path with test ([01](01-plugin-interfaces.md) section 8) |
| CI-only stage without control plane (secure-quality V4) | not adopted; topology "offline eval" only as eval and offline mode, never live (ADR-27) |
| Pool on a production host of the operator (ops-lean) | not adopted; control plane and workers never on hosts that carry other production ([06](06-operations-and-deployment.md) section 2) |
| Subscription also for triggers "approved" by the operator | Triggers exclusively by the operator, test S2 ([05](05-security.md) section 6) |
| `allowed_regions: [eu]` collides with `region: global` in the example | Example consistent, check at configuration load plus test S2 ([04](04-configuration-and-limits.md)) |
| Live operation without ledger, policy, limits | Ledger, policy, and limits are part of stage 0; no live or shadow run without them ([08](08-roadmap.md) principle 4) |
| `submitReview` with `approve` | removed from the contract; since O24 only a separate optional method `approve` for human PRs, never for agent PRs (ADR-14, [01](01-plugin-interfaces.md) section 5) |
| Credential of the MCP sidecar unclear | Platform MCP in the control plane, item token only for one work item with read and `propose_*` rights; pool key never in the sandbox ([05](05-security.md) section 2) |
| no gate "level of the best vendor" | Gate B per service with required parts and reference values ([10](10-standards-per-layer.md)); `live` without green Gate B only via a visibly marked deviation (ADR-47). The earlier rule "without a measurable Gate B, Gate A suffices" is revoked |

## 2. ADR list

One row per ADR with number, title, status, and file. Decision, alternatives, rationale, and references are in the ADR file.

### 2.1 ADR-01 to ADR-36

| # | Title | Status | File |
|---|---|---|---|
| ADR-01 | Base plugin-core with all grafts | Accepted | [0001-base-plugin-core-with-all-grafts.md](../adr/0001-base-plugin-core-with-all-grafts.md) |
| ADR-02 | Single control plane with Postgres as the only state | Accepted | [0002-single-control-plane-with-postgres-as-only-state.md](../adr/0002-single-control-plane-with-postgres-as-only-state.md) |
| ADR-03 | TypeScript on Node 22+ | Accepted | [0003-typescript-on-node-22.md](../adr/0003-typescript-on-node-22.md) |
| ADR-04 | Own versioned state machine in Postgres with pg-boss | Accepted | [0004-own-versioned-state-machine-in-postgres-with-pg-boss.md](../adr/0004-own-versioned-state-machine-in-postgres-with-pg-boss.md) |
| ADR-05 | Pull workers with long poll and lease | Accepted | [0005-pull-workers-with-long-poll-and-lease.md](../adr/0005-pull-workers-with-long-poll-and-lease.md) |
| ADR-06 | Effect Gateway as the single write point | Accepted | [0006-effect-gateway-as-single-write-point.md](../adr/0006-effect-gateway-as-single-write-point.md) |
| ADR-07 | Platform MCP in the control plane with item token | Accepted | [0007-platform-mcp-in-control-plane-with-item-token.md](../adr/0007-platform-mcp-in-control-plane-with-item-token.md) |
| ADR-08 | GitHub ingress as app webhook with modes public and private | Accepted | [0008-github-ingress-as-app-webhook-with-public-and-private-modes.md](../adr/0008-github-ingress-as-app-webhook-with-public-and-private-modes.md) |
| ADR-09 | Nine plugin kinds | Accepted | [0009-nine-plugin-kinds.md](../adr/0009-nine-plugin-kinds.md) |
| ADR-10 | Fixed capability enums with fallback chains | Accepted | [0010-fixed-capability-enums-with-fallback-chains.md](../adr/0010-fixed-capability-enums-with-fallback-chains.md) |
| ADR-11 | Finding state in the database | Accepted | [0011-finding-state-in-the-database.md](../adr/0011-finding-state-in-the-database.md) |
| ADR-12 | pg-kb as the default KnowledgeStore | Accepted | [0012-pg-kb-as-default-knowledge-store.md](../adr/0012-pg-kb-as-default-knowledge-store.md) |
| ADR-13 | AgentRuntime as a plugin with two axes | Accepted | [0013-agent-runtime-as-plugin-with-two-axes.md](../adr/0013-agent-runtime-as-plugin-with-two-axes.md) |
| ADR-14 | Optional approve and merge in the SCM contract | Accepted | [0014-optional-approve-and-merge-in-the-scm-contract.md](../adr/0014-optional-approve-and-merge-in-the-scm-contract.md) |
| ADR-15 | Qualification matrix with off, shadow, live per service | Accepted | [0015-qualification-matrix-with-off-shadow-live.md](../adr/0015-qualification-matrix-with-off-shadow-live.md) |
| ADR-16 | Own limit ledger with reservation | Accepted | [0016-own-limit-ledger-with-reservation.md](../adr/0016-own-limit-ledger-with-reservation.md) |
| ADR-17 | Configuration, rules, and agent files from the base SHA | Accepted | [0017-configuration-rules-and-agent-files-from-the-base-sha.md](../adr/0017-configuration-rules-and-agent-files-from-the-base-sha.md) |
| ADR-18 | Credential kind subscription only as a personal operator mode | Accepted | [0018-subscription-credential-only-as-personal-operator-mode.md](../adr/0018-subscription-credential-only-as-personal-operator-mode.md) |
| ADR-19 | Sysbox container per work item | Superseded by ADR-48 | [0019-sysbox-container-per-work-item.md](../adr/0019-sysbox-container-per-work-item.md) |
| ADR-20 | Egress proxy with allowlist per service | Accepted | [0020-egress-proxy-with-allowlist-per-service.md](../adr/0020-egress-proxy-with-allowlist-per-service.md) |
| ADR-21 | OTel SDK and collector with own required alerts | Accepted | [0021-otel-sdk-and-collector-with-own-required-alerts.md](../adr/0021-otel-sdk-and-collector-with-own-required-alerts.md) |
| ADR-22 | Credential broker with SecretStore and CloudIdentity | Accepted | [0022-credential-broker-with-secret-store-and-cloud-identity.md](../adr/0022-credential-broker-with-secret-store-and-cloud-identity.md) |
| ADR-23 | Data path per repo class enforced | Accepted | [0023-data-path-per-repo-class-enforced.md](../adr/0023-data-path-per-repo-class-enforced.md) |
| ADR-24 | Untrusted type for all foreign content | Accepted | [0024-untrusted-type-for-all-foreign-content.md](../adr/0024-untrusted-type-for-all-foreign-content.md) |
| ADR-25 | Host exclusion moved to the reference installation | Moved to the reference installation | [0025-host-exclusion-moved-to-reference-installation.md](../adr/0025-host-exclusion-moved-to-reference-installation.md) |
| ADR-26 | Roadmap stages | Accepted | [0026-roadmap-stages.md](../adr/0026-roadmap-stages.md) |
| ADR-27 | CI-only topology only as eval and offline mode | Accepted | [0027-ci-only-topology-only-for-eval-and-offline-mode.md](../adr/0027-ci-only-topology-only-for-eval-and-offline-mode.md) |
| ADR-28 | Gate A and Gate B per service | Accepted | [0028-gate-a-and-gate-b-per-service.md](../adr/0028-gate-a-and-gate-b-per-service.md) |
| ADR-29 | Hash-chained audit with daily anchor outside the database | Accepted | [0029-hash-chained-audit-with-daily-anchor.md](../adr/0029-hash-chained-audit-with-daily-anchor.md) |
| ADR-30 | Runner pool slot limit moved to the reference installation | Moved to the reference installation | [0030-runner-pool-slot-limit-moved-to-reference-installation.md](../adr/0030-runner-pool-slot-limit-moved-to-reference-installation.md) |
| ADR-31 | ModelProvider as thin adapters on the Vercel AI SDK | Accepted | [0031-model-provider-as-thin-adapters-on-the-vercel-ai-sdk.md](../adr/0031-model-provider-as-thin-adapters-on-the-vercel-ai-sdk.md) |
| ADR-32 | Commands as text mentions with a configurable handle | Accepted | [0032-commands-as-text-mentions-with-configurable-handle.md](../adr/0032-commands-as-text-mentions-with-configurable-handle.md) |
| ADR-33 | Linter and SAST findings as verifier candidates | Accepted | [0033-linter-and-sast-findings-as-verifier-candidates.md](../adr/0033-linter-and-sast-findings-as-verifier-candidates.md) |
| ADR-34 | No AGPL, EE, or noncommercial code in the product | Accepted | [0034-no-agpl-ee-or-noncommercial-code-in-the-product.md](../adr/0034-no-agpl-ee-or-noncommercial-code-in-the-product.md) |
| ADR-35 | Autonomous run as a chain of specialized services | Accepted | [0035-autonomous-run-as-chain-of-specialized-services.md](../adr/0035-autonomous-run-as-chain-of-specialized-services.md) |
| ADR-36 | Optional auto-merge via a deterministic merge gate | Accepted | [0036-optional-auto-merge-via-deterministic-merge-gate.md](../adr/0036-optional-auto-merge-via-deterministic-merge-gate.md) |

### 2.2 ADR-37 to ADR-53 (third round, 2026-10-31)

| # | Title | Status | File |
|---|---|---|---|
| ADR-37 | Apache-2.0 license with DCO | Accepted | [0037-apache-2-0-license-with-dco.md](../adr/0037-apache-2-0-license-with-dco.md) |
| ADR-38 | Two repos: product repo and ops repo | Accepted | [0038-two-repos-product-and-ops.md](../adr/0038-two-repos-product-and-ops.md) |
| ADR-39 | No proprietary binaries in our artifacts | Accepted | [0039-no-proprietary-binaries-in-our-artifacts.md](../adr/0039-no-proprietary-binaries-in-our-artifacts.md) |
| ADR-40 | Analyzer plugin kind and platform gate on new code | Accepted | [0040-analyzer-plugin-kind-and-platform-gate-on-new-code.md](../adr/0040-analyzer-plugin-kind-and-platform-gate-on-new-code.md) |
| ADR-41 | Driver class for the base | Accepted | [0041-driver-class-for-the-base.md](../adr/0041-driver-class-for-the-base.md) |
| ADR-42 | Installation ladder | Accepted | [0042-installation-ladder.md](../adr/0042-installation-ladder.md) |
| ADR-43 | No MinIO | Accepted | [0043-no-minio.md](../adr/0043-no-minio.md) |
| ADR-44 | Product telemetry off by default and air-gap mode | Accepted | [0044-telemetry-off-by-default-and-air-gap-mode.md](../adr/0044-telemetry-off-by-default-and-air-gap-mode.md) |
| ADR-45 | GitHub App via manifest flow | Accepted | [0045-github-app-via-manifest-flow.md](../adr/0045-github-app-via-manifest-flow.md) |
| ADR-46 | New services architect, triage, and docs | Accepted | [0046-new-services-architect-triage-and-docs.md](../adr/0046-new-services-architect-triage-and-docs.md) |
| ADR-47 | Live requires Gate A and Gate B or an adopted reference qualification | Accepted | [0047-live-requires-gate-a-and-gate-b.md](../adr/0047-live-requires-gate-a-and-gate-b.md) |
| ADR-48 | Isolation with a minimum per repo class | Accepted | [0048-isolation-with-minimum-per-repo-class.md](../adr/0048-isolation-with-minimum-per-repo-class.md) |
| ADR-49 | No own SRE agent | Accepted | [0049-no-own-sre-agent.md](../adr/0049-no-own-sre-agent.md) |
| ADR-50 | Bundled third-party tools and rules only with a free license | Accepted | [0050-bundled-tools-and-rules-only-with-free-license.md](../adr/0050-bundled-tools-and-rules-only-with-free-license.md) |
| ADR-51 | Credential kinds subscription and chatgpt only as a personal operator mode | Accepted | [0051-subscription-and-chatgpt-only-as-personal-operator-mode.md](../adr/0051-subscription-and-chatgpt-only-as-personal-operator-mode.md) |
| ADR-52 | Public eval sets and reference qualification | Accepted | [0052-public-eval-sets-and-reference-qualification.md](../adr/0052-public-eval-sets-and-reference-qualification.md) |
| ADR-53 | Planning docs in German, public docs in English from publication | Accepted | [0053-planning-docs-in-german-public-docs-in-english.md](../adr/0053-planning-docs-in-german-public-docs-in-english.md) |

### 2.3 ADR-54 to ADR-58 (Red Team on the overall idea, 2026-10-31)

The basis is the rulings R-A to R-C of the project of 2026-10-31 (the owner handed all open points over to the project) and findings 1, 17, 18, and 19 of the Red Team on the overall idea; ADR-57 and ADR-58 come from findings 2 and 3 (package LLM runtime and subscription operation).

| # | Title | Status | File |
|---|---|---|---|
| ADR-54 | Roadmap as a dependency graph, core first | Accepted | [0054-roadmap-as-dependency-graph-core-first.md](../adr/0054-roadmap-as-dependency-graph-core-first.md) |
| ADR-55 | Done criterion without a Gate B block | Accepted | [0055-done-criterion-without-gate-b-block.md](../adr/0055-done-criterion-without-gate-b-block.md) |
| ADR-56 | Gate B as a measurement target with a statistics rule | Accepted | [0056-gate-b-as-measurement-target-with-statistics-rule.md](../adr/0056-gate-b-as-measurement-target-with-statistics-rule.md) |
| ADR-57 | Start path of the credential kind subscription | Accepted | [0057-start-path-of-the-subscription-credential.md](../adr/0057-start-path-of-the-subscription-credential.md) |
| ADR-58 | ModelProvider claude-cli for subscription operation | Accepted | [0058-claude-cli-model-provider-for-subscription-operation.md](../adr/0058-claude-cli-model-provider-for-subscription-operation.md) |

### 2.4 ADR-59 to ADR-65 (Red Team on the overall idea, package security of autonomous effects, 2026-10-31)

The basis is findings 4, 5, 6, 7, 11, 12, and 13 of the Red Team on the overall idea and the ruling R-D of the project of 2026-10-31 (autonomous effects on public repos only once agent branches run like fork code and provenance and stale-approve conditions apply).

| # | Title | Status | File |
|---|---|---|---|
| ADR-59 | CI on agent branches like fork code | Accepted | [0059-ci-on-agent-branches-like-fork-code.md](../adr/0059-ci-on-agent-branches-like-fork-code.md) |
| ADR-60 | Provenance as a condition of auto-merge | Accepted | [0060-provenance-as-a-condition-of-auto-merge.md](../adr/0060-provenance-as-a-condition-of-auto-merge.md) |
| ADR-61 | Conditions for approving human PRs | Accepted | [0061-conditions-for-approving-human-prs.md](../adr/0061-conditions-for-approving-human-prs.md) |
| ADR-62 | Zone separation on single-host | Accepted | [0062-zone-separation-on-single-host.md](../adr/0062-zone-separation-on-single-host.md) |
| ADR-63 | Visibility rule across repo boundaries | Accepted | [0063-visibility-rule-across-repo-boundaries.md](../adr/0063-visibility-rule-across-repo-boundaries.md) |
| ADR-64 | Registry cache offline, DNS only in the egress proxy | Accepted | [0064-registry-cache-offline-and-dns-only-in-egress-proxy.md](../adr/0064-registry-cache-offline-and-dns-only-in-egress-proxy.md) |
| ADR-65 | Fail closed on an invalid config file | Accepted | [0065-fail-closed-on-invalid-config-file.md](../adr/0065-fail-closed-on-invalid-config-file.md) |

### 2.5 ADR-66 to ADR-70 (Red Team on the overall idea, package architecture and law, 2026-10-31)

The basis is findings 8, 9, 14, 15, and 16 of the Red Team on the overall idea and the ruling R-E of the project of 2026-10-31 (the chain of rights to the employer is an owner step, V0, and cannot be solved by the project).

| # | Title | Status | File |
|---|---|---|---|
| ADR-66 | Qualification profile as the key of the qualification matrix | Accepted | [0066-qualification-profile-as-key-of-the-qualification-matrix.md](../adr/0066-qualification-profile-as-key-of-the-qualification-matrix.md) |
| ADR-67 | Run state machine as a state times event table | Accepted | [0067-run-state-machine-as-state-times-event-table.md](../adr/0067-run-state-machine-as-state-times-event-table.md) |
| ADR-68 | Object lock: at most one active run per object and service | Accepted | [0068-object-lock-at-most-one-active-run.md](../adr/0068-object-lock-at-most-one-active-run.md) |
| ADR-69 | Chain of rights before publication | Accepted | [0069-chain-of-rights-before-publication.md](../adr/0069-chain-of-rights-before-publication.md) |
| ADR-70 | Eval runner bound to the data path | Accepted | [0070-eval-runner-bound-to-the-data-path.md](../adr/0070-eval-runner-bound-to-the-data-path.md) |

### 2.6 ADR-71 (consistency run of the detailed design, 2026-11-01)

The basis is the ruling FE-1127 of the detailed design ([11](../design/11-qa-prfix-automerge.md) section 9) and the contradiction between the reading of O9 ("commits of the PR fixer in watch mode") and ADR-59. The project decides; the owner has handed all open points over to the project.

| # | Title | Status | File |
|---|---|---|---|
| ADR-71 | PR fixer never writes to human branches | Accepted | [0071-pr-fixer-never-writes-to-human-branches.md](../adr/0071-pr-fixer-never-writes-to-human-branches.md) |

### 2.7 ADR-72 and ADR-73 (sixth round, O28, 2026-11-01)

The basis is the owner decision O28 ([DECISIONS](../DECISIONS.md) section 3.2): The project uses Claude exclusively, via the owner's subscription, including for eval and reference qualification. Without the two decisions the project could not measure services with a shell on public sets (condition 9 requires a private repo in `operator_repos`) and could not call the benchmark judges (the subscription token may only go into the `claude` process, ADR-57).

| # | Title | Status | File |
|---|---|---|---|
| ADR-72 | Operator eval on public sets via subscription | Accepted | [0072-operator-eval-on-public-sets-via-subscription.md](../adr/0072-operator-eval-on-public-sets-via-subscription.md) |
| ADR-73 | Benchmark judges and re-measured reference tools via claude-cli | Accepted | [0073-benchmark-judges-and-reference-tools-via-claude-cli.md](../adr/0073-benchmark-judges-and-reference-tools-via-claude-cli.md) |
## 3. Owner decisions of the project

The owner decisions of the project (open, decided or done, and moved to the reference installation) are in `docs/DECISIONS.md` ([DECISIONS](../DECISIONS.md)).

## 4. Technically open (without owner, clarified in the named stage)

| Item | Stage |
|---|---|
| Licenses of Caddy, restic, OTel Collector, Prettier or Biome, and the other tools in the repo against the allowlist | **Clarified 2026-11-01 (R-E01-T07):** Caddy Apache-2.0, restic BSD-2-Clause, OTel Collector contrib Apache-2.0, Prettier MIT (not used), Biome MIT OR Apache-2.0, all on the allowlist; Opengrep LGPL-2.1-only and ScanCode (Apache-2.0 AND CC-BY-4.0) only for development via exception; Node.js (BlueOak-1.0.0) and PostgreSQL led to an extension of the allowlist ([12](12-open-source-and-project.md) section 5.2). References in `docs/quality/toolchain.md` of the build repo |
| DBOS license | 0 |
| Does the manifest of a GitHub App accept an inactive webhook (operating mode `private`)? | 0 |
| Presigned URLs with Hetzner Object Storage, Azure SAS, and GCS; does Azurite cover all `BlobStore` capabilities? | 0 and 8 |
| Does `claude -p` run with an empty `CLAUDE_CONFIG_DIR` and only `CLAUDE_CODE_OAUTH_TOKEN` from the host file (ADR-57)? Contract test "start with `subscription`" | 0 |
| Do Sysbox or gVisor run with a rootless daemon under its own user, and which Docker API calls does the worker need behind the socket proxy (ADR-62)? | 0 |
| Does Claude Code load a `CLAUDE.md` from the workspace despite `--setting-sources user`? (case in S1, fallback described) | 1 |
| Does a reference qualification apply across credential kinds of the same provider? ([10](10-standards-per-layer.md) section 1.2 and [07](07-eval.md) section 2.1 assume so; contract test) | 1 |
| Read reference values directly: ReviewBench leaderboard (before stage 1), unit of the Scale values on SWE-Bench Pro V2 (before stage 2), TDD-Bench, DevBench, Terminal-Bench version; a reference value that cannot be read makes the part not decidable ([10](10-standards-per-layer.md) section 1.4) | before the first Gate B run of the respective stage |
| Data licenses of public sets (SWT-bench data, ContextBench, CI-Repair-Bench, JetBrains LCA, BUMP, Merge-Bench, c-CRAB, CodeWikiBench, DocAgent, SWE-RPG, SWE Atlas, SWE-rebench leaderboard set, gh-aw; OpenSSF CVE Benchmark and CWE-Bench-Java read as MIT on 2026-10-31); a request to the authors acts externally and is a step of the owner | Done criterion of the stage that needs the set (QA: 3, PR fixer: 4, triage: 7, docs: 10); until then "done with Gate B open" ([10](10-standards-per-layer.md) section 1.2 item 6), which does not block any following stage |
| Are the pinned judge models (Claude Opus 4.5, Claude Sonnet 4.5, Claude Sonnet 5) selectable via the subscription with `claude -p --model`, and does the model bridge (ADR-73) reproduce the published values of the Martian file (deviation due to parameters not set)? | 0 (building the bridge) and 1 (probe before the first Gate B run) |
| Handover of a Claude Code transcript into a local tool on `@agent handoff` | 2 |
| Agent fork on GitHub (ADR-59): Does GitHub withhold secrets for PRs from a fork in another organization when the app opens the PR, and does the approval requirement for workflows apply there? Offline mode of the registry caches per ecosystem (npm, PyPI, Go modules, Maven) without loading upstream (ADR-64) | 2 |
| Docker-in-Docker under gVisor (QA with E2E) | 3 |
| Can the app read the ruleset settings "Dismiss stale approvals" and "most recent push" without `administration` (ADR-61 (a))? | 6 |
| Can a GitHub ruleset bind a required check to an app? Merge of agent PRs without approval and without bypass when human PRs need an approval | 5 |
| Does the merge path need the hoster's merge queue (asynchronous merge API)? | 5 |
| Federation details for Bedrock, Vertex, Foundry from the own OIDC issuer role; WIF claims in the ruleset context; whether Vertex offers EU regions for Claude | 8 |
| Does Cloud Run carry the control plane (long poll, background jobs)? `/dev/kvm` on Hetzner Cloud | 8 |
| Codex plan limits; structured output with Gemini CLI, OpenCode, Goose; Azure OpenAI and Gemini in detail | 8, 9 |
| Licenses of OpenCode and ACP; ACP specification beyond the introduction page | 9 |
| Linear signature and stop signal; Bitbucket and Azure DevOps details; Gitea thread resolving | 9 |
| Renovate (AGPL-3.0) in its own container: legal assessment; account requirement with Infracost; licenses of git-cliff and release-please | 10 |
| Whole-repo security scan on demand (deep scan): not planned in any stage | Planning of stage 10 |
| whether Hatchet workers only connect outbound | only on a switch |

## 5. Follow-up list

**Third round (2026-10-31), changes in this file:**

| Fact | Status |
|---|---|
| ADR-05, ADR-06, ADR-11 to ADR-14, ADR-17, ADR-33, ADR-34 | Rationale without non-public preliminary research; ADR-06 with a public source since R-E04-T03 |
| ADR-08, ADR-09, ADR-18, ADR-21, ADR-22, ADR-23, ADR-26, ADR-29, ADR-33, ADR-36 | adapted to drivers, Analyzer, operating mode `private`, pool `self-hosted`, inspection proxy (M20), stage order R and 0 to 10 |
| ADR-19 | superseded by ADR-48 |
| ADR-25, ADR-30, O1 to O6, O11, O15, org prerequisites | moved to the reference installation; O6 rewritten there for the test operation (M18) |
| O12, O13, O14 | done, superseded, or decided respectively |
| O7, O9, O10 | Recommendations added after the research of the third round |
| O16 to O26 | new; fourth round (2026-10-31): O16, O18 to O26 decided; fifth round (2026-10-31): O7, O9, O10, O17 decided |
| Gate B reference | switched from 07 section 4 to [10](10-standards-per-layer.md) |

**Fourth round (2026-10-31), owner decisions O16, O18 to O26 incorporated** (O17 remains open with a proposal): changed in [01](01-plugin-interfaces.md) (optional method `approve`, capability `APPROVE_HUMAN`), [02](02-services.md), [03](03-flow-and-orchestration.md), [04](04-configuration-and-limits.md) (`auto_approve`, `auto_approve_risk_cap`), [05](05-security.md), [07](07-eval.md), [08](08-roadmap.md) (diagram without decided items, stages 6 and 7, steps R), [10](10-standards-per-layer.md) (header, sections 1, 3, 4, 8, 12, 16, 17, 18), [12](12-open-source-and-project.md) (sections 2, 3, 4, 5.3, 6, 7, 8, 9), [README](README.md), [backlog-minors](backlog-minors.md), this file (section 1, ADR-14, ADR-52), `docs/research/README.md`, one private preliminary work, and the files of the reference installation. Dated research reports under `docs/research/` remain unchanged.

**Red Team on the overall idea, package roadmap, gates, and quality claim (2026-10-31; rulings R-A to R-C, findings 1, 17, 18, 19):** new ADR-54 to ADR-56; changed ADR-26 (graph), ADR-42 (OpenTofu modules in sub-stage 0b), ADR-47 (done criterion via ADR-55), section 4 (reference values, licenses OpenSSF CVE Benchmark and CWE-Bench-Java); [08](08-roadmap.md) (section 1, principles 1, 2, 5, stages 0, 1, 2, 3, 6, 7, graph), [10](10-standards-per-layer.md) (header, sections 1.1, 1.2 item 6, 1.4, 1.5, 2, 3, 4, 6, 10, 13, 16, 17, 18), [07](07-eval.md) (sections 1, 1.1, 2, 3.1, 3.4, 3.8, 4, 7), [02](02-services.md) (section 0 rule 5, DoD tables planner, coder, reviewer, QA, indexer, standards), [01](01-plugin-interfaces.md) (section 13, sub-stage 0b), [11](11-installation-and-hosting.md) (sections 4 and 10, sub-stage 0b), [README](README.md) (goal, glossary, reading order, status); in the reference installation rollout and decisions (sub-stage 0b). Dated research reports under `docs/research/` remain unchanged.

**Red Team on the overall idea, package LLM runtime and subscription operation (2026-10-31; findings 2, 3, 10):** new ADR-57 (start path `subscription`) and ADR-58 (ModelProvider `claude-cli`, resolver rule); changed ADR-03 (rationale without Agent SDK), ADR-18 (token never in the control plane), ADR-31, ADR-39 (main package of the Agent SDK, gate test), ADR-51 (honest version: local pass-through, operator risk "intermediate"), section 4 (SDK contract test dropped, contract test "start with `subscription`" in stage 0); [01](01-plugin-interfaces.md) (section 1.1 rule 7, section 6 row `subscription`, contract test, allowlist, section 7 `claude-cli` and resolver rule, matrices 11.4 and 11.5), [05](05-security.md) (section 3 item 2, section 6 reading, platform rule, conditions 1, 4, 8, section 10 item 5), [04](04-configuration-and-limits.md) (sections 3a and 5), [06](06-operations-and-deployment.md) (sections 3 and 8), [07](07-eval.md) (S1, S2, S4), [08](08-roadmap.md) (stages 0 and 1, step 0.5), [11](11-installation-and-hosting.md) (sections 1, 2.1, 2.3), [12](12-open-source-and-project.md) (section 7), [README](README.md) (glossary, status), [backlog-minors](backlog-minors.md) (M45 superseded); in the reference installation the configuration (`models` with `claude-cli`, token storage). Left as is: 02 (the single calls still name "ModelProvider", which with `claude-cli` now also applies in subscription operation); dated research reports unchanged.

**Red Team on the overall idea, package security of autonomous effects (2026-10-31; ruling R-D, findings 4, 5, 6, 7, 11, 12, 13):** new ADR-59 to ADR-65; changed ADR-14 (approve conditions under ADR-61), ADR-36 (provenance, no `auto` for `external_code`), section 4 (rootless daemon, agent fork, offline caches, reading the ruleset); [01](01-plugin-interfaces.md) section 5 (`repoInfo`, `approvalProtection`, `withdrawApprove`), [02](02-services.md) (write request `propose_dependency`, visibility rule, approve conditions, withdrawal by the author, triage search), [03](03-flow-and-orchestration.md) (conditions 10 and 12, block for `external_code`, branch protection, three failure paths), [04](04-configuration-and-limits.md) (rule 4 fail closed, `security.agent_ci`, `security.dependencies`, approve conditions, resolver rules, example 3a), [05](05-security.md) (section 1 `single-host` with residual risk, section 2, section 3 CI and registry cache, section 6 residual risk, section 7 visibility, section 8 Run Record, section 9), [06](06-operations-and-deployment.md) section 2, [07](07-eval.md) S1, S2, S6, S7, [08](08-roadmap.md) stages 0, 2, 5, 6, 7, [10](10-standards-per-layer.md) section 14, [11](11-installation-and-hosting.md) sections 2.2 and 2.4, README, backlog M84 done; reference installation: configuration (`agent_ci`, `dependencies`), rollout and decisions (CI rule as a prerequisite).

**Red Team on the overall idea, package architecture and law (2026-10-31; ruling R-E, findings 8, 9, 14, 15, 16):** new ADR-66 to ADR-70 and O27 (open, owner step); changed ADR-11 (marker with all active runs), ADR-47 (adoption via the qualification profile); [03](03-flow-and-orchestration.md) (condition 2, section 2.1 as a table, 2.2, 2.3, new section 2.5, section 4, failure paths of the PR fixer, section 6 item 1 and test), [04](04-configuration-and-limits.md) (rule 5, route `pipeline.ci_failed`, assignment of control commands, section 5, schema marking in section 7), [07](07-eval.md) (sections 1, 2, 2.1, S2, S5, S6, S7), [10](10-standards-per-layer.md) section 1.2 items 1 and 2, [02](02-services.md) section 0, [05](05-security.md) section 6 condition 10, [12](12-open-source-and-project.md) (section 2.5, V0, V7, R0, R5, done criterion, section 9), [08](08-roadmap.md) (stage R, stage 0, section 3), [README](README.md) (glossary, status); reference installation: decisions (O20 with V0, O3), rollout (test operation without sets of the employer, org connection with approval), configuration (eval runner bound to `operator_repos`), overview (eval, accounts). Left as is: dated research reports (for example [`open-source-lizenz-und-recht`](../research/open-source-lizenz-und-recht.md) L6); 06 and 11 do not name an upgrade block due to open runs.

**Consistency run of the detailed design and work plan (2026-11-01; rulings of the detailed designs `docs/design/`, the owner has handed all open points over to the project):** new ADR-71 (section 2.6, from FE-1127); changed O9 (only stacked PR), ADR-14 and O24 (full key `services.reviewer.auto_approve`, M81), ADR-59 (exclusion of `agent/**` per event, FE-1040). Further places:

| File | Changed places (source) |
|---|---|
| [01](01-plugin-interfaces.md) | Section 3 `ack` with token (FE-510); section 5 `TokenProfile` with `audit_anchor` (FE-407), push check with exception for the anchor branch and without human branches (ADR-71), agent PR term "one of the three attributes" (FE-928, M83), key `services.reviewer.auto_approve`; section 6 `run` and `resume` with `SandboxHandle` (FE-541), environment allowlist with OTel variables (FE-523), `api_key` with the same protection flags as the subscription (FE-525); section 8 `SandboxHandle.spawn` and `SandboxSpec.trustedCaCerts` (FE-511); section 9 lexical search as an approximation (FE-1204); section 10 notifier kinds `alert` and `report` (FE-018, FE-926) |
| [02](02-services.md) | Header table `indexer` stage 7a and 7 (M141); section 0 reviewer `propose_reply` (FE-913), coder `propose_check` (FE-1062, W-6), indexer answer to `@agent ask` (FE-1209, M110); section 3 hard gates with G4 for test deletion and WIP exception (FE-1019, FE-1059, W-2); section 4 key (M81) and CLI name `guildwork review --local` (FE-917); section 6 output only stacked PR on human PRs (ADR-71), conflicts never via rebase (FE-1124, M88) |
| [03](03-flow-and-orchestration.md) | Section 1a branch protection with ADR-71; section 3 G0 exception of the automatic triage (FE-1254); section 4 `approve risk` on the ticket before the push (FE-1019, W-1), new command `approve dependency` (FE-1034, W-4), `ask` with answer effect (FE-1209); section 5 "repo cannot be assigned" as `skipped(repo_unresolved)` (FE-209) |
| [04](04-configuration-and-limits.md) | Section 2 exception `.agents/environment.yaml` in mode `env_bootstrap` (W-9); example: `runtimes` bound to `harness_pins` (FE-521), `approval.auto_mode` (FE-1006, W-5), `spec_path` and `doc_paths` (FE-1009, W-3), `command_permissions.approve_risk` and `approve_dependency` (W-1, W-4), `allow_on_human_branches: never` as the only value (ADR-71); section 3 agent PR sentence and key (ADR-71, M81) |
| [05](05-security.md) | Section 2 item 4 (never human branches, exception anchor branch) and profile `audit_anchor` (FE-407, ADR-71), item 5 key (M81); section 3 `guarded_workflows` per event (FE-1040, W-8); section 10 item 1 digest hard, cosign where available (FE-620) |
| [06](06-operations-and-deployment.md) | Section 3 admin UI as a SPA with server session (FE-601); section 6 upgrade lifts open runs (ADR-67, M137) |
| [07](07-eval.md) | S8 smoke run in stage 0 with dummy service (FE-615) |
| [08](08-roadmap.md) | Stage 1 GitHub plugin and `claude-code` from stage 0 (M103); stage 3 mutants as a notice (moved from stage 6, plan 3-E06, FE-1113); stage 5 watch mode only as a stacked PR (ADR-71); stage 6 key (M81) |
| [10](10-standards-per-layer.md) | Section 1.4 minimum power (FE-711, M139); section 3 Learnings stage 6 and 7a (M141) and key (M81); section 7 mutants stage 3; sections 9 and 10 Learnings sub-stage 7a (M141) |
| [11](11-installation-and-hosting.md) | Section 1 principle 1 with optional service `embedder` (FE-1205); section 2.3 item 6 and test matrix smoke run in stage 0 with dummy service (FE-615); section 6 rule 10 lifting of open runs (ADR-67, M137) |
| [README](README.md) | Table of files: ADR-01 to ADR-71 (M136) |
| [backlog-minors](backlog-minors.md) | M81, M83, M88, M103, M136, M137, M139, M141 done; M110 and M123 partially; M143 and M144 new |

**Sixth round (2026-11-01): O28 "Claude only, via the subscription", V0 completed, organization `guildwork-dev`, catalog and issues.** The owner message is summarized in O28 (`docs/DECISIONS.md`). New: O28, ADR-72, ADR-73, section 4 row judge models via the subscription; changed O17 (approval to create the organization, web form only), O22 (accounts), O23 (consequences for the leaderboard submission), O27 (completed, Claude accounts private, commit address), section 3.1 (status). Further places:

| File | Changed places |
|---|---|
| [01](01-plugin-interfaces.md) | Section 1.1 rule 1 (cassettes from the docs where there is no account), section 6 contract test per kind against stubs |
| [02](02-services.md) | Coder DoD "free harness" only an optional owner run; reviewer DoD R2 under the Claude judges; indexer K4 without own Codex measurement |
| [04](04-configuration-and-limits.md) | Section 3 example `judge-alt` as a different Claude model |
| [05](05-security.md) | Section 3 consequence for the own public repo; section 6 platform rule (the project uses only `subscription`), condition 10 with operator eval (ADR-72) |
| [07](07-eval.md) | Section 1 execution (pool `self-hosted`), judges (Claude judges, deviation for R2, model bridge), R2 in 3.1, table section 4, S2 |
| [08](08-roadmap.md) | Principle 7, stages 1, 8, 9, section 3 (owner items), section 4 stage R |
| [10](10-standards-per-layer.md) | Section 1.5 (deviation neutral judge), 1.7 (subscription instead of USD), section 3 B1, section 6 free harness, section 9 K4 |
| [11](11-installation-and-hosting.md) | Test matrix and support matrix: real applies aws, gcp, hetzner optional |
| [12](12-open-source-and-project.md) | Section 2.5 status, 5.4 dogfooding via the subscription, section 6 R1, section 7 consequences, section 9 O27 and O28 |
| [README](README.md) | Reading order (detailed design with catalog and build book, plan as issues, ADR-73), glossary, sources [gh-ghes-orgs], [gh-org-new], [gh-transfer], and [gh-proj-link], status sixth round |
| [backlog-minors](backlog-minors.md) | M127 done by O28; M131 and M135 with a note |
| Detailed design | 00 FE-064 (V7 via issues, comments, project), 05 FE-564 (cassettes from the docs) and section 2.19, 07 FE-758 to FE-760, 08 FE-854, 10 OP-16, 12 FE-1272, 13 FE-1366, 14 FE-1456, 15 open items, README section 1, component catalog |
| Work plan | 0-E20-T26 dropped; done criteria or content changed: 0-E15-T11, 0-E20-T07, T12, T14, T16, 1-E07-T02, T05, 1-E09-T08, T09, T11, 1-E10-T09, 2-E08-T02, T03, T04, 4-E06-T01, 7-E06-T03, T06, 8-E01-T01, T02, T10, 8-E02-T01, T02, T03, 8-E03-T01, T04, 8-E04-T01, T02, T03, T10, 8-E06-T02, T03, 9-E01-T01, T02, 9-E02-T01, T02, 9-E03-T02, T03, T04, 10-E03-T02, R-E04-T13, R-E05-T02; README section 5; draft KE and GE section 3 |
| Reference installation | private files in the ops repo (overview, decisions with O2 and O28, rollout, configuration, operations, addendum to the V0 evidence) |

Left as is: 04 section 6 (spend limit of the Console as a fallback limit applies to third-party installations with an API key); 07 F2p "own eval account" (meant is a GitHub account for commits of the LCA evaluation, not a model vendor); 10 section 7 entries with GPT-5 (published leaderboard values of third parties); 01 matrices with OpenAI, Gemini, and other vendors (product scope for third parties); sub-stage 0b with real Azure (base of the reference installation under O1, not a model vendor); O3 and the org connection (data path of the employer, with the owner); dated research reports under `docs/research/` and the private preliminary works under `docs/` unchanged.

**Older private documents** (precedence notes, superseded decisions of the first draft) are kept by the reference installation, because these documents do not become public.
