"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity,
  BellRing,
  Brain,
  Building2,
  CheckCircle2,
  Command,
  DatabaseZap,
  Flame,
  Gauge,
  Layers3,
  LogOut,
  Lock,
  Mail,
  MessageCircle,
  Network,
  Save,
  RadioTower,
  ShieldCheck,
  Sparkles,
  UserRound,
  X,
  Zap
} from "lucide-react";
import type { Session } from "@supabase/supabase-js";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { getSupabaseClient, isMockAuthEnabled, isSupabaseAuthAvailable } from "@/lib/supabase";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";
const DEMO_TENANT_ID = process.env.NEXT_PUBLIC_DEMO_TENANT_ID ?? "00000000-0000-0000-0000-000000000301";
const DEMO_ADMIN_EMAIL = process.env.NEXT_PUBLIC_DEMO_ADMIN_EMAIL ?? "admin@vulcan.local";
const DEMO_ADMIN_PASSWORD = process.env.NEXT_PUBLIC_DEMO_ADMIN_PASSWORD ?? "VulcanAdmin123!";
const MOCK_AUTH = isMockAuthEnabled();
const SUPABASE_AUTH_READY = isSupabaseAuthAvailable();
const LOCAL_TEST_AUTH_READY =
  process.env.NEXT_PUBLIC_LOCAL_TEST_AUTH !== "false" && process.env.NEXT_PUBLIC_ENVIRONMENT !== "production";
const LOCAL_AUTH_READY = MOCK_AUTH || LOCAL_TEST_AUTH_READY;

type ViewKey = "dashboard" | "hierarchy" | "metrics" | "insights" | "notifications" | "settings";

type Metric = {
  id: string;
  label: string;
  value: string;
  trend: string;
  tone: "positive" | "warning" | "critical" | "neutral";
};

type Insight = {
  id: string;
  title: string;
  impact: "high" | "medium" | "low";
  summary: string;
  recommendation: string;
  automationSavingsHours: number;
};

type NotificationItem = {
  id: string;
  channel: "system" | "push" | "windows" | "whatsapp" | "email";
  status: "queued" | "sent" | "failed" | "ready" | "mocked" | "missing_credentials" | "disabled";
  title: string;
  message: string;
  createdAt: string;
  recipient?: string | null;
  attempts?: number;
  error?: string | null;
  notificationType?: string | null;
};

type Device = {
  id: string;
  ownerMembershipId?: string | null;
  owner: string;
  hostname: string;
  os: string;
  status: string;
  lastSeenAt: string;
  collectionQuality?: string | null;
  queueDepth?: number | null;
  lastError?: string | null;
  localIp?: string | null;
  agentVersion?: string | null;
};

type OperationalMetric = {
  id: string;
  tenantId: string;
  membershipId?: string | null;
  departmentId?: string | null;
  metricKey: string;
  metricLabel: string;
  valueNumeric?: number | null;
  valueText?: string | null;
  periodStart: string;
  periodEnd: string;
};

type OperationalAppBreakdown = {
  app: string;
  category: string;
  activeSeconds: number;
  idleSeconds: number;
  events: number;
  contextSwitches: number;
  percent: number;
  lastSeenAt?: string | null;
  focusLabel: string;
};

type OperationalWindowBreakdown = {
  title: string;
  app: string;
  activeSeconds: number;
  events: number;
  percent: number;
  collectionNote: string;
};

type OperationalTimelinePoint = {
  label: string;
  activeSeconds: number;
  idleSeconds: number;
  unidentifiedSeconds: number;
  contextSwitches: number;
  events: number;
};

type OperationalQualitySignal = {
  device: string;
  quality: string;
  message: string;
  lastSeenAt?: string | null;
};

type OperationalIntelligence = {
  generatedAt: string;
  periodLabel: string;
  totalEvents: number;
  totalActiveSeconds: number;
  totalIdleSeconds: number;
  unidentifiedSeconds: number;
  trackedSeconds: number;
  idleRate: number;
  focusScore: number;
  distractionScore: number;
  contextSwitches: number;
  contextSwitchesPerHour: number;
  longestFocusSeconds: number;
  fragmentedSeconds: number;
  currentActivity: string;
  aiSummary: string;
  aiRecommendations: string[];
  topApps: OperationalAppBreakdown[];
  topWindows: OperationalWindowBreakdown[];
  timeline: OperationalTimelinePoint[];
  qualitySignals: OperationalQualitySignal[];
};

type HierarchyNode = {
  id: string;
  tenantId: string;
  userId: string | null;
  parentId: string | null;
  name: string;
  title: string;
  department: string;
  email: string;
  phone?: string | null;
  whatsapp?: string | null;
  hierarchyLevel: number;
  directReports: number;
  visibleScope: "self" | "subtree" | "tenant" | "global";
};

type SupabaseStatus = {
  configured: boolean;
  projectRef: string | null;
  urlConfigured: boolean;
  restUrlConfigured: boolean;
  publishableKeyConfigured: boolean;
  anonKeyConfigured: boolean;
  serviceRoleConfigured: boolean;
  databaseUrlConfigured: boolean;
  restReachable: boolean | null;
  databaseReachable: boolean | null;
  authProvider: string;
  requiredItems: string[];
};

type WhatsAppStatus = {
  rootChannelEnabled: boolean;
  rootChannelName: string;
  rootChannelNumber: string | null;
  provider: string;
  connected: boolean;
  status: string;
  qrRequired: boolean;
  qrCode: string | null;
  lastConnectionAt: string | null;
  lastSyncAt: string | null;
  logs: string[];
};

type EmailProviderStatus = {
  provider: string;
  configured: boolean;
  canSend: boolean;
  canRead: boolean;
  status: string;
  message: string;
  requiredItems: string[];
  lastCheckedAt: string;
};

type NotificationSchedule = {
  id: string;
  name: string;
  recurrence: string;
  timezone: string;
  daysOfWeek: string[];
  times: string[];
  reportType: string;
  recipients: string[];
  channels: string[];
  enabled: boolean;
};

type ReportTemplate = {
  id: string;
  name: string;
  description: string;
  cadence: string;
  channels: string[];
  enabled: boolean;
};

type AIStatus = {
  provider: string;
  openaiConfigured: boolean;
  llamaConfigured: boolean;
  llamaProvider: string;
  complexModel: string;
  operationalModel: string;
  routePolicy: string;
};

const fallbackMetrics: Metric[] = [
  { id: "active-users", label: "Usuários ativos", value: "148", trend: "+12% vs ontem", tone: "positive" },
  { id: "events", label: "Eventos processados", value: "42,8 mil", trend: "+8,4% em 24h", tone: "neutral" },
  { id: "bottlenecks", label: "Gargalos detectados", value: "17", trend: "5 críticos", tone: "warning" },
  { id: "insights", label: "Insights de IA", value: "63", trend: "11 de alto impacto", tone: "positive" },
  { id: "automation", label: "Potencial de automação", value: "219h", trend: "estimativa mensal", tone: "critical" }
];

const emptyOperationalIntelligence: OperationalIntelligence = {
  generatedAt: new Date(0).toISOString(),
  periodLabel: "Últimas 24 horas",
  totalEvents: 0,
  totalActiveSeconds: 0,
  totalIdleSeconds: 0,
  unidentifiedSeconds: 0,
  trackedSeconds: 0,
  idleRate: 0,
  focusScore: 0,
  distractionScore: 0,
  contextSwitches: 0,
  contextSwitchesPerHour: 0,
  longestFocusSeconds: 0,
  fragmentedSeconds: 0,
  currentActivity: "Aguardando eventos do agente",
  aiSummary: "Ainda não há volume suficiente de eventos reais para gerar diagnóstico operacional.",
  aiRecommendations: ["Instale ou reinicie o Vulcan Agent e aguarde alguns minutos de uso real."],
  topApps: [],
  topWindows: [],
  timeline: [],
  qualitySignals: []
};

const liveTestMetrics: Metric[] = [
  { id: "active-users", label: "Usuários ativos", value: "1", trend: "escopo do teste", tone: "neutral" },
  { id: "events", label: "Eventos processados", value: "0", trend: "aguardando agente", tone: "neutral" },
  { id: "bottlenecks", label: "Gargalos detectados", value: "0", trend: "somente dados reais", tone: "neutral" },
  { id: "insights", label: "Insights de IA", value: "0", trend: "gerados por métricas reais", tone: "neutral" },
  { id: "automation", label: "Potencial de automação", value: "0h", trend: "estimativa mensal", tone: "neutral" }
];

const fallbackInsights: Insight[] = [
  {
    id: "ins-001",
    title: "Ciclo de faturamento financeiro está desacelerando",
    impact: "high",
    summary: "O tempo médio do fluxo de faturamento aumentou 38% nas últimas 24 horas, concentrado no ERP e em repasses por planilha.",
    recommendation: "Priorize automação de validação de notas e reduza redigitação entre planilhas e ERP.",
    automationSavingsHours: 27
  },
  {
    id: "ins-002",
    title: "Troca de contexto está criando retrabalho oculto",
    impact: "medium",
    summary: "Usuários financeiros alternaram entre e-mail, planilhas e ERP 420 vezes no último dia útil.",
    recommendation: "Crie uma fila guiada para exceções e consolide checagens de status no fluxo do ERP.",
    automationSavingsHours: 14
  },
  {
    id: "ins-003",
    title: "Aprovações de compras formam fila recorrente",
    impact: "high",
    summary: "As janelas de espera por aprovação se concentram no fim da tarde e atrasam etapas operacionais posteriores.",
    recommendation: "Implemente escalonamento automático e uma janela diária de 15 minutos para aprovações.",
    automationSavingsHours: 19
  }
];

const fallbackNotifications: NotificationItem[] = [
  {
    id: "ntf-001",
    channel: "windows",
    status: "mocked",
    title: "Alerta Vulcan",
    message: "O setor financeiro apresentou aumento de 38% no tempo médio do processo de faturamento nas últimas 24 horas.",
    createdAt: "2026-06-02T21:30:00Z"
  },
  {
    id: "ntf-002",
    channel: "whatsapp",
    status: "missing_credentials",
    title: "Insight Vulcan",
    message: "Foram identificadas aproximadamente 1.200 tarefas repetitivas nesta semana. Potencial estimado: 27 horas mensais.",
    createdAt: "2026-06-02T21:12:00Z"
  },
  {
    id: "ntf-003",
    channel: "email",
    status: "missing_credentials",
    title: "Resumo executivo semanal",
    message: "Resumo semanal preparado para gestores com gargalos, oportunidades e recomendações.",
    createdAt: "2026-06-02T20:45:00Z"
  }
];

const fallbackDevices: Device[] = [
  { id: "1", ownerMembershipId: "22222222-2222-2222-2222-222222222222", owner: "Líder Financeiro", hostname: "ACME-FIN-042", os: "Windows 11", status: "online", lastSeenAt: "2026-06-02T21:45:00Z", collectionQuality: "high", queueDepth: 0 },
  { id: "2", ownerMembershipId: "33333333-3333-3333-3333-333333333333", owner: "Operações", hostname: "ACME-OPS-119", os: "Windows 11", status: "syncing", lastSeenAt: "2026-06-02T21:41:00Z", collectionQuality: "medium", queueDepth: 2 }
];

const fallbackHierarchy: HierarchyNode[] = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    tenantId: "00000000-0000-0000-0000-000000000301",
    userId: "11111111-1111-1111-1111-111111111111",
    parentId: null,
    name: "Administrador Local Vulcan",
    title: "Administrador do tenant",
    department: "Operações Executivas",
    email: "admin@vulcan.local",
    phone: "+1 555 0100",
    whatsapp: "+1 555 0100",
    hierarchyLevel: 0,
    directReports: 2,
    visibleScope: "tenant"
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    tenantId: "00000000-0000-0000-0000-000000000301",
    userId: "22222222-2222-2222-2222-222222222222",
    parentId: "11111111-1111-1111-1111-111111111111",
    name: "Líder Financeiro",
    title: "Supervisor Financeiro",
    department: "Financeiro",
    email: "finance@acme.example",
    phone: "+1 555 0101",
    whatsapp: "+1 555 0101",
    hierarchyLevel: 2,
    directReports: 1,
    visibleScope: "subtree"
  },
  {
    id: "33333333-3333-3333-3333-333333333333",
    tenantId: "00000000-0000-0000-0000-000000000301",
    userId: "33333333-3333-3333-3333-333333333333",
    parentId: "22222222-2222-2222-2222-222222222222",
    name: "Operador de Faturamento",
    title: "Analista de Faturamento",
    department: "Financeiro",
    email: "billing@acme.example",
    phone: "+1 555 0102",
    whatsapp: "+1 555 0102",
    hierarchyLevel: 3,
    directReports: 0,
    visibleScope: "self"
  }
];

const fallbackSupabaseStatus: SupabaseStatus = {
  configured: false,
  projectRef: null,
  urlConfigured: false,
  restUrlConfigured: false,
  publishableKeyConfigured: false,
  anonKeyConfigured: false,
  serviceRoleConfigured: false,
  databaseUrlConfigured: false,
  restReachable: null,
  databaseReachable: null,
  authProvider: "local",
  requiredItems: []
};

const fallbackWhatsAppStatus: WhatsAppStatus = {
  rootChannelEnabled: false,
  rootChannelName: "Notificações Vulcan",
  rootChannelNumber: null,
  provider: "lanchat",
  connected: false,
  status: "pendente",
  qrRequired: false,
  qrCode: null,
  lastConnectionAt: null,
  lastSyncAt: null,
  logs: ["Canal WhatsApp raiz aguardando configuração no backend."]
};

const fallbackEmailStatuses: EmailProviderStatus[] = [
  {
    provider: "smtp",
    configured: false,
    canSend: false,
    canRead: false,
    status: "pendente",
    message: "Configure SMTP para envio de e-mail.",
    requiredItems: ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "EMAIL_FROM"],
    lastCheckedAt: new Date(0).toISOString()
  }
];

const fallbackAIStatus: AIStatus = {
  provider: "hybrid",
  openaiConfigured: false,
  llamaConfigured: false,
  llamaProvider: "openai-compatible",
  complexModel: "GPT executivo pendente",
  operationalModel: "Llama operacional pendente",
  routePolicy: "operacional -> Llama | executivo -> GPT"
};

const fallbackSchedules: NotificationSchedule[] = [
  {
    id: "alertas-tempo-real",
    name: "Alertas críticos em tempo real",
    recurrence: "Imediatamente",
    timezone: "America/Sao_Paulo",
    daysOfWeek: ["segunda", "terça", "quarta", "quinta", "sexta"],
    times: ["tempo real"],
    reportType: "alerta_tempo_real",
    recipients: ["Supervisor", "Gerente", "Diretor"],
    channels: ["sistema", "windows", "whatsapp", "email"],
    enabled: true
  }
];

const fallbackReportTemplates: ReportTemplate[] = [
  {
    id: "resumo-operacional-diario",
    name: "Resumo Operacional Diário",
    description: "Principais métricas, gargalos, agentes offline e alertas.",
    cadence: "Diário",
    channels: ["whatsapp", "email", "sistema"],
    enabled: true
  }
];

const trendData = [
  { name: "Seg", events: 2600, bottlenecks: 9, automation: 32 },
  { name: "Ter", events: 3400, bottlenecks: 11, automation: 41 },
  { name: "Qua", events: 4200, bottlenecks: 15, automation: 46 },
  { name: "Qui", events: 5100, bottlenecks: 18, automation: 53 },
  { name: "Sex", events: 4800, bottlenecks: 13, automation: 58 },
  { name: "Sáb", events: 2200, bottlenecks: 6, automation: 22 },
  { name: "Dom", events: 1800, bottlenecks: 4, automation: 18 }
];

const appUsage = [
  { app: "ERP", minutes: 420 },
  { app: "E-mail", minutes: 310 },
  { app: "Planilhas", minutes: 280 },
  { app: "CRM", minutes: 190 },
  { app: "Portal", minutes: 160 }
];

const departments = [
  { name: "Financeiro", score: 76 },
  { name: "Operações", score: 68 },
  { name: "Comercial", score: 82 },
  { name: "Suporte", score: 71 }
];

