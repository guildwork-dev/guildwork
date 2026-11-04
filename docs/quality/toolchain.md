<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->

# TypeScript toolchain

This file records the pinned TypeScript toolchain, where each setting lives and the measurements behind the rulings FE-001 and FE-002 of the detailed design. The section "Licenses" records the license of every tool and planned library, read at the source.

## Pinned versions

Every version is exact; `pnpm-lock.yaml` is committed and `pnpm install --frozen-lockfile` must not change it.

| Tool | Version | Pinned in |
|---|---|---|
| Node.js | 22.23.4 | `.node-version`, `engines.node` in `package.json` |
| pnpm | 12.16.1 | `packageManager` in `package.json`, run through Corepack |
| TypeScript | 6.0.3 | `devDependencies` |
| Biome | 2.6.4 | `devDependencies` |
| ESLint | 10.14.0 | `devDependencies` |
| typescript-eslint | 8.72.1 | `devDependencies` |
| Vitest, `@vitest/coverage-v8` | 5.0.5 | `devDependencies` |
| Vite | 8.3.5 | `devDependencies` (peer dependency of Vitest, imported by `vitest.config.ts`) |
| `@types/node` | 22.20.5 | `devDependencies` (latest release for Node.js 22) |

Version choices:

- TypeScript stays on 6.0. The current release line 7.0 is outside the peer range of typescript-eslint 8.72.1 (`typescript: >=4.8.4 <6.1.0`, read with `npm view typescript-eslint@8.72.1 peerDependencies` on 2026-11-01), and `strictPeerDependencies` rejects it.
- `engines.node` is exact, so `engineStrict` rejects any other Node.js release. Measured on 2026-11-01 with Node.js 22.23.1: `pnpm install --frozen-lockfile` exits 1 with `ERR_PNPM_UNSUPPORTED_ENGINE ... wanted: {"node":"22.23.4"} (current: {"node":"22.23.1"})`.

## Where the pnpm settings live

pnpm 12 reads install settings only from `pnpm-workspace.yaml`; `.npmrc` is read for registry and authentication only. Measured on 2026-11-01 with pnpm 12.16.1 in a scratch project:

```text
$ printf 'engine-strict=true\n...' > .npmrc && pnpm config get engineStrict
undefined
$ printf 'engineStrict: true\n...' >> pnpm-workspace.yaml && pnpm config get engineStrict
true
$ printf 'registry=https://registry.example.invalid/\n' > .npmrc && pnpm config get registry
https://registry.example.invalid/
```

So `engineStrict`, `saveExact`, `strictPeerDependencies` and `linkWorkspacePackages` are set in `pnpm-workspace.yaml`, and `.npmrc` pins only the registry.

**Install scripts of dependencies.** pnpm 12 names the allowlist `allowBuilds` (a map of package name to `true` or `false`) in `pnpm-workspace.yaml`; the older `onlyBuiltDependencies` list in `package.json` does not apply. The list is empty: the current dependency tree installs without any build script. Every entry added later needs a row here:

| Package | Reason |
|---|---|
| (none) | |

## Formatter and linter split

Biome formats and lints TypeScript, JavaScript and JSON files (`files.includes` in `biome.json`). Biome 2.6.4 also formats Markdown and YAML; those are left out because its Markdown formatter rewrites texts that must stay verbatim (for example the numbered lists of `CODE_OF_CONDUCT.md`). Text rules for Markdown come from the `text-rules` and `links` gates.

Biome rule names were checked against the configuration schema of the pinned version (`node_modules/@biomejs/biome/configuration_schema.json`): `suspicious/noExplicitAny`, `suspicious/noConsole`, `style/noDefaultExport`, `style/noNonNullAssertion`, `style/useImportType`, `style/noParameterAssign`. The field `linter.rules.recommended` is deprecated in 2.6.4; the configuration uses `linter.rules.preset: "recommended"`.

ESLint runs only the five type-aware rules of FE-002 (`eslint.config.js`). It uses the typescript-eslint project service, so every linted TypeScript file must belong to a `tsconfig.json`; a file outside every project is a parse error, not a weaker check.

