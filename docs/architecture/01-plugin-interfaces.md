<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# 01 Plugin interfaces

All signatures in TypeScript (language of the control plane, rationale in [06](06-operations-and-deployment.md) and ADR-03). Keys and classifications as in the [README](README.md).

This file describes three classes of extensions with the same framework (manifest, capabilities, contract suite): **plugins** (nine kinds, sections 1 to 12) connect third-party systems, **drivers** (three kinds, section 13) connect the base an installation runs on, and **third-party services** (section 14) extend the domain logic. This is how every operator attaches their base and their own services (owner requirement 4, 2026-10-31).

## 1. Common framework for all plugin kinds

### 1.1 Versioning, manifest, load condition

```ts
// Versioning in the Kubernetes style. The core supports the current and the previous major version per plugin kind.
// API group fixed with O17 (2026-10-31): Pages domain of the project's GitHub organization; changeable only with deprecation per rule 6.
type ApiVersion = "guildwork-dev.github.io/v1alpha1" | "guildwork-dev.github.io/v1";
type PluginKind = "TriggerSource" | "WorkItemProvider" | "SCMProvider" | "AgentRuntime"
                | "ModelProvider" | "ExecutionBackend" | "KnowledgeStore" | "Notifier" | "Analyzer";

interface PluginManifest {
  apiVersion: ApiVersion;
  kind: PluginKind[];                  // a package may implement several kinds (github = Trigger + WorkItem + SCM)
  id: string;                          // "github", "jira-cloud", "claude-code", "ci-dispatch-github"
  version: string;                     // semver of the plugin
  license: string;                     // SPDX expression of the plugin code, required
  distribution: "bundled" | "operator_supplied";  // bundled only with a license from the allowlist (rule 7)
  trust: "first_party" | "vetted" | "third_party";      // third_party only across a process boundary or WASM
  transport: "in_process" | "subprocess_grpc" | "subprocess_jsonrpc" | "http" | "wasm";
  configSchema: JSONSchema;            // validates the instance configuration, unknown keys = error
  secrets: SecretDecl[];               // names and kind, never values
  egress: string[];                    // hosts the plugin may reach
  contractSuite: { version: string; passedAt: string; fixturesHash: string };  // load condition
}

interface PluginContext {
  instanceId: string; tenant: TenantRef;
  log: Logger; metrics: Metrics; tracer: Tracer;
  http: EgressHttp;                    // only hosts from manifest.egress
  secrets: { resolve(ref: SecretRef): Promise<SecretValue> };   // via the Credential Broker, with audit
  clock: Clock;
}

interface PluginBase<C extends string> {
  manifest(): PluginManifest;
  init(ctx: PluginContext, config: unknown): Promise<Result<void>>;
  capabilities(scope?: ScopeRef): Promise<CapabilitySet<C>>;  // per instance or per repo (GitLab tier)
  health(): Promise<HealthReport>;     // expiry of tokens and webhooks, self-disabling at the provider
}

type CapabilitySet<C extends string> = Record<C, { level: "native" | "fallback" | "none"; note?: string }>;

type Result<T> = { ok: true; value: T } | { ok: false; error: PluginError };
interface PluginError {
  code: "auth" | "permission" | "not_found" | "rate_limited" | "conflict" | "unsupported" | "transient" | "invalid";
  retryAfterMs?: number; providerRequestId?: string; message: string;
}

interface HealthReport { ok: boolean; expiresAt?: string; disabledByProvider?: boolean; weakAuth?: boolean; notes: string[] }

// Foreign content is marked as a type; the prompt builder embeds untrusted blocks only marked.
interface Untrusted<T = string> { readonly untrusted: true; value: T; origin: string; sha256: string; sanitized: boolean }
```

**Rules:**
1. **Load condition:** A plugin without a passed contract test suite in the matching version is not loaded. The suite runs against recorded real API responses (fixtures with a hash in the manifest); where the project has no account with the vendor (O28: only the Claude subscription), against fixtures built from the vendor's public documentation, with a source reference per fixture. Recordings from optional owner runs replace them later.
2. **Capability instead of name:** The core never queries the provider name, only capabilities. If a capability is `none`, the core switches the feature off and reports this visibly instead of crashing. Every `fallback` level is recorded in the audit and in the run summary.
3. **Error model:** Every method with external effect or network access returns `Result<T>`. `rate_limited` and `transient` are retried with increasing backoff; `auth`, `permission`, `invalid` never.
4. **Trust:** `third_party` plugins run only as a subprocess (gRPC following the go-plugin pattern, [go-plugin] VERIFIED) or as WASM (Extism, [extism] VERIFIED, only for small pure functions such as filters and mapping), with an egress allowlist from the manifest. Agent harnesses are processes anyway.
5. **Write methods** (`addComment`, `submitReview`, `push`, ...) are called exclusively by the Effect Gateway, with a token it receives from the Credential Broker for exactly this effect ([05](05-security.md)).
6. **Two versions at the same time:** current and previous major version; older ones are deprecated with a deadline and then no longer loaded.
7. **License and distribution (ADR-50):** `distribution: bundled` means the project ships the plugin together with everything it executes (image, binary, rules) in its artifacts. This is only allowed if every included license is on the project's license allowlist ([12](12-open-source-and-project.md)); a license gate in the project's CI checks this per release. Everything else is `operator_supplied`: the operator chooses and installs it themselves, the project only ships the adapter. Proprietary software (Claude Code, the Agent SDK including platform packages) is never `bundled` (ADR-39, section 6).

### 1.2 Normalized base types

```ts
interface TenantRef { orgId: string; installationId: string }
interface RepoRef { scm: string; instance: string; owner: string; name: string; id: string }
interface ChangeRef { repo: RepoRef; number: number; headSha: string; baseSha: string; headRef: string; baseRef: string; draft: boolean }
interface WorkItemRef { provider: string; instance: string; project: string; key: string }
interface Actor { providerId: string; login: string; kind: "human" | "bot" | "app" | "automation"; email?: string; viaRule?: string }
type PermissionLevel = "none" | "read" | "triage" | "write" | "maintain" | "admin";
type BuiltinServiceId = "planner" | "architect" | "coder" | "reviewer" | "qa" | "prfixer" | "indexer"
                      | "standards" | "triage" | "docs";                 // ten services, ADR-46
type ServiceId = BuiltinServiceId | `${string}/${string}`;            // third parties with namespace "<vendor>/<name>" (section 14)
type StatusCategory = "todo" | "started" | "in_review" | "done" | "blocked";
```

## 2. Normalized event schema

Reference project for fields and routing: OpenHands Automation `EventTrigger{source, on, filter}` with JMESPath ([oh-automation] `schemas.py:84-140`, VERIFIED), deduplication key from the provider delivery IDs ([gh-webhooks], [gl-webhooks], [jira-webhooks], VERIFIED).

```ts
interface TriggerEvent {
  id: string;                          // delivery ID: X-GitHub-Delivery, webhook-id, X-Atlassian-Webhook-Identifier
  dedupeKey: string;                   // hash(source.instance, subject, action, commentId, headSha)
  occurredAt: string; receivedAt: string;
  source: { plugin: string; instance: string;
            mode: "webhook" | "ci_event" | "poll" | "relay" | "schedule" | "manual";
            signature: { scheme: "hmac_sha256_hex" | "standard_webhooks" | "jwt" | "shared_secret" | "oidc" | "none";
                         verified: boolean; strength: "strong" | "weak" } };
  actor: Actor;
  where: { repo?: RepoRef; change?: ChangeRef; workItem?: WorkItemRef;
           thread?: { id: string; commentId: string; path?: string; lines?: [number, number] } };
  what: { action: "created" | "commented" | "mentioned" | "assigned" | "delegated" | "review_requested" | "labeled"
                | "synchronized" | "ready_for_review" | "ci_failed" | "review_submitted" | "prompted" | "stop"
                | "merged" | "pushed_default" | "button" | "alert_fired" | "handoff";
          subject: "issue" | "pr" | "review_comment" | "commit" | "pipeline" | "work_item" | "agent_session" | "check"
                 | "alert" | "incident" };
  mention?: { handle: string; native: boolean; offset: number };   // native: Linear, Jira ADF userType APP, GitLab service account
  command?: { name: CommandName; args: Record<string, string>;
              origin: "comment" | "label" | "assignment" | "delegation" | "button" | "dispatch" | "cli" | "mcp" };
  text?: Untrusted & { editedAfterTrigger: boolean };            // never an instruction except the command itself
  links: { workItemKeys: string[]; closes: string[]; urls: string[] };
  rawRef: string;                      // raw payload in object storage, never inline to agents
}

type CommandName = "plan" | "architect" | "code" | "review" | "qa" | "fix" | "ask" | "triage" | "docs" | "release"
                 | "approve" | "say" | "handoff" | "resume" | "pause" | "remember" | "continue" | "stop" | "hold"
                 | "config" | "ignore" | "help";   // meaning and minimum permissions: 03 section 4
                 // third-party services register further commands in the service manifest (section 14)

// Added by the router, never by the TriggerSource and never from the payload:
interface ResolvedEvent extends TriggerEvent {
  permission: { scm?: PermissionLevel; workItem?: PermissionLevel; checkedAt: string; source: string };
  identity: { platformUserId?: string };      // link from Jira account to GitHub login (identity_links)
}
type Skipped = { skipped: true; reason: string };   // every discarded event with a reason in log and metric
```

**Rules for the event:**
- The signature is verified on the raw body before JSON is parsed.
- Permissions are always queried at the provider and briefly cached, never taken from the payload. Cheap checks (event kind, bot, self-trigger) come before the expensive permission call (reference project OpenHands `github_manager.py:105-129, 233-253` [oh-cloud], VERIFIED).
- If a ticket triggers code, the trigger needs **both** permissions: write access in the ticket project and in the target repo of the linked identity.
- Jira webhooks arrive unordered and with repetitions, Forge triggers delayed by up to 3 minutes ([jira-webhooks], [forge-trigger], VERIFIED). Therefore the router reads the state fresh (`getItem`) before it acts; the payload is never the truth.
- `alert` and `incident` with `alert_fired` or `handoff` respectively are only a handoff input from monitoring and incident tools (such as Sentry Seer, plugin `incident-handoff`); the platform does not run its own SRE agent (ADR-49). Such an event produces at most a ticket or fix job that goes through the same permission and policy checks as any other input.

## 3. TriggerSource

```ts
type TriggerCap = "WEBHOOK" | "WEBHOOK_HMAC" | "POLL" | "RECONCILE" | "CI_EVENT" | "RELAY"
                | "NATIVE_BOT_MENTION" | "ACK_REACTION" | "AGENT_SESSION" | "BUTTON_ACTIONS";

interface TriggerSource extends PluginBase<TriggerCap> {
  describe(): { modes: TriggerEvent["source"]["mode"][]; events: string[]; ackDeadlineMs: number };
  verify(headers: Headers, rawBody: Uint8Array, secret: SecretRef): Promise<{ verified: boolean; scheme: string; strength: "strong" | "weak"; reason?: string }>;
  parse(headers: Headers, rawBody: Uint8Array): Promise<TriggerEvent[] | Skipped>;
  ack(ev: TriggerEvent, t?: ScopedToken): Promise<Result<void>>;   // reaction "eyes", Linear thought within 10 s; writes to the outside, therefore as effect `ack` via the Effect Gateway with a token (rule 5)
  poll?(cursor: string | null): Promise<Result<{ events: TriggerEvent[]; cursor: string }>>;
  reconcile?(since: string): Promise<Result<TriggerEvent[]>>;   // required if the provider does not redeliver
  install?(target: InstallTarget, url: string, secret: SecretRef): Promise<Result<InstallReceipt>>;
  renew?(receipt: InstallReceipt): Promise<Result<InstallReceipt>>;  // Jira app webhooks expire after 30 days
  isSelf(actor: Actor): boolean;                            // own bot identity, Forge ignoreSelf
}
```

