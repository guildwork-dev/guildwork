// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Writing credential names into an object typed NodeJS.ProcessEnv builds the
// child environment (ADR-57) and is not reported.

declare function readTokenFile(): string;

export function fillChildEnv(out: NodeJS.ProcessEnv): NodeJS.ProcessEnv {
  // ok: gw-no-model-credential-env
  out.CLAUDE_CODE_OAUTH_TOKEN = readTokenFile();
  // ok: gw-no-model-credential-env
  out["CLAUDE_CONFIG_DIR"] = "config-dir";
  // ok: gw-no-model-credential-env
  delete out.ANTHROPIC_API_KEY;
  return out;
}
