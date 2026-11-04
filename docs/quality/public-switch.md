<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->

# Release checklist V0 to V10

The repository becomes public with its first push. Before that push, the points V0 to V10 run once, in this order, each with evidence (architecture 12 section 4.4, detailed design 00 section 4.7).

## Setting

Two repositories take part:

- the **build repository**: local, without a remote until V10 (FE-031). Every plan task is a branch merged into its local `main`; its history is never pushed.
- the private **operations repository** of the installation: it holds the private deny list, the allowed commit identities (`allow-authors.txt`), the list of leak terms, the export manifest with its tools and the evidence of this checklist.

The public history starts with **one** root commit, created from the tree of the build repository in a fresh directory (V5). Every point records its evidence in the operations repository as `publish/evidence/V<n>.txt`: date, checked commit, command and complete output.

## Checklist

| No. | Command or step | Green means | Who |
|---|---|---|---|
| V0 | Chain of rights: the owner's employer has released the work, or evidence of private creation (outside working hours, without the employer's means) is recorded | evidence recorded (done 2026-10-31) | owner |
| V1 | `grep -rnE` over the build repository for the placeholders that templates use for the project name, its domain and the code owner (exact pattern in detailed design 00 section 4.7); the owner decisions on license, name, licensor and language recorded as decided in `docs/DECISIONS.md`; trademark register search for the name | 0 matches; no collision in the register, or a replacement name chosen | agent; owner for the trademark |
| V2 | Export manifest complete; documentation neutralized and translated, every check step of the neutralization and translation flow (detailed design 00 section 4.6) | every check step with 0 findings | agent |
| V3 | In a fresh clone of the root commit: `make denylist DENYLIST_FILE=<ops>/denylist.txt ALLOW_AUTHORS_FILE=<ops>/allow-authors.txt` and `make denylist-history` with the same files | 0 findings | agent |
| V4 | In a fresh clone: `make gitleaks GITLEAKS_LOG_OPTS=--all` | 0 findings | agent |
| V5 | `git rev-list --count HEAD`; `git log --format='%an <%ae> %cn <%ce>'` | `1`; only identities from `allow-authors.txt` | agent prepares and checks, owner commits |
| V6 | `make licenses`, `make scancode`, `tools/ci/third_party_notices.py --check`, reading `NOTICE` | green, no unexpected license | agent |
| V7 | Deny-list scan with the leak terms; overlap check against the private prior work (word shingles of 12 words, FE-035); `test ! -e data`; deny patterns for vendor documentation; scan of the issues, comments (on pull requests too) and project items of the product repository with the deny list and the leak terms (FE-064) | 0 matches; no sequence of 12 or more words equal to private prior work; 0 matches in issues, comments and project | agent |
| V8 | List of every secret that ever stood in planning files or logs (gitleaks with `.gitleaks.toml` over the history of the operations repository and the log locations it names); counter check of the list itself with `gitleaks dir --config .gitleaks.toml <list>`; rotation | every line with its rotation date, counter check 0 findings | agent (list), owner (rotation) |
| V9 | Red team over the whole tree of the root commit ([red-team-gate.md](red-team-gate.md)) | `.review/<sha>.md` with the last line `Urteil: JA` | agent (independent reviewer) |
| V10 | Make the empty product repository public, then push as `main` | repository public, `main` equal to the root commit | owner |

## Rules

- V1 starts only after V0 is recorded.
- A NEIN in V9 leads to a fix in the build repository, a new root commit (again exactly one) and a repeat of V3 to V7 and V9 on the new commit.
- The tools of V2 and V7 (export, neutrality check, overlap check, issue scan) live in the operations repository, because the export manifest names private paths (FE-034).
- After V10 the English files in the product repository are the source; the planning documents they came from are frozen.
- Around V10 the owner sets up the product repository: first the empty repository becomes public, because on the Free plan environments and environment secrets exist only in public repositories; then the deny-list environment with its secrets, before the push; private vulnerability reporting, secret scanning with push protection and the ruleset of `main` ([push-discipline.md](push-discipline.md#protection-of-main)) right after it.
