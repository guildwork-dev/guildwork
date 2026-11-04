// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Other names through an alias, and checks on a child environment object.

export function buildChildEnv(parent: NodeJS.ProcessEnv = process.env) {
  const child: Record<string, string> = {};
  // ok: gw-no-model-credential-env
  child.ANTHROPIC_BASE_URL = "https://proxy.invalid";
  // ok: gw-no-model-credential-env
  const hasKey = "ANTHROPIC_API_KEY" in child;
  // ok: gw-no-model-credential-env
  return { path: parent.PATH, hasKey, home: "HOME" in process.env };
}
