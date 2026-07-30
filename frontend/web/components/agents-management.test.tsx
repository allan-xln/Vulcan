import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AgentsManagement } from "@/components/agents-management";

const agent = {
  id: "00000000-0000-0000-0000-000000000501",
  tenantId: "00000000-0000-0000-0000-000000000301",
  deviceId: "00000000-0000-0000-0000-000000000601",
  hostname: "ERS-DEV-01",
  profile: "workstation",
  operatingSystem: "Zorin OS 18",
  architecture: "amd64",
  agentVersion: "0.2.0",
  status: "online",
  policyRevision: 1,
  policyStatus: "applied",
  queueDepth: 0,
  lastSeenAt: new Date().toISOString(),
  lastIp: "127.0.0.1",
  siteId: null,
  siteName: null,
  owner: "Operador",
  department: "Operacional",
  modules: { inventory: "enabled", systemMetrics: "enabled" },
  lastError: null,
  createdAt: new Date().toISOString()
};

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

function installFetchMock() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    if (url.endsWith("/agent/v2/admin/agents")) return jsonResponse([agent]);
    if (url.endsWith("/agent/v2/admin/policies")) return jsonResponse([]);
    if (url.includes("/timeline?")) return jsonResponse({ items: [] });
    if (url.endsWith("/audit-logs")) return jsonResponse([]);
    if (url.endsWith("/agent/v2/admin/enrollment-tokens") && init?.method === "POST") {
      return jsonResponse({
        id: "00000000-0000-0000-0000-000000000701",
        tenantId: agent.tenantId,
        token: "vulcan_enroll_short_lived_test_value",
        tokenPrefix: "vulcan_enroll_sh",
        profile: "workstation",
        expiresAt: new Date(Date.now() + 3_600_000).toISOString(),
        maxUses: 1,
        warning: "O token bruto é exibido uma única vez."
      }, 201);
    }
    throw new Error(`Unexpected fetch: ${url}`);
  });
}

describe("AgentsManagement", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/");
  });

  it("renders real agent state without invasive capability claims", async () => {
    installFetchMock();
    render(
      <AgentsManagement
        apiUrl="http://localhost:3001"
        tenantId={agent.tenantId}
        token="test-token"
      />
    );

    expect(await screen.findByText("ERS-DEV-01")).toBeInTheDocument();
    expect(screen.getByText(/Sem shell remoto, captura de teclas/)).toBeInTheDocument();
    expect(screen.getByText("2 módulos · fila 0")).toBeInTheDocument();
  });

  it("creates a short-lived enrollment command only after an explicit action", async () => {
    installFetchMock();
    render(
      <AgentsManagement
        apiUrl="http://localhost:3001"
        tenantId={agent.tenantId}
        token="test-token"
      />
    );
    await screen.findByText("ERS-DEV-01");
    fireEvent.click(screen.getByRole("button", { name: "Instalação" }));
    expect(window.location.search).toContain("agent=installation");
    fireEvent.click(screen.getByRole("button", { name: /Gerar token/ }));

    await waitFor(() => {
      expect(screen.getByText("PowerShell elevado")).toBeInTheDocument();
    });
    expect(screen.getByText(/expira/i)).toBeInTheDocument();
    expect(screen.getByText(/ENROLLMENT_TOKEN="vulcan_enroll_short_lived_test_value"/)).toBeInTheDocument();
    expect(screen.getByText(/ALLOW_INSECURE_PRIVATE_NETWORK=true/)).toBeInTheDocument();
    expect(screen.getByText(/--allow-insecure-private-network/)).toBeInTheDocument();
    expect(screen.getByText(/systemctl --user enable --now vulcan-agent-user/)).toBeInTheDocument();
  });
});
