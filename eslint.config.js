// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors

// ESLint runs only the five type-aware rules of FE-002. Biome does formatting and
// all other lint rules; no style rule belongs here.

import { defineConfig, globalIgnores } from "eslint/config";
import tseslint from "typescript-eslint";

/** The only rules ESLint enforces (FE-002). */
export const TYPE_AWARE_RULES = {
  "@typescript-eslint/no-floating-promises": "error",
  "@typescript-eslint/no-misused-promises": "error",
  "@typescript-eslint/switch-exhaustiveness-check": "error",
  "@typescript-eslint/await-thenable": "error",
  "@typescript-eslint/require-await": "error",
};

export default defineConfig(
  // Fixtures belong to no TypeScript project; .opengrep/tests/ holds Opengrep rule tests.
  globalIgnores([
    "**/dist/",
    "**/coverage/",
    ".tools/",
    ".reports/",
    "tools/fixtures/",
    ".opengrep/tests/",
  ]),
  {
    files: ["**/*.ts", "**/*.tsx", "**/*.mts", "**/*.cts"],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      "@typescript-eslint": tseslint.plugin,
    },
    linterOptions: {
      reportUnusedDisableDirectives: "error",
    },
    rules: TYPE_AWARE_RULES,
  },
);
