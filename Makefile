# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: The Guildwork Authors
#
# Entry point for local checks and CI. `make check` is the same locally and in
# CI. The list of gates lives only in quality/gates.toml (FE-006); every target
# here has an entry there, checked by `make gates`. `make help` lists them.
#
# Everything is installed inside the repository: binaries in .tools/bin,
# Python in .tools/python and .venv, Node.js packages in node_modules,
# pnpm through Corepack in .tools/corepack, its package store and metadata
# cache in .tools/pnpm-store and .tools/pnpm-cache (pnpm-workspace.yaml).
# Nothing is installed system wide.
# Requirements: git, make, Node.js of .node-version with Corepack, python3 3.11+.

.DEFAULT_GOAL := help

# Interpreter for the standard library scripts (fetch.py, gates.py), which run
# before the Python environment exists.
PYTHON ?= python3
PNPM := corepack pnpm
UV := .tools/bin/uv
VENV_BIN := .venv/bin
VITEST_PROJECTS := --project unit --project integration --project contract
# JUnit reports of the gates with tests, one file per make target; gates.py
# collects them into .reports/junit-<job>.xml for the CI artifact (FE-062).
JUNIT_DIR := .reports/junit
# Commits checked by `make commitlint`: those of the current branch on top of
# the local main. CI passes the commits of the pull request instead.
COMMIT_RANGE ?= main..HEAD

# Keep uv and Corepack inside the repository instead of the user's home.
export UV_CACHE_DIR := $(CURDIR)/.tools/uv-cache
export UV_PYTHON_INSTALL_DIR := $(CURDIR)/.tools/python
export UV_PYTHON_PREFERENCE := only-managed
export COREPACK_HOME := $(CURDIR)/.tools/corepack
export COREPACK_ENABLE_DOWNLOAD_PROMPT := 0

GITLEAKS := .tools/bin/gitleaks
# Commits that `make gitleaks` scans (git log options). Default: the commits
# not yet on origin/main; without that ref (a repository without remote, FE-031)
# the whole history. V4 sets --all.
GITLEAKS_LOG_OPTS ?= $(if $(shell git rev-parse -q --verify refs/remotes/origin/main 2>/dev/null),origin/main..HEAD,--all)

# Deny-list scanner (FE-023). The private list and the allowed identities come
# from the files named by DENYLIST_FILE and ALLOW_AUTHORS_FILE (environment or
# make command line); DENYLIST_FLAGS=--allow-missing runs the generic rules
# alone. PR_TITLE and PR_BODY reach the scanner only through the environment.
DENYLIST_FLAGS ?=
DENYLIST := $(PYTHON) tools/denylist/scan.py $(DENYLIST_FLAGS)

GATES := $(PYTHON) tools/ci/gates.py
RUN_GATES := $(GATES) run --make "$(MAKE) --no-print-directory"

.PHONY: help bootstrap check check-ts check-tools check-security
.PHONY: fmt fmt-check lint typecheck test coverage layers gates
.PHONY: commitlint
.PHONY: gitleaks
.PHONY: licenses notices
.PHONY: denylist denylist-history

help:
	@$(GATES) help

bootstrap:
	$(PYTHON) tools/bootstrap/fetch.py
	$(PNPM) install --frozen-lockfile
	$(UV) sync --frozen
	@if [ -f .pre-commit-config.yaml ]; then \
		$(VENV_BIN)/pre-commit install -t pre-commit -t commit-msg -t pre-push; \
	else \
		echo "bootstrap.hooks_skipped reason=no_pre_commit_config"; \
	fi

check:
	@$(RUN_GATES) --in-check

check-ts:
	@$(RUN_GATES) --job ts --junit .reports/junit-ts.xml

check-tools:
	@$(RUN_GATES) --job tools --junit .reports/junit-tools.xml

check-security:
	@$(RUN_GATES) --job security --junit .reports/junit-security.xml

fmt:
	$(PNPM) exec biome format --write .
	$(VENV_BIN)/ruff format tools

