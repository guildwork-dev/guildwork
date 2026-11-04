// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// A presence check and a non-null assertion are reads too.

// ruleid: gw-no-model-credential-env
export const hasKey = "ANTHROPIC_API_KEY" in process.env;
// ruleid: gw-no-model-credential-env
export const token = process.env!.CLAUDE_CODE_OAUTH_TOKEN;
