<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->

# Push discipline

How a change travels from a branch to `main`, and which check runs at which step. The rules come from section 4.1 of the detailed design 00 (rulings FE-020, FE-021, FE-040 and FE-041) and section 5.1 of architecture 12.

## Flow

1. **Branch.** `<type>/<topic>`, for a plan task `<type>/<task id>-<topic>` (for example `feat/0-e01-t04-logger`). One writer per branch.
2. **Commits.** Conventional Commits with DCO sign-off (`git commit -s`), `Co-Authored-By:` for an agent, `Plan-Task: <id>` for a plan task; details in [CONTRIBUTING.md](../../CONTRIBUTING.md#commits). Tests come first: the failing test is its own commit before the code.
3. **Local checks.** `make check` runs the same gates as CI ([gates.md](gates.md)). A red CI run after a green `make check` is a defect of the toolchain and is fixed there, not worked around in the change.
4. **Red team review.** An independent, read-only reviewer reads the diff against `main` and writes `.review/<sha>.md` ([red-team-gate.md](red-team-gate.md)).
5. **Push.** The `pre-push` hook requires the report with the verdict `Urteil: JA` and a green `make check`.
6. **Pull request.** One per change or plan task. The title is a Conventional Commit subject and becomes the squash commit subject; the body follows `.github/PULL_REQUEST_TEMPLATE.md`, including the evidence for each done criterion and the docs and follow-up list. The review section names the reviewed commit, the verdict and the corrections in own words, never the raw report.
7. **Merge.** Squash only, after the required check `ci-ok` is green.

## Git hooks

`make bootstrap` installs the hooks of `.pre-commit-config.yaml` for the hook types `pre-commit`, `commit-msg` and `pre-push`. All hooks are local and run tools that the bootstrap pinned; pre-commit downloads nothing. pre-commit writes the hooks into the git directory that all worktrees of a clone share, so they apply to every worktree.

| Hook type | Hooks | Input |
|---|---|---|
| `pre-commit` | text rules (`tools/hooks/text_rules.py`); file hygiene (merge conflict markers, files above the size limit set in the hook, file names that differ only in case, TOML and YAML parse, final newline, trailing whitespace, LF line endings); `gitleaks git --staged` with `.gitleaks.toml`; `biome check` on changed TypeScript, JavaScript and JSON files | the staged files (pre-commit stashes unstaged changes while it runs) |
| `commit-msg` | `tools/hooks/commit_msg.py`: Conventional Commits, sign-off equal to the author, `Plan-Task:` form, no dash characters | the message file |
| `pre-push` | `tools/hooks/review_gate.py`, then `make check` | the report of `HEAD`; `make check` runs on the working tree |

The fixers among the hygiene hooks change the file and fail; stage the result and commit again. Verbatim license texts (`LICENSE`, `LICENSES/`) are never rewritten. `pre-commit run --all-files` runs the `pre-commit` hooks over the whole tree.

`git commit --no-verify` and `git push --no-verify` skip the hooks. Do not use them: CI runs the same gates, and a skipped review has no evidence for the pull request.

## Before a push

The `pre-push` hook runs the full `make check`, not a selection of affected parts (FE-040): it is simple and equal to CI, and a partial plan only pays off when `make check` takes long.

The review gate checks the report of `HEAD`, and `make check` runs on the working tree (pre-commit stashes only unstaged changes). Push from a clean working tree with the pushed commit checked out. When pre-commit knows the pushed commit and it is not `HEAD`, the gate fails; on a first push to a remote without any of its refs, pre-commit does not pass the pushed commit, and only the report of `HEAD` is checked. pre-commit runs the `pre-push` hooks for the first pushed ref only, so push one branch at a time.

**Deny-list scan without the private list.** `make check` includes the deny-list scan (`make denylist`), which needs the private list and the allowed identities (`DENYLIST_FILE`, `ALLOW_AUTHORS_FILE`) that only maintainers have. Without them the scan ends with exit 2 and the push is refused; the hook then prints a hint. Running the scan with the generic rules only is an explicit choice through the environment:

```sh
DENYLIST_FLAGS=--allow-missing git push
```

Reason: a branch pushed to the public repository is public at once, so the hook is the last check before private data would leave the machine. Falling back to the generic rules on its own would let a maintainer who forgot to set the variables push a private term unnoticed. With the explicit choice the reduced scan is always intended. CI decides independently of the local hook: pull requests from the repository run the full scan with the list from the protected environment, pull requests from forks the generic rules; the maintainer's run after merging scans in full (architecture 12 section 4.3).

## Fork contributors

Forks have neither the private deny list nor a red team reviewer:

```sh
make check DENYLIST_FLAGS=--allow-missing
DENYLIST_FLAGS=--allow-missing REVIEW_SKIP=1 git push
```

`REVIEW_SKIP=1` (exactly `1`) skips the review gate and says so; a maintainer reviews the pull request instead.

## Pull requests and CI

- The pull request title and body pass the deny-list scan in CI. They reach the scanner only through the environment variables `PR_TITLE` and `PR_BODY`, never as command line text.
- Pull requests from bots run like pull requests from forks. A commit without sign-off is accepted only from an author address listed exactly in `quality/commits/bots.txt`.
- Each pull request workflow cancels its superseded runs (`concurrency` with `cancel-in-progress`) and has at most `max_jobs_per_run` jobs (`quality/ci/policy.toml`, checked by `make workflows`). Only GitHub-hosted standard runners with fixed labels are allowed.

## Queue time and concurrency

At most 2 concurrent pull request runs is a starting value that is measured, not enforced (FE-025, architecture 12 section 5.1): a concurrency group holds only one waiting run, so a global group would discard runs of other pull requests. `tools/ci/measure_queue.py` reads the runs of a period and their jobs through the Actions API with GET requests only and writes `.reports/queue-runs.csv`, `.reports/queue-jobs.csv` and a summary (median and maximum of the queue time, highest number of concurrent pull request runs and jobs). The definitions of the columns are in its docstring.

```sh
GITHUB_TOKEN=<read-only token> python3 tools/ci/measure_queue.py \
  --repo <owner/name> --since <YYYY-MM-DD> --until <YYYY-MM-DD>
```

| Period | Runs | Queue time of runs (median, max) | Queue time of jobs (median, max) | Concurrent PR runs (max) | Concurrent PR jobs (max) |
|---|---|---|---|---|---|
| first measurement over the trial pull requests: pending until they ran (R-E05-T09) | | | | | |

The measured values are compared with the starting values of architecture 12 section 5.1 (2 concurrent runs, at most 6 jobs per run). The summary counts every workflow run of a pull request event; a pull request starts one run of `ci.yml` and one of `codeql.yml`, so for the comparison count the runs per workflow from `queue-runs.csv`.

## Protection of `main`

The ruleset of `main` requires a pull request, allows squash merges only, requires the status check `ci-ok`, a linear history and signed commits, and forbids force pushes and deletion. `ci-ok` is the only required check; it summarizes every CI job, so new jobs and path filters never change the ruleset.

## Before the first push

Until the repository becomes public, there is no remote (FE-031): every task is a branch of a local build repository, reviewed and merged into its `main` locally. The `pre-commit` and `commit-msg` hooks apply there in the same way; the `pre-push` hook does not run without a push, so the red team report and `make check` before each local merge are part of the merge step, not of a hook. The first push is the single root commit of the release checklist ([public-switch.md](public-switch.md), V10).

The workflows never run before that push. In their place, `make workflows workflows-dry-run` runs once in a fresh clone (step R4): the policy, actionlint, zizmor and the Renovate schema, then `ci_ok.py` against its fixtures, `check_workflows.py --strict` and every job of every workflow (`tools/ci/workflows_dry_run.py`). Each job runs in its own fresh clone made like `actions/checkout` makes it, with the `env:` the job sets and invented event values, and without a git identity, like a fresh GitHub-hosted runner. Steps with `uses:` other than checkout, setup-node, cache and upload-artifact do not run locally (CodeQL, Scorecard); without a container runtime the ScanCode job runs `make scancode SCANCODE_RUNNER=local` instead and says so.

## Deny list in CI

The deny-list scanner (`tools/denylist/scan.py`, gate `denylist` in `quality/gates.toml`) checks the tree, the commits and the pull request title and body for private terms and instance data. The private list never enters the repository: CI reads it from the secrets of the GitHub environment `denylist`.

| Workflow and job | Runs for | Private list | Command |
|---|---|---|---|
| `ci.yml` `denylist` | pull requests from this repository whose author is not a bot, pushes to `main`, manual runs | yes, environment `denylist` | `make denylist COMMIT_RANGE=<range>` |
| `ci.yml` `denylist-fork` | pull requests from forks and from bots (`user.type` `Bot`, such as Renovate or Dependabot) | no; no environment, no secrets | `make denylist DENYLIST_FLAGS=--allow-missing COMMIT_RANGE=<range>` |
| `denylist-main.yml` `scan` | every push to `main` | yes, environment `denylist` | `make denylist COMMIT_RANGE=<before>..<after>`; on the first push of `main` (`before` all zeros) `make denylist-history` over the whole history |

The two jobs of `ci.yml` have complementary conditions, so exactly one of them runs and `ci-ok` decides with both (`tools/ci/ci_ok.py`). `tools/ci/commit_range.py` prints the range: the commits of the pull request (`<base>..<head>`) or of the push, since a CI clone has no local `main`. Both jobs check out the full history (`fetch-depth: 0`).

Handling of the private data:

- The secrets `DENYLIST` and `ALLOW_AUTHORS` are set as `env` of one step only, which writes them with `umask 077` to `$RUNNER_TEMP/denylist/list` and `$RUNNER_TEMP/denylist/authors` (mode `0600`, directory `0700`). The scan step gets the paths in `DENYLIST_FILE` and `ALLOW_AUTHORS_FILE`, never the values and never an argument.
- An empty or missing secret stops the job with `denylist.secret_missing` before the scan; it never falls back to the generic rules.
- `PR_TITLE` and `PR_BODY` reach the scan only through `env`. A push or manual run unsets them, so the mode `pr` runs only for pull requests.
- The deny jobs run `make` with the system `python3` only. The scanner uses the standard library, so these jobs restore no cache and install no dependencies: no third-party code runs next to the secrets.
- Findings name a hash and a location, never the term (FE-023), because CI logs of a public repository are public.

### Setting up the environment `denylist`

- Secret `DENYLIST`: the private list, one entry per line (format in `tools/denylist/scan.py`).
- Secret `ALLOW_AUTHORS`: the allowed identities, one `Name <mail>` per line. Author and committer of every scanned commit must equal one line, otherwise the scan reports `identity-not-allowed`. Besides the identity of the maintainer it needs the committer identity that GitHub writes when a pull request is merged in the web interface (squash or merge commit, measured below):

```text
GitHub <noreply@github.com>
```

- A squash merge keeps a person as author. A merged pull request of another contributor or of a bot therefore fails the scans of the push to `main` with `identity-not-allowed` until that identity is a line of `ALLOW_AUTHORS`.
- Deployment branches and tags: no restriction. With a branch rule, the runs of pull requests (ref `refs/pull/<number>/merge`) would need their own rule, see the evidence below.
- No required reviewers: they would hold every pull request run until someone approves it.

Remaining risk: a person with write access can change `ci.yml` on a branch of this repository and read the secrets in a pull request run, since the environment has no branch rule. Only the maintainers have write access; forks never get the secrets.

### Evidence from the GitHub documentation

Retrieved on 2026-11-01.

| Question | Answer | Source and wording |
|---|---|---|
| Are environment secrets withheld from pull requests from forks? | Yes. The rule covers every secret except `GITHUB_TOKEN`, environment secrets included; the environment pages themselves say nothing about forks. Dependabot runs count as fork runs. | [Using secrets in GitHub Actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets): "With the exception of `GITHUB_TOKEN`, secrets are not passed to the runner when a workflow is triggered from a forked repository." [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows), `pull_request`: the same sentence, and "Workflows triggered by Dependabot pull requests are treated as though they are from a forked repository". |
| Can pull request runs from this repository use an environment without a branch rule? | Yes, by the documented option; not yet seen in a run of this repository (to confirm with the first pull request). | [Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments), "Deployment branches and tags": "No restriction on which branch or tag can deploy to the environment." For "Selected branches and tags" a rule for `refs/pull/*/merge` "would also allow workflows triggered by `pull_request` events to deploy to the environment". "Protected branches only" lets every branch deploy only "If no branch protection rules are defined for any branch in the repository". Secrets of an environment "are only available to workflow jobs that reference the environment", after required reviewers approve. |
| Which committer identity do merges in the web interface have? | `GitHub` with the address in the block above (account `web-flow`), for squash merges and merge commits. The documentation does not name it; measured instead. | [About commit signature verification](https://docs.github.com/en/authentication/managing-commit-signature-verification/about-commit-signature-verification) says only that GitHub signs commits made in the web interface, with the key at `https://github.com/web-flow.gpg`; [About merge methods](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github) says that rebase and merge "Always updates the committer information". Measured with `GET /repos/actions/checkout/commits` and `GET /repos/actions/cache/commits` (public REST API, no token): squash merges such as `3d3c42e5aac5` (`prep v7.0.1 release (#2531)`) and merge commits such as `55cc8345863c` (`Merge pull request #1768 ...`) have committer name `GitHub`, login `web-flow`; the author stays the person. |
