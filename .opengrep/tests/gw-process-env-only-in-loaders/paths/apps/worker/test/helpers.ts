// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Files below a test directory.

// ok: gw-process-env-only-in-loaders
const value = process.env.GUILDWORK_LOG_LEVEL;

export { value };
