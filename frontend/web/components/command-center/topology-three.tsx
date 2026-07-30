"use client";

import { Line } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef } from "react";
import type { Group } from "three";
import { topologyLayout } from "./topology-layout";
import { QUALITY_CAPABILITIES } from "./config";
import { RuntimeMetrics, TopologyLink, TopologyNode } from "./types";

const STATUS_COLORS: Record<string, string> = {
  online: "#39d98a",
  degraded: "#ffb347",
  offline: "#ff4d5f",
  unknown: "#69707d",
  maintenance: "#44b7ff"
};

function ContextGuard({ onLost }: { onLost: () => void }) {
  const { gl } = useThree();
  useEffect(() => {
    const canvas = gl.domElement;
    const handleLost = (event: Event) => {
      event.preventDefault();
      onLost();
    };
    canvas.addEventListener("webglcontextlost", handleLost);
    return () => canvas.removeEventListener("webglcontextlost", handleLost);
  }, [gl, onLost]);
  return null;
}

function Graph({
  nodes,
  links,
  metrics,
  visible
}: {
  nodes: TopologyNode[];
  links: TopologyLink[];
  metrics: RuntimeMetrics;
  visible: boolean;
}) {
  const group = useRef<Group>(null);
  const graph = useMemo(() => topologyLayout(nodes, links, 1000, 560), [links, nodes]);
  const positions = useMemo(
    () =>
      new Map(
        graph.nodes.map((node) => [
          node.id,
          [(node.x - 500) / 68, (280 - node.y) / 68, node.z] as [number, number, number]
        ])
      ),
    [graph.nodes]
  );

  useFrame(({ clock }) => {
    if (!group.current || !visible || !QUALITY_CAPABILITIES[metrics.effectiveQuality].cameraMotion) {
      return;
    }
    group.current.rotation.y = Math.sin(clock.elapsedTime * 0.08) * 0.075;
    group.current.rotation.x = Math.cos(clock.elapsedTime * 0.055) * 0.025;
  });

  return (
    <group ref={group}>
      {graph.links.map((link) => {
        const start = positions.get(link.sourceNode.id);
        const end = positions.get(link.targetNode.id);
        if (!start || !end) return null;
        const hasTraffic = Number(link.details.trafficBps) > 0;
        return (
          <Line
            key={link.id}
            points={[start, end]}
            color={hasTraffic ? "#44b7ff" : "#535b69"}
            lineWidth={link.relationshipType === "uplink" ? 1.6 : 0.8}
            transparent
            opacity={hasTraffic ? 0.78 : 0.34}
          />
        );
      })}
      {graph.nodes.map((node) => {
        const position = positions.get(node.id);
        if (!position) return null;
        const color = STATUS_COLORS[node.status] ?? STATUS_COLORS.unknown;
        const scale =
          node.assetType === "firewall" || node.assetType === "proxmox_cluster" ? 0.18 : 0.12;
        return (
          <mesh key={node.id} position={position} scale={scale}>
            <octahedronGeometry args={[1, 0]} />
            <meshStandardMaterial
              color={color}
              emissive={color}
              emissiveIntensity={node.status === "online" ? 0.75 : 0.32}
              roughness={0.36}
              metalness={0.68}
            />
          </mesh>
        );
      })}
    </group>
  );
}

export function TopologyThree({
  nodes,
  links,
  metrics,
  visible,
  onContextLost
}: {
  nodes: TopologyNode[];
  links: TopologyLink[];
  metrics: RuntimeMetrics;
  visible: boolean;
  onContextLost: () => void;
}) {
  const capabilities = QUALITY_CAPABILITIES[metrics.effectiveQuality];
  return (
    <Canvas
      camera={{ position: [0, 0.5, 10.8], fov: 48 }}
      dpr={[1, capabilities.pixelRatio]}
      frameloop={visible ? "always" : "never"}
      gl={{ antialias: capabilities.antialias, alpha: true, powerPreference: "high-performance" }}
      aria-label={`Topologia 3D com ${nodes.length} ativos e ${links.length} relações reais`}
    >
      <ambientLight intensity={0.52} />
      <pointLight position={[5, 6, 8]} intensity={24} color="#ff7a1a" />
      <pointLight position={[-5, -2, 4]} intensity={16} color="#44b7ff" />
      <gridHelper args={[18, 24, "#302116", "#161b22"]} position={[0, -4.25, -1]} />
      <Graph nodes={nodes} links={links} metrics={metrics} visible={visible} />
      <ContextGuard onLost={onContextLost} />
    </Canvas>
  );
}
