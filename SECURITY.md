<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->

# Security Policy

## Reporting a vulnerability

The only way to report a vulnerability is **GitHub Private Vulnerability Reporting** of this repository: open the "Security" tab of `guildwork-dev/guildwork` and choose "Report a vulnerability" (direct link: <https://github.com/guildwork-dev/guildwork/security/advisories/new>).

- Do not open a public issue, discussion or pull request for a vulnerability.
- There is no security email address. Reports sent through other channels are not handled as security reports.
- There is no bug bounty program and no monetary reward.

Please include the affected version or commit, the component (service, plugin, driver, CLI, installer), steps to reproduce, the impact you expect, and whether the issue is already public.

## Named values

Target times are goals of a volunteer project, not a service level agreement. They are counted from the time the report arrives.

| Name | Value | Meaning |
|---|---|---|
| `ACKNOWLEDGEMENT_TARGET` | 3 business days | A maintainer confirms receipt of the report. |
| `ASSESSMENT_TARGET` | 14 calendar days | A maintainer confirms or rejects the vulnerability and rates its severity (CVSS). |
| `FIX_TARGET_CRITICAL_HIGH` | 30 calendar days after assessment | A fix release for a confirmed vulnerability rated critical or high. |
| `FIX_TARGET_OTHER` | 90 calendar days after assessment | A fix release for a confirmed vulnerability rated medium or low. |

Changing a value in this table needs the approval of all maintainers (see [GOVERNANCE.md](GOVERNANCE.md)).

## What happens after a report

1. The maintainers acknowledge, reproduce and assess the report in the private advisory.
2. A fix is developed in a private fork of the advisory. The reporter is invited to review it.
3. The fix is released, the advisory is published with a CVE where applicable, and the reporter is credited unless they ask not to be.

If a target time cannot be met, the maintainers say so in the advisory and give a new date.

## Supported versions

Security fixes are provided for the newest minor version only (see [SUPPORT.md](SUPPORT.md)). There is no release yet.

## Scope

In scope: the code, container images, installer and documentation published from this repository.

Out of scope:

- A specific installation run by someone else: report to its operator.
- Vulnerabilities in dependencies: report them upstream. Tell us through Private Vulnerability Reporting if the way Guildwork uses the dependency makes it exploitable.
- Behavior of external services and model providers that Guildwork connects to.
