// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// An env imported from node:process and assigned to another variable.

import { env } from "node:process";

const copy = env;
// ruleid: gw-no-model-credential-env
export const apiKey = copy.ANTHROPIC_API_KEY;
