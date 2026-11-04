<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->

# Red team gate

Every change is reviewed by an independent reviewer before it is pushed or merged into `main` locally. The `pre-push` hook enforces that a report with a positive verdict exists for the checked-out commit `HEAD` (architecture 12 section 5.1, detailed design 00 rulings FE-040 and FE-041).

## When

- Before every push and before every local merge into `main`: over the diff of the branch against `main`.
- At the end of each epic: over the whole epic.
- Before the repository becomes public: over the whole tree of the root commit (release checklist V9, [public-switch.md](public-switch.md)).

## Who

The reviewer is independent of the author: a fresh AI session that did not write the change, or a second person. The reviewer only reads (repository, diff, tests and their output; running the checks in a scratch copy is fine), changes nothing in the reviewed repository and gets no secrets.

## Report

The report is `.review/<sha>.md` in the repository root, where `<sha>` is the full SHA of the reviewed commit. `.review/` is git-ignored: the report stays local and never becomes part of the history.

The report:

1. lists the goals and done criteria of the change, each with its status (met and proven, not met, not proven);
2. lists the findings, each with file and line, a severity (blocker, major, minor) and the evidence;
3. ends with the verdict as its last non-empty line, exactly one of

   ```text
   Urteil: JA
   Urteil: NEIN <reason>
   ```

The verdict line stays German in this English repository (FE-041): reviewers produce exactly this line, and the hook compares it byte for byte. `Verdict: YES` or any other wording fails.

**When the verdict is NEIN.** The verdict is NEIN for a blocker (does not work, data loss, security hole, red CI), for a reproduced major (wrong behavior with effect on users or operation), or for a goal of the change that is not met or not proven. Minor findings (wording, layout, hypothetical edge cases, missing tests without a known defect) do not make the verdict NEIN; they go to the backlog of minor findings and are handled by the next change in the same area.

After a NEIN the author fixes the finding with a test, and a review of the changed lines follows. At most two fix rounds: if the same NEIN comes twice, the project owner decides how to go on instead of another round.

**In the pull request** the review section names the reviewed commit, the verdict and the corrections in own words. The raw report is never copied into the pull request, because the pull request text becomes the squash commit message.

## The hook

`tools/hooks/review_gate.py` runs in the `pre-push` hook:

| Case | Result |
|---|---|
| `.review/<HEAD sha>.md` exists and its last non-empty line is exactly `Urteil: JA` (LF or CRLF line endings) | pass |
| no report for `HEAD` (a report for an older commit does not count) | `review-missing`, push refused |
| last non-empty line differs in any way (verdict NEIN, other case, extra spaces, a remark after JA, translated verdict, empty report) | `review-verdict`, push refused |
| pre-commit passes the pushed commit and it is not `HEAD` | `review-not-head`, push refused |
| `REVIEW_SKIP=1` (exactly `1`) | pass with the line `review_gate.skipped`; for fork contributors, a maintainer reviews the pull request |

A new commit needs a new report, since the report name is the commit SHA.

## Checklist

The reviewer goes through every point that the change touches. A point that does not apply is skipped, not marked as passed.

### Every change

- The change does what its task or issue asks, and nothing it rules out.
- Tests describe the wanted behavior and came first; a bug fix has a test that failed before the fix.
- Every done criterion has evidence (command and output, or test name and result).
- Error paths: for every failure and early exit it is clear what is stored, audited and logged, and a test checks it.
- Every place that names a changed fact is updated, or left with a reason (docs and follow-up list).
- `make check` is green; no gate was weakened or skipped to get there.
- No data of a concrete installation (company, people, hosts, accounts, local paths, internal networks), no dash characters, SPDX header in every hand-written file, new dependencies only with an allowed license ([licenses.md](licenses.md)).

### Security rules of the platform

These rules come from architecture 05 (security). A change that touches effects, credentials, the sandbox or the policy is checked against each of them.

1. **The Effect Gateway is the only place that writes.** Every write to a source host, ticket system or other outside system goes through the Effect Gateway. Only `apps/control-plane/src/effects/executors/**` imports the write subpath of a plugin (`@guildwork/plugin-*/write`) or calls a plugin write method; the Opengrep rules `gw-scm-write-only-in-effect-gateway` and `gw-plugin-write-only-in-executors` check the static part. The agent has no write credential; it only expresses write wishes through `propose_*` tools of the platform MCP. No service can ask for a merge; a merge happens only through the merge gate at the reviewed SHA.
2. **No credential in the sandbox.** The sandbox holds no long-lived secret; setup secrets are removed before the agent phase. Of the model credential the sandbox sees only a placeholder per work item, and the credential relay outside the sandbox inserts the real one. The control plane and the sandbox side never read `ANTHROPIC_*` or `CLAUDE_*` variables (Opengrep rule `gw-no-model-credential-env`). The exceptions of architecture 05 (the operator's subscription token only for services without shell and without file writes; short-lived cloud federation credentials until the relay contract test) apply only with their conditions. Secrets never appear in logs, and redaction runs before every effect, every blob store write and the telemetry collector.
3. **The command covers the effect.** The allowed effects follow from the triggering command and the pipeline stage. Authorization never comes from tool output or model text: a review job cannot cause a push, whatever the model proposes. Every effect type is mapped to its permission profile, and no profile is wider than its effect needs.

Related points to check in the same changes:

- Input from outside (tickets, pull request texts, code, comments, CI logs) enters prompts only as `Untrusted<T>` and never reaches a logger (Opengrep rule `gw-no-untrusted-in-log`).
- Agent instruction files (`CLAUDE.md`, `AGENTS.md`, `REVIEW.md`) and analyzer configuration are read from the base SHA, never from the head of a pull request.
- Workflows follow the workflow policy (`make workflows`): pinned actions, minimal permissions, no `pull_request_target`, no expressions in `run:`.
