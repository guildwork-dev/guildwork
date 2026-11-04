<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# 04 Configuration and limits

Source keys and classifications as in the [README](README.md). All numbers in the examples are **starting values (estimate)**; fixed values are set by the expansion stage of the respective service after measurement ([08](08-roadmap.md)). All names in the examples are neutral (`example-org`, `example.atlassian.net`, `<org>/<repo>`). The examples do not show every key; the complete reference is the published JSON Schema (section 7), further keys per service are in [02](02-services.md).

## 1. Hierarchy

```
Platform defaults (in code, versioned)
  -> Installation (installation.yaml, section 7; admin UI)
    -> Org (central repo, e.g. <org>/.agents-platform: org.yaml)
      -> Repo group (custom property or topic, e.g. data_class=pci)
        -> Repo (.agents/config.yaml, read at the base SHA)
          -> Path globs (rules, path_instructions, protected_paths)
    -> Service layer (per service within each layer)
    -> User (only preferences and tighter personal limits)
Platform overrides (table repo_overrides, only tightening, applied last)
```

**Inheritance rules:**
1. **Only tightening** apply to: limits, permissions (`min_permission`), autonomy, provider allowlist, data path (`allowed_regions`), `forbidden_paths`, `protected_paths`, `merge`, analyzer allowlist, pools and minimum isolation. An inner layer may lower, block or select, never loosen. The upper bounds for autonomy and merge are set by the installation (`max_autonomy`, `merge.max_mode`); the platform default is `medium` and `human` respectively, the installation may raise them up to `full` and `auto` respectively. Org, repo group and repo choose below that, never above.
2. **Normally overridable** are: prompts, `path_instructions`, profile (`chill`, `assertive`), language, notifications, selection of a provider **within** the allowed list.
3. **Services:** `mode` per layer; the org can pin a service for all inner layers with `lock: true`. `live` requires Gate A and Gate B or an adopted reference qualification ([07](07-eval.md), ADR-47), otherwise the service runs `shadow`. Only the operator may deviate, with `qualification.allow_unproven_live` in the installation (section 7); the org may only shorten this list.
4. **Validation, fail closed (ADR-65):** the field `version` is required; JSON Schema (section 7); unknown keys are an error. If an org, repo group or repo file is invalid (typo, schema error, key unknown after an upgrade), the last valid version of this file continues to apply to the affected repos (the resolver stores the last valid version per file with its SHA; every snapshot under rule 5 records the fallback). If there is none, the strictest level applies: all services at most `shadow`, `merge.mode: human`, `autonomy: low`. Both apply until a valid file is present at the base SHA, with a visible notice on the PR or ticket and in the admin UI. The layer is never silently omitted, because it is precisely the one that carries the tightenings (rule 1, for example `protected_paths`). Test in S2.
5. **Snapshot:** every run stores the effective configuration with a hash (`config_snapshots`), plus, for each participating service, the qualification profile with `qualification_key` ([07](07-eval.md) section 2, ADR-66). Running runs do not change when the configuration changes.
6. **User layer:** only language, notification and tighter personal limits.
7. **Platform overrides:** the table `repo_overrides` in the control plane holds platform-side tightenings per repo, for example `merge.mode: human` after a red target branch ([03](03-flow-and-orchestration.md) section 1a, post-merge follow-up) or a service set to `shadow` after an incident. The resolver applies them after all layers and only as tightening; it rejects a loosening through an override. Writers are the orchestrator (only the defined fallbacks) and admins in the admin UI; every change is in the audit. Reason: the repo file applies at the base SHA and would otherwise cancel a fallback on the next run.
8. **Personal credential kinds:** `credential.kind: subscription` and `chatgpt` are blocked in the platform default. Only the installation unlocks them, per kind with `acknowledge_terms` (section 7, ADR-51). Org and repo cannot unlock them.

## 2. Base branch rule

- Configuration, rules (`.agents/rules/`), `AGENTS.md`, `REVIEW.md`, `CLAUDE.md`, third-party guideline files (list in [02](02-services.md), standards), path instructions and analyzer configuration are **always read from the base SHA**, never from the PR head.
- For ticket runs without a PR, the default branch HEAD at run start applies; the SHA is pinned in the snapshot.
- Reference project: Cursor Bugbot reads its configuration from the base branch ([cursor-bugbot] VERIFIED according to [`ebene-review`](../research/ebene-review.md) section 2). Counterexample: Copilot Code Review reads repo and agent instructions from the head branch ([copilot-instr] VERIFIED).
- If a PR changes configuration or rules, it gets a bot comment with the diff of the effective configuration. The change only takes effect after the merge.
- `.agents/**`, `.agents-platform/**` and CODEOWNERS are on the `forbidden_paths` of all agent services: an agent cannot change its own configuration. Exceptions: the standards service may change `.agents/rules/` only through its own rule PR, which only takes effect through CODEOWNERS; the coder may, in the `env_bootstrap` mode, propose exactly the file `.agents/environment.yaml` in its own draft PR ([02](02-services.md) section 0).

## 3. Complete example: org layer

