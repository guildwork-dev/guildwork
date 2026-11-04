<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# 06 Operations and deployment

Source keys and classifications as in the [README](README.md). This file defines what every installation consists of and which topologies the platform supports. Installation path, profiles per base, driver assignment, upgrade and test matrix are in [11](11-installation-and-hosting.md). What a particular installation has chosen is in its private ops repo (ADR-38).

## 1. Common operations core (all topologies)

- **Control plane:** one container image `control-plane` (Node 22+) with the roles `web` (ingress, Work API, platform MCP, admin UI), `orchestrator` and `migrate`; one process or scaled separately, the same codebase.
- **PostgreSQL with pgvector** as the only state: queue (pg-boss), runs, ledger, findings, audit, knowledge base. No database abstraction and no queue port (ADR-41): a second state store would contradict ADR-02. The operator chooses "managed" (Azure Flexible Server, Amazon RDS, Cloud SQL) or "bundled" (container, CloudNativePG); that is configuration. The pgvector versions of the bases vary (0.8.0 to 0.8.7, [`hosting-und-installation`](../research/hosting-und-installation.md) section 2.5, VERIFIED); the platform only uses functions of the smallest version in the test matrix and checks `SELECT extversion` at startup with a clear error message. Backup with point-in-time recovery; once per expansion stage an evidenced restore test.
- **Drivers for the base** (ADR-41, contract in [01](01-plugin-interfaces.md)):
  - `BlobStore` for raw payloads, transcripts, logs, bundles, test artifacts, screenshots: `fs`, `s3` (AWS S3, Hetzner Object Storage, SeaweedFS and other S3-compatible), `azure-blob`; later `gcs`. Presigned upload URLs for `uploadUrl` per driver. No MinIO (community repo archived, no binaries), SeaweedFS in the Compose bundle (ADR-43).
  - `SecretStore`: `file`, `env` (read-only), `azure-keyvault`; later `aws-secretsmanager`, `gcp-secretmanager`, `openbao`.
  - `CloudIdentity`: `self-issuer` (control plane as OIDC issuer); from stage 8 `azure-managed-identity`, AWS, GCP; `k8s-projected-token` later.
- **Worker image** `agent-worker`: one binary for all pools; weekly rebuild; harness CLIs are not in the image (section 8).
- **Egress proxy image** (with credential relay, [05](05-security.md) section 3) and **OTel collector**.
- **Identity of the admin UI** via a generic OIDC client plus emergency admin ([05](05-security.md) section 7); no plugin.
- No Redis, no Temporal, no Langfuse, no Vault in the first stages; each only when a need is demonstrated.
- **Optional companion services**, each as an unmodified upstream image in its own container, never in the platform code: Renovate CLI (AGPL-3.0, [`ebene-pr-fix-und-ci`](../research/ebene-pr-fix-und-ci.md) section 2.6) as the producer of update PRs; the platform only reads its PRs.

## 2. Topologies

