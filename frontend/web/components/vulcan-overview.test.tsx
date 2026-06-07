import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { VulcanOverview } from "@/components/vulcan-overview";

vi.mock("swr", () => ({
  default: () => ({
    data: {
      status: "ok",
      product: "vulcan"
    }
  })
}));

vi.mock("recharts", () => ({
  Bar: () => null,
  BarChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CartesianGrid: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null
}));

describe("VulcanOverview", () => {
  it("renders the product title and health status", () => {
    render(<VulcanOverview />);

    expect(screen.getByText(/Vulcan transforma fatos operacionais/i)).toBeInTheDocument();
    expect(screen.getByText(/Endpoint de saúde: ok \(vulcan\)/i)).toBeInTheDocument();
  });
});
