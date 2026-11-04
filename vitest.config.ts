// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors

import { readFileSync } from "node:fs";
import { defaultServerConditions } from "vite";
import { configDefaults, defineConfig } from "vitest/config";

/** Workspace packages export their sources under this condition (FE-001). */
export const SOURCE_CONDITION = "@guildwork/source";

interface CoverageValues {
  lines: number;
  functions: number;
  branches: number;
  statements: number;
}

interface CoverageFile {
  global: CoverageValues;
  areas: Record<string, CoverageValues>;
}

/** Reads the named coverage thresholds from quality/coverage.json, the only place they are set. */
export function coverageThresholds(): CoverageValues & Record<string, CoverageValues | number> {
  const file = JSON.parse(
    readFileSync(new URL("./quality/coverage.json", import.meta.url), "utf8"),
  ) as CoverageFile;
  return { ...file.global, ...file.areas };
}

const PACKAGE_DIRS = "{apps,packages,plugins,drivers,services,eval}";

/** e2e tests run only in their own project, never in make check (FE-003). */
const E2E_TESTS = "**/*.e2e.test.ts";
const NOT_E2E = [...configDefaults.exclude, E2E_TESTS];

export default defineConfig({
  // Tests run in the Node.js (server) environment of Vite, so the condition goes into
  // ssr.resolve.conditions; resolve.conditions alone does not reach it (measured, see
  // docs/quality/toolchain.md). The list replaces Vite's defaults, so they are kept.
  ssr: {
    resolve: {
      conditions: [SOURCE_CONDITION, ...defaultServerConditions],
    },
  },
  test: {
    retry: 0,
    coverage: {
      provider: "v8",
      include: [`${PACKAGE_DIRS}/**/src/**/*.ts`],
      exclude: ["**/*.test.ts"],
      thresholds: coverageThresholds(),
    },
    projects: [
      {
        extends: true,
        test: {
          name: "unit",
          include: [`${PACKAGE_DIRS}/**/src/**/*.test.ts`, "tools/toolchain/**/*.test.ts"],
          exclude: NOT_E2E,
        },
      },
      {
        extends: true,
        test: {
          name: "integration",
          include: [`${PACKAGE_DIRS}/**/test/integration/**/*.int.test.ts`],
          exclude: NOT_E2E,
          pool: "forks",
        },
      },
      {
        extends: true,
        test: {
          name: "contract",
          include: [`${PACKAGE_DIRS}/**/test/contract/**/*.contract.test.ts`],
          exclude: NOT_E2E,
        },
      },
      {
        extends: true,
        test: {
          name: "e2e",
          include: [E2E_TESTS],
          exclude: ["**/node_modules/**"],
        },
      },
    ],
  },
});