The platform knows no company-specific variants, but topologies. Each consists of the operations core plus at least one worker pool. Pools are named after their kind: `self-hosted` (permanent workers on the operator's hardware or VMs), `ci-dispatch` (job per item on CI runners), `cloud` (VM pool or Kubernetes jobs of a cloud). Which building blocks are verified per base is in the profiles of [11](11-installation-and-hosting.md) section 3.

| Topology | Control plane | Workers and isolation | For whom | Package (stage) |
|---|---|---|---|---|
| `single-host` | Compose on a Linux VM or own hardware, Postgres container with pgvector, `fs` or SeaweedFS, `file`, `self-issuer` | pool `self-hosted` on the same host; `sysbox` or `gvisor`; `microvm` only with `/dev/kvm`; worker without the socket of the control plane's daemon (socket proxy with allowlist or own rootless daemon), sandbox networks without contact to the Compose network ([05](05-security.md) section 1, ADR-62) | single operators, small teams, testing; also Docker on Hetzner; for `external_code` and multi-user operation, workers on a second VM recommended | Compose bundle with installer CLI and `doctor` (stage 0) |
| `kubernetes` | Helm chart, roles separated, `migrate` as a job before the rollout, Postgres external or CloudNativePG | pool `cloud` as a deployment per pool, sandbox pods via RuntimeClass (`sysbox-runc`, `runsc`, `kata`) | production with high availability | Helm (stage 8) |
| Cloud profile `azure` | container service or VM, Flexible Server with `vector`, `azure-blob`, `azure-keyvault`, from stage 8 `azure-managed-identity` | VM pool with Sysbox, gVisor or microVM, or AKS with pod sandboxing; never Container Apps | operators on Azure | OpenTofu module `azure` (stage 0) |
| Cloud profiles `aws`, `gcp`, `hetzner` | managed services of the respective base or Compose on Hetzner servers | EC2 or GCE pool or GKE Sandbox; on Hetzner Cloud `sysbox` or `gvisor`, `microvm` only on dedicated servers | operators on AWS, Google Cloud, Hetzner | OpenTofu modules (stage 8) |
| Add-on `self-hosted` | any | permanent worker as a systemd service on further hardware of the operator (worker package, `worker register`), a fresh container per item, only outbound HTTPS | additional capacity, subscription operation of a single operator ([05](05-security.md) section 6) | worker package (stage 0) |
| Add-on `ci-dispatch` | any | job per item on runners of a CI system (section 2a) | operators with an existing runner fleet | backend `ci-dispatch-github` (stage 8) |
| Offline eval | without a central DB | CI jobs with `sqlite-artifact` KB, Effect Gateway in the mode `record` | only eval or repos without a network path to the control plane; **no live operation**, because ledger, policy and user and org limits are missing (ADR-27) | as stage 1 |

Rules for all topologies (DERIVED, evidence in [`hosting-und-installation`](../research/hosting-und-installation.md) section 2.8):
- **Workers never on container services without privileged mode** (Azure Container Apps, AWS Fargate, Cloud Run). They are only suitable for the control plane.
- **Workers only need outbound HTTPS** (ADR-05). Reason: execution locations are often behind NAT or a firewall without inbound connections. In the operating mode `public`, the control plane therefore has a publicly reachable HTTPS endpoint for the Work API and webhooks (ADR-08); in the operating mode `private` there is no public entry point, inputs only via `poll` and `reconcile`, workers in the same network ([11](11-installation-and-hosting.md) section 1.1).
- **Control plane and workers never on hosts that carry other production.** An agent with a shell on someone else's production host increases the damage of every gap in the sandbox.
- **Which isolation a pool offers is decided by the verified capability at claim**, not by the configuration ([05](05-security.md) section 3).
- **QA with E2E** needs Docker-in-Docker and Chromium in the worker ([02](02-services.md)); the profile table of [11](11-installation-and-hosting.md) states per base whether that runs there.

### 2a. Backend `ci-dispatch`

For operators who want to share their own runner fleet (GitHub Actions, later GitLab CI).

- **Flow:** the control plane triggers `workflow_dispatch` in the operator's runner repo. The token for this is minted by the broker with profile `dispatch` from a separate dispatch app that is only installed on the runner repo ([05](05-security.md) section 2). The job starts the worker; it authenticates to the Work API via the OIDC of the CI system ([05](05-security.md) section 5), fetches exactly one item and ends.
- **Nested setup** (DERIVED): runner, inside it the job container with the Sysbox runtime, inside that three parts: the worker process, the egress proxy with credential relay as its own container and the sandbox as its own container. The sandbox is only attached to an internal Docker network without egress (`internal: true`); its only way out is the proxy, which as the only container is also attached to the outbound network. Pool key or OIDC token and the LLM credential stay in the worker and the proxy, never in the sandbox.
- **Done criterion (stage 8):** "nested sandbox with enforced proxy" is evidenced if from the sandbox (a) a direct connection to a test host outside the allowlist fails, (b) the same host is rejected via the proxy, (c) the LLM call via the relay succeeds and (d) S1 shows 0 hits of a real credential outside the relay there.
- **Hard upper bound:** the runners are shared with the operator's CI. The pool has a fixed `max_concurrency` below the slot count; the CI waiting time is measured (section 4) and the limit is readjusted.
- **Outage:** if jobs do not reach the Work API, leases expire; items wait or go to another pool, if configured.
- The isolation is as strong as the job container: `private_own` yes, `external_code` only for services without execution of repo code ([05](05-security.md) section 3).

## 3. Technology choice per building block

| Building block | Choice | Rationale | Alternatives and migration path |
|---|---|---|---|
| Language of control plane and worker | TypeScript on Node 22+ | Vercel AI SDK with official packages for Anthropic, Bedrock, Vertex, Azure, OpenAI ([aisdk] VERIFIED), pg-boss (MIT, Node 22+, [pg-boss] VERIFIED); reference projects Pullfrog and Kodus are TS | Go only with River as the queue; there concurrency limits and workflows exist only in "River Pro" (https://riverqueue.com/docs, VERIFIED according to research) |
| Queue | pg-boss | MIT, SKIP LOCKED, retries with backoff, DLQ, rate and concurrency policies, OTel ([pg-boss] VERIFIED); no second state store | graphile-worker (without advantage); BullMQ no (group fairness only in Pro, needs Redis, [bullmq] VERIFIED) |
| Flows | own versioned state machine in Postgres plus pg-boss | approvals take days, states must be testable and versioned | DBOS ("no infrastructure required besides Postgres", [dbos] VERIFIED), as soon as the license is checked; Hatchet (MIT, [hatchet] VERIFIED) or Temporal for very complex workflows; work items and leases sit behind an own interface. Not: Restate (BSL, push), Inngest (SSPL, push default) ([restate], [inngest] VERIFIED) |
| Worker pickup | own Work API with long poll and lease | workers behind NAT or a firewall without inbound connections; reference project Managed Agents self-hosted sandboxes ("only outbound HTTPS", [an-managed-sh] VERIFIED) | Hatchet worker (whether outbound only: unverified) |
| Sandbox | `sysbox` and `gvisor` equivalent for own code, `microvm` (E2B self-hosted with Firecracker or Kata) required for repo code of the class `external_code` (ADR-48) | Sysbox provides Docker-in-Docker without `--privileged` ([sysbox] VERIFIED), but is a risk for a public product: "not officially supported by Docker", support "best effort" (VERIFIED, [`hosting-und-installation`](../research/hosting-und-installation.md) section 2.8). gVisor runs with `systrap` on any Linux VM without virtualization ([gvisor-plat] VERIFIED); microVMs need `/dev/kvm` | Daytona no (repo archived, [daytona] VERIFIED); Azure Container Apps Dynamic Sessions as an option for services without Docker-in-Docker (unverified) |
| Environment description | `.agents/environment.yaml` or devcontainer | Devin blueprint and Codex setup patterns | |
| Plugin mechanics | in-process modules for own adapters; subprocess with gRPC for third parties and harnesses; WASM (Extism) only for small pure functions | go-plugin: "a panic in a plugin doesn't panic the plugin user" ([go-plugin] VERIFIED); Extism for untrusted code ([extism] VERIFIED) | HTTP plugins for triggers as a separate service |
| ModelProvider adapter | own thin adapters on the Vercel AI SDK | official provider packages ([aisdk] VERIFIED) | LiteLLM proxy only optionally as an additional fallback limit, not the source of truth ("fails open" without DB, [litellm] VERIFIED) |
| Limits | own ledger in Postgres | subscription and Codex bypass any gateway | LiteLLM, Claude apps gateway ([cc-appsgw]) as a supplement |
| Knowledge base | `pg-kb` (Postgres plus pgvector) | one state store, cross-repo possible because the control plane is reachable | `sqlite-artifact` for offline eval |
| Object storage | `BlobStore` driver, SeaweedFS (Apache-2.0) in the Compose bundle | one interface for all bases; Azure Blob has no S3 API (CLAIMED, forum), hence its own driver; retention is enforced by a deletion job of the control plane, not by bucket lifecycle, because not every S3 service fully supports lifecycle ([`hosting-und-installation`](../research/hosting-und-installation.md) section 2.6) | Garage (AGPL-3.0, without versioning and Object Lock) as a lightweight alternative; no MinIO (ADR-43) |
| Secrets | `SecretStore` driver; `file` on `single-host`, otherwise the cloud's KMS service | few machine secrets; every base has a path without cloud lock-in | OpenBao if needed ([openbao] VERIFIED); on Kubernetes any backend of the External Secrets Operator via files |
| Observability | OTel SDK and OTel collector, export via OTLP to any backend; the control plane computes required alerts itself and delivers them via `Notifier` | no third-party backend needed to get required alerts; Claude Code exports OTLP natively ([cc-monitoring] VERIFIED) | bundled minimum stack in the Compose bundle: collector with Prometheus exporter and file export ([11](11-installation-and-hosting.md)); Langfuse later (needs web, worker, Postgres, ClickHouse, Redis, S3, [langfuse] VERIFIED) |
| Admin UI | single-page app with a server-side session (backend for frontend), behind OIDC; no token in the browser | one UI technology for all pages, the security gain of a server-rendered UI is preserved through the server session (detailed design 06 FE-601) | server-rendered with templates (second UI pattern) |
| Installation | Compose bundle with installer CLI, then OpenTofu modules, then Helm; setup wizard in the admin UI (ADR-42) | industry pattern of a staircase of three paths ([`hosting-und-installation`](../research/hosting-und-installation.md) section 2.1) | details in [11](11-installation-and-hosting.md) |

## 4. Observability

- **Traces:** control plane and worker with OTel; the worker sets the OTel variables for Claude Code and passes the `TRACEPARENT` of the work item through, which yields one trace from ticket to PR ([cc-monitoring] VERIFIED; traces there are beta with `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`). Repo settings cannot redirect the telemetry ([cc-monitoring] VERIFIED).
- **GenAI conventions** are in the status "Development" ([otel-genai] VERIFIED): pin the version, rename attributes in the collector, do not build dashboards hard on attribute names.
- **Metrics (minimum set):** waiting time per pool, CI waiting time per `ci-dispatch` pool, lease expiries, claims without matching isolation, effect errors per plugin, fallback levels per capability, skipped reasons, run duration and cost per service and provider, ledger fill level per key, `health()` per plugin and driver (expiring tokens and webhooks), share of `neutral` results, eval metrics from [07](07-eval.md).
- **Costs and runs** come from the ledger (one SQL source for dashboards).
- **Alerts (required):** queue age, lease expiries, error rate per provider, budget at 80 %, webhook deactivation or expiry, token expiry (subscription after one year, GitLab PAT), audit chain broken or daily anchor missing, sign-in of the emergency admin, Postgres backup failed. The control plane computes them itself and delivers them via `Notifier`; an external alerting system is optional.

## 5. Data storage and retention

| Data | Location | Retention (starting value; decided by the operator) |
|---|---|---|
| Runs, steps, work items, effects, ledger, config snapshots, qualification matrix | Postgres | permanent, PITR |
| Findings and feedback | Postgres (`findings`, `finding_feedback`), PR markers only anchors | like the repo |
| Raw payloads | BlobStore, encrypted | 30 days |
| Transcripts, diffs, test logs, screenshots | BlobStore, secret scan before storage | 30 to 90 days; evidence for merged PRs longer |
| Audit | Postgres append-only plus daily anchor in the BlobStore with Object Lock or in the anchor repo ([05](05-security.md) section 8) | at least 1 year |
| Knowledge base L0 to L5 | Postgres with pgvector | per watermark |
| Rules and standards | files in the repo | Git |
| Eval datasets | public, license-clean sets in the project repo; private sets per installation in its eval repo plus BlobStore (ADR-52, [07](07-eval.md)) | permanent |

Retention periods are enforced by a deletion job of the control plane (section 3, row object storage). Code leaves the installation only toward the configured LLM provider; the data path is enforced per repo class ([04](04-configuration-and-limits.md) `data_policy`).

## 6. Operational routines

- Weekly rebuild of worker and sandbox base images; images by digest and signature ([05](05-security.md) section 10).
- Harness versions pinned with checksum; raised only after a green eval regression run ([07](07-eval.md)).
- Health checks per plugin and driver: expired Jira app webhooks (30 days, [jira-webhooks] VERIFIED) with `renew`, deactivated GitLab hooks, token expiries, reachability of BlobStore and SecretStore.
- Kill switch per service, repo and org in the admin UI, effective at the next claim; running leases are revoked.
- **Upgrade** (rules in [11](11-installation-and-hosting.md) section 6): expand/contract without down migrations, `migrate` before the rollout and abort without a fresh backup, only N-1 to N per minor version with stopping points from the release notes, workers of the previous version continue to work against the new control plane, the control plane lifts open runs to the new version of the run state machine before the next migration (ADR-67, [03](03-flow-and-orchestration.md) section 6). Plugins and drivers: the core supports the current and previous `apiVersion` per kind.
- Key rotation: GitHub App keys (main and dispatch app), OIDC signing keys, pool keys on schedule and on suspicion.

## 7. Cost levers

Ordered by expected effect (estimate, to be measured per stage):
1. **Gate before every run** and incremental review: one run per push, not per event; re-review only over new commits.
2. **Model tiering:** small model for gate, triage and classification, medium for finder and coder, large only for verifier, planner and architect.
3. **Prompt caching:** stable prefix (system, rules, repo map) before the diff; subagents sparingly. With Bedrock, caching is regionally restricted ([cc-features] VERIFIED).
4. **Batch API** for full analysis, summaries, standards run (check the discount per provider, unverified).
5. **Reservation before the run** and cost forecast at G1 prevent expensive failed runs.
6. **Best-of-N and multiple runs** off by default; only where the eval shows the gain.
7. **Knowledge base only with an eval gain**; embeddings local (O7).
8. **Own runners and own hardware** cost no hoster minutes (DERIVED); a cloud pool only as overflow.
9. **API credit from Max, Ultra or Team** usable since 2026-10-07 for API key runs ([cc-sdkplan] VERIFIED), capped at $100 (Max), $200 (Ultra) or up to $500 (Team) per month, without rollover, Pro excluded ([an-credits], VERIFIED according to the cross-check).
10. **Hard limits:** `maxTurns`, `maxBudgetUsd`, wall time, number of attempts, provider spend limit as the fallback limit.

## 8. Artifacts and licenses

- **What the project ships:** images `control-plane`, `agent-worker`, `egress-proxy`, `sandbox-base` for amd64 and arm64, the installer CLI, the Compose bundle, OpenTofu modules and later the Helm chart ([11](11-installation-and-hosting.md)). Signature, SBOM and attestation: [05](05-security.md) section 10.
- **No proprietary binaries (ADR-39):** no image and no lockfile contains any of the packages from ADR-39: npm `@anthropic-ai/claude-code` and its platform packages `@anthropic-ai/claude-code-*` (with native binary), the Agent SDK `@anthropic-ai/claude-agent-sdk` including platform packages (`@anthropic-ai/claude-agent-sdk*`), PyPI `claude-agent-sdk` (bundles the CLI) and `claude-code-sdk`; no package of the project depends on the Agent SDK (the adapter `claude-code` starts `claude -p`). All are "All rights reserved" and are under the Commercial Terms; the platform packages contain the native CLI (VERIFIED, [`open-source-lizenz-und-recht`](../research/open-source-lizenz-und-recht.md) section 2.3 with [`gegenpruefung-lizenz-und-recht`](../research/gegenpruefung-lizenz-und-recht.md) points 7 and 8). The license gate has a negative test for this: a lockfile with one of these packages is red (stage R), as is an image with the SDK package (image license gate). The worker installs the harness at the operator's site at first start or via an init container from the official source, with a pinned version and checksum from the configuration (`install(sb, pin: PinnedVersion)` in [01](01-plugin-interfaces.md) section 6). Other harness CLIs are installed by the worker the same way, so that there is only one path.
- **Required files of every publication:** `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES` (generated from the license gate, not maintained by hand) and the SBOM. Texts taken over from Apache-2.0 sources carry an SPDX header, a provenance line and the note "modified" ([`open-source-lizenz-und-recht`](../research/open-source-lizenz-und-recht.md) section 2.3).
- **License gate in CI:** dependencies against an allowlist, ScanCode before every release; a finding stops the release before the image tag ([12](12-open-source-and-project.md)).
- **Analyzer catalog (ADR-50):** only tools and rules with a free license are shipped (for example the Opengrep and Semgrep CE engines with own rules, osv-scanner, gitleaks, Trivy). Not shipped: the Semgrep Registry rules ("only for your own internal business purposes"), the CodeQL CLI and SonarQube. The Opengrep rules are under LGPL-2.1 with the Commons Clause, which prohibits selling (including hosting and support fees); they are never shipped, because an operator who hosts for a fee would otherwise be selling (ADR-50). An operator can import results of such tools as SARIF ([`open-source-lizenz-und-recht`](../research/open-source-lizenz-und-recht.md) section 2.3, cross-check points 23, 24, 26).

## 9. Telemetry and air gap

- **Product telemetry to the project is off by default** (ADR-44). Opt-in in the setup wizard, content publicly documented, never code, tickets, prompts or names.
- **Mode `air_gap`:** the egress proxy blocks all outbound connections except the configured SCM, ticket and LLM endpoints (update check, pulls from public registries, third-party content); images come from an own registry mirror. Enforced in the proxy, not just as a flag. With a cloud LLM, no installation is fully offline. Details in [11](11-installation-and-hosting.md).
