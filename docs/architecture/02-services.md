<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# 02 Services

Ten services: `planner`, `architect`, `coder`, `reviewer`, `qa`, `prfixer`, `indexer`, `standards`, `triage`, `docs`. Source keys and classifications as in the [README](README.md).

This file describes, for each service, its purpose, inputs and outputs, steps, write requests, switches, and Definition of Done (DoD). The standard of the field per service, the capability checklist, and the Gate B thresholds are in [10](10-standards-per-layer.md); the bar here is only the short version. Test sets are in [07](07-eval.md), expansion stages in [08](08-roadmap.md). The derivations are in the research documents under `docs/research/` (dated, not binding).

| Service | Layer | Benchmark (short version, details [10](10-standards-per-layer.md)) | Expansion stage |
|---|---|---|---|
| `planner` | Planning | Factory Spec Mode, Jules Planning Critic | 2 |
| `architect` | Architecture and design | Methods arc42, C4, ADR, ATAM, STRIDE, EARS; Kiro, Spec Kit, STRIDE GPT | 2 |
| `coder` | Coding (ticket to PR) | Harness: Claude Code, Codex; product shell: Copilot cloud agent, Devin, Cursor | 2 |
| `reviewer` | PR review | Feature set according to the capability table ([10](10-standards-per-layer.md) section 3), accuracy like the top group on R2 and R4 | 1 (core), 6 (companion features, developer loop) |
| `qa` | Tests and QA | Meta (TestGen-LLM, ACH, JiT), SWT-bench top, Playwright Test Agents | 3 |
| `prfixer` | PR fix and CI | Copilot Agent Merge, Bugbot Autofix, Gitar, Nx | 4 (core), 10 (`dependency_update`, `ci_doctor`) |
| `indexer` | Knowledge, Q&A | Copilot Memory, Sourcegraph Deep Search, DeepWiki | 7a (L0, L5 Learnings), 7 |
| `standards` | Team rules | AGENTS.md, Qodo Rule Miner, Bugbot and Greptile per rule | 7 |
| `triage` | Issue triage | Linear Triage Intelligence | 7 |
| `docs` | Docs, docstrings, release notes | Mintlify, DocAgent, git-cliff and release-please | 10 |

Deliberately not a separate service (ADR-46, ADR-49): static analysis as an engine (connected via the plugin kind `Analyzer`, ADR-40), dependency updates (Renovate or Dependabot create them, `prfixer` repairs), incident and SRE (handoff input only, section 11), migration as a campaign (later, [08](08-roadmap.md) stage 10).

## 0. Common to all services

**Structure of a service:**
- **Manifest:** input and output schemas, dependencies, subscribed events, required plugin capabilities, allowed write requests. The manifest is a published contract with `apiVersion` (`guildwork-dev.github.io/v1alpha1`, set with O17) and the same versioning as plugins; fields in [01](01-plugin-interfaces.md) section 14 (`ServiceManifest`). This lets an operator attach their own services; they run under the same rules as the bundled ones (write requests only via the Effect Gateway, qualification via [07](07-eval.md)).
- **Controller:** deterministic, runs in the control plane process.
- **Jobs:** agent and check steps as work items that workers execute in sandboxes.

**Common flow:** input (normalized request from router or pipeline), agent phase in the sandbox without outward write rights, check phase (deterministic or by an independent model), effect phase via the Effect Gateway.

**Guidelines:** All services read rules and guidelines via the guideline loader of the standards service (section 8) at the base SHA, even when `standards` itself is `off` (ADR-17).

**On, off, shadow:**
- Every service has `mode: off | shadow | live` per configuration layer ([04](04-configuration-and-limits.md)). The org can use `lock: true` to prevent a repo from switching a service on.
- `off`: The controller subscribes to nothing. Commands to it end with `Skipped(service_disabled)` and a visible reply, such as "Review is off for this repo".
- `shadow`: The service runs fully, the Effect Gateway writes nothing outward but to the eval log instead. Costs still count against the limits.
- `live` requires a qualified row of the qualification matrix: Gate A and Gate B green or an adopted reference qualification ([07](07-eval.md), ADR-47, ADR-52). The row applies to exactly one qualification profile (all models per role, `prompt_v` per step, plugin versions, marked config keys); library calls of another service, such as the coder's self-review, belong to the profile of the caller ([07](07-eval.md) section 2, ADR-66). If that is missing, the policy sets the run to `shadow` and records this.
- An operator may deviate from this only via the installation configuration. Then every output of the service (status comment, check, admin UI) visibly carries the note "Standard not proven" (ADR-47). This also applies to services whose Gate B is "open" today (no public reference); for them there is no reference qualification yet.
- In pipelines, every step sets `on_disabled: skip | fail | human`.
- Every service has a test "this one on, all others off" (suite S4).

**Allowed write requests per service** (policy, deny by default; a request can only produce effects covered by its command):

| Service | allowed write requests |
|---|---|
| planner | `propose_plan`, `request_human_input`, `propose_comment` (ticket only) |
| architect | `propose_comment`, `propose_change` (only `architect.doc_paths`, such as ADR and spec paths), `propose_check` (`ai-design-review`), `request_human_input` |
| coder | `propose_push` (only branch `agent/*`), `propose_change` (draft PR; on `.agents/environment.yaml` only in mode `env_bootstrap`), `propose_check` (`quality-gate`, `ai-self-check`), `propose_comment`, `propose_dependency` (ADR-64), `request_human_input` |
| reviewer | `propose_review`, `propose_check`, `propose_thread_resolve` (only own threads without a human reply), `propose_reply` (chat: only in threads of the platform or on mention, stage 6), `propose_labels` (only with `summary.labels: apply`). Approval via the SCM method `approve` only with `services.reviewer.auto_approve: true` and only on human PRs (O24, default off) |
| qa | `propose_check`, `propose_comment`, `propose_push` (only test branch or agent branch and only paths from `qa.test_paths`), `propose_change` (test PR), `propose_dependency` (ADR-64) |
| prfixer | `propose_push` (agent branch or stacked PR), `propose_reply`, `propose_change`, `propose_rerun` (only jobs of the current SHA, at most one per commit), `propose_issue` (only mode `ci_doctor`), `propose_dependency` (ADR-64) |
| indexer | outward only the answer to `@agent ask` (`propose_comment` or `propose_reply` at the place of the question); otherwise it writes only to the KnowledgeStore |
| standards | `propose_change` (rule PR on `.agents/rules/`) |
| triage | `propose_comment`, `propose_labels`, `propose_link` (duplicate, related). Closing only with `auto_close: true` (O25, default off) |
| docs | `propose_change` (only `docs.paths`, docstrings of touched symbols, changelog file), `propose_check` (`docs-drift`), `propose_comment` |

New write requests in this round: `propose_labels` (set labels), `propose_issue` (create or update an issue), `propose_link` (link items), `propose_rerun` (restart a CI job); in addition `propose_dependency` (new dependency that the worker loads into the registry cache outside the sandbox only after a name allowlist and osv check, otherwise a clarifying question; [05](05-security.md) section 3, ADR-64). Contract and permission profiles are in [01](01-plugin-interfaces.md) and [05](05-security.md). For every service the visibility rule across repo boundaries applies ([05](05-security.md) section 7, ADR-63): context only from sources that every reader of the output target is allowed to see.

**Common quality rules** (DERIVED from the layer research):
1. Every result is checked before output, by execution or a separate check step.
2. What is measured is what humans adopt (address rate, merge without rework, approval without change), not a self-assessment.
3. Silence is a valid result.
4. Every DoD is measured per combination of harness, credential kind, and model, because a model change shifts comment count and acceptance (DERIVED).
5. **Two gate kinds per service:** Gate A "not worse than the bare harness with the same model without the platform" and Gate B "level of the standard of the field" against an externally comparable, published reference. Gate B is the measurement form of requirement 1 and decides on `live` and the merge gate, not on building (ADR-55); thresholds in [10](10-standards-per-layer.md), test sets in [07](07-eval.md) section 4. What "not worse", "no significant gap", or "at least" against a reference means (one-sided non-inferiority test with margin, minimum power, "not decidable") is governed only by [10](10-standards-per-layer.md) section 1.4; the DoD tables below only name the set and the reference.
6. **Third-party products as reference:** Comparison values only from benchmarks that third parties have published. No own comparison runs against CodeRabbit or SonarQube and no outputs of these products as ground truth, permanently (O18, O19 decided: not connected, no request; [cr-tos] 4.2 (iv) by its wording prohibits "use the Services to develop competing products or services without CodeRabbit's prior written consent" and the publication of benchmarks; a reading of the texts, not legal advice). Also no further analysis of their documentation for replication ([10](10-standards-per-layer.md) section 16).

