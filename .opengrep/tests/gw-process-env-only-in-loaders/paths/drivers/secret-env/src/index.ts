// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Loader modules of later tasks join the allowlist with the task that builds them (FE-063).

// ruleid: gw-process-env-only-in-loaders
const value = process.env.GUILDWORK_LOG_LEVEL;

export { value };
