<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# 11 Installation and hosting

Keys and classifications as in the [README](README.md). Basis: [`research/hosting-und-installation.md`](../research/hosting-und-installation.md) (hereafter [HI]) and [`research/bothy-vorlage-projekt-setup.md`](../research/bothy-vorlage-projekt-setup.md). The reference project for installer, OpenTofu modules, upgrade and portability test is the public project bothy ([bothy-repo], state `origin/main` as of 2026-10-31; whether the reference with account names stays in the public repo is checked by the publication checklist in [12](12-open-source-and-project.md); files `docs/spec/16-operations.md` sections 3, 3.1, 8, 10 and 11, `infra/tofu/README.md`, `.github/workflows/portability.yml`, read firsthand, VERIFIED).

Classification in tables: (B) VERIFIED, (G) CLAIMED, (A) DERIVED, (V) ASSUMED, (u) unverified. A cell with (u) is a plan, not evidence.

A concrete installation (base, subscription, pools, values) is never stated here, but in the private ops repo of the respective operator. This also applies to the reference installation of the project (private, ADR-38).

## 1. Goal and principles

**Goal:** Anyone installs the platform on their own base (a Linux host, Kubernetes, Azure, AWS, Google Cloud, Hetzner or their own hardware), with a documented path that is tested in CI, and attaches their own plugins, drivers and services without changing the product.

**Principles:**
1. **Control plane without an LLM.** The control plane needs no LLM and no GPU; it is a Node service with Postgres and object storage (ADR-02). Only the worker or the credential relay in the egress proxy reaches LLMs. Optionally, a separate service `embedder` in the internal network of the control plane computes embeddings with a local, freely licensed model on the CPU (for vector search from stage 7, O7); without it, vector search is off (detailed design 12 FE-1205).
2. **Workers pull work.** Workers only talk outbound to the Work API (long poll with lease, ADR-05). A worker never needs an inbound connection; that is why workers can sit behind NAT, in a CI network or on their own hardware.
3. **One state.** Postgres with pgvector is the only state store, plus object storage via the driver `BlobStore`. No Redis, no second queue, no database abstraction (ADR-41).
4. **Base behind drivers, domain logic behind plugins.** What depends on the base (object storage, secrets, cloud identity) goes through drivers (section 4); what connects third-party systems to the domain logic goes through the 9 plugin kinds ([01](01-plugin-interfaces.md)).
5. **The control plane may run on a container service, workers never.** Azure Container Apps, AWS Fargate and Cloud Run allow no privileged containers or no custom container runtime ([HI] 2.8: [aca-priv] G, [fargate] B, [cloudrun-env] G). Workers need a VM, a Kubernetes node with a suitable RuntimeClass or their own hardware.
6. **We ship no proprietary binaries.** Images contain neither Claude Code nor the Agent SDK including platform packages; the worker installs the pinned version with checksum at the operator (ADR-39; [`research/open-source-lizenz-und-recht.md`](../research/open-source-lizenz-und-recht.md) verdict 4).
7. **No `sudo`, no silent interventions.** Installer and CLI install no packages, never call `sudo` and write only into their target folder (bothy rule, `16-operations.md` section 3.1 rule 2, B).

### 1.1 Ingress operating modes

| Operating mode | When | What is publicly reachable | Consequences |
|---|---|---|---|
| `public` (default) | Control plane has a public HTTPS address | Ingress (webhooks), Work API, platform MCP; admin UI only behind SSO | Webhooks with `reconcile` (ADR-08); workers anywhere with outbound HTTPS |
| `private` (without public ingress) | Installation behind NAT, in a home network, in a corporate network without outbound exposure | nothing | Inputs only via `poll` and `reconcile` of the TriggerSource ([01](01-plugin-interfaces.md) section 3); workers in the same network or via a VPN of the operator; admin UI and setup wizard only in the internal network |

Rules for `private` (DERIVED):
- An ingress plugin without the capability `POLL` cannot be loaded in this operating mode; `doctor` reports this before startup.
- The poll interval is a named value per TriggerSource (`trigger.poll_interval`), limited by the rate limits of the provider; the response time to a mention increases by up to one interval. Whether that is sufficient for a service is not measured by 07; the admin UI shows the operating mode on the service.
- The GitHub App is created without an active webhook (section 2.3). Whether the manifest accepts `hook_attributes.active: false` is unverified; otherwise the wizard enters a placeholder URL and deactivates the webhook via API after creation (u).
- Tunnel services (reverse tunnel of a third-party provider) are the operator's concern. The product ships none and depends on none.

