import { describe, expect, it } from "vitest";

import { topologyLayout } from "./topology-layout";
import type { TopologyLink, TopologyNode } from "./types";

const nodes: TopologyNode[] = [
  {
    id: "firewall-1",
    siteId: "site-1",
    siteName: "Matriz",
    name: "Firewall",
    assetType: "firewall",
    status: "online",
    criticality: "critical",
    source: "inventory",
    ipAddress: "192.0.2.1",
    lastSeenAt: "2026-07-30T12:00:00Z",
    details: {}
  },
  {
    id: "switch-1",
    siteId: "site-1",
    siteName: "Matriz",
    name: "Switch",
    assetType: "switch",
    status: "online",
    criticality: "high",
    source: "unifi",
    ipAddress: "192.0.2.2",
    lastSeenAt: "2026-07-30T12:00:00Z",
    details: {}
  }
];

const links: TopologyLink[] = [
  {
    id: "link-valid",
    sourceAssetId: "firewall-1",
    targetAssetId: "switch-1",
    relationshipType: "uplink",
    status: "active",
    confidence: 1,
    source: "inventory",
    observedAt: "2026-07-30T12:00:00Z",
    details: {}
  },
  {
    id: "link-orphan",
    sourceAssetId: "firewall-1",
    targetAssetId: "missing-node",
    relationshipType: "uplink",
    status: "active",
    confidence: 0.5,
    source: "inventory",
    observedAt: null,
    details: {}
  }
];

describe("topologyLayout", () => {
  it("positions only the supplied real nodes and never invents orphan links", () => {
    const result = topologyLayout(nodes, links, 800, 480);

    expect(result.nodes.map((node) => node.id)).toEqual(["firewall-1", "switch-1"]);
    expect(result.links.map((link) => link.id)).toEqual(["link-valid"]);
    expect(result.links[0]?.sourceNode.id).toBe("firewall-1");
    expect(result.links[0]?.targetNode.id).toBe("switch-1");
    for (const node of result.nodes) {
      expect(Number.isFinite(node.x)).toBe(true);
      expect(Number.isFinite(node.y)).toBe(true);
      expect(Number.isFinite(node.z)).toBe(true);
      expect(node.x).toBeGreaterThanOrEqual(64);
      expect(node.x).toBeLessThanOrEqual(736);
      expect(node.y).toBeGreaterThanOrEqual(52);
      expect(node.y).toBeLessThanOrEqual(428);
    }
  });
});