```yaml
# <org>/.agents-platform/org.yaml (org layer), here example-org
version: 1
installation: example
org: example-org
# Upper bounds, pools, drivers and unlocks are in installation.yaml (section 7);
# for this example: max_autonomy: medium, merge.max_mode: human, pools self-hosted (on), ci-dispatch and cloud (off).

# ---------- Plugin instances ----------
plugins:
  scm:
    - { id: gh, plugin: github, instance: github.com/example-org,
        app_id_ref: secret://github-app/id, key_ref: secret://github-app/key }   # key only in the Credential Broker
  work_items:
    - { id: ghi, plugin: github-issues, scm: gh }
    - id: jira
      plugin: jira-cloud
      site: example.atlassian.net
      auth: { kind: service_account, ref: secret://jira/service-account }
      project_allowlist: [WEB, APP, OPS]          # example values
      status_mapping:                              # status category -> workflow status per project (example values)
        WEB: { started: "In Progress", in_review: "In Review", done: "Done", blocked: "Blocked" }
  triggers:
    - { id: gh-hook, plugin: github, mode: [webhook, reconcile] }           # ADR-08; alternative ci_event
    - { id: jira-in, plugin: jira-cloud, mode: [relay], verify: hmac_sha256_hex }  # Automation "Send web request"
  runtimes:                                        # harness x credential kind; version must match an entry in harness_pins of the installation, checksum and source are only there (detailed design 05 FE-521)
    - { id: cc-bedrock-eu, harness: claude-code, version: "pinned:<x.y.z>",
        credential: { kind: bedrock, region_prefix: eu, federation: oidc, role_ref: secret://aws/agents-role },
        region: eu }
    - { id: cc-api-wif, harness: claude-code, version: "pinned:<x.y.z>",
        credential: { kind: wif, workspace: agents-prod, token_lifetime: lease },   # exchange in the worker, token only in the credential relay
        start: bare_relay, region: global }                                      # --bare reads no federation variables (01 section 6)
    - { id: codex-api, harness: codex, version: "pinned:<x.y.z>",
        credential: { kind: openai, ref: secret://openai/agents }, region: global }
    # subscription and chatgpt are intentionally missing here: personal operator modes, not for an org (section 3a, ADR-51)
  models:                                          # ModelProvider for single calls; concrete IDs per installation
    - { id: small-eu,  plugin: bedrock, model: "eu.anthropic.<small-model>", region: eu }
    - { id: mid-eu,    plugin: bedrock, model: "eu.anthropic.<medium-model>", region: eu }
    - { id: large-eu,  plugin: bedrock, model: "eu.anthropic.<large-model>", region: eu }
    - { id: judge-alt, plugin: bedrock, model: "eu.anthropic.<model-other-than-system-under-test>", region: eu, use: [eval_judge] }   # own judge: a different Claude model than the system under test (O28)
  knowledge: { plugin: pg-kb }
  notifiers: [ { id: comments, plugin: comment-on-source } ]

# ---------- Analyzers (selection from the allowlist of the installation, section 7) ----------
analyzers:                                         # normal form SARIF 2.1.0, always runs in the sandbox (ADR-40)
  - { id: opengrep,    image: "<registry>/opengrep@sha256:<digest>",    license: LGPL-2.1-only, distribution: bundled,
      rules: ".agents/rules/opengrep/" }           # own rules; no Semgrep Registry rules (ADR-50)
  - { id: osv-scanner, image: "<registry>/osv-scanner@sha256:<digest>", license: Apache-2.0,    distribution: bundled }
  - { id: gitleaks,    image: "<registry>/gitleaks@sha256:<digest>",    license: MIT,           distribution: bundled }

# ---------- Data path (only tightening) ----------
data_policy:
  default: { allowed_regions: [eu] }               # example: EU data path (operator's choice)
  repo_classes:                                    # assignment via custom property data_class
    pci:        { allowed_regions: [eu], providers: [cc-bedrock-eu, small-eu, mid-eu, large-eu], services_off: [standards] }
    allow_global: { allowed_regions: [eu, global] }   # only repos for which the operator allows global
  embeddings: local                                # O7

# ---------- Ticket to repo ----------
repo_mapping:
  - { match: { source: jira, project: WEB, component: checkout }, repo: example-org/web-checkout }
  - { match: { source: jira, project: WEB }, repo: example-org/web }
  - { match: { source: jira, project: APP }, repo: example-org/app }
  - { match: { source: ghi }, repo: same }         # GitHub issue: repo of the issue
  fallback: ask                                    # links in the ticket, otherwise a question (awaiting_input)

# ---------- Services ----------
services:
  triage:    { mode: off, runtime: cc-bedrock-eu, model_hint: small,
               properties: { duplicates: suggest, labels: auto_apply, assignees: suggest, repo: suggest, spam: suggest },  # per property suggest | auto_apply | off
               spam_action: label,                 # label | hide_comment
               labeling_instructions: ".agents/rules/labels.md",   # instructions per repo (Linear pattern, 02 section 9)
               auto_close: false }                 # off by default (O25); repo opt-in only after green eval T1 (07)
  planner:   { mode: live,   runtime: cc-bedrock-eu, model_hint: large, gate_model: small-eu, lock: false, persist: none,   # none | branch
               approval: { auto_mode: shadow,      # shadow | live; live only after green S7 (c), until then the automatic approval is only measured
                           required_if: "autonomy in ['low', 'medium'] || !approval.auto_if",      # G1 human
                           auto_if: "plan.verified && plan.questions == 0 && plan.critique != 'blocked' && plan.risk != 'high' && !plan.protected_paths_touched && design.review != 'blocked' && plan.estimate.tokens < 3000000" } }   # G1 automatic (03 section 1a); tokens instead of USD, because measurable with every credential kind
  architect: { mode: off,    runtime: cc-bedrock-eu, model_hint: large,
               modes: [spec, adr, review],
               required_if: "plan.risk == 'high' || plan.protected_paths_touched || plan.design_needed",
               adr_path: "docs/adr/", spec_path: "docs/specs/", quality_scenarios_path: "docs/quality-scenarios.md",   # architect.doc_paths (02) = adr_path and spec_path, derived
               threat_model: stride,               # off | stride
               review_paths: ["docs/architecture/**", "docs/adr/**"] }   # PR review of these paths
  coder:     { mode: shadow, runtime: cc-bedrock-eu, model_hint: mid, pool: self-hosted,
               best_of_n: 1, repair_rounds: 2,
               self_check: { analyzers: [opengrep, osv-scanner, gitleaks], tests: true, lint: true, self_review: true },   # analyzer IDs from analyzers (ADR-40)
               env_bootstrap: off, max_children: 0,          # env_bootstrap: off | propose (02 section 3)
               ask_timeout_h: 72, allow_steer: true, allow_handoff: true,                 # 03 section 2.4
               forbidden_paths: [".github/workflows/**", ".gitlab-ci.yml", "**/CODEOWNERS", ".agents/**", ".agents-platform/**"] }
  reviewer:  { mode: live,   runtime: cc-bedrock-eu, pool: self-hosted,
               models: { gate: small-eu, finder: mid-eu, verifier: large-eu },
               verifier: { build: false },         # true: verifier builds and tests (egress, credential rules in section 3 text)
               profile: chill, inline_min_severity: P1, max_comments: 10, incremental: true, tier: auto, auto_pause_after: 10,
               summary: { walkthrough: true, diagrams: true, effort: true, related: true, labels: suggest, reviewers: suggest },   # stage 6; labels: suggest | apply
               checks: [],                         # own pre-merge checks in natural language, optionally blocking
               auto_approve: false, auto_approve_risk_cap: low,   # services.reviewer.auto_approve (O24, stage 6): approve only human PRs at the verified SHA, only with empty P0/P1, riskScore below the cap, never on protected_paths, conditions a to d (ADR-61); never agent PRs (ADR-14)
               finders: [bugs_diff, bugs_introduced, security, standards, ticket] }
  qa:        { mode: off, flake_runs: 5, mutation: true, output: pr,   # pr | commit
               test_paths: ["**/test/**", "**/tests/**", "**/*.test.*", "**/*_test.*"], catch: { mode: off } }   # catch: off | shadow | live
  prfixer:   { mode: off, max_rounds: 3, commit_mode: agent_branch_or_stacked_pr,
               sources: [review_threads, ci_failure, merge_conflict, static_analysis], bot_allowlist: [self],
               allow_on_human_branches: never, auto_on: [ci_failed_agent_pr] }   # O9, ADR-71: never is the only value; dependency_update and ci_doctor from stage 10
  indexer:   { mode: shadow, layers: [L0, L1, L5], vectors: false }   # vectors only after an eval gain
  standards: { mode: off, schedule: biweekly, max_new_rules: 5, auto_activate: false }   # auto_activate only effective at installation level (O10)
  docs:      { mode: off, runtime: cc-bedrock-eu, model_hint: small,
               modes: [docstrings, sync, release],
               paths: ["docs/**", "README.md"],    # docs may only change these paths (except docstrings)
               release: { tool: git-cliff, notes_model: small-eu } }   # deterministic plus readable text; docs PRs always merge.mode human

# ---------- Who triggers what ----------
routing:
  - { on: "work_item.created", source: [jira-in, gh-hook], services: [triage],   # automatic triage, any human author
      filter: "actor.kind == 'human'", actor: any, enabled: false }
  - { on: "work_item.mentioned", source: [jira-in, gh-hook],
      commands: [triage, plan, architect, code, approve, ask, say, handoff, continue, stop, help],
      pipeline: ticket-to-pr, min_permission: { work_item: write, scm: write } }
  - { on: "work_item.created|work_item.labeled|item.triaged", source: [jira-in, gh-hook],   # auto trigger, optional (03 section 1a)
      filter: "item.labels contains 'agent:auto'", pipeline: ticket-to-pr,
      min_permission: { work_item: write, scm: write }, actor: item_author, enabled: false }
  - { on: "change.opened|change.synchronized|change.ready_for_review", source: gh-hook,
      services: [reviewer], filter: "!change.draft && actor.kind == 'human'" }
  - { on: "comment.command", source: gh-hook,
      commands: [review, fix, qa, architect, docs, release, ask, remember, pause, approve, say, handoff, resume, stop, hold, config, ignore, continue, help],
      min_permission: { scm: write } }
  - { on: "pipeline.ci_failed", source: gh-hook, services: [prfixer],
      filter: "starts_with(change.head_ref, 'agent/')" }   # if a pipeline holds the PR, the event is delivered to it (03 section 2.5)
  - { on: "change.merged", source: gh-hook, pipeline: docs-after-merge, enabled: false }

# Minimum permissions per command (03 section 4). An entry here replaces the min_permission of the route for this
# command, even if it is lower (for example ask); commands without an entry use the min_permission of the route.
# A command only runs if a route names it (deny by default). "Only tightening" applies between the
# config layers: org, repo group and repo may only raise an entry, never lower it.
# `approve` is checked per subcommand (approve plan, approve risk or approve dependency).
command_permissions:
  triage:        { any_of: [{ scm: triage }, { work_item: write }] }
  plan:          { work_item: write, scm: read }
  architect:     { any_of: [{ work_item: write, scm: read }, { scm: write }] }   # ticket like plan, PR write
  approve_plan:  { work_item: write, scm: write }                       # G1, only for the current plan and design version
  approve_risk:  { codeowner_of: touched_protected_paths }              # G4 on the PR or before the first push on the ticket; for test deletion CODEOWNER of the test paths
  approve_dependency: { scm: write }                                    # approval under ADR-64 (propose_dependency)
  docs:          { scm: write }
  release:       { scm: write }
  say:           { any_of: [run_trigger, { scm: write }] }
  handoff:       { any_of: [run_trigger, { scm: write }] }
  resume:        { scm: write }
  continue:      { role: budget_owner }                                  # G5, approvals.budget_owner
  stop:          { any_of: [run_trigger, { scm: write }] }
  hold:          { scm: write }                                          # objection to auto-merge
  pause:         { scm: write }
  remember:      { scm: write }                                          # learning only from humans with write permission
  ask:           { work_item: read, scm: read }
  config:        { scm: read }
  help:          { scm: read }

# ---------- Pipelines ----------
pipelines:
  ticket-to-pr:
    autonomy: medium                              # low | medium | high | full (03 section 1a)
    stages:
      - { service: triage,    on_disabled: skip }
      - { service: planner,   on_disabled: human }
      - { service: architect, on_disabled: skip, when: "services.architect.required_if" }
      - { service: coder,     on_disabled: fail }
      - { parallel: [ { service: reviewer, on_disabled: human }, { service: qa, on_disabled: skip } ] }
      - { service: prfixer,   on_disabled: human, until: "checks.green && findings.p0p1 == 0", max_rounds: 3 }
    merge:
      mode: human                                 # human | shadow | auto; auto only with autonomy full and installation upper bound
      method: squash
      veto_window_min: 30                         # starting value (estimate)
      max_diff_lines: 400                         # starting value (estimate)
      block_on_severity: [P0, P1]
  docs-after-merge:
    stages: [ { service: docs, mode: sync, on_disabled: skip } ]
    merge: { mode: human }                        # the resolver rejects any other value here

approvals:
  protected_paths: ["src/payment/**", "db/migrations/**", "infra/**", "**/auth/**"]
  plan_expiry_days: 7
  budget_owner: "@example-org/platform-owners"

# ---------- Limits (keys: org, repo_group, repo, user, service, provider, pool; only tighten) ----------
limits:
  org:          { usd_month: 2000, runs_day: 400, concurrency: 8 }
  repo_default: { usd_day: 40, runs_day: 60, concurrency: 2 }
  user_default: { runs_hour: 10, runs_day: 30, usd_day: 25, tokens_day: 5000000, concurrency: 2 }   # tokens_day also applies without a USD source
  service:
    triage:    { usd_run: 0.5, turns: 10,  wall_min: 5 }
    planner:   { usd_run: 3,   turns: 60,  wall_min: 15 }
    architect: { usd_run: 3,   turns: 60,  wall_min: 20 }
    coder:     { usd_run: 10,  turns: 120, wall_min: 45 }
    reviewer:  { usd_run: 2,   turns: 40,  wall_min: 15 }
    qa:        { usd_run: 5,   turns: 80,  wall_min: 30 }
    prfixer:   { usd_run: 5,   turns: 80,  wall_min: 30 }
    docs:      { usd_run: 2,   turns: 40,  wall_min: 15 }
  provider:
    codex-api:     { usd_day: 50 }
  pool:
    self-hosted: { concurrency: 4 }
  on_exhausted: neutral_with_reason                # never silent green
  warn_at_percent: 80

security:
  config_from: base_sha
  egress:                                          # allowlist per service, hosts per installation
    triage:    [control.<control-plane-host>, bedrock-runtime.eu-central-1.amazonaws.com]
    planner:   [control.<control-plane-host>, bedrock-runtime.eu-central-1.amazonaws.com]
    architect: [control.<control-plane-host>, bedrock-runtime.eu-central-1.amazonaws.com]
    reviewer:  [control.<control-plane-host>, bedrock-runtime.eu-central-1.amazonaws.com]   # registry-cache only with verifier.build: true
    coder:     [control.<control-plane-host>, bedrock-runtime.eu-central-1.amazonaws.com, registry-cache.internal]
    qa:        [control.<control-plane-host>, bedrock-runtime.eu-central-1.amazonaws.com, registry-cache.internal]
    prfixer:   [control.<control-plane-host>, bedrock-runtime.eu-central-1.amazonaws.com, registry-cache.internal]
    docs:      [control.<control-plane-host>, bedrock-runtime.eu-central-1.amazonaws.com]
  agent_ci: { mode: agent_fork, fork_owner: example-org-agents }   # agent_fork | guarded_workflows (ADR-59, 05 section 3)
  dependencies: { allow: [] }                      # name allowlist for propose_dependency (ADR-64); empty: every new dependency becomes a question
```

