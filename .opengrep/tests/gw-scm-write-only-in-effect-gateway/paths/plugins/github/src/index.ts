// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// The main entry point of a plugin must not expose its write code.

// ruleid: gw-scm-write-only-in-effect-gateway
export * from "./write/index.js";