## 2. Installation package

What the project ships per release. Version, signature and place of publication are governed by [12](12-open-source-and-project.md).

### 2.1 Container images

| Image | Content | Roles |
|---|---|---|
| `control-plane` | Control plane; `migrate` as a subcommand | `web`, `orchestrator`, `migrate` per argument |
| `agent-worker` | Worker binary, without harness binaries | Pickup, sandbox setup, harness installation at runtime |
| `egress-proxy` | Proxy with allowlist per service and credential relay | per worker host or per pod |
| `sandbox-base` | Base of the sandbox per work item | extended per repo via blueprint |

Rules:
- amd64 and arm64 for every image; referenced by digest, never by `latest` (bothy pattern, B).
- Signed (cosign keyless) with SBOM and attestation; image scan before the tag ([`bothy-vorlage`](../research/bothy-vorlage-projekt-setup.md) section 2.9, B).
- No `claude`, none of the packages from ADR-39 (Claude Code and Agent SDK, each including platform packages, the PyPI SDKs), no other proprietary CLI in the image (ADR-39). The worker installs the harness on first need with the version and checksum pinned in the configuration (`AgentRuntime.install`, [01](01-plugin-interfaces.md) section 6) into a cache outside the sandbox; in air-gap mode from the operator's mirror (section 8).
- Bundled third-party tools (analyzers) only with a free license, each manifest with an SPDX identifier (ADR-50).

### 2.2 CLI

One binary named `guildwork` (O17).

| Command | Purpose | Writes |
|---|---|---|
| `guildwork install` | Setup wizard for `single-host` (section 2.4) | only the target folder |
| `guildwork doctor` | Preflight check and operational check, without writing: Postgres major version, `SELECT extversion` of `vector` against the minimum version, drivers reachable (write and read probe in its own prefix), isolation verified (`/dev/kvm` readable and writable, `sysbox-runc` or `runsc` registered, RuntimeClass present), outbound HTTPS to the configured targets, public URL and webhook reachability (only `public`), clock, air-gap locks (section 8), on `single-host` the separation of worker and control plane ([05](05-security.md) section 1, ADR-62: no Docker socket of the control plane in the worker, socket proxy with allowlist or rootless daemon, worker without network access to Postgres and SeaweedFS and without `secrets/`, sandbox networks `internal`), sandbox without DNS resolver and registry cache in offline mode (ADR-64), per repo with Coder, QA or PR-Fixer the CI variant for agent branches ([05](05-security.md) section 3, ADR-59) and with `auto_approve` the hoster settings from ADR-61 (a), audit anchor present (otherwise "audit chain not anchored", section 4), org default `GITHUB_TOKEN` read-only, as far as the app is allowed to read this ([05](05-security.md) section 5), checksum of the pinned harness version ([01](01-plugin-interfaces.md) section 6, `PinnedVersion`) | nothing |
| `guildwork upgrade` | Upgrade according to section 6: check backup, `migrate`, rollout, check readiness | Stack, schema |
| `guildwork backup`, `guildwork restore` | Backup and restore according to section 7 | Backup target or target instance |
| `guildwork worker register` | Generate a pool key for a worker on own hardware and display it once | Control plane (pool entry) |
| `guildwork github-app create` | GitHub App via manifest flow without admin UI (section 2.3) | SecretStore |

Every question has an option, `--yes` takes the defaults, without a terminal no required value is silently missing (abort with step and reason). Exit codes `0` success, `1` step failed, `2` invalid option (bothy pattern `16-operations.md` 3.1, B).

### 2.3 Setup wizard in the admin UI

