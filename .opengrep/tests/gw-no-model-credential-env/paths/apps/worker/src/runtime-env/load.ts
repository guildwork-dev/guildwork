// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Destructuring from an alias of process.env, in the module that may read
// process.env.

export function loadConfig(source: NodeJS.ProcessEnv = process.env) {
  // ruleid: gw-no-model-credential-env
  const { CLAUDE_CODE_OAUTH_TOKEN: token } = source;
  const env = process.env;
  // ruleid: gw-no-model-credential-env
  const { ANTHROPIC_API_KEY } = env;
  return { ANTHROPIC_API_KEY, token };
}