fmt-check:
	$(PNPM) exec biome format .
	$(VENV_BIN)/ruff format --check tools

lint:
	$(PNPM) exec biome lint .
	$(PNPM) exec eslint .
	$(VENV_BIN)/ruff check tools

typecheck:
	$(PNPM) exec tsc -b
	$(VENV_BIN)/mypy tools

# e2e tests are not part of make check (FE-003). The Python tests of the
# repository tools run in test-tools (CI job tools).
test:
	$(PNPM) exec vitest run $(VITEST_PROJECTS) --reporter=default --reporter=junit \
		--outputFile.junit=$(JUNIT_DIR)/$@.xml

coverage:
	$(PNPM) exec vitest run --coverage $(VITEST_PROJECTS)

layers:
	$(PYTHON) tools/ci/check_layers.py

gates:
	$(GATES) check

commitlint:
	$(PYTHON) tools/hooks/commit_msg.py --range="$(COMMIT_RANGE)"

# Findings are masked (--redact) on stdout and in .reports/gitleaks.json.
gitleaks:
	@mkdir -p .reports
	$(GITLEAKS) git --no-banner --redact --verbose --config .gitleaks.toml \
		--report-format json --report-path .reports/gitleaks.json \
		--log-opts "$(GITLEAKS_LOG_OPTS)" .

# Known vulnerabilities in pnpm-lock.yaml and uv.lock. With OSV_BASE=<ref> only
# findings that are new against that ref fail (pull requests); without it every
# finding fails (full scan of main).
.PHONY: osv
osv:
	$(PYTHON) tools/ci/osv_diff.py --base "$(OSV_BASE)"

