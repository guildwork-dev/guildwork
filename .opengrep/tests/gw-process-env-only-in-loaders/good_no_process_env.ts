// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Environment objects that are not process.env, and other members of process,
// are not reported.

import { argv } from "node:process";

// ok: gw-process-env-only-in-loaders
const childEnv: Record<string, string> = { PATH: "/usr/bin" };
// ok: gw-process-env-only-in-loaders
childEnv.HOME = "/home/worker";
// ok: gw-process-env-only-in-loaders
const fromChild = childEnv.PATH;
// ok: gw-process-env-only-in-loaders
const platform = process.platform;
// ok: gw-process-env-only-in-loaders
const text = "process.env.HOME";
// ok: gw-process-env-only-in-loaders
const settings = { env: { HOME: "x" } };
// ok: gw-process-env-only-in-loaders
const nested = settings.env.HOME;

// ok: gw-process-env-only-in-loaders
const { argv: args, platform: os } = process;

export { args, argv, childEnv, fromChild, nested, os, platform, text };
