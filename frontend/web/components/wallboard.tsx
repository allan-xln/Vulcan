"use client";

import Image from "next/image";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Building2,
  CheckCircle2,
  Clock3,
  Gauge,
  LogOut,
  Maximize2,
  Network,
  Pause,
  Play,
  RefreshCw,
  Server,
  ShieldCheck,
  Users
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";
const SESSION_KEY = "vulcan-wallboard-access-token";
const PAUSED_KEY = "vulcan-wallboard-rotation-paused";

type WallboardType = "workforce" | "infrastructure";

type PlaylistItem = {
  id: string;
  siteId: string | null;
  siteName: string | null;
  panelKey: string;
  title: string;
  position: number;
  durationSeconds: number | null;
  enabled: boolean;
};

type Playlist = {
  id: string;
  name: string;
  enabled: boolean;
  rotationEnabled: boolean;
  defaultDurationSeconds: number;
  transition: "none" | "fade" | "slide";
  alertPriorityEnabled: boolean;
  autoReturnSeconds: number;
  items: PlaylistItem[];
};

type WallboardProfile = {
  id: string;
  name: string;
  wallboardType: WallboardType;
  enabled: boolean;
  refreshSeconds: number;
  fullscreen: boolean;
  nightMode: boolean;
  burnInPrevention: boolean;
  showClock: boolean;
  showLastUpdate: boolean;
  showConnectionStatus: boolean;
  playlists: Playlist[];
};

type SnapshotRow = Record<string, unknown>;

type WallboardSnapshot = {
  tenantId: string;
  wallboardType: WallboardType;
  dataOrigin: "real";
  generatedAt: string;
  siteId: string | null;
  siteName: string | null;
  kpis: Record<string, number | string | null>;
  sites: SnapshotRow[];
  statusGroups: SnapshotRow[];
  activity: SnapshotRow[];
  alerts: SnapshotRow[];
  integrations: SnapshotRow[];
};

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

