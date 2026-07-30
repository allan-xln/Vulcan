"use client";

import type { EChartsOption } from "echarts";
import { Activity, Building2, CircleGauge, RadioTower, UsersRound } from "lucide-react";
import { useMemo } from "react";
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
import { WallboardSnapshot } from "./types";

export function WorkforceScene({
  scene,
  snapshot
}: {
  scene: string;
  snapshot: WallboardSnapshot;
}) {
  if (scene === "pulse") return <WorkforcePulse snapshot={snapshot} />;
  if (scene === "teams") return <WorkforceTeams snapshot={snapshot} />;
  if (scene === "applications") return <WorkforceApplications snapshot={snapshot} />;
  if (scene === "branches") return <WorkforceBranches snapshot={snapshot} />;
  if (scene === "collection") return <WorkforceCollection snapshot={snapshot} />;
  return <WorkforceCommand snapshot={snapshot} />;
}

function WorkforceCommand({ snapshot }: { snapshot: WallboardSnapshot }) {
  const activePeople = kpi(snapshot.kpis, "activePeople", "active_people");
  const agents = numeric(kpi(snapshot.kpis, "agents", "agents"));
  const online = numeric(kpi(snapshot.kpis, "onlineAgents", "online_agents"));
  const delayed = numeric(kpi(snapshot.kpis, "delayedAgents", "delayed_agents"));
  const offline = numeric(kpi(snapshot.kpis, "offlineAgents", "offline_agents"));
  const events = kpi(snapshot.kpis, "events24h", "events_24h");
  const coverage = agents ? Math.round((online / agents) * 100) : null;

  return (
    <div className="command-scene-grid workforce-command-scene">
      <div className="command-side-telemetry command-side-left">
        <TelemetryLabel
          label="Pessoas ativas"
          value={formatNumber(activePeople)}
          detail="sinais confirmados nos últimos 15 min"
        />
        <TelemetryLabel
          label="Eventos 24h"
          value={formatNumber(events)}
          detail="telemetria operacional real"
          tone="cold"
        />
      </div>

      <section className="command-core" aria-label="Pulso central da operação">
        <div className="command-core-rings" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <div
          className="command-core-meter"
          style={{ "--command-progress": `${coverage ?? 0}%` } as React.CSSProperties}
        >
          <div className="command-core-center">
            <span>COBERTURA</span>
            <strong>{coverage === null ? "—" : `${coverage}%`}</strong>
            <small>{coverage === null ? "Aguardando agentes" : "coleta ativa"}</small>
          </div>
        </div>
        <div className="command-core-caption">
          <Activity aria-hidden="true" />
          <span>Ritmo operacional</span>
          <strong>{online ? "EM CURSO" : "SEM SINAL RECENTE"}</strong>
        </div>
      </section>

      <div className="command-side-telemetry command-side-right">
        <TelemetryLabel
          label="Agentes online"
          value={formatNumber(online)}
          detail={`${formatNumber(agents)} identidade(s) real(is)`}
          tone="healthy"
        />
        <div className="command-dual-signal">
          <TelemetryLabel
            label="Atrasados"
            value={formatNumber(delayed)}
            detail="5–30 min"
            tone={delayed ? "warning" : "healthy"}
          />
          <TelemetryLabel
            label="Offline"
            value={formatNumber(offline)}
            detail="mais de 30 min"
            tone={offline ? "critical" : "healthy"}
          />
        </div>
      </div>

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
        eyebrow="Fluxo temporal"
        title="Pulso operacional"
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
        eyebrow="Últimas leituras"
        title="Sinais da operação"
        className="command-span-4"
      >
        <div className="command-event-stream">
          {snapshot.activity
            .slice(-8)
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
        eyebrow="Sem ranking individual"
        title="Equipes por unidade operacional"
        detail="atividade agregada"
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
                  <strong>{active}</strong><span>pessoas ativas</span>
                  <strong>{events}</strong><span>eventos 24h</span>
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
        eyebrow="Contexto operacional"
        title="Aplicações em uso"
        detail="janela de 24 horas"
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
        eyebrow="Distribuição"
        title="Categorias observadas"
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
          <p>Unidade operacional 0{index + 1}</p>
          <dl>
            <div><dt>Pessoas</dt><dd>{formatNumber(site.active_people)}</dd></div>
            <div><dt>Eventos 24h</dt><dd>{formatNumber(site.events_24h)}</dd></div>
            <div><dt>Agentes</dt><dd>Sem vínculo de filial</dd></div>
          </dl>
          <StatusMark status={text(site.status, "unknown")} />
        </article>
      ))}
    </div>
  );
}

function WorkforceCollection({ snapshot }: { snapshot: WallboardSnapshot }) {
  return (
    <div className="command-scene-grid">
      <CommandFrame
        eyebrow="Telemetria de endpoint"
        title="Saúde da coleta"
        detail={`${snapshot.agents.length} agente(s) real(is)`}
        className="command-span-8"
      >
        <div className="command-agent-list">
          {snapshot.agents.map((agent) => (
            <article key={agent.id}>
              <div className="command-agent-icon"><RadioTower /></div>
              <div>
                <h3>{agent.hostname}</h3>
                <p>{agent.profile} · {agent.operatingSystem}</p>
              </div>
              <dl>
                <div><dt>Versão</dt><dd>{agent.agentVersion ?? "não informada"}</dd></div>
                <div><dt>Fila</dt><dd>{agent.queueDepth}</dd></div>
                <div><dt>Política</dt><dd>{agent.policyStatus}</dd></div>
                <div><dt>Último contato</dt><dd>{formatMoment(agent.lastSeenAt)}</dd></div>
              </dl>
              <StatusMark status={agent.effectiveStatus} />
            </article>
          ))}
        </div>
        {!snapshot.agents.length ? (
          <HonestEmpty title="Aguardando agente" detail="Nenhuma identidade real está ativa." />
        ) : null}
      </CommandFrame>
      <CommandFrame eyebrow="Cobertura" title="Qualidade da sessão" className="command-span-4">
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
          <span>agentes comunicando</span>
        </div>
        <div className="command-signal-legend">
          <span><i className="is-healthy" />online</span>
          <span><i className="is-warning" />atrasado</span>
          <span><i className="is-critical" />offline</span>
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
