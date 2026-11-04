// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Every access to process.env outside a loader module is reported.

// ruleid: gw-process-env-only-in-loaders
const level = process.env.GUILDWORK_LOG_LEVEL;
// ruleid: gw-process-env-only-in-loaders
const config = process.env["GUILDWORK_CONFIG"];
// ruleid: gw-process-env-only-in-loaders
const { HOME } = process.env;
// ruleid: gw-process-env-only-in-loaders
const all = process.env;
// ruleid: gw-process-env-only-in-loaders
const optional = process.env?.GW_TEST_MODE;
// ruleid: gw-process-env-only-in-loaders
const global = globalThis.process.env.PATH;
// ruleid: gw-process-env-only-in-loaders
process.env.GW_TEST_MODE = "1";

export { all, config, global, HOME, level, optional };
