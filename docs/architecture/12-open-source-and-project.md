<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# 12 Open source and project (as of 2026-10-31)

This file defines how the platform comes into being as an open-source project: license, name, repos, publication, development repo with check tools, stage R, third-party terms of use and governance. The project is called Guildwork (O17); the planning keeps calling it "the platform".

**No legal advice.** Statements about contracts and licenses are the reading of the cited original texts with the location of the passage. Basis: [`open-source-lizenz-und-recht`](../research/open-source-lizenz-und-recht.md), corrected by [`gegenpruefung-lizenz-und-recht`](../research/gegenpruefung-lizenz-und-recht.md) (takes precedence), plus [`bothy-vorlage-projekt-setup`](../research/bothy-vorlage-projekt-setup.md) (reference project bothy, state `origin/main` as of 2026-10-31). Classification and keys as in the [README](README.md) section 6. ADR texts are in [09](09-decisions.md) section 2, owner decisions in [DECISIONS.md](../DECISIONS.md) section 3.

---

## 1. The open-source goal and what it means for every decision

Goal: The platform is a public open-source project, not tailored to one company. Anyone can install it themselves, host it on their own base and attach their own services and plugins ([11](11-installation-and-hosting.md)).

From this follow rules that every architecture decision must satisfy (DERIVED):

| No. | Rule | Reason | Where enforced |
|---|---|---|---|
| OS1 | Every function has a path without a paid service and without proprietary software in the shipped scope. Paid services are plugins, never mandatory. | "anyone installs it themselves" | License gate (section 5), ADR-39, ADR-50 |
| OS2 | No company, person or host details in the product. Instance values live in the installation; the product only describes keys. | Requirement 2; pattern of the reference project ("The configuration reference in the product describes every key, the ops repository only sets values", VERIFIED according to [`open-source-lizenz-und-recht`](../research/open-source-lizenz-und-recht.md) section 2.9) | Deny list scanner (section 4.3) |
| OS3 | Everything shipped is under a license on the allowlist; third-party rules and third-party texts only with a free license. | License cleanliness for redistribution | ADR-50, license gate |
| OS4 | The base is interchangeable: storage, secrets and identity go through drivers, not through a cloud service. | Requirement 4 | ADR-41, [11](11-installation-and-hosting.md) |
| OS5 | Safe and quiet by default: telemetry off, subscription credentials locked, `live` only after qualification. | Operators decide for themselves | ADR-44, ADR-51, ADR-47 |
| OS6 | Quality is verifiable for third parties: public, license-clean eval sets and a published reference qualification per release. | Without them, every service stays `shadow` for third parties (DERIVED; derivation in the private audit of the third round) | ADR-52, [07](07-eval.md), [10](10-standards-per-layer.md) |
| OS7 | Decisions are public: permanent ones as ADR via PR, project name and API group before the first commit. | A change of the API group breaks every third-party plugin | Section 8, O17 |
| OS8 | Public documentation is in English from publication; this planning stays in German. | Contributors worldwide | ADR-53, O21 |

---

## 2. License and contributions

### 2.1 Decision (ADR-37, O16 decided)

**Apache-2.0 with DCO, no CLA, no open core.** Reasons (details in [`open-source-lizenz-und-recht`](../research/open-source-lizenz-und-recht.md) sections 2.1 to 2.4):
- Permissive and with an explicit patent license; contributions are under the same license without an additional agreement ("any Contribution intentionally submitted ... shall be under the terms and conditions of this License", §5); no trademark rights ("does not grant permission to use the trade names, trademarks", §6) ([apache2] VERIFIED).
- FSL, BSL, Sustainable Use License and the modified Apache license of Dify are not open-source licenses according to OSD point 6 ([osd], [bsl] VERIFIED). AGPL-3.0 deters companies that want to self-host (DERIVED).
- Agent tools without their own hosting business choose Apache-2.0 or MIT (Continue, Cline, Aider, Goose, PR-Agent, OpenHands core; VERIFIED in the research, section 2.2).
- Without a CLA, a later relicensing is only possible with the consent of all contributors. This is intended (DERIVED).

### 2.2 DCO

- Every commit carries `Signed-off-by: Name <mail>` according to DCO 1.1 ([dco]).
- Enforced twice: locally via a `commit-msg` hook (pre-commit) and in CI in the required check `ci-ok` (section 5). A PR without sign-off fails; this is part of the trial run in stage R.
- Bot commits (Renovate) without sign-off only for exactly the bot address; the maintainer takes over the PR with their own sign-off (pattern of the reference project, [`bothy-vorlage-projekt-setup`](../research/bothy-vorlage-projekt-setup.md) section 2.5).
- Commits written by an agent carry a `Co-Authored-By` line of the agent. The sign-off is given by the responsible human; with it, they confirm the DCO for the whole commit (DERIVED).

### 2.3 Required license files

