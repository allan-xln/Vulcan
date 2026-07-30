"use client";

import { AlertTriangle, CheckCircle2, CircleDashed, Radio } from "lucide-react";
import { ReactNode } from "react";

export function numeric(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function kpi(
  values: Record<string, number | string | null>,
  camel: string,
  snake: string
) {
  return values[camel] ?? values[snake] ?? null;
}

export function formatNumber(value: unknown, suffix = "") {
  if (value === null || value === undefined || value === "") return "Sem coleta";
  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? `${parsed.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}${suffix}`
    : `${String(value)}${suffix}`;
}

export function formatMoment(value: unknown, compact = false) {
  if (typeof value !== "string") return "sem coleta";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "sem coleta";
  return date.toLocaleString("pt-BR", {
    timeZone: "America/Sao_Paulo",
    ...(compact
      ? { hour: "2-digit", minute: "2-digit" }
      : { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
  });
}

export function text(value: unknown, fallback = "Não informado") {
  return typeof value === "string" && value.trim() ? value : fallback;
}

export function statusClass(status: string) {
  if (["online", "ok", "ready", "connected", "active", "live"].includes(status)) {
    return "is-healthy";
  }
  if (["degraded", "warning", "investigating", "monitoring", "delayed", "stale"].includes(status)) {
    return "is-warning";
  }
  if (["offline", "critical", "error", "unavailable", "failed"].includes(status)) {
    return "is-critical";
  }
  return "is-unknown";
}

export function TelemetryLabel({
  label,
  value,
  detail,
  tone = "identity"
}: {
  label: string;
  value: ReactNode;
  detail: string;
  tone?: "identity" | "healthy" | "warning" | "critical" | "cold";
}) {
  return (
    <div className={`command-telemetry command-tone-${tone}`}>
      <span className="command-corner command-corner-nw" />
      <span className="command-corner command-corner-se" />
      <p className="command-eyebrow">{label}</p>
      <strong className="command-telemetry-value">{value}</strong>
      <span className="command-telemetry-detail">{detail}</span>
    </div>
  );
}

export function CommandFrame({
  title,
  eyebrow,
  detail,
  children,
  className = ""
}: {
  title: string;
  eyebrow?: string;
  detail?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`command-frame ${className}`}>
      <span className="command-frame-line" />
      <header className="command-frame-header">
        <div>
          {eyebrow ? <p className="command-eyebrow">{eyebrow}</p> : null}
          <h2>{title}</h2>
        </div>
        {detail ? <span>{detail}</span> : null}
      </header>
      <div className="command-frame-body">{children}</div>
    </section>
  );
}

export function StatusMark({ status, label }: { status: string; label?: string }) {
  const className = statusClass(status);
  return (
    <span className={`command-status ${className}`}>
      <span className="command-status-dot" />
      {label ?? status}
    </span>
  );
}

export function HonestEmpty({
  title,
  detail,
  state = "empty"
}: {
  title: string;
  detail: string;
  state?: "empty" | "healthy" | "warning";
}) {
  const Icon =
    state === "healthy" ? CheckCircle2 : state === "warning" ? AlertTriangle : CircleDashed;
  return (
    <div className={`command-empty command-empty-${state}`}>
      <Icon aria-hidden="true" />
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  );
}

export function DataOriginBadge() {
  return (
    <span className="command-data-origin">
      <Radio aria-hidden="true" />
      dados reais
    </span>
  );
}