**Self-check bundle:** Coder and PR fixer check every push with a list of `Analyzer` instances from the repo configuration (`self_check.analyzers`, [04](04-configuration-and-limits.md)), not with fixed tool names (ADR-40). Default list with a free license (ADR-50): project tests, linters of the repo, Opengrep (LGPL-2.1) only with own rules, osv-scanner (Apache-2.0), gitleaks (MIT), plus the diff policy (no `forbidden_paths`, no deleted or skipped tests without approval). Semgrep registry rules, the Opengrep rule collection (Commons Clause, [opengrep-rules]), and the CodeQL CLI are never part of the bundle; results from the operator's code scanning come in only as `ingest` ([opengrep], [semgrep-rules], [codeql-lic] VERIFIED according to [research static analysis](../research/ebene-statische-analyse-und-security.md) section 2.4). All analyzers run in the sandbox; the output is SARIF 2.1.0 ([sarif]).

---

## 1. Planner

**Purpose:** Turn a ticket (Jira, GitHub, GitLab, Linear, Azure DevOps) or a free description into a checked, versioned plan that a human approves, or with autonomy `high` and `full` the automatic plan approval ([03](03-flow-and-orchestration.md) section 1a), and that the coder or a human implements.

**Bar** (short version; standard and checklist in [10](10-standards-per-layer.md), derivation in [research planning](../research/ebene-planung-und-architektur.md) section 2.1):

| Vendor | Mechanism | Source |
|---|---|---|
| Factory Spec Mode | agent read-only, approval via `ExitSpecMode`, autonomy selectable afterwards, org ceiling | [factory-spec] VERIFIED |
| Jules | clarifying questions, Planning Critic for automatically approved plans, according to Google 9.5% fewer task failures | [jules-changelog] VERIFIED, number CLAIMED |
| Spec Kit, Kiro | `clarify`, `analyze` (gaps and contradictions), tasks with dependencies | [speckit-repo], [kiro-specs] VERIFIED |

**Input:** `PlanRequest { workItem | change | brief, trigger, autonomyCeiling, targetRepos? }` with `brief = { text, attachments[] }` (image, PRD). Ticket read fresh via `getItem`, rules from the default branch at run start (SHA pinned in the config snapshot).

**Output:** `PlanArtifact v{n}` (JSON plus rendered Markdown): `kind: feature | bugfix | refactor`, `summary`, `research[]` (each with a citation), `designChoices[]` with rationale, `phases[]` with `tasks[]` (`dependsOn[]`, `requirementIds[]`), `acceptance[]` (ID, text, `testHint`), `assumptions[]`, `relatedItems[]` (duplicates, related tickets), `risk`, `confidence` (0 to 1, calibrated against the resolve rate once measurement data exists), `agentPrompt` per phase and overall, `questions[]`, `estimate` (files, runs, costs as an estimate), `protectedPathsTouched[]`, `designNeeded` (planner reports a design need; field `plan.design_needed` in `architect.required_if`, [04](04-configuration-and-limits.md)), `humanEdited`. Requirements in the EARS pattern are provided by the architect (section 2); the plan refers to their IDs. Comment on the ticket (Jira via ADF, Linear as session plan), version in `artifacts`.

**Steps:**
1. **Repo resolution:** ticket to repo via `repo_mapping` (project, component, labels), links in the ticket, otherwise a clarifying question ([04](04-configuration-and-limits.md)).
2. **Clarity gate** (small model via ModelProvider, shared library with `triage`): is the specification sufficient, is the task too large? If unclear: `questions[]` instead of a plan, the run waits (G1b).
3. **Research read-only:** harness with `nativeTools: "read"`, no effects except `request_human_input`, egress only the LLM endpoint and platform MCP. KB tools if the indexer is qualified, otherwise agentic via grep.
4. **Consistency analysis** (Spec Kit `analyze` principle): gaps, contradictions, and unstated requirements in the ticket go into `questions[]`. Reason: according to SWE-RPG, unstated requirements are the largest source of errors ("24.5%-46.0% of agent runs", [swe-rpg] VERIFIED).
5. **Synthesis** into the schema, mandatory citation per research item.
6. **Plan verifier** (deterministic plus fresh model): every named file and every symbol must exist at the base SHA or is marked as "to be created"; invalid citations are dropped. Check against rules, AGENTS.md, and an optional principles file of the repo from the base SHA. Large tasks are broken down into milestones with a validation point.
7. **Plan critique** (only with autonomy `high` and `full`): a fresh model without planner context checks the plan against ticket and base SHA and assigns `ok`, `concerns`, or `blocked`; input for `approval.auto_if` ([04](04-configuration-and-limits.md)).
8. **Publish** via the Effect Gateway, status comment "Plan awaiting approval" or "Plan automatically approved" with the conditions met, event `plan.ready`.

**Human editing:** `@agent plan --replace` with attached Markdown or editing the plan comment creates `v{n+1}` with `humanEdited: true`; the plan verifier runs again. Optionally the coder stores the approved plan as the first file in the agent branch (`planner.persist: none | branch`, default `none`).

**Quality mechanics:** read-only phase technically enforced; citation check; cost prediction before G1; versions are kept; autonomy level selectable on approval, capped by the org; no approval after timeout ([03](03-flow-and-orchestration.md) section 1a).

**Dependencies:** WorkItemProvider or SCM issues, SCMProvider read-only. Optional: KnowledgeStore, Architect.

**On/off and combination:**
- On alone: plans as a comment, no follow-on chain.
- Off in `ticket-to-pr`: default `on_disabled: human`, so an explicit approval "code without a plan" is needed (`@agent code --no-plan`); with `skip` the coder gets the ticket directly as its task.

**DoD** (test sets [07](07-eval.md), thresholds [10](10-standards-per-layer.md)):

| Metric | Test set | Gate |
|---|---|---|
| File recall of the plan, share of named files not touched | P1 (repos of the installation plus public set) | Gate A: not below the bare harness |
| File localization, external | Loc-Bench V0.1 (Apache-2.0, [locbench-hf]) | Gate B: Acc@5 against LocAgent with the same model, state recorded at measurement (rule [10](10-standards-per-layer.md) sections 1.4 and 4) |
| Plan benefit: resolve rate of the coder with minus without plan, same model | P1; externally a non-saturated C1p subset | Gate A and Gate B: "plan does no harm" ([10](10-standards-per-layer.md) section 4); a benefit greater than 0 is reported as a goal, together with the efficiency effect (costs, turns, review rounds per solved task) |
| Clarifying questions | P2 (unclear tickets, Ambig-SWE method [ambig-swe]) | clarifying question on P2, no unnecessary one on P1 |
| Plan content | P3 (own set following the SWE-RPG method; the dataset itself has no license file) | coverage of the reference points, reference in [10](10-standards-per-layer.md) |
| Plan critique | P4 (planted plan errors) | detects planted errors; task failure rate with minus without critique reported, Jules 9.5% only as a guide value (CLAIMED) |
| Mandatory properties, one test each | Suite | structure incl. agent prompt; read-only; versions; same flow from GitHub and Jira; duration at most 10 minutes (starting value) |

A comparison run against CodeRabbit Plan is not part of Gate B (rule 6, O18).

---

## 2. Architect

**Purpose:** Make architecture and design checkable: specification with requirements in the EARS pattern, ADR drafts, design review against C4 and arc42 checkpoints, threat model following STRIDE, and plan conformance after implementation. A separate service rather than a planner option, because inputs, check methods, and qualification differ and the chain of specialized services applies (ADR-35, ADR-46).

**Bar** (derivation [research planning and architecture](../research/ebene-planung-und-architektur.md) sections 2.2 to 2.4): The recognized standard is a method, not a product (DERIVED). The benchmark is "method fully applied, every statement backed by a citation":

