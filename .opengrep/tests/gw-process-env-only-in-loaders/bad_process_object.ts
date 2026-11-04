// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// The environment reached through other spellings of the process object, and
// env taken out of process.

// ruleid: gw-process-env-only-in-loaders
const viaBracket = process["env"];
// ruleid: gw-process-env-only-in-loaders
const viaGlobal = globalThis["process"].env;
// ruleid: gw-process-env-only-in-loaders
const viaRequire = require("node:process").env;
// ruleid: gw-process-env-only-in-loaders
const { env } = process;
// ruleid: gw-process-env-only-in-loaders
const { argv, env: renamed } = process;
// ruleid: gw-process-env-only-in-loaders
const {
  env: { HOME },
} = process;

export { argv, env, HOME, renamed, viaBracket, viaGlobal, viaRequire };
