// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// The module that builds the child environment may read process.env, but never
// a model credential from it, not even through an alias.

export function buildChildEnv(token: string, parent: NodeJS.ProcessEnv = process.env) {
  // ok: gw-no-model-credential-env
  const child: Record<string, string | undefined> = { PATH: parent.PATH };
  // ok: gw-no-model-credential-env
  child.CLAUDE_CODE_OAUTH_TOKEN = token;
  // ruleid: gw-no-model-credential-env
  child.ANTHROPIC_BASE_URL = parent.ANTHROPIC_BASE_URL;
  const raw = process.env;
  // ruleid: gw-no-model-credential-env
  child.CLAUDE_CONFIG_DIR = raw.CLAUDE_CONFIG_DIR;
  return child;
}