Consistency check of the example (test in the config resolver, suite S2; every rule rejects at load time, not only at runtime):
- The org default `allowed_regions: [eu]` only admits `region: eu` runtimes and models. All services in the example use `cc-bedrock-eu` or `*-eu`. `cc-api-wif` and `codex-api` are declared, but only selectable in repos of the class `allow_global`.
- A runtime with `credential.kind: subscription` or `chatgpt` is only valid if the installation has unlocked the kind with `acknowledge_terms` (section 7, ADR-51). It is then only admissible for services whose `nativeTools` do not go beyond `read` (planner, triage, indexer for `ask`, reviewer with `verifier.build: false`), because the token is in the sandbox ([05](05-security.md) section 3). The only exception is the profile `operator_test` (section 3a).
- `verifier.build: true` gives the reviewer `registry-cache` in egress and a shell in the verifier; the credential rules of coder and QA then apply to it.
- `auto_close: true` for `triage` only applies in a repo with a green eval T1 ([07](07-eval.md)); otherwise it has no effect and produces a notice.
- `auto_approve: true` for the reviewer (`services.reviewer.auto_approve`, O24) only takes effect if the reviewer is `live` in the repo (Gate B, ADR-47) and the SCMProvider reports `APPROVE_HUMAN` ([01](01-plugin-interfaces.md) section 5); it never applies to agent PRs (term in [01](01-plugin-interfaces.md) section 5; a human PR into which a human has taken over commits of the platform, for example by merging a stacked PR, also counts as one; the PR fixer itself never writes to human branches, ADR-71) and never if the PR touches `protected_paths`, P0/P1 are open or `riskScore` is above `auto_approve_risk_cap` ([02](02-services.md) section 4). In addition, all conditions from ADR-61 must hold:
  - (a) The hoster's branch protection requires "Dismiss stale pull request approvals when new commits are pushed" and "Require approval of the most recent reviewable push"; `doctor` and the provider check this per repo via the readable rulesets (whether the app can read this without `administration` is unverified, contract test in stage 6; if it is not readable, the condition counts as not met). In addition, the platform withdraws its own approve on every new push, including a push by the Effect Gateway (resolved M84).
  - (b) The author has write permission (freshly read from the provider), and the PR does not come from a fork.
  - (c) A full review (mode `full`) ran at the current head, not just an increment, and the reviewer was not paused (`auto_pause_after`, `@agent pause`).
  - (d) A P0 or P1 finding only counts as withdrawn for the approve if a human with write permission other than the author triggered the withdrawal; a withdrawal via a thread reply by the author leaves the finding open for this check.

  Otherwise it has no effect and produces a notice. The platform's approve never counts as a human approve for `agent-approval-check` ([03](03-flow-and-orchestration.md) section 1a); it only satisfies an approve requirement of the hoster.
