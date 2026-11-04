// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Read paths of plugins, other packages and names that only contain "write"
// are not reported.

// ok: gw-scm-write-only-in-effect-gateway
import { listFiles } from "@guildwork/plugin-github";
// ok: gw-scm-write-only-in-effect-gateway
import { readFile } from "@guildwork/plugin-github/read";
// ok: gw-scm-write-only-in-effect-gateway
import { writeback } from "@guildwork/plugin-github/writeback";
// ok: gw-scm-write-only-in-effect-gateway
import { ok } from "@guildwork/core";
// ok: gw-scm-write-only-in-effect-gateway
import { writer } from "./writer.js";
// ok: gw-scm-write-only-in-effect-gateway
import { rewrite } from "./rewrite/index.js";
// ok: gw-scm-write-only-in-effect-gateway
import { writeFile } from "node:fs/promises";
// ok: gw-scm-write-only-in-effect-gateway
import { other } from "../../plugins/github/src/read/index.js";

export { listFiles, ok, other, readFile, rewrite, writeback, writeFile, writer };