## Measurement (a): `customConditions` with `NodeNext`

Question: does a workspace package resolve to its sources through the condition `@guildwork/source` without a build (FE-001)?

Result on 2026-11-01: **yes**, for both TypeScript and Vitest. The fallback of FE-001 (build before tests) is not needed.

TypeScript 6.0.3:

```text
$ pnpm exec tsc -p packages/core --traceResolution --noEmit
======== Resolving module '@guildwork/core' from '<repo>/packages/core/src/index.test.ts'. ========
Explicitly specified module resolution kind: 'NodeNext'.
Resolving in ESM mode with conditions 'import', 'types', 'node', '@guildwork/source'.
...
======== Module name '@guildwork/core' was successfully resolved to '<repo>/packages/core/src/index.ts' with Package ID '@guildwork/core/src/index.ts@0.0.0'. ========
```

Vitest 5.0.5: the test `core/index > imports workspace source without build` imports the package by name and by relative path and expects the same module instance. Evidence:

- Without `packages/core/dist/` (after removing it, before any `tsc -b`): `pnpm exec vitest run --project unit` passes, 5 tests.
- With `dist/` present and the condition removed from `vitest.config.ts`, the test fails: `AssertionError: expected { VERSION: '0.0.0', ...(1) } to be { VERSION: '0.0.0', ...(1) } // Object.is equality`. The test therefore tells source from build output.
- Vitest runs tests in Vite's server environment. The condition must be in `ssr.resolve.conditions`; with only `resolve.conditions` the test fails, with only `ssr.resolve.conditions` it passes. The list replaces Vite's defaults, so `vitest.config.ts` appends `defaultServerConditions` from Vite.

## Measurement (b): does Biome find floating promises?

Question: does Biome find floating promises as well as ESLint, so that ESLint could be dropped (FE-002)?

Result on 2026-11-01: **no**. ESLint stays.

The fixture `tools/fixtures/floating-promise.ts` has two floating promises: line 17 calls a local async function, line 19 calls `readFile` from `node:fs/promises` (a typed library function). The test `toolchain/floating-promise` in `tools/toolchain/floating-promise.test.ts` keeps both results below true.

Biome 2.6.4 with the repository configuration (preset `recommended`): no finding.

```text
$ pnpm exec biome lint tools/fixtures/floating-promise.ts
Checked 1 file in 5ms. No fixes applied.
(exit 0)
```

Biome 2.6.4 with its rule `nursery/noFloatingPromises` switched on: finds line 17 only, as an info, and misses the library promise on line 19.

```text
$ pnpm exec biome lint --only=nursery/noFloatingPromises tools/fixtures/floating-promise.ts
tools/fixtures/floating-promise.ts:17:3 lint/nursery/noFloatingPromises
  i A "floating" Promise was found, meaning it is not properly handled and could lead to ignored errors or unexpected behavior.
Checked 1 file in 89ms. No fixes applied.
Found 1 info.
(exit 0)
```

ESLint 10.14.0 with typescript-eslint 8.72.1: finds both.

```text
$ pnpm exec eslint --no-ignore tools/fixtures/floating-promise.ts
tools/fixtures/floating-promise.ts
  17:3  error  Promises must be awaited, ...  @typescript-eslint/no-floating-promises
  19:3  error  Promises must be awaited, ...  @typescript-eslint/no-floating-promises
2 problems (2 errors, 0 warnings)
(exit 1)
```

The fixture has its own `tools/fixtures/tsconfig.json`. Without it (fixture linted through `allowDefaultProject`), ESLint also found only line 17: the default project did not type the library call as a promise (cause not examined further). This is why the project service runs without a default project.

## Opengrep rule tests

Opengrep 1.32.0 has a built-in test mode; `make opengrep` uses it through `tools/ci/opengrep_test.py`. Checked on 2026-11-01 with `.tools/bin/opengrep test --help` of the pinned binary and in scratch directories:

