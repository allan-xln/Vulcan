"use client";

import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Cpu,
  Gauge,
  LogOut,
  Maximize2,
  Network,
  RefreshCw,
  Server,
  ShieldCheck,
  Users
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";
const SESSION_KEY = "vulcan-wallboard-access-token";

type Metric = {
  id: string;
  label: string;
  value: string;
  trend: string;
  tone: "positive" | "warning" | "critical" | "neutral";
};

type OperationalIntelligence = {
  generatedAt: string;
  periodLabel: string;
  totalEvents: number;
  totalActiveSeconds: number;
  totalIdleSeconds: number;
  idleRate: number;
  focusScore: number;
  contextSwitches: number;
  currentActivity: string;
  aiSummary: string;
};

type InfrastructureOverview = {
  dataOrigin: "real" | "simulated";
  generatedAt: string;
  sites: number;
  networks: number;
  assets: number;
  onlineAssets: number;
  degradedAssets: number;
  offlineAssets: number;
  openIncidents: number;
  eventsLast24h: number;
  healthScore: number | null;
};

type ManagedAgent = {
  id: string;
  status: string;
  profile: "workstation" | "server" | "collector";
  lastSeenAt: string | null;
};

type Incident = {
  id: string;
  status: string;
  severity: string;
};

type WallboardData = {
  metrics: Metric[];
  intelligence: OperationalIntelligence;
  infrastructure: InfrastructureOverview;
  agents: ManagedAgent[];
  incidents: Incident[];
};

