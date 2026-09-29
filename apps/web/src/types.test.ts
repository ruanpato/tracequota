// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Ruan Pato

import { describe, it, expect } from "vitest";
import { deltaLabel, money, matchesSearch, formatDateTime } from "./types";
import type { Task, Delta } from "./types";
describe("honest quota and cost display", () => {
  it("uses en-US dates and UTC independently of browser defaults", () => {
    expect(formatDateTime("2026-09-28T08:00:00Z")).toBe(
      "Sep 28, 2026, 8:00:00 AM UTC",
    );
  });
  it("does not present a reset as negative consumption", () => {
    expect(deltaLabel({ reset_crossed: true, delta_pp: null } as Delta)).toBe(
      "Reset crossed",
    );
  });
  it("shows percentage points", () => {
    expect(deltaLabel({ reset_crossed: false, delta_pp: 9 } as Delta)).toBe(
      "+9 pp",
    );
  });
  it("distinguishes unpriced usage from zero cost", () => {
    expect(money(null)).toBe("Unknown");
    expect(money("0")).toBe("$0.00");
    expect(money("22.05")).toBe("$22.05");
    expect(money(0)).toBe("$0.00");
  });
  it("finds model and agent metadata without case sensitivity", () => {
    const t = {
      title: "Task",
      project: "repo",
      session_id: "s",
      models: { Sonnet: {} },
      agents: { Reviewer: {} },
    } as unknown as Task;
    expect(matchesSearch(t, "reviewer")).toBe(true);
    expect(matchesSearch(t, "opus")).toBe(false);
  });
});