- Command: `opengrep test --config <rule file or directory> <test files or directories>`. A test file marks an expected finding with a comment `ruleid: <rule-id>` on the line before it and a case that must stay quiet with `ok: <rule-id>`. Exit 0 when every test passes, 1 when a test fails (for example `unexpected findings lines 2.`), 123 to 125 for errors (from `--help`).
- With a rules directory and a tests directory, every rule runs on every test file, and the annotations of one rule count as missing findings of the others. `opengrep_test.py` therefore runs `opengrep test` once per rule, with that rule's file and the `bad_*.ts` and `good_*.ts` files of `.opengrep/tests/<rule-id>/`.
- The test mode ignores the `paths:` filter of a rule: a test file below `packages/core/src/time.ts` was still reported by a rule that excludes that path. Cases that depend on the path of a file therefore live in `.opengrep/tests/<rule-id>/paths/<repository path>`; `opengrep_test.py` copies them into a scratch directory and compares `opengrep scan --json` with their annotations.
- Path patterns in `paths:` match at any depth: `packages/core/src/time.ts` and `/packages/core/src/time.ts` both also exclude `x/packages/core/src/time.ts`.
- Without a `.semgrepignore` file, `opengrep scan` skips `test/`, `tests/` and `node_modules/` directories by a built-in list; a `.semgrepignore` replaces that list. Opengrep reads `.semgrepignore`, not `.opengrepignore`. The repository's `.semgrepignore` keeps test directories in the scan and leaves out only `.opengrep/tests/`; files ignored by git are skipped anyway.
- `metavariable-regex` matches from the start of the bound text: `(log|logger)$` does not match `ctx.log`, `^(.*\.)?log$` does.
- Rules with `languages: [typescript]` scan `*.ts` and `*.tsx` only; `*.mts` and `*.cts` files are not scanned at all, not even when named on the command line, and `*.js` files only by rules for `javascript`.
- Without type information the rules see types only where the same file declares them. `gw-no-untrusted-in-log` runs in taint mode from variables and parameters declared as `Untrusted` or `Untrusted<T>` and follows values derived from them within the file. `gw-no-model-credential-env` sees aliases of `process.env` as a variable, a parameter default, a parameter typed `NodeJS.ProcessEnv`, `env` renamed out of `process` and `env` imported from `node:process` under another name or assigned to a variable; writing into a parameter typed `NodeJS.ProcessEnv` and `delete` on it stay allowed, because that builds the child environment (ADR-57).
- Not covered by `gw-no-model-credential-env`: an alias passed on without the type `NodeJS.ProcessEnv`, a destructuring parameter default, and parsing the whole of `process.env` with a schema (for example `schema.parse(process.env)`) followed by a read of the parsed object; outside loader modules `gw-process-env-only-in-loaders` still reports the access to `process.env`.
- Not covered by `gw-no-untrusted-in-log`: an `Untrusted` value whose type comes from another file (a field of an imported interface, the result of an imported function). Known false positive: a value derived from an `Untrusted` value stays tainted even when it carries no content, for example a boolean such as `body.value === ""` or `body.value.includes("x")`; derive such a fact from `untrustedSummary(value)` (for example its `length`) instead.
- `opengrep scan --help` of 1.32.0 lists no metrics option; `make opengrep` passes `--disable-version-check` so that a scan makes no network request.

## Coverage thresholds

`vitest.config.ts` reads the thresholds from `quality/coverage.json` (`global` plus one entry per area glob); no number is set in the configuration itself. The test `toolchain/vitest-config > coverage thresholds come from quality/coverage.json` keeps both equal. Measured on 2026-11-01: raising the `packages/core/src/**` line threshold to 101 makes `pnpm exec vitest run --coverage` fail with `ERROR: Coverage for lines (100%) does not meet "packages/core/src/**" threshold (101%)`.

## Secret scanning

`make gitleaks` runs `gitleaks git --config .gitleaks.toml --redact --log-opts "$(GITLEAKS_LOG_OPTS)"`. The default range is `origin/main..HEAD`; a repository without that ref scans all history.

