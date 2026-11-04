// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// A service controller proposes effects and never writes itself.

// ruleid: gw-scm-write-only-in-effect-gateway
import { submitReview } from "@guildwork/plugin-github/write";

export { submitReview };