| Standard | What we adopt | Source |
|---|---|---|
| EARS | requirement sentence "WHEN ... THE SYSTEM SHALL ..." with ID | [ears] CLAIMED, use by Kiro [kiro-feature] VERIFIED |
| Spec Kit, Kiro | files for requirements, design, tasks; `analyze` and `converge` (implementation against spec) | [speckit-repo] (MIT), [kiro-specs] VERIFIED |
| C4 with review checklist | diagrams levels 1 to 3, check against the 21 yes/no questions | [c4-checklist] VERIFIED (CC BY 4.0) |
| arc42 | structure, quality scenarios from section 10 | [arc42] VERIFIED (CC BY-SA 4.0, link only) |
| ADR, MADR | one decision per record with rationale | [adr], [madr-license] VERIFIED (MIT or CC0) |
| ATAM-like evaluation | quality scenarios, risks, tradeoffs | [atam] CLAIMED |
| STRIDE, Threat Modeling Manifesto | threats per trust boundary | [ms-stride], [tm-manifesto] VERIFIED |
| STRIDE GPT, AWS Threat Designer | AI threat model with code evidence | [stride-gpt] (MIT), [threat-designer] (Apache-2.0) VERIFIED |

**Input:** `DesignRequest { mode: spec | adr | review | threat_model | conformance, workItem? | plan? | change?, targets? }`. Triggers: `@agent architect [spec|adr|review]` ([03](03-flow-and-orchestration.md) section 4; `@agent design`, `@agent adr`, and `@agent design-review` at most as aliases); in `ticket-to-pr` automatically when `plan.risk == high`, `protected_paths` are touched, or the repo sets `architect.required_if`; as a PR review for paths from `architect.review_paths` (such as ADR folders, architecture docs, C4 sources).

**Output:** `DesignArtifact v{n}`: `requirements[]` (ID, EARS text, source in the ticket), `design` (C4 levels 1 to 3 as Mermaid, data flow, error handling, test strategy), `tasks[]` with dependencies (to the planner), `adrDrafts[]` (MADR), `findings[]` (finding schema as for the reviewer, section 4, with `kind: design | threat | plan_deviation`), `threatModel?` (elements, trust boundaries, STRIDE threats with code location and countermeasure), `verdict: ok | concerns | blocked` (in `approval.auto_if` as `design.review`). Check `ai-design-review` with `success`, `neutral`, or `failure`, never silent green.

**Steps:**
1. **Context** read-only: ticket, plan, rules, and existing architecture docs from the base SHA, quality scenarios from `architect.quality_scenarios_path`, KB tools if qualified.
2. **Mode `spec`:** requirements with IDs in the EARS pattern, design, tasks; consistency analysis like Spec Kit `analyze`; clarifying questions instead of assumptions.
3. **Mode `adr`:** ADR draft per `designChoice` with impact beyond the ticket (criterion in the manifest), as a file under `architect.adr_path`.
4. **Mode `review`:** check against quality scenarios, C4 checklist (deterministically checkable questions by rule, the rest by model), contradictions with existing ADRs.
5. **Mode `threat_model`:** STRIDE per touched trust boundary; every threat with a verified code or document location.
6. **Mode `conformance`** (plan conformance, Spec Kit `converge` principle): implementation against the approved plan and spec; every requirement met, open, or deviating; result as `plan_deviation` findings. Runs as a library in the reviewer when the architect is on; an open `plan_deviation` of severity P1 blocks the merge gate like other P1 ([03](03-flow-and-orchestration.md) section 1a).
7. **Verifier:** every citation exists at the base SHA or head; Mermaid parses; findings without a valid citation are dropped.
8. **Publish** via the Effect Gateway; with `blocked` the run waits for G1 by a human.

No shell except for rendering diagrams; egress only the LLM endpoint and platform MCP. Bundled templates: MADR, C4 checklist, and Spec Kit templates with license notice; arc42 only linked, because share-alike could otherwise extend to own templates (a reading of the license, not legal advice).

**Dependencies:** SCMProvider read-only, WorkItemProvider. Optional: Planner, KnowledgeStore.

**On/off and combination:** Default `off`; in `ticket-to-pr` `on_disabled: skip`. On alone: design review on architecture PRs and ADR drafts by command. Order of switching on: first `review` in shadow on architecture PRs, then `spec` and `adr`.

**DoD:**

| Metric | Test set | Gate |
|---|---|---|
| Design from PRD | AR1 (DevBench design, Apache-2.0, [devbench]) | Gate B report part, required part once the published values have been read ([10](10-standards-per-layer.md) section 5) |
| Design review | AR2 (planted defects in architecture documents of public repos) | Gate A: above the bare harness with a simple prompt |
| Method conformance (EARS, MADR, C4 checklist) | Suite | Gate B required part: 100% of the automatically checkable points ([10](10-standards-per-layer.md) section 5) |
| Threat model | AR3 (systems with a human-made model) | Gate B required part: no significant gap against STRIDE GPT, re-measured ourselves with the same model ([10](10-standards-per-layer.md) section 5) |
| Plan conformance | AR4 (planted deviations between plan and PR) | every planted P1 deviation found; traceability requirement, task, test 100% |
| Citations | Suite | 0 findings without a valid citation |

---

## 3. Coder

**Purpose:** Turn an approved plan or a clear task into a checked draft PR, with evidence instead of claims.

**Bar** (derivation [research coding](../research/ebene-coding.md) sections 2.1 to 2.3): Two layers. For the agent core, harness and model lead (Claude Code, Codex in the top rows of SWE-Bench Pro V2 and SWE Atlas, [scale-lb] VERIFIED); the platform wraps harnesses as `AgentRuntime` and must not make them worse. For the product shell the following apply:

| Vendor | Mechanism | Source |
|---|---|---|
| Devin | blueprints in layers, Managed Devins (child sessions with their own limit), takeover of the session by humans | [devin-blueprints], [devin-adv], [devin-tools] VERIFIED |
| Copilot cloud agent | self-check before the PR (tests, linters, CodeQL, advisory, secret scanning, code review), steering in the same session | [copilot-validate], [copilot-agent] VERIFIED |
| Claude Code (cloud) | messages to a running session, teleport into the terminal, clarifying questions, self-hosted runners outbound only | [cc-cloud] VERIFIED |
| Cursor Cloud Agents | agent-driven environment setup, snapshots, desktop takeover | [cursor-cloud] VERIFIED |
| Codex Cloud | setup separate from the agent, best-of-N | [codex-cloud] VERIFIED, best-of-N [codex-bon] CLAIMED |

**Free harness:** Claude Code is proprietary ([cc-license] VERIFIED) and is never bundled, but installed at the operator with a pinned version and checksum (ADR-39). At least one free harness must be qualified for the coder so that third parties can work without an Anthropic contract: Codex CLI (Apache-2.0, [codex-repo]) or OpenHands Agent SDK (MIT, [oh-sdk-repo]), both VERIFIED. The OpenHands Index measures the same harness with many models and thus provides a direct reference ([oh-index]).

**Input:** `CodeRequest { plan?: PlanArtifact@version (hash bound), design?: DesignArtifact@version, workItem, repo, baseRef, autonomy }`.

**Output:** `ChangeProposal { bundleRef, branch, diffStat, selfCheck: SelfCheckReport, prBodyMd, risks[] }`, then event `change.proposed`. Draft PR via the Effect Gateway with `Closes` or ticket key, plan link, self-check report, and AI notice; `prBodyMd` fills the repo's PR template from the base SHA, every commit carries the trailers `Agent-Run: <url>` and `Co-authored-by` of the platform identity. Or `cannot_implement` with a reason.

