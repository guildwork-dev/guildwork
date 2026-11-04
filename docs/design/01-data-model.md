<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# 01 Data model

Detailed design of the platform's Postgres schema. Precedence and abbreviations as in [README](README.md). Rulings of this document: FE-100 to FE-199.

## 1. Purpose and sources

This document defines the database schema of stage 0 (DDL, constraints, indexes, foreign keys, tenant separation, partitioning, retention and deletion), plus the migrator with expand/contract, schema check at startup, lock against parallel migration and the numbering scheme of the migrations of all stages. Section 3.1a names **every** table of the platform with its migration and the document that carries its columns (FE-128): the core tables of stage 0 with DDL here, the tables of individual areas and later stages by reference. The logic lives in the respective detailed designs.

Sources implemented:

| Source | Content implemented here |
|---|---|
| [08](../architecture/08-roadmap.md) section 4 stage 0 item 1 | Table list, migrations forward only, schema version at startup |
| [06](../architecture/06-operations-and-deployment.md) sections 1, 5 | Postgres with pgvector as the only state, `SELECT extversion` at startup, retention, deletion job |
| [11](../architecture/11-installation-and-hosting.md) sections 3, 6, 7 | Minimum version of PostgreSQL and pgvector, upgrade rules 1 to 11, `backup_runs`, manifest |
| [05](../architecture/05-security.md) sections 7, 8 | `tenant_id` in every table with row-level security, audit append-only with hash chain, Run Record, `identity_links` only via OAuth |
| [03](../architecture/03-flow-and-orchestration.md) sections 2, 2.5, 5, 6 | States of run, step, work item, effect, approval; object lock as a unique partial index; inbox and outbox durable; lifting of open runs |
| [04](../architecture/04-configuration-and-limits.md) sections 1, 6 | `config_snapshots` with profile and `qualification_key`, `repo_overrides`, last valid version per file, ledger keys and kinds |
| [01](../architecture/01-plugin-interfaces.md) sections 1 to 3, 13 | Plugin instances with manifest and contract suite, event fields, BlobStore references |
| [07](../architecture/07-eval.md) sections 1, 2 | Case metadata with `origin`, `eval_runs` per `qualification_key`, qualification matrix |
| ADR-02, ADR-04, ADR-11, ADR-16, ADR-29, ADR-41, ADR-65 to ADR-68 | one state, own state machine, finding state in the DB, ledger, audit anchor, no DB abstraction, fail closed, qualification profile, run state machine, object lock |

## 2. Modules and responsibility

**Package** `@guildwork/db` (defined in [README](README.md) section 2). It contains the migrator, migrations, Kysely types, tenant context and thin repositories. The role `migrate` of `apps/control-plane` only calls the migrator.

```
packages/db/
  migrations/
    0001_grundlagen.sql            -- schema, role grants, helper functions, tenants, plugin_instances, identities, identity_links
    0002_eingang.sql               -- inbox, events (partitioned), event_dedupe
    0003_ablauf.sql                -- runs, run_transitions, run_object_locks, run_followups, run_steer_messages, steps, work_items, leases, status_comments
    0004_effekte_befunde.sql       -- effects, approvals, artifacts, policy_decisions, findings, finding_feedback
    0005_ledger_konfig.sql         -- buckets, reservations, reservation_lines, usage (partitioned), config_snapshots, config_last_valid, repo_overrides
    0006_audit_gate.sql            -- audit (partitioned), audit_head, audit_insert, audit_anchors, merge_gate_decisions
    0007_betrieb.sql               -- pools, workers, backup_runs, blob_refs, issued_jwts
    0008_rls.sql                   -- policies for all tables with tenant_id
    0009_wartung.sql               -- functions for partitions and audit retention (SECURITY DEFINER)
    0010 to 0016                   -- tables of the areas eval, alarms, admin UI, operations (section 3.1a, each with its own policy)
    0100 to 1099                   -- blocks of the later stages (section 3.1a)
  src/
    index.ts                       -- public interface of the package
    connection.ts                  -- pool, Kysely instance, statement timeouts
    tenant.ts                      -- withTenant, withInstallationScope
    audit-port.ts                  -- DbAuditSink, port to the AuditWriter (section 2.1, FE-129)
    locks.ts                       -- advisory lock constants (FE-120)
    testing.ts                     -- subpath @guildwork/db/testing, test callback for testkit (section 2.1, FE-130)
    generated/required-versions.ts -- generated at build time (section 4.2)
    schema.ts                      -- Kysely table types (by hand, reconciled by test, FE-114)
    migrator/
      files.ts                     -- loading, parsing header lines, checksum
      lock.ts                      -- advisory lock
      apply.ts                     -- applying with one transaction per file
      gates.ts                     -- backup gate, halt points, pgvector minimum version
    startcheck.ts                  -- schema check at startup (all roles)
    maintenance/
      partitions.ts                -- create partitions ahead of time (section 2.2)
      retention.ts                 -- deletion job (rows and BlobStore objects, section 2.2)
    repos/                         -- one module per table group with typed queries (section 2.3)
  test/
    *.test.ts                      -- against a real Postgres container (Testcontainers), never mocked
```

**Public interface:**

```ts
// packages/db/src/index.ts
import type { Kysely, Transaction } from "kysely";
import type { DB } from "./schema.js";

export type TenantId = string & { readonly __brand: "TenantId" };   // UUIDv7 as text
export type Db = Kysely<DB>;
export type Tx = Transaction<DB>;

export interface DbConfig {
  url: string;                       // resolved from database.url_ref via the SecretStore
  role: "web" | "orchestrator" | "migrate" | "cli" | "ops";   // ops: backup as guildwork_ops (06 FE-648, section 6)
  poolMax: number;                   // db.pool_max
  statementTimeoutMs: number;        // db.statement_timeout_ms
  applicationName: string;           // "guildwork-<role>-<release>"
}
export function connect(cfg: DbConfig, deps: DbDeps): Db;   // DbDeps in section 2.1

// Tenant context (FE-102): sets guildwork.tenant_id via SET LOCAL in a transaction.
export function withTenant<T>(db: Db, tenant: TenantId, fn: (tx: Tx) => Promise<T>): Promise<T>;
// Cross-tenant, only for the callers from the FE-102 list; the reason goes into the audit.
export type InstallationScopeCaller =
  | "retention" | "partition_maintenance" | "audit_anchor" | "admin_cross_org_view"
  | "orchestrator_sweep" | "ledger" | "upgrade_lift" | "backup_manifest"
  | "ingress_process"                // inbox (installation tenant) to event (org tenant), 02 FE-212
  | "plugin_registry"                // loading all plugin instances at startup
  | "work_api_claim" | "worker_auth"; // claim across the tenants of a pool, check pool key (0-E11)
export function withInstallationScope<T>(db: Db, caller: InstallationScopeCaller, reason: string,
                                         fn: (tx: Tx) => Promise<T>): Promise<T>;
// Inside a running withTenant transaction: sets the installation scope only for fn
// and restores the previous value afterwards (FE-123), for example for the reservation in intake.
export function inInstallationScope<T>(tx: Tx, caller: InstallationScopeCaller, reason: string,
                                       fn: (tx: Tx) => Promise<T>): Promise<T>;
// Ingress without tenant context: SECURITY DEFINER function guildwork.ingress_instance(id) (FE-123)
export function ingressInstance(db: Db, pluginInstanceId: string): Promise<IngressInstance | null>;
export interface IngressInstance { id: string; tenantId: string; pluginId: string; state: string;
                                   sourceModes: string[]; webhookSecretRef: string | null }

// Schema check at startup (section 4.2)
export type StartCheck =
  | { status: "ok"; schemaVersion: number; pgvector: string }
  | { status: "schema_too_old"; schemaVersion: number; missing: number[] }            // abort startup
  | { status: "app_too_old"; schemaVersion: number; minAppRelease: string }           // keep running, never ready
  | { status: "pgvector_too_old"; installed: string | null; required: string }        // abort startup
  | { status: "postgres_too_old"; serverVersionNum: number; required: number }       // abort startup
  | { status: "unsafe_db_role"; reason: "superuser" | "bypassrls" | "owns_schema" }  // abort startup (FE-112); bypassrls never for role ops
  | { status: "unreachable"; error: string };
export function startCheck(db: Db, app: { release: string; requiredVersions: number[] }): Promise<StartCheck>;

// Migrator (section 4.1)
export interface MigrationFile {
  version: number;                   // from the file name, unique, within the block of the stage (section 3.1a, FE-126)
  name: string;
  phase: "expand" | "contract" | "data";
  transactional: boolean;            // false only for CREATE INDEX CONCURRENTLY and similar
  minAppRelease?: string;            // after this migration older releases no longer start ready
  haltepunkt: boolean;               // release with halt point (11 section 6 rule 5)
  checksum: string;                  // sha256 over the normalized file content
  sql: string;
}
export interface MigratePlan { current: number; target: number; pending: MigrationFile[]; emptyDatabase: boolean }
export type MigrateResult =
  | { ok: true; applied: number[]; schemaVersion: number }
  | { ok: false; code: MigrateErrorCode; message: string; version?: number };
// Names of the locks equal to 06 section 2.10 (no_recent_backup, halt_point_skipped), FE-133
export type MigrateErrorCode =
  | "lock_timeout" | "checksum_mismatch" | "no_recent_backup" | "halt_point_skipped"
  | "pgvector_too_old" | "postgres_too_old" | "migration_failed" | "unknown_applied_version" | "roles_missing";
export interface MigrateOptions {
  release: string;                   // release that migrates (build constant of the control plane), semver
  backupMaxAgeS: number;             // migrate.recent_backup_max_age in seconds
  lockWaitMs: number;                // migrate.lock_wait_s * 1000
  haltPoints: string[];              // mandatory intermediate versions from release.json upgrade.haltPoints (06 section 2.10); [] until 0-E18-T12
  dryRun?: boolean;                  // only check and plan, apply nothing, no lock longer than the check
}
export interface Migrator {
  plan(): Promise<MigratePlan>;
  apply(opts: MigrateOptions): Promise<MigrateResult>;
}
export function createMigrator(db: Db, files: MigrationFile[]): Migrator;
// Reads migrations/*.sql of the package (or dir), parses the header lines, computes the checksum;
// error "invalid" for a duplicate number, a missing header line phase or a number outside every block (3.1a).
export function loadMigrationFiles(dir?: string): Promise<Result<MigrationFile[]>>;   // Result from @guildwork/core
```

**Who calls whom:** The role `migrate` calls `createMigrator(...).apply()` (section 2.5). Every role calls `startCheck()` at startup. All modules of the control plane work only through `withTenant` or `withInstallationScope`; an access outside of them returns no rows because of row-level security (fail closed). The deletion job and partition maintenance run as pg-boss jobs of the role `orchestrator` ([02-control-plane.md](02-control-plane.md) section 4.9).

### 2.1 Audit port, locks and test callback

`@guildwork/db` may only use `core` and `contracts` ([00](00-codebase-and-conventions.md) section 2.2); the `AuditWriter` lives in the control plane ([04](04-effects-audit-credentials.md) section 2.2.1). The package therefore defines a narrow port that the `AuditWriter` satisfies structurally (FE-129). Until 0-E08 the control plane uses a fake that writes into a list.

**Origin:** `audit-port.ts` and `locks.ts` are created by the package scaffold 0-E02-T01, because `connect(cfg, deps)` receives the port from the start and the migrator (0-E02-T02) needs `MIGRATE_LOCK` and the audit entry `schema.migration_failed`; all three constants are fixed by FE-120. The test `locks.constants_unique` runs with 0-E02-T08, which inserts `AUDIT_CHAIN_LOCK` as a number into `audit_head` and `audit_insert`; it additionally checks that the number in `0006_audit_gate.sql` equals the constant. The fake for tests is `fakeAuditSink()` in `packages/db/test/helpers/audit.ts` (list `entries`, only for tests of this package).

```ts
// packages/db/src/audit-port.ts
export interface DbAuditEntry {
  tenantId: string;                                   // installation tenant for installation scope
  actor: { kind: "system"; id: string };              // id = InstallationScopeCaller
  action: "db.installation_scope" | "retention.batch" | "retention.tenant_purged" | "retention.identity_erased"
        | "schema.migration_failed" | "schema.migration_refused" | "schema.app_too_old";
  subject: string;                                    // for example "installation", "tenant:<id>", "identity:<id>", "migration:<nnnn>"
  details?: Record<string, unknown>;                  // only numbers, IDs, reasons; never contents (FE-117)
}
export interface DbAuditSink { append(tx: Tx, e: DbAuditEntry): Promise<unknown> }
export interface DbDeps { audit: DbAuditSink; log: Logger; metrics: Metrics }   // Logger, Metrics from @guildwork/core

// packages/db/src/locks.ts (FE-120); test locks.constants_unique
export const MIGRATE_LOCK = 7462001;
export const AUDIT_CHAIN_LOCK = 7462011;
export const PARTITION_LOCK = 7462021;
```

`connect` attaches `deps` to the instance; through it `withInstallationScope` and `inInstallationScope` write the entry `db.installation_scope` (section 4.3), the migrator writes `schema.migration_failed` and `schema.migration_refused` (checksum, backup, halt point), `startCheck` writes `schema.app_too_old` (section 5). If the context of a tenant is missing when writing, the package logs `tenant_context_missing` via `deps.log`.

**Test callback** (FE-130): testkit starts Postgres and, for the template `gw_template`, calls a callback from `@guildwork/db` without depending on `db` itself ([00](00-codebase-and-conventions.md) section 2.7, `startPostgres({ migrate })`). The callback lives in the subpath `@guildwork/db/testing` (its own entry in `exports` of the `package.json`), so that production code does not import it by accident; `tools/ci/check_layers.py` blocks the subpath outside of test files via the list `[test_only].subpaths` in `quality/layers.toml` (comparison of the full import specifier, [00](00-codebase-and-conventions.md) section 2.2 and FE-052, test `test_check_layers.py::TestLayers::test_db_testing_subpath_in_production_file_fails`).

```ts
// packages/db/src/testing.ts, import only as "@guildwork/db/testing"
// Creates guildwork_owner (LOGIN, NOSUPERUSER, CREATEROLE only if needed) and guildwork_app (LOGIN, NOBYPASSRLS)
// with fixed test passwords if they are missing, and applies all migrations as guildwork_owner
// (migrator without backup gate, because the DB is empty). Idempotent.
export function migrateForTests(adminUrl: string): Promise<void>;
// Connection URLs of the same database for both roles (for connect with role "migrate" or "web").
export function roleUrls(databaseUrl: string): { ownerUrl: string; appUrl: string };
```

`migrateForTests` is created in 0-E02-T02 (initially with the test migrations from `packages/db/test/fixtures/migrations/`, from 0-E02-T04 on with `packages/db/migrations/`); `testkit.startPostgres` wires it in via the global setup of the Vitest project `integration` (00 section 2.7).

Until migration 0009 is applied (tasks 0-E02-T05 to 0-E02-T08), tests that write into `events`, `usage` or `audit` create the partition of the current month themselves as owner. In the release, 0009 runs in the same migrator run before any role starts.

### 2.2 Maintenance jobs

Handlers of the pg-boss jobs `db-partition-maintenance` and `db-retention` ([02](02-control-plane.md) section 4.9); the registration is done by 0-E05-T05, the required alerts are computed by the alert state machine ([00](00-codebase-and-conventions.md) section 2.9) from `dbAlertSignals`. The handlers work in the installation scope with the callers `partition_maintenance` and `retention` respectively.

```ts
// packages/db/src/maintenance/index.ts (export via src/index.ts)
export interface MaintenanceDeps {
  db: Db;
  blobs: Pick<BlobStore, "delete">;                   // BlobStore from @guildwork/contracts (05 section 2.11.7)
  clock: Clock;
  metrics: Metrics;                                   // core, names in section 2.4
  log: Logger;
  audit: DbAuditSink;                                 // section 2.1
  // Lock of the backup (06 FE-610): returns the holder as long as ops_locks('retention') is set.
  // Not set until 0-E18-T10; until then runRetention deletes without this check. 0-E18-T10 sets the value
  // when registering the job db-retention (row in ops_locks of the installation tenant, expires_at > now()).
  retentionHold?: (tx: Tx) => Promise<string | null>;
}
export interface RetentionConfig {                    // keys retention.* from section 7
  rawDays: number; quarantineDays: number; transcriptsDays: number; evidenceMergedDays: number;
  skippedEventsDays: number; usageDays: number; auditDays: number; repoRemovedGraceDays: number;
  tenantGraceDays: number; batchSize: number; maxDeleteAttempts: number;
}
export type PartitionTable = "events" | "usage" | "audit";
export interface PartitionReport { created: number; leadMonths: Record<PartitionTable, number> }
export function runPartitionMaintenance(deps: MaintenanceDeps, opts: { monthsAhead: number }): Promise<Result<PartitionReport>>;

export interface RetentionReport {
  deletedBlobs: Record<string, number>;               // per blob_refs.class, including missingBlobs
  missingBlobs: number;                               // object was missing on deletion (not_found), row deleted anyway (FE-137)
  deferredLocked: number; failedDeletes: number;
  deletedRows: Record<"inbox" | "event_dedupe" | "events_skipped" | "issued_jwts" | "findings_repo_removed"
                      | "identity_link_flows", number>;   // identity_link_flows from 8-E01-T07 on (13 section 2.1.6 rule 8)
  droppedPartitions: string[]; keptAuditPartitions: string[];   // keptAuditPartitions: without complete anchors
  purgedTenants: string[];
  moreDue: boolean;                                   // batch limit reached; the next run continues
  heldBy: string | null;                              // holder of ops_locks('retention'); then everything else is 0 or empty
}
export function runRetention(deps: MaintenanceDeps, cfg: RetentionConfig): Promise<Result<RetentionReport>>;

// Deletion of a person (section 3.11): clear the login, redact events.actor.login; deleteRawPayloads
// additionally deletes the raw payloads of the affected events immediately (CLI "guildwork data erase-identity", 0-E18).
export function eraseIdentity(deps: MaintenanceDeps, tenant: TenantId, identityId: string,
                              opts: { deleteRawPayloads: boolean; reason: string }): Promise<Result<{ events: number; blobs: number }>>;

// Signals for the alarm rules partition_missing, retention_stuck, audit_anchor_gap (read only)
export interface DbAlertSignals {
  partitionLeadMonths: Record<PartitionTable, number>; // alarm if a value is below 2
  retentionStuck: number;                              // blob_refs with delete_attempts >= maxDeleteAttempts
  auditPartitionsWithoutAnchors: string[];             // due audit partitions that must stay
}
export function dbAlertSignals(db: Db, cfg: Pick<RetentionConfig, "maxDeleteAttempts" | "auditDays">): Promise<DbAlertSignals>;
```

**Order of a run of `runRetention`** (one call per job run, each step in its own transaction in the installation scope `retention`, one entry `db.installation_scope` per run):

1. Ask `retentionHold`; if it returns a holder, the run ends with `heldBy` set, without deleting (log `retention.held`, no audit).
2. Blobs according to section 3.11 "Flow per blob", at most `batchSize` rows from `blob_refs` per run, classes in the order `quarantine`, `raw`, then the rest.
3. Rows: `inbox` with `received_at` older than `rawDays` (quarantine rows: `quarantineDays`) and state `processed`, `duplicate`, `skipped` or `quarantined`; `event_dedupe` with `expires_at < now()`; `events` with `state = 'skipped'` older than `skippedEventsDays`; `issued_jwts` with `expires_at` older than one day; from 8-E01-T07 on `identity_link_flows` with `expires_at + 1 Tag < now()` (class `identity_link_flow`, before deletion the verifier under `pkce_verifier_ref` is overwritten with an empty value if not done yet; rule from [13](13-stage-8-providers-and-bases.md) section 2.1.6 rule 8, counter `guildwork.retention.deleted{class="identity_link_flow"}`). Per table at most `batchSize` rows, `DELETE ... WHERE ctid IN (SELECT ... LIMIT batchSize)`.
4. Partitions: `drop_expired_partitions('usage', usageDays)` and `drop_expired_audit_partitions(auditDays)`.
5. Tenants with `deletion_requested_at` older than `tenantGraceDays` and `deleted_at IS NULL`: at most one tenant per run (section 3.11).
6. One audit entry `retention.batch` with the numbers from the report (`subject = "installation"`), plus `retention.tenant_purged` per deleted tenant.

`moreDue` is true when a step has reached its batch limit; the job handler (0-E05-T05) then schedules another run immediately. A database error in one step rolls back only that step, the others keep running; the result is then `err(appError("transient", "db.maintenance_failed", ...))` (for SQLSTATE of class 08 or 40) or `err(appError("internal", "db.maintenance_failed", ...))` (otherwise) with the partial report in `details`, pg-boss retries according to section 4.9 of 02. `runPartitionMaintenance` takes `PARTITION_LOCK` via `pg_try_advisory_xact_lock` (taken: result `ok` with `created: 0`, log `partition_maintenance.skipped_locked`), calls `ensure_partitions` for `events`, `usage`, `audit` and then measures the lead.

**Required alerts:** The rules `partition_missing` (a value from `partitionLeadMonths` below 2, critical), `retention_stuck` (`retentionStuck > 0`, warning) and `audit_anchor_gap` (`auditPartitionsWithoutAnchors` not empty, warning) are written by the alert state machine ([00](00-codebase-and-conventions.md) section 2.9) as `AlertRule` over `dbAlertSignals`; this package only supplies the signals and tests them (`maintenance.alert_signals`). The rule `app_too_old` reads `schema_state.min_app_release` against the release of the role `orchestrator`. The rules belong to the Epic 0-E19, because 0-E19-T04 depends on 0-E02 and not the other way round (FE-134).