On first start, before any service runs, in this order:
1. **Emergency admin:** local account with a one-time code from `guildwork install` or the startup log; afterwards only for emergencies (ADR text in 09, SSO is not a plugin).
2. **SSO:** generic OIDC client (issuer URL, client ID, secret in the SecretStore, group claim to roles `viewer`, `approver`, `admin`). Entra ID, Google, Okta, Keycloak, Zitadel are configuration ([HI] 2.9, A).
3. **GitHub App via manifest flow** (ADR-45): The admin UI builds the manifest with exactly the permission profiles from [05](05-security.md) section 2, redirects the admin to GitHub, exchanges the returned `code` via `POST /app-manifests/{code}/conversions` and stores `id`, `pem` and `webhook_secret` directly in the SecretStore; the exchange must happen within one hour ([gh-manifest] B). The flow only needs the admin's browser, not a public ingress (A). Other SCM providers: guided instructions with a token or service account, no equivalent flow known ([HI] 2.2, u).
4. **Model access:** choose the credential kind; preferably without a static key (WIF, Bedrock, Vertex, Foundry via `CloudIdentity`). `subscription` and `chatgpt` are locked and can only be enabled with `acknowledge_terms` as a personal operator mode; the platform implements no login, and the control plane never sees the token; the operator places their `setup-token` in a file on the worker host that only the worker user can read (ADR-51, ADR-57).
5. **First pool:** confirm the local worker (`single-host`) or `guildwork worker register` for own hardware; the pool reports its verified isolation capabilities (ADR-48).
6. **Trial run in mode `shadow`:** a review on a repo chosen by the admin (in stage 0, before the reviewer, a run of the dummy service; detailed design 06 FE-615); the Effect Gateway writes nothing to the outside. Success criterion: Run Record complete, findings in the eval log, no policy violation.

Telemetry and update notice appear in the wizard as two separate opt-ins, both preselected to "off" (section 8).

### 2.4 Compose bundle (`single-host`)

Content: `control-plane` (both roles in one process), `migrate` as a one-off service before the start, Postgres with pgvector (`pgvector/pgvector`, [pgv-docker] B), worker with selectable isolation behind a socket proxy with allowlist (or with its own rootless daemon, ADR-62), `egress-proxy`, reverse proxy with automatic TLS (Caddy, pattern [ph-self] B), OTel Collector; optionally SeaweedFS as an S3 service (ADR-43, profile `s3`, otherwise driver `fs` on a volume) and a small local observability stack.

Installer rules (adopted from bothy `16-operations.md` 3.1, B):
1. Preflight check without writing (Docker and Compose minimum version, architecture, memory, kernel and isolation, target folder empty or a previous installation).
2. Check the bundle with the built-in SHA-256, check the signature if `cosign` is present, otherwise name the verification command.
3. `.env` with mode `0600`, `secrets/` with `0700`; generate generatable secrets on first start; no secret as a command-line option.
4. A second run overwrites neither `.env` nor `secrets/`.
5. Database and object storage only in the internal network; only the reverse proxy faces outward (bothy `infra/tofu/README.md` rule 3, B).
6. Workers and sandboxes never attach to this internal network: the worker reaches the Work API and platform MCP only via the reverse proxy, each sandbox only its own internal network with the egress proxy as the only exit; the worker gets neither `secrets/` nor `.env` nor the Docker socket of the control plane ([05](05-security.md) section 1, ADR-62). For repos of class `external_code`, the installer recommends running the pool with the worker package (section 2.7) on a second VM.

Minimum requirements (CPU, RAM, disk per slot) are named values (`install.min_cpu`, `install.min_mem_gb`, `install.min_disk_gb`, `pool.slot_mem_gb`) that `doctor` checks. Stage 0 sets starting values after measurement; without measurement no number is stated here. Sysbox requires a kernel from 5.12 ([sysbox-distro] B).

### 2.5 Helm chart (`kubernetes`, from stage 8)

Separate deployments for `web`, `orchestrator` and worker pools from one image; `migrate` as a job before the rollout (Helm hook); no database in the chart (external Postgres or CloudNativePG with image variant `standard`, [cnpg-img] B); worker pools with selectable RuntimeClass (`sysbox-runc`, `runsc`, `kata`); NetworkPolicy that lets sandbox pods reach only the egress proxy; ingress and TLS are the operator's concern (bothy `infra/helm/README.md`, B).

### 2.6 OpenTofu modules

