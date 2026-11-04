<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->

# Governance

Guildwork is a community project without a company behind it. This file describes who decides and how.

## Named values

| Name | Value | Used in |
|---|---|---|
| `LAZY_CONSENSUS_PERIOD` | 7 calendar days | [Lazy consensus](#lazy-consensus) |
| `FIRST_TRIAGE_TARGET` | 14 calendar days | [Triage](#triage) |

Changing a value in this table is a governance change (see [Changing this document](#changing-this-document)).

## Maintainers

- The project starts with one maintainer.
- The maintainers are the members of the GitHub team `@guildwork-dev/maintainers`. `.github/CODEOWNERS` assigns the repository to this team, so every pull request needs the approval of a maintainer. While there is one maintainer, only that maintainer can merge, and the merge is this approval; the ruleset of `main` has no bypass, so the required checks apply to the maintainer too.
- A new maintainer is proposed by a pull request that records the proposal in `docs/DECISIONS.md`. The proposal is accepted only with the approval of all existing maintainers; after the merge, the person is added to the team. With the second maintainer, the ruleset of `main` is changed to require a code owner approval (one approval, still without bypass).
- A maintainer may step down at any time by pull request. A maintainer who has not taken part in reviews or decisions for a long time may be moved to emeritus status by the other maintainers, with the approval of all of them.

## Decisions

- **Lasting decisions** (architecture, interfaces, licensing of dependencies, security model, processes) are recorded as an ADR in `docs/adr/` in MADR format, one file per decision, proposed by pull request.
- **Smaller decisions** (rulings that settle a detail without changing an ADR) are recorded in `docs/DECISIONS.md`, also by pull request.
- An ADR is never edited to reverse its decision. A new ADR supersedes it, and the old one is marked as superseded with a link.

## Lazy consensus

While there is one maintainer, that maintainer decides, and the reasoning is recorded in the ADR or ruling.

From two maintainers on, a pull request that adds or changes an ADR is accepted by lazy consensus: it is accepted if no maintainer objects within `LAZY_CONSENSUS_PERIOD` after the pull request was marked ready for review. An objection must state its reason in the pull request. An objection blocks the merge until the maintainers agree; if they cannot agree, the proposal is not accepted.

## Triage

- New issues are opened with the issue forms and get the label `status: triage`. Labels are versioned in `.github/labels.yml`.
- A maintainer gives every new issue a first triage within `FIRST_TRIAGE_TARGET`: a type label (`type: bug`, `type: feature`, `type: docs`), one or more area labels, and a status other than `status: triage`, or a question to the reporter (`status: needs-info`).
- This target is a goal of a volunteer project, not a service level agreement.

## Code of Conduct

Everyone taking part in the project follows the [Code of Conduct](CODE_OF_CONDUCT.md). The maintainers enforce it.

## Changing this document

Changes to this document, including the named values above, need the approval of all maintainers. Lazy consensus does not apply to them.