const weekdayOrder = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
const weekdayMap: Record<number, string> = { 0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sáb" };
const traceRows = Array.from({ length: 7 }, (_, index) => ({ top: 10 + index * 12, delay: index * 0.45, width: 14 + (index % 3) * 6 }));
const verticalScans = Array.from({ length: 5 }, (_, index) => ({ left: 12 + index * 18, delay: index * 0.55 }));
const signalNodes = Array.from({ length: 12 }, (_, index) => ({
  left: 4 + ((index * 17) % 92),
  top: 6 + ((index * 29) % 86),
  delay: index * 0.13,
  scale: 0.72 + (index % 5) * 0.08
}));

function emptyFlowData() {
  return weekdayOrder.map((name) => ({ name, events: 0, bottlenecks: 0, automation: 0 }));
}

function buildFlowData(operationalMetrics: OperationalMetric[], allowDemoFallback: boolean) {
  if (!operationalMetrics.length) {
    return allowDemoFallback ? trendData : emptyFlowData();
  }
  const totals = new Map(weekdayOrder.map((day) => [day, 0]));
  operationalMetrics
    .filter((metric) => metric.metricKey === "app_usage_seconds")
    .forEach((metric) => {
      const date = new Date(metric.periodStart);
      const day = weekdayMap[date.getUTCDay()];
      totals.set(day, (totals.get(day) ?? 0) + Number(metric.valueNumeric ?? 0));
    });
  return weekdayOrder.map((name) => ({
    name,
    events: Math.round(totals.get(name) ?? 0),
    bottlenecks: 0,
    automation: 0
  }));
}

function buildAppUsageData(operationalMetrics: OperationalMetric[], allowDemoFallback: boolean) {
  if (!operationalMetrics.length) {
    return allowDemoFallback ? appUsage : [];
  }
  const totals = new Map<string, number>();
  operationalMetrics
    .filter((metric) => metric.metricKey === "app_usage_seconds")
    .forEach((metric) => {
      const label = metric.metricLabel || "Desconhecido";
      totals.set(label, (totals.get(label) ?? 0) + Number(metric.valueNumeric ?? 0));
    });
  const rows = [...totals.entries()]
    .map(([app, seconds]) => ({ app, minutes: Math.max(1, Math.round(seconds / 60)) }))
    .sort((a, b) => b.minutes - a.minutes)
    .slice(0, 8);
  return rows.length ? rows : allowDemoFallback ? appUsage : [];
}

function sumMetric(operationalMetrics: OperationalMetric[], metricKey: string) {
  return operationalMetrics
    .filter((metric) => metric.metricKey === metricKey)
    .reduce((total, metric) => total + Number(metric.valueNumeric ?? 0), 0);
}

function buildTopUsers(operationalMetrics: OperationalMetric[], hierarchy: HierarchyNode[]) {
  const nodeById = new Map(hierarchy.map((node) => [node.id, node]));
  const rows = new Map<string, { id: string; name: string; title: string; active: number; idle: number; switches: number }>();

  operationalMetrics.forEach((metric) => {
    if (!metric.membershipId) {
      return;
    }
    const node = nodeById.get(metric.membershipId);
    const row = rows.get(metric.membershipId) ?? {
      id: metric.membershipId,
      name: node?.name ?? "Usuário sem cadastro",
      title: node?.title ?? "Sem cargo",
      active: 0,
      idle: 0,
      switches: 0
    };
    const value = Number(metric.valueNumeric ?? 0);
    if (metric.metricKey === "active_seconds") {
      row.active += value;
    }
    if (metric.metricKey === "idle_seconds") {
      row.idle += value;
    }
    if (metric.metricKey === "context_switch_count") {
      row.switches += value;
    }
    rows.set(metric.membershipId, row);
  });

  return [...rows.values()]
    .sort((a, b) => b.active - a.active)
    .slice(0, 6);
}

function buildDepartmentPerformance(operationalMetrics: OperationalMetric[], hierarchy: HierarchyNode[], allowDemoFallback: boolean) {
  const departmentByMembership = new Map(hierarchy.map((node) => [node.id, node.department]));
  const rows = new Map<string, { name: string; active: number; idle: number; switches: number }>();

  operationalMetrics.forEach((metric) => {
    const department = metric.membershipId ? departmentByMembership.get(metric.membershipId) : null;
    const name = department || metric.departmentId || "Sem departamento";
    const row = rows.get(name) ?? { name, active: 0, idle: 0, switches: 0 };
    const value = Number(metric.valueNumeric ?? 0);
    if (metric.metricKey === "active_seconds") {
      row.active += value;
    }
    if (metric.metricKey === "idle_seconds") {
      row.idle += value;
    }
    if (metric.metricKey === "context_switch_count") {
      row.switches += value;
    }
    rows.set(name, row);
  });

  const data = [...rows.values()]
    .map((row) => {
      const tracked = row.active + row.idle;
      const score = tracked ? Math.max(12, Math.min(96, Math.round((row.active / tracked) * 100 - row.switches / 18))) : 0;
      return { ...row, score };
    })
    .sort((a, b) => b.active - a.active)
    .slice(0, 6);

  return data.length ? data : allowDemoFallback ? departments.map((department) => ({ ...department, active: department.score * 240, idle: (100 - department.score) * 90, switches: 0 })) : [];
}

function buildHeatmap(operationalIntelligence: OperationalIntelligence) {
  return operationalIntelligence.timeline.map((point) => {
    const total = point.activeSeconds + point.idleSeconds + point.unidentifiedSeconds;
    const intensity = total ? Math.min(100, Math.round((point.activeSeconds / Math.max(total, 1)) * 100)) : 0;
    return {
      label: point.label,
      activeMinutes: Math.round(point.activeSeconds / 60),
      idleMinutes: Math.round(point.idleSeconds / 60),
      switches: point.contextSwitches,
      intensity
    };
  });
}

function buildLossBreakdown({
  idleSeconds,
  contextSwitches,
  pendingQueue,
  offlineDevices,
  qualityIssues,
  automationHours
}: {
  idleSeconds: number;
  contextSwitches: number;
  pendingQueue: number;
  offlineDevices: number;
  qualityIssues: number;
  automationHours: number;
}) {
  const idleHours = idleSeconds / 3600;
  const contextHours = contextSwitches * 0.018;
  const offlineHours = offlineDevices * 1.4;
  const queueHours = pendingQueue * 0.08;
  const qualityHours = qualityIssues * 1.1;
  const manualHours = Math.max(automationHours * 0.42, 0);
  return [
    {
      label: "Ociosidade operacional",
      cause: "Tempo sem atividade produtiva detectado pelo agente.",
      impact: idleHours,
      money: idleHours * 95,
      action: "Revisar carga, fila de trabalho e janelas de espera."
    },
    {
      label: "Troca de contexto",
      cause: "Alternância constante entre sistemas aumenta retrabalho.",
      impact: contextHours,
      money: contextHours * 95,
      action: "Consolidar etapas repetidas em fluxo guiado."
    },
    {
      label: "Processos manuais",
      cause: "Tarefas repetitivas aparecem como automação possível.",
      impact: manualHours,
      money: manualHours * 95,
      action: "Priorizar automação com maior retorno e menor complexidade."
    },
    {
      label: "Agentes offline ou fila alta",
      cause: "Dispositivo sem sync reduz visibilidade gerencial.",
      impact: offlineHours + queueHours,
      money: (offlineHours + queueHours) * 95,
      action: "Reinstalar agente, reduzir lote ou validar conectividade."
    },
    {
      label: "Coleta limitada",
      cause: "Sistema operacional bloqueou detalhes finos de janela/app.",
      impact: qualityHours,
      money: qualityHours * 95,
      action: "Ajustar política, ambiente gráfico ou orientação do usuário."
    }
  ].filter((item) => item.impact > 0 || item.money > 0);
}

function buildRecommendedActions(
  insights: Insight[],
  operationalIntelligence: OperationalIntelligence,
  pendingNotifications: number,
  financialSavings: number
) {
  const insightActions = insights.slice(0, 3).map((insight, index) => ({
    id: `insight-action-${insight.id}`,
    title: insight.recommendation,
    impact: `${insight.automationSavingsHours}h potenciais`,
    urgency: insight.impact === "high" ? "Alta" : insight.impact === "medium" ? "Média" : "Baixa",
    scope: index === 0 ? "Financeiro" : index === 1 ? "Backoffice" : "Operações",
    owner: index === 0 ? "Gerente operacional" : index === 1 ? "Supervisor" : "Coordenação",
    money: insight.automationSavingsHours * 95
  }));
  const aiActions = operationalIntelligence.aiRecommendations.slice(0, 2).map((recommendation, index) => ({
    id: `ai-action-${index}`,
    title: recommendation,
    impact: "Ação preventiva",
    urgency: operationalIntelligence.distractionScore > 45 ? "Alta" : "Média",
    scope: "Operação atual",
    owner: "Gestor do turno",
    money: Math.max(financialSavings * 0.12, 0)
  }));
  const notificationAction = pendingNotifications
    ? [{
        id: "notification-action",
        title: "Configurar canais pendentes para alertas chegarem fora do painel.",
        impact: `${pendingNotifications} alerta${pendingNotifications === 1 ? "" : "s"} pendente${pendingNotifications === 1 ? "" : "s"}`,
        urgency: "Alta",
        scope: "Notificações",
        owner: "Administrador",
        money: 0
      }]
    : [];
  return [...insightActions, ...aiActions, ...notificationAction].slice(0, 6);
}

function buildBottlenecks(insights: Insight[], appUsageData: { app: string; minutes: number; category?: string; percent?: number }[], departments: { name: string; score: number; active?: number; idle?: number }[]) {
  const insightRows = insights.slice(0, 3).map((insight, index) => ({
    id: `bottleneck-${insight.id}`,
    system: index === 0 ? "ERP / planilhas" : index === 1 ? "E-mail / CRM" : "Portal de aprovações",
    sector: departments[index]?.name ?? (index === 0 ? "Financeiro" : "Operações"),
    affected: index === 0 ? "Equipe financeira" : index === 1 ? "Backoffice" : "Gestores",
    time: `${insight.automationSavingsHours}h/mês`,
    severity: insight.impact === "high" ? "crítico" : "atenção",
    trend: insight.impact === "high" ? "subindo" : "estável",
    recommendation: insight.recommendation
  }));
  const appRows = appUsageData.slice(0, 2).map((app, index) => ({
    id: `app-bottleneck-${app.app}`,
    system: app.app,
    sector: departments[index]?.name ?? "Operações",
    affected: `${Math.max(2, index + 3)} pessoa${index === 0 ? "s" : "s"}`,
    time: `${app.minutes}min analisados`,
    severity: index === 0 ? "alto uso" : "monitorar",
    trend: index === 0 ? "concentrado" : "normal",
    recommendation: "Validar se o tempo no sistema é trabalho produtivo ou espera operacional."
  }));
  return [...insightRows, ...appRows].slice(0, 5);
}

function buildAutomationOpportunities(insights: Insight[], automationHours: number) {
  const rows = insights.map((insight, index) => ({
    id: `automation-${insight.id}`,
    process: index === 0 ? "Validação de faturamento" : index === 1 ? "Triagem de exceções" : "Aprovação e escalonamento",
    frequency: index === 0 ? "diária" : index === 1 ? "múltiplas vezes ao dia" : "semanal",
    wasted: `${insight.automationSavingsHours}h/mês`,
    suggestion: insight.recommendation,
    roi: formatMoneyBRL(insight.automationSavingsHours * 95),
    complexity: index === 0 ? "média" : index === 1 ? "baixa" : "média"
  }));
  if (rows.length) {
    return rows;
  }
  return [{
    id: "automation-empty",
    process: "Mapeamento inicial",
    frequency: "após coleta",
    wasted: `${automationHours}h/mês`,
    suggestion: "Rodar agentes por alguns dias para ranquear processos repetitivos.",
    roi: formatMoneyBRL(automationHours * 95),
    complexity: "baixa"
  }];
}

function buildOnboardingChecklist({
  supabaseStatus,
  hierarchy,
  devices,
  whatsAppStatus,
  emailStatuses,
  aiStatus,
  schedules
}: {
  supabaseStatus: SupabaseStatus;
  hierarchy: HierarchyNode[];
  devices: Device[];
  whatsAppStatus: WhatsAppStatus;
  emailStatuses: EmailProviderStatus[];
  aiStatus: AIStatus;
  schedules: NotificationSchedule[];
}) {
  const emailReady = emailStatuses.some((item) => item.configured && item.canSend);
  return [
    { label: "Empresa e banco configurados", done: supabaseStatus.configured && supabaseStatus.databaseReachable !== false, detail: supabaseStatus.projectRef ?? "Supabase pendente" },
    { label: "Usuários e hierarquia", done: hierarchy.length > 1, detail: `${hierarchy.length} pessoa${hierarchy.length === 1 ? "" : "s"} na árvore` },
    { label: "Agentes conectados", done: devices.some((device) => ["online", "syncing"].includes(device.status)), detail: `${devices.length} dispositivo${devices.length === 1 ? "" : "s"}` },
    { label: "IA operacional/executiva", done: aiStatus.openaiConfigured || aiStatus.llamaConfigured, detail: aiStatus.openaiConfigured ? aiStatus.complexModel : "chaves pendentes" },
    { label: "WhatsApp de alertas", done: whatsAppStatus.connected || Boolean(whatsAppStatus.rootChannelNumber), detail: whatsAppStatus.rootChannelNumber ?? "número raiz pendente" },
    { label: "E-mail de relatórios", done: emailReady, detail: emailReady ? "envio configurado" : "SMTP/OAuth pendente" },
    { label: "Relatórios agendados", done: schedules.some((schedule) => schedule.enabled), detail: `${schedules.filter((schedule) => schedule.enabled).length} agenda${schedules.filter((schedule) => schedule.enabled).length === 1 ? "" : "s"} ativa${schedules.filter((schedule) => schedule.enabled).length === 1 ? "" : "s"}` }
  ];
}

function formatMoneyBRL(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0
  }).format(value);
}

const commands: { key: ViewKey; label: string; icon: typeof Gauge }[] = [
  { key: "dashboard", label: "Comando", icon: Gauge },
  { key: "hierarchy", label: "Hierarquia", icon: Network },
  { key: "metrics", label: "Métricas", icon: Activity },
  { key: "insights", label: "Insights", icon: Brain },
  { key: "notifications", label: "Notificações", icon: BellRing },
  { key: "settings", label: "Configurações", icon: Layers3 }
];

const commandSummary: Record<ViewKey, string> = {
  dashboard: "Pulso executivo, agentes, sinais de IA e saúde operacional.",
  hierarchy: "Organograma dinâmico com visibilidade por tenant e subárvore.",
  metrics: "Concentração de uso, setores, tendências e carga de contexto.",
  insights: "Recomendações de IA híbrida e oportunidades de automação.",
  notifications: "Sistema, Windows, WhatsApp, e-mail e agendamentos.",
  settings: "Empresa, Supabase, IA, segurança, WhatsApp, e-mail e integrações."
};

async function fetchProtected<T>(path: string, token: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${API_URL}${path}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Tenant-Id": DEMO_TENANT_ID
      }
    });
    if (!response.ok) {
      return fallback;
    }
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

function formatRelativeTime(date: Date | null, now: Date) {
  if (!date) {
    return "aguardando primeira sincronização";
  }
  const seconds = Math.max(0, Math.round((now.getTime() - date.getTime()) / 1000));
  if (seconds < 5) {
    return "agora";
  }
  if (seconds < 60) {
    return `há ${seconds} segundos`;
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `há ${minutes} minuto${minutes === 1 ? "" : "s"}`;
  }
  const hours = Math.round(minutes / 60);
  return `há ${hours} hora${hours === 1 ? "" : "s"}`;
}