| Module | Builds | Stage |
|---|---|---|
| `generic-vm` | sets up an existing Linux host with the Compose bundle | 0 |
| `azure` | Network, VM for the control plane or Container Apps, Flexible Server with `vector`, Blob Storage, Key Vault, Managed Identity, worker VM pool; calls `generic-vm` for the VMs | 0 |
| `aws` | Network, control plane on ECS Fargate or EC2, RDS with pgvector, S3, Secrets Manager, worker EC2 pool | 8 |
| `gcp` | Network, control plane on Cloud Run or GCE, Cloud SQL with pgvector, GCS, Secret Manager, worker GCE pool or GKE Sandbox | 8 |
| `hetzner` | Network and firewall, cloud server, Object Storage connection; calls `generic-vm` | 8 |

Rules (bothy `infra/tofu/README.md`, B): secrets are never input or output of a module, state encrypted, providers pinned, only port 443 of the reverse proxy faces outward, SSH only from the networks the operator names. Real applies cost money and run only with Owner go (section 9, O22).

Marketplace listings of the clouds are not planned; they need publisher accounts and contracts ([HI] section 4, A).

### 2.7 Worker package for own hardware

A package with `agent-worker`, `egress-proxy` and a systemd unit for pool `self-hosted`. Registration with the pool key from `guildwork worker register`; only outbound HTTPS to the Work API. `doctor` checks the prerequisites (Docker, isolation, kernel). A worker on a workstation or a production host of the operator is not intended: the pool should be dedicated hardware ([05](05-security.md) section 3).

## 3. Profiles per base

A profile is the verified mapping of building blocks to a base. Sources of the cells: [HI] 2.5 to 2.8.

| Profile | Control plane | Postgres with pgvector | Object storage (`BlobStore`) | Secrets (`SecretStore`) | Identity (`CloudIdentity`) | Worker isolation | Package, stage |
|---|---|---|---|---|---|---|---|
| `single-host` | Compose on a Linux VM or own hardware (A) | Container `pgvector/pgvector` (B) | `fs` on a volume or `s3` with SeaweedFS in the bundle (B: Apache-2.0, S3 API, [seaweed]) | `file` (A, bothy pattern B) | `self-issuer` (ADR-22) | Sysbox (kernel from 5.12) or gVisor `systrap` on any VM (B); MicroVM only with `/dev/kvm` (B) | Compose bundle, stage 0 |
| `kubernetes` | Helm, roles separated (A) | external or CloudNativePG `standard` (B) | `s3` against an S3 service of the operator (A) | `file` via mounted Kubernetes secrets, filled by External Secrets Operator from any backend ([eso] B) | `self-issuer`; later `k8s-projected-token` | RuntimeClass `runsc` (B), `sysbox-runc` only on Ubuntu nodes (B, currency of the docs questionable), `kata` only with KVM (B) | Helm, stage 8 |
| `azure` | Container Apps or VM (A; ACA without privileged mode suffices for the control plane) | Flexible Server, `vector` 0.8.2 after allowlisting in `azure.extensions` (B) | `azure-blob` (own driver, no S3 API: G) | `azure-keyvault` (A) | `self-issuer`; `azure-managed-identity` from stage 8 (A; Entra as WIF issuer B [an-wif]) | VM pool with nested virtualization on Dsv5, Dsv6 and others (G) with Sysbox, gVisor or MicroVM; or AKS Pod Sandboxing with Kata (B, Azure Linux only, no Arm64); never ACA | OpenTofu `azure`, stage 0 |
| `aws` | ECS Fargate or EC2 (A) | RDS, pgvector 0.8.2 on 17.10 to 17.11 and 18.4 to 18.6, older minor versions 0.8.0 or 0.8.1 (B) | `s3` (A) | `aws-secretsmanager` (A) | `aws` (IRSA or Pod Identity, u) | EC2 pool; MicroVM only on nested-capable Intel types (C8i, M8i, R8i, C7i and others) or `.metal` (B, vendor announcement); never Fargate (B) | OpenTofu `aws`, stage 8 |
| `gcp` | Cloud Run or GCE (A; whether Cloud Run supports long poll and background jobs without permanently allocated CPU: u) | Cloud SQL, pgvector 0.8.5 (B); PostgreSQL 18 there u | `gcs` (own driver, S3 interop u) | `gcp-secretmanager` (A) | `gcp` (Workload Identity, A) | GCE pool on Intel, not E2 (B), or GKE Sandbox with gVisor or MicroVM (B); never Cloud Run | OpenTofu `gcp`, stage 8 |
| `hetzner` | Cloud server with Compose (A) | self-operated in a container; no managed service (B [hz-cloud]) | `s3` against Hetzner Object Storage (B: S3-compatible, versioning, Object Lock); presigned URLs there u, otherwise SeaweedFS on the server | `file`; later `openbao` (A) | `self-issuer` | Cloud server with Sysbox or gVisor (A); no `/dev/kvm` on cloud servers according to a third-party report (G [hz-kvm]); MicroVM only on dedicated servers (A) | OpenTofu `hetzner`, stage 8; Compose by hand from stage 0 |