function numberValue(value: unknown) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function textValue(value: unknown, fallback = "Não informado") {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function formatDate(value: unknown) {
  if (typeof value !== "string") return "sem coleta";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "sem coleta";
  return date.toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" });
}

function formatKpi(value: number | string | null | undefined, suffix = "") {
  if (value === null || value === undefined || value === "") return "Sem base";
  if (typeof value === "number") return `${value.toLocaleString("pt-BR")}${suffix}`;
  return `${value}${suffix}`;
}

function statusTone(status: string) {
  if (["online", "ok", "connected", "active"].includes(status)) return "text-emerald-300";
  if (["degraded", "warning", "investigating", "monitoring"].includes(status)) return "text-amber-300";
  if (["offline", "critical", "error", "unavailable"].includes(status)) return "text-red-300";
  return "text-zinc-400";
}

function updatePanelUrl(panelKey: string) {
  const url = new URL(window.location.href);
  if (panelKey === "overview") url.searchParams.delete("panel");
  else url.searchParams.set("panel", panelKey);
  window.history.replaceState({ panel: panelKey }, "", `${url.pathname}${url.search}`);
}

export function VulcanWallboard({ type }: { type: WallboardType }) {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [profiles, setProfiles] = useState<WallboardProfile[]>([]);
  const [snapshot, setSnapshot] = useState<WallboardSnapshot | null>(null);
  const [panelIndex, setPanelIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [connected, setConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const [clock, setClock] = useState(() => new Date());
  const [burnInShift, setBurnInShift] = useState(0);
  const refreshTimer = useRef<number | null>(null);

  const profile = useMemo(
    () => profiles.find((item) => item.wallboardType === type && item.enabled) ?? null,
    [profiles, type]
  );
  const playlist = useMemo(
    () => profile?.playlists.find((item) => item.enabled) ?? null,
    [profile]
  );
  const items = useMemo(
    () => playlist?.items.filter((item) => item.enabled).sort((a, b) => a.position - b.position) ?? [],
    [playlist]
  );
  const activeItem = items[panelIndex] ?? items[0] ?? null;

  useEffect(() => {
    const storedToken = window.sessionStorage.getItem(SESSION_KEY);
    setToken(storedToken);
    setPaused(window.sessionStorage.getItem(PAUSED_KEY) === "true");
    setLoading(Boolean(storedToken));
  }, []);

  useEffect(() => {
    const interval = window.setInterval(() => setClock(new Date()), 1_000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!profile?.burnInPrevention) return;
    const interval = window.setInterval(
      () => setBurnInShift((current) => (current + 1) % 4),
      5 * 60 * 1_000
    );
    return () => window.clearInterval(interval);
  }, [profile?.burnInPrevention]);

  const logout = useCallback(() => {
    window.sessionStorage.removeItem(SESSION_KEY);
    setToken(null);
    setProfiles([]);
    setSnapshot(null);
    setConnected(false);
    setError(null);
    setPassword("");
  }, []);

  const loadProfiles = useCallback(async (accessToken: string, signal?: AbortSignal) => {
    const loadedProfiles = await protectedJson<WallboardProfile[]>(
      "/wallboards/profiles",
      accessToken,
      signal
    );
    setProfiles(loadedProfiles);
    const matchingProfile = loadedProfiles.find(
      (item) => item.wallboardType === type && item.enabled
    );
    const matchingItems =
      matchingProfile?.playlists
        .find((item) => item.enabled)
        ?.items.filter((item) => item.enabled)
        .sort((a, b) => a.position - b.position) ?? [];
    const requestedPanel = new URLSearchParams(window.location.search).get("panel");
    const requestedIndex = requestedPanel
      ? matchingItems.findIndex((item) => item.panelKey === requestedPanel)
      : 0;
    setPanelIndex(requestedIndex >= 0 ? requestedIndex : 0);
  }, [type]);

  const refresh = useCallback(
    async (signal?: AbortSignal) => {
      if (!token) return;
      const query = new URLSearchParams({ type });
      if (activeItem?.siteId) query.set("siteId", activeItem.siteId);
      try {
        const nextSnapshot = await protectedJson<WallboardSnapshot>(
          `/wallboards/snapshot?${query}`,
          token,
          signal
        );
        setSnapshot(nextSnapshot);
        setLastUpdatedAt(new Date());
        setError(null);
      } catch (requestError) {
        if (signal?.aborted) return;
        const message =
          requestError instanceof Error ? requestError.message : "Falha ao atualizar o Wallboard.";
        setError(message);
        if (message.includes("sessão")) logout();
      } finally {
        if (!signal?.aborted) setLoading(false);
      }
    },
    [activeItem?.siteId, logout, token, type]
  );

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    void loadProfiles(token, controller.signal).catch((requestError: unknown) => {
      if (!controller.signal.aborted) {
        const message = requestError instanceof Error ? requestError.message : "Falha ao carregar a configuração.";
        setError(message);
        setLoading(false);
        if (message.includes("sessão")) logout();
      }
    });
    return () => controller.abort();
  }, [loadProfiles, logout, token]);

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    void refresh(controller.signal);
    const interval = window.setInterval(
      () => void refresh(controller.signal),
      Math.max(5, profile?.refreshSeconds ?? 30) * 1_000
    );
    return () => {
      controller.abort();
      window.clearInterval(interval);
    };
  }, [profile?.refreshSeconds, refresh, token]);

  useEffect(() => {
    if (!items.length || paused || !playlist?.rotationEnabled) return;
    const duration =
      (activeItem?.durationSeconds ?? playlist.defaultDurationSeconds) * 1_000;
    const timeout = window.setTimeout(() => {
      setPanelIndex((current) => {
        const next = (current + 1) % items.length;
        updatePanelUrl(items[next]?.panelKey ?? "overview");
        return next;
      });
    }, duration);
    return () => window.clearTimeout(timeout);
  }, [activeItem?.durationSeconds, items, paused, playlist]);

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    let reconnectTimeout: number | null = null;
    const connect = async () => {
      try {
        const response = await fetch(`${API_URL}/realtime/events`, {
          headers: { Accept: "text/event-stream", Authorization: `Bearer ${token}` },
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

  const selectPanel = useCallback(
    (direction: -1 | 1) => {
      if (!items.length) return;
      setPanelIndex((current) => {
        const next = (current + direction + items.length) % items.length;
        updatePanelUrl(items[next]?.panelKey ?? "overview");
        return next;
      });
    },
    [items]
  );

  const togglePaused = useCallback(() => {
    setPaused((current) => {
      const next = !current;
      window.sessionStorage.setItem(PAUSED_KEY, String(next));
      return next;
    });
  }, []);

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
      const payload = (await response.json()) as {
        accessToken: string;
        user: { role?: string };
      };
      if (!["read_only", "root", "tenant_admin"].includes(payload.user.role ?? "")) {
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

  if (!token) {
    return (
      <main className="vulcan-tv flex min-h-screen items-center justify-center p-6 text-white">
        <form onSubmit={handleLogin} className="w-full max-w-md border border-zinc-800 bg-[#111111] p-8">
          <Image src="/vulcan-logo.svg" alt="Vulcan" width={184} height={48} priority />
          <p className="mt-8 text-xs font-semibold uppercase tracking-[0.22em] text-orange-400">
            {type === "workforce" ? "Workforce Wallboard" : "Infra Wallboard"}
          </p>
          <h1 className="mt-2 text-2xl font-semibold">Painel operacional ERS</h1>
          <p className="mt-3 text-sm leading-6 text-zinc-400">
            Use a conta somente leitura da TV. A senha não é armazenada nesta página.
          </p>
          <label className="mt-7 block text-sm text-zinc-300">
            Usuário
            <input
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="mt-2 w-full border border-zinc-700 bg-black px-4 py-3 outline-none focus:border-orange-500"
              required
            />
          </label>
          <label className="mt-4 block text-sm text-zinc-300">
            Senha
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-2 w-full border border-zinc-700 bg-black px-4 py-3 outline-none focus:border-orange-500"
              required
            />
          </label>
          {error ? <p className="mt-4 border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">{error}</p> : null}
          <button
            type="submit"
            disabled={loading}
            className="mt-6 flex w-full items-center justify-center gap-2 bg-orange-500 px-4 py-3 font-semibold text-black hover:bg-orange-400 disabled:opacity-60"
          >
            {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
            Acessar painel
          </button>
        </form>
      </main>
    );
  }

  const shiftClass = ["translate-x-0 translate-y-0", "translate-x-px", "translate-y-px", "-translate-x-px"][burnInShift];

  return (
    <main className="vulcan-tv min-h-screen overflow-hidden p-4 text-white lg:p-6">
      <div className={`transition-transform duration-700 ${shiftClass}`}>
        <header className="mb-4 flex flex-wrap items-center justify-between gap-4 border-b border-zinc-800 pb-4">
          <div className="flex items-center gap-5">
            <Image src="/vulcan-logo.svg" alt="Vulcan" width={162} height={42} priority />
            <div className="border-l border-zinc-700 pl-5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-orange-400">
                {type === "workforce" ? "Workforce" : "Infrastructure"}
              </p>
              <h1 className="mt-1 text-xl font-semibold">
                {activeItem?.title ?? (type === "workforce" ? "Visão geral das equipes" : "Visão geral da infraestrutura")}
              </h1>
              <p className="mt-1 text-xs text-zinc-500">
                {snapshot?.siteName ?? "Todas as filiais"} · ERS Transportes
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {profile?.showConnectionStatus !== false ? (
              <span className={`flex items-center gap-2 border px-3 py-2 text-xs ${connected ? "border-emerald-900 bg-emerald-950/30 text-emerald-300" : "border-amber-900 bg-amber-950/30 text-amber-300"}`}>
                <span className={`h-2 w-2 ${connected ? "bg-emerald-400" : "bg-amber-400"}`} />
                {connected ? "Tempo real" : "Reconectando"}
              </span>
            ) : null}
            {profile?.showClock !== false ? (
              <span className="border border-zinc-800 bg-[#111] px-3 py-2 font-mono text-sm text-zinc-200">
                {clock.toLocaleTimeString("pt-BR", { timeZone: "America/Sao_Paulo" })}
              </span>
            ) : null}
            {items.length > 1 ? (
              <>
                <IconButton label="Painel anterior" onClick={() => selectPanel(-1)} icon={ArrowLeft} />
                <IconButton label={paused ? "Retomar rotação" : "Pausar rotação"} onClick={togglePaused} icon={paused ? Play : Pause} />
                <IconButton label="Próximo painel" onClick={() => selectPanel(1)} icon={ArrowRight} />
              </>
            ) : null}
            <IconButton label="Tela cheia" onClick={() => void document.documentElement.requestFullscreen?.()} icon={Maximize2} />
            <IconButton label="Sair" onClick={logout} icon={LogOut} />
          </div>
        </header>

        {error ? (
          <div className="mb-4 flex items-center gap-3 border border-red-900 bg-red-950/35 px-4 py-3 text-red-200">
            <AlertTriangle className="h-5 w-5" />
            {error}
          </div>
        ) : null}

        {loading || !snapshot ? (
          <div className="grid gap-px bg-zinc-800 md:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, index) => (
              <div key={index} className="h-36 animate-pulse bg-[#111]" />
            ))}
          </div>
        ) : type === "workforce" ? (
          <WorkforcePanel snapshot={snapshot} />
        ) : (
          <InfrastructurePanel snapshot={snapshot} />
        )}

        <footer className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-zinc-800 pt-3 text-[11px] text-zinc-500">
          <span>
            {profile?.showLastUpdate !== false
              ? `Atualizado em ${lastUpdatedAt?.toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" }) ?? "aguardando coleta"}`
              : "Atualização automática"}
          </span>
          <span>Dados reais · leitura somente · perfil {profile?.name ?? "não configurado"}</span>
        </footer>
      </div>
    </main>
  );
}

function WorkforcePanel({ snapshot }: { snapshot: WallboardSnapshot }) {
  const kpis = snapshot.kpis;
  return (
    <>
      <section className="grid gap-px bg-zinc-800 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi icon={Users} label="Pessoas ativas" value={formatKpi(kpis.activePeople)} detail="sinais nos últimos 15 minutos" />
        <Kpi icon={CheckCircle2} label="Agentes online" value={formatKpi(kpis.onlineAgents)} detail={`${formatKpi(kpis.agents)} agentes reais cadastrados`} />
        <Kpi icon={Clock3} label="Agentes atrasados" value={formatKpi(kpis.delayedAgents)} detail="entre 5 e 30 minutos sem contato" tone="warning" />
        <Kpi icon={AlertTriangle} label="Agentes offline" value={formatKpi(kpis.offlineAgents)} detail="mais de 30 minutos sem contato" tone={numberValue(kpis.offlineAgents) ? "critical" : "normal"} />
      </section>
      <section className="mt-px grid gap-px bg-zinc-800 xl:grid-cols-[1.2fr_0.8fr]">
        <DataPanel title="Pulso operacional — últimas 12 horas" subtitle={`${formatKpi(kpis.events24h)} eventos reais nas últimas 24 horas`}>
          <ActivityRows rows={snapshot.activity} />
        </DataPanel>
        <DataPanel title="Comparação por filial" subtitle="Atividade e cobertura técnica observadas">
          <SiteRows rows={snapshot.sites} workforce />
        </DataPanel>
        <DataPanel title="Saúde da coleta" subtitle="Identidades reais; simuladores são excluídos">
          <div className="grid grid-cols-2 gap-px bg-zinc-800">
            <CompactValue label="Online" value={kpis.onlineAgents} />
            <CompactValue label="Atrasados" value={kpis.delayedAgents} />
            <CompactValue label="Offline" value={kpis.offlineAgents} />
            <CompactValue label="Eventos 24h" value={kpis.events24h} />
          </div>
        </DataPanel>
        <DataPanel title="Atenção necessária" subtitle="Incidentes sustentados por evidências">
          <AlertRows rows={snapshot.alerts} />
        </DataPanel>
      </section>
    </>
  );
}

function InfrastructurePanel({ snapshot }: { snapshot: WallboardSnapshot }) {
  const kpis = snapshot.kpis;
  return (
    <>
      <section className="grid gap-px bg-zinc-800 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi icon={Gauge} label="Disponibilidade" value={formatKpi(kpis.availability, "%")} detail={`${formatKpi(kpis.assets)} ativos monitorados`} />
        <Kpi icon={CheckCircle2} label="Ativos online" value={formatKpi(kpis.onlineAssets)} detail="última observação registrada" />
        <Kpi icon={AlertTriangle} label="Degradados" value={formatKpi(kpis.degradedAssets)} detail="exigem acompanhamento" tone={numberValue(kpis.degradedAssets) ? "warning" : "normal"} />
        <Kpi icon={Server} label="Offline" value={formatKpi(kpis.offlineAssets)} detail={`${formatKpi(kpis.incidents)} incidentes abertos`} tone={numberValue(kpis.offlineAssets) ? "critical" : "normal"} />
      </section>
      <section className="mt-px grid gap-px bg-zinc-800 xl:grid-cols-[1.2fr_0.8fr]">
        <DataPanel title="Infraestrutura por classe" subtitle="Inventário reconciliado por origem">
          <StatusRows rows={snapshot.statusGroups} />
        </DataPanel>
        <DataPanel title="Filiais" subtitle="Disponibilidade por local operacional">
          <SiteRows rows={snapshot.sites} />
        </DataPanel>
        <DataPanel title="Integrações somente leitura" subtitle="Última sincronização e estado do coletor">
          <IntegrationRows rows={snapshot.integrations} />
        </DataPanel>
        <DataPanel title="Alertas e incidentes" subtitle="Sem ocorrência sintética misturada">
          <AlertRows rows={snapshot.alerts} />
        </DataPanel>
      </section>
    </>
  );
}

function Kpi({
  icon: Icon,
  label,
  value,
  detail,
  tone = "normal"
}: {
  icon: typeof Gauge;
  label: string;
  value: string;
  detail: string;
  tone?: "normal" | "warning" | "critical";
}) {
  const color = tone === "critical" ? "text-red-300" : tone === "warning" ? "text-amber-300" : "text-orange-300";
  return (
    <article className="bg-[#111] p-5">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-500">{label}</p>
        <Icon className={`h-5 w-5 ${color}`} />
      </div>
      <p className={`mt-5 text-4xl font-semibold tabular-nums ${color}`}>{value}</p>
      <p className="mt-2 text-xs text-zinc-500">{detail}</p>
    </article>
  );
}

function DataPanel({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <article className="min-h-56 bg-[#111] p-5">
      <div className="mb-4 border-b border-zinc-800 pb-3">
        <h2 className="font-semibold text-zinc-100">{title}</h2>
        <p className="mt-1 text-xs text-zinc-500">{subtitle}</p>
      </div>
      {children}
    </article>
  );
}

function ActivityRows({ rows }: { rows: SnapshotRow[] }) {
  const visible = rows.slice(-8).reverse();
  if (!visible.length) return <EmptyData label="Ainda não há atividade real nesse intervalo." />;
  return (
    <div className="divide-y divide-zinc-800">
      {visible.map((row, index) => (
        <div key={`${String(row.bucket)}-${String(row.category)}-${index}`} className="grid grid-cols-[1fr_auto_auto] gap-3 py-2.5 text-sm">
          <span className="capitalize text-zinc-300">{textValue(row.category, "operacional")}</span>
          <span className="text-zinc-500">{formatDate(row.bucket)}</span>
          <span className="font-mono text-orange-300">{numberValue(row.events)}</span>
        </div>
      ))}
    </div>
  );
}

function SiteRows({ rows, workforce = false }: { rows: SnapshotRow[]; workforce?: boolean }) {
  if (!rows.length) return <EmptyData label="Nenhuma filial está visível neste perfil." />;
  return (
    <div className="divide-y divide-zinc-800">
      {rows.map((row) => (
        <div key={String(row.id)} className="grid grid-cols-[1fr_auto_auto] items-center gap-4 py-3">
          <div>
            <p className="text-sm font-medium text-zinc-200">{textValue(row.name)}</p>
            <p className="mt-1 text-xs text-zinc-500">{textValue(row.code, "sem código")}</p>
          </div>
          <div className="text-right">
            <p className="font-mono text-sm text-zinc-200">
              {workforce ? numberValue(row.active_people) : `${numberValue(row.online)}/${numberValue(row.assets)}`}
            </p>
            <p className="text-[10px] uppercase text-zinc-600">{workforce ? "pessoas ativas" : "online"}</p>
          </div>
          <Building2 className="h-4 w-4 text-orange-400" />
        </div>
      ))}
    </div>
  );
}

function StatusRows({ rows }: { rows: SnapshotRow[] }) {
  if (!rows.length) return <EmptyData label="Nenhum ativo cadastrado para esta filial." />;
  return (
    <div className="grid gap-px bg-zinc-800 sm:grid-cols-2">
      {rows.map((row, index) => (
        <div key={`${String(row.key)}-${String(row.status)}-${index}`} className="flex items-center justify-between bg-[#111] px-3 py-3">
          <div>
            <p className="text-sm text-zinc-300">{textValue(row.key).replaceAll("_", " ")}</p>
            <p className={`mt-1 text-xs uppercase ${statusTone(textValue(row.status, "unknown"))}`}>{textValue(row.status, "unknown")}</p>
          </div>
          <span className="font-mono text-lg text-zinc-100">{numberValue(row.value)}</span>
        </div>
      ))}
    </div>
  );
}

function IntegrationRows({ rows }: { rows: SnapshotRow[] }) {
  if (!rows.length) return <EmptyData label="Nenhuma integração habilitada." />;
  return (
    <div className="divide-y divide-zinc-800">
      {rows.map((row, index) => (
        <div key={`${String(row.adapter_type)}-${index}`} className="flex items-center justify-between gap-4 py-3">
          <div>
            <p className="text-sm text-zinc-200">{textValue(row.name)}</p>
            <p className="mt-1 text-xs text-zinc-500">Último sucesso: {formatDate(row.last_success_at)}</p>
          </div>
          <span className={`text-xs font-semibold uppercase ${statusTone(textValue(row.status, "unknown"))}`}>
            {textValue(row.status, "unknown")}
          </span>
        </div>
      ))}
    </div>
  );
}

function AlertRows({ rows }: { rows: SnapshotRow[] }) {
  if (!rows.length) return <EmptyData label="Nenhum incidente aberto com evidência." icon={CheckCircle2} />;
  return (
    <div className="divide-y divide-zinc-800">
      {rows.map((row) => (
        <div key={String(row.id)} className="py-3">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-medium text-zinc-200">{textValue(row.title)}</p>
            <span className={`text-xs font-semibold uppercase ${statusTone(textValue(row.severity))}`}>{textValue(row.severity)}</span>
          </div>
          <p className="mt-1 text-xs text-zinc-500">{textValue(row.impact, "Impacto em análise")} · {formatDate(row.last_occurred_at)}</p>
        </div>
      ))}
    </div>
  );
}

function CompactValue({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="bg-[#111] p-4">
      <p className="text-xs text-zinc-500">{label}</p>
      <p className="mt-2 font-mono text-2xl text-zinc-100">{numberValue(value).toLocaleString("pt-BR")}</p>
    </div>
  );
}

function EmptyData({ label, icon: Icon = Network }: { label: string; icon?: typeof Network }) {
  return (
    <div className="flex min-h-28 items-center justify-center gap-3 border border-dashed border-zinc-800 px-5 text-sm text-zinc-500">
      <Icon className="h-5 w-5 text-zinc-600" />
      {label}
    </div>
  );
}

function IconButton({ label, onClick, icon: Icon }: { label: string; onClick: () => void; icon: typeof Pause }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className="grid h-9 w-9 place-items-center border border-zinc-800 bg-[#111] text-zinc-300 hover:border-orange-500 hover:text-orange-300"
    >
      <Icon className="h-4 w-4" />
    </button>
  );
}