Operating modes (`mode`):
- `webhook`: default when the control plane is publicly reachable (ADR-08).
- `relay`: a third-party system forwards, for example Jira Automation "Send web request" to the control plane or to `repository_dispatch` ([jira-automation], VERIFIED).
- `ci_event`: GitHub Actions delivers the event as `GITHUB_EVENT_PATH`; a workflow forwards it outbound. For installations without a public inbound path.
- `poll`: JQL `updated >= cursor`, GitHub search or notifications. Required in operating mode `private` without a public inbound path ([11](11-installation-and-hosting.md) section 1.1): an input plugin without `POLL` cannot be loaded there.
- `schedule`, `manual`: schedules and admin UI.

`ackDeadlineMs` comes from provider facts: GitHub 10,000, Linear 5,000 ([gh-webhooks], [linear-agents], VERIFIED).

## 4. WorkItemProvider

```ts
type WorkItemCap = "RICH_TEXT_ADF" | "TRANSITIONS" | "DELEGATION" | "AGENT_SESSION" | "PLAN_NATIVE" | "EXTERNAL_LINK"
                 | "DEV_PANEL" | "CUSTOM_FIELDS" | "ATTACHMENTS" | "PERMISSION_API" | "NATIVE_BOT_MENTION"
                 | "SET_LABELS" | "CREATE_ISSUE" | "LINK_ITEMS" | "CLOSE_AS_DUPLICATE" | "RELATED_SEARCH";  // triage, docs, planner

interface WorkItem {
  ref: WorkItemRef; title: Untrusted; body: Untrusted;
  status: { name: string; category: StatusCategory }; assignee?: Actor; labels: string[];
  fields: Record<string, Untrusted<unknown>>; acceptanceCriteria?: Untrusted[];
  components: string[]; url: string; updatedAt: string;
}

interface WorkItemProvider extends PluginBase<WorkItemCap> {
  // Reading (also from within the platform MCP)
  getItem(ref: WorkItemRef): Promise<Result<WorkItem>>;             // always fresh, the payload is never the truth
  getComments(ref: WorkItemRef, since?: string): Promise<Result<{ id: string; author: Actor; body: Untrusted; at: string }[]>>;
  search(query: string, cursor?: string): Promise<Result<Page<WorkItemRef>>>;
  searchRelated?(ref: WorkItemRef, k: number): Promise<Result<{ ref: WorkItemRef; score: number; how: "native" | "text" }[]>>;  // RELATED_SEARCH; fallback: platform search in the KnowledgeStore
  getAttachments(ref: WorkItemRef): Promise<Result<AttachmentRef[]>>;
  getLinks(ref: WorkItemRef): Promise<Result<{ url: string; kind: string }[]>>;
  userPermission(user: Actor, project: string): Promise<Result<PermissionLevel>>;
  whoami(): Promise<Result<Actor>>;
  renderMention(user: Actor): string;                                // ADF mention, @login
  // Writing, Effect Gateway only
  addComment(ref: WorkItemRef, markdown: string, opts?: { marker?: string }): Promise<Result<{ id: string }>>;  // adapter renders ADF or wiki markup
  updateComment(ref: WorkItemRef, id: string, markdown: string): Promise<Result<void>>;
  transition(ref: WorkItemRef, target: StatusCategory): Promise<Result<{ from: string; to: string }>>;  // mapping per project in the configuration
  assign(ref: WorkItemRef, who: Actor | "agent"): Promise<Result<void>>;
  linkExternal(ref: WorkItemRef, link: { url: string; title: string; kind: "pr" | "branch" | "build" | "plan" }): Promise<Result<void>>;
  setLabels?(ref: WorkItemRef, add: string[], remove: string[]): Promise<Result<void>>;                          // SET_LABELS
  createItem?(project: string, item: { title: string; bodyMd: string; labels?: string[]; marker: string }): Promise<Result<WorkItemRef>>;  // CREATE_ISSUE
  linkItems?(a: WorkItemRef, b: WorkItemRef, kind: "relates" | "duplicates" | "blocks"): Promise<Result<void>>;  // LINK_ITEMS
  closeAsDuplicate?(ref: WorkItemRef, of: WorkItemRef): Promise<Result<void>>;  // CLOSE_AS_DUPLICATE; triage only with repo opt-in (O25), default is a suggestion
  session?: {                          // native only in Linear; otherwise a status comment with a marker
    start(ref: WorkItemRef): Promise<Result<string>>;
    activity(id: string, a: { type: "thought" | "action" | "response" | "error" | "elicitation"; body: string }): Promise<Result<void>>;
    plan(id: string, steps: { title: string; status: "pending" | "in_progress" | "done" }[]): Promise<Result<void>>;   // Linear: always replace entirely
    end(id: string): Promise<Result<void>>;
  };
}
```

## 5. SCMProvider

```ts
type ScmCap = "BATCH_REVIEW" | "REVIEW_REQUEST_CHANGES" | "INLINE_MULTILINE" | "SUGGESTION_BLOCK" | "THREAD_RESOLVE"
            | "COMMENT_HIDE" | "CHECK_RUN" | "CHECK_ANNOTATIONS" | "CHECK_ACTIONS" | "COMMIT_STATUS" | "LABELS"
            | "DRAFT_CHANGE" | "SCOPED_SHORT_TOKEN" | "WEBHOOK_HMAC" | "PERMISSION_API" | "CODEOWNERS" | "CI_LOGS"
            | "MERGE_QUEUE" | "MERGE_SHA_GUARDED" | "SET_LABELS" | "REQUEST_REVIEWERS"
            | "CODE_SCANNING_READ" | "CODE_SCANNING_UPLOAD"    // code scanning: read the host's analyzer results or upload SARIF (section 12)
            | "CI_RERUN"                                       // propose_rerun of the PR fixer (05 section 2, profile rerun)
            | "APPROVE_HUMAN";                                 // optional approval of human PRs (services.reviewer.auto_approve, O24)

type TokenProfile = "read" | "review" | "comment_issue" | "labels" | "rerun" | "write_branch" | "merge" | "dispatch" | "audit_anchor";   // permission profiles in 05, section 2

interface ReviewComment { path: string; lines: [number, number]; side: "new" | "old"; bodyMd: string;
                          suggestion?: { code: string; range: [number, number] }; fingerprint: string }
interface ReviewOutcome { posted: string[]; demotedToSummary: string[];
                          fallbackUsed: "none" | "draft_notes_bulk" | "single_inline" | "summary_only"; failedPositions: string[] }
interface CheckEvidence { name: string; status: "queued" | "running" | "done";
                          conclusion?: "success" | "failure" | "neutral" | "cancelled" | "skipped";
                          annotations?: Annotation[]; url?: string }   // undefined means unknown, not empty (idea from [kodus])

interface SCMProvider extends PluginBase<ScmCap> {
  // Auth (Credential Broker only)
  mintToken(repos: RepoRef[], profile: TokenProfile, ttlS: number): Promise<Result<ScopedToken>>;
  cloneSpec(repo: RepoRef, ref: string): Promise<{ url: string; credentialHelper: "askpass" | "proxy"; depth?: number }>;  // token never in the URL
  // Reading
  getFile(repo: RepoRef, path: string, ref: string): Promise<Result<Uint8Array | null>>;
  compare(repo: RepoRef, base: string, head: string): Promise<Result<FileChange[]>>;
  getPermission(user: Actor, repo: RepoRef): Promise<Result<PermissionLevel>>;
  codeowners(repo: RepoRef, paths: string[], ref: string): Promise<Result<Record<string, Actor[]>>>;
  getChange(ref: ChangeRef): Promise<Result<{ title: Untrusted; body: Untrusted; author: Actor; draft: boolean; headSha: string; baseSha: string }>>;
  listChangedFiles(ref: ChangeRef): Promise<Result<FileChange[]>>;          // with position mapping
  getThreads(ref: ChangeRef, includeResolved: boolean): Promise<Result<Thread[]>>;
  mergeStatus(ref: ChangeRef): Promise<Result<{ mergeable: boolean; conflicts: boolean; requiredChecks: string[];
                                                 approvals: number; blocking: string[]; draft: boolean }>>;
  checkEvidence(repo: RepoRef, sha: string): Promise<Result<CheckEvidence[]>>;
  repoInfo(repo: RepoRef): Promise<Result<{ visibility: "public" | "internal" | "private"; fork: boolean }>>;   // fresh per claim: repo class (05 section 3), visibility rule (ADR-63)
  approvalProtection?(repo: RepoRef, branch: string): Promise<Result<{ dismissStale: boolean; lastPushApproval: boolean } | { unreadable: true }>>;   // ADR-61 (a); unreadable counts as not fulfilled
  ciFailureLogs(repo: RepoRef, sha: string, maxBytes: number): Promise<Result<Untrusted[]>>;
  rateLimitState(): Promise<RateLimitSnapshot | null>;
  // Writing (Effect Gateway only, token per effect)
  upsertSummary(t: ScopedToken, ref: ChangeRef, marker: string, md: string): Promise<Result<{ id: string }>>;  // marker carries only run_id and last_reviewed_sha
  submitReview(t: ScopedToken, ref: ChangeRef, r: { comments: ReviewComment[]; verdict: "comment" | "request_changes";
               commitSha: string; bodyMd: string; idempotencyKey: string }): Promise<Result<ReviewOutcome>>;  // fallback chain internal
  reply(t: ScopedToken, ref: ChangeRef, threadId: string, md: string): Promise<Result<void>>;
  resolveThread(t: ScopedToken, ref: ChangeRef, threadId: string, resolved: boolean): Promise<Result<void>>;
  renderSuggestion(code: string, range: [number, number]): string;   // GitHub ```suggestion, GitLab suggestion:-a+b, otherwise code block
  startCheck(t: ScopedToken, repo: RepoRef, sha: string, name: string): Promise<Result<string>>;
  updateCheck(t: ScopedToken, repo: RepoRef, id: string, u: { status: "queued" | "in_progress" | "completed";
              conclusion?: "success" | "neutral" | "failure" | "action_required"; summaryMd: string;
              annotations?: Annotation[]; actions?: { id: string; label: string }[] }): Promise<Result<void>>;
  push(t: ScopedToken, repo: RepoRef, branch: string, bundleRef: string, expectedOldSha: string | null): Promise<Result<{ newSha: string }>>;  // never force
  openChange(t: ScopedToken, repo: RepoRef, c: { head: string; base: string; title: string; bodyMd: string;
             draft: true; labels?: string[]; reviewers?: Actor[] }): Promise<Result<ChangeRef>>;
  updateChange(t: ScopedToken, ref: ChangeRef, patch: Partial<{ title: string; bodyMd: string; draft: boolean }>): Promise<Result<void>>;
  requestReview(t: ScopedToken, ref: ChangeRef, users: Actor[]): Promise<Result<void>>;           // REQUEST_REVIEWERS, assignees from codeowners()
  setLabels?(t: ScopedToken, ref: ChangeRef, add: string[], remove: string[]): Promise<Result<void>>;  // SET_LABELS
  rerunFailedJobs?(t: ScopedToken, repo: RepoRef, sha: string, jobIds: string[]): Promise<Result<void>>;  // CI_RERUN; only jobs of the current SHA, at most once per commit
  // Optional, only with capability APPROVE_HUMAN; Effect Gateway only, profile "review" only, human PRs only (never agent PRs), only with services.reviewer.auto_approve (04)
  // Agent PR here means (one of the three criteria suffices, detailed design 09 FE-928): branch agent/*, or opened by the app, or at least one commit between base and head pushed by the Effect Gateway (SHA chain from effects, like merge gate condition 11 in 03); then "agent_pr"
  // Conditions a to d from ADR-61 are checked by the Effect Gateway before the call (04 section 3); every new push leads to withdrawApprove
  approve?(t: ScopedToken, ref: ChangeRef, a: { commitSha: string; bodyMd: string; idempotencyKey: string }): Promise<Result<void | { rejected: "head_moved" | "agent_pr" }>>;
  withdrawApprove?(t: ScopedToken, ref: ChangeRef, a: { reason: string; idempotencyKey: string }): Promise<Result<void>>;   // only the app's own approve (GitHub: dismiss review)
  // Optional, only with capability MERGE_SHA_GUARDED or MERGE_QUEUE; Effect Gateway only, profile "merge" only, only after the merge gate (03 section 1a)
  merge?(t: ScopedToken, ref: ChangeRef, m: { expectedHeadSha: string; method: "merge" | "squash" | "rebase";
         viaQueue: boolean; idempotencyKey: string }): Promise<Result<{ mergeSha: string } | { rejected: "head_moved" | "not_mergeable" }>>;
}
// Deliberately absent: approve() for agent PRs, verdict "approve" in submitReview, approve or merge without SHA binding, writing under .github/workflows.
```

**Rationale for the gaps in the contract:** A bot approve could satisfy branch protection and thereby bypass human approval; this was a blocker raised by the reviewers. Therefore `approve` is only an optional method for **human** PRs (O24 decided, ADR-14): bound to the verified head SHA (`commitSha`, rejected if the head has moved), only via the Effect Gateway, only with `services.reviewer.auto_approve: true` and the conditions in [02](02-services.md) section 4 and [04](04-configuration-and-limits.md), including (a) to (d) from ADR-61: the host dismisses stale approves and requires an approve after the last push, author with write access and not a fork, full non-paused review at the head, P0/P1 withdrawal only by another human with write access. The platform withdraws its approve with `withdrawApprove` on every new push. Never for agent PRs; there `agent-approval-check` continues to apply. A provider without SHA-bound approval reports `APPROVE_HUMAN: none`; then there is no automatic approval. `merge` is an optional method for the optional autonomous merge (stage 5). It is bound to the verified head SHA: GitHub rejects with 409 if the head differs ([gh-merge] VERIFIED). Only the Effect Gateway may call it, after the merge gate ([03](03-flow-and-orchestration.md) section 1a). A provider without SHA binding and without a merge queue reports `none`; there the merge stays with the human.

**Push check:** `push` takes a Git bundle that the worker has uploaded. The Effect Gateway checks beforehand: `expectedOldSha` matches, branch prefix `agent/` (only exception: the platform effect `audit_anchor` on the fixed anchor branch with profile `audit_anchor`; never a human PR branch, not even in the PR fixer's watch mode, ADR-71), no forbidden paths ([04](04-configuration-and-limits.md) `forbidden_paths`), no secret found (gitleaks rules), size limit.

**Fallback chains (excerpt):**

| Capability | Fallback chain |
|---|---|
| Publish review | Batch review (GitHub, Gitea) > draft notes plus `bulk_publish` (GitLab) > individual inline comments plus summary > summary only |
| Result status | Check with annotations (GitHub, Bitbucket Code Insights) > commit or PR status plus summary (GitLab, Azure DevOps, Gitea) > code quality artifact (GitLab Ultimate only) |
| Code suggestion | Suggestion block > normal code block |
| Command buttons | Check actions (GitHub, at most 3) > command in a comment |
| Short-lived token | Installation token (GitHub) > project access token per repo with minimal role and rotation, marked as a "weaker level" |
| Labels | `SET_LABELS` > comment marker (for example Bitbucket) |
| Close duplicate (`triage`) | Suggestion as a comment with a link (default) > `LINK_ITEMS` "duplicates" > `CLOSE_AS_DUPLICATE` only with repo opt-in (O25) |
| Find similar items | The provider's `RELATED_SEARCH` > full-text and vector search in the KnowledgeStore |
| Analyzer results at the host | `CODE_SCANNING_UPLOAD` > check annotations > summary |

## 6. AgentRuntime (harness)

Reference project: Pullfrog `interface Agent { install; run }` with `AgentCredential` types and usage ([pullfrog] `agents/shared.ts:102-202`, VERIFIED).

```ts
type RuntimeCap = "NATIVE_TOOLS_LOCKABLE" | "SHELL_VIA_SANDBOX_ONLY" | "STRUCTURED_OUTPUT" | "SUBAGENTS_GATED"
                | "BUDGET_ABORT" | "COST_USD" | "CACHE_TOKENS" | "LIMITS_READABLE" | "RESUME" | "BARE_MODE" | "OTEL_NATIVE"
                | "STEER" | "EXPORT_SESSION";   // RESUME is required for the coder (follow-up question, 03 section 2.4)
