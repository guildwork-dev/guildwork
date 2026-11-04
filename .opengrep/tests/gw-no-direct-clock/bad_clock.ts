// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Reading the system clock directly is reported (FE-013).

// ruleid: gw-no-direct-clock
const millis = Date.now();
// ruleid: gw-no-direct-clock
const now = new Date();
// ruleid: gw-no-direct-clock
const started = performance.now();

export { millis, now, started };
