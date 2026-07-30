"use client";

import { useMemo } from "react";
import { topologyLayout } from "./topology-layout";
import { TopologyLink, TopologyNode } from "./types";

const STATUS_COLORS: Record<string, string> = {
  online: "#39d98a",
  degraded: "#ffb347",
  offline: "#ff4d5f",
  unknown: "#69707d",
  maintenance: "#44b7ff"
};

export function TopologyFallback({
  nodes,
  links,
  onSelect
}: {
  nodes: TopologyNode[];
  links: TopologyLink[];
  onSelect?: (node: TopologyNode) => void;
}) {
  const graph = useMemo(() => topologyLayout(nodes, links, 1000, 560), [links, nodes]);

  if (!nodes.length) {
    return (
      <div className="command-empty">
        <span className="command-empty-mark" />
        <strong>Topologia sem relações coletadas</strong>
        <span>Cadastre relacionamentos reais ou sincronize uma integração compatível.</span>
      </div>
    );
  }

  return (
    <svg
      className="h-full w-full"
      viewBox="0 0 1000 560"
      role="img"
      aria-label={`Topologia 2D com ${nodes.length} ativos e ${graph.links.length} relações reais`}
    >
      <defs>
        <linearGradient id="vulcan-link" x1="0" x2="1">
          <stop offset="0" stopColor="#ff7a1a" stopOpacity=".14" />
          <stop offset=".5" stopColor="#64748b" stopOpacity=".38" />
          <stop offset="1" stopColor="#44b7ff" stopOpacity=".14" />
        </linearGradient>
      </defs>
      <g>
        {graph.links.map((link) => (
          <line
            key={link.id}
            x1={link.sourceNode.x}
            y1={link.sourceNode.y}
            x2={link.targetNode.x}
            y2={link.targetNode.y}
            stroke="url(#vulcan-link)"
            strokeWidth={link.relationshipType === "uplink" ? 2.5 : 1.2}
          />
        ))}
      </g>
      <g>
        {graph.nodes.map((node) => {
          const color = STATUS_COLORS[node.status] ?? STATUS_COLORS.unknown;
          return (
            <g
              key={node.id}
              transform={`translate(${node.x} ${node.y})`}
              role="button"
              tabIndex={0}
              aria-label={`${node.name}, ${node.assetType}, ${node.status}`}
              onClick={() => onSelect?.(node)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") onSelect?.(node);
              }}
              className="cursor-pointer outline-none"
            >
              <circle r="15" fill="#0b0d11" stroke={color} strokeWidth="2" />
              <circle r="4" fill={color} />
              <text y="29" textAnchor="middle" fill="#b8bec8" fontSize="10">
                {node.name.slice(0, 22)}
              </text>
            </g>
          );
        })}
      </g>
    </svg>
  );
}
