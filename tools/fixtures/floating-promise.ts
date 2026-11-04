// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors

// Fixture with two floating promises that a linter must report (FE-002).
// `eslint .` ignores this directory; tools/toolchain/floating-promise.test.ts
// lints this file on purpose. Results are recorded in docs/quality/toolchain.md.

import { readFile } from "node:fs/promises";

async function loadLocal(): Promise<string> {
  await Promise.resolve();
  return "local";
}

export function startWork(): void {
  // Case 1: promise of a local async function, neither awaited nor handled.
  loadLocal();
  // Case 2: promise of a typed library function, neither awaited nor handled.
  readFile("package.json", "utf8");
}
