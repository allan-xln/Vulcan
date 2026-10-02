"use client";

import type { EChartsOption } from "echarts";
import { Activity, BrainCircuit, Building2, CircleGauge, Clock3, RadioTower, Sparkles, WalletCards } from "lucide-react";
import { useMemo } from "react";
import { VulcanChart } from "./vulcan-chart";
import {
  CommandFrame,
  AtGlanceKpi,
  HonestEmpty,
  StatusMark,
  formatMoment,
  formatNumber,
  kpi,
  numeric,
  text
} from "./primitives";
import { WallboardSnapshot } from "./types";

export function WorkforceScene({
  scene,
  snapshot
}: {
  scene: string;
  snapshot: WallboardSnapshot;
}) {
  if (scene === "economy") return <WorkforceEconomy snapshot={snapshot} />;
  if (scene === "pulse") return <WorkforcePulse snapshot={snapshot} />;
  if (scene === "teams") return <WorkforceTeams snapshot={snapshot} />;
  if (scene === "applications") return <WorkforceApplications snapshot={snapshot} />;
  if (scene === "branches") return <WorkforceBranches snapshot={snapshot} />;
  if (scene === "collection") return <WorkforceCollection snapshot={snapshot} />;
  return <WorkforceCommand snapshot={snapshot} />;
}

function WorkforceEconomy({ snapshot }: { snapshot: WallboardSnapshot }) {
  const activeHours = numeric(kpi(snapshot.kpis, "activeHours", "active_hours"));
  const idleHours = numeric(kpi(snapshot.kpis, "idleHours", "idle_hours"));
  const opportunityHours = numeric(kpi(snapshot.kpis, "opportunityHours", "opportunity_hours"));
  const estimatedSavings = numeric(kpi(snapshot.kpis, "estimatedSavings", "estimated_savings"));
  const insightCount = numeric(kpi(snapshot.kpis, "aiInsightCount", "ai_insight_count"));
  const confidence = numeric(kpi(snapshot.kpis, "aiConfidence", "ai_confidence"));
  const total = Math.max(activeHours + idleHours, 0);
  const activityShare = total ? Math.round((activeHours / total) * 100) : 0;
  const timeData = [
    { value: activeHours, name: "Tempo ativo", itemStyle: { color: "#39d98a" } },
    { value: idleHours, name: "Tempo em oportunidade", itemStyle: { color: "#ff7a1a" } }
  ].filter((item) => item.value > 0);
  const timeOption: EChartsOption = {
    tooltip: { trigger: "item", valueFormatter: (value) => `${Number(value).toFixed(1)}h` },
    series: [{
      type: "pie",
      radius: ["63%", "84%"],
      center: ["50%", "50%"],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: "#09090b", borderWidth: 5, borderRadius: 8 },
      label: { show: false },
      data: timeData
    }]
  };

  return (
    <div className="command-scene-grid">
      <CommandFrame eyebrow="Últimas 24 horas" title="Como o tempo foi usado" detail="leitura consolidada" className="command-span-7">
        {timeData.length ? (
          <div className="command-economy-time">
            <div className="command-economy-chart">
              <VulcanChart option={timeOption} ariaLabel="Distribuição real entre tempo ativo e oportunidade" />
              <div><strong>{activityShare}%</strong><span>tempo ativo</span></div>
            </div>
            <div className="command-economy-kpis">
              <article><Clock3 /><span>Trabalho ativo</span><strong>{activeHours.toFixed(1)}h</strong></article>
              <article><Activity /><span>Tempo que pode melhorar</span><strong>{opportunityHours.toFixed(1)}h</strong></article>
            </div>
          </div>
        ) : (
          <HonestEmpty title="Aguardando base real" detail="A distribuição surgirá após a coleta dos primeiros períodos completos." />
        )}
      </CommandFrame>
      <CommandFrame eyebrow="Oportunidade encontrada" title="Potencial de economia" detail="estimativa com evidências" className="command-span-5">
        {insightCount ? (
          <div className="command-economy-ai">
            <div className="command-economy-value"><WalletCards /><strong>{estimatedSavings.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 })}</strong><span>potencial identificado</span></div>
            <div className="command-economy-proof">
              <BrainCircuit /><p><strong>{insightCount}</strong><span>análises com evidência</span></p>
              <Sparkles /><p><strong>{Math.round(confidence * 100)}%</strong><span>confiança média</span></p>
            </div>
            <small>Estimativa operacional baseada nos padrões medidos no período.</small>
          </div>
        ) : (
          <HonestEmpty title="Sem estimativa ainda" detail="O Vulcan só exibirá economia quando houver insight real com evidência e confiança." />
        )}
      </CommandFrame>
    </div>
  );
}

