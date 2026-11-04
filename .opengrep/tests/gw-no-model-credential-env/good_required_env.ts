// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// The same for an env object required from another module.

const { env } = require("./settings.js");

// ok: gw-no-model-credential-env
const configDir = env.CLAUDE_CONFIG_DIR;

export { configDir };
