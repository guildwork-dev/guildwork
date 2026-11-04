// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Every import form of the write subpath of a plugin package is reported.

// ruleid: gw-scm-write-only-in-effect-gateway
import { addComment } from "@guildwork/plugin-github/write";
// ruleid: gw-scm-write-only-in-effect-gateway
import * as gitlabWrite from "@guildwork/plugin-gitlab/write";
// ruleid: gw-scm-write-only-in-effect-gateway
import type { WriteClient } from "@guildwork/plugin-github/write";
// ruleid: gw-scm-write-only-in-effect-gateway
import submitReview from "@guildwork/plugin-github/write/review.js";
// ruleid: gw-scm-write-only-in-effect-gateway
import "@guildwork/plugin-github/write";
// ruleid: gw-scm-write-only-in-effect-gateway
export { push } from "@guildwork/plugin-github/write";
// ruleid: gw-scm-write-only-in-effect-gateway
export * from "@guildwork/plugin-gitlab/write";
// ruleid: gw-scm-write-only-in-effect-gateway
export type { WriteResult } from "@guildwork/plugin-github/write";

export async function load(): Promise<unknown> {
  // ruleid: gw-scm-write-only-in-effect-gateway
  return import("@guildwork/plugin-github/write");
}

// ruleid: gw-scm-write-only-in-effect-gateway
const legacy = require("@guildwork/plugin-github/write");

export { addComment, gitlabWrite, legacy, submitReview, type WriteClient };
