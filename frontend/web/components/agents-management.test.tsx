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
        apiUrl="/api"
        tenantId={agent.tenantId}
        token="test-token"
      />
    );
    await screen.findByText("ERS-DEV-01");
    fireEvent.click(screen.getByRole("button", { name: "Instalação" }));
    expect(window.location.pathname).toBe("/agents/installation");
    fireEvent.click(screen.getByRole("button", { name: /^Servidor / }));
    fireEvent.click(screen.getByRole("button", { name: /Gerar comando/ }));

    await waitFor(() => {
      expect(screen.getByText("Windows · PowerShell como administrador")).toBeInTheDocument();
    });
    expect(screen.getByText(/expira/i)).toBeInTheDocument();
    const powershellCommand = screen.getByText(/ENROLLMENT_TOKEN="vulcan_enroll_short_lived_test_value"/).textContent;
    expect(powershellCommand).toContain(`Invoke-WebRequest -UseBasicParsing -Uri '${window.location.origin}/agent-v2/VulcanAgent-Windows-x64.msi'`);
    expect(powershellCommand).toContain("Get-FileHash $Msi -Algorithm SHA256");
    expect(powershellCommand?.startsWith("& {\n$ErrorActionPreference = 'Stop'")).toBe(true);
    expect(powershellCommand).toContain(`VULCAN_SERVER="${window.location.origin}/api"`);
    expect(powershellCommand).toContain('AGENT_PROFILE="server"');
    expect(powershellCommand).toContain("ALLOW_INSECURE_PRIVATE_NETWORK=true");
    expect(powershellCommand).toContain("Remove-Item $Msi");
    expect(powershellCommand).toContain("Get-Service VulcanAgent");
    expect(powershellCommand?.endsWith("\n}")).toBe(true);
    expect(screen.queryByRole("link", { name: /MSI Windows/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /DEB Linux/i })).not.toBeInTheDocument();
  });

  it("discards a generated command when the profile changes", async () => {
    installFetchMock();
    render(<AgentsManagement apiUrl="/api" tenantId={agent.tenantId} token="test-token" />);
    await screen.findByText("ERS-DEV-01");
    fireEvent.click(screen.getByRole("button", { name: "Instalação" }));
    fireEvent.click(screen.getByRole("button", { name: /Gerar comando/ }));
    expect(await screen.findByText("Windows · PowerShell como administrador")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^Servidor / }));
    expect(screen.queryByText("Windows · PowerShell como administrador")).not.toBeInTheDocument();
  });
});
