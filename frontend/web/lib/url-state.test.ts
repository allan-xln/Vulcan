import { describe, expect, it } from "vitest";

import { readUrlState, urlWithState } from "@/lib/url-state";

const views = ["dashboard", "infrastructure", "agents"] as const;

describe("URL state", () => {
  it("restores a valid view and rejects unknown values", () => {
    expect(readUrlState("?view=infrastructure", "view", views, "dashboard")).toBe(
      "infrastructure"
    );
    expect(readUrlState("?view=unknown", "view", views, "dashboard")).toBe(
      "dashboard"
    );
  });

  it("writes a deep link and removes the default value", () => {
    expect(
      urlWithState(
        "http://vulcan.local/?tenant=ers",
        "view",
        "infrastructure",
        "dashboard"
      )
    ).toBe("/?tenant=ers&view=infrastructure");
    expect(
      urlWithState(
        "http://vulcan.local/?tenant=ers&view=infrastructure",
        "view",
        "dashboard",
        "dashboard"
      )
    ).toBe("/?tenant=ers");
  });
});
