// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// The rule has no allowlist: tests do not log untrusted content either.

import type { Untrusted } from "@guildwork/contracts";
import type { Logger } from "@guildwork/core";

export function check(log: Logger, input: Untrusted<string>): void {
  // ruleid: gw-no-untrusted-in-log
  log.info("test.input", { input });
}
