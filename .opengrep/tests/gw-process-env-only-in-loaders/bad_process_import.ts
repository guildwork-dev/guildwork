// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// The same through an import of node:process.

// ruleid: gw-process-env-only-in-loaders
import { env } from "node:process";
// ruleid: gw-process-env-only-in-loaders
import { env as processEnv } from "process";
import * as proc from "node:process";
import nodeProcess from "node:process";

// ruleid: gw-process-env-only-in-loaders
const level = proc.env.GUILDWORK_LOG_LEVEL;
// ruleid: gw-process-env-only-in-loaders
const home = nodeProcess.env.HOME;
// ruleid: gw-process-env-only-in-loaders
const { env: fromNamespace } = proc;

export { env, fromNamespace, home, level, processEnv };
