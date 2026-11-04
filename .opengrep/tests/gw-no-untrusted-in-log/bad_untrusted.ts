// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// A value of type Untrusted, or its field value, passed to a logger is reported
// (FE-014). The rule sees the declared type of a variable or parameter.

import type { Untrusted } from "@guildwork/contracts";
import type { Logger } from "@guildwork/core";

export function handle(
  log: Logger,
  ctx: { log: Logger },
  body: Untrusted<string>,
  title: Untrusted,
): void {
  // ruleid: gw-no-untrusted-in-log
  log.info("review.body_received", { body });
  // ruleid: gw-no-untrusted-in-log
  ctx.log.warn("review.body_received", { text: body.value });
  // ruleid: gw-no-untrusted-in-log
  log.error("review.title_received", { nested: { list: [title.value] } });
  // ruleid: gw-no-untrusted-in-log
  log.debug(`review.${body.value}`);
  // ruleid: gw-no-untrusted-in-log
  const childLog = log.child({ title });
  const copy: Untrusted<string> = body;
  // ruleid: gw-no-untrusted-in-log
  childLog.trace("review.copy", { copy });
  // ruleid: gw-no-untrusted-in-log
  ctx.log.fatal("review.copy", { copy: copy.value });
}
