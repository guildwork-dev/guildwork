// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Values derived from an Untrusted value, and loggers reached through child()
// or a class field, are reported.

import type { Untrusted } from "@guildwork/contracts";
import type { Logger } from "@guildwork/core";

export class Reviewer {
  constructor(private readonly logger: Logger) {}

  run(body: Untrusted<string>): void {
    // ruleid: gw-no-untrusted-in-log
    this.logger.child({ run: "r1" }).info("review.body", { body: body.value });
    const text = body.value;
    // ruleid: gw-no-untrusted-in-log
    this.logger.info("review.body", { text });
    const quoted = `> ${text}`;
    // ruleid: gw-no-untrusted-in-log
    this.logger.warn("review.quote", { quoted });
  }
}