Cross-cutting rules:
- **Minimum version of Postgres and pgvector:** PostgreSQL 17 and 18, pgvector from 0.8.2 (A: the lowest level that Azure and the current RDS minor versions have in common, [HI] 2.5). We use only features of this minimum version. On startup, the control plane checks `SELECT extversion FROM pg_extension WHERE extname = 'vector'` and aborts with a clear message if the version is below it. The matrix only changes together with the test matrix (section 9).
- **No MinIO** (ADR-43): the community repo has been archived since 2026-04-25, without binaries ([minio] B). Garage is the lightweight alternative for operators who need neither versioning nor Object Lock (AGPLv3, only expiration in the lifecycle, [garage-s3] B); the bundle does not ship it. Ceph RGW only where Ceph is already running.
- **Retention periods** are enforced by the control plane itself via a deletion job, not via bucket lifecycle, because not every S3 service fully supports lifecycle ([HI] 2.6, A).
- **Isolation is verified, not configured:** On `claim`, the worker reports only capabilities it has verified itself; a policy rule sets the minimum isolation per repo class (`private_own` at least `sysbox` or `gvisor`; `external_code` `microvm` for services that execute repo code, otherwise `sysbox` or `gvisor`; key `isolation_min` in [04](04-configuration-and-limits.md) section 7), and a pool without a matching capability never gets the item (ADR-48; contract in [01](01-plugin-interfaces.md) section 8, rule in [05](05-security.md) section 3).
- **Sysbox is not load-bearing on its own:** support "best effort", "not officially supported by Docker" ([sysbox] B). gVisor is equivalent and runs on any Linux VM without nested virtualization ([gvisor-plat] B).

## 4. Drivers

The driver class (ADR-41) connects the base. Signatures, capabilities and contract suite are in [01](01-plugin-interfaces.md) section 13; here only the mapping to stages. "0b" is the bases sub-stage of stage 0, which is not part of the core ([08](08-roadmap.md) section 1).

| Driver kind | Purpose | Stage 0 | Stage 8 | later |
|---|---|---|---|---|
| `BlobStore` | Raw payloads, transcripts, bundles, artifacts, presigned upload URLs of the Work API, daily audit anchor with Object Lock | `fs`, `s3`, `azure-blob` (0b) | `gcs` | |
| `SecretStore` | Machine secrets, signing keys of the OIDC issuer, rotation | `file`, `env` (read only), `azure-keyvault` (0b) | `aws-secretsmanager`, `gcp-secretmanager` | `openbao` |
| `CloudIdentity` | Tokens without a static key for WIF, Bedrock, Vertex, Foundry | `self-issuer` | `azure-managed-identity`, `aws`, `gcp` | `k8s-projected-token` |

Deliberately without a driver: queue (Postgres with pg-boss, ADR-04), database (only PostgreSQL with pgvector), ingress, TLS, SSO and OTel (standards: HTTP behind a proxy, OIDC, OTLP). The daily audit anchor writes into a `BlobStore` with Object Lock or via `SCMProvider` into a repo of the operator ([05](05-security.md) section 8).

A driver with capability `PRESIGN: none` (such as an S3 service without presigned URLs) forces the upload through the control plane; this is a fallback level with audit, not an error (A).

## 5. Attaching your own plugins, drivers and services

An operator extends the platform without changing the product. The same framework applies to all three classes:

