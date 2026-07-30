"use client";

import dynamic from "next/dynamic";
import type { EChartsOption } from "echarts";
import {
  Boxes,
  CloudCog,
  Database,
  Network,
  Printer,
  Router,
  Server,
  Shield,
  Wifi
} from "lucide-react";
import { useMemo, useState } from "react";
import { VulcanChart } from "./vulcan-chart";
import {
  CommandFrame,
  HonestEmpty,
  StatusMark,
  TelemetryLabel,
  formatMoment,
  formatNumber,
  kpi,
  numeric,
  text
} from "./primitives";
import { TopologyFallback } from "./topology-fallback";
import {
  PlatformHealth,
  PlatformVersion,
  RuntimeMetrics,
  TopologyNode,
  WallboardSnapshot
} from "./types";

const TopologyThree = dynamic(
  () => import("./topology-three").then((module) => module.TopologyThree),
  { ssr: false }
);

export function InfrastructureScene({
  scene,
  snapshot,
  health,
  version,
  metrics,
  visible,
  onContextLost
}: {
  scene: string;
  snapshot: WallboardSnapshot;
  health: PlatformHealth | null;
  version: PlatformVersion | null;
  metrics: RuntimeMetrics;
  visible: boolean;
  onContextLost: () => void;
}) {
  if (scene === "topology") {
    return (
      <InfrastructureTopology
        snapshot={snapshot}
        metrics={metrics}
        visible={visible}
        onContextLost={onContextLost}
      />
    );
  }
  if (scene === "connectivity") return <ConnectivityScene snapshot={snapshot} />;
  if (scene === "proxmox") return <ProxmoxScene snapshot={snapshot} />;
  if (scene === "servers") return <AssetFleetScene snapshot={snapshot} kind="servers" />;
  if (scene === "unifi") return <AssetFleetScene snapshot={snapshot} kind="unifi" />;
  if (scene === "printing") return <AssetFleetScene snapshot={snapshot} kind="printing" />;
  if (scene === "platform") {
    return <PlatformScene snapshot={snapshot} health={health} version={version} />;
  }
  return <InfrastructureCommand snapshot={snapshot} />;
}

function InfrastructureCommand({ snapshot }: { snapshot: WallboardSnapshot }) {
  const assets = numeric(kpi(snapshot.kpis, "assets", "assets"));
  const online = numeric(kpi(snapshot.kpis, "onlineAssets", "online_assets"));
  const degraded = numeric(kpi(snapshot.kpis, "degradedAssets", "degraded_assets"));
  const offline = numeric(kpi(snapshot.kpis, "offlineAssets", "offline_assets"));
  const unknown = numeric(kpi(snapshot.kpis, "unknownAssets", "unknown_assets"));
  const monitoredValue = kpi(snapshot.kpis, "monitoredAssets", "monitored_assets");
  const measured = monitoredValue === null
    ? Math.max(0, assets - unknown)
    : numeric(monitoredValue);
  const availability = kpi(snapshot.kpis, "availability", "availability");

  return (
    <div className="command-scene-grid infra-command-scene">
      <section className="infra-command-core">
        <div className="infra-core-grid" aria-hidden="true" />
        <div className="infra-core-mark">
          <Network />
          <span>ERS / VULCAN</span>
        </div>
        <div className="infra-core-value">
          <small>DISPONIBILIDADE OBSERVADA</small>
          <strong>{formatNumber(availability, "%")}</strong>
          <span>{formatNumber(measured)} de {formatNumber(assets)} ativos com estado confirmado</span>
          <small className="infra-core-formula">
            Fórmula: ({formatNumber(online)} online + 0,5 × {formatNumber(degraded)} degradados)
            {" ÷ "}{formatNumber(measured)} ativos com estado confirmado
          </small>
        </div>
        <div className="infra-orbit infra-orbit-a" />
        <div className="infra-orbit infra-orbit-b" />
      </section>
      <div className="infra-command-signals">
        <TelemetryLabel label="Online" value={online} detail="última observação" tone="healthy" />
        <TelemetryLabel label="Degradados" value={degraded} detail="atenção operacional" tone={degraded ? "warning" : "healthy"} />
        <TelemetryLabel label="Offline" value={offline} detail="sem resposta observada" tone={offline ? "critical" : "healthy"} />
        <TelemetryLabel label="Sem coleta" value={unknown} detail="estado não confirmado" tone="cold" />
      </div>
      <div className="infra-type-rail">
        <InfraType icon={Server} label="Servidores" value={kpi(snapshot.kpis, "servers", "servers")} />
        <InfraType icon={Boxes} label="Máquinas virtuais" value={kpi(snapshot.kpis, "virtualMachines", "virtual_machines")} />
        <InfraType icon={Router} label="Switches" value={kpi(snapshot.kpis, "switches", "switches")} />
        <InfraType icon={Wifi} label="Pontos de acesso" value={kpi(snapshot.kpis, "accessPoints", "access_points")} />
        <InfraType icon={Printer} label="Impressoras" value={kpi(snapshot.kpis, "printers", "printers")} />
      </div>
    </div>
  );
}

