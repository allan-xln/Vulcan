import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { InfrastructureView, UnifiedTimelineView } from "@/components/platform-expansion";

const props = {
  apiUrl: "http://api.test",
  tenantId: "00000000-0000-0000-0000-000000000301",
  token: "test-token"
};

function response(payload: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    })
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.history.replaceState({}, "", "/");
});

describe("InfrastructureView", () => {
  it("renders real platform data and explains the health score", async () => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/infrastructure/overview")) {
        return response({
          tenantId: props.tenantId,
          dataOrigin: "real",
          generatedAt: "2026-07-23T12:00:00Z",
          sites: 1,
          networks: 1,
          assets: 2,
          onlineAssets: 1,
          degradedAssets: 1,
          offlineAssets: 0,
          unknownAssets: 0,
          openIncidents: 1,
          eventsLast24h: 32,
          pendingDiscoveries: 0,
          healthScore: 83,
          scoreComponents: [{
            key: "availability",
            label: "Disponibilidade dos ativos",
            value: 0.75,
            maxPoints: 50,
            points: 37.5,
            formula: "(online + 0,5 × degradados) ÷ ativos monitorados × 50"
          }]
        });
      }
      if (url.endsWith("/infrastructure/sites")) {
        return response([{ id: "site-1", code: "SJP", name: "Unidade SJP", description: null, timezone: "America/Sao_Paulo", status: "active", tags: [], dataOrigin: "real" }]);
      }
      if (url.endsWith("/infrastructure/networks")) {
        return response([{ id: "network-1", siteId: "site-1", siteName: "Unidade SJP", name: "Corporativa", networkCidr: "192.168.10.0/24", gateway: "192.168.10.1", vlanId: 10, discoveryAllowed: false, status: "active", dataOrigin: "real" }]);
      }
      if (url.endsWith("/infrastructure/assets")) {
        return response([{ id: "asset-1", siteId: "site-1", siteName: "Unidade SJP", networkId: "network-1", networkName: "Corporativa", assetType: "server", name: "Servidor ERP", hostname: "SRV-ERP-01", manufacturer: "Dell", model: "R650", ipAddress: "192.168.10.20", status: "online", criticality: "critical", lastSeenAt: "2026-07-23T12:00:00Z", dataOrigin: "real" }]);
      }
      if (url.includes("/infrastructure/discovery/policies") || url.includes("/infrastructure/discovery/runs")) {
        return response([]);
      }
      if (url.endsWith("/infrastructure/integrations/catalog")) {
        return response([]);
      }
      if (url.endsWith("/incidents")) {
        return response([]);
      }
      if (url.endsWith("/healthz")) {
        return response({ status: "ok", service: "vulcan-api", timestamp: "2026-07-23T12:00:00Z", dataOrigin: "real", checks: [] });
      }
      if (url.endsWith("/version")) {
        return response({ product: "Vulcan", service: "vulcan-api", version: "0.2.0", commit: "test", build: "test", eventSchemaVersion: "2026-07-vulcan-event.v1" });
      }
      return response({});
    }));

    render(<InfrastructureView {...props} />);

    expect(await screen.findByText("Saúde transparente")).toBeInTheDocument();
    expect(screen.getByText("83")).toBeInTheDocument();
    expect(screen.getByText("Disponibilidade dos ativos")).toBeInTheDocument();
    expect(screen.getAllByText("Real").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: "Ativos e redes" }));
    expect(await screen.findByText("Servidor ERP")).toBeInTheDocument();
    expect(screen.getByText(/SRV-ERP-01/)).toBeInTheDocument();
    expect(window.location.search).toContain("infra=inventory");
  });
});

describe("UnifiedTimelineView", () => {
  it("renders a friendly canonical event and keeps technical data expandable", async () => {
    const event = {
      eventId: "event-1",
      siteId: null,
      assetId: null,
      agentId: null,
      source: "vulcan-agent",
      sourceType: "endpoint",
      eventType: "network.disconnect",
      category: "network",
      severity: "warning",
      occurredAt: "2026-07-23T12:00:00Z",
      receivedAt: "2026-07-23T12:00:01Z",
      clockDriftMs: 1000,
      offlineBuffered: false,
      actor: { username: "domain\\allan" },
      device: { hostname: "ERS-SJP-055" },
      context: {},
      metrics: {},
      message: "A estação perdeu conectividade com a rede corporativa.",
      technicalMessage: "Interface carrier changed to down.",
      correlationId: "incident-1",
      confidence: 0.91,
      privacyClassification: "operational",
      dataOrigin: "real"
    };

    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/timeline?")) {
        return response({ items: [event], nextCursor: null, hasMore: false, dataOrigin: "real" });
      }
      if (url.endsWith("/realtime/events")) {
        return Promise.resolve(new Response("", { status: 200, headers: { "Content-Type": "text/event-stream" } }));
      }
      return response({});
    }));

    render(<UnifiedTimelineView {...props} />);

    expect(await screen.findByText("A estação perdeu conectividade com a rede corporativa.")).toBeInTheDocument();
    expect(screen.getByText("ERS-SJP-055")).toBeInTheDocument();
    expect(screen.getByText("91%")).toBeInTheDocument();
    expect(screen.getByText("Detalhes técnicos e contexto")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Tempo real conectado")).toBeInTheDocument());
  });
});
