"use client";

import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clipboard,
  Clock3,
  Download,
  FileClock,
  HardDrive,
  KeyRound,
  Laptop,
  LoaderCircle,
  Network,
  RefreshCw,
  Server,
  Settings2,
  ShieldCheck,
  TerminalSquare,
  Unplug,
  UsersRound
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { usePathState } from "@/lib/url-state";

type AgentProfile = "workstation" | "server" | "collector";
type AgentPlatform = "windows" | "linux";
type AgentSection =
  | "all"
  | "workstations"
  | "servers"
  | "collectors"
  | "pending"
  | "offline"
  | "updates"
  | "policies"
  | "installation"
  | "deployments"
  | "diagnostics"
  | "events"
  | "audit";

type ManagedAgent = {
  id: string;
  tenantId: string;
  deviceId: string;
  hostname: string;
  profile: AgentProfile;
  operatingSystem: string;
  architecture: string | null;
  agentVersion: string | null;
  status: string;
  policyRevision: number;
  policyStatus: string;
  queueDepth: number;
  lastSeenAt: string | null;
  lastIp: string | null;
  siteId: string | null;
  siteName: string | null;
  owner: string | null;
  department: string | null;
  modules: Record<string, string>;
  lastError: string | null;
  createdAt: string;
};

type AgentPolicy = {
  id: string;
  tenantId: string;
  name: string;
  profile: AgentProfile;
  scopeType: string;
  revision: number;
  schemaVersion: string;
  document: Record<string, unknown>;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
};

type EnrollmentToken = {
  id: string;
  token: string;
  tokenPrefix: string;
  profile: AgentProfile;
  expiresAt: string;
  maxUses: number;
  warning: string;
};

type TimelineEvent = {
  eventId: string;
  agentId: string | null;
  eventType: string;
  category: string;
  severity: string;
  occurredAt: string;
  message: string;
  source: string;
  dataOrigin: "real" | "simulated" | "imported";
};

type AuditEntry = {
  id: string;
  action: string;
  resourceType?: string | null;
  resourceId?: string | null;
  metadata?: Record<string, unknown>;
  createdAt: string;
};

type Props = {
  apiUrl: string;
  tenantId: string;
  token: string;
};

const navigation: { key: AgentSection; label: string; icon: typeof Activity }[] = [
  { key: "all", label: "Todos", icon: UsersRound },
  { key: "workstations", label: "Estações", icon: Laptop },
  { key: "servers", label: "Servidores", icon: Server },
  { key: "collectors", label: "Coletores", icon: Network },
  { key: "pending", label: "Pendentes", icon: Clock3 },
  { key: "offline", label: "Offline", icon: Unplug },
  { key: "updates", label: "Atualizações", icon: Download },
  { key: "policies", label: "Políticas", icon: Settings2 },
  { key: "installation", label: "Instalação", icon: TerminalSquare },
  { key: "deployments", label: "Instalação em massa", icon: Network },
  { key: "diagnostics", label: "Diagnóstico", icon: HardDrive },
  { key: "events", label: "Eventos", icon: Activity },
  { key: "audit", label: "Auditoria", icon: FileClock }
];
const agentSections = navigation.map((item) => item.key);
const agentRoutes: Readonly<Record<AgentSection, string>> = {
  all: "/agents",
  workstations: "/agents/workstations",
  servers: "/agents/servers",
  collectors: "/agents/collectors",
  pending: "/agents/pending",
  offline: "/agents/offline",
  updates: "/agents/updates",
  policies: "/agents/policies",
  installation: "/agents/installation",
  deployments: "/agents/deployments",
  diagnostics: "/agents/diagnostics",
  events: "/agents/events",
  audit: "/agents/audit"
};

async function fetchJson<T>(
  apiUrl: string,
  path: string,
  token: string,
  tenantId: string,
  init?: RequestInit
): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      "X-Tenant-Id": tenantId,
      "Content-Type": "application/json",
      ...init?.headers
    }
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    throw new Error(String(problem.detail ?? `HTTP ${response.status}`));
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function relativeTime(value: string | null) {
  if (!value) return "nunca comunicou";
  const seconds = Math.max(0, Math.round((Date.now() - Date.parse(value)) / 1000));
  if (seconds < 60) return `há ${seconds}s`;
  if (seconds < 3600) return `há ${Math.round(seconds / 60)}min`;
  if (seconds < 86400) return `há ${Math.round(seconds / 3600)}h`;
  return `há ${Math.round(seconds / 86400)}d`;
}

