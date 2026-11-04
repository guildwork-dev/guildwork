// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// env taken out of process first, then read.

const { env } = process;

// ruleid: gw-no-model-credential-env
const apiKey = env.ANTHROPIC_API_KEY;
// ruleid: gw-no-model-credential-env
const token = env["CLAUDE_CODE_OAUTH_TOKEN"];
// ruleid: gw-no-model-credential-env
const { ANTHROPIC_BASE_URL } = env;

export { ANTHROPIC_BASE_URL, apiKey, token };
