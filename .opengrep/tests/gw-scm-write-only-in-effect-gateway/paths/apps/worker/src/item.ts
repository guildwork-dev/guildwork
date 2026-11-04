// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// The worker has no write access to an SCM.

// ruleid: gw-scm-write-only-in-effect-gateway
import { push } from "../../../plugins/github/src/write/push.js";

export { push };