**Repo removal (interim rule):** No component of stage 0 records that a repo leaves the installation (the GitHub plugin skips `installation_repositories.*`, [05](05-plugins-and-contracts.md) section 2.14.3). Until a source exists, `findings` and `finding_feedback` stay until the tenant is deleted, and `deletedRows.findings_repo_removed` is 0. Open item in section 10.

### 2.3 Repository framework

`src/repos/` has one module per table group of the migrations 0001 to 0009 (`basis`, `eingang`, `ablauf`, `effekte`, `befunde`, `ledger`, `konfig`, `audit`, `betrieb`); areas with their own tables (section 3.1a) create their module in `src/repos/<area>/`. Repositories read and write single rows with types; domain logic, state transitions and audit belong to the users. Every function takes the transaction as its first parameter, so that it only runs inside `withTenant` or `withInstallationScope`.

```ts
// Pattern per table, example packages/db/src/repos/ablauf.ts
import type { Insertable, Selectable, Updateable } from "kysely";
export type RunRow = Selectable<DB["runs"]>;
export function insertRun(tx: Tx, row: Insertable<DB["runs"]>): Promise<RunRow>;
export function getRun(tx: Tx, id: string, opts?: { forUpdate?: boolean }): Promise<RunRow | null>;
// Optimistic lock: updates only if version matches; null means "stale"
export function updateRun(tx: Tx, id: string, expectedVersion: bigint, patch: Updateable<DB["runs"]>): Promise<RunRow | null>;
```

All repositories are exported via `@guildwork/db` as the namespace `repos` (`repos.ablauf.getRun`). Queries across several tables are written by the user with Kysely; new shared queries go into the module of the table.

### 2.4 Metrics

Names according to the catalog in [00](00-codebase-and-conventions.md) section 3.3 (FE-131); the building task enters them in `core/src/telemetry/catalog.ts`.

| Name | Kind, unit | Attributes | Source | Task |
|---|---|---|---|---|
| `guildwork.db.startup_unreachable` | counter | `role` | `startCheck` without connection | 0-E02-T03 |
| `guildwork.app.not_ready` | gauge 0 or 1 | `reason` (`app_too_old`) | role after `startCheck` | 0-E02-T03 |
| `guildwork.migrate.lock_timeout` | counter | | migrator | 0-E02-T03 |
| `guildwork.db.partition_lead` | gauge, months | `table` | `runPartitionMaintenance` | 0-E02-T10 |
| `guildwork.retention.deleted` | counter | `class` | `runRetention` | 0-E02-T10 |
| `guildwork.retention.locked` | counter | `class` | `runRetention` (Object Lock) | 0-E02-T10 |
| `guildwork.db.append_only_violation` | counter | `table` (`audit`, `merge_gate_decisions`) | Kysely plugin in `connection.ts`: error with SQLSTATE `42501` and message "... ist append-only" (FE-135) | 0-E02-T08 |

`connect` does not count the maintenance metrics itself; they come via `MaintenanceDeps.metrics`. For the startup check and the migrator the role receives a `Metrics` from `@guildwork/core` (section 2.5); `guildwork.db.append_only_violation` is counted by the plugin via `DbDeps.metrics` (FE-135).

### 2.5 Role `migrate`

The role is a module of `apps/control-plane` (0-E02-T02), `main.ts` selects it according to FE-200 from [02](02-control-plane.md) section 2.4 (0-E05-T10). Until 0-E05-T10 it is only called from tests.

```ts
// apps/control-plane/src/roles/migrate.ts
export interface MigrateRoleInput {
  ownerUrl: string;            // from database.migrate_url_ref, resolved via the SecretStore by main.ts (0-E05-T10)
  appUrl: string;              // from database.url_ref; only for the "not equal" check and startCheck after the run
  release: string;             // build constant of the control plane
  lockWaitS: number;           // migrate.lock_wait_s
  backupMaxAgeS: number;       // migrate.recent_backup_max_age
  haltPoints: string[];        // from release.json upgrade.haltPoints (0-E18-T12); [] until then
  dryRun: boolean;             // subcommand "control-plane migrate --dry-run"
}
export interface MigrateRoleDeps { log: Logger; metrics: Metrics; audit: DbAuditSink; clock: Clock }
export function runMigrateRole(input: MigrateRoleInput, deps: MigrateRoleDeps): Promise<0 | 1 | 2>;
```

| Case | Exit code | Log event |
|---|---|---|
| all pending files applied or nothing pending | 0 | `migrate.done` with `applied`, `schemaVersion`, `durationMs` |
| `--dry-run` | 0 | `migrate.plan` with `pending` (numbers) and the result of the locks (backup, halt point) |
| `ownerUrl` equal to `appUrl`, unknown option, missing key | 2 | `migrate.invalid_input` |
| every `MigrateErrorCode` | 1 | `migrate.failed` with `code`, `version`, `sqlstate` (for `migration_failed`) |
| database not reachable after `db.startup_wait_s` | 1 | `migrate.failed` with `code = "unreachable"` |

For each applied file the role writes `migrate.applied` with `version`, `name`, `phase`, `durationMs`. From 0-E18-T12 on, the role calls the lifting of open runs of the control plane before `apply()` (ADR-67, queue `orchestrator-upgrade-lift` from 02, synchronously via the handler in the same process) and aborts with exit 1 if it fails, without migrating; the locks for backup and halt point remain solely in the migrator (`gates.ts`), `apps/control-plane/src/migrate/guards.ts` from [06](06-installation-operations-ui.md) only supplies their inputs (`haltPoints` from `release.json`, `backupMaxAgeS`) and maps the codes to messages (FE-133).

## 3. Data

### 3.1 Conventions

| Topic | Definition | Ruling |
|---|---|---|
| Minimum version | PostgreSQL 17, tested 17 and 18; pgvector from 0.8.2 | FE-100 |
| Schema | all tables in the schema `guildwork`; pg-boss in its own schema `pgboss` | FE-101 |
| Tenants | column `tenant_id uuid NOT NULL` in every domain table, row-level security with `FORCE` | FE-102 |
| IDs | `uuid` as UUIDv7, generated in `@guildwork/core`, without database default | FE-103 |
| States | `text` with `CHECK`, no PostgreSQL `ENUM` types | FE-104 |
| Time | `timestamptz`, default `now()` only for `created_at`, all deadlines as absolute points in time | FE-105 |
| Money | `numeric(14,6)` in USD; `NULL` means "unknown", never 0 | FE-106 |
| Foreign content | never stored inline as prompt text; raw data and large contents in the BlobStore, in the DB only `*_ref` (key) and `*_sha256` | FE-107 |
| Secrets | never in the DB; only references `secret://...` (`*_secret_ref`) and hashes of tokens | FE-108 |
| Partitioning | `events`, `usage`, `audit` monthly by time; otherwise none | FE-109 |
| Foreign keys | within non-partitioned tables with `ON DELETE RESTRICT`; no foreign keys into partitioned tables | FE-110 |
| Object keys | `object_key text` in normalized form (section 3.4) | FE-111 |
| Roles | `guildwork_owner` (owns everything, only `migrate`), `guildwork_app` (all other roles, `NOBYPASSRLS`), `guildwork_ops` (only role `ops` for backup and restore test, `BYPASSRLS`, [06](06-installation-operations-ui.md) FE-648; privileges in section 6) | FE-112 |
| Check rules with value lists | single-column `CHECK` constraints are named `<table>_<column>_check`; lists that later stages extend carry the name explicitly | FE-138 |

Naming rules: tables in the plural, columns in `snake_case`, timestamps end in `_at`, references into the BlobStore in `_ref`, hashes in `_sha256` (`bytea`, 32 bytes) or `_hash` for text hashes. Every table with mutable rows has `updated_at`, set by the application (no trigger, so that Kysely types and tests see it).

### 3.1a Migration blocks and table directory

**Numbering scheme (FE-126):** Every stage has its own block of migration numbers; a number belongs to exactly one file in the whole project. Within a block the building task assigns the next free number, unless the table below fixes it. Gaps between and within blocks are allowed. The migrator applies all unapplied files of the release in ascending order, even if their number is below the highest applied one (stages that are built in parallel); a file may only presuppose tables that a file with a smaller number creates.

| Stage | Block | Stage | Block |
|---|---|---|---|
| 0 (also 0b) | 0001 to 0099 | 6 | 0600 to 0699 |
| 1 | 0100 to 0199 | 7a | 0700 to 0749 |
| 2 | 0200 to 0299 | 7 | 0750 to 0799 |
| 3 | 0300 to 0399 | 8 | 0800 to 0899 |
| 4 | 0400 to 0499 | 9 | 0900 to 0999 |
| 5 | 0500 to 0599 | 10 | 1000 to 1099 |

In machine-readable form the table lives in `packages/db/migrations/blocks.json` (`{ "<stage>": [<from>, <to>] }`, created by 0-E02-T02); `loadMigrationFiles` (error `invalid`) and the linter (rule `number-outside-block`, section 4.4) read only this file, the test `migrator.blocks_match_doc` compares it with the table above.

**Table directory (FE-128).** A table name occurs exactly once in the project. "Columns" names the document that carries the columns bindingly; where it says "01", the DDL is in this document. For tables with a reference, the named task writes the SQL file according to the conventions from section 3.1 (tenant with row-level security and policy in the same file, section 3.9). Installation-wide tables without `tenant_id` (`backup_runs`, `audit_anchors`, `alerts`, `alert_deliveries`, `alerting_heartbeat`, `price_entries`, `job_outbox`) instead get the privileges as in section 3.9 for installation-wide tables.

| Table | Columns | Migration | Building task |
|---|---|---|---|
| `schema_migrations`, `schema_state`, `tenants`, `plugin_instances`, `identities`, `identity_links` | 01 (3.2) | 0001 | 0-E02 |
| `inbox`, `events`, `event_dedupe` | 01 (3.3) | 0002 | 0-E02 |
| `runs`, `run_transitions`, `run_object_locks`, `run_followups`, `run_steer_messages`, `steps`, `work_items`, `leases`, `status_comments` | 01 (3.4) | 0003 | 0-E02 |
| `policy_decisions`, `effects`, `approvals`, `artifacts`, `findings`, `finding_feedback` | 01 (3.5) | 0004 | 0-E02 |
| `config_snapshots`, `config_last_valid`, `repo_overrides`, `buckets`, `reservations`, `reservation_lines`, `usage` | 01 (3.6) | 0005 | 0-E02 |
| `audit`, `audit_anchors`, `merge_gate_decisions` | 01 (3.7) | 0006 | 0-E02 |
| `pools`, `workers`, `backup_runs`, `blob_refs`, `issued_jwts` | 01 (3.8) | 0007 | 0-E02 |
| `eval_suites`, `eval_cases`, `eval_runs`, `eval_case_results`, `qualification`, `qualification_parts`, `eval_references`, `qualification_adoptions`, `shadow_ratings` | [07](07-eval-and-qualification.md) section 3 | 0010 | 0-E20-T06 |
| `alerts`, `alert_deliveries`, `alerting_heartbeat` | [00](00-codebase-and-conventions.md) section 3.4 | 0011 | 0-E19-T04 |
| `admin_sessions` | [06](06-installation-operations-ui.md) section 3.1 | 0012 | 0-E17-T01 |
| `break_glass_accounts` | 06 section 3.1 | 0013 | 0-E17-T03 |
| `installation_settings`, `installation_settings_history`, `setup_steps` | 06 section 3.1 | 0014 | 0-E17-T05 |
| `ops_locks` | 06 section 3.1 | 0015 | 0-E18-T10 |
| `update_checks` | 06 section 3.1 | 0016 | 0-E18-T16 |
| `job_outbox` (only if pg-boss cannot send within the transaction; installation-wide, privileges in section 3.9) | [02](02-control-plane.md) section 4.9.1 | 0017 | 0-E02-T13 |
| `review_pr_state` | [08](08-reviewer.md) section 3.1 | 0101 | 1-E01-T03 |
| `kill_switches` | 06 section 3.1 | 0102 | 1-E08-T04 |
| `plan_versions`, `design_versions`, `change_proposals`, `env_snapshots`, `work_snapshots`, `dependency_requests`, `run_untrusted_inputs`, `agent_ci_checks`, `analyzer_runs`, `analyzer_baselines`, `quality_gate_decisions`, `pipeline_stage_outcomes`, `plan_approval_shadow`, `input_grants`; column `approvals.bound_subject` | [10](10-planner-architect-coder.md) section 3.2 | 0201 to 0215 (0208 free; `input_grants` 0215) | Epics of stage 2 |
| `qa_flake_observations`, `qa_quarantine` | [11](11-qa-prfix-automerge.md) section 3.1 | block 0300 | stage 3 |
| `prfix_rounds`, `prfix_reruns`, `watch_subscriptions` | 11 section 3.1 | block 0400 | stage 4 |
| `shadow_outcomes`, `post_merge_watches`, `autonomy_qualification` | 11 section 3.1 | block 0500 | stage 5 |
| `review_auto_approve_decisions`, `review_auto_approvals`, `dev_tokens`, `dev_auth_sessions`, `review_metrics_daily`, `learnings`, `learning_events`; columns `finding_feedback.actor_role`, `findings.dev_claim_*` | [09](09-reviewer-companion-features-and-learnings.md) sections 3.1 and 3.2 | block 0600 | stage 6 |
| `learning_votes`, `learning_uses`, `learning_imports`, `kb_layer_state` | 09 section 3.1 | block 0700 | stage 7a |
| `kb_files`, `kb_symbols`, `kb_edges`, `kb_summaries`, `kb_chunks`, `kb_vectors`, `kb_items`, `rule_stats`, `standard_candidates`, `compiled_rules`, `repo_eval_gates` | [12](12-expansion.md) section 3.1 | block 0750 | stage 7 |
| `identity_link_flows`, `dispatch_records`, `price_entries` (installation-wide, FE-1255); columns `identity_links.revoked_by`, `pools.health`, `pools.unhealthy_since`, `work_items.pool_alt` | [13](13-stage-8-providers-and-bases.md) section 3.2 | block 0800 | stage 8 |
| `plugin_artifacts`, `scm_static_tokens`, `work_item_sessions`, `notifier_messages`, `notifier_approvals`, `run_handoffs`, `coder_fanouts`, `coder_fanout_members`, `injection_signals`, `kb_doc_pages`; columns `runs.injection_suspected`, `runs.human_commits_seen`, `runs.integration_conflict`, `steps.parent_step_id`, `steps.fanout_kind`, `steps.fanout_index`, `kb_chunks.doc_key`, `identity_links.link_kind` | [14](14-stage-9-breadth-and-hardening.md) section 3.1 | 0901 to 0911 | stage 9 |
| `campaigns`, `campaign_children`; column `runs.campaign_id`; extended check rules `runs.state`, `runs.object_kind`, `buckets.key_kind` | [15](15-stage-10-edge-layers.md) section 3.1 | 1001, 1002 (tasks 10-E05-T01, 10-E02-T02) | stage 10 |
| `user_preferences` (configuration layer `user`, FE-142) | 01 (3.12) | next free number in the block of the building stage | open: no task of the plan requires user preferences so far (section 10); until then the layer is `absent` (02 section 4.6) |

Columns and check rules that later stages add to tables of this document are additionally listed at the end of the respective section (3.2, 3.4, 3.6) as a reference with migration and leading document; the DDL stays where the table above names it.

A document that needs a column of a table from another document names it as a requirement; the building task adds it in an expand migration of its own block and records it in the leading document. Repos have no table of their own; the reference everywhere is `repo_key` according to FE-111.

### 3.2 Foundations, tenants and identity (migration 0001)

```sql
-- 0001_grundlagen.sql
-- phase: expand
-- transactional: true
CREATE SCHEMA IF NOT EXISTS guildwork AUTHORIZATION guildwork_owner;
CREATE EXTENSION IF NOT EXISTS vector;          -- never ALTER EXTENSION ... UPDATE (11 section 6 rule 7)

GRANT USAGE ON SCHEMA guildwork TO guildwork_app;
ALTER DEFAULT PRIVILEGES FOR ROLE guildwork_owner IN SCHEMA guildwork
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO guildwork_app;
ALTER DEFAULT PRIVILEGES FOR ROLE guildwork_owner IN SCHEMA guildwork
  GRANT USAGE, SELECT ON SEQUENCES TO guildwork_app;

-- Schema of the queue (FE-101, FE-141): created empty; the tables are created by installQueueSchema with the owner connection
-- after the last migration (02 FE-276), they inherit DML for guildwork_app via the default privileges.
-- Unverified, to be proven in 0-E02-T13: whether pg-boss accepts an existing empty schema and whether it needs DDL at runtime
-- (for example when creating a queue); in that case installQueueSchema also creates the queues as owner.
CREATE SCHEMA IF NOT EXISTS pgboss AUTHORIZATION guildwork_owner;
GRANT USAGE ON SCHEMA pgboss TO guildwork_app;
ALTER DEFAULT PRIVILEGES FOR ROLE guildwork_owner IN SCHEMA pgboss
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO guildwork_app;
ALTER DEFAULT PRIVILEGES FOR ROLE guildwork_owner IN SCHEMA pgboss
  GRANT USAGE, SELECT ON SEQUENCES TO guildwork_app;

-- Privileges of the optional role guildwork_ops (06 FE-648, FE-141). It reads via pg_read_all_data and BYPASSRLS;
-- it writes only where the backup writes. The role does not exist in every installation, therefore the
-- migrator grants the privileges at the end of each run via this function (section 4.1), not via GRANT in a file.
CREATE FUNCTION guildwork.grant_ops_role() RETURNS boolean LANGUAGE plpgsql AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'guildwork_ops') THEN RETURN false; END IF;
  GRANT USAGE ON SCHEMA guildwork, pgboss TO guildwork_ops;
  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA pgboss TO guildwork_ops;   -- own pg-boss instance (06)
  GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA pgboss TO guildwork_ops;
  IF to_regclass('guildwork.backup_runs') IS NOT NULL THEN
    GRANT SELECT, INSERT, UPDATE ON guildwork.backup_runs TO guildwork_ops; END IF;
  IF to_regclass('guildwork.ops_locks') IS NOT NULL THEN                   -- 0015, 06 section 3.1
    GRANT SELECT, INSERT, UPDATE, DELETE ON guildwork.ops_locks TO guildwork_ops; END IF;
  RETURN true;
END $$;
REVOKE ALL ON FUNCTION guildwork.grant_ops_role() FROM PUBLIC;          -- only the owner calls it

-- Tenant context (FE-102). Without setting it, all policies return no rows.
CREATE FUNCTION guildwork.current_tenant() RETURNS uuid
  LANGUAGE sql STABLE AS $$ SELECT nullif(current_setting('guildwork.tenant_id', true), '')::uuid $$;
CREATE FUNCTION guildwork.installation_scope() RETURNS boolean
  LANGUAGE sql STABLE AS $$ SELECT coalesce(current_setting('guildwork.scope', true), '') = 'installation' $$;

CREATE TABLE guildwork.schema_migrations (
  version        integer PRIMARY KEY CHECK (version > 0),
  name           text NOT NULL,
  phase          text NOT NULL CHECK (phase IN ('expand','contract','data')),
  checksum       text NOT NULL CHECK (checksum ~ '^[0-9a-f]{64}$'),
  min_app_release text,
  haltepunkt     boolean NOT NULL DEFAULT false,
  applied_at     timestamptz NOT NULL DEFAULT now(),
  applied_by_release text NOT NULL,
  duration_ms    integer NOT NULL CHECK (duration_ms >= 0)
);

CREATE TABLE guildwork.schema_state (
  id              smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  schema_version  integer NOT NULL,                       -- highest applied migration
  min_app_release text NOT NULL,                          -- max(min_app_release) of all applied migrations
  automaton_versions integer[] NOT NULL DEFAULT '{1}',    -- run automata that carry runs in the DB (ADR-67)
  last_release    text NOT NULL,                          -- release of the last successful migrator run, even without a new file (halt point check, FE-133)
  updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE guildwork.tenants (
  id              uuid PRIMARY KEY,
  kind            text NOT NULL CHECK (kind IN ('installation','org')),
  installation_id text NOT NULL,                          -- field installation from installation.yaml
  org_key         text,                                   -- e.g. "github/github.com/example-org"; NULL only for kind = 'installation'
  display_name    text NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  deletion_requested_at timestamptz,                      -- deletion of a tenant, section 3.11
  deleted_at      timestamptz,
  drain_since     timestamptz,                            -- drain switch, only row kind = 'installation' (03 section 3)
  CHECK ((kind = 'installation') = (org_key IS NULL))
);
CREATE UNIQUE INDEX tenants_one_installation ON guildwork.tenants (installation_id) WHERE kind = 'installation';
CREATE UNIQUE INDEX tenants_org_key ON guildwork.tenants (installation_id, org_key) WHERE kind = 'org';
-- tenants itself carries no tenant_id; policy: row visible if id = current_tenant() or installation_scope().

CREATE TABLE guildwork.plugin_instances (
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  config_id       text NOT NULL,                          -- InstanceDecl.instanceId from the configuration, e.g. "gh", "cc-abo" (05 section 2.5)
  config_level    text NOT NULL CHECK (config_level IN ('installation','org')),
  config          jsonb NOT NULL,                         -- instance configuration without secrets (only secret:// references)
  plugin_id       text NOT NULL,                          -- manifest.id, e.g. "github"
  plugin_version  text NOT NULL,                          -- semver
  api_version     text NOT NULL CHECK (api_version IN ('guildwork-dev.github.io/v1alpha1','guildwork-dev.github.io/v1')),
  kinds           text[] NOT NULL CHECK (cardinality(kinds) > 0),
  class           text NOT NULL CHECK (class IN ('plugin','driver','service')),
  trust           text NOT NULL CHECK (trust IN ('first_party','vetted','third_party')),
  transport       text NOT NULL CHECK (transport IN ('in_process','subprocess_grpc','subprocess_jsonrpc','http','wasm')),
  manifest        jsonb NOT NULL,                         -- complete manifest, without secrets (names only)
  config_hash     text NOT NULL,                          -- sha256 of the instance configuration
  attestation     jsonb NOT NULL,                         -- ContractAttestation (05 section 2.10): suite version per kind, passedAt, fixturesHash
  webhook_secret_ref text,                                -- secret://..., only for a TriggerSource with webhook
  state           text NOT NULL CHECK (state IN ('declared','validated','initializing','ready','degraded','failed','disabled')),   -- InstanceState (05 section 2.5)
  state_reason    jsonb,                                  -- LoadError {code, message, path?}
  capabilities    jsonb,                                  -- {cap: {level, note?}} from the probe run
  capabilities_at timestamptz,
  health          jsonb,                                  -- last HealthReport, plus field cursor for reconcile and poll (02 section 4.1)
  health_at       timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, config_id),
  CHECK (webhook_secret_ref IS NULL OR webhook_secret_ref LIKE 'secret://%')
);
CREATE INDEX plugin_instances_by_plugin ON guildwork.plugin_instances (tenant_id, plugin_id) WHERE state IN ('ready','degraded');   -- "active" means ready or degraded

-- Ingress knows no tenant before the signature check (FE-123): exactly one row per ID,
-- runs as owner; the policies allow current_user = 'guildwork_owner' (0008, FE-123).
CREATE FUNCTION guildwork.ingress_instance(p_id uuid)
  RETURNS TABLE (id uuid, tenant_id uuid, plugin_id text, state text, kinds text[], manifest jsonb, webhook_secret_ref text)
  LANGUAGE sql STABLE SECURITY DEFINER
  SET search_path = guildwork, pg_temp AS $$
  SELECT p.id, p.tenant_id, p.plugin_id, p.state, p.kinds, p.manifest, p.webhook_secret_ref
  FROM guildwork.plugin_instances p WHERE p.id = p_id
$$;
REVOKE ALL ON FUNCTION guildwork.ingress_instance(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION guildwork.ingress_instance(uuid) TO guildwork_app;

CREATE TABLE guildwork.identities (
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  plugin_instance_id uuid NOT NULL REFERENCES guildwork.plugin_instances(id),
  provider_user_id text NOT NULL,                         -- stable ID at the provider, never the login
  login           text,                                   -- display; NULL after deletion (section 3.11)
  kind            text NOT NULL CHECK (kind IN ('human','bot','app','automation')),
  is_self         boolean NOT NULL DEFAULT false,         -- own bot identity of the installation
  first_seen_at   timestamptz NOT NULL DEFAULT now(),
  last_seen_at    timestamptz NOT NULL DEFAULT now(),
  erased_at       timestamptz,
  UNIQUE (plugin_instance_id, provider_user_id),
  CHECK (erased_at IS NULL OR login IS NULL)
);
CREATE INDEX identities_login ON guildwork.identities (tenant_id, plugin_instance_id, lower(login)) WHERE login IS NOT NULL;

CREATE TABLE guildwork.identity_links (
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  work_item_identity_id uuid NOT NULL REFERENCES guildwork.identities(id),   -- for example a Jira account
  scm_identity_id uuid NOT NULL REFERENCES guildwork.identities(id),         -- for example a GitHub login
  confirmed_via   text NOT NULL CHECK (confirmed_via = 'oauth'),             -- never email equality (05 section 7)
  oauth_subject_sha256 bytea NOT NULL CHECK (length(oauth_subject_sha256) = 32),
  confirmed_at    timestamptz NOT NULL,
  revoked_at      timestamptz,
  revoked_reason  text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  CHECK (work_item_identity_id <> scm_identity_id)
);
CREATE UNIQUE INDEX identity_links_active ON guildwork.identity_links (work_item_identity_id, scm_identity_id)
  WHERE revoked_at IS NULL;
CREATE UNIQUE INDEX identity_links_one_scm_per_item_identity ON guildwork.identity_links (work_item_identity_id)
  WHERE revoked_at IS NULL;
```

