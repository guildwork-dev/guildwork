// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// An alias of process.env: a variable, a parameter default or a parameter
// typed NodeJS.ProcessEnv. Loader modules may read process.env, so this rule is
// the only guard there.

export function buildChildEnv(parent: NodeJS.ProcessEnv = process.env) {
  // ruleid: gw-no-model-credential-env
  return { key: parent.ANTHROPIC_API_KEY };
}

export function fromParameter(source: NodeJS.ProcessEnv) {
  // ruleid: gw-no-model-credential-env
  return source["CLAUDE_CODE_OAUTH_TOKEN"];
}

export class Loader {
  loadEnv(env = process.env) {
    // ruleid: gw-no-model-credential-env
    return env.ANTHROPIC_AUTH_TOKEN;
  }
}

const raw = process.env;
// ruleid: gw-no-model-credential-env
export const token = raw.CLAUDE_CODE_OAUTH_TOKEN;
