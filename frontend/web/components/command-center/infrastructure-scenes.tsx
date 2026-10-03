"use client";

import dynamic from "next/dynamic";
import {
  AlertTriangle,
  CheckCircle2,
  Boxes,
  CloudCog,
  Database,
  Gauge,
  HardDrive,
  Network,
  Printer,
  Router,
  Server,
  Shield,
  Wifi
} from "lucide-react";
import { useState, type CSSProperties, type ReactNode } from "react";
import {
  AtGlanceKpi,
  CommandFrame,
  HonestEmpty,
  StatusMark,
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
  if (scene === "site") return <SiteOperationsScene snapshot={snapshot} />;
  if (scene === "connectivity") return <ConnectivityScene snapshot={snapshot} />;
  if (scene === "proxmox") return <ProxmoxScene snapshot={snapshot} />;
  if (scene === "servers") return <ServerOperationsScene snapshot={snapshot} />;
  if (scene === "unifi") return <NetworkOperationsScene snapshot={snapshot} />;
  if (scene === "printing") return <AssetFleetScene snapshot={snapshot} kind="printing" />;
  if (scene === "platform") {
    return <PlatformScene snapshot={snapshot} health={health} version={version} />;
  }
  return <InfrastructureCommand snapshot={snapshot} />;
}

function SiteOperationsScene({ snapshot }: { snapshot: WallboardSnapshot }) {
  const assets = snapshot.topologyNodes;
  const measured = assets.filter((asset) => asset.status !== "unknown");
  const healthy = measured.filter((asset) => healthyStatus(asset.status)).length;
  const attention = measured.filter((asset) => !healthyStatus(asset.status)).length;
  const availability = measured.length ? Math.round((healthy / measured.length) * 100) : null;
  const links = assets.filter((asset) => ["wan_link", "vpn_tunnel", "firewall", "gateway"].includes(asset.assetType));
  const wireless = assets.filter((asset) => ["access_point", "switch", "controller"].includes(asset.assetType));
  const servers = assets.filter((asset) => ["server", "virtualization_host", "virtual_machine"].includes(asset.assetType));
  const devices = assets.filter((asset) => ["printer", "workstation"].includes(asset.assetType));
  const siteLabel = snapshot.siteName ?? (snapshot.sites.length === 1 ? text(snapshot.sites[0]?.name) : "Todas as unidades");

  return (
    <div className="command-ops-board command-site-board">
      <section className="command-ops-hero">
        <div><small>PAINEL DA UNIDADE</small><h2>{siteLabel}</h2><p>Infraestrutura e rede em tempo real</p></div>
        <div className={`command-ops-health ${attention ? "is-warning" : "is-healthy"}`}>
          {attention ? <AlertTriangle /> : <CheckCircle2 />}
          <strong>{measured.length ? `${availability}%` : "—"}</strong>
          <span>{attention ? `${attention} item(ns) para verificar` : measured.length ? "Operação normal" : "Aguardando coleta"}</span>
        </div>
      </section>

      <OpsPanel title="Links e firewall" icon={Shield} className="command-ops-span-4">
        <AssetRows assets={links} limit={5} detail={(asset) => linkDetail(asset)} />
      </OpsPanel>
      <OpsPanel title="Rede e Wi-Fi" icon={Wifi} className="command-ops-span-4">
        <AssetRows assets={wireless} limit={5} detail={(asset) => networkDetail(asset)} />
      </OpsPanel>
      <OpsPanel title="Alertas prioritários" icon={AlertTriangle} className="command-ops-span-4">
        <AlertRows snapshot={snapshot} fallbackAssets={assets} />
      </OpsPanel>

      <OpsPanel title="Servidores" icon={Server} className="command-ops-span-4">
        <AssetRows assets={servers} limit={5} detail={(asset) => resourceDetail(asset)} />
      </OpsPanel>
      <OpsPanel title="Impressão e dispositivos" icon={Printer} className="command-ops-span-4">
        <AssetRows assets={devices} limit={5} detail={(asset) => deviceDetail(asset)} />
      </OpsPanel>
      <OpsPanel title="Resumo da unidade" icon={Gauge} className="command-ops-span-4">
        <div className="command-ops-kpis">
          <OpsKpi label="Equipamentos" value={assets.length} />
          <OpsKpi label="Funcionando" value={healthy} tone="healthy" />
          <OpsKpi label="Agentes online" value={snapshot.agents.filter((agent) => agent.effectiveStatus === "online").length} />
          <OpsKpi label="Clientes Wi-Fi" value={sumDetails(wireless, "clients")} />
        </div>
      </OpsPanel>
    </div>
  );
}

