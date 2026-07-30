import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation
} from "d3-force";
import { TopologyLink, TopologyNode } from "./types";

export type PositionedNode = TopologyNode & {
  x: number;
  y: number;
  z: number;
};

export type PositionedLink = TopologyLink & {
  sourceNode: PositionedNode;
  targetNode: PositionedNode;
};

const TYPE_DEPTH: Record<string, number> = {
  firewall: 1.8,
  gateway: 1.5,
  vpn_tunnel: 1.2,
  wan_link: 1,
  switch: 0.6,
  access_point: 0.25,
  proxmox_cluster: 0.8,
  virtualization_host: 0.35,
  server: 0,
  virtual_machine: -0.45,
  printer: -0.8
};

export function topologyLayout(
  nodes: TopologyNode[],
  links: TopologyLink[],
  width = 1000,
  height = 600
) {
  const positioned: PositionedNode[] = nodes.map((node, index) => ({
    ...node,
    x: width / 2 + Math.cos(index) * 60,
    y: height / 2 + Math.sin(index) * 60,
    z: TYPE_DEPTH[node.assetType] ?? -0.2
  }));
  const ids = new Set(positioned.map((node) => node.id));
  const validLinks = links
    .filter((link) => ids.has(link.sourceAssetId) && ids.has(link.targetAssetId))
    .map((link) => ({
      ...link,
      source: link.sourceAssetId,
      target: link.targetAssetId
    }));
  const simulation = forceSimulation(positioned)
    .force(
      "link",
      forceLink<PositionedNode, (typeof validLinks)[number]>(validLinks)
        .id((node) => node.id)
        .distance((link) => (link.relationshipType === "hosts" ? 78 : 112))
        .strength(0.55)
    )
    .force("charge", forceManyBody().strength(-330))
    .force("collide", forceCollide<PositionedNode>().radius(30))
    .force("center", forceCenter(width / 2, height / 2))
    .stop();

  for (let tick = 0; tick < 170; tick += 1) simulation.tick();

  const horizontalSafeArea = 64;
  const verticalSafeArea = 52;
  for (const node of positioned) {
    node.x = Math.min(width - horizontalSafeArea, Math.max(horizontalSafeArea, node.x));
    node.y = Math.min(height - verticalSafeArea, Math.max(verticalSafeArea, node.y));
  }

  const nodeById = new Map(positioned.map((node) => [node.id, node]));
  const positionedLinks: PositionedLink[] = links.flatMap((link) => {
    const source = nodeById.get(link.sourceAssetId);
    const target = nodeById.get(link.targetAssetId);
    return source && target ? [{ ...link, sourceNode: source, targetNode: target }] : [];
  });
  return { nodes: positioned, links: positionedLinks };
}
