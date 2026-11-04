// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors
// Relative imports of a plugin's src/write/ directory are reported: across
// packages through the plugins/ directory, and inside a plugin from its other
// source files.

// ruleid: gw-scm-write-only-in-effect-gateway
import { addComment } from "../../plugins/github/src/write/index.js";
// ruleid: gw-scm-write-only-in-effect-gateway
import { push } from "../../../plugins/gitlab/src/write/push.js";
// ruleid: gw-scm-write-only-in-effect-gateway
import { submitReview } from "./write/index.js";
// ruleid: gw-scm-write-only-in-effect-gateway
import { setLabels } from "../write/labels.js";
// ruleid: gw-scm-write-only-in-effect-gateway
import * as write from "../../write";

export { addComment, push, setLabels, submitReview, write };