Subcommands of the pinned gitleaks 8.30.1, read from `gitleaks --help` on 2026-11-01: `git` (commits, option `--log-opts`), `dir` with the aliases `file` and `directory` (files without Git history) and `stdin`. The older `detect` and `protect` still answer `--help` but are not listed. A check of a single file without history, such as the counter check of release point V8, uses `gitleaks dir --config .gitleaks.toml <file>`; `tools/ci/tests/test_gitleaks.py` runs it the same way.

The pre-commit hook scans the staged changes with `gitleaks git --staged --config .gitleaks.toml .` (option `--staged` of `gitleaks git --help`, read 2026-11-01; the older `protect --staged` is not listed). Checked on 2026-11-01 in a scratch repository: a staged file with a random `ghp_` token gives `RuleID: github-pat` and exit 1; after `git reset` the same call exits 0.

`.gitleaks.toml` extends the default rules (`[extend] useDefault = true`) with two own rules and one allowlist of exact values from `quality/secrets/samples.txt`. Credential formats, checked on 2026-11-01:

| Credential | Shape used for the samples | Source |
|---|---|---|
| GitHub `ghp_`, `gho_`, `ghu_`, `ghs_`, `ghr_` | prefix plus 36 Base62 characters (30 random, 6 CRC32 checksum) | prefixes: GitHub documentation "About authentication to GitHub", section "GitHub's token formats"; length and checksum: GitHub blog "Behind GitHub's new authentication token formats" (2021-04-05, updated 2023-05-10) |
| GitHub `github_pat_` | prefix plus 82 word characters | prefix: GitHub documentation as above; the vendor documents no length, 82 is the default gitleaks rule `github-fine-grained-pat` |
| GitHub stateless installation token | `ghs_<app id>_<JWT>`, about 520 characters, two dots | GitHub documentation as above (rollout from 2026-04-27) and GitHub changelog 2026-05-15 "GitHub App installation tokens per-request override header" |
| Anthropic API key and Admin API key | prefix plus 93 characters `[A-Za-z0-9_-]` plus `AA` | default gitleaks rules `anthropic-api-key` and `anthropic-admin-api-key`; the Anthropic Admin API documentation names the admin prefix |
| Claude Code OAuth tokens (`oat01`, `ort01` after the family prefix) | as the API key | not documented by the vendor; the Claude Code authentication documentation names `claude setup-token` without a format |

Results:

- The detailed design's pattern for GitHub tokens (`gh[opsur]_[A-Za-z0-9]{20,}`) misses the stateless installation token, and so do the default rules: `github-app-token` expects 36 alphanumeric characters after `ghs_`, and `jwt` needs a word boundary before `ey`. The own rule `github-app-token-stateless` covers it.
- Gitleaks drops a finding whose secret contains a stopword of its global allowlist, case-insensitive; one of them is the alphabet `abcdefghijklmnopqrstuvwxyz`. Sample values avoid it.
- The default GitHub rules require an entropy of at least 3, so a sample of one repeated character is not found. The samples mix the marker `EXAMPLE` with digits and letters instead.
- Whether GitHub push protection blocks the synthetic values on the first push is not checked (the GitHub values carry no valid checksum).

## Licenses

Every license below was read at the source on 2026-11-01: the license file in the vendor repository at the release tag, or the registry metadata of the exact version (npm: `https://registry.npmjs.org/<name>/<version>`, field `license`; PyPI: `https://pypi.org/pypi/<name>/<version>/json`, fields `license_expression`, `license` and the license classifiers). Where a registry field was empty or not an SPDX identifier, the license file at the tag was read instead. The column "Allowlist" compares the license with `quality/licenses/allowed.txt`; "dev exception" means an entry in `quality/licenses/dev-exceptions.txt`. "Shipped" means part of a Guildwork release, of its container images or of its compose bundle.

