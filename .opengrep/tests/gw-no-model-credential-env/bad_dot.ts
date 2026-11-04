// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Dot access to a model credential variable is reported, read or written.

// ruleid: gw-no-model-credential-env
const apiKey = process.env.ANTHROPIC_API_KEY;
// ruleid: gw-no-model-credential-env
const token = process.env.CLAUDE_CODE_OAUTH_TOKEN;
// ruleid: gw-no-model-credential-env
const baseUrl = process.env?.ANTHROPIC_BASE_URL;
// ruleid: gw-no-model-credential-env
const configDir = globalThis.process.env.CLAUDE_CONFIG_DIR;
// ruleid: gw-no-model-credential-env
process.env.ANTHROPIC_AUTH_TOKEN = "placeholder";

export { apiKey, baseUrl, configDir, token };