type CredentialKind = "subscription" | "api_key" | "wif" | "gateway" | "bedrock" | "vertex" | "foundry"
                    | "openai" | "azure_openai" | "chatgpt";

interface AgentTask {
  service: ServiceId; runId: string; stepId: string; itemId: string;
  systemInstructions: string;          // platform prompt plus rules from the base SHA, trusted
  instruction: string;                 // only the triggering command and the task
  context: Untrusted[];                // ticket, PR text, comments, logs: embedded marked
  workdir: string;
  model: { id: string; fallback?: string }; credential: CredentialRef;   // broker resolves, runtime never stores
  platformMcp: { url: string; token: string; tools: string[] };          // token bound to exactly this work item
  nativeTools: "none" | "read" | "edit" | "edit+shell";
  subagents: { allowed: boolean; maxDepth: 1; deniedTools: string[] };
  outputSchema?: JSONSchema;
  budget: { maxUsd?: number; maxTurns: number; maxWallMs: number; maxOutputTokens?: number };
  telemetry: { traceparent: string; otlpEndpoint: string };
}
type RuntimeEvent =
  | { t: "started" } | { t: "message"; role: string; textHash: string }
  | { t: "tool_use"; name: string; argsHash: string } | { t: "tool_result"; name: string; ok: boolean }
  | { t: "usage"; model: string; in: number; out: number; cacheRead: number; cacheWrite: number }
  | { t: "rate_limit"; status: "allowed" | "allowed_warning" | "rejected"; utilization?: number; resetsAt?: string }
  | { t: "permission_denied"; tool: string } | { t: "error"; code: string } | { t: "finished" };
