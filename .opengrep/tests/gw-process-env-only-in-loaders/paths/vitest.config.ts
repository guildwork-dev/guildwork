// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// The Vitest configuration.

// ok: gw-process-env-only-in-loaders
const value = process.env.GUILDWORK_LOG_LEVEL;

export { value };