Libraries and bundle components that are not pinned yet were read at the latest release on the retrieval date; the version is pinned by the task that adds them, and the license gate checks it again from the lockfile.

### Repository toolchain

| Tool | Version read | License (SPDX) | Source | Retrieved | Shipped | Allowlist |
|---|---|---|---|---|---|---|
| Node.js | 22.23.4 | MIT for Node.js itself; the same file lists bundled components under their own licenses, among them `deps/minimatch` (BlueOak-1.0.0) and `deps/npm` (Artistic-2.0) | https://github.com/nodejs/node/blob/v22.23.4/LICENSE | 2026-11-01 | yes (runtime of the images) | yes since 2026-11-01 (BlueOak-1.0.0 added; images ship without npm), see "Findings" |
| pnpm | 12.16.1 (and `@pnpm/exe.*` 12.16.1) | MIT | https://registry.npmjs.org/pnpm/12.16.1 | 2026-11-01 | no | yes |
| TypeScript | 6.0.3 | Apache-2.0 | https://registry.npmjs.org/typescript/6.0.3 | 2026-11-01 | no | yes |
| Biome (`@biomejs/biome` and `@biomejs/cli-*`) | 2.6.4 | MIT OR Apache-2.0 | https://registry.npmjs.org/@biomejs%2Fbiome/2.6.4; license files https://github.com/biomejs/biome/blob/%40biomejs/biome%402.6.4/LICENSE-MIT and `LICENSE-APACHE` at the same tag | 2026-11-01 | no | yes |
| ESLint | 10.14.0 | MIT | https://registry.npmjs.org/eslint/10.14.0 | 2026-11-01 | no | yes |
| typescript-eslint (and `@typescript-eslint/*`) | 8.72.1 | MIT | https://registry.npmjs.org/typescript-eslint/8.72.1 | 2026-11-01 | no | yes |
| Vitest, `@vitest/coverage-v8` | 5.0.5 | MIT | https://registry.npmjs.org/vitest/5.0.5, https://registry.npmjs.org/@vitest%2Fcoverage-v8/5.0.5 | 2026-11-01 | no | yes |
| Vite | 8.3.5 | MIT | https://registry.npmjs.org/vite/8.3.5 | 2026-11-01 | no | yes |
| `@types/node` | 22.20.5 | MIT | https://registry.npmjs.org/@types%2Fnode/22.20.5 | 2026-11-01 | no | yes |
| Testcontainers for Node (`testcontainers`, `@testcontainers/postgresql`) | 12.2.1 (latest) | MIT | https://registry.npmjs.org/testcontainers/12.2.1, https://registry.npmjs.org/@testcontainers%2Fpostgresql/12.2.1 | 2026-11-01 | no | yes |
| Python | 3.12 (file read at tag v3.12.16) | Python-2.0 (PSF License Agreement version 2 plus the historical BeOpen, CNRI and CWI terms in one file; code in the documentation 0BSD) | https://github.com/python/cpython/blob/v3.12.16/LICENSE | 2026-11-01 | no | yes |
| uv | 0.13.5 | MIT OR Apache-2.0 | https://github.com/astral-sh/uv/blob/0.13.5/Cargo.toml (`license`), license files `LICENSE-MIT` and `LICENSE-APACHE` at the same tag | 2026-11-01 | no | yes |
| ruff | 0.17.2 | MIT | https://pypi.org/pypi/ruff/0.17.2/json | 2026-11-01 | no | yes |
| mypy | 2.4.0 | MIT | https://pypi.org/pypi/mypy/2.4.0/json | 2026-11-01 | no | yes |
| pre-commit | 4.7.0 | MIT | https://pypi.org/pypi/pre-commit/4.7.0/json | 2026-11-01 | no | yes |
| pre-commit-hooks (file hygiene hooks of `.pre-commit-config.yaml`) | 6.0.0 | MIT | https://pypi.org/pypi/pre-commit-hooks/6.0.0/json (`license`), https://github.com/pre-commit/pre-commit-hooks/blob/v6.0.0/LICENSE | 2026-11-01 | no | yes |
| zizmor | 1.31.1 | MIT | https://github.com/zizmorcore/zizmor/blob/v1.31.1/LICENSE | 2026-11-01 | no | yes |
| check-jsonschema | 0.38.2 | Apache-2.0 | https://github.com/python-jsonschema/check-jsonschema/blob/0.38.2/LICENSE | 2026-11-01 | no | yes |
| gitleaks | 8.30.1 | MIT | https://github.com/gitleaks/gitleaks/blob/v8.30.1/LICENSE | 2026-11-01 | no | yes |
| Opengrep | 1.32.0 | LGPL-2.1-only (license file LGPL 2.1; source headers: "version 2.1 as published by the Free Software Foundation", no "or later") | https://github.com/opengrep/opengrep/blob/v1.32.0/LICENSE, header of `src/osemgrep/cli/CLI.ml` at the same tag | 2026-11-01 | no | dev exception |
| actionlint | 1.7.12 | MIT | https://github.com/rhysd/actionlint/blob/v1.7.12/LICENSE.txt | 2026-11-01 | no | yes |
| osv-scanner | 2.7.0 | Apache-2.0 | https://github.com/google/osv-scanner/blob/v2.7.0/LICENSE | 2026-11-01 | no | yes |
| ScanCode Toolkit (PyPI `scancode-toolkit-mini`, the build without prebuilt native plugins) | 32.5.0 (latest) | Apache-2.0 AND CC-BY-4.0 (code Apache-2.0, license data CC-BY-4.0, NOTICE); the package metadata adds `LicenseRef-scancode-other-permissive AND LicenseRef-scancode-other-copyleft` for embedded third party packages, which NOTICE documents in `.ABOUT` files | https://github.com/aboutcode-org/scancode-toolkit/blob/v32.5.0/NOTICE, https://github.com/aboutcode-org/scancode-toolkit/blob/v32.5.0/setup-mini.cfg (`license`), https://pypi.org/pypi/scancode-toolkit-mini/32.5.0/json | 2026-11-01 | no | dev exception |
| pylibmagic (libmagic for ScanCode) | 0.5.0 | BSD-3-Clause; the bundled libmagic of `file` 5.41 is BSD-2-Clause | https://github.com/kratsg/pylibmagic/blob/v0.5.0/LICENSE, `GIT_TAG FILE5_41` in https://github.com/kratsg/pylibmagic/blob/v0.5.0/CMakeLists.txt, https://github.com/file/file/blob/FILE5_41/COPYING | 2026-11-01 | no | yes |
| Python container image for ScanCode (Docker Official Image `python`) | tag 3.12.15-slim-trixie, pinned by digest in `tools/bootstrap/tools.toml` | Python-2.0 for Python; the Dockerfiles are MIT; the image also holds Debian packages under their own licenses ("License" section of the image page) | https://hub.docker.com/_/python, https://github.com/docker-library/python/blob/master/LICENSE | 2026-11-01 | no | not checked (only run, never shipped) |
| Docker Engine | not pinned (file read at tag docker-v29.9.2) | Apache-2.0 | https://github.com/moby/moby/blob/docker-v29.9.2/LICENSE | 2026-11-01 | no (provided by the developer or the CI runner) | yes |