| Point | Rule |
|---|---|
| Manifest | `apiVersion: guildwork-dev.github.io/v1alpha1` (O17), kind, `id`, semver, SPDX license, `trust`, `transport`, config schema, secrets only as names, egress list, `distribution: bundled \| operator_supplied` ([01](01-plugin-interfaces.md) section 1.1) |
| Load condition | passed contract suite in the matching version against recorded responses; no suite, no loading ([01](01-plugin-interfaces.md) rule 1) |
| Trust | `third_party` always runs out of process (subprocess with gRPC or its own container), analyzers always in the sandbox (ADR-40) |
| Distribution | OCI artifact by digest with signature; added via `guildwork plugin add <ref>@<digest>` or the admin UI; active only after an entry in the installation configuration ([04](04-configuration-and-limits.md)) |
| Versions | The core supports the current and the previous major version per kind; older ones are deprecated with a deadline |

**Own services:** A third-party service brings a published, versioned service manifest ([01](01-plugin-interfaces.md) section 14, [02](02-services.md) section 0): input and output artifacts, permission profile, egress, image by digest, eval set. Like every service, it runs as a work item in the sandbox, reads via the platform MCP and acts only via `propose_*` and the Effect Gateway. `live` requires Gate A and Gate B or an adopted reference qualification; otherwise only via operator configuration with the visible label "standard not proven" (ADR-47).

**Own base:** Anyone using a base that is missing here (such as another cloud provider) implements the three drivers or uses the generic ones (`s3`, `file`, `self-issuer`) and `generic-vm`. A profile only counts as supported once it is in the test matrix (section 10).

## 6. Upgrade

Rules (bothy `16-operations.md` section 10, B; required stops after Sentry and GitLab [sentry-rel], [gl-up] B; order schema before server after Temporal [temporal-up] B):
1. **Expand/contract:** Version N removes only what N-1 no longer uses. This way the code of N-1 runs against the schema of N, and the way back is an image switch without a database rollback.
2. **No down migrations.** The next version fixes errors.
3. **`migrate` before the rollout** of `web`, `orchestrator` and workers; as its own job or service.
4. **Backup before the migration:** `migrate` aborts if pending migrations meet an existing schema and there is no successful backup younger than `migrate.recent_backup_max_age`. An empty database is exempt.
5. **N-1 to N** per minor version. Versions with a required stop are listed in the release notes; `migrate` checks itself whether a required stop would be skipped, and then aborts.
6. **Schema check on startup:** a schema that is too old aborts the startup (pointer to `migrate`); a schema that requires a newer version lets the process run, but never become ready.
7. **Do not silently raise pgvector:** `ALTER EXTENSION vector UPDATE` is never part of a migration. The migration only requires the minimum version; `doctor` reports the installed one. Reason: RDS does not raise extensions along with the engine upgrade ([rds-ext] B).
8. **Postgres major version** is a separate step of the operator with a maintenance window.
9. **Worker to control plane:** On `claim`, the worker reports its version; control plane N gives items to workers N and N-1 (minor), to older ones it answers `upgrade_required` without an item. The Work API itself is versioned like plugins.
10. **Running work:** `guildwork upgrade` first sets `drain` (no new claims, running leases end or expire); before the next migration, the control plane raises open runs to the version of the run state machine of the new release, no upgrade lock due to waiting runs (ADR-67, [03](03-flow-and-orchestration.md) sections 2 and 6).
11. **Configuration:** The installation and repo configuration carry `version`; the resolver reads the current and the previous one, `doctor` reports deprecated keys.
12. **Release channels:** `stable` (minor and patch releases) and `next` (pre-releases). No `latest` tag; upgrade only to a named version. Support window and security fixes are governed by [12](12-open-source-and-project.md).

## 7. Backup and restore

| Data | Method | Target |
|---|---|---|
| Postgres, managed (Azure, AWS, Google Cloud) | Point-in-time recovery of the provider plus logical dump (`pg_dump -Fc`) on a schedule | Provider or `BlobStore` outside the installation |
| Postgres, self-operated | physical with WAL archive (pgBackRest, pattern bothy `16-operations.md` 8.1, B) plus logical dump | local repo and a second target outside |
| Objects, driver `fs` | incremental, encrypted backup (restic, pattern bothy, B) | second target |
| Objects, S3, Blob, GCS | Versioning and replication of the service, otherwise mirror without deletion | second bucket or container |
| Secrets | encrypted export (`guildwork backup --secrets`) | offline at the operator |
| Configuration | Files in the operator's own repo | Git |