function statusTone(status: string) {
  if (["online", "approved", "applied", "enabled"].includes(status)) return "border-emerald-400/30 bg-emerald-400/10 text-emerald-200";
  if (["pending", "syncing", "degraded"].includes(status)) return "border-amber-400/30 bg-amber-400/10 text-amber-200";
  return "border-red-400/30 bg-red-400/10 text-red-200";
}

function profileLabel(profile: AgentProfile) {
  if (profile === "workstation") return "Estação";
  if (profile === "server") return "Servidor";
  return "Coletor";
}

function AgentRow({ agent }: { agent: ManagedAgent }) {
  const enabledModules = Object.values(agent.modules).filter((value) => value === "enabled").length;
  return (
    <article className="grid gap-4 border border-zinc-800 bg-black/35 p-4 transition hover:border-orange-400/35 lg:grid-cols-[minmax(15rem,1.2fr)_repeat(4,minmax(8rem,0.65fr))] lg:items-center">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="truncate font-semibold text-zinc-100">{agent.hostname}</h3>
          <span className={`border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] ${statusTone(agent.status)}`}>
            {agent.status}
          </span>
        </div>
        <p className="mt-2 truncate text-xs text-zinc-500">{agent.operatingSystem}</p>
        <p className="mt-1 text-xs text-zinc-600">{agent.owner ?? "Sem responsável"} · {agent.department ?? "Sem setor"}</p>
      </div>
      <AgentDatum label="Perfil" value={profileLabel(agent.profile)} />
      <AgentDatum label="Versão" value={agent.agentVersion ?? "não informada"} />
      <AgentDatum label="Última comunicação" value={relativeTime(agent.lastSeenAt)} />
      <div>
        <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-600">Saúde</p>
        <p className="mt-1 text-sm text-zinc-300">{enabledModules} módulos · fila {agent.queueDepth}</p>
        {agent.lastError ? <p className="mt-1 line-clamp-2 text-xs text-red-300">{agent.lastError}</p> : null}
      </div>
    </article>
  );
}

function AgentDatum({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-600">{label}</p>
      <p className="mt-1 truncate text-sm text-zinc-300">{value}</p>
    </div>
  );
}

