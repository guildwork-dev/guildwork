// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// The environment reached through other spellings of the process object.

// ruleid: gw-no-model-credential-env
const viaBracket = process["env"].ANTHROPIC_API_KEY;
// ruleid: gw-no-model-credential-env
const viaGlobal = globalThis["process"].env.CLAUDE_CODE_OAUTH_TOKEN;
// ruleid: gw-no-model-credential-env
const viaRequire = require("node:process").env.ANTHROPIC_AUTH_TOKEN;

export { viaBracket, viaGlobal, viaRequire };