function WorkforceCommand({ snapshot }: { snapshot: WallboardSnapshot }) {
  const activePeople = kpi(snapshot.kpis, "activePeople", "active_people");
  const agents = numeric(kpi(snapshot.kpis, "agents", "agents"));
  const online = numeric(kpi(snapshot.kpis, "onlineAgents", "online_agents"));
  const delayed = numeric(kpi(snapshot.kpis, "delayedAgents", "delayed_agents"));
  const offline = numeric(kpi(snapshot.kpis, "offlineAgents", "offline_agents"));
  const events = kpi(snapshot.kpis, "events24h", "events_24h");
  const coverage = agents ? Math.round((online / agents) * 100) : null;
  const needsAttention = delayed + offline;

  return (
    <div className="command-scene-grid workforce-command-scene command-at-glance-scene">
      <div className="command-glance-grid command-span-12">
        <AtGlanceKpi label="Pessoas ativas agora" value={formatNumber(activePeople)} hint="atividade nos últimos 15 min" />
        <AtGlanceKpi label="Computadores conectados" value={`${online}/${agents}`} hint={coverage === null ? "aguardando coleta" : `${coverage}% comunicando`} tone="healthy" />
        <AtGlanceKpi label="Precisam de atenção" value={needsAttention} hint={`${delayed} atrasados · ${offline} offline`} tone={needsAttention ? "critical" : "healthy"} />
        <AtGlanceKpi label="Atividades em 24h" value={formatNumber(events)} hint="eventos operacionais" tone="cold" />
      </div>

      <section className={`command-decision-card command-span-12 ${needsAttention ? "is-warning" : "is-healthy"}`}>
        <div>
          <span>SITUAÇÃO AGORA</span>
          <strong>{needsAttention ? `${needsAttention} computador(es) precisam ser verificados` : "Operação monitorada normalmente"}</strong>
        </div>
        <p>{needsAttention ? "Veja a tela Computadores monitorados para identificar os pontos." : "Todos os computadores cadastrados estão enviando informações."}</p>
      </section>

      <div className="command-bottom-rail">
        {snapshot.sites.map((site) => (
          <div key={String(site.id)} className="command-branch-chip">
            <span>{text(site.code, "—")}</span>
            <strong>{text(site.name)}</strong>
            <small>{formatNumber(site.active_people)} pessoa(s) ativa(s)</small>
          </div>
        ))}
      </div>
    </div>
  );
}

function WorkforcePulse({ snapshot }: { snapshot: WallboardSnapshot }) {
  const option = useMemo<EChartsOption>(() => {
    const categories = [...new Set(snapshot.activity.map((row) => text(row.category, "operacional")))];
    const buckets = [...new Set(snapshot.activity.map((row) => String(row.bucket)))];
    return {
      grid: { left: 42, right: 24, top: 34, bottom: 34 },
      tooltip: { trigger: "axis" },
      legend: { top: 0, right: 0, data: categories },
      xAxis: {
        type: "category",
        boundaryGap: false,
        data: buckets.map((bucket) => formatMoment(bucket, true))
      },
      yAxis: { type: "value", minInterval: 1 },
      series: categories.map((category, index) => ({
        name: category,
        type: "line",
        smooth: 0.35,
        symbol: "none",
        lineStyle: { width: index === 0 ? 2.5 : 1.4 },
        areaStyle: { opacity: index === 0 ? 0.18 : 0.04 },
        data: buckets.map((bucket) => {
          const match = snapshot.activity.find(
            (row) => String(row.bucket) === bucket && text(row.category, "operacional") === category
          );
          return numeric(match?.events);
        })
      }))
    };
  }, [snapshot.activity]);

  return (
    <div className="command-scene-grid pulse-scene">
      <CommandFrame
        eyebrow="Últimas 24 horas"
        title="Volume de atividade ao longo do dia"
        detail={`${formatNumber(kpi(snapshot.kpis, "events24h", "events_24h"))} eventos · 24h`}
        className="command-span-8"
      >
        {snapshot.activity.length ? (
          <VulcanChart option={option} ariaLabel="Linha temporal de eventos operacionais reais" />
        ) : (
          <HonestEmpty
            title="Sem atividade no intervalo"
            detail="Aguardando eventos reais dos agentes."
          />
        )}
      </CommandFrame>
      <CommandFrame
        eyebrow="Mais recente primeiro"
        title="Atividades registradas"
        className="command-span-4"
      >
        <div className="command-event-stream">
          {snapshot.activity
            .slice(-5)
            .reverse()
            .map((row, index) => (
              <div key={`${String(row.bucket)}-${String(row.category)}-${index}`}>
                <span className="command-event-pulse" />
                <p>
                  <strong>{text(row.category, "operacional")}</strong>
                  <small>{formatMoment(row.bucket)}</small>
                </p>
                <b>{formatNumber(row.events)}</b>
              </div>
            ))}
        </div>
      </CommandFrame>
    </div>
  );
}