- `merge.mode: auto` is invalid for repos of the class `external_code`, i.e. for every public repo (ADR-60, Ruling R-D); the resolver checks the class at load time via the SCMProvider, the orchestrator again on every claim.
- Coder, QA and PR fixer are only admissible in a repo if `security.agent_ci` is set and the check of this variant is green ([05](05-security.md) section 3, ADR-59); otherwise the item stays put with `no_safe_ci`. `agent_fork` requires `fork_owner`, an organization of the installation on which the app is installed.
- Every analyzer must be in the allowlist of the installation, with an identical image digest and license; `distribution: bundled` only with a license from the allowlist of free licenses (ADR-50).
- `merge.mode` of a pipeline with `docs` is always `human`.

Control commands for a running run (`approve plan`, `approve risk`, `say`, `handoff`, `resume`, `stop`, `continue`) go through the same routes as all commands (deny by default applies unchanged). The router checks the route and `command_permissions`; the orchestrator assigns the command to the matching active run of the object (ticket or PR; with several matching runs, a question with `run=<run_id>`) and resolves the matching approval point ([03](03-flow-and-orchestration.md) sections 2.5, 3 and 4). **Routes with `services:`** do not start a run if a pipeline holds the object or a run is already active for object and service; the event then goes to the pipeline or waits as one merged follow-up job (object lock, ADR-68). If there is no waiting run, the platform visibly answers "nothing to approve" or "no running run". The sandbox reaches the LLM hosts in `security.egress` only via the credential relay in the egress proxy ([01](01-plugin-interfaces.md) section 6). The exception is the credential kind `subscription`: there the traffic to the LLM endpoint goes through the inspection proxy, which passes the auth header through unchanged ([05](05-security.md) section 6, condition 9).