interface AgentRunResult {
  status: "ok" | "failed" | "budget_exceeded" | "rate_limited" | "auth_failed" | "cancelled" | "schema_invalid";
  structured?: unknown; text?: string; sessionRef?: string; transcriptRef: string; workspaceDiffRef?: string;
  usage: Record<string, { in: number; out: number; cacheRead: number; cacheWrite: number; reasoning?: number }>;
  cost: { usd?: number; source: "provider" | "client_estimate" | "price_table" | "subscription_utilization" };
  limitEvents: LimitSnapshot[];
}
interface AgentRuntime extends PluginBase<RuntimeCap> {
  supports(cred: CredentialKind): { ok: boolean; constraints: string[] };   // start path per kind: table below (subscription: no --bare, only nativeTools none|read; wif: --bare only via credential relay)
  install(sb: SandboxHandle, pin: PinnedVersion): Promise<Result<void>>;     // at the operator from the official source, ADR-39
  run(task: AgentTask, sb: SandboxHandle, sink: (e: RuntimeEvent) => void, signal: AbortSignal): Promise<AgentRunResult>;   // sandbox of the item as a parameter
  resume?(sessionRef: string, prompt: string, task: AgentTask, sb: SandboxHandle, sink: (e: RuntimeEvent) => void, signal: AbortSignal): Promise<AgentRunResult>;
  steer?(sessionRef: string, text: string): Promise<Result<void>>;           // STEER: message into the running session (@agent say)
  exportSession?(sessionRef: string): Promise<Result<{ bundleRef: string }>>;  // EXPORT_SESSION: transcript bundle for @agent handoff
  probeLimits?(cred: CredentialRef): Promise<LimitSnapshot | null>;          // null = only reactive (subscription)
}
interface PinnedVersion {
  package: string;                     // for example "@anthropic-ai/claude-code", "@openai/codex"
  version: string;                     // exact, never "latest"
  sha256: string;                      // from the operator configuration; mismatch = abort with error "invalid"
  source: "npm" | "official_installer" | "operator_mirror";
}
```

**Harness installed at the operator, never shipped (ADR-39):** Claude Code, the Agent SDK `@anthropic-ai/claude-agent-sdk` itself and its platform packages are "All rights reserved" and are subject to Anthropic's terms ([cc-npm], [sdk-npm] VERIFIED; the main package according to [`open-source-lizenz-und-recht`](../research/open-source-lizenz-und-recht.md) section 2.3 "ship: no"; according to the registry the platform packages contain the native CLI, [`gegenpruefung-lizenz-und-recht`](../research/gegenpruefung-lizenz-und-recht.md) item 7). Our images and packages contain none of them, and no package of the project depends on the Agent SDK: the adapter `claude-code` starts the CLI via `claude -p` (below), without the SDK. Should a later adapter need the SDK, it would be `operator_supplied` like the CLI. `install` loads the version pinned by the operator with a checksum from the official source or from their mirror; the worker may cache it on the operator's machine. Free harnesses with their own license (Codex CLI Apache-2.0 [codex-repo], OpenHands SDK MIT [oh-sdk-repo], VERIFIED) may be `bundled` if their license is on the allowlist (rule 7); the terms of use of the respective service apply separately (matrix 11.4).

**Implementations and conditions:**
- **`claude-code`:** default `claude -p --bare --setting-sources user` with its own `CLAUDE_CONFIG_DIR`, managed settings deny for native exec tools, output via `--json-schema` (field `structured_output`), abort via `--max-budget-usd` and `maxTurns` ([cc-headless], [cc-sdk-ts], VERIFIED). Reason for `--bare`: without `--bare`, `-p` executes hooks and `.mcp.json` of the repo ([cc-headless], VERIFIED). Reason for additionally `--setting-sources user`: even `--bare` applies the `env` block of the project settings; `--setting-sources user` reads neither project settings nor `.mcp.json` ([cc-permissions] "What runs before you trust a folder", VERIFIED, read 2026-10-31; whether both flags work together: unverified, contract test). Reason for managed settings deny instead of only `--disallowedTools`: the latter "was observed to leak" ([pullfrog] `agents/claude.ts:1-19`, VERIFIED). Managed settings pin the LLM endpoint: `allowedProviders: ["customEndpoint"]` plus `ANTHROPIC_BASE_URL` of the credential relay in the managed `env` block; Claude Code then rejects any other endpoint ([cc-auth], [cc-gateway], VERIFIED).
- **Start path per credential kind** (principle from [05](05-security.md) section 3: a long-lived LLM credential never goes into the sandbox; the **credential relay** is part of the egress proxy, runs outside the sandbox in Z1 and inserts the real credential header only when forwarding to the one allowed LLM host; it only lets `/v1/messages` through without `mcp_servers` and server tools and books every response against the item budget, see [05](05-security.md) section 3 "Limiting the relay"):

| Credential kind | Start and authentication | Visible in the sandbox | Evidence |
|---|---|---|---|
| `api_key` | `--bare` with `--setting-sources user`, `--strict-mcp-config --mcp-config <platform MCP only>` and `--settings '{"disableAllHooks": true}'` as with the subscription ([05](05-security.md) section 3 item 5; detailed design 05 FE-525); `ANTHROPIC_BASE_URL` = relay, `ANTHROPIC_API_KEY` = placeholder per item; the relay replaces `X-Api-Key` with the key from the broker | placeholder only | `--bare` takes `ANTHROPIC_API_KEY` or `apiKeyHelper` from `--settings` ([cc-headless] B); `X-Api-Key` header ([cc-auth] B); `ANTHROPIC_BASE_URL` for gateways ([cc-gateway] B); replacement in the relay A |
| `wif` | In Z1 the worker exchanges the OIDC JWT signed by the broker via `POST /v1/oauth/token` (`jwt-bearer`) for an access token `sk-ant-oat01-...` ([an-wif] B). The lifetime is set by the federation rule (`token_lifetime_seconds` 60 to 86,400, default 3,600), not by the item; per item only the `exp` of the broker JWT limits it, because the access token lives "the lesser of" the rule value and "twice the remaining lifetime of the IdP JWT", at least 60 s ([an-wif] B, section "Token lifetime and refresh"). Therefore the broker sets `exp` to at most half of the remaining lease time and issues a fresh JWT for every exchange (tokens with `jti` are single-use by default, [an-wif] B). Start like `api_key` with a placeholder; the relay removes `X-Api-Key` and sets `Authorization: Bearer <access token>` (Bearer according to [an-wif] B) | placeholder only | `--bare` reads no profiles and no federation variables ("Claude Code doesn't read profiles or federation variables in bare mode", [cc-auth] B), therefore never federation variables in the sandbox; the exchange is done by the worker |
| `gateway` | like `api_key`; the relay sets the gateway header | placeholder only | [cc-gateway] B; header swap A |
| `bedrock` | `--bare` with `CLAUDE_CODE_USE_BEDROCK=1`; target: `ANTHROPIC_BEDROCK_BASE_URL` = relay, which signs with short-lived STS credentials. Until the contract test is green: short-lived STS credentials per item in the sandbox, role only `InvokeModel*` on the allowed `eu.` profiles, lifetime at most the lease | target: nothing; transition: STS credentials of an item role | `--bare` reads provider credentials as usual ([cc-headless] B); `ANTHROPIC_BEDROCK_BASE_URL` for gateways ([cc-bedrock] B); disabling client signing is only verified for Mantle (`CLAUDE_CODE_SKIP_MANTLE_AUTH`, [cc-bedrock] B), unverified for the invoke API |
| `vertex`, `foundry` | like `bedrock` (relay target, transition short-lived federation credentials) | like `bedrock` | unverified, before stage 8 |
| `subscription` | no `--bare` (reads no OAuth and no `CLAUDE_CODE_OAUTH_TOKEN`, [cc-auth], [cc-headless] B); `--setting-sources user`, `--strict-mcp-config --mcp-config <platform MCP only>`, `--settings '{"disableAllHooks": true}'`, its own empty `CLAUDE_CONFIG_DIR`, managed settings, unmodified binary. **Authentication (ADR-57):** The operator creates the token themselves with `claude setup-token` and stores it in a file on the worker host that only the worker user can read; only the local configuration of the worker package knows the path, never `installation.yaml`, org or repo configuration. The worker reads the file per item and sets the token only in the environment of the `claude` process (`CLAUDE_CODE_OAUTH_TOKEN`), never in the DB, work item envelope, snapshot, log or transcript. Reason: `setup-token` "does not save the token anywhere", it is set as `CLAUDE_CODE_OAUTH_TOKEN` ([cc-auth] B); with an empty config directory and without this variable the CLI reports "Not logged in" (Red Team on the overall idea, finding 2, reproduced with CLI 2.1.288). `/login` is not a start path, not even with `max_concurrency` above 1: its token would be in `.credentials.json` of the config directory, which is empty per item, and parallel copies of a token with refresh could invalidate each other (unverified) | the subscription token (lifetime one year, [cc-auth] B) in the environment of the `claude` process | Insertion by the relay is ruled out because the platform would then "intermediate[s]" the token ([cc-legal] B, assessment A). Therefore only services with `nativeTools: none` or `read`, without a build verifier, pool `self-hosted` with `single_operator: true`; exception profile `operator_test` for a single operator who works on their own private repos with their own subscription ([05](05-security.md) sections 3 and 6). **Personal operator mode (ADR-51):** locked by default, enabled only with `acknowledge_terms` in the configuration ([04](04-configuration-and-limits.md)); the platform never implements a login; the control plane never sees the token, only the worker binary on the operator's host passes it locally to the `claude` process (ADR-57). Whether this passing counts as "intermediate" is an operator risk alongside `acknowledge_terms` ([05](05-security.md) section 6) |
| `openai` (harness `codex`) | relay with a placeholder key; whether Codex supports the base URL change for this purpose: unverified | target: placeholder only | until the contract test only services without a shell |
| `chatgpt` (harness `codex`) | login only in the unmodified Codex CLI on the worker host; access tokens for automation exist only in ChatGPT Enterprise workspaces ([codex-auth] B) | the ChatGPT token in the Codex process | like `subscription`: personal operator mode, locked by default, `acknowledge_terms`, only `self-hosted` with `single_operator`, only services without a shell (ADR-51); [codex-auth] recommends the API key for programmatic runs ("Use API key authentication for programmatic Codex CLI workflows", B) |

  Contract test per row (in the stage that first uses the kind: `api_key` stage 1, `subscription` stage 0, because the test operation of the reference installation and the project itself run on it (O28), the others stage 8, [08](08-roadmap.md); except for `subscription`, against a stub of the vendor endpoint built from the public documentation, a run against a real account is an optional owner task, O28): "Start with `<kind>`" starts the harness with exactly this path, a model call succeeds, and a scan of the sandbox's environment, file system and process list finds no real credential (except the documented transition for `bedrock` and the operator modes `subscription` and `chatgpt`). For `subscription` additionally: the token comes only from the host file (ADR-57), and a secret scan finds it in no table, no work item envelope, no snapshot and no log (cases in S1 and S2).
- **Environment per credential kind from an allowlist:** Claude Code evaluates several credential sources in a fixed order of precedence; `ANTHROPIC_AUTH_TOKEN` and `ANTHROPIC_API_KEY` rank above `CLAUDE_CODE_OAUTH_TOKEN` and above WIF, and a leftover `ANTHROPIC_API_KEY` "silently shadows federation" ([cc-auth], [an-wif] B). The worker therefore never builds the environment of the harness process from its own environment, but empty plus the allowlist of the chosen kind: common `PATH`, `HOME`, `LANG`, `CLAUDE_CONFIG_DIR`, `HTTPS_PROXY` and the OTel variables from [06](06-operations-and-deployment.md) section 4 (`TRACEPARENT`, endpoint and switch of the telemetry; detailed design 05 FE-523); in addition for `api_key` and `wif` only `ANTHROPIC_BASE_URL` and the placeholder `ANTHROPIC_API_KEY`; for `gateway` `ANTHROPIC_BASE_URL` and the placeholder `ANTHROPIC_AUTH_TOKEN`; for `bedrock` `CLAUDE_CODE_USE_BEDROCK`, `ANTHROPIC_BEDROCK_BASE_URL`, `AWS_REGION` and during the transition the STS variables of the item role; for `subscription` only `CLAUDE_CODE_OAUTH_TOKEN`, filled from the host file (ADR-57), never from the worker environment; CA trust for the inspection proxy open (M21). All other credential variables (`ANTHROPIC_*`, `CLAUDE_CODE_OAUTH_TOKEN` except for `subscription`, `CLAUDE_CODE_USE_*`, `AWS_*`, `GOOGLE_*`, `AZURE_*`, `OPENAI_*`) are absent. Test in the contract test of every row: the worker environment deliberately contains foreign credential variables (for `subscription` also a foreign `CLAUDE_CODE_OAUTH_TOKEN`), and `/proc/<pid>/environ` of the harness contains none of them.
- **`claude-code` with `subscription`:** further conditions in [05](05-security.md) section 6.
- **`codex` (free harness, stage 8):** Codex CLI under Apache-2.0 ([codex-repo] VERIFIED). `codex exec --json --output-schema`, sandbox `read-only` or `workspace-write` ([codex-exec], VERIFIED); repo configuration as `untrusted`, subagents off, because Codex has no pre-tool hook ([pullfrog] `agents/codex.ts`, VERIFIED). Cost only via the price table.
- **`openhands-sdk` (free harness, stage 9):** OpenHands Agent SDK under MIT ([oh-sdk-repo] VERIFIED; the separate folder `enterprise/` of the OpenHands repo is under PolyForm Free Trial and is not used, [oh-lic] VERIFIED). Reason for inclusion: at least one free harness must be qualifiable for coder and PR fixer so that the platform is usable without an Anthropic contract, and the OpenHands Index measures exactly this harness with varying models, thus providing a direct Gate B reference ([`ebene-coding`](../research/ebene-coding.md) section 1 item 5 and table "OpenHands Index", DERIVED).
- **`opencode`:** via `opencode serve` over HTTP ([opencode], [pullfrog] `agents/opencode.ts`, VERIFIED); more than 75 providers. Claude subscription plugins have been removed there ("Anthropic explicitly prohibits this", [opencode], CLAIMED according to [`gegenpruefung-lizenz-und-recht`](../research/gegenpruefung-lizenz-und-recht.md) item 11, primary source not retrieved ourselves).
- **`gemini-cli`, `goose`:** in stage 9 as needed; structured output unverified. For the unpaid tier and Google One, Gemini CLI was replaced by Antigravity CLI on 2026-06-18 ([gemini-tos] VERIFIED); an adapter for free tiers would therefore have to connect Antigravity CLI (unverified, check before stage 9). Google login only in the unmodified CLI, never its token in platform code ([gemini-tos] B).
- **`acp-generic`:** only as a fallback adapter; according to its introduction page ACP standardizes neither budget nor schema nor sandbox, remote is "a work in progress" ([acp], VERIFIED; specification itself unverified).
- **Aider:** not an option, one instruction per run without a documented tool loop ([aider], VERIFIED; assessment DERIVED).

## 7. ModelProvider (single calls)

For gate, triage, verifier judges, eval judges, summaries, embeddings and batch analysis.

```ts
type ModelCap = "TOOLS" | "STRICT_SCHEMA" | "PROMPT_CACHE" | "BATCH_API" | "EMBEDDINGS" | "COST_FROM_PROVIDER"
              | "LIMIT_HEADERS" | "REGION_EU";