function WorkforceTeams({ snapshot }: { snapshot: WallboardSnapshot }) {
  return (
    <div className="command-scene-grid">
      <CommandFrame
        eyebrow="Visão por local"
        title="Como está cada filial"
        detail="sem comparação individual"
        className="command-span-12"
      >
        <div className="command-branch-field">
          {snapshot.sites.map((site, index) => {
            const active = numeric(site.active_people);
            const events = numeric(site.events_24h);
            return (
              <article key={String(site.id)} className="command-branch-node">
                <span className="command-branch-index">0{index + 1}</span>
                <Building2 aria-hidden="true" />
                <div>
                  <p>{text(site.code, "—")}</p>
                  <h3>{text(site.name)}</h3>
                </div>
                <div className="command-branch-stats">
                  <strong>{active}</strong><span>ativas agora</span>
                  <strong>{events}</strong><span>atividades em 24h</span>
                </div>
                <StatusMark status={text(site.status, "unknown")} />
              </article>
            );
          })}
        </div>
        {!snapshot.sites.length ? (
          <HonestEmpty title="Nenhuma filial visível" detail="Revise o perfil do Wallboard." />
        ) : null}
      </CommandFrame>
    </div>
  );
}

function WorkforceApplications({ snapshot }: { snapshot: WallboardSnapshot }) {
  const option = useMemo<EChartsOption>(
    () => ({
      grid: { left: 138, right: 34, top: 18, bottom: 30 },
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        valueFormatter: (value) => `${Math.round(Number(value) / 60)} min`
      },
      xAxis: { type: "value", axisLabel: { formatter: (value: number) => `${Math.round(value / 60)}m` } },
      yAxis: {
        type: "category",
        inverse: true,
        data: snapshot.applications.slice(0, 9).map((item) => item.name)
      },
      series: [
        {
          name: "Tempo ativo",
          type: "bar",
          barWidth: 11,
          data: snapshot.applications.slice(0, 9).map((item) => ({
            value: item.activeSeconds,
            itemStyle: {
              borderRadius: [0, 6, 6, 0],
              color:
                item.category.toLowerCase().includes("produt")
                  ? "#39d98a"
                  : item.category.toLowerCase().includes("ocioso")
                    ? "#ffb347"
                    : "#ff7a1a"
            }
          }))
        }
      ]
    }),
    [snapshot.applications]
  );

  return (
    <div className="command-scene-grid">
      <CommandFrame
        eyebrow="Últimas 24 horas"
        title="Sistemas com mais tempo de uso"
        detail="tempo ativo registrado"
        className="command-span-8"
      >
        {snapshot.applications.length ? (
          <VulcanChart option={option} ariaLabel="Aplicações reais por duração ativa" />
        ) : (
          <HonestEmpty
            title="Métrica indisponível"
            detail="Aguardando coleta de aplicações com duração."
          />
        )}
      </CommandFrame>
      <CommandFrame
        eyebrow="Resumo"
        title="Uso por categoria"
        className="command-span-4"
      >
        <div className="command-category-list">
          {aggregateCategories(snapshot).map((category) => (
            <div key={category.name}>
              <span style={{ "--category-share": `${category.share}%` } as React.CSSProperties} />
              <p><strong>{category.name}</strong><small>{category.share}% do tempo coletado</small></p>
              <b>{Math.round(category.seconds / 60)}m</b>
            </div>
          ))}
        </div>
        {!snapshot.applications.length ? (
          <HonestEmpty
            title="Sem distribuição calculável"
            detail="Nenhum tempo de aplicação foi recebido."
          />
        ) : null}
      </CommandFrame>
    </div>
  );
}