## 3a. Example: single operator with their own subscription (profile `operator_test`)

An operator installs the platform for themselves alone, works on their own private repos and uses their own subscription. This is a personal operator mode, blocked by default (ADR-51); the platform implements no login, and the control plane never sees the token; the operator places their `setup-token` in a file on the worker host that only the worker user can read (ADR-57). The providers' terms are in [05](05-security.md) section 6; whether autonomous continuous operation is compatible with them is decided by each operator. Switching to an API key or WIF is a configuration change (`runtime` per service), not a rebuild.

```yaml
# installation.yaml (excerpt, section 7)
version: 1
installation: solo
max_autonomy: full
merge: { max_mode: auto }
credentials:
  personal_modes:
    subscription: { acknowledge_terms: "<version of the terms, e.g. retrieval date>" }   # blocked without this entry
pools:
  - { id: self-hosted, plugin: self-hosted, max_concurrency: 2, isolation: [sysbox, gvisor], single_operator: true }
```

```yaml
# <operator>/.agents-platform/org.yaml (excerpt)
version: 1
installation: solo
org: <operator>
plugins:
  scm:        [ { id: gh, plugin: github, instance: github.com/<operator>, app_id_ref: secret://github-app/id, key_ref: secret://github-app/key } ]
  work_items: [ { id: ghi, plugin: github-issues, scm: gh } ]
  triggers:   [ { id: gh-hook, plugin: github, mode: [webhook, reconcile] } ]
  runtimes:
    - { id: cc-abo, harness: claude-code, version: "pinned:<x.y.z>",
        credential: { kind: subscription, operator: "<operator login>" },
        region: global, allowed_pools: [self-hosted], allowed_triggers: operator_only,
        allowed_services: [triage, planner, architect, indexer, reviewer, coder, qa, prfixer],   # indexer covers @agent ask (02)
        profile: operator_test,                   # shell only with all conditions from 05 section 6
        operator_repos: ["<operator>/<repo-a>", "<operator>/<repo-b>"],   # only private repos of the operator
        acknowledge_risk: [subscription_token_in_shell_sandbox] }           # enum of risk kinds (section 7)
  models:                                          # single calls on the subscription via claude-cli (01 section 7, ADR-58)
    - { id: abo-small, plugin: claude-cli, runtime: cc-abo, model: "<small-model>" }
    - { id: abo-large, plugin: claude-cli, runtime: cc-abo, model: "<large-model>" }
data_policy: { default: { allowed_regions: [eu, global] } }
services:                                         # initial state shadow; live only after qualification (07)
  planner:  { mode: shadow, runtime: cc-abo, gate_model: abo-small }
  coder:    { mode: shadow, runtime: cc-abo, pool: self-hosted }
  reviewer: { mode: shadow, runtime: cc-abo, pool: self-hosted, verifier: { build: true },
              models: { gate: abo-small, finder: abo-large, verifier: abo-large } }
pipelines:
  ticket-to-pr: { autonomy: full, merge: { mode: shadow } }   # auto only after suite S7
routing:
  - { on: "work_item.created|work_item.labeled", source: gh-hook, filter: "item.labels contains 'agent:auto'",
      pipeline: ticket-to-pr, actor: item_author, min_permission: { work_item: write, scm: write } }
  - { on: "change.opened|change.synchronized|change.ready_for_review", source: gh-hook, services: [reviewer],
      filter: "!change.draft && actor.kind == 'human'" }   # bot PRs of the own chain do not trigger twice
approvals: { budget_owner: "<operator login>", plan_expiry_days: 7 }
security:
  egress:                                         # no open internet (05 section 6, condition 9)
    planner:  [control.<control-plane-host>, api.anthropic.com]
    reviewer: [control.<control-plane-host>, api.anthropic.com, registry-cache.internal]
    coder:    [control.<control-plane-host>, api.anthropic.com, registry-cache.internal]
  llm_inspection_proxy: required                  # inspection proxy, 05 section 6 condition 9
  agent_ci: { mode: guarded_workflows }           # ADR-59; doctor checks the workflows of the operator_repos
limits:
  provider: { cc-abo: { runs_5h: 20, tokens_day: 3000000, concurrency: 1 } }   # subscription: runs and tokens, no USD
```