function formatDuration(seconds: number) {
  const safeSeconds = Math.max(0, Math.round(seconds || 0));
  const hours = Math.floor(safeSeconds / 3600);
  const minutes = Math.floor((safeSeconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${minutes.toString().padStart(2, "0")}min`;
  }
  return `${minutes}min`;
}

function percentPt(value: number) {
  return `${Math.round((value || 0) * 100)}%`;
}

function statusPt(status: string) {
  const dictionary: Record<string, string> = {
    online: "online",
    syncing: "sincronizando",
    offline: "offline",
    ready: "pronto",
    mocked: "simulado",
    missing_credentials: "faltam credenciais",
    disabled: "desativado",
    queued: "na fila",
    sent: "enviado",
    failed: "falhou",
    oauth_pronto: "OAuth pronto",
    oauth_pendente: "OAuth pendente",
    consulta_pronta: "consulta pronta",
    consulta_pendente: "consulta pendente",
    unknown_provider: "provedor desconhecido",
    missing_destination: "destinatário ausente",
    conectado: "conectado",
    pendente: "pendente",
    aguardando_configuracao: "aguardando configuração"
  };
  return dictionary[status] ?? status;
}

function impactPt(impact: Insight["impact"]) {
  const dictionary: Record<Insight["impact"], string> = {
    high: "alto impacto",
    medium: "impacto médio",
    low: "baixo impacto"
  };
  return dictionary[impact];
}

function scopePt(scope: string) {
  const dictionary: Record<string, string> = {
    self: "próprio",
    subtree: "subárvore",
    tenant: "empresa",
    global: "global"
  };
  return dictionary[scope] ?? scope;
}

function channelPt(channel: string) {
  const dictionary: Record<string, string> = {
    system: "sistema",
    push: "push",
    windows: "Windows/agente",
    whatsapp: "WhatsApp",
    email: "e-mail"
  };
  return dictionary[channel] ?? channel;
}

function qualityPt(quality?: string | null) {
  const dictionary: Record<string, string> = {
    high: "alta",
    medium: "média",
    low: "baixa",
    blocked_by_os: "limitada pelo sistema"
  };
  return dictionary[quality ?? ""] ?? "não informada";
}

export default function HomePage() {
  const [token, setToken] = useState<string | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [authLoading, setAuthLoading] = useState(SUPABASE_AUTH_READY);
  const [authMode, setAuthMode] = useState<"supabase" | "local" | null>(null);
  const [identity, setIdentity] = useState("operador Vulcan");
  const [view, setView] = useState<ViewKey>("dashboard");
  const [loginError, setLoginError] = useState("");
  const [metrics, setMetrics] = useState<Metric[]>(fallbackMetrics);
  const [insights, setInsights] = useState<Insight[]>(fallbackInsights);
  const [notifications, setNotifications] = useState<NotificationItem[]>(fallbackNotifications);
  const [devices, setDevices] = useState<Device[]>(fallbackDevices);
  const [operationalMetrics, setOperationalMetrics] = useState<OperationalMetric[]>([]);
  const [operationalIntelligence, setOperationalIntelligence] = useState<OperationalIntelligence>(emptyOperationalIntelligence);
  const [hierarchy, setHierarchy] = useState<HierarchyNode[]>(fallbackHierarchy);
  const [supabaseStatus, setSupabaseStatus] = useState<SupabaseStatus>(fallbackSupabaseStatus);
  const [whatsAppStatus, setWhatsAppStatus] = useState<WhatsAppStatus>(fallbackWhatsAppStatus);
  const [emailStatuses, setEmailStatuses] = useState<EmailProviderStatus[]>(fallbackEmailStatuses);
  const [aiStatus, setAIStatus] = useState<AIStatus>(fallbackAIStatus);
  const [schedules, setSchedules] = useState<NotificationSchedule[]>(fallbackSchedules);
  const [reportTemplates, setReportTemplates] = useState<ReportTemplate[]>(fallbackReportTemplates);
  const [lastRefreshAt, setLastRefreshAt] = useState<Date | null>(null);
  const [now, setNow] = useState(() => new Date());

  const liveTestMode = authMode === "local" && identity.toLowerCase() === "teste";
  const highImpact = useMemo(() => insights.filter((item) => item.impact === "high").length, [insights]);
  const onlineAgents = useMemo(() => devices.filter((device) => ["online", "syncing"].includes(device.status)).length, [devices]);
  const lastSyncAt = useMemo(() => {
    const dates = [
      ...devices.map((device) => new Date(device.lastSeenAt).getTime()),
      ...operationalMetrics.map((metric) => new Date(metric.periodEnd).getTime()),
      lastRefreshAt?.getTime() ?? 0
    ].filter((value) => Number.isFinite(value) && value > 0);
    return dates.length ? new Date(Math.max(...dates)) : null;
  }, [devices, operationalMetrics, lastRefreshAt]);
  const liveStatusLabel = useMemo(() => formatRelativeTime(lastSyncAt, now), [lastSyncAt, now]);

  useEffect(() => {
    const supabase = getSupabaseClient();
    if (!supabase) {
      setAuthLoading(false);
      return;
    }

    let mounted = true;
    const sessionRestoreTimeout = window.setTimeout(() => {
      if (mounted) {
        setAuthLoading(false);
      }
    }, 4000);

    void supabase.auth.getSession().then(({ data }) => {
      if (!mounted) {
        return;
      }
      if (data.session) {
        setSession(data.session);
        setToken(data.session.access_token);
        setIdentity(data.session.user.email ?? "usuário Supabase");
        setAuthMode("supabase");
      }
      setAuthLoading(false);
    }).catch(() => {
      if (mounted) {
        setAuthLoading(false);
      }
    }).finally(() => window.clearTimeout(sessionRestoreTimeout));

    const {
      data: { subscription }
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setToken(nextSession?.access_token ?? null);
      setIdentity(nextSession?.user.email ?? "operador Vulcan");
      setAuthMode(nextSession ? "supabase" : null);
    });

    return () => {
      mounted = false;
      window.clearTimeout(sessionRestoreTimeout);
      subscription.unsubscribe();
    };
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!token) {
      return;
    }
    const metricFallback = liveTestMode ? liveTestMetrics : fallbackMetrics;
    const insightFallback = liveTestMode ? [] : fallbackInsights;
    const notificationFallback = liveTestMode ? [] : fallbackNotifications;
    const deviceFallback = liveTestMode ? [] : fallbackDevices;
    const hierarchyFallback = liveTestMode ? [] : fallbackHierarchy;

    if (liveTestMode) {
      setMetrics(liveTestMetrics);
      setInsights([]);
      setNotifications([]);
      setDevices([]);
      setOperationalMetrics([]);
      setOperationalIntelligence(emptyOperationalIntelligence);
      setHierarchy([]);
    }

    let cancelled = false;

    async function loadDashboard() {
      const [
        nextSupabaseStatus,
        nextWhatsAppStatus,
        nextEmailStatuses,
        nextAIStatus,
        nextSchedules,
        nextReportTemplates
      ] = await Promise.all([
        fetchProtected<SupabaseStatus>("/supabase/status", token!, fallbackSupabaseStatus),
        fetchProtected<WhatsAppStatus>("/integrations/whatsapp/status", token!, fallbackWhatsAppStatus),
        fetchProtected<EmailProviderStatus[]>("/integrations/email/status", token!, fallbackEmailStatuses),
        fetchProtected<AIStatus>("/ai/status", token!, fallbackAIStatus),
        fetchProtected<NotificationSchedule[]>("/notifications/schedules", token!, fallbackSchedules),
        fetchProtected<ReportTemplate[]>("/reports/templates", token!, fallbackReportTemplates)
      ]);

      if (cancelled) {
        return;
      }

      setSupabaseStatus(nextSupabaseStatus);
      setWhatsAppStatus(nextWhatsAppStatus);
      setEmailStatuses(nextEmailStatuses);
      setAIStatus(nextAIStatus);
      setSchedules(nextSchedules);
      setReportTemplates(nextReportTemplates);

      if (nextSupabaseStatus.databaseReachable === false) {
        setMetrics(metricFallback);
        setInsights(insightFallback);
        setNotifications(notificationFallback);
        setDevices(deviceFallback);
        setOperationalMetrics([]);
        setOperationalIntelligence(emptyOperationalIntelligence);
        setHierarchy(hierarchyFallback);
        setLastRefreshAt(new Date());
        return;
      }

      const [
        nextMetrics,
        nextInsights,
        nextNotifications,
        nextDevices,
        nextOperationalMetrics,
        nextOperationalIntelligence,
        nextHierarchy
      ] = await Promise.all([
        fetchProtected<Metric[]>("/metrics", token!, metricFallback),
        fetchProtected<Insight[]>("/insights", token!, insightFallback),
        fetchProtected<NotificationItem[]>("/notifications", token!, notificationFallback),
        fetchProtected<Device[]>("/devices", token!, deviceFallback),
        fetchProtected<OperationalMetric[]>("/operational-metrics", token!, []),
        fetchProtected<OperationalIntelligence>("/operational-intelligence", token!, emptyOperationalIntelligence),
        fetchProtected<HierarchyNode[]>("/hierarchy", token!, hierarchyFallback)
      ]);

      if (cancelled) {
        return;
      }

      setMetrics(nextMetrics);
      setInsights(nextInsights);
      setNotifications(nextNotifications);
      setDevices(nextDevices);
      setOperationalMetrics(nextOperationalMetrics);
      setOperationalIntelligence(nextOperationalIntelligence);
      setHierarchy(nextHierarchy);
      setLastRefreshAt(new Date());
    }

    void loadDashboard();

    return () => {
      cancelled = true;
    };
  }, [token, liveTestMode]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoginError("");
    const form = new FormData(event.currentTarget);
    const username = String(form.get("username") ?? "");
    const password = String(form.get("password") ?? "");

    if (SUPABASE_AUTH_READY && username.includes("@")) {
      const supabase = getSupabaseClient();
      const { data, error } = await supabase!.auth.signInWithPassword({ email: username, password });
      if (error || !data.session) {
        setLoginError("Supabase Auth recusou essas credenciais.");
        return;
      }
      setSession(data.session);
      setToken(data.session.access_token);
      setIdentity(data.session.user.email ?? username);
      setAuthMode("supabase");
      return;
    }

    if (!LOCAL_AUTH_READY) {
        setLoginError("Use e-mail e senha do Supabase Auth. O fallback local está desligado.");
      return;
    }

    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });

      if (!response.ok) {
        setLoginError("Credenciais locais inválidas.");
        return;
      }

      const data = (await response.json()) as { accessToken: string; user?: { name?: string; email?: string } };
      setToken(data.accessToken);
      setAuthMode("local");
      setIdentity(data.user?.name ?? data.user?.email ?? username);
      if (username.toLowerCase() === "teste") {
        setMetrics(liveTestMetrics);
        setInsights([]);
        setNotifications([]);
        setDevices([]);
        setOperationalMetrics([]);
        setOperationalIntelligence(emptyOperationalIntelligence);
        setHierarchy([]);
      }
    } catch {
      if ((username === "admin" && password === "admin") || (username === "teste" && password === "teste")) {
        setToken(username === "teste" ? "dev-vulcan-test-token" : "dev-vulcan-admin-token");
        setAuthMode("local");
        setIdentity(username === "teste" ? "teste" : "admin local de demonstração");
        if (username === "teste") {
          setMetrics(liveTestMetrics);
          setInsights([]);
          setNotifications([]);
          setDevices([]);
          setOperationalMetrics([]);
          setOperationalIntelligence(emptyOperationalIntelligence);
          setHierarchy([]);
        }
        return;
      }
      setLoginError("Backend local indisponível. Use teste/teste, admin/admin ou inicie a API.");
    }
  }

  async function handleLogout() {
    if (session) {
      await getSupabaseClient()?.auth.signOut();
    }
    setSession(null);
    setToken(null);
    setAuthMode(null);
    setIdentity("operador Vulcan");
  }

  async function handleDeviceOwnerChange(deviceId: string, ownerMembershipId: string | null) {
    if (!token) {
      return;
    }
    try {
      const response = await fetch(`${API_URL}/devices/${deviceId}/owner`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "X-Tenant-Id": DEMO_TENANT_ID
        },
        body: JSON.stringify({ tenantId: DEMO_TENANT_ID, ownerMembershipId })
      });
      if (!response.ok) {
        return;
      }
      const refreshed = await fetchProtected<Device[]>("/devices", token, liveTestMode ? [] : fallbackDevices);
      setDevices(refreshed);
    } catch {
      // A tela continua funcional mesmo se o backend local estiver fora do ar.
    }
  }

  return (
    <main className="min-h-screen overflow-hidden bg-[#070707] text-zinc-100">
      <AnimatedAtmosphere />
      <AnimatePresence mode="wait">
        {authLoading ? (
          <AuthLoading key="auth-loading" />
        ) : !token ? (
          <LoginExperience
            key="login"
            onLogin={handleLogin}
            error={loginError}
            supabaseReady={SUPABASE_AUTH_READY}
            mockAuth={LOCAL_AUTH_READY}
          />
        ) : (
          <DashboardShell
            key="dashboard"
            activeView={view}
            setView={setView}
            onLogout={handleLogout}
            identity={identity}
            authMode={authMode ?? "local"}
            metrics={metrics}
            insights={insights}
            notifications={notifications}
            devices={devices}
            operationalMetrics={operationalMetrics}
            operationalIntelligence={operationalIntelligence}
            hierarchy={hierarchy}
            supabaseStatus={supabaseStatus}
            whatsAppStatus={whatsAppStatus}
            emailStatuses={emailStatuses}
            aiStatus={aiStatus}
            schedules={schedules}
            reportTemplates={reportTemplates}
            highImpact={highImpact}
            onlineAgents={onlineAgents}
            liveStatusLabel={liveStatusLabel}
            allowDemoFallback={!liveTestMode}
            token={token}
            onDeviceOwnerChange={handleDeviceOwnerChange}
          />
        )}
      </AnimatePresence>
    </main>
  );
}

function AuthLoading() {
  return (
    <motion.section
      className="relative z-10 grid min-h-screen place-items-center px-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className="grid place-items-center gap-5">
        <motion.div
          className="grid h-24 w-24 place-items-center border border-orange-400/25 bg-black/70 shadow-[0_0_32px_rgba(249,115,22,0.14)]"
          animate={{ rotate: [0, 90, 180, 270, 360], scale: [1, 1.08, 1] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
        >
          <BrandMark size={54} />
        </motion.div>
        <p className="text-xs uppercase tracking-[0.36em] text-orange-300">restaurando sessão segura</p>
      </div>
    </motion.section>
  );
}

function AnimatedAtmosphere() {
  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden">
      <motion.div
        className="absolute inset-0 opacity-35"
        style={{
          background:
            "repeating-linear-gradient(115deg, rgba(249,115,22,0.025) 0px, rgba(249,115,22,0.025) 1px, transparent 1px, transparent 32px)"
        }}
        animate={{ x: [-40, 40, -40], y: [-18, 18, -18] }}
        transition={{ duration: 14, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute inset-x-0 top-0 h-56 bg-[linear-gradient(110deg,transparent,rgba(249,115,22,0.055),rgba(250,204,21,0.025),transparent)] blur-lg"
        animate={{ x: ["-35%", "35%", "-35%"], opacity: [0.12, 0.28, 0.12] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-0 left-0 h-72 w-full bg-[linear-gradient(0deg,rgba(249,115,22,0.045),transparent)]"
        animate={{ opacity: [0.12, 0.24, 0.12] }}
        transition={{ duration: 5.5, repeat: Infinity, ease: "easeInOut" }}
      />
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.025)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px)] bg-[size:44px_44px] opacity-22" />
      <motion.div
        className="absolute inset-0 bg-[linear-gradient(90deg,transparent,rgba(249,115,22,0.035),transparent)]"
        animate={{ x: ["-115%", "115%"], opacity: [0, 0.32, 0] }}
        transition={{ duration: 6.8, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-400 to-transparent"
        animate={{ opacity: [0.14, 0.55, 0.14] }}
        transition={{ duration: 2.8, repeat: Infinity }}
      />
      <motion.div
        className="absolute inset-x-0 top-1/2 h-px bg-orange-300/16"
        animate={{ y: [-260, 260, -260], opacity: [0, 0.42, 0] }}
        transition={{ duration: 6.2, repeat: Infinity, ease: "easeInOut" }}
      />
      {verticalScans.map((scan, index) => (
        <motion.div
          key={`vscan-${index}`}
          className="absolute top-0 h-full w-px bg-gradient-to-b from-transparent via-orange-300/16 to-transparent"
          style={{ left: `${scan.left}%` }}
          animate={{ opacity: [0.02, 0.28, 0.02], scaleY: [0.7, 1, 0.7] }}
          transition={{ duration: 3.4, repeat: Infinity, ease: "easeInOut", delay: scan.delay }}
        />
      ))}
      {traceRows.map((row, index) => (
        <motion.div
          key={`trace-${index}`}
          className="absolute h-px bg-gradient-to-r from-transparent via-orange-300/28 to-transparent"
          style={{ top: `${row.top}%`, width: `${row.width}%` }}
          animate={{ x: ["-35vw", "115vw"], opacity: [0, 0.38, 0] }}
          transition={{ duration: 5.4 + index * 0.16, repeat: Infinity, ease: "easeInOut", delay: row.delay }}
        />
      ))}
      {signalNodes.map((node, index) => (
        <motion.div
          key={`node-${index}`}
          className="absolute h-1.5 w-1.5 border border-orange-300/30 bg-black/45 shadow-[0_0_8px_rgba(249,115,22,0.25)]"
          style={{ left: `${node.left}%`, top: `${node.top}%` }}
          animate={{ opacity: [0.08, 0.45, 0.08], scale: [node.scale, node.scale + 0.24, node.scale], rotate: [0, 180, 360] }}
          transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut", delay: node.delay }}
        />
      ))}
      <motion.div
        className="absolute left-[-10%] top-[18%] h-56 w-[120%] border-y border-orange-400/10 bg-[linear-gradient(90deg,transparent,rgba(249,115,22,0.05),transparent)]"
        animate={{ rotate: [-2, 2, -2], y: [-18, 18, -18], opacity: [0.18, 0.55, 0.18] }}
        transition={{ duration: 9, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}

function BrandMark({ size, className = "" }: { size: number; className?: string }) {
  return (
    <motion.div
      className={`relative grid shrink-0 place-items-center ${className}`}
      style={{ width: size, height: size }}
      animate={{ filter: ["drop-shadow(0 0 6px rgba(249,115,22,0.18))", "drop-shadow(0 0 14px rgba(249,115,22,0.30))", "drop-shadow(0 0 6px rgba(249,115,22,0.18))"] }}
      transition={{ duration: 2.7, repeat: Infinity, ease: "easeInOut" }}
    >
      <motion.div
        className="absolute inset-0 border border-orange-300/35"
        animate={{ rotate: [0, 90, 180, 270, 360], scale: [1, 1.08, 1] }}
        transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="absolute inset-1 border border-orange-500/25"
        animate={{ rotate: [360, 270, 180, 90, 0], opacity: [0.25, 0.75, 0.25] }}
        transition={{ duration: 5, repeat: Infinity, ease: "linear" }}
      />
      <Image src="/vulcan-symbol.svg" alt="Vulcan" width={size} height={size} className="relative z-10 h-full w-full" />
    </motion.div>
  );
}

function LoginExperience({
  onLogin,
  error,
  supabaseReady,
  mockAuth
}: {
  onLogin: (event: FormEvent<HTMLFormElement>) => void;
  error: string;
  supabaseReady: boolean;
  mockAuth: boolean;
}) {
  const defaultUser = supabaseReady && !mockAuth ? DEMO_ADMIN_EMAIL : "teste";
  const defaultPassword = supabaseReady && !mockAuth ? DEMO_ADMIN_PASSWORD : "teste";

  return (
    <motion.section
      className="relative z-10 grid min-h-screen place-items-center px-6 py-10"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <div className="grid w-full max-w-6xl items-center gap-10 lg:grid-cols-[1.1fr_0.9fr]">
        <motion.div initial={{ x: -70, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ duration: 0.8 }}>
          <div className="mb-8 flex items-center gap-4">
            <BrandMark size={76} />
            <div>
              <p className="text-sm uppercase tracking-[0.48em] text-orange-300">Vulcan</p>
              <h1 className="text-5xl font-semibold tracking-tight md:text-7xl">Central de inteligência operacional</h1>
            </div>
          </div>
          <p className="max-w-2xl text-xl leading-9 text-zinc-300">
            Transformando operações em inteligência com dados reais, IA híbrida e recomendações executivas.
          </p>
          <div className="mt-10 grid max-w-2xl gap-4 sm:grid-cols-3">
            {[
              ["42,8 mil", "eventos processados"],
              ["17", "gargalos encontrados"],
              ["219h", "potencial de automação"]
            ].map(([value, label], index) => (
              <motion.div
                key={label}
                className="border border-orange-400/20 bg-zinc-950/70 p-5 shadow-[0_0_24px_rgba(249,115,22,0.08)] backdrop-blur"
                initial={{ y: 35, opacity: 0 }}
                animate={{
                  y: [0, -5, 0],
                  opacity: 1,
                  boxShadow: [
                    "0 0 18px rgba(249,115,22,0.08)",
                    "0 0 32px rgba(249,115,22,0.14)",
                    "0 0 18px rgba(249,115,22,0.08)"
                  ]
                }}
                transition={{ delay: 0.2 + index * 0.12, duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
              >
                <p className="text-3xl font-semibold text-orange-300">{value}</p>
                <p className="mt-2 text-xs uppercase tracking-[0.25em] text-zinc-500">{label}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        <motion.form
          onSubmit={onLogin}
          className="relative overflow-hidden border border-orange-400/20 bg-zinc-950/85 p-8 shadow-[0_0_42px_rgba(249,115,22,0.10)] backdrop-blur-md"
          initial={{ x: 70, opacity: 0, scale: 0.96 }}
          animate={{ x: 0, opacity: 1, scale: 1 }}
          transition={{ duration: 0.75, delay: 0.15 }}
        >
          <motion.div
            className="absolute right-0 top-8 h-px w-40 bg-gradient-to-r from-transparent via-orange-300 to-transparent"
            animate={{ x: [-90, 20, -90], opacity: [0.2, 1, 0.2] }}
            transition={{ duration: 3.6, repeat: Infinity, ease: "easeInOut" }}
          />
          <div className="relative">
            <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-orange-400/30 px-4 py-2 text-sm text-orange-200">
              <Lock className="h-4 w-4" />
              {supabaseReady ? "Acesso seguro Supabase" : "Acesso local de desenvolvimento"}
            </div>
            <h2 className="text-3xl font-semibold">Entrar no Vulcan</h2>
            <p className="mt-3 text-sm leading-6 text-zinc-400">
              {supabaseReady
                ? "Sessão Supabase Auth com acesso isolado por tenant."
                : "Autenticação local temporária para desenvolvimento isolado."}
            </p>
            <div className="mt-8 grid gap-4">
              <input
                name="username"
                defaultValue={defaultUser}
                className="h-14 border border-zinc-800 bg-black/70 px-5 text-zinc-100 outline-none transition focus:border-orange-400 focus:shadow-[0_0_16px_rgba(249,115,22,0.12)]"
                placeholder="E-mail ou usuário"
              />
              <input
                name="password"
                type="password"
                defaultValue={defaultPassword}
                className="h-14 border border-zinc-800 bg-black/70 px-5 text-zinc-100 outline-none transition focus:border-orange-400 focus:shadow-[0_0_16px_rgba(249,115,22,0.12)]"
                placeholder="Senha"
              />
            </div>
            {error ? <p className="mt-4 text-sm text-orange-300">{error}</p> : null}
            <motion.button
              type="submit"
              className="mt-8 flex h-14 w-full items-center justify-center gap-3 bg-orange-500 font-semibold text-black shadow-[0_0_22px_rgba(249,115,22,0.20)]"
              whileHover={{ scale: 1.025 }}
              whileTap={{ scale: 0.98 }}
            >
              Entrar na central
              <Flame className="h-5 w-5" />
            </motion.button>
          </div>
        </motion.form>
      </div>
    </motion.section>
  );
}

function DashboardShell({
  activeView,
  setView,
  onLogout,
  identity,
  authMode,
  metrics,
  insights,
  notifications,
  devices,
  operationalMetrics,
  operationalIntelligence,
  hierarchy,
  supabaseStatus,
  whatsAppStatus,
  emailStatuses,
  aiStatus,
  schedules,
  reportTemplates,
  highImpact,
  onlineAgents,
  liveStatusLabel,
  allowDemoFallback,
  token,
  onDeviceOwnerChange
}: {
  activeView: ViewKey;
  setView: (view: ViewKey) => void;
  onLogout: () => void;
  identity: string;
  authMode: "supabase" | "local";
  metrics: Metric[];
  insights: Insight[];
  notifications: NotificationItem[];
  devices: Device[];
  operationalMetrics: OperationalMetric[];
  operationalIntelligence: OperationalIntelligence;
  hierarchy: HierarchyNode[];
  supabaseStatus: SupabaseStatus;
  whatsAppStatus: WhatsAppStatus;
  emailStatuses: EmailProviderStatus[];
  aiStatus: AIStatus;
  schedules: NotificationSchedule[];
  reportTemplates: ReportTemplate[];
  highImpact: number;
  onlineAgents: number;
  liveStatusLabel: string;
  allowDemoFallback: boolean;
  token: string;
  onDeviceOwnerChange: (deviceId: string, ownerMembershipId: string | null) => void;
}) {
  const [commandOpen, setCommandOpen] = useState(false);

  return (
    <motion.section className="relative z-10 min-h-screen px-4 py-4 md:px-6" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <motion.div
        className="pointer-events-none fixed left-5 top-6 hidden h-[calc(100vh-3rem)] w-px bg-gradient-to-b from-transparent via-orange-400/24 to-transparent xl:block"
        animate={{ opacity: [0.12, 0.55, 0.12], scaleY: [0.86, 1, 0.86] }}
        transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="pointer-events-none fixed right-5 top-6 hidden h-[calc(100vh-3rem)] w-px bg-gradient-to-b from-transparent via-orange-400/24 to-transparent xl:block"
        animate={{ opacity: [0.55, 0.12, 0.55], scaleY: [1, 0.86, 1] }}
        transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
      />
      <div className="mx-auto min-h-[calc(100vh-2rem)] w-full max-w-[1920px]">
        <Header
          activeView={activeView}
          highImpact={highImpact}
          identity={identity}
          authMode={authMode}
          onlineAgents={onlineAgents}
          liveStatusLabel={liveStatusLabel}
          supabaseStatus={supabaseStatus}
          onOpenCommand={() => setCommandOpen(true)}
          onLogout={onLogout}
        />
        <AnimatePresence mode="wait">
          {activeView === "dashboard" && (
            <DashboardView
              key="dashboard"
              metrics={metrics}
              insights={insights}
              notifications={notifications}
              devices={devices}
              operationalMetrics={operationalMetrics}
              operationalIntelligence={operationalIntelligence}
              hierarchy={hierarchy}
              supabaseStatus={supabaseStatus}
              whatsAppStatus={whatsAppStatus}
              emailStatuses={emailStatuses}
              aiStatus={aiStatus}
              schedules={schedules}
              onlineAgents={onlineAgents}
              liveStatusLabel={liveStatusLabel}
              allowDemoFallback={allowDemoFallback}
            />
          )}
          {activeView === "hierarchy" && <HierarchyView key="hierarchy" hierarchy={hierarchy} devices={devices} onDeviceOwnerChange={onDeviceOwnerChange} />}
          {activeView === "metrics" && (
            <MetricsView
              key="metrics"
              operationalMetrics={operationalMetrics}
              operationalIntelligence={operationalIntelligence}
              liveStatusLabel={liveStatusLabel}
              allowDemoFallback={allowDemoFallback}
            />
          )}
          {activeView === "insights" && <InsightsView key="insights" insights={insights} />}
          {activeView === "notifications" && <NotificationsView key="notifications" notifications={notifications} liveStatusLabel={liveStatusLabel} schedules={schedules} />}
          {activeView === "settings" && (
            <SettingsView
              key="settings"
              supabaseStatus={supabaseStatus}
              whatsAppStatus={whatsAppStatus}
              emailStatuses={emailStatuses}
              schedules={schedules}
              reportTemplates={reportTemplates}
              token={token}
            />
          )}
        </AnimatePresence>
      </div>
      <CommandOverlay
        open={commandOpen}
        activeView={activeView}
        setView={(view) => {
          setView(view);
          setCommandOpen(false);
        }}
        onClose={() => setCommandOpen(false)}
        onLogout={onLogout}
      />
    </motion.section>
  );
}

function Header({
  activeView,
  highImpact,
  identity,
  authMode,
  onlineAgents,
  liveStatusLabel,
  supabaseStatus,
  onOpenCommand,
  onLogout
}: {
  activeView: ViewKey;
  highImpact: number;
  identity: string;
  authMode: "supabase" | "local";
  onlineAgents: number;
  liveStatusLabel: string;
  supabaseStatus: SupabaseStatus;
  onOpenCommand: () => void;
  onLogout: () => void;
}) {
  const currentCommand = commands.find((item) => item.key === activeView) ?? commands[0];
  const supabaseLabel = !supabaseStatus.configured
    ? "Supabase pendente"
    : supabaseStatus.databaseReachable === false
      ? "Supabase degradado"
      : "Supabase conectado";

  return (
    <motion.header
      className="relative mb-4 grid gap-4 overflow-hidden border border-zinc-800 bg-zinc-950/65 p-4 backdrop-blur-xl lg:grid-cols-[1fr_auto]"
      initial={{ y: -18, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
    >
      <motion.div
        className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-300 to-transparent"
        animate={{ x: ["-100%", "100%"], opacity: [0, 1, 0] }}
        transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute bottom-0 right-0 h-24 w-2/3 bg-[linear-gradient(120deg,transparent,rgba(249,115,22,0.08),transparent)]"
        animate={{ x: ["35%", "-15%", "35%"], opacity: [0.25, 0.75, 0.25] }}
        transition={{ duration: 5.8, repeat: Infinity, ease: "easeInOut" }}
      />
      <div className="flex min-w-0 gap-4">
        <div className="hidden h-16 w-16 shrink-0 place-items-center border border-orange-400/25 bg-black/60 md:grid">
          <BrandMark size={42} />
        </div>
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-[0.36em] text-orange-300">Central de Inteligência Operacional</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight md:text-5xl">Transformando operações em inteligência.</h2>
          <div className="mt-4 flex flex-wrap gap-2">
            <LiveBadge label="Tempo real ativo" detail={`Última sincronização: ${liveStatusLabel}`} />
            <LiveBadge label={`${onlineAgents} agente${onlineAgents === 1 ? "" : "s"} online`} detail="Atualizando métricas operacionais" />
          </div>
        </div>
      </div>
      <div className="flex flex-wrap items-start justify-start gap-3 lg:justify-end">
        <motion.button
          type="button"
          onClick={onOpenCommand}
          className="flex h-12 items-center gap-3 border border-orange-400/35 bg-orange-500 px-4 font-semibold text-black shadow-[0_0_18px_rgba(249,115,22,0.14)] transition hover:bg-orange-400"
          whileHover={{ y: -2, scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <Command className="h-4 w-4" />
          {currentCommand.label}
        </motion.button>
        <StatusPill icon={ShieldCheck} label="empresa isolada" />
        <StatusPill icon={Brain} label={`${highImpact} alto impacto`} />
        <StatusPill icon={DatabaseZap} label={supabaseLabel} />
        <StatusPill icon={UserRound} label={`${authMode}: ${identity}`} />
        <motion.button
          type="button"
          onClick={onLogout}
          className="grid h-12 w-12 place-items-center border border-zinc-800 bg-black/50 text-zinc-400 transition hover:border-orange-400/60 hover:text-orange-200"
          whileHover={{ y: -2, scale: 1.04 }}
          whileTap={{ scale: 0.96 }}
          aria-label="Sair"
          title="Sair"
        >
          <LogOut className="h-5 w-5" />
        </motion.button>
      </div>
    </motion.header>
  );
}

function CommandOverlay({
  open,
  activeView,
  setView,
  onClose,
  onLogout
}: {
  open: boolean;
  activeView: ViewKey;
  setView: (view: ViewKey) => void;
  onClose: () => void;
  onLogout: () => void;
}) {
  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-50 bg-black/78 p-4 backdrop-blur-xl md:p-8"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="mx-auto flex h-full max-w-6xl flex-col border border-orange-400/20 bg-zinc-950/88 p-4 shadow-[0_0_48px_rgba(249,115,22,0.10)] md:p-6"
            initial={{ scale: 0.96, y: 20, filter: "blur(10px)" }}
            animate={{ scale: 1, y: 0, filter: "blur(0px)" }}
            exit={{ scale: 0.98, y: 18, filter: "blur(8px)" }}
            transition={{ duration: 0.28 }}
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div className="flex min-w-0 items-center gap-4">
                <BrandMark size={48} />
                <div className="min-w-0">
                  <p className="text-xs uppercase tracking-[0.34em] text-orange-300">Camada de comando Vulcan</p>
                  <h3 className="mt-2 text-2xl font-semibold md:text-4xl">Visões operacionais</h3>
                </div>
              </div>
              <motion.button
                type="button"
                onClick={onClose}
                className="grid h-12 w-12 shrink-0 place-items-center border border-zinc-800 bg-black/60 text-zinc-300 transition hover:border-orange-400/60 hover:text-orange-200"
                whileHover={{ rotate: 90, scale: 1.05 }}
                whileTap={{ scale: 0.96 }}
                aria-label="Fechar camada de comando"
                title="Fechar"
              >
                <X className="h-5 w-5" />
              </motion.button>
            </div>

            <div className="grid flex-1 auto-rows-fr gap-3 overflow-y-auto md:grid-cols-2 xl:grid-cols-3">
              {commands.map((command, index) => {
                const Icon = command.icon;
                const active = activeView === command.key;
                return (
                  <motion.button
                    key={command.key}
                    type="button"
                    onClick={() => setView(command.key)}
                    className={`group relative min-h-40 overflow-hidden border p-5 text-left transition ${
                      active
                        ? "border-orange-300 bg-orange-500 text-black shadow-[0_0_24px_rgba(249,115,22,0.18)]"
                        : "border-zinc-800 bg-black/48 text-zinc-100 hover:border-orange-400/60 hover:bg-zinc-950"
                    }`}
                    initial={{ y: 28, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: index * 0.045 }}
                    whileHover={{ y: -5, scale: 1.015 }}
                    whileTap={{ scale: 0.985 }}
                  >
                    <motion.div
                      className={`absolute inset-x-0 top-0 h-px ${active ? "bg-black/35" : "bg-orange-300/50"}`}
                      animate={{ opacity: [0.2, 1, 0.2] }}
                      transition={{ duration: 2.4, repeat: Infinity, delay: index * 0.12 }}
                    />
                    <div className={`mb-8 grid h-12 w-12 place-items-center ${active ? "bg-black text-orange-300" : "bg-orange-500 text-black"}`}>
                      <Icon className="h-6 w-6" />
                    </div>
                    <p className="text-xl font-semibold">{command.label}</p>
                    <p className={`mt-3 text-sm leading-6 ${active ? "text-black/70" : "text-zinc-500"}`}>{commandSummary[command.key]}</p>
                  </motion.button>
                );
              })}
            </div>

            <div className="mt-5 flex flex-wrap justify-end gap-3">
              <motion.button
                type="button"
                onClick={onLogout}
                className="flex h-12 items-center gap-3 border border-zinc-800 bg-black/55 px-4 text-zinc-300 transition hover:border-orange-400/60 hover:text-orange-200"
                whileHover={{ y: -2 }}
                whileTap={{ scale: 0.98 }}
              >
                <LogOut className="h-4 w-4" />
                Sair
              </motion.button>
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

function HierarchyView({
  hierarchy,
  devices,
  onDeviceOwnerChange
}: {
  hierarchy: HierarchyNode[];
  devices: Device[];
  onDeviceOwnerChange: (deviceId: string, ownerMembershipId: string | null) => void;
}) {
  const [expandedNode, setExpandedNode] = useState<string | null>(null);
  const sortedNodes = [...hierarchy].sort((a, b) => a.hierarchyLevel - b.hierarchyLevel);
  const tenantScope = hierarchy.filter((node) => node.visibleScope === "tenant" || node.visibleScope === "global").length;
  const subtreeScope = hierarchy.filter((node) => node.visibleScope === "subtree").length;
  const devicesByOwner = useMemo(() => {
    const map = new Map<string, Device[]>();
    devices.forEach((device) => {
      if (!device.ownerMembershipId) {
        return;
      }
      map.set(device.ownerMembershipId, [...(map.get(device.ownerMembershipId) ?? []), device]);
    });
    return map;
  }, [devices]);
  const unassignedDevices = devices.filter((device) => !device.ownerMembershipId);

  return (
    <ViewFrame>
      <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <Panel title="Organograma de autoridade" icon={Network}>
          <div className="relative overflow-hidden border border-orange-400/10 bg-black/35 p-5">
            <motion.div
              className="absolute inset-x-0 top-0 h-px bg-orange-300/60"
              animate={{ y: [0, 360, 0], opacity: [0, 0.75, 0] }}
              transition={{ duration: 4.8, repeat: Infinity, ease: "easeInOut" }}
            />
            <div className="grid gap-4">
              {sortedNodes.length ? (
                sortedNodes.map((node, index) => (
                  <motion.div
                    key={node.id}
                    className="relative grid gap-3 border border-zinc-800 bg-zinc-950/80 p-4 md:grid-cols-[auto_1fr_auto]"
                    style={{ marginLeft: `${Math.min(node.hierarchyLevel, 6) * 22}px` }}
                    initial={{ x: -20, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ delay: index * 0.08 }}
                    whileHover={{ x: 6, borderColor: "rgba(251,146,60,.55)" }}
                  >
                    <div className="grid h-12 w-12 place-items-center bg-orange-500 text-black">
                      <UserRound className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-3">
                        <p className="font-semibold text-zinc-100">{node.name}</p>
                        <span className="border border-orange-400/20 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-orange-300">{scopePt(node.visibleScope)}</span>
                      </div>
                      <p className="mt-1 text-sm text-zinc-400">{node.title} | {node.department}</p>
                      <p className="mt-2 break-all text-xs text-zinc-600">{node.email}</p>
                    </div>
                    <div className="text-left md:text-right">
                      <p className="text-2xl font-semibold text-orange-200">{node.directReports}</p>
                      <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">subordinados</p>
                      <button
                        type="button"
                        onClick={() => setExpandedNode(expandedNode === node.id ? null : node.id)}
                        className="mt-3 border border-orange-400/25 px-3 py-2 text-xs text-orange-200 transition hover:border-orange-300/60"
                      >
                        {(devicesByOwner.get(node.id)?.length ?? 0)} dispositivo{(devicesByOwner.get(node.id)?.length ?? 0) === 1 ? "" : "s"}
                      </button>
                    </div>
                    {expandedNode === node.id ? (
                      <div className="md:col-span-3">
                        <div className="mt-3 grid gap-3 border-t border-zinc-800 pt-3">
                          {(devicesByOwner.get(node.id) ?? []).length ? (
                            (devicesByOwner.get(node.id) ?? []).map((device) => (
                              <DeviceHierarchyRow
                                key={device.id}
                                device={device}
                                targetMembershipId={node.id}
                                onDeviceOwnerChange={onDeviceOwnerChange}
                              />
                            ))
                          ) : (
                            <EmptyState title="Nenhum dispositivo vinculado" description="Quando um agente for instalado para este usuário, o notebook aparecerá aqui." />
                          )}
                          {unassignedDevices.length ? (
                            <div className="grid gap-2">
                              <p className="text-xs uppercase tracking-[0.16em] text-zinc-500">Dispositivos sem usuário</p>
                              {unassignedDevices.map((device) => (
                                <DeviceHierarchyRow
                                  key={device.id}
                                  device={device}
                                  targetMembershipId={node.id}
                                  onDeviceOwnerChange={onDeviceOwnerChange}
                                />
                              ))}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    ) : null}
                  </motion.div>
                ))
              ) : (
                <EmptyState title="Hierarquia aguardando vínculo" description="O usuário teste será exibido quando o vínculo estiver disponível no backend conectado." />
              )}
            </div>
          </div>
        </Panel>
        <Panel title="Envelope de permissões" icon={ShieldCheck}>
          <div className="grid gap-4">
            {[
              ["Administradores da empresa", tenantScope, "veem todos os registros dentro da empresa"],
              ["Gestores", subtreeScope, "veem seus próprios dados e subordinados"],
              ["Usuários individuais", hierarchy.length - tenantScope - subtreeScope, "veem apenas seus próprios dados"],
              ["Dispositivos vinculados", devices.filter((device) => device.ownerMembershipId).length, "aparecem abaixo do usuário responsável"]
            ].map(([label, value, description], index) => (
              <motion.div
                key={String(label)}
                className="border border-zinc-800 bg-black/45 p-5"
                initial={{ scale: 0.96, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: index * 0.08 }}
              >
                <div className="flex items-center justify-between gap-4">
                  <p className="font-semibold">{label}</p>
                  <span className="text-3xl font-semibold text-orange-300">{value}</span>
                </div>
                <p className="mt-3 text-sm leading-6 text-zinc-400">{description}</p>
              </motion.div>
            ))}
          </div>
        </Panel>
      </div>
    </ViewFrame>
  );
}

function DeviceHierarchyRow({
  device,
  targetMembershipId,
  onDeviceOwnerChange
}: {
  device: Device;
  targetMembershipId: string;
  onDeviceOwnerChange: (deviceId: string, ownerMembershipId: string | null) => void;
}) {
  const alreadyLinkedHere = device.ownerMembershipId === targetMembershipId;
  return (
    <div className="grid gap-3 border border-zinc-800 bg-black/35 p-4 md:grid-cols-[1fr_auto]">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-semibold text-zinc-100">{device.hostname}</p>
          <span className="border border-orange-400/20 px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-orange-300">{statusPt(device.status)}</span>
          <span className="border border-emerald-400/20 px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-emerald-200">qualidade {qualityPt(device.collectionQuality)}</span>
        </div>
        <p className="mt-2 text-sm text-zinc-500">{device.os}</p>
        <p className="mt-1 text-xs text-zinc-600">
          Última sincronização: {device.lastSeenAt} | Fila: {device.queueDepth ?? 0} | Agente: {device.agentVersion ?? "não informado"}
        </p>
        {device.lastError ? <p className="mt-2 text-xs text-orange-300">Erro recente: {device.lastError}</p> : null}
        {device.collectionQuality === "blocked_by_os" ? (
          <p className="mt-2 text-xs text-orange-200">Coleta limitada pelo ambiente gráfico.</p>
        ) : null}
      </div>
      <div className="flex flex-wrap items-center gap-2 md:justify-end">
        <button
          type="button"
          onClick={() => onDeviceOwnerChange(device.id, targetMembershipId)}
          className="border border-orange-400/25 px-3 py-2 text-xs text-orange-200 transition hover:border-orange-300/60 disabled:cursor-not-allowed disabled:opacity-40"
          disabled={alreadyLinkedHere}
        >
          {alreadyLinkedHere ? "Vinculado" : "Mover para este usuário"}
        </button>
        <button
          type="button"
          onClick={() => onDeviceOwnerChange(device.id, null)}
          className="border border-zinc-700 px-3 py-2 text-xs text-zinc-300 transition hover:border-orange-400/45"
        >
          Desvincular
        </button>
      </div>
    </div>
  );
}

function StatusPill({ icon: Icon, label }: { icon: typeof Gauge; label: string }) {
  return (
    <motion.div
      className="relative flex h-12 items-center gap-2 overflow-hidden border border-orange-400/20 bg-black/50 px-4 text-sm text-zinc-300"
        animate={{ borderColor: ["rgba(251,146,60,0.14)", "rgba(251,146,60,0.30)", "rgba(251,146,60,0.14)"] }}
      transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
    >
      <motion.div
        className="absolute inset-y-0 -left-1/2 w-1/2 bg-[linear-gradient(90deg,transparent,rgba(249,115,22,0.08),transparent)]"
        animate={{ x: ["0%", "320%"] }}
        transition={{ duration: 4.2, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div animate={{ rotate: [0, 12, -12, 0], scale: [1, 1.12, 1] }} transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}>
        <Icon className="h-4 w-4 text-orange-300" />
      </motion.div>
      <span className="relative z-10">{label}</span>
    </motion.div>
  );
}

function LiveBadge({ label, detail }: { label: string; detail: string }) {
  return (
    <div className="inline-flex items-center gap-3 border border-emerald-400/20 bg-emerald-950/20 px-3 py-2 text-xs text-emerald-100">
      <motion.span
        className="h-2 w-2 rounded-full bg-emerald-400"
        animate={{ opacity: [0.45, 1, 0.45], scale: [0.9, 1.12, 0.9] }}
        transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
      />
      <span className="font-medium">{label}</span>
      <span className="text-emerald-200/70">{detail}</span>
    </div>
  );
}

function DashboardView({
  metrics,
  insights,
  notifications,
  devices,
  operationalMetrics,
  operationalIntelligence,
  hierarchy,
  supabaseStatus,
  whatsAppStatus,
  emailStatuses,
  aiStatus,
  schedules,
  onlineAgents,
  liveStatusLabel,
  allowDemoFallback
}: {
  metrics: Metric[];
  insights: Insight[];
  notifications: NotificationItem[];
  devices: Device[];
  operationalMetrics: OperationalMetric[];
  operationalIntelligence: OperationalIntelligence;
  hierarchy: HierarchyNode[];
  supabaseStatus: SupabaseStatus;
  whatsAppStatus: WhatsAppStatus;
  emailStatuses: EmailProviderStatus[];
  aiStatus: AIStatus;
  schedules: NotificationSchedule[];
  onlineAgents: number;
  liveStatusLabel: string;
  allowDemoFallback: boolean;
}) {
  const [demoAction, setDemoAction] = useState<string | null>(null);
  const flowData = useMemo(() => buildFlowData(operationalMetrics, allowDemoFallback), [operationalMetrics, allowDemoFallback]);
  const topUsers = useMemo(() => buildTopUsers(operationalMetrics, hierarchy), [operationalMetrics, hierarchy]);
  const departmentPerformance = useMemo(() => buildDepartmentPerformance(operationalMetrics, hierarchy, allowDemoFallback), [operationalMetrics, hierarchy, allowDemoFallback]);
  const heatmap = useMemo(() => buildHeatmap(operationalIntelligence), [operationalIntelligence]);
  const appUsageData = useMemo(() => {
    if (operationalIntelligence.topApps.length) {
      return operationalIntelligence.topApps
        .map((item) => ({ app: item.app, minutes: Math.max(1, Math.round((item.activeSeconds || item.idleSeconds) / 60)), category: item.category, percent: item.percent }))
        .slice(0, 8);
    }
    return buildAppUsageData(operationalMetrics, allowDemoFallback).map((item) => ({ ...item, category: "operacional", percent: 0 }));
  }, [operationalIntelligence, operationalMetrics, allowDemoFallback]);
  const activeSeconds = operationalIntelligence.totalActiveSeconds || sumMetric(operationalMetrics, "active_seconds");
  const idleSeconds = operationalIntelligence.totalIdleSeconds || sumMetric(operationalMetrics, "idle_seconds");
  const contextSwitches = operationalIntelligence.contextSwitches || sumMetric(operationalMetrics, "context_switch_count");
  const trackedSeconds = operationalIntelligence.trackedSeconds || activeSeconds + idleSeconds;
  const offlineDevices = devices.filter((device) => device.status === "offline").length;
  const pendingQueue = devices.reduce((total, device) => total + Number(device.queueDepth ?? 0), 0);
  const qualityIssues = devices.filter((device) => ["low", "blocked_by_os"].includes(device.collectionQuality ?? "")).length;
  const pendingNotifications = notifications.filter((item) => ["queued", "missing_credentials", "failed"].includes(item.status)).length;
  const sentNotifications = notifications.filter((item) => item.status === "sent").length;
  const automationHours = insights.reduce((total, insight) => total + insight.automationSavingsHours, 0);
  const financialSavings = automationHours * 95;
  const emailReady = emailStatuses.some((item) => item.configured && item.canSend);
  const dataPlaneReady = supabaseStatus.configured && supabaseStatus.databaseReachable !== false && supabaseStatus.restReachable !== false;
  const aiReady = aiStatus.openaiConfigured || aiStatus.llamaConfigured;
  const lossBreakdown = useMemo(
    () => buildLossBreakdown({ idleSeconds, contextSwitches, pendingQueue, offlineDevices, qualityIssues, automationHours }),
    [idleSeconds, contextSwitches, pendingQueue, offlineDevices, qualityIssues, automationHours]
  );
  const recommendedActions = useMemo(
    () => buildRecommendedActions(insights, operationalIntelligence, pendingNotifications, financialSavings),
    [insights, operationalIntelligence, pendingNotifications, financialSavings]
  );
  const bottlenecks = useMemo(
    () => buildBottlenecks(insights, appUsageData, departmentPerformance),
    [insights, appUsageData, departmentPerformance]
  );
  const automationOpportunities = useMemo(
    () => buildAutomationOpportunities(insights, automationHours),
    [insights, automationHours]
  );
  const onboardingChecklist = useMemo(
    () => buildOnboardingChecklist({ supabaseStatus, hierarchy, devices, whatsAppStatus, emailStatuses, aiStatus, schedules }),
    [supabaseStatus, hierarchy, devices, whatsAppStatus, emailStatuses, aiStatus, schedules]
  );
  const onboardingReady = onboardingChecklist.filter((item) => item.done).length;
  const topLoss = lossBreakdown.reduce<(typeof lossBreakdown)[number] | null>(
    (current, item) => (!current || item.money > current.money ? item : current),
    null
  );
  const primaryAction = recommendedActions[0] ?? null;
  const channelReadiness = [
    whatsAppStatus.connected || Boolean(whatsAppStatus.rootChannelNumber),
    emailReady,
    schedules.some((schedule) => schedule.enabled)
  ].filter(Boolean).length;
  const dashboardMetrics: Metric[] = [
    ...metrics,
    { id: "tracked-time", label: "Tempo analisado", value: formatDuration(trackedSeconds), trend: operationalIntelligence.periodLabel, tone: "neutral" },
    { id: "active-time", label: "Tempo ativo", value: formatDuration(activeSeconds), trend: "uso operacional consolidado", tone: "positive" },
    { id: "idle-time", label: "Tempo ocioso", value: formatDuration(idleSeconds), trend: `${percentPt(operationalIntelligence.idleRate)} do período`, tone: idleSeconds > activeSeconds * 0.35 ? "warning" : "neutral" },
    { id: "focus-score", label: "Taxa de foco", value: `${operationalIntelligence.focusScore}/100`, trend: `maior bloco: ${formatDuration(operationalIntelligence.longestFocusSeconds)}`, tone: operationalIntelligence.focusScore >= 55 ? "positive" : "warning" },
    { id: "fragmentation", label: "Fragmentação", value: `${operationalIntelligence.distractionScore}/100`, trend: `${Number(contextSwitches).toFixed(0)} trocas`, tone: operationalIntelligence.distractionScore > 45 ? "warning" : "neutral" },
    { id: "online-devices", label: "Dispositivos online", value: `${onlineAgents}`, trend: `${offlineDevices} offline | fila ${pendingQueue}`, tone: offlineDevices ? "warning" : "positive" },
    { id: "collection-quality", label: "Qualidade de coleta", value: qualityIssues ? `${qualityIssues} atenção` : "estável", trend: "Windows, Linux e macOS demo", tone: qualityIssues ? "warning" : "positive" },
    { id: "financial-savings", label: "Economia estimada", value: formatMoneyBRL(financialSavings), trend: `${automationHours}h de automação`, tone: "positive" },
    { id: "notifications-sent", label: "Notificações", value: `${sentNotifications}/${notifications.length}`, trend: `${pendingNotifications} pendentes`, tone: pendingNotifications ? "warning" : "positive" }
  ];
  const liveFeed = [
    ...notifications.slice(0, 4).map((item) => ({
      id: `ntf-${item.id}`,
      title: item.title,
      detail: `${channelPt(item.channel)} | ${statusPt(item.status)}`,
      tone: item.status === "failed" || item.status === "missing_credentials" ? "warn" : "ok"
    })),
    ...operationalIntelligence.qualitySignals.slice(0, 3).map((signal) => ({
      id: `quality-${signal.device}`,
      title: signal.device,
      detail: signal.message,
      tone: signal.quality === "high" ? "ok" : "warn"
    })),
    ...insights.slice(0, 3).map((insight) => ({
      id: `insight-${insight.id}`,
      title: insight.title,
      detail: `${impactPt(insight.impact)} | ${insight.automationSavingsHours}h potenciais`,
      tone: insight.impact === "high" ? "warn" : "ok"
    }))
  ].slice(0, 8);

  return (
    <ViewFrame>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <LiveBadge label="Tempo real ativo" detail={`${onlineAgents} agente${onlineAgents === 1 ? "" : "s"} sincronizando | última atualização ${liveStatusLabel}`} />
        <span className="border border-orange-400/25 bg-orange-950/15 px-3 py-2 text-xs uppercase tracking-[0.2em] text-orange-200">
          {!dataPlaneReady ? "Modo degradado: banco indisponível" : allowDemoFallback ? "Ambiente demonstrativo" : "Somente dados reais"}
        </span>
      </div>

      <div className="mb-5 grid gap-3 md:grid-cols-3 xl:grid-cols-6">
        <ConnectionSummary label="Banco operacional" value={dataPlaneReady ? "pronto" : "atenção"} tone={dataPlaneReady ? "ok" : "warn"} />
        <ConnectionSummary label="IA híbrida" value={aiReady ? "configurada" : "mock explícito"} tone={aiReady ? "ok" : "warn"} />
        <ConnectionSummary label="WhatsApp" value={whatsAppStatus.connected ? "conectado" : statusPt(whatsAppStatus.status)} tone={whatsAppStatus.connected ? "ok" : "warn"} />
        <ConnectionSummary label="E-mail" value={emailReady ? "envio pronto" : "pendente"} tone={emailReady ? "ok" : "warn"} />
        <ConnectionSummary label="Agentes online" value={`${onlineAgents}/${devices.length}`} tone={onlineAgents ? "ok" : "warn"} />
        <ConnectionSummary label="Eventos hoje" value={`${operationalIntelligence.totalEvents || metrics.find((metric) => metric.id === "events")?.value || 0}`} tone={operationalIntelligence.totalEvents ? "ok" : "warn"} />
      </div>

      <div className="mb-5 grid gap-3 xl:grid-cols-[0.9fr_1.2fr_0.9fr]">
        <motion.div
          className="border border-orange-400/25 bg-[linear-gradient(135deg,rgba(249,115,22,0.14),rgba(9,9,11,0.72))] p-5 shadow-[0_0_28px_rgba(249,115,22,0.08)]"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
        >
          <p className="text-xs uppercase tracking-[0.2em] text-orange-200">Perda financeira prioritaria</p>
          <p className="mt-3 text-3xl font-semibold text-zinc-50">{formatMoneyBRL(topLoss?.money ?? financialSavings)}</p>
          <p className="mt-2 text-sm leading-6 text-zinc-300">{topLoss ? `${topLoss.label}: ${topLoss.action}` : "Aguardando mais eventos para estimar o primeiro gargalo financeiro."}</p>
        </motion.div>

        <motion.div
          className="border border-zinc-800 bg-black/45 p-5"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.04 }}
        >
          <p className="text-xs uppercase tracking-[0.2em] text-orange-200">O que fazer agora</p>
          <p className="mt-3 text-xl font-semibold text-zinc-50">{primaryAction?.title ?? "Rodar os agentes por algumas horas e revisar o primeiro ranking de gargalos."}</p>
          <div className="mt-4 grid gap-2 sm:grid-cols-3">
            <ConnectionSummary label="Urgência" value={primaryAction?.urgency ?? "Média"} tone={primaryAction?.urgency === "Alta" ? "warn" : "ok"} />
            <ConnectionSummary label="Responsável" value={primaryAction?.owner ?? "Gestor"} tone="ok" />
            <ConnectionSummary label="Economia" value={formatMoneyBRL(primaryAction?.money ?? financialSavings)} tone={(primaryAction?.money ?? financialSavings) ? "ok" : "warn"} />
          </div>
        </motion.div>

        <motion.div
          className="border border-zinc-800 bg-zinc-950/70 p-5"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.08 }}
        >
          <p className="text-xs uppercase tracking-[0.2em] text-orange-200">Piloto pago em 60 segundos</p>
          <p className="mt-3 text-3xl font-semibold text-zinc-50">{onboardingReady}/{onboardingChecklist.length}</p>
          <p className="mt-2 text-sm leading-6 text-zinc-400">Base configurada com {channelReadiness}/3 canais essenciais para alertar gestor, supervisor e diretoria.</p>
        </motion.div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        {dashboardMetrics.map((metric, index) => (
          <MetricTile key={metric.id} metric={metric} index={index} />
        ))}
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <Panel title="Pulso executivo da operação" icon={Command}>
          <div className="grid gap-4">
            <div className="border border-orange-400/20 bg-black/45 p-5">
              <p className="text-xs uppercase tracking-[0.2em] text-orange-300">O que está acontecendo agora</p>
              <p className="mt-3 text-3xl font-semibold text-zinc-50">{operationalIntelligence.currentActivity}</p>
              <p className="mt-4 text-sm leading-6 text-zinc-400">{operationalIntelligence.aiSummary}</p>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <ConnectionSummary label="Produtivo" value={formatDuration(activeSeconds)} tone="ok" />
              <ConnectionSummary label="Ocioso" value={formatDuration(idleSeconds)} tone={idleSeconds > activeSeconds * 0.35 ? "warn" : "ok"} />
              <ConnectionSummary label="Trocas/hora" value={`${operationalIntelligence.contextSwitchesPerHour.toFixed(1)}/h`} tone={operationalIntelligence.contextSwitchesPerHour > 25 ? "warn" : "ok"} />
            </div>
            {demoAction ? <FeedbackBanner tone="ok" message={demoAction} /> : null}
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {[
                "Atualizar simulação",
                "Gerar novo insight",
                "Simular agente online/offline",
                "Simular alerta crítico"
              ].map((label) => (
                <motion.button
                  key={label}
                  type="button"
                  onClick={() => setDemoAction(`${label}: ação de demonstração preparada. Para produção, conecte este botão ao job correspondente no backend.`)}
                  className="min-h-16 border border-zinc-800 bg-zinc-950/70 px-4 text-left text-sm text-zinc-200 transition hover:border-orange-400/45 hover:text-orange-100"
                  whileHover={{ y: -3 }}
                  whileTap={{ scale: 0.98 }}
                >
                  {label}
                </motion.button>
              ))}
            </div>
          </div>
        </Panel>

        <Panel title="Fluxo operacional" icon={Activity}>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={flowData}>
                <defs>
                  <linearGradient id="events" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f97316" stopOpacity={0.75} />
                    <stop offset="95%" stopColor="#f97316" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="name" stroke="#71717a" />
                <YAxis stroke="#71717a" />
                <Tooltip contentStyle={{ background: "#09090b", border: "1px solid rgba(249,115,22,.35)", color: "#fff" }} />
                <Area type="monotone" dataKey="events" stroke="#fb923c" fill="url(#events)" strokeWidth={3} />
                <Line type="monotone" dataKey="automation" stroke="#facc15" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_1fr]">
        <Panel title="Onde a empresa está perdendo dinheiro" icon={Flame}>
          <div className="grid gap-3">
            {lossBreakdown.length ? (
              lossBreakdown.map((item, index) => (
                <motion.div
                  key={item.label}
                  className="border border-zinc-800 bg-black/42 p-4"
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-zinc-100">{item.label}</p>
                      <p className="mt-1 text-sm leading-6 text-zinc-500">{item.cause}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-semibold text-orange-200">{formatMoneyBRL(item.money)}</p>
                      <p className="text-xs uppercase tracking-[0.14em] text-zinc-500">{formatDuration(item.impact * 3600)}</p>
                    </div>
                  </div>
                  <p className="mt-3 border-l border-orange-400/35 pl-3 text-sm leading-6 text-zinc-300">{item.action}</p>
                </motion.div>
              ))
            ) : (
              <EmptyState title="Sem perdas mensuráveis ainda" description="Quando os agentes enviarem eventos suficientes, o Vulcan calcula o impacto por ociosidade, troca de contexto, filas e automação." />
            )}
          </div>
        </Panel>

        <Panel title="Ações recomendadas pela IA" icon={Brain}>
          <div className="grid gap-3">
            {recommendedActions.map((action, index) => (
              <motion.div
                key={action.id}
                className="border border-orange-400/15 bg-orange-950/10 p-4"
                initial={{ opacity: 0, x: 18 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="max-w-2xl">
                    <p className="font-semibold text-orange-50">{action.title}</p>
                    <p className="mt-2 text-sm text-zinc-400">Setor: {action.scope} | Responsável sugerido: {action.owner}</p>
                  </div>
                  <span className="border border-orange-400/25 px-3 py-1 text-xs uppercase tracking-[0.16em] text-orange-200">Urgência {action.urgency}</span>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <ConnectionSummary label="Impacto esperado" value={action.impact} tone="ok" />
                  <ConnectionSummary label="Economia estimada" value={formatMoneyBRL(action.money)} tone={action.money ? "ok" : "warn"} />
                  <ConnectionSummary label="Próximo passo" value="criar alerta" tone="ok" />
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {["Ver detalhes", "Criar alerta", "Enviar por WhatsApp/e-mail"].map((label) => (
                    <button key={label} type="button" className="border border-zinc-800 bg-black/35 px-3 py-2 text-xs text-zinc-200 transition hover:border-orange-400/50 hover:text-orange-100">
                      {label}
                    </button>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_1fr]">
        <Panel title="Gargalos que travam a operação" icon={Gauge}>
          <div className="grid gap-3">
            {bottlenecks.map((item, index) => (
              <div key={item.id} className="border border-zinc-800 bg-black/40 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-zinc-100">{item.system}</p>
                    <p className="mt-1 text-sm text-zinc-500">{item.sector} | {item.affected}</p>
                  </div>
                  <span className="text-sm text-orange-200">{item.time}</span>
                </div>
                <div className="mt-3 grid gap-2 md:grid-cols-3">
                  <ConnectionSummary label="Severidade" value={item.severity} tone={item.severity === "crítico" ? "warn" : "ok"} />
                  <ConnectionSummary label="Tendência" value={item.trend} tone={item.trend === "subindo" ? "warn" : "ok"} />
                  <ConnectionSummary label="Prioridade" value={index < 2 ? "agir agora" : "monitorar"} tone={index < 2 ? "warn" : "ok"} />
                </div>
                <p className="mt-3 text-sm leading-6 text-zinc-400">{item.recommendation}</p>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Plano de automação e ROI" icon={Zap}>
          <div className="grid gap-3">
            {automationOpportunities.map((item) => (
              <div key={item.id} className="border border-zinc-800 bg-black/40 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-zinc-100">{item.process}</p>
                    <p className="mt-1 text-sm text-zinc-500">Frequência: {item.frequency} | Complexidade: {item.complexity}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-orange-200">{item.roi}</p>
                    <p className="text-xs uppercase tracking-[0.14em] text-zinc-500">{item.wasted}</p>
                  </div>
                </div>
                <p className="mt-3 text-sm leading-6 text-zinc-400">{item.suggestion}</p>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="mt-5">
        <Panel title="Checklist para piloto pago" icon={CheckCircle2}>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {onboardingChecklist.map((item) => (
              <div key={item.label} className="border border-zinc-800 bg-black/35 p-4">
                <div className="flex items-start gap-3">
                  <span className={`mt-1 h-3 w-3 rounded-full ${item.done ? "bg-emerald-400" : "bg-orange-400"}`} />
                  <div>
                    <p className="font-medium text-zinc-100">{item.label}</p>
                    <p className="mt-1 text-sm text-zinc-500">{item.detail}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-4 text-sm text-zinc-400">
            Prontidão do piloto: {onboardingReady}/{onboardingChecklist.length} blocos essenciais configurados. O objetivo é sair da apresentação com empresa, hierarquia, agente e canal de alerta funcionando.
          </p>
        </Panel>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <Panel title="Heatmap operacional por horário" icon={Activity}>
          {heatmap.length ? (
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6 xl:grid-cols-8">
              {heatmap.map((point, index) => (
                <motion.div
                  key={`${point.label}-${index}`}
                  className="min-h-24 border border-zinc-800 p-3"
                  style={{ backgroundColor: `rgba(249,115,22,${0.08 + point.intensity / 260})` }}
                  initial={{ opacity: 0, scale: 0.92 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: index * 0.025 }}
                  whileHover={{ y: -4, borderColor: "rgba(251,146,60,.55)" }}
                >
                  <p className="text-sm font-semibold text-zinc-50">{point.label}</p>
                  <p className="mt-2 text-xs text-zinc-300">{point.activeMinutes}min ativos</p>
                  <p className="text-xs text-zinc-500">{point.idleMinutes}min ociosos</p>
                  <p className="mt-2 text-[10px] uppercase tracking-[0.12em] text-orange-200">{point.switches} trocas</p>
                </motion.div>
              ))}
            </div>
          ) : (
            <EmptyState title="Heatmap aguardando eventos" description="A distribuição por horário aparece assim que o agente envia eventos recentes ou o seed demo é gerado." />
          )}
        </Panel>

        <Panel title="Agentes conectados em tempo real" icon={RadioTower}>
          <div className="space-y-3">
            {devices.length ? (
              devices.map((device, index) => (
                <motion.div
                  key={device.id}
                  className="border border-zinc-800 bg-black/45 p-4"
                  initial={{ x: 20, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  transition={{ delay: index * 0.08 }}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-zinc-100">{device.hostname}</p>
                      <p className="mt-1 text-sm text-zinc-500">{device.owner} | {device.os}</p>
                      <p className="mt-1 text-xs text-zinc-600">Qualidade de coleta: {qualityPt(device.collectionQuality)} | Fila: {device.queueDepth ?? 0}</p>
                      {device.collectionQuality === "blocked_by_os" ? <p className="mt-2 text-xs text-orange-300">Coleta limitada pelo ambiente gráfico.</p> : null}
                    </div>
                    <span className="text-xs uppercase tracking-[0.18em] text-orange-300">{statusPt(device.status)}</span>
                  </div>
                </motion.div>
              ))
            ) : (
              <EmptyState title="Nenhum agente real vinculado" description="Instale ou reinicie o Vulcan Agent neste notebook para o usuário teste. Dados demo não aparecem nesta sessão." />
            )}
          </div>
        </Panel>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <Panel title="Aplicativos mais usados" icon={Gauge}>
          <div className="grid gap-3">
            {appUsageData.map((item, index) => (
              <div key={`${item.app}-${index}`} className="border border-zinc-800 bg-black/40 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="font-medium text-zinc-100">{item.app}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.14em] text-zinc-500">{item.category}</p>
                  </div>
                  <p className="text-orange-200">{item.minutes}min</p>
                </div>
                <div className="mt-3 h-2 bg-zinc-900">
                  <motion.div
                    className="h-full bg-gradient-to-r from-orange-700 via-orange-400 to-yellow-300"
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(100, item.percent || item.minutes / Math.max(appUsageData[0]?.minutes ?? 1, 1) * 100)}%` }}
                    transition={{ duration: 0.7, delay: index * 0.04 }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Ranking de usuários" icon={UserRound}>
          <div className="grid gap-3">
            {topUsers.length ? (
              topUsers.map((user, index) => (
                <motion.div
                  key={user.id}
                  className="border border-zinc-800 bg-black/40 p-4"
                  initial={{ x: 16, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium text-zinc-100">{user.name}</p>
                      <p className="mt-1 text-sm text-zinc-500">{user.title}</p>
                    </div>
                    <p className="text-orange-200">{formatDuration(user.active)}</p>
                  </div>
                  <p className="mt-3 text-xs text-zinc-500">Ocioso: {formatDuration(user.idle)} | Trocas: {Math.round(user.switches)}</p>
                </motion.div>
              ))
            ) : (
              <EmptyState title="Sem ranking por usuário" description="Faça login com um perfil da demo ou rode o seed para carregar a hierarquia completa." />
            )}
          </div>
        </Panel>

        <Panel title="Setores mais ativos" icon={Building2}>
          <div className="grid gap-4">
            {departmentPerformance.length ? (
              departmentPerformance.map((department, index) => (
                <div key={department.name}>
                  <div className="mb-2 flex justify-between gap-3 text-sm">
                    <span>{department.name}</span>
                    <span className="text-orange-300">{department.score}%</span>
                  </div>
                  <div className="h-3 bg-zinc-900">
                    <motion.div
                      className="h-full bg-gradient-to-r from-orange-700 via-orange-400 to-yellow-300"
                      initial={{ width: 0 }}
                      animate={{ width: `${department.score}%` }}
                      transition={{ duration: 0.8, delay: index * 0.08 }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-zinc-500">Ativo: {formatDuration(department.active)} | Ocioso: {formatDuration(department.idle)}</p>
                </div>
              ))
            ) : (
              <EmptyState title="Sem dados por setor" description="Os setores aparecem quando houver métricas vinculadas aos usuários da árvore." />
            )}
          </div>
        </Panel>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <Panel title="Feed vivo de sinais" icon={Sparkles}>
          <div className="grid gap-3">
            {liveFeed.length ? (
              liveFeed.map((item, index) => (
                <motion.div
                  key={item.id}
                  className="flex items-start gap-3 border border-zinc-800 bg-black/40 p-4"
                  initial={{ x: -16, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <span className={`mt-1 h-2.5 w-2.5 rounded-full ${item.tone === "ok" ? "bg-emerald-400" : "bg-orange-400"}`} />
                  <div>
                    <p className="font-medium text-zinc-100">{item.title}</p>
                    <p className="mt-1 text-sm text-zinc-500">{item.detail}</p>
                  </div>
                </motion.div>
              ))
            ) : (
              <EmptyState title="Feed aguardando sinais" description="Alertas, insights e avisos de coleta aparecem aqui em tempo real." />
            )}
          </div>
        </Panel>

        <Panel title="Saúde da operação" icon={ShieldCheck}>
          <div className="grid gap-3 md:grid-cols-2">
            <ConnectionSummary label="Agentes online" value={`${onlineAgents}`} tone={onlineAgents ? "ok" : "warn"} />
            <ConnectionSummary label="Agentes offline" value={`${offlineDevices}`} tone={offlineDevices ? "warn" : "ok"} />
            <ConnectionSummary label="Fila offline" value={`${pendingQueue} evento${pendingQueue === 1 ? "" : "s"}`} tone={pendingQueue ? "warn" : "ok"} />
            <ConnectionSummary label="Coleta limitada" value={`${qualityIssues} dispositivo${qualityIssues === 1 ? "" : "s"}`} tone={qualityIssues ? "warn" : "ok"} />
            <ConnectionSummary label="Insights gerados" value={`${insights.length}`} tone={insights.length ? "ok" : "warn"} />
            <ConnectionSummary label="Alertas pendentes" value={`${pendingNotifications}`} tone={pendingNotifications ? "warn" : "ok"} />
          </div>
          <div className="mt-5">
            <p className="text-xs uppercase tracking-[0.18em] text-orange-300">Oportunidades de automação</p>
            <p className="mt-3 text-4xl font-semibold text-zinc-50">{automationHours}h</p>
            <p className="mt-2 text-sm text-zinc-400">Economia financeira estimada em {formatMoneyBRL(financialSavings)} por ciclo de análise.</p>
          </div>
        </Panel>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <InsightsView insights={insights} compact />
        <NotificationsView notifications={notifications} compact />
      </div>
    </ViewFrame>
  );
}

function MetricsView({
  operationalMetrics,
  operationalIntelligence,
  liveStatusLabel,
  allowDemoFallback
}: {
  operationalMetrics: OperationalMetric[];
  operationalIntelligence: OperationalIntelligence;
  liveStatusLabel: string;
  allowDemoFallback: boolean;
}) {
  const appUsageData = useMemo(() => buildAppUsageData(operationalMetrics, allowDemoFallback), [operationalMetrics, allowDemoFallback]);
  const departmentData = allowDemoFallback ? departments : [];
  const metricActiveSeconds = operationalMetrics.filter((metric) => metric.metricKey === "active_seconds").reduce((total, metric) => total + Number(metric.valueNumeric ?? 0), 0);
  const metricIdleSeconds = operationalMetrics.filter((metric) => metric.metricKey === "idle_seconds").reduce((total, metric) => total + Number(metric.valueNumeric ?? 0), 0);
  const metricContextSwitches = operationalMetrics.filter((metric) => metric.metricKey === "context_switch_count").reduce((total, metric) => total + Number(metric.valueNumeric ?? 0), 0);
  const activeSeconds = operationalIntelligence.totalActiveSeconds || metricActiveSeconds;
  const idleSecondsTotal = operationalIntelligence.totalIdleSeconds || metricIdleSeconds;
  const contextSwitches = operationalIntelligence.contextSwitches || metricContextSwitches;
  const deepAppUsage = operationalIntelligence.topApps.length
    ? operationalIntelligence.topApps.filter((item) => item.app !== "Ociosidade").map((item) => ({ app: item.app, minutes: Math.max(1, Math.round(item.activeSeconds / 60)) }))
    : appUsageData;
  const timelineData = operationalIntelligence.timeline.map((point) => ({
    label: point.label,
    ativo: Math.round(point.activeSeconds / 60),
    ocioso: Math.round(point.idleSeconds / 60),
    naoIdentificado: Math.round((point.unidentifiedSeconds ?? 0) / 60),
    trocas: point.contextSwitches
  }));
  return (
    <ViewFrame>
      <div className="mb-4">
        <LiveBadge label="Métricas profundas em tempo real" detail={`Última sincronização: ${liveStatusLabel} | ${operationalIntelligence.periodLabel}`} />
      </div>
      <div className="mb-5 grid gap-3 md:grid-cols-3 xl:grid-cols-7">
        <ConnectionSummary label="Tempo ativo" value={formatDuration(activeSeconds)} tone="ok" />
        <ConnectionSummary label="Tempo ocioso" value={formatDuration(idleSecondsTotal)} tone={idleSecondsTotal > 0 ? "warn" : "ok"} />
        <ConnectionSummary label="Não identificado" value={formatDuration(operationalIntelligence.unidentifiedSeconds)} tone={operationalIntelligence.unidentifiedSeconds > 0 ? "warn" : "ok"} />
        <ConnectionSummary label="Ociosidade" value={percentPt(operationalIntelligence.idleRate)} tone={operationalIntelligence.idleRate > 0.2 ? "warn" : "ok"} />
        <ConnectionSummary label="Trocas de contexto" value={`${Math.round(contextSwitches)}`} tone={contextSwitches > 20 ? "warn" : "ok"} />
        <ConnectionSummary label="Trocas por hora" value={`${operationalIntelligence.contextSwitchesPerHour.toFixed(1)}/h`} tone={operationalIntelligence.contextSwitchesPerHour > 25 ? "warn" : "ok"} />
        <ConnectionSummary label="Dispersão estimada" value={`${operationalIntelligence.distractionScore}/100`} tone={operationalIntelligence.distractionScore > 45 ? "warn" : "ok"} />
      </div>

      <div className="mb-5 grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
        <Panel title="Agora e diagnóstico de IA" icon={Brain}>
          <div className="grid gap-4">
            <div className="border border-orange-400/20 bg-black/45 p-5">
              <p className="text-xs uppercase tracking-[0.2em] text-orange-300">O que está acontecendo</p>
              <p className="mt-3 text-2xl font-semibold text-zinc-50">{operationalIntelligence.currentActivity}</p>
              <p className="mt-3 text-sm leading-6 text-zinc-400">{operationalIntelligence.aiSummary}</p>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <ConnectionSummary label="Score de foco" value={`${operationalIntelligence.focusScore}/100`} tone={operationalIntelligence.focusScore >= 55 ? "ok" : "warn"} />
              <ConnectionSummary label="Maior bloco de foco" value={formatDuration(operationalIntelligence.longestFocusSeconds)} tone="ok" />
              <ConnectionSummary label="Tempo fragmentado" value={formatDuration(operationalIntelligence.fragmentedSeconds)} tone={operationalIntelligence.fragmentedSeconds > activeSeconds * 0.35 ? "warn" : "ok"} />
            </div>
            <div className="space-y-2">
              {operationalIntelligence.aiRecommendations.map((recommendation) => (
                <div key={recommendation} className="flex items-start gap-3 border border-zinc-800 bg-zinc-950/65 p-3 text-sm text-zinc-300">
                  <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-orange-300" />
                  <span>{recommendation}</span>
                </div>
              ))}
            </div>
          </div>
        </Panel>
        <Panel title="Controle por sistema utilizado" icon={Gauge}>
          <div className="grid gap-3">
            {operationalIntelligence.topApps.length ? (
              operationalIntelligence.topApps.map((item, index) => (
                <motion.div
                  key={`${item.app}-${item.category}`}
                  className="border border-zinc-800 bg-black/45 p-4"
                  initial={{ opacity: 0, x: 18 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.04 }}
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="font-medium text-zinc-100">{item.app}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.14em] text-zinc-500">{item.category} | {item.focusLabel}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-semibold text-orange-200">{formatDuration(item.activeSeconds || item.idleSeconds)}</p>
                      <p className="text-xs text-zinc-500">{item.percent.toFixed(1)}% do período comparável</p>
                    </div>
                  </div>
                  <div className="mt-3 h-2 bg-zinc-900">
                    <motion.div
                      className="h-full bg-gradient-to-r from-orange-700 via-orange-400 to-yellow-300"
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min(100, item.percent)}%` }}
                      transition={{ duration: 0.7, delay: index * 0.04 }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-zinc-600">{item.events} evento{item.events === 1 ? "" : "s"} | {item.contextSwitches} troca{item.contextSwitches === 1 ? "" : "s"}</p>
                </motion.div>
              ))
            ) : (
              <EmptyState title="Sem uso por sistema ainda" description="Reinicie o agente 0.2.0 e gere alguns minutos de uso real para ver o ranking de sistemas." />
            )}
          </div>
        </Panel>
      </div>

      {operationalIntelligence.qualitySignals.length ? (
        <div className="mb-5">
          <Panel title="Qualidade da coleta" icon={ShieldCheck}>
            <div className="grid gap-3 md:grid-cols-2">
              {operationalIntelligence.qualitySignals.map((signal) => (
                <div key={`${signal.device}-${signal.quality}-${signal.message}`} className="border border-orange-400/20 bg-orange-950/10 p-4">
                  <p className="font-medium text-orange-100">{signal.device}</p>
                  <p className="mt-1 text-sm text-orange-200">{signal.message}</p>
                  <p className="mt-2 text-xs uppercase tracking-[0.14em] text-orange-300/70">Qualidade: {qualityPt(signal.quality)}</p>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      ) : null}

      <div className="mb-5 grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
        <Panel title="Linha do tempo ativa x ociosa" icon={Activity}>
          <div className="h-72">
            {timelineData.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={timelineData}>
                  <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="label" stroke="#71717a" />
                  <YAxis stroke="#71717a" />
                  <Tooltip contentStyle={{ background: "#09090b", border: "1px solid rgba(249,115,22,.35)", color: "#fff" }} />
                  <Bar dataKey="ativo" stackId="a" fill="#f97316" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="ocioso" stackId="a" fill="#52525b" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="naoIdentificado" stackId="a" fill="#a16207" radius={[4, 4, 0, 0]} />
                  <Line type="monotone" dataKey="trocas" stroke="#facc15" strokeWidth={2} />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState title="Sem linha do tempo" description="A linha ativa/ociosa aparece assim que o agente enviar eventos recentes." />
            )}
          </div>
        </Panel>
        <Panel title="Janelas e detalhes permitidos por política" icon={Layers3}>
          <div className="space-y-3">
            {operationalIntelligence.topWindows.map((item) => (
              <div key={`${item.app}-${item.title}`} className="border border-zinc-800 bg-black/45 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-zinc-100">{item.title}</p>
                    <p className="mt-1 text-sm text-zinc-500">{item.app}</p>
                  </div>
                  <p className="text-sm text-orange-200">{item.activeSeconds ? formatDuration(item.activeSeconds) : "protegido"}</p>
                </div>
                <p className="mt-2 text-xs leading-5 text-zinc-500">{item.collectionNote}</p>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
        <Panel title="Concentração de tempo por aplicativo" icon={Gauge}>
          <div className="h-96">
            {deepAppUsage.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={deepAppUsage}>
                  <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="app" stroke="#71717a" />
                  <YAxis stroke="#71717a" />
                  <Tooltip contentStyle={{ background: "#09090b", border: "1px solid rgba(249,115,22,.35)", color: "#fff" }} />
                  <Bar dataKey="minutes" radius={[10, 10, 0, 0]}>
                    {deepAppUsage.map((_, index) => (
                      <Cell key={index} fill={index === 0 ? "#f97316" : "#52525b"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState title="Sem métricas reais ainda" description="O gráfico será preenchido após o agente sincronizar eventos de uso deste notebook." />
            )}
          </div>
        </Panel>
        <Panel title="Pulso de eficiência por setor" icon={Building2}>
          <div className="grid gap-4">
            {departmentData.length ? (
              departmentData.map((department, index) => (
                <div key={department.name}>
                  <div className="mb-2 flex justify-between text-sm">
                    <span>{department.name}</span>
                    <span className="text-orange-300">{department.score}%</span>
                  </div>
                  <div className="h-3 bg-zinc-900">
                    <motion.div
                      className="h-full bg-gradient-to-r from-orange-700 via-orange-400 to-yellow-300"
                      initial={{ width: 0 }}
                      animate={{ width: `${department.score}%` }}
                      transition={{ duration: 0.8, delay: index * 0.1 }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <EmptyState title="Sem comparativo por setor" description="Esta sessão do usuário teste mostra somente dados reais; comparativos aparecem quando existirem mais usuários e agentes." />
            )}
          </div>
        </Panel>
      </div>
    </ViewFrame>
  );
}

function InsightsView({ insights, compact = false }: { insights: Insight[]; compact?: boolean }) {
  return (
    <ViewFrame compact={compact}>
      <Panel title="Fluxo de insights de IA" icon={Sparkles}>
        <div className="grid gap-4">
          {insights.length ? (
            insights.map((insight, index) => (
              <motion.article
                key={insight.id}
                className="border border-orange-400/15 bg-black/45 p-5 transition hover:border-orange-300/50 hover:shadow-[0_0_24px_rgba(249,115,22,0.08)]"
                initial={{ y: 24, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: index * 0.08 }}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <h3 className="text-lg font-semibold">{insight.title}</h3>
                  <span className="border border-orange-400/25 px-3 py-1 text-xs uppercase tracking-[0.18em] text-orange-300">{impactPt(insight.impact)}</span>
                </div>
                <p className="mt-3 text-sm leading-6 text-zinc-400">{insight.summary}</p>
                <p className="mt-4 text-sm leading-6 text-zinc-200">{insight.recommendation}</p>
                <div className="mt-4 flex items-center gap-2 text-orange-300">
                  <Zap className="h-4 w-4" />
                  <span>{insight.automationSavingsHours}h de potencial de automação</span>
                </div>
              </motion.article>
            ))
          ) : (
            <EmptyState title="Sem insights gerados" description="Os insights aparecem depois que houver volume real suficiente de métricas operacionais." />
          )}
        </div>
      </Panel>
    </ViewFrame>
  );
}

function NotificationsView({ notifications, liveStatusLabel = "agora", schedules = [], compact = false }: { notifications: NotificationItem[]; liveStatusLabel?: string; schedules?: NotificationSchedule[]; compact?: boolean }) {
  const iconByChannel = { system: BellRing, push: BellRing, windows: BellRing, whatsapp: MessageCircle, email: Mail };
  return (
    <ViewFrame compact={compact}>
      {!compact ? (
        <div className="mb-4">
          <LiveBadge label="Central de notificações ao vivo" detail={`Última atualização: ${liveStatusLabel}`} />
        </div>
      ) : null}
      <Panel title="Canais de notificação" icon={BellRing}>
        <div className="grid gap-4">
          {notifications.length ? (
            notifications.map((item, index) => {
              const Icon = iconByChannel[item.channel];
              return (
                <motion.div
                  key={item.id}
                  className="border border-zinc-800 bg-black/45 p-5"
                  initial={{ x: 22, opacity: 0 }}
                  animate={{ x: 0, opacity: 1 }}
                  transition={{ delay: index * 0.08 }}
                >
                  <div className="flex items-center gap-3">
                    <div className="grid h-11 w-11 place-items-center bg-orange-500 text-black">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="font-medium">{item.title}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.14em] text-zinc-500">
                        {channelPt(item.channel)} | {statusPt(item.status)} | {item.recipient ?? "sem destinatário"}
                      </p>
                    </div>
                  </div>
                  <p className="mt-4 text-sm leading-6 text-zinc-400">{item.message}</p>
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-zinc-500">
                    <span>Tentativas: {item.attempts ?? 0}</span>
                    {item.error ? <span className="text-orange-300">Erro: {item.error}</span> : null}
                    <button className="border border-orange-400/25 px-3 py-2 text-orange-200 transition hover:border-orange-300/60" type="button">
                      Reenviar
                    </button>
                  </div>
                </motion.div>
              );
            })
          ) : (
            <EmptyState title="Sem notificações reais" description="Alertas e notificações serão exibidos quando o Vulcan detectar sinais reais do agente." />
          )}
        </div>
      </Panel>
      {!compact ? (
        <div className="mt-5">
          <Panel title="Agendamentos automáticos" icon={Activity}>
            <div className="grid gap-3 md:grid-cols-3">
              {schedules.map((schedule) => (
                <div key={schedule.id} className="border border-zinc-800 bg-black/35 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-zinc-100">{schedule.name}</p>
                      <p className="mt-1 text-sm text-zinc-500">{schedule.recurrence} | {schedule.timezone}</p>
                    </div>
                    <span className="border border-emerald-400/20 px-2 py-1 text-xs text-emerald-200">{schedule.enabled ? "ativo" : "pausado"}</span>
                  </div>
                  <p className="mt-3 text-sm text-zinc-400">Horários: {schedule.times.join(", ")}</p>
                  <p className="mt-2 text-sm text-zinc-400">Destinatários: {schedule.recipients.join(", ")}</p>
                  <p className="mt-2 text-xs uppercase tracking-[0.14em] text-orange-300">{schedule.channels.map(channelPt).join(" | ")}</p>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      ) : null}
    </ViewFrame>
  );
}

function SettingsView({
  supabaseStatus,
  whatsAppStatus,
  emailStatuses,
  schedules,
  reportTemplates,
  token
}: {
  supabaseStatus: SupabaseStatus;
  whatsAppStatus: WhatsAppStatus;
  emailStatuses: EmailProviderStatus[];
  schedules: NotificationSchedule[];
  reportTemplates: ReportTemplate[];
  token: string;
}) {
  const smtpStatus = emailStatuses.find((item) => item.provider === "smtp") ?? fallbackEmailStatuses[0];
  const gmailStatus = emailStatuses.find((item) => item.provider === "gmail");
  const outlookStatus = emailStatuses.find((item) => item.provider === "outlook");
  const imapStatus = emailStatuses.find((item) => item.provider === "imap");
  const pop3Status = emailStatuses.find((item) => item.provider === "pop3");
  const [feedback, setFeedback] = useState<{ tone: "ok" | "warn"; message: string } | null>(null);

  async function testIntegration(kind: "whatsapp" | "email", provider?: string, destination?: string | null) {
    setFeedback({ tone: "warn", message: "Testando conexão..." });
    try {
      const response = await fetch(`${API_URL}/integrations/${kind}/test`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "X-Tenant-Id": DEMO_TENANT_ID
        },
        body: JSON.stringify({
          tenantId: DEMO_TENANT_ID,
          provider,
          destination: destination || undefined,
          message: "Mensagem de teste enviada pela central de configurações do Vulcan."
        })
      });
      const payload = (await response.json()) as { ok?: boolean; status?: string; message?: string; providerResult?: string };
      setFeedback({
        tone: payload.ok ? "ok" : "warn",
        message: `${kind === "whatsapp" ? "WhatsApp" : "E-mail"}: ${payload.message ?? statusPt(payload.status ?? "pendente")}`
      });
    } catch {
      setFeedback({ tone: "warn", message: "Não foi possível chamar o backend local. Verifique se a API está rodando em http://localhost:3001." });
    }
  }

  return (
    <ViewFrame>
      <div className="grid gap-5">
        <Panel title="Configurações guiadas" icon={CheckCircle2}>
          <div className="grid gap-3 md:grid-cols-4">
            <ConnectionSummary label="Tempo real" value="ativo" tone="ok" />
            <ConnectionSummary label="Supabase" value={supabaseStatus.configured ? "conectado" : "pendente"} tone={supabaseStatus.configured ? "ok" : "warn"} />
            <ConnectionSummary label="WhatsApp raiz" value={whatsAppStatus.connected ? "conectado" : "pendente"} tone={whatsAppStatus.connected ? "ok" : "warn"} />
            <ConnectionSummary label="E-mail" value={smtpStatus.configured ? "pronto" : "pendente"} tone={smtpStatus.configured ? "ok" : "warn"} />
          </div>
          {feedback ? <FeedbackBanner tone={feedback.tone} message={feedback.message} /> : null}
        </Panel>

        <div className="grid gap-5 xl:grid-cols-2">
          <ConfigSection
            title="Geral"
            description="Defina nome, idioma, fuso horário e comportamento padrão da plataforma."
            status="pronto"
            fields={[
              ["Nome do produto", "Vulcan"],
              ["Idioma", "Português do Brasil"],
              ["Fuso horário", "America/Sao_Paulo"]
            ]}
          />
          <ConfigSection
            title="Empresa"
            description="Cadastre dados básicos da empresa, unidade operacional e responsáveis."
            status="pendente"
            fields={[
              ["Nome da empresa", "Ex.: LanFuture"],
              ["Documento", "CNPJ ou identificação interna"],
              ["Responsável", "Nome do gestor principal"]
            ]}
          />
          <ConfigSection
            title="Usuários e hierarquia"
            description="Monte a árvore de cargos sem limite de níveis e defina quem recebe cada alerta."
            status="ativo"
            fields={[
              ["Cargo", "Supervisor, Gerente, Diretor..."],
              ["Gestor direto", "Selecione o responsável"],
              ["Preferências", "WhatsApp, e-mail, sistema"]
            ]}
          />
          <ConfigSection
            title="Agentes"
            description="Instale agentes, acompanhe status e garanta sincronização operacional em tempo real."
            status="sincronizando"
            fields={[
              ["Token de instalação", "vulcan-local-enrollment-token"],
              ["Backend", "http://localhost:3001"],
              ["Modo de coleta", "Aplicativo ativo e duração"]
            ]}
          />
        </div>

        <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
          <Panel title="Supabase" icon={DatabaseZap}>
            <div className="grid gap-3 md:grid-cols-2">
              <ConnectionSummary label="Projeto" value={supabaseStatus.projectRef ?? "não definido"} tone={supabaseStatus.projectRef ? "ok" : "warn"} />
              <ConnectionSummary label="Auth" value={supabaseStatus.authProvider} tone="ok" />
              <ConnectionSummary label="REST" value={supabaseStatus.restReachable === null ? "não testado" : supabaseStatus.restReachable ? "alcançável" : "bloqueado"} tone={supabaseStatus.restReachable ? "ok" : "warn"} />
              <ConnectionSummary label="Banco" value={supabaseStatus.databaseReachable === null ? supabaseStatus.databaseUrlConfigured ? "configurado" : "pendente" : supabaseStatus.databaseReachable ? "alcançável" : "bloqueado"} tone={supabaseStatus.databaseReachable === false ? "warn" : supabaseStatus.databaseUrlConfigured ? "ok" : "warn"} />
            </div>
            <ActionRow primary="Testar conexão" secondary="Salvar configuração" />
          </Panel>

          <Panel title="Inteligência Artificial" icon={Brain}>
            <div className="grid gap-3 md:grid-cols-2">
              <ConfigField label="Modelo operacional" placeholder="Llama via Ollama, Groq, Together ou OpenRouter" />
              <ConfigField label="Modelo executivo" placeholder="GPT para Copilot, relatórios e recomendações" />
              <ConfigField label="Política de roteamento" placeholder="Métricas -> Llama | Estratégia -> GPT" />
              <ConfigField label="Chaves" placeholder="OPENAI_API_KEY e LLAMA_API_KEY no .env" />
            </div>
            <ActionRow primary="Testar IA" secondary="Salvar configuração" />
          </Panel>
        </div>

        <div className="grid gap-5 xl:grid-cols-2">
          <Panel title="WhatsApp" icon={MessageCircle}>
            <div className="mb-4 grid gap-3 md:grid-cols-2">
              <ConnectionSummary label="Canal Oficial Vulcan" value={whatsAppStatus.rootChannelName} tone="ok" />
              <ConnectionSummary label="Número raiz" value={whatsAppStatus.rootChannelNumber ?? "pendente"} tone={whatsAppStatus.rootChannelNumber ? "ok" : "warn"} />
              <ConnectionSummary label="Provedor" value={whatsAppStatus.provider} tone="ok" />
              <ConnectionSummary label="Status" value={statusPt(whatsAppStatus.status)} tone={whatsAppStatus.connected ? "ok" : "warn"} />
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <ConfigField label="Provedor" placeholder="lanchat ou whatsapp-business-api" />
              <ConfigField label="Token" placeholder="WHATSAPP_ACCESS_TOKEN" secret />
              <ConfigField label="ID do número" placeholder="WHATSAPP_PHONE_NUMBER_ID" />
              <ConfigField label="ID da conta Business" placeholder="WHATSAPP_BUSINESS_ACCOUNT_ID" />
              <ConfigField label="Webhook Verify Token" placeholder="WHATSAPP_WEBHOOK_VERIFY_TOKEN" secret />
              <ConfigField label="Número padrão de envio" placeholder="5541984166423" />
            </div>
            {whatsAppStatus.qrRequired ? (
              <div className="mt-4 border border-dashed border-orange-400/25 bg-black/35 p-4">
                <p className="font-medium text-orange-200">QR Code necessário</p>
                <p className="mt-2 text-sm text-zinc-400">A sessão local está preparada para QR no padrão de sessão inspirado no LanChat.</p>
              </div>
            ) : null}
            <ActionRow
              primary="Testar conexão"
              secondary="Enviar mensagem teste"
              tertiary="Salvar configuração"
              onPrimary={() => testIntegration("whatsapp", whatsAppStatus.provider, whatsAppStatus.rootChannelNumber)}
              onSecondary={() => testIntegration("whatsapp", whatsAppStatus.provider, whatsAppStatus.rootChannelNumber)}
              onTertiary={() => setFeedback({ tone: "warn", message: "As configurações sensíveis do WhatsApp devem ser salvas no .env ou no cofre seguro do tenant antes de produção." })}
            />
          </Panel>

          <Panel title="E-mail" icon={Mail}>
            <div className="grid gap-3">
              {[smtpStatus, gmailStatus, outlookStatus, imapStatus, pop3Status].filter(Boolean).map((status) => (
                <div key={status!.provider} className="border border-zinc-800 bg-black/35 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-semibold text-zinc-100">{status!.provider.toUpperCase()}</p>
                    <span className={status!.configured ? "text-emerald-300" : "text-orange-300"}>{statusPt(status!.status)}</span>
                  </div>
                  <p className="mt-2 text-sm text-zinc-400">{status!.message}</p>
                  {status!.requiredItems.length ? <p className="mt-2 text-xs text-zinc-500">Faltam: {status!.requiredItems.join(", ")}</p> : null}
                </div>
              ))}
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <ConfigField label="Host SMTP" placeholder="smtp.seudominio.com" />
              <ConfigField label="Porta" placeholder="587" />
              <ConfigField label="Usuário" placeholder="notificacoes@empresa.com" />
              <ConfigField label="Senha" placeholder="senha ou app password" secret />
              <ConfigField label="Remetente" placeholder="Vulcan <notificacoes@empresa.com>" />
              <ConfigField label="TLS/SSL" placeholder="TLS ativo" />
              <ConfigField label="Client ID do Google" placeholder="GMAIL_CLIENT_ID" />
              <ConfigField label="Tenant ID do Outlook" placeholder="OUTLOOK_TENANT_ID" />
              <ConfigField label="Host IMAP" placeholder="imap.seudominio.com" />
              <ConfigField label="Host POP3" placeholder="pop.seudominio.com" />
            </div>
            <ActionRow
              primary="Testar conexão"
              secondary="Enviar e-mail teste"
              tertiary="Salvar configuração"
              onPrimary={() => testIntegration("email", smtpStatus.provider)}
              onSecondary={() => testIntegration("email", smtpStatus.provider)}
              onTertiary={() => setFeedback({ tone: "warn", message: "As credenciais de e-mail devem ser salvas em ambiente seguro. A tela já mostra exatamente quais campos faltam." })}
            />
          </Panel>
        </div>

        <div className="grid gap-5 xl:grid-cols-2">
          <Panel title="Notificações e recorrências" icon={BellRing}>
            <div className="grid gap-3">
              {schedules.map((schedule) => (
                <div key={schedule.id} className="border border-zinc-800 bg-black/35 p-4">
                  <p className="font-semibold text-zinc-100">{schedule.name}</p>
                  <p className="mt-2 text-sm text-zinc-400">{schedule.recurrence} | {schedule.times.join(", ")} | {schedule.timezone}</p>
                  <p className="mt-2 text-xs uppercase tracking-[0.14em] text-orange-300">{schedule.channels.map(channelPt).join(" | ")}</p>
                </div>
              ))}
            </div>
            <ActionRow primary="Novo agendamento" secondary="Testar notificação" tertiary="Salvar regras" />
          </Panel>

          <Panel title="Motor de relatórios automáticos" icon={Sparkles}>
            <div className="grid gap-3">
              {reportTemplates.map((template) => (
                <div key={template.id} className="border border-zinc-800 bg-black/35 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <p className="font-semibold text-zinc-100">{template.name}</p>
                    <span className="text-xs text-orange-300">{template.cadence}</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-zinc-400">{template.description}</p>
                </div>
              ))}
            </div>
            <ActionRow primary="Gerar prévia" secondary="Agendar relatório" tertiary="Salvar modelo" />
          </Panel>
        </div>

        <div className="grid gap-5 xl:grid-cols-2">
          <ConfigSection
            title="Segurança"
            description="Controle fallback local, isolamento por tenant, auditoria e permissões hierárquicas."
            status="atenção"
            fields={[
              ["Login local", "admin/admin somente desenvolvimento"],
              ["RLS", "habilitado no Supabase"],
              ["Auditoria", "eventos críticos registrados"]
            ]}
          />
          <ConfigSection
            title="Integrações"
            description="Centralize provedores externos sem travar o Vulcan em um único fornecedor."
            status="preparado"
            fields={[
              ["WhatsApp", "Canal raiz + conexões por tenant futuras"],
              ["E-mail", "SMTP, Gmail, Outlook, IMAP e POP3"],
              ["Push", "FCM/VAPID preparado"]
            ]}
          />
        </div>

        <Panel title="LGPD e privacidade operacional" icon={ShieldCheck}>
          <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
            <div className="border border-emerald-400/20 bg-emerald-950/10 p-5">
              <p className="text-xs uppercase tracking-[0.18em] text-emerald-200">Mensagem central</p>
              <p className="mt-3 text-2xl font-semibold text-zinc-50">O Vulcan mede fluxo operacional, não conteúdo pessoal.</p>
              <p className="mt-3 text-sm leading-6 text-zinc-400">
                A coleta é orientada por política corporativa, consentimento e transparência. O objetivo é revelar gargalos, filas, ociosidade e oportunidades de automação sem capturar conteúdo privado.
              </p>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {[
                ["Coleta", "app ativo, duração, troca de contexto, status do agente e métricas agregadas"],
                ["Não coleta", "senhas, teclas digitadas, áudio, webcam, prints contínuos ou mensagens privadas"],
                ["Controles", "retenção, auditoria, permissões por hierarquia e isolamento por tenant"],
                ["Confiança", "colaborador sabe o que é medido e gestores enxergam apenas o escopo autorizado"]
              ].map(([title, text]) => (
                <div key={title} className="border border-zinc-800 bg-black/35 p-4">
                  <p className="font-semibold text-zinc-100">{title}</p>
                  <p className="mt-2 text-sm leading-6 text-zinc-400">{text}</p>
                </div>
              ))}
            </div>
          </div>
          <ActionRow primary="Revisar política" secondary="Exportar dados" tertiary="Registrar consentimento" />
        </Panel>
      </div>
    </ViewFrame>
  );
}

function ConnectionSummary({ label, value, tone }: { label: string; value: string; tone: "ok" | "warn" }) {
  return (
    <div className="border border-zinc-800 bg-black/35 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-zinc-500">{label}</p>
      <div className="mt-2 flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${tone === "ok" ? "bg-emerald-400" : "bg-orange-400"}`} />
        <p className={tone === "ok" ? "truncate text-sm text-emerald-200" : "truncate text-sm text-orange-200"}>{value}</p>
      </div>
    </div>
  );
}

function FeedbackBanner({ tone, message }: { tone: "ok" | "warn"; message: string }) {
  return (
    <motion.div
      className={`mt-4 border px-4 py-3 text-sm ${
        tone === "ok" ? "border-emerald-400/25 bg-emerald-950/20 text-emerald-100" : "border-orange-400/25 bg-orange-950/20 text-orange-100"
      }`}
      initial={{ y: 8, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
    >
      {message}
    </motion.div>
  );
}

function ConfigSection({ title, description, status, fields }: { title: string; description: string; status: string; fields: [string, string][] }) {
  return (
    <Panel title={title} icon={Layers3}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <p className="max-w-xl text-sm leading-6 text-zinc-400">{description}</p>
        <span className="shrink-0 border border-orange-400/20 px-3 py-1 text-xs uppercase tracking-[0.14em] text-orange-200">{status}</span>
      </div>
      <div className="grid gap-3">
        {fields.map(([label, placeholder]) => (
          <ConfigField key={label} label={label} placeholder={placeholder} />
        ))}
      </div>
      <ActionRow primary="Testar conexão" secondary="Salvar" />
    </Panel>
  );
}

function ConfigField({ label, placeholder, secret = false }: { label: string; placeholder: string; secret?: boolean }) {
  return (
    <label className="grid gap-2">
      <span className="text-xs uppercase tracking-[0.16em] text-zinc-500">{label}</span>
      <input
        type={secret ? "password" : "text"}
        placeholder={placeholder}
        className="h-11 border border-zinc-800 bg-black/45 px-3 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-orange-400/55"
      />
    </label>
  );
}

function ActionRow({
  primary,
  secondary,
  tertiary,
  onPrimary,
  onSecondary,
  onTertiary
}: {
  primary: string;
  secondary: string;
  tertiary?: string;
  onPrimary?: () => void;
  onSecondary?: () => void;
  onTertiary?: () => void;
}) {
  return (
    <div className="mt-5 flex flex-wrap gap-3">
      <button type="button" onClick={onPrimary} className="inline-flex h-11 items-center gap-2 bg-orange-500 px-4 text-sm font-semibold text-black transition hover:bg-orange-400">
        <CheckCircle2 className="h-4 w-4" />
        {primary}
      </button>
      <button type="button" onClick={onSecondary} className="inline-flex h-11 items-center gap-2 border border-zinc-800 bg-black/45 px-4 text-sm text-zinc-200 transition hover:border-orange-400/45">
        <Zap className="h-4 w-4 text-orange-300" />
        {secondary}
      </button>
      {tertiary ? (
        <button type="button" onClick={onTertiary} className="inline-flex h-11 items-center gap-2 border border-zinc-800 bg-black/45 px-4 text-sm text-zinc-200 transition hover:border-orange-400/45">
          <Save className="h-4 w-4 text-orange-300" />
          {tertiary}
        </button>
      ) : null}
    </div>
  );
}

function MetricTile({ metric, index }: { metric: Metric; index: number }) {
  return (
    <motion.div
      className="relative overflow-hidden border border-orange-400/15 bg-zinc-950/70 p-5 shadow-[0_0_26px_rgba(249,115,22,0.05)]"
      initial={{ y: 28, opacity: 0 }}
      animate={{ y: [0, -2, 0], opacity: 1 }}
      transition={{ delay: index * 0.07 }}
      whileHover={{ y: -6, borderColor: "rgba(251,146,60,.65)" }}
    >
      <motion.div
        className="absolute inset-x-0 top-0 h-px bg-orange-300/50"
        animate={{ opacity: [0.12, 0.55, 0.12] }}
        transition={{ duration: 2.5, repeat: Infinity, delay: index * 0.2 }}
      />
      <motion.div
        className="absolute inset-y-0 -left-1/2 w-1/2 bg-[linear-gradient(90deg,transparent,rgba(249,115,22,0.08),transparent)]"
        animate={{ x: ["0%", "320%"] }}
        transition={{ duration: 3.8, repeat: Infinity, ease: "easeInOut", delay: index * 0.18 }}
      />
      <motion.div
        className="absolute right-4 top-4 h-2 w-2 border border-orange-300/60 bg-orange-400/20"
        animate={{ opacity: [0.20, 0.68, 0.20], scale: [0.88, 1.18, 0.88], rotate: [0, 180, 360] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut", delay: index * 0.12 }}
      />
      <div className="relative z-10">
        <p className="text-sm text-zinc-500">{metric.label}</p>
        <motion.p
          className="mt-3 text-4xl font-semibold text-zinc-50"
          animate={{ textShadow: ["0 0 0 rgba(249,115,22,0)", "0 0 8px rgba(249,115,22,0.10)", "0 0 0 rgba(249,115,22,0)"] }}
          transition={{ duration: 3, repeat: Infinity, ease: "easeInOut", delay: index * 0.18 }}
        >
          {metric.value}
        </motion.p>
        <p className="mt-3 text-sm text-orange-300">{metric.trend}</p>
      </div>
    </motion.div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <motion.div
      className="grid min-h-44 place-items-center border border-dashed border-orange-400/20 bg-black/35 p-6 text-center"
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: [1, 1.01, 1], borderColor: ["rgba(251,146,60,0.18)", "rgba(251,146,60,0.46)", "rgba(251,146,60,0.18)"] }}
      transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut" }}
    >
      <div>
        <motion.div
          className="mx-auto mb-4 grid h-12 w-12 place-items-center border border-orange-400/25 bg-orange-500/10 text-orange-300"
          animate={{ rotate: [0, 180, 360], boxShadow: ["0 0 0 rgba(249,115,22,0)", "0 0 16px rgba(249,115,22,0.18)", "0 0 0 rgba(249,115,22,0)"] }}
          transition={{ duration: 5, repeat: Infinity, ease: "linear" }}
        >
          <RadioTower className="h-5 w-5" />
        </motion.div>
        <p className="font-semibold text-zinc-100">{title}</p>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-zinc-500">{description}</p>
      </div>
    </motion.div>
  );
}

function Panel({ title, icon: Icon, children }: { title: string; icon: typeof Gauge; children: ReactNode }) {
  return (
    <motion.section
      className="relative overflow-hidden border border-zinc-800 bg-zinc-950/78 p-5 shadow-[0_0_36px_rgba(0,0,0,0.22)] backdrop-blur-md"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
      whileHover={{ borderColor: "rgba(251,146,60,0.34)", boxShadow: "0 0 34px rgba(249,115,22,0.07)" }}
    >
      <motion.div
        className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-300 to-transparent"
        animate={{ x: ["-100%", "100%"], opacity: [0, 0.95, 0] }}
        transition={{ duration: 3.6, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        className="absolute -right-24 -top-24 h-56 w-56 border border-orange-400/10"
        animate={{ rotate: [0, 180, 360], scale: [1, 1.12, 1], opacity: [0.22, 0.55, 0.22] }}
        transition={{ duration: 9, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="absolute inset-0 bg-[linear-gradient(135deg,transparent,rgba(249,115,22,0.04),transparent)]"
        animate={{ x: ["-20%", "20%", "-20%"], opacity: [0.18, 0.55, 0.18] }}
        transition={{ duration: 6.5, repeat: Infinity, ease: "easeInOut" }}
      />
      <div className="relative z-10 mb-5 flex items-center gap-3">
        <motion.div
          className="grid h-10 w-10 place-items-center bg-orange-500 text-black"
          animate={{ boxShadow: ["0 0 0 rgba(249,115,22,0)", "0 0 16px rgba(249,115,22,0.22)", "0 0 0 rgba(249,115,22,0)"] }}
          transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut" }}
        >
          <Icon className="h-5 w-5" />
        </motion.div>
        <h3 className="text-lg font-semibold">{title}</h3>
      </div>
      <div className="relative z-10">{children}</div>
    </motion.section>
  );
}

function ViewFrame({ children, compact = false }: { children: ReactNode; compact?: boolean }) {
  return (
    <motion.div
      className={compact ? "" : "pb-8"}
      initial={{ opacity: 0, y: 24, filter: "blur(10px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      exit={{ opacity: 0, y: -18, filter: "blur(10px)" }}
      transition={{ duration: 0.45 }}
    >
      {children}
    </motion.div>
  );
}