function ServerOperationsScene({ snapshot }: { snapshot: WallboardSnapshot }) {
  const servers = snapshot.topologyNodes.filter((asset) =>
    ["server", "virtualization_host", "virtual_machine", "backup_server"].includes(asset.assetType)
  );
  const backups = snapshot.topologyNodes.filter((asset) => asset.assetType === "backup_job");
  const online = servers.filter((asset) => healthyStatus(asset.status)).length;
  const warning = servers.filter((asset) => ["degraded", "warning", "maintenance"].includes(asset.status)).length;
  const offline = servers.filter((asset) => ["offline", "critical"].includes(asset.status)).length;

  return (
    <div className="command-ops-board command-server-board">
      <OpsPanel title="Status geral dos servidores" icon={Server} className="command-ops-span-5">
        <div className="command-ops-kpis command-ops-kpis-wide">
          <OpsKpi label="Monitorados" value={servers.length} />
          <OpsKpi label="Online" value={online} tone="healthy" />
          <OpsKpi label="Atenção" value={warning} tone="warning" />
          <OpsKpi label="Críticos" value={offline} tone="critical" />
        </div>
      </OpsPanel>
      <OpsPanel title="Uso médio dos recursos" icon={Gauge} className="command-ops-span-4">
        <div className="command-resource-overview">
          <ResourceDial label="CPU" value={averageDetail(servers, "cpuUsage")} />
          <ResourceDial label="Memória" value={averageRatio(servers, "memoryBytes", "memoryMaxBytes")} />
          <ResourceDial label="Disco" value={averageRatio(servers, "diskBytes", "diskMaxBytes")} />
        </div>
      </OpsPanel>
      <OpsPanel title="Alertas prioritários" icon={AlertTriangle} className="command-ops-span-3">
        <AlertRows snapshot={snapshot} fallbackAssets={servers} />
      </OpsPanel>

      <OpsPanel title="Lista de servidores" icon={Server} className="command-ops-span-12 command-ops-table-panel">
        <div className="command-ops-table">
          <div className="command-ops-table-head"><span>Servidor</span><span>Status</span><span>CPU</span><span>Memória</span><span>Disco</span><span>Última coleta</span></div>
          {servers.slice(0, 12).map((server) => (
            <div key={server.id} className="command-ops-table-row">
              <span><strong>{server.name}</strong><small>{server.ipAddress ?? server.siteName ?? "sem IP"}</small></span>
              <StatusMark status={server.status} />
              <MiniMetric value={fraction(server.details.cpuUsage)} />
              <MiniMetric value={ratio(server.details.memoryBytes, server.details.memoryMaxBytes)} />
              <MiniMetric value={ratio(server.details.diskBytes, server.details.diskMaxBytes)} />
              <span className="command-ops-moment">{formatMoment(server.lastSeenAt)}</span>
            </div>
          ))}
        </div>
        {!servers.length ? <HonestEmpty title="Sem servidores monitorados" detail="Os servidores aparecerão após a primeira coleta real." /> : null}
      </OpsPanel>

      <OpsPanel title="Backup e armazenamento" icon={HardDrive} className="command-ops-span-6">
        <AssetRows assets={backups} limit={6} detail={(asset) => resourceDetail(asset)} />
      </OpsPanel>
      <OpsPanel title="Agentes de servidor" icon={CloudCog} className="command-ops-span-6">
        <div className="command-ops-kpis command-ops-kpis-wide">
          <OpsKpi label="Online" value={snapshot.agents.filter((agent) => agent.profile === "server" && agent.effectiveStatus === "online").length} tone="healthy" />
          <OpsKpi label="Atrasados" value={snapshot.agents.filter((agent) => agent.profile === "server" && agent.effectiveStatus === "delayed").length} tone="warning" />
          <OpsKpi label="Offline" value={snapshot.agents.filter((agent) => agent.profile === "server" && agent.effectiveStatus === "offline").length} tone="critical" />
        </div>
      </OpsPanel>
    </div>
  );
}

