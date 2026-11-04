<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->

# Contributing to Guildwork

Thank you for your interest. This file describes how to set up the repository, what a change must contain and how it gets merged. Decision making is described in [GOVERNANCE.md](GOVERNANCE.md), help channels in [SUPPORT.md](SUPPORT.md).

## Before you start

- Bugs and feature requests: open an issue with one of the issue forms. New issues get the label `status: triage` until a maintainer has looked at them.
- Questions: use GitHub Discussions, not issues.
- Security problems: never in a public issue; follow [SECURITY.md](SECURITY.md).
- Larger changes (a new plugin kind, a new service, a change to an interface or to the governance): open an issue or a discussion first, and expect an ADR (see [GOVERNANCE.md](GOVERNANCE.md)).

## Setup

```sh
make bootstrap
```

`make bootstrap` installs everything the checks need: pinned tool binaries with verified SHA-256 checksums into `.tools/bin/`, the Node.js dependencies with the frozen lockfile, the Python environment of the repository tools, and the git hooks (`pre-commit`, `commit-msg`, `pre-push`). It never uses `sudo`. You need `git`, `make`, Node.js with Corepack, and Python 3.11 or later to run the bootstrap script `tools/bootstrap/fetch.py`; `uv` is one of the pinned binaries it fetches (`tools/bootstrap/tools.toml`). The expected versions are pinned in the repository (`.node-version`, `.python-version`, `package.json`, `tools/bootstrap/tools.toml`).

## Checks

```sh
make check
```

`make check` runs the same gates as CI; a change that is green locally must be green in CI. The list of gates lives in `quality/gates.toml`, and `make help` prints every target with a one-line description. The only required status check on pull requests is `ci-ok`, which summarizes all CI jobs.

Before a push, the `pre-push` hook requires a red team report for the commit and a green `make check`. The flow from branch to merge, the hooks and the review are described in [docs/quality/](docs/quality/README.md).

## New packages

Create a workspace package only with the generator, then link it:

```sh
corepack pnpm new:package <location>/<name>
corepack pnpm install
```

The generator writes the package layout with SPDX headers, adds it to the root `tsconfig.json` and, if no entry covers it yet, to `quality/layers.toml`. That file holds the allowed dependencies between workspace packages; `make layers` checks every `package.json` and import against it and fails for a package without entry.

## Commits

- **DCO sign-off is required on every commit.** Use `git commit -s`. The sign-off certifies the [Developer Certificate of Origin 1.1](https://developercertificate.org/) for the whole commit. The `commit-msg` hook and CI both reject commits without a sign-off that matches the author.
- **Conventional Commits.** The subject is `<type>(<optional scope>): <summary>`, in English, imperative mood, no trailing period. Allowed types: `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `chore`, `perf`, `revert`. A scope, if used, names a package or area such as `core`, `config`, `tools`, `ci` or `plan`. The maximum subject length is a named value in `quality/commits/limits.toml`.
- **Agents.** A commit written by an AI agent carries a `Co-Authored-By:` trailer for the agent. The sign-off is given by the responsible human.
- **Plan tasks.** A commit or pull request for a task of the project plan carries the trailer `Plan-Task: <task id>`.
- **Check.** `make commitlint` runs `tools/hooks/commit_msg.py` over the commits of `COMMIT_RANGE` (default `main..HEAD`), merge commits included; the `commit-msg` hook checks each new message the same way. Both also reject the dash characters named under "Text rules". Only authors whose address is listed exactly in `quality/commits/bots.txt` may commit without a sign-off.
- Branch names follow `<type>/<topic>`, or `<type>/<task id>-<topic>` for a plan task.

## Pull requests

- One pull request per change or plan task. The title is a Conventional Commit subject; it becomes the squash commit subject.
- Fill in every section of the pull request template, including the evidence for each done criterion and the docs and follow-up list.
- Pull requests are merged by squash only, with linear history and signed commits.
- Files under `tools/`, `quality/`, `.github/` and the license files need approval from a code owner (see `.github/CODEOWNERS`).

## Documentation belongs to the change

A change is complete only when every place that names a changed fact is updated in the same pull request: code, tests, docs, ADRs, templates and examples. List those places in the "Docs and follow-up list" section of the pull request, each one updated or left unchanged with a reason.

## Text rules

- Everything in the repository is written in English. The `text-rules` gate reports German text in the public documentation (`quality/text/english-only.toml`; `docs/research/` stays untranslated) and superseded terms (`quality/text/glossary.toml`).
- No dashes used as punctuation: do not write the en dash (U+2013) or the em dash (U+2014), nor the other dash characters U+2012 and U+2015. Use a hyphen, a comma, a colon, parentheses or a new sentence instead. The `text-rules` gate enforces this.
- Links in Markdown are relative and point to tracked files and existing headings; the `links` gate checks them. A file is exempt from the text rules only through `quality/text/exempt-paths.txt` (verbatim texts such as `LICENSES/**`), a single English-only line only through `quality/text/english-exceptions.toml`.
- No data of a concrete installation (names of companies, people, hosts, accounts, local paths, internal network ranges). Use placeholders such as `example-org`, `example.org` and the documentation address ranges.
- Every hand-written file starts with an SPDX header, as a comment in the file's own syntax:

  ```text
  SPDX-License-Identifier: Apache-2.0
  SPDX-FileCopyrightText: The Guildwork Authors
  ```

  Code or prompts taken over from elsewhere keep the SPDX header of their source and add an `Origin:` line (`<owner>/<repo>@<commit>:<path>, modified`) within the first five lines. Only licenses on the project's allowlist (`quality/licenses/allowed.txt`) may be taken over; the one other case, the code of conduct, is listed with its reason in `quality/licenses/header.toml`. `make licenses` checks the headers, the dependency licenses and `THIRD_PARTY_NOTICES`; after a dependency change run `make notices` and commit the result.

## Contributing from a fork

Two gates need data that forks do not have: the private deny list of the maintainers and the local red team review evidence. Fork contributors switch them off:

```sh
make check DENYLIST_FLAGS=--allow-missing
DENYLIST_FLAGS=--allow-missing REVIEW_SKIP=1 git push
```

With `DENYLIST_FLAGS=--allow-missing` the deny-list scan runs with the generic rules only; every `make check` without the private list needs it, including the one in the `pre-push` hook, which never chooses the reduced scan on its own. With `REVIEW_SKIP=1` the `pre-push` hook skips the check for a red team report; a maintainer reviews the pull request instead. CI runs the reduced checks for pull requests from forks on its own. Details: [docs/quality/push-discipline.md](docs/quality/push-discipline.md).

## License of contributions

Contributions are accepted under the [Apache License 2.0](LICENSE), as stated in its section 5. There is no contributor license agreement.
