import { describe, expect, it } from "vitest";

import {
  readPathState,
  readUrlState,
  urlWithPath,
  urlWithState
} from "@/lib/url-state";

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

  it("restores modules and nested sections from real paths", () => {
    const routes = {
      dashboard: "/",
      infrastructure: "/infrastructure",
      agents: "/agents"
    } as const;

    expect(readPathState("/infrastructure/discovery", routes, "dashboard")).toBe(
      "infrastructure"
    );
    expect(readPathState("/agents/installation/", routes, "dashboard")).toBe(
      "agents"
    );
    expect(readPathState("/unknown", routes, "dashboard")).toBe("dashboard");
  });

  it("writes a real path without losing unrelated query state", () => {
    expect(
      urlWithPath(
        "http://vulcan.local/?tenant=ers&view=infrastructure",
        "/agents/installation",
        ["view"]
      )
    ).toBe("/agents/installation?tenant=ers");
  });
});