Prettier is not used; Biome is the only formatter. For the record: `prettier` 3.9.10 (latest) is MIT, https://registry.npmjs.org/prettier/3.9.10, retrieved 2026-11-01.

### ScanCode

ScanCode Toolkit publishes no container image of its own: the release workflow at tag v32.5.0 (`.github/workflows/scancode-release.yml`) builds none, the vendor organization on GitHub lists container packages only for other projects (`scancode.io`, `purldb`, `vulnerablecode`, `dejacode`, `healthycode`), and Docker Hub has only third party copies (all checked 2026-11-01). `make scancode` therefore runs the Docker Official Image of Python, pinned by digest, and installs ScanCode into it on every run from `tools/bootstrap/scancode/requirements.txt` (exact versions with hashes, `pip --require-hashes`). Without a container runtime, `make scancode SCANCODE_RUNNER=local` installs the same file with uv into `.tools/scancode`, apart from the project `.venv`. The file is compiled from `requirements.in` with ScanCode's own pins of tag v32.5.0 as constraints (`constraints.txt`): with newer dependencies, ScanCode 32.5.0 fails at start (with pluggy 1.7.0 it stops with `did not find any 'pre_scan' hooks`, measured 2026-11-01). Two of those pins, `intbitset` 4.1.0 and `pyahocorasick` 2.3.0, have no wheel for Linux aarch64; `constraints.txt` raises them to the patch releases 4.1.2 and 2.3.1. Measured 2026-11-01 with `pip download --require-hashes --only-binary :all: --python-version 3.12` for Linux x86_64 and aarch64: every package of `requirements.txt` resolves to a wheel with a listed hash on both. ScanCode needs libmagic; its plugin `typecode-libmagic` has wheels only for x86_64, so `pylibmagic` provides libmagic for x86_64 and arm64 on Linux and macOS.

