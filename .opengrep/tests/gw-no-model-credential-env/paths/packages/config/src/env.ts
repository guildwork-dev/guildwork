// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// The rule has no allowlist: not even the configuration loader reads these names.

// ruleid: gw-no-model-credential-env
const apiKey = process.env.ANTHROPIC_API_KEY;
// ruleid: gw-no-model-credential-env
const { CLAUDE_CODE_OAUTH_TOKEN = "" } = process.env;
let assigned: string | undefined;
// ruleid: gw-no-model-credential-env
({ ANTHROPIC_AUTH_TOKEN: assigned } = process.env);

export { apiKey, assigned, CLAUDE_CODE_OAUTH_TOKEN };