function InfrastructureTopology({
  snapshot,
  metrics,
  visible,
  onContextLost
}: {
  snapshot: WallboardSnapshot;
  metrics: RuntimeMetrics;
  visible: boolean;
  onContextLost: () => void;
}) {
  const [selected, setSelected] = useState<TopologyNode | null>(null);
  const useFallback = metrics.effectiveQuality === "low" || !metrics.webglAvailable;
  return (
    <div className="command-scene-grid topology-scene">
      <CommandFrame
        eyebrow={useFallback ? "Fallback operacional 2D" : "Malha operacional 3D"}
        title="Topologia Vulcan"
        detail={`${snapshot.topologyNodes.length} nós · ${snapshot.topologyLinks.length} relações`}
        className="command-span-9 command-topology-frame"
      >
        <div className="command-topology-stage">
          {useFallback ? (
            <TopologyFallback
              nodes={snapshot.topologyNodes}
              links={snapshot.topologyLinks}
              onSelect={setSelected}
            />
          ) : (
            <TopologyThree
              nodes={snapshot.topologyNodes}
              links={snapshot.topologyLinks}
              metrics={metrics}
              visible={visible}
              onContextLost={onContextLost}
            />
          )}
          <div className="command-topology-legend">
            <span><i className="is-healthy" />online</span>
            <span><i className="is-warning" />degradado</span>
            <span><i className="is-critical" />offline</span>
            <span><i className="is-unknown" />sem coleta</span>
          </div>
        </div>
      </CommandFrame>
      <CommandFrame eyebrow="Leitura técnica" title={selected?.name ?? "Malha ERS"} className="command-span-3">
        {selected ? (
          <div className="command-node-inspector">
            <StatusMark status={selected.status} />
            <dl>
              <div><dt>Tipo</dt><dd>{selected.assetType.replaceAll("_", " ")}</dd></div>
              <div><dt>Filial</dt><dd>{selected.siteName ?? "não vinculada"}</dd></div>
              <div><dt>Origem</dt><dd>{selected.source}</dd></div>
              <div><dt>IP</dt><dd>{selected.ipAddress ?? "não informado"}</dd></div>
              <div><dt>Última coleta</dt><dd>{formatMoment(selected.lastSeenAt)}</dd></div>
            </dl>
          </div>
        ) : (
          <div className="command-topology-summary">
            <Network />
            <strong>{snapshot.sites.length}</strong>
            <span>filiais representadas</span>
            <p>Selecione um nó no fallback 2D para inspecionar detalhes. No modo 3D, os textos permanecem no DOM.</p>
          </div>
        )}
      </CommandFrame>
    </div>
  );
}

function ConnectivityScene({ snapshot }: { snapshot: WallboardSnapshot }) {
  const links = snapshot.topologyNodes.filter((node) =>
    ["wan_link", "vpn_tunnel", "firewall", "gateway", "nat_service"].includes(node.assetType)
  );
  return (
    <div className="command-scene-grid connectivity-scene">
      <CommandFrame
        eyebrow="WAN / ADVPN"
        title="Conectividade entre unidades"
        detail={`${links.length} componentes observados`}
        className="command-span-12"
      >
        <div className="command-link-map">
          {snapshot.sites.map((site, index) => (
            <div key={String(site.id)} className="command-link-hub">
              <span className="command-link-beam" aria-hidden="true" />
              <Shield />
              <strong>{text(site.code, "—")}</strong>
              <small>{text(site.name)}</small>
              <StatusMark status={text(site.status, "unknown")} />
              <p>{numeric(site.online)}/{numeric(site.assets)} ativos online</p>
              {index < snapshot.sites.length - 1 ? <i aria-hidden="true" /> : null}
            </div>
          ))}
        </div>
        <div className="command-link-list">
          {links.map((node) => (
            <article key={node.id}>
              <Network />
              <div><strong>{node.name}</strong><span>{node.assetType.replaceAll("_", " ")} · {node.siteName ?? "sem filial"}</span></div>
              <p>Latência: <b>Métrica indisponível</b></p>
              <p>Perda: <b>Métrica indisponível</b></p>
              <StatusMark status={node.status} />
            </article>
          ))}
        </div>
        {!links.length ? <HonestEmpty title="Integração não habilitada" detail="Nenhum link WAN/ADVPN está cadastrado." /> : null}
      </CommandFrame>
    </div>
  );
}

