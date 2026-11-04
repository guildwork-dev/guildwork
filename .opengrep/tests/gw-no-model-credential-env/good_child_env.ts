// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// The worker sets these names only as keys of the child process environment
// (ADR-57); other variables and names that merely contain the prefix are not
// this rule's concern.

declare function readTokenFile(): string;

// ok: gw-no-model-credential-env
const childEnv: Record<string, string> = { CLAUDE_CODE_OAUTH_TOKEN: readTokenFile() };
// ok: gw-no-model-credential-env
childEnv.ANTHROPIC_BASE_URL = "https://proxy.invalid";
// ok: gw-no-model-credential-env
childEnv["CLAUDE_CONFIG_DIR"] = "config-dir";
// ok: gw-no-model-credential-env
const home = process.env.HOME;
// ok: gw-no-model-credential-env
const notCredential = process.env.MY_ANTHROPIC_NOTE;
// ok: gw-no-model-credential-env
const { PATH } = process.env;
// ok: gw-no-model-credential-env
const fromChild = childEnv.CLAUDE_CODE_OAUTH_TOKEN;
// ok: gw-no-model-credential-env
const env: Record<string, string> = { CLAUDE_CODE_OAUTH_TOKEN: readTokenFile() };
// ok: gw-no-model-credential-env
env.ANTHROPIC_BASE_URL = "https://proxy.invalid";
// ok: gw-no-model-credential-env
const { LANG, ...rest } = process.env;

export { childEnv, env, fromChild, home, LANG, notCredential, PATH, rest };
