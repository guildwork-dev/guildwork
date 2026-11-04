// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// The executors of the Effect Gateway may import the write subpath.

// ok: gw-scm-write-only-in-effect-gateway
import { addComment } from "@guildwork/plugin-github/write";

export { addComment };