function ProxmoxScene({ snapshot }: { snapshot: WallboardSnapshot }) {
  const assets = snapshot.topologyNodes.filter((node) =>
    ["proxmox_cluster", "virtualization_host", "virtual_machine", "backup_job", "backup_server"].includes(node.assetType)
  );
  const hosts = assets.filter((node) => node.assetType === "virtualization_host");
  const virtualMachines = assets.filter((node) => node.assetType === "virtual_machine");
  return (
    <div className="command-scene-grid">
      <CommandFrame
        eyebrow="Virtualização"
        title="Cluster Proxmox ERS"
        detail={`${hosts.length} nós · ${virtualMachines.length} VMs`}
        className="command-span-8"
      >
        <div className="command-rack-grid">
          {hosts.map((host) => (
            <article key={host.id} className="command-rack">
              <header><Server /><div><strong>{host.name}</strong><span>{host.ipAddress ?? "IP não informado"}</span></div><StatusMark status={host.status} /></header>
              <ResourceBar label="CPU" value={fraction(host.details.cpuUsage)} />
              <ResourceBar label="RAM" value={ratio(host.details.memoryBytes, host.details.memoryMaxBytes)} />
              <ResourceBar label="Disco" value={ratio(host.details.diskBytes, host.details.diskMaxBytes)} />
              <footer>{formatMoment(host.lastSeenAt)}</footer>
            </article>
          ))}
        </div>
        {!hosts.length ? <HonestEmpty title="Sem coleta Proxmox" detail="Nenhum nó foi reconciliado." /> : null}
      </CommandFrame>
      <CommandFrame eyebrow="Máquinas e backup" title="Carga observada" className="command-span-4">
        <div className="command-compact-fleet">
          {assets
            .filter((asset) => asset.assetType !== "virtualization_host")
            .slice(0, 12)
            .map((asset) => (
              <div key={asset.id}>
                <span>{asset.assetType === "backup_job" ? <Database /> : <Boxes />}</span>
                <p><strong>{asset.name}</strong><small>{asset.details.node ? `host ${String(asset.details.node)}` : asset.assetType.replaceAll("_", " ")}</small></p>
                <StatusMark status={asset.status} />
              </div>
            ))}
        </div>
      </CommandFrame>
    </div>
  );
}