Rules:
- Targets outside are encrypted and append-only (Object Lock or an account without delete permission); whoever takes over the control plane cannot delete backups (bothy 8.2 rule 3, B).
- Every backup writes a manifest (schema version, row counts per table, last audit hash) and a row in `backup_runs`; a failed run triggers the required alert ([06](06-operations-and-deployment.md) section 4).
- **Automatic restore test** on a schedule (`backup.restore_test.schedule`): last backup into a throwaway database, compare the manifest, check the audit chain. In addition, the test is part of the test matrix (section 9).
- Moving to another base is a restore onto a new target: build the target, trial restore, control plane to `drain`, last backup, restore, compare the manifest, switch DNS and webhook URL (bothy section 11, B).
- Schedules and retention are named values in the installation configuration; stage 0 sets starting values.

## 8. Telemetry and air gap

**Product telemetry to the project is off by default** (ADR-44). Reason: the platform processes code and tickets; most comparable products send by default ([lf-tel], [coder-tel], [n8n-iso] B), trust weighs more here than usage data (A).
- Opt-in in the setup wizard or in the installation configuration (`telemetry.product`, [04](04-configuration-and-limits.md) section 7). Content publicly documented and viewable in the admin UI before sending: product version, profile, number of runs per service and mode, IDs of bundled plugins. Never code, diffs, tickets, prompts, findings, names, repo or org names, URLs.
- The **update notice** (query for the newest version) is a separate switch (`telemetry.update_check`), also off by default.
- OTel data of the installation goes only to the OTLP target that the operator configures ([06](06-operations-and-deployment.md) section 4); this is not product telemetry.

**Air-gap mode** (`air_gap: true`):
- The egress proxy (ADR-20) only lets through the configured SCM, ticket and LLM endpoints as well as the operator's registry and package mirror. This is enforced in the proxy and by network rule, not only via a flag (pattern [HI] M5, A).
- Images, harness packages (with checksum) and analyzer rules come from the mirror; telemetry and update notice are locked, even if they were switched on.
- Harness-specific traffic (telemetry, update check of the CLI) is turned off via its switches and additionally blocked by the proxy; which switches work per harness is demonstrated by the contract test of the `AgentRuntime` plugin (u).
- `doctor` checks the mode actively: a request to a non-approved target must fail.

**Limit:** With a cloud LLM, no installation is completely isolated; code goes to the provider that `data_policy` allows per repo class ([04](04-configuration-and-limits.md)). Fully offline only with a self-hosted model via `ModelProvider` or a harness with a local endpoint; whether such a model reaches the gates is decided by the qualification matrix ([07](07-eval.md)).

## 9. Test matrix per target

This matrix is suite S8 (installation and upgrade); its gate values (0 data loss, 0 telemetry requests by default, in air-gap mode 0 connections except configured targets) are in [07](07-eval.md) section 5. CI runs on GitHub-hosted standard runners of the public repo; they are free there ([gh-runners] B, via [`bothy-vorlage`](../research/bothy-vorlage-projekt-setup.md) 2.4). Real cloud applies cost money per run (amount not measured, estimate only with the module) and run only with Owner go according to O22.

| Target | What is checked | Where | When | Cost |
|---|---|---|---|---|
| Portability `single-host` amd64 and arm64 | fresh runner; installer without a terminal with exactly the documented options; signature verification of the images; smoke run (webhook fixture, review in `shadow`, in stage 0 dummy service); upgrade N-1 to N with data; backup and restore | CI | every release; upgrade test additionally on every migration | free (B) |
| Isolation | Sandbox suite S1 to S6 ([07](07-eval.md) section 5) under Sysbox, gVisor and Firecracker; verified capability report on `claim` | CI (KVM usable on standard Linux runners after a udev rule, [gh-kvm] G) | every PR to worker or sandbox | free |
| Postgres | PostgreSQL 17 and 18, each with pgvector 0.8.2 (minimum version) and the newest version of the image; startup check aborts below the minimum version | CI, container | every PR with a migration | free |
| `BlobStore` | Contract suite against SeaweedFS and Garage (container), `azure-blob` against an emulator (u) and recorded responses; `PRESIGN` per driver | CI | every PR to the driver | free |
| `SecretStore`, `CloudIdentity` | `file`, OpenBao container; cloud drivers against recorded responses; `jti` single use in the WIF exchange | CI | every PR to the driver | free |
| Air gap | Stack with `air_gap: true` in a network without exit except the mirror; every other request must fail | CI | every release | free |
| `kubernetes` | Helm install on kind or k3d with RuntimeClass `runsc`; Sysbox on kind (u) | CI | every release from stage 8 | free |
| OpenTofu modules | `tofu validate`, `plan` against fake credentials | CI | every PR to the module | free |
| `azure` real | Apply in a throwaway environment, portability and smoke test, destroy | Cloud account of the project | before every minor and major release, with Owner go | Money (O22) |
| `aws`, `gcp`, `hetzner` real | like `azure` | respective account | optional: only if the Owner provides an account, with Owner go; not a done criterion (O28) | Money, accounts (O22) |