function NetworkOperationsScene({ snapshot }: { snapshot: WallboardSnapshot }) {
  const switches = snapshot.topologyNodes.filter((asset) => asset.assetType === "switch");
  const accessPoints = snapshot.topologyNodes.filter((asset) => asset.assetType === "access_point");
  const controllers = snapshot.topologyNodes.filter((asset) => asset.assetType === "controller");
  const networkAssets = [...controllers, ...switches, ...accessPoints];
  const online = networkAssets.filter((asset) => healthyStatus(asset.status)).length;
  const warning = networkAssets.filter((asset) => ["degraded", "warning", "maintenance"].includes(asset.status)).length;
  const offline = networkAssets.filter((asset) => ["offline", "critical"].includes(asset.status)).length;

  return (
    <div className="command-ops-board command-network-board">
      <OpsPanel title="Status geral da rede" icon={Network} className="command-ops-span-4">
        <div className="command-network-score"><strong>{networkAssets.length}</strong><span>equipamentos de rede</span></div>
        <div className="command-ops-kpis">
          <OpsKpi label="Online" value={online} tone="healthy" />
          <OpsKpi label="Atenção" value={warning} tone="warning" />
          <OpsKpi label="Offline" value={offline} tone="critical" />
          <OpsKpi label="Clientes" value={sumDetails(accessPoints, "clients")} />
        </div>
      </OpsPanel>
      <OpsPanel title="Resumo da rede sem fio" icon={Wifi} className="command-ops-span-5">
        <div className="command-wireless-summary">
          <OpsKpi label="Access points" value={accessPoints.length} />
          <OpsKpi label="APs online" value={accessPoints.filter((asset) => healthyStatus(asset.status)).length} tone="healthy" />
          <OpsKpi label="Clientes conectados" value={sumDetails(accessPoints, "clients")} />
        </div>
        <AssetRows assets={accessPoints} limit={4} detail={(asset) => networkDetail(asset)} />
      </OpsPanel>
      <OpsPanel title="Alertas prioritários" icon={AlertTriangle} className="command-ops-span-3">
        <AlertRows snapshot={snapshot} fallbackAssets={networkAssets} />
      </OpsPanel>

      <OpsPanel title="Switches" icon={Router} className="command-ops-span-6 command-ops-table-panel">
        <NetworkTable assets={switches} />
      </OpsPanel>
      <OpsPanel title="Access points" icon={Wifi} className="command-ops-span-6 command-ops-table-panel">
        <NetworkTable assets={accessPoints} />
      </OpsPanel>

      <OpsPanel title="Resumo de switching" icon={Network} className="command-ops-span-12">
        <div className="command-ops-kpis command-ops-kpis-wide">
          <OpsKpi label="Switches" value={switches.length} />
          <OpsKpi label="APs" value={accessPoints.length} />
          <OpsKpi label="Uplinks com erro" value={networkAssets.filter((asset) => numeric(asset.details.uplinkRxErrors) > 0).length} tone="warning" />
          <OpsKpi label="Disponibilidade" value={networkAssets.length ? `${Math.round((online / networkAssets.length) * 100)}%` : "—"} tone="healthy" />
        </div>
      </OpsPanel>
    </div>
  );
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
  const attention = degraded + offline;

  return (
    <div className="command-scene-grid infra-command-scene command-at-glance-scene">
      <section className="infra-command-core">
        <div className="infra-core-grid" aria-hidden="true" />
        <div className="infra-core-mark">
          <Network />
          <span>ERS / VULCAN</span>
        </div>
        <div className="infra-core-value">
          <small>INFRAESTRUTURA DISPONÍVEL AGORA</small>
          <strong>{formatNumber(availability, "%")}</strong>
          <span>{attention ? `${attention} equipamento(s) precisam de atenção` : "Nenhum equipamento com falha detectada"}</span>
        </div>
        <div className="infra-orbit infra-orbit-a" />
        <div className="infra-orbit infra-orbit-b" />
      </section>
      <div className="infra-command-signals">
        <AtGlanceKpi label="Funcionando" value={online} hint={`de ${measured} monitorados`} tone="healthy" />
        <AtGlanceKpi label="Com alerta" value={degraded} hint="funcionando com restrição" tone={degraded ? "warning" : "healthy"} />
        <AtGlanceKpi label="Fora do ar" value={offline} hint="sem resposta" tone={offline ? "critical" : "healthy"} />
        <AtGlanceKpi label="Sem informação" value={unknown} hint={`${assets} equipamentos cadastrados`} tone="cold" />
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
        eyebrow={useFallback ? "Mapa simplificado" : "Mapa interativo"}
        title="Como os equipamentos estão conectados"
        detail={`${snapshot.topologyNodes.length} equipamentos · ${snapshot.topologyLinks.length} conexões`}
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
      <CommandFrame eyebrow="Detalhes" title={selected?.name ?? "Resumo do mapa"} className="command-span-3">
        {selected ? (
          <div className="command-node-inspector">
            <StatusMark status={selected.status} />
            <dl>
              <div><dt>Tipo</dt><dd>{assetTypeLabel(selected.assetType)}</dd></div>
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
            <span>filiais no mapa</span>
            <p>Selecione um equipamento para ver o estado, a filial e o último contato.</p>
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
        eyebrow="Conexões da empresa"
        title="As filiais estão conectadas?"
        detail={`${links.length} links monitorados`}
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
              <p><strong>{numeric(site.online)}/{numeric(site.assets)}</strong> equipamentos funcionando</p>
              {index < snapshot.sites.length - 1 ? <i aria-hidden="true" /> : null}
            </div>
          ))}
        </div>
        <div className="command-link-list">
          {links.slice(0, 9).map((node) => (
            <article key={node.id}>
              <Network />
              <div><strong>{node.name}</strong><span>{assetTypeLabel(node.assetType)} · {node.siteName ?? "sem filial"}</span></div>
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
        eyebrow="Ambiente virtual"
        title="Capacidade dos servidores"
        detail={`${hosts.length} servidores físicos · ${virtualMachines.length} máquinas virtuais`}
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
      <CommandFrame eyebrow="Verificar agora" title="Itens que precisam de atenção" className="command-span-4">
        <div className="command-compact-fleet">
          {assets
            .filter((asset) => asset.assetType !== "virtualization_host")
            .filter((asset) => !["online", "ok", "active"].includes(asset.status))
            .slice(0, 10)
            .map((asset) => (
              <div key={asset.id}>
                <span>{asset.assetType === "backup_job" ? <Database /> : <Boxes />}</span>
                <p><strong>{asset.name}</strong><small>{asset.details.node ? `servidor ${String(asset.details.node)}` : assetTypeLabel(asset.assetType)}</small></p>
                <StatusMark status={asset.status} />
              </div>
            ))}
        </div>
        {!assets.some((asset) => asset.assetType !== "virtualization_host" && !["online", "ok", "active"].includes(asset.status)) ? (
          <HonestEmpty title="Tudo normal" detail="Nenhuma máquina virtual ou rotina de backup exige atenção." state="healthy" />
        ) : null}
      </CommandFrame>
    </div>
  );
}

function OpsPanel({
  title,
  icon: Icon,
  className,
  children
}: {
  title: string;
  icon: typeof Server;
  className: string;
  children: ReactNode;
}) {
  return (
    <section className={`command-ops-panel ${className}`}>
      <header><Icon /><h2>{title}</h2></header>
      <div className="command-ops-panel-body">{children}</div>
    </section>
  );
}

function OpsKpi({
  label,
  value,
  tone = "neutral"
}: {
  label: string;
  value: string | number;
  tone?: "neutral" | "healthy" | "warning" | "critical";
}) {
  return <div className={`command-ops-kpi is-${tone}`}><span>{label}</span><strong>{value}</strong></div>;
}

function AssetRows({
  assets,
  limit,
  detail
}: {
  assets: TopologyNode[];
  limit: number;
  detail: (asset: TopologyNode) => string;
}) {
  const ordered = [...assets].sort((left, right) => statusPriority(left.status) - statusPriority(right.status));
  if (!ordered.length) return <HonestEmpty title="Aguardando coleta" detail="Nenhum equipamento real encontrado nesta categoria." />;
  return (
    <div className="command-ops-rows">
      {ordered.slice(0, limit).map((asset) => (
        <article key={asset.id}>
          <StatusMark status={asset.status} />
          <div><strong>{asset.name}</strong><small>{detail(asset)}</small></div>
          <span>{asset.ipAddress ?? "—"}</span>
        </article>
      ))}
    </div>
  );
}

function AlertRows({ snapshot, fallbackAssets }: { snapshot: WallboardSnapshot; fallbackAssets: TopologyNode[] }) {
  const alerts = snapshot.alerts.slice(0, 5);
  const unhealthy = fallbackAssets
    .filter((asset) => !healthyStatus(asset.status) && asset.status !== "unknown")
    .slice(0, 5);
  if (!alerts.length && !unhealthy.length) {
    return <HonestEmpty title="Sem alertas ativos" detail="Nenhum equipamento exige ação agora." state="healthy" />;
  }
  return (
    <div className="command-alert-rows">
      {alerts.map((alert, index) => (
        <article key={`${text(alert.id, "alert")}-${index}`}>
          <StatusMark status={text(alert.severity, "warning")} />
          <div><strong>{text(alert.title, text(alert.description, "Alerta operacional"))}</strong><small>{formatMoment(text(alert.last_occurred_at, text(alert.created_at, "")) || null)}</small></div>
        </article>
      ))}
      {!alerts.length ? unhealthy.map((asset) => (
        <article key={asset.id}>
          <StatusMark status={asset.status} />
          <div><strong>{asset.name}</strong><small>{asset.siteName ?? assetTypeLabel(asset.assetType)}</small></div>
        </article>
      )) : null}
    </div>
  );
}

function NetworkTable({ assets }: { assets: TopologyNode[] }) {
  if (!assets.length) return <HonestEmpty title="Aguardando integração" detail="Nenhum equipamento foi reconciliado." />;
  return (
    <div className="command-network-table">
      {assets.slice(0, 8).map((asset) => (
        <article key={asset.id}>
          <div><strong>{asset.name}</strong><small>{asset.ipAddress ?? asset.siteName ?? "sem IP"}</small></div>
          <span>{formatDetail(asset.details.clients, "clientes")}</span>
          <span>{formatDetail(asset.details.uplinkSpeedMbps, "Mb/s")}</span>
          <StatusMark status={asset.status} />
        </article>
      ))}
    </div>
  );
}

function MiniMetric({ value }: { value: number | null }) {
  return (
    <span className="command-mini-metric">
      <i><b style={{ width: `${value ?? 0}%` }} /></i>
      <strong>{value === null ? "—" : `${Math.round(value)}%`}</strong>
    </span>
  );
}

function ResourceDial({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="command-resource-dial" style={{ "--resource-value": `${value ?? 0}%` } as CSSProperties}>
      <div><strong>{value === null ? "—" : `${Math.round(value)}%`}</strong></div>
      <span>{label}</span>
    </div>
  );
}

function healthyStatus(status: string) {
  return ["online", "ok", "active", "success", "healthy"].includes(status);
}

function sumDetails(assets: TopologyNode[], key: string) {
  return assets.reduce((total, asset) => total + numeric(asset.details[key]), 0);
}

function averageDetail(assets: TopologyNode[], key: string) {
  const values = assets.map((asset) => fraction(asset.details[key])).filter((value): value is number => value !== null);
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

function averageRatio(assets: TopologyNode[], valueKey: string, maximumKey: string) {
  const values = assets
    .map((asset) => ratio(asset.details[valueKey], asset.details[maximumKey]))
    .filter((value): value is number => value !== null);
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

function linkDetail(asset: TopologyNode) {
  const latency = asset.details.latencyMs;
  const loss = asset.details.packetLossPercent;
  return [assetTypeLabel(asset.assetType), latency !== undefined ? `${latency} ms` : null, loss !== undefined ? `${loss}% perda` : null]
    .filter(Boolean)
    .join(" · ");
}

function networkDetail(asset: TopologyNode) {
  return [asset.siteName, asset.details.clients !== undefined ? `${asset.details.clients} clientes` : null, asset.details.uplinkSpeedMbps !== undefined ? `${asset.details.uplinkSpeedMbps} Mb/s` : null]
    .filter(Boolean)
    .join(" · ") || assetTypeLabel(asset.assetType);
}

function resourceDetail(asset: TopologyNode) {
  const cpu = fraction(asset.details.cpuUsage);
  const memory = ratio(asset.details.memoryBytes, asset.details.memoryMaxBytes);
  return [asset.siteName, cpu === null ? null : `CPU ${Math.round(cpu)}%`, memory === null ? null : `RAM ${Math.round(memory)}%`]
    .filter(Boolean)
    .join(" · ") || `Última coleta ${formatMoment(asset.lastSeenAt)}`;
}

function deviceDetail(asset: TopologyNode) {
  if (asset.assetType === "printer") {
    return [asset.siteName, asset.details.toner ? `toner ${asset.details.toner}` : null].filter(Boolean).join(" · ");
  }
  return asset.siteName ?? assetTypeLabel(asset.assetType);
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
      eyebrow: "Serviços da empresa",
      title: "Situação dos servidores",
      icon: Server
    },
    unifi: {
      types: ["switch", "access_point", "controller"],
      eyebrow: "Rede interna",
      title: "Situação do Wi-Fi e switches",
      icon: Wifi
    },
    printing: {
      types: ["printer"],
      eyebrow: "Impressão",
      title: "Situação das impressoras",
      icon: Printer
    }
  }[kind];
  const assets = snapshot.topologyNodes.filter((node) => config.types.includes(node.assetType));
  const online = assets.filter((asset) => asset.status === "online").length;
  const degraded = assets.filter((asset) => asset.status === "degraded").length;
  const offline = assets.filter((asset) => asset.status === "offline").length;
  const unknown = assets.filter((asset) => asset.status === "unknown").length;
  const availability = assets.length ? Math.round((online / assets.length) * 100) : 0;
  const orderedAssets = [...assets].sort((left, right) => statusPriority(left.status) - statusPriority(right.status));

  return (
    <div className="command-scene-grid">
      <CommandFrame
        eyebrow={config.eyebrow}
        title={config.title}
        detail={`${assets.length} equipamentos cadastrados`}
        className="command-span-9"
      >
        <div className="command-fleet-grid">
          {orderedAssets.slice(0, 15).map((asset) => (
            <article key={asset.id}>
              <config.icon />
              <div>
                <h3>{asset.name}</h3>
                <p>{asset.siteName ?? "sem filial"} · {asset.ipAddress ?? "IP não informado"}</p>
                {kind === "unifi" ? (
                  <small>{formatDetail(asset.details.clients, "clientes conectados")} · {formatDetail(asset.details.uplinkSpeedMbps, "Mb/s")}</small>
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
      <CommandFrame eyebrow="Resumo agora" title="Disponibilidade" className="command-span-3">
        <div className="command-fleet-availability">
          <strong>{assets.length ? `${availability}%` : "—"}</strong>
          <span>funcionando</span>
        </div>
        <div className="command-fleet-summary">
          <strong className="is-healthy">{online}</strong><span>funcionando</span>
          <strong className="is-warning">{degraded}</strong><span>com alerta</span>
          <strong className="is-critical">{offline}</strong><span>fora do ar</span>
          <strong>{unknown}</strong><span>sem informação</span>
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
      <CommandFrame eyebrow="Serviços do sistema" title="O Vulcan está funcionando?" className="command-span-7">
        <div className="command-health-grid">
          {health?.checks.map((check) => (
            <article key={check.name}>
              <CloudCog />
              <div><strong>{healthCheckLabel(check.name)}</strong><span>{check.detail}</span></div>
              <p>{check.latencyMs === null ? "—" : `${check.latencyMs.toFixed(1)} ms`}</p>
              <StatusMark status={check.status} />
            </article>
          ))}
        </div>
        {!health ? <HonestEmpty title="Health indisponível" detail="Aguardando resposta do próprio Vulcan." state="warning" /> : null}
      </CommandFrame>
      <CommandFrame eyebrow="Fontes de informação" title="Conexões do Vulcan" className="command-span-5">
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

function statusPriority(status: string) {
  return ({ offline: 0, critical: 0, degraded: 1, warning: 1, unknown: 2, online: 3 } as Record<string, number>)[status] ?? 2;
}

function assetTypeLabel(type: string) {
  return ({
    wan_link: "Link de internet",
    vpn_tunnel: "Túnel entre filiais",
    firewall: "Firewall",
    gateway: "Saída da rede",
    nat_service: "Serviço publicado",
    server: "Servidor",
    virtualization_host: "Servidor físico",
    virtual_machine: "Máquina virtual",
    backup_job: "Rotina de backup",
    backup_server: "Servidor de backup",
    switch: "Switch",
    access_point: "Ponto de Wi-Fi",
    controller: "Controlador de rede",
    printer: "Impressora"
  } as Record<string, string>)[type] ?? type.replaceAll("_", " ");
}

function healthCheckLabel(name: string) {
  return ({
    database: "Banco de dados",
    schema: "Estrutura do banco",
    supabase: "Banco Supabase",
    evolution: "WhatsApp",
    ingestion: "Entrada de dados"
  } as Record<string, string>)[name] ?? name.replaceAll("_", " ");
}