| File | Content | Check |
|---|---|---|
| `LICENSE` | Apache-2.0, byte-for-byte identical to the original text | sha256 in the license gate |
| `NOTICE` | "Copyright The Guildwork Authors" (licensor: the founder privately, O20) and notices that adopted Apache parts require in their NOTICE (Apache-2.0 §4 (d)) | Review in the release gate |
| `THIRD_PARTY_NOTICES` | Name, version, SPDX identifier and copyright of every shipped dependency and every adopted code or prompt part | **generated** from SBOM and origin lines, never maintained by hand |
| `LICENSES/<SPDX>.txt` | License texts according to REUSE 3.3 ([reuse-spec]) | REUSE check in the license gate (check the tool's license before adoption) |
| SPDX header | `SPDX-License-Identifier` and `SPDX-FileCopyrightText` in the first lines of every handwritten file | License gate |

### 2.4 Adopted code and adopted prompts

- Only parts under licenses on the allowlist (section 5.2) are adopted. Ideas from AGPL, PolyForm or enterprise code are not adopted as code (ADR-34).
- Every adopted file, including every prompt file, carries an SPDX header and an origin line. Form (example):
  ```
  SPDX-License-Identifier: MIT
  SPDX-FileCopyrightText: <original rights holder>
  Origin: <owner>/<repo>@<commit>:<path>, modified
  ```
  In Markdown prompts, the block is an HTML comment. For Apache-2.0 sources, the change is marked (§4 (b)) and their NOTICE is adopted.
- **No leaked or proprietary texts in the public repo, not even as a quotation.** This applies to leaked system prompts, prompt techniques from leak collections and output texts of third-party services (CodeRabbit comments, Sonar findings). Reason: copyright in the text and contract clauses of the vendors (section 7). The list of leak sources is not published.
- Vendor documentation may be described with a link and in our own words; verbatim quotations only briefly and only from publicly accessible pages (DERIVED). This concerns only copyright. For CodeRabbit and SonarSource documentation, the contract also applies: even evaluating it for a reimplementation can fall under the CodeRabbit terms of use (1.9 with 4.2 (iv), section 5.3) or [sonar-aup] §5; according to O18 and O19, permanently no further evaluation ([10](10-standards-per-layer.md) section 16).

### 2.5 Chain of rights to the employer (V0, ADR-69)

The planning began as an evaluation assignment in the environment of the founder's employer (private preliminary work). O20 sets the founder privately as the licensor, and every sign-off confirms according to DCO 1.1 (a) "I have the right to submit it under the open source license" ([dco]). Whether rights to work results lie with the employer (such as § 69b UrhG for software from an employment relationship) is unverified for this case and is not legal advice; also open is in which role the founder works there. Without a CLA, an error can hardly be remedied afterwards, because third-party contributions build on the foundation (DERIVED).
- **Mandatory item V0 before V1** (section 4.4): either a written release or a waiver of rights by the employer for planning and code, or written evidence that planning and code were created outside working hours and without the employer's resources. The evidence is in the ops repo. V0 is an **Owner step** (Ruling R-E, O27): the project can neither replace it nor provide it itself.
- **Until V0 is proven:** no resources of the employer for the product (computers, runners, repos, accounts, API keys, working time), no public commit and no push to the product repo (stage R from R6).
- **Texts from the private preliminary work** do not go verbatim into the product repo; when in doubt, they are rewritten. The review is part of V7.
- **Status (2026-10-31): V0 proven** by the evidence of private creation (O27 decided, evidence in the ops repo). The two rules above on resources and texts continue to apply permanently, because the evidence only holds as long as they are followed. On 2026-11-01, the Owner confirmed that the Claude accounts used for planning and building are also private; the topic is thereby closed (O27).

---

## 3. Name and trademark

**O17 is decided (2026-10-31):** project name Guildwork, product repo `guildwork-dev/guildwork` in the organization (Owner, 2026-11-01; created on 2026-10-31 on the founder's personal account and transferred empty, private until V10), the private ops repo (name in the reference installation) on the founder's personal account, API group `guildwork-dev.github.io/v1alpha1` ([01](01-plugin-interfaces.md) section 1, [DECISIONS.md](../DECISIONS.md) section 3.2). Reason for fixing this before the first commit: the API group is in every third-party plugin manifest; a later change breaks all plugins.

Rules for the name:

| Rule | Evidence |
|---|---|
| No "CodeRabbit", no rabbit allusion. CODERABBIT is a registered US service mark with a design element (word and design mark), Reg. No. 7548845, "Registration Date: Oct. 29, 2024", "LIVE/REGISTRATION/Issued and Active", "Mark Type: Service Mark" | [tm-cr-uspto] VERIFIED (cross-check point 15); EU marks unverified |
| No "Claude", "Claude Code" or "Anthropic" in the name, logo or feature names: "you can't use the Claude Code or Anthropic names or logos as part of your own product, feature, or company name, in your own logo, or in a way that suggests Anthropic built, endorses, or is partnered with your product." | [cc-legal] VERIFIED |
| Factual mention is allowed: "You can accurately say, in plain text, that your product has Claude Code preinstalled or that it runs Claude Code." | [cc-legal] VERIFIED |
| Allowed for agents on the Agent SDK: "{YourAgentName} Powered by Claude"; not allowed "Claude Code" or "Claude Code Agent"; "Your product should maintain its own branding and not appear to be Claude Code or any Anthropic product." | [cc-sdk-overview] VERIFIED |
| No purely generic word ("Code Review AI"), because it cannot be protected and is hard to find | DERIVED |
| Comparisons in running text ("alternative to CodeRabbit") only factual, without third-party logos and without the appearance of a partnership; no published benchmarks against CodeRabbit or SonarQube (O18, O19; section 7) | DERIVED from the CodeRabbit terms of use 4.2 (iv) (section 5.3), [sonar-aup] §5 |

Procedure O17: npm, PyPI, GitHub and domains checked (2026-10-31), trademark register query in classes 9 and 42 without an earlier right (Owner, 2026-11-01, R-E04-T08). No own trademark and no purchased domain, because no company is formed (Owner); the API group therefore depends on the Pages domain of the organization. Replacement names in case of a collision before the first public commit: [DECISIONS.md](../DECISIONS.md) section 3.2.

---

## 4. Two repos and publication (ADR-38)

### 4.1 Structure

| Repo | Visibility | Content |
|---|---|---|
| **Product repo** | public from the first push | Code, `docs/` (platform documentation in English), installation package, public eval sets, community files, check tools, configuration drafts for third-party reviewers |
| **Ops repo** | private, per installation | Instance configuration, runbooks, the private deny list and `allow-authors.txt`, private eval sets, preliminary research, documents of the reference installation, raw data |

Reason: requirement 2 demands a company-neutral product; but every installation has values that must not be public. The pattern already works in the reference project ([`bothy-vorlage-projekt-setup`](../research/bothy-vorlage-projekt-setup.md) section 2.10, VERIFIED).

The situation is favorable: today's planning repo has no commit yet (`git log`: "does not have any commits yet", VERIFIED, cross-check point 32). The public history therefore begins with **one** root commit without planning history. Today's folder becomes the ops repo; what becomes public is newly taken over by the product repo.

### 4.2 Paths of this project and their publication status

Status: **public** (as is), **public after neutralization** (first remove references to companies, persons and hosts as well as local paths, replace references to private sources, then translate according to O21), **private** (ops repo only).

| Path | Status | Reason |
|---|---|---|
| `docs/architecture/README.md` | public after neutralization | Title and assignment are neutral; since R-E04-T02 it names no company, persons, accounts or local paths and no longer refers to non-public preliminary research; still to be checked before the translation are the owner decisions (O numbers), the chronicle of rounds in section 7, the reference to the private ops repo and the sources with contract texts of CodeRabbit and SonarSource |
| `docs/architecture/01` to `09` | public after neutralization | Core of the platform documentation; company references according to a private audit of the third round |
| `docs/architecture/10-standards-per-layer.md`, `11-installation-and-hosting.md`, this file | public after neutralization | newly written and neutral; checked with the deny scan like everything else |
| `docs/architecture/backlog-minors.md` | public after neutralization | Project knowledge; entries referring to a specific installation are phrased neutrally |
| `docs/research/README.md` | public after neutralization | Index; lines about private files are dropped in the public version |
| `docs/research/ebene-*.md`, `ebenen-landkarte.md`, `hosting-und-installation.md` | public after neutralization | domain research; they name the Owner, company repos and local paths |
| `docs/research/open-source-lizenz-und-recht.md`, `gegenpruefung-lizenz-und-recht.md` | public after neutralization | Reading of the terms with passage locations; section 2.9 and L6 name the company |
| `docs/research/bothy-vorlage-projekt-setup.md` | public after neutralization | The reference project is a public repo; local checkout paths are replaced by references to the public repo with commit 4485084b8, without the repo URL (4.4); the older planning state is not in the public repo and is not linked |
| Documents of the reference installation (values, hosts, accounts, decisions of a specific installation) | private | belong to an installation, not to the platform |
| Preliminary research, audit of the company references, raw data with outputs of third-party services | private | Company reference, leak sources, outputs of third-party services (O18) |
| private eval sets and transcripts (future) | private | Company code, personal data |

This file does not name individual private files; their classification is kept by the publication manifest in the ops repo.

Consequence for references: [docs/architecture/](README.md) and the public research files no longer refer to non-public preliminary research after neutralization (R-E04-T02, R-E04-T03) and no longer carry a note for a private source; where evidence was missing, a public source or a research file is cited, otherwise the statement is deleted. Which source keys and notes count as private is kept in the lists of the check tool in the ops repo ([detailed design 00](../design/00-codebase-and-conventions.md) section 4.6).

### 4.3 Deny list scanner

- **List:** private in the ops repo (company and person names, host names, internal repo names, network ranges, local home paths), plus `allow-authors.txt` with the one allowed author identity and the committer identity of squash merges via the web interface (GitHub `web-flow`). The initial terms for this project are maintained by the reference installation in the ops repo, not by this file.
- **Checked:** file contents, file names, commit messages, author and committer identities, refs, PR title and PR text (via environment variables, never interpolated in the script) (pattern of the reference project, [`bothy-vorlage-projekt-setup`](../research/bothy-vorlage-projekt-setup.md) sections 2.5 and 2.10).
- **When:** locally in `make check` and in the pre-push hook; in CI as job `denylist` in the required check `ci-ok`; after every push to `main` (`denylist-main.yml`); before making public, over the entire history of a fresh clone.
- **CI access to the list:** as a secret of a GitHub environment `denylist`, only for PRs from the repo and for `main`. Fork PRs and PRs from bots (GitHub account type `Bot`, such as Renovate) run with the generic rules (`--allow-missing`); the maintainer run after takeover checks fully.
- **Third-party contributions:** a squash merge keeps the person as author; a merged PR of another contributor or of a bot would turn the scan of the push to `main` red with `identity-not-allowed`. Third-party contributions are therefore taken over by a maintainer with their own commit, instead of extending `allow-authors.txt` per contributor (Ruling R-E03-T02, [Detailed design 00](../design/00-codebase-and-conventions.md) section 3.5).
- **Rule "0 hits":** a hit is a red check, not a notice. Exceptions only exactly per value with a reason in the PR, never per file.

### 4.4 Publication checklist

Worked through in this order, each item with evidence (command output in the ops repo). Reference: `docs/quality/public-switch.md` of the reference project ([`bothy-vorlage-projekt-setup`](../research/bothy-vorlage-projekt-setup.md) section 3.2).

| No. | Item | Evidence |
|---|---|---|
| V0 | Chain of rights to the employer clarified (section 2.5, ADR-69): written release or waiver of rights by the employer, or recorded evidence of private creation (outside working hours, without the employer's resources); **Owner step** (O27). **Proven 2026-10-31** (evidence of private creation) | Document in the ops repo; without V0, V1 does not begin |
| V1 | O16 (license), O17 (name, API group), O20 (licensor) and O21 (language) are decided; all placeholders (`[<]project>`, `[<]project-domain>` in bracket form as in the check column, owner handle in CODEOWNERS) are replaced | `grep -rnE --exclude-dir=research "[<]projekt\|[<]Projekt\|[@]OWNER\|[<]projekt-domain[>]" .` without hits (form and exclusion: [detailed design 00](../design/00-codebase-and-conventions.md) FE-065) |
| V2 | Documentation neutralized and translated into English (O21); research files either neutralized with the header note "dated, not binding" or private; the lines and sources affected by O18 and O19 ([10](10-standards-per-layer.md) section 16) are deleted or backed by third-party sources | Review plus V3; deny scan with the leak terms (documentation domains of both vendors) |
| V3 | Deny scan with the private list over working tree and history: **0 hits**. The same check then runs in every PR (4.3) | `make denylist`, `make denylist-history` |
| V4 | gitleaks over all commits of a fresh clone, with default rules plus a rule for every Anthropic credential (5.1) | `make gitleaks GITLEAKS_LOG_OPTS=--all` green |
| V5 | History starts clean: exactly one root commit with the chosen identity, no planning history | `git rev-list --count HEAD` returns 1; `git log --format='%an %ae %cn %ce'` only the allowed identity |
| V6 | License gate green, ScanCode over all files of HEAD (raw, including `export-ignore` files) without an unexpected license, `NOTICE` and `THIRD_PARTY_NOTICES` complete | Gate output |
| V7 | No leaked or proprietary text, no outputs of third-party services, no `data/` in the tree, no text adopted verbatim from the private preliminary work (section 2.5); the same for issues, comments and the project of the product repo that become public with it (work plan as issues, [Plan](../plan/README.md) section 8) | Review plus deny list with leak terms, also over all issues and comments |
| V8 | Secrets that were ever in planning files or logs are rotated | List in the ops repo |
| V9 | Red Team over the whole state with `Urteil: JA` | `.review/<sha>.md` |
| V10 | Only then: make the empty repo public, then push as `main` (stage R, section 6 R6) | Repo setting |

Reference project (Ruling 2026-11-01): publicly, the reference project is only named via [`bothy-vorlage-projekt-setup`](../research/bothy-vorlage-projekt-setup.md) with the commit, without a link, because the repo URL contains a term of the private deny list. A public link would need an exception for exactly this value (4.3) or a transfer of the reference repo; neither is planned. V2 and V3 check this as well.

---

## 5. Development repo and check tools

The product repo is set up following the pattern of the reference project ([`bothy-vorlage-projekt-setup`](../research/bothy-vorlage-projekt-setup.md) sections 2 and 3.1, VERIFIED). The pattern is adopted, not the project-specific parts (Go, Dart, apps, macOS runners).

### 5.1 Basic rules

| Rule | Content | Reason |
|---|---|---|
| `make check` equals CI | The same gates locally and in CI; a red CI run after a green `make check` is a defect of the toolchain | no surprise after the push |
| One required check | Only `ci-ok` is required in the ruleset; it aggregates all jobs and runs with `always()` | Path filters and new jobs do not change the ruleset |
| Public from the first push | No private pre-run, no runner switch | simpler, free ([gh-runners]: "Use of the standard GitHub-hosted runners is free and unlimited on public repositories", VERIFIED) |
| Only GitHub-hosted standard runners | Fixed labels `ubuntu-24.04` and `ubuntu-24.04-arm`; no self-hosted runners, no larger runners, no `*-latest` | no third-party code on our own hardware; cost 0 |
| Workflow policy via tool | A check script (reference `check_runners.py`) forbids: runners outside the labels, actions without a full commit SHA, missing `timeout-minutes`, `permissions` broader than `contents: read` at the top, `actions: write`, `pull_request_target`, untrusted values outside of `env` | Supply chain |
| Concurrency | at most 2 concurrent PR runs with at most 6 jobs each, `concurrency` cancels superseded runs; measure the wait time per run via the Actions API (the starting value is an estimate from [`bothy-vorlage-projekt-setup`](../research/bothy-vorlage-projekt-setup.md) section 3.1 e) | Account concurrency limit ([gh-limits]) |
| Red Team gate | Before every push and local merge, an independent, read-only reviewer over the diff against `main`; report `.review/<sha>.md` (git-ignored); the pre-push hook requires exactly `Urteil: JA` as the last line; fork contributors via `REVIEW_SKIP=1`, the maintainer checks afterwards | Checklist adapted to the security rules from [05](05-security.md): Effect Gateway is the only write point, no credential in the sandbox, command covers effect |
| Text rules | no dashes, no instance data, glossary terms | Hook in pre-commit |

### 5.2 Gates of `make check` and CI

| Gate | Tool | License | From |
|---|---|---|---|
| Format, lint, types | Prettier or Biome, ESLint, `tsc`; for tools in Python, ruff and mypy | MIT or Apache-2.0 according to the vendor (unverified, check with the tool choice in stage R) | R |
| Tests and coverage | Vitest or Node test runner; threshold as a named value | as above | R |
| Commit rules | Conventional Commits, DCO | | R |
| Workflows | actionlint, zizmor, workflow policy (5.1); `renovate.json` with check-jsonschema against the bundled Renovate schema | MIT according to the reference project; check-jsonschema Apache-2.0 | R |
| Secrets | gitleaks as CLI, default rules plus a custom rule for every Anthropic credential (prefix family `sk-ant-`), later OpenAI, GitHub App and Azure formats; allowlist only per exact test value | MIT according to the reference project | R |
| Rule SAST | **Opengrep** (engine LGPL-2.1, [opengrep]) only with our own rules including rule tests; first rules: only the Effect Gateway imports the SCM write client; the control plane and the sandbox side read no `ANTHROPIC_*` or `CLAUDE_*` variables. No Semgrep registry rules, no Opengrep rule collection (section 7) | LGPL-2.1 | R |
| Code scanning | **CodeQL** (`javascript-typescript`, `actions`, `python` for tools, suite `security-extended`), only with a public repo. Free, because the repo is OSI-licensed and on GitHub.com ("Perform analysis on the Open Source Codebase"; CI only "If the Open Source Codebase is hosted and maintained on GitHub.com", [codeql] VERIFIED) | GitHub CodeQL Terms | R |
| Supply chain assessment | OpenSSF **Scorecard** with SARIF upload, weekly and on changes to the protection rules; free for public repos ([scorecard] VERIFIED) | Apache-2.0 according to the reference project | R |
| Vulnerabilities | osv-scanner on lock files; a PR fails only on dependencies it changes itself; daily full scan of `main` (`advisories.yml`, job `osv-full`) | Apache-2.0 according to the reference project | R |
| License gate | `LICENSE` checksum, SPDX headers, dependencies against the allowlist (0BSD, Apache-2.0, BSD-2-Clause, BSD-3-Clause, BSL-1.0, CC0-1.0, ISC, MIT, MIT-0, MPL-2.0, PSF-2.0, Python-2.0, Unicode-3.0 and Unicode-DFS-2016, Zlib; list of the reference project, VERIFIED; plus, since 2026-11-01, BlueOak-1.0.0 and PostgreSQL, because Node.js ships minimatch and the bundle ships PostgreSQL and pgvector under these permissive licenses, Ruling after R-E01-T07; the runtime images therefore contain neither npm nor Corepack, whose Artistic-2.0 is not on the list; license per tool with the location of the passage in `docs/quality/toolchain.md` of the build repo); GPL, AGPL, SSPL, BUSL only as a separate process with justification; ScanCode before every release and before making public, plus daily over `main` (`advisories.yml`, job `scancode`) | ScanCode: Apache-2.0 AND CC-BY-4.0, checked 2026-11-01 (R-E01-T07) | R |
| Deny scan | 4.3 | own tool | R |
| Dependencies up to date | **Renovate** as a hosted GitHub App: grouped, `minimumReleaseAge` 7 days, majors via dashboard, at most 5 open PRs (values of the reference project); lock file maintenance off, because Renovate does not apply the waiting period there (transitive versions change with the manifest update that needs them; Rulings in [Detailed design 00](../design/00-codebase-and-conventions.md) section 2.11). Renovate is AGPL-3.0 and is not bundled, only used as a service. Terms and permissions of the hosted app reviewed on 2026-11-01 (R-E05-T07, decision sheet in the ops repo): free tier at no cost, installed only on the product repo, no bypass exception in the ruleset; replacement if needed Dependabot | | R |
| Container | Trivy (misconfiguration, image), version pinned, Renovate off for Trivy (lesson of the reference project after a compromised version, cited there, not rechecked) | Apache-2.0 according to the reference project | 0 |
| Release | SBOM (Syft), image first by digest, then Trivy, then tag; cosign keyless and GitHub attestation; release secrets only in environment `release` with a required reviewer; no proprietary binaries in the image (ADR-39) | | first release (stage 0) |
| Portability test | fresh runner amd64 and arm64: installation via the documented command without login, signature verification, smoke test of control plane plus worker, restore test (details [11](11-installation-and-hosting.md)) | | Stage 0 |

### 5.3 Third-party reviewers CodeRabbit and SonarQube (requirement 3)

**Decision:** CodeRabbit and SonarQube are **not connected** to the development repo, and there is **no inquiry** to the vendors (O18, O19 decided, 2026-10-31). Reason: by their wording, both sets of contract terms prohibit exactly our case. Requirement 3 ("as with bothy") cannot be transferred one to one, because bothy is not a competing product (DERIVED, [`open-source-lizenz-und-recht`](../research/open-source-lizenz-und-recht.md) sections 2.6 and 2.7).

**The clauses (VERIFIED, verbatim):**

| Vendor | Location | Wording |
|---|---|---|
| CodeRabbit | Terms of Service, "Updated: April 20, 2026", 4.2 (iv) | "disclose the results of any benchmarking of the Services, or use the Services to develop competing products or services without CodeRabbit's prior written consent" |
| CodeRabbit | Terms of Service, 4.2 (ii) | "decompile, disassemble, reverse engineer or otherwise attempt to derive the source code, underlying ideas, techniques, structure or algorithms of the Services" |
| CodeRabbit | Terms of Service, 5.4 "Effect of Termination" | "any terms or conditions that by their nature should survive such termination will survive, including Sections 3-13." |
| SonarSource | [sonar-aup] "Last updated November 7, 2025", §5, each "without prior written consent" | "Access or use the Products or Documentation if you are a direct competitor of SonarSource."; "Disclose, publish, or otherwise make publicly available any benchmark, comparative, or performance tests or evaluations of the Products." |
| SonarSource | [sonar-aup] §6 | "Use Results Data to develop, build, or enhance products or services that compete with the Products, including but not limited to static code analysis tools, code quality platforms, security scanning tools, or code review systems (whether based on LLM Technologies or not.)" |
| SonarQube Community Build (analyzers under SSALv1) | [ssal] "Last Updated November 13, 2024", definition "Non-competitive Purpose" (c) | "employing, using, or engaging artificial intelligence technology that is not part of the Program to ingest, interpret, analyze, train on, or interact with the data provided by the Program" |

**Reading (DERIVED):** CodeRabbit on the repo of a CodeRabbit replacement is "use the Services to develop competing products". SonarQube Cloud hits §5 and §6, because the platform is a code review system and SonarSource itself markets "AI code review" (VERIFIED, cross-check point 19). The Community Build hits (c) as soon as an AI agent (Red Team reviewer, Coder, our own reviewer) reads its findings; that is the core of the development process. It therefore also stays off (O19). Evaluating the vendor documentation for a reimplementation can also fall under the clauses (according to the Red Team review of 2026-10-31, the CodeRabbit terms of use count the website and content among the "Services" in 1.9; [sonar-aup] §5 names "Documentation" explicitly); therefore no further evaluation, previous evaluations are affected ([10](10-standards-per-layer.md) section 16).

**Replacement (permanent):**
- the platform's own reviewer in dogfooding from stage 1 (see below);
- CodeQL, Opengrep with our own rules, linters, type checking, osv-scanner, gitleaks (5.2);
- Red Team gate before every push;
- Rule of the reference project, adapted: a finding that only a third-party reviewer or our own reviewer finds and that a human confirms becomes a local rule (Opengrep rule, test or lint).
- CodeRabbit outputs from other projects do not serve as ground truth (O18); comparison runs against CodeRabbit or SonarQube are not published ([10](10-standards-per-layer.md), [07](07-eval.md)).

Drafts for a CodeRabbit and a SonarQube configuration from the third round are discarded (O18, O19) and are not part of this documentation, so that the public repo does not indicate usage that does not take place.

### 5.4 Dogfooding

The platform reviews its own repo as soon as stage 1 is in place. Rules (DERIVED from [05](05-security.md) section 3 and ADR-48):
- **Credential:** the Owner's Claude subscription in personal operator mode (`subscription`, O28). Only runs that the Owner triggers themselves go through the subscription ([05](05-security.md) section 6 condition 3), that is, reviews of their own PRs; a public repo with third-party contributions would otherwise be usage "on behalf of their users" ([cc-legal]). Third-party contributions therefore get no platform run as long as the project uses no other credential; they are checked by CodeQL, Opengrep, the linters and human maintainers. Services with a shell do not run on the public repo via the subscription (condition 9 requires a private repo).
- **PRs from maintainers:** reviewer first `shadow`, `live` only after Gate A and Gate B or an adopted reference qualification (ADR-47).
- **PRs from forks (third-party code):** until stage 9 (MicroVM required before third-party code), only the reviewer without build verifier, no execution of repo code; Coder and PR-Fixer do not run on fork PRs.
- **App:** own GitHub App via manifest flow (ADR-45), pool `self-hosted` of the project with `single_operator: true` (condition 2 for `subscription`).
- **Eval benefit:** our own outputs on our own Apache-2.0 repo are license-clean. Findings confirmed by humans may go into the public eval set (ADR-52), outputs of third-party services may not.

---

## 6. Stage R: repo foundation

Stage R comes before stage 0 ([08](08-roadmap.md)). It builds no product, but the public repo with all check tools.

**Steps** (process of the reference project, [`bothy-vorlage-projekt-setup`](../research/bothy-vorlage-projekt-setup.md) section 3.2):

| No. | Step | Who |
|---|---|---|
| R0 | Prove V0: chain of rights to the employer (section 2.5, O27); no resources of the employer for the product. **Done 2026-10-31** | **Owner** |
| R1 | Create the product repo and the private ops repo (name in the reference installation) as private (**done 2026-10-31**, the product repo stays empty); create the organization `guildwork-dev` (**done 2026-11-01** by the Owner in the web form with the Free plan, no API path on github.com, O17) and transfer the product repo there (**done 2026-11-01**, now `guildwork-dev/guildwork`) | Owner (org in the web form), agent (repos on instruction) |
| R2 | Locally without a remote: scaffold with community files (section 8), `LICENSE`, `NOTICE`, `.pre-commit-config.yaml`, `.gitleaks.toml`, Opengrep rules with tests, workflow policy with tests, license gate, deny scanner, `make bootstrap` and `make check` green; tool choice (Prettier or Biome, Vitest or Node test runner) with license in `toolchain.md` | Agent |
| R3 | Create the private deny list and `allow-authors.txt` in the ops repo | Owner and agent |
| R4 | Check the workflow set once locally against the policy (lesson of the reference project: the first CI run broke there) | Agent |
| R5 | Publication checklist V1 to V9 (4.4), only after V0 is proven | Agent, Red Team |
| R6 | Make the empty product repo public (on the Free plan, environments and environment secrets exist only in public repos; settings sheet in the ops repo, R-E05-T01), create the environment `denylist` with secrets, push the root commit as `main`; enable Private Vulnerability Reporting, Secret Scanning and Push Protection | **Owner** |
| R7 | Ruleset for `main`: PR required, squash only, required check `ci-ok`, linear history, signed commits, no force push, no deletion; "Require actions to be pinned to a full-length commit SHA"; environment `release` with a required reviewer | **Owner** |
| R8 | Install the Renovate app; CodeQL and Scorecard run without an account | **Owner** (app), agent (workflows) |
| R9 | Trial run: a PR from the repo (full), a PR from a fork (generic rules), a PR without sign-off (must fail on `ci-ok`) | Agent |
| R10 | Dropped: no CodeRabbit app, no SonarQube Cloud organization, no inquiry (O18, O19 decided) | dropped |

**Steps that only the Owner can do:** V0 (chain of rights, R0), repo account and name (O17), commit identity, repo settings and ruleset (R6, R7), environment secrets, installation of apps (Renovate). Trademark registration and domain are dropped (O17).

**Done criterion** (each with evidence):
0. V0 proven (document in the ops repo).
1. `ci-ok` green on the trial PR; all jobs ran on standard runners (job log).
2. Fork PR green with reduced checks; PR without sign-off red.
3. `denylist-main.yml` green for the first push; deny scan of the history 0 hits.
4. gitleaks over all refs of a fresh clone green; license gate and ScanCode green.
5. CodeQL and Scorecard ran on `main` and uploaded SARIF.
6. Red Team verdict `JA` over the state of the root commit.
7. Money: 0 (estimate for standard runners of public repos and free services).

SonarQube and CodeRabbit are not part of the done criterion (O18, O19: not connected).

---

## 7. Terms of use that affect the project

All sources retrieved on 2026-10-31, quotations verbatim (VERIFIED, confirmed by cross-check), consequences DERIVED. Dashes present in the original are replaced by " - " according to the text rule.

| Condition | Quotation | Location | Consequence for the product | Consequence for development |
|---|---|---|---|---|
| Anthropic Claude Code Legal | "preinstalling or running Claude Code in your products or services (e.g. in hosted sandboxes or other agent infrastructure) requires agreeing to our Commercial Terms of Service"; "The Claude Code binary must not be modified." | [cc-legal] | Neither Claude Code nor the Agent SDK including platform packages in our images, no SDK dependency; installation of the CLI at the operator with a pinned version and checksum (ADR-39). The SDK platform packages contain the native CLI ("Native CLI binary for @anthropic-ai/claude-agent-sdk on darwin-arm64", [sdk-npm] VERIFIED according to cross-check point 7) | none |
| Anthropic Claude Code Legal | "Anthropic does not permit third-party developers to offer Claude.ai login into their own applications, or to route requests through Free, Pro, Max, or Ultra plan credentials on behalf of their users. Moreover, developers may not collect, store, or intermediate Claude.ai credentials or session tokens - sign-in to a Claude account must complete through Anthropic's own flow." | [cc-legal] | `subscription` only as a personal operator mode, locked by default, enabled with `acknowledge_terms`; no login of our own; the operator generates the token themselves, the worker binary only passes it through locally to the `claude` process, the control plane never sees it; whether this counts as "intermediate" is an operator risk (ADR-51, ADR-57) | Dogfooding on the public repo never with a subscription (5.4) |
| Anthropic Claude Code Legal | "Developers building products or services that interact with Claude's capabilities, including those using the Agent SDK, should use API key authentication through Claude Console or a supported cloud provider." | [cc-legal], section "Authentication and credential use" | The platform's default credential is an API key or cloud provider | The project uses only the Owner's Claude subscription for development, eval and dogfooding (O28, owner decision against the earlier recommendation "API key for automated runs"); residual risk lies with the Owner |
| Anthropic Consumer Terms (EEA version, "Effective Oct 8, 2025", for consumers only) | §3: "Except when you are accessing our Services via an Anthropic API Key or where we otherwise explicitly permit it, to access the Services through automated or non-human means, whether through a bot, script, or otherwise."; §3: "To develop any products or services that compete with our Services ..."; §11: "Non-commercial use only." | [an-consumer] | Autonomous continuous operation via a subscription is a gray area; the documentation warns when `subscription` is enabled | Interactive development with a consumer subscription: competition question unresolved, no inquiry (O26, below); this version does not apply to business activity, which version applies then is unverified |
| Anthropic API credit in plans | Max "$100", Ultra "$200", Team "capped at $500"; "Doesn't roll over."; "Free, Pro, and Enterprise plans aren't eligible." | [cc-credits] | no relevance to the product | Path without a gray area for runs with the Agent SDK and `claude -p`, without extra cost only up to the monthly limit; not used by the project, because it requires API key or Console access (O28) |
| Anthropic Commercial Terms ("Effective Jun 17, 2025") | D.4: "Customer may not and must not attempt to (a) access the Services to build a competing product or service, including to train competing AI models or resell the Services except as expressly approved by Anthropic; (b) reverse engineer or duplicate the Services" | [an-commercial] | applies to every operator with an API key; competition question unresolved, no inquiry (O26, below) | as on the left |
| Anthropic Usage Policy (displayed "Effective Nov 12, 2026"; currently applicable version unverified) | "Agentic use cases must comply with the Usage Policy. Users are responsible for ensuring that agents they build or deploy ... comply with this Usage Policy."; "This section does not prohibit security research, testing, or tool development conducted on systems you own or operate, with the authorization of the system owner" | [an-aup] | Operators are responsible; the installation documentation says so; security functions only on own or authorized repos | none |
| Anthropic Agent SDK branding | "{YourAgentName} Powered by Claude"; not "Claude Code" or "Claude Code Agent" | [cc-sdk-overview] | Naming rule (section 3) | none |
| CodeRabbit Terms of Service ("Updated: April 20, 2026") | 4.2 (iv) and (ii) as in 5.3; 4.2 (vi): "use any automated system or software (including robots, spiders, or scripts) to extract data or content from the Services"; 5.4 survival "including Sections 3-13" | CodeRabbit Terms of Service | No CodeRabbit outputs as training or eval data, no published comparisons | no CodeRabbit on the repo (O18); no further derivations from CodeRabbit outputs as long as a customer relationship exists; no further evaluation of the CodeRabbit documentation for a reimplementation (O18) |
| SonarSource AUP ("Last updated November 7, 2025") | §5 and §6 as in 5.3; plus §5: "Create, market, or distribute add-ons or enhancements to the Products, or incorporate the Products into another product." | [sonar-aup] | No SonarQube in the product and no bundled Sonar plugin; at most a neutral SARIF import under the operator's responsibility (ADR-50) | no SonarQube Cloud on the repo; no further evaluation of the SonarSource documentation for a reimplementation (O19) |
| SonarSource Available License v1 (analyzers of the Community Build) | Definition "Non-competitive Purpose" (c) as in 5.3; "Competing" means "marketing a product or service as a substitute for the functionality or value of SonarQube ... even if it is provided free of charge." | [ssal] | Never market the platform as a replacement for SonarQube; do not ship analyzers of the Community Build | Community Build not in the agent loop (O19) |
| Semgrep Rules License ("Last updated: December 13th, 2024") | "You may use the rules only for your own internal business purposes. This license does not allow you to distribute the rules, or to make them available to others as a service." | [semgrep-rules] | Never ship registry rules (ADR-50); own rules under Apache-2.0 | only own rules |
| Opengrep rule collection | "Commons Clause" License Condition v1.0 on LGPL-2.1, licensor Semgrep, Inc.; only "Sell" is forbidden (redistribution "for a fee or other consideration", including hosting and support fees) | [opengrep-rules], clarification cross-check point 24 | do not ship: operators who host the platform for a fee would be selling (DERIVED) | not needed, own rules |
| CodeQL CLI | "Perform analysis on the Open Source Codebase"; CI only "If the Open Source Codebase is hosted and maintained on GitHub.com"; no "provide or make available the Software as a hosted solution" | [codeql] | never in the image, never run by the platform for third parties; only import of existing code scanning results | free on our own public repo |
| OpenAI Codex authentication | "Use API key authentication for programmatic Codex CLI workflows, such as CI/CD jobs. Don't expose Codex execution in untrusted or public environments." | [codex-auth]; OpenAI Terms of Use unread (HTTP 403) | `chatgpt` only as a personal operator mode like `subscription` (ADR-51); pipelines with an API key | none |
| Gemini CLI ("Last updated: Apr 10, 2026") | "Directly accessing the services powering Gemini CLI (for example, the Gemini Code Assist service) using third-party software, tools, or services ... is a violation of applicable terms and policies." | [gemini-tos] | Google login only in the unmodified CLI, never its token in our own code; pipelines with a Gemini API key or Vertex | none |

**Competition clauses (O26 decided, 2026-10-31):** Whether Anthropic considers a review or agent product based on Claude as "compete with our Services" (Consumer Terms §3) or "competing product or service" (Commercial Terms D.4) is unresolved. It affects every product based on Claude and every credential kind, not only the subscription. The Owner decided not to send an inquiry to Anthropic; the planning stays unchanged, because the text of Anthropic's own documentation explicitly provides for products on the Agent SDK ([cc-sdk-overview], [an-commercial] A.1 "to power products and services Customer makes available to its own customers and end users", DERIVED).

---

## 8. Governance and support

Pattern of the reference project ([`bothy-vorlage-projekt-setup`](../research/bothy-vorlage-projekt-setup.md) section 2.10, VERIFIED), numbers as named values in the files, not here.

| File or rule | Content |
|---|---|
| `GOVERNANCE.md` | Start with one maintainer (the Owner); maintainers are listed in `.github/CODEOWNERS`; new maintainers via PR with the consent of all existing ones; changes to the governance only with the consent of all maintainers |
| Decisions | permanent decisions as ADR (MADR form) via PR in `docs/adr/`; smaller ones in the Ruling log `docs/DECISIONS.md`. The ADRs from [09](09-decisions.md) move there |
| Lazy consensus | from two maintainers: a PR with an ADR counts as accepted if no maintainer objects within the named period |
| `SECURITY.md` | the only reporting channel is GitHub Private Vulnerability Reporting, no mail address, no bounties; target times for acknowledgment and assessment as named values |
| Triage labels | `.github/labels.yml` versioned; new issues via form with `status: triage`; type labels (`type: bug`, `type: feature`, `type: docs`), area labels per service and plugin kind; target time for the first triage as a named value. Later the service `triage` helps (proposal; closing only as the repo opt-in `auto_close` after a green T1, O25) |
| `CONTRIBUTING.md` | `make bootstrap`, `make check`, DCO, Conventional Commits, documentation belongs to the change, no dashes; fork switches for the deny list and Red Team evidence |
| `CODE_OF_CONDUCT.md` | Contributor Covenant; set the version in stage R; reporting channel as in `SECURITY.md` |
| `SUPPORT.md` and support promise | Community project without commercial support; questions about an installation go to its operator. Promised are: security fixes for the newest minor version at any time; plugin and service interfaces without a stability guarantee as long as they are `v1alpha1`; from `v1beta1`, deprecation over at least one minor version with both `apiVersion` in parallel ([01](01-plugin-interfaces.md)); upgrade and migration path per release ([11](11-installation-and-hosting.md)) (DERIVED) |
| Releases | SemVer, `CHANGELOG.md`, no `latest` tag, signed images with SBOM (5.2); reference qualification published per release (ADR-52) |

---

## 9. Owner decisions of this file (details in [DECISIONS.md](../DECISIONS.md) section 3)

| No. | Question | Decision or recommendation | Reason |
|---|---|---|---|
| O16 | License | **Decided:** Apache-2.0 with DCO, no CLA, no open core | Section 2.1 |
| O17 | Project name, trademark, repo name, API group | **Decided:** Guildwork, `guildwork-dev/guildwork` plus a private ops repo, API group `guildwork-dev.github.io/v1alpha1`; no trademark, no domain ([DECISIONS.md](../DECISIONS.md) section 3.2) | Section 3 |
| O18 | CodeRabbit on the development repo, CodeRabbit outputs as eval data, documentation for the planning | **Decided:** do not connect, no inquiry to CodeRabbit; permanently no CodeRabbit outputs as ground truth and no further evaluation of the documentation for a reimplementation; replacement according to 5.3 | CodeRabbit terms of use 1.9, 4.2 (iv) |
| O19 | SonarQube on the development repo, documentation for the planning | **Decided:** do not connect, no inquiry to SonarSource; permanently neither Cloud nor Community Build in the process and no further evaluation of the documentation for a reimplementation | [sonar-aup] §5, §6; [ssal] (c) |
| O20 | Licensor and copyright | **Decided:** the founder privately ("The Guildwork Authors" in NOTICE) | a later change would need the consent of all contributors |
| O21 | Language of the public documentation | **Decided:** English from publication; the planning stays in German until then (ADR-53) | contributors worldwide; the reference project translated on the day it was made public |
| O26 | Inquiry to Anthropic about the competition clauses | **Decided:** no inquiry, planning unchanged | Section 7 |
| O27 | Chain of rights to the employer (V0) | **Decided (Owner, 2026-10-31):** evidence of private creation, V0 proven; the rules from ADR-69 continue to apply permanently; closed on 2026-11-01 (the Claude accounts are also private) | Section 2.5; DCO 1.1 (a) |
| O28 | Claude only, via the subscription | **Decided (Owner, 2026-11-01):** development, eval, reference qualification and dogfooding only via the Owner's Claude subscription; no other vendor account, no API key or Console access as a prerequisite | Sections 5.4 and 7 |

Settled by requirement 2: O14 (delivery to third parties) is decided, the project is open source.
