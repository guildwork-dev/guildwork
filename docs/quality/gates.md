<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->

# Quality gates

Generated from `quality/gates.toml` by `python3 tools/ci/gates.py doc --write`; do not edit by hand. `make check` builds every gate marked yes in the column `make check`, in this order, and stops at the first failure. The group targets `check-ts`, `check-tools` and `check-security` build the gates of `make check` that run in that CI job. Fork PR: `same` runs unchanged for pull requests from forks, `generic` runs with the generic rules only, `skip` does not run.

## Gates

| Gate | Make target | CI job | `make check` | Fork PR | Tool | Description |
|---|---|---|---|---|---|---|
| `fmt` | `make fmt` | none | no | skip | biome format --write, ruff format | Format TypeScript, JSON and the Python tools in place |
| `fmt-check` | `make fmt-check` | ts | yes | same | biome format, ruff format --check | Check formatting without writing |
| `lint` | `make lint` | ts | yes | same | biome lint, eslint, ruff check | Lint TypeScript (Biome, type-aware ESLint rules) and the Python tools |
| `typecheck` | `make typecheck` | ts | yes | same | tsc -b, mypy | Type check TypeScript project references and the Python tools |
| `test` | `make test` | ts | yes | same | vitest (unit, integration, contract) with a JUnit report | Run the unit, integration and contract tests of the TypeScript packages; no e2e |
| `coverage` | `make coverage` | ts | yes | same | vitest --coverage | Run the TypeScript tests with the thresholds of quality/coverage.json |
| `layers` | `make layers` | ts | yes | same | tools/ci/check_layers.py | Workspace dependency rules from quality/layers.toml |
| `gates` | `make gates` | tools | yes | same | tools/ci/gates.py | Check the Makefile and docs/quality/gates.md against quality/gates.toml |
| `commitlint` | `make commitlint` | tools | yes | same | tools/hooks/commit_msg.py | Check the commits of COMMIT_RANGE (default main..HEAD): Conventional Commits, DCO sign-off, Plan-Task |
| `gitleaks` | `make gitleaks` | security | yes | same | gitleaks git with .gitleaks.toml | Scan the commits of GITLEAKS_LOG_OPTS for secrets (default rules plus Anthropic credentials) |
| `osv` | `make osv` | security | yes | same | osv-scanner, tools/ci/osv_diff.py | Known vulnerabilities in the lockfiles; with OSV_BASE only new findings fail |
| `workflows` | `make workflows` | tools | yes | same | tools/ci/check_workflows.py, check-jsonschema (renovate.json), actionlint, zizmor --offline | Workflow policy from quality/ci/policy.toml, the Renovate schema on renovate.json, then actionlint and zizmor |
| `licenses` | `make licenses` | security | yes | same | tools/ci/license_check.py, tools/ci/third_party_notices.py --check | License file, SPDX headers, dependency licenses, LICENSES texts, ADR-39 lockfile test, notices |
| `notices` | `make notices` | none | no | skip | tools/ci/third_party_notices.py --write | Regenerate THIRD_PARTY_NOTICES from the lockfiles and adopted files |
| `denylist` | `make denylist` | denylist | yes | generic | tools/denylist/scan.py tree commits, and pr when PR_TITLE is set | Scan the tree, the commits of COMMIT_RANGE and PR_TITLE and PR_BODY for private terms and instance data; needs DENYLIST_FILE and ALLOW_AUTHORS_FILE or DENYLIST_FLAGS=--allow-missing |
| `denylist-history` | `make denylist-history` | none | no | skip | tools/denylist/scan.py history tree | Scan every commit, object and ref name of the history and the tree for private terms and instance data |
| `opengrep` | `make opengrep` | tools | yes | same | opengrep scan, tools/ci/opengrep_test.py | Scan with the own Opengrep rules, then run their rule tests |
| `scancode` | `make scancode` | none | no | skip | ScanCode Toolkit over the files of HEAD, tools/ci/scancode_policy.py | License scan of the committed tree (V6, before a release); SCANCODE_RUNNER=container or local |
| `text-rules` | `make text-rules` | tools | yes | same | tools/hooks/text_rules.py | Text rules on every tracked file: no dashes, English docs, glossary, instance data |
| `links` | `make links` | tools | yes | same | tools/hooks/links.py | Relative links and anchors of the tracked Markdown files; no links to private paths |
| `plan` | `make plan` | tools | yes | same | tools/plan/plan.py check | Check the work plan and the component catalog; overview and build book must be up to date |
| `test-tools` | `make test-tools` | tools | yes | same | tools/ci/junit_unittest.py (unittest discovery under tools/) | Run the Python tests of the repository tools with a JUnit report |

## Other targets

| Target | Description |
|---|---|
| `make help` | List every make target with its description |
| `make bootstrap` | Install pinned binaries, Node.js and Python dependencies and git hooks |
| `make check` | Run every gate of make check in order; stop at the first failure |
| `make check-ts` | Run the gates of make check that belong to the CI job ts |
| `make check-tools` | Run the gates of make check that belong to the CI job tools |
| `make check-security` | Run the gates of make check that belong to the CI job security |
| `make workflows-dry-run` | Step R4: ci_ok.py fixtures, check_workflows.py --strict and every workflow job in a fresh clone with its job env |