**Extensions by later stages** (DDL in the leading document, rule from section 3.1a):

| Column | Form | Migration, task | Leading |
|---|---|---|---|
| `identity_links.revoked_by` | `text`, `"self"` or `"admin:<sha256 des Subjekts>"` | 0801, 8-E01-T07 | [13](13-stage-8-providers-and-bases.md) section 3.2 |
| `identity_links.link_kind` | `text NOT NULL DEFAULT 'work_item'`, `CHECK (link_kind IN ('work_item','chat'))`; for `chat` the chat identity is in `work_item_identity_id` (14 FE-1413) | 0910, 9-E02-T02 | [14](14-stage-9-breadth-and-hardening.md) section 3.1 |

### 3.3 Intake (migration 0002)

```sql
-- 0002_eingang.sql
-- phase: expand
CREATE TABLE guildwork.inbox (
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  plugin_instance_id uuid NOT NULL REFERENCES guildwork.plugin_instances(id),
  source_mode     text NOT NULL CHECK (source_mode IN ('webhook','ci_event','poll','relay','schedule','manual')),
  delivery_id     text NOT NULL,                          -- X-GitHub-Delivery and others; synthetic for poll/reconcile (FE-205)
  received_at     timestamptz NOT NULL DEFAULT now(),
  raw_ref         text,                                   -- BlobStore key raw/<tenant>/<yyyy>/<mm>/<id>; NULL only for quarantine above the size limit
  raw_sha256      bytea CHECK (length(raw_sha256) = 32),
  raw_bytes       integer NOT NULL CHECK (raw_bytes >= 0),
  headers         jsonb NOT NULL,                         -- only allowlisted headers, signature headers redacted
  signature_scheme text NOT NULL CHECK (signature_scheme IN ('hmac_sha256_hex','standard_webhooks','jwt','shared_secret','oidc','none')),
  signature_verified boolean NOT NULL,
  signature_strength text NOT NULL CHECK (signature_strength IN ('strong','weak')),
  state           text NOT NULL CHECK (state IN ('received','processing','processed','duplicate','skipped','quarantined','failed')),
  attempts        smallint NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  last_error      jsonb,
  processed_at    timestamptz,
  CHECK (state <> 'quarantined' OR signature_verified = false),
  CHECK (state = 'quarantined' OR (raw_ref IS NOT NULL AND raw_sha256 IS NOT NULL))
);
-- Dedupe only over verified intakes: a redelivery with the same delivery ID after a
-- quarantine (for example after correcting the webhook secret) is accepted (FE-124).
CREATE UNIQUE INDEX inbox_delivery_unique ON guildwork.inbox (plugin_instance_id, delivery_id)
  WHERE state <> 'quarantined';
CREATE INDEX inbox_pending ON guildwork.inbox (received_at) WHERE state IN ('received','processing','failed');
CREATE INDEX inbox_retention ON guildwork.inbox (received_at);

CREATE TABLE guildwork.events (
  id              uuid NOT NULL,
  received_at     timestamptz NOT NULL,                   -- partition key
  tenant_id       uuid NOT NULL,
  inbox_id        uuid NOT NULL,
  plugin_instance_id uuid NOT NULL,
  delivery_id     text NOT NULL,
  dedupe_key      text NOT NULL,
  occurred_at     timestamptz NOT NULL,
  source_mode     text NOT NULL,
  signature       jsonb NOT NULL,                         -- {scheme, verified, strength}
  actor           jsonb NOT NULL,                         -- Actor from 01 section 1.2, without email
  actor_identity_id uuid,
  what_action     text NOT NULL,
  what_subject    text NOT NULL,
  where_ref       jsonb NOT NULL,                         -- {repo?, change?, workItem?, thread?}
  object_key      text,                                   -- FE-111, NULL if there is no object
  command         jsonb,                                  -- {name, args, origin}
  mention         jsonb,
  text_ref        text,                                   -- untrusted text in the BlobStore
  text_sha256     bytea,
  edited_after_trigger boolean NOT NULL DEFAULT false,
  links           jsonb NOT NULL DEFAULT '{"workItemKeys":[],"closes":[],"urls":[]}',
  raw_ref         text NOT NULL,
  routing_on      text,                                   -- routing name after mapping (02 FE-206)
  resolved        jsonb,                                  -- ResolvedEvent part from the router: permission, identity
  state           text NOT NULL CHECK (state IN ('new','routed','skipped','delivered','run_started','failed')),
  skip_reason     text,
  run_id          uuid,
  routed_at       timestamptz,
  PRIMARY KEY (received_at, id),
  CHECK (state <> 'skipped' OR skip_reason IS NOT NULL)
) PARTITION BY RANGE (received_at);
CREATE INDEX events_by_id ON guildwork.events (id);
CREATE INDEX events_by_object ON guildwork.events (tenant_id, object_key, received_at DESC) WHERE object_key IS NOT NULL;
CREATE INDEX events_open ON guildwork.events (received_at) WHERE state = 'new';
CREATE INDEX events_by_run ON guildwork.events (run_id) WHERE run_id IS NOT NULL;

-- Dedupe across the partition boundary (FE-110: unique indexes on partitioned tables
-- would have to contain received_at and are therefore unsuitable for the dedupe).
CREATE TABLE guildwork.event_dedupe (
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  dedupe_key      text NOT NULL,
  first_event_id  uuid NOT NULL,
  first_seen_at   timestamptz NOT NULL DEFAULT now(),
  expires_at      timestamptz NOT NULL,                   -- first_seen_at + ingress.dedupe_window_h
  hits            integer NOT NULL DEFAULT 0,
  PRIMARY KEY (tenant_id, dedupe_key)
);
CREATE INDEX event_dedupe_expiry ON guildwork.event_dedupe (expires_at);
```

### 3.4 Flow (migration 0003)

**Object key (FE-111):** `object_key` is a unique, stable string per ticket or PR, independent of title and login: `pr:<plugin_instance_id>:<repo_provider_id>:<number>` or `item:<plugin_instance_id>:<project>:<key>`. Built only by `objectKey()` in `@guildwork/contracts` (`packages/contracts/src/events/object-key.ts`, definition in [05](05-plugins-and-contracts.md) section 2.11.1); a test checks that renaming a repo does not change the key (provider ID instead of name).

```sql
-- 0003_ablauf.sql
-- phase: expand
CREATE TABLE guildwork.runs (
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  kind            text NOT NULL CHECK (kind IN ('pipeline','single_service')),
  pipeline        text,                                   -- e.g. "ticket-to-pr"
  service         text,                                   -- for single_service: ServiceId
  object_key      text NOT NULL,
  object_kind     text NOT NULL CONSTRAINT runs_object_kind_check CHECK (object_kind IN ('ticket','pr')),   -- name fixed (FE-138)
  pr_object_key   text,                                   -- as soon as a pipeline has opened its agent PR
  repo_ref        jsonb,                                  -- RepoRef
  work_item_ref   jsonb,
  change_ref      jsonb,                                  -- ChangeRef at the time of the trigger
  state           text NOT NULL CONSTRAINT runs_state_check CHECK (state IN (   -- name fixed (FE-138)
                    'received','queued','triaging','planning','designing','awaiting_input','awaiting_plan_approval',
                    'coding','awaiting_risk_approval','handed_off','proposing','verifying','fixing','merge_gate',
                    'merging','awaiting_human_review','paused_budget','merged',
                    'done','skipped','cancelled','expired','failed')),
  resume_state    text,                                   -- only for awaiting_input and paused_budget
  end_reason      text,                                   -- for example skipped(triage_rejected), failed(policy:POL-020)
  automaton_version integer NOT NULL CHECK (automaton_version > 0),
  version         bigint NOT NULL DEFAULT 0,              -- optimistic lock per transition
  trigger_kind    text NOT NULL DEFAULT 'event' CHECK (trigger_kind IN ('event','eval','eval_judge','admin')),   -- FE-139
  trigger_event_id uuid,                                  -- events.id for trigger_kind = 'event' (no FK, FE-110)
  trigger         jsonb,                                  -- trigger without event: EvalTriggerV1, EvalJudgeTriggerV1 (07 sections 2.16.5, 2.17.3)
                                                          -- or {kind: "admin", subject, purpose} (probe run, 06 section 2.7)
  effect_sink     text NOT NULL DEFAULT 'live' CHECK (effect_sink IN ('live','record')),   -- 02 FE-241; record: effects only as a record (04)
  trigger_identity_id uuid REFERENCES guildwork.identities(id),
  config_snapshot_id uuid,                                -- FK in 0005
  base_sha        text,
  head_sha        text,
  hold            boolean NOT NULL DEFAULT false,         -- @agent hold
  foreign_input_seen boolean NOT NULL DEFAULT false,      -- ADR-60; individual evidence in run_untrusted_inputs (10 section 3.2)
  repo_class      text CHECK (repo_class IN ('private_own','external_code')),
  ci_variant      text CHECK (ci_variant IN ('agent_fork','guarded_workflows','none')),
  deadline_at     timestamptz,                            -- next deadline of the current state
  cost_usd        numeric(14,6),
  traceparent     text,                                   -- W3C, Run Record (06 section 3.3)
  harness_version text,                                   -- Run Record (05 section 3.1)
  harness_sha256  text,
  credential_kind text,
  operator_checks jsonb,                                  -- checks by the operator for subscription (05 section 3.1)
  capability_fallbacks jsonb NOT NULL DEFAULT '[]',       -- fallback levels used (05 section 3.1)
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  ended_at        timestamptz,
  CHECK ((kind = 'pipeline') = (pipeline IS NOT NULL)),
  CHECK ((kind = 'single_service') = (service IS NOT NULL)),
  CHECK ((state IN ('done','skipped','cancelled','expired','failed')) = (ended_at IS NOT NULL)),
  CHECK ((state IN ('awaiting_input','paused_budget')) = (resume_state IS NOT NULL)),
  CHECK ((trigger_kind = 'event') = (trigger_event_id IS NOT NULL)),
  CHECK ((trigger_kind = 'event') = (trigger IS NULL)),
  CHECK (trigger IS NULL OR trigger->>'kind' = trigger_kind),
  CHECK (trigger_kind NOT IN ('eval','eval_judge') OR effect_sink = 'record')
);
CREATE INDEX runs_active_by_object ON guildwork.runs (tenant_id, object_key)
  WHERE state NOT IN ('done','skipped','cancelled','expired','failed');
CREATE INDEX runs_active_by_pr ON guildwork.runs (tenant_id, pr_object_key)
  WHERE pr_object_key IS NOT NULL AND state NOT IN ('done','skipped','cancelled','expired','failed');
CREATE INDEX runs_deadline ON guildwork.runs (deadline_at) WHERE deadline_at IS NOT NULL AND ended_at IS NULL;
CREATE INDEX runs_by_state ON guildwork.runs (tenant_id, state, updated_at);
CREATE INDEX runs_by_automaton ON guildwork.runs (automaton_version) WHERE ended_at IS NULL;

CREATE TABLE guildwork.run_transitions (            -- history, part of the Run Record
  run_id          uuid NOT NULL REFERENCES guildwork.runs(id),
  seq             integer NOT NULL CHECK (seq > 0),
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  event_type      text NOT NULL,
  event_key       text NOT NULL,                          -- idempotency key of the event
  from_state      text NOT NULL,
  to_state        text NOT NULL,                          -- equal to from_state for discarded events
  outcome         text NOT NULL CHECK (outcome IN ('applied','rejected_not_in_table','rejected_guard','duplicate_ignored')),
  actor_identity_id uuid REFERENCES guildwork.identities(id),
  details         jsonb NOT NULL DEFAULT '{}',
  automaton_version integer NOT NULL,
  at              timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (run_id, seq),
  UNIQUE (run_id, event_key)
);

-- Object lock (ADR-68, FE-115): at most one active run per object and service.
CREATE TABLE guildwork.run_object_locks (
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  object_key      text NOT NULL,
  service         text NOT NULL,
  run_id          uuid NOT NULL REFERENCES guildwork.runs(id),
  acquired_at     timestamptz NOT NULL DEFAULT now(),
  released_at     timestamptz,
  release_reason  text,
  PRIMARY KEY (run_id, object_key, service)
);
CREATE UNIQUE INDEX run_object_locks_active ON guildwork.run_object_locks (tenant_id, object_key, service)
  WHERE released_at IS NULL;

-- Merged follow-up request per object and service (03 section 2.5)
CREATE TABLE guildwork.run_followups (
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  object_key      text NOT NULL,
  service         text NOT NULL,
  event_id        uuid NOT NULL,                          -- last event, replaces earlier ones
  replaced_count  integer NOT NULL DEFAULT 0,
  blocking_run_id uuid NOT NULL REFERENCES guildwork.runs(id),
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, object_key, service)
);

-- Steering instructions (@agent say, 03 section 2.4): are never discarded but kept until they are handed
-- to the running session or the next work item of the run. Delivery values according to 10 section 4.6 (FE-1021).
CREATE TABLE guildwork.run_steer_messages (
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  run_id          uuid NOT NULL REFERENCES guildwork.runs(id),
  actor_identity_id uuid NOT NULL REFERENCES guildwork.identities(id),
  text_ref        text NOT NULL,                          -- BlobStore, redacted; instruction of this actor only
  text_sha256     bytea NOT NULL CHECK (length(text_sha256) = 32),
  source_event_id uuid NOT NULL,
  received_in_state text NOT NULL,                        -- run state on arrival
  delivery        text NOT NULL DEFAULT 'pending' CHECK (delivery IN ('pending','live_steer','next_item','undelivered_handover')),
  delivered_step_id uuid,                                 -- FK below, after CREATE TABLE steps
  created_at      timestamptz NOT NULL DEFAULT now(),
  delivered_at    timestamptz,
  CHECK ((delivery = 'pending') = (delivered_at IS NULL))
);
CREATE INDEX run_steer_pending ON guildwork.run_steer_messages (run_id, created_at) WHERE delivery = 'pending';

CREATE TABLE guildwork.steps (
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  run_id          uuid NOT NULL REFERENCES guildwork.runs(id),
  stage           text NOT NULL,                          -- state of the run or pipeline stage
  service         text NOT NULL,
  name            text NOT NULL CHECK (name ~ '^[a-z0-9_-]+(\.[a-z0-9_-]+)*$'),   -- PlannedStep.name, for example "reviewer.find" (02 section 4.4, FE-140)
  kind            text NOT NULL CHECK (kind IN ('agent','model_call','check','dummy','deterministic','effect')),   -- WorkItemKind plus steps without a worker
  state           text NOT NULL CHECK (state IN ('pending','leased','running','succeeded','failed','cancelled','timed_out')),
  attempt         smallint NOT NULL DEFAULT 1 CHECK (attempt >= 1),   -- attempt of the work item according to item.leased (02 section 4.4)
  max_attempts    smallint NOT NULL CHECK (max_attempts >= 1),
  result_lease_id uuid,                                   -- lease whose result counts (idempotency); the running lease is in leases
  result_ref      text,
  result_sha256   bytea,
  error           jsonb,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  started_at      timestamptz,
  finished_at     timestamptz,
  CHECK (attempt <= max_attempts)
);
-- No unique key over (run_id, stage, ...): a stage has parallel steps (reviewer find and verify,
-- ControllerDecision.next with several entries, fan-out from stage 9 on); run_transitions prevents duplicate creation (FE-140).
CREATE INDEX steps_open ON guildwork.steps (run_id) WHERE state IN ('pending','leased','running');
CREATE INDEX steps_by_stage ON guildwork.steps (run_id, stage, name);
ALTER TABLE guildwork.run_steer_messages ADD CONSTRAINT run_steer_step_fk
  FOREIGN KEY (delivered_step_id) REFERENCES guildwork.steps(id);

-- Column needs of the work API and worker: 03 section 3 (types there: WorkItemKind, BlockedReason, RevokeReason).
CREATE TABLE guildwork.work_items (
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  run_id          uuid NOT NULL REFERENCES guildwork.runs(id),
  step_id         uuid NOT NULL REFERENCES guildwork.steps(id),
  service         text NOT NULL,
  kind            text NOT NULL CHECK (kind IN ('agent','model_call','check','dummy')),   -- WorkItemKind (03 section 2.3)
  pool            text NOT NULL,                          -- pool ID from installation.yaml
  state           text NOT NULL CHECK (state IN ('available','leased','completed','failed','revoked')),
  envelope_version smallint NOT NULL CHECK (envelope_version > 0),
  envelope        jsonb NOT NULL,                         -- WorkItemEnvelopeV1 without secrets, at most 2 MiB (secret scan test)
  requirements    jsonb NOT NULL,                         -- WorkItemRequirementsV1 (03 section 2.3)
  repo_class      text CHECK (repo_class IN ('private_own','external_code')),
  priority        integer NOT NULL DEFAULT 100,
  attempts        smallint NOT NULL DEFAULT 0,            -- counter of claims; the envelope carries attempt = attempts
  max_attempts    smallint NOT NULL CHECK (max_attempts >= 1),
  not_before      timestamptz NOT NULL DEFAULT now(),
  deadline_at     timestamptz,                            -- set per lease
  blocked_reason  text CHECK (blocked_reason IN ('no_qualified_pool','upgrade_required','draining','no_safe_ci','kill_switch')),   -- BlockedReason (03 section 2.4.1); kill_switch from 1-E08-T04 on
  blocked_since   timestamptz,
  last_confirmed_stage text,                              -- "last confirmed stage" (03 section 2.2)
  last_error      jsonb,                                  -- last StepErrorV1
  result          jsonb,                                  -- StepResultV1 without artifact contents
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  ended_at        timestamptz,
  UNIQUE (step_id)
);
CREATE INDEX work_items_claimable ON guildwork.work_items (pool, priority, created_at) WHERE state = 'available';
CREATE INDEX work_items_requirements ON guildwork.work_items USING gin (requirements);
CREATE INDEX work_items_by_run ON guildwork.work_items (run_id);

CREATE TABLE guildwork.leases (
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  work_item_id    uuid NOT NULL REFERENCES guildwork.work_items(id),
  worker_id       uuid NOT NULL,                          -- FK in 0007; the pool key lives in workers (FE-412 in 04)
  pool            text NOT NULL,
  worker_version  text NOT NULL,
  verified_caps   jsonb NOT NULL,                         -- WorkerCaps at claim time (Run Record: isolation according to the verified capability)
  attempt         smallint NOT NULL CHECK (attempt >= 1),
  item_token_jti  text NOT NULL,                          -- identifier of the item token, never the token
  state           text NOT NULL DEFAULT 'active' CHECK (state IN ('active','released','expired','revoked')),   -- 03 section 4.2
  granted_at      timestamptz NOT NULL DEFAULT now(),
  expires_at      timestamptz NOT NULL,
  heartbeat_at    timestamptz,
  usage_reported  jsonb NOT NULL DEFAULT '{}',            -- last cumulative usage per model (02 FE-262)
  ended_at        timestamptz,
  end_reason      text CHECK (end_reason IN ('completed','failed','expired','stop','budget_exhausted','deadline','kill_switch','superseded')),   -- RevokeReason from stop on
  CHECK (expires_at > granted_at),
  CHECK ((state = 'active') = (ended_at IS NULL)),
  CHECK ((ended_at IS NULL) = (end_reason IS NULL))
);
CREATE UNIQUE INDEX leases_one_active ON guildwork.leases (work_item_id) WHERE state = 'active';
CREATE UNIQUE INDEX leases_item_token ON guildwork.leases (item_token_jti);
CREATE INDEX leases_expiring ON guildwork.leases (expires_at) WHERE state = 'active';

CREATE TABLE guildwork.status_comments (               -- 03 section 2.3, FE-116
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  object_key      text NOT NULL,
  provider_comment_id text,                               -- NULL until the first effect
  version         bigint NOT NULL DEFAULT 0,              -- compare-and-swap
  rendered_sha256 bytea,
  last_effect_id  uuid,
  updated_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, object_key)
);
```

