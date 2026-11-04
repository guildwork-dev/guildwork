<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->

# Quality documentation

How changes reach `main` and what is checked on the way. [CONTRIBUTING.md](../../CONTRIBUTING.md) is the short version for contributors; the files here hold the rules and the reasons.

| File | Content |
|---|---|
| [push-discipline.md](push-discipline.md) | Branches, commits, the git hooks, what runs before a push, pull requests and the protection of `main` |
| [red-team-gate.md](red-team-gate.md) | The independent review before every push and local merge: report, verdict line, checklist |
| [gates.md](gates.md) | Every gate of `make check` and CI, generated from `quality/gates.toml` |
| [toolchain.md](toolchain.md) | Pinned tool versions, measurements behind the toolchain rulings, the license of every tool |
| [licenses.md](licenses.md) | License of the project, SPDX headers, the dependency allowlist and the license gate |
| [public-switch.md](public-switch.md) | The release checklist V0 to V10 that runs once before the repository becomes public |

Single sources: the list of gates is `quality/gates.toml`, the hooks are `.pre-commit-config.yaml`, the allowed licenses are `quality/licenses/allowed.txt`. These documents link to them and do not repeat their values.
