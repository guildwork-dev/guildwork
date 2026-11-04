<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# 10 Standards per Layer

Source keys and classifications as in the [README](README.md) section 6. This file answers the project goal "every layer works at the level of the worldwide standard of its field". For each layer it defines: who the standard is, which capabilities it has, which of them the platform gets and when, and how Gate A and Gate B are measured. The level is a **measurement goal, not a build condition** (ADR-56): results are published measured and honest, including "Gate B red" or "not decidable", and only on sets that can distinguish the level (section 1.5); Gate B never decides about the build (section 1.2 item 6, ADR-55). The test sets themselves (structure, origin per case, judges, harness) are in [07](07-eval.md); here are only name, license, size, metric, reference value, and rule. The services themselves are described in [02](02-services.md), the expansion stages in [08](08-roadmap.md).

The basis is the research of 2026-10-31 in `docs/research/` (dated, not binding). Evidence is kept there in detail; this file refers to it by section and does not repeat it. "available" in the tables means: described in the architecture, not built. Standard descriptions and capability rows that relied only on the evaluation of CodeRabbit or SonarSource documentation are deleted under O18 and O19 respectively; where other vendors evidence a capability, the row names only those (section 16).

## 1. Rules for all layers

### 1.1 Terms

- **Standard of the field:** the vendor or method against which the field measures itself. Where there is no single leader, a **leading group** is given. The classification states whether the leadership is evidenced (measurement, analyst report) or only derived (feature set, adoption).
- **Gate A:** not worse than the bare harness with the same model and a simple prompt, without the platform. Gate A proves that the platform does not make anything worse.
- **Gate B:** level of the standard, measured against an externally comparable reference. Gate B consists of **required parts** (measurable, with reference value, margin, and minimum power according to section 1.4) and **report parts** (measured and reported, without a threshold, because a reference or license is missing). Its status per service and part is **green**, **red**, **not decidable**, or **open** (section 1.2 item 6); it controls only `live` and the merge gate.
- **Reference value:** number against which Gate B measures. Three kinds are allowed: (a) values published by third parties on open benchmarks, (b) own remeasurement of an open reference agent or tool with the same model, (c) published definitions (such as the C4 checklist, MADR) or own published named values against which parity is checked.
- **Reference qualification:** qualification matrix published by the project per release (ADR-52), which an installation may adopt (section 1.2).

### 1.2 When a service may go `live` (ADR-47)

1. `mode: live` requires, for the qualification profile in use (`qualification_key`: harness, credential kind, provider, all models per role, `prompt_v` per step, plugin versions, marked config keys; library calls inherit the profile of the caller; [07](07-eval.md) section 2, ADR-66):
   - Gate A green, the required suites S1 to S6 from [07](07-eval.md) green, and
   - all required parts of Gate B green **or** an adopted reference qualification.
2. **Adopting a reference qualification:** allowed if the platform release and qualification profile are the same (item 1; the quality-relevant configuration values such as router thresholds, filters, and profiles are included in it via the schema marking). The credential kind may differ within the same provider (comparison without the field `credential_kind`; DERIVED: same model at the same endpoint; to be confirmed by the contract test in stage 1). After adoption, the installation re-measures Gate A in shadow mode on its private set; if it fails there, the policy automatically sets the service back to `shadow`; the same applies if the continuously measured online metric falls significantly below the reference value ([07](07-eval.md) section 2.1).
3. **Gate B per part or scope:** If a service has parts with their own Gate B (such as QA scope `e2e`, PR fixer source `merge_conflict`), the rule applies per part. A part without a green required part may not run `live`, even if other parts of the service may.
4. **Deviation:** only via configuration of the installation (keys in [04](04-configuration-and-limits.md), not in repo files, because otherwise a PR could override the rule), with a mandatory justification. The deviation is visible everywhere: admin UI, status comment, and check summary carry "standard not proven", the Run Record stores reason and actor, the audit log the switch.
5. A service whose Gate B has no required part today (section 2, column "Gate B today") can only go `live` via a deviation. This is intended: the gap becomes visible instead of hidden.
6. **Done criterion of an expansion stage** (ADR-55, applies to every stage in [08](08-roadmap.md)): A stage is done when its components are built, the suites required for it from [07](07-eval.md) section 5 and Gate A of its services are green, and Gate B is measured and reported per service and part (item 3). Gate B decides only about `live` (items 1 to 5) and the merge gate ([03](03-flow-and-orchestration.md) section 1a condition 2), never about whether building continues. The stage report and the reference qualification (ADR-52) carry exactly one status per service and part:
   - **green:** every required part passes according to section 1.4; stage "done".
   - **red:** at least one required part is decidably missed according to section 1.4; stage **"done, Gate B red"**. Fix rounds for the service run alongside the subsequent stages.
   - **not decidable:** no required part red, but at least one not decidable according to section 1.4 (minimum power missed, saturated set, reference value not readable, estimated threshold before the first run); stage **"done, Gate B not decidable"**.
   - **open:** for the service or part there is not yet a required part on a set with an evidenced license (section 1.5); stage **"done with Gate B open"**. The license clarification that makes the required part possible is listed as an owner step in the done criterion of the stage (a request to the authors has an external effect).

   With red, not decidable, and open, the service may not go `live` under item 4 without the operator deviation, and it never counts in the merge gate. None of these statuses blocks a subsequent stage. Gate A, by contrast, is part of the done criterion: a not decidable Gate A is decided by enlarging the own set, because own sets are in the hands of the project.

This rule thus replaces the earlier rule "A service without a measurable Gate B counts as qualified with Gate A" (correction to [07](07-eval.md) section 4, see section 17) and the version up to 2026-10-31, under which every Gate B required part had to be green for the done criterion (Red Team on the overall idea, finding 1; ADR-55).

### 1.3 Reference values and classification

- A threshold rests on a VERIFIED value or an own remeasurement. A CLAIMED value (vendor figure on its own data) may only be an **indicative value**: it is reported and compared, but does not block as long as no VERIFIED value exists.
- Every reference value carries date, source, version of the leaderboard or file, and classification. References from leaderboards are re-read or recomputed from the raw file on every gate run.
- Values from online leaderboards never count as a reference for offline sets and vice versa.

### 1.4 Statistics

These rules apply to every "not worse", "no significant gap", and "not below" in Gate A and Gate B, here and in [02](02-services.md) and [07](07-eval.md) (ADR-56). Other files only refer here.

- **One-sided non-inferiority test:** The difference D = own value minus reference value (reversed for metrics where less is better, such as false positives) is compared with its two-sided 95% interval (one-sided 2.5%). A part **passes** if the lower bound of D lies above minus the margin.
- **Margin per part:** stated explicitly in the column "Rule" of the tables. Where none is given, **5 percentage points** applies for Gate B and **10 percentage points** for Gate A (both starting values, estimate; Gate A thus fits the set size from [07](07-eval.md) section 1.1). Margins are fixed before the first run and never changed after the own result; a change is a change of this file (section 1.6). Deterministic rules (100%, 0 violations) have no margin.
- **Minimum power:** A part that does not pass is red rather than not decidable only if the half width of the 95% interval of D is at most 0.7 times the margin (a passing part is green even without it, item "Decision"; detailed design 07 FE-711) (corresponds to about 80% power at the same true value, DERIVED: (1.96 + 0.84) × standard error ≤ margin). Before the run, the required size is estimated from [07](07-eval.md) section 1.1; afterwards the measured interval applies.
- **Decision:** A part is **not decidable** in advance if its reference value cannot be read (section 1.3), if its set is saturated for this part (section 1.5), or if its threshold is still an estimate (next item). Otherwise it is **green** if it passes (even with missed minimum power), **red** if the upper bound of D lies below minus the margin or the minimum power is reached and it does not pass, and **not decidable** in all other cases.
- **Estimated thresholds:** An absolute threshold with the note "starting value, estimate" (such as reviewer precision 55%, security precision 70%) is binding only after the first run. Until then the value is reported. After the first run, the project sets the threshold with a justification from reference values and measured variance, not from the own result, and enters it here.
- **Cluster bootstrap:** Intervals are drawn over the independent units: whole PRs (review), tasks (coding, QA, PR fix), issues (triage). Comments or findings of the same PR never count as independent. For paired comparisons (Gate A; reference with results per case, such as Martian per PR and tool), both arms are drawn together. If the reference exists only as a published number, it counts as fixed; this is stated as a limitation in the report. With several runs per case (ReviewBench: three), the mean per case counts.
- **Example** (own recalculation from `benchmark_dashboard.json`, 2026-10-31, VERIFIED [mcr-repo]): Martian offline has 158 golden comments (tp plus fn) in profile `core`, not 173. The cluster bootstrap over the 50 PRs yields F2 47.7 with about plus or minus 8.7 points for Claude Code (CLI), and about minus 11.9 to plus 5.2 for the paired difference to CodeRabbit. With a margin of 5 points, B1 alone is therefore only decidable if the candidate lies clearly above the reference; this is why the reviewer combines several required parts (section 3).
- Sample sizes and the goal "resolve 10 percentage points" are governed by [07](07-eval.md) section 1.1.

### 1.5 Data sets and licenses (ADR-52)

