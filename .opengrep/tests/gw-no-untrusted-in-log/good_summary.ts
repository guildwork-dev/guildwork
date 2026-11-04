// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// The summary of an Untrusted value, its origin and hash, other values and
// other receivers are not reported.

import type { Untrusted } from "@guildwork/contracts";
import { type Logger, untrustedSummary } from "@guildwork/core";

declare const metrics: { info(name: string, fields: object): void };

export function handle(log: Logger, body: Untrusted<string>, plain: string): void {
  // ok: gw-no-untrusted-in-log
  log.info("review.body_received", { body: untrustedSummary(body) });
  // ok: gw-no-untrusted-in-log
  log.info("review.body_received", { origin: body.origin, sha256: body.sha256 });
  // ok: gw-no-untrusted-in-log
  log.info("review.plain", { plain });
  // ok: gw-no-untrusted-in-log
  log.info("review.sanitized", { sanitized: body.sanitized });
  // ok: gw-no-untrusted-in-log
  metrics.info("review.body", { body });
}
