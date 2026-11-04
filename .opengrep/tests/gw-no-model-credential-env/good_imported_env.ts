// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// A child environment object named env that comes from another module is not
// the process environment.

import { env } from "./child-env.js";

declare const token: string;

// ok: gw-no-model-credential-env
env.ANTHROPIC_API_KEY = token;
// ok: gw-no-model-credential-env
const baseUrl = env.ANTHROPIC_BASE_URL;

export { baseUrl };