- Required parts of Gate B use only public sets with a verified license (classification VERIFIED; a CLAIMED statement is not enough). The same applies to open reference tools that are re-measured for a required part. The project ships adapters and download scripts with a pinned commit, no copies of the data.
- Sets without a verified data license may be measured internally if their terms of use do not exclude this; results are published only after license clarification. Until then the part counts as a report part.
- Sets with a noncommercial license (such as CC BY-NC) are never a required part.
- Outputs of CodeRabbit and SonarQube (`vendor_output`) are permanently barred as eval data (O18, O19 decided: not connected, no request; section 16).
- Private sets per installation (own repos, own labels) serve Gate A and the remeasurement according to section 1.2, never the published reference qualification.
- **Discriminating power (ADR-56):** A required part stands only on a set that can distinguish the level:
  - **not saturated:** If the reference value or the comparison arm lies above about 90% (starting value, estimate), the set evidences no level. It may then only carry a named non-degradation against the same harness (coder B1); a benefit or superiority part is not decidable there.
  - **without solution leak:** Inputs do not reveal the truth (such as function names, comments, file names with the error class). A set with a leak is cleaned before the run, a test checks the cleaning; otherwise it is only a regression or report set (Juliet, section 13).
  - **neutral judge:** If a benchmark prescribes several judges, the part must pass under each of them; the judge least favorable to the candidate counts, with reference values per judge from the same file. If a model of the candidate's family co-produced the truth, scoring is additionally done without these producers (ReviewBench, section 3). **Project deviation (O28):** The project uses only Claude; it scores under the Claude judges of a benchmark and omits judges of other vendors (R2: without GPT-5.2). The eval report names the omitted judges, the part then counts as "measured under the Claude judges" and is not 1:1 comparable with the leaderboard. An installation with access to all judges scores under all of them.
  - **Contamination:** Per run the report states the producer mix of the truth, the judge family, and whether the training cutoff of the candidate model lies after the publication of the set.

### 1.6 Expiry

A stored gate status is valid only as long as the rule and the reference under which it was created are valid. It expires with a new leaderboard version of the reference, with a change of harness, model, prompt, plugin version, judge, or platform release, and with a change of this file. The regression run from [07](07-eval.md) section 2 then measures again.

### 1.7 Cost of measurement

Full Gate B runs cost inference. For the coder, the research estimates per combination about 170 to 670 USD for a regression run with about 120 tasks and 1,500 to 6,000 USD for the full basket (estimate from the average cost per task in the OpenHands Index of 1.44 to 5.54 USD, [oh-index-api]; [`ebene-coding`](../research/ebene-coding.md) section 3.3). There is no budget cap (O22 decided): full baskets may run at any time, regression subsets remain the standard per PR because they are faster; budget alarm only as a measurement. The project measures via the Owner's Claude subscription (O28): no USD per run is incurred, throughput is limited by the usage limits of the subscription (only visible reactively, [05](05-security.md) section 6 requirement 6); the USD estimates apply to installations with API billing. Limits are measured before and after every run ([07](07-eval.md) section 1).

## 2. Overview

| Layer | Standard or leading group | Service | Gate B today | Section |
|---|---|---|---|---|
| Review | Volume: GitHub Copilot code review; accuracy: leading group Qodo, cubic, Augment (offline), cubic, Greptile, CodeRabbit, Copilot (online) | `reviewer` | required parts measurable (Martian offline, ReviewBench) | 3 |
| Planning | Kiro and Spec Kit, Jules Planning Critic, Factory Spec Mode (DERIVED) | `planner` | required parts measurable (Loc-Bench, "plan does no harm" on a non-saturated set) | 4 |
| Architecture and design | Methods arc42, C4, ADR, STRIDE, EARS; AI: STRIDE GPT, Threat Designer | `architect` | partial (method conformance, threat model against STRIDE GPT) | 5 |
| Coding | Core: Claude Code, Codex; shell: Copilot cloud agent, Devin, Cursor | `coder` | required part measurable (SWE-Bench Pro V2 Full as non-degradation; level only with SWE Atlas and SWE-rebench after license verification) | 6 |
| QA | per subfield: SWT-bench top, Meta, Playwright, Google | `qa` | reproduction measurable (TDD-Bench Verified); SWT-bench after license clarification; E2E open | 7 |
| PR fix and CI | Copilot, Bugbot, Nx, Gitar | `prfixer` | open until license clarification of the sets | 8 |
| Knowledge base | Sourcegraph, Augment, Cursor; DeepWiki; Copilot Memory | `indexer` | required part measurable (SWE-QA, DeepCodeBench) | 9 |
| Standards and Learnings | AGENTS.md; Qodo Rule Miner; Bugbot, Greptile | `standards` | parity plus relative measurement | 10 |
| Docs | Mintlify, Swimm, DeepWiki, release-please, git-cliff | `docs` | open until license clarification | 11 |
| Triage | Linear Triage Intelligence, gh-aw Issue Triage | `triage` | open until license verification of gh-aw, then required part against the re-measured reference workflow | 12 |
| Static analysis and security | Gartner Leader AST, CodeQL, Opengrep; AI: Claude Security, Codex Security | plugin kind `Analyzer`, `reviewer`, `prfixer`, `architect` | required parts measurable (own gate values, real CVE pairs from OpenSSF CVE Benchmark and CWE-Bench-Java); Juliet only cleaned as a regression set | 13 |
| Autonomous pass, auto-merge | Copilot Agent Merge with auto-merge | orchestrator, merge gate | suite S7 plus shadow comparison | 14 |
| Edge layers | Renovate, gh-aw CI Doctor, Sentry Seer, axe-core, Infracost, OpenRewrite | plugins and inputs | via the carrying service | 15 |

## 3. Review (`reviewer`)

**Standard** ([`ebene-review`](../research/ebene-review.md) sections 1, 2.1, 2.3):
- The volume standard is **GitHub Copilot code review** ("more than one in five code reviews on GitHub", CLAIMED [gh-60m]).
- Accuracy: no single leader, but a leading group. Offline on Martian (profile `core`, F2) Qodo Extended 65.1%, cubic v2 64.9%, Augment 64.0% (own recalculation from the MIT data, VERIFIED [mcr-repo]); online cubic 64.9% F1 on 2026-10-06 (CLAIMED [tns-rb]). The gaps at the top lie within statistical noise (DERIVED).
- Bar: **feature set according to the capability table below, accuracy like the leading group.**

**Capabilities** (condensed from the checklist in [`ebene-review`](../research/ebene-review.md) section 3; dropped numbers are noted there):

| Capability | Standard vendor | Our service, location | Status |
|---|---|---|---|
| Automatic review on open, push, ready; filters | Copilot, Bugbot | `reviewer`, `routing` in 04 | available, stage 1 |
| Incremental since the last reviewed SHA | Bugbot | `reviewer` increment | available, stage 1 |
| Inline findings with severity, category, suggestion | all | `reviewer` finding schema | available, stage 1 |
| Ticket fulfillment per requirement | Qodo, Copilot | `reviewer` finder `ticket` | available, stage 1 |
| Block merge on open findings | Bugbot | check `ai-review` | available, stage 1 |
| Path instructions, rules from the base SHA | Copilot, Bugbot | 04 section 2 | available; deliberately base instead of head (Copilot reads from the head, [gh-ccr-doc]) |
| Fix prompt per finding | Greptile, Bugbot | `agent_prompt`, `prfixer` | available; handover to third-party agents via MCP stage 6 |
| Cost per review disclosed | Copilot, Greptile | ledger | available |
| Walkthrough, change table, effort, diagrams | Greptile | `reviewer` companion features | stage 6 |
| Chat in the PR, `pause` and resume via `review`, selectable strictness levels | Copilot, Greptile | `reviewer`, commands in 03 | stage 6 |
| Local review via CLI and IDE, machine-readable output | Greptile, cubic, Bugbot | reviewer as a library plus CLI | stage 6 |
| Developer MCP (open findings, report as fixed) | Greptile, cubic, Qodo | platform MCP | stage 6 |
| Review analytics with export | Greptile | admin UI | stage 6 |
| Automatic approval with risk cap | Greptile, cubic | `reviewer` | option, platform default off (O24 decided, `services.reviewer.auto_approve`), stage 6 |
| Learnings, `remember` | Bugbot, Greptile | `standards`, `indexer` | stage 6 (`@agent remember`, creation), sub-stage 7a (lifecycle, retrieval) |
| Multi-repo context | Greptile, cubic | `indexer` `CROSS_REPO` | stage 7 |
| Multiple code hosts | Greptile | SCM plugins | GitHub stage 1; GitLab, Azure DevOps, Bitbucket, Gitea stage 9 |
| Ensemble of several runs | Copilot | `reviewer` optional for P0 | partial; active only with an eval gain |
| Review queue and own review interface | cubic | none | deliberately not in stages 0 to 10: own UI product area without effect on accuracy; reassess after analytics |

**Gate A and Gate B** (sets in [07](07-eval.md); derivation [`ebene-review`](../research/ebene-review.md) section 4):