**Runs without an event (FE-139):** `createRun` from [02](02-control-plane.md) section 4.5 writes `trigger_kind`, `trigger_event_id` or `trigger` and `effect_sink` from `CreateRunRequest`. The intake sets `trigger_kind = 'event'` and `effect_sink = 'live'`; the eval service sets `eval` or `eval_judge` with the trigger object and always `record`; the probe run of the setup wizard sets `admin` with `{ kind: "admin", subject: "admin:<session-subject>", purpose: "probe_run" }` and `live` (its effects are already `shadowed` via the mode `shadow`). The Effect Gateway reads `effect_sink` per run ([04](04-effects-audit-credentials.md)). For runs without an event the Run Record names `trigger` instead of the event.

**Extensions by later stages** to `runs` and `steps` (DDL in the leading document, rule from section 3.1a; check rules with a fixed name according to FE-138):

| Column or check rule | Form | Migration, task | Leading |
|---|---|---|---|
| `runs.injection_suspected` | `boolean NOT NULL DEFAULT false`, never reset (POL-080) | 0908, 9-E06-T01 (14 FE-1454) | [14](14-stage-9-breadth-and-hardening.md) section 3.1 |
| `runs.human_commits_seen` | `boolean NOT NULL DEFAULT false` (POL-081) | 0905, 9-E06-T02 | 14 section 3.1 |
| `runs.integration_conflict` | `boolean NOT NULL DEFAULT false` (guard in the run state machine) | 0905, 9-E06-T03 | 14 section 3.1 |
| `steps.parent_step_id` | `uuid REFERENCES steps(id)` | 0905, 9-E06-T03 | 14 section 3.1 |
| `steps.fanout_kind` | `text CHECK (fanout_kind IN ('child','best_of_n'))` | 0905, 9-E06-T03 | 14 section 3.1 |
| `steps.fanout_index` | `smallint CHECK (fanout_index >= 0)` | 0905, 9-E06-T03 | 14 section 3.1 |
| `runs.campaign_id` | `uuid REFERENCES campaigns(id)`, index `runs_by_campaign` | 1001, 10-E05-T01 | [15](15-stage-10-edge-layers.md) section 3.1 |
| `runs_state_check` | additional value `campaign_running` (24 states) | 1001, 10-E05-T01 | 15 section 3.1 |
| `runs_object_kind_check` | additional values `campaign_child`, `repo_branch`; 1001 and 1002 write the same complete list | 1001 (10-E05-T01), 1002 (10-E02-T02) | 15 section 3.1 |

`work_items.pool_alt` (block 0800) is carried by [13](13-stage-8-providers-and-bases.md) section 3.2.

### 3.5 Effects, approvals, artifacts, findings (migration 0004)

```sql
-- 0004_effekte_befunde.sql
-- phase: expand
CREATE TABLE guildwork.policy_decisions (
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  run_id          uuid REFERENCES guildwork.runs(id),
  step_id         uuid REFERENCES guildwork.steps(id),
  subject         text NOT NULL CHECK (subject IN ('run_start','service_mode','command','effect','work_item','config')),
  decision        text NOT NULL CHECK (decision IN ('allow','deny','require_approval','shadow')),
  rule_id         text NOT NULL CHECK (rule_id ~ '^POL-[0-9]{3}$'),
  inputs_sha256   bytea NOT NULL CHECK (length(inputs_sha256) = 32),   -- hash of the canonical inputs
  details         jsonb NOT NULL,                         -- reasoning, checked facts, never secrets
  policy_version  text NOT NULL,
  at              timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX policy_decisions_by_run ON guildwork.policy_decisions (run_id, at);

CREATE TABLE guildwork.effects (                      -- outbox (04 FE-401); column needs 04 section 3
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  run_id          uuid REFERENCES guildwork.runs(id),      -- NULL only for platform effects without a run (daily anchor, ack before the run)
  step_id         uuid REFERENCES guildwork.steps(id),     -- NULL for platform effects without a step
  work_item_id    uuid REFERENCES guildwork.work_items(id),
  lease_id        uuid REFERENCES guildwork.leases(id),
  origin          text NOT NULL CHECK (origin IN ('mcp','step_result','platform')),   -- platform: effects of the core (04 FE-406)
  service         text NOT NULL,                          -- ServiceId or 'platform'
  type            text NOT NULL,                          -- EffectType (04 section 2.1.1), for example comment, status_comment, ack
  target          jsonb NOT NULL,                         -- EffectTarget
  ordering_key    text NOT NULL,                          -- serialization per target (04 FE-405)
  idempotency_key text NOT NULL,                          -- 04 FE-402
  state           text NOT NULL CHECK (state IN ('pending','applied','failed','rejected_policy','shadowed')),
  shadow_reason   text CHECK (shadow_reason IN ('service_shadow','gateway_record')),   -- 04 FE-403
  hold            text,                                   -- for example 'G4'; not ready to dispatch
  approval_id     uuid,                                   -- FK below, after approvals
  policy_decision_id uuid REFERENCES guildwork.policy_decisions(id),
  checks          jsonb NOT NULL DEFAULT '{}',            -- redaction (rule IDs, count), removed links, visibility checks
  payload_inline  jsonb,                                  -- redacted payload up to effects.payload_inline_max_bytes
  payload_ref     text,                                   -- BlobStore for larger content (04 FE-419)
  payload_sha256  bytea NOT NULL CHECK (length(payload_sha256) = 32),
  attempts        smallint NOT NULL DEFAULT 0,
  next_attempt_at timestamptz,
  dispatch_started_at timestamptz,
  provider_request_id text,
  provider_object_id text,                                -- for example comment ID, PR number
  pushed_sha      text,                                   -- for a push: new head (SHA chain, merge gate condition 11)
  expected_old_sha text,
  fallback_used   text NOT NULL DEFAULT 'none',
  result          jsonb,
  error           jsonb,                                  -- PluginError
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  applied_at      timestamptz,
  UNIQUE (tenant_id, idempotency_key),
  CHECK (payload_inline IS NOT NULL OR payload_ref IS NOT NULL),
  CHECK (run_id IS NOT NULL OR (origin = 'platform' AND type IN ('audit_anchor','ack'))),
  CHECK ((state = 'applied') = (applied_at IS NOT NULL)),
  CHECK ((state = 'shadowed') = (shadow_reason IS NOT NULL))
);
CREATE INDEX effects_dispatchable ON guildwork.effects (state, next_attempt_at) WHERE state = 'pending' AND hold IS NULL;
CREATE INDEX effects_ordering ON guildwork.effects (ordering_key, created_at) WHERE state = 'pending';
CREATE INDEX effects_by_run ON guildwork.effects (run_id, created_at);
CREATE INDEX effects_pushed ON guildwork.effects (tenant_id, (target->>'repo'), pushed_sha) WHERE pushed_sha IS NOT NULL;

CREATE TABLE guildwork.approvals (
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  run_id          uuid NOT NULL REFERENCES guildwork.runs(id),
  gate            text NOT NULL CHECK (gate IN ('G1','G4','G5')),   -- G2/G3 live at the hoster or in the merge gate
  state           text NOT NULL CHECK (state IN ('requested','granted','denied','expired')),
  plan_sha256     bytea,
  design_sha256   bytea,
  bound_sha       text,                                   -- head SHA for G4
  requested_at    timestamptz NOT NULL DEFAULT now(),
  expires_at      timestamptz,
  decided_at      timestamptz,
  decided_by_identity_id uuid REFERENCES guildwork.identities(id),
  decided_by_kind text CHECK (decided_by_kind IN ('human','auto_if')),
  command_event_id uuid,
  CHECK (gate <> 'G1' OR plan_sha256 IS NOT NULL),
  CHECK (gate <> 'G4' OR bound_sha IS NOT NULL),
  CHECK ((state IN ('granted','denied')) = (decided_at IS NOT NULL))
);
CREATE UNIQUE INDEX approvals_one_open ON guildwork.approvals (run_id, gate) WHERE state = 'requested';
ALTER TABLE guildwork.effects ADD CONSTRAINT effects_approval_fk FOREIGN KEY (approval_id) REFERENCES guildwork.approvals(id);

CREATE TABLE guildwork.artifacts (                    -- column needs 03 section 3 and 04 section 3
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  run_id          uuid REFERENCES guildwork.runs(id),     -- NULL only for kind = 'audit_anchor'
  step_id         uuid REFERENCES guildwork.steps(id),
  work_item_id    uuid REFERENCES guildwork.work_items(id),
  lease_id        uuid REFERENCES guildwork.leases(id),
  kind            text NOT NULL CHECK (kind IN ('log','transcript','bundle','artifact','sarif','egress_log',
                    'effect_record','eval_log','audit_anchor')),   -- ArtifactKind (03 section 2.3) plus kinds from 04
  type            text CHECK (type ~ '^[A-Z][A-Za-z]+$'),  -- domain type for kind = 'artifact': TriageArtifact, PlanArtifact,
                                                          -- DesignArtifact, ChangeProposal, ReviewArtifact, QAReport, FixResult, DummyResult,
                                                          -- AskAnswer (12 section 2.3), RulePrPlan (12 section 2.5), ...; the complete list is carried by the writer's document
  schema_version  smallint CHECK (schema_version > 0),
  version         integer NOT NULL DEFAULT 1 CHECK (version > 0),   -- plan v1, v2 ...
  state           text NOT NULL CHECK (state IN ('pending','stored','quarantined','deleted')),   -- 03 section 4.3
  content_ref     text NOT NULL,                          -- BlobStore key
  content_sha256  bytea NOT NULL CHECK (length(content_sha256) = 32),
  content_bytes   bigint NOT NULL CHECK (content_bytes >= 0),
  content_type    text NOT NULL,
  scan            jsonb,                                  -- post-scan: rule IDs and count, never the matched text
  summary         jsonb,                                  -- small, checked key figures for queries
  object_version  text,                                   -- ticket version (reuse of the TriageArtifact)
  retain_until    timestamptz,
  created_at      timestamptz NOT NULL DEFAULT now(),
  stored_at       timestamptz,
  CHECK ((kind = 'artifact') = (type IS NOT NULL)),
  CHECK (kind = 'audit_anchor' OR run_id IS NOT NULL)
);
CREATE UNIQUE INDEX artifacts_typed_version ON guildwork.artifacts (run_id, type, version) WHERE type IS NOT NULL;
CREATE INDEX artifacts_by_object_version ON guildwork.artifacts (tenant_id, type, object_version) WHERE object_version IS NOT NULL;

-- Columns according to 08 section 3.1 (types Finding, FindingState in 08 section 2); extensions of stage 6 in 09 section 3.2.
CREATE TABLE guildwork.findings (                       -- ADR-11: state here, PR marker only an anchor
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  repo_key        text NOT NULL,                          -- <plugin_instance_id>:<repo_provider_id> (FE-111)
  change_number   integer,                                -- NULL for a local review or a design finding without PR
  fingerprint     text NOT NULL,
  fingerprint_v   smallint NOT NULL,
  producer        text NOT NULL CHECK (producer IN ('reviewer','architect','qa')),
  source          text NOT NULL CHECK (source IN ('llm','architect','qa:catch','qa:mutant') OR source LIKE 'analyzer:%'),   -- FindingSource
  producers       text[] NOT NULL DEFAULT '{}',
  state           text NOT NULL CHECK (state IN ('open','addressed','outdated','resolved_by_human','withdrawn','merged_open','superseded')),
  severity        text NOT NULL CHECK (severity IN ('P0','P1','P2','P3')),
  kind            text NOT NULL CHECK (kind IN ('bug','flag','plan_deviation','design','threat')),
  category        text,
  cwe             text[] NOT NULL DEFAULT '{}',
  reachability    text,
  exploitability  text,
  rule_id         text,
  rule_quote      jsonb,                                  -- {path, sha, text}
  path            text,
  side            text CHECK (side IN ('new','old')),
  start_line      integer,
  end_line        integer,
  anchor_line     integer,
  symbol          text,
  title           text NOT NULL,                          -- texts from platform models, redacted (08 FE-840, exception to FE-107)
  trigger_scenario text,
  existing_code   text,
  agent_prompt    text,
  evidence        jsonb NOT NULL DEFAULT '[]',
  suggestion      jsonb,
  confidence      real CHECK (confidence BETWEEN 0 AND 1),
  score           real,
  evidence_level  text NOT NULL CHECK (evidence_level IN ('proven','plausible','unsupported')),
  reproduction    jsonb,
  presentation    text CHECK (presentation IN ('inline','summary','hidden')),
  comment_id      text,
  thread_id       text,
  first_seen_run_id uuid NOT NULL REFERENCES guildwork.runs(id),
  first_seen_sha  text NOT NULL,
  last_seen_run_id uuid NOT NULL REFERENCES guildwork.runs(id),
  last_seen_sha   text NOT NULL,
  addressed_sha   text,
  external_fingerprint text,                              -- SARIF partialFingerprints
  prompt_v        jsonb,
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  CHECK (start_line IS NULL OR end_line >= start_line),
  CHECK (state <> 'addressed' OR addressed_sha IS NOT NULL)
);
CREATE UNIQUE INDEX findings_identity ON guildwork.findings (tenant_id, repo_key, coalesce(change_number, -1), fingerprint);
CREATE INDEX findings_by_state ON guildwork.findings (tenant_id, repo_key, state);
CREATE INDEX findings_noise ON guildwork.findings (tenant_id, repo_key, category, updated_at);

CREATE TABLE guildwork.finding_feedback (               -- append-only, columns according to 08 section 3.1
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  finding_id      uuid NOT NULL REFERENCES guildwork.findings(id),
  kind            text NOT NULL CHECK (kind IN ('thread_resolved_by_human','thread_reopened_by_human','human_reply','addressed',
                    'outdated','withdrawn','merged_open','confirmed','question','marked_fixed_dev')),   -- 08 section 4.12, 09 section 3.2
  actor_identity_id uuid REFERENCES guildwork.identities(id),   -- never the login (section 3.11)
  actor_permission text CHECK (actor_permission IN ('none','read','triage','write','maintain','admin')),   -- freshly read at the provider
  actor_is_author boolean,                                -- author of the PR, ADR-61 (d)
  body_ref        text,                                   -- reply text in the BlobStore, untrusted
  run_id          uuid REFERENCES guildwork.runs(id),     -- run that harvested the signal
  sha             text,
  provider_ref    text NOT NULL,                          -- comment or thread ID
  at              timestamptz NOT NULL,                   -- point in time at the provider
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (finding_id, kind, provider_ref)
);
CREATE INDEX finding_feedback_by_finding ON guildwork.finding_feedback (finding_id, at);
```

### 3.6 Ledger and configuration (migration 0005)

