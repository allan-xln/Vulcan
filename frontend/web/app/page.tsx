"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import * as Tremor from "@tremor/react";
import CountUp from "react-countup";
import {
  Activity,
  BarChart3,
  BellRing,
  Brain,
  Building2,
  CalendarClock,
  CheckCircle2,
  Command,
  DatabaseZap,
  Download,
  FileText,
  Flame,
  Gauge,
  Layers3,
  LogOut,
  Lock,
  Mail,
  MessageCircle,
  Monitor,
  Network,
  Save,
  RadioTower,
  ShieldCheck,
  SlidersHorizontal,
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
  Line,
  Pie,
  PieChart,
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

type MetricsIntent = {
  nonce: number;
  period?: string;
  teamId?: string;
  membershipId?: string;
  deviceId?: string;
  supervisorId?: string;
  department?: string;
  title?: string;
  os?: string;
  category?: string;
  agentStatus?: string;
  metricType?: string;
  app?: string;
};

type Metric = {
  id: string;
  label: string;
  value: string;
  trend: string;
  tone: "positive" | "warning" | "critical" | "neutral";
};

type Insight = {
  id: string;
  tenantId?: string | null;
  membershipId?: string | null;
  departmentId?: string | null;
  scopeType?: string;
  scopeId?: string | null;
  targetUserId?: string | null;
  targetTeamId?: string | null;
  targetDepartmentId?: string | null;
  roleVisibility?: string[];
  insightType?: string;
  title: string;
  impact: "high" | "medium" | "low";
  summary: string;
  diagnosis?: string;
  recommendation: string;
  evidence?: string[];
  metricsUsed?: string[];
  affectedUsers?: string[];
  affectedTeams?: string[];
  severity?: string;
  confidence?: number | null;
  estimatedTimeLoss?: number;
  estimatedCostLoss?: number;
  estimatedSavings?: number;
  periodStart?: string | null;
  periodEnd?: string | null;
  status?: string;
  sourceRoute?: string | null;
  sentToWhatsapp?: boolean;
  sentToEmail?: boolean;
  whatsappStatus?: string;
  emailStatus?: string;
  lastSentAt?: string | null;
  recipients?: string[];
  suggestedQuestions?: string[];
  actionStatus?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  automationSavingsHours: number;
};

type InsightAskResponse = {
  insightId: string;
  question: string;
  answer: string;
  aiMode: string;
  suggestedActions: string[];
};

type NotificationItem = {
  id: string;
  tenantId?: string | null;
  channel: "system" | "push" | "windows" | "whatsapp" | "email";
  status: "pending" | "queued" | "sending" | "sent" | "delivered" | "failed" | "cancelled" | "skipped" | "retrying" | "ready" | "mocked" | "missing_credentials" | "missing_destination" | "unknown_provider" | "disabled" | "resolved" | "provider_unavailable" | "qr_required" | "rate_limited";
  title: string;
  message: string;
  createdAt: string;
  recipient?: string | null;
  recipientMembershipId?: string | null;
  priority?: "informativo" | "baixo" | "medio" | "alto" | "critico";
  attempts?: number;
  maxAttempts?: number;
  error?: string | null;
  notificationType?: string | null;
  provider?: string | null;
  providerMessageId?: string | null;
  scheduledFor?: string | null;
  sentAt?: string | null;
  deliveredAt?: string | null;
  readAt?: string | null;
  resolvedAt?: string | null;
  actionUrl?: string | null;
  requiresAck?: boolean;
};

type NotificationSummary = {
  total: number;
  pending: number;
  sent: number;
  failed: number;
  critical: number;
  unread: number;
  whatsappReady: boolean;
  emailReady: boolean;
  agentReady: boolean;
  nextScheduleAt?: string | null;
  byChannel: Record<string, number>;
  byStatus: Record<string, number>;
  byPriority: Record<string, number>;
};

type NotificationTypeDefinition = {
  id: string;
  name: string;
  description: string;
  defaultPriority: string;
  allowedChannels: string[];
  defaultAudience: string;
  defaultFrequency: string;
  template: string;
  canDisable: boolean;
  requiresPermission: boolean;
  critical: boolean;
  enabled: boolean;
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
  osUser?: string | null;
  adoptionStatus?: string | null;
  adoptionCode?: string | null;
  teamId?: string | null;
  teamName?: string | null;
};

type AgentDeploymentPrepareResponse = {
  status: "ready" | "blocked";
  message: string;
  tenantId: string;
  target: string;
  backendUrl: string;
  packageUrl: string;
  remoteExecutionAvailable: boolean;
  supportedExecutors: string[];
  powershellCommand: string;
  gpoCommand: string;
  nextStep: string;
};

type Team = {
  id: string;
  tenantId: string;
  name: string;
  description?: string | null;
  color: string;
  membersCount: number;
  devicesCount: number;
  activeSeconds: number;
  idleSeconds: number;
};

type MetricsDetailedRow = {
  id: string;
  userName: string;
  userTitle?: string | null;
  supervisorId?: string | null;
  supervisorName?: string | null;
  teamId?: string | null;
  teamName?: string | null;
  department: string;
  deviceId?: string | null;
  device: string;
  os: string;
  agentStatus?: string | null;
  app: string;
  category: string;
  eventType: string;
  durationSeconds: number;
  occurredAt: string;
  collectionQuality?: string | null;
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
  whatsappEnabled?: boolean;
  whatsappOptIn?: boolean;
  whatsappNotificationTypes?: string[];
  quietHoursStart?: string | null;
  quietHoursEnd?: string | null;
  hierarchyLevel: number;
  directReports: number;
  visibleScope: "self" | "subtree" | "tenant" | "global";
};

type DepartmentOption = {
  id: string;
  tenantId: string;
  parentDepartmentId?: string | null;
  name: string;
  slug: string;
  description?: string | null;
};

type RoleOption = {
  id: string;
  tenantId?: string | null;
  slug: string;
  name: string;
  description?: string | null;
  scope: "self" | "hierarchy" | "tenant" | "global";
  isSystem: boolean;
};

type HierarchyMemberFormPayload = {
  id?: string;
  parentId: string | null;
  level: number;
  fullName: string;
  title: string;
  departmentId: string | null;
  workEmail: string;
  username: string;
  password: string;
  phone: string;
  whatsapp: string;
  whatsappEnabled: boolean;
  whatsappOptIn: boolean;
  quietHoursStart: string;
  quietHoursEnd: string;
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

type EvolutionStatus = {
  provider: string;
  status: string;
  connected: boolean;
  unofficial: boolean;
  serviceReachable: boolean;
  instanceName: string;
  baseUrl: string | null;
  rootNumber: string | null;
  rootName: string;
  qrRequired: boolean;
  qrCode: string | null;
  apiKeyConfigured: boolean;
  webhookConfigured: boolean;
  mockMode: boolean;
  requireOptIn: boolean;
  emailFallbackEnabled: boolean;
  inAppFallbackEnabled: boolean;
  logs: string[];
};

type RootWhatsAppQueueItem = {
  id: string;
  recipient?: string | null;
  destination: string;
  title: string;
  status: string;
  provider?: string | null;
  providerMessageId?: string | null;
  attempts: number;
  maxAttempts: number;
  nextAttemptAt?: string | null;
  deadLetterAt?: string | null;
  lastError?: string | null;
  createdAt: string;
};

type RootWhatsAppLog = {
  id: string;
  queueId?: string | null;
  destination?: string | null;
  status: string;
  provider?: string | null;
  providerResult?: string | null;
  error?: string | null;
  createdAt: string;
};

type EvolutionActionResponse = {
  ok: boolean;
  status: string;
  message: string;
  qrCode?: string | null;
};

type EvolutionConfigDraft = {
  enabled: boolean;
  provider: "mock" | "evolution" | "meta_cloud_future";
  rootNumber: string;
  rootName: string;
  baseUrl: string;
  apiKey: string;
  instanceName: string;
  mockMode: boolean;
  requireOptIn: boolean;
  emailFallbackEnabled: boolean;
  inAppFallbackEnabled: boolean;
  testDestination: string;
  testMessage: string;
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

type NotificationTemplate = {
  id: string;
  channel: "system" | "push" | "windows" | "whatsapp" | "email";
  notificationType: string;
  title: string;
  body: string;
  variables: string[];
  language: string;
  version: number;
  active: boolean;
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

type SettingsField = {
  key: string;
  label: string;
  value: string | number | boolean | null;
  valueType: "text" | "number" | "boolean" | "select" | "multiselect" | "json" | "secret" | "readonly";
  description: string;
  status: "ok" | "attention" | "missing" | "error" | "mock" | "readonly" | "disabled";
  required: boolean;
  isSecret: boolean;
  editable: boolean;
  options: string[];
  placeholder?: string | null;
  unit?: string | null;
};

type SettingsSectionData = {
  id: string;
  title: string;
  description: string;
  scope: "system" | "tenant" | "team" | "user" | "agent";
  status: "ok" | "attention" | "missing" | "error" | "mock" | "readonly" | "disabled";
  canEdit: boolean;
  lastUpdatedAt?: string | null;
  fields: SettingsField[];
};

type SettingsSummaryData = {
  tenantId: string;
  environment: string;
  canEdit: boolean;
  totalSections: number;
  ok: number;
  attention: number;
  missing: number;
  error: number;
  mock: number;
  lastUpdatedAt?: string | null;
  criticalPending: string[];
  statuses: Record<string, string>;
};

type SettingsResponseData = {
  summary: SettingsSummaryData;
  sections: SettingsSectionData[];
};

type SettingsActionResponseData = {
  section: string;
  status: string;
  message: string;
  saved: boolean;
  tested: boolean;
  sectionData?: SettingsSectionData | null;
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

const fallbackNotificationSummary: NotificationSummary = {
  total: fallbackNotifications.length,
  pending: 2,
  sent: 1,
  failed: 0,
  critical: 1,
  unread: 3,
  whatsappReady: false,
  emailReady: false,
  agentReady: true,
  nextScheduleAt: null,
  byChannel: { windows: 1, whatsapp: 1, email: 1 },
  byStatus: { mocked: 1, missing_credentials: 2 },
  byPriority: { alto: 1, medio: 2 }
};

const fallbackNotificationTypes: NotificationTypeDefinition[] = [
  { id: "agente_offline", name: "Agente offline", description: "Dispositivo sem sincronizar acima do limite.", defaultPriority: "alto", allowedChannels: ["system", "whatsapp", "email", "windows"], defaultAudience: "supervisor/TI", defaultFrequency: "imediato", template: "{{dispositivo}} ficou offline.", canDisable: true, requiresPermission: true, critical: false, enabled: true },
  { id: "insight_critico", name: "Insight crítico", description: "Insight de alto impacto gerado pela IA/regras.", defaultPriority: "critico", allowedChannels: ["system", "whatsapp", "email"], defaultAudience: "gestor responsável", defaultFrequency: "imediato", template: "Insight crítico: {{titulo}}.", canDisable: false, requiresPermission: true, critical: true, enabled: true },
  { id: "relatorio_diario", name: "Relatório diário", description: "Resumo operacional diário.", defaultPriority: "informativo", allowedChannels: ["system", "email", "whatsapp"], defaultAudience: "gestores", defaultFrequency: "diário", template: "Relatório diário de {{empresa}} pronto.", canDisable: true, requiresPermission: true, critical: false, enabled: true },
  { id: "falha_whatsapp", name: "Falha WhatsApp", description: "Canal WhatsApp sem credenciais ou indisponível.", defaultPriority: "alto", allowedChannels: ["system", "email"], defaultAudience: "admin", defaultFrequency: "imediato", template: "WhatsApp requer atenção: {{erro}}.", canDisable: false, requiresPermission: true, critical: true, enabled: true }
];

const fallbackNotificationTemplates: NotificationTemplate[] = [
  { id: "tpl-whatsapp-critical", channel: "whatsapp", notificationType: "insight_critico", title: "Vulcan alerta crítico", body: "Vulcan: {{equipe}} apresentou {{metrica}} acima do esperado. Impacto: {{impacto}}.", variables: ["equipe", "metrica", "impacto"], language: "pt-BR", version: 1, active: true },
  { id: "tpl-email-daily", channel: "email", notificationType: "relatorio_diario", title: "Vulcan - Relatório diário de {{empresa}}", body: "Resumo executivo, gargalos, insights e ações recomendadas.", variables: ["empresa"], language: "pt-BR", version: 1, active: true },
  { id: "tpl-system-device", channel: "system", notificationType: "dispositivo_aguardando_adocao", title: "Dispositivo aguardando adoção", body: "{{dispositivo}} precisa ser vinculado.", variables: ["dispositivo"], language: "pt-BR", version: 1, active: true }
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

const fallbackSettingsCenter: SettingsResponseData = {
  summary: {
    tenantId: DEMO_TENANT_ID,
    environment: "local",
    canEdit: false,
    totalSections: 0,
    ok: 0,
    attention: 0,
    missing: 0,
    error: 0,
    mock: 0,
    lastUpdatedAt: null,
    criticalPending: ["Backend de configurações indisponível"],
    statuses: {}
  },
  sections: []
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

const hierarchyLevelCatalog = [
  { value: 0, label: "Dono / Presidência", shortLabel: "Dono", scope: "tenant" },
  { value: 1, label: "Diretor", shortLabel: "Diretor", scope: "hierarchy" },
  { value: 2, label: "Superintendente", shortLabel: "Superintendente", scope: "hierarchy" },
  { value: 3, label: "Head / Coordenador", shortLabel: "Coordenação", scope: "hierarchy" },
  { value: 4, label: "Gerente", shortLabel: "Gerente", scope: "hierarchy" },
  { value: 5, label: "Supervisor", shortLabel: "Supervisor", scope: "hierarchy" },
  { value: 6, label: "Líder", shortLabel: "Líder", scope: "hierarchy" },
  { value: 7, label: "Monitor", shortLabel: "Monitor", scope: "hierarchy" },
  { value: 8, label: "Analista", shortLabel: "Analista", scope: "self" },
  { value: 9, label: "Operador / Usuário", shortLabel: "Usuário", scope: "self" },
  { value: 10, label: "Terceiro / Temporário", shortLabel: "Terceiro", scope: "self" }
] as const;

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

function formatEventDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function formatDateTime(value?: string | null) {
  if (!value) return "sem data";
  return formatEventDate(value);
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
    mock: "mock explícito",
    unofficial_connected: "Evolution conectado",
    unofficial_disconnected: "Evolution desconectado",
    unofficial_qr_required: "QR necessário",
    unofficial_failed: "Evolution indisponível",
    unofficial_rate_limited: "Evolution limitado",
    official_ready_future: "API oficial preparada para o futuro",
    provider_unavailable: "provider indisponível",
    qr_required: "QR necessário",
    rate_limited: "limite temporário",
    retrying: "nova tentativa agendada",
    delivered: "entregue",
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
    global: "global",
    system: "sistema",
    team: "equipe",
    user: "usuário",
    agent: "agente"
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

function priorityPt(priority: string) {
  const dictionary: Record<string, string> = {
    informativo: "informativo",
    baixo: "baixo",
    medio: "médio",
    alto: "alto",
    critico: "crítico"
  };
  return dictionary[priority] ?? priority;
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

type TimeDistributionSlice = {
  key: "productive" | "idle" | "communication" | "internal" | "navigation" | "other";
  name: string;
  value: number;
  seconds: number;
  percent: number;
  color: string;
};

type RankingChartItem = {
  name: string;
  value: number;
  detail?: string;
};

type ProductivityTimelinePoint = {
  label: string;
  produtivo: number;
  ocioso: number;
  trocas: number;
};

type HourlyHeatmapPoint = {
  day: string;
  hour: string;
  minutes: number;
  intensity: number;
  switches: number;
};

type MetricsAnalytics = {
  activeSeconds: number;
  idleSeconds: number;
  trackedSeconds: number;
  contextSwitches: number;
  contextSwitchesPerHour: number;
  focusScore: number;
  fragmentationScore: number;
  longestFocusSeconds: number;
  timeDistribution: TimeDistributionSlice[];
  appRanking: RankingChartItem[];
  teamRanking: RankingChartItem[];
  userRanking: RankingChartItem[];
  timeline: ProductivityTimelinePoint[];
  contextTimeline: Array<{ label: string; trocas: number }>;
  heatmap: HourlyHeatmapPoint[];
  currentActivity: string;
  sourceLabel: string;
};

type AgentOsGroup = {
  os: string;
  online: number;
  syncing: number;
  offline: number;
  pending: number;
  total: number;
};

type QualityOsGroup = {
  os: string;
  high: number;
  medium: number;
  low: number;
  blocked: number;
  total: number;
};

const timeSliceMeta: Record<TimeDistributionSlice["key"], { name: string; color: string }> = {
  productive: { name: "Produtivo", color: "#34d399" },
  idle: { name: "Ocioso", color: "#fb923c" },
  communication: { name: "Comunicação", color: "#38bdf8" },
  internal: { name: "Sistemas internos", color: "#f97316" },
  navigation: { name: "Navegação", color: "#a78bfa" },
  other: { name: "Outros", color: "#71717a" }
};

function clamp(value: number, min = 0, max = 100) {
  return Math.min(max, Math.max(min, value));
}

function normalizeMetricText(value?: string | null) {
  return (value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function osFamily(os?: string | null) {
  const normalized = normalizeMetricText(os);
  if (normalized.includes("win")) {
    return "Windows";
  }
  if (normalized.includes("mac") || normalized.includes("darwin")) {
    return "macOS";
  }
  if (normalized.includes("linux") || normalized.includes("ubuntu") || normalized.includes("debian") || normalized.includes("fedora")) {
    return "Linux";
  }
  return os?.trim() || "Outro";
}

function categoryPt(category: string) {
  const normalized = normalizeMetricText(category);
  const dictionary: Array<[string, string]> = [
    ["productive", "Produtivo"],
    ["produtiv", "Produtivo"],
    ["business", "Sistemas internos"],
    ["gestao", "Sistemas internos"],
    ["erp", "Sistemas internos"],
    ["communication", "Comunicação"],
    ["comunic", "Comunicação"],
    ["idle", "Ocioso"],
    ["ocios", "Ocioso"],
    ["browser", "Navegação"],
    ["naveg", "Navegação"],
    ["development", "Desenvolvimento"],
    ["dev", "Desenvolvimento"],
    ["distraction", "Improdutivo"],
    ["improductive", "Improdutivo"],
    ["agent", "Agente"],
    ["sync", "Sincronização"]
  ];
  return dictionary.find(([key]) => normalized.includes(key))?.[1] ?? category;
}

function isIdleMetricRow(row: MetricsDetailedRow) {
  const signal = normalizeMetricText(`${row.eventType} ${row.category}`);
  return signal.includes("idle") || signal.includes("ocios");
}

function isContextSwitchMetricRow(row: MetricsDetailedRow) {
  return normalizeMetricText(row.eventType).includes("context_switch") || normalizeMetricText(row.category).includes("context");
}

function isAgentMetricRow(row: MetricsDetailedRow) {
  const signal = normalizeMetricText(`${row.eventType} ${row.category}`);
  return ["heartbeat", "sync", "agent", "collection_quality", "coleta"].some((token) => signal.includes(token));
}

function classifyTimeSlice(row: MetricsDetailedRow): TimeDistributionSlice["key"] | null {
  if (isIdleMetricRow(row)) {
    return "idle";
  }
  if (isContextSwitchMetricRow(row) || isAgentMetricRow(row)) {
    return null;
  }
  const signal = normalizeMetricText(`${row.app} ${row.category} ${row.eventType}`);
  if (["email", "mail", "teams", "slack", "whatsapp", "chat", "comunic"].some((token) => signal.includes(token))) {
    return "communication";
  }
  if (["erp", "crm", "sap", "protheus", "totvs", "business", "gestao", "interno", "portal", "sistema"].some((token) => signal.includes(token))) {
    return "internal";
  }
  if (["browser", "chrome", "edge", "firefox", "safari", "naveg"].some((token) => signal.includes(token))) {
    return "navigation";
  }
  if (["produtiv", "productive", "development", "dev", "planilha", "spreadsheet", "excel"].some((token) => signal.includes(token))) {
    return "productive";
  }
  return "other";
}

function buildTimeDistribution(bucketSeconds: Record<TimeDistributionSlice["key"], number>) {
  const total = Object.values(bucketSeconds).reduce((sum, value) => sum + value, 0);
  if (!total) {
    return [];
  }
  return (Object.keys(timeSliceMeta) as TimeDistributionSlice["key"][])
    .map((key) => {
      const seconds = Math.max(0, bucketSeconds[key] ?? 0);
      const meta = timeSliceMeta[key];
      return {
        key,
        name: meta.name,
        color: meta.color,
        seconds,
        value: seconds > 0 ? Math.max(1, Math.round(seconds / 60)) : 0,
        percent: Math.round((seconds / total) * 100)
      };
    })
    .filter((item) => item.seconds > 0);
}

function topRanking(map: Map<string, { seconds: number; detail?: string }>, limit = 8): RankingChartItem[] {
  return [...map.entries()]
    .map(([name, item]) => ({
      name,
      value: Math.max(1, Math.round(item.seconds / 60)),
      detail: item.detail ?? formatDuration(item.seconds)
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, limit);
}

function hourBucket(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return { key: "sem-data", label: "sem hora", day: "Sem data", hour: "--", sort: 0 };
  }
  const day = weekdayMap[date.getDay()];
  const hour = date.getHours().toString().padStart(2, "0");
  return {
    key: `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}-${hour}`,
    label: `${day} ${hour}h`,
    day,
    hour,
    sort: new Date(date.getFullYear(), date.getMonth(), date.getDate(), date.getHours()).getTime()
  };
}

function buildMetricsAnalytics(
  rows: MetricsDetailedRow[],
  operationalMetrics: OperationalMetric[],
  operationalIntelligence: OperationalIntelligence,
  hierarchy: HierarchyNode[],
  allowFallbackSummary: boolean
): MetricsAnalytics {
  if (!rows.length) {
    const summaryActiveSeconds = operationalIntelligence.totalActiveSeconds || sumMetric(operationalMetrics, "active_seconds");
    const summaryIdleSeconds = operationalIntelligence.totalIdleSeconds || sumMetric(operationalMetrics, "idle_seconds");
    const summaryContextSwitches = operationalIntelligence.contextSwitches || sumMetric(operationalMetrics, "context_switch_count");
    const hasSummaryData = Boolean(summaryActiveSeconds || summaryIdleSeconds || summaryContextSwitches || operationalIntelligence.timeline.length || operationalIntelligence.topApps.length);
    if (!hasSummaryData && !allowFallbackSummary) {
      return emptyMetricsAnalytics("Filtro sem resultado real");
    }

    const demoMode = !hasSummaryData && allowFallbackSummary;
    const activeSeconds = demoMode ? 7.2 * 3600 : summaryActiveSeconds;
    const idleSeconds = demoMode ? 1.4 * 3600 : summaryIdleSeconds;
    const trackedSeconds = activeSeconds + idleSeconds;
    const contextSwitches = demoMode ? 42 : summaryContextSwitches;
    const hours = Math.max(trackedSeconds / 3600, 1);
    const contextSwitchesPerHour = demoMode ? 5.8 : (operationalIntelligence.contextSwitchesPerHour || contextSwitches / hours);
    const focusScore = demoMode ? 78 : (operationalIntelligence.focusScore || clamp((activeSeconds / Math.max(trackedSeconds, 1)) * 100 - contextSwitchesPerHour * 0.9));
    const fragmentationScore = demoMode ? 38 : (operationalIntelligence.distractionScore || clamp(contextSwitchesPerHour * 3.1));
    const bucketSeconds = {
      productive: activeSeconds * 0.46,
      idle: idleSeconds,
      communication: activeSeconds * 0.16,
      internal: activeSeconds * 0.25,
      navigation: activeSeconds * 0.07,
      other: activeSeconds * 0.06
    };
    const appRanking = operationalIntelligence.topApps.length
      ? operationalIntelligence.topApps
          .filter((item) => item.app !== "Ociosidade")
          .map((item) => ({ name: item.app, value: Math.max(1, Math.round((item.activeSeconds || item.idleSeconds) / 60)), detail: `${item.focusLabel} | ${item.events} eventos` }))
          .slice(0, 8)
      : demoMode
        ? appUsage.map((item) => ({ name: item.app, value: item.minutes, detail: "dados demo" }))
        : [];
    const timeline = operationalIntelligence.timeline.length
      ? operationalIntelligence.timeline.map((point) => ({
          label: point.label,
          produtivo: Math.round(point.activeSeconds / 60),
          ocioso: Math.round(point.idleSeconds / 60),
          trocas: point.contextSwitches
        }))
      : demoMode
        ? weekdayOrder.slice(0, 5).map((day, index) => ({ label: day, produtivo: 210 + index * 18, ocioso: 32 + index * 4, trocas: 5 + index * 2 }))
        : [];
    const departmentPerformance = buildDepartmentPerformance(operationalMetrics, hierarchy.length ? hierarchy : fallbackHierarchy, demoMode);
    const userPerformance = buildTopUsers(operationalMetrics, hierarchy.length ? hierarchy : fallbackHierarchy);
    return {
      activeSeconds,
      idleSeconds,
      trackedSeconds,
      contextSwitches,
      contextSwitchesPerHour,
      focusScore,
      fragmentationScore,
      longestFocusSeconds: operationalIntelligence.longestFocusSeconds || (demoMode ? 54 * 60 : 0),
      timeDistribution: buildTimeDistribution(bucketSeconds),
      appRanking,
      teamRanking: departmentPerformance.map((item) => ({ name: item.name, value: Math.max(1, Math.round((item.active ?? 0) / 60)), detail: `${item.score}% foco` })),
      userRanking: userPerformance.length
        ? userPerformance.map((item) => ({ name: item.name, value: Math.max(1, Math.round(item.active / 60)), detail: item.title }))
        : demoMode
          ? fallbackHierarchy.slice(1).map((item, index) => ({ name: item.name, value: 260 - index * 38, detail: item.title }))
          : [],
      timeline,
      contextTimeline: timeline.filter((point) => point.trocas > 0).map((point) => ({ label: point.label, trocas: point.trocas })),
      heatmap: operationalIntelligence.timeline.length
        ? buildTimelineHeatmap(operationalIntelligence.timeline)
        : demoMode
          ? buildDemoHeatmap()
          : [],
      currentActivity: operationalIntelligence.currentActivity,
      sourceLabel: demoMode ? "dados demo sinalizados" : operationalIntelligence.periodLabel
    };
  }

  const bucketSeconds: Record<TimeDistributionSlice["key"], number> = {
    productive: 0,
    idle: 0,
    communication: 0,
    internal: 0,
    navigation: 0,
    other: 0
  };
  const appTotals = new Map<string, { seconds: number; detail?: string }>();
  const teamTotals = new Map<string, { seconds: number; detail?: string }>();
  const userTotals = new Map<string, { seconds: number; detail?: string }>();
  const timelineTotals = new Map<string, ProductivityTimelinePoint & { sort: number }>();
  const heatmapTotals = new Map<string, HourlyHeatmapPoint>();
  let activeSeconds = 0;
  let idleSeconds = 0;
  let contextSwitches = 0;
  let longestFocusSeconds = 0;

  rows.forEach((row) => {
    const duration = Math.max(0, Number(row.durationSeconds ?? 0));
    const bucket = hourBucket(row.occurredAt);
    const timelineRow = timelineTotals.get(bucket.key) ?? { label: bucket.label, produtivo: 0, ocioso: 0, trocas: 0, sort: bucket.sort };
    const heatmapKey = `${bucket.day}-${bucket.hour}`;
    const heatmapRow = heatmapTotals.get(heatmapKey) ?? { day: bucket.day, hour: bucket.hour, minutes: 0, intensity: 0, switches: 0 };

    if (isContextSwitchMetricRow(row)) {
      contextSwitches += 1;
      timelineRow.trocas += 1;
      heatmapRow.switches += 1;
      timelineTotals.set(bucket.key, timelineRow);
      heatmapTotals.set(heatmapKey, heatmapRow);
      return;
    }
    if (isAgentMetricRow(row)) {
      return;
    }

    const slice = classifyTimeSlice(row);
    if (!slice || duration <= 0) {
      return;
    }

    bucketSeconds[slice] += duration;
    heatmapRow.minutes += Math.max(1, Math.round(duration / 60));
    if (slice === "idle") {
      idleSeconds += duration;
      timelineRow.ocioso += Math.max(1, Math.round(duration / 60));
    } else {
      activeSeconds += duration;
      timelineRow.produtivo += Math.max(1, Math.round(duration / 60));
      longestFocusSeconds = Math.max(longestFocusSeconds, duration);
      const appRow = appTotals.get(row.app) ?? { seconds: 0, detail: categoryPt(row.category) };
      appRow.seconds += duration;
      appTotals.set(row.app, appRow);
      const teamName = row.teamName || row.department || "Sem equipe";
      const teamRow = teamTotals.get(teamName) ?? { seconds: 0, detail: row.department };
      teamRow.seconds += duration;
      teamTotals.set(teamName, teamRow);
      const userRow = userTotals.get(row.userName) ?? { seconds: 0, detail: row.userTitle ?? row.teamName ?? row.department };
      userRow.seconds += duration;
      userTotals.set(row.userName, userRow);
    }
    timelineTotals.set(bucket.key, timelineRow);
    heatmapTotals.set(heatmapKey, heatmapRow);
  });

  const trackedSeconds = activeSeconds + idleSeconds;
  const contextSwitchesPerHour = contextSwitches / Math.max(trackedSeconds / 3600, 1);
  const focusScore = clamp((activeSeconds / Math.max(trackedSeconds, 1)) * 100 - contextSwitchesPerHour * 1.1);
  const fragmentationScore = clamp(contextSwitchesPerHour * 3.2 + contextSwitches * 0.08);
  const heatmapMax = Math.max(...[...heatmapTotals.values()].map((item) => item.minutes), 1);
  const heatmap = [...heatmapTotals.values()]
    .map((item) => ({ ...item, intensity: Math.round((item.minutes / heatmapMax) * 100) }))
    .sort((a, b) => weekdayOrder.indexOf(a.day) - weekdayOrder.indexOf(b.day) || a.hour.localeCompare(b.hour));
  const latestRow = rows.reduce<MetricsDetailedRow | null>((latest, row) => {
    if (!latest) {
      return row;
    }
    return new Date(row.occurredAt).getTime() > new Date(latest.occurredAt).getTime() ? row : latest;
  }, null);

  return {
    activeSeconds,
    idleSeconds,
    trackedSeconds,
    contextSwitches,
    contextSwitchesPerHour,
    focusScore,
    fragmentationScore,
    longestFocusSeconds,
    timeDistribution: buildTimeDistribution(bucketSeconds),
    appRanking: topRanking(appTotals),
    teamRanking: topRanking(teamTotals, 8),
    userRanking: topRanking(userTotals, 8),
    timeline: [...timelineTotals.values()]
      .sort((a, b) => a.sort - b.sort)
      .map(({ sort: _sort, ...point }) => point)
      .slice(-24),
    contextTimeline: [...timelineTotals.values()]
      .sort((a, b) => a.sort - b.sort)
      .filter((point) => point.trocas > 0)
      .map((point) => ({ label: point.label, trocas: point.trocas }))
      .slice(-24),
    heatmap,
    currentActivity: latestRow ? `${latestRow.userName}: ${latestRow.app} (${categoryPt(latestRow.category)})` : "Sem evento recente no recorte",
    sourceLabel: `recorte filtrado (${rows.length} eventos)`
  };
}

function emptyMetricsAnalytics(sourceLabel: string): MetricsAnalytics {
  return {
    activeSeconds: 0,
    idleSeconds: 0,
    trackedSeconds: 0,
    contextSwitches: 0,
    contextSwitchesPerHour: 0,
    focusScore: 0,
    fragmentationScore: 0,
    longestFocusSeconds: 0,
    timeDistribution: [],
    appRanking: [],
    teamRanking: [],
    userRanking: [],
    timeline: [],
    contextTimeline: [],
    heatmap: [],
    currentActivity: "Sem dados para o filtro atual",
    sourceLabel
  };
}

function buildTimelineHeatmap(timeline: OperationalTimelinePoint[]): HourlyHeatmapPoint[] {
  const rows = timeline.map((point, index) => {
    const hourMatch = point.label.match(/(\d{1,2})/);
    const minutes = Math.round((point.activeSeconds + point.idleSeconds + point.unidentifiedSeconds) / 60);
    return {
      day: weekdayOrder[index % weekdayOrder.length],
      hour: hourMatch ? hourMatch[1].padStart(2, "0") : `${(8 + index).toString().padStart(2, "0")}`,
      minutes,
      intensity: 0,
      switches: point.contextSwitches
    };
  });
  const maxMinutes = Math.max(...rows.map((item) => item.minutes), 1);
  return rows.map((item) => ({ ...item, intensity: Math.round((item.minutes / maxMinutes) * 100) }));
}

function buildDemoHeatmap(): HourlyHeatmapPoint[] {
  const hours = ["08", "09", "10", "11", "14", "15", "16", "17"];
  const rows = weekdayOrder.slice(0, 5).flatMap((day, dayIndex) =>
    hours.map((hour, hourIndex) => {
      const minutes = 18 + ((dayIndex * 13 + hourIndex * 9) % 44);
      return {
        day,
        hour,
        minutes,
        intensity: Math.round((minutes / 62) * 100),
        switches: (dayIndex + hourIndex) % 7
      };
    })
  );
  return rows;
}

function buildAgentStatusByOs(devices: Device[]): AgentOsGroup[] {
  const rows = new Map<string, AgentOsGroup>();
  devices.forEach((device) => {
    const os = osFamily(device.os);
    const row = rows.get(os) ?? { os, online: 0, syncing: 0, offline: 0, pending: 0, total: 0 };
    const status = normalizeMetricText(device.status);
    if (status.includes("online")) {
      row.online += 1;
    } else if (status.includes("sync")) {
      row.syncing += 1;
    } else if (status.includes("offline")) {
      row.offline += 1;
    } else {
      row.pending += 1;
    }
    row.total += 1;
    rows.set(os, row);
  });
  return [...rows.values()].sort((a, b) => b.total - a.total);
}

function buildQualityByOs(rows: MetricsDetailedRow[], devices: Device[]): QualityOsGroup[] {
  const grouped = new Map<string, QualityOsGroup>();
  const add = (osValue: string, qualityValue?: string | null) => {
    const os = osFamily(osValue);
    const row = grouped.get(os) ?? { os, high: 0, medium: 0, low: 0, blocked: 0, total: 0 };
    const quality = normalizeMetricText(qualityValue);
    if (quality.includes("blocked")) {
      row.blocked += 1;
    } else if (quality.includes("low") || quality.includes("baixa")) {
      row.low += 1;
    } else if (quality.includes("medium") || quality.includes("media")) {
      row.medium += 1;
    } else {
      row.high += 1;
    }
    row.total += 1;
    grouped.set(os, row);
  };
  if (rows.length) {
    rows.forEach((row) => add(row.os, row.collectionQuality));
  } else {
    devices.forEach((device) => add(device.os, device.collectionQuality));
  }
  return [...grouped.values()].sort((a, b) => b.total - a.total);
}

export default function HomePage() {
  const [token, setToken] = useState<string | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [authLoading, setAuthLoading] = useState(SUPABASE_AUTH_READY);
  const [authMode, setAuthMode] = useState<"supabase" | "local" | null>(null);
  const [identity, setIdentity] = useState("operador Vulcan");
  const [currentRole, setCurrentRole] = useState("guest");
  const [view, setView] = useState<ViewKey>("dashboard");
  const [metricsIntent, setMetricsIntent] = useState<MetricsIntent | null>(null);
  const [loginError, setLoginError] = useState("");
  const [metrics, setMetrics] = useState<Metric[]>(fallbackMetrics);
  const [insights, setInsights] = useState<Insight[]>(fallbackInsights);
  const [notifications, setNotifications] = useState<NotificationItem[]>(fallbackNotifications);
  const [notificationSummary, setNotificationSummary] = useState<NotificationSummary>(fallbackNotificationSummary);
  const [notificationTypes, setNotificationTypes] = useState<NotificationTypeDefinition[]>(fallbackNotificationTypes);
  const [notificationTemplates, setNotificationTemplates] = useState<NotificationTemplate[]>(fallbackNotificationTemplates);
  const [devices, setDevices] = useState<Device[]>(fallbackDevices);
  const [operationalMetrics, setOperationalMetrics] = useState<OperationalMetric[]>([]);
  const [operationalIntelligence, setOperationalIntelligence] = useState<OperationalIntelligence>(emptyOperationalIntelligence);
  const [hierarchy, setHierarchy] = useState<HierarchyNode[]>(fallbackHierarchy);
  const [departments, setDepartments] = useState<DepartmentOption[]>([]);
  const [roles, setRoles] = useState<RoleOption[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [pendingDevices, setPendingDevices] = useState<Device[]>([]);
  const [supabaseStatus, setSupabaseStatus] = useState<SupabaseStatus>(fallbackSupabaseStatus);
  const [whatsAppStatus, setWhatsAppStatus] = useState<WhatsAppStatus>(fallbackWhatsAppStatus);
  const [emailStatuses, setEmailStatuses] = useState<EmailProviderStatus[]>(fallbackEmailStatuses);
  const [aiStatus, setAIStatus] = useState<AIStatus>(fallbackAIStatus);
  const [settingsCenter, setSettingsCenter] = useState<SettingsResponseData>(fallbackSettingsCenter);
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
        setCurrentRole("supabase_user");
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
      setCurrentRole(nextSession ? "supabase_user" : "guest");
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
      setDepartments([]);
      setRoles([]);
      setTeams([]);
      setPendingDevices([]);
    }

    let cancelled = false;

    async function loadDashboard() {
      const [
        nextSupabaseStatus,
        nextWhatsAppStatus,
        nextEmailStatuses,
        nextAIStatus,
        nextSchedules,
        nextReportTemplates,
        nextNotificationTypes,
        nextNotificationTemplates,
        nextNotificationSummary,
        nextSettingsCenter
      ] = await Promise.all([
        fetchProtected<SupabaseStatus>("/supabase/status", token!, fallbackSupabaseStatus),
        fetchProtected<WhatsAppStatus>("/integrations/whatsapp/status", token!, fallbackWhatsAppStatus),
        fetchProtected<EmailProviderStatus[]>("/integrations/email/status", token!, fallbackEmailStatuses),
        fetchProtected<AIStatus>("/ai/status", token!, fallbackAIStatus),
        fetchProtected<NotificationSchedule[]>("/notifications/schedules", token!, fallbackSchedules),
        fetchProtected<ReportTemplate[]>("/reports/templates", token!, fallbackReportTemplates),
        fetchProtected<NotificationTypeDefinition[]>("/notification-types", token!, fallbackNotificationTypes),
        fetchProtected<NotificationTemplate[]>("/notification-templates", token!, fallbackNotificationTemplates),
        fetchProtected<NotificationSummary>("/notifications/summary", token!, fallbackNotificationSummary),
        fetchProtected<SettingsResponseData>("/settings", token!, fallbackSettingsCenter)
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
      setNotificationTypes(nextNotificationTypes);
      setNotificationTemplates(nextNotificationTemplates);
      setNotificationSummary(nextNotificationSummary);
      setSettingsCenter(nextSettingsCenter);

      if (nextSupabaseStatus.databaseReachable === false) {
        setMetrics(metricFallback);
        setInsights(insightFallback);
        setNotifications(notificationFallback);
        setNotificationSummary(fallbackNotificationSummary);
        setNotificationTypes(fallbackNotificationTypes);
        setNotificationTemplates(fallbackNotificationTemplates);
        setSettingsCenter(nextSettingsCenter);
        setDevices(deviceFallback);
        setOperationalMetrics([]);
        setOperationalIntelligence(emptyOperationalIntelligence);
        setHierarchy(hierarchyFallback);
        setDepartments([]);
        setRoles([]);
        setTeams([]);
        setPendingDevices([]);
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
        nextHierarchy,
        nextDepartments,
        nextRoles,
        nextTeams,
        nextPendingDevices
      ] = await Promise.all([
        fetchProtected<Metric[]>("/metrics", token!, metricFallback),
        fetchProtected<Insight[]>("/insights", token!, insightFallback),
        fetchProtected<NotificationItem[]>("/notifications", token!, notificationFallback),
        fetchProtected<Device[]>("/devices", token!, deviceFallback),
        fetchProtected<OperationalMetric[]>("/operational-metrics", token!, []),
        fetchProtected<OperationalIntelligence>("/operational-intelligence", token!, emptyOperationalIntelligence),
        fetchProtected<HierarchyNode[]>("/hierarchy", token!, hierarchyFallback),
        fetchProtected<DepartmentOption[]>("/departments", token!, []),
        fetchProtected<RoleOption[]>("/roles", token!, []),
        fetchProtected<Team[]>("/teams", token!, []),
        fetchProtected<Device[]>("/devices/pending-adoption", token!, [])
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
      setDepartments(nextDepartments);
      setRoles(nextRoles);
      setTeams(nextTeams);
      setPendingDevices(nextPendingDevices);
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
      setCurrentRole("supabase_user");
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

      const data = (await response.json()) as { accessToken: string; user?: { name?: string; email?: string; role?: string } };
      setToken(data.accessToken);
      setAuthMode("local");
      setIdentity(data.user?.name ?? data.user?.email ?? username);
      setCurrentRole(data.user?.role ?? "user");
      if (username.toLowerCase() === "teste") {
        setMetrics(liveTestMetrics);
        setInsights([]);
        setNotifications([]);
        setDevices([]);
        setOperationalMetrics([]);
        setOperationalIntelligence(emptyOperationalIntelligence);
        setHierarchy([]);
        setDepartments([]);
        setRoles([]);
        setTeams([]);
        setPendingDevices([]);
      }
    } catch {
      if ((username === "admin" && password === "admin") || (username === "teste" && password === "teste")) {
        setToken(username === "teste" ? "dev-vulcan-test-token" : "dev-vulcan-admin-token");
        setAuthMode("local");
        setIdentity(username === "teste" ? "teste" : "admin local de demonstração");
        setCurrentRole(username === "teste" ? "tenant_admin" : "owner");
        if (username === "teste") {
          setMetrics(liveTestMetrics);
          setInsights([]);
          setNotifications([]);
          setDevices([]);
          setOperationalMetrics([]);
          setOperationalIntelligence(emptyOperationalIntelligence);
          setHierarchy([]);
          setDepartments([]);
          setRoles([]);
          setTeams([]);
          setPendingDevices([]);
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
    setCurrentRole("guest");
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

  function roleIdForHierarchyLevel(level: number) {
    const desiredScope = hierarchyLevelCatalog.find((item) => item.value === level)?.scope ?? "self";
    const scopedRole = roles.find((role) => role.scope === desiredScope);
    if (scopedRole) {
      return scopedRole.id;
    }
    return roles.find((role) => role.scope === "hierarchy")?.id ?? roles[0]?.id ?? null;
  }

  async function refreshHierarchyData() {
    if (!token) {
      return;
    }
    const [nextHierarchy, nextDevices, nextDepartments, nextRoles, nextTeams, nextPendingDevices] = await Promise.all([
      fetchProtected<HierarchyNode[]>("/hierarchy", token, liveTestMode ? [] : fallbackHierarchy),
      fetchProtected<Device[]>("/devices", token, liveTestMode ? [] : fallbackDevices),
      fetchProtected<DepartmentOption[]>("/departments", token, []),
      fetchProtected<RoleOption[]>("/roles", token, []),
      fetchProtected<Team[]>("/teams", token, []),
      fetchProtected<Device[]>("/devices/pending-adoption", token, [])
    ]);
    setHierarchy(nextHierarchy);
    setDevices(nextDevices);
    setDepartments(nextDepartments);
    setRoles(nextRoles);
    setTeams(nextTeams);
    setPendingDevices(nextPendingDevices);
    setLastRefreshAt(new Date());
  }

  async function handleHierarchyMemberSave(payload: HierarchyMemberFormPayload) {
    if (!token) {
      throw new Error("Sessão expirada.");
    }
    const roleId = roleIdForHierarchyLevel(payload.level);
    if (!roleId) {
      throw new Error("Perfis de acesso ainda não foram carregados.");
    }
    const body: Record<string, unknown> = {
      tenantId: DEMO_TENANT_ID,
      username: payload.username.trim(),
      roleId,
      departmentId: payload.departmentId,
      directManagerMembershipId: payload.parentId,
      fullName: payload.fullName.trim(),
      workEmail: payload.workEmail.trim(),
      phone: payload.phone.trim() || null,
      whatsapp: payload.whatsapp.trim() || null,
      whatsappEnabled: payload.whatsappEnabled,
      whatsappOptIn: payload.whatsappOptIn,
      whatsappNotificationTypes: [],
      quietHoursStart: payload.quietHoursStart || null,
      quietHoursEnd: payload.quietHoursEnd || null,
      title: payload.title.trim(),
      hierarchyLevel: payload.level
    };
    if (payload.password.trim()) {
      body.password = payload.password.trim();
    }
    const response = await fetch(`${API_URL}${payload.id ? `/memberships/${payload.id}` : "/memberships"}`, {
      method: payload.id ? "PUT" : "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "X-Tenant-Id": DEMO_TENANT_ID
      },
      body: JSON.stringify(body)
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Não foi possível salvar." }));
      throw new Error(String(error.detail ?? "Não foi possível salvar."));
    }
    await refreshHierarchyData();
  }

  async function handleHierarchyMemberDelete(membershipId: string) {
    if (!token) {
      throw new Error("Sessão expirada.");
    }
    const response = await fetch(`${API_URL}/memberships/${membershipId}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Tenant-Id": DEMO_TENANT_ID
      }
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Não foi possível excluir." }));
      throw new Error(String(error.detail ?? "Não foi possível excluir."));
    }
    await refreshHierarchyData();
  }

  async function handleDeviceAdoption(deviceId: string, membershipId: string | null, teamId: string | null, mode: "existing_user" | "dry" = "existing_user") {
    if (!token) {
      throw new Error("Sessão expirada.");
    }
    const response = await fetch(`${API_URL}/devices/${deviceId}/adopt`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "X-Tenant-Id": DEMO_TENANT_ID
      },
      body: JSON.stringify({
        tenantId: DEMO_TENANT_ID,
        mode,
        membershipId,
        teamId,
        policy: "standard"
      })
    });
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Não foi possível adotar o dispositivo." }));
      throw new Error(String(error.detail ?? "Não foi possível adotar o dispositivo."));
    }
    await refreshHierarchyData();
  }

  function openMetricsWithFilters(filters: Omit<MetricsIntent, "nonce">) {
    setMetricsIntent({ ...filters, nonce: Date.now() });
    setView("metrics");
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
            userRole={currentRole}
            metrics={metrics}
            insights={insights}
            notifications={notifications}
            notificationSummary={notificationSummary}
            notificationTypes={notificationTypes}
            notificationTemplates={notificationTemplates}
            devices={devices}
            operationalMetrics={operationalMetrics}
            operationalIntelligence={operationalIntelligence}
            hierarchy={hierarchy}
            departments={departments}
            roles={roles}
            teams={teams}
            pendingDevices={pendingDevices}
            supabaseStatus={supabaseStatus}
            whatsAppStatus={whatsAppStatus}
            emailStatuses={emailStatuses}
            aiStatus={aiStatus}
            settingsCenter={settingsCenter}
            onSettingsCenterChange={setSettingsCenter}
            schedules={schedules}
            reportTemplates={reportTemplates}
            highImpact={highImpact}
            onlineAgents={onlineAgents}
            liveStatusLabel={liveStatusLabel}
            allowDemoFallback={!liveTestMode}
            token={token}
            metricsIntent={metricsIntent}
            onOpenMetrics={openMetricsWithFilters}
            onDeviceOwnerChange={handleDeviceOwnerChange}
            onHierarchyMemberSave={handleHierarchyMemberSave}
            onHierarchyMemberDelete={handleHierarchyMemberDelete}
            onDeviceAdoption={handleDeviceAdoption}
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
  userRole,
  metrics,
  insights,
  notifications,
  notificationSummary,
  notificationTypes,
  notificationTemplates,
  devices,
  teams,
  pendingDevices,
  operationalMetrics,
  operationalIntelligence,
  hierarchy,
  departments,
  roles,
  supabaseStatus,
  whatsAppStatus,
  emailStatuses,
  aiStatus,
  settingsCenter,
  onSettingsCenterChange,
  schedules,
  reportTemplates,
  highImpact,
  onlineAgents,
  liveStatusLabel,
  allowDemoFallback,
  token,
  metricsIntent,
  onOpenMetrics,
  onDeviceOwnerChange,
  onHierarchyMemberSave,
  onHierarchyMemberDelete,
  onDeviceAdoption
}: {
  activeView: ViewKey;
  setView: (view: ViewKey) => void;
  onLogout: () => void;
  identity: string;
  authMode: "supabase" | "local";
  userRole: string;
  metrics: Metric[];
  insights: Insight[];
  notifications: NotificationItem[];
  notificationSummary: NotificationSummary;
  notificationTypes: NotificationTypeDefinition[];
  notificationTemplates: NotificationTemplate[];
  devices: Device[];
  teams: Team[];
  pendingDevices: Device[];
  operationalMetrics: OperationalMetric[];
  operationalIntelligence: OperationalIntelligence;
  hierarchy: HierarchyNode[];
  departments: DepartmentOption[];
  roles: RoleOption[];
  supabaseStatus: SupabaseStatus;
  whatsAppStatus: WhatsAppStatus;
  emailStatuses: EmailProviderStatus[];
  aiStatus: AIStatus;
  settingsCenter: SettingsResponseData;
  onSettingsCenterChange: (next: SettingsResponseData) => void;
  schedules: NotificationSchedule[];
  reportTemplates: ReportTemplate[];
  highImpact: number;
  onlineAgents: number;
  liveStatusLabel: string;
  allowDemoFallback: boolean;
  token: string;
  metricsIntent: MetricsIntent | null;
  onOpenMetrics: (filters: Omit<MetricsIntent, "nonce">) => void;
  onDeviceOwnerChange: (deviceId: string, ownerMembershipId: string | null) => void;
  onHierarchyMemberSave: (payload: HierarchyMemberFormPayload) => Promise<void>;
  onHierarchyMemberDelete: (membershipId: string) => Promise<void>;
  onDeviceAdoption: (deviceId: string, membershipId: string | null, teamId: string | null, mode?: "existing_user" | "dry") => Promise<void>;
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
              teams={teams}
              pendingDevices={pendingDevices}
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
              onOpenMetrics={onOpenMetrics}
            />
          )}
          {activeView === "hierarchy" && (
            <HierarchyView
              key="hierarchy"
              token={token}
              hierarchy={hierarchy}
              devices={devices}
              departments={departments}
              roles={roles}
              teams={teams}
              pendingDevices={pendingDevices}
              onDeviceOwnerChange={onDeviceOwnerChange}
              onHierarchyMemberSave={onHierarchyMemberSave}
              onHierarchyMemberDelete={onHierarchyMemberDelete}
              onDeviceAdoption={onDeviceAdoption}
            />
          )}
          {activeView === "metrics" && (
            <MetricsView
              key="metrics"
              operationalMetrics={operationalMetrics}
              operationalIntelligence={operationalIntelligence}
              teams={teams}
              devices={devices}
              hierarchy={hierarchy}
              token={token}
              liveStatusLabel={liveStatusLabel}
              allowDemoFallback={allowDemoFallback}
              metricsIntent={metricsIntent}
            />
          )}
          {activeView === "insights" && (
            <InsightsView
              key="insights"
              insights={insights}
              token={token}
              teams={teams}
              hierarchy={hierarchy}
              devices={devices}
              whatsAppStatus={whatsAppStatus}
              emailStatuses={emailStatuses}
              liveStatusLabel={liveStatusLabel}
              onOpenMetrics={onOpenMetrics}
            />
          )}
          {activeView === "notifications" && (
            <NotificationsView
              key="notifications"
              notifications={notifications}
              summary={notificationSummary}
              notificationTypes={notificationTypes}
              notificationTemplates={notificationTemplates}
              whatsAppStatus={whatsAppStatus}
              emailStatuses={emailStatuses}
              liveStatusLabel={liveStatusLabel}
              schedules={schedules}
              token={token}
              userRole={userRole}
            />
          )}
          {activeView === "settings" && (
            <SettingsView
              key="settings"
              settingsCenter={settingsCenter}
              onSettingsCenterChange={onSettingsCenterChange}
              supabaseStatus={supabaseStatus}
              aiStatus={aiStatus}
              whatsAppStatus={whatsAppStatus}
              emailStatuses={emailStatuses}
              devices={devices}
              pendingDevices={pendingDevices}
              teams={teams}
              hierarchy={hierarchy}
              notifications={notifications}
              schedules={schedules}
              reportTemplates={reportTemplates}
              token={token}
              userRole={userRole}
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
          className="fixed inset-0 z-50 overflow-hidden bg-black/78 p-4 backdrop-blur-xl md:p-8"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <motion.div
            className="mx-auto flex h-full max-w-[76rem] flex-col overflow-hidden border border-orange-400/20 bg-zinc-950/88 p-4 shadow-[0_0_48px_rgba(249,115,22,0.10)] md:p-6"
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

            <div className="grid min-h-0 flex-1 auto-rows-fr gap-3 overflow-hidden p-2 md:grid-cols-2 xl:grid-cols-3">
              {commands.map((command, index) => {
                const Icon = command.icon;
                const active = activeView === command.key;
                return (
                  <motion.button
                    key={command.key}
                    type="button"
                    onClick={() => setView(command.key)}
                    className={`group relative min-h-36 overflow-hidden border p-5 text-left transition will-change-transform md:min-h-40 ${
                      active
                        ? "border-orange-300 bg-orange-500 text-black shadow-[0_0_24px_rgba(249,115,22,0.18)]"
                        : "border-zinc-800 bg-black/48 text-zinc-100 hover:border-orange-400/60 hover:bg-zinc-950"
                    }`}
                    initial={{ y: 28, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: index * 0.045 }}
                    whileHover={{ y: -5, scale: 1.012 }}
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
  token,
  hierarchy,
  devices,
  departments,
  roles,
  teams,
  pendingDevices,
  onDeviceOwnerChange,
  onHierarchyMemberSave,
  onHierarchyMemberDelete,
  onDeviceAdoption
}: {
  token: string;
  hierarchy: HierarchyNode[];
  devices: Device[];
  departments: DepartmentOption[];
  roles: RoleOption[];
  teams: Team[];
  pendingDevices: Device[];
  onDeviceOwnerChange: (deviceId: string, ownerMembershipId: string | null) => void;
  onHierarchyMemberSave: (payload: HierarchyMemberFormPayload) => Promise<void>;
  onHierarchyMemberDelete: (membershipId: string) => Promise<void>;
  onDeviceAdoption: (deviceId: string, membershipId: string | null, teamId: string | null, mode?: "existing_user" | "dry") => Promise<void>;
}) {
  const [expandedNode, setExpandedNode] = useState<string | null>(null);
  const [selectedParentId, setSelectedParentId] = useState<string | null>(hierarchy[0]?.id ?? null);
  const [editingNodeId, setEditingNodeId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "ok" | "warn"; message: string } | null>(null);
  const [adoptionFeedback, setAdoptionFeedback] = useState<{ tone: "ok" | "warn"; message: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const [adoptingDeviceId, setAdoptingDeviceId] = useState<string | null>(null);
  const [deploymentPreparing, setDeploymentPreparing] = useState(false);
  const [deploymentPlan, setDeploymentPlan] = useState<AgentDeploymentPrepareResponse | null>(null);
  const [deploymentFeedback, setDeploymentFeedback] = useState<{ tone: "ok" | "warn"; message: string } | null>(null);
  const [adoptionAssignments, setAdoptionAssignments] = useState<Record<string, { membershipId: string; teamId: string }>>({});
  const [form, setForm] = useState<HierarchyMemberFormPayload>({
    parentId: hierarchy[0]?.id ?? null,
    level: 1,
    fullName: "",
    title: "Gerente",
    departmentId: departments[0]?.id ?? null,
    workEmail: "",
    username: "",
    password: "",
    phone: "",
    whatsapp: "",
    whatsappEnabled: true,
    whatsappOptIn: false,
    quietHoursStart: "22:00",
    quietHoursEnd: "07:00"
  });
  const sortedNodes = [...hierarchy].sort((a, b) => a.hierarchyLevel - b.hierarchyLevel);
  const tenantScope = hierarchy.filter((node) => node.visibleScope === "tenant" || node.visibleScope === "global").length;
  const subtreeScope = hierarchy.filter((node) => node.visibleScope === "subtree").length;
  const individualScope = hierarchy.length - tenantScope - subtreeScope;
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
  const selectedParent = hierarchy.find((node) => node.id === form.parentId) ?? hierarchy.find((node) => node.id === selectedParentId) ?? null;
  const editingNode = hierarchy.find((node) => node.id === editingNodeId) ?? null;
  const levelOptions = hierarchyLevelCatalog.filter((level) => !selectedParent || level.value > selectedParent.hierarchyLevel);
  const primaryRoleLabel = roles.length
    ? roles.map((role) => `${role.name}: ${scopePt(role.scope === "hierarchy" ? "subtree" : role.scope)}`).join(" | ")
    : "Perfis serão carregados do backend";
  const membersWithContact = hierarchy.filter((node) => node.email || node.whatsapp || node.phone).length;
  const departmentNameById = new Map(departments.map((department) => [department.id, department.name]));
  const hierarchyLevelData = hierarchyLevelCatalog
    .map((level) => ({
      name: level.shortLabel,
      value: hierarchy.filter((node) => node.hierarchyLevel === level.value).length
    }))
    .filter((item) => item.value > 0);
  const deviceStatusData = [
    { name: "Online", value: devices.filter((device) => ["online", "syncing"].includes(device.status)).length },
    { name: "Offline", value: devices.filter((device) => device.status === "offline").length },
    { name: "Pendente", value: pendingDevices.length },
    { name: "Sem vínculo", value: unassignedDevices.length }
  ].filter((item) => item.value > 0);
  const teamStructureData = teams.map((team) => ({
    name: team.name,
    value: Math.max(
      1,
      hierarchy.filter((node) => node.department === team.name).length
      + devices.filter((device) => device.teamId === team.id).length
    )
  })).slice(0, 8);

  useEffect(() => {
    if (editingNodeId) {
      return;
    }
    const firstNode = hierarchy[0] ?? null;
    if (!firstNode) {
      if (selectedParentId) {
        setSelectedParentId(null);
      }
      return;
    }
    const parentExists = form.parentId ? hierarchy.some((node) => node.id === form.parentId) : false;
    if (!parentExists) {
      const nextLevel = hierarchyLevelCatalog.find((item) => item.value > firstNode.hierarchyLevel)?.value ?? firstNode.hierarchyLevel + 1;
      setSelectedParentId(firstNode.id);
      setForm((current) => ({
        ...current,
        parentId: firstNode.id,
        level: nextLevel,
        title: current.title.trim() ? current.title : hierarchyLevelCatalog.find((item) => item.value === nextLevel)?.shortLabel ?? "Colaborador"
      }));
      return;
    }
    if (selectedParentId !== form.parentId) {
      setSelectedParentId(form.parentId);
    }
  }, [editingNodeId, form.parentId, hierarchy, selectedParentId]);

  function levelName(level: number) {
    return hierarchyLevelCatalog.find((item) => item.value === level)?.label ?? `Nível ${level}`;
  }

  function startCreate(parent: HierarchyNode) {
    const nextLevel = hierarchyLevelCatalog.find((item) => item.value > parent.hierarchyLevel)?.value ?? parent.hierarchyLevel + 1;
    setSelectedParentId(parent.id);
    setEditingNodeId(null);
    setFeedback(null);
    setForm({
      parentId: parent.id,
      level: nextLevel,
      fullName: "",
      title: hierarchyLevelCatalog.find((item) => item.value === nextLevel)?.shortLabel ?? "Colaborador",
      departmentId: departments.find((department) => department.name === parent.department)?.id ?? departments[0]?.id ?? null,
      workEmail: "",
      username: "",
      password: "",
      phone: "",
      whatsapp: "",
      whatsappEnabled: true,
      whatsappOptIn: false,
      quietHoursStart: "22:00",
      quietHoursEnd: "07:00"
    });
  }

  function startEdit(node: HierarchyNode) {
    setEditingNodeId(node.id);
    setSelectedParentId(node.parentId ?? hierarchy[0]?.id ?? null);
    setFeedback(null);
    setForm({
      id: node.id,
      parentId: node.parentId,
      level: node.hierarchyLevel,
      fullName: node.name,
      title: node.title,
      departmentId: departments.find((department) => department.name === node.department)?.id ?? departments[0]?.id ?? null,
      workEmail: node.email,
      username: node.email ? node.email.split("@")[0] : node.name.toLowerCase().replace(/\s+/g, "."),
      password: "",
      phone: node.phone ?? "",
      whatsapp: node.whatsapp ?? "",
      whatsappEnabled: node.whatsappEnabled ?? true,
      whatsappOptIn: node.whatsappOptIn ?? false,
      quietHoursStart: node.quietHoursStart?.slice(0, 5) ?? "22:00",
      quietHoursEnd: node.quietHoursEnd?.slice(0, 5) ?? "07:00"
    });
  }

  function updateForm<K extends keyof HierarchyMemberFormPayload>(key: K, value: HierarchyMemberFormPayload[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submitForm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    if (!form.fullName.trim() || !form.title.trim() || !form.workEmail.trim() || !form.username.trim()) {
      setFeedback({ tone: "warn", message: "Preencha nome, cargo, e-mail e usuário." });
      return;
    }
    if (!form.id && !form.password.trim()) {
      setFeedback({ tone: "warn", message: "Defina uma senha inicial para o novo usuário." });
      return;
    }
    if (!form.id && hierarchy.length > 0 && !form.parentId) {
      setFeedback({ tone: "warn", message: "Escolha um gestor acima deste usuário." });
      return;
    }
    try {
      setSaving(true);
      await onHierarchyMemberSave(form);
      const nextFeedback = { tone: "ok" as const, message: form.id ? "Pessoa atualizada e hierarquia recalculada." : "Pessoa criada com login, contato e hierarquia ativa." };
      if (!form.id && selectedParent) {
        startCreate(selectedParent);
      }
      setFeedback(nextFeedback);
    } catch (error) {
      setFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Não foi possível salvar." });
    } finally {
      setSaving(false);
    }
  }

  async function deleteNode(node: HierarchyNode) {
    if (!window.confirm(`Excluir ${node.name}? Subordinados diretos serão religados ao gestor acima e dispositivos ficarão sem vínculo.`)) {
      return;
    }
    try {
      setSaving(true);
      await onHierarchyMemberDelete(node.id);
      const nextFeedback = { tone: "ok" as const, message: `${node.name} foi removido e a hierarquia foi fechada.` };
      if (editingNodeId === node.id) {
        setEditingNodeId(null);
        const nextParent = hierarchy.find((candidate) => candidate.id === node.parentId) ?? hierarchy.find((candidate) => candidate.id !== node.id) ?? null;
        if (nextParent) {
          startCreate(nextParent);
        } else {
          setSelectedParentId(null);
          setForm({
            parentId: null,
            level: 1,
            fullName: "",
            title: "Gerente",
            departmentId: departments[0]?.id ?? null,
            workEmail: "",
            username: "",
            password: "",
            phone: "",
            whatsapp: "",
            whatsappEnabled: true,
            whatsappOptIn: false,
            quietHoursStart: "22:00",
            quietHoursEnd: "07:00"
          });
        }
      }
      setFeedback(nextFeedback);
    } catch (error) {
      setFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Não foi possível excluir." });
    } finally {
      setSaving(false);
    }
  }

  function adoptionValue(device: Device, key: "membershipId" | "teamId") {
    const current = adoptionAssignments[device.id];
    if (key === "membershipId") {
      return current?.membershipId ?? selectedParentId ?? hierarchy[0]?.id ?? "";
    }
    return current?.teamId ?? device.teamId ?? teams[0]?.id ?? "";
  }

  function updateAdoptionAssignment(deviceId: string, key: "membershipId" | "teamId", value: string) {
    setAdoptionAssignments((current) => ({
      ...current,
      [deviceId]: {
        membershipId: key === "membershipId" ? value : current[deviceId]?.membershipId ?? selectedParentId ?? hierarchy[0]?.id ?? "",
        teamId: key === "teamId" ? value : current[deviceId]?.teamId ?? teams[0]?.id ?? ""
      }
    }));
  }

  async function adoptPendingDevice(device: Device) {
    const membershipId = adoptionValue(device, "membershipId") || null;
    const teamId = adoptionValue(device, "teamId") || null;
    if (!membershipId) {
      setAdoptionFeedback({ tone: "warn", message: "Escolha uma pessoa para receber este dispositivo." });
      return;
    }
    try {
      setAdoptingDeviceId(device.id);
      setAdoptionFeedback(null);
      await onDeviceAdoption(device.id, membershipId, teamId, "existing_user");
      setAdoptionFeedback({ tone: "ok", message: `${device.hostname} adotado e vinculado à hierarquia.` });
    } catch (error) {
      setAdoptionFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Não foi possível adotar o dispositivo." });
    } finally {
      setAdoptingDeviceId(null);
    }
  }

  async function prepareCorporateDeployment() {
    if (deploymentPreparing) {
      return;
    }
    try {
      setDeploymentPreparing(true);
      setDeploymentFeedback(null);
      const response = await fetch(`${API_URL}/agent/deployments/prepare`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "X-Tenant-Id": DEMO_TENANT_ID
        },
        body: JSON.stringify({
          tenantId: DEMO_TENANT_ID,
          target: "windows_corporate"
        })
      });
      const data = await response.json().catch(() => null) as AgentDeploymentPrepareResponse | { detail?: string } | null;
      if (!response.ok || !data || !("powershellCommand" in data)) {
        const detail = data && "detail" in data ? data.detail : null;
        throw new Error(String(detail ?? "Não foi possível preparar o disparo."));
      }
      setDeploymentPlan(data);
      setDeploymentFeedback({
        tone: data.remoteExecutionAvailable ? "ok" : "warn",
        message: data.message
      });
    } catch (error) {
      setDeploymentFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Não foi possível preparar o disparo." });
    } finally {
      setDeploymentPreparing(false);
    }
  }

  return (
    <ViewFrame>
      <div className="mb-5 grid gap-3 md:grid-cols-4">
        <ConnectionSummary label="Pessoas visíveis" value={`${hierarchy.length}`} tone={hierarchy.length ? "ok" : "warn"} />
        <ConnectionSummary label="Gestores de árvore" value={`${subtreeScope}`} tone={subtreeScope ? "ok" : "warn"} />
        <ConnectionSummary label="Usuários individuais" value={`${Math.max(0, individualScope)}`} tone="ok" />
        <ConnectionSummary label="Contatos configurados" value={`${membersWithContact}/${hierarchy.length}`} tone={membersWithContact === hierarchy.length ? "ok" : "warn"} />
      </div>

      <div className="mb-5 grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <Tremor.Card className="rounded-lg border border-zinc-800 bg-zinc-950/82 p-5 shadow-tremor-card">
          <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
            <div>
              <Tremor.Text className="text-xs uppercase tracking-[0.2em] text-orange-200">Arquitetura da empresa</Tremor.Text>
              <Tremor.Title className="mt-2 text-zinc-50">Quem vê, quem responde e quais dispositivos alimentam cada pessoa.</Tremor.Title>
            </div>
            <Tremor.Badge color={pendingDevices.length ? "orange" : "emerald"}>{pendingDevices.length ? "adoção aberta" : "fechado"}</Tremor.Badge>
          </div>
          <div className="grid gap-4 md:grid-cols-[0.9fr_1.1fr]">
            <div className="grid place-items-center rounded-lg border border-orange-400/15 bg-black/35 p-4">
              <Tremor.DonutChart
                className="h-56"
                data={deviceStatusData.length ? deviceStatusData : [{ name: "Sem dados", value: 1 }]}
                category="value"
                index="name"
                colors={["emerald", "rose", "orange", "zinc"]}
                variant="donut"
                valueFormatter={(value) => `${value}`}
                showAnimation
              />
            </div>
            <div className="grid content-center gap-3">
              <ConnectionSummary label="Escopo empresa" value={`${tenantScope}`} tone={tenantScope ? "ok" : "warn"} />
              <ConnectionSummary label="Escopo subárvore" value={`${subtreeScope}`} tone={subtreeScope ? "ok" : "warn"} />
              <ConnectionSummary label="Dispositivos vinculados" value={`${devices.filter((device) => device.ownerMembershipId).length}/${devices.length}`} tone={devices.length ? "ok" : "warn"} />
            </div>
          </div>
        </Tremor.Card>

        <div className="grid gap-5 md:grid-cols-2">
          <Tremor.Card className="rounded-lg border border-zinc-800 bg-zinc-950/82 p-5 shadow-tremor-card">
            <Tremor.Title className="mb-4 text-zinc-50">Níveis da pirâmide</Tremor.Title>
            {hierarchyLevelData.length ? (
              <Tremor.BarList data={hierarchyLevelData} color="orange" valueFormatter={(value: number) => `${value}`} />
            ) : (
              <EmptyState title="Sem níveis" description="Cadastre a primeira pessoa para abrir a pirâmide." />
            )}
          </Tremor.Card>
          <Tremor.Card className="rounded-lg border border-zinc-800 bg-zinc-950/82 p-5 shadow-tremor-card">
            <Tremor.Title className="mb-4 text-zinc-50">Equipes operacionais</Tremor.Title>
            {teamStructureData.length ? (
              <Tremor.BarList data={teamStructureData} color="orange" valueFormatter={(value: number) => `${value}`} />
            ) : (
              <EmptyState title="Sem equipes" description="Crie equipes para separar operação, financeiro, suporte e administrativo." />
            )}
          </Tremor.Card>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <Panel title="Organograma vivo e editável" icon={Network}>
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
                    className={`relative grid gap-3 border bg-zinc-950/80 p-4 md:grid-cols-[auto_1fr_auto] ${editingNodeId === node.id ? "border-orange-300/70 shadow-[0_0_28px_rgba(249,115,22,0.10)]" : "border-zinc-800"}`}
                    style={{ marginLeft: `${Math.min(node.hierarchyLevel, 7) * 18}px` }}
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
                        <span className="border border-zinc-700 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-zinc-400">{levelName(node.hierarchyLevel)}</span>
                      </div>
                      <p className="mt-1 text-sm text-zinc-400">{node.title} | {node.department}</p>
                      <p className="mt-2 break-all text-xs text-zinc-600">
                        {node.email || "sem e-mail"} | WhatsApp: {node.whatsapp || "não definido"} | Tel: {node.phone || "não definido"}
                      </p>
                    </div>
                    <div className="text-left md:text-right">
                      <p className="text-2xl font-semibold text-orange-200">{node.directReports}</p>
                      <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">subordinados</p>
                      <div className="mt-3 flex flex-wrap justify-start gap-2 md:justify-end">
                        <button type="button" onClick={() => startCreate(node)} className="border border-emerald-400/25 px-3 py-2 text-xs text-emerald-200 transition hover:border-emerald-300/60">Criar abaixo</button>
                        <button type="button" onClick={() => startEdit(node)} className="border border-orange-400/25 px-3 py-2 text-xs text-orange-200 transition hover:border-orange-300/60">Editar</button>
                        <button type="button" onClick={() => void deleteNode(node)} className="border border-rose-400/25 px-3 py-2 text-xs text-rose-200 transition hover:border-rose-300/60">Excluir</button>
                        <button
                          type="button"
                          onClick={() => setExpandedNode(expandedNode === node.id ? null : node.id)}
                          className="border border-zinc-700 px-3 py-2 text-xs text-zinc-300 transition hover:border-orange-400/45"
                        >
                          {(devicesByOwner.get(node.id)?.length ?? 0)} disp.
                        </button>
                      </div>
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
        <Panel title={editingNode ? "Editar pessoa da pirâmide" : "Cadastrar abaixo da hierarquia"} icon={ShieldCheck}>
          <div className="grid gap-4">
              <div className="border border-orange-400/20 bg-orange-950/10 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-orange-300">Regra ativa</p>
                <p className="mt-2 text-sm leading-6 text-zinc-300">
                {hierarchy.length
                  ? "O cadastro sempre nasce abaixo do gestor escolhido. Um gestor só consegue criar níveis inferiores dentro do escopo visível."
                  : "A primeira pessoa criada abre a pirâmide da empresa. Depois disso, todo novo usuário nasce abaixo de um gestor visível."}
              </p>
              <p className="mt-2 text-xs leading-5 text-zinc-500">{primaryRoleLabel}</p>
            </div>

            {feedback ? <FeedbackBanner tone={feedback.tone} message={feedback.message} /> : null}

            <form onSubmit={(event) => void submitForm(event)} className="grid gap-3">
              <div className="grid gap-3 md:grid-cols-2">
                <label className="grid gap-2 text-sm text-zinc-300">
                  Gestor acima
                  <select
                    value={form.parentId ?? ""}
                    onChange={(event) => {
                      const parent = hierarchy.find((node) => node.id === event.target.value) ?? null;
                      const nextLevel = hierarchyLevelCatalog.find((item) => !parent || item.value > parent.hierarchyLevel)?.value ?? form.level;
                      setSelectedParentId(parent?.id ?? null);
                      setForm((current) => ({ ...current, parentId: parent?.id ?? null, level: nextLevel }));
                    }}
                    className="h-12 border border-zinc-800 bg-black/60 px-3 text-zinc-100 outline-none focus:border-orange-400"
                  >
                    {hierarchy.length ? <option value="" disabled>Escolha um gestor</option> : <option value="">Sem gestor: primeiro nível</option>}
                    {hierarchy.map((node) => (
                      <option key={node.id} value={node.id}>{node.name} - {node.title}</option>
                    ))}
                  </select>
                </label>
                <label className="grid gap-2 text-sm text-zinc-300">
                  Nível na pirâmide
                  <select
                    value={form.level}
                    onChange={(event) => {
                      const level = Number(event.target.value);
                      updateForm("level", level);
                      updateForm("title", hierarchyLevelCatalog.find((item) => item.value === level)?.shortLabel ?? form.title);
                    }}
                    className="h-12 border border-zinc-800 bg-black/60 px-3 text-zinc-100 outline-none focus:border-orange-400"
                  >
                    {(levelOptions.length ? levelOptions : hierarchyLevelCatalog).map((level) => (
                      <option key={level.value} value={level.value}>{level.label}</option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <HierarchyInput label="Nome completo" value={form.fullName} onChange={(value) => updateForm("fullName", value)} />
                <HierarchyInput label="Cargo exibido" value={form.title} onChange={(value) => updateForm("title", value)} />
              </div>

              <label className="grid gap-2 text-sm text-zinc-300">
                Departamento
                <select
                  value={form.departmentId ?? ""}
                  onChange={(event) => updateForm("departmentId", event.target.value || null)}
                  className="h-12 border border-zinc-800 bg-black/60 px-3 text-zinc-100 outline-none focus:border-orange-400"
                >
                  <option value="">Sem departamento</option>
                  {departments.map((department) => (
                    <option key={department.id} value={department.id}>{department.name}</option>
                  ))}
                </select>
              </label>

              <div className="grid gap-3 md:grid-cols-2">
                <HierarchyInput label="E-mail de trabalho/notificação" value={form.workEmail} onChange={(value) => updateForm("workEmail", value)} type="email" />
                <HierarchyInput label="Usuário de login" value={form.username} onChange={(value) => updateForm("username", value)} />
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <HierarchyInput label={form.id ? "Nova senha opcional" : "Senha inicial"} value={form.password} onChange={(value) => updateForm("password", value)} type="password" />
                <HierarchyInput label="Telefone" value={form.phone} onChange={(value) => updateForm("phone", value)} />
                <HierarchyInput label="WhatsApp para alertas" value={form.whatsapp} onChange={(value) => updateForm("whatsapp", value)} />
              </div>

              <div className="grid gap-3 border border-zinc-800 bg-black/35 p-4 md:grid-cols-4">
                <button type="button" onClick={() => updateForm("whatsappEnabled", !form.whatsappEnabled)} className={`h-11 border px-3 text-sm ${form.whatsappEnabled ? "border-emerald-400/30 text-emerald-200" : "border-zinc-700 text-zinc-500"}`}>
                  WhatsApp {form.whatsappEnabled ? "ativo" : "inativo"}
                </button>
                <button type="button" onClick={() => updateForm("whatsappOptIn", !form.whatsappOptIn)} className={`h-11 border px-3 text-sm ${form.whatsappOptIn ? "border-emerald-400/30 text-emerald-200" : "border-orange-400/25 text-orange-200"}`}>
                  Opt-in {form.whatsappOptIn ? "confirmado" : "pendente"}
                </button>
                <HierarchyInput label="Silêncio início" value={form.quietHoursStart} onChange={(value) => updateForm("quietHoursStart", value)} type="time" />
                <HierarchyInput label="Silêncio fim" value={form.quietHoursEnd} onChange={(value) => updateForm("quietHoursEnd", value)} type="time" />
              </div>

              <div className="grid gap-3 border border-zinc-800 bg-black/35 p-4 md:grid-cols-3">
                <ConnectionSummary label="Gestor" value={selectedParent?.name ?? (hierarchy.length ? "não definido" : "primeiro nível")} tone={selectedParent || !hierarchy.length ? "ok" : "warn"} />
                <ConnectionSummary label="Nível" value={levelName(form.level)} tone="ok" />
                <ConnectionSummary label="Departamento" value={form.departmentId ? departmentNameById.get(form.departmentId) ?? "definido" : "sem setor"} tone={form.departmentId ? "ok" : "warn"} />
              </div>

              <div className="flex flex-wrap gap-3">
                <button type="submit" disabled={saving} className="inline-flex h-12 items-center gap-2 bg-orange-500 px-5 font-semibold text-black transition hover:bg-orange-400 disabled:opacity-50">
                  <Save className="h-4 w-4" />
                  {saving ? "Salvando..." : form.id ? "Salvar edição" : "Criar usuário"}
                </button>
                {editingNode ? (
                  <button type="button" onClick={() => startCreate(selectedParent ?? hierarchy[0])} className="h-12 border border-zinc-700 px-5 text-sm text-zinc-200 transition hover:border-orange-400/50">
                    Novo abaixo
                  </button>
                ) : null}
              </div>
            </form>

            <div className="grid gap-3 md:grid-cols-2">
              <ConnectionSummary label="Dispositivos vinculados" value={`${devices.filter((device) => device.ownerMembershipId).length}/${devices.length}`} tone="ok" />
              <ConnectionSummary label="Sem vínculo" value={`${unassignedDevices.length}`} tone={unassignedDevices.length ? "warn" : "ok"} />
            </div>

            <div className="border border-orange-400/15 bg-black/35 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-orange-300">Dispositivos aguardando adoção</p>
                  <p className="mt-2 text-sm leading-6 text-zinc-400">
                    O agente aparece pendente, o gestor escolhe pessoa/equipe e ele passa a alimentar as métricas certas.
                  </p>
                </div>
                <span className="text-2xl font-semibold text-orange-200">{pendingDevices.length}</span>
              </div>
              <div className="mt-4 border border-orange-400/15 bg-orange-950/10 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-orange-300">Rollout Windows corporativo</p>
                    <p className="mt-2 text-sm leading-6 text-zinc-400">
                      Pacote oficial, token de enrollment e modo corporativo prontos para executor autorizado.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void prepareCorporateDeployment()}
                    disabled={deploymentPreparing}
                    className="inline-flex h-11 items-center gap-2 bg-orange-500 px-4 text-sm font-semibold text-black transition hover:bg-orange-400 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Download className="h-4 w-4" />
                    {deploymentPreparing ? "Preparando..." : "Preparar disparo"}
                  </button>
                </div>
                {deploymentFeedback ? <FeedbackBanner tone={deploymentFeedback.tone} message={deploymentFeedback.message} /> : null}
                {deploymentPlan ? (
                  <div className="mt-4 grid gap-3">
                    <div className="grid gap-3 md:grid-cols-3">
                      <ConnectionSummary label="Backend" value={deploymentPlan.backendUrl.replace(/^https?:\/\//, "")} tone="ok" />
                      <ConnectionSummary label="Pacote" value={deploymentPlan.packageUrl.replace(/^https?:\/\//, "")} tone="ok" />
                      <ConnectionSummary label="Executor remoto" value={deploymentPlan.remoteExecutionAvailable ? "ativo" : "pendente"} tone={deploymentPlan.remoteExecutionAvailable ? "ok" : "warn"} />
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => navigator.clipboard?.writeText(deploymentPlan.powershellCommand)}
                        className="inline-flex h-10 items-center gap-2 border border-zinc-700 px-3 text-sm text-zinc-200 transition hover:border-orange-400/50"
                      >
                        <FileText className="h-4 w-4" />
                        Copiar PowerShell
                      </button>
                      <button
                        type="button"
                        onClick={() => navigator.clipboard?.writeText(deploymentPlan.gpoCommand)}
                        className="inline-flex h-10 items-center gap-2 border border-zinc-700 px-3 text-sm text-zinc-200 transition hover:border-orange-400/50"
                      >
                        <ShieldCheck className="h-4 w-4" />
                        Copiar GPO
                      </button>
                    </div>
                    <pre className="max-h-56 overflow-auto whitespace-pre-wrap border border-zinc-800 bg-black/65 p-3 text-xs leading-5 text-zinc-300">{deploymentPlan.powershellCommand}</pre>
                    <p className="text-xs leading-5 text-zinc-500">{deploymentPlan.nextStep}</p>
                  </div>
                ) : null}
              </div>
              {adoptionFeedback ? <div className="mt-3"><FeedbackBanner tone={adoptionFeedback.tone} message={adoptionFeedback.message} /></div> : null}
              <div className="mt-4 grid gap-3">
                {pendingDevices.length ? (
                  pendingDevices.map((device) => (
                    <motion.div
                      key={device.id}
                      className="grid gap-3 border border-zinc-800 bg-zinc-950/70 p-4"
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      whileHover={{ y: -3, borderColor: "rgba(251,146,60,.45)" }}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-zinc-100">{device.hostname}</p>
                          <p className="mt-1 text-xs text-zinc-500">
                            {device.os} | usuário SO: {device.osUser ?? "não informado"} | código {device.adoptionCode ?? "pendente"}
                          </p>
                          <p className="mt-1 text-xs text-zinc-600">Último contato: {device.lastSeenAt} | qualidade {qualityPt(device.collectionQuality)}</p>
                        </div>
                        <span className="border border-orange-400/20 px-2 py-1 text-[10px] uppercase tracking-[0.16em] text-orange-200">
                          aguardando
                        </span>
                      </div>
                      <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
                        <label className="grid gap-2 text-xs uppercase tracking-[0.12em] text-zinc-500">
                          Pessoa
                          <select
                            value={adoptionValue(device, "membershipId")}
                            onChange={(event) => updateAdoptionAssignment(device.id, "membershipId", event.target.value)}
                            className="h-11 border border-zinc-800 bg-black/60 px-3 text-sm normal-case tracking-normal text-zinc-100 outline-none focus:border-orange-400"
                          >
                            {hierarchy.map((node) => (
                              <option key={node.id} value={node.id}>{node.name} - {node.title}</option>
                            ))}
                          </select>
                        </label>
                        <label className="grid gap-2 text-xs uppercase tracking-[0.12em] text-zinc-500">
                          Equipe
                          <select
                            value={adoptionValue(device, "teamId")}
                            onChange={(event) => updateAdoptionAssignment(device.id, "teamId", event.target.value)}
                            className="h-11 border border-zinc-800 bg-black/60 px-3 text-sm normal-case tracking-normal text-zinc-100 outline-none focus:border-orange-400"
                          >
                            <option value="">Sem equipe</option>
                            {teams.map((team) => (
                              <option key={team.id} value={team.id}>{team.name}</option>
                            ))}
                          </select>
                        </label>
                        <button
                          type="button"
                          onClick={() => void adoptPendingDevice(device)}
                          disabled={adoptingDeviceId === device.id || !hierarchy.length}
                          className="h-11 self-end bg-orange-500 px-4 text-sm font-semibold text-black transition hover:bg-orange-400 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {adoptingDeviceId === device.id ? "Adotando..." : "Adotar"}
                        </button>
                      </div>
                    </motion.div>
                  ))
                ) : (
                  <EmptyState title="Nenhum dispositivo pendente" description="Instale um agente sem vínculo ou rode o seed demo para ver WIN-NOVO e LINUX-NOVO nesta fila." />
                )}
              </div>
            </div>
          </div>
        </Panel>
      </div>
    </ViewFrame>
  );
}

function HierarchyInput({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return (
    <label className="grid gap-2 text-sm text-zinc-300">
      {label}
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-12 border border-zinc-800 bg-black/60 px-3 text-zinc-100 outline-none transition focus:border-orange-400 focus:shadow-[0_0_18px_rgba(249,115,22,0.10)]"
      />
    </label>
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
          Última sincronização: {device.lastSeenAt} | Equipe: {device.teamName ?? "sem equipe"} | Fila: {device.queueDepth ?? 0} | Agente: {device.agentVersion ?? "não informado"}
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

function TeamFilter({ teams, selectedTeamId, onChange }: { teams: Team[]; selectedTeamId: string; onChange: (teamId: string) => void }) {
  return (
    <label className="flex h-10 items-center gap-3 border border-zinc-800 bg-black/55 px-3 text-xs uppercase tracking-[0.16em] text-zinc-500">
      Equipe
      <select
        value={selectedTeamId}
        onChange={(event) => onChange(event.target.value)}
        className="h-full min-w-44 bg-transparent text-sm normal-case tracking-normal text-zinc-100 outline-none"
      >
        <option value="all">Toda empresa</option>
        {teams.map((team) => (
          <option key={team.id} value={team.id}>{team.name}</option>
        ))}
      </select>
    </label>
  );
}

function OperationalHealthGauge({
  onlineAgents,
  totalAgents,
  focusScore,
  idleRate,
  contextSwitchesPerHour,
  criticalSignals
}: {
  onlineAgents: number;
  totalAgents: number;
  focusScore: number;
  idleRate: number;
  contextSwitchesPerHour: number;
  criticalSignals: number;
}) {
  const onlineScore = totalAgents ? (onlineAgents / totalAgents) * 100 : 0;
  const idleScore = Math.max(0, 100 - idleRate * 100);
  const switchScore = Math.max(0, 100 - contextSwitchesPerHour * 2.2);
  const signalScore = Math.max(0, 100 - criticalSignals * 9);
  const score = Math.max(0, Math.min(100, Math.round((onlineScore * 0.28) + (focusScore * 0.30) + (idleScore * 0.18) + (switchScore * 0.14) + (signalScore * 0.10))));
  const status = score >= 88 ? "Excelente" : score >= 74 ? "Saudável" : score >= 54 ? "Atenção" : "Crítico";
  const color = score >= 88 ? "#22c55e" : score >= 74 ? "#34d399" : score >= 54 ? "#fb923c" : "#fb7185";
  const circumference = 283;
  const dashOffset = circumference - (score / 100) * circumference;
  const angle = (180 + score * 1.8) * (Math.PI / 180);
  const pointerX = 120 + Math.cos(angle) * 72;
  const pointerY = 118 + Math.sin(angle) * 72;
  const composition = [
    { label: "Agentes online", value: Math.round(onlineScore), tone: onlineScore >= 75 ? "ok" : "warn" },
    { label: "Foco", value: Math.round(focusScore), tone: focusScore >= 60 ? "ok" : "warn" },
    { label: "Baixa ociosidade", value: Math.round(idleScore), tone: idleScore >= 65 ? "ok" : "warn" },
    { label: "Sincronização", value: Math.round(signalScore), tone: signalScore >= 75 ? "ok" : "warn" }
  ];

  return (
    <div className="grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
      <div className="relative grid min-h-80 place-items-center overflow-hidden rounded-lg border border-orange-400/10 bg-[radial-gradient(circle_at_50%_58%,rgba(249,115,22,0.18),rgba(9,9,11,0)_62%)] px-4 pb-2 pt-7">
        <motion.div
          className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-300 to-transparent"
          animate={{ x: ["-100%", "100%"], opacity: [0, 0.95, 0] }}
          transition={{ duration: 4.2, repeat: Infinity, ease: "easeInOut" }}
        />
        <svg viewBox="0 0 240 158" className="h-56 w-full max-w-sm overflow-visible" role="img" aria-label={`Saúde operacional ${score} de 100, status ${status}`}>
          <path d="M30 118 A90 90 0 0 1 210 118" fill="none" stroke="rgba(255,255,255,0.10)" strokeWidth="18" strokeLinecap="round" />
          <motion.path
            d="M30 118 A90 90 0 0 1 210 118"
            fill="none"
            stroke={color}
            strokeWidth="18"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: dashOffset }}
            transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          />
          <path d="M30 118 A90 90 0 0 1 210 118" fill="none" stroke="rgba(255,255,255,0.14)" strokeWidth="1" strokeDasharray="2 13" />
          <motion.line
            x1="120"
            y1="118"
            initial={{ x2: 48, y2: 118 }}
            animate={{ x2: pointerX, y2: pointerY }}
            transition={{ duration: 0.85, ease: [0.22, 1, 0.36, 1] }}
            stroke="#fafafa"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <circle cx="120" cy="118" r="8" fill="#09090b" stroke={color} strokeWidth="3" />
          <text x="120" y="86" textAnchor="middle" className="fill-zinc-50 text-[34px] font-semibold">{score}</text>
          <text x="120" y="106" textAnchor="middle" className="fill-orange-200 text-[8px] uppercase tracking-[0.22em]">/100</text>
          <text x="30" y="148" textAnchor="middle" className="fill-zinc-600 text-[9px]">0</text>
          <text x="210" y="148" textAnchor="middle" className="fill-zinc-600 text-[9px]">100</text>
        </svg>
        <div className="absolute bottom-5 left-1/2 -translate-x-1/2 text-center">
          <p className="text-xs uppercase tracking-[0.24em] text-zinc-500">Saúde Operacional</p>
          <p className="mt-1 text-2xl font-semibold" style={{ color }}>{status}</p>
        </div>
      </div>
      <div className="grid content-center gap-3">
        <p className="text-3xl font-semibold text-zinc-50">{status === "Crítico" ? "Ação imediata" : status === "Atenção" ? "Atenção controlada" : "Operação sob controle"}</p>
        <p className="max-w-xl text-sm leading-6 text-zinc-400">
          Leitura composta por agentes online, estabilidade de sincronização, foco, baixa ociosidade, baixa troca de contexto e qualidade dos dados.
        </p>
        <div className="grid gap-3">
          {composition.map((item) => (
            <div key={item.label} className="rounded-lg border border-zinc-800 bg-black/35 p-3">
              <div className="mb-2 flex items-center justify-between text-sm">
                <span className="text-zinc-300">{item.label}</span>
                <span className={item.tone === "ok" ? "text-emerald-300" : "text-orange-300"}>{item.value}%</span>
              </div>
              <div className="h-2 overflow-hidden bg-zinc-900">
                <motion.div
                  className={`h-full ${item.tone === "ok" ? "bg-emerald-400" : "bg-orange-400"}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(100, Math.max(0, item.value))}%` }}
                  transition={{ duration: 0.7, ease: "easeOut" }}
                />
              </div>
            </div>
          ))}
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          <ConnectionSummary label="Agentes" value={`${onlineAgents}/${totalAgents || 0}`} tone={onlineAgents ? "ok" : "warn"} />
          <ConnectionSummary label="Trocas/hora" value={`${contextSwitchesPerHour.toFixed(1)}`} tone={contextSwitchesPerHour > 20 ? "warn" : "ok"} />
        </div>
      </div>
    </div>
  );
}

function DashboardView({
  metrics,
  insights,
  notifications,
  devices,
  teams,
  pendingDevices,
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
  allowDemoFallback,
  onOpenMetrics
}: {
  metrics: Metric[];
  insights: Insight[];
  notifications: NotificationItem[];
  devices: Device[];
  teams: Team[];
  pendingDevices: Device[];
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
  onOpenMetrics: (filters: Omit<MetricsIntent, "nonce">) => void;
}) {
  const activeSeconds = operationalIntelligence.totalActiveSeconds || sumMetric(operationalMetrics, "active_seconds");
  const idleSeconds = operationalIntelligence.totalIdleSeconds || sumMetric(operationalMetrics, "idle_seconds");
  const contextSwitches = operationalIntelligence.contextSwitches || sumMetric(operationalMetrics, "context_switch_count");
  const trackedSeconds = operationalIntelligence.trackedSeconds || activeSeconds + idleSeconds;
  const [selectedTeamId, setSelectedTeamId] = useState("all");
  const selectedTeam = teams.find((team) => team.id === selectedTeamId) ?? null;
  const visibleDevices = selectedTeam ? devices.filter((device) => device.teamId === selectedTeam.id) : devices;
  const visibleOnlineAgents = visibleDevices.filter((device) => ["online", "syncing"].includes(device.status)).length;
  const visibleTotalAgents = visibleDevices.length || devices.length;
  const offlineDevices = visibleDevices.filter((device) => device.status === "offline").length;
  const pendingQueue = visibleDevices.reduce((total, device) => total + Number(device.queueDepth ?? 0), 0);
  const qualityIssues = visibleDevices.filter((device) => ["low", "blocked_by_os"].includes(device.collectionQuality ?? "")).length;
  const pendingNotifications = notifications.filter((item) => ["queued", "missing_credentials", "failed"].includes(item.status)).length;
  const automationHours = insights.reduce((total, insight) => total + insight.automationSavingsHours, 0);
  const financialSavings = automationHours * 95;
  const emailReady = emailStatuses.some((item) => item.configured && item.canSend);
  const dataPlaneReady = supabaseStatus.configured && supabaseStatus.databaseReachable !== false && supabaseStatus.restReachable !== false;
  const aiReady = aiStatus.openaiConfigured || aiStatus.llamaConfigured;
  const baseMetricsFilter = selectedTeam ? { teamId: selectedTeam.id } : {};
  const recommendedActions = useMemo(
    () => buildRecommendedActions(insights, operationalIntelligence, pendingNotifications, financialSavings),
    [insights, operationalIntelligence, pendingNotifications, financialSavings]
  );
  const lossBreakdown = useMemo(
    () => buildLossBreakdown({ idleSeconds, contextSwitches, pendingQueue, offlineDevices, qualityIssues, automationHours }),
    [idleSeconds, contextSwitches, pendingQueue, offlineDevices, qualityIssues, automationHours]
  );
  const topLoss = lossBreakdown.reduce<(typeof lossBreakdown)[number] | null>(
    (current, item) => (!current || item.money > current.money ? item : current),
    null
  );
  const primaryAction = recommendedActions[0] ?? null;
  const activeUsersValue = selectedTeam ? String(selectedTeam.membersCount || 0) : metrics.find((metric) => metric.id === "active-users")?.value ?? String(hierarchy.length || 0);
  const criticalInsights = insights.filter((item) => item.impact === "high").length;
  const essentialAlerts = [
    ...notifications
      .filter((item) => ["failed", "missing_credentials", "queued"].includes(item.status))
      .slice(0, 2)
      .map((item) => ({
        id: `notification-${item.id}`,
        title: item.title,
        detail: `${channelPt(item.channel)} | ${statusPt(item.status)}${item.recipient ? ` | ${item.recipient}` : ""}`,
        severity: item.status === "failed" ? "crítico" : "atenção",
        filters: baseMetricsFilter
      })),
    ...visibleDevices
      .filter((device) => device.status === "offline" || Number(device.queueDepth ?? 0) > 6 || ["low", "blocked_by_os"].includes(device.collectionQuality ?? ""))
      .slice(0, 2)
      .map((device) => ({
        id: `device-${device.id}`,
        title: device.status === "offline" ? `Agente offline: ${device.hostname}` : `Agente exige atenção: ${device.hostname}`,
        detail: `${device.owner} | fila ${device.queueDepth ?? 0} | coleta ${qualityPt(device.collectionQuality)}`,
        severity: device.status === "offline" ? "crítico" : "atenção",
        filters: { ...baseMetricsFilter, deviceId: device.id, agentStatus: device.status }
      })),
    ...insights.slice(0, 2).map((insight) => ({
      id: `insight-${insight.id}`,
      title: insight.title,
      detail: `${impactPt(insight.impact)} | ${insight.automationSavingsHours}h potenciais`,
      severity: insight.impact === "high" ? "crítico" : "atenção",
      filters: baseMetricsFilter
    }))
  ].slice(0, 5);
  const commandKpis = [
    {
      label: "Agentes online",
      value: `${visibleOnlineAgents}/${visibleTotalAgents || 0}`,
      detail: offlineDevices ? `${offlineDevices} offline` : "sincronização estável",
      tone: offlineDevices ? "warn" : "ok",
      filters: { ...baseMetricsFilter, agentStatus: offlineDevices ? "offline" : "online" }
    },
    {
      label: "Usuários ativos",
      value: activeUsersValue,
      detail: selectedTeam?.name ?? "escopo visível",
      tone: "ok",
      filters: baseMetricsFilter
    },
    {
      label: "Gargalos críticos",
      value: `${criticalInsights}`,
      detail: criticalInsights ? "requer decisão" : "sem crítico agora",
      tone: criticalInsights ? "warn" : "ok",
      filters: { ...baseMetricsFilter, metricType: "context_switch" }
    },
    {
      label: "Foco operacional",
      value: `${operationalIntelligence.focusScore}/100`,
      detail: `maior bloco ${formatDuration(operationalIntelligence.longestFocusSeconds)}`,
      tone: operationalIntelligence.focusScore >= 60 ? "ok" : "warn",
      filters: { ...baseMetricsFilter, metricType: "productive" }
    },
    {
      label: "Economia estimada",
      value: formatMoneyBRL(financialSavings),
      detail: `${automationHours}h potenciais`,
      tone: financialSavings ? "ok" : "warn",
      filters: baseMetricsFilter
    },
    {
      label: "Alertas abertos",
      value: `${pendingNotifications}`,
      detail: pendingNotifications ? "fora do painel" : "sem pendências",
      tone: pendingNotifications ? "warn" : "ok",
      filters: baseMetricsFilter
    }
  ] as const;
  const statusItems = [
    { label: "Tempo real", value: "ativo", tone: "ok" as const },
    { label: "Última atualização", value: liveStatusLabel, tone: "ok" as const },
    { label: "Agentes", value: `${visibleOnlineAgents}/${visibleTotalAgents || 0}`, tone: visibleOnlineAgents ? "ok" as const : "warn" as const },
    { label: "IA", value: aiReady ? "configurada" : "mock explícito", tone: aiReady ? "ok" as const : "warn" as const },
    { label: "Notificações", value: whatsAppStatus.connected || emailReady || schedules.some((schedule) => schedule.enabled) ? "preparadas" : "pendentes", tone: pendingNotifications ? "warn" as const : "ok" as const }
  ];
  const quickActivity = operationalIntelligence.currentActivity || "Aguardando sinal operacional";

  return (
    <ViewFrame>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <LiveBadge label="Tempo real ativo" detail={`${onlineAgents} agente${onlineAgents === 1 ? "" : "s"} sincronizando | ${operationalIntelligence.periodLabel}`} />
        <TeamFilter teams={teams} selectedTeamId={selectedTeamId} onChange={setSelectedTeamId} />
        <span className="border border-orange-400/25 bg-orange-950/15 px-3 py-2 text-xs uppercase tracking-[0.2em] text-orange-200">
          {!dataPlaneReady ? "Modo degradado" : allowDemoFallback ? "Demo comercial" : "Dados reais"}
        </span>
      </div>

      <Panel title="Status geral" icon={Command}>
        <div className="grid gap-3 md:grid-cols-5">
          {statusItems.map((item) => (
            <ConnectionSummary key={item.label} label={item.label} value={item.value} tone={item.tone} />
          ))}
        </div>
      </Panel>

      <div className="mt-5 grid gap-5 xl:grid-cols-[0.92fr_1.08fr]">
        <Panel title="Saúde Operacional" icon={Gauge}>
          <OperationalHealthGauge
            onlineAgents={visibleOnlineAgents}
            totalAgents={visibleTotalAgents}
            focusScore={operationalIntelligence.focusScore}
            idleRate={operationalIntelligence.idleRate}
            contextSwitchesPerHour={operationalIntelligence.contextSwitchesPerHour}
            criticalSignals={offlineDevices + qualityIssues + pendingDevices.length}
          />
        </Panel>

        <div className="grid gap-5">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {commandKpis.map((item) => (
              <CommandKpiCard
                key={item.label}
                label={item.label}
                value={item.value}
                detail={item.detail}
                tone={item.tone}
                onClick={() => onOpenMetrics(item.filters)}
              />
            ))}
          </div>

          <Panel title="Ação recomendada agora" icon={Brain}>
            <div className="grid gap-4 xl:grid-cols-[1fr_auto]">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-orange-300">Prioridade</p>
                <p className="mt-3 text-2xl font-semibold leading-tight text-zinc-50">
                  {primaryAction?.title ?? operationalIntelligence.aiRecommendations[0] ?? "Mantenha os agentes ativos para consolidar o próximo diagnóstico."}
                </p>
                <p className="mt-3 text-sm leading-6 text-zinc-400">
                  Agora: {quickActivity}. Tempo ativo {formatDuration(activeSeconds)}, ocioso {formatDuration(idleSeconds)} e {Math.round(contextSwitches)} trocas no recorte.
                </p>
              </div>
              <button
                type="button"
                onClick={() => onOpenMetrics({ ...baseMetricsFilter, metricType: primaryAction?.urgency === "Alta" ? "context_switch" : undefined })}
                className="h-12 self-end bg-orange-500 px-5 text-sm font-semibold text-black transition hover:bg-orange-400"
              >
                Abrir análise
              </button>
            </div>
          </Panel>
        </div>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <Panel title="Alertas essenciais" icon={BellRing}>
          <div className="grid gap-3">
            {essentialAlerts.length ? (
              essentialAlerts.map((alert) => (
                <button
                  key={alert.id}
                  type="button"
                  onClick={() => onOpenMetrics(alert.filters)}
                  className="group border border-zinc-800 bg-black/42 p-4 text-left transition hover:border-orange-400/45 hover:bg-orange-950/10"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-zinc-100">{alert.title}</p>
                      <p className="mt-1 text-sm text-zinc-500">{alert.detail}</p>
                    </div>
                    <span className={alert.severity === "crítico" ? "text-rose-300" : "text-orange-300"}>{alert.severity}</span>
                  </div>
                  <p className="mt-3 text-xs uppercase tracking-[0.16em] text-zinc-600 transition group-hover:text-orange-200">abrir Métricas filtrada</p>
                </button>
              ))
            ) : (
              <EmptyState title="Sem alerta urgente" description="A central fica limpa quando não há agente offline, fila alta, credencial crítica ou insight de alto impacto." />
            )}
          </div>
        </Panel>

        <Panel title="Leitura de 5 segundos" icon={ShieldCheck}>
          <div className="grid gap-4">
            <div className="border border-orange-400/20 bg-[linear-gradient(135deg,rgba(249,115,22,0.12),rgba(9,9,11,0.72))] p-5">
              <p className="text-xs uppercase tracking-[0.22em] text-orange-300">Maior perda provável</p>
              <p className="mt-3 text-3xl font-semibold text-zinc-50">{formatMoneyBRL(topLoss?.money ?? financialSavings)}</p>
              <p className="mt-2 text-sm leading-6 text-zinc-400">
                {topLoss ? `${topLoss.label}: ${topLoss.action}` : "Nenhuma perda relevante detectada no recorte atual."}
              </p>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <ConnectionSummary label="Tempo analisado" value={formatDuration(trackedSeconds)} tone="ok" />
              <ConnectionSummary label="Fila offline" value={`${pendingQueue} evento${pendingQueue === 1 ? "" : "s"}`} tone={pendingQueue ? "warn" : "ok"} />
              <ConnectionSummary label="Coleta limitada" value={`${qualityIssues}`} tone={qualityIssues ? "warn" : "ok"} />
              <ConnectionSummary label="Escopo" value={selectedTeam?.name ?? "Toda empresa"} tone="ok" />
            </div>
          </div>
        </Panel>
      </div>
    </ViewFrame>
  );
}

function CommandKpiCard({
  label,
  value,
  detail,
  tone,
  onClick
}: {
  label: string;
  value: string;
  detail: string;
  tone: "ok" | "warn";
  onClick: () => void;
}) {
  return (
    <motion.button
      type="button"
      onClick={onClick}
      className="group min-h-36 rounded-lg border border-zinc-800 bg-zinc-950/78 p-4 text-left shadow-tremor-card transition hover:border-orange-400/45 hover:bg-orange-950/10"
      whileHover={{ y: -4 }}
      whileTap={{ scale: 0.985 }}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">{label}</p>
        <span className={`h-2.5 w-2.5 rounded-full ${tone === "ok" ? "bg-emerald-400" : "bg-orange-400"}`} />
      </div>
      <p className="mt-5 text-3xl font-semibold text-zinc-50">{value}</p>
      <p className="mt-3 text-sm leading-5 text-zinc-500">{detail}</p>
      <p className="mt-4 text-[10px] uppercase tracking-[0.16em] text-zinc-700 transition group-hover:text-orange-200">investigar</p>
    </motion.button>
  );
}

function ExecutiveAnalyticsDeck({
  lossData,
  systemData,
  departmentData,
  pulseData,
  pilotReadinessScore,
  financialSavings,
  pendingDevices,
  primaryAction
}: {
  lossData: { name: string; value: number }[];
  systemData: { name: string; value: number }[];
  departmentData: { setor: string; foco: number; ativo: number; ocioso: number }[];
  pulseData: { horario: string; eventos: number; automacao: number }[];
  pilotReadinessScore: number;
  financialSavings: number;
  pendingDevices: number;
  primaryAction: string;
}) {
  return (
    <div className="mb-5 grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
      <Tremor.Card className="rounded-lg border border-zinc-800 bg-zinc-950/82 p-5 shadow-tremor-card">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div>
            <Tremor.Text className="text-xs uppercase tracking-[0.2em] text-orange-200">Cockpit executivo</Tremor.Text>
            <Tremor.Title className="mt-2 text-zinc-50">A empresa em uma tela que dá vontade de abrir todo dia.</Tremor.Title>
          </div>
          <Tremor.Badge color={pendingDevices ? "orange" : "emerald"}>{pendingDevices ? `${pendingDevices} adoções pendentes` : "agentes fechados"}</Tremor.Badge>
        </div>
        <div className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="grid gap-4">
            <div className="rounded-lg border border-orange-400/15 bg-black/35 p-4">
              <Tremor.Text className="text-zinc-500">Economia potencial rastreada</Tremor.Text>
              <Tremor.Metric className="mt-2 text-zinc-50">{formatMoneyBRL(financialSavings)}</Tremor.Metric>
              <Tremor.ProgressBar className="mt-4" value={Math.min(100, Math.max(18, financialSavings / 220))} color="orange" />
              <p className="mt-3 text-sm leading-6 text-zinc-400">{primaryAction}</p>
            </div>
            <div className="rounded-lg border border-zinc-800 bg-black/35 p-4">
              <div className="mb-3 flex items-center justify-between">
                <Tremor.Text className="text-zinc-500">Prontidão de piloto pago</Tremor.Text>
                <span className="text-sm font-semibold text-orange-200">{pilotReadinessScore}%</span>
              </div>
              <Tremor.ProgressBar value={pilotReadinessScore} color={pilotReadinessScore >= 75 ? "emerald" : "orange"} />
            </div>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-black/25 p-4">
            <Tremor.Text className="mb-3 text-zinc-500">Pulso operacional</Tremor.Text>
            <Tremor.AreaChart
              className="h-52"
              data={pulseData}
              index="horario"
              categories={["eventos", "automacao"]}
              colors={["orange", "yellow"]}
              showLegend={false}
              showAnimation
            />
          </div>
        </div>
      </Tremor.Card>

      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-1">
        <Tremor.Card className="rounded-lg border border-zinc-800 bg-zinc-950/82 p-5 shadow-tremor-card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <Tremor.Title className="text-zinc-50">Perdas por causa</Tremor.Title>
            <Tremor.Badge color="orange">R$</Tremor.Badge>
          </div>
          <Tremor.BarList data={lossData} color="orange" valueFormatter={(value: number) => formatMoneyBRL(value)} />
        </Tremor.Card>
        <Tremor.Card className="rounded-lg border border-zinc-800 bg-zinc-950/82 p-5 shadow-tremor-card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <Tremor.Title className="text-zinc-50">Setores e sistemas</Tremor.Title>
            <Tremor.Badge color="zinc">tempo</Tremor.Badge>
          </div>
          {departmentData.length ? (
            <Tremor.BarChart
              className="h-48"
              data={departmentData}
              index="setor"
              categories={["foco", "ativo", "ocioso"]}
              colors={["emerald", "orange", "rose"]}
              valueFormatter={(value: number) => `${value}`}
              showLegend
              showAnimation
            />
          ) : (
            <Tremor.BarList data={systemData} color="orange" valueFormatter={(value: number) => `${value}min`} />
          )}
        </Tremor.Card>
      </div>
    </div>
  );
}

function MetricsView({
  operationalMetrics,
  operationalIntelligence,
  teams,
  devices,
  hierarchy,
  token,
  liveStatusLabel,
  allowDemoFallback,
  metricsIntent
}: {
  operationalMetrics: OperationalMetric[];
  operationalIntelligence: OperationalIntelligence;
  teams: Team[];
  devices: Device[];
  hierarchy: HierarchyNode[];
  token: string;
  liveStatusLabel: string;
  allowDemoFallback: boolean;
  metricsIntent: MetricsIntent | null;
}) {
  const [period, setPeriod] = useState("24h");
  const [selectedTeamId, setSelectedTeamId] = useState("all");
  const [selectedMembershipId, setSelectedMembershipId] = useState("all");
  const [selectedDeviceId, setSelectedDeviceId] = useState("all");
  const [selectedSupervisorId, setSelectedSupervisorId] = useState("all");
  const [selectedDepartment, setSelectedDepartment] = useState("all");
  const [selectedTitle, setSelectedTitle] = useState("all");
  const [selectedOs, setSelectedOs] = useState("all");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedAgentStatus, setSelectedAgentStatus] = useState("all");
  const [selectedMetricType, setSelectedMetricType] = useState("all");
  const [appFilter, setAppFilter] = useState("");
  const [detailedRows, setDetailedRows] = useState<MetricsDetailedRow[]>([]);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [exportFeedback, setExportFeedback] = useState<{ tone: "ok" | "warn"; message: string } | null>(null);

  useEffect(() => {
    if (!metricsIntent) {
      return;
    }
    setPeriod(metricsIntent.period ?? "24h");
    setSelectedTeamId(metricsIntent.teamId ?? "all");
    setSelectedMembershipId(metricsIntent.membershipId ?? "all");
    setSelectedDeviceId(metricsIntent.deviceId ?? "all");
    setSelectedSupervisorId(metricsIntent.supervisorId ?? "all");
    setSelectedDepartment(metricsIntent.department ?? "all");
    setSelectedTitle(metricsIntent.title ?? "all");
    setSelectedOs(metricsIntent.os ?? "all");
    setSelectedCategory(metricsIntent.category ?? "all");
    setSelectedAgentStatus(metricsIntent.agentStatus ?? "all");
    setSelectedMetricType(metricsIntent.metricType ?? "all");
    setAppFilter(metricsIntent.app ?? "");
  }, [metricsIntent]);

  const filterOptions = useMemo(() => {
    const unique = (values: Array<string | null | undefined>) => [...new Set(values.filter((value): value is string => Boolean(value && value.trim())))].sort((a, b) => a.localeCompare(b, "pt-BR"));
    return {
      departments: unique([...hierarchy.map((item) => item.department), ...detailedRows.map((item) => item.department)]),
      titles: unique([...hierarchy.map((item) => item.title), ...detailedRows.map((item) => item.userTitle)]),
      supervisors: hierarchy.filter((node) => node.directReports > 0),
      os: unique([...devices.map((device) => osFamily(device.os)), ...detailedRows.map((row) => osFamily(row.os))]),
      categories: unique(detailedRows.map((row) => row.category)),
      agentStatuses: unique(devices.map((device) => device.status)),
      apps: unique([...operationalIntelligence.topApps.map((item) => item.app).filter((app) => app !== "Ociosidade"), ...detailedRows.map((row) => row.app)]).slice(0, 20)
    };
  }, [detailedRows, devices, hierarchy, operationalIntelligence.topApps]);

  const filteredDevices = useMemo(() => devices.filter((device) => {
    if (selectedTeamId !== "all" && device.teamId !== selectedTeamId) {
      return false;
    }
    if (selectedDeviceId !== "all" && device.id !== selectedDeviceId) {
      return false;
    }
    if (selectedOs !== "all" && osFamily(device.os) !== selectedOs) {
      return false;
    }
    if (selectedAgentStatus !== "all" && device.status !== selectedAgentStatus) {
      return false;
    }
    return true;
  }), [devices, selectedAgentStatus, selectedDeviceId, selectedOs, selectedTeamId]);

  const hasScopedFilters = selectedTeamId !== "all"
    || selectedMembershipId !== "all"
    || selectedDeviceId !== "all"
    || selectedSupervisorId !== "all"
    || selectedDepartment !== "all"
    || selectedTitle !== "all"
    || selectedOs !== "all"
    || selectedCategory !== "all"
    || selectedAgentStatus !== "all"
    || selectedMetricType !== "all"
    || Boolean(appFilter.trim());
  const analytics = useMemo(
    () => buildMetricsAnalytics(detailedRows, operationalMetrics, operationalIntelligence, hierarchy, allowDemoFallback && !hasScopedFilters),
    [allowDemoFallback, detailedRows, hasScopedFilters, hierarchy, operationalIntelligence, operationalMetrics]
  );
  const activeRate = Math.round((analytics.activeSeconds / Math.max(analytics.trackedSeconds, 1)) * 100);
  const idleRate = Math.round((analytics.idleSeconds / Math.max(analytics.trackedSeconds, 1)) * 100);
  const contextLossHours = analytics.contextSwitches * 0.018;
  const idleLossHours = analytics.idleSeconds / 3600;
  const estimatedLeak = (idleLossHours + contextLossHours) * 95;
  const agentStatusByOs = useMemo(() => buildAgentStatusByOs(filteredDevices), [filteredDevices]);
  const qualityByOs = useMemo(() => buildQualityByOs(detailedRows, filteredDevices), [detailedRows, filteredDevices]);
  const actionNow = operationalIntelligence.aiRecommendations[0]
    ?? (idleRate > 25
      ? "Revisar ociosidade do turno e validar se existe espera por sistema ou processo."
      : analytics.contextSwitches > 30
        ? "Reduzir alternância entre sistemas com fila única ou automação de etapas repetidas."
        : "Manter coleta por mais algumas horas para consolidar tendência operacional.");
  const metricsQuery = useMemo(() => {
    const params = new URLSearchParams({ period });
    if (selectedTeamId !== "all") {
      params.set("teamId", selectedTeamId);
    }
    if (selectedMembershipId !== "all") {
      params.set("membershipId", selectedMembershipId);
    }
    if (selectedDeviceId !== "all") {
      params.set("deviceId", selectedDeviceId);
    }
    if (selectedSupervisorId !== "all") {
      params.set("supervisorId", selectedSupervisorId);
    }
    if (selectedDepartment !== "all") {
      params.set("department", selectedDepartment);
    }
    if (selectedTitle !== "all") {
      params.set("title", selectedTitle);
    }
    if (selectedOs !== "all") {
      params.set("os", selectedOs);
    }
    if (selectedCategory !== "all") {
      params.set("category", selectedCategory);
    }
    if (selectedAgentStatus !== "all") {
      params.set("agentStatus", selectedAgentStatus);
    }
    if (selectedMetricType !== "all") {
      params.set("metricType", selectedMetricType);
    }
    if (appFilter.trim()) {
      params.set("app", appFilter.trim());
    }
    return params.toString();
  }, [appFilter, period, selectedAgentStatus, selectedCategory, selectedDepartment, selectedDeviceId, selectedMembershipId, selectedMetricType, selectedOs, selectedSupervisorId, selectedTeamId, selectedTitle]);

  useEffect(() => {
    let cancelled = false;
    async function loadDetailedMetrics() {
      setMetricsLoading(true);
      try {
        const response = await fetch(`${API_URL}/metrics/detailed?${metricsQuery}`, {
          headers: {
            Authorization: `Bearer ${token}`,
            "X-Tenant-Id": DEMO_TENANT_ID
          }
        });
        if (!response.ok) {
          if (!cancelled) {
            setDetailedRows([]);
          }
          return;
        }
        const rows = (await response.json()) as MetricsDetailedRow[];
        if (!cancelled) {
          setDetailedRows(rows);
        }
      } catch {
        if (!cancelled) {
          setDetailedRows([]);
        }
      } finally {
        if (!cancelled) {
          setMetricsLoading(false);
        }
      }
    }
    void loadDetailedMetrics();
    return () => {
      cancelled = true;
    };
  }, [metricsQuery, token]);

  function clearFilters() {
    setPeriod("24h");
    setSelectedTeamId("all");
    setSelectedMembershipId("all");
    setSelectedDeviceId("all");
    setSelectedSupervisorId("all");
    setSelectedDepartment("all");
    setSelectedTitle("all");
    setSelectedOs("all");
    setSelectedCategory("all");
    setSelectedAgentStatus("all");
    setSelectedMetricType("all");
    setAppFilter("");
  }

  async function downloadMetrics(format: "csv" | "excel") {
    setExportFeedback(null);
    try {
      const response = await fetch(`${API_URL}/metrics/export?format=${format}&${metricsQuery}`, {
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Tenant-Id": DEMO_TENANT_ID
        }
      });
      if (!response.ok) {
        throw new Error("Exportação recusada pelo backend.");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = format === "csv" ? "vulcan-metricas.csv" : "vulcan-metricas-excel.csv";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setExportFeedback({ tone: "ok", message: format === "csv" ? "CSV gerado com os filtros atuais." : "Arquivo compatível com Excel gerado." });
    } catch (error) {
      setExportFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Não foi possível exportar." });
    }
  }

  function preparedExport(kind: "pdf" | "email" | "whatsapp") {
    const label = kind === "pdf" ? "PDF" : kind === "email" ? "envio por e-mail" : "envio por WhatsApp";
    setExportFeedback({ tone: "warn", message: `${label} está preparado na interface, mas depende do módulo de relatórios/canal real estar configurado para produção.` });
  }

  return (
    <ViewFrame>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <LiveBadge label="Métricas analíticas" detail={`Última sincronização: ${liveStatusLabel} | ${analytics.sourceLabel}`} />
        <span className="border border-orange-400/25 bg-orange-950/15 px-3 py-2 text-xs uppercase tracking-[0.2em] text-orange-200">
          investigação profunda
        </span>
      </div>

      <Panel title="Filtros e exportação" icon={Download}>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-6">
          <MetricFilterSelect label="Período" value={period} onChange={setPeriod} options={[["24h", "Últimas 24h"], ["7d", "Últimos 7 dias"], ["30d", "Últimos 30 dias"], ["90d", "Últimos 90 dias"]]} />
          <MetricFilterSelect label="Equipe" value={selectedTeamId} onChange={setSelectedTeamId} options={[["all", "Todas"], ...teams.map((team) => [team.id, team.name] as [string, string])]} />
          <MetricFilterSelect label="Usuário" value={selectedMembershipId} onChange={setSelectedMembershipId} options={[["all", "Todos"], ...hierarchy.map((node) => [node.id, node.name] as [string, string])]} />
          <MetricFilterSelect label="Supervisor" value={selectedSupervisorId} onChange={setSelectedSupervisorId} options={[["all", "Todos"], ...filterOptions.supervisors.map((node) => [node.id, node.name] as [string, string])]} />
          <MetricFilterSelect label="Departamento" value={selectedDepartment} onChange={setSelectedDepartment} options={[["all", "Todos"], ...filterOptions.departments.map((item) => [item, item] as [string, string])]} />
          <MetricFilterSelect label="Cargo" value={selectedTitle} onChange={setSelectedTitle} options={[["all", "Todos"], ...filterOptions.titles.map((item) => [item, item] as [string, string])]} />
          <MetricFilterSelect label="Dispositivo" value={selectedDeviceId} onChange={setSelectedDeviceId} options={[["all", "Todos"], ...devices.map((device) => [device.id, device.hostname] as [string, string])]} />
          <MetricFilterSelect label="Sistema operacional" value={selectedOs} onChange={setSelectedOs} options={[["all", "Todos"], ...filterOptions.os.map((item) => [item, item] as [string, string])]} />
          <MetricFilterSelect label="Categoria" value={selectedCategory} onChange={setSelectedCategory} options={[["all", "Todas"], ...filterOptions.categories.map((item) => [item, categoryPt(item)] as [string, string])]} />
          <MetricFilterSelect label="Status agente" value={selectedAgentStatus} onChange={setSelectedAgentStatus} options={[["all", "Todos"], ...filterOptions.agentStatuses.map((item) => [item, statusPt(item)] as [string, string])]} />
          <MetricFilterSelect label="Tipo de métrica" value={selectedMetricType} onChange={setSelectedMetricType} options={[["all", "Todas"], ["productive", "Produtividade"], ["idle", "Ociosidade"], ["context_switch", "Troca de contexto"], ["agent", "Agente/coleta"], ["improductive", "Improdutivo"]]} />
          <label className="grid gap-2 text-xs uppercase tracking-[0.14em] text-zinc-500">
            Aplicativo
            <input
              value={appFilter}
              onChange={(event) => setAppFilter(event.target.value)}
              list="metric-apps"
              placeholder="ERP, Chrome..."
              className="h-11 border border-zinc-800 bg-black/60 px-3 text-sm normal-case tracking-normal text-zinc-100 outline-none transition placeholder:text-zinc-700 focus:border-orange-400"
            />
            <datalist id="metric-apps">
              {filterOptions.apps.map((item) => <option key={item} value={item} />)}
            </datalist>
          </label>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" onClick={() => void downloadMetrics("csv")} className="h-10 border border-orange-400/25 px-3 text-xs text-orange-200 transition hover:border-orange-300/60">
            Exportar CSV
          </button>
          <button type="button" onClick={() => void downloadMetrics("excel")} className="h-10 bg-orange-500 px-3 text-xs font-semibold text-black transition hover:bg-orange-400">
            Exportar Excel
          </button>
          <button type="button" onClick={() => preparedExport("pdf")} className="h-10 border border-zinc-800 px-3 text-xs text-zinc-200 transition hover:border-orange-400/45">
            Exportar PDF
          </button>
          <button type="button" onClick={() => preparedExport("email")} className="h-10 border border-zinc-800 px-3 text-xs text-zinc-200 transition hover:border-orange-400/45">
            Enviar por e-mail
          </button>
          <button type="button" onClick={() => preparedExport("whatsapp")} className="h-10 border border-zinc-800 px-3 text-xs text-zinc-200 transition hover:border-orange-400/45">
            Enviar por WhatsApp
          </button>
          <button type="button" onClick={clearFilters} className="h-10 border border-zinc-800 px-3 text-xs text-zinc-500 transition hover:border-orange-400/45 hover:text-zinc-100">
            Limpar filtros
          </button>
        </div>
        {exportFeedback ? <div className="mt-3"><FeedbackBanner tone={exportFeedback.tone} message={exportFeedback.message} /></div> : null}
      </Panel>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <Panel title="Saúde operacional do recorte" icon={Gauge}>
          <div className="grid gap-4 xl:grid-cols-[1fr_1.2fr]">
            <OperationalHealthGauge
              onlineAgents={filteredDevices.filter((device) => ["online", "syncing"].includes(device.status)).length}
              totalAgents={filteredDevices.length || devices.length}
              focusScore={analytics.focusScore}
              idleRate={analytics.idleSeconds / Math.max(analytics.trackedSeconds, 1)}
              contextSwitchesPerHour={analytics.contextSwitchesPerHour}
              criticalSignals={filteredDevices.filter((device) => device.status === "offline").length + filteredDevices.filter((device) => ["low", "blocked_by_os"].includes(device.collectionQuality ?? "")).length}
            />
            <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-1">
              <MetricSpeedometer
                label="Foco operacional"
                value={analytics.focusScore}
                detail={`Maior bloco: ${formatDuration(analytics.longestFocusSeconds)}`}
                tone={analytics.focusScore >= 65 ? "ok" : analytics.focusScore >= 45 ? "warn" : "critical"}
              />
              <MetricSpeedometer
                label="Ociosidade"
                value={idleRate}
                detail={`${formatDuration(analytics.idleSeconds)} fora de fluxo ativo`}
                tone={idleRate > 35 ? "critical" : idleRate > 18 ? "warn" : "ok"}
              />
              <MetricSpeedometer
                label="Fragmentação"
                value={analytics.fragmentationScore}
                detail={`${Math.round(analytics.contextSwitches)} trocas | ${analytics.contextSwitchesPerHour.toFixed(1)}/h`}
                tone={analytics.fragmentationScore > 55 ? "critical" : analytics.fragmentationScore > 35 ? "warn" : "ok"}
              />
            </div>
          </div>
        </Panel>

        <Panel title="Distribuição de tempo" icon={Activity}>
          {analytics.timeDistribution.length ? (
            <div className="grid gap-4">
              <PremiumDonutChart data={analytics.timeDistribution} centerLabel={`${activeRate}%`} centerDetail="ativo" />
              <div className="grid gap-3">
                {analytics.timeDistribution.map((item) => (
                  <MetricLegend key={item.name} color={item.color} label={item.name} value={`${item.percent}%`} detail={formatDuration(item.seconds)} />
                ))}
              </div>
            </div>
          ) : (
            <EmptyState title="Sem tempo suficiente" description="Quando o agente sincronizar os primeiros eventos, a distribuição aparece aqui." />
          )}
        </Panel>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-4">
        <MetricSignalCard
          icon={Activity}
          label="Tempo ativo"
          value={formatDuration(analytics.activeSeconds)}
          detail={`${activeRate}% do tempo analisado no recorte.`}
          tone="ok"
        />
        <MetricSignalCard
          icon={Flame}
          label="Perda estimada"
          value={formatMoneyBRL(estimatedLeak)}
          detail="Ociosidade + custo estimado de troca de contexto."
          tone={estimatedLeak > 5000 ? "critical" : estimatedLeak > 1000 ? "warn" : "ok"}
        />
        <MetricSignalCard
          icon={Zap}
          label="Trocas de contexto"
          value={`${analytics.contextSwitches}`}
          detail={`${analytics.contextSwitchesPerHour.toFixed(1)} por hora no recorte.`}
          tone={analytics.contextSwitchesPerHour > 18 ? "warn" : "ok"}
        />
        <MetricSignalCard
          icon={Brain}
          label="Ação analítica"
          value="Prioridade atual"
          detail={actionNow}
          tone="warn"
        />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Apps mais usados" icon={BarChart3}>
          <HorizontalBarsChart data={analytics.appRanking} valueLabel="min" />
        </Panel>

        <Panel title="Linha temporal de produtividade" icon={Activity}>
          {analytics.timeline.length ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={analytics.timeline} margin={{ left: 4, right: 10, top: 12, bottom: 4 }}>
                  <defs>
                    <linearGradient id="productiveTimeline" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#34d399" stopOpacity={0.55} />
                      <stop offset="95%" stopColor="#34d399" stopOpacity={0.02} />
                    </linearGradient>
                    <linearGradient id="idleTimeline" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#fb923c" stopOpacity={0.45} />
                      <stop offset="95%" stopColor="#fb923c" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="label" stroke="#71717a" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#71717a" tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ background: "#09090b", border: "1px solid rgba(249,115,22,.35)", color: "#fff" }} formatter={(value: number) => `${value}min`} />
                  <Area type="monotone" dataKey="produtivo" stroke="#34d399" fill="url(#productiveTimeline)" strokeWidth={2} />
                  <Area type="monotone" dataKey="ocioso" stroke="#fb923c" fill="url(#idleTimeline)" strokeWidth={2} />
                  <Line type="monotone" dataKey="trocas" stroke="#facc15" strokeWidth={2} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="Sem linha temporal" description="A tendência aparece após os primeiros blocos de eventos por horário." />
          )}
        </Panel>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1fr_1fr]">
        <Panel title="Heatmap por hora e dia" icon={Activity}>
          <HourlyHeatmap data={analytics.heatmap} />
        </Panel>

        <Panel title="Troca de contexto" icon={Zap}>
          {analytics.contextTimeline.length ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={analytics.contextTimeline} margin={{ left: 4, right: 10, top: 12, bottom: 4 }}>
                  <CartesianGrid stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="label" stroke="#71717a" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#71717a" tick={{ fontSize: 11 }} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: "#09090b", border: "1px solid rgba(249,115,22,.35)", color: "#fff" }} />
                  <Bar dataKey="trocas" fill="#fb923c" radius={[5, 5, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="Sem trocas no recorte" description="As alternâncias entre sistemas aparecem aqui por bloco de horário." />
          )}
        </Panel>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <Panel title="Ranking de equipes" icon={Building2}>
          <HorizontalBarsChart data={analytics.teamRanking} valueLabel="min" />
        </Panel>

        <Panel title="Ranking de usuários" icon={UserRound}>
          <HorizontalBarsChart data={analytics.userRanking} valueLabel="min" />
        </Panel>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <Panel title="Status dos agentes por SO" icon={RadioTower}>
          <AgentOsChart data={agentStatusByOs} />
        </Panel>

        <Panel title="Qualidade de coleta por sistema" icon={ShieldCheck}>
          <QualityByOsChart data={qualityByOs} />
        </Panel>
      </div>

      <div className="mt-5">
        <Panel title="Tabela detalhada filtrável" icon={Layers3}>
          <AdvancedMetricsTable rows={detailedRows} loading={metricsLoading} />
        </Panel>
      </div>

      <div className="mt-5">
        <Panel title="Resumo analítico" icon={Brain}>
          <div className="grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
            <div className="border border-orange-400/20 bg-black/45 p-5">
              <p className="text-xs uppercase tracking-[0.2em] text-orange-300">Recorte atual</p>
              <p className="mt-3 text-2xl font-semibold text-zinc-50">{analytics.currentActivity}</p>
              <p className="mt-3 text-sm leading-6 text-zinc-400">{operationalIntelligence.aiSummary}</p>
            </div>
            <div className="grid gap-3">
              {[actionNow, ...operationalIntelligence.aiRecommendations.filter((item) => item !== actionNow).slice(0, 2)].map((recommendation, index) => (
                <motion.div
                  key={`${recommendation}-${index}`}
                  className="flex items-start gap-3 border border-zinc-800 bg-zinc-950/65 p-4 text-sm text-zinc-300"
                  initial={{ opacity: 0, x: 14 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.06 }}
                >
                  <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-orange-300" />
                  <span>{recommendation}</span>
                </motion.div>
              ))}
            </div>
          </div>
        </Panel>
      </div>
    </ViewFrame>
  );
}

function MetricFilterSelect({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: [string, string][] }) {
  return (
    <label className="grid gap-2 text-xs uppercase tracking-[0.14em] text-zinc-500">
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)} className="h-11 min-w-0 border border-zinc-800 bg-black/60 px-3 text-sm normal-case tracking-normal text-zinc-100 outline-none focus:border-orange-400">
        {options.map(([optionValue, optionLabel]) => (
          <option key={`${label}-${optionValue}`} value={optionValue}>{optionLabel}</option>
        ))}
      </select>
    </label>
  );
}

function PremiumDonutChart({ data, centerLabel, centerDetail }: { data: TimeDistributionSlice[]; centerLabel: string; centerDetail: string }) {
  if (!data.length) {
    return <EmptyState title="Sem distribuição" description="Não há tempo suficiente no recorte atual para montar o donut." />;
  }

  return (
    <div className="relative h-72 overflow-hidden rounded-lg border border-orange-400/10 bg-black/35">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart margin={{ top: 12, right: 12, bottom: 12, left: 12 }}>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius="62%"
            outerRadius="86%"
            paddingAngle={2}
            stroke="#09090b"
            strokeWidth={4}
            isAnimationActive
            animationDuration={850}
          >
            {data.map((entry) => (
              <Cell key={entry.key} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ background: "#09090b", border: "1px solid rgba(249,115,22,.35)", color: "#fafafa" }}
            itemStyle={{ color: "#fafafa" }}
            formatter={(value, name) => [`${value}min`, name]}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 grid place-items-center">
        <div className="text-center">
          <p className="text-4xl font-semibold text-zinc-50">{centerLabel}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.22em] text-orange-200">{centerDetail}</p>
        </div>
      </div>
    </div>
  );
}

function HorizontalBarsChart({ data, valueLabel }: { data: RankingChartItem[]; valueLabel: string }) {
  const chartData = data.slice(0, 8);
  const colors = ["#fb923c", "#f97316", "#facc15", "#34d399", "#38bdf8", "#a78bfa", "#f472b6", "#71717a"];

  if (!chartData.length) {
    return <EmptyState title="Sem ranking no recorte" description="Aplique outro filtro ou aguarde a sincronização dos eventos reais." />;
  }

  return (
    <div className="grid gap-4">
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 22, bottom: 8, left: 8 }}>
            <CartesianGrid horizontal={false} stroke="rgba(255,255,255,0.06)" />
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="name"
              width={118}
              axisLine={false}
              tickLine={false}
              stroke="#a1a1aa"
              tick={{ fontSize: 11 }}
            />
            <Tooltip
              cursor={{ fill: "rgba(249,115,22,0.06)" }}
              contentStyle={{ background: "#09090b", border: "1px solid rgba(249,115,22,.35)", color: "#fafafa" }}
              formatter={(value) => [`${value}${valueLabel}`, "Tempo"]}
            />
            <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={18}>
              {chartData.map((entry, index) => (
                <Cell key={`${entry.name}-${index}`} fill={colors[index % colors.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="grid gap-2">
        {chartData.slice(0, 3).map((item, index) => (
          <div key={`${item.name}-detail`} className="flex items-center justify-between gap-3 border border-zinc-800 bg-black/35 px-3 py-2 text-xs">
            <span className="truncate text-zinc-300">{index + 1}. {item.name}</span>
            <span className="shrink-0 text-orange-200">{item.detail ?? `${item.value}${valueLabel}`}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function HourlyHeatmap({ data }: { data: HourlyHeatmapPoint[] }) {
  if (!data.length) {
    return <EmptyState title="Sem mapa de horário" description="O heatmap aparece quando houver eventos com hora válida no recorte." />;
  }

  const hours = [...new Set(data.map((item) => item.hour))].sort((a, b) => a.localeCompare(b));
  const days = weekdayOrder.filter((day) => data.some((item) => item.day === day));
  const byKey = new Map(data.map((item) => [`${item.day}-${item.hour}`, item]));

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[560px]">
        <div className="grid gap-2" style={{ gridTemplateColumns: `72px repeat(${hours.length}, minmax(38px, 1fr))` }}>
          <div />
          {hours.map((hour) => (
            <div key={hour} className="text-center text-[10px] uppercase tracking-[0.12em] text-zinc-500">{hour}h</div>
          ))}
          {days.map((day) => (
            <div key={day} className="contents">
              <div className="flex h-10 items-center text-xs font-medium text-zinc-300">{day}</div>
              {hours.map((hour) => {
                const item = byKey.get(`${day}-${hour}`);
                const alpha = item ? 0.12 + (item.intensity / 100) * 0.58 : 0.04;
                return (
                  <div
                    key={`${day}-${hour}`}
                    className="grid h-10 place-items-center border border-zinc-900 text-[10px] text-zinc-100"
                    title={item ? `${day} ${hour}h: ${item.minutes}min, ${item.switches} trocas` : `${day} ${hour}h: sem dados`}
                    style={{ backgroundColor: item ? `rgba(249,115,22,${alpha})` : "rgba(39,39,42,0.32)", boxShadow: item && item.intensity > 70 ? "0 0 18px rgba(249,115,22,0.18)" : "none" }}
                  >
                    {item?.minutes ? item.minutes : ""}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        <div className="mt-4 flex items-center justify-between text-xs text-zinc-500">
          <span>menos atividade</span>
          <div className="flex gap-1">
            {[0.1, 0.22, 0.36, 0.52, 0.7].map((alpha) => (
              <span key={alpha} className="h-3 w-8 border border-zinc-900" style={{ backgroundColor: `rgba(249,115,22,${alpha})` }} />
            ))}
          </div>
          <span>mais atividade</span>
        </div>
      </div>
    </div>
  );
}

function AgentOsChart({ data }: { data: AgentOsGroup[] }) {
  if (!data.length) {
    return <EmptyState title="Sem agentes no recorte" description="Nenhum dispositivo respeita os filtros atuais." />;
  }

  return (
    <div className="grid gap-3">
      {data.map((row) => (
        <StackedOperationalRow
          key={row.os}
          label={row.os}
          total={row.total}
          segments={[
            { label: "online", value: row.online, color: "#34d399" },
            { label: "sync", value: row.syncing, color: "#facc15" },
            { label: "offline", value: row.offline, color: "#fb7185" },
            { label: "pendente", value: row.pending, color: "#71717a" }
          ]}
        />
      ))}
    </div>
  );
}

function QualityByOsChart({ data }: { data: QualityOsGroup[] }) {
  if (!data.length) {
    return <EmptyState title="Sem sinal de coleta" description="A qualidade aparece quando agentes ou eventos trouxerem metadados de coleta." />;
  }

  return (
    <div className="grid gap-3">
      {data.map((row) => (
        <StackedOperationalRow
          key={row.os}
          label={row.os}
          total={row.total}
          segments={[
            { label: "alta", value: row.high, color: "#34d399" },
            { label: "média", value: row.medium, color: "#facc15" },
            { label: "baixa", value: row.low, color: "#fb923c" },
            { label: "bloqueada", value: row.blocked, color: "#fb7185" }
          ]}
        />
      ))}
    </div>
  );
}

function StackedOperationalRow({
  label,
  total,
  segments
}: {
  label: string;
  total: number;
  segments: Array<{ label: string; value: number; color: string }>;
}) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-black/35 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p className="font-medium text-zinc-100">{label}</p>
          <p className="mt-1 text-xs text-zinc-500">{total} registro{total === 1 ? "" : "s"}</p>
        </div>
        <span className="text-sm font-semibold text-orange-200">{total}</span>
      </div>
      <div className="flex h-3 overflow-hidden bg-zinc-900">
        {segments.filter((segment) => segment.value > 0).map((segment) => (
          <motion.div
            key={segment.label}
            className="h-full"
            style={{ backgroundColor: segment.color }}
            initial={{ width: 0 }}
            animate={{ width: `${(segment.value / Math.max(total, 1)) * 100}%` }}
            transition={{ duration: 0.65, ease: "easeOut" }}
            title={`${segment.label}: ${segment.value}`}
          />
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-3 text-[11px] text-zinc-500">
        {segments.map((segment) => (
          <span key={segment.label} className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: segment.color }} />
            {segment.label}: {segment.value}
          </span>
        ))}
      </div>
    </div>
  );
}

function AdvancedMetricsTable({ rows, loading }: { rows: MetricsDetailedRow[]; loading: boolean }) {
  if (loading) {
    return (
      <div className="grid min-h-48 place-items-center border border-zinc-800 bg-black/35">
        <div className="flex items-center gap-3 text-sm text-orange-200">
          <motion.span
            className="h-2.5 w-2.5 rounded-full bg-orange-400"
            animate={{ opacity: [0.35, 1, 0.35], scale: [0.8, 1.15, 0.8] }}
            transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
          />
          Carregando recorte operacional...
        </div>
      </div>
    );
  }

  if (!rows.length) {
    return (
      <EmptyState
        title="Sem eventos para os filtros atuais"
        description="Altere período, pessoa, equipe ou dispositivo. A tabela só mostra eventos reais respeitando tenant e escopo de hierarquia."
      />
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-800 bg-zinc-950/60">
      <Tremor.Table>
        <Tremor.TableHead>
          <Tremor.TableRow>
            <Tremor.TableHeaderCell>Hora</Tremor.TableHeaderCell>
            <Tremor.TableHeaderCell>Pessoa</Tremor.TableHeaderCell>
            <Tremor.TableHeaderCell>Cargo</Tremor.TableHeaderCell>
            <Tremor.TableHeaderCell>Supervisor</Tremor.TableHeaderCell>
            <Tremor.TableHeaderCell>Equipe</Tremor.TableHeaderCell>
            <Tremor.TableHeaderCell>Dispositivo</Tremor.TableHeaderCell>
            <Tremor.TableHeaderCell>Status</Tremor.TableHeaderCell>
            <Tremor.TableHeaderCell>App</Tremor.TableHeaderCell>
            <Tremor.TableHeaderCell>Categoria</Tremor.TableHeaderCell>
            <Tremor.TableHeaderCell>Duração</Tremor.TableHeaderCell>
            <Tremor.TableHeaderCell>Coleta</Tremor.TableHeaderCell>
          </Tremor.TableRow>
        </Tremor.TableHead>
        <Tremor.TableBody>
          {rows.slice(0, 80).map((row) => (
            <Tremor.TableRow key={row.id} className="transition hover:bg-orange-950/10">
              <Tremor.TableCell className="whitespace-nowrap text-zinc-400">{formatEventDate(row.occurredAt)}</Tremor.TableCell>
              <Tremor.TableCell className="font-medium text-zinc-100">{row.userName}</Tremor.TableCell>
              <Tremor.TableCell>{row.userTitle ?? "sem cargo"}</Tremor.TableCell>
              <Tremor.TableCell>{row.supervisorName ?? "sem supervisor"}</Tremor.TableCell>
              <Tremor.TableCell>{row.teamName ?? "sem equipe"}</Tremor.TableCell>
              <Tremor.TableCell>{row.device}</Tremor.TableCell>
              <Tremor.TableCell>
                <Tremor.Badge color={["online", "syncing"].includes(row.agentStatus ?? "") ? "emerald" : row.agentStatus === "offline" ? "rose" : "orange"} size="xs">
                  {statusPt(row.agentStatus ?? "pendente")}
                </Tremor.Badge>
              </Tremor.TableCell>
              <Tremor.TableCell className="text-orange-100">{row.app}</Tremor.TableCell>
              <Tremor.TableCell>
                <Tremor.Badge color="zinc" size="xs">{categoryPt(row.category)}</Tremor.Badge>
              </Tremor.TableCell>
              <Tremor.TableCell className="whitespace-nowrap text-zinc-100">{formatDuration(row.durationSeconds)}</Tremor.TableCell>
              <Tremor.TableCell>
                <Tremor.Badge color={row.collectionQuality === "high" ? "emerald" : row.collectionQuality === "blocked_by_os" ? "rose" : "orange"} size="xs">
                  {qualityPt(row.collectionQuality)}
                </Tremor.Badge>
              </Tremor.TableCell>
            </Tremor.TableRow>
          ))}
        </Tremor.TableBody>
      </Tremor.Table>
      {rows.length > 80 ? (
        <p className="border-t border-zinc-800 bg-black/45 px-4 py-3 text-xs text-zinc-500">
          Mostrando 80 de {rows.length} registros. Use CSV/Excel para baixar o recorte completo.
        </p>
      ) : null}
    </div>
  );
}

function MetricSpeedometer({
  label,
  value,
  detail,
  tone
}: {
  label: string;
  value: number;
  detail: string;
  tone: "ok" | "warn" | "critical";
}) {
  const percentage = Math.max(0, Math.min(100, Math.round(value)));
  const color = tone === "ok" ? "emerald" : tone === "critical" ? "rose" : "orange";

  return (
    <motion.div
      className="relative"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -5 }}
    >
      <Tremor.Card className="h-full rounded-lg border border-zinc-800 bg-zinc-950/78 p-4 shadow-tremor-card">
        <div className="grid place-items-center">
          <Tremor.ProgressCircle value={percentage} color={color} size="lg">
            <div className="text-center">
              <p className="text-2xl font-semibold text-zinc-50">{percentage}</p>
              <p className="text-[10px] uppercase tracking-[0.18em] text-orange-200">/100</p>
            </div>
          </Tremor.ProgressCircle>
        </div>
        <p className="mt-4 text-sm font-semibold text-zinc-100">{label}</p>
        <p className="mt-1 text-xs leading-5 text-zinc-500">{detail}</p>
      </Tremor.Card>
    </motion.div>
  );
}

function MetricLegend({ color, label, value, detail }: { color: string; label: string; value: string; detail: string }) {
  return (
    <Tremor.Card className="flex items-center justify-between gap-3 rounded-lg border border-zinc-800 bg-zinc-950/65 p-3">
      <div className="flex items-center gap-3">
        <span className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
        <div>
          <p className="text-sm font-medium text-zinc-100">{label}</p>
          <p className="text-xs text-zinc-500">{detail}</p>
        </div>
      </div>
      <p className="text-lg font-semibold text-zinc-50">{value}</p>
    </Tremor.Card>
  );
}

function MetricSignalCard({
  icon: Icon,
  label,
  value,
  detail,
  tone
}: {
  icon: typeof Gauge;
  label: string;
  value: string;
  detail: string;
  tone: "ok" | "warn" | "critical";
}) {
  const colorClass = tone === "ok" ? "text-emerald-300" : tone === "critical" ? "text-rose-300" : "text-orange-300";

  return (
    <motion.div
      className="relative overflow-hidden border border-orange-400/18 bg-zinc-950/78 p-5 shadow-[0_0_30px_rgba(249,115,22,0.06)]"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -5, borderColor: "rgba(251,146,60,.50)" }}
    >
      <motion.div
        className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-300 to-transparent"
        animate={{ x: ["-100%", "100%"], opacity: [0, 0.9, 0] }}
        transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
      />
      <div className="relative z-10 flex items-start gap-4">
        <div className="grid h-11 w-11 shrink-0 place-items-center bg-orange-500 text-black">
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-[0.22em] text-zinc-500">{label}</p>
          <p className={`mt-3 text-2xl font-semibold leading-tight ${colorClass}`}>{value}</p>
          <p className="mt-3 text-sm leading-6 text-zinc-500">{detail}</p>
        </div>
      </div>
    </motion.div>
  );
}

function InsightsView({
  insights,
  token,
  teams = [],
  hierarchy = [],
  devices = [],
  whatsAppStatus,
  emailStatuses = [],
  liveStatusLabel = "agora",
  compact = false,
  onOpenMetrics
}: {
  insights: Insight[];
  token?: string;
  teams?: Team[];
  hierarchy?: HierarchyNode[];
  devices?: Device[];
  whatsAppStatus?: WhatsAppStatus;
  emailStatuses?: EmailProviderStatus[];
  liveStatusLabel?: string;
  compact?: boolean;
  onOpenMetrics?: (filters: Omit<MetricsIntent, "nonce">) => void;
}) {
  const [items, setItems] = useState<Insight[]>(insights);
  const [period, setPeriod] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [teamFilter, setTeamFilter] = useState("all");
  const [userFilter, setUserFilter] = useState("all");
  const [deliveryFilter, setDeliveryFilter] = useState("all");
  const [selectedInsightId, setSelectedInsightId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [aiAnswer, setAiAnswer] = useState<InsightAskResponse | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "ok" | "warn"; message: string } | null>(null);

  useEffect(() => {
    setItems(insights);
  }, [insights]);

  const selectedInsight = items.find((item) => item.id === selectedInsightId) ?? items[0] ?? null;
  const emailReady = emailStatuses.some((item) => item.configured && item.canSend);
  const whatsReady = Boolean(whatsAppStatus?.connected);
  const insightTypes = [...new Set(items.map((item) => item.insightType ?? "recomendacao_processo"))].sort();
  const severities = [...new Set(items.map((item) => item.severity ?? item.impact ?? "medium"))].sort();
  const statuses = [...new Set(items.map((item) => item.status ?? "open"))].sort();
  const visibleUsers = hierarchy.map((node) => [node.id, node.name] as [string, string]);
  const visibleTeams = teams.map((team) => [team.id, team.name] as [string, string]);
  const filteredInsights = items.filter((item) => {
    if (typeFilter !== "all" && (item.insightType ?? "recomendacao_processo") !== typeFilter) return false;
    if (severityFilter !== "all" && (item.severity ?? item.impact) !== severityFilter) return false;
    if (statusFilter !== "all" && (item.status ?? "open") !== statusFilter) return false;
    if (teamFilter !== "all" && item.targetTeamId !== teamFilter && !item.affectedTeams?.includes(teams.find((team) => team.id === teamFilter)?.name ?? "")) return false;
    if (userFilter !== "all" && item.targetUserId !== userFilter && item.membershipId !== userFilter) return false;
    if (deliveryFilter === "whatsapp" && !item.sentToWhatsapp) return false;
    if (deliveryFilter === "email" && !item.sentToEmail) return false;
    if (deliveryFilter === "not_sent" && (item.sentToWhatsapp || item.sentToEmail)) return false;
    if (period !== "all" && item.createdAt) {
      const days = period === "24h" ? 1 : period === "7d" ? 7 : 30;
      if (Date.now() - new Date(item.createdAt).getTime() > days * 86400000) return false;
    }
    return true;
  });
  const criticalCount = items.filter((item) => ["critical", "high"].includes(item.severity ?? item.impact)).length;
  const automationCount = items.filter((item) => (item.insightType ?? "").includes("autom") || item.automationSavingsHours > 0).length;
  const totalSavings = items.reduce((total, item) => total + (item.estimatedSavings ?? item.automationSavingsHours * 95), 0);
  const sentWhats = items.filter((item) => item.sentToWhatsapp).length;
  const sentEmail = items.filter((item) => item.sentToEmail).length;
  const resolved = items.filter((item) => (item.status ?? "open") === "resolved").length;
  const severityChart = severities.map((severity) => ({
    name: severityPt(severity),
    value: items.filter((item) => (item.severity ?? item.impact) === severity).length
  }));
  const typeChart = insightTypes.slice(0, 6).map((type) => ({
    name: insightTypePt(type),
    value: items.filter((item) => (item.insightType ?? "recomendacao_processo") === type).length
  }));

  async function runInsightAction(action: string, endpoint: string, options?: RequestInit) {
    if (!token) {
      setFeedback({ tone: "warn", message: "Sessão expirada. Faça login novamente." });
      return null;
    }
    try {
      setBusyAction(action);
      setFeedback(null);
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "X-Tenant-Id": DEMO_TENANT_ID
        },
        ...options
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(String(body.detail ?? "Ação recusada pelo backend."));
      }
      return response;
    } catch (error) {
      setFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Não foi possível executar a ação." });
      return null;
    } finally {
      setBusyAction(null);
    }
  }

  async function refreshInsights() {
    if (!token) return;
    const next = await fetchProtected<Insight[]>("/insights", token, items);
    setItems(next);
    setFeedback({ tone: "ok", message: "Insights atualizados com o escopo permitido." });
  }

  async function generateInsight() {
    const response = await runInsightAction("generate", "/insights/generate", {
      body: JSON.stringify({ tenantId: DEMO_TENANT_ID, period: period === "all" ? "24h" : period })
    });
    if (!response) return;
    const insight = (await response.json()) as Insight;
    setItems((current) => [insight, ...current.filter((item) => item.id !== insight.id)]);
    setSelectedInsightId(insight.id);
    setFeedback({ tone: "ok", message: "Insight gerado por regras determinísticas. GPT/Llama entram quando as chaves estiverem configuradas." });
  }

  async function askSelectedInsight(customQuestion?: string) {
    if (!selectedInsight) return;
    const currentQuestion = (customQuestion ?? question).trim();
    if (!currentQuestion) {
      setFeedback({ tone: "warn", message: "Digite uma pergunta para aprofundar o diagnóstico." });
      return;
    }
    const response = await runInsightAction("ask", `/insights/${selectedInsight.id}/ask`, {
      body: JSON.stringify({ question: currentQuestion })
    });
    if (!response) return;
    setAiAnswer((await response.json()) as InsightAskResponse);
  }

  async function mutateInsight(action: "send-whatsapp" | "send-email" | "resolve" | "create-action") {
    if (!selectedInsight) return;
    const body = action === "create-action"
      ? { title: selectedInsight.recommendation, priority: selectedInsight.severity === "critical" ? "crítica" : "alta", note: selectedInsight.summary }
      : undefined;
    const response = await runInsightAction(action, `/insights/${selectedInsight.id}/${action}`, body ? { body: JSON.stringify(body) } : undefined);
    if (!response) return;
    const updated = (await response.json()) as Insight;
    setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    setSelectedInsightId(updated.id);
    const actionLabel = action === "send-whatsapp" ? "WhatsApp" : action === "send-email" ? "e-mail" : action === "resolve" ? "resolução" : "plano de ação";
    setFeedback({ tone: "ok", message: `${actionLabel} registrado. Status: ${updated.whatsappStatus || updated.emailStatus || updated.status || updated.actionStatus || "ok"}.` });
  }

  function openMetricsForInsight(item: Insight) {
    onOpenMetrics?.({
      period: "7d",
      teamId: item.targetTeamId ?? undefined,
      membershipId: item.targetUserId ?? item.membershipId ?? undefined,
      department: item.targetDepartmentId ? undefined : item.affectedTeams?.[0],
      metricType: (item.insightType ?? "").includes("context") ? "context_switch" : (item.insightType ?? "").includes("ocios") ? "idle" : undefined
    });
  }

  if (compact) {
    return (
      <ViewFrame compact>
        <Panel title="Fluxo de insights de IA" icon={Sparkles}>
          <div className="grid gap-4">
            {items.length ? (
              items.slice(0, 4).map((insight, index) => (
                <motion.article
                  key={insight.id}
                  className="border border-orange-400/15 bg-black/45 p-5 transition hover:border-orange-300/50"
                  initial={{ y: 24, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: index * 0.08 }}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <h3 className="text-lg font-semibold">{insight.title}</h3>
                    <span className="border border-orange-400/25 px-3 py-1 text-xs uppercase tracking-[0.18em] text-orange-300">{severityPt(insight.severity ?? insight.impact)}</span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-zinc-400">{insight.summary}</p>
                  <p className="mt-4 text-sm leading-6 text-zinc-200">{insight.recommendation}</p>
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

  return (
    <ViewFrame>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <LiveBadge label="Insights inteligentes" detail={`Tempo real ativo | última atualização ${liveStatusLabel}`} />
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => void generateInsight()} disabled={busyAction === "generate"} className="h-10 bg-orange-500 px-4 text-sm font-semibold text-black transition hover:bg-orange-400 disabled:opacity-50">
            {busyAction === "generate" ? "Gerando..." : "Gerar novo insight"}
          </button>
          <button type="button" onClick={() => void refreshInsights()} className="h-10 border border-zinc-800 bg-black/45 px-4 text-sm text-zinc-200 transition hover:border-orange-400/45">
            Atualizar
          </button>
        </div>
      </div>

      <div className="mb-5 grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
        <Tremor.Card className="rounded-lg border border-zinc-800 bg-zinc-950/82 p-5 shadow-tremor-card">
          <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
            <div>
              <Tremor.Text className="text-xs uppercase tracking-[0.2em] text-orange-200">Cérebro operacional</Tremor.Text>
              <Tremor.Title className="mt-2 text-zinc-50">Diagnósticos que explicam o que aconteceu, por que importa e o que fazer agora.</Tremor.Title>
            </div>
            <div className="flex flex-wrap gap-2">
              <Tremor.Badge color={whatsReady ? "emerald" : "orange"}>WhatsApp {whatsReady ? "pronto" : "pendente"}</Tremor.Badge>
              <Tremor.Badge color={emailReady ? "emerald" : "orange"}>E-mail {emailReady ? "pronto" : "pendente"}</Tremor.Badge>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            <MetricSignalCard icon={Flame} label="Críticos" value={`${criticalCount}`} detail="Prioridades com risco operacional ou financeiro." tone={criticalCount ? "critical" : "ok"} />
            <MetricSignalCard icon={Zap} label="Automações" value={`${automationCount}`} detail="Processos com indício de repetição automatizável." tone={automationCount ? "warn" : "ok"} />
            <MetricSignalCard icon={Brain} label="Economia potencial" value={formatMoneyBRL(totalSavings)} detail="Estimativa a partir dos insights visíveis." tone={totalSavings > 0 ? "ok" : "warn"} />
          </div>
        </Tremor.Card>

        <div className="grid gap-5 md:grid-cols-2">
          <Tremor.Card className="rounded-lg border border-zinc-800 bg-zinc-950/82 p-5 shadow-tremor-card">
            <Tremor.Title className="mb-4 text-zinc-50">Severidade</Tremor.Title>
            {severityChart.length ? <Tremor.BarList data={severityChart} color="orange" valueFormatter={(value: number) => `${value}`} /> : <EmptyState title="Sem dados" description="Gere o primeiro insight para montar o painel." />}
          </Tremor.Card>
          <Tremor.Card className="rounded-lg border border-zinc-800 bg-zinc-950/82 p-5 shadow-tremor-card">
            <Tremor.Title className="mb-4 text-zinc-50">Envios e resolução</Tremor.Title>
            <div className="grid gap-3">
              <ConnectionSummary label="WhatsApp" value={`${sentWhats}/${items.length}`} tone={sentWhats ? "ok" : "warn"} />
              <ConnectionSummary label="E-mail" value={`${sentEmail}/${items.length}`} tone={sentEmail ? "ok" : "warn"} />
              <ConnectionSummary label="Resolvidos" value={`${resolved}/${items.length}`} tone={resolved ? "ok" : "warn"} />
            </div>
          </Tremor.Card>
        </div>
      </div>

      <Panel title="Filtros de diagnóstico" icon={Layers3}>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-8">
          <MetricFilterSelect label="Período" value={period} onChange={setPeriod} options={[["all", "Todos"], ["24h", "24h"], ["7d", "7 dias"], ["30d", "30 dias"]]} />
          <MetricFilterSelect label="Tipo" value={typeFilter} onChange={setTypeFilter} options={[["all", "Todos"], ...insightTypes.map((item) => [item, insightTypePt(item)] as [string, string])]} />
          <MetricFilterSelect label="Severidade" value={severityFilter} onChange={setSeverityFilter} options={[["all", "Todas"], ...severities.map((item) => [item, severityPt(item)] as [string, string])]} />
          <MetricFilterSelect label="Status" value={statusFilter} onChange={setStatusFilter} options={[["all", "Todos"], ...statuses.map((item) => [item, insightStatusPt(item)] as [string, string])]} />
          <MetricFilterSelect label="Equipe" value={teamFilter} onChange={setTeamFilter} options={[["all", "Todas"], ...visibleTeams]} />
          <MetricFilterSelect label="Usuário" value={userFilter} onChange={setUserFilter} options={[["all", "Todos"], ...visibleUsers]} />
          <MetricFilterSelect label="Envio" value={deliveryFilter} onChange={setDeliveryFilter} options={[["all", "Todos"], ["whatsapp", "WhatsApp enviado"], ["email", "E-mail enviado"], ["not_sent", "Não enviados"]]} />
          <MetricFilterSelect label="Origem" value="all" onChange={() => undefined} options={[["all", "IA + regras"]]} />
        </div>
      </Panel>

      {feedback ? <div className="mt-4"><FeedbackBanner tone={feedback.tone} message={feedback.message} /></div> : null}

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="grid gap-4">
          {filteredInsights.length ? (
            filteredInsights.map((insight, index) => (
              <InsightDiagnosticCard
                key={insight.id}
                insight={insight}
                index={index}
                selected={selectedInsight?.id === insight.id}
                onSelect={() => {
                  setSelectedInsightId(insight.id);
                  setAiAnswer(null);
                  setQuestion("");
                }}
                onOpenMetrics={() => openMetricsForInsight(insight)}
              />
            ))
          ) : (
            <EmptyState title="Nenhum insight no filtro" description="Altere período, severidade, tipo ou gere um novo insight com base nos dados atuais." />
          )}
        </div>

        <Panel title="Detalhe, IA e ação" icon={Brain}>
          {selectedInsight ? (
            <div className="grid gap-5">
              <div className="border border-orange-400/20 bg-black/45 p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-orange-300">{insightTypePt(selectedInsight.insightType ?? "recomendacao_processo")}</p>
                    <h3 className="mt-2 text-2xl font-semibold text-zinc-50">{selectedInsight.title}</h3>
                  </div>
                  <span className="border border-orange-400/25 px-3 py-1 text-xs uppercase tracking-[0.18em] text-orange-200">{severityPt(selectedInsight.severity ?? selectedInsight.impact)}</span>
                </div>
                <p className="mt-4 text-sm leading-6 text-zinc-300">{selectedInsight.diagnosis || selectedInsight.summary}</p>
                <p className="mt-4 border-l border-orange-400/40 pl-3 text-sm leading-6 text-zinc-100">{selectedInsight.recommendation}</p>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <ConnectionSummary label="Confiança" value={`${Math.round((selectedInsight.confidence ?? 0.72) * 100)}%`} tone="ok" />
                <ConnectionSummary label="Tempo perdido" value={`${selectedInsight.estimatedTimeLoss ?? selectedInsight.automationSavingsHours}h`} tone={(selectedInsight.estimatedTimeLoss ?? 0) > 0 ? "warn" : "ok"} />
                <ConnectionSummary label="Economia" value={formatMoneyBRL(selectedInsight.estimatedSavings ?? selectedInsight.automationSavingsHours * 95)} tone="ok" />
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div className="border border-zinc-800 bg-black/35 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">Evidências</p>
                  <div className="mt-3 grid gap-2">
                    {(selectedInsight.evidence?.length ? selectedInsight.evidence : [selectedInsight.summary]).map((item) => (
                      <p key={item} className="text-sm leading-6 text-zinc-300">• {item}</p>
                    ))}
                  </div>
                </div>
                <div className="border border-zinc-800 bg-black/35 p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">Escopo e envio</p>
                  <div className="mt-3 grid gap-2">
                    <ConnectionSummary label="Escopo" value={scopeTypePt(selectedInsight.scopeType ?? "tenant")} tone="ok" />
                    <ConnectionSummary label="WhatsApp" value={deliveryStatusPt(selectedInsight.whatsappStatus ?? "not_sent")} tone={selectedInsight.sentToWhatsapp ? "ok" : "warn"} />
                    <ConnectionSummary label="E-mail" value={deliveryStatusPt(selectedInsight.emailStatus ?? "not_sent")} tone={selectedInsight.sentToEmail ? "ok" : "warn"} />
                  </div>
                </div>
              </div>

              <div className="grid gap-2">
                <p className="text-xs uppercase tracking-[0.18em] text-orange-300">Perguntas sugeridas</p>
                <div className="flex flex-wrap gap-2">
                  {(selectedInsight.suggestedQuestions?.length ? selectedInsight.suggestedQuestions : ["Por que isso aconteceu?", "O que eu faço primeiro?", "Dá para automatizar?"]).map((item) => (
                    <button key={item} type="button" onClick={() => void askSelectedInsight(item)} className="border border-zinc-800 bg-black/45 px-3 py-2 text-xs text-zinc-200 transition hover:border-orange-400/45">
                      {item}
                    </button>
                  ))}
                </div>
              </div>

              <div className="border border-zinc-800 bg-zinc-950/65 p-4">
                <label className="grid gap-2 text-sm text-zinc-300">
                  Aprofundar com IA
                  <textarea
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="Ex.: quanto isso pode custar por mês?"
                    className="min-h-24 border border-zinc-800 bg-black/55 p-3 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-700 focus:border-orange-400"
                  />
                </label>
                <button type="button" onClick={() => void askSelectedInsight()} disabled={busyAction === "ask"} className="mt-3 h-10 bg-orange-500 px-4 text-sm font-semibold text-black transition hover:bg-orange-400 disabled:opacity-50">
                  {busyAction === "ask" ? "Analisando..." : "Aprofundar com IA"}
                </button>
                {aiAnswer ? (
                  <motion.div className="mt-4 border border-orange-400/20 bg-black/45 p-4" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
                    <p className="text-xs uppercase tracking-[0.18em] text-orange-300">{aiAnswer.aiMode}</p>
                    <p className="mt-3 text-sm leading-6 text-zinc-200">{aiAnswer.answer}</p>
                  </motion.div>
                ) : null}
              </div>

              <div className="grid gap-2 md:grid-cols-2">
                <button type="button" onClick={() => openMetricsForInsight(selectedInsight)} className="h-11 border border-zinc-800 bg-black/45 px-3 text-sm text-zinc-200 transition hover:border-orange-400/45">Abrir Métricas relacionadas</button>
                <button type="button" onClick={() => void mutateInsight("create-action")} disabled={busyAction === "create-action"} className="h-11 border border-zinc-800 bg-black/45 px-3 text-sm text-zinc-200 transition hover:border-orange-400/45">Criar plano de ação</button>
                <button type="button" onClick={() => void mutateInsight("send-whatsapp")} disabled={busyAction === "send-whatsapp"} className="h-11 border border-orange-400/25 px-3 text-sm text-orange-200 transition hover:border-orange-300/60">Enviar por WhatsApp</button>
                <button type="button" onClick={() => void mutateInsight("send-email")} disabled={busyAction === "send-email"} className="h-11 border border-orange-400/25 px-3 text-sm text-orange-200 transition hover:border-orange-300/60">Enviar por e-mail</button>
                <button type="button" onClick={() => navigator.clipboard?.writeText(`${selectedInsight.title}\n${selectedInsight.summary}\nAção: ${selectedInsight.recommendation}`)} className="h-11 border border-zinc-800 bg-black/45 px-3 text-sm text-zinc-200 transition hover:border-orange-400/45">Copiar resumo</button>
                <button type="button" onClick={() => void mutateInsight("resolve")} disabled={busyAction === "resolve"} className="h-11 border border-emerald-400/25 px-3 text-sm text-emerald-200 transition hover:border-emerald-300/60">Marcar resolvido</button>
              </div>
            </div>
          ) : (
            <EmptyState title="Selecione um insight" description="O diagnóstico completo, evidências, IA e ações aparecem aqui." />
          )}
        </Panel>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <Panel title="Insights por tipo" icon={Activity}>
          {typeChart.length ? <HorizontalBarsChart data={typeChart.map((item) => ({ ...item, detail: `${item.value} diagnóstico(s)` }))} valueLabel="" /> : <EmptyState title="Sem distribuição" description="Gere insights para visualizar tipos." />}
        </Panel>
        <Panel title="Privacidade e hierarquia" icon={ShieldCheck}>
          <div className="grid gap-3">
            <p className="text-sm leading-6 text-zinc-300">A tela usa apenas insights retornados pelo backend para o escopo autenticado. Operadores recebem visão pessoal; gestores recebem a árvore permitida; diretoria/admin recebe visão agregada do tenant.</p>
            <div className="grid gap-3 md:grid-cols-3">
              <ConnectionSummary label="Pessoas no escopo" value={`${hierarchy.length}`} tone={hierarchy.length ? "ok" : "warn"} />
              <ConnectionSummary label="Equipes" value={`${teams.length}`} tone={teams.length ? "ok" : "warn"} />
              <ConnectionSummary label="Dispositivos" value={`${devices.length}`} tone={devices.length ? "ok" : "warn"} />
            </div>
          </div>
        </Panel>
      </div>
    </ViewFrame>
  );
}

function InsightDiagnosticCard({
  insight,
  index,
  selected,
  onSelect,
  onOpenMetrics
}: {
  insight: Insight;
  index: number;
  selected: boolean;
  onSelect: () => void;
  onOpenMetrics: () => void;
}) {
  const tone = ["critical", "high"].includes(insight.severity ?? insight.impact) ? "critical" : insight.impact === "medium" ? "warn" : "ok";
  const Icon = insightIcon(insight.insightType ?? "");
  return (
    <motion.article
      className={`relative overflow-hidden border p-5 transition ${selected ? "border-orange-300/70 bg-orange-950/10 shadow-[0_0_34px_rgba(249,115,22,0.12)]" : "border-zinc-800 bg-zinc-950/70 hover:border-orange-400/45"}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      whileHover={{ y: -4 }}
    >
      <motion.div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-300 to-transparent" animate={{ x: ["-100%", "100%"], opacity: [0, 0.75, 0] }} transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }} />
      <button type="button" onClick={onSelect} className="relative z-10 block w-full text-left">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="grid h-11 w-11 shrink-0 place-items-center bg-orange-500 text-black"><Icon className="h-5 w-5" /></div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-orange-300">{insightTypePt(insight.insightType ?? "recomendacao_processo")}</p>
              <h3 className="mt-1 text-xl font-semibold text-zinc-50">{insight.title}</h3>
            </div>
          </div>
          <span className={`border px-3 py-1 text-xs uppercase tracking-[0.16em] ${tone === "critical" ? "border-rose-400/30 text-rose-200" : tone === "warn" ? "border-orange-400/30 text-orange-200" : "border-emerald-400/30 text-emerald-200"}`}>{severityPt(insight.severity ?? insight.impact)}</span>
        </div>
        <p className="mt-4 text-sm leading-6 text-zinc-400">{insight.summary}</p>
        <p className="mt-3 text-sm leading-6 text-zinc-200">{insight.recommendation}</p>
      </button>
      <div className="relative z-10 mt-4 grid gap-2 md:grid-cols-4">
        <ConnectionSummary label="Economia" value={formatMoneyBRL(insight.estimatedSavings ?? insight.automationSavingsHours * 95)} tone="ok" />
        <ConnectionSummary label="Confiança" value={`${Math.round((insight.confidence ?? 0.72) * 100)}%`} tone="ok" />
        <ConnectionSummary label="WhatsApp" value={deliveryStatusPt(insight.whatsappStatus ?? "not_sent")} tone={insight.sentToWhatsapp ? "ok" : "warn"} />
        <ConnectionSummary label="Status" value={insightStatusPt(insight.status ?? "open")} tone={(insight.status ?? "open") === "resolved" ? "ok" : "warn"} />
      </div>
      <div className="relative z-10 mt-4 flex flex-wrap gap-2">
        <button type="button" onClick={onSelect} className="h-9 bg-orange-500 px-3 text-xs font-semibold text-black transition hover:bg-orange-400">Ver diagnóstico</button>
        <button type="button" onClick={onOpenMetrics} className="h-9 border border-zinc-800 px-3 text-xs text-zinc-200 transition hover:border-orange-400/45">Métricas</button>
      </div>
    </motion.article>
  );
}

function insightTypePt(type: string) {
  const normalized = type.toLowerCase();
  const map: Record<string, string> = {
    produtividade: "Produtividade",
    ociosidade: "Ociosidade",
    foco: "Foco",
    troca_contexto: "Troca de contexto",
    context_switch: "Troca de contexto",
    bottleneck: "Gargalo operacional",
    gargalo_operacional: "Gargalo operacional",
    automation: "Automação sugerida",
    automacao_sugerida: "Automação sugerida",
    risco_operacional: "Risco operacional",
    agent: "Agente",
    agente_offline: "Agente offline",
    coleta_limitada: "Coleta limitada",
    equipe_sobrecarregada: "Equipe sobrecarregada",
    desvio_padrao: "Desvio de padrão",
    eficiencia_equipe: "Eficiência por equipe",
    economia_estimada: "Economia estimada",
    tendencia_negativa: "Tendência negativa",
    tendencia_positiva: "Tendência positiva",
    relatorio_executivo: "Relatório executivo",
    alerta_critico: "Alerta crítico",
    treinamento: "Treinamento",
    recomendacao_processo: "Recomendação de processo",
    recomendacao_integracao: "Recomendação de integração"
  };
  return map[normalized] ?? normalized.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function severityPt(value: string) {
  const map: Record<string, string> = {
    critical: "Crítica",
    high: "Alta",
    medium: "Média",
    low: "Baixa",
    warn: "Atenção"
  };
  return map[value] ?? value;
}

function insightStatusPt(value: string) {
  const map: Record<string, string> = {
    open: "Aberto",
    resolved: "Resolvido",
    ignored: "Ignorado",
    in_progress: "Em andamento",
    reviewing: "Em análise"
  };
  return map[value] ?? value;
}

function deliveryStatusPt(value: string) {
  const map: Record<string, string> = {
    not_sent: "Não enviado",
    ready: "Pronto",
    sent: "Enviado",
    queued: "Na fila",
    mocked: "Simulado",
    missing_credentials: "Credencial pendente",
    failed: "Falhou",
    disabled: "Desativado",
    missing_destination: "Sem destino"
  };
  return map[value] ?? value;
}

function scopeTypePt(value: string) {
  const map: Record<string, string> = {
    self: "Individual",
    user: "Usuário",
    team: "Equipe",
    department: "Departamento",
    subtree: "Subárvore",
    tenant: "Empresa",
    global: "Global"
  };
  return map[value] ?? value;
}

function insightIcon(type: string): typeof Gauge {
  const normalized = type.toLowerCase();
  if (normalized.includes("autom")) return Zap;
  if (normalized.includes("agent") || normalized.includes("agente") || normalized.includes("coleta")) return RadioTower;
  if (normalized.includes("risco") || normalized.includes("alerta")) return ShieldCheck;
  if (normalized.includes("econom")) return Flame;
  if (normalized.includes("equipe") || normalized.includes("supervisor")) return Network;
  if (normalized.includes("foco") || normalized.includes("produt")) return Gauge;
  return Brain;
}

function NotificationsView({
  notifications,
  summary,
  notificationTypes,
  notificationTemplates,
  whatsAppStatus,
  emailStatuses,
  liveStatusLabel = "agora",
  schedules = [],
  compact = false,
  token,
  userRole = "user"
}: {
  notifications: NotificationItem[];
  summary: NotificationSummary;
  notificationTypes: NotificationTypeDefinition[];
  notificationTemplates: NotificationTemplate[];
  whatsAppStatus: WhatsAppStatus;
  emailStatuses: EmailProviderStatus[];
  liveStatusLabel?: string;
  schedules?: NotificationSchedule[];
  compact?: boolean;
  token?: string;
  userRole?: string;
}) {
  const [items, setItems] = useState(notifications);
  const [types, setTypes] = useState(notificationTypes);
  const [channelFilter, setChannelFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [selectedTemplateId, setSelectedTemplateId] = useState(notificationTemplates[0]?.id ?? "");
  const [templatePreview, setTemplatePreview] = useState<{ title: string; body: string } | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "ok" | "warn"; message: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [rootQueue, setRootQueue] = useState<RootWhatsAppQueueItem[]>([]);
  const [rootLogs, setRootLogs] = useState<RootWhatsAppLog[]>([]);
  const iconByChannel = { system: BellRing, push: BellRing, windows: Monitor, whatsapp: MessageCircle, email: Mail };
  const emailReady = emailStatuses.some((item) => item.configured && item.canSend);
  const isSystemOwner = userRole === "owner" || userRole === "root";

  useEffect(() => setItems(notifications), [notifications]);
  useEffect(() => setTypes(notificationTypes), [notificationTypes]);
  useEffect(() => {
    if (isSystemOwner) {
      void refreshRootWhatsappQueue();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, isSystemOwner]);

  const filtered = items.filter((item) => {
    if (channelFilter !== "all" && item.channel !== channelFilter) return false;
    if (statusFilter !== "all" && item.status !== statusFilter) return false;
    if (priorityFilter !== "all" && (item.priority ?? "medio") !== priorityFilter) return false;
    return true;
  });
  const channels = ["system", "whatsapp", "email", "windows", "push"];
  const statuses = [...new Set(items.map((item) => item.status))];
  const priorities = ["informativo", "baixo", "medio", "alto", "critico"];
  const selectedTemplate = notificationTemplates.find((item) => item.id === selectedTemplateId) ?? notificationTemplates[0];
  const rootQueueIssues = rootQueue.filter((item) => ["failed", "provider_unavailable", "qr_required", "rate_limited", "retrying"].includes(item.status));

  async function rootRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
    if (!token) throw new Error("Sessão ausente.");
    const response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Tenant-Id": DEMO_TENANT_ID,
        ...(init.body ? { "Content-Type": "application/json" } : {})
      }
    });
    const payload = (await response.json().catch(() => ({}))) as T & { detail?: string };
    if (!response.ok) throw new Error(String(payload.detail ?? "Requisição recusada pelo backend."));
    return payload;
  }

  async function refreshRootWhatsappQueue() {
    if (!token || !isSystemOwner) return;
    try {
      const [queuePayload, logsPayload] = await Promise.all([
        rootRequest<RootWhatsAppQueueItem[]>("/integrations/whatsapp/root/queue?limit=8"),
        rootRequest<RootWhatsAppLog[]>("/integrations/whatsapp/root/logs?limit=5")
      ]);
      setRootQueue(queuePayload);
      setRootLogs(logsPayload);
    } catch {
      setRootQueue([]);
      setRootLogs([]);
    }
  }

  async function processRootWhatsappQueue() {
    if (!isSystemOwner) return;
    setBusy("root-process-queue");
    try {
      const payload = await rootRequest<{ queued: number; sent: number; failed: number; mode: string }>("/integrations/whatsapp/root/process-queue?limit=25", { method: "POST" });
      setFeedback({ tone: payload.failed ? "warn" : "ok", message: `WhatsApp raiz: ${payload.sent} enviada(s), ${payload.failed} falha(s), ${payload.queued} pendente(s). Modo: ${statusPt(payload.mode)}.` });
      await refreshRootWhatsappQueue();
    } catch (error) {
      setFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Falha ao processar fila WhatsApp." });
    } finally {
      setBusy(null);
    }
  }

  async function retryRootWhatsappItem(id: string) {
    if (!isSystemOwner) return;
    setBusy(`root-retry-${id}`);
    try {
      const updated = await rootRequest<RootWhatsAppQueueItem>(`/integrations/whatsapp/root/queue/${id}/retry`, { method: "POST" });
      setRootQueue((current) => current.map((item) => item.id === id ? updated : item));
      setFeedback({ tone: "ok", message: "Item WhatsApp reaberto para retry com auditoria." });
      await refreshRootWhatsappQueue();
    } catch (error) {
      setFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Falha ao reabrir item WhatsApp." });
    } finally {
      setBusy(null);
    }
  }

  async function notificationAction(id: string, action: "retry" | "cancel" | "mark-read" | "resolve") {
    if (!token) return;
    setBusy(`${action}-${id}`);
    try {
      const response = await fetch(`${API_URL}/notifications/${id}/${action}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "X-Tenant-Id": DEMO_TENANT_ID }
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(String(payload.detail ?? "Ação recusada pelo backend."));
      if (action === "retry") {
        const updated = payload as NotificationItem;
        setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      } else {
        setItems((current) => current.map((item) => item.id === id ? { ...item, status: action === "cancel" ? "cancelled" : action === "resolve" ? "resolved" : item.status, readAt: action === "mark-read" ? new Date().toISOString() : item.readAt, resolvedAt: action === "resolve" ? new Date().toISOString() : item.resolvedAt } : item));
      }
      setFeedback({ tone: "ok", message: action === "retry" ? "Reenvio processado com status atualizado." : "Ação registrada com auditoria." });
    } catch (error) {
      setFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Falha ao executar ação." });
    } finally {
      setBusy(null);
    }
  }

  async function testChannel(channel: NotificationItem["channel"]) {
    if (!token) return;
    setBusy(`test-${channel}`);
    try {
      const response = await fetch(`${API_URL}/notifications/test`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", "X-Tenant-Id": DEMO_TENANT_ID },
        body: JSON.stringify({
          tenantId: DEMO_TENANT_ID,
          channel,
          notificationType: channel === "whatsapp" ? "falha_whatsapp" : channel === "email" ? "relatorio_diario" : "alerta_critico",
          title: "Teste de notificação Vulcan",
          message: "Mensagem de teste gerada pela central de notificações.",
          priority: channel === "system" ? "medio" : "alto"
        })
      });
      const payload = (await response.json()) as { status?: string; providerResult?: string; detail?: string };
      if (!response.ok) throw new Error(String(payload.detail ?? "Teste recusado."));
      setFeedback({ tone: payload.status === "failed" || payload.status === "missing_credentials" ? "warn" : "ok", message: `${channelPt(channel)}: ${statusPt(payload.status ?? "queued")} | ${payload.providerResult ?? "registrado"}` });
    } catch (error) {
      setFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Falha no teste." });
    } finally {
      setBusy(null);
    }
  }

  async function previewTemplate() {
    if (!token || !selectedTemplate) return;
    setBusy("preview-template");
    try {
      const response = await fetch(`${API_URL}/notification-templates/${selectedTemplate.id}/preview`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", "X-Tenant-Id": DEMO_TENANT_ID },
        body: JSON.stringify({ variables: { empresa: "Vulcan Demo", equipe: "Operação", metrica: "ociosidade", impacto: "alto", link_dashboard: "http://localhost:3002" } })
      });
      const payload = (await response.json()) as { title: string; body: string; detail?: string };
      if (!response.ok) throw new Error(String(payload.detail ?? "Preview recusado."));
      setTemplatePreview({ title: payload.title, body: payload.body });
    } catch (error) {
      setFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Falha ao gerar preview." });
    } finally {
      setBusy(null);
    }
  }

  if (compact) {
    return (
      <ViewFrame compact>
        <Panel title="Notificações críticas" icon={BellRing}>
          <div className="grid gap-3">
            {items.slice(0, 4).map((item) => <NotificationRow key={item.id} item={item} compact />)}
          </div>
        </Panel>
      </ViewFrame>
    );
  }

  return (
    <ViewFrame>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <LiveBadge label="Central de notificações" detail={`Tempo real ativo | última atualização ${liveStatusLabel}`} />
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => void testChannel("system")} className="h-10 bg-orange-500 px-4 text-sm font-semibold text-black transition hover:bg-orange-400">Testar sistema</button>
          <button type="button" onClick={() => void testChannel("whatsapp")} className="h-10 border border-orange-400/30 px-4 text-sm text-orange-200 transition hover:border-orange-300/60">Testar WhatsApp</button>
          <button type="button" onClick={() => void testChannel("email")} className="h-10 border border-orange-400/30 px-4 text-sm text-orange-200 transition hover:border-orange-300/60">Testar e-mail</button>
        </div>
      </div>

      {feedback ? <div className="mb-5"><FeedbackBanner tone={feedback.tone} message={feedback.message} /></div> : null}

      <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <Tremor.Card className="rounded-lg border border-zinc-800 bg-zinc-950/82 p-5 shadow-tremor-card">
          <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
            <div>
              <Tremor.Text className="text-xs uppercase tracking-[0.2em] text-orange-200">Orquestração operacional</Tremor.Text>
              <Tremor.Title className="mt-2 text-zinc-50">Alertas, envios, preferências e ações em um só lugar.</Tremor.Title>
            </div>
            <div className="flex flex-wrap gap-2">
              <Tremor.Badge color={whatsAppStatus.connected ? "emerald" : "orange"}>WhatsApp {whatsAppStatus.connected ? "pronto" : "pendente"}</Tremor.Badge>
              <Tremor.Badge color={emailReady ? "emerald" : "orange"}>E-mail {emailReady ? "pronto" : "pendente"}</Tremor.Badge>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <MetricSignalCard icon={BellRing} label="Pendentes" value={`${summary.pending}`} detail={`${summary.unread} não lidas`} tone={summary.pending ? "warn" : "ok"} />
            <MetricSignalCard icon={ShieldCheck} label="Críticas" value={`${summary.critical}`} detail="exigem ação ou confirmação" tone={summary.critical ? "critical" : "ok"} />
            <MetricSignalCard icon={CheckCircle2} label="Enviadas" value={`${summary.sent}`} detail={`${summary.failed} falhas registradas`} tone={summary.failed ? "warn" : "ok"} />
          </div>
        </Tremor.Card>

        <Panel title="Canais" icon={RadioTower}>
          <div className="grid gap-3 md:grid-cols-2">
            {channels.map((channel) => {
              const Icon = iconByChannel[channel as NotificationItem["channel"]] ?? BellRing;
              const count = summary.byChannel[channel] ?? items.filter((item) => item.channel === channel).length;
              const ready = channel === "whatsapp" ? whatsAppStatus.connected : channel === "email" ? emailReady : channel === "push" ? false : true;
              return (
                <button key={channel} type="button" onClick={() => setChannelFilter(channel)} className={`border p-4 text-left transition hover:border-orange-400/50 ${channelFilter === channel ? "border-orange-300/70 bg-orange-950/10" : "border-zinc-800 bg-black/35"}`}>
                  <div className="flex items-center gap-3">
                    <div className="grid h-10 w-10 place-items-center bg-orange-500 text-black"><Icon className="h-5 w-5" /></div>
                    <div>
                      <p className="font-semibold">{channelPt(channel)}</p>
                      <p className={ready ? "text-xs text-emerald-300" : "text-xs text-orange-300"}>{ready ? "operacional" : "pendente/configuração"}</p>
                    </div>
                  </div>
                  <p className="mt-3 text-sm text-zinc-500">{count} registro(s) no escopo</p>
                </button>
              );
            })}
          </div>
          {isSystemOwner ? (
            <div className="mt-4 border border-zinc-800 bg-black/35 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-zinc-100">Operação WhatsApp raiz</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.14em] text-zinc-500">{statusPt(whatsAppStatus.status)} | {rootQueueIssues.length} atenção</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => void processRootWhatsappQueue()} disabled={Boolean(busy)} className="h-9 border border-orange-400/25 px-3 text-xs text-orange-200 transition hover:border-orange-300/60 disabled:opacity-40">Processar</button>
                  <button type="button" onClick={() => void refreshRootWhatsappQueue()} disabled={Boolean(busy)} className="h-9 border border-zinc-800 px-3 text-xs text-zinc-300 transition hover:border-orange-400/50 disabled:opacity-40">Atualizar</button>
                </div>
              </div>
              <div className="mt-3 grid gap-2">
                {rootQueue.slice(0, 4).map((item) => (
                  <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 border border-zinc-800 bg-zinc-950/55 px-3 py-2">
                    <div>
                      <p className="text-sm text-zinc-200">{item.title}</p>
                      <p className="text-xs text-zinc-500">{maskPhone(item.destination)} | {statusPt(item.status)} | {item.attempts}/{item.maxAttempts}</p>
                    </div>
                    <button type="button" onClick={() => void retryRootWhatsappItem(item.id)} disabled={Boolean(busy)} className="border border-orange-400/25 px-2 py-1 text-xs text-orange-200 transition hover:border-orange-300/60 disabled:opacity-40">Reabrir</button>
                  </div>
                ))}
                {!rootQueue.length ? <p className="text-sm text-zinc-500">Sem envios WhatsApp pendentes no escopo atual.</p> : null}
                {rootLogs[0] ? <p className="text-xs text-zinc-600">Último log: {statusPt(rootLogs[0].status)} em {formatDateTime(rootLogs[0].createdAt)}</p> : null}
              </div>
            </div>
          ) : (
            <div className="mt-4 border border-zinc-800 bg-black/35 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-zinc-100">Canal WhatsApp gerenciado pela Vulcan</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.14em] text-zinc-500">{statusPt(whatsAppStatus.status)} | fallback e-mail/interno preparado</p>
                </div>
                <Tremor.Badge color={whatsAppStatus.connected ? "emerald" : "orange"}>{whatsAppStatus.connected ? "operacional" : "pendente"}</Tremor.Badge>
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <ConnectionSummary label="Emissor" value={maskPhone(whatsAppStatus.rootChannelNumber)} tone={whatsAppStatus.rootChannelNumber ? "ok" : "warn"} />
                <ConnectionSummary label="Proteção" value="tenant + hierarquia" tone="ok" />
              </div>
            </div>
          )}
        </Panel>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[0.95fr_1.05fr]">
        <Panel title="Tipos e preferências" icon={SlidersHorizontal}>
          <div className="mb-4 grid gap-3 md:grid-cols-3">
            <MetricFilterSelect label="Canal" value={channelFilter} onChange={setChannelFilter} options={[["all", "Todos"], ...channels.map((item) => [item, channelPt(item)] as [string, string])]} />
            <MetricFilterSelect label="Status" value={statusFilter} onChange={setStatusFilter} options={[["all", "Todos"], ...statuses.map((item) => [item, statusPt(item)] as [string, string])]} />
            <MetricFilterSelect label="Prioridade" value={priorityFilter} onChange={setPriorityFilter} options={[["all", "Todas"], ...priorities.map((item) => [item, priorityPt(item)] as [string, string])]} />
          </div>
          <div className="grid max-h-[560px] gap-3 overflow-y-auto pr-1">
            {types.map((type, index) => (
              <motion.div key={type.id} className="border border-zinc-800 bg-black/35 p-4" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.025 }}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-zinc-100">{type.name}</p>
                    <p className="mt-2 text-sm leading-6 text-zinc-500">{type.description}</p>
                  </div>
                  <button type="button" onClick={() => type.canDisable && setTypes((current) => current.map((item) => item.id === type.id ? { ...item, enabled: !item.enabled } : item))} className={`border px-3 py-1 text-xs uppercase tracking-[0.14em] ${type.enabled ? "border-emerald-400/25 text-emerald-200" : "border-zinc-700 text-zinc-500"}`}>
                    {type.enabled ? "ativo" : "pausado"}
                  </button>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <span className="border border-orange-400/20 px-2 py-1 text-orange-200">{priorityPt(type.defaultPriority)}</span>
                  <span className="border border-zinc-800 px-2 py-1 text-zinc-400">{type.defaultFrequency}</span>
                  <span className="border border-zinc-800 px-2 py-1 text-zinc-400">{type.defaultAudience}</span>
                </div>
              </motion.div>
            ))}
          </div>
        </Panel>

        <Panel title="Histórico e fila" icon={Activity}>
          <div className="grid max-h-[640px] gap-3 overflow-y-auto pr-1">
            {filtered.length ? filtered.map((item, index) => (
              <NotificationRow
                key={item.id}
                item={item}
                index={index}
                busy={busy}
                onRetry={() => void notificationAction(item.id, "retry")}
                onRead={() => void notificationAction(item.id, "mark-read")}
                onResolve={() => void notificationAction(item.id, "resolve")}
                onCancel={() => void notificationAction(item.id, "cancel")}
              />
            )) : <EmptyState title="Sem notificações no filtro" description="Ajuste canal, status ou prioridade para ver o histórico." />}
          </div>
        </Panel>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <Panel title="Agendamentos" icon={CalendarClock}>
          <div className="grid gap-3">
            {schedules.map((schedule) => (
              <div key={schedule.id} className="border border-zinc-800 bg-black/35 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-zinc-100">{schedule.name}</p>
                    <p className="mt-1 text-sm text-zinc-500">{schedule.recurrence} | {schedule.timezone}</p>
                  </div>
                  <span className={schedule.enabled ? "border border-emerald-400/20 px-2 py-1 text-xs text-emerald-200" : "border border-zinc-700 px-2 py-1 text-xs text-zinc-500"}>{schedule.enabled ? "ativo" : "pausado"}</span>
                </div>
                <p className="mt-3 text-sm text-zinc-400">Horários: {schedule.times.join(", ")}</p>
                <p className="mt-2 text-sm text-zinc-400">Destinatários: {schedule.recipients.join(", ") || "escopo configurado"}</p>
                <p className="mt-2 text-xs uppercase tracking-[0.14em] text-orange-300">{schedule.channels.map(channelPt).join(" | ")}</p>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Templates" icon={FileText}>
          <div className="grid gap-3">
            <MetricFilterSelect label="Modelo" value={selectedTemplate?.id ?? selectedTemplateId} onChange={setSelectedTemplateId} options={notificationTemplates.map((item) => [item.id, `${channelPt(item.channel)} - ${item.title}`] as [string, string])} />
            {selectedTemplate ? (
              <div className="border border-zinc-800 bg-black/35 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-zinc-100">{selectedTemplate.title}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.14em] text-orange-300">{channelPt(selectedTemplate.channel)} | {selectedTemplate.notificationType} | v{selectedTemplate.version}</p>
                  </div>
                  <span className={selectedTemplate.active ? "text-emerald-300" : "text-zinc-500"}>{selectedTemplate.active ? "ativo" : "inativo"}</span>
                </div>
                <p className="mt-4 whitespace-pre-line text-sm leading-6 text-zinc-400">{selectedTemplate.body}</p>
                <p className="mt-3 text-xs text-zinc-500">Variáveis: {selectedTemplate.variables.join(", ")}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button type="button" onClick={() => void previewTemplate()} className="h-9 bg-orange-500 px-3 text-xs font-semibold text-black transition hover:bg-orange-400">Gerar preview</button>
                  <button type="button" onClick={() => void testChannel(selectedTemplate.channel)} className="h-9 border border-orange-400/25 px-3 text-xs text-orange-200 transition hover:border-orange-300/60">Testar canal</button>
                </div>
              </div>
            ) : null}
            {templatePreview ? (
              <motion.div className="border border-orange-400/20 bg-orange-950/10 p-4" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
                <p className="font-semibold text-orange-100">{templatePreview.title}</p>
                <p className="mt-3 whitespace-pre-line text-sm leading-6 text-zinc-300">{templatePreview.body}</p>
              </motion.div>
            ) : null}
          </div>
        </Panel>
      </div>

      <Panel title="Segurança, hierarquia e LGPD" icon={ShieldCheck}>
        <div className="grid gap-4 md:grid-cols-3">
          <ConnectionSummary label="Escopo" value="tenant + subárvore" tone="ok" />
          <ConnectionSummary label="Dados sensíveis" value="sem conteúdo pessoal" tone="ok" />
          <ConnectionSummary label="Mocks" value="explícitos por status" tone="warn" />
        </div>
        <p className="mt-4 text-sm leading-6 text-zinc-400">Notificações usam o mesmo backend hierárquico do Vulcan. Operador vê alertas pessoais; líderes e gestores veem apenas sua subárvore; admin/diretor recebe visão consolidada. WhatsApp/e-mail exibem `missing_credentials` ou `mocked` quando não há provedor real configurado.</p>
      </Panel>
    </ViewFrame>
  );
}

function NotificationRow({ item, index = 0, compact = false, busy, onRetry, onRead, onResolve, onCancel }: { item: NotificationItem; index?: number; compact?: boolean; busy?: string | null; onRetry?: () => void; onRead?: () => void; onResolve?: () => void; onCancel?: () => void }) {
  const iconByChannel = { system: BellRing, push: BellRing, windows: Monitor, whatsapp: MessageCircle, email: Mail };
  const Icon = iconByChannel[item.channel] ?? BellRing;
  const tone = item.priority === "critico" || item.status === "failed" ? "critical" : ["missing_credentials", "queued", "retrying"].includes(item.status) ? "warn" : "ok";
  return (
    <motion.div className={`border p-4 ${tone === "critical" ? "border-rose-400/25 bg-rose-950/10" : tone === "warn" ? "border-orange-400/20 bg-orange-950/10" : "border-zinc-800 bg-black/35"}`} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.035 }}>
      <div className="flex items-start gap-3">
        <div className="grid h-10 w-10 shrink-0 place-items-center bg-orange-500 text-black"><Icon className="h-5 w-5" /></div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <p className="font-semibold text-zinc-100">{item.title}</p>
              <p className="mt-1 text-xs uppercase tracking-[0.14em] text-zinc-500">{channelPt(item.channel)} | {statusPt(item.status)} | {priorityPt(item.priority ?? "medio")} | {item.recipient ?? "escopo permitido"}</p>
            </div>
            <span className="text-xs text-zinc-500">{formatDateTime(item.createdAt)}</span>
          </div>
          <p className="mt-3 text-sm leading-6 text-zinc-400">{item.message}</p>
          {!compact ? (
            <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
              <span className="border border-zinc-800 px-2 py-1 text-zinc-500">Tentativas {item.attempts ?? 0}/{item.maxAttempts ?? 3}</span>
              {item.error ? <span className="border border-orange-400/25 px-2 py-1 text-orange-200">{item.error}</span> : null}
              <button disabled={!onRetry || Boolean(busy)} onClick={onRetry} type="button" className="border border-orange-400/25 px-3 py-2 text-orange-200 transition hover:border-orange-300/60 disabled:opacity-40">Reenviar</button>
              <button disabled={!onRead || Boolean(busy)} onClick={onRead} type="button" className="border border-zinc-800 px-3 py-2 text-zinc-300 transition hover:border-orange-400/50 disabled:opacity-40">Lida</button>
              <button disabled={!onResolve || Boolean(busy)} onClick={onResolve} type="button" className="border border-emerald-400/25 px-3 py-2 text-emerald-200 transition hover:border-emerald-300/60 disabled:opacity-40">Resolver</button>
              <button disabled={!onCancel || Boolean(busy)} onClick={onCancel} type="button" className="border border-zinc-800 px-3 py-2 text-zinc-400 transition hover:border-zinc-500 disabled:opacity-40">Cancelar</button>
            </div>
          ) : null}
        </div>
      </div>
    </motion.div>
  );
}

function SettingsView({
  settingsCenter,
  onSettingsCenterChange,
  supabaseStatus,
  aiStatus,
  whatsAppStatus,
  emailStatuses,
  devices,
  pendingDevices,
  teams,
  hierarchy,
  notifications,
  schedules,
  reportTemplates,
  token,
  userRole
}: {
  settingsCenter: SettingsResponseData;
  onSettingsCenterChange: (next: SettingsResponseData) => void;
  supabaseStatus: SupabaseStatus;
  aiStatus: AIStatus;
  whatsAppStatus: WhatsAppStatus;
  emailStatuses: EmailProviderStatus[];
  devices: Device[];
  pendingDevices: Device[];
  teams: Team[];
  hierarchy: HierarchyNode[];
  notifications: NotificationItem[];
  schedules: NotificationSchedule[];
  reportTemplates: ReportTemplate[];
  token: string;
  userRole: string;
}) {
  const [selectedSectionId, setSelectedSectionId] = useState(settingsCenter.sections[0]?.id ?? "");
  const [query, setQuery] = useState("");
  const [drafts, setDrafts] = useState<Record<string, Record<string, string | number | boolean | null>>>({});
  const [feedback, setFeedback] = useState<{ tone: "ok" | "warn"; message: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const smtpStatus = emailStatuses.find((item) => item.provider === "smtp") ?? fallbackEmailStatuses[0];
  const emailReady = emailStatuses.some((item) => item.configured && item.canSend);
  const offlineAgents = devices.filter((device) => device.status === "offline").length;
  const queueIssues = devices.filter((device) => Number(device.queueDepth ?? 0) > 50).length;
  const failedNotifications = notifications.filter((item) => ["failed", "missing_credentials"].includes(item.status)).length;
  const isSystemOwner = userRole === "owner" || userRole === "root";

  useEffect(() => {
    const nextDrafts: Record<string, Record<string, string | number | boolean | null>> = {};
    settingsCenter.sections.forEach((section) => {
      nextDrafts[section.id] = Object.fromEntries(section.fields.map((field) => [field.key, field.value]));
    });
    setDrafts(nextDrafts);
    if (!selectedSectionId && settingsCenter.sections[0]) setSelectedSectionId(settingsCenter.sections[0].id);
  }, [settingsCenter, selectedSectionId]);

  const filteredSections = settingsCenter.sections.filter((section) => {
    const haystack = `${section.title} ${section.description} ${section.fields.map((field) => `${field.label} ${field.description}`).join(" ")}`.toLowerCase();
    return haystack.includes(query.trim().toLowerCase());
  });
  const selectedSection = settingsCenter.sections.find((section) => section.id === selectedSectionId) ?? filteredSections[0] ?? settingsCenter.sections[0] ?? null;
  const selectedDraft = selectedSection ? drafts[selectedSection.id] ?? {} : {};

  async function refreshSettings() {
    const next = await fetchProtected<SettingsResponseData>("/settings", token, settingsCenter);
    onSettingsCenterChange(next);
  }

  async function saveSection(section: SettingsSectionData) {
    setBusy(`save-${section.id}`);
    setFeedback(null);
    try {
      const values = Object.fromEntries(
        section.fields
          .filter((field) => field.editable && field.valueType !== "readonly" && field.valueType !== "secret")
          .map((field) => [field.key, selectedDraft[field.key]])
      );
      const response = await fetch(`${API_URL}/settings/${section.id}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", "X-Tenant-Id": DEMO_TENANT_ID },
        body: JSON.stringify({ values })
      });
      const payload = (await response.json()) as SettingsActionResponseData & { detail?: string };
      if (!response.ok) throw new Error(String(payload.detail ?? "Configuração recusada pelo backend."));
      await refreshSettings();
      setFeedback({ tone: "ok", message: payload.message });
    } catch (error) {
      setFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Falha ao salvar configuração." });
    } finally {
      setBusy(null);
    }
  }

  async function testSection(section: SettingsSectionData) {
    setBusy(`test-${section.id}`);
    setFeedback(null);
    try {
      const response = await fetch(`${API_URL}/settings/${section.id}/test`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "X-Tenant-Id": DEMO_TENANT_ID }
      });
      const payload = (await response.json()) as SettingsActionResponseData & { detail?: string };
      if (!response.ok) throw new Error(String(payload.detail ?? "Teste recusado pelo backend."));
      setFeedback({ tone: payload.status === "ok" ? "ok" : "warn", message: payload.message });
    } catch (error) {
      setFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Falha ao testar configuração." });
    } finally {
      setBusy(null);
    }
  }

  async function testIntegration(kind: "whatsapp" | "email", provider?: string, destination?: string | null) {
    setBusy(`integration-${kind}`);
    try {
      const response = await fetch(`${API_URL}/integrations/${kind}/test`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json", "X-Tenant-Id": DEMO_TENANT_ID },
        body: JSON.stringify({ tenantId: DEMO_TENANT_ID, provider, destination: destination || undefined, message: "Mensagem de teste enviada pela central de configurações do Vulcan." })
      });
      const payload = (await response.json()) as { ok?: boolean; status?: string; message?: string; detail?: string };
      if (!response.ok) throw new Error(String(payload.detail ?? "Teste recusado."));
      setFeedback({ tone: payload.ok ? "ok" : "warn", message: `${kind === "whatsapp" ? "WhatsApp" : "E-mail"}: ${payload.message ?? statusPt(payload.status ?? "pendente")}` });
    } catch (error) {
      setFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Falha ao testar integração." });
    } finally {
      setBusy(null);
    }
  }

  return (
    <ViewFrame>
      <div className="grid gap-5">
        <div className="grid gap-5 xl:grid-cols-[1fr_0.72fr]">
          <Tremor.Card className="rounded-lg border border-zinc-800 bg-zinc-950/82 p-5 shadow-tremor-card">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <Tremor.Text className="text-xs uppercase tracking-[0.22em] text-orange-200">Central de controle</Tremor.Text>
                <Tremor.Title className="mt-2 text-zinc-50">Configurações reais, testáveis e auditadas do Vulcan.</Tremor.Title>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-400">Campos editáveis salvam em `tenant_settings`; secrets aparecem apenas como status; integrações sem credencial ficam marcadas como pendentes ou mock explícito.</p>
              </div>
              <Tremor.Badge color={settingsCenter.summary.canEdit ? "emerald" : "orange"}>{settingsCenter.summary.canEdit ? "admin: edição liberada" : "somente leitura"}</Tremor.Badge>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-5">
              <MetricSignalCard icon={CheckCircle2} label="OK" value={`${settingsCenter.summary.ok}`} detail="seções prontas" tone="ok" />
              <MetricSignalCard icon={ShieldCheck} label="Atenção" value={`${settingsCenter.summary.attention}`} detail="requer revisão" tone={settingsCenter.summary.attention ? "warn" : "ok"} />
              <MetricSignalCard icon={Lock} label="Credenciais" value={`${settingsCenter.summary.missing}`} detail="faltando ou pendente" tone={settingsCenter.summary.missing ? "warn" : "ok"} />
              <MetricSignalCard icon={RadioTower} label="Agentes" value={`${devices.length - offlineAgents}/${devices.length || 0}`} detail={`${pendingDevices.length} pendente(s) de adoção`} tone={offlineAgents || queueIssues ? "warn" : "ok"} />
              <MetricSignalCard icon={BellRing} label="Notificações" value={`${failedNotifications}`} detail="falhas/credenciais" tone={failedNotifications ? "warn" : "ok"} />
            </div>
          </Tremor.Card>

          <Panel title="Diagnóstico rápido" icon={DatabaseZap}>
            <div className="grid gap-3">
              <ConnectionSummary label="Supabase REST" value={supabaseStatus.restReachable === false ? "bloqueado" : supabaseStatus.restReachable ? "alcançável" : "não testado"} tone={supabaseStatus.restReachable === false ? "warn" : "ok"} />
              <ConnectionSummary label="Banco" value={supabaseStatus.databaseReachable === false ? "bloqueado" : supabaseStatus.databaseUrlConfigured ? "configurado" : "pendente"} tone={supabaseStatus.databaseReachable === false || !supabaseStatus.databaseUrlConfigured ? "warn" : "ok"} />
              <ConnectionSummary label="GPT" value={aiStatus.openaiConfigured ? "configurado" : "fallback explícito"} tone={aiStatus.openaiConfigured ? "ok" : "warn"} />
              <ConnectionSummary label="WhatsApp" value={whatsAppStatus.connected ? "conectado" : statusPt(whatsAppStatus.status)} tone={whatsAppStatus.connected ? "ok" : "warn"} />
              <ConnectionSummary label="SMTP" value={smtpStatus.configured ? "configurado" : "requer credencial"} tone={smtpStatus.configured ? "ok" : "warn"} />
            </div>
          </Panel>
        </div>

        {feedback ? <FeedbackBanner tone={feedback.tone} message={feedback.message} /> : null}

        <div className="grid gap-5 xl:grid-cols-[330px_1fr]">
          <Panel title="Seções" icon={Layers3}>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Buscar configuração..."
              className="mb-4 h-11 w-full border border-zinc-800 bg-black/45 px-3 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-orange-400/55"
            />
            <div className="grid max-h-[720px] gap-2 overflow-y-auto pr-1">
              {(filteredSections.length ? filteredSections : settingsCenter.sections).map((section) => {
                const Icon = settingsIcon(section.id);
                return (
                  <button
                    key={section.id}
                    type="button"
                    onClick={() => setSelectedSectionId(section.id)}
                    className={`border p-3 text-left transition hover:border-orange-400/45 ${selectedSection?.id === section.id ? "border-orange-300/60 bg-orange-950/10" : "border-zinc-800 bg-black/35"}`}
                  >
                    <div className="flex items-start gap-3">
                      <div className="grid h-9 w-9 shrink-0 place-items-center bg-orange-500 text-black"><Icon className="h-4 w-4" /></div>
                      <div className="min-w-0">
                        <p className="truncate font-semibold text-zinc-100">{section.title}</p>
                        <p className="mt-1 text-xs text-zinc-500">{settingsStatusPt(section.status)} | {scopePt(section.scope)}</p>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </Panel>

          {selectedSection ? (
            <Panel title={selectedSection.title} icon={settingsIcon(selectedSection.id)}>
              <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="max-w-3xl text-sm leading-6 text-zinc-400">{selectedSection.description}</p>
                  <p className="mt-2 text-xs uppercase tracking-[0.16em] text-zinc-500">Escopo: {scopePt(selectedSection.scope)} | Última alteração: {formatDateTime(selectedSection.lastUpdatedAt)}</p>
                </div>
                <Tremor.Badge color={settingsToneColor(selectedSection.status)}>{settingsStatusPt(selectedSection.status)}</Tremor.Badge>
              </div>

              <div className="grid gap-4 xl:grid-cols-2">
                {selectedSection.fields.map((field) => (
                  <SettingsFieldControl
                    key={field.key}
                    field={field}
                    value={selectedDraft[field.key]}
                    onChange={(value) => {
                      setDrafts((current) => ({
                        ...current,
                        [selectedSection.id]: { ...(current[selectedSection.id] ?? {}), [field.key]: value }
                      }));
                    }}
                  />
                ))}
              </div>

              <div className="mt-5 flex flex-wrap gap-3">
                <button type="button" onClick={() => void testSection(selectedSection)} disabled={Boolean(busy)} className="inline-flex h-11 items-center gap-2 border border-zinc-800 bg-black/45 px-4 text-sm text-zinc-200 transition hover:border-orange-400/45 disabled:opacity-40">
                  <Zap className="h-4 w-4 text-orange-300" />
                  Testar seção
                </button>
                {selectedSection.canEdit ? (
                  <button type="button" onClick={() => void saveSection(selectedSection)} disabled={Boolean(busy)} className="inline-flex h-11 items-center gap-2 bg-orange-500 px-4 text-sm font-semibold text-black transition hover:bg-orange-400 disabled:opacity-40">
                    <Save className="h-4 w-4" />
                    Salvar e auditar
                  </button>
                ) : null}
                {selectedSection.id === "whatsapp" && isSystemOwner ? (
                  <button type="button" onClick={() => void testIntegration("whatsapp", whatsAppStatus.provider, whatsAppStatus.rootChannelNumber)} disabled={Boolean(busy)} className="inline-flex h-11 items-center gap-2 border border-orange-400/25 px-4 text-sm text-orange-200 transition hover:border-orange-300/60 disabled:opacity-40">
                    <MessageCircle className="h-4 w-4" />
                    Testar WhatsApp
                  </button>
                ) : null}
                {selectedSection.id === "email" ? (
                  <button type="button" onClick={() => void testIntegration("email", smtpStatus.provider)} disabled={Boolean(busy)} className="inline-flex h-11 items-center gap-2 border border-orange-400/25 px-4 text-sm text-orange-200 transition hover:border-orange-300/60 disabled:opacity-40">
                    <Mail className="h-4 w-4" />
                    Testar e-mail
                  </button>
                ) : null}
              </div>

              {selectedSection.id === "whatsapp" ? (
                isSystemOwner ? (
                <EvolutionWhatsAppPanel token={token} initialWhatsAppStatus={whatsAppStatus} />
                ) : (
                  <ManagedWhatsAppPanel status={whatsAppStatus} />
                )
              ) : null}
            </Panel>
          ) : (
            <EmptyState title="Configurações indisponíveis" description="O backend ainda não retornou seções de configuração para este usuário." />
          )}
        </div>

        <div className="grid gap-5 xl:grid-cols-3">
          <Panel title="Usuários, equipes e hierarquia" icon={Network}>
            <div className="grid gap-3">
              <ConnectionSummary label="Pessoas no escopo" value={`${hierarchy.length}`} tone={hierarchy.length ? "ok" : "warn"} />
              <ConnectionSummary label="Equipes" value={`${teams.length}`} tone={teams.length ? "ok" : "warn"} />
              <ConnectionSummary label="Dispositivos" value={`${devices.length}`} tone={devices.length ? "ok" : "warn"} />
            </div>
            <p className="mt-4 text-sm leading-6 text-zinc-400">CRUD avançado continua na tela Hierarquia para evitar duplicidade. Configurações controla políticas, permissões e defaults do tenant.</p>
          </Panel>

          <Panel title="Relatórios e exportações" icon={Download}>
            <div className="grid gap-3">
              {reportTemplates.slice(0, 3).map((template) => (
                <ConnectionSummary key={template.id} label={template.name} value={template.enabled ? template.cadence : "pausado"} tone={template.enabled ? "ok" : "warn"} />
              ))}
            </div>
            <p className="mt-4 text-sm leading-6 text-zinc-400">CSV/Excel ficam em Métricas; agendamentos e templates ficam em Notificações. Configurações mostra status e defaults.</p>
          </Panel>

          <Panel title="Agendamentos ativos" icon={BellRing}>
            <div className="grid gap-3">
              {schedules.slice(0, 3).map((schedule) => (
                <ConnectionSummary key={schedule.id} label={schedule.name} value={`${schedule.recurrence} | ${schedule.channels.map(channelPt).join(", ")}`} tone={schedule.enabled ? "ok" : "warn"} />
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </ViewFrame>
  );
}

function ManagedWhatsAppPanel({ status }: { status: WhatsAppStatus }) {
  return (
    <div className="mt-6 border-t border-zinc-800 pt-6">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-zinc-100">Canal WhatsApp gerenciado pela Vulcan</p>
          <p className="mt-1 text-sm leading-6 text-zinc-500">As mensagens automáticas usam o emissor mestre da Vulcan e respeitam destinatários, opt-in, tenant e hierarquia.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Tremor.Badge color={status.connected ? "emerald" : "orange"}>{status.connected ? "operacional" : statusPt(status.status)}</Tremor.Badge>
          <Tremor.Badge color={status.rootChannelNumber ? "emerald" : "orange"}>{status.rootChannelNumber ? "número configurado" : "número pendente"}</Tremor.Badge>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <ConnectionSummary label="Número mestre" value={maskPhone(status.rootChannelNumber)} tone={status.rootChannelNumber ? "ok" : "warn"} />
        <ConnectionSummary label="Escopo" value="tenant + subárvore" tone="ok" />
        <ConnectionSummary label="Opt-in" value={status.rootChannelEnabled ? "obrigatório" : "pendente"} tone={status.rootChannelEnabled ? "ok" : "warn"} />
        <ConnectionSummary label="Fallback" value="e-mail/in-app" tone="ok" />
      </div>
    </div>
  );
}

function EvolutionWhatsAppPanel({ token, initialWhatsAppStatus }: { token: string; initialWhatsAppStatus: WhatsAppStatus }) {
  const [status, setStatus] = useState<EvolutionStatus | null>(null);
  const [queue, setQueue] = useState<RootWhatsAppQueueItem[]>([]);
  const [logs, setLogs] = useState<RootWhatsAppLog[]>([]);
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [draft, setDraft] = useState<EvolutionConfigDraft>(() => evolutionDraftFromStatus(null, initialWhatsAppStatus));
  const [busy, setBusy] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "ok" | "warn"; message: string } | null>(null);
  const actionBusyRef = useRef(false);

  useEffect(() => {
    void refreshAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        "X-Tenant-Id": DEMO_TENANT_ID,
        ...(init.body ? { "Content-Type": "application/json" } : {})
      }
    });
    const payload = (await response.json().catch(() => ({}))) as T & { detail?: string };
    if (!response.ok) throw new Error(String(payload.detail ?? "Requisição recusada pelo backend."));
    return payload;
  }

  async function refreshAll(options: { force?: boolean } = {}) {
    if (!token) return;
    if (actionBusyRef.current && !options.force) return;
    if (!options.force) setBusy((current) => current ?? "refresh");
    try {
      const [nextStatus, nextQueue, nextLogs] = await Promise.all([
        requestJson<EvolutionStatus>("/integrations/whatsapp/evolution/status"),
        requestJson<RootWhatsAppQueueItem[]>("/integrations/whatsapp/root/queue?limit=12"),
        requestJson<RootWhatsAppLog[]>("/integrations/whatsapp/root/logs?limit=12")
      ]);
      setStatus(nextStatus);
      setQueue(nextQueue);
      setLogs(nextLogs);
      setQrCode(nextStatus.qrCode);
      setDraft((current) => {
        const next = evolutionDraftFromStatus(nextStatus, initialWhatsAppStatus);
        return {
          ...next,
          apiKey: current.apiKey,
          testDestination: current.testDestination || next.rootNumber,
          testMessage: current.testMessage || next.testMessage
        };
      });
    } catch (error) {
      setFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Falha ao atualizar WhatsApp." });
    } finally {
      if (!options.force) setBusy(null);
    }
  }

  function beginAction(key: string) {
    if (actionBusyRef.current) return false;
    actionBusyRef.current = true;
    setBusy(key);
    return true;
  }

  function endAction() {
    actionBusyRef.current = false;
    setBusy(null);
  }

  function updateDraft<K extends keyof EvolutionConfigDraft>(key: K, value: EvolutionConfigDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  async function saveConfig() {
    if (!beginAction("save-evolution")) return;
    setFeedback(null);
    try {
      const nextStatus = await requestJson<EvolutionStatus>("/integrations/whatsapp/evolution/config", {
        method: "PUT",
        body: JSON.stringify({
          enabled: draft.enabled,
          provider: draft.provider,
          rootNumber: draft.rootNumber,
          rootName: draft.rootName,
          baseUrl: draft.baseUrl,
          apiKey: draft.apiKey.trim() || undefined,
          instanceName: draft.instanceName,
          mockMode: draft.mockMode || draft.provider === "mock",
          requireOptIn: draft.requireOptIn,
          emailFallbackEnabled: draft.emailFallbackEnabled,
          inAppFallbackEnabled: draft.inAppFallbackEnabled
        })
      });
      setStatus(nextStatus);
      setQrCode(nextStatus.qrCode);
      setDraft((current) => ({ ...evolutionDraftFromStatus(nextStatus, initialWhatsAppStatus), apiKey: "", testDestination: current.testDestination, testMessage: current.testMessage }));
      setFeedback({ tone: "ok", message: `WhatsApp salvo. Status: ${statusPt(nextStatus.status)}.` });
      await refreshAll({ force: true });
    } catch (error) {
      setFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Falha ao salvar WhatsApp." });
    } finally {
      endAction();
    }
  }

  async function runEvolutionAction(key: string, label: string, path: string, init: RequestInit = {}) {
    if (!beginAction(key)) return;
    setFeedback(null);
    try {
      const payload = await requestJson<EvolutionActionResponse>(path, init);
      setQrCode(payload.qrCode ?? qrCode);
      setFeedback({ tone: payload.ok ? "ok" : "warn", message: `${label}: ${payload.message || statusPt(payload.status)}` });
      await refreshAll({ force: true });
    } catch (error) {
      setFeedback({ tone: "warn", message: error instanceof Error ? error.message : `Falha em ${label}.` });
    } finally {
      endAction();
    }
  }

  async function sendTest() {
    await runEvolutionAction("send-test", "Envio teste", "/integrations/whatsapp/evolution/send-test", {
      method: "POST",
      body: JSON.stringify({
        tenantId: DEMO_TENANT_ID,
        provider: "evolution",
        destination: draft.testDestination,
        message: draft.testMessage
      })
    });
  }

  async function processQueue() {
    if (!beginAction("process-queue")) return;
    setFeedback(null);
    try {
      const payload = await requestJson<{ status: string; queued: number; sent: number; failed: number; mode: string }>("/integrations/whatsapp/root/process-queue?limit=25", { method: "POST" });
      setFeedback({ tone: payload.failed ? "warn" : "ok", message: `Fila processada: ${payload.sent} enviada(s), ${payload.failed} falha(s), ${payload.queued} ainda na fila. Modo: ${statusPt(payload.mode)}.` });
      await refreshAll({ force: true });
    } catch (error) {
      setFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Falha ao processar fila." });
    } finally {
      endAction();
    }
  }

  async function retryQueueItem(id: string) {
    if (!beginAction(`retry-${id}`)) return;
    setFeedback(null);
    try {
      const updated = await requestJson<RootWhatsAppQueueItem>(`/integrations/whatsapp/root/queue/${id}/retry`, { method: "POST" });
      setQueue((current) => current.map((item) => item.id === id ? updated : item));
      setFeedback({ tone: "ok", message: `Reenvio reaberto para ${maskPhone(updated.destination)}.` });
      await refreshAll({ force: true });
    } catch (error) {
      setFeedback({ tone: "warn", message: error instanceof Error ? error.message : "Falha ao reagendar envio." });
    } finally {
      endAction();
    }
  }

  const currentStatus = status?.status ?? initialWhatsAppStatus.status;
  const connected = Boolean(status?.connected ?? initialWhatsAppStatus.connected);
  const latestFailures = queue.filter((item) => ["failed", "provider_unavailable", "qr_required", "rate_limited"].includes(item.status));
  const canShowQr = Boolean(qrCode);

  return (
    <div className="mt-6 border-t border-zinc-800 pt-6">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-zinc-100">Evolution/Baileys</p>
          <p className="mt-1 text-sm leading-6 text-zinc-500">Provider não oficial. O Vulcan mantém tenant, hierarquia, fila, retry e auditoria; a Evolution faz só o transporte.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Tremor.Badge color={connected ? "emerald" : currentStatus === "mock" ? "orange" : "rose"}>{statusPt(currentStatus)}</Tremor.Badge>
          <Tremor.Badge color={status?.apiKeyConfigured ? "emerald" : "orange"}>{status?.apiKeyConfigured ? "API key configurada" : "sem API key"}</Tremor.Badge>
          <Tremor.Badge color={status?.unofficial ? "orange" : "emerald"}>{status?.unofficial ? "não oficial" : "oficial/futuro"}</Tremor.Badge>
        </div>
      </div>

      {feedback ? <FeedbackBanner tone={feedback.tone} message={feedback.message} /> : null}
      {busy ? (
        <div className="mb-4 border border-orange-400/25 bg-orange-950/15 px-4 py-3 text-sm text-orange-100">
          Ação em andamento: {statusPt(busy)}. Aguarde concluir antes de iniciar outra conexão.
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="border border-zinc-800 bg-black/35 p-4">
          <div className="grid gap-4 md:grid-cols-2">
            <ToggleControl label="Canal raiz" value={draft.enabled} onChange={(value) => updateDraft("enabled", value)} />
            <ToggleControl label="Mock explícito" value={draft.mockMode} onChange={(value) => updateDraft("mockMode", value)} />
            <label className="grid gap-2 text-xs uppercase tracking-[0.14em] text-zinc-500">
              Provider
              <select value={draft.provider} onChange={(event) => updateDraft("provider", event.target.value as EvolutionConfigDraft["provider"])} className="h-11 border border-zinc-800 bg-black/60 px-3 text-sm normal-case tracking-normal text-zinc-100 outline-none focus:border-orange-400">
                <option value="mock">mock</option>
                <option value="evolution">evolution</option>
                <option value="meta_cloud_future">meta_cloud_future</option>
              </select>
            </label>
            <TextControl label="Número mestre do Vulcan" value={draft.rootNumber} onChange={(value) => updateDraft("rootNumber", value)} placeholder="5541999999999" />
            <TextControl label="Nome do canal" value={draft.rootName} onChange={(value) => updateDraft("rootName", value)} placeholder="Vulcan Notifications" />
            <TextControl label="URL Evolution" value={draft.baseUrl} onChange={(value) => updateDraft("baseUrl", value)} placeholder="http://127.0.0.1:8080" />
            <TextControl label="Instância" value={draft.instanceName} onChange={(value) => updateDraft("instanceName", value)} placeholder="vulcan-root" />
            <TextControl label="API key Evolution" value={draft.apiKey} onChange={(value) => updateDraft("apiKey", value)} placeholder={status?.apiKeyConfigured ? "******** configurada" : "cole a chave"} type="password" />
            <ToggleControl label="Exigir opt-in" value={draft.requireOptIn} onChange={(value) => updateDraft("requireOptIn", value)} />
            <ToggleControl label="Fallback e-mail" value={draft.emailFallbackEnabled} onChange={(value) => updateDraft("emailFallbackEnabled", value)} />
            <ToggleControl label="Fallback in-app" value={draft.inAppFallbackEnabled} onChange={(value) => updateDraft("inAppFallbackEnabled", value)} />
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <button type="button" onClick={() => void saveConfig()} disabled={Boolean(busy)} className="inline-flex h-10 items-center gap-2 bg-orange-500 px-4 text-sm font-semibold text-black transition hover:bg-orange-400 disabled:opacity-40">
              <Save className="h-4 w-4" />
              Salvar
            </button>
            <button type="button" onClick={() => void runEvolutionAction("test", "Conexão", "/integrations/whatsapp/evolution/test", { method: "POST" })} disabled={Boolean(busy)} className="h-10 border border-orange-400/25 px-4 text-sm text-orange-200 transition hover:border-orange-300/60 disabled:opacity-40">Testar conexão</button>
            <button type="button" onClick={() => void runEvolutionAction("qr", "QR Code", "/integrations/whatsapp/evolution/qr")} disabled={Boolean(busy)} className="h-10 border border-zinc-800 px-4 text-sm text-zinc-200 transition hover:border-orange-400/50 disabled:opacity-40">Ver QR</button>
            <button type="button" onClick={() => void runEvolutionAction("reconnect", "Reconectar", "/integrations/whatsapp/evolution/reconnect", { method: "POST" })} disabled={Boolean(busy)} className="h-10 border border-zinc-800 px-4 text-sm text-zinc-200 transition hover:border-orange-400/50 disabled:opacity-40">Reconectar</button>
          </div>
        </div>

        <div className="grid gap-4">
          <div className="border border-zinc-800 bg-black/35 p-4">
            <div className="grid gap-3 md:grid-cols-2">
              <TextControl label="Destino teste" value={draft.testDestination} onChange={(value) => updateDraft("testDestination", value)} placeholder="5541999999999" />
              <TextControl label="Mensagem teste" value={draft.testMessage} onChange={(value) => updateDraft("testMessage", value)} placeholder="Teste Vulcan" />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button type="button" onClick={() => void sendTest()} disabled={Boolean(busy) || !draft.testDestination.trim()} className="h-10 bg-orange-500 px-4 text-sm font-semibold text-black transition hover:bg-orange-400 disabled:opacity-40">Enviar teste</button>
              <button type="button" onClick={() => void processQueue()} disabled={Boolean(busy)} className="h-10 border border-orange-400/25 px-4 text-sm text-orange-200 transition hover:border-orange-300/60 disabled:opacity-40">Processar fila</button>
              <button type="button" onClick={() => void refreshAll()} disabled={Boolean(busy)} className="h-10 border border-zinc-800 px-4 text-sm text-zinc-200 transition hover:border-orange-400/50 disabled:opacity-40">Atualizar</button>
            </div>
          </div>

          <div className="border border-zinc-800 bg-black/35 p-4">
            <div className="grid gap-3 md:grid-cols-3">
              <ConnectionSummary label="Serviço" value={status?.serviceReachable ? "alcançável" : "pendente"} tone={status?.serviceReachable ? "ok" : "warn"} />
              <ConnectionSummary label="Instância" value={status?.instanceName || draft.instanceName || "pendente"} tone={connected ? "ok" : "warn"} />
              <ConnectionSummary label="Falhas recentes" value={`${latestFailures.length}`} tone={latestFailures.length ? "warn" : "ok"} />
            </div>
          </div>
        </div>
      </div>

      {canShowQr ? (
        <div className="mt-4 border border-orange-400/20 bg-orange-950/10 p-4">
          <p className="text-sm font-semibold text-orange-100">QR Code de conexão</p>
          <div className="mt-3">{renderQrCode(qrCode)}</div>
        </div>
      ) : null}

      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <div className="border border-zinc-800 bg-black/35 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <p className="font-semibold text-zinc-100">Fila WhatsApp</p>
            <span className="text-xs text-zinc-500">{queue.length} item(ns)</span>
          </div>
          <div className="grid max-h-80 gap-2 overflow-y-auto pr-1">
            {queue.length ? queue.map((item) => (
              <div key={item.id} className="border border-zinc-800 bg-zinc-950/55 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-zinc-100">{item.title}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.12em] text-zinc-500">{maskPhone(item.destination)} | {statusPt(item.status)} | {item.attempts}/{item.maxAttempts}</p>
                  </div>
                  <button type="button" onClick={() => void retryQueueItem(item.id)} disabled={Boolean(busy)} className="border border-orange-400/25 px-3 py-2 text-xs text-orange-200 transition hover:border-orange-300/60 disabled:opacity-40">Reabrir</button>
                </div>
                {item.lastError ? <p className="mt-2 text-xs leading-5 text-orange-200">{item.lastError}</p> : null}
              </div>
            )) : <EmptyState title="Fila vazia" description="Novos envios do canal raiz aparecerão aqui com status e tentativas." />}
          </div>
        </div>

        <div className="border border-zinc-800 bg-black/35 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <p className="font-semibold text-zinc-100">Logs e auditoria</p>
            <span className="text-xs text-zinc-500">{logs.length} registro(s)</span>
          </div>
          <div className="grid max-h-80 gap-2 overflow-y-auto pr-1">
            {logs.length ? logs.map((item) => (
              <div key={item.id} className="border border-zinc-800 bg-zinc-950/55 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="text-sm font-semibold text-zinc-100">{statusPt(item.status)}</p>
                  <span className="text-xs text-zinc-500">{formatDateTime(item.createdAt)}</span>
                </div>
                <p className="mt-1 text-xs uppercase tracking-[0.12em] text-zinc-500">{item.provider || "provider"} | {item.destination ? maskPhone(item.destination) : "sem destino"}</p>
                {item.error ? <p className="mt-2 text-xs leading-5 text-orange-200">{item.error}</p> : null}
              </div>
            )) : <EmptyState title="Sem logs recentes" description="Tentativas de envio e webhooks da Evolution aparecerão neste histórico." />}
          </div>
        </div>
      </div>

      {status?.logs?.length ? (
        <div className="mt-4 border border-zinc-800 bg-black/35 p-4">
          <p className="mb-2 font-semibold text-zinc-100">Diagnóstico do provider</p>
          <div className="grid gap-2">
            {status.logs.map((line) => <p key={line} className="text-sm leading-6 text-zinc-500">{line}</p>)}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function evolutionDraftFromStatus(status: EvolutionStatus | null, fallback: WhatsAppStatus): EvolutionConfigDraft {
  const provider = status?.provider === "mock" || status?.provider === "meta_cloud_future" || status?.provider === "evolution"
    ? status.provider
    : fallback.provider === "mock"
      ? "mock"
      : "evolution";
  return {
    enabled: fallback.rootChannelEnabled || Boolean(status && status.status !== "disabled"),
    provider,
    rootNumber: status?.rootNumber ?? fallback.rootChannelNumber ?? "",
    rootName: status?.rootName ?? fallback.rootChannelName ?? "Vulcan Notifications",
    baseUrl: status?.baseUrl ?? "http://127.0.0.1:8080",
    apiKey: "",
    instanceName: status?.instanceName ?? "vulcan-root",
    mockMode: status?.mockMode ?? fallback.status === "mock",
    requireOptIn: status?.requireOptIn ?? true,
    emailFallbackEnabled: status?.emailFallbackEnabled ?? true,
    inAppFallbackEnabled: status?.inAppFallbackEnabled ?? true,
    testDestination: status?.rootNumber ?? fallback.rootChannelNumber ?? "",
    testMessage: "Teste do Canal WhatsApp Raiz do Vulcan."
  };
}

function ToggleControl({ label, value, onChange }: { label: string; value: boolean; onChange: (value: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className={`h-11 border px-3 text-left text-sm transition ${value ? "border-emerald-400/30 text-emerald-200" : "border-zinc-700 text-zinc-400"}`}
    >
      {label}: {value ? "ativo" : "inativo"}
    </button>
  );
}

function TextControl({ label, value, onChange, placeholder, type = "text" }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string; type?: string }) {
  return (
    <label className="grid gap-2 text-xs uppercase tracking-[0.14em] text-zinc-500">
      {label}
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        className="h-11 min-w-0 border border-zinc-800 bg-black/60 px-3 text-sm normal-case tracking-normal text-zinc-100 outline-none placeholder:text-zinc-600 focus:border-orange-400"
      />
    </label>
  );
}

function renderQrCode(value: string | null) {
  if (!value) return null;
  const trimmed = value.trim();
  const imageSrc = trimmed.startsWith("data:image") ? trimmed : /^[A-Za-z0-9+/=]{120,}$/.test(trimmed) ? `data:image/png;base64,${trimmed}` : null;
  if (imageSrc) {
    return <Image unoptimized src={imageSrc} alt="QR Code WhatsApp Evolution" width={220} height={220} className="border border-zinc-800 bg-white p-2" />;
  }
  return <pre className="max-h-64 overflow-auto whitespace-pre-wrap border border-zinc-800 bg-black/60 p-3 text-xs leading-5 text-zinc-300">{trimmed}</pre>;
}

function maskPhone(value: string | null | undefined) {
  const digits = String(value ?? "").replace(/\D/g, "");
  if (digits.length <= 4) return digits || "sem telefone";
  return `${digits.slice(0, 4)}*****${digits.slice(-4)}`;
}

function ConnectionSummary({ label, value, tone }: { label: string; value: string; tone: "ok" | "warn" }) {
  return (
    <Tremor.Card className="rounded-lg border border-zinc-800 bg-zinc-950/55 p-4 shadow-none">
      <Tremor.Text className="text-xs uppercase tracking-[0.16em] text-zinc-500">{label}</Tremor.Text>
      <div className="mt-2 flex items-center justify-between gap-2">
        <p className="truncate text-sm font-medium text-zinc-100">{value}</p>
        <Tremor.Badge color={tone === "ok" ? "emerald" : "orange"} size="xs">{tone === "ok" ? "ok" : "atenção"}</Tremor.Badge>
      </div>
    </Tremor.Card>
  );
}

function SettingsFieldControl({
  field,
  value,
  onChange
}: {
  field: SettingsField;
  value: string | number | boolean | null | undefined;
  onChange: (value: string | number | boolean | null) => void;
}) {
  const disabled = !field.editable || field.valueType === "readonly" || field.valueType === "secret";
  const statusColor = field.status === "ok" ? "emerald" : field.status === "error" ? "rose" : field.status === "missing" ? "orange" : "zinc";
  return (
    <motion.div
      className={`border p-4 ${disabled ? "border-zinc-800 bg-black/30" : "border-zinc-800 bg-black/45"}`}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: disabled ? 0 : -2 }}
    >
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-zinc-100">{field.label}</p>
          <p className="mt-1 text-sm leading-6 text-zinc-500">{field.description}</p>
        </div>
        <Tremor.Badge color={statusColor} size="xs">{settingsStatusPt(field.status)}</Tremor.Badge>
      </div>

      {field.valueType === "boolean" ? (
        <button
          type="button"
          disabled={disabled}
          onClick={() => onChange(!Boolean(value))}
          className={`inline-flex h-10 items-center gap-3 border px-3 text-sm transition disabled:cursor-not-allowed disabled:opacity-55 ${Boolean(value) ? "border-emerald-400/30 text-emerald-200" : "border-zinc-700 text-zinc-400"}`}
        >
          <span className={`h-3 w-3 ${Boolean(value) ? "bg-emerald-300" : "bg-zinc-600"}`} />
          {Boolean(value) ? "Ativo" : "Inativo"}
        </button>
      ) : field.valueType === "select" ? (
        <select
          disabled={disabled}
          value={String(value ?? "")}
          onChange={(event) => onChange(event.target.value)}
          className="h-11 w-full border border-zinc-800 bg-black/55 px-3 text-sm text-zinc-100 outline-none transition focus:border-orange-400/55 disabled:cursor-not-allowed disabled:opacity-55"
        >
          {field.options.map((option) => <option key={option} value={option}>{option}</option>)}
        </select>
      ) : field.valueType === "number" ? (
        <div className="flex items-center gap-2">
          <input
            disabled={disabled}
            type="number"
            value={value === null || value === undefined ? "" : Number(value)}
            onChange={(event) => onChange(event.target.value === "" ? null : Number(event.target.value))}
            className="h-11 min-w-0 flex-1 border border-zinc-800 bg-black/55 px-3 text-sm text-zinc-100 outline-none transition focus:border-orange-400/55 disabled:cursor-not-allowed disabled:opacity-55"
          />
          {field.unit ? <span className="border border-zinc-800 px-3 py-3 text-xs text-zinc-500">{field.unit}</span> : null}
        </div>
      ) : field.valueType === "secret" ? (
        <div className="border border-dashed border-orange-400/25 bg-orange-950/10 p-3">
          <p className="text-sm text-orange-100">{String(value ?? "requer credencial")}</p>
          <p className="mt-1 text-xs text-zinc-500">Secret protegido: configure por `.env` ou cofre seguro. O valor real nunca volta para o navegador.</p>
        </div>
      ) : field.valueType === "readonly" ? (
        <div className="border border-zinc-800 bg-zinc-950/60 p-3 text-sm text-zinc-200">{String(value ?? "não informado")}</div>
      ) : (
        <input
          disabled={disabled}
          value={String(value ?? "")}
          placeholder={field.placeholder ?? undefined}
          onChange={(event) => onChange(event.target.value)}
          className="h-11 w-full border border-zinc-800 bg-black/55 px-3 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-orange-400/55 disabled:cursor-not-allowed disabled:opacity-55"
        />
      )}

      {field.required ? <p className="mt-2 text-xs text-zinc-600">Obrigatório para produção/piloto.</p> : null}
    </motion.div>
  );
}

function settingsStatusPt(status: string) {
  const map: Record<string, string> = {
    ok: "OK",
    attention: "atenção",
    missing: "requer credencial",
    error: "erro",
    mock: "mock explícito",
    readonly: "somente leitura",
    disabled: "desativado"
  };
  return map[status] ?? status;
}

function settingsToneColor(status: string): "emerald" | "orange" | "rose" | "zinc" {
  if (status === "ok") return "emerald";
  if (status === "error") return "rose";
  if (status === "missing" || status === "attention" || status === "mock") return "orange";
  return "zinc";
}

function settingsIcon(sectionId: string): typeof Gauge {
  const map: Record<string, typeof Gauge> = {
    company: Building2,
    agents: RadioTower,
    collection: ShieldCheck,
    metrics: Gauge,
    ai: Brain,
    notifications: BellRing,
    whatsapp: MessageCircle,
    email: Mail,
    security: Lock,
    privacy: ShieldCheck,
    appearance: Layers3
  };
  return map[sectionId] ?? Layers3;
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
  const numeric = metric.value.match(/^\d+$/) ? Number(metric.value) : null;
  const progressValue = metric.tone === "positive" ? 82 : metric.tone === "warning" ? 58 : metric.tone === "critical" ? 36 : 68;
  const badgeColor = metric.tone === "positive" ? "emerald" : metric.tone === "warning" ? "orange" : metric.tone === "critical" ? "rose" : "zinc";
  return (
    <motion.div
      initial={{ y: 28, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ delay: index * 0.07 }}
      whileHover={{ y: -5 }}
    >
      <Tremor.Card className="h-full rounded-lg border border-zinc-800 bg-zinc-950/80 p-5 shadow-tremor-card transition hover:border-orange-400/40">
        <Tremor.Flex alignItems="start">
          <div>
            <Tremor.Text className="text-zinc-500">{metric.label}</Tremor.Text>
            <Tremor.Metric className="mt-2 text-zinc-50">
              {numeric === null ? metric.value : <CountUp end={numeric} duration={0.8} separator="." />}
            </Tremor.Metric>
          </div>
          <Tremor.Badge color={badgeColor} size="xs">{metric.tone === "positive" ? "bom" : metric.tone === "warning" ? "atenção" : metric.tone === "critical" ? "crítico" : "neutro"}</Tremor.Badge>
        </Tremor.Flex>
        <Tremor.ProgressBar className="mt-5" value={progressValue} color={badgeColor} />
        <Tremor.Text className="mt-3 text-orange-200">{metric.trend}</Tremor.Text>
      </Tremor.Card>
    </motion.div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <motion.div
      className="grid min-h-44 place-items-center rounded-lg border border-dashed border-zinc-800 bg-zinc-950/55 p-6 text-center"
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.28 }}
    >
      <div>
        <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-lg border border-orange-400/20 bg-orange-500/10 text-orange-300">
          <RadioTower className="h-5 w-5" />
        </div>
        <p className="font-semibold text-zinc-100">{title}</p>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-zinc-500">{description}</p>
      </div>
    </motion.div>
  );
}

function Panel({ title, icon: Icon, children }: { title: string; icon: typeof Gauge; children: ReactNode }) {
  return (
    <motion.section
      className="relative"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45 }}
      whileHover={{ y: -2 }}
    >
      <Tremor.Card className="relative overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950/82 p-5 shadow-tremor-card backdrop-blur-md">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-orange-300/70 to-transparent" />
        <div className="relative z-10 mb-5 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-lg bg-orange-500 text-black shadow-[0_10px_30px_rgba(249,115,22,0.16)]">
              <Icon className="h-5 w-5" />
            </div>
            <Tremor.Title className="text-zinc-50">{title}</Tremor.Title>
          </div>
        </div>
        <div className="relative z-10">{children}</div>
      </Tremor.Card>
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
