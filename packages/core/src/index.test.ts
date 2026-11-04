// SPDX-License-Identifier: Apache-2.0
// SPDX-FileCopyrightText: The Guildwork Authors

import * as viaPackage from "@guildwork/core";
import { describe, expect, it } from "vitest";
import * as viaSource from "./index.js";

describe("core/index", () => {
  it("imports workspace source without build", () => {
    // The same module instance proves that the package name resolved to
    // src/index.ts through the @guildwork/source condition, not to dist/.
    expect(viaPackage).toBe(viaSource);
    expect(viaPackage.VERSION).toBe("0.0.0");
  });
});
