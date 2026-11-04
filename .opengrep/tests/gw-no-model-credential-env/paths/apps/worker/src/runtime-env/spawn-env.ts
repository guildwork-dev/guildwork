// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// The child environment of the harness as ADR-57 describes it: built from an
// allowlist, the token read from the host file. Not reported.

import { spawn } from "node:child_process";

declare function readTokenFile(): string;

export function startHarness(path: string): void {
  // ok: gw-no-model-credential-env
  const env: NodeJS.ProcessEnv = { PATH: path };
  // ok: gw-no-model-credential-env
  env.CLAUDE_CODE_OAUTH_TOKEN = readTokenFile();
  // ok: gw-no-model-credential-env
  spawn("claude", ["-p"], { env });
}