export function AgentsManagement({ apiUrl, tenantId, token }: Props) {
  const [section, setSection] = usePathState<AgentSection>(
    agentRoutes,
    "all",
    "agent",
    agentSections
  );
  const [agents, setAgents] = useState<ManagedAgent[]>([]);
  const [policies, setPolicies] = useState<AgentPolicy[]>([]);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [agentRows, policyRows, timeline, auditRows] = await Promise.all([
        fetchJson<ManagedAgent[]>(apiUrl, "/agent/v2/admin/agents", token, tenantId),
        fetchJson<AgentPolicy[]>(apiUrl, "/agent/v2/admin/policies", token, tenantId),
        fetchJson<{ items: TimelineEvent[] }>(apiUrl, "/timeline?source=vulcan-agent&limit=50", token, tenantId),
        fetchJson<AuditEntry[]>(apiUrl, "/audit-logs", token, tenantId)
      ]);
      setAgents(agentRows);
      setPolicies(policyRows);
      setEvents(timeline.items);
      setAudit(auditRows.filter((entry) => entry.action.startsWith("agent.")));
      setLastRefresh(new Date());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível carregar os agentes.");
    } finally {
      setLoading(false);
    }
  }, [apiUrl, tenantId, token]);

  useEffect(() => {
    void load();
    const interval = window.setInterval(() => void load(), 30_000);
    return () => window.clearInterval(interval);
  }, [load]);

  const visibleAgents = useMemo(() => {
    if (section === "workstations") return agents.filter((agent) => agent.profile === "workstation");
    if (section === "servers") return agents.filter((agent) => agent.profile === "server");
    if (section === "collectors") return agents.filter((agent) => agent.profile === "collector");
    if (section === "pending") return agents.filter((agent) => agent.status === "pending");
    if (section === "offline") return agents.filter((agent) => agent.status === "offline" || agent.status === "revoked");
    return agents;
  }, [agents, section]);

  const online = agents.filter((agent) => agent.status === "online").length;
  const pending = agents.filter((agent) => agent.status === "pending").length;
  const queueDepth = agents.reduce((total, agent) => total + agent.queueDepth, 0);

  return (
    <section className="grid gap-5 xl:grid-cols-[15rem_minmax(0,1fr)]">
      <aside className="border border-zinc-800 bg-black/35 p-3">
        <div className="mb-4 border-b border-zinc-800 px-2 pb-4">
          <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-orange-300">Vulcan Agent</p>
          <p className="mt-2 text-xs leading-5 text-zinc-500">Estações, servidores e coletores sob a mesma política.</p>
        </div>
        <nav className="grid grid-cols-2 gap-1 sm:grid-cols-3 xl:grid-cols-1">
          {navigation.map((item) => {
            const Icon = item.icon;
            const active = item.key === section;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => setSection(item.key)}
                className={`flex items-center gap-2 border px-3 py-2 text-left text-xs transition ${
                  active
                    ? "border-orange-400/45 bg-orange-400/10 text-orange-200"
                    : "border-transparent text-zinc-500 hover:border-zinc-800 hover:text-zinc-200"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {item.label}
              </button>
            );
          })}
        </nav>
      </aside>

      <div className="min-w-0 space-y-5">
        <header className="border border-zinc-800 bg-zinc-950/55 p-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-orange-300">Inteligência no endpoint</p>
              <h1 className="mt-2 text-2xl font-semibold md:text-3xl">Agentes</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-500">
                Inventário, saúde e contexto operacional governados pelo tenant. Sem shell remoto, captura de teclas, tela, câmera ou microfone.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void load()}
              disabled={loading}
              className="flex items-center gap-2 border border-zinc-700 px-3 py-2 text-xs text-zinc-300 transition hover:border-orange-400/50 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Atualizar
            </button>
          </div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Summary label="Agentes" value={String(agents.length)} detail="identidades v2" />
            <Summary label="Online" value={String(online)} detail="comunicação atual" tone="ok" />
            <Summary label="Pendentes" value={String(pending)} detail="aguardando aprovação" tone={pending ? "warn" : "default"} />
            <Summary label="Fila total" value={String(queueDepth)} detail="eventos informados" tone={queueDepth ? "warn" : "default"} />
          </div>
          {lastRefresh ? <p className="mt-3 text-right text-[10px] text-zinc-700">Atualizado {relativeTime(lastRefresh.toISOString())}</p> : null}
        </header>

        {error ? (
          <div className="flex items-start gap-3 border border-red-400/30 bg-red-400/5 p-4 text-sm text-red-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div><p className="font-medium">A área de agentes não está disponível.</p><p className="mt-1 text-red-300/70">{error}</p></div>
          </div>
        ) : null}

        {loading && !agents.length ? (
          <div className="grid min-h-64 place-items-center border border-zinc-800 bg-black/30">
            <div className="text-center text-sm text-zinc-500"><LoaderCircle className="mx-auto mb-3 h-6 w-6 animate-spin text-orange-300" />Carregando agentes reais...</div>
          </div>
        ) : null}

        {!loading && ["all", "workstations", "servers", "collectors", "pending", "offline"].includes(section) ? (
          <AgentList agents={visibleAgents} section={section} />
        ) : null}
        {section === "updates" ? <UpdatesView agents={agents} /> : null}
        {section === "policies" ? (
          <PoliciesView apiUrl={apiUrl} tenantId={tenantId} token={token} policies={policies} onCreated={load} />
        ) : null}
        {["installation", "deployments"].includes(section) ? (
          <InstallationView apiUrl={apiUrl} tenantId={tenantId} token={token} />
        ) : null}
        {section === "diagnostics" ? <DiagnosticsView agents={agents} /> : null}
        {section === "events" ? <EventsView events={events} /> : null}
        {section === "audit" ? <AuditView audit={audit} /> : null}
      </div>
    </section>
  );
}

function Summary({ label, value, detail, tone = "default" }: { label: string; value: string; detail: string; tone?: "default" | "ok" | "warn" }) {
  return (
    <div className="border border-zinc-800 bg-black/35 p-3">
      <p className="text-[10px] uppercase tracking-[0.2em] text-zinc-600">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${tone === "ok" ? "text-emerald-300" : tone === "warn" ? "text-amber-300" : "text-zinc-100"}`}>{value}</p>
      <p className="mt-1 text-xs text-zinc-600">{detail}</p>
    </div>
  );
}

function AgentList({ agents, section }: { agents: ManagedAgent[]; section: AgentSection }) {
  if (!agents.length) {
    return (
      <div className="grid min-h-64 place-items-center border border-dashed border-zinc-800 bg-black/20 p-8 text-center">
        <div><CheckCircle2 className="mx-auto h-7 w-7 text-zinc-700" /><p className="mt-3 text-sm text-zinc-400">Nenhum agente em {navigation.find((item) => item.key === section)?.label.toLowerCase()}.</p><p className="mt-1 text-xs text-zinc-600">Use Instalação para gerar um token efêmero.</p></div>
      </div>
    );
  }
  return <div className="space-y-2">{agents.map((agent) => <AgentRow key={agent.id} agent={agent} />)}</div>;
}

function UpdatesView({ agents }: { agents: ManagedAgent[] }) {
  const versions = [...new Set(agents.map((agent) => agent.agentVersion).filter(Boolean))];
  return (
    <div className="border border-zinc-800 bg-black/30 p-5">
      <h2 className="text-lg font-semibold">Atualizações</h2>
      <p className="mt-2 text-sm text-zinc-500">O servidor registra versões e canais, mas rollout automático permanece bloqueado até assinatura de release ser configurada.</p>
      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <Summary label="Versões em uso" value={String(versions.length)} detail={versions.join(", ") || "nenhum agente v2"} />
        <Summary label="Rollout automático" value="Desativado" detail="exige manifesto e binário assinados" />
      </div>
    </div>
  );
}

function PoliciesView({ apiUrl, tenantId, token, policies, onCreated }: Props & { policies: AgentPolicy[]; onCreated: () => Promise<void> }) {
  const [profile, setProfile] = useState<AgentProfile>("workstation");
  const [name, setName] = useState("Política padrão");
  const [objectives, setObjectives] = useState({
    activity: true,
    health: true,
    inventory: true,
    network: true,
    printing: false,
    serverChecks: false,
    discovery: false
  });
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  useEffect(() => {
    setObjectives((current) => ({
      ...current,
      activity: profile === "workstation",
      serverChecks: profile === "server",
      discovery: profile === "collector"
    }));
  }, [profile]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setFeedback(null);
    try {
      await fetchJson(apiUrl, "/agent/v2/admin/policies", token, tenantId, {
        method: "POST",
        body: JSON.stringify({
          tenantId,
          name,
          profile,
          scopeType: "tenant",
          enabled: true,
          document: {
            schemaVersion: "v1",
            profile,
            modules: {
              selfHealth: { enabled: objectives.health },
              systemMetrics: { enabled: objectives.health },
              inventory: { enabled: objectives.inventory, diffOnly: true },
              network: { enabled: objectives.network, activeTests: false },
              activity: { enabled: profile === "workstation" && objectives.activity, windowTitles: false },
              printing: { enabled: objectives.printing, documentNames: false },
              serverChecks: { enabled: profile === "server" && objectives.serverChecks, checks: [] },
              discovery: {
                enabled: profile === "collector" && objectives.discovery,
                readOnly: true,
                allowedNetworks: [],
                deniedNetworks: [],
                portScan: false,
                targets: []
              },
              visual: { screenCapture: false, liveSupport: false, privacyGuard: true }
            },
            privacy: { collectTypedContent: false, collectClipboard: false, collectCredentials: false, windowTitles: false },
            allowedCommands: ["request_inventory", "request_diagnostics", "refresh_policy", "restart_agent"]
          }
        })
      });
      setFeedback("Política criada. Os agentes receberão a revisão no próximo heartbeat.");
      await onCreated();
    } catch (reason) {
      setFeedback(reason instanceof Error ? reason.message : "Não foi possível criar a política.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1.15fr]">
      <form onSubmit={submit} className="border border-zinc-800 bg-black/30 p-5">
        <h2 className="text-lg font-semibold">Nova política</h2>
        <p className="mt-2 text-sm text-zinc-500">Escolha objetivos. Títulos de janela e módulos visuais permanecem desativados.</p>
        <label className="mt-5 block text-xs text-zinc-500">Nome<input value={name} onChange={(event) => setName(event.target.value)} className="mt-2 w-full border border-zinc-800 bg-black px-3 py-2 text-sm text-zinc-100 outline-none focus:border-orange-400/50" /></label>
        <label className="mt-4 block text-xs text-zinc-500">Perfil<select value={profile} onChange={(event) => setProfile(event.target.value as AgentProfile)} className="mt-2 w-full border border-zinc-800 bg-black px-3 py-2 text-sm text-zinc-100 outline-none"><option value="workstation">Workstation</option><option value="server">Server</option><option value="collector">Collector</option></select></label>
        <div className="mt-5 space-y-2">
          {Object.entries(objectives).map(([key, enabled]) => {
            const incompatible = (key === "activity" && profile !== "workstation") || (key === "serverChecks" && profile !== "server") || (key === "discovery" && profile !== "collector");
            return (
              <label key={key} className={`flex items-center justify-between border border-zinc-800 px-3 py-2 text-sm ${incompatible ? "opacity-35" : ""}`}>
                <span>{({ activity: "Acompanhar produtividade", health: "Monitorar saúde", inventory: "Coletar inventário", network: "Diagnosticar rede", printing: "Registrar impressões", serverChecks: "Monitorar serviços", discovery: "Descoberta somente leitura" } as Record<string, string>)[key]}</span>
                <input type="checkbox" checked={incompatible ? false : enabled} disabled={incompatible} onChange={(event) => setObjectives((current) => ({ ...current, [key]: event.target.checked }))} className="accent-orange-500" />
              </label>
            );
          })}
        </div>
        <button disabled={saving} className="mt-5 w-full bg-orange-500 px-4 py-3 text-sm font-semibold text-black transition hover:bg-orange-400 disabled:opacity-50">{saving ? "Salvando..." : "Criar política"}</button>
        {feedback ? <p className="mt-3 text-xs text-zinc-400">{feedback}</p> : null}
      </form>
      <div className="border border-zinc-800 bg-black/30 p-5">
        <h2 className="text-lg font-semibold">Revisões reais</h2>
        <div className="mt-4 space-y-2">
          {policies.length ? policies.map((item) => (
            <article key={item.id} className="border border-zinc-800 p-3">
              <div className="flex items-center justify-between gap-3"><p className="font-medium">{item.name}</p><span className="text-xs text-orange-300">r{item.revision}</span></div>
              <p className="mt-2 text-xs text-zinc-600">{profileLabel(item.profile)} · {item.scopeType} · {relativeTime(item.updatedAt)}</p>
            </article>
          )) : <p className="border border-dashed border-zinc-800 p-6 text-center text-sm text-zinc-600">Nenhuma política customizada. O agente usa defaults seguros assinados.</p>}
        </div>
      </div>
    </div>
  );
}

function InstallationView({ apiUrl, tenantId, token }: Props) {
  const [profile, setProfile] = useState<AgentProfile>("workstation");
  const [platform, setPlatform] = useState<AgentPlatform>("windows");
  const [creating, setCreating] = useState(false);
  const [enrollment, setEnrollment] = useState<EnrollmentToken | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [agentServerUrl, setAgentServerUrl] = useState(apiUrl);

  useEffect(() => {
    setAgentServerUrl(apiUrl.startsWith("/") ? new URL(apiUrl, window.location.origin).toString() : apiUrl);
  }, [apiUrl]);

  async function createToken() {
    setCreating(true);
    setError(null);
    setEnrollment(null);
    try {
      setEnrollment(await fetchJson<EnrollmentToken>(apiUrl, "/agent/v2/admin/enrollment-tokens", token, tenantId, {
        method: "POST",
        body: JSON.stringify({ tenantId, profile, approvalMode: "automatic", expiresInMinutes: 60, maxUses: 1 })
      }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível criar o token.");
    } finally {
      setCreating(false);
    }
  }

  function selectProfile(nextProfile: AgentProfile) {
    setProfile(nextProfile);
    setEnrollment(null);
    setError(null);
  }

  const privateHttp = agentServerUrl.startsWith("http://");
  const windowsInstallerUrl = agentServerUrl.startsWith("http")
    ? new URL("/agent-v2/VulcanAgent-Windows-x64.msi", agentServerUrl).toString()
    : "/agent-v2/VulcanAgent-Windows-x64.msi";
  const linuxInstallerUrl = agentServerUrl.startsWith("http")
    ? new URL("/agent-v2/vulcan-agent_amd64.deb", agentServerUrl).toString()
    : "/agent-v2/vulcan-agent_amd64.deb";
  const powershell = enrollment
    ? `& {
$ErrorActionPreference = 'Stop'
$Msi = Join-Path $env:TEMP 'VulcanAgent-Windows-x64.msi'
$Log = Join-Path $env:TEMP 'VulcanAgent-install.log'
$ExpectedHash = '27B29853FB01900594280CDC5F85406B847CCA15617BA0B2CDE8E98B3228D1F7'

$IsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $IsAdmin) { throw 'Abra o PowerShell como administrador e execute novamente.' }
if (Get-Service VulcanAgent -ErrorAction SilentlyContinue) { throw 'O Vulcan Agent ja esta instalado nesta maquina.' }

Invoke-WebRequest -UseBasicParsing -Uri '${windowsInstallerUrl}' -OutFile $Msi
if ((Get-FileHash $Msi -Algorithm SHA256).Hash -ne $ExpectedHash) {
  Remove-Item $Msi -Force -ErrorAction SilentlyContinue
  throw 'O instalador baixado nao passou na validacao SHA-256.'
}
Unblock-File $Msi

$Arguments = @(
  '/i', ('"' + $Msi + '"'), '/qn', '/norestart',
  'VULCAN_SERVER="${agentServerUrl}"',
  'ENROLLMENT_TOKEN="${enrollment.token}"',
  'AGENT_PROFILE="${profile}"',
  'ALLOW_INSECURE_PRIVATE_NETWORK=${privateHttp ? "true" : "false"}',
  '/l*v', ('"' + $Log + '"')
)
$Install = Start-Process -FilePath "$env:SystemRoot\\System32\\msiexec.exe" -ArgumentList $Arguments -Wait -PassThru
Remove-Item $Msi -Force -ErrorAction SilentlyContinue
if ($Install.ExitCode -notin @(0, 3010)) { throw "Falha na instalacao (codigo $($Install.ExitCode)). Log: $Log" }

Start-Sleep -Seconds 3
$Service = Get-Service VulcanAgent -ErrorAction Stop
$Agent = Join-Path $env:ProgramFiles 'Vulcan\\Agent\\VulcanAgent.exe'
& $Agent status
Write-Host "Vulcan Agent instalado. Servico: $($Service.Status). Codigo: $($Install.ExitCode)." -ForegroundColor Green
}`
    : "";
  const linux = enrollment
    ? `set -euo pipefail
pkg="$(mktemp --suffix=.deb)"
trap 'rm -f "$pkg"' EXIT
curl -fsSL '${linuxInstallerUrl}' -o "$pkg"
echo '9ffc36fc732ea8bd3436b46ebe8e6f5bf588c6e476fb460e7841e507b8bb2174  '"$pkg" | sha256sum -c -
sudo apt-get install -y "$pkg"
${profile === "workstation"
  ? `VULCAN_ENROLLMENT_TOKEN='${enrollment.token}' vulcan-agent enroll --server '${agentServerUrl}' --profile workstation${privateHttp ? " --allow-insecure-private-network" : ""}
systemctl --user enable --now vulcan-agent-user
systemctl --user status vulcan-agent-user --no-pager`
  : `sudo -u vulcan-agent env VULCAN_AGENT_CONFIG_DIR=/etc/vulcan-agent VULCAN_AGENT_DATA_DIR=/var/lib/vulcan-agent VULCAN_AGENT_LOG_DIR=/var/log/vulcan-agent VULCAN_ENROLLMENT_TOKEN='${enrollment.token}' /usr/bin/vulcan-agent enroll --server '${agentServerUrl}' --profile ${profile}${privateHttp ? " --allow-insecure-private-network" : ""}
sudo systemctl enable --now vulcan-agent
sudo systemctl status vulcan-agent --no-pager`}`
    : "";

  const profiles: Array<{ value: AgentProfile; label: string; description: string; icon: typeof Laptop }> = [
    { value: "workstation", label: "Estação", description: "Produtividade, atividade, saúde e inventário.", icon: Laptop },
    { value: "server", label: "Servidor", description: "Serviços, recursos e disponibilidade. Sem produtividade.", icon: Server },
    { value: "collector", label: "Coletor", description: "Descoberta e integrações de rede somente leitura.", icon: Network }
  ];

  return (
    <div className="border border-zinc-800 bg-black/30 p-5">
      <div className="max-w-3xl">
        <p className="text-[10px] uppercase tracking-[0.24em] text-orange-300">Instalar Vulcan Agent</p>
        <h2 className="mt-2 text-2xl font-semibold">Escolha, copie e instale</h2>
        <p className="mt-2 text-sm text-zinc-500">O comando baixa, valida, instala, remove o pacote temporário e confirma o serviço.</p>
        <ol className="mt-5 grid gap-2 text-sm text-zinc-400 sm:grid-cols-3">
          {["Escolha o sistema e o perfil", "Gere o comando de uso único", "Cole como administrador"].map((step, index) => <li key={step} className="border border-zinc-800 p-3"><span className="text-orange-300">{index + 1}.</span><br />{step}</li>)}
        </ol>
      </div>
      <div className="mt-6">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">Sistema</p>
        <div className="mt-2 inline-flex border border-zinc-800 bg-black p-1">
          {(["windows", "linux"] as AgentPlatform[]).map((item) => (
            <button key={item} type="button" aria-pressed={platform === item} onClick={() => setPlatform(item)} className={`px-4 py-2 text-sm font-medium transition ${platform === item ? "bg-orange-500 text-black" : "text-zinc-400 hover:text-white"}`}>
              {item === "windows" ? "Windows" : "Linux"}
            </button>
          ))}
        </div>
        <p className="mt-5 text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">Perfil</p>
        <div className="mt-2 grid gap-3 lg:grid-cols-3">
          {profiles.map((item) => {
            const Icon = item.icon;
            const selected = profile === item.value;
            return (
              <button key={item.value} type="button" aria-pressed={selected} onClick={() => selectProfile(item.value)} className={`flex items-start gap-3 border p-4 text-left transition ${selected ? "border-orange-400 bg-orange-400/10" : "border-zinc-800 bg-black/30 hover:border-zinc-700"}`}>
                <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${selected ? "text-orange-300" : "text-zinc-600"}`} />
                <span><span className="block text-sm font-semibold text-zinc-200">{item.label}</span><span className="mt-1 block text-xs leading-5 text-zinc-500">{item.description}</span></span>
              </button>
            );
          })}
        </div>
        <button onClick={() => void createToken()} disabled={creating} className="mt-5 flex w-full items-center justify-center gap-2 bg-orange-500 px-4 py-3 text-sm font-semibold text-black transition hover:bg-orange-400 disabled:opacity-50 sm:w-auto"><KeyRound className="h-4 w-4" />{creating ? "Gerando comando..." : `Gerar comando para ${profileLabel(profile)}`}</button>
      </div>
      <p className="mt-3 text-xs text-zinc-500">
        Endpoint entregue ao agente: <span className="text-zinc-300">{agentServerUrl}</span>
        {privateHttp ? " · HTTP privado autorizado no comando." : ""}
      </p>
      {error ? <p className="mt-4 text-sm text-red-300">{error}</p> : null}
      {enrollment ? (
        <div className="mt-6 space-y-4">
          <CommandBlock title={platform === "windows" ? "Windows · PowerShell como administrador" : "Linux · terminal"} command={platform === "windows" ? powershell : linux} />
          <div className="flex items-start gap-3 border border-amber-400/25 bg-amber-400/5 p-4 text-xs text-amber-100/75"><ShieldCheck className="h-4 w-4 shrink-0" /><p>{enrollment.warning} Expira {new Date(enrollment.expiresAt).toLocaleString("pt-BR")} e aceita {enrollment.maxUses} uso. Alterar o perfil descarta este comando para evitar cadastro incorreto.</p></div>
        </div>
      ) : null}
    </div>
  );
}

function CommandBlock({ title, command }: { title: string; command: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="border border-zinc-800 bg-zinc-950 p-4">
      <div className="flex items-center justify-between gap-3"><p className="text-xs font-semibold text-zinc-300">{title}</p><button type="button" onClick={() => { void navigator.clipboard.writeText(command); setCopied(true); }} className="flex items-center gap-1 text-xs text-orange-300"><Clipboard className="h-3.5 w-3.5" />{copied ? "Copiado" : "Copiar"}</button></div>
      <pre className="mt-3 overflow-x-auto whitespace-pre-wrap text-xs leading-5 text-zinc-500">{command}</pre>
    </div>
  );
}

function DiagnosticsView({ agents }: { agents: ManagedAgent[] }) {
  const attention = agents.filter((agent) => agent.lastError || agent.queueDepth > 0 || Object.values(agent.modules).some((value) => ["degraded", "invalid_policy"].includes(value)));
  return (
    <div className="border border-zinc-800 bg-black/30 p-5">
      <h2 className="text-lg font-semibold">Diagnóstico</h2>
      <p className="mt-2 text-sm text-zinc-500">Sinais enviados pelo próprio agente, sem segredo ou dump sensível.</p>
      <div className="mt-5 space-y-2">
        {attention.length ? attention.map((agent) => <AgentRow key={agent.id} agent={agent} />) : <p className="border border-dashed border-zinc-800 p-8 text-center text-sm text-zinc-600">Nenhum agente v2 reportou fila ou erro.</p>}
      </div>
    </div>
  );
}

function EventsView({ events }: { events: TimelineEvent[] }) {
  return (
    <div className="border border-zinc-800 bg-black/30 p-5">
      <h2 className="text-lg font-semibold">Eventos recentes</h2>
      <p className="mt-2 text-sm text-zinc-500">Mesmos eventos canônicos usados pela Vulcan Timeline.</p>
      <div className="mt-5 space-y-2">
        {events.length ? events.map((event) => (
          <article key={event.eventId} className="flex items-start gap-3 border border-zinc-800 p-3">
            <Activity className="mt-0.5 h-4 w-4 shrink-0 text-orange-300" />
            <div className="min-w-0"><p className="text-sm text-zinc-200">{event.message}</p><p className="mt-1 text-xs text-zinc-600">{event.eventType} · {event.category} · {relativeTime(event.occurredAt)} · {event.dataOrigin}</p></div>
          </article>
        )) : <p className="border border-dashed border-zinc-800 p-8 text-center text-sm text-zinc-600">Nenhum evento de agente recebido.</p>}
      </div>
    </div>
  );
}

function AuditView({ audit }: { audit: AuditEntry[] }) {
  return (
    <div className="border border-zinc-800 bg-black/30 p-5">
      <h2 className="text-lg font-semibold">Auditoria de agentes</h2>
      <p className="mt-2 text-sm text-zinc-500">Enrollment, política, ingestão, comando seguro e revogação.</p>
      <div className="mt-5 space-y-2">
        {audit.length ? audit.map((entry) => <article key={entry.id} className="border border-zinc-800 p-3"><p className="text-sm text-zinc-300">{entry.action}</p><p className="mt-1 text-xs text-zinc-600">{entry.resourceType ?? "agent"} · {relativeTime(entry.createdAt)}</p></article>) : <p className="border border-dashed border-zinc-800 p-8 text-center text-sm text-zinc-600">Nenhuma ação de agente no escopo visível.</p>}
      </div>
    </div>
  );
}
