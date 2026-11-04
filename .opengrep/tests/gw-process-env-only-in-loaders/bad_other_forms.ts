// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// A presence check and a non-null assertion are accesses too.

// ruleid: gw-process-env-only-in-loaders
export const testMode = "GW_TEST_MODE" in process.env;
// ruleid: gw-process-env-only-in-loaders
export const level = process.env!.GUILDWORK_LOG_LEVEL;
