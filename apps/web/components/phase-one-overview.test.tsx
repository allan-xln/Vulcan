import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PhaseOneOverview } from "@/components/phase-one-overview";

vi.mock("swr", () => ({
  default: () => ({
    data: {
      status: "ok",
      phase: "phase-1"
    }
  })
}));

describe("PhaseOneOverview", () => {
  it("renders the phase title and health status", () => {
    render(<PhaseOneOverview />);

    expect(screen.getByText(/Phase 1 is a control-plane shell/i)).toBeInTheDocument();
    expect(screen.getByText(/Health endpoint: ok \(phase-1\)/i)).toBeInTheDocument();
  });
});
