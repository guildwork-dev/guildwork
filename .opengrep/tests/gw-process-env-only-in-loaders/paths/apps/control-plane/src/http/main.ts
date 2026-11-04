// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Only src/main.ts is the entry point, not any main.ts.

// ruleid: gw-process-env-only-in-loaders
const value = process.env.GUILDWORK_LOG_LEVEL;

export { value };