```sql
-- 0005_ledger_konfig.sql
-- phase: expand
CREATE TABLE guildwork.config_snapshots (
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  hash            text NOT NULL CHECK (hash ~ '^[0-9a-f]{64}$'),   -- sha256 over the canonical effective configuration
  schema_version  smallint NOT NULL,
  effective       jsonb NOT NULL,
  sources         jsonb NOT NULL,      -- per layer: {level, ref, path, sha, status: valid|fallback_last_valid|strictest|absent}
  fallback_used   boolean NOT NULL,    -- ADR-65: fallback to the last valid version or the strictest level
  overrides_applied jsonb NOT NULL DEFAULT '[]',          -- applied repo_overrides
  profiles        jsonb NOT NULL,      -- {service: {profile: {...}, qualification_key}}
  warnings        jsonb NOT NULL DEFAULT '[]',            -- ignored relaxations and others (02 FE-231)
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, hash)
);
ALTER TABLE guildwork.runs ADD CONSTRAINT runs_config_snapshot_fk
  FOREIGN KEY (config_snapshot_id) REFERENCES guildwork.config_snapshots(id);

CREATE TABLE guildwork.config_last_valid (            -- ADR-65
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  level           text NOT NULL CHECK (level IN ('org','repo_group','repo')),
  source_key      text NOT NULL,                          -- <repo_key>:<path>
  valid_sha       text,                                   -- commit of the last valid version, NULL if never valid
  valid_content   jsonb,
  valid_schema_version smallint,
  validated_at    timestamptz,
  error_sha       text,                                   -- commit of the currently invalid version
  error           jsonb,                                  -- [{key, line, column, message}]
  error_since     timestamptz,
  updated_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, level, source_key),
  CHECK ((valid_sha IS NULL) = (valid_content IS NULL))
);
CREATE INDEX config_last_valid_errors ON guildwork.config_last_valid (tenant_id) WHERE error IS NOT NULL;

CREATE TABLE guildwork.repo_overrides (               -- 04 section 1 rule 7
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  repo_key        text NOT NULL,
  key_path        text NOT NULL CHECK (key_path ~ '^[a-z_]+(\.[a-z_]+)*$'),   -- for example merge.mode, services.coder.mode
  value           jsonb NOT NULL,
  reason          text NOT NULL,
  set_by          text NOT NULL CHECK (set_by IN ('orchestrator','admin')),
  set_by_identity text,                                   -- admin subject from OIDC or emergency admin
  rule            text,                                   -- for orchestrator: fallback rule, for example target_branch_red, post_merge_red (11 section 3.1)
  ref             text,                                   -- evidence of the rule, for example merge SHA for post_merge_red
  created_at      timestamptz NOT NULL DEFAULT now(),
  lifted_at       timestamptz,
  lifted_by       text,
  CHECK ((lifted_at IS NULL) = (lifted_by IS NULL)),
  CHECK (set_by <> 'orchestrator' OR rule IS NOT NULL)
);
CREATE UNIQUE INDEX repo_overrides_active ON guildwork.repo_overrides (tenant_id, repo_key, key_path) WHERE lifted_at IS NULL;

CREATE TABLE guildwork.buckets (                      -- 04 section 6
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  key_kind        text NOT NULL CONSTRAINT buckets_key_kind_check
                    CHECK (key_kind IN ('org','repo_group','repo','user','service','provider','pool')),   -- name fixed (FE-138)
  key_value       text NOT NULL,
  metric          text NOT NULL CHECK (metric IN ('usd','runs','tokens','concurrency')),
  window_kind     text NOT NULL CHECK (window_kind IN ('hour','day','month','rolling_5h','none')),
  limit_value     numeric(18,6) NOT NULL CHECK (limit_value >= 0),
  used            numeric(18,6) NOT NULL DEFAULT 0 CHECK (used >= 0),      -- in the current fixed window
  reserved        numeric(18,6) NOT NULL DEFAULT 0 CHECK (reserved >= 0),
  window_start    timestamptz,                            -- NULL for rolling_5h and none
  warned_at       timestamptz,                            -- warn_at_percent triggered in the current window
  source_snapshot_hash text NOT NULL,                     -- configuration state that set the limit
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, key_kind, key_value, metric, window_kind),
  CHECK ((window_kind IN ('hour','day','month')) = (window_start IS NOT NULL)),
  CHECK (metric <> 'concurrency' OR window_kind = 'none')
);

CREATE TABLE guildwork.reservations (
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  run_id          uuid NOT NULL REFERENCES guildwork.runs(id),
  step_id         uuid REFERENCES guildwork.steps(id),
  state           text NOT NULL CHECK (state IN ('held','settled','released','rejected','expired')),
  amounts         jsonb NOT NULL,                         -- {usd?, tokens, runs, concurrency, turns, wall_min}
  rejected_bucket_id uuid REFERENCES guildwork.buckets(id),
  rejected_metric text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  expires_at      timestamptz NOT NULL,                   -- safety net in case a run never settles
  closed_at       timestamptz,
  CHECK ((state = 'held') = (closed_at IS NULL)),
  CHECK (state <> 'rejected' OR rejected_bucket_id IS NOT NULL)
);
CREATE UNIQUE INDEX reservations_one_held_per_step ON guildwork.reservations (run_id, coalesce(step_id, '00000000-0000-0000-0000-000000000000'::uuid))
  WHERE state = 'held';
CREATE INDEX reservations_expiring ON guildwork.reservations (expires_at) WHERE state = 'held';

CREATE TABLE guildwork.reservation_lines (
  reservation_id  uuid NOT NULL REFERENCES guildwork.reservations(id),
  bucket_id       uuid NOT NULL REFERENCES guildwork.buckets(id),
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  amount          numeric(18,6) NOT NULL CHECK (amount >= 0),
  consumed        numeric(18,6) NOT NULL DEFAULT 0 CHECK (consumed >= 0),
  PRIMARY KEY (reservation_id, bucket_id)
);

CREATE TABLE guildwork.usage (
  id              uuid NOT NULL,
  at              timestamptz NOT NULL,                   -- partition key
  tenant_id       uuid NOT NULL,
  run_id          uuid NOT NULL,
  step_id         uuid,
  work_item_id    uuid,
  lease_id        uuid,
  reservation_id  uuid,
  source          text NOT NULL CHECK (source IN ('heartbeat','final','relay','model_call','settlement','correction')),   -- final: completion of the item (03 section 3)
  provider        text NOT NULL,                          -- runtime or model instance from the configuration
  model           text NOT NULL,
  in_tokens       bigint NOT NULL DEFAULT 0 CHECK (in_tokens >= 0),
  out_tokens      bigint NOT NULL DEFAULT 0 CHECK (out_tokens >= 0),
  cache_read_tokens bigint NOT NULL DEFAULT 0 CHECK (cache_read_tokens >= 0),
  cache_write_tokens bigint NOT NULL DEFAULT 0 CHECK (cache_write_tokens >= 0),
  reasoning_tokens bigint NOT NULL DEFAULT 0 CHECK (reasoning_tokens >= 0),
  usd             numeric(14,6),
  cost_source     text NOT NULL CHECK (cost_source IN ('provider','client_estimate','price_table','subscription_utilization','none')),
  bucket_keys     text[] NOT NULL,                        -- key chain at the time of booking (for rolling_5h)
  PRIMARY KEY (at, id)
) PARTITION BY RANGE (at);
CREATE INDEX usage_by_run ON guildwork.usage (run_id, at);
CREATE INDEX usage_by_keys ON guildwork.usage USING gin (bucket_keys);
CREATE INDEX usage_recent ON guildwork.usage (tenant_id, at DESC);
```

**Extensions by later stages:** `buckets_key_kind_check` receives the value `campaign` in migration 1001 (10-E05-T01) for the budget per campaign (`budget_key = "campaign:<id>"`); DDL in [15](15-stage-10-edge-layers.md) section 3.1.

### 3.7 Audit and merge gate (migration 0006)

The eval and qualification tables (`eval_suites`, `eval_cases`, `eval_runs`, `qualification` from [08](../architecture/08-roadmap.md) section 4 and the additions from FE-707) are carried with columns by [07](07-eval-and-qualification.md) section 3; migration 0010 (section 3.1a). "Qualified" is computed from these tables on every query (`decideMode` in 07 section 2.11, FE-708), never stored (FE-118).

```sql
-- 0006_audit_gate.sql
-- phase: expand
CREATE TABLE guildwork.audit (                        -- 05 section 8; chain logic and hash in 04 section 2.2 (FE-408)
  seq             bigint NOT NULL,                        -- gapless across the whole installation (FE-127)
  at              timestamptz NOT NULL,                   -- partition key; set by the writer, goes into the hash
  tenant_id       uuid NOT NULL,
  actor_kind      text NOT NULL CHECK (actor_kind IN ('system','user','worker','service','plugin','admin')),   -- AuditActor.kind (04 section 2.2.1)
  actor_ref       text NOT NULL,                          -- identities.id, OIDC subject, role, worker_id, ServiceId or plugin instance; never login or email
  action          text NOT NULL CHECK (action ~ '^[a-z_]+(\.[a-z_]+)+$'),   -- for example run.transition, effect.applied
  subject         text NOT NULL,                          -- for example run:<id>, effect:<id>, config:<repo_key>
  run_id          uuid,
  details         jsonb,                                  -- redacted, at most audit.details_inline_max_bytes (04 FE-409)
  details_ref     text,                                   -- blob for larger details
  details_sha256  bytea NOT NULL CHECK (length(details_sha256) = 32),   -- hash of the canonical details, goes into the chain
  prev_hash       bytea NOT NULL CHECK (length(prev_hash) = 32),
  hash            bytea NOT NULL CHECK (length(hash) = 32),
  PRIMARY KEY (at, seq)
) PARTITION BY RANGE (at);
CREATE INDEX audit_by_seq ON guildwork.audit (seq);
CREATE INDEX audit_by_subject ON guildwork.audit (tenant_id, subject, at);
CREATE INDEX audit_by_run ON guildwork.audit (run_id, seq) WHERE run_id IS NOT NULL;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON guildwork.audit FROM guildwork_app;   -- writing only via audit_insert
CREATE FUNCTION guildwork.audit_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'audit ist append-only' USING ERRCODE = 'insufficient_privilege'; END $$;
CREATE TRIGGER audit_no_update BEFORE UPDATE OR DELETE ON guildwork.audit
  FOR EACH ROW EXECUTE FUNCTION guildwork.audit_append_only();
CREATE TRIGGER audit_no_truncate BEFORE TRUNCATE ON guildwork.audit
  FOR EACH STATEMENT EXECUTE FUNCTION guildwork.audit_append_only();

-- Appending to the one installation-wide chain (FE-125, FE-127) in two calls within the same transaction:
-- audit_head locks the chain until the end of the transaction and returns the head across all tenants;
-- the AuditWriter (04 section 2.2.1) forms seq = head + 1, at and the hash according to FE-408 with canonicalJson
-- from @guildwork/core; audit_insert checks the lock and the chaining and writes. Both run as owner
-- (the policies allow current_user = 'guildwork_owner'; no SET clause on a placeholder parameter,
-- because from PostgreSQL 15 on that requires GRANT SET ON PARAMETER by a superuser).
CREATE FUNCTION guildwork.audit_head()
  RETURNS TABLE (seq bigint, hash bytea)
  LANGUAGE plpgsql VOLATILE SECURITY DEFINER
  SET search_path = guildwork, pg_temp AS $$
BEGIN
  PERFORM pg_advisory_xact_lock(7462011);                 -- AUDIT_CHAIN_LOCK
  RETURN QUERY SELECT coalesce(max(a.seq), 0),
    coalesce((SELECT a2.hash FROM guildwork.audit a2 ORDER BY a2.seq DESC LIMIT 1), decode(repeat('00', 32), 'hex'))   -- genesis
    FROM guildwork.audit a;
END $$;
CREATE FUNCTION guildwork.audit_insert(
    p_seq bigint, p_at timestamptz, p_tenant_id uuid, p_actor_kind text, p_actor_ref text, p_action text,
    p_subject text, p_run_id uuid, p_details jsonb, p_details_ref text, p_details_sha256 bytea,
    p_prev_hash bytea, p_hash bytea)
  RETURNS void
  LANGUAGE plpgsql VOLATILE SECURITY DEFINER
  SET search_path = guildwork, pg_temp AS $$
DECLARE v_seq bigint; v_hash bytea;
BEGIN
  PERFORM pg_advisory_xact_lock(7462011);                 -- repeated in the same transaction: obtained immediately
  SELECT h.seq, h.hash INTO v_seq, v_hash FROM guildwork.audit_head() h;
  IF p_seq <> v_seq + 1 OR p_prev_hash <> v_hash THEN
    RAISE EXCEPTION 'audit: Kopf veraltet (erwartet seq %)', v_seq + 1 USING ERRCODE = 'serialization_failure';
  END IF;
  INSERT INTO guildwork.audit (seq, at, tenant_id, actor_kind, actor_ref, action, subject, run_id, details, details_ref,
                               details_sha256, prev_hash, hash)
    VALUES (p_seq, p_at, p_tenant_id, p_actor_kind, p_actor_ref, p_action, p_subject, p_run_id, p_details, p_details_ref,
            p_details_sha256, p_prev_hash, p_hash);
END $$;
REVOKE ALL ON FUNCTION guildwork.audit_head() FROM PUBLIC;
REVOKE ALL ON FUNCTION guildwork.audit_insert(bigint,timestamptz,uuid,text,text,text,text,uuid,jsonb,text,bytea,bytea,bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION guildwork.audit_head() TO guildwork_app;
GRANT EXECUTE ON FUNCTION guildwork.audit_insert(bigint,timestamptz,uuid,text,text,text,text,uuid,jsonb,text,bytea,bytea,bytea) TO guildwork_app;

CREATE TABLE guildwork.audit_anchors (                -- daily anchor (ADR-29), installation-wide, without RLS tenant; job audit-anchor (04 section 2.2.3)
  day             date PRIMARY KEY,
  last_seq        bigint NOT NULL,
  hash            bytea NOT NULL CHECK (length(hash) = 32),
  sink            text NOT NULL CHECK (sink IN ('blob','scm')),
  sink_ref        text NOT NULL,                          -- blob key or repo and commit SHA
  written_at      timestamptz NOT NULL DEFAULT now(),
  verified_at     timestamptz
);

-- Columns according to 11 section 3.1 (merge gate, written from stage 5 on); append-only except for superseded_by.
CREATE TABLE guildwork.merge_gate_decisions (
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  run_id          uuid NOT NULL REFERENCES guildwork.runs(id),
  run_version     bigint NOT NULL,                        -- runs.version at the time of the decision
  repo_key        text NOT NULL,
  change_number   integer NOT NULL,
  head_sha        text NOT NULL,
  mode            text NOT NULL CHECK (mode IN ('shadow','auto')),
  phase           text NOT NULL CHECK (phase IN ('initial','window_end','pre_merge','recheck_409')),
  decision        text NOT NULL CHECK (decision IN ('merge','wait_veto','human')),
  conditions      jsonb NOT NULL,                         -- ConditionResult[] (11 section 2)
  failed          text[] NOT NULL DEFAULT '{}',
  window_ends_at  timestamptz,
  combination_key text NOT NULL,
  gate_version    text NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  superseded_by   uuid REFERENCES guildwork.merge_gate_decisions(id),
  CHECK ((decision = 'merge') = (cardinality(failed) = 0))
);
CREATE INDEX merge_gate_by_run ON guildwork.merge_gate_decisions (run_id, created_at);
CREATE FUNCTION guildwork.merge_gate_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' OR (to_jsonb(NEW) - 'superseded_by') <> (to_jsonb(OLD) - 'superseded_by') THEN
    RAISE EXCEPTION 'merge_gate_decisions ist append-only' USING ERRCODE = 'insufficient_privilege';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER merge_gate_no_change BEFORE UPDATE OR DELETE ON guildwork.merge_gate_decisions
  FOR EACH ROW EXECUTE FUNCTION guildwork.merge_gate_append_only();
```

### 3.8 Operations and tables of further stage 0 areas (migration 0007)

These tables are not in the list from [08](../architecture/08-roadmap.md) section 4, but are required by functions of stage 0 (FE-119). The logic belongs to the named Epic; the schema belongs here so that there is only one source.

| Table | Required by | Epic |
|---|---|---|
| `pools`, `workers` | work API, `guildwork worker register` ([11](../architecture/11-installation-and-hosting.md) section 2.2); pool key according to 04 FE-412 | 0-E11, 0-E10 |
| `backup_runs` | backup gate of the migrator, manifest ([11](../architecture/11-installation-and-hosting.md) sections 6 and 7); flow and kinds in [06](06-installation-operations-ui.md) section 2.11, alarm in [00](00-codebase-and-conventions.md) section 2.9 | 0-E18 (writing), 0-E02 (reading) |
| `blob_refs` | deletion job for retention periods ([06](../architecture/06-operations-and-deployment.md) section 5) | 0-E02 |
| `issued_jwts` | one-time JWT for the WIF exchange (`jti`), [01](../architecture/01-plugin-interfaces.md) section 6 | 0-E10 |

Emergency admin (`break_glass_accounts`, 06) and required alerts (`alerts`, 00) are in the table directory (section 3.1a) with their own migrations.

```sql
-- 0007_betrieb.sql
-- phase: expand
CREATE TABLE guildwork.pools (
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),   -- installation tenant
  pool_key        text NOT NULL,                          -- id from installation.yaml
  plugin          text NOT NULL,
  max_concurrency integer NOT NULL CHECK (max_concurrency > 0),
  isolation_allowed text[] NOT NULL,
  single_operator boolean NOT NULL DEFAULT false,
  enabled         boolean NOT NULL,
  updated_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, pool_key)
);

CREATE TABLE guildwork.workers (                     -- one row per pool key (04 FE-412: gwpk_<keyId>.<secret>)
  id              uuid PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  pool_id         uuid NOT NULL REFERENCES guildwork.pools(id),
  key_id          text NOT NULL UNIQUE,                   -- keyId from the key, 10 characters base32
  key_sha256      bytea NOT NULL CHECK (length(key_sha256) = 32),   -- SHA-256(secret), comparison in constant time
  label           text NOT NULL,
  created_by      text NOT NULL,                          -- admin subject
  single_operator text,                                   -- operator ID for single_operator
  worker_version  text,
  verified_caps   jsonb,
  last_seen_at    timestamptz,
  registered_at   timestamptz NOT NULL DEFAULT now(),
  revoked_at      timestamptz,
  UNIQUE (key_sha256)
);
ALTER TABLE guildwork.leases ADD CONSTRAINT leases_worker_fk FOREIGN KEY (worker_id) REFERENCES guildwork.workers(id);

CREATE TABLE guildwork.backup_runs (                  -- installation-wide, without RLS tenant; column needs 06 section 3.1 and 00 section 3.4
  id              uuid PRIMARY KEY,
  kind            text NOT NULL CHECK (kind IN ('scheduled','manual','pre_upgrade','restore_test')),   -- BackupRunKind (06 section 2.11)
  state           text NOT NULL CHECK (state IN ('running','succeeded','failed')),                     -- BackupRunStatus
  started_at      timestamptz NOT NULL DEFAULT now(),
  finished_at     timestamptz,
  target          text NOT NULL,                          -- restic target without credentials
  snapshot_id     text,
  manifest_ref    text,                                   -- BackupManifest: row counts, last audit hash
  schema_version  integer NOT NULL,
  product_version text NOT NULL,
  error           text,                                   -- for example 'abandoned'
  CHECK ((state = 'running') = (finished_at IS NULL))
);
CREATE INDEX backup_runs_recent ON guildwork.backup_runs (kind, state, finished_at DESC);

CREATE TABLE guildwork.blob_refs (                    -- directory of all BlobStore objects for the deletion job
  key             text PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  class           text NOT NULL CHECK (class IN ('raw','quarantine','transcript','log','diff','bundle','artifact',
                    'sarif','screenshot','evidence','export','audit_detail','eval')),
  run_id          uuid,
  sha256          bytea NOT NULL CHECK (length(sha256) = 32),
  bytes           bigint NOT NULL CHECK (bytes >= 0),
  retain_until    timestamptz,                            -- NULL = permanent
  locked_until    timestamptz,                            -- OBJECT_LOCK at the driver
  evidence_hold   boolean NOT NULL DEFAULT false,         -- evidence for a merged PR (06 section 5)
  created_at      timestamptz NOT NULL DEFAULT now(),
  deleted_at      timestamptz,
  delete_attempts smallint NOT NULL DEFAULT 0
);
CREATE INDEX blob_refs_due ON guildwork.blob_refs (retain_until) WHERE deleted_at IS NULL AND retain_until IS NOT NULL;
CREATE INDEX blob_refs_by_run ON guildwork.blob_refs (run_id) WHERE run_id IS NOT NULL;

CREATE TABLE guildwork.issued_jwts (
  jti             text PRIMARY KEY,
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  lease_id        uuid REFERENCES guildwork.leases(id),
  audience        text NOT NULL,
  expires_at      timestamptz NOT NULL,
  issued_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX issued_jwts_expiry ON guildwork.issued_jwts (expires_at);
```

### 3.9 Row-level security (migration 0008)

Every table with `tenant_id` gets the same policy. The migration generates the statements from a list; the test `rls.every_tenant_table_has_policy` reads `information_schema.columns` and `pg_policies` and fails if a table with `tenant_id` has no policy or no `FORCE`.

```sql
-- 0008_rls.sql
-- phase: expand
DO $$
DECLARE t text;
BEGIN
  FOR t IN SELECT c.table_name FROM information_schema.columns c
           JOIN information_schema.tables x USING (table_schema, table_name)
           WHERE c.table_schema = 'guildwork' AND c.column_name = 'tenant_id' AND x.table_type = 'BASE TABLE'
             AND NOT EXISTS (SELECT 1 FROM pg_class p JOIN pg_namespace n ON n.oid = p.relnamespace
                             WHERE n.nspname = 'guildwork' AND p.relname = c.table_name AND p.relispartition)
  LOOP
    EXECUTE format('ALTER TABLE guildwork.%I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE guildwork.%I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format($p$CREATE POLICY tenant_isolation ON guildwork.%I
                      USING (tenant_id = guildwork.current_tenant() OR guildwork.installation_scope()
                             OR current_user = 'guildwork_owner')
                      WITH CHECK (tenant_id = guildwork.current_tenant() OR guildwork.installation_scope()
                             OR current_user = 'guildwork_owner')$p$, t);
  END LOOP;
END $$;
ALTER TABLE guildwork.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE guildwork.tenants FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_self ON guildwork.tenants
  USING (id = guildwork.current_tenant() OR guildwork.installation_scope() OR current_user = 'guildwork_owner')
  WITH CHECK (guildwork.installation_scope());
-- Installation-wide tables without tenant_id: only owner and installation scope
REVOKE ALL ON guildwork.schema_migrations, guildwork.schema_state FROM guildwork_app;
GRANT SELECT ON guildwork.schema_migrations, guildwork.schema_state TO guildwork_app;   -- startup check
-- audit_anchors and backup_runs: reading and inserting for guildwork_app, no UPDATE except verified_at or state
```

**Privileges of installation-wide tables** (without `tenant_id`, hence without policy; access only from roles of the control plane, never with a tenant reference). The file that creates the table sets the privileges in the same file; the default privileges from 0001 (DML for `guildwork_app`) are revoked first for this:

| Table | `guildwork_app` | `guildwork_ops` (via `grant_ops_role`, FE-141) | Migration |
|---|---|---|---|
| `schema_migrations`, `schema_state` | `SELECT` | reading via `pg_read_all_data` | 0008 |
| `audit_anchors` | `SELECT`, `INSERT`, `UPDATE (verified_at)` | reading | 0008 |
| `backup_runs` | `SELECT`, `INSERT`, `UPDATE (state, finished_at, error, snapshot_id, manifest_ref)` | `SELECT`, `INSERT`, `UPDATE` | 0008 |
| `job_outbox` | `SELECT`, `INSERT`, `DELETE` (the forwarder reads with `FOR UPDATE SKIP LOCKED` and deletes, no `UPDATE`; [02](02-control-plane.md) section 4.9.1) | none | 0017 |
| `alerts`, `alert_deliveries`, `alerting_heartbeat`, `price_entries` | according to the leading document (section 3.1a) | according to the leading document | 0011, block 0800 |

`job_outbox` carries no `tenant_id`, but the payload carries the `tenantId` of the job; the forwarder needs no installation scope because the table has no policy. The test `rls.installation_tables_grants` reads `information_schema.role_table_grants` and compares with this table (for `job_outbox` only if 0017 exists).

Partitioned tables (`events`, `usage`, `audit`) get the policy on the parent table; accesses always go through the parent table (FE-109). Because the default privileges (`ALTER DEFAULT PRIVILEGES`) also apply to new partitions, `ensure_partitions` revokes all privileges of `guildwork_app` from every newly created partition; a test queries a partition directly with `guildwork_app` and expects "permission denied". Every later migration that creates a table with `tenant_id` creates the policy in the same file; the test `rls.every_tenant_table_has_policy` runs after every migration.