function AssetFleetScene({
  snapshot,
  kind
}: {
  snapshot: WallboardSnapshot;
  kind: "servers" | "unifi" | "printing";
}) {
  const config = {
    servers: {
      types: ["server"],
      eyebrow: "Serviços essenciais",
      title: "Servidores ERS",
      icon: Server
    },
    unifi: {
      types: ["switch", "access_point", "controller"],
      eyebrow: "Integração somente leitura",
      title: "Rede e UniFi",
      icon: Wifi
    },
    printing: {
      types: ["printer"],
      eyebrow: "Frota de impressão",
      title: "Impressoras ERS",
      icon: Printer
    }
  }[kind];
  const assets = snapshot.topologyNodes.filter((node) => config.types.includes(node.assetType));
  const statusOption = useMemo<EChartsOption>(() => {
    const groups = ["online", "degraded", "offline", "unknown"].map((status) => ({
      name: status === "unknown" ? "sem coleta" : status,
      value: assets.filter((asset) => asset.status === status).length
    }));
    return {
      tooltip: { trigger: "item" },
      series: [{
        type: "pie",
        radius: ["64%", "88%"],
        center: ["50%", "48%"],
        label: { show: false },
        data: groups.filter((group) => group.value)
      }]
    };
  }, [assets]);

  return (
    <div className="command-scene-grid">
      <CommandFrame
        eyebrow={config.eyebrow}
        title={config.title}
        detail={`${assets.length} ativo(s) real(is)`}
        className="command-span-9"
      >
        <div className="command-fleet-grid">
          {assets.slice(0, 24).map((asset) => (
            <article key={asset.id}>
              <config.icon />
              <div>
                <h3>{asset.name}</h3>
                <p>{asset.siteName ?? "sem filial"} · {asset.ipAddress ?? "IP não informado"}</p>
                {kind === "unifi" ? (
                  <small>{formatDetail(asset.details.clients, "clientes")} · {formatDetail(asset.details.uplinkSpeedMbps, "Mb/s uplink")}</small>
                ) : kind === "printing" ? (
                  <small>Toner: {formatDetail(asset.details.toner, "")}</small>
                ) : (
                  <small>Última observação {formatMoment(asset.lastSeenAt)}</small>
                )}
              </div>
              <StatusMark status={asset.status} />
            </article>
          ))}
        </div>
        {!assets.length ? <HonestEmpty title="Sem coleta" detail={`Nenhum ativo de ${config.title.toLowerCase()} foi encontrado.`} /> : null}
      </CommandFrame>
      <CommandFrame eyebrow="Estado observado" title="Distribuição" className="command-span-3">
        {assets.length ? <VulcanChart option={statusOption} ariaLabel={`Estados reais de ${config.title}`} /> : null}
        <div className="command-fleet-summary">
          <strong>{assets.filter((asset) => asset.status === "online").length}</strong><span>online</span>
          <strong>{assets.filter((asset) => asset.status === "offline").length}</strong><span>offline</span>
          <strong>{assets.filter((asset) => asset.status === "unknown").length}</strong><span>sem coleta</span>
        </div>
      </CommandFrame>
    </div>
  );
}

function PlatformScene({
  snapshot,
  health,
  version
}: {
  snapshot: WallboardSnapshot;
  health: PlatformHealth | null;
  version: PlatformVersion | null;
}) {
  return (
    <div className="command-scene-grid">
      <CommandFrame eyebrow="Autobservabilidade" title="Saúde do Vulcan" className="command-span-7">
        <div className="command-health-grid">
          {health?.checks.map((check) => (
            <article key={check.name}>
              <CloudCog />
              <div><strong>{check.name.replaceAll("_", " ")}</strong><span>{check.detail}</span></div>
              <p>{check.latencyMs === null ? "—" : `${check.latencyMs.toFixed(1)} ms`}</p>
              <StatusMark status={check.status} />
            </article>
          ))}
        </div>
        {!health ? <HonestEmpty title="Health indisponível" detail="Aguardando resposta do próprio Vulcan." state="warning" /> : null}
      </CommandFrame>
      <CommandFrame eyebrow="Coletores" title="Integrações" className="command-span-5">
        <div className="command-integration-grid">
          {snapshot.integrations.map((integration, index) => (
            <article key={`${String(integration.adapter_type)}-${index}`}>
              <span>{text(integration.adapter_type, "adapter").slice(0, 2).toUpperCase()}</span>
              <div><strong>{text(integration.name)}</strong><small>último sucesso {formatMoment(integration.last_success_at)}</small></div>
              <StatusMark status={text(integration.status, "unknown")} />
            </article>
          ))}
        </div>
        <div className="command-platform-release">
          <p>Release observada</p>
          <strong>{version?.version ?? "sem coleta"}</strong>
          <span>{version ? `${version.service} · ${version.commit.slice(0, 8)}` : "Aguardando /version"}</span>
        </div>
      </CommandFrame>
    </div>
  );
}

function InfraType({
  icon: Icon,
  label,
  value
}: {
  icon: typeof Server;
  label: string;
  value: unknown;
}) {
  return <div><Icon /><span>{label}</span><strong>{formatNumber(value)}</strong></div>;
}

function ResourceBar({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="command-resource">
      <span>{label}</span>
      <i><b style={{ width: `${value === null ? 0 : value}%` }} /></i>
      <strong>{value === null ? "sem coleta" : `${Math.round(value)}%`}</strong>
    </div>
  );
}

function ratio(value: unknown, maximum: unknown) {
  const parsed = numeric(value);
  const max = numeric(maximum);
  return max ? Math.min(100, (parsed / max) * 100) : null;
}

function fraction(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.min(100, Math.max(0, parsed <= 1 ? parsed * 100 : parsed)) : null;
}

function formatDetail(value: unknown, suffix: string) {
  return value === null || value === undefined || value === ""
    ? "sem coleta"
    : `${String(value)}${suffix ? ` ${suffix}` : ""}`;
}
