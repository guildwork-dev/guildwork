// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Every read form through an alias of process.env: destructuring (also with
// renaming), presence check, non-null assertion, and the aliases env renamed out
// of process and an imported env assigned to a variable.

import { env as importedEnv } from "node:process";

const env = process.env;
// ruleid: gw-no-model-credential-env
const { ANTHROPIC_API_KEY } = env;
// ruleid: gw-no-model-credential-env
const hasToken = "CLAUDE_CODE_OAUTH_TOKEN" in env;
// ruleid: gw-no-model-credential-env
const baseUrl = env!.ANTHROPIC_BASE_URL;

export function loadConfig(source: NodeJS.ProcessEnv = process.env) {
  // ruleid: gw-no-model-credential-env
  const { CLAUDE_CODE_OAUTH_TOKEN: token } = source;
  return token;
}

const { env: processEnv } = process;
// ruleid: gw-no-model-credential-env
const configDir = processEnv.CLAUDE_CONFIG_DIR;
// ruleid: gw-no-model-credential-env
const model = importedEnv.ANTHROPIC_MODEL;

export { ANTHROPIC_API_KEY, baseUrl, configDir, hasToken, model };