### 3.10 Partitioning and maintenance functions (migration 0009)

| Table | Key | Range | Lead | Reason |
|---|---|---|---|---|
| `events` | `received_at` | month | 3 months | grows with every webhook; delete skipped events after the deadline |
| `usage` | `at` | month | 3 months | grows with every heartbeat; queries for rolling windows only on the most recent partitions |
| `audit` | `at` | month | 3 months | retention by detaching whole months, no `DELETE` on the chain |

Maintenance functions run as `SECURITY DEFINER` with owner `guildwork_owner`, because `guildwork_app` has no DDL privileges (FE-112):

```sql
-- 0009_wartung.sql
-- phase: expand
CREATE FUNCTION guildwork.ensure_partitions(p_table text, p_months_ahead int)
  RETURNS int LANGUAGE plpgsql SECURITY DEFINER SET search_path = guildwork, pg_temp AS $$
DECLARE m date; n int := 0; part text;
BEGIN
  IF p_table NOT IN ('events','usage','audit') THEN RAISE EXCEPTION 'unbekannte Tabelle %', p_table; END IF;
  IF p_months_ahead < 1 OR p_months_ahead > 12 THEN RAISE EXCEPTION 'months_ahead außerhalb 1..12'; END IF;
  FOR i IN -1..p_months_ahead LOOP
    m := date_trunc('month', now())::date + make_interval(months => i);
    part := format('%s_%s', p_table, to_char(m, 'YYYYMM'));
    IF to_regclass('guildwork.' || part) IS NULL THEN
      EXECUTE format('CREATE TABLE guildwork.%I PARTITION OF guildwork.%I FOR VALUES FROM (%L) TO (%L)',
                     part, p_table, m, m + interval '1 month');
      EXECUTE format('REVOKE ALL ON guildwork.%I FROM guildwork_app', part);   -- access only via the parent table
      n := n + 1;
    END IF;
  END LOOP;
  RETURN n;
END $$;

-- Detach and drop audit partitions only if older than the deadline (at least 365 days)
-- and a daily anchor exists for every day of the month (otherwise the chain could no longer be verified).
CREATE FUNCTION guildwork.drop_expired_audit_partitions(p_keep_days int)
  RETURNS text[] LANGUAGE plpgsql SECURITY DEFINER SET search_path = guildwork, pg_temp AS $$
DECLARE r record; dropped text[] := '{}'; month_start date; month_end date;
BEGIN
  IF p_keep_days < 365 THEN RAISE EXCEPTION 'Audit-Aufbewahrung unter 365 Tagen ist nicht erlaubt'; END IF;
  FOR r IN SELECT c.relname FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid
           WHERE i.inhparent = 'guildwork.audit'::regclass LOOP
    month_start := to_date(right(r.relname, 6), 'YYYYMM');
    month_end := (month_start + interval '1 month')::date;
    CONTINUE WHEN month_end > (now() - make_interval(days => p_keep_days))::date;
    IF (SELECT count(*) FROM guildwork.audit_anchors WHERE day >= month_start AND day < month_end)
       < (month_end - month_start) THEN
      RAISE WARNING 'Partition % ohne vollständige Tagesanker bleibt erhalten', r.relname;
      CONTINUE;
    END IF;
    EXECUTE format('ALTER TABLE guildwork.audit DETACH PARTITION guildwork.%I', r.relname);
    EXECUTE format('DROP TABLE guildwork.%I', r.relname);
    dropped := dropped || r.relname::text;
  END LOOP;
  RETURN dropped;
END $$;
-- Analogous: drop_expired_partitions(p_table text, p_keep_days int) RETURNS text[] without the anchor condition; allows only
-- p_table = 'usage' (otherwise exception), p_keep_days >= 30; events is cleaned up row by row (section 3.11).
REVOKE ALL ON FUNCTION guildwork.ensure_partitions(text,int), guildwork.drop_expired_audit_partitions(int),
  guildwork.drop_expired_partitions(text,int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION guildwork.ensure_partitions(text,int), guildwork.drop_expired_audit_partitions(int),
  guildwork.drop_expired_partitions(text,int) TO guildwork_app;
```

On its first run the migration creates the partitions from the previous month up to three months ahead; afterwards the job `db-partition-maintenance` (daily) keeps the lead. An insert without a matching partition fails (no `DEFAULT` partition, FE-109); for this there is the required alert `partition_missing`, which the alert state machine computes from `dbAlertSignals` when the lead falls below 2 months (FE-134).

### 3.11 Retention and deletion

Starting values from [06](../architecture/06-operations-and-deployment.md) section 5; the operator makes the decision via the keys in section 7. The deletion job `db-retention` (hourly, in batches of `retention.batch_size`) enforces them, not the bucket lifecycle.

| Data | Table or class | Starting value | Mechanism |
|---|---|---|---|
| Runs, steps, work items, leases, effects, approvals, artifact rows, ledger, snapshots, merge gate, eval and qualification | tables from 3.4 to 3.7 and from [07](07-eval-and-qualification.md) section 3 | permanent (PITR) | no deletion except tenant deletion |
| Findings and feedback | `findings`, `finding_feedback` | "like repo": until the repo is removed from the installation | repo removal deletes after `retention.repo_removed_grace_days` |
| Raw payloads | `blob_refs.class = 'raw'`, `inbox` | 30 days | delete the blob, delete the `inbox` row, `events.raw_ref` stays as a dead reference with `blob_refs.deleted_at` |
| Quarantine (invalid signature) | `blob_refs.class = 'quarantine'` | 7 days | like raw payloads |
| Transcripts, diffs, test logs, screenshots | classes `transcript`, `diff`, `log`, `screenshot` | 90 days | `evidence_hold = true` for runs with a merged PR extends to `retention.evidence_merged_days` |
| Skipped events | `events` with `state = 'skipped'` | 90 days | row by row from old partitions |
| Events with a run | `events` with `run_id` | permanent | part of the Run Record |
| Dedupe entries | `event_dedupe` | `ingress.dedupe_window_h` | row by row according to `expires_at` |
| Usage rows | `usage` | 400 days | detach the monthly partition; totals per run remain in `runs.cost_usd` and `reservations` |
| Audit | `audit` | 365 days, never less | detach the monthly partition only with complete daily anchors (section 3.10) |
| One-time JWT | `issued_jwts` | until `expires_at` plus 1 day | row by row |
| Open linking flows (from stage 8 on) | `identity_link_flows` | until `expires_at` plus 1 day | row by row, verifier overwritten beforehand (section 2.2, 8-E01-T07) |

**Flow per blob:** select `blob_refs` with `retain_until < now()` and without `evidence_hold`, `BlobStore.delete(key)`; on success set `deleted_at`; on error `not_found` (the object does not exist, for example because `putTracked` writes the row before the object and `put` failed, 02 FE-215) likewise set `deleted_at`, count it in `deletedBlobs` and `missingBlobs` and write the `info` log `retention.blob_missing` with key and class, without increasing `delete_attempts` (FE-137); on error `permission` (Object Lock before `retainUntil`) set `retain_until = locked_until` and retry later; on any other error `delete_attempts + 1`, from `retention.max_delete_attempts` on the required alert `retention_stuck`. Each batch writes an audit entry `retention.batch` with a count per class, never with contents.

**Deletion of a tenant** (org leaves the installation): the admin sets `tenants.deletion_requested_at` (audit). After `retention.tenant_grace_days` the job deletes all rows with this `tenant_id` in the order of the foreign keys (children first) and all blobs of the tenant, sets `tenants.deleted_at` and leaves only the audit entries in place until their partition goes away after the audit deadline. Audit entries contain no logins and no contents (FE-117), so after the deletion only the evidence that a deletion happened remains.

**Deletion of a person** (request for information or deletion): `identities.login = NULL`, `erased_at = now()`. Because events, audit and findings only carry `identities.id` and logins only appear in `events.actor` (JSON), the job additionally redacts `events.actor->>'login'` of all events of this identity. Raw payloads with the login expire after their deadline; an early deletion is the command `guildwork data erase-identity` (0-E18), which deletes the raw payloads of the affected events.

### 3.12 Tables of later stages

The directory of all tables of later stages with block and leading document is in section 3.1a (FE-128). Plans are `artifacts` with `type = 'PlanArtifact'` and `version`; the version data is carried by `plan_versions` (10).

**User preferences (FE-142).** The configuration layer `user` ([04](../architecture/04-configuration-and-limits.md) section 1 rule 6: only language, notification and narrower own limits) is read by the config resolver ([02](02-control-plane.md) section 4.6, `ResolveRequest.userIdentityId`) from this table. The key is the identity of the initiator at the SCM or ticket system, not a login. Until a task creates the table (section 10), the layer is `absent`.

```sql
-- NNNN_user_preferences.sql (number in the block of the building stage, section 3.1a)
-- phase: expand
CREATE TABLE guildwork.user_preferences (
  tenant_id       uuid NOT NULL REFERENCES guildwork.tenants(id),
  identity_id     uuid NOT NULL REFERENCES guildwork.identities(id),
  language        text CHECK (language ~ '^[a-z]{2}(-[A-Z]{2})?$'),   -- BCP 47 short form, for example de, en-US; NULL: layer above
  notifications   jsonb NOT NULL DEFAULT '{}',            -- only keys under notifications.* of the schema (04 section 7)
  limits          jsonb NOT NULL DEFAULT '{}',            -- only keys under limits.*; the resolver applies them only to tighten
  set_by          text NOT NULL,                          -- "self:<identity_id>" or "admin:<sha256 des Subjekts>"
  updated_at      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, identity_id)
);
-- Policy tenant_isolation as in section 3.9 in the same file
```

Invalid contents (unknown key, relaxation of a limit) are discarded by the resolver like an invalid file according to ADR-65, only for this layer, and noted as `warnings` in the snapshot; the row stays unchanged. On `eraseIdentity` (section 2.2) the row of the identity is deleted.

## 4. Flows

### 4.1 Migration

```mermaid
sequenceDiagram
  autonumber
  participant CLI as guildwork upgrade / role migrate
  participant M as Migrator
  participant PG as Postgres
  CLI->>M: apply(release, backupMaxAgeS, lockWaitMs)
  M->>PG: SHOW server_version_num; SELECT extversion FROM pg_extension WHERE extname='vector'
  alt too old
    M-->>CLI: postgres_too_old or pgvector_too_old (Exit 1)
  end
  M->>PG: pg_try_advisory_lock(7462001) in a loop until lockWaitMs
  alt lock not obtained
    M-->>CLI: lock_timeout (Exit 1), no change
  end
  M->>PG: SELECT * FROM schema_migrations
  M->>M: compare checksums of applied files, detect unknown versions
  alt mismatch
    M-->>CLI: checksum_mismatch or unknown_applied_version (Exit 1)
  end
  M->>M: determine pending files, check halt points against schema_state.last_release
  alt halt point skipped
    M-->>CLI: halt_point_skipped (Exit 1)
  end
  M->>PG: SELECT max(finished_at) FROM backup_runs WHERE state='succeeded' AND kind IN ('scheduled','manual','pre_upgrade')
  alt schema not empty, pending migrations, no backup younger than backupMaxAgeS
    M-->>CLI: no_recent_backup (Exit 1)
  end
  loop per pending file
    M->>PG: BEGIN (if transactional); SET LOCAL guildwork.scope='installation'; SQL; INSERT schema_migrations; UPDATE schema_state; COMMIT
    alt error
      M->>PG: ROLLBACK
      M-->>CLI: migration_failed with version and error (Exit 1), earlier files stay applied
    end
  end
  M->>PG: ensure_partitions for events, usage, audit (from 0009 on)
  M->>PG: installQueueSchema (from 0-E02-T13 on, 02 FE-276), then SELECT guildwork.grant_ops_role()
  M->>PG: UPDATE schema_state SET last_release = release (even without a pending file)
  M->>PG: pg_advisory_unlock(7462001)
  M-->>CLI: ok, applied[], schemaVersion
```

**File format:** Every file starts with header lines `-- phase: expand|contract|data`, optionally `-- transactional: false`, `-- min_app_release: <semver>`, `-- haltepunkt: true`. The checksum is computed over the content with normalized line endings (LF) and without trailing blank lines. An applied file is never changed; a correction is a new file (11 section 6 rule 2).

**Expand/contract (11 section 6 rule 1):**
- `expand` only adds (tables, nullable columns or columns with a default, indexes, check constraints `NOT VALID` with a later `VALIDATE`), so that the code of N-1 keeps running.
- `contract` removes what N-1 no longer uses; the file must set `min_app_release` to the release from which the code no longer reads what was removed. The linter `tools/migration-lint` (part of `make check`, rules in section 4.4) rejects `DROP`, `RENAME`, `ALTER ... TYPE` and `SET NOT NULL` in `expand` files and requires `min_app_release` in `contract` files.
- `data` fills data in batches; long data migrations run as a job after the rollout, not in the migrator (FE-121).
- Indexes on large tables: `CREATE INDEX CONCURRENTLY` in a separate file with `transactional: false`.

**Lock against parallel migration:** session advisory lock with the fixed constant `MIGRATE_LOCK = 7462001` (FE-120). Two simultaneous `migrate` runs: the second waits until `migrate.lock_wait_s` and then ends with `lock_timeout` without any change. Because the lock is tied to the session, a crashed run releases it when the connection ends.

**Individual rules of the migrator** (0-E02-T02 and 0-E02-T03):

| Rule | Definition |
|---|---|
| Empty database | `to_regclass('guildwork.schema_migrations') IS NULL`; then the backup and halt point locks do not apply |
| Roles | before anything else: if `guildwork_owner` or `guildwork_app` are missing in `pg_roles`, the migrator creates them if `rolcreaterole` of the user is true, otherwise `roles_missing` with the SQL from section 6 in `message` |
| `schema_state` | after file 0001 the migrator creates the row (`schema_version = 1`, `min_app_release = '0.0.0'`, `last_release = release`); after every file, in the same transaction, `schema_version = max(version)` and `min_app_release = max(min_app_release)` by semver over all applied files |
| Checksum | comparison per applied version that the release knows as a file; mismatch: `checksum_mismatch` with `version`, audit `schema.migration_refused` |
| Unknown applied version | every applied number without a file in the release results in `unknown_applied_version` with `version`: an older release never migrates a newer schema (the way back is an image switch without `migrate`, 06 section 2.10); starting a role, in contrast, allows such numbers (section 4.2) |
| Halt point (FE-133) | `halt_point_skipped` if an entry `h` from `haltPoints` exists with `last_release < h < release` (semver, only `major.minor.patch`); `message` names `h`. The header line `-- haltepunkt: true` remains a marker in the file and in `schema_migrations.haltepunkt`; what counts for the check is `haltPoints` |
| Backup | query as in the sequence; `kind = 'restore_test'` does not count; without a hit or older than `backupMaxAgeS`: `no_recent_backup`, audit `schema.migration_refused` |
| Privileges after the run (FE-141) | after applying (even without a pending file, never for `dryRun`) the migrator, from 0-E02-T13 on, calls `installQueueSchema` and then `SELECT guildwork.grant_ops_role()`; result in the log `migrate.ops_role_granted` (`true`, or `false` if the role does not exist). An error in it is `migration_failed` without `version` |
| `dryRun` | take the lock, all checks up to just before applying, release the lock; result `ok: true` with `applied: []`; nothing written |
| Audit | `schema.migration_failed` and `schema.migration_refused` go via `DbDeps.audit` in a separate transaction after the rollback, the tenant is the installation tenant; if it does not exist yet (empty database), log only |

### 4.2 Schema check at startup

Every role (`web`, `orchestrator`, `migrate`, CLI commands with DB access) calls `startCheck` before anything else.

| Check | Result | Behavior of the role | Log and metric |
|---|---|---|---|
| Server not reachable | `unreachable` | retry with growing pause until `db.startup_wait_s`, then exit 1 | `guildwork.db.startup_unreachable` |
| `server_version_num < 170000` | `postgres_too_old` | exit 1 with the message "PostgreSQL 17 or newer required" | error log |
| `vector` missing or `< 0.8.2` | `pgvector_too_old` | exit 1 with installed and required version, never `ALTER EXTENSION` | error log |
| Runtime user is superuser, has `BYPASSRLS` (except `DbConfig.role = "ops"`, FE-141) or owns tables in `guildwork` (not for `migrate`) | `unsafe_db_role` | exit 1 with a hint about separate roles | error log |
| a number from `requiredVersions` is missing in `schema_migrations` | `schema_too_old` (with `missing`) | exit 1 with the hint "run guildwork upgrade or role migrate" (11 section 6 rule 6) | error log |
| `release < schema_state.min_app_release` | `app_too_old` | process runs, `/readyz` stays 503 with a reason, worker claims are not served | gauge `guildwork.app.not_ready{reason="app_too_old"}`, required alert |
| otherwise | `ok` | continue | info log with versions |

`requiredVersions` is the list of all migration numbers that the release ships, and is a constant in the build (`packages/db/src/generated/required-versions.ts`, generated from the folder `migrations/` at build time; a test checks equality). Because the numbers lie in blocks per stage (FE-126), startup checks the set, not the highest number. Applied numbers that the release does not know are allowed as long as `min_app_release` does not apply (N-1 code against N schema).

### 4.3 Tenant context

```mermaid
sequenceDiagram
  participant S as Module (for example router)
  participant DB as @guildwork/db
  participant PG as Postgres
  S->>DB: withTenant(db, tenantId, fn)
  DB->>PG: BEGIN; SELECT set_config('guildwork.tenant_id', $1, true)
  DB->>S: fn(tx)
  S->>PG: queries (RLS filters on tenant_id)
  DB->>PG: COMMIT or ROLLBACK
```

`set_config(..., true)` only takes effect until the end of the transaction; the pool returns the connection without a tenant. `withInstallationScope` sets `guildwork.scope = 'installation'` in the same way and first writes an audit entry `db.installation_scope` with caller and reason (only once per job run, not per row).

### 4.4 Migration linter and N-1 against N probe

**Linter** `tools/migration-lint/lint.py` (Python like the other check tools, FE-132), gate `migration-lint` in `quality/gates.toml` with `in_check = true`, CI job `tools`. Invocation `lint.py [--json <file>] <folder>` (default `packages/db/migrations`). Exit codes, finding format and `--json` according to [00](00-codebase-and-conventions.md) section 2.10. The linter removes comments and strings before searching and checks keywords case-insensitively.

| Rule ID | Finding when | Applies to |
|---|---|---|
| `header-missing` | header line `-- phase:` is missing or has a value other than `expand`, `contract`, `data` | every file |
| `number-outside-block` | the number lies in no block from section 3.1a or occurs twice | every file |
| `expand-no-drop` | `DROP` (table, column, index, constraint, function); excepted is `ALTER TABLE t DROP CONSTRAINT [IF EXISTS] c` if the same file afterwards contains `ALTER TABLE t ADD CONSTRAINT c CHECK (...)` with the same name (extension of a value list, FE-138) | `expand` |
| `expand-no-rename` | `RENAME` | `expand` |
| `expand-no-type-change` | `ALTER ... TYPE` | `expand` |
| `expand-no-set-not-null` | `SET NOT NULL` | `expand` |
| `contract-needs-min-app-release` | header line `-- min_app_release:` is missing | `contract` |
| `concurrently-needs-nontransactional` | `CONCURRENTLY` without `-- transactional: false` | every file |
| `no-extension-update` | `ALTER EXTENSION` (11 section 6 rule 7) | every file |

Header lines are the contiguous lines `-- <key>: <value>` directly after the first line (`-- NNNN_name.sql`); allowed keys `phase`, `transactional` (`true`, `false`), `min_app_release` (semver), `haltepunkt` (`true`). An unknown key is the finding `header-missing` with the message "unknown header". A finding line looks like `packages/db/migrations/0104_x.sql:7:1 expand-no-drop DROP in expand migration`. Tests under `tools/migration-lint/tests/` with sample files per rule (positive and negative), invocation `python -m unittest` like the other tools; the linter runs in `make check` via the target `check-tools` and in the CI job `tools`.

That such an extension only adds to the old list (N-1 keeps writing only valid values) is not checked by the linter; that is checked by the migration test of the building task (old values remain insertable) and by the review. `ADD CONSTRAINT ... CHECK` without `NOT VALID` on an existing table is not a finding (it cannot be separated statically from new tables in the same file); that is checked by the review.

**N-1 against N probe** (`packages/db/test/upgrade.test.ts`): fixture `packages/db/test/fixtures/n-minus-1/` with the repository queries at the state of the previous release (copied at the release cut, 0-E21) and the migration list of N-1. The probe applies N-1, runs all fixture queries, applies the `expand` files of N and runs the same queries again: same results, no errors. Before the first release, N-1 is an `expand` file generated in the test on top of the current state.

## 5. Failure and abort paths

