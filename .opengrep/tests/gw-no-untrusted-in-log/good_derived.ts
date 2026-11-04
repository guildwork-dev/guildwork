// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Values derived only from the summary, origin or hash are not reported.

import type { Untrusted } from "@guildwork/contracts";
import { type Logger, untrustedSummary } from "@guildwork/core";

export class Reviewer {
  constructor(private readonly logger: Logger) {}

  run(body: Untrusted<string>): void {
    const origin = body.origin;
    // ok: gw-no-untrusted-in-log
    this.logger.info("review.origin", { origin });
    const summary = untrustedSummary(body);
    // ok: gw-no-untrusted-in-log
    this.logger.child({ run: "r1" }).info("review.body", { summary });
    // ok: gw-no-untrusted-in-log
    this.logger.info("review.size", { bytes: body.value.length });
  }
}
