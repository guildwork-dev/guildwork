// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors

// Keeps the measurement behind FE-002 true: ESLint must report both floating
// promises in tools/fixtures/floating-promise.ts. The Biome case records that its
// nursery rule misses the promise of a typed library call; if a Biome upgrade
// makes that case fail, revisit FE-002 (docs/quality/toolchain.md).

import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { ESLint } from "eslint";
import { describe, expect, it } from "vitest";

const ROOT = fileURLToPath(new URL("../../", import.meta.url));
const FIXTURE = "tools/fixtures/floating-promise.ts";
const LOCAL_PROMISE_LINE = 17;
const LIBRARY_PROMISE_LINE = 19;
// Type-aware ESLint cold start exceeds the 5 s default under load with coverage on.
const ESLINT_COLD_START = { timeout: 60_000 };

describe("toolchain/floating-promise", () => {
  it("eslint reports both floating promises in the fixture", ESLINT_COLD_START, async () => {
    const eslint = new ESLint({ cwd: ROOT, ignore: false });
    const [result] = await eslint.lintFiles([FIXTURE]);
    const lines = (result?.messages ?? [])
      .filter((message) => message.ruleId === "@typescript-eslint/no-floating-promises")
      .map((message) => message.line);
    expect(lines).toEqual([LOCAL_PROMISE_LINE, LIBRARY_PROMISE_LINE]);
  });

  it("biome nursery rule misses the promise of a typed library call", () => {
    const biome = createRequire(import.meta.url).resolve("@biomejs/biome/bin/biome");
    const run = spawnSync(
      process.execPath,
      [biome, "lint", "--only=nursery/noFloatingPromises", "--reporter=github", FIXTURE],
      { cwd: ROOT, encoding: "utf8" },
    );
    expect(run.status).toBe(0);
    const lines = [
      ...run.stdout.matchAll(/title=lint\/nursery\/noFloatingPromises,.*?,line=(\d+),/g),
    ].map((match) => Number(match[1]));
    expect(lines).toEqual([LOCAL_PROMISE_LINE]);
  });
});