interface GenerateRequest {
  model: string; system?: string; messages: Msg[]; tools?: ToolDef[]; outputSchema?: JSONSchema; strictTools?: boolean;
  cache?: { breakpoints: number[] } | "auto"; maxTokens: number; region?: "eu" | "us" | "global";
  meta: { tenant: TenantRef; repo?: string; user?: string; service: ServiceId; runId: string };  // limits and audit
}
interface GenerateResult {
  text?: string; structured?: unknown; toolCalls?: ToolCall[]; requestId: string;
  usage: { in: number; out: number; cacheRead: number; cacheWrite: number; reasoning?: number };
  cost: { usd?: number; source: "provider" | "price_table" }; limits?: LimitSnapshot;
}
interface ModelProvider extends PluginBase<ModelCap> {
  models(): Promise<ModelInfo[]>;                            // price per token, context, regions
  generate(req: GenerateRequest, signal: AbortSignal): Promise<Result<GenerateResult>>;
  submitBatch?(reqs: GenerateRequest[]): Promise<Result<string>>;
  collectBatch?(id: string): Promise<Result<GenerateResult[]>>;
  embed?(texts: string[], model: string): Promise<Result<{ vectors: Float32Array[]; dim: number; usage: Usage }>>;
  countTokens?(req: GenerateRequest): Promise<Result<number>>;
}
```

Implementation: per provider a thin adapter of our own on top of the Vercel AI SDK, which has official packages for Anthropic, Bedrock, Google Vertex, Azure, OpenAI and Google ([aisdk], VERIFIED). The subscription has no direct adapter because the setup token is intended for model requests only via the CLI ([cc-auth], VERIFIED; assessment DERIVED); for that there is `claude-cli`.

**`claude-cli` (ModelProvider for the credential kind `subscription`, ADR-58):** Every single call is a work item that runs via worker and egress proxy, never in the control plane. The worker starts `claude -p` without tools (managed settings deny for all native tools, no platform MCP) with `--json-schema` for `outputSchema`, in the start path and with the environment of the row `subscription` from section 6 (token from the host file, ADR-57). The same conditions apply as for `subscription` ([05](05-security.md) section 6: pool `self-hosted` with `single_operator`, trigger only the operator, `acknowledge_terms`). Capability level `fallback` per rule 2: startup overhead per call, no batch API, no embeddings, no limit headers, no cost from the provider; `fallback` and startup overhead are recorded in the audit and in the run summary. If `EMBEDDINGS` is missing, the core switches off vector search per rule 2. Configuration: entry in `models` with `plugin: claude-cli` and a reference to a runtime of kind `subscription` ([04](04-configuration-and-limits.md) section 3a).

**Resolver rule (ADR-58):** A service whose model references (`models.*`, `gate_model`, `notes_model`) point to no reachable ModelProvider is rejected on load. Reachable means: entry in `models` present, plugin loaded, data path allowed, and with `claude-cli` the referenced `subscription` runtime is enabled and permitted for the service. A service with a required single call (reviewer gate, clarity gate and plan critique of the planner, equivalence judge of QA, classification of triage, [02](02-services.md)) without its own reference needs at least one entry in `models` reachable for it, otherwise the same applies. Test in S2 and in S4 ("reviewer alone on with `subscription`").

## 8. ExecutionBackend and sandbox

```ts
type ExecCap = "DOCKER_IN_DOCKER" | "MICROVM" | "USERSPACE_KERNEL" | "EGRESS_PROXY" | "SNAPSHOT" | "GPU" | "BROWSER"
             | "KVM" | "SELF_HOSTED" | "SINGLE_OPERATOR";
type Isolation = "sysbox" | "gvisor" | "microvm";        // microvm: Firecracker (E2B) or Kata

interface SandboxSpec {
  image: string;                      // digest, not tag
  envSpec?: { devcontainer?: string; setupScript?: string; maintenanceScript?: string; blueprint?: string };
  resources: { cpu: number; memMb: number; diskMb: number; wallMs: number };
  isolation: Isolation;               // at least the minimum isolation of the repo class (rule below)
  phases: {
    setup: { secrets: SecretRef[]; network: "open" | "allowlist" };       // secrets only here (Codex pattern)
    agent: { secrets: []; network: "allowlist" };                          // removed before the agent phase
  };
  egress: { allow: string[]; proxy: string };                               // per service, see 05
  mounts: { repo: "ro" | "rw"; gitDir: "ro" };
  readOnlyPaths: string[]; denyReadPaths: string[];                         // .git/config, credential files
  trustedCaCerts?: string[];                                                // PEM into the sandbox trust store (check proxy, 05 section 6 condition 9)
  snapshotKey?: string;                                                     // rebuild on change (Devin blueprint idea)
}
interface SandboxHandle {
  id: string;
  exec(cmd: string[], opts: { role: "setup" | "agent" | "check"; cwd?: string; env?: Record<string, string>; timeoutMs: number }): Promise<{ code: number; outRef: string }>;
  spawn(cmd: string[], opts: { role: "agent" | "check"; cwd?: string; env: Record<string, string> }): Promise<SandboxProcess>;   // output as a stream (stdout, stderr, stdin, kill, wait), for AgentRuntime.run
  copyIn(src: string, dst: string): Promise<void>;
  copyOut(src: string): Promise<Uint8Array>;
  exportBundle(base: string, branch: string): Promise<{ bundleRef: string; files: string[] }>;
  snapshot?(tag: string): Promise<string>;
  destroy(): Promise<void>;           // always, also in the failure path (finally), test S6
}
interface ExecutionBackend extends PluginBase<ExecCap> {
  pools(): Promise<PoolInfo[]>;                      // label, slots, capabilities, harness x credential
  maxConcurrency(pool: string): number;              // hard upper limit (with ci-dispatch: share of the runner slots)
  dispatch?(item: WorkItemEnvelope): Promise<Result<{ started: boolean; reason?: string }>>;   // e.g. workflow_dispatch with ci-dispatch-github
  create(spec: SandboxSpec, ctx: RunCtx): Promise<Result<SandboxHandle>>;     // runs in the worker
  buildSnapshot?(repo: RepoRef, spec: SandboxSpec): Promise<Result<{ snapshot: string; postBuildOk: boolean }>>;
  restore?(snapshotRef: string, spec: SandboxSpec, ctx: RunCtx): Promise<Result<SandboxHandle>>;   // SNAPSHOT: counterpart to snapshot(tag), continuation after a follow-up question
}

// Worker side (one binary for all backends), talks only to the work API
interface WorkerApi {
  claim(pool: string, caps: WorkerCaps, waitMs: number): Promise<WorkItemEnvelope | null | { upgradeRequired: true } | { retryAfterMs: number }>;   // long poll; upgrade_required for workers older than N-1, retry_after in drain mode (03 section 6)
  heartbeat(leaseId: string, usage?: Usage): Promise<{ cancel: boolean; reason?: string }>;  // abort on budget or stop
  complete(leaseId: string, result: StepResult): Promise<void>;
  fail(leaseId: string, err: StepError): Promise<void>;
  uploadUrl(leaseId: string, kind: "log" | "transcript" | "bundle" | "artifact" | "sarif"): Promise<string>;  // presigned via BlobStore.presignPut (section 13)
}
interface WorkerCaps {
  workerVersion: string;
  verified: {                          // self-checked at startup and before every claim, never taken from the configuration
    isolation: Isolation[];            // sysbox: sysbox-runc registered; gvisor: runsc registered; microvm: /dev/kvm readable and writable or RuntimeClass kata
    runtimeClasses?: string[];         // k8s only: available RuntimeClasses
    egressProxy: boolean;              // probe: direct access from the sandbox fails, access via the proxy succeeds
    probedAt: string; probeVersion: string;
  };
  harnesses: { runtime: string; credentialKinds: CredentialKind[] }[];
  singleOperator?: string;             // operator ID with single_operator
}
```

**Implementations, named by kind:**

| Implementation | What it is | Isolation | Pool example | Stage |
|---|---|---|---|---|
| `docker-sysbox` | Sandbox container with the Sysbox runtime, Docker-in-Docker without `--privileged` ([sysbox] VERIFIED) | `sysbox` | `self-hosted`, `cloud` | 0 |
| `docker-gvisor` | Sandbox container with gVisor (`runsc`), runs without KVM ([gvisor] VERIFIED) | `gvisor` | `self-hosted`, `cloud` | 0 |
| `self-hosted` | Worker package (systemd service) for the operator's own machines; uses `docker-sysbox` or `docker-gvisor` locally; with `single_operator: true` a prerequisite of the operator modes `subscription` and `chatgpt` | as chosen | `self-hosted` | 0 |
| `k8s` | Worker as a deployment per pool, sandbox pods via RuntimeClass (`sysbox-runc`, `runsc`, `kata`) | per RuntimeClass | `cloud` | 8 (with Helm) |
| `ci-dispatch-github` | triggers `workflow_dispatch` in a runner repo per item; the job starts the same worker | Sysbox or gVisor in the job, depending on the runner | `ci-dispatch` | 8 |
| `microvm` | Firecracker via E2B self-hosted ([e2b] VERIFIED) or Kata | `microvm` | `cloud`, `self-hosted` with KVM | 9 (required before foreign code) |

Further CI systems (such as `ci-dispatch-gitlab`) follow the same pattern as needed. Evidence on KVM and privileged containers per base: [`hosting-und-installation`](../research/hosting-und-installation.md) section 2.8.

**Rules on isolation (ADR-48):**
1. **gVisor is equivalent to Sysbox.** Reason: gVisor runs on any Linux base without KVM and without privileged mode, Sysbox only has "best effort" support ([`hosting-und-installation`](../research/hosting-und-installation.md) sections 2.8 and 3.3, DERIVED). Builds that need Docker-in-Docker require `DOCKER_IN_DOCKER` and thus Sysbox or MicroVM.
2. **Minimum isolation per repo class:** repos whose content comes only from people with write access need at least `sysbox` or `gvisor`. Repos with foreign code (public repos with outside contributions, forks, customer code) need `microvm`. The mapping is in the repo class ([04](04-configuration-and-limits.md)); the router gives an item only to a pool whose workers report the minimum isolation as verified. If there is none, the item stays pending with reason `no_qualified_pool` instead of running weaker.
3. **Verified, not configured:** On `claim` the worker reports its `WorkerCaps.verified`. Reason: Fargate and Container Apps look like normal Linux environments but do not allow privileged containers (Fargate VERIFIED, Container Apps CLAIMED), and according to a third-party report Hetzner Cloud offers no `/dev/kvm` (CLAIMED; all in [`hosting-und-installation`](../research/hosting-und-installation.md) section 2.8). If the report deviates from the pool configuration, the report applies, and the admin UI shows the deviation.
4. The built-in Claude Code sandbox only counts as an addition, never as a boundary: it only covers shell commands and silently falls back to "off" without `failIfUnavailable` ([cc-sandbox], VERIFIED).

## 9. KnowledgeStore

```ts
type KbCap = "SYMBOL_GRAPH" | "VECTOR" | "FTS" | "SUMMARIES" | "LEARNINGS" | "CROSS_REPO" | "OFFLINE_ARTIFACT";
interface Citation { repo: RepoRef; path: string; sha: string; lines: [number, number]; quoteHash: string }
interface KnowledgeStore extends PluginBase<KbCap> {
  layerState(repo: RepoRef): Promise<LayerState[]>;   // L0: watermark_sha, schema_v, parser_v, prompt_v, model, embed_model
  applyIncrement(repo: RepoRef, layer: Layer, from: string, to: string, delta: LayerDelta): Promise<Result<void>>;  // watermark only after success
  rebuild(repo: RepoRef, layer: Layer, at: string, data: AsyncIterable<LayerRecord>): Promise<Result<void>>;
  query: {
    repoMap(repo: RepoRef, at: string, budgetTokens: number): Promise<string>;
    symbolContext(repo: RepoRef, symbol: string, at: string): Promise<SymbolContext>;
    impact(repo: RepoRef, diff: FileChange[]): Promise<ImpactSet>;
    search(repo: RepoRef | "org", q: string, k: number): Promise<{ ref: Citation; score: number; kind: "code" | "summary" }[]>;  // lexical (BM25 or approximation with Postgres tsvector and ts_rank_cd, detailed design 12 FE-1204) plus vector plus RRF
    learnings(repo: RepoRef, path: string, headSha: string): Promise<Learning[]>;      // only with a valid quote at headSha
    standards(repo: RepoRef, path: string, baseSha: string): Promise<{ ruleId: string; text: string; source: Citation }[]>;
    findingsHistory(repo: RepoRef, path: string): Promise<FindingStat[]>;
  };
  putLearning(l: LearningCandidate, origin: { actor: Actor; permission: PermissionLevel; sourceRef: string }): Promise<Result<string>>;  // only humans with write access
  invalidate(id: string, reason: string): Promise<void>;   // invalid_at instead of deletion
  // Lifecycle of the learnings (02 section 7)
  voteLearning(id: string, vote: 1 | -1, actor: Actor): Promise<Result<void>>;
  expireLearnings(now: string): Promise<{ expired: number }>;       // after expires_at; only confirmation extends
  exportLearnings(scope: { repo?: RepoRef; org?: string }, format: "csv" | "json"): Promise<Result<string>>;
  importLearnings(data: Untrusted, format: "csv" | "json" | "coderabbit_csv", actor: Actor): Promise<Result<{ imported: number; rejected: number }>>;  // only those with write access
}
interface Learning { id: string; kind: "repo_fact" | "user_pref"; scope: "repo" | "org" | "auto"; text: string; source: Citation;
                     prRef?: ChangeRef; expiresAt: string; votes: number; uses: number; lastUsed?: string; invalidAt?: string }