| Error | Stored | Audit | Log and metric | What the user sees |
|---|---|---|---|---|
| Migration fails in file N | files before N applied, N rolled back, `schema_state` and `schema_migrations` without N | yes (`schema.migration_failed` with version) | error log with SQLSTATE, exit 1 | `guildwork upgrade` aborts with step and reason; the stack is not swapped |
| Second `migrate` at the same time | nothing | no | `guildwork.migrate.lock_timeout` | exit 1 "another migration is running" |
| Checksum of an applied file changed (`checksum_mismatch`) or applied number without a file (`unknown_applied_version`) | nothing | yes (`schema.migration_refused`) | error log | exit 1 "migration N changed"; release error, not an operator error |
| No fresh backup (`no_recent_backup`) | nothing | yes (`schema.migration_refused`) | error log | exit 1 with the hint `guildwork backup` |
| Halt point skipped (`halt_point_skipped`) | nothing | yes (`schema.migration_refused`) | error log | exit 1 with the release that must be upgraded to first |
| Schema too old at startup | nothing | no | error log | role does not start; `doctor` shows "migration pending" |
| App too old for the schema | nothing | yes (once per start) | alarm `app_too_old` | `/readyz` 503; admin UI shows "version outdated" |
| Partition missing on insert | insert fails, transaction rolled back | no | alarm `partition_missing`, error log with table | the affected operation is retried by pg-boss; ingress answers 503, the provider redelivers |
| RLS without tenant context | 0 rows or `WITH CHECK` error on write | no | error log `tenant_context_missing` with caller | the operation fails visibly instead of touching data of other tenants |
| UPDATE, DELETE or TRUNCATE on `audit` or a change to `merge_gate_decisions` other than `superseded_by` | error `insufficient_privilege`, transaction rolled back | no (the caller's transaction is rolled back; FE-135) | error log `db.append_only_violation` with table and caller, counter `guildwork.db.append_only_violation` | the operation fails; a real manipulation of the chain is reported by the chain check (alarm `audit_chain`, 04) |
| Deletion job: blob under Object Lock | `retain_until` postponed | yes (`retention.batch`) | counter `guildwork.retention.locked` | nothing |
| Deletion job: repeated driver error | `delete_attempts` increased | yes | alarm `retention_stuck` | admin UI notice |
| Audit partition without complete anchors | partition stays | yes | warning, alarm `audit_anchor_gap` | `doctor` reports a gap |
| Deletion job during a backup (`ops_locks('retention')`) | nothing deleted, report with `heldBy` | no | info log `retention.held` | nothing; the next hourly run catches up |
| Deletion job: database error in one step | this step rolled back, the others persist | yes (`retention.batch` with partial numbers) | error log `db.maintenance_failed` with step and SQLSTATE | pg-boss retries; after the last attempt alarm `job_dead_letter` (02) |
| Partition maintenance: lock taken | nothing | no | info log `partition_maintenance.skipped_locked` | nothing |
| Role `migrate` with invalid input (for example `database.migrate_url_ref` equal to `database.url_ref`) | nothing | no | error log `migrate.invalid_input` | exit 2 |

## 6. Security

- **Roles (FE-112):** `guildwork_owner` owns the schema, tables and functions and is used only by `migrate` (its own mandatory connection URL `database.migrate_url_ref`, never equal to `database.url_ref`). `guildwork_app` is `NOBYPASSRLS`, has DML privileges, no DDL privileges, on `audit` only `SELECT` and appending via `audit_head` and `audit_insert`. `startCheck` aborts with `unsafe_db_role` if the runtime user is a superuser, has `BYPASSRLS` (except for the role `ops`, see below) or owns tables in the schema `guildwork`; this way a misconfiguration (for example the superuser of the Postgres container as runtime user) cannot silently override RLS. If the roles are missing, `migrate` creates them if its user has `CREATEROLE`; otherwise it aborts with `roles_missing` and the SQL for creating them in the message. In the Compose bundle, the init script of the Postgres container (`deploy/compose/postgres/init/01-roles.sh`, [06](06-installation-operations-ui.md) section 2.3) creates all three roles on first start, including `guildwork_ops` (0-E18). The SQL that `migrate` executes or names in the message (without a password; the operator sets it with `ALTER ROLE ... PASSWORD` to match the two connection URLs, `migrate` reports this in the log `migrate.roles_created`):

```sql
CREATE ROLE guildwork_owner LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB;
CREATE ROLE guildwork_app   LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
GRANT guildwork_owner TO CURRENT_USER;   -- only if the migration user is not guildwork_owner: so that it can create objects for the role
```

If the migration user is not itself `guildwork_owner`, the migrator executes every file after `SET LOCAL ROLE guildwork_owner`, so that all objects belong to this role (FE-112); `startCheck` with `unsafe_db_role` detects a runtime user that still owns tables.
- **Role `guildwork_ops` (FE-141, [06](06-installation-operations-ui.md) FE-648):** only for the role `ops` (backup, restore test), `LOGIN NOSUPERUSER BYPASSRLS CREATEDB`, member of `pg_read_all_data`; `pg_dump` needs `BYPASSRLS` because all tenant tables have `FORCE ROW LEVEL SECURITY` (unverified, to be proven in 0-E18-T10). It is optional: `migrate` does not create it and does not report its absence as `roles_missing`; outside the Compose bundle the operator creates it if they run the role `ops` (SQL below). It gets write privileges only on `backup_runs`, `ops_locks` and the schema `pgboss` via `guildwork.grant_ops_role()` at the end of each migrator run (section 4.1), so that a role created later receives its privileges at the next `migrate`. `startCheck` allows `BYPASSRLS` only for `DbConfig.role = "ops"`; superuser and schema ownership abort there too. Whether a managed database grants `BYPASSRLS` to a non-superuser is unverified (section 10).

```sql
CREATE ROLE guildwork_ops LOGIN NOSUPERUSER BYPASSRLS CREATEDB NOCREATEROLE;   -- password as above via ALTER ROLE
GRANT pg_read_all_data TO guildwork_ops;
```
- **Cross-tenant access (FE-123):** only via (a) `SECURITY DEFINER` functions with a fixed task that run as `guildwork_owner`; the policies allow `current_user = 'guildwork_owner'`, the scope of the calling transaction stays untouched (`ingress_instance`, `audit_head`, `audit_insert`, maintenance functions; a `SET` clause on `guildwork.scope` is not possible because from PostgreSQL 15 on that requires `GRANT SET ON PARAMETER` by a superuser), or (b) `withInstallationScope` or `inInstallationScope` with a caller from the fixed list. The inbox belongs to the tenant of the plugin instance (for installation-wide instances to the installation tenant); events, runs and everything after them belong to the org tenant that the ingress processing determines (02 FE-212).
- **Row-level security with `FORCE`** on every table with `tenant_id`; fail closed without context. Residual risk: code of the control plane can set `guildwork.scope` itself; RLS protects against programming errors, not against a compromised control plane. That is why `withInstallationScope` is limited to a fixed list of callers (type `InstallationScopeCaller`), and a lint test searches for `guildwork.scope` outside of `tenant.ts`.
- **No secrets in the DB (FE-108):** columns related to secrets end in `_secret_ref` and have a `CHECK (... LIKE 'secret://%')`; tokens only as SHA-256 (`workers.key_sha256`) or as an identifier without the secret (`leases.item_token_jti`). The test `secrets.no_token_in_any_table` fills the DB through a real flow with fixture tokens (including `sk-ant-oat01-...` patterns) and afterwards scans every text and JSON column of all tables in the schema `guildwork` (list from `information_schema.columns`) for the exact fixture values (also Base64 and URL encoded) and for `SECRET_PATTERNS` from `@guildwork/core` (00 section 2.5, starting list of the gitleaks patterns plus `sk-ant-`): 0 hits. Until 0-E08-T05 the scanner is a helper in `packages/db/test/helpers/scan.ts`; from then on `scanForSecrets` from testkit replaces it (0-E08-T05 depends on 0-E02, not the other way round). It covers the done criterion "secret scan finds the token in no table" of stage 0 for the database.
- **Foreign content (FE-107):** untrusted texts only in the BlobStore, in the DB only reference and hash; this way no foreign text ends up in indexes or logs of the database.
- **Audit append-only:** privileges revoked plus triggers; deletion only by dropping partitions after the deadline with an anchor check.
- **Connection:** TLS to the database if it is not in the same internal network (`database.tls: require | verify-full`); in the Compose bundle an internal network without TLS (11 section 2.4 rule 5).

## 7. Configuration

Keys in `installation.yaml` ([04](../architecture/04-configuration-and-limits.md) section 7 "further named values"); starting values are estimates, stage 0 re-measures. `@guildwork/db` reads no configuration (layer rule, 00 section 2.2); the values come via `DbConfig`, `MigrateRoleInput` and `RetentionConfig`. The task that introduces a key enters it with type and default into the TypeBox schema of `InstallationConfig` ([00](00-codebase-and-conventions.md) section 2.8): `database.*`, `db.pool_max`, `db.statement_timeout_ms`, `db.startup_wait_s` 0-E02-T01; `migrate.*` 0-E02-T02 (`lock_wait_s`) and 0-E02-T03 (`recent_backup_max_age`, if not present yet); `retention.*` and `db.partition_months_ahead` 0-E02-T10. Durations like `24h` are read by `parseDuration` from `@guildwork/core`.

| Key | Type | Default | Effect |
|---|---|---|---|
| `database.url_ref` | `secret://` | mandatory | connection for `guildwork_app` |
| `database.migrate_url_ref` | `secret://` | mandatory, not equal to `database.url_ref` | connection for `guildwork_owner` (only role `migrate`) |
| `database.tls` | `disable \| require \| verify-full` | `disable` in the Compose bundle, otherwise `verify-full` | TLS to the DB |
| `db.pool_max` | int | 10 per role | pool size |
| `db.statement_timeout_ms` | int | 30000 | protection against hanging queries |
| `db.startup_wait_s` | int | 120 | waiting time for the DB at startup |
| `migrate.recent_backup_max_age` | duration | `24h` | backup gate (11 section 6 rule 4) |
| `migrate.lock_wait_s` | int | 300 | waiting time for the migration lock |
| `db.partition_months_ahead` | int 1..12 | 3 | lead of the monthly partitions |
| `retention.raw_days` | int | 30 | raw payloads |
| `retention.quarantine_days` | int | 7 | quarantine |
| `retention.transcripts_days` | int | 90 | transcripts, diffs, logs, screenshots |
| `retention.evidence_merged_days` | int | 365 | evidence for merged PRs |
| `retention.skipped_events_days` | int | 90 | skipped events |
| `retention.usage_days` | int | 400 | usage partitions |
| `retention.audit_days` | int, min 365 | 365 | audit (the schema rejects anything below) |
| `retention.repo_removed_grace_days` | int | 30 | findings after a repo is removed |
| `retention.tenant_grace_days` | int | 30 | tenant deletion |
| `retention.batch_size` | int | 500 | batch size of the deletion job |
| `retention.max_delete_attempts` | int | 10 | after that alarm `retention_stuck` |

## 8. Tests

All tests run against a real Postgres 17 and 18 with pgvector in a container (Testcontainers), never against mocks ([README](README.md) section 2). Test files under `packages/db/test/`.

| Test | Checks | Task |
|---|---|---|
| `migrator.applies_all_on_empty_db` | empty DB until all `requiredVersions` are applied, `schema_state` correct | 0-E02-T02 |
| `migrator.applies_lower_pending_version` | applied all files of stage 0 (0001 to 0017) and 0201, pending 0101: 0101 is applied, startup afterwards `ok` (FE-126) | 0-E02-T02 |
| `migrator.is_idempotent` | a second run applies nothing | 0-E02-T02 |
| `migrator.parallel_second_run_times_out` | two runs at the same time, exactly one applies, the other `lock_timeout` without change | 0-E02-T02 |
| `migrator.checksum_mismatch_aborts` | a changed applied file aborts | 0-E02-T02 |
| `migrator.failed_file_rolls_back_only_itself` | error in file 3: 1 and 2 stay, 3 does not, audit entry present | 0-E02-T02 |
| `migrator.requires_recent_backup` | pending migration on a non-empty schema without backup (or only `restore_test`, or older than `backupMaxAgeS`): `no_recent_backup` and audit `schema.migration_refused`; empty DB excepted | 0-E02-T03 |
| `migrator.haltepunkt_skipped_aborts` | `last_release = 0.3.0`, `release = 0.5.0`, `haltPoints = ["0.4.0"]`: `halt_point_skipped` without change; with `last_release = 0.4.0` it runs through | 0-E02-T03 |
| `migrator.never_updates_extension` | no `ALTER EXTENSION` in any file (static test) | 0-E02-T03 |
| `migration_lint.expand_rejects_drop` | linter rejects `DROP`, `RENAME`, `TYPE`, `SET NOT NULL` in `expand` | 0-E02-T12 |
| `migration_lint.contract_requires_min_app_release` | `contract` file without `min_app_release` results in finding `contract-needs-min-app-release` | 0-E02-T12 |
| `migration_lint.concurrently_and_extension` | `CONCURRENTLY` without `transactional: false` and `ALTER EXTENSION` each result in one finding; comments with these words do not | 0-E02-T12 |
| `startcheck.schema_too_old_exits` | startup with a schema that is too old ends with exit 1 | 0-E02-T03 |
| `startcheck.app_too_old_runs_not_ready` | `min_app_release` higher than the release: process runs, `/readyz` 503 | 0-E02-T03 |
| `startcheck.pgvector_min_version` | `vector` 0.8.1 simulated via a fake query of the extension version, abort with message | 0-E02-T03 |
| `schema.types_match_db` | Kysely types in `schema.ts` equal `information_schema` (columns, nullability, types) | 0-E02-T11 |
| `rls.every_tenant_table_has_policy` | every table with `tenant_id` has a policy and `FORCE` | 0-E02-T09 |
| `rls.no_context_no_rows` | without `withTenant` every table returns 0 rows and insert fails | 0-E02-T09 |
| `rls.tenant_a_cannot_see_tenant_b` | per table: a row of B is invisible and unmodifiable under context A | 0-E02-T09 |
| `rls.partition_direct_access_denied` | direct access to `events_YYYYMM` as `guildwork_app` fails | 0-E02-T09 |
| `rls.scope_setting_only_in_tenant_module` | lint: `guildwork.scope` only in `tenant.ts` | 0-E02-T09 |
| `constraints.run_end_state_requires_ended_at` | check constraints of the state columns take effect | 0-E02-T05 |
| `constraints.object_lock_unique_active` | two active locks for object and service: the second fails with `unique_violation` | 0-E02-T05 |
| `constraints.effect_idempotency_unique` | same idempotency key: the second insert fails | 0-E02-T06 |
| `constraints.identity_link_oauth_only` | `confirmed_via` not equal to `oauth` fails | 0-E02-T04 |
| `audit.append_only` | UPDATE, DELETE and TRUNCATE on `audit` fail, also as owner via the triggers; direct INSERT as `guildwork_app` fails | 0-E02-T08 |
| `migrator.runs_as_non_superuser` | all migrations as `guildwork_owner` without superuser privileges | 0-E02-T04 |
| `audit.append_via_function_as_app` | `audit_head` and `audit_insert` as `guildwork_app` under tenant A read the head of an entry of tenant B and chain correctly; afterwards the scope is empty again | 0-E02-T08 |
| `audit.insert_rejects_stale_head` | `audit_insert` with `seq` not equal to head plus 1 or a wrong `prev_hash` fails; `seq` stays gapless after a rollback (FE-127) | 0-E02-T08 |
| `rls.ingress_instance_without_context` | `ingress_instance(id)` returns exactly the row without tenant context, a direct query returns 0 rows | 0-E02-T09 |
| `rls.nested_scope_restores` | `inInstallationScope` inside `withTenant` restores the tenant context afterwards, also on error | 0-E02-T09 |
| `startcheck.unsafe_db_role` | runtime with superuser, with `BYPASSRLS` and as owner: startup aborted | 0-E02-T03 |
| `ingress.redelivery_after_quarantine` | a redelivery with the same delivery ID after quarantine is accepted | 0-E02-T05 |
| `partitions.ensure_creates_ahead` | lead present, a second call creates nothing twice | 0-E02-T10 |
| `partitions.missing_partition_alarm` | lead below 2 months (partitions removed by hand): `dbAlertSignals.partitionLeadMonths` reports the value below 2, so does the gauge `guildwork.db.partition_lead`; the alarm rule itself is tested by 0-E19 (section 2.2) | 0-E02-T10 |
| `retention.deletes_due_blobs_and_rows` | due raw payloads deleted, audit entry with numbers, no contents | 0-E02-T10 |
| `retention.object_lock_defers` | driver reports `permission`: deletion postponed, no error | 0-E02-T10 |
| `retention.audit_partition_needs_anchors` | a partition without complete anchors stays, with anchors it is removed | 0-E02-T10 |
| `retention.audit_min_365` | `drop_expired_audit_partitions(100)` fails | 0-E02-T10 |
| `retention.tenant_purge_keeps_audit` | tenant deletion: all domain rows gone, audit stays | 0-E02-T10 |
| `retention.erase_identity_blanks_login` | `eraseIdentity`: `identities.login` empty, `events.actor.login` redacted, audit `retention.identity_erased` without login | 0-E02-T10 |
| `maintenance.alert_signals` | `dbAlertSignals` reports a lead below 2 months, stuck deletions and audit partitions without anchors | 0-E02-T10 |
| `testing.migrate_for_tests_creates_roles` | `migrateForTests` on an empty server: both roles created, all migrations applied as `guildwork_owner`, a second call changes nothing | 0-E02-T02 |
| `locks.constants_unique` | advisory lock constants from `locks.ts` pairwise different | 0-E02-T08 |
| `tenant.installation_scope_audited_once` | `withInstallationScope` writes exactly one entry `db.installation_scope` via `DbAuditSink` | 0-E02-T09 |
| `secrets.no_token_in_any_table` | scan of all text and JSON columns after a real flow with fixture tokens: 0 hits | 0-E02-T09 |
| `upgrade.n_minus_1_code_on_n_schema` | code of the previous release (fixture) runs against the new schema after an `expand` migration | 0-E02-T12 |
| `connection.connects_pg17_and_pg18` | `connect` with role `web` against Postgres 17 and 18 with pgvector: `SELECT 1` and `application_name` set | 0-E02-T01 |
| `connection.statement_timeout_applies` | `pg_sleep` beyond `statementTimeoutMs` aborts with SQLSTATE `57014` | 0-E02-T01 |
| `migrator.blocks_match_doc` | `migrations/blocks.json` equal to the block table in section 3.1a; a file with a number outside every block: `loadMigrationFiles` returns `invalid` | 0-E02-T02 |
| `migrator.unknown_applied_version_aborts` | applied number without a file in the release: `unknown_applied_version` without change | 0-E02-T02 |
| `migrate_role.exit_codes` | role `migrate`: success 0, `lock_timeout` 1, `ownerUrl` equal to `appUrl` 2, unknown option 2; log events according to section 2.5 | 0-E02-T02 |
| `migrator.dry_run_changes_nothing` | `dryRun`: `schema_migrations` and `schema_state` unchanged, lock free afterwards | 0-E02-T03 |
| `migrator.roles_missing_reports_sql` | user without `CREATEROLE` and without roles: `roles_missing` with the SQL from section 6; with `CREATEROLE` both roles are created | 0-E02-T03 |
| `constraints.tenants_one_installation` | a second tenant `kind = 'installation'` of the same installation fails with `unique_violation` | 0-E02-T04 |
| `constraints.plugin_instance_secret_ref_only` | `webhook_secret_ref` without the prefix `secret://` fails with `check_violation` | 0-E02-T04 |
| `constraints.one_active_lease_per_item` | a second lease with `state = 'active'` for the same work item fails (`leases_one_active`) | 0-E02-T05 |
| `constraints.inbox_delivery_unique` | the same delivery ID twice not quarantined fails; quarantined and verified side by side allowed (FE-124) | 0-E02-T05 |
| `constraints.steer_messages_kept` | `run_steer_messages` with `delivery = 'pending'` requires `delivered_at IS NULL`; delivery sets both together, otherwise `check_violation` | 0-E02-T05 |
| `constraints.run_states_match_automaton` | values in the CHECK of `runs.state` equal the fixed list of the 23 states from 03 section 2.1 in the test (FE-136) | 0-E02-T05 |
| `constraints.effect_shadowed_needs_reason` | `state = 'shadowed'` if and only if with `shadow_reason` | 0-E02-T06 |
| `constraints.approval_one_open_per_gate` | a second approval with `state = 'requested'` for run and gate fails (`approvals_one_open`) | 0-E02-T06 |
| `constraints.finding_identity_unique` | a second finding with the same tenant, `repo_key`, change and fingerprint fails (`findings_identity`) | 0-E02-T06 |
| `constraints.bucket_window_consistency` | `window_kind` `hour`, `day`, `month` only with `window_start`; `metric = 'concurrency'` only with `window_kind = 'none'` | 0-E02-T07 |
| `constraints.repo_override_one_active` | a second active override for tenant, repo and key fails (`repo_overrides_active`) | 0-E02-T07 |
| `constraints.snapshot_dedupe_by_hash` | a second `config_snapshots` entry with the same tenant and hash fails | 0-E02-T07 |
| `constraints.reservation_rejected_needs_bucket` | `reservations.state = 'rejected'` without `rejected_bucket_id` fails | 0-E02-T07 |
| `constraints.merge_gate_decision_consistent` | UPDATE allowed only of `superseded_by`, every other column and DELETE fail; `decision = 'merge'` only with an empty `failed` | 0-E02-T08 |
| `db.append_only_violation_logged` | UPDATE on `audit` via `connect`: error, log `db.append_only_violation` with `table = audit`, counter increased by 1 (FE-135) | 0-E02-T08 |
| `rls.insert_without_context_fails` | insert into a tenant table without `withTenant`: error `new row violates row-level security policy` (SQLSTATE `42501`) | 0-E02-T09 |
| `retention.held_by_backup_lock` | `retentionHold` returns a holder: nothing deleted, report with `heldBy`, log `retention.held` | 0-E02-T10 |
| `retention.step_failure_keeps_others` | error in the rows step (simulated via a missing grant in the test): blobs of the run stay deleted, result `err` with partial report, audit `retention.batch` with partial numbers | 0-E02-T10 |
| `startcheck.ops_role_allows_bypassrls` | user with `BYPASSRLS`: with `DbConfig.role = "ops"` result `ok`, with `web` `unsafe_db_role`; superuser also with `ops` `unsafe_db_role` (FE-141) | 0-E02-T03 |
| `constraints.run_trigger_consistency` | `trigger_kind = 'event'` without `trigger_event_id` fails; `eval` without `trigger` or with `effect_sink = 'live'` fails; `trigger->>'kind'` not equal to `trigger_kind` fails (FE-139) | 0-E02-T05 |
| `constraints.steps_parallel_in_stage` | two steps with the same run, the same stage and the same name are created; `kind = 'dummy'` is allowed (FE-140) | 0-E02-T05 |
| `constraints.work_item_blocked_kill_switch` | `blocked_reason = 'kill_switch'` is allowed, an unknown reason fails with `check_violation` | 0-E02-T05 |
| `constraints.value_check_names` | `pg_constraint` contains `runs_state_check`, `runs_object_kind_check`, `buckets_key_kind_check` with exactly these names (FE-138) | 0-E02-T07 |
| `rls.installation_tables_grants` | privileges of the installation-wide tables equal to the table in section 3.9 (`information_schema.role_table_grants`) | 0-E02-T09 |
| `rls.ops_role_grants` | `grant_ops_role()` without role `guildwork_ops`: `false`, no change; with the role: privileges on `backup_runs` and schema `pgboss` set, `INSERT` into `runs` as `guildwork_ops` fails with `permission denied` (FE-141) | 0-E02-T09 |
| `retention.missing_blob_counts_as_deleted` | `BlobStore.delete` returns `not_found`: `deleted_at` set, `missingBlobs = 1`, `delete_attempts` unchanged, log `retention.blob_missing` (FE-137) | 0-E02-T10 |
| `migration_lint.expand_allows_check_widening` | `DROP CONSTRAINT c` followed by `ADD CONSTRAINT c CHECK` in `expand`: no finding; `DROP CONSTRAINT c` without `ADD` of the same name: finding `expand-no-drop` (FE-138) | 0-E02-T12 |
| `partitions.skip_when_locked` | a second simultaneous run of `runPartitionMaintenance` creates nothing and reports `created: 0` | 0-E02-T10 |

## 9. Rulings

| No. | Decision | Reason | Rejected alternative |
|---|---|---|---|
| FE-100 | Minimum version **PostgreSQL 17** (tested 17 and 18), pgvector from 0.8.2. [11](../architecture/11-installation-and-hosting.md) section 3 fixes 17 and 18, the architecture takes precedence; the [README](README.md) section 2 has also named 17 since the consistency run 2026-11-01 | architecture rank; Azure and RDS have the common minimum version there | PostgreSQL 16 as the lower bound (contradicts 11, not in the test matrix) |
| FE-101 | Own schema `guildwork`, pg-boss in the schema `pgboss` | clear privilege boundary, fixed `search_path`, pg-boss upgrades do not touch our tables | everything in `public` |
| FE-102 | Tenant separation via **column `tenant_id` plus row-level security with `FORCE`** in a shared database; context via `set_config(..., true)` in every transaction; installation-wide jobs via `withInstallationScope` with a fixed caller list and audit. The tenant is the org; installation objects belong to the one tenant `kind = 'installation'` | 05 section 7 requires RLS and `tenant_id`; one database per installation is the normal case | own database or own schema per tenant (migration n times, pool per tenant); separate DB role with `BYPASSRLS` for jobs (second kind of connection, more operations) |
| FE-103 | IDs are UUIDv7, generated in `@guildwork/core`, without DB default | sortable by time (indexes), independent of the PostgreSQL version; without a default a missing ID is noticed in the test | `gen_random_uuid()` (v4, not sortable); `bigserial` (reveals quantities, hard across tenants) |
| FE-104 | States and kinds as `text` with `CHECK` instead of an `ENUM` type | expand/contract: new value = new constraint (`NOT VALID`, then `VALIDATE`); `ENUM` values cannot be removed | PostgreSQL `ENUM` |
| FE-105 | Deadlines as absolute points in time (`deadline_at`, `expires_at`) | the sweeper only needs an index; no computation at runtime | relative durations in JSON |
| FE-106 | USD as `numeric(14,6)`, `NULL` = unknown | subscription and some providers deliver no USD (04 section 6); 0 would be wrong | `double precision`; 0 as a substitute |
| FE-107 | Foreign contents and large objects only in the BlobStore, the DB holds reference and hash. Exception: redacted finding texts of the platform models in `findings` ([08](08-reviewer.md) FE-840) | 01 section 2 (`rawRef`), 06 section 5; less attack surface in DB logs | texts as `text` columns |
| FE-108 | No secrets in the DB; tokens only as SHA-256 | 05 sections 5 and 6, done criterion secret scan of stage 0 | encrypted columns (key management in the DB layer) |
| FE-109 | Monthly partitions only for `events`, `usage`, `audit`; no `DEFAULT` partition; lead via job | the three tables grow with every webhook, heartbeat and transition; audit retention without `DELETE` on the chain; without a default, a missing lead shows up as an alarm instead of as a full default partition | `pg_partman` (extension not on every managed database, unverified); partitioning of all large tables |
| FE-110 | No foreign keys into partitioned tables (`runs.trigger_event_id`, `usage.run_id`, `audit.run_id`); integrity through application and tests | an FK to partitioned tables requires the partition key in the target; that would carry `received_at` into every referencing table | carry `received_at` along |
| FE-111 | `object_key` from plugin instance, provider ID of the repo or project and number; repos are identified in all tables of all stages via `repo_key` = `<plugin_instance_id>:<repo_provider_id>`, without a separate repo table (consistency run 2026-11-01) | stable on renaming, unique across SCM instances, basis of the object lock | repo name in the key |
| FE-112 | Two DB roles of the control plane: `guildwork_owner` (only `migrate`) and `guildwork_app` (`NOBYPASSRLS`), plus the optional role `guildwork_ops` only for backups (FE-141); maintenance DDL only via `SECURITY DEFINER` functions with fixed parameters | the runtime cannot change the schema; partition maintenance nevertheless without an owner connection in operation | one role for everything |
| FE-113 | Migrations as numbered SQL files with header lines (`phase`, `transactional`, `min_app_release`, `haltepunkt`), own migrator, checksum sha256 | [README](README.md) section 2 (own migrator); header lines carry the rules from 11 section 6 in machine-readable form | migrations in TypeScript (harder to check, no linter for SQL possible) |
| FE-114 | Kysely types by hand in `schema.ts`, a test reconciles them with `information_schema` | no unverified generator tool in the supply chain; the test catches deviations | `kysely-codegen` (license and maintenance unverified) |
| FE-115 | Object lock in its own table `run_object_locks` with the unique partial index `(tenant_id, object_key, service) WHERE released_at IS NULL`, not as a partial index on `runs` | ADR-68 requires "unique partial index over (object, service)"; a pipeline run holds the lock for **every** service of its stages, which is not possible with one row in `runs` | partial index on `runs(object_key, service)` (does not cover pipelines); advisory locks (not durable across restarts) |
| FE-116 | Status comment: the DB is the source (`status_comments` with `version` for compare-and-swap), the comment at the provider is re-rendered from all active runs of the object | 03 section 2.3 requires CAS on the comment version; the provider API has no CAS semantics (DERIVED) | read the marker in the comment as the source and write it back |
| FE-117 | Audit entries carry only IDs and actions (`actor_ref`), never logins, emails or contents; large items via `details_ref` | tenant and person deletion without breaking the hash chain | logins in the audit (the chain would have to be broken for deletions) |
| FE-118 | "qualified" is computed on every query from `qualification` and `qualification_parts` (`decideMode`, [07](07-eval-and-qualification.md) FE-708), no stored flag and no separate view (consistency run 2026-11-01: the former view `qualification_live_ok` is dropped because 07 computes validity with release, rule hash and reference version) | a stored value only holds as long as the rule that wrote it holds | column `qualified boolean`; view over gate fields only (does not know the validity rules from 07) |
| FE-119 | Additional tables of stage 0 outside the list from 08 with DDL here: `event_dedupe`, `run_transitions`, `run_object_locks`, `run_followups`, `run_steer_messages`, `status_comments`, `policy_decisions`, `reservation_lines`, `config_last_valid`, `repo_overrides`, `audit_anchors`, `pools`, `workers`, `backup_runs`, `blob_refs`, `issued_jwts`; tables of individual areas by reference in section 3.1a | each is required by a function of stage 0 (04 rules 4 and 7, 03 sections 2.3 and 2.5, 11 sections 2.2 and 7, 06 section 5) | scatter tables without a directory across the detailed designs of the users |
| FE-120 | Fixed advisory lock constants in `@guildwork/db`: `MIGRATE_LOCK = 7462001`, `AUDIT_CHAIN_LOCK = 7462011`, `PARTITION_LOCK = 7462021` | one list prevents collisions; tests check uniqueness | `hashtext('...')` at runtime (collisions not excluded) |
| FE-121 | Long data migrations run as a job after the rollout, not in the migrator | `migrate` must be fast and repeatable before the rollout; data backfill needs batches and progress | backfill in the migrator |
| FE-122 | Raw ledger counters separated by `in`, `out`, `cache_read`, `cache_write`, `reasoning` in `usage` | allows any later weighting without data loss (backlog M128); 04 section 6 names "usage per model incl. cache tokens" | one total "tokens" |
| FE-123 | Cross-tenant access only via `SECURITY DEFINER` functions of the owner (policies allow `current_user = 'guildwork_owner'`, no `SET` clause on placeholder parameters) or via `withInstallationScope`/`inInstallationScope` with a fixed caller list; ingress determines instance and tenant via `ingress_instance(id)` | ingress, ingress processing, audit chain, pool buckets and claim need access across tenants; without a fixed path every place would build its own exceptions | `BYPASSRLS` role for jobs (second kind of connection); RLS without `FORCE` (owner accesses unnoticed) |
| FE-124 | Unique delivery ID only over non-quarantined inbox rows; `raw_ref` empty only for quarantine above the size limit | a redelivery after correcting the secret must not get lost as a duplicate | separate quarantine table (second path for the same data) |
| FE-125 | Audit chain installation-wide; appending only via `audit_head` and `audit_insert` (FE-127); `guildwork_app` has no `INSERT` on `audit`; hash and canonical format are defined by [04](04-effects-audit-credentials.md) FE-408 | 05 section 8 names one chain with a daily anchor; under RLS the app cannot read the last hash of other tenants | chain per tenant (anchor per tenant, more sink writes) |
| FE-126 | Migration numbers in fixed blocks per stage (section 3.1a); gaps allowed; the migrator applies pending files in ascending order, even below the highest applied number; startup checks the set `requiredVersions` (consistency run 2026-11-01) | stages are designed in detail and built in parallel; fixed blocks prevent collisions without central assignment ([10](10-planner-architect-coder.md) FE-1049 already uses this) | consecutive numbers across all stages (collisions in parallel work); timestamp as the number (order not readable) |
| FE-127 | `audit.seq` gapless: `audit_head` takes the chain lock and returns the head, the writer forms `seq`, `at` and hash, `audit_insert` checks head and lock (consistency run 2026-11-01; replaces sequence and hash in the database function) | 04 FE-408 computes the hash over `seq` and `at` with `canonicalJson` from `@guildwork/core`; that only works if the writer knows both before the insert; a rollback leaves no gap | sequence with gaps (contradicts FE-408); hash in plpgsql (second implementation of RFC 8785) |
| FE-128 | One table directory in 01 names every table of the platform exactly once with migration and the document that carries its columns; DDL is here only for the core tables of stage 0 (consistency run 2026-11-01) | one home per table, no duplicate column lists; area documents stay complete for their tasks | all DDL in 01 (01 grows with every stage, area documents go stale); no central list (name and number collisions) |
| FE-129 | `@guildwork/db` writes audit entries via its own port `DbAuditSink` (`append(tx, entry)`), which `connect` receives with `DbDeps`; the `AuditWriter` from [04](04-effects-audit-credentials.md) section 2.2.1 satisfies it structurally | the layer rule from 00 section 2.2 allows `db` no dependency on the control plane; 0-E02-T09 requires the audit before 0-E08 | move `AuditWriter` to `db` (chain logic belongs to 04); audit at the caller (forgotten entries) |
| FE-130 | Test callback `migrateForTests` and `roleUrls` in the subpath `@guildwork/db/testing`; it creates both roles and migrates as `guildwork_owner` | 00 section 2.7 requires a callback from `db` without the dependency `testkit -> db`; the subpath keeps test passwords out of the production import | create roles in testkit (testkit would have to know the role rules from FE-112) |
| FE-131 | Metrics of this area are named according to the catalog `guildwork.<area>.<name>` (section 2.4); the former names `db_startup_unreachable`, `app_not_ready`, `migrate_lock_timeout`, `retention_locked` are dropped | one naming scheme for all metrics (00 section 3.3) | own names per document |
| FE-132 | Migration linter in Python under `tools/migration-lint/`, rule IDs and flow in section 4.4; it also covers `ALTER EXTENSION` (static part of `migrator.never_updates_extension` and `migrate.no-extension-update` from 06) | same tool chain and finding format as the check tools from 00 section 2.10 (`ruff`, `mypy`, `unittest`) | linter in TypeScript in the package `db` (second format for check tools); SQL parser as a dependency (license and maintenance unverified) |
| FE-133 | Halt point check of the migrator via `MigrateOptions.haltPoints` (from `release.json` `upgrade.haltPoints`, 06 section 2.10) against the new column `schema_state.last_release`: abort if a halt point lies between the installed and the new release. Error codes `no_recent_backup` and `halt_point_skipped` as in 06; both locks only in `packages/db/src/migrator/gates.ts`, `apps/control-plane/src/migrate/guards.ts` (06, 0-E18-T12) supplies the inputs and maps the codes to messages | halt points are properties of releases, not of files; with number blocks per stage (FE-126) the order of the files says nothing about releases; one place per rule | check solely via the header line `haltepunkt` (a release without a new migration would be invisible); two implementations of the locks in `db` and `control-plane` |
| FE-134 | The alarm rules `partition_missing`, `retention_stuck`, `audit_anchor_gap` and `app_too_old` are written by the alert state machine (Epic 0-E19) over `dbAlertSignals` or `schema_state`; `@guildwork/db` only supplies signals and metrics | 0-E19-T04 depends on 0-E02; a rule in 0-E02 would create a cycle in the plan. Deviation from the rule in 00 section 2.9 ("the task that builds the trigger adds the rule") for this reason | rules in 0-E02-T10 (cycle via 0-E19-T04 and 0-E05-T05) |
| FE-135 | A violation of the append-only triggers (`audit`, `merge_gate_decisions`) produces an error log `db.append_only_violation` and the counter `guildwork.db.append_only_violation` from a Kysely plugin in `connection.ts`; no audit entry and no separate required alert, the former alarm `audit_tamper_attempt` is dropped | the caller's transaction is rolled back, an audit entry in it would be lost; manipulations of the chain are detected by the chain check with the alarm `audit_chain` (04); no writer of the platform changes these tables, a violation is a programming error | audit in a separate transaction (second write path into the audit bypassing the AuditWriter logic); alarm via log evaluation (the alert state machine only reads the database) |
| FE-136 | `constraints.run_states_match_automaton` checks in 0-E02-T05 against a fixed list of the 23 states from 03 section 2.1 in the test; the reconciliation with `run-automaton.v1.json` is done by the orchestrator from 0-E05-T01 on with its automaton test | the automaton file only comes into existence in 0-E05-T01, which depends on 0-E02 | the test reads the automaton file (does not exist yet in 0-E02-T05) |
| FE-137 | The deletion job treats `not_found` when deleting an object as deleted (set `deleted_at`, count `missingBlobs`, info log), without increasing `delete_attempts` | `putTracked` writes the row `blob_refs` before the object (02 FE-215); if `put` fails, there is a row without an object that would otherwise be retried until `retention_stuck` | count `not_found` as an error (false alarm `retention_stuck`); leave the row without an object in place (grows without bound) |
| FE-138 | Single-column check rules are named according to the PostgreSQL default `<table>_<column>_check`; the lists extended by later stages (`runs_state_check`, `runs_object_kind_check`, `buckets_key_kind_check`) appear with this name explicitly in the DDL. An extension is allowed in `expand` as `DROP CONSTRAINT c` plus `ADD CONSTRAINT c CHECK` with the whole new list in the same file; the linter exempts exactly this form from `expand-no-drop` | 15 section 3.1 extends the lists and needs fixed names; an additional value changes nothing for N-1 code; without the exception every extension would be a linter finding or a contract migration with `min_app_release` | leave names to the chance of the default (unverified in 15); separate check table instead of `CHECK` (FE-104); extension only as `contract` (unnecessary minimum release) |
| FE-139 | `runs` carries `trigger_kind` (`event`, `eval`, `eval_judge`, `admin`), `trigger_event_id` only for `event`, otherwise the trigger object in `trigger`, and `effect_sink` (`live`, `record`; eval always `record`) | 02 FE-241 starts runs without an event via `createRun`; the Run Record must carry trigger and sink, and the column was `NOT NULL` | synthetic event per eval run (foreign data in `events`, rejected in 02 FE-241); sink only per installation (`effects.mode`, no eval alongside live operation) |
| FE-140 | `steps` has the column `name` (step name of the service) and no unique key over stage and attempt; `kind` knows `dummy`; the running lease is in `leases`, the valid result in `result_lease_id` | parallel steps of the same stage (reviewer `find` and `verify`, `ControllerDecision.next`, fan-out of stage 9); duplicate creation is already prevented by `run_transitions` (unique `event_key`); a second lease column on the step would duplicate the state from `leases` | `UNIQUE (run_id, stage, name, attempt)` (fan-out has equal names); column `lease_id` on the step (second source for the active lease) |
| FE-141 | A third DB role `guildwork_ops` (06 FE-648) is optional; privileges are granted by `guildwork.grant_ops_role()` at the end of each migrator run; `startCheck` allows `BYPASSRLS` only for `DbConfig.role = "ops"`. The schema `pgboss` is created empty by 0001 with default privileges for `guildwork_app`, the tables are created by `installQueueSchema` as owner (02 FE-276) | without the exception `startCheck` would abort the role `ops`; GRANTs in a migration file fail if the role is missing, and would never be caught up for a role created later; default privileges give the app role DML without DDL on the queue tables | mandatory role for every installation (managed databases without `BYPASSRLS` would remain without migration); privileges by hand according to the docs; DDL privilege of the app role on `pgboss` |
| FE-142 | User preferences in a table `user_preferences` per tenant and identity (language, notifications, narrower limits), DDL in section 3.12; created by the first task that requires the layer `user` | architecture 04 section 1 names the layer; 02 treats it as `absent` until there is a table; keying by identity keeps it stable on login change and deletion (FE-117) | preferences in a repo or org file (the user has no write access there); key by login |

## 10. Open items

| Item | Resolved by | Task |
|---|---|---|
| Encryption of raw payloads with the driver `fs` (06 section 5 "encrypted"): the driver has no capability for it; proposal: encryption at volume level as an operator prerequisite, `doctor` does not check | 0-E03 (driver), otherwise an owner note in the docs | 0-E02-T10 notes it, decision in 0-E03 |
| Whether all databases of the test matrix allow `CREATE EXTENSION vector` for the migration user (Azure requires enabling it in `azure.extensions`) | portability test | 0-E02-T03 |
| Whether `FORCE ROW LEVEL SECURITY` on managed databases with the admin user as owner has unexpected effects (unverified) | test matrix | 0-E02-T09 |
| Size of the partitions and index costs of `usage` with many heartbeats (measurement) | load test stage 0 | 0-E02-T10 |
| Repo group files and where they are stored (02 FE-232) determine `config_last_valid.level = 'repo_group'` | 02 | 0-E06-T03 |
| Source of the repo removal for the deadline "like repo" (06 section 5 of the architecture): today no component records that a repo leaves the installation; until then findings stay until the tenant is deleted (section 2.2) | 05 (GitHub plugin, `installation_repositories.removed`) and the Epic that manages the repo selection | 0-E02-T10 builds the interim rule and notes the state in the PR |
| How the release build fills `release.json` `upgrade.haltPoints` (FE-133 requires the list) | 06 section 2.10 and release tools | 0-E21-T01 |
| No task of the plan creates `user_preferences` or offers users a way to set preferences (FE-142); until then the layer `user` is always `absent` | work plan (task for the user layer, for example with the developer login of stage 6) | open |
| Whether managed databases (Azure, RDS) allow granting a non-superuser `BYPASSRLS` and `pg_read_all_data` (role `guildwork_ops`, FE-141; unverified) | test matrix of the databases | 0-E18-T10 or stage 0b |
| Which `object_kind` runs without an event carry (eval runs with `objectKey` `eval:...`, 07 section 2.17.2; probe run): the list in `runs_object_kind_check` only knows `ticket` and `pr`; an extension must write the whole list from 15 section 3.1 as well (FE-138) | 07 or 02 fix the value, 01 extends the list | before 0-E20-T08 |