**Steps:**
0. **Bootstrap the environment** (gap L4, only when `.agents/environment.yaml` and devcontainer are missing and `coder.env_bootstrap: propose`): a setup work item with an open network and without repo write rights detects dependencies, installs, runs lint, build, and tests, and delivers a blueprint proposal as its own PR. It only applies after merge. Reason: without this, the platform is usable on third-party repos only after manual work.
1. **Environment:** sandbox from the repo blueprint (`.agents/environment.yaml` or devcontainer). Setup phase with secrets and an open network, after which secrets are removed; agent phase only with an egress allowlist. Snapshot per repo, rebuild on change.
2. **Reproduction first** for bug tickets: a test that is red at the base SHA.
3. **Implementation** per plan phase with `nativeTools: "edit+shell"`; shell only in the sandbox. The plan of the current phase is put into the context anew for each phase (plan reminder, [plan-to-action] VERIFIED).
4. **Clarifying question and steering** (gaps L1, L2): The coder may issue `request_human_input` in the middle of the run. The worker then stores `snapshot(tag)` of the sandbox plus `sessionRef` and releases the lease; state `coding -> awaiting_input`. An answer or steering instruction from an authorized person (`@agent say <text>`, event `run.steer`) starts a new work item with `restore(snapshotRef)` and `AgentRuntime.resume()`. Never a live sandbox without a lease. A harness without `RESUME` reports the capability as `none`; then the run ends with a WIP branch and a summary.
5. **Handoff to humans** (gap L3, expansion stage 9): `@agent handoff` pushes the intermediate state to `agent/<key>-wip`, stores a transcript bundle in the BlobStore, and posts the continuation instruction; `@agent resume` takes over the branch including human commits as the new base. After human commits there is never an auto-merge ([03](03-flow-and-orchestration.md) section 1a).
6. **Breakdown into child runs** (gap L5, expansion stage 9, `coder.max_children`, default 0): plan phases with `parallelizable: true` and disjoint paths run as child steps with their own sandbox, their own branch, and their own limit; a deterministic integrator merges them into the agent branch or opens stacked PRs; a conflict becomes a conflict step of the PR fixer.
7. **Self-check bundle** (section 0), deterministic in the worker, not claimed by the agent; in addition plan reconciliation: changed files against `phases[].tasks[]`, every `requirementId` with a test or a justified waiver. For diffs in `qa.apps[].path_patterns` the coder calls the QA library "E2E smoke" and attaches a screenshot or video.
8. **Self-review** by a fresh reviewer run that sees only the diff and the task (reviewer as a library, also runs when the reviewer service is switched off). Findings from P1 upward go back to step 3, at most `repair_rounds` (starting value 2, estimate).
9. **Optional best-of-N** (expansion stage 9, default 1): selection is deterministic (self-check green, then fewer P0/P1 in the self-review, then smaller diff); all attempts in the Run Record. Switch on only if Gate A shows a gain per cost.
10. **Upload bundle**, write requests `propose_push` and `propose_change`. The gateway checks hard gates, pushes to `agent/<key>-<slug>`, opens the draft PR, sets `agent-approval-check` to `pending`, links the ticket.

**Hard gates** (one test each, target 0 violations): no change to `.github/workflows` or CI configuration; no secret in diff, log, or snapshot; no deleted or skipped test without G4; no push without a green self-check bundle, except the WIP branch after the deadline ([03](03-flow-and-orchestration.md) sections 2.1 and 2.4; all other gates apply, no PR); no change to `protected_paths` without G4.

**Dependencies:** SCMProvider, ExecutionBackend with `DOCKER_IN_DOCKER` (Testcontainers) and `snapshot`/`restore`, AgentRuntime, Analyzer. Optional: Planner, Architect, KnowledgeStore, QA.

**On/off and combination:** On alone: `@agent code` with a clear task, the PR stays a draft. Off: the pipeline ends with "Plan ready, coding is off"; the plan's `agentPrompt` remains usable for humans or third-party tools.

**DoD:**