The packages of the ScanCode environment are development tools that are only run, like the content of the image; the license gate does not read them. Read from their metadata on 2026-11-01: besides licenses of the allowlist, `chardet` 5.2.0 is LGPL-2.0-or-later, `intbitset` 4.1.0 LGPL-3.0-or-later and `text-unidecode` 1.3 the Artistic License or GPL-2.0-or-later (classifiers only).

### Planned runtime libraries

| Library | npm name | Version read | License (SPDX) | Source | Retrieved | Shipped | Allowlist |
|---|---|---|---|---|---|---|---|
| TypeBox | `typebox` | 1.4.3 (latest) | MIT | https://registry.npmjs.org/typebox/1.4.3, https://github.com/sinclairzx81/typebox/blob/1.4.3/license | 2026-11-01 | yes | yes |
| Ajv | `ajv` | 8.20.0 (latest) | MIT | https://registry.npmjs.org/ajv/8.20.0 | 2026-11-01 | yes | yes |
| pino | `pino` | 10.4.0 (latest) | MIT | https://registry.npmjs.org/pino/10.4.0 | 2026-11-01 | yes | yes |
| Fastify | `fastify` | 5.12.7 (latest) | MIT | https://registry.npmjs.org/fastify/5.12.7 | 2026-11-01 | yes | yes |
| Kysely | `kysely` | 0.29.8 (latest) | MIT | https://registry.npmjs.org/kysely/0.29.8 | 2026-11-01 | yes | yes |
| pg-boss | `pg-boss` | 12.38.0 (latest) | MIT | https://registry.npmjs.org/pg-boss/12.38.0 | 2026-11-01 | yes | yes |

npm name of TypeBox: the current release line is published as `typebox` (1.x; its readme installs it with `npm install typebox`, repository `sinclairzx81/typebox`). The older name `@sinclair/typebox` holds the 0.34 line (0.34.52, MIT, repository `sinclairzx81/sinclair-typebox`). New code uses `typebox`.

Only the packages themselves were read; their dependency trees enter the license gate with the lockfile when the packages are added.

### Bundle components

| Component | Version read | License (SPDX) | Source | Retrieved | Shipped | Allowlist |
|---|---|---|---|---|---|---|
| Caddy | 2.11.7 (latest) | Apache-2.0 | https://github.com/caddyserver/caddy/blob/v2.11.7/LICENSE | 2026-11-01 | yes (compose bundle) | yes |
| restic | 0.19.1 (latest) | BSD-2-Clause | https://github.com/restic/restic/blob/v0.19.1/LICENSE | 2026-11-01 | yes (backup) | yes |
| OpenTelemetry Collector, contrib distribution (`otelcol-contrib`) | 0.164.0 (distribution), 0.164.1 (contrib components) | Apache-2.0 | https://github.com/open-telemetry/opentelemetry-collector-releases/blob/v0.164.0/LICENSE, https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/v0.164.1/LICENSE | 2026-11-01 | yes (compose bundle) | yes |
| PostgreSQL | file read at tag REL_17_11 | PostgreSQL | https://github.com/postgres/postgres/blob/REL_17_11/COPYRIGHT | 2026-11-01 | yes (compose bundle) | yes since 2026-11-01 (PostgreSQL added), see "Findings" |
| pgvector | 0.8.7 (latest) | PostgreSQL | https://github.com/pgvector/pgvector/blob/v0.8.7/LICENSE | 2026-11-01 | yes (compose bundle) | yes since 2026-11-01 (PostgreSQL added), see "Findings" |