```

The platform MCP additionally offers the tool `kb.ask` (ask flow in [02](02-services.md) section 7).

Implementations: `pg-kb` (default, Postgres with pgvector in the control plane), `sqlite-artifact` (one artifact per repo for installations without a central DB). Layers L0 to L5 as in [02](02-services.md) section 7. Rules never live in the DB, but versioned in the repo.

## 10. Notifier

```ts
type NotifyCap = "THREADS" | "INTERACTIVE_APPROVAL" | "DM" | "MENTION";
interface Notifier extends PluginBase<NotifyCap> {
  send(to: Audience, msg: { title: string; md: string; runId: string; links: Link[];
        kind: "approval_needed" | "run_failed" | "budget_warning" | "done" | "plugin_unhealthy" | "driver_unhealthy"
            | "alert" | "report";   // alert: required alarms (06 section 4); report: scheduled report (stage 6)
        severity: "info" | "action" | "alert" }, idempotencyKey: string): Promise<Result<MessageRef>>;
  update(ref: MessageRef, md: string): Promise<Result<void>>;
  requestApproval?(to: Audience, req: { gate: "G1" | "G4" | "G5"; runId: string; expiresAt: string }): Promise<Result<MessageRef>>;  // click via signed callback
}
```

Default is `comment-on-source` (comment on the ticket or PR, no additional account). Teams, Slack and email follow as needed. Notifier messages also go through the Effect Gateway.

## 11. Provider matrices

Legend: B = VERIFIED, G = CLAIMED, A = DERIVED, V = ASSUMED, ? = unverified.

### 11.1 Inputs (TriggerSource and WorkItemProvider)

| Capability | GitHub Issues/PRs | Jira Cloud | Jira DC | GitLab | Linear | Azure DevOps | Bitbucket Cloud | Gitea/Forgejo |
|---|---|---|---|---|---|---|---|---|
| Signed webhook | HMAC `X-Hub-Signature-256` (B) | HMAC (admin webhook), JWT (app webhook) (B) | HMAC in 11.x (G, version ?) | plain-text token; Standard Webhooks signature from 19.0 (B) | yes (G), header ? | no HMAC; Basic Auth or header (B) | HMAC-sha256 (B) | HMAC-sha256 (B) |
| Redelivery | no, `reconcile` required (B) | up to 5 retries, unordered (B) | ? | yes, disabled after failures (B) | ? | ? | ? | ? |
| Response deadline | 10 s (B) | ? | ? | ? | 5 s, activity within 10 s (B) | ? | ? | ? |
| Native bot mention | text (B, OpenHands) | ADF `mention` with `userType: APP`, Forge `avi:jira:mentioned:comment` (B) | text (A) | service account, Duo trigger only Premium/Ultimate (B) | AgentSession `created`/`prompted` (B) | text (A) | text (A) | text (A) |
| Delegation to agents | assignment to bot (V) | assignment to service account (V) | assignment (V) | assign trigger (B) | `delegate` (B) | ? | ? | ? |
| Rich text | Markdown | ADF (B) | wiki markup (V) | Markdown | Markdown (V) | Markdown (V) | Markdown | Markdown |
| Set status | open/closed plus labels (A) | transitions (V) | transitions (V) | open/closed plus labels (A) | status category `started` (B) | work item state (V) | not applicable | open/closed (A) |
| Link PR | cross-reference, `Closes #n` (V) | dev info only app/Forge (B), otherwise remote link (?) | remote link (V) | `Closes #n` (V) | `externalUrls` (B) | ? | not applicable | `Closes #n` (V) |
| Agent session, plan | no | no; Rovo only as an input, without model choice (B) | no | no | yes (B) | no | no | no |
| Input without own webhook | Actions event (B) | automation relay (B), JQL polling (A) | polling (A) | pipeline trigger (V) | no (B) | polling (A) | polling (A) | polling (A) |
| `SET_LABELS` | yes (A, as 11.2) | labels field (V) | labels field (V) | yes (A) | yes (V) | tags (V) | not applicable | yes (A) |
| `CREATE_ISSUE` | yes (V) | yes (V) | yes (V) | yes (V) | yes (V) | yes (V) | not applicable | yes (V) |
| `LINK_ITEMS` | cross-reference in text (V) | issue links with type (V) | issue links (V) | linked issues (V) | relations (V) | work item links (V) | not applicable | cross-reference (V) |
| `CLOSE_AS_DUPLICATE` | close reason "duplicate" (?) | resolution "Duplicate" per workflow (V) | like Cloud (V) | quick action `/duplicate` (V) | duplicate relation (V) | ? | not applicable | ? |
| `RELATED_SEARCH` | ? | ? | ? | ? | ? | ? | not applicable | ? |

The five new rows are a plan, not evidence: they are verified with the contract suite of the respective plugin, for GitHub in stage 7 (service `triage`), for the others with the plugin itself (stages 8 and 9). If `RELATED_SEARCH` is missing, `triage` uses the fallback chain from section 5.

Sources: [gh-webhooks], [gh-events], [jira-webhooks], [jira-automation], [forge-events], [forge-trigger], [rovo], [adf], [jira-devinfo], [jira-dc], [gl-webhooks], [gl-duo], [linear-agents], [ado-webhooks], [bb-webhooks], [gitea], [forgejo], [oh-cloud].

### 11.2 Code hosting (SCMProvider)

| Capability | GitHub | GitLab | Bitbucket Cloud | Bitbucket DC | Azure DevOps | Gitea/Forgejo |
|---|---|---|---|---|---|---|
| `BATCH_REVIEW` | yes (B) | draft notes plus `bulk_publish` (B) | no according to PR-Agent (B) | ? | no (B) | yes (B) |
| `REVIEW_REQUEST_CHANGES` | yes (B) | only Premium/Ultimate (B) | yes (B) | ? | vote (V) | yes, "rejected" (B) |
| `SUGGESTION_BLOCK` | yes (V) | `suggestion:-0+N` (B) | no (V) | no (V) | no (V) | ? |
| `THREAD_RESOLVE` | GraphQL (B) | yes (B) | ? | ? | thread status (B) | ? |
| `CHECK_ANNOTATIONS` | yes, 50 per request, apps only (B) | no; code quality in the diff only Ultimate (B) | Code Insights, 1000 per report (B) | Code Insights (V) | no, only PR status (B) | no (V) |
| `CHECK_ACTIONS` | 3 buttons (B) | no (A) | no (V) | no (V) | no (V) | no (V) |
| `LABELS` | yes | yes | no (B) | no (B) | tags (V) | yes |
| `SCOPED_SHORT_TOKEN` | 1 h, repos and permissions (B) | no, project access token up to 365 days, GitLab.com from Premium (B) | ? | ? | ? | ? |
| `WEBHOOK_HMAC` | yes (B) | from 19.0 (B) | yes (B) | yes (B) | no (B) | yes (B) |
| `SET_LABELS` | yes (A, like `LABELS`) | yes (A) | no (B, like `LABELS`) | no (B) | tags (V) | yes (A) |
| `REQUEST_REVIEWERS` | yes (V) | set reviewers (V) | yes (V) | yes (V) | yes (V) | yes (V) |
| `CODE_SCANNING_READ` | code scanning alerts (B according to [`ebene-statische-analyse-und-security`](../research/ebene-statische-analyse-und-security.md) 2.4) | SAST report as an artifact, MR display only from Ultimate (B, ibid. 2.3) | ? | ? | ? | ? |
| `CODE_SCANNING_UPLOAD` | SARIF 2.1.0, private repos only with Code Security (B [gh-sarif]) | artifact only (B, ibid.) | ? | ? | ? | ? |

Sources: [gh-checks], [gh-reviews], [gh-insttoken], [gl-draftnotes], [gl-reviews], [gl-commits], [gl-statuschecks], [gl-codequality], [gl-pat], [bb-insights], [ado-threads], [ado-status], [pr-agent] (`gitlab_provider.py:719-721,1817,1971`, `bitbucket_provider.py:374-379`, `bitbucket_server_provider.py:214-217`).

### 11.3 AgentRuntime

| Capability | Claude Code | Codex | OpenCode | Gemini CLI | OpenHands SDK | Goose | ACP generic |
|---|---|---|---|---|---|---|---|
| Native tools lockable | B (managed settings) | B (sandbox modes) | B (Pullfrog) | ? | B | ? | ? |
| Built-in sandbox | B (shell only) | B | ? | ? (docs mention sandboxing) | B (Docker, remote) | ? | no |
| MCP for platform tools | B | B | B | B | B | B | B (MCP types) |
| Subagents with gate | B (PreToolUse) | no (A) | B | ? | ? | ? | ? |
| Structured output | B `--json-schema` | B `--output-schema` | ? | not documented | ? | ? | ? |
| Cache tokens visible | B | B `cached_input_tokens` | ? | ? | B | ? | ? |
| Cost in USD | B (estimate, "not a billing statement") | no, price table (A) | ? | no (A) | B (`Metrics`) | ? | ? |
| Limits readable | with API key via headers B; subscription only reactive (`rate_limit_event`) B | ? | ? | ? | via provider | ? | ? |
| Budget abort during the run | B `maxBudgetUsd`, `maxTurns` | ? | ? | B turn limit, exit 53 | ? | ? | no |
| Credential kinds | subscription, API, WIF, Bedrock, Vertex, Foundry, gateway, Claude Platform on AWS | API, ChatGPT, enterprise token, Azure (G), Bedrock (OpenAI models only) | more than 75 providers, ChatGPT | API key, Vertex, Google login | LiteLLM | many | per agent |
| License, `distribution` | proprietary, only `operator_supplied` (B [cc-npm]) | Apache-2.0 (B [codex-repo]) | ? | Apache-2.0 (B, npm registry according to [`open-source-lizenz-und-recht`](../research/open-source-lizenz-und-recht.md) 2.3) | MIT (B [oh-sdk-repo]) | Apache-2.0 (B, ibid. 2.2) | ? |

Sources: [cc-auth], [cc-headless], [cc-sdk-ts], [cc-features], [codex-auth], [codex-exec], [codex-azure], [codex-repo], [cc-npm], [opencode], [gemini-auth], [gemini-headless], [openhands-sdk], [oh-sdk-repo], [goose], [acp], [pullfrog].

### 11.4 ModelProvider and credential paths for Claude Code

The column "Terms of use" gives the reading of the original texts with their location, not legal advice. Basis: [`open-source-lizenz-und-recht`](../research/open-source-lizenz-und-recht.md) sections 2.5 and 2.8 with the corrections from [`gegenpruefung-lizenz-und-recht`](../research/gegenpruefung-lizenz-und-recht.md) (the cross-check takes precedence).