An apply without go is blocked by the environment: cloud credentials are only in a GitHub environment with a required reviewer, the workflow starts only via `workflow_dispatch` (pattern bothy release environments, B). Every real run ends with destroy and evidence (job log, cost query afterwards).

## 10. Support matrix and delivery per stage

Stages as in [08](08-roadmap.md). "Supported" means: is in the test matrix, real run before release (for cloud profiles) or portability test green. "CI-checked" means: only container, `plan` or fakes, no real apply. "Community" means: documented, not tested.

| Profile, building block | Stage | Status from this stage | Done criterion (evidence) |
|---|---|---|---|
| Repo, release chain, signature | R | Scaffold | Done criterion in [12](12-open-source-and-project.md) and [08](08-roadmap.md) |
| `single-host` amd64 and arm64 | 0 | supported | Portability test green on fresh runners of both architectures (job log) |
| Drivers `fs`, `s3`, `file`, `env`, `self-issuer` | 0 | supported | Contract suites green |
| Drivers `azure-blob`, `azure-keyvault` | 0b (sub-stage, not in the core, [08](08-roadmap.md)) | supported | Contract suites green |
| CLI `install`, `doctor`, `upgrade`, `backup`, `restore`, `worker register`, `github-app create`; setup wizard | 0 | supported | Trial run in `shadow` from the wizard on a fresh installation |
| OpenTofu `generic-vm`, `azure` | 0b | `generic-vm` supported; `azure` CI-checked, supported after the first real apply with Owner go | `tofu plan` green; one real apply with destroy (log) |
| `hetzner` via Compose by hand | 0 | Community | Instructions with `generic-vm` |
| Stages 1 to 7 | 1 to 7 | no new base | every release runs the test matrix of the existing profiles, upgrade N-1 to N with data |
| Helm, `kubernetes` | 8 | CI-checked on kind or k3d | Helm install and smoke green |
| OpenTofu `aws`, `gcp`, `hetzner`; drivers `gcs`, `aws-secretsmanager`, `gcp-secretmanager`, `azure-managed-identity`, `aws`, `gcp` | 8 | CI-checked per module; supported only after an optional real apply with Owner go (O28) | Contract suites green against emulators or fixtures from the public docs; one real apply with destroy per module only in the optional Owner run |
| Isolation `microvm` as mandatory before third-party code | 9 | supported | Sandbox suite green under Firecracker or Kata; policy routes `external_code` only to MicroVM pools |
| `openbao`, `k8s-projected-token` | 9 or later | as needed | Contract suite green |
| Stage 10 | 10 | no new base | like stages 1 to 7 |

Anyone who needs a base today that will only be supported later uses `single-host` on a VM of that base (`generic-vm`); from stage 0, this is the supported path on any Linux VM (A).

## 11. Open points (unverified)

1. Hetzner Cloud without KVM only per third-party report; check on a test instance before the module `hetzner` ([HI] 5.1).
2. Nested virtualization per Azure series only from search excerpts; check against the Learn pages before the real apply of the module `azure` ([HI] 5.2).
3. Presigned URLs for Hetzner Object Storage, Azure SAS and GCS Signed URLs for `presignPut` ([HI] 5.6).
4. Manifest field to deactivate the webhook for the operating mode `private` (section 1.1).
5. Cloud Run as the location of the control plane (long poll, background jobs, CPU allocation).
6. Emulator for `azure-blob` in CI (Azurite, license and coverage).
7. PostgreSQL 18 on Cloud SQL; pgvector on Aurora and AlloyDB ([HI] 5.8).