Only the license of each project was read; the Go modules compiled into the Caddy, restic and Collector binaries are checked by the release scan (SBOM and ScanCode), not here.

### Locked development dependencies

All packages in `pnpm-lock.yaml` were read from the npm registry by exact version, all packages in `uv.lock` from PyPI by exact version, on 2026-11-01. Licenses found: MIT, ISC, BSD-2-Clause, BSD-3-Clause, Apache-2.0, `MIT OR Apache-2.0`, `Apache-2.0 OR BSD-2-Clause`, PSF-2.0, MPL-2.0 and BlueOak-1.0.0. Every one is in the allowlist; BlueOak-1.0.0 (`minimatch` 10.2.6, a dependency of ESLint) since 2026-11-01. MPL-2.0 is allowed; it comes from `lightningcss` 1.33.0 and its platform packages (through Vite) and from the Python packages `certifi` and `pathspec`. Three Python packages carry no SPDX value in their metadata; their license files were read at the tag: `mypy-extensions` 1.1.0 MIT (https://github.com/python/mypy_extensions/blob/1.1.0/LICENSE), `nodeenv` 1.12.0 BSD-3-Clause text (https://github.com/ekalinin/nodeenv/blob/1.12.0/LICENSE), `check-jsonschema` 0.38.2 Apache-2.0 (row above).

The license gate (`make licenses`) reads these licenses again on every run: npm packages from `pnpm --recursive licenses list --json` over the whole workspace, once for all packages and once with `--prod` for the runtime ones (pnpm 12.16.1, read 2026-11-01: a JSON object keyed by license expression whose values list packages with `name`, `versions`, `paths`, `license` and `author`), Python packages from `uv.lock` with the license of the installed wheel metadata in `.venv` (`License-Expression`, else a one-line `License` field). That metadata differs from the PyPI page in one place: `mypy-extensions` 1.1.0 carries `License-Expression: MIT`, while `pathspec` 1.1.1 has only a classifier; its license file is MPL-2.0 (https://github.com/cpburnz/python-pathspec/blob/v1.1.1/LICENSE, read 2026-11-01). `check-jsonschema`, `nodeenv` and `pathspec` are therefore entered in `quality/licenses/dev-exceptions.txt` with the license of their license file.

### Findings

Two shipped components had a license outside the allowlist. Replacing them is not possible without changing the architecture; decided on 2026-11-01 (architecture 12 section 5.2): BlueOak-1.0.0 and PostgreSQL are added to the allowlist, and the runtime images are built without npm (Artistic-2.0).

- **Node.js** is the runtime of the images (ADR-03). Its binary contains `deps/minimatch` under BlueOak-1.0.0, and the official distributions add `deps/npm` under Artistic-2.0. Decision: BlueOak-1.0.0 (a permissive license) is in the allowlist, and the runtime images are built without npm so that Artistic-2.0 is not shipped (Corepack is MIT, but the images do not need it either).
- **PostgreSQL** and **pgvector** are services of the compose bundle under the PostgreSQL license. Decision: `PostgreSQL` (a permissive license) is in the allowlist, since the architecture fixes PostgreSQL as the database.

Terms beyond the license: ScanCode's license data is CC-BY-4.0, which asks for attribution when the data is redistributed; Guildwork only runs the scanner and does not redistribute the data. The Opengrep rule collection is under other terms and is not used (ADR-50); only own rules run.