| Provider | Configuration in Claude Code | Structured output | Caching | Cost measurement | Limits readable | EU data path | Terms of use |
|---|---|---|---|---|---|---|---|
| **Local Claude Code with subscription (OAuth)**, kind `subscription` | `claude setup-token` by the operator, token in a host file readable only by the worker user, the worker sets it per item as `CLAUDE_CODE_OAUTH_TOKEN` in the environment of the `claude` process (section 6, ADR-57); `/login` is not a start path; token one year, "only model requests" (B [cc-auth]); no `--bare`, only services without a shell except profile `operator_test` (section 6); single calls via the ModelProvider `claude-cli` (section 7, ADR-58) | B via CLI | B | tokens only; `total_cost_usd` is an estimate (B [cc-sdk-ts]) | only reactive; `rate_limits` is `null` without scope `user:profile` (B [cc-sdk-ts]) | like Anthropic API (A) | Personal operator mode, locked by default (ADR-51). [cc-legal] B: OAuth "is intended exclusively for purchasers of Claude Free, Pro, Max, Ultra, Team, and Enterprise subscription plans and is designed to support ordinary use of Claude Code"; "Developers building products or services that interact with Claude's capabilities, including those using the Agent SDK, should use API key authentication"; still allowed is that "an end user [signs] in to the unmodified Claude Code binary with their own Claude subscription, including where a platform hosts Claude Code". [an-consumer] B (EEA version, applies to consumers only): §3 automated access only "via an Anthropic API Key" or with express permission, §11 "Non-commercial use only". Reading (A): the operator's own runs in the unmodified binary are covered; runs for other people are not; autonomous continuous operation is a gray area (O2) |
| **Claude API (Anthropic 1P)**, kinds `api_key`, `wif` | `ANTHROPIC_API_KEY` or WIF (B [an-wif]), both via the credential relay with `--bare` (section 6); `--bare` reads no federation variables (B [cc-auth]) | B (`output_config.format`, `strict`) [an-structured] | B | tokens; workspace spend limit (B [an-ratelimits]) | B (`anthropic-ratelimit-*`) | no: `inference_geo` only knows `global` and `us`, workspace geo only `us` (B [an-residency]) | [an-commercial] (Commercial Terms) B; [cc-legal] B: "Customers may not pay for, resell, or intermediate Claude usage on their end users' behalf"; own keys "for use by the customer's own authorized users" are fine. Monthly API credit in Max (100 USD), Ultra (200 USD) and Team (per seat, capped at 500 USD), "Doesn't roll over", Free, Pro and Enterprise excluded (B [cc-credits]) |
| **AWS Bedrock**, kind `bedrock` | `CLAUDE_CODE_USE_BEDROCK`, `ANTHROPIC_BEDROCK_REGION_PREFIX=eu` (B [cc-features], [cc-bedrock]) | B | B, "may not be available in all regions" (B) | tokens; billing via AWS | ? (Service Quotas, V) | B (`eu.` profiles); region via endpoint or inference profile (B [an-residency]) | Terms of AWS and for Anthropic models there: unverified |
| **Google Vertex**, kind `vertex` | `CLAUDE_CODE_USE_VERTEX`, `CLOUD_ML_REGION` (B [cc-features]) | B | ? | tokens | ? | region via the endpoint (B [an-residency]); whether EU regions are offered for Claude: unverified | Google Cloud terms: unverified |
| **Microsoft Foundry (Azure)**, kind `foundry` | `CLAUDE_CODE_USE_FOUNDRY`, `ANTHROPIC_FOUNDRY_RESOURCE` (B [cc-features]) | B | ? | tokens | ? | `inference_geo` not applicable; only the US Data Zone is documented (B [an-residency]); an EU zone is not verified | Azure terms: unverified |
| **Claude Platform on AWS** | `CLAUDE_CODE_USE_ANTHROPIC_AWS` (B [cc-features]) | B | B | via AWS Marketplace | B | no: `inference_geo` only `global` or `us`, workspace geo fixed `us` (B [an-residency]) | unverified |
| **LLM gateway / Claude apps gateway**, kind `gateway` | `ANTHROPIC_BASE_URL` plus `ANTHROPIC_AUTH_TOKEN`; apps gateway with SSO, RBAC per IdP group, needs Postgres (B [cc-gateway], [cc-appsgw]) | like upstream | like upstream | like upstream | like upstream | like upstream | like upstream |
| **OpenAI API / Codex**, kind `openai` | harness `codex`, API key recommended for automation (B [codex-auth]) | B `--output-schema` | B | tokens only; project spend limit (B [openai-rl]) | B `x-ratelimit-*` | ? | [codex-auth] B: "Use API key authentication for programmatic Codex CLI workflows, such as CI/CD jobs. Don't expose Codex execution in untrusted or public environments." OpenAI Terms of Use: not checkable (HTTP 403) |
| **ChatGPT account (Codex)**, kind `chatgpt` | login in the unmodified Codex CLI on the worker host (section 6) | like Codex | like Codex | tokens only | ? | ? | Personal operator mode, locked by default (ADR-51). [codex-auth] B: access tokens only in ChatGPT Enterprise workspaces, "intended for trusted scripts, schedulers, and private CI runners"; `~/.codex/auth.json` "contains access tokens. Don't commit it, paste it into tickets, or share it in chat." |
| **Azure OpenAI**, kind `azure_openai` | Codex `[model_providers.azure]` with `wire_api="responses"` (G [codex-azure]) | ? | ? | ? | ? | ? | unverified |
| **Gemini API / Vertex Gemini** | harness `gemini-cli` or ModelProvider; Google OAuth in third-party software prohibited (B [gemini-tos]) | ? | B implicit from 2.5 [gemini-cache] | tokens | ? | ? | [gemini-tos] B: access to the services behind Gemini CLI "using third-party software, tools, or services ... is a violation of applicable terms and policies"; for pipelines API key or Vertex |
| **OpenRouter** | ModelProvider | ? | B | B `usage.cost` [openrouter] | ? | ? | unverified |

**Non-compete clauses:** Consumer Terms §3 ("develop any products or services that compete with our Services") and Commercial Terms D.4 contain a non-compete clause ([an-consumer], [an-commercial] B). Whether a review or agent product on Claude falls under it is open and affects every Anthropic credential kind, including API keys ([`open-source-lizenz-und-recht`](../research/open-source-lizenz-und-recht.md) section 5). Only Anthropic can clarify this.

Important: Anthropic explicitly does not support "routing Claude Code to non-Claude models through any gateway" ([cc-gateway], VERIFIED); LiteLLM claims the opposite ([litellm], CLAIMED). The Anthropic source applies: non-Claude models run via the harnesses `codex`, `opencode` or `gemini-cli`.

### 11.5 Gaps per provider (and what the platform does about them)

| Provider | Gap | Consequence in the architecture |
|---|---|---|
| GitHub | no redelivery of missed webhooks; secondary rate limits with fast reviews (B) | `reconcile` required; one review per run (batch) |
| GitLab | no line-accurate checks below Ultimate, no short-lived token, HMAC only from 19.0, request changes only Premium/Ultimate (B) | fallback chains; token level "weak" with rotation; signature level `weak` with shared secret, IP allowlist and fresh re-reading |
| Bitbucket | no labels, no batch inline according to PR-Agent; merge blocking through Code Insights unverified | fallback chains; labels as comment markers |
| Azure DevOps | no HMAC signature, no batch review, no annotations (B); votes via API unverified | signature level `weak`; summary plus PR status |
| Gitea/Forgejo | no checks with annotations (V); thread resolving unverified | commit status plus summary |
| Jira Cloud | Forge up to 3 min delay, unordered webhooks, app webhooks expire after 30 days, dev panel only for apps, ADF when writing (B) | re-read fresh, `renew`, ADF rendering in the adapter, remote link as fallback |
| Linear | response within 5 s required, needs a public inbound path (B); signature and stop signal unverified | only with public ingress (stage 9) |
| Claude subscription | limits only reactive, no `--bare`, token with a one-year lifetime is in the sandbox, no direct API path for single calls, terms of use limit multi-user operation (B [cc-auth], [cc-legal]) | personal operator mode, locked by default (ADR-51); token only from the worker user's host file (ADR-57); single calls via `claude-cli` with capability level `fallback` (ADR-58); only `self-hosted` with one operator, only services without a shell except profile `operator_test`, [05](05-security.md) sections 3 and 6 |
| Claude API via WIF | `--bare` reads no federation variables (B [cc-auth]) | exchange in the worker, access token only in the credential relay (section 6) |
| Bedrock | no web search, no fast mode, no advisor; caching regionally restricted (B [cc-features]) | capability `none`; eval per provider |
| Foundry | tool search does not work when hosting on Azure (B [cc-features]); only the US Data Zone is documented (B [an-residency]) | the data path policy does not allow Foundry for `eu` as long as no EU zone is verified |
| Codex | no USD cost, no pre-tool hook (B/A) | cost via price table, subagents off |
| Gemini CLI | replaced by Antigravity CLI for the unpaid tier and Google One (2026-06-18); Google OAuth in third-party software prohibited (B [gemini-auth], [gemini-tos]) | only API key or Vertex service account; free tiers only via an adapter for Antigravity CLI (unverified, section 6) |
| LiteLLM proxy | without Postgres "fails open"; budgets per model only Enterprise (B [litellm]) | not the source of truth; own limit ledger |

## 12. Analyzer (third-party tools, ADR-40)

**Purpose:** Connect deterministic tools (SAST, dependencies, secrets, IaC, accessibility, cost, dependency updates) uniformly instead of naming them hard-coded in service texts. We do not build our own analysis engine; the value lies in the AI layer on top (verifier, fix with re-scan), see [`ebene-statische-analyse-und-security`](../research/ebene-statische-analyse-und-security.md) sections 1 and 3.2. The normal form of all results is SARIF 2.1.0 ([sarif] VERIFIED), because reviewer, coder self-check, QA and PR fixer read the same form and the hosts accept it ([gh-sarif] VERIFIED).

```ts
type AnalyzerCap = "SARIF_NATIVE" | "FINGERPRINT" | "BASELINE" | "TAINT_INTERFILE" | "AUTOFIX" | "QUALITY_GATE" | "INGEST";

interface AnalyzerManifestExt {        // addition to the PluginManifest for kind "Analyzer"
  image: string;                       // digest, not tag
  rulesLicense?: string;               // SPDX or "LicenseRef-...", separate from the engine license
  languages: string[]; filePatterns: string[];
  runsRepoCode: boolean;               // true: executes code of the repo (build, plugins), then isolation like build and tests
  needsBuild: boolean; offline: boolean;   // offline: runs without network (rules in the image)
  cost: "free" | "byo_license";        // byo_license: the operator brings their own license or their own account
}

interface Analyzer extends PluginBase<AnalyzerCap> {
  describe(): { languages: string[]; filePatterns: string[]; output: "sarif-2.1.0"; network: "none" | "allowlist";
                cost: "free" | "byo_license"; typicalWallMs?: number };
  // Run always in a sandbox (ExecutionBackend), never in the control plane process
  run(sb: SandboxHandle, req: { scope: "diff" | "full"; baseSha: string; headSha: string; paths?: string[];
      config: unknown }): Promise<Result<AnalyzerReport>>;
  // Read results from outside: SARIF from a CI artifact, the host's code scanning, quality gate webhook
  ingest?(src: { kind: "ci_artifact" | "scm_code_scanning" | "webhook"; ref: string; headSha: string }): Promise<Result<AnalyzerReport>>;
}
interface AnalyzerReport {
  sarifRef: string;                    // SARIF 2.1.0 in the BlobStore
  findings: AnalyzerFinding[]; toolVersion: string; rulesHash: string;
  gate?: { status: "passed" | "failed" | "neutral"; revision: string; reason?: string };  // revision not equal to headSha yields neutral
}
interface AnalyzerFinding {
  ruleId: string; path: string; lines: [number, number]; level: "error" | "warning" | "note";
  securitySeverity?: number; cwe: string[]; fingerprint: string;          // if missing, the platform computes it from rule, path, normalized line
  baselineState: "new" | "unchanged" | "absent"; message: Untrusted; fix?: Untrusted;
  llmUse: "allowed" | "forbidden";     // forbidden: deterministic gate only, never into a prompt
}
```

