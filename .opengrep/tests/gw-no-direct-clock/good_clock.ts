// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Dates from a given value and time from the Clock are not reported.

interface Clock {
  now(): number;
}
declare const clock: Clock;

// ok: gw-no-direct-clock
const epoch = new Date(0);
// ok: gw-no-direct-clock
const parsed = new Date("2026-11-01T00:00:00.000Z");
// ok: gw-no-direct-clock
const fromClock = new Date(clock.now());
// ok: gw-no-direct-clock
const millis = Date.parse("2026-11-01T00:00:00.000Z");
// ok: gw-no-direct-clock
const utc = Date.UTC(2026, 10, 1);

export { epoch, fromClock, millis, parsed, utc };