| Metric | Test set | Gate |
|---|---|---|
| Resolve rate (FAIL_TO_PASS and PASS_TO_PASS green) | C1 (private per installation) and C1p (public, ADR-52) | Gate A: not worse than the bare harness with the same model |
| Capability, quality, contamination, shell, languages | Gate B basket B1 to B5 in Harbor format (SWE-Bench Pro V2 Full, HARD-51 as regression, SWE Atlas Refactoring and Test Writing, SWE-rebench, Terminal-Bench, language sets incl. C#) | Gate B against the published value of the same harness with the same model ([scale-lb] VERIFIED); rule, margin, and set (B1 on V2 Full as non-regression) in [10](10-standards-per-layer.md) sections 1.4 and 6; required part today only B1, B2 and B3 only after license review. SWE-bench Verified is no longer a reference |
| Free harness | C1p, B1 | at least one free harness with Gate A and B1 green; the project measures this only in an optional owner run with its own account (O28), it is not a done criterion of any stage |
| Clarifying question, steering, handoff, child runs | Suite S5, S6 | continuation from snapshot without loss; failure paths as in [03](03-flow-and-orchestration.md) section 5 |
| Merge without human code change, review rounds per PR | B6 online | measured per provider, no fixed target before measurement |
| Cost and duration per case | C1, C1p | reported per provider |
| Hard gates | own suite plus S1 to S6 | 0 violations |

---

## 4. Reviewer

**Purpose:** Check PRs like the standard of the field: few, evidenced findings with a fix instruction per finding, incremental, plus the companion features that teams are used to from the standard.

**Bar** (derivation [research review](../research/ebene-review.md) sections 2 and 3): **Feature set according to the capability table in [10](10-standards-per-layer.md) section 3, accuracy like the top group on R2 and R4.** On Martian offline, Qodo Extended, cubic, and Augment lead (F2 `core` 64 to 65%, own calculation from the MIT data [mcr-repo], VERIFIED according to the research); online the ranking changes.

| Vendor | Mechanism | Source |
|---|---|---|
| Copilot code review | levels Lite, Balanced, Max; ensemble of several runs (address rate plus 8%, CLAIMED); reads instructions from the head | [gh-ccr-doc] VERIFIED, [rb-blog] CLAIMED |
| Greptile | tiers, confidence 0 to 5, auto-approve with a risk cap, CLI, analytics | [greptile-tiers], [greptile-approve], [greptile-cli] VERIFIED |
| Cursor Bugbot | configuration from the base branch, `resolution_status`, `@cursor remember` | [cursor-bugbot] VERIFIED |
| Qodo, cubic | specialist agents, requirement gaps, top on Martian offline | [qodo-overview], [cubic-llms] VERIFIED |
| Codex, Devin Review | only P0 and P1; bugs and flags separate, output limit | [codex-gh], [devin-review] VERIFIED |

**Input:** `ReviewRequest { change, mode: full | incremental, since?: sha, profile, tier: auto | base | deep, origin: pr | cli | mcp }`. Triggers: `opened`, `synchronized`, `ready_for_review`, `@agent review`, `change.proposed`; locally via CLI (section 4a).

**Output:** `ReviewArtifact`:
- `findings[]`: fingerprint, path, lines, `existing_code`, title, trigger scenario, evidence file:line, severity P0 to P3, confidence, kind (`bug | flag | plan_deviation`), category, `cwe[]`, `reachability` (`external | internal | unreachable`, `unreachable` at most P3), `exploitability`, `source` (`llm | analyzer:<id> | architect`), `rule_id` plus verbatim quote, `agent_prompt`, evidence level (`proven | plausible | unsupported`).
- `walkthrough { summary, changes[]: { files[], text } }`, `diagram?` (Mermaid sequence diagram), `effort` (1 to 5), `riskScore`, `related[]` (issues and PRs with citation), `labels[]`, `suggestedReviewers[]`, `preMergeChecks[]: { id, result: passed | failed | inconclusive, reason }`, `addressed[]`.
- One review per run (`verdict: comment` or `request_changes`), inline only P0 and P1, the rest in the summary. Check `ai-review` with `success`, `neutral` (error, budget), or `failure`, never silent green. State in the DB ([05](05-security.md), ADR-11).
- Automatic approval (approve) for human PRs as an option (O24 decided, stage 6), platform default off (`services.reviewer.auto_approve`, [04](04-configuration-and-limits.md)): only with empty P0/P1, risk below the cap, never on `protected_paths`, at the checked head SHA via the optional SCM method `approve` ([01](01-plugin-interfaces.md) section 5), and only under conditions (a) to (d) from ADR-61 ([04](04-configuration-and-limits.md) section 3): the host discards stale approves, author with write access and no fork, full non-paused review at the head (an increment or an auto-pause is not enough), P0/P1 withdrawal only by a human with write access other than the author; on every new push the platform withdraws its approve; never for agent PRs (ADR-14), not even for human PRs with commits of the platform ([01](01-plugin-interfaces.md) section 5); it does not replace a branch rule.

**Steps:**
1. **Gate** (small model plus rules): draft, bot, only generated files or lockfiles, HEAD already checked, auto-pause after `reviewer.auto_pause_after` commits or `@agent pause`; quota check beforehand.
2. **Router:** complexity determines depth and models, capped by `tier`.
3. **Context package**, deterministic: diff with line numbers, impact set from KB L1 or live via parser, guidelines from the base SHA via the guideline loader (incl. AGENTS.md, CLAUDE.md, `.cursorrules`, Copilot instructions, section 8), learnings with a valid citation, finding state, linked tickets with acceptance criteria, CI results, **analyzer results** at the head (own `run` runs or `ingest` as SARIF from CI and code scanning; SonarQube results only with `llmUse: forbidden`, so never in the context of a model, ADR-50; there is no SonarQube on the development repo, O19).
4. **Finders:** narrow subagents (bugs in the diff, bugs in introduced code, security with a threat model if available, standards, ticket fulfillment, plan conformance via the architect), output only via schema. Analyzer findings go in as a **candidate signal**, not as a finished finding (ADR-40).
5. **Companion generators** in parallel to the finders (small model, only on the context package): walkthrough, diagram, effort, related items, labels, reviewer suggestions (from CODEOWNERS and history), pre-merge checks. Built-in checks: title, description, issue linked, docstring coverage of touched symbols; own checks in natural language from `reviewer.checks[]`, optionally blocking.
6. **Verifier per finding:** reads up and assigns `proven`, `plausible`, `unsupported`. Two modes via the switch `reviewer.verifier.build: true | false` (default `true`): with `build` it may run build and tests in the sandbox, without `build` only read. The config resolver rejects at load time any combination in which a runtime with `max_native_tools: read` (such as credential kind `subscription` outside `operator_test`, ADR-51) is to serve the reviewer with `verifier.build: true` (resolves M10).
7. **Code filter:** evidence times severity times confidence; convention finding only with a verbatim quote at the base SHA; noise filter via similarity to findings the team rejected earlier; dedupe via fingerprint, line IoU, and CWE (LLM and analyzer findings together); output limit per PR.
8. **Poster** via the Effect Gateway with a fallback chain per SCM capability.
9. **Increment:** only since `last_reviewed_sha`; "Addressed in commit" for open findings; resolve own threads only without a human reply.

**Chat and learnings** (core, not optional): a reply in the thread produces a withdrawal, confirmation, or learning candidate (only from humans with write access). A withdrawal of a P0 or P1 finding by the author of the PR does not count for `auto_approve` (ADR-61 (d)). `@agent remember <fact>` creates a learning explicitly; lifecycle at the indexer (section 7). Multiple runs of the finders with shuffled order and majority only if the eval shows the gain.

**Dependencies:** SCMProvider, AgentRuntime or ModelProvider. Optional: Analyzer, KnowledgeStore, Standards, Architect, WorkItemProvider (ticket fulfillment).

**On/off and combination:** On alone is the most common case. Off: agent PRs from `ticket-to-pr` get no machine review (step `on_disabled: human`, note in the PR); the coder's self-review still runs.

### 4a. Local review and developer loop (expansion stage 6)

- **CLI:** `guildwork review --local [--uncommitted]` (command of the platform CLI) checks committed and uncommitted changes against the merge base with the default branch, rules from the default branch. Output NDJSON for coding agents (`finding`, `heartbeat`, `complete`). Execution either locally with the user's own credential or as a work item via the Work API; then the data path policy applies.
- **Developer MCP:** read tools for IDE agents (open findings of a PR, fix prompt, rules, learnings) with a token per user and permission check at the provider. The only write request is "marked as fixed"; the next increment run verifies it.
- **Analytics** in the admin UI: address rate and recall by the Martian definition, comments per PR by severity, silent runs, time to merge, cost per review; CSV export; scheduled report via the `Notifier`.

**DoD** (test sets [07](07-eval.md), thresholds [10](10-standards-per-layer.md)):

| Metric | Test set | Gate |
|---|---|---|
| Recall and precision against human findings | R1 (public repos, bothy first, findings labeled by humans; never CodeRabbit outputs, O18), R3 (repos of the installation, private) | Gate A: not worse than the bare harness with a simple review prompt |
| F2 `core` and precision | R2 Martian offline (MIT, 50 PRs, 173 golden comments) | Gate B against CodeRabbit's value (mandatory) and the top (goal) under all three judges of the file (in the project under the two Claude judges, O28), precision starting value 55% (estimate, binding only after the first run); recompute the reference per run from the current file; rule and margin in [10](10-standards-per-layer.md) sections 1.4 and 3 |
| Grounded recall and F1 on the full golden set, leave-producer-out as diagnosis | R4 ReviewBench (MIT, 219 PRs) | Gate B against the best publicly listed value; rule, margin, and condition for leave-producer-out in [10](10-standards-per-layer.md) sections 1.4 and 3 |
| Recall against human feedback, multilingual | R5 SWE-PRBench (CC-BY-4.0), AACR-Bench (Apache-2.0) | Gate A, plausibility |
| Comments per PR, silent runs | R2, R4 | report (reference Copilot 5.1 per review, 29% silent, CLAIMED [gh-60m]) |
| Companion features | Suite | every named file exists in the diff (100%); diagram parses, 0 invented participants; pre-merge checks 0 wrong verdicts on the suite |
| Local review | Suite | P0/P1 fingerprints equal to the PR review on the same diff, starting value 90% (estimate) |
| Verifier without build | Suite | resolver rejects the forbidden combination at load time |
| Increment | Suite | no re-posting on unchanged code, "Addressed" correct |
| Online | pilot repos | address rate measured by the Martian definition; no comparison with CodeRabbit (O18) |
| Cost and duration per run | all | reported per provider; no reference to CodeRabbit run times (O18) |

---

## 5. QA

**Purpose:** Demonstrate that a change does what it should, and find errors in the diff: reproduction tests, tests with demonstrated benefit, catching tests, E2E checks with evidence.

**Bar** (derivation [research QA](../research/ebene-qa-und-tests.md) section 2): Four subfields, each with its own top (DERIVED).

| Subfield | Standard | Source |
|---|---|---|
| Reproduction | SWT-bench top (agents with test selection and execution) | [swt-lb] VERIFIED as a leaderboard entry |
| Unit tests with benefit | Meta TestGen-LLM (filter: builds, passes, covers) and ACH (mutation-guided); Microsoft `code-testing-generator` (MIT: test files only, discovery check, quality audit); Copilot `@Test` | [testgen], [ach], [ms-skills] VERIFIED; [ms-vs-test] VERIFIED |
| Catching | Meta JiT: tests that are meant to fail on the diff, checker against false alarms; 41 candidates, 8 real bugs | [jit] VERIFIED |
| E2E | Playwright Test Agents (Apache-2.0), Momentic (quarantine, failure classification), Factory QA | [playwright-agents], [momentic-llms], [factory-qa] VERIFIED |

Qodo is no longer a benchmark: Qodo Cover has been unmaintained since 2025-06-15 and is AGPL ([qodo-cover] VERIFIED), the v1 command `test` was removed on 2026-10-01 ([qodo-sunset] VERIFIED).

**Input:** `QARequest { change, scope: unit | repro | catch | e2e | all, targets?: paths }` via `change.proposed`, `@agent qa`, `@agent tests` (alias for `unit`), or a pipeline step.

**Output:** `QAReport { verdict: pass | fail | blocked, tests: GeneratedTest[], catchFindings[], failures[]: { test, class: product_bug | test_bug | flake | environment }, coverage: { before, after } (changed lines), mutation?: { before, after }, evidence: Artifact[] (screenshots, videos, logs) }`. Check and comment; new tests as a commit on the agent branch or as a separate stacked test PR (`qa.output: pr | commit`).

**Steps:**
1. **Mapping** of the diff to apps via `qa.apps[].path_patterns`.
2. **Run existing tests** of the affected areas.
3. **Reproduction test** for bug tickets: red at the base commit, green with the fix.
4. **Unit and integration tests (mode hardening):** generate candidates, then hard filters in the worker: builds; passes 5 times; is found and executed by the repo's standard test command (discovery check, otherwise it does not count); assertion quality (no empty or tautological assertions, pattern `test-quality-auditor` [ms-skills]); no network, no fixed ports, no time dependency; and covers new lines or branches or kills at least one non-equivalent mutant (Stryker, mutmut, PIT, cargo-mutants per language; equivalence judge via ModelProvider).
5. **Mode catching** (`scope: catch`): diff-aware tests that are meant to fail at the head; checkers from rules plus a fresh model decide "real bug" or "false alarm". The result is a finding to the reviewer or `request_human_input`, never a test commit. Catch findings block the merge gate only for P0/P1 with the checker verdict "real bug"; at first only `shadow`.
6. **E2E:** planner, generator, healer following the Playwright pattern. Selector healing is allowed; if the function is broken, a finding is reported, never healed away (false healing target 0).
7. **Failure classification** after every red run: `product_bug | test_bug | flake | environment`. Flake quarantine per repo only as a proposal with approval by a human; a `flake` or `environment` leads to a retry or `blocked`, never to a merge; a `product_bug` always blocks.
8. **Report** as check `pass`, `fail`, or `blocked` with evidence and coverage before and after, optionally a required check.

**Path policy:** QA only creates test files or appends to existing ones (`qa.test_paths`); build manifests only for registering new test projects; production code never. The Effect Gateway checks this before every push.

**Dependencies:** ExecutionBackend with `DOCKER_IN_DOCKER` and for E2E `BROWSER` (Chromium in the container; the Claude Code sandbox is incompatible with Chromium [cc-sandbox] VERIFIED), SCMProvider. Optional: Planner (acceptance criteria), Architect (requirement IDs), Coder, Analyzer (axe-core in the E2E step from expansion stage 10).

**On/off and combination:** On alone: `@agent qa` on any PR. Off: the pipeline takes the existing CI as evidence (`CheckEvidence`).

**DoD:**

| Metric | Test set | Gate |
|---|---|---|
| Filter per delivered test | all | 100% build, pass 5 times, discovery check green, add coverage or kill a mutant |
| Reproduction | Q1 (TDD-Bench Verified Apache-2.0; SWT-bench Verified in unit test mode only internally until the license is clarified) | Gate A against the bare harness with the same model; Gate B: required part on TDD-Bench Verified against the best published value with a comparable model, table with date; rule in [10](10-standards-per-layer.md) sections 1.4 and 7 |
| Mutation score per 1,000 tokens | Q2 | measured, above the bare agent |
| Healer | Q3 | heals selector cases, reports all real bugs, false healing 0 |
| Catch precision | Q4 (injected errors and later fix commits) | share of real bugs among reported candidates not below Meta (8 of 41, [jit]) |
| Unit tests public | Q5 (XRepoTest, code MIT) | above the bare agent |
| Acceptance rate of test PRs | Pilot | measured; Meta's 73% apply only to test-a-thons after filtering ([testgen]) and are not a target |
| Flake rate of new tests | 20 CI runs (estimate) | 0 |

---

## 6. PR Fixer

**Purpose:** Fix review comments, red CI, merge conflicts, analyzer and security findings on a PR without weakening the checks.

**Bar** (derivation [research PR fix and CI](../research/ebene-pr-fix-und-ci.md) section 2): No independent product benchmark; top group by feature set (DERIVED).

| Vendor | Mechanism | Source |
|---|---|---|
| Copilot | Agent Merge "Watch and fix", `@copilot` on any PR, Dependabot alerts to agents | [copilot-merge], [copilot-anypr], [gh-depagent] VERIFIED |
| Cursor Bugbot Autofix | at most 3 attempts, the repo file may only lower the mode, own check only `success`/`neutral`; over 35% merged | [cursor-bugbot] VERIFIED, number [cursor-autofix-blog] CLAIMED |
| Gitar | caused by the PR or not; rerun at most once per commit; recovery ends after 3 own commits | [gitar-ci] VERIFIED |
| Nx Self-Healing CI | auto-apply only with a high verification rate; restart flakes instead of repairing them | [nx-shci] VERIFIED |
| Devin | bot comments ignored by default, allowlist against infinite loops | [devin-bots] CLAIMED |

**Input:** `FixRequest { change, source: review_threads | ci_failure | merge_conflict | static_analysis | dependency_update, scope: thread | review | pr, ids[] }` via `@agent fix`, check button, `ci_failed` on agent PRs (if configured), watch mode. `review_threads` covers threads with `agent_prompt` and human threads without one. `static_analysis` covers SARIF findings, code scanning alerts, and security findings; SonarQube findings not (O19, [10](10-standards-per-layer.md) section 16, ADR-50).

**Output:** `FixResult { outcome: fixed | no_fix_needed | not_caused_by_pr | rerun_requested | cannot_fix | aborted_conflict, commits[], perItem: { id, status, note }[], outOfScopeSuggestions[] }`. `outOfScopeSuggestions[]` contains patch text for workflows, lockfiles, or manifests, never committed. Commit on the agent branch, or a stacked PR for human branches, also in watch mode; the platform never commits to a human branch (O9, ADR-71); a retry on an own stacked PR commits there instead of building a new stack. Reply per thread; own check `ai-fix` only `success` or `neutral`.

**Steps:**
1. **Collect:** open threads or error logs at the head SHA plus CI configuration (read-only); identical errors across jobs only once, runs of outdated commits ignored.
2. **Classify:** `caused_by_pr | flaky | infra | target_branch | unknown`. Only `caused_by_pr` leads to a fix. For `flaky` and `infra` at most one rerun per commit (`propose_rerun`, result `rerun_requested`); for `target_branch` `not_caused_by_pr` with a rationale and 0 code changes.
3. **Run the exact CI command** in the sandbox, reproduce the error.
4. **Fix**, test green, self-check bundle (section 0). **Security and analyzer findings** count as fixed only if the triggering finding is gone on a rescan with the same analyzer version, no new findings at or above the threshold appear, and the tests are green ([gh-autofix] VERIFIED).
5. **Conflicts** as a separate substep: merge simulation in the sandbox, intent of both sides; refusal for security logic and `protected_paths`; all or nothing (one rejected file aborts the whole attempt without a commit); always a merge commit with two parents, never a rebase, not even on agent branches, because the push contract knows no force ([01](01-plugin-interfaces.md) section 5); check for markers, build, and lint.
6. **Prohibitions** (one test each): no change to workflows, lockfiles, manifests, or CI configuration (exception only profile `dependency_update`); no deleted or skipped tests; no lowered thresholds. Necessary changes of this kind go to `outOfScopeSuggestions[]`.
7. **Push** via the gateway with `expectedOldSha`; at most 3 attempts per PR (`max_rounds`).
8. **Wait for real CI:** `fixed` only when the red job is green at the new SHA. Recovery: if an own fix turns a green CI red, that counts as an attempt; after 3 own commits in a row the run ends with a report.
9. **Completion:** reply per thread; threads stay open until the reviewer confirms "Addressed" in the increment.

**Protection against bot-to-bot loops:** The fixer reacts only to comments from humans with write access and from bots in `prfixer.bot_allowlist` (default: the own reviewer). Rounds between reviewer and fixer count together against `max_rounds`; a push by the fixer does not trigger a new fix, only an increment review. When the limit is reached, the run ends with a status comment.

**Profile `dependency_update`** (expansion stage 10): input is a PR from a bot on the allowlist (such as Renovate, Dependabot) with red CI. The agent changes only code; manifest and lockfile are at most regenerated deterministically by the package manager in the worker, only for the packages affected by the update. Delivery by default as a stacked PR on the update branch, because a foreign commit on a Renovate branch stops its maintenance ([renovate-rebase] CLAIMED). Renovate itself is not part of the product (AGPL-3.0, [renovate] VERIFIED; ADR-50).

**Mode `ci_doctor`** (expansion stage 10): red CI on the default branch. Only cause and `propose_issue`; on repetition the same issue is updated; no push (pattern gh-aw "CI Doctor", [gh-aw] VERIFIED).

**Dependencies:** SCMProvider with `CI_LOGS`, ExecutionBackend, AgentRuntime, Analyzer. Optional: Reviewer.

**On/off and combination:** On alone: fixer for human reviews and CI even without AI review. Off: after red CI the pipeline waits for a human.

**DoD:**

| Metric | Test set | Gate |
|---|---|---|
| same problem solved as the human commit | F1 (review findings of own repos implemented by humans; never CodeRabbit findings, O18) | LLM judge plus sample; Gate A: not worse than the bare harness |
| review comment actionable | F1x (one test per comment, red before, green after the human fix) | Gate A; online acceptance rate with reference Bugbot over 35% (CLAIMED) |
| CI green without a forbidden change | F2 (red CI runs of public repos), F2p (CI-Repair-Bench or JetBrains LCA, after license review) | prohibitions 0 violations; Gate B on F2p: report part until the data license, then required part against the best published value (18.9%, [10](10-standards-per-layer.md) section 8) |
| Conflicts | F3 | build and tests green, no conflict markers, otherwise abort without a commit; Gate B open until Merge-Bench is reviewed |
| Breaking dependency update | F4 (BUMP subset, own Renovate cases) | manifest and lockfile only by the package manager; Gate B as in [10](10-standards-per-layer.md) |
| Security and analyzer finding | F5 | finding gone, no new ones, tests still green; Gate B open (no public number) |
| Error not caused | F6 | `not_caused_by_pr` or at most one rerun per commit, 0 code changes |
| Bot loops | Suite | rounds per PR at most `max_rounds` |
| No-op | Suite | "no fix needed" and "no fix possible" correct |

---

## 7. Indexer and knowledge base

**Purpose:** Provide all services with fast, citable context (structure, summaries, search, learnings) and answer questions about the code, without the services depending on it.

**Bar** (derivation [research knowledge, standards, docs](../research/ebene-wissen-standards-doku.md) section 2.1):

| Vendor | Mechanism | Source |
|---|---|---|
| Copilot Memory | facts with citation, check before use, voting, expiry 90 days (7 to 180), repo facts separate from user preferences, secrets rejected | [copilot-memory] VERIFIED |
| Sourcegraph Deep Search, Zoekt | agentic search read-only, notice "sample"; trigram index (Apache-2.0) | [sg-deepsearch], [zoekt] VERIFIED |
| DeepWiki, Devin Knowledge | repo wiki via control file; knowledge with a trigger instead of permanent context | [devin-wiki], [devin-knowledge] VERIFIED |

**Input:** `pushed_default` (merge), schedule `index.full`, L0 version change, thread completion on merge; questions via `@agent ask` and MCP tool `kb.ask`.

**Output:** layer increments in the KnowledgeStore: L0 state per layer (watermark, versions), L1 structure (files, symbols, edges), L2 summaries (symbol, file, module, repo), L3 full text and vectors, L4 rule candidates (for `standards`), L5 learnings. Event `kb.updated { repo, layer, watermark }`. MCP read tools `repo_map`, `symbol_context`, `impact`, `search`, `standards`, `learnings`, `module_summary`, `ask`.

**Steps:** increment chain per merge: changed files since the watermark; L1 with re-resolution of edges; L2 only for the dirty set, upward only when a child summary changed; L3 only new content hashes; L5 harvest of the threads of the merged PR; watermark only after success; rebuild on an unreachable watermark or a version change. Full analysis via `ModelProvider.submitBatch`.

**Ask flow:** `AskRequest { repo | org, question, scope }` to `AskAnswer { answer, citations[], confidence, searchedQueries[] }`. Agentic search read-only via `kb.*` plus grep; citation check as in planner step 6; an answer without a valid citation is not output; notice "sample, not exhaustive".

**Lifecycle of learnings:**
- **Scope** `repo | org | auto`; default `auto`: public repos see only their own learnings, learnings from public repos do not flow into private ones.
- **PR-bound:** learnings from an open PR apply only to this PR until the merge.
- **Approval delay** `approval_delay_days` (starting value 0) with an approval view in the admin UI.
- **Voting** from finding reactions and explicit confirmation; below a threshold no longer used.
- **Expiry** `expiry_days` (starting value 90, range 7 to 180, reference Copilot); only confirmation extends, retrieval does not.
- **Kinds** `repo_fact | user_pref`; reviewer and PR fixer use only repo facts.
- **Secret redaction** before storage and embedding (gitleaks rules, type markers), with a test.
- **Import and export** CSV and JSON, only by those with write access; import from CodeRabbit CSV as a separate adapter. Imported content is `Untrusted` ([05](05-security.md)).
- **Metrics** `uses`, `last_used`, `never_used`, voting; view in the admin UI.
- Only from humans with write access, with citation and `invalid_at`; citation check before every output.

**Quality mechanics:** Every stored value carries the version of the rule that wrote it (`prompt_v`, `parser_v`, `model`); a version change forces a rebuild. Embedding models only with a license that allows redistribution and commercial use (ADR-50).

**On/off:** Off: all services work agentically with grep and reading, the MCP tools `kb.*` answer `unavailable`. The KB becomes active for a service only when it improves or cheapens that service's eval.

**DoD:**

| Metric | Test set | Gate |
|---|---|---|
| Recall@10 of files and symbols | K1 (from C1p and R1) | Gate A: review and coder with KB better or cheaper than without |
| Context retrieval file and span F1 | K3 ContextBench verified (code Apache-2.0, data license open, download only) | Gate B report part, required part after license clarification ([10](10-standards-per-layer.md) section 9) |
| Repo Q&A | K4 SWE-QA and DeepCodeBench (both Apache-2.0) | Gate B: judge score against the best self-re-measured reference agent (claude-code; codex-cli in the project only with published values, O28) under the same judge, rule in [10](10-standards-per-layer.md) sections 1.4 and 9; vendor values only for orientation |
| Citation validity | K2 (questions per repo of the installation, optional), K4 | 100% (mandatory property, no Gate B) |
| Learnings | Suite | secret redaction, expiry, scope `auto`, and PR binding, one test each green |
| Increment chain equals rebuild | Test | green |
| Watermark failure path | Test | layer stays put, next run catches up |

This way Gate B measures against published references instead of against a property (resolves M5 for the indexer).

---

## 8. Standards

**Purpose:** Read guidelines from all common formats, derive team rules from accepted feedback, measure per rule, and propose rules as versioned files.

**Bar** (derivation [research knowledge, standards, docs](../research/ebene-wissen-standards-doku.md) section 2.1 c):

| Vendor | Mechanism | Source |
|---|---|---|
| AGENTS.md | open format, nested, nearest file wins | [agentsmd] VERIFIED |
| Qodo Rule Miner | only accepted comments with a code change, ownership weight, window about 1,000 PRs, first up to 10 rules, then every two weeks up to 5; weakening on rejection | [qodo-miner] VERIFIED |
| Bugbot, Greptile | metrics per rule (acceptance rate, addressed rate), `verbose` output of the rules used, switching off inherited rules by ID | [cursor-bugbot], [greptile-std] VERIFIED |

**Guideline loader** (always runs, even with `standards.mode: off`): reads at the base SHA AGENTS.md, AGENT.md, CLAUDE.md, `.claude/rules/**` (with `paths`), GEMINI.md, `.cursorrules`, `.cursor/rules/*.mdc` (`globs`, `alwaysApply`, `description`), `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md` (`applyTo`), `.windsurfrules`, `.clinerules/*`, `.greptile/`, `.cursor/BUGBOT.md`, `.coderabbit.yaml` (only `path_instructions`), and `.agents/rules/`. Scope from the file's own directory downward, nearest file wins; inherited rules can be switched off by ID; budget per run with a report of the truncated sources in the Run Record and via `@agent review verbose`. Contents count as rules from the base SHA, never as an instruction from the head (ADR-17); Copilot by contrast reads from the head ([copilot-instr] VERIFIED), we deliberately do not.

**Input:** schedule every two weeks (starting value, reference Qodo), L4 candidates, review threads with acceptance and rejection, accepted fixes, existing guidelines, findings confirmed by humans that only the model found.

**Output:** one rule PR per repo on `.agents/rules/*.md` in AGENTS.md-compatible format; per rule glob, rationale, origin PR, verbatim quote, support count, contradiction. Withdrawal PRs for rules with persistently rejected findings. **Rule compilation:** a confirmed finding that only the model found is proposed as an Opengrep or ast-grep rule with a positive and a negative test case.

**Rule metrics** per `rule_id`: findings, PRs, accepted, addressed rate. Below a threshold the rule weakens (decay) and the service proposes its withdrawal.

**Steps:** candidates following the Rule Miner pattern, dedupe against existing rules, limit per run (starting values following Qodo), PR to CODEOWNERS. Valid only after merge; automatic activation only via the switch `standards.auto_activate` per installation, default off (O10).

**On/off:** Off: rule files maintained by hand; the guideline loader keeps running, reviewer and coder read them from the base SHA.

**DoD:**

| Metric | Test set | Gate |
|---|---|---|
| Effect | R1 and R3 with and without rules | Gate A: "rules do no harm" ([10](10-standards-per-layer.md) section 10); gain greater than 0 reported as a goal |
| Addressed rate of rule-based findings | R1, online | Gate B: at least equal to the addressed rate of the reviewer without a rule reference. A published reference value of a vendor is missing; the external part of Gate B is therefore open (resolves M5 as an explicit marking) |
| Guideline loader | Suite | every format from the list with a fixture; scope per directory; base SHA instead of head |
| Origin | Test | every active rule with origin PR and citation |
| Rule compilation | Suite | every proposed rule with positive and negative test case green |
| Withdrawal | Test | a rule with persistently rejected findings is proposed for withdrawal |

---

## 9. Triage

**Purpose:** Classify every new or changed issue: duplicates and related items with citation, labels, assignees, repo assignment, spam and slop classification, clarity. Entry point of the autonomous run and protection of public repos against outside noise (ADR-46).

**Bar** (derivation [layer map](../research/ebenen-landkarte.md) section 2.2 E1):

| Vendor | Mechanism | Source |
|---|---|---|
| Linear Triage Intelligence | per property "shown, hidden or auto-applied", guidance per team, the most local carries the most weight | [linear-triage] VERIFIED |
| GitHub Agentic Workflows "Issue Triage" | read-only, writing only via declared outputs (comment, labels) | [gh-aw] VERIFIED |

**Input:** `TriageRequest { item, trigger }` via `opened`, `edited`, `@agent triage`, schedule for follow-up runs.

**Output:** `TriageArtifact { duplicates[] (with citation and similarity), related[], labels[], assignees[], repo?, spam: none | spam | slop, clarity: ok | questions, rationale }`. Comment plus `propose_labels` and `propose_link`; event `item.triaged`, which `ticket-to-pr` can use as input.

**Steps:**
1. **Gate:** bot, own output, already triaged at the same state.
2. **Search** without a shell: vector and full-text search over issues and PRs from the KnowledgeStore; without a qualified indexer only labels and clarity, no duplicates. Search covers only sources that every reader of the issue is allowed to see: on a public repo only public issues and PRs, even with `CROSS_REPO` ([05](05-security.md) section 7, ADR-63).
3. **Classification** with a small model: labels according to `labeling_instructions`, assignees from CODEOWNERS and history, repo assignment, clarity gate (shared library with the planner).
4. **Spam and slop** as a classification with rationale; consequence only a label or hiding the comment, according to the configuration.
5. **Verifier:** every named duplicate exists and is cited; labels only from the repo's list.
6. **Publish** per property according to `triage.<property>: suggest | auto_apply | off` (Linear pattern).

**Closing only as an option:** The default is that `triage` does not close; duplicates and spam are marked and linked. Automatic closing is an option (O25 decided): `auto_close: true` as a repo opt-in, effective only after a green eval T1 of this repo, platform default off ([04](04-configuration-and-limits.md)); every closing carries a comment with the reason and can be reopened. Issue text from outside users is `Untrusted` (suite S1).

**Dependencies:** WorkItemProvider or SCM issues with `SET_LABELS`, `LINK_ITEMS`. Optional: KnowledgeStore (duplicates).

**On/off and combination:** Default `off`. In `ticket-to-pr` the first step with `on_disabled: skip`; spam or slop ends the run with `Skipped(triage_rejected)` and a note.

**DoD:**

| Metric | Test set | Gate |
|---|---|---|
| Duplicate precision and recall | T1 (public repos with duplicates marked by maintainers; private per installation optional) | Gate A: above a simple prompt with the same model |
| Label adoption | T1, pilot | label agreement with maintainers measured; adoption rate online |
| Spam and slop | T2 (planted cases) | false alarms on real issues reported, threshold after the first run |
| Closing | Suite | 0 automatic closings |
| Duplicate F1 external | T1 | Gate B required part once the license of gh-aw is VERIFIED (until then report part): no significant gap against the "Issue Triage" workflow of GitHub Agentic Workflows, re-measured ourselves with the same model ([10](10-standards-per-layer.md) section 12); no comparison with CodeRabbit Issue Enrichment (O18) |

---

## 10. Docs

**Purpose:** Keep documentation current: docstrings for touched symbols, docs sync after merge, release notes. The indexer writes to the KB, `docs` writes to the repo (ADR-46).

**Bar** (derivation [research knowledge, standards, docs](../research/ebene-wissen-standards-doku.md) section 2.1 e and [layer map](../research/ebenen-landkarte.md) E13, E14):

| Vendor | Mechanism | Source |
|---|---|---|
| Mintlify Autopilot, gh-aw docs updater | check on PR, docs proposal after merge, docs PR without auto-merge | [mintlify] CLAIMED, [gh-aw] VERIFIED |
| DocAgent | docstrings in topological order, truthfulness via the dependency graph | [docagent] CLAIMED |
| GitHub release notes, release-please, git-cliff | release notes deterministically from Conventional Commits and labels | [relnotes] CLAIMED |

**Input:** `DocsRequest { mode: docstrings | sync | release, change? | range? }` via `@agent docs [docstrings | sync]`, `@agent release`, `pushed_default` (only `sync`), check on PRs (drift).

**Output:** `DocsArtifact { mode, patches[], driftFindings[], releaseNotes? }`. Follow-up PR against the originating branch or the default branch (fallback chain: comment for SCMs without a branch workflow). Check `docs-drift` only `success` or `neutral`, never blocking without configuration.

**Steps:**
1. **Drift check** on PRs: code references in docs (paths, symbols, examples) are checked against the head; broken references are findings with citation.
2. **Mode `docstrings`:** touched symbols without a docstring via ast-grep; style from existing docstrings; order by L1 dependencies; build and linter green.
3. **Mode `sync`:** after merge a docs proposal for touched docs locations from `docs.paths`, as a docs PR, never auto-merge.
4. **Mode `release`:** version, date, and breaking list deterministically from Conventional Commits and labels via a tool as `Analyzer` (git-cliff or release-please, license in the manifest, unverified); the model writes only the reading text; the verifier checks every line against a PR and lets no invented version or invented date through.
5. **Verifier:** every named entity exists in the code (L1), every sentence of the release notes has a PR.

**Dependencies:** SCMProvider, ExecutionBackend (build for docstrings), Analyzer. Optional: KnowledgeStore (L1, L2).

**On/off:** Default `off`; every mode switchable individually (`docs.modes`).

**DoD:**

| Metric | Test set | Gate |
|---|---|---|
| Drift check | DO1 (public repos: merged PRs with a docs change against those without) | Gate A: precision above a simple prompt |
| Repo docs | DO2 CodeWikiBench (after license review) | Gate B report part with guide value DeepWiki 64.06% (CLAIMED [codewiki]); required part after license clarification ([10](10-standards-per-layer.md) section 11) |
| Docstrings | DO3 (DocAgent method) | build 100% green; 0 invented entities |
| Release notes | DO4 (own cases) | 0 lines without a PR, 0 invented versions or dates, breaking list complete |

---

## 11. Combinations (examples)

| Combination | Services on | Typical trigger |
|---|---|---|
| Review replacement | reviewer (+ indexer, standards) | PR opened |
| Fix assistant for human PRs | prfixer (+ reviewer) | `@agent fix` |
| Planning without coding | planner (+ architect) | `@agent plan` in the ticket |
| Design review | architect | architecture PR, `@agent architect review` |
| Ticket to PR | triage, planner, architect, coder, reviewer, qa, prfixer | `@agent code` in the ticket |
| Ticket to merge, autonomous | triage, planner, architect, coder, reviewer, qa, prfixer, merge gate | ticket with label `agent:auto` or mention, `autonomy: full`, `merge.mode: auto` ([03](03-flow-and-orchestration.md) section 1a) |
| Test assistant | qa | `@agent qa` |
| Knowledge only | indexer | `@agent ask` in the PR or ticket |
| Maintainer assistant | triage (+ indexer) | issue opened |
| Docs maintenance | docs (+ indexer) | merge to the default branch, `@agent docs`, `@agent release` |
| Incident handoff | coder, prfixer (+ reviewer) | TriggerSource `sentry` (Seer webhooks) or generic `incident-handoff` (signed webhook with cause, plan, links); no separate SRE agent (ADR-49, [sentry-fix] VERIFIED); expansion stage 10 |
| Dependency repair | prfixer (profile `dependency_update`) | red PR from a bot on the allowlist; expansion stage 10 |
