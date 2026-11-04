// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// The tests of a plugin may import its write code.

// ok: gw-scm-write-only-in-effect-gateway
import { addComment } from "../src/write/index.js";
// ok: gw-scm-write-only-in-effect-gateway
import { push } from "@guildwork/plugin-github/write";

export { addComment, push };
