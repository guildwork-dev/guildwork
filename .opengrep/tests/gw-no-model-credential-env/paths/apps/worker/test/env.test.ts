// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Tests do not read them either.

// ruleid: gw-no-model-credential-env
const token = process.env.CLAUDE_CODE_OAUTH_TOKEN;

export { token };