The resolver rejects `profile: operator_test` if a condition from [05](05-security.md) section 6 is missing (test in S2): pool with `single_operator`, trigger and ticket author are the operator, the repo is in `operator_repos` and is private, egress allowlist without open internet, `llm_inspection_proxy: required`, `acknowledge_risk` contains `subscription_token_in_shell_sandbox`. The automatic plan approval measures consumption in tokens (`plan.estimate.tokens`), because the subscription provides no USD.

## 4. Example: repo layer

```yaml
# <repo>/.agents/config.yaml (read at the base SHA)
version: 1
extends: org
services:
  reviewer:
    path_instructions:
      - { glob: "src/api/**", text_ref: ".agents/rules/api.md" }
  qa:
    mode: shadow                                  # repo may switch on if the org does not set lock
    apps:
      - { name: web, path_patterns: ["web/**"], start: "pnpm e2e:serve", seed: "e2e/seed.spec.ts" }
  triage:
    mode: shadow
    properties: { labels: suggest }               # only tightening compared to auto_apply of the org
analyzers:                                        # extends the org list; only images from the allowlist of the installation
  - { id: trivy, image: "<registry>/trivy@sha256:<digest>", license: Apache-2.0, distribution: bundled }
limits:
  service: { coder: { usd_run: 8 } }              # only lowering possible
approvals:
  protected_paths: ["src/billing/**"]             # extends the org list
environment: .agents/environment.yaml             # blueprint: setup, maintenance, knowledge, post_build
```

## 5. Provider choice per service