**Rules:**
1. **Sandbox required:** Every `run` runs in a sandbox with an egress allowlist; with `runsRepoCode: true` with the same minimum isolation as build and tests (section 8). Configuration and rules come from the base SHA, never from the PR ([05](05-security.md) section 3).
2. **Baseline by the platform:** The platform sets `baselineState` by analyzing base and head with the same pinned version or by using a stored base analysis; a stored base is only valid with the same `toolVersion` and `rulesHash`.
3. **Foreign text is `Untrusted`:** SARIF messages and fix suggestions of third-party tools are treated like ticket text ([05](05-security.md) section 4).
4. **No silent green:** A crash, timeout or a report without the required SARIF fields yields `neutral` with a reason, never `passed`.
5. **License:** `distribution: bundled` only if the engine license and `rulesLicense` are on the allowlist (rule 7, ADR-50). The operator sets `llmUse: forbidden` for sources whose license excludes processing by AI (example SonarQube, see table).
6. **Extensions:** Cost diffs (Infracost) and documentation gaps do not fit into SARIF without an extension; they go into the `properties` bag with their own schema, draft in stage 2 ([`ebenen-landkarte`](../research/ebenen-landkarte.md) section 5 item 6).

Contract `v1alpha1` binding from stage 2, because the coder's self-check bundle is the first to need it.

**Distribution and license situation (ADR-50):**

| Tool | License | `distribution` | Role | Stage | Evidence |
|---|---|---|---|---|---|
| Opengrep (engine) | LGPL-2.1 | `bundled`, only with the project's own rules | rule SAST | 2 | [opengrep], license situation [`ebene-statische-analyse-und-security`](../research/ebene-statische-analyse-und-security.md) 2.3 and 2.4 |
| Opengrep rule collection | Commons Clause on LGPL-2.1; selling is prohibited | `operator_supplied` (Commons Clause is not on the allowlist) | rules | | [opengrep-rules] B, clarification according to cross-check item 24 |
| Semgrep CE (engine) | LGPL-2.1 | `bundled` possible | rule SAST | 2 | ibid. 2.3 |
| Semgrep registry rules | Semgrep Rules License: only "for your own internal business purposes" | never `bundled`; the operator may include them for themselves | rules | | [semgrep-rules] B |
| osv-scanner | Apache-2.0 | `bundled` | dependencies | 2 | ibid. 2.3 |
| gitleaks | MIT | `bundled` | secrets | 2 | ibid. 2.3 |
| Trivy | Apache-2.0 | `bundled` | dependencies, IaC, containers | 2 | ibid. 2.3 |
| axe-core | MPL-2.0 | `bundled` | accessibility in the QA E2E stage | 10 | [`ebenen-landkarte`](../research/ebenen-landkarte.md) section 2.2 (E18) |
| Infracost | Apache-2.0; whether the pricing data needs an account: unverified | `bundled`, `cost` unverified | cost diff for IaC | 10 | ibid. 2.2 (E19) |
| Renovate (diff mode) | AGPL-3.0 | `operator_supplied` (AGPL in its own container: legal assessment open) | dependency updates | 10 | ibid. 2.2 and owner item 4.3 |
| CodeQL | CLI under GitHub CodeQL Terms, no hosting for others | never `bundled`, never executed by the platform; only results via `CODE_SCANNING_READ` | SAST | | [codeql-lic] B |
| SonarQube (Server, Cloud, Community Build) | AUP with non-compete and AI clauses; SSALv1 for the analyzers of the Community Build | never `bundled`; at most SARIF or webhook import for which the operator is responsible, with `llmUse: forbidden` | quality gate | | [sonar-aup] §5 and §6, [ssal] (c) B; reading, not legal advice |

## 13. Drivers for the base (ADR-41)

**Purpose:** Storage, secrets and cloud identity depend on the base an installation runs on (own machine, Azure, AWS, Google Cloud, Hetzner), not on a third-party system of the domain logic. Therefore they are not a plugin kind but a separate class **driver** with the same framework as section 1.1 (manifest with `license` and `distribution`, capabilities, contract suite as load condition, two major versions), but counted separately. Basis: [`hosting-und-installation`](../research/hosting-und-installation.md) section 3.1.

```ts
type DriverKind = "BlobStore" | "SecretStore" | "CloudIdentity";

type BlobCap = "PRESIGN" | "VERSIONING" | "OBJECT_LOCK" | "SSE_KMS";
interface BlobStore extends PluginBase<BlobCap> {
  put(key: string, data: Uint8Array | AsyncIterable<Uint8Array>, opts?: { contentType?: string; retainUntil?: string }): Promise<Result<{ etag: string }>>;
  get(key: string): Promise<Result<AsyncIterable<Uint8Array> | null>>;
  delete(key: string): Promise<Result<void>>;       // with OBJECT_LOCK before retainUntil: error "permission"
  list(prefix: string, cursor?: string): Promise<Result<Page<{ key: string; size: number; etag: string }>>>;
  presignPut?(key: string, ttlS: number): Promise<Result<string>>;    // PRESIGN; without: upload via the work API
  presignGet?(key: string, ttlS: number): Promise<Result<string>>;
}

type SecretCap = "WRITE" | "SIGN" | "ROTATION_EVENT";
interface SecretStore extends PluginBase<SecretCap> {
  get(ref: SecretRef): Promise<Result<{ value: SecretValue; version: string }>>;
  put?(ref: SecretRef, value: SecretValue): Promise<Result<{ version: string }>>;           // WRITE
  sign?(keyRef: SecretRef, payload: Uint8Array, alg: "ES256" | "RS256"): Promise<Result<Uint8Array>>;  // SIGN: the key never leaves the store (OIDC issuer, audit anchor)
}

type IdentityCap = "AMBIENT" | "SELF_ISSUER";
interface CloudIdentity extends PluginBase<IdentityCap> {
  ambientToken(audience: string): Promise<Result<{ jwt: string; exp: string }>>;   // identity of the base (managed identity, IRSA, workload identity, projected token) or own issuer
  exchange(target: "anthropic_wif" | "aws_sts" | "gcp_sts" | "entra", req: { audience: string; ttlS: number }): Promise<Result<{ credential: SecretValue; exp: string }>>;
}
```

**Implementations per stage:**

| Driver kind | cloud-free default | Stage 0 | Stage 8 | later |
|---|---|---|---|---|
| `BlobStore` | `fs` (directory, for one machine) | `fs`, `s3` (any S3-compatible service, SeaweedFS in the Compose bundle, never MinIO, ADR-43), `azure-blob` | | `gcs` |
| `SecretStore` | `file` (encrypted file) | `file`, `env` (read only), `azure-keyvault` | | `aws-secretsmanager`, `gcp-secretmanager`, `openbao` |
| `CloudIdentity` | `self-issuer` (control plane as OIDC issuer with key in the `SecretStore`, ADR-22) | `self-issuer` | `azure-managed-identity` (with WIF and Foundry) | `aws` (IRSA, Pod Identity), `gcp` (Workload Identity), `k8s-projected-token` |

In stage 0 (sub-stage 0b), `azure-keyvault` authenticates with the host's identity via the Azure SDK's default credential chain (DERIVED); the platform needs `CloudIdentity` only for the exchange for LLM credentials in stage 8.

**Contract suite (load condition as in rule 1):** `BlobStore` against SeaweedFS and Garage as containers, `azure-blob` against the Azurite emulator (whether it covers all capabilities: unverified) and against recorded real responses; `SecretStore` against `file` and an OpenBao container, cloud drivers against recorded responses; `CloudIdentity` with a test issuer and recorded exchange responses. Every suite also checks the failure paths: expired presign URL, deletion under object lock, unknown secret version, rejected exchange. Runs in the project's CI on every PR touching the driver ([`hosting-und-installation`](../research/hosting-und-installation.md) section 3.8).

**Rules:**
1. **Runnable without a cloud:** Every installation runs with `fs`, `file` and `self-issuer` without an account at a cloud provider. Cloud drivers are add-ons.
2. **Audit daily anchor:** The core writes the daily anchor of the audit hash chain ([05](05-security.md) section 8) either into a `BlobStore` with `OBJECT_LOCK` or via `SCMProvider` as a commit into a repo of the operator. Without one of the two, `doctor` reports the audit chain as "not anchored". This is a core function, not a separate driver.
3. **Deliberately no driver for:** queue and workflow control (stays Postgres with pg-boss, ADR-04; a queue port invites a second state store, ADR-02), database (only PostgreSQL with pgvector, managed or bundled is configuration), ingress, TLS and OTel (standards, configuration). The admin UI authenticates via a generic OIDC client, plus an emergency admin; this is not a plugin.
4. Choice and configuration of the drivers are in the installation configuration ([11](11-installation-and-hosting.md)).

## 14. Third-party services: service manifest

**Purpose:** An operator or vendor attaches their own services without changing the core (owner requirement 4). The structure of a service (manifest, controller, jobs, [02](02-services.md) section 0) becomes a published contract for this, with the same versioning as plugins (rule 6) and the same load condition (contract suite).

```ts
interface ServiceManifest {
  apiVersion: ApiVersion; kind: "Service";
  id: ServiceId;                       // third parties always "<vendor>/<name>"; the ten built-in names are reserved
  version: string; license: string; distribution: "bundled" | "operator_supplied";
  trust: "first_party" | "vetted" | "third_party";
  controller: { transport: "in_process" | "subprocess_grpc" | "http"; image?: string };   // third_party never in_process
  commands: { name: string; minPermission: PermissionLevel; args?: JSONSchema }[];       // must not override any built-in CommandName
  subscribes: { subject: TriggerEvent["what"]["subject"]; action: TriggerEvent["what"]["action"]; filter?: string }[];  // filter in JMESPath
  inputSchema: JSONSchema; outputSchema: JSONSchema;
  requires: { plugin: PluginKind; caps: string[]; level: "native" | "fallback" }[];      // if a capability is missing: service off for this instance
  effects: string[];                   // allowed write requests, deny by default as in [02] section 0
  jobs: { nativeTools: AgentTask["nativeTools"]; minIsolation: Isolation; egress: string[]; analyzers?: string[] }[];
  platformMcpTools: string[];          // read tools the jobs may use
  qualification: { evalSuite: string; gateA: boolean; gateB?: { reference: string } };   // for live, ADR-47
  configSchema: JSONSchema;
  contractSuite: { version: string; passedAt: string; fixturesHash: string };
}
```

**Rules:**
1. **Same boundaries as built-in services:** A third-party service never writes to the outside itself, only via write requests from `effects`, which policy and Effect Gateway check. It receives no SCM token, no LLM credentials and no access to the database; reading only works via the platform MCP with an item token. Its jobs run as work items in sandboxes with `minIsolation` at least according to the repo class (section 8).
2. **On, off, shadow like built-in services:** `mode: off | shadow | live` per configuration layer. `live` requires Gate A and Gate B from `qualification` or an adopted reference qualification; without that only via operator configuration with the visible label "standard not proven" (ADR-47, [10](10-standards-per-layer.md)).
3. **Registration:** The operator enters the manifest into the installation configuration; on load the core checks schema, namespace, command collisions, `requires` against the available plugins and the contract suite. An error rejects only this service, not the installation.
4. **Template:** The project ships an example service package with a contract suite as a template for third parties ([12](12-open-source-and-project.md)); timing in [08](08-roadmap.md) stage 9 (third-party plugins).
