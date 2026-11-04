// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Bracket access with a literal name is reported.

// ruleid: gw-no-model-credential-env
const apiKey = process.env["ANTHROPIC_API_KEY"];
// ruleid: gw-no-model-credential-env
const token = process.env["CLAUDE_CODE_OAUTH_TOKEN"];
// ruleid: gw-no-model-credential-env
const model = process.env[`ANTHROPIC_MODEL`];
// ruleid: gw-no-model-credential-env
const bedrock = process.env?.["CLAUDE_CODE_USE_BEDROCK"];

export { apiKey, bedrock, model, token };