# Workflow policy from quality/ci/policy.toml (FE-024), then actionlint and
# zizmor on the same files. Both fail without any workflow (measured
# 2026-11-01: actionlint 1.7.12 exits 3 "no project was found", zizmor 1.31.1
# exits 3 "no inputs collected"), so they run only when workflow files exist.
# actionlint runs without its shellcheck and pyflakes integrations: these use
# whatever happens to be installed, which differs between machines and CI.
WORKFLOWS_DIR ?= .github/workflows
WORKFLOW_FILES = $(wildcard $(WORKFLOWS_DIR)/*.yml $(WORKFLOWS_DIR)/*.yaml)

# renovate.json is checked against the Renovate schema that check-jsonschema
# ships (--builtin-schema vendor.renovate, docs/quality/renovate.md); no network.
RENOVATE_CONFIG ?= renovate.json

.PHONY: workflows
workflows:
	$(PYTHON) tools/ci/check_workflows.py --dir $(WORKFLOWS_DIR) --json .reports/workflows.json
	$(VENV_BIN)/check-jsonschema --builtin-schema vendor.renovate $(RENOVATE_CONFIG)
	@if [ -z "$(WORKFLOW_FILES)" ]; then \
		echo "workflows.skipped tools=actionlint,zizmor reason=no_workflow_files"; \
	else \
		echo ".tools/bin/actionlint -shellcheck= -pyflakes= $(WORKFLOW_FILES)"; \
		.tools/bin/actionlint -shellcheck= -pyflakes= $(WORKFLOW_FILES) || exit 1; \
		echo "$(VENV_BIN)/zizmor --offline --no-progress $(WORKFLOW_FILES)"; \
		$(VENV_BIN)/zizmor --offline --no-progress $(WORKFLOW_FILES) || exit 1; \
	fi

# The license gate also checks THIRD_PARTY_NOTICES (third_party_notices.py --check).
licenses:
	$(PYTHON) tools/ci/license_check.py --json .reports/license_check.json

notices:
	$(PYTHON) tools/ci/third_party_notices.py --write

# The tree, the commits of COMMIT_RANGE and, when PR_TITLE is set, the pull
# request title and body. The shell tests PR_TITLE without expanding it. Pass
# PR_TITLE and PR_BODY only through the environment, never on the make command
# line: make would expand the untrusted text as make syntax there.
denylist:
	@modes="tree commits"; if [ -n "$${PR_TITLE+set}" ]; then modes="$$modes pr"; fi; \
	$(DENYLIST) --json .reports/denylist.json --range "$(COMMIT_RANGE)" $$modes

denylist-history:
	$(DENYLIST) --json .reports/denylist-history.json --all history tree

# Own Opengrep rules only (ADR-50), then their rule tests. .semgrepignore keeps
# test directories in the scan; the version check is off, so no network request.
OPENGREP := .tools/bin/opengrep
.PHONY: opengrep
opengrep:
	@mkdir -p .reports
	$(OPENGREP) scan --config .opengrep/rules --error --disable-version-check --quiet --emacs --json-output=.reports/opengrep.json .
	$(PYTHON) tools/ci/opengrep_test.py --opengrep $(OPENGREP)

# ScanCode Toolkit over the committed files of HEAD (as `git archive HEAD`,
# without export attributes), checked against allowed.txt and
# quality/licenses/scancode-exceptions.txt (V6, before a release; not part of
# make check). SCANCODE_RUNNER selects how ScanCode runs; both use the same
# packages from tools/bootstrap/scancode/requirements.txt (exact versions and
# hashes): `container` (CI) runs the image pinned by digest in
# tools/bootstrap/tools.toml through SCANCODE_DOCKER (default docker); `local`
# installs them with uv into .tools/scancode, for machines without a
# container runtime.
SCANCODE_RUNNER ?= container
SCANCODE_ENV := .tools/scancode

.PHONY: scancode
scancode:
	@if [ "$(SCANCODE_RUNNER)" = local ]; then \
		echo "$(UV) pip sync --require-hashes tools/bootstrap/scancode/requirements.txt"; \
		$(UV) venv --quiet --allow-existing --python 3.12 $(SCANCODE_ENV) && \
		$(UV) pip sync --quiet --python $(SCANCODE_ENV)/bin/python --require-hashes \
			--only-binary :all: tools/bootstrap/scancode/requirements.txt || exit 2; \
	fi
	$(PYTHON) tools/ci/scancode_policy.py --runner "$(SCANCODE_RUNNER)" --env $(SCANCODE_ENV) \
		--scan-output .reports/scancode-scan.json --json .reports/scancode_policy.json

# Text rules (FE-022) on every tracked file, configured in quality/text/.
.PHONY: text-rules
text-rules:
	$(PYTHON) tools/hooks/text_rules.py --json .reports/text-rules.json

# Relative links and anchors of the tracked Markdown files.
.PHONY: links
links:
	$(PYTHON) tools/hooks/links.py --json .reports/links.json

# Work plan and component catalog (FE-037): plan.py check validates
# docs/plan/tasks and docs/design/components and fails when docs/plan/overview.md
# or docs/design/build-book.md differs from what `plan.py generate` writes.
# Without docs/plan/tasks it prints plan.skipped and passes.
.PHONY: plan
plan:
	$(PYTHON) tools/plan/plan.py check

# Python tests of the repository tools: unittest discovery under tools/.
.PHONY: test-tools
test-tools:
	$(VENV_BIN)/python tools/ci/junit_unittest.py --start-dir tools --top-level-dir . \
		--output $(JUNIT_DIR)/$@.xml

# Step R4 before the first push (FE-031), not part of make check: ci_ok.py
# against its fixtures, check_workflows.py --strict, then every job of every
# workflow in a fresh clone of HEAD with the env the job sets, without a git
# identity like a fresh runner (tools/ci/workflows_dry_run.py). Needs network
# (bootstrap, osv-scanner, ScanCode). Step logs in .reports/workflows-dry-run/.
# DRY_RUN_FLAGS passes options, such as --only ci.yml:denylist --keep.
.PHONY: workflows-dry-run
workflows-dry-run:
	$(PYTHON) tools/ci/workflows_dry_run.py --json .reports/workflows-dry-run.json $(DRY_RUN_FLAGS)