| Part | Data set (license, size) | Metric | Reference value (source, classification) | Rule |
|---|---|---|---|---|
| Gate A | R5: SWE-PRBench (CC-BY-4.0, 350 PRs, [swe-prbench-hf]) and AACR-Bench (Apache-2.0, 200 PRs, 1,505 comments, [aacr-gh]) | recall against human review feedback | bare Claude Code with a simple review prompt, same model | not worse |
| Gate A | private set of the installation (R3) | precision, rated by hand | bare harness | not worse |
| B1 required | R2 Martian offline (MIT, 50 PRs, 173 golden comments, of which 158 in profile `core`) | F2 in profile `core`, micro average, under **all three judges** of the file (Claude Opus 4.5, Claude Sonnet 4.5, GPT-5.2); the project scores only under the two Claude judges (O28, section 1.5), the report shows this as a deviation | per judge: CodeRabbit 51.1 / 50.9 / 48.9%, top Qodo Extended 65.1 / 56.8 / 59.3%, Claude Code (CLI) 47.7 / 40.1 / 40.9% (own recalculation from `benchmark_dashboard.json`, retrieved 2026-10-31, VERIFIED [mcr-repo]) | required: not worse than CodeRabbit with a margin of 5 points under every judge (the one least favorable to the candidate counts, section 1.5), paired over the PRs; goal: not worse than the top. Recompute the reference per run and judge from the current file. Reason: the gap of Claude Code to CodeRabbit is 3.4 points under Opus 4.5, but 10.8 under Sonnet 4.5 and 8.0 under GPT-5.2; a single judge would determine the result. Without GPT-5.2 (project, O28), Sonnet 4.5 with the largest gap remains in the set, so according to these values the least favorable judge is not missing |
| B2 required | R2 | precision `core`, judges as B1 | per judge: CodeRabbit 32.6 / 33.8 / 28.6%, top 67.1 / 56.2 / 58.4% (Qodo Extended, VERIFIED as B1) | at least 55% (starting value, estimate; binding only after the first run, section 1.4), so that B1 is not reached only via recall |
| B3 required | R4 ReviewBench (MIT, 219 PRs from 187 repos, 19 languages, 2,623 TP findings, [rb-readme]) | grounded recall and F1 on the full golden set as on the leaderboard, judge as on the leaderboard (Claude Sonnet 5), three runs; in addition per run leave-producer-out without `ccr:` and, if the candidate model comes from the Claude family, without `llm_review:claude` (46.0% of the golden TPs) and `ccr:claude` (8.7%) ([rb-method] section 5.5, retrieved 2026-10-31, VERIFIED) | Copilot Balanced 40.1% grounded F1 (CLAIMED [tns-rb], vendor of the first-placed entry); leaderboard not read ourselves (unverified). Leave-producer-out values are according to [rb-judging] diagnostic only and not comparable with the leaderboard (VERIFIED) | not worse than the best listed value with a margin of 5 points; read the value from the leaderboard before the first run, otherwise not decidable. If the candidate's leave-producer-out value falls more than the margin below its full value, B3 is at most "not decidable" (advantage through overlap with the producers not excluded, section 1.5) |
| B4 report | own repos, online | address rate and recall according to the Martian definition (ETL in the repo, MIT) | Martian online: cubic 64.9% F1 (2026-10-06), Greptile 60.8% F1 (2026-07-30) (both CLAIMED [tns-rb], [greptile-martian]) | report; threshold only with an entry in the Martian tracker (O23); a comparison with CodeRabbit on the same repos is dropped (O18) |
| B5 report | R2, R4 | comments per PR, share of silent runs, duration, cost | Copilot 5.1 comments per review, 29% silent (CLAIMED [gh-60m]); cost per level 0.25, 1.50, 10 USD (VERIFIED [gh-ccr-doc]) | report |
| Companion features | own cases from public repos | deterministic checks | none needed | walkthrough: 100% of the named files in the diff; diagram: 100% parsable, 0 invented participants; pre-merge checks: 0 misjudgments on the suite; local review: P0/P1 fingerprints at least 90% equal to the PR review (starting value, estimate) |

Required parts: B1, B2, B3 together; the status of Gate B follows section 1.2 item 6. B1 alone is often not decidable because of the interval of about plus or minus 8.7 points (cluster bootstrap over 50 PRs) (section 1.4).

## 4. Planning (`planner`)

**Standard** ([`ebene-planung-und-architektur`](../research/ebene-planung-und-architektur.md) sections 1, 2.1): No single world standard and no independent product comparison. Leading group by function and disclosure (DERIVED): **Kiro** and **GitHub Spec Kit** for specification-driven planning (VERIFIED [kiro-specs], [speckit-repo]); **Jules Planning Critic** with the only published measurement, 9.5% fewer task failures (CLAIMED [jules-changelog]); **Factory Spec Mode** for control after approval (VERIFIED [factory-spec]).

**Capabilities** (condensed from the checklist there, section 2.4, dropped numbers noted there; items on specification and design see section 5):

| Capability | Standard vendor | Our service, location | Status |
|---|---|---|---|
| Plan via command and automatically under conditions | Jules, Copilot | `planner`, 03 triggers | available, stage 2 |
| Research with code citations, citation check | Devin, Cursor | `planner` | available, stage 2 |
| Questions instead of a plan when unclear | Jules, Spec Kit `clarify` | clarity gate | available, stage 2 |
| Autonomy on approval, upper limit per installation | Factory | `max_autonomy` | available |
| Plan critique for automatically approved plans | Jules | `planner` plan critique | available |
| Cost estimate before approval | none evidenced | `estimate`, `auto_if` | available, above the standard |
| Approval after timeout without an answer | Jules (CLAIMED) | none | deliberately not: waving through contradicts the approval model in 03 |
| Plan from a free description, PRD, or image | Kiro, Cursor | `planner` input `brief` | stage 2 |
| Consistency analysis of ticket, plan, tasks; check project principles | Spec Kit `analyze`, `constitution`; Kiro | `planner` | stage 2 |
| Human edits the plan, new version | Claude Code, Cursor | `planner` | stage 2 |
| Task dependency graph, parallel waves | Kiro, Spec Kit | `planner`, `architect` | stage 2 |
| Plan as a file in the repo (optional) | Factory, Kiro, Spec Kit | `planner.persist` | stage 2 |
| Confidence value per ticket | Devin | `planner` `confidence` | stage 2, calibration after the first measurement |
| Convergence check of implementation against plan | Spec Kit `converge` | `reviewer` finding kind `plan_deviation` | stage 2 |

**Gate A and Gate B** (there section 2.5):

| Part | Data set (license, size) | Metric | Reference value (source, classification) | Rule |
|---|---|---|---|---|
| Gate A | P1 (public set plus private set of the installation, see 07) | plan benefit: resolve rate of the coder with minus without plan, same model, paired | coder without plan | "plan does no harm": not worse (section 1.4); a plan benefit greater than 0 is reported as a goal |
| Gate A | P2 unclear tickets; P4 planted plan errors (own cases) | question correctness; detection rate of the plan critique | bare harness | not worse |
| B1 required | Loc-Bench V0.1 (Apache-2.0, 660 cases, [locbench-hf]) | file Acc@5 of the localization | LocAgent (Apache-2.0, [locagent]) re-measured ourselves with the same model; the published value "up to 92.7%" serves only for context (benchmark assignment unverified) | not worse, margin 5 points (section 1.4) |
| B2 required | non-saturated subset of C1p (license per case), on which the coder without plan solves at most about 70% (starting value, estimate); SWE-rebench tasks after the model cutoff are added as soon as their license is VERIFIED | plan benefit external: resolve rate with minus without plan, paired | coder without plan, same model; direction evidenced: a plan helps, a weak plan harms more than none (VERIFIED [plan-to-action], abstract) | "plan does no harm": not worse, margin 5 points (section 1.4); "plan benefit greater than 0" is reported only as a goal. SWE-Bench Pro V2 does not carry this part: there the same coder solves 98.00% (HARD) or 99.40% (Full), the set is saturated ([`ebene-coding`](../research/ebene-coding.md) section 2.2; whether the Scale values are percent of solved tasks is unverified, ibid. section 5 item 3, and is read before stage 2) |
| B2a report | as B2 | efficiency effect of the plan: cost, turns, and review rounds per solved task with versus without plan | coder without plan | report |
| B3 report | Ambig-SWE method (code MIT; data from SWE-bench Verified without license tag) | detection of underspecified tasks | values per model only from a search excerpt (CLAIMED) | report until license and values are verified |
| B4 report | SWE-RPG (163 cases, repo without license file) | coverage of the reference "information points" | none usable | only rebuild the method on an own set; required part only with a license |
| B5 report | P4 | task error rate with minus without plan critique | Jules 9.5% (CLAIMED) | indicative value |

The earlier Gate B path "P1 against CodeRabbit Issue Planner" is permanently dropped (O18, section 16).

## 5. Architecture and design (`architect`, ADR-46)

**Standard** ([`ebene-planung-und-architektur`](../research/ebene-planung-und-architektur.md) sections 2.2, 2.3): The recognized standard is a **method, not a product**: arc42 (structure, CC BY-SA 4.0, VERIFIED [arc42]), C4 with an official review checklist of 21 yes/no questions (CC BY 4.0, VERIFIED [c4-checklist]), ADR according to MADR (MIT or CC0, VERIFIED [madr-license]), ISO/IEC/IEEE 42010:2022 (CLAIMED [iso42010]), ATAM for evaluation against quality scenarios (CLAIMED [atam]), STRIDE (VERIFIED [ms-stride]) and the Threat Modeling Manifesto (VERIFIED [tm-manifesto]), requirements in the EARS pattern (CLAIMED [ears], use by Kiro VERIFIED [kiro-specs]). AI tools exist almost only for threat models: STRIDE GPT (MIT, VERIFIED [stride-gpt]) and AWS Threat Designer (Apache-2.0, VERIFIED [threat-designer]). An AI product that checks ADRs or arc42 with evidence was not found (unverified). Bar: **method fully applied, every statement with a citation.**

**Capabilities:**

