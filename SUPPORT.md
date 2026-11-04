<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->

# Support

Guildwork is a community project. There is no commercial support, no service level agreement and no paid support plan.

## Where to ask

| Topic | Channel |
|---|---|
| Questions about using or extending Guildwork | GitHub Discussions of this repository |
| Bugs and feature requests | GitHub Issues, using the issue forms |
| Security vulnerabilities | only privately, see [SECURITY.md](SECURITY.md) |
| Problems with a specific installation (accounts, access, configuration, data) | the operator of that installation; the project has no access to installations and their data |

## What the project promises

- **Security fixes** are provided for the newest minor version only. Older versions do not get fixes; upgrade to the newest minor version.
- **Plugin and service interfaces** carry no stability promise while their `apiVersion` is `v1alpha1`. From `v1beta1` on, a deprecated interface version stays supported for at least one minor version, during which the old and the new `apiVersion` work side by side.
- **Upgrades**: every release documents its upgrade and migration path in `CHANGELOG.md` and in the installation documentation.

Everything else is best effort by volunteers.
