<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->

# Dependency updates (Renovate)

`renovate.json` configures the hosted Renovate app (installed by the owner; Renovate itself is AGPL-3.0 and is only used as a service, never bundled). The values come from section 2.11 of the detailed design: `config:best-practices`, early Monday (cron `* 0-5 * * 1`, UTC), `minimumReleaseAge` 7 days, majors only after approval on the Dependency Dashboard, grouped pull requests, at most 5 open pull requests, digest pins for actions and images. JSON has no comments, so each package rule carries its reason in `description`.

## Schema check

`make workflows` runs `check-jsonschema --builtin-schema vendor.renovate renovate.json` (variable `RENOVATE_CONFIG`). The option is listed by `check-jsonschema --help` of the pinned 0.38.2 (read 2026-11-01: "The '--builtin-schema' flag supports the following schema names: ... vendor.renovate ..."); the schema ships inside the package (`check_jsonschema/builtin_schemas/vendor/renovate.json`, "JSON schema for Renovate 44.103.6 config files"), so the check needs no network. The test `tools/ci/tests/test_renovate_schema.py` runs `make workflows` with a broken copy and expects it to fail.

Limit: the schema allows unknown top level keys, so it catches wrong types and values, not a misspelled option name. The same test therefore also checks the values of section 2.11 by name. Renovate's own validator is stricter but is an AGPL npm package with a Node.js 24 requirement and is not part of the toolchain; it was run once by hand (below).

## What Renovate updates

| Files | Manager | Group (non-major) | Notes |
|---|---|---|---|
| `package.json`, `pnpm-lock.yaml`, `packageManager` | npm | npm dependencies | the lockfile changes with the manifest |
| `pyproject.toml`, `uv.lock` | pep621 | Python tools | the lockfile changes with the manifest |
| `.github/workflows/*.yml` | github-actions | GitHub Actions | commit SHA plus `# v<version>` comment; runner labels are not updated (fixed by `quality/ci/policy.toml`) |
| `.node-version`, `engines.node` | nodenv, npm | Node.js | both together; a new major (Node.js 22 LTS, ADR-03) only after approval |
| `.python-version`, ScanCode image | pyenv, regex | | held on 3.12 (`allowedVersions`) |
| `tools/bootstrap/tools.toml` binaries | regex, `github-releases` | bootstrap binaries | only `version`, see below |
| `tools/bootstrap/tools.toml` images | regex, `docker` | bootstrap images | tag and digest together |
| `tools/bootstrap/scancode/requirements.in` | pip_requirements | ScanCode | only after approval, see below |
| `tools/bootstrap/scancode/requirements.txt` | pip_requirements | | disabled, see below |

## Rulings

- **Checksums of the pinned binaries.** Renovate cannot fill in `sha256`, and the rule of `tools.toml` is that a checksum is only ever copied from the vendor's published source, never computed. The regex manager therefore matches only `version` (with the GitHub repository from `url`); the pull request carries a note to copy the checksums of every platform, update `source` and `retrieved` and check the license row in `toolchain.md`. Until that is done, `make bootstrap` stops with `bootstrap.checksum_mismatch`, so `ci-ok` stays red and the half-done update cannot be merged. The binaries get their own group so that a pull request waiting for this step does not hold back other updates.
- **ScanCode environment.** `requirements.txt` is compiled with ScanCode's own pins as constraints (`constraints.txt`, see `toolchain.md` section ScanCode); Renovate would update single packages with new hashes and break ScanCode (as pluggy 1.7.0 does). The file is disabled for Renovate; the two direct pins in `requirements.in` are watched and raise a pull request only after approval on the dashboard, with the steps to recompile in the note.
- **Lock file maintenance off.** `config:best-practices` turns on weekly lock file maintenance (`:maintainLockFilesWeekly`). There the package managers choose new transitive versions, and Renovate does not apply `minimumReleaseAge` to it (its own preset `security:minimumReleaseAgeNpm` says so in a note). It is off; transitive versions move with the manifest update that needs them, and known vulnerabilities still surface through `make osv` (and the planned daily full scan of `main`).
- **Waiting time everywhere.** `config:best-practices` contains `security:minimumReleaseAgeNpm`, a package rule with 3 days for npm that beats the top level value. A package rule after it sets 7 days again for major, minor and patch updates of every package. `internalChecksFilter: strict` keeps the branch from being created before that time.
- **Updates without a release date.** Renovate requires a release date for the waiting time (`minimumReleaseAgeBehaviour` default `timestamp-required`). Docker Hub gives one only through its tag listing; in the dry run below that listing stopped with HTTP 403 on page 11 for `library/python`, so the image update stayed pending. It is not forced: a pending update is listed on the Dependency Dashboard and can be created from there by a maintainer.
- **Commit messages.** `semanticCommits: enabled`, so bot commits are Conventional Commits (`chore(deps): ...`). Bot commits have no sign-off; the maintainer takes over the pull request with an own sign-off.

## Dry run (2026-11-01)

Renovate 44.103.6 (the version of the bundled schema) from npm in a scratch directory, with Node.js 22 and a polyfill for `RegExp.escape` (Renovate 44 asks for Node.js 24): `renovate-config-validator --strict --no-global renovate.json` reports "Config validated successfully"; a copy with `prConcurrentLimit: "five"` fails. `renovate --platform=local --dry-run=lookup` on a clone extracted the 5 binaries and the ScanCode image from `tools.toml` with their current versions and digest, marked every dependency of the ScanCode `requirements.txt` as disabled, held `.python-version` on 3.12, put three Python updates into the branch `renovate/python-tools` as pending (released 5 to 6 days before, so the 7 days apply to PyPI as well), proposed a newer ScanCode image tag with a new digest in `renovate/bootstrap-images`, and offered the Node.js and TypeScript majors only as majors. The GitHub release lookups were skipped without a token (`github-token-required`); the hosted app has one.