| Capability | Standard vendor or method | Our service, location | Status |
|---|---|---|---|
| Specification with requirements in the EARS pattern, IDs, traceability requirement, task, test | Kiro, Spec Kit | `architect` mode `spec` | stage 2 |
| Bugfix specification (current, target, unchanged) | Kiro, Spec Kit | `architect` `spec` | stage 2 |
| ADR draft per load-bearing decision (MADR) | method ADR | `architect` mode `adr` | stage 2 |
| Design review against quality scenarios (ATAM-like) | method ATAM | `architect` mode `review` | stage 2, first `shadow` |
| Diagram review according to the C4 checklist | C4 | `architect` `review` | stage 2 |
| Threat model according to STRIDE with code evidence per threat | STRIDE GPT, Threat Designer | `architect` `review` | stage 2 |
| Plan conformance after implementation | Spec Kit `converge` | `architect` and `reviewer` `plan_deviation` | stage 2 |
| Generate an architecture description according to arc42 and keep it current | Devin DeepWiki (diagrams), Kiro `design.md` | `docs` wiki mode | stage 10 |
| Ship arc42 templates | arc42 | none | deliberately not: CC BY-SA 4.0 would bind own templates; link only |

**Gate A and Gate B** (there section 2.5):

| Part | Data set (license, size) | Metric | Reference value (source, classification) | Rule |
|---|---|---|---|---|
| Gate A | planted defects and contradictions in public architecture and specification documents (own set, size in 07) | recall and precision of the findings | bare harness with a simple prompt | not worse |
| B1 required | every generated artifact | method conformance: requirements in the EARS pattern, ADR with all MADR mandatory sections, all automatically checkable C4 questions fulfilled | method definition (VERIFIED [c4-checklist], [madr-license]) | 100%; which C4 questions are automatically checkable is defined by stage 2 |
| B2 required | own, publicly documented systems with a human-created threat model (size in 07) | recall and precision of the threats, share with code evidence | STRIDE GPT (MIT) re-measured ourselves with the same model | no significant gap |
| B3 report | DevBench (Apache-2.0; number of repos unverified, [devbench]) | design from PRD with an LLM judge | published values not read (unverified) | required part as soon as the values are read before stage 2 |
| B4 report | design review | acceptance rate of the findings online | no public reference | Gate B for design review open |

## 6. Coding (`coder`)

**Standard** ([`ebene-coding`](../research/ebene-coding.md) sections 1, 2.1, 2.2): Two layers. The **agent core** (harness plus model) is led by Claude Code and Codex; Scale lists both as harness in the top rows of SWE-Bench Pro V2 and SWE Atlas (VERIFIED [scale-lb]). The **product shell ticket to PR** is set by GitHub Copilot cloud agent, Devin, Cursor Cloud Agents, and Claude Code in the cloud (VERIFIED [cp-about], [devin-adv], [cu-cloud], [cc-cloud]). Consequence (DERIVED): the platform does not build its own agent loop, but encapsulates the leading harnesses; Gate B checks that the shell does not make the harness worse. The added value is shown by the capabilities of the shell and the online values.

**Capabilities** (condensed from 31 items, there section 2.3):

| Capability | Standard vendor | Our service, location | Status |
|---|---|---|---|
| Trigger from ticket, assignment, label | Copilot, Jules, Cursor, Devin | 03, `routing` | available, stage 2 |
| Declarative environment with snapshot; secrets only in setup | Devin, Copilot, Cursor | `coder`, `SandboxSpec` | available |
| Credentials outside the sandbox, egress allowlist | Claude Code, Copilot | Effect Gateway, credential relay, 05 | available |
| Self-hosted execution with outbound connections only | Claude Code, Factory | pull worker | available, stage 0 |
| Self-check before the PR, critic in the loop | Copilot, Jules | self-check bundle, self-review | available |
| Cost limit per session, model choice | Devin, Cursor, Copilot | limit ledger, `ModelProvider` | available |
| Reproduction first; deterministic merge gate | no vendor evidenced | `coder`, 03 | available, above the standard |
| Agent-driven environment setup | Cursor, Codex, Devin | `coder` step "bootstrap environment" | stage 2 |
| Questions during coding, steering a running session | Claude Code, Jules, Copilot, Devin | `coder`, state machine in 03 | stage 2 |
| PR description according to the repo template, provenance trailer | Devin, Amp | `coder` output | stage 2 |
| Operate the running app, screenshots as evidence | Cursor, Devin | QA library "E2E smoke" | stage 3 |
| Fix CI and review comments on the own PR | Claude Code, Copilot | `prfixer` | stage 4 |
| Live log for readers of the ticket; session analysis | Copilot, Devin | Run Record, admin UI | stage 6 |
| Free harness for the coder (Codex CLI Apache-2.0) | Codex | `AgentRuntime` `codex` | stage 8; until then Claude Code is the only coder runtime, installed by the operator (ADR-39). The project does not qualify free harnesses itself, because they need an account outside the Claude subscription (O28); measurement happens only on an optional Owner run |
| Trigger from chat (Slack, Teams) | Cursor, Devin, Claude Code | trigger plugin | stage 9 |
| Handover to humans and back | Claude Code, Devin, Cursor | `@agent handoff`, `resume` | stage 9 |
| Decomposition into child runs, best-of-N | Devin, Factory, Codex | `coder` | stage 9; best-of-N only with a measured gain per cost |
| Environment layers, periodic rebuild, pin | Devin | `SandboxSpec` | stage 9 |
| Changes across many repos | Cursor, Copilot, Devin | campaigns | stage 10 |

**Gate A and Gate B** (there section 3.3; measuring instrument: import in Harbor format, normal platform run with `effect_sink: record`):

