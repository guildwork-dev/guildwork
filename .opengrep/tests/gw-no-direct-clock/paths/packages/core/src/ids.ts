// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Every other module gets the time from a Clock.

// ruleid: gw-no-direct-clock
const value = Date.now();

export { value };
