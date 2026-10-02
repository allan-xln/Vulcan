"use client";

import dynamic from "next/dynamic";
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
import { useState } from "react";
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