function formatDuration(seconds: number) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes.toString().padStart(2, "0")}min`;
}

function isOnlineAgent(agent: ManagedAgent) {
  if (!agent.lastSeenAt || !["online", "syncing"].includes(agent.status)) return false;
  return Date.now() - new Date(agent.lastSeenAt).getTime() <= 5 * 60 * 1000;
}

async function protectedJson<T>(path: string, token: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
    signal
  });
  if (response.status === 401 || response.status === 403) {
    throw new Error("A sessão do Wallboard expirou ou não possui acesso.");
  }
  if (!response.ok) {
    throw new Error(`O backend respondeu ${response.status} ao carregar ${path}.`);
  }
  return (await response.json()) as T;
}

export default function WallboardPage() {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [data, setData] = useState<WallboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const refreshTimer = useRef<number | null>(null);

  useEffect(() => {
    const storedToken = window.sessionStorage.getItem(SESSION_KEY);
    setToken(storedToken);
    setLoading(Boolean(storedToken));
  }, []);

  const logout = useCallback(() => {
    window.sessionStorage.removeItem(SESSION_KEY);
    setToken(null);
    setData(null);
    setConnected(false);
    setError(null);
    setPassword("");
  }, []);

  const refresh = useCallback(
    async (signal?: AbortSignal) => {
      if (!token) return;
      try {
        const [metrics, intelligence, infrastructure, agents, incidents] = await Promise.all([
          protectedJson<Metric[]>("/metrics", token, signal),
          protectedJson<OperationalIntelligence>("/operational-intelligence", token, signal),
          protectedJson<InfrastructureOverview>("/infrastructure/overview", token, signal),
          protectedJson<ManagedAgent[]>("/agent/v2/admin/agents", token, signal),
          protectedJson<Incident[]>("/incidents", token, signal)
        ]);
        setData({ metrics, intelligence, infrastructure, agents, incidents });
        setLastUpdatedAt(new Date());
        setError(null);
      } catch (requestError) {
        if (signal?.aborted) return;
        const message = requestError instanceof Error ? requestError.message : "Falha ao atualizar o Wallboard.";
        setError(message);
        if (message.includes("sessão")) logout();
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [logout, token]
  );

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    void refresh(controller.signal);
    const interval = window.setInterval(() => void refresh(controller.signal), 30_000);
    return () => {
      controller.abort();
      window.clearInterval(interval);
    };
  }, [refresh, token]);

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    let reconnectTimeout: number | null = null;

    const connect = async () => {
      try {
        const response = await fetch(`${API_URL}/realtime/events`, {
          headers: {
            Accept: "text/event-stream",
            Authorization: `Bearer ${token}`
          },
          cache: "no-store",
          signal: controller.signal
        });
        if (!response.ok || !response.body) throw new Error(`stream ${response.status}`);
        setConnected(true);
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        while (!controller.signal.aborted) {
          const { done, value } = await reader.read();
          if (done) break;
          if (decoder.decode(value, { stream: true }).includes("data:")) {
            if (refreshTimer.current) window.clearTimeout(refreshTimer.current);
            refreshTimer.current = window.setTimeout(() => void refresh(), 600);
          }
        }
      } catch {
        if (!controller.signal.aborted) {
          setConnected(false);
          reconnectTimeout = window.setTimeout(() => void connect(), 3_000);
        }
      }
    };

    void connect();
    return () => {
      controller.abort();
      if (reconnectTimeout) window.clearTimeout(reconnectTimeout);
      if (refreshTimer.current) window.clearTimeout(refreshTimer.current);
    };
  }, [refresh, token]);

  const handleLogin = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });
      if (!response.ok) throw new Error("Usuário ou senha inválidos.");
      const payload = (await response.json()) as { accessToken: string; user: { role?: string } };
      if (payload.user.role !== "read_only" && payload.user.role !== "root" && payload.user.role !== "tenant_admin") {
        throw new Error("Este usuário não possui um perfil permitido para o Wallboard.");
      }
      window.sessionStorage.setItem(SESSION_KEY, payload.accessToken);
      setToken(payload.accessToken);
      setPassword("");
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "Falha no login.");
    } finally {
      setLoading(false);
    }
  };

  const agentSummary = useMemo(() => {
    const agents = data?.agents ?? [];
    return {
      total: agents.length,
      online: agents.filter(isOnlineAgent).length,
      workstations: agents.filter((agent) => agent.profile === "workstation").length,
      servers: agents.filter((agent) => agent.profile === "server").length,
      collectors: agents.filter((agent) => agent.profile === "collector").length
    };
  }, [data]);

  if (!token) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#080b10] p-6 text-white">
        <form
          onSubmit={handleLogin}
          className="w-full max-w-md rounded-3xl border border-white/10 bg-[#10151d] p-8 shadow-2xl shadow-orange-950/20"
        >
          <div className="mb-8 flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-500/15 text-orange-400">
              <Gauge className="h-7 w-7" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-orange-400">Vulcan</p>
              <h1 className="text-2xl font-semibold">Wallboard ERS</h1>
            </div>
          </div>
          <p className="mb-6 text-sm leading-6 text-slate-400">
            Entre com o usuário somente leitura reservado à TV. A senha não fica armazenada nesta página.
          </p>
          <label className="mb-4 block text-sm text-slate-300">
            Usuário
            <input
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 outline-none transition focus:border-orange-500"
              required
            />
          </label>
          <label className="mb-6 block text-sm text-slate-300">
            Senha
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 outline-none transition focus:border-orange-500"
              required
            />
          </label>
          {error ? <p className="mb-4 rounded-xl bg-red-500/10 p-3 text-sm text-red-300">{error}</p> : null}
          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-orange-500 px-4 py-3 font-semibold text-black transition hover:bg-orange-400 disabled:opacity-60"
          >
            {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
            Acessar Wallboard
          </button>
        </form>
      </main>
    );
  }

  const openIncidents = data?.incidents.filter((incident) =>
    ["open", "investigating", "monitoring"].includes(incident.status)
  ).length ?? 0;

  return (
    <main className="min-h-screen bg-[#070a0f] p-5 text-white lg:p-7">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="rounded-lg bg-orange-500 px-2.5 py-1 text-xs font-black tracking-[0.22em] text-black">
              VULCAN
            </span>
            <span className="text-sm uppercase tracking-[0.18em] text-slate-500">ERS Transportes</span>
          </div>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">Inteligência operacional em tempo real</h1>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className={`flex items-center gap-2 rounded-full border px-3 py-2 ${connected ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" : "border-amber-500/30 bg-amber-500/10 text-amber-300"}`}>
            <span className={`h-2 w-2 rounded-full ${connected ? "bg-emerald-400" : "bg-amber-400"}`} />
            {connected ? "Tempo real conectado" : "Reconectando"}
          </span>
          <button
            aria-label="Tela cheia"
            onClick={() => void document.documentElement.requestFullscreen?.()}
            className="rounded-xl border border-white/10 p-2.5 text-slate-300 hover:bg-white/5"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
          <button
            aria-label="Sair"
            onClick={logout}
            className="rounded-xl border border-white/10 p-2.5 text-slate-300 hover:bg-white/5"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </header>

      {error ? (
        <div className="mb-5 flex items-center gap-3 rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-red-200">
          <AlertTriangle className="h-5 w-5" />
          {error}
        </div>
      ) : null}

      {loading || !data ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, index) => (
            <div key={index} className="h-40 animate-pulse rounded-2xl border border-white/5 bg-white/[0.035]" />
          ))}
        </div>
      ) : (
        <>
          <section className="mb-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <WallboardStat icon={Gauge} label="Foco operacional" value={`${data.intelligence.focusScore}%`} detail={data.intelligence.periodLabel} tone="orange" />
            <WallboardStat icon={Clock3} label="Tempo ativo" value={formatDuration(data.intelligence.totalActiveSeconds)} detail={`${data.intelligence.totalEvents.toLocaleString("pt-BR")} eventos`} tone="blue" />
            <WallboardStat icon={Users} label="Agentes online" value={`${agentSummary.online}/${agentSummary.total}`} detail={`${agentSummary.workstations} estações · ${agentSummary.servers} servidores`} tone="green" />
            <WallboardStat icon={Network} label="Saúde da infraestrutura" value={data.infrastructure.healthScore === null ? "Sem base" : `${data.infrastructure.healthScore}%`} detail={`${data.infrastructure.assets} ativos monitorados`} tone="violet" />
          </section>

          <section className="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
            <div className="rounded-3xl border border-white/10 bg-[#10151d] p-6">
              <div className="mb-5 flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-orange-400">Leitura executiva</p>
                  <h2 className="mt-2 text-2xl font-semibold">O que está acontecendo agora</h2>
                </div>
                <span className={`rounded-full px-3 py-1 text-xs font-medium ${data.infrastructure.dataOrigin === "real" ? "bg-emerald-500/10 text-emerald-300" : "bg-amber-500/10 text-amber-300"}`}>
                  {data.infrastructure.dataOrigin === "real" ? "Dados reais" : "Dados simulados"}
                </span>
              </div>
              <p className="max-w-4xl text-xl leading-9 text-slate-200">{data.intelligence.aiSummary}</p>
              <div className="mt-7 grid gap-3 md:grid-cols-3">
                <Signal icon={Activity} label="Atividade atual" value={data.intelligence.currentActivity} />
                <Signal icon={RefreshCw} label="Trocas de contexto" value={data.intelligence.contextSwitches.toLocaleString("pt-BR")} />
                <Signal icon={Clock3} label="Taxa de ociosidade" value={`${data.intelligence.idleRate.toFixed(1)}%`} />
              </div>
              {data.metrics.length ? (
                <div className="mt-6 grid gap-3 border-t border-white/10 pt-6 md:grid-cols-2">
                  {data.metrics.slice(0, 4).map((metric) => (
                    <div key={metric.id} className="flex items-center justify-between rounded-2xl bg-white/[0.035] px-4 py-3">
                      <div>
                        <p className="text-sm text-slate-400">{metric.label}</p>
                        <p className="mt-1 text-lg font-semibold">{metric.value}</p>
                      </div>
                      <span className="text-xs text-slate-500">{metric.trend}</span>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>

            <div className="space-y-5">
              <div className="rounded-3xl border border-white/10 bg-[#10151d] p-6">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Infraestrutura</p>
                <div className="mt-5 space-y-4">
                  <HealthRow icon={CheckCircle2} label="Ativos online" value={data.infrastructure.onlineAssets} tone="text-emerald-400" />
                  <HealthRow icon={AlertTriangle} label="Ativos degradados" value={data.infrastructure.degradedAssets} tone="text-amber-400" />
                  <HealthRow icon={Server} label="Ativos offline" value={data.infrastructure.offlineAssets} tone="text-red-400" />
                  <HealthRow icon={Cpu} label="Coletores" value={agentSummary.collectors} tone="text-sky-400" />
                </div>
              </div>
              <div className="rounded-3xl border border-white/10 bg-[#10151d] p-6">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Atenção necessária</p>
                <div className="mt-4 flex items-end justify-between">
                  <div>
                    <p className="text-4xl font-semibold">{Math.max(openIncidents, data.infrastructure.openIncidents)}</p>
                    <p className="mt-1 text-sm text-slate-400">incidentes em acompanhamento</p>
                  </div>
                  <AlertTriangle className={`h-9 w-9 ${openIncidents ? "text-amber-400" : "text-slate-600"}`} />
                </div>
              </div>
            </div>
          </section>
        </>
      )}

      <footer className="mt-5 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
        <span>
          Última atualização: {lastUpdatedAt ? lastUpdatedAt.toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" }) : "aguardando dados"}
        </span>
        <span>Atualização automática · leitura somente · sem dados fictícios ocultos</span>
      </footer>
    </main>
  );
}

function WallboardStat({
  icon: Icon,
  label,
  value,
  detail,
  tone
}: {
  icon: typeof Activity;
  label: string;
  value: string;
  detail: string;
  tone: "orange" | "blue" | "green" | "violet";
}) {
  const tones = {
    orange: "bg-orange-500/10 text-orange-400",
    blue: "bg-sky-500/10 text-sky-400",
    green: "bg-emerald-500/10 text-emerald-400",
    violet: "bg-violet-500/10 text-violet-400"
  };
  return (
    <div className="rounded-3xl border border-white/10 bg-[#10151d] p-5">
      <div className={`mb-5 flex h-10 w-10 items-center justify-center rounded-xl ${tones[tone]}`}>
        <Icon className="h-5 w-5" />
      </div>
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-1 text-3xl font-semibold tracking-tight">{value}</p>
      <p className="mt-2 text-xs text-slate-500">{detail}</p>
    </div>
  );
}

function Signal({ icon: Icon, label, value }: { icon: typeof Activity; label: string; value: string | number }) {
  return (
    <div className="rounded-2xl bg-white/[0.035] p-4">
      <Icon className="mb-3 h-5 w-5 text-orange-400" />
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 truncate text-sm font-medium text-slate-200">{value}</p>
    </div>
  );
}

function HealthRow({
  icon: Icon,
  label,
  value,
  tone
}: {
  icon: typeof Activity;
  label: string;
  value: number;
  tone: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3 text-sm text-slate-300">
        <Icon className={`h-4 w-4 ${tone}`} />
        {label}
      </div>
      <span className="text-lg font-semibold">{value}</span>
    </div>
  );
}