| Part | Data set (license, size) | Metric | Reference value (source, classification) | Rule |
|---|---|---|---|---|
| Gate A | C1 public (permissively licensed repos, license per case) plus private set of the installation | resolve rate (FAIL_TO_PASS and PASS_TO_PASS green) | bare harness (Claude Code or Codex) with the same model | not worse; hard gates 0 violations |
| B1 required | SWE-Bench Pro V2 Full with 642 tasks per release; HARD-51 (51 tasks) as regression subset (harness MIT, tasks under upstream licenses, [scale-pro-repo]) | resolve rate | Scale value of the same harness with the same model, for example Opus 5 (Claude Code) xhigh 99.40 on V2 Full and 98.00 on HARD (VERIFIED [scale-lb]; unit unverified, section 18) | not worse, margin 5 points (section 1.4), as a named non-degradation against the same harness: the set is saturated at the top and evidences no level (section 1.5). The decision is made on V2 Full, because HARD-51 alone does not reach the minimum power (with 51 tasks the interval around 90% is about plus or minus 8 points, DERIVED); HARD-51 remains the regression subset |
| B2 report per release | SWE Atlas Refactoring (70) and Test Writing (90) | Scale's rubric checker | top value of the same harness and model, today 56.67 to 67.04 (VERIFIED [scale-lb]); data availability and license unverified | required part (no significant gap) as soon as data and license are verified |
| B3 report per release | SWE-rebench (tasks after the model cutoff; companion data CC-BY-4.0 only CLAIMED, license of the leaderboard set unverified) | resolve rate | value of the same model in the fixed scaffold (CLAIMED [swe-rebench]) | required part (not worse; protection against contamination) as soon as the license is VERIFIED |
| B4 report | Terminal-Bench, current version via Harbor (Apache-2.0, [harbor]) | success | value of the same agent model row; version unverified [tbench] | report |
| B5 report | Multi-SWE-bench mini, SWE-PolyBench Verified (394), SWE-Sharp-Bench (150, C#) | resolve rate per language | no reference with the same harness | Gate A per language, publish the result |
| B6 report | own agent PRs, online | merge without human code change, review rounds, time to merge | review shares per agent (VERIFIED [amplifying-autonomy]); merge rates 2025 (CLAIMED [aidev]) | report |

Required part today: B1. Regression per change to prompt, harness, or platform code: HARD-51 plus B2 Refactoring (about 120 tasks; B2 internal, results published only after license verification). SWE-bench Verified is no longer a reference: contaminated and flawed (OpenAI CLAIMED [openai-verified], Epoch VERIFIED [epoch-verified]).

## 7. QA (`qa`)

**Standard** ([`ebene-qa-und-tests`](../research/ebene-qa-und-tests.md) sections 1, 2.1): Four subfields with their own top (DERIVED).
- **Reproduction tests:** publicly ranked via SWT-bench; first place on 2026-10-31 DPIAgent (GPT-5, with test selection) 87.5% on SWT-bench Verified (VERIFIED as a leaderboard entry [swt-lb]; whether the operator recomputed it is unverified).
- **Unit tests with benefit:** Meta TestGen-LLM, ACH, and JiT Catching Tests as a method with peer review (VERIFIED [testgen], [ach], [jit]); as an open agent split Microsoft `code-testing-generator` (MIT, mechanics VERIFIED [ms-skills], figures CLAIMED [ms-polyglot]).
- **E2E in the browser:** open base Playwright Test Agents (Apache-2.0, VERIFIED [playwright-agents]); commercially mabl, Momentic, QA Wolf. No public benchmark found.
- **Mutation in review:** Google shows mutants only on changed lines (VERIFIED [google-mut]).
- Qodo is no longer a yardstick for test generation (v1 `test` removed on 2026-10-01, VERIFIED [qodo-sunset]).

**Capabilities** (condensed from the checklist there, section 2.2; dropped numbers noted there):

| Capability | Standard vendor | Our service, location | Status |
|---|---|---|---|
| Reproduction test red on the base, green with the fix | SWT-bench top | `qa`, `coder` | available, stage 3 |
| Hard filters (builds, passes repeatedly, adds coverage or mutation) | Meta TestGen-LLM, ACH | `qa` filters | available, stage 3 |
| E2E with planner, generator, healer; healer does not heal away a broken function | Playwright | `qa` E2E | available, stage 3 |
| Map the diff to the app, pass, fail, blocked with evidence | Factory | `qa.apps` | available, stage 3 |
| Catching mode: tests that should fail on the diff, with checkers against false positives | Meta JiT | `qa` scope `catch` | stage 3, first `shadow` |
| Discovery check (standard test command finds the test), test quality audit, change only test files, no tests with network or timing | Microsoft | `qa` filters and write policy | stage 3 |
| Coverage of changed lines before and after | Copilot `@Test`, Diffblue | `QAReport` | stage 3 |
| Flake quarantine and failure classification | Momentic, mabl, QA Wolf | `qa` step failure classification | stage 3 |
| Mutants as a hint in the review | Google | `qa` generates, `reviewer` shows | stage 3 |
| QA tools via MCP for third-party agents | Momentic, mabl, Playwright | platform MCP | stage 6 |
| Learning loop from rejected tests | Factory | `standards` | stage 7 |
| Accessibility (axe-core) in the E2E step | Deque | `qa` with `Analyzer` axe-core | stage 10 |
| Visual comparison, LLM assertions | Momentic, mabl | none | deliberately not before stage 10: no open reference, high maintenance effort |
| Mobile (iOS, Android) | Momentic, QA Wolf | none | deliberately not: needs Mac or emulator infrastructure that self-hosters on Docker bases rarely have |

**Gate A and Gate B** (there section 2.3):

| Part | Data set (license, size) | Metric | Reference value (source, classification) | Rule |
|---|---|---|---|---|
| Gate A | TDD-Bench Verified; SWT-bench Verified in unit test mode only internally (results published only after license clarification, section 1.5) | success S | bare harness, same model | not worse |
| Gate A | own cases | filters, discovery check | rule | 100% each |
| Gate A | Q3 web app with broken selectors and real bugs | false healing | rule | 0 |
| B1 required | TDD-Bench Verified (Apache-2.0 read ourselves, VERIFIED; 449 cases, [tdd-bench]) | tests before the fix with coverage | best published value with a comparable model; read before the first run (not read today, unverified) | no significant gap; if there is no published value with a comparable model, stage 3 is "done with Gate B open" (section 1.2 item 6) |
| B2 report | SWT-bench Verified (433 cases from 11 projects; harness MIT according to README; data license not stated; [swt-repo]) | success S, coverage delta | best entry with a comparable model, table with date: DPIAgent (Claude Opus 4.5) 78.8%, top DPIAgent (GPT-5) 87.5% (VERIFIED as entries [swt-lb]) | load data at runtime, measure internally, publish results only after license clarification; required part (no significant gap) after license clarification (Owner request to the operators, section 18) |
| B3 required from catching | Q4: public cases with bugs found later plus injected errors | share of real bugs among reported candidates | Meta JiT 8 of 41, about 20% (VERIFIED [jit]) | not below |
| B4 report | XRepoTest (code MIT, data unverified, [xrepotest]) | solved unit test tasks, mutation score | bare agent with the same model (principle [ms-polyglot], there 92.1% versus 78.9%, CLAIMED) | above the bare agent |
| B5 open | E2E | Q3 plus false healing | no public reference | scope `e2e` `live` only via deviation (section 1.2 item 3) |
| Online report | test PRs | acceptance rate, flake rate | Meta 73% is an acceptance rate in the test-a-thon after hard filters ([testgen], [ach]) and **not** a reference for test PRs in the normal review flow | report |

TestGenEval (CC BY-NC 4.0) is never a required part (section 1.5). The earlier reference "testing category in the OpenHands Index for the same model" is dropped: the model used is not always listed there, subset and mode are not stated ([oh-index]).

## 8. PR fix and CI (`prfixer`)

**Standard** ([`ebene-pr-fix-und-ci`](../research/ebene-pr-fix-und-ci.md) sections 1, 2): No independent product benchmark; leading group by function and market position (DERIVED): **GitHub Copilot** (Agent Merge "Watch and fix" with auto-merge, `@copilot` on every PR, VERIFIED [copilot-merge], [copilot-anypr]); **Cursor Bugbot Autofix** with the only published merge rate, over 35% (CLAIMED [cursor-autofix-blog]); **Nx Self-Healing CI** for verified CI fixes (VERIFIED [nx-shci]); **Gitar** with a disclosed failure classification (VERIFIED [gitar-ci]). Dependency updates: Renovate (AGPL-3.0) and the Dependabot core (MIT) as producers (VERIFIED [renovate], [dependabot-core]).

**Capabilities** (condensed from the checklist there, section 3; dropped numbers noted there):

| Capability | Standard vendor | Our service, location | Status |
|---|---|---|---|
| Fix a single thread or all open bot findings | Copilot | `prfixer` `scope` | available, stage 4 |
| Delivery as a commit or stacked PR | Bugbot | `commit_mode` | available, stage 4 |
| Attempt limit per PR; abort if the branch moves | Bugbot, Gitar | 3 attempts, `expectedOldSha` | available |
| Only users with write access trigger; fork PRs excluded | Copilot | `min_permission`, 05 | available |
| Implement human review comments | Copilot, Devin | `prfixer` | stage 4 |
| Attribute failures to the PR; restart those not caused once per commit; recovery after an own faulty fix | Gitar, Nx | `prfixer` step "classify" | stage 4 |
| Real CI as truth; own check only `success` or `neutral` | Nx, Bugbot | `prfixer` | stage 4 |
| Bot allowlist against bot loops | Devin | `routing` | stage 4 |
| Fix analyzer and security findings, valid only with a re-scan | Copilot Autofix, Snyk | `prfixer` source `static_analysis` | stage 4 |
| Continuous loop on human PRs (opt-in per PR) | Copilot | `prfixer` watch mode | stage 5 |
| Repair a dependency update with a breaking change | Copilot (Dependabot assignment) | source `dependency_update` | stage 10 |
| Red CI on the default branch (cause as an issue, no push) | gh-aw CI Doctor | mode `ci_doctor` | stage 10 |
| CI logs from third-party CI (Jenkins, CircleCI, Buildkite) | Gitar | `SCMProvider` `CI_LOGS` | partial; no own plugin kind, because the plugin kinds are fixed at nine (ADR-40, ADR-41); reassess the need in stage 9 |
| Auto-apply only for failure classes with a high verification rate | Nx | `prfixer.auto_apply` | stage 9 |

**Gate A and Gate B** (there section 4):

| Part | Data set (license, size) | Metric | Reference value (source, classification) | Rule |
|---|---|---|---|---|
| Gate A | F1x (review comment with a test per comment), F2 (red CI), F3 (conflicts), F4 (dependency), F6 (failures not caused); public plus private set | success; violations of prohibitions | bare harness, same model | not worse; violations 0; F6: 0 code changes, at most one rerun per commit (rule after Gitar, VERIFIED [gitar-ci]) |
| B1 report | CI-Repair-Bench (567 cases from 103 Python repos; data publication unverified) or JetBrains LCA CI Builds Repair (68 cases; data license unverified, [lca-ci]) | original workflow green, prohibitions 0 | best model 18.9% on CI-Repair-Bench (VERIFIED [ci-repair-bench], abstract) | required part as soon as the data license is clarified: not below |
| B2 report | BUMP (571 breaking updates, code MIT, data unverified) | build success | 27% (Byam with o3-mini, CLAIMED [bump]) | indicative value; required part after license and reading the paper |
| B3 report | F1x according to the c-CRAB principle (c-CRAB data unverified, [c-crab]) | comment test green after the fix | no fix reference published | report |
| B4 open | conflicts: Merge-Bench (7,938 hunks, data unverified, [merge-bench]) | build, tests, lint green without markers | reference values unverified | source `merge_conflict` `live` only via deviation |
| B5 open | security findings (schema after Copilot Autofix: finding gone, no new ones, no syntax error, tests unchanged) | fix validity | GitHub gives only words, Snyk "over 80%" without method (CLAIMED) | report; the hard fix rule remains Gate A |
| Online report | own PRs | fix acceptance rate, verification rate per class, time to green | Bugbot over 35% (CLAIMED), Nx 60% (CLAIMED) | indicative values |

Gate B of the PR fixer is not measurable today: all public sets have an unclarified data license. Until clarification, stage 4 is only "done with Gate B open" (section 1.2 item 6); the license request is an owner step in the done criterion of stage 4 (section 18). The earlier reference "not worse than CodeRabbit Autofix on the same findings" is dropped (O18).

## 9. Knowledge base (`indexer`)

**Standard** ([`ebene-wissen-standards-doku`](../research/ebene-wissen-standards-doku.md) sections 1, 2.1): Leading group per sublayer, no independent product ranking (DERIVED). Retrieval: Sourcegraph (Zoekt Apache-2.0, Deep Search; VERIFIED [zoekt], [sg-deepsearch]), Augment Context Engine and Cursor Semantic Search (figures only self-measured, CLAIMED). Repo Q&A and wiki: Devin DeepWiki and Ask Devin (VERIFIED [devin-wiki]). Memory: GitHub Copilot Memory as the most rigorously documented model (citation per fact, check before use, expiry; VERIFIED [copilot-memory]).

**Capabilities** (condensed from items 1 to 11 and 26 to 33, there section 2.2):

| Capability | Standard vendor | Our service, location | Status |
|---|---|---|---|
| Structure graph, hybrid search, summaries per symbol and file | Greptile, Sourcegraph, Cursor | `indexer`, `KnowledgeStore` | available, stage 7 |
| Citation per fact, check against the current state before use | Copilot Memory | `indexer` | available, stage 7 |
| Agentic deep search as a user surface (`@agent ask` with citations) | Sourcegraph Deep Search, Ask Devin | `indexer` ask flow | stage 7 |
| Cross-repo context, PR and issue index | Augment, Sourcegraph | `CROSS_REPO`, KB | stage 7 |
| External document sources (Confluence, Notion) | Dosu | `KnowledgeStore` source | stage 7 |
| Learnings lifecycle: scope, expiry, voting, repo facts separate from user preferences, secret redaction, import and export | Copilot Memory | `indexer`, `standards` | sub-stage 7a |
| Context as MCP for third-party agents | Augment, Sourcegraph, DeepWiki | external KB MCP, default off | stage 7 |
| Trigram and regex index across many repos | Sourcegraph Zoekt | optional `KnowledgeStore` | stage 9 |
| Generated repo wiki | DeepWiki | `docs` | stage 10 |

**Gate A and Gate B** (there section 2.3):

| Part | Data set (license, size) | Metric | Reference value (source, classification) | Rule |
|---|---|---|---|---|
| Gate A | K1 from C1 and reviewer sets | Recall@10 of files and symbols; cost | review and coder without KB | better or cheaper than without KB |
| Gate A | all answers | citation validity (citation exists at HEAD and supports the statement) | rule (Copilot Memory principle) | 100% |
| B1 required | K4: SWE-QA v2 (Apache-2.0, 720 questions, 15 Python repos, [sweqa-gh]) and DeepCodeBench (Apache-2.0 according to the data set card, VERIFIED [qodo-dcb-hf]; 1,144 pairs according to Qodo, CLAIMED) | judge score or fact recall | best reference agent re-measured ourselves (Claude Code, Codex CLI, bare) under the same judge; Qodo 0.76 to 0.77 (CLAIMED [qodo-dcb-hf]) for context only. The project re-measures only Claude Code (O28); Codex CLI is included only with published values under a comparable judge, otherwise it is listed as not measured in the report | no significant gap against the best reference agent |
| B2 report | K3: ContextBench verified (500 tasks; code Apache-2.0, data license open, [contextbench-gh]) | file and span F1 of the context retrieval | best leaderboard value of the same model (only as an image in the repo, unverified) | required part after license clarification |
| B3 report | K5: RepoQA (Apache-2.0, 500 tests, [repoqa]), CoIR subset with free data licenses | NDCG@10, hits | published values of the embedding models (CLAIMED) | selection of the default embedding model; only models with a license that allows commercial use |

## 10. Standards and Learnings (`standards`)

**Standard** (there sections 2.1 c and d): File format **AGENTS.md** under the Agentic AI Foundation of the Linux Foundation (steward VERIFIED [agentsmd]). Derivation from review history: **Qodo Rule Miner** (VERIFIED [qodo-miner]). Measurement per rule: Bugbot (acceptance rate) and Greptile (addressed rate) (VERIFIED [cursor-bugbot], [greptile-std]).

**Capabilities** (there items 12 to 25):

| Capability | Standard vendor | Our service, location | Status |
|---|---|---|---|
| Rules from the base SHA | Bugbot | 04 section 2 | available |
| Derive rules from accepted review comments, weight by ownership, withdrawal | Qodo Rule Miner | `standards` | available, stage 7 |
| Derived rules only via PR with approval | (Qodo activates automatically) | `standards` | available; deliberately stricter than Qodo (O10) |
| Read third-party rule formats, scope per directory, nearest file wins | AGENTS.md | guideline loader | stage 7 |
| Disable an inherited rule by ID; rule budget with visible truncation | Greptile, Bugbot | guideline loader, Run Record | stage 7 |
| Metrics per rule (usage, acceptance, addressed rate), weakening of poor rules | Bugbot, Greptile, Qodo | `standards`, `KnowledgeStore` `RULE_STATS` | stage 7 |
| A finding that only the LLM found becomes a deterministic rule with a test | Semgrep Memories | `standards` rule compilation (Opengrep or ast-grep) | stage 7 |

**Gate A and Gate B:** No vendor publishes figures on the effect of its rules. Gate B therefore measures feature parity plus a relative measurement (classification DERIVED). This is weaker than a numeric reference and is stated as such in the qualification report ("reference: parity").

| Part | Data set | Metric | Reference value | Rule |
|---|---|---|---|---|
| Gate A | reviewer sets R5 and private set, each with and without rules | precision of the reviewer | reviewer without rules | "rules do no harm": not worse (section 1.4); a gain greater than 0 is reported as a goal (same error class as planner B2, ADR-55) |
| B1 required | capability list above | parity of the rule metrics with Bugbot and Greptile | feature definition (VERIFIED [cursor-bugbot], [greptile-std]) | all metrics present and retrievable per rule |
| B2 required | online, own repos | addressed rate of findings with a rule reference | addressed rate of findings without a rule reference in the same period | not lower |
| B3 report | rule PRs | acceptance rate, withdrawals | none | report |

## 11. Docs (`docs`, ADR-46)

**Standard** ([`ebene-wissen-standards-doku`](../research/ebene-wissen-standards-doku.md) section 2.1 e; [`ebenen-landkarte`](../research/ebenen-landkarte.md) section 2.2 E13, E14): Docs sync: **Mintlify Autopilot** (docs PR from a merged PR, CLAIMED [mintlify]) and **Swimm** (code-coupled docs, CLAIMED [swimm]). Wiki: **DeepWiki** (VERIFIED [devin-wiki]). Release notes: GitHub generated release notes, release-please, git-cliff, deterministic from Conventional Commits and labels (CLAIMED [relnotes]).

**Capabilities:**

| Capability | Standard vendor | Our service, location | Status |
|---|---|---|---|
| Docs drift check on PRs | Mintlify, Swimm | `docs` check `docs-drift` | stage 10 |
| Docs PR after merge | Mintlify, gh-aw | `docs` mode `sync` | stage 10 |
| Release notes: version, date, breaking list deterministic, reading text from the model | release-please, git-cliff | `docs` mode `release` | stage 10 |
| Repo wiki according to a control file | DeepWiki | `docs` wiki mode | stage 10 |
| Automatically update code references in docs | Swimm | none | deliberately not: algorithm patented according to the vendor (patent not identified, CLAIMED); only verifiable citations |

**Gate A and Gate B:**

| Part | Data set (license, size) | Metric | Reference value (source, classification) | Rule |
|---|---|---|---|---|
| Gate A | own drift set from public repos (merged PRs with and without docs change; truth is the human docs change) | precision of the drift check | simple prompt, same model | not worse |
| Gate A | docstrings, release notes | build and linter green; every release line refers to a PR; version, date, breaking list equal to the deterministic source | rule | 100% each |
| B1 report | CodeWikiBench (21 repos, 7 languages; license unverified) | rubric score of generated repo docs | DeepWiki 64.06% (CLAIMED, by authors of a competing product [codewiki]) | indicative value; required part after license clarification |
| B2 report | DocAgent set (366 components; MIT according to a third-party source, unverified) | completeness, truthfulness of the docstrings | DocAgent re-measured | required part after license clarification |

Gate B for `docs` is open today. Until license clarification, stage 10 for `docs` is only "done with Gate B open" (section 1.2 item 6); the license request is an owner step in the done criterion of stage 10.

## 12. Triage (`triage`, ADR-46)

**Standard** ([`ebenen-landkarte`](../research/ebenen-landkarte.md) section 2.2 E1): **Linear Triage Intelligence** (per property show, hide, or apply automatically; VERIFIED [linear-triage]). Free competitor in every GitHub repo: the workflow "Issue Triage" of GitHub Agentic Workflows (VERIFIED [gh-aw]). A public benchmark for triage was not found.

**Capabilities:**

| Capability | Standard vendor | Our service, location | Status |
|---|---|---|---|
| Duplicates and related issues with citation | Linear | `triage` with vector search of the `indexer` | stage 7 |
| Labels, assignees, repo assignment as a suggestion | Linear | `triage`, `propose_labels` | stage 7 |
| Per property `suggest`, `auto_apply`, `off` | Linear | configuration in 04 | stage 7 |
| Without a shell, writing only via declared outputs | gh-aw | Effect Gateway | stage 7 |
| Close issues automatically | third-party sources call it risky | `triage` | option, platform default off; repo opt-in `auto_close` only after a green eval T1 (O25 decided) |

**Gate A and Gate B:**

| Part | Data set (license, size) | Metric | Reference value (source, classification) | Rule |
|---|---|---|---|---|
| Gate A | T1: public repos with issues marked as duplicates by maintainers and labels set (size in 07) | duplicate precision and recall, label agreement | simple prompt with vector search, same model | not worse |
| Gate A | S1, S2, and own cases | automatic closings without approval; execution of instructions from issue text | rule | 0 each |
| B1 report | T1 | duplicate F1 | gh-aw "Issue Triage" re-measured ourselves with the same model (license of gh-aw unverified) | no significant gap; required part as soon as the license of gh-aw is VERIFIED (read the license file before stage 7); until then stage 7 for `triage` is "done with Gate B open" (section 1.2 item 6) |
| B2 report | online | adoption rate of the suggestions per property | none published | report |

A comparison with CodeRabbit Issue Enrichment on the same issues is dropped (O18).

## 13. Static analysis and security

Carriers: plugin kind `Analyzer` (ADR-40, SARIF 2.1.0 as normal form), security finder and verifier in the `reviewer`, source `static_analysis` in the `prfixer`, threat model in the `architect`. There is no separate analysis or security service.

**Standard** ([`ebene-statische-analyse-und-security`](../research/ebene-statische-analyse-und-security.md) sections 1, 2.1):
- SAST: Gartner Magic Quadrant AST 2025 with the leaders Black Duck, Checkmarx, HCLSoftware, OpenText, Snyk, Veracode (CLAIMED [gartner-ast]); open and free CodeQL (queries MIT, CLI proprietary), Semgrep CE, and Opengrep (LGPL-2.1) (VERIFIED [codeql-lic], [opengrep]).
- AI security review: Claude Security and Codex Security with the same pattern: candidates, verification per finding, threat model, fix only with a re-scan (VERIFIED [an-ccsec], [cx-sec]).
- License limits (ADR-50): no Semgrep registry rules, no CodeQL CLI, no SonarQube in the product; results of third-party tools at most as a SARIF import for which the operator is responsible.

**Capabilities** (condensed from the checklist there, section 3.1; dropped numbers noted there):

| Capability | Standard vendor | Our service, location | Status |
|---|---|---|---|
| Analyzer configuration from the PR counts as code execution | Lesson from the remote code execution at CodeRabbit via a linter configuration in the PR ([kudelski-cr] CLAIMED) | 05 | available |
| Verification per finding with proof or refutation | Claude Security, Codex Security | `reviewer` verifier | available for LLM findings |
| Import external results (SARIF) | GitHub Code Scanning | `Analyzer` operating mode `ingest` | stage 1 |
| Stable fingerprints, only new findings (baseline) | GitHub, SARIF, Opengrep | `Analyzer` | stage 2 |
| Analyzer findings as candidates for the verifier | Aikido, Semgrep Assistant | `reviewer` | stage 2 |
| CWE, reachability, exploitability per finding, severity capped accordingly | Aikido | finding schema `reviewer` | stage 2 |
| A security fix counts only if the alert is gone on the re-scan and tests are green | Copilot Autofix, Snyk, CodeMender | `prfixer` | stage 4 |
| Secrets, SCA, IaC in the PR as normal analyzers (gitleaks, osv-scanner, Trivy, Checkov) | ZeroPath | `Analyzer` catalog with free licenses | stage 2 |
| Threat model per repo as an editable artifact | Codex Security, ZeroPath | `architect` STRIDE | stage 2 |
| SARIF output to the host | Codex Security | `SCMProvider` | stage 9 |
| Team memory for false positives with approval | Semgrep Memories | `standards` | stage 7 |
| Whole-repo scan on demand (deep scan) | Codex Security, Claude Security | none | not planned in stages 0 to 10: expensive, separate billing path; open (section 18) |

**Gate A and Gate B** (there section 3.5):

| Part | Data set (license, size) | Metric | Reference value (source, classification) | Rule |
|---|---|---|---|---|
| Gate A | AN1: own fixture repos per analyzer (size in 07) | same finding fingerprints as the direct call of the same version | direct call | 100%; failure paths (crash, timeout, required field missing) end `neutral` with a reason |
| Gate A | SEC1 to SEC4 | recall of the security finder at the same false positive rate on patched versions | bare Claude Code with the prompt from `claude-code-security-review` (MIT) | not worse |
| B1 required | own fixture cases per gate condition | platform gate with own named values under `analysis.gate` (starting values as in the reference project bothy: 0 new findings, hotspots reviewed, coverage of new code at least 80%, duplication at most 3%, [`bothy-vorlage-projekt-setup`](../research/bothy-vorlage-projekt-setup.md) section 2.3, DERIVED; minimum number of new lines as a named value, starting value estimate) | own published definition; no parity with Sonar way (section 16) | 100% same gate decision as the own definition; B1 thus evidences the correctness of the gate computation, not the level of a third-party product (DERIVED) |
| B2 required | SEC1: real CVE pairs, vulnerable and patched: OpenSSF CVE Benchmark (over 200 CVEs in JS/TS according to README, 218 CLAIMED; tool MIT, LICENSE read 2026-10-31, VERIFIED [ossf-cve]; case repos under their original license, only via download) and CWE-Bench-Java (120 CVEs CLAIMED; MIT, LICENSE read 2026-10-31, VERIFIED [iris]) | recall; false positives on patched versions | union of Opengrep and CodeQL under the same conditions, re-measured ourselves (CodeQL only on OSI-licensed code, reading of the CodeQL terms [codeql-lic]); for context: CodeQL 27 of 120 on CWE-Bench-Java (CLAIMED [iris]) | recall not worse, false positives not higher, precision at least 70% (starting value, estimate) |
| B3 required | SEC1 and SEC4 | verifier: discarded real findings; agreement on real hits | Semgrep 96% on hits (CLAIMED [semgrep-ai]) | 0 discarded real findings; agreement at least 95% (indicative value) |
| B4 report | SEC2 Juliet C/C++ and Java 1.3 (CC0, VERIFIED [juliet]) only in the cleaned version ([07](07-eval.md) section 3.8), as a regression set; RealVuln (license unverified), OWASP Benchmark (GPL-2.0, loaded externally only) | recall, F1, F3 | Juliet: union of Opengrep and CodeQL as in B2; RealVuln F3 Sonnet 4.6 51.7 versus Semgrep 17.7 (VERIFIED [realvuln], abstract; the publisher is a vendor) | context |
| B5 open | SEC5 CyberGym (Apache-2.0, 1,507 vulnerabilities, [cybergym]) | share of findings with a reproduced PoC | no product reference | report |

## 14. Autonomous pass and auto-merge (cross-cutting)

**Standard:** GitHub Copilot Agent Merge can merge with the host's auto-merge, "as soon as all requirements are met" (VERIFIED [copilot-merge]); Renovate merges bot PRs via the platform automerge (VERIFIED according to [`ebene-pr-fix-und-ci`](../research/ebene-pr-fix-und-ci.md) section 2.6). No vendor has evidenced a deterministic merge decision instead of an agent; our merge gate in [03](03-flow-and-orchestration.md) section 1a lies above that (DERIVED).

**Gate:** Suite S7 from [07](07-eval.md) section 5 is Gate A and mandatory before `merge.mode: auto`. For the shadow comparison "gate says merge, human would not have merged" the following applies: 0 wrong decisions out of n cases bounds the error rate at 95% only to about 3/n (rule of three, DERIVED). 30 cases thus bound it to about 10%. Therefore the starting amount from [07](07-eval.md) section 5 applies: at least 100 agent PRs per installation and combination (bound about 3%, estimate), of which at least 20 per repo with `auto`. An external numeric reference is missing; Gate B here is parity with the standard (merge only when the host's required checks are fulfilled) plus S7. Independent of the gate, `auto` never applies to repos of the class `external_code` and only with the provenance condition (ADR-60).

## 15. Edge layers

Edge layers have no service of their own. They qualify via parity of the tool (analyzer run equal to direct call) and via the gate of the service that carries them ([`ebenen-landkarte`](../research/ebenen-landkarte.md) section 2 and appendix).

| Layer | Standard (classification) | Here | Stage | Gate |
|---|---|---|---|---|
| Dependency updates | Renovate (AGPL-3.0), Dependabot (core MIT) (VERIFIED [renovate], [dependabot-core]) | third-party tool creates PRs; `prfixer` source `dependency_update` repairs breakages | 10 | `prfixer` section 8, part B2 |
| Red CI on the default branch | gh-aw CI Doctor (VERIFIED [gh-aw]) | `prfixer` mode `ci_doctor`: cause as an issue, no push | 10 | Gate A: cause confirmed by hand on an own set; Gate B open |
| Incident and SRE | Azure SRE Agent, Datadog Bits Investigation, Sentry Seer (VERIFIED [az-sre], [dd-bits], [sentry-fix]) | no own agent (ADR-49); handover input `sentry`, `incident-handoff`, then `coder`, `prfixer` | 10 | gates of `coder` and `prfixer` |
| Accessibility | Deque Axe (product CLAIMED); axe-core MPL-2.0 (VERIFIED [axe-core]) | `Analyzer` axe-core in the QA E2E step | 10 | parity with direct call |
| Cloud cost of IaC | Infracost (Apache-2.0, VERIFIED [infracost]) | `Analyzer`, cost diff as context in the `reviewer` | 10 | parity with direct call |
| Migration, modernization | AWS Transform, OpenRewrite (core Apache-2.0) (VERIFIED [aws-transform], [openrewrite]) | campaigns via `planner` and `coder`, OpenRewrite as `Analyzer` | 10, last | gates of `planner` and `coder` |
| Performance | Codeflash (BSL-1.1, VERIFIED [codeflash]) | deliberately no service: measurement needs quiet machines; tool only as an analyzer of the operator | after 10 | open |
| Continuous runs ("Continuous AI") | GitHub Agentic Workflows (VERIFIED [gh-aw]) | schedule trigger for `triage`, `docs`, `ci_doctor` | 7 and 10 | gates of the services |

## 16. Comparisons with CodeRabbit and SonarQube (O18, O19)

The terms of use of both vendors restrict comparisons. The following is a reading of the texts with references, not legal advice ([`open-source-lizenz-und-recht`](../research/open-source-lizenz-und-recht.md) sections 2.6 and 2.7, with the corrections from [`gegenpruefung-lizenz-und-recht`](../research/gegenpruefung-lizenz-und-recht.md)).

**CodeRabbit (O18).** The terms of use of CodeRabbit (Terms of Service, "Updated: April 20, 2026", [12](12-open-source-and-project.md) section 5.3) prohibit customers in 4.2 (iv) to "disclose the results of any benchmarking of the Services, or use the Services to develop competing products or services without CodeRabbit's prior written consent". Section 4 continues to apply after the end of the contract (5.4). O18 is decided (not connected, no request); this permanently drops:

| Comparison | Where | Replacement |
|---|---|---|
| CodeRabbit findings as ground truth (R1) | `reviewer` Gate A | R5 (SWE-PRBench, AACR-Bench) and hand-labeled cases without CodeRabbit outputs |
| Online address rate against CodeRabbit on the same repos | `reviewer` B4 | Martian online definition on own repos; context via the online values published by Martian |
| Walkthrough in a paired comparison against CodeRabbit | `reviewer` companion features | rubric with human labels |
| Plan against CodeRabbit Plan | `planner` | Loc-Bench with re-measured LocAgent, "plan does no harm" on a non-saturated C1p subset (section 4) |
| Fixes against CodeRabbit Autofix | `prfixer` | public sets after license clarification (section 8) |
| Triage against Issue Enrichment | `triage` | re-measured gh-aw workflow |
| own published ranking "platform against CodeRabbit" | all | none; only own values on third-party benchmarks |

According to the license report, the following remains allowed: citing values published by third parties (Martian values of CodeRabbit are Martian's measurements, not ours) and own measurements on sets without CodeRabbit outputs.

**Vendor documentation (reading with references, not legal advice).** The earlier reading that reading the vendor documentation is not use of the services ([`open-source-lizenz-und-recht`](../research/open-source-lizenz-und-recht.md) section 2.6) is not tenable. Its section 1.9, according to the Red Team review of 2026-10-31, counts the website and its contents among the "Services" (wording not quoted here), and 4.2 (iv) prohibits "use the Services to develop competing products". [sonar-aup] §5 prohibits "Access or use the Products or Documentation if you are a direct competitor of SonarSource" (VERIFIED, [12](12-open-source-and-project.md) section 5.3). Both apply without written consent. So evaluating the vendor documentation for a rebuild can also fall under this (DERIVED). After O18 and O19 (no request), the following therefore applies permanently:
- no further evaluation of CodeRabbit or SonarSource documentation for a rebuild;
- **affected** were the previous evaluations of this documentation in the preliminary research and in the layer research under `docs/research/` (dated, not binding) as well as the rows of this file and of [02](02-services.md) and [03](03-flow-and-orchestration.md) based on them. All of them are deleted: in the layer research the sources on the documentation domains and the statements and checklist rows based only on them (the numbers stay, noted per file); here the standard descriptions and capability rows of sections 2 to 13 that relied only on them, together with their sources, where rows evidenced by other vendors now only name those; in 02 the CodeRabbit rows of the vendor tables (planner, reviewer, PR fixer, indexer, standards, triage, docs) and in 02 and 03 the evidence based on this documentation;
- there is no request to CodeRabbit or SonarSource (O18, O19 decided); where an affected row is needed, it is re-evidenced from third-party sources or deleted (recommendation).

**SonarQube (O19).** Without written consent, the AUP prohibits access for "a direct competitor of SonarSource" and the publication of "any benchmark, comparative, or performance tests or evaluations of the Products" (§5) as well as the use of Results Data for competing "code review systems (whether based on LLM Technologies or not.)" (§6) ([sonar-aup]). The analyzers of the Community Build are under SSALv1; its "Non-competitive Purpose" excludes in (c) the processing of the results by third-party AI ([ssal]). According to Sonar, the OSS plan of the cloud requires a public project with an open source license ([sonar-oss], made more precise by the cross-check). O19 is decided (not connected, no request); this permanently drops:

| Comparison | Where | Replacement |
|---|---|---|
| Platform gate against Sonar gate at the same SHA | section 13 B1 | own named gate values (`analysis.gate`) on own fixtures, without parity with Sonar way |
| SonarQube results as eval data or as input of the PR fixer | `prfixer` source `static_analysis` | Opengrep, CodeQL (only via the host), language linters |
| published comparison with SonarQube | all | none |

**How Gate B remains measurable without both:** (a) third-party values on open benchmarks (Martian, ReviewBench, Scale, SWT-bench, and CI-Repair-Bench after license clarification); (b) own remeasurement of open references with the same model (bare harnesses, LocAgent, STRIDE GPT, gh-aw after license verification, Opengrep, CodeQL on open source code); (c) parity against published definitions (C4 checklist, MADR) and own named values (platform gate). None of these paths needs an account with CodeRabbit or SonarSource.

## 17. Corrections to 07 and 02

From now on this file is the home of the gate values. [07](07-eval.md) section 4 and the DoD tables in [02](02-services.md) refer here instead of keeping their own values. The following corrections were implemented there on 2026-10-31; the table remains as derivation:

| Location today | Wrong | Right | Evidence |
|---|---|---|---|
| 07 section 3.1 R2, 02 reviewer DoD | "136 hand-curated golden comments"; scoring F1 | 173 golden comments (counted ourselves); scoring F2 in profile `core`, judge Claude Opus 4.5, micro average; license MIT | [`ebene-review`](../research/ebene-review.md) sections 2.2, 2.3 |
| 07 section 4 reviewer, 02 reviewer DoD | reference "Greptile 60.8% F1" for R2 | 60.8% is an online value of 2026-07-30 and does not apply to R2; the reference for R2 is the table in section 3 | [greptile-martian] |
| 07 section 3.2 C2, 02 coder DoD | "sample SWE-bench Pro, Scale SEAL or aggregator" | coder basket B1 to B6 (section 6) with the reference from Scale's leaderboard per harness and model | [`ebene-coding`](../research/ebene-coding.md) sections 2.2, 3.3 |
| 07 section 3.3 Q1, 02 QA DoD | "calibrated against the testing category in the OpenHands Index" | own run on SWT-bench Verified and TDD-Bench Verified (section 7) | [`ebene-qa-und-tests`](../research/ebene-qa-und-tests.md) section 1 |
| 07 sections 3.3 and 4 | "acceptance rate close to Meta 73%" as reference | Meta 73% is an acceptance rate in the test-a-thon after hard filters, not a reference for the review flow; report only | [testgen], [ach] |
| 07 section 4 PR fixer, 02 PR fixer DoD | Gate B against CodeRabbit Autofix from the history | 0 CodeRabbit commits in the comparison set; comparison dropped (O18); Gate B according to section 8 | [`ebene-pr-fix-und-ci`](../research/ebene-pr-fix-und-ci.md) section 2.8 |
| 07 section 4 planner, 02 planner DoD | Gate B only via a comparison run against CodeRabbit (O13) | Gate B according to section 4; comparison dropped (O18) | section 16 |
| 07 section 4 knowledge base and standards (minor M5) | Gate B without reference to the standard | sections 9 and 10 | this file |
| 07 section 4 closing sentence | "A service without a measurable Gate B counts as qualified with Gate A" | rule from section 1.2 (ADR-47) | ADR-47 |
| 07 section 1.1, 02 all DoD tables (Red Team on the overall idea, finding 18) | "not worse" without a margin; in 02 deviating rules ("at least LocAgent", "not below the confidence interval of the published value", "within the interval") | one-sided non-inferiority test with margin, minimum power, and "not decidable" according to section 1.4; 02 only refers here | section 1.4, ADR-56 |
| 07 sections 1 and 3.1, 02 reviewer DoD (finding 17) | Martian only with the judge Claude Opus 4.5; ReviewBench only without `ccr`; `ccr` named as Copilot | Martian under all three judges, the least favorable counts; ReviewBench on the full golden set, leave-producer-out without `ccr:` and, for a Claude candidate, without Claude producers as diagnostics; `ccr` is not named according to the methodology | section 3; [rb-method] section 5.5 |
| 07 section 3.8, 02 (finding 19) | Juliet as required part SEC2 without cleaning | Juliet only cleaned and only as a regression set; required part on real CVE pairs (SEC1) | section 13 |
| 07 section 4 planner, 02 planner DoD (finding 1) | plan benefit "greater than 0 and significant" on SWE-Bench Pro V2 | "plan does no harm" on a non-saturated C1p subset; benefit only as a goal | section 4 |
| 07 section 7 | O12 open; "whether CodeRabbit fixes exist: unverified" | Martian is MIT (O12 settled for the benchmark; what remains open is the redistribution of code from the source repos); CodeRabbit fixes: 0 found | [`ebene-review`](../research/ebene-review.md) section 1; [`ebene-pr-fix-und-ci`](../research/ebene-pr-fix-und-ci.md) section 2.8 |

## 18. Open points

- **Clarify data licenses** (prerequisite for required parts): SWT-bench data, ContextBench, CI-Repair-Bench, JetBrains LCA, BUMP data, Merge-Bench, c-CRAB, CodeWikiBench, DocAgent, SWE-RPG, SWE Atlas Refactoring and Test Writing, SWE-rebench leaderboard set, gh-aw (OpenSSF CVE Benchmark and CWE-Bench-Java read as MIT on 2026-10-31). A request to the authors has an external effect and is an owner step in the done criterion of the respective stage (section 1.2 item 6).
- **Read reference values directly before the first run:** ReviewBench leaderboard before stage 1 (JavaScript page, not read ourselves; the Martian values per judge are recomputed from the raw file), unit of the Scale values on SWE-Bench Pro V2 (percent of solved tasks or scaled value) before stage 2, TDD-Bench and DevBench values, Terminal-Bench version. A reference value that cannot be read makes the part not decidable (section 1.4), not the stage unfinished.
- **Whole-repo security scan:** planned in no stage; decision when planning stage 10.
- **Credential kind when adopting a reference qualification:** the assumption "the same model at the same endpoint delivers the same quality" is evidenced only by the contract test in stage 1.
- Owner decisions with an effect on this file, all decided on 2026-10-31 and incorporated here: O18 (CodeRabbit), O19 (SonarQube), O22 (budget for eval runs), O23 (submission to public leaderboards), O24 (automatic approval as an option), O25 (triage closes issues). Status in [DECISIONS.md](../DECISIONS.md) section 3.2.
