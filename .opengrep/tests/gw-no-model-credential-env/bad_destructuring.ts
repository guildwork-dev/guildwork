// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Destructuring a model credential variable from the environment is reported.

// ruleid: gw-no-model-credential-env
const { ANTHROPIC_API_KEY } = process.env;
// ruleid: gw-no-model-credential-env
const { CLAUDE_CODE_OAUTH_TOKEN: token } = process.env;
// ruleid: gw-no-model-credential-env
const { HOME, ANTHROPIC_AUTH_TOKEN, PATH } = process.env;
// ruleid: gw-no-model-credential-env
let { CLAUDE_CONFIG_DIR } = process.env;
CLAUDE_CONFIG_DIR = "";
// ruleid: gw-no-model-credential-env
const { ANTHROPIC_BASE_URL = "" } = process.env;
// ruleid: gw-no-model-credential-env
const { CLAUDE_CODE_USE_BEDROCK: bedrock = "0" } = process.env;
let assigned: string | undefined;
// ruleid: gw-no-model-credential-env
({ ANTHROPIC_MODEL: assigned } = process.env);
// ruleid: gw-no-model-credential-env
const {
  env: { CLAUDE_CODE_OAUTH_TOKEN: nested },
} = process;
// ruleid: gw-no-model-credential-env
const { LANG, ANTHROPIC_SMALL_FAST_MODEL } = process.env;

export {
  ANTHROPIC_API_KEY,
  ANTHROPIC_AUTH_TOKEN,
  ANTHROPIC_BASE_URL,
  ANTHROPIC_SMALL_FAST_MODEL,
  CLAUDE_CONFIG_DIR,
  HOME,
  LANG,
  PATH,
  assigned,
  bedrock,
  nested,
  token,
};
