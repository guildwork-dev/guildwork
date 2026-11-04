// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import config from "../../vitest.config.js";

function readCoverageFile(): unknown {
  return JSON.parse(readFileSync(new URL("../../quality/coverage.json", import.meta.url), "utf8"));
}

describe("toolchain/vitest-config", () => {
  it("coverage thresholds come from quality/coverage.json", () => {
    const file = readCoverageFile() as { global: object; areas: object };
    const coverage = config.test?.coverage as { thresholds?: unknown } | undefined;
    expect(coverage?.thresholds).toEqual({ ...file.global, ...file.areas });
  });

  it("keeps e2e tests out of the projects of make check", () => {
    const projects = (config.test?.projects ?? []) as {
      test?: { name?: string; exclude?: string[] };
    }[];
    for (const name of ["unit", "integration", "contract"]) {
      const project = projects.find((entry) => entry.test?.name === name);
      expect(project?.test?.exclude, name).toContain("**/*.e2e.test.ts");
    }
  });

  it("never retries a failed test", () => {
    expect(config.test?.retry).toBe(0);
  });
});