function WorkforceBranches({ snapshot }: { snapshot: WallboardSnapshot }) {
  return (
    <div className="command-scene-grid branches-scene">
      <div className="command-branch-axis" aria-hidden="true" />
      {snapshot.sites.map((site, index) => (
        <article key={String(site.id)} className="command-station">
          <span className="command-station-code">{text(site.code, "—")}</span>
          <div className="command-station-orbit"><Building2 /></div>
          <h2>{text(site.name)}</h2>
          <p>Filial {String(index + 1).padStart(2, "0")}</p>
          <dl>
            <div><dt>Ativas agora</dt><dd>{formatNumber(site.active_people)}</dd></div>
            <div><dt>Atividades em 24h</dt><dd>{formatNumber(site.events_24h)}</dd></div>
          </dl>
          <StatusMark status={text(site.status, "unknown")} />
        </article>
      ))}
    </div>
  );
}

function WorkforceCollection({ snapshot }: { snapshot: WallboardSnapshot }) {
  const online = snapshot.agents.filter((agent) => agent.effectiveStatus === "online").length;
  const delayed = snapshot.agents.filter((agent) => agent.effectiveStatus === "delayed").length;
  const offline = snapshot.agents.filter((agent) => agent.effectiveStatus === "offline").length;
  return (
    <div className="command-scene-grid">
      <CommandFrame
        eyebrow="Computadores cadastrados"
        title="Quem está enviando informações"
        detail={`${snapshot.agents.length} no total`}
        className="command-span-8"
      >
        <div className="command-agent-list">
          {snapshot.agents.map((agent) => (
            <article key={agent.id}>
              <div className="command-agent-icon"><RadioTower /></div>
              <div>
                <h3>{agent.hostname}</h3>
                <p>{agent.operatingSystem}</p>
              </div>
              <p className="command-agent-last-seen">Último contato <strong>{formatMoment(agent.lastSeenAt)}</strong></p>
              <StatusMark status={agent.effectiveStatus} />
            </article>
          ))}
        </div>
        {!snapshot.agents.length ? (
          <HonestEmpty title="Aguardando agente" detail="Nenhuma identidade real está ativa." />
        ) : null}
      </CommandFrame>
      <CommandFrame eyebrow="Resumo agora" title="Situação dos computadores" className="command-span-4">
        <div className="command-coverage-core">
          <CircleGauge aria-hidden="true" />
          <strong>
            {snapshot.agents.length
              ? `${Math.round(
                  (snapshot.agents.filter((agent) => agent.effectiveStatus === "online").length /
                    snapshot.agents.length) *
                    100
                )}%`
              : "—"}
          </strong>
          <span>computadores conectados</span>
        </div>
        <div className="command-collection-counts">
          <AtGlanceKpi label="Online" value={online} tone="healthy" />
          <AtGlanceKpi label="Atrasados" value={delayed} tone={delayed ? "warning" : "healthy"} />
          <AtGlanceKpi label="Offline" value={offline} tone={offline ? "critical" : "healthy"} />
        </div>
      </CommandFrame>
    </div>
  );
}

function aggregateCategories(snapshot: WallboardSnapshot) {
  const totals = new Map<string, number>();
  for (const application of snapshot.applications) {
    totals.set(application.category, (totals.get(application.category) ?? 0) + application.activeSeconds);
  }
  const total = [...totals.values()].reduce((sum, value) => sum + value, 0);
  return [...totals.entries()]
    .map(([name, seconds]) => ({ name, seconds, share: total ? Math.round((seconds / total) * 100) : 0 }))
    .sort((left, right) => right.seconds - left.seconds);
}
