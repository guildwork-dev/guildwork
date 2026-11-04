// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// The same through an import of node:process.

import * as proc from "node:process";
import nodeProcess from "node:process";
import { env } from "node:process";

// ruleid: gw-no-model-credential-env
const apiKey = env.ANTHROPIC_API_KEY;
// ruleid: gw-no-model-credential-env
const token = proc.env.CLAUDE_CODE_OAUTH_TOKEN;
// ruleid: gw-no-model-credential-env
const { CLAUDE_CONFIG_DIR } = nodeProcess.env;

export { apiKey, CLAUDE_CONFIG_DIR, token };