- `services.<id>.runtime` selects the harness with credential kind; `models.*` select ModelProviders for single calls (gate, verifier judge, summaries). If a model reference points to no reachable ModelProvider, the resolver rejects the service at load time; in subscription operation `claude-cli` is the ModelProvider ([01](01-plugin-interfaces.md) section 7, ADR-58).
- The control plane assigns a work item only to a worker that reports the harness, credential kind, region and **verified** pool capabilities (isolation, ADR-48) that the service requires.
- Policy order of resolution: (1) `data_policy` of the repo class, (2) provider allowlist of the layers, (3) qualification matrix for the desired `mode`, compared via the `qualification_key` of the effective profile ([07](07-eval.md) section 2, ADR-66), (4) limits per provider. If a provider fails, the control plane uses a fallback only if it passes all four checks.
- Typical split (cost lever, DERIVED): small model for gate and triage, medium for finder and coder, large for verifier, planner and architect. Which split applies is decided by the eval per provider.

## 6. Limits

**Keys:** any combination of `org`, `repo_group`, `repo`, `user` (trigger, via linked identity), `service`, `provider` (runtime instance or model) and `pool`.

**Kinds:**

| Kind | Unit | Measurement source |
|---|---|---|
| Cost | USD per run, day, month | provider figure, otherwise client estimate (`total_cost_usd`, "not a billing statement" [cc-sdk-ts] VERIFIED), otherwise price table; no cost for subscription |
| Runs | per hour, day, rolling 5-hour window | ledger |
| Tokens | per day | usage per model incl. cache tokens |
| Concurrency | simultaneous leases | lease table |
| Wall time, turns | per run | worker and harness (`maxTurns`, `maxBudgetUsd` [cc-sdk-ts] VERIFIED) |

**Mechanics** (DERIVED, reference project token bucket and quota per identity):
1. **Reservation before the run:** estimated upper bound from service profile, `turns` and price table. All keys of the chain are checked atomically in one transaction (token bucket per key as a row, `UPDATE ... RETURNING`).
2. **During the run:** the worker reports usage in the heartbeat. If it exceeds the reservation, the Work API responds with `cancel`; in addition, the harness itself aborts where it can.
3. **After the run:** billing from actual usage with a stored cost source (`provider`, `client_estimate`, `price_table`, `subscription_utilization`); the reservation is released.
4. **Subscription runs:** runs and tokens count; subscription utilization is only visible reactively via `rate_limit_event` ([cc-sdk-ts] VERIFIED).
5. **Fallback limit at the provider:** spend limit of the Console workspace ([an-ratelimits] VERIFIED), budgets of the cloud providers. They do not replace the ledger, because subscription and Codex runs bypass any gateway and Codex provides no USD.
6. **Result on exhaustion:** `neutral` with reason and G5, never silent green.
7. **Measurement:** counters are read before and after every eval run; a test proves that an overrun aborts hard on every layer (suite S3).

## 7. Installation configuration

The file `installation.yaml` describes the base on which an installation runs: drivers, public URL, sign-in to the admin UI, pools, upper bounds and unlocks. It belongs to the operator and lies outside the repos (file on the host, secret in the cluster or admin UI). Profiles per base and the installer are in [11](11-installation-and-hosting.md).

**Published as JSON Schema:** the project publishes `installation.schema.json`, `org.schema.json` and `repo.schema.json` (JSON Schema Draft 2020-12) per release in the public repo, versioned via the field `version`. The resolver, the installer CLI (`config validate`, `doctor`) and editors validate against the same file. Keys that change the quality of a service (for example router thresholds, filters, `profile`, `max_comments`, `inline_min_severity`, `incremental`, `finders`) carry the marker `x-qualification: true` in the schema; they go into the qualification profile ([07](07-eval.md) section 2, ADR-66). A schema test checks that every key under `services.*` is either marked or explicitly listed as not quality-relevant (`x-qualification: false`). Reason: third parties write their configuration without our code; a single, machine-readable source prevents documentation and validation from drifting apart.

```yaml
# installation.yaml (example for the Compose bundle on one host)
version: 1
installation: example
public_url: https://agents.example.org          # Work API, ingress, platform MCP, admin UI (ADR-08)
database: { url_ref: secret://postgres/url }    # only PostgreSQL with pgvector, no driver
blob:                                           # BlobStore driver: fs | s3 | azure-blob (later gcs), ADR-41
  driver: s3
  endpoint: http://seaweedfs:8333               # bundled S3 service in the bundle (ADR-43)
  bucket: platform
secrets:                                        # SecretStore driver: file | env | azure-keyvault (more later)
  driver: file
  path: /etc/platform/secrets
cloud_identity:                                 # CloudIdentity driver: self-issuer | azure-managed-identity (more later)
  - { driver: self-issuer, issuer_url: https://agents.example.org/oidc }   # control plane as OIDC issuer (ADR-22)
audit_anchor:                                   # daily anchor: BlobStore with Object Lock or repo via SCMProvider
  sink: scm
  repo: example-org/audit-anchor
admin_sso:                                      # generic OIDC client, no plugin
  oidc: { issuer: https://idp.example.org, client_id: platform-admin, client_secret_ref: secret://oidc/client,
          group_claim: groups,
          roles: { admin: [platform-admins], approver: [platform-approvers], viewer: [engineering] } }
  break_glass: { enabled: true }                # emergency admin at first start; use produces audit and alert
pools:                                          # pools belong to the base; org and repo only select
  - { id: self-hosted, plugin: self-hosted, max_concurrency: 4, isolation: [gvisor, sysbox] }
  - { id: ci-dispatch, plugin: ci-dispatch-github, repo: example-org/worker-runner, max_concurrency: 2, isolation: [sysbox], enabled: false }
  - { id: cloud, plugin: k8s, max_concurrency: 10, isolation: [gvisor, microvm], enabled: false }   # Helm, stage 8
isolation_min:                                  # minimum isolation per repo class (ADR-48, 05 section 3); checked at claim
  private_own:   { runs_repo_code: [sysbox, gvisor], no_repo_code: [sysbox, gvisor] }
  external_code: { runs_repo_code: [microvm],       no_repo_code: [sysbox, gvisor] }   # no_repo_code: reviewer without build, planner, architect, triage, docs without build
max_autonomy: medium
merge: { max_mode: human }
credentials:
  personal_modes: {}                            # subscription and chatgpt blocked; unlock per kind with acknowledge_terms (ADR-51)
qualification:
  allow_unproven_live: []                       # ADR-47; example: [{ service: qa, scope: e2e, reason: "<reason>" }]
analyzers_allowlist:                            # only tightening; org and repo select from it
  - { id: opengrep,    image: "<registry>/opengrep@sha256:<digest>",    license: LGPL-2.1-only }
  - { id: osv-scanner, image: "<registry>/osv-scanner@sha256:<digest>", license: Apache-2.0 }
  - { id: gitleaks,    image: "<registry>/gitleaks@sha256:<digest>",    license: MIT }
  - { id: trivy,       image: "<registry>/trivy@sha256:<digest>",       license: Apache-2.0 }
bundled_licenses: [Apache-2.0, MIT, BSD-3-Clause, LGPL-2.1-only, MPL-2.0]   # allowlist for distribution: bundled (ADR-50)
telemetry:
  product: off                                  # product telemetry to the project, off by default (ADR-44)
  update_check: off
air_gap: false                                  # true: only SCM, ticket and LLM endpoints plus registry_mirror
registry_mirror: null
```

**Rules for individual keys:**
- **Drivers:** exactly one driver per class, except `cloud_identity` (a list, because an issuer and a cloud identity may be needed side by side). Contracts and capabilities in [01](01-plugin-interfaces.md) (driver class, ADR-41). No queue port and no database abstraction: Postgres with pg-boss remains the only state.
- **Pools with isolation:** `isolation` names what the pool may offer; what it can actually do is reported by the worker at claim as a verified capability (ADR-48). A work item that executes repo code of the class `external_code` (`runs_repo_code`) only gets a pool with `microvm`; services without execution of repo code (`no_repo_code`) may use `sysbox` or `gvisor` there. If there is no matching pool, the item stays put ([03](03-flow-and-orchestration.md) section 5). `single_operator: true` marks a pool for exactly one operator (prerequisite for `subscription`).
- **`credentials.personal_modes`:** keys `subscription` and `chatgpt`, each with the required field `acknowledge_terms` (text of the confirmed version, for example the retrieval date of the terms [cc-legal] or [codex-auth]). Without an entry, the resolver rejects every runtime of this kind. The admin UI shows the option as "operator risk, not for multi-user operation".
- **`acknowledge_risk`** (on the runtime, section 3a) is a list from the enum of risk kinds. Today there is only `subscription_token_in_shell_sandbox` (profile `operator_test`); new kinds are only added through a schema version. `acknowledge_terms` concerns terms of use, `acknowledge_risk` technical residual risks; the two are separate fields.
- **`qualification.allow_unproven_live`** (ADR-47): list of services, optionally per part or scope (`scope`, for example `qa` with `e2e` or `prfixer` with `merge_conflict`, [10](10-standards-per-layer.md) section 1.2 point 3), that may run `live` without Gate B or a reference qualification, each with the required field `reason`. Gate A remains required. Admin UI, status comment and check summary then visibly carry "standard not proven". This deviation does not count for the merge gate ([03](03-flow-and-orchestration.md) section 1a condition 2). The default is the empty list.
- **`analyzers_allowlist` and `bundled_licenses`** (ADR-40, ADR-50): an analyzer only runs with an image digest from the allowlist. Only what has a license from `bundled_licenses` is shipped (`bundled`); everything else is `operator_supplied` and obtained by the operator. Results of third-party services (for example SonarQube) only come in as a SARIF import by the operator.
- **`telemetry` and `air_gap`** (ADR-44): product telemetry and the update check are off by default; the operator can switch them on in the setup wizard. `air_gap: true` blocks all outbound connections in the egress proxy except the configured SCM, ticket and LLM endpoints; images then only come from `registry_mirror`. The proxy enforces this, not just a flag. With a cloud LLM, no installation is fully offline ([`hosting-und-installation`](../research/hosting-und-installation.md) section 3.6).
- **`audit_anchor`:** `sink: blob` requires a BlobStore with the capability `OBJECT_LOCK` (the resolver checks this); `sink: scm` writes the daily hash via the SCMProvider into the named repo.
- **Secrets** are never in the file, only references `secret://...`, resolved via the SecretStore driver.
- **Further named values** belong in the same schema; meaning and starting value are governed by [11](11-installation-and-hosting.md): `trigger.poll_interval` (operating mode `private`, section 1.1), `migrate.recent_backup_max_age` (section 6), `backup.restore_test.schedule` (section 7), `install.min_cpu`, `install.min_mem_gb`, `install.min_disk_gb`, `pool.slot_mem_gb` (section 2.4). Starting values are set by stage 0 after measurement.
