"use client";

import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ShieldCheck } from "lucide-react";
import Image from "next/image";
import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";
import { commandCenterConfig, initialRuntimeMetrics } from "./command-center/config";
import { CommandCenterShell } from "./command-center/command-center-shell";
import { InfrastructureScene } from "./command-center/infrastructure-scenes";
import { WorkforceScene } from "./command-center/workforce-scenes";
import {
  ConnectionState,
  PlatformHealth,
  PlatformVersion,
  RuntimeMetrics,
  WallboardProfile,
  WallboardSnapshot,
  WallboardType
} from "./command-center/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001";
const SESSION_KEY = "vulcan-wallboard-access-token";
const PAUSED_KEY = "vulcan-wallboard-rotation-paused";

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

function updateWallboardUrl(panelKey: string | null, scene: string | null) {
  const url = new URL(window.location.href);
  if (!panelKey || panelKey === "overview") url.searchParams.delete("panel");
  else url.searchParams.set("panel", panelKey);
  if (scene) url.searchParams.set("scene", scene);
  else url.searchParams.delete("scene");
  window.history.replaceState(
    { panel: panelKey, scene },
    "",
    `${url.pathname}${url.search}`
  );
}

function healthUrl() {
  if (API_URL.startsWith("/")) return "/healthz";
  return `${API_URL.replace(/\/api\/?$/, "")}/healthz`;
}

function versionUrl() {
  if (API_URL.startsWith("/")) return "/api/version";
  return `${API_URL.replace(/\/?$/, "")}/version`;
}

export function VulcanWallboard({ type }: { type: WallboardType }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 4_000,
            retry: (failureCount, error) =>
              !String(error).includes("sessão") && failureCount < 3,
            retryDelay: (attempt) => Math.min(1_000 * 2 ** attempt, 12_000)
          }
        }
      })
  );
  return (
    <QueryClientProvider client={client}>
      <WallboardRuntime type={type} />
    </QueryClientProvider>
  );
}

function WallboardRuntime({ type }: { type: WallboardType }) {
  const queryClient = useQueryClient();
  const [token, setToken] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [itemIndex, setItemIndex] = useState(0);
  const [sceneIndex, setSceneIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [sseConnected, setSseConnected] = useState(false);
  const [sseAttempt, setSseAttempt] = useState(0);
  const [clock, setClock] = useState(() => new Date());
  const [itemStartedAt, setItemStartedAt] = useState(() => Date.now());
  const [burnInShift, setBurnInShift] = useState(0);
  const [visible, setVisible] = useState(true);
  const [browserOnline, setBrowserOnline] = useState(true);
  const [dismissedCritical, setDismissedCritical] = useState<Set<string>>(() => new Set());
  const [metrics, setMetrics] = useState<RuntimeMetrics>({
    fps: null,
    effectiveQuality: "low",
    webglAvailable: false,
    reducedMotion: false
  });
  const refreshTimer = useRef<number | null>(null);
  const qualitySamples = useRef({ low: 0, high: 0 });

  useEffect(() => {
    const storedToken = window.sessionStorage.getItem(SESSION_KEY);
    setToken(storedToken);
    setPaused(window.sessionStorage.getItem(PAUSED_KEY) === "true");
    setBrowserOnline(navigator.onLine);
    setVisible(!document.hidden);
    setInitialized(true);
  }, []);

  const logout = useCallback(() => {
    window.sessionStorage.removeItem(SESSION_KEY);
    setToken(null);
    setSseConnected(false);
    setPassword("");
    queryClient.clear();
  }, [queryClient]);

  const profilesQuery = useQuery({
    queryKey: ["wallboard-profiles", type, token],
    queryFn: ({ signal }) =>
      protectedJson<WallboardProfile[]>("/wallboards/profiles", token!, signal),
    enabled: Boolean(token && initialized && visible),
    refetchInterval: 60_000
  });

  const profile = useMemo(
    () =>
      profilesQuery.data?.find(
        (candidate) => candidate.wallboardType === type && candidate.enabled
      ) ?? null,
    [profilesQuery.data, type]
  );
  const playlist = useMemo(
    () => profile?.playlists.find((candidate) => candidate.enabled) ?? null,
    [profile]
  );
  const items = useMemo(
    () =>
      playlist?.items
        .filter((candidate) => candidate.enabled)
        .sort((left, right) => left.position - right.position) ?? [],
    [playlist]
  );
  const activeItem = items[itemIndex] ?? items[0] ?? null;
  const config = useMemo(() => commandCenterConfig(profile, type), [profile, type]);
  const scenes = config.sceneSequence;
  const activeScene = scenes[sceneIndex] ?? scenes[0] ?? "command";
  const navigationState = useMemo(() => {
    if (typeof window === "undefined") return "";
    const search = new URLSearchParams(window.location.search);
    const requestedPanel = search.get("panel");
    const requestedScene = search.get("scene");
    const requestedItemIndex = requestedPanel
      ? items.findIndex((item) => item.panelKey === requestedPanel)
      : 0;
    const requestedSceneIndex = requestedScene ? scenes.indexOf(requestedScene) : 0;
    return JSON.stringify({
      signature: {
        items: items.map((item) => [
          item.id,
          item.panelKey,
          item.position,
          item.durationSeconds,
          item.enabled
        ]),
        scenes
      },
      itemIndex: requestedItemIndex >= 0 ? requestedItemIndex : 0,
      sceneIndex: requestedSceneIndex >= 0 ? requestedSceneIndex : 0
    });
  }, [items, scenes]);

  useEffect(() => {
    if (!navigationState) return;
    const next = JSON.parse(navigationState) as { itemIndex: number; sceneIndex: number };
    setItemIndex(next.itemIndex);
    setSceneIndex(next.sceneIndex);
    setItemStartedAt(Date.now());
  }, [navigationState]);

  useEffect(() => {
    if (!profile) return;
    setMetrics(initialRuntimeMetrics(config));
  }, [config, profile]);

  const snapshotQuery = useQuery({
    queryKey: ["wallboard-snapshot", type, activeItem?.siteId ?? null, token],
    queryFn: ({ signal }) => {
      const query = new URLSearchParams({ type });
      if (activeItem?.siteId) query.set("siteId", activeItem.siteId);
      return protectedJson<WallboardSnapshot>(
        `/wallboards/snapshot?${query}`,
        token!,
        signal
      );
    },
    enabled: Boolean(token && profile && visible),
    refetchInterval: sseConnected
      ? Math.max(60, profile?.refreshSeconds ?? 30) * 1_000
      : Math.max(5, profile?.refreshSeconds ?? 30) * 1_000,
    placeholderData: (previous) => previous
  });

  const healthQuery = useQuery({
    queryKey: ["wallboard-platform-health"],
    queryFn: async ({ signal }) => {
      const response = await fetch(healthUrl(), { cache: "no-store", signal });
      if (!response.ok) throw new Error(`Health respondeu ${response.status}.`);
      return (await response.json()) as PlatformHealth;
    },
    enabled: Boolean(token && visible),
    refetchInterval: 30_000
  });

  const versionQuery = useQuery({
    queryKey: ["wallboard-platform-version"],
    queryFn: async ({ signal }) => {
      const response = await fetch(versionUrl(), { cache: "no-store", signal });
      if (!response.ok) throw new Error(`Version respondeu ${response.status}.`);
      return (await response.json()) as PlatformVersion;
    },
    enabled: Boolean(token && visible),
    staleTime: 5 * 60_000
  });

  useEffect(() => {
    const error = profilesQuery.error ?? snapshotQuery.error;
    if (error && String(error).includes("sessão")) logout();
  }, [logout, profilesQuery.error, snapshotQuery.error]);

  useEffect(() => {
    const interval = window.setInterval(() => setClock(new Date()), 1_000);
    return () => window.clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleVisibility = () => setVisible(!document.hidden);
    const handleOnline = () => setBrowserOnline(true);
    const handleOffline = () => setBrowserOnline(false);
    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  useEffect(() => {
    if (!profile?.burnInPrevention) return;
    const interval = window.setInterval(
      () => setBurnInShift((current) => (current + 1) % 4),
      5 * 60 * 1_000
    );
    return () => window.clearInterval(interval);
  }, [profile?.burnInPrevention]);

  useEffect(() => {
    if (!token || !visible || !browserOnline) {
      setSseConnected(false);
      return;
    }
    const controller = new AbortController();
    let reconnectTimeout: number | null = null;
    let retry = 0;

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
        retry = 0;
        setSseAttempt(0);
        setSseConnected(true);
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        while (!controller.signal.aborted) {
          const { done, value } = await reader.read();
          if (done) throw new Error("stream encerrado");
          const chunk = decoder.decode(value, { stream: true });
          if (chunk.includes("data:")) {
            if (refreshTimer.current) window.clearTimeout(refreshTimer.current);
            refreshTimer.current = window.setTimeout(
              () =>
                void queryClient.invalidateQueries({
                  queryKey: ["wallboard-snapshot", type]
                }),
              550
            );
          }
        }
      } catch {
        if (controller.signal.aborted) return;
        setSseConnected(false);
        retry += 1;
        setSseAttempt(retry);
        const backoff = Math.min(30_000, 1_000 * 2 ** Math.min(retry, 5));
        const jitter = Math.floor(Math.random() * 400);
        reconnectTimeout = window.setTimeout(() => void connect(), backoff + jitter);
      }
    };

    void connect();
    return () => {
      controller.abort();
      if (reconnectTimeout) window.clearTimeout(reconnectTimeout);
      if (refreshTimer.current) window.clearTimeout(refreshTimer.current);
    };
  }, [browserOnline, queryClient, token, type, visible]);

  const snapshot = useMemo<WallboardSnapshot | null>(() => {
    if (!snapshotQuery.data) return null;
    return {
      ...snapshotQuery.data,
      applications: snapshotQuery.data.applications ?? [],
      agents: snapshotQuery.data.agents ?? [],
      topologyNodes: snapshotQuery.data.topologyNodes ?? [],
      topologyLinks: snapshotQuery.data.topologyLinks ?? []
    };
  }, [snapshotQuery.data]);
  const criticalAlerts = useMemo(
    () =>
      config.alertTakeoverEnabled && playlist?.alertPriorityEnabled !== false
        ? snapshot?.alerts.filter(
            (alert) =>
              ["critical", "error"].includes(String(alert.severity ?? "")) &&
              !dismissedCritical.has(String(alert.id))
          ) ?? []
        : [],
    [
      config.alertTakeoverEnabled,
      dismissedCritical,
      playlist?.alertPriorityEnabled,
      snapshot?.alerts
    ]
  );
  const rotationPaused = paused || criticalAlerts.length > 0 || !visible;
  const itemDurationSeconds =
    activeItem?.durationSeconds ?? playlist?.defaultDurationSeconds ?? 30;
  const sceneDurationSeconds = Math.max(5, itemDurationSeconds / Math.max(1, scenes.length));

  const selectItem = useCallback(
    (direction: -1 | 1) => {
      if (!items.length) return;
      const next = (itemIndex + direction + items.length) % items.length;
      setItemIndex(next);
      setSceneIndex(0);
      setItemStartedAt(Date.now());
      updateWallboardUrl(items[next]?.panelKey ?? null, scenes[0] ?? null);
    },
    [itemIndex, items, scenes]
  );

  useEffect(() => {
    if (rotationPaused || !playlist?.rotationEnabled || !items.length) return;
    const timeout = window.setTimeout(() => {
      if (sceneIndex + 1 < scenes.length) {
        const nextSceneIndex = sceneIndex + 1;
        setSceneIndex(nextSceneIndex);
        updateWallboardUrl(activeItem?.panelKey ?? null, scenes[nextSceneIndex] ?? null);
      } else {
        selectItem(1);
      }
    }, sceneDurationSeconds * 1_000);
    return () => window.clearTimeout(timeout);
  }, [
    activeItem?.panelKey,
    items.length,
    playlist?.rotationEnabled,
    rotationPaused,
    sceneDurationSeconds,
    sceneIndex,
    scenes,
    selectItem
  ]);

  useEffect(() => {
    if (!visible || metrics.reducedMotion) return;
    let frame = 0;
    let last = performance.now();
    let animationFrame = 0;
    const sample = (time: number) => {
      frame += 1;
      if (time - last >= 1_000) {
        const fps = Math.round((frame * 1_000) / (time - last));
        setMetrics((current) => {
          let effectiveQuality = current.effectiveQuality;
          if (config.quality === "auto") {
            if (fps < config.targetFps * 0.65) {
              qualitySamples.current.low += 1;
              qualitySamples.current.high = 0;
            } else if (fps > config.targetFps * 0.9) {
              qualitySamples.current.high += 1;
              qualitySamples.current.low = 0;
            } else {
              qualitySamples.current.low = 0;
              qualitySamples.current.high = 0;
            }
            if (qualitySamples.current.low >= 4) {
              effectiveQuality =
                current.effectiveQuality === "4k"
                  ? "cinematic"
                  : current.effectiveQuality === "cinematic"
                    ? "balanced"
                    : "low";
              qualitySamples.current.low = 0;
            } else if (qualitySamples.current.high >= 20) {
              effectiveQuality =
                current.effectiveQuality === "low"
                  ? "balanced"
                  : current.effectiveQuality === "balanced"
                    ? "cinematic"
                    : current.effectiveQuality;
              qualitySamples.current.high = 0;
            }
          }
          return { ...current, fps, effectiveQuality };
        });
        frame = 0;
        last = time;
      }
      animationFrame = window.requestAnimationFrame(sample);
    };
    animationFrame = window.requestAnimationFrame(sample);
    return () => window.cancelAnimationFrame(animationFrame);
  }, [config.quality, config.targetFps, metrics.reducedMotion, visible]);

  const togglePaused = useCallback(() => {
    setPaused((current) => {
      const next = !current;
      window.sessionStorage.setItem(PAUSED_KEY, String(next));
      return next;
    });
  }, []);

  const handleLogin = async (event: FormEvent) => {
    event.preventDefault();
    setLoginLoading(true);
    setLoginError(null);
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
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : "Falha no login.");
    } finally {
      setLoginLoading(false);
    }
  };

  if (!initialized) return <div className="command-loading-screen" />;

  if (!token) {
    return (
      <main className="command-login">
        <div className="command-login-grid" aria-hidden="true" />
        <form onSubmit={handleLogin}>
          <span className="command-login-kicker">VULCAN COMMAND SYSTEM</span>
          <Image src="/vulcan-logo.svg" alt="Vulcan" width={210} height={56} priority />
          <h1>{type === "workforce" ? "Workforce Command Center" : "Infrastructure Command Center"}</h1>
          <p>Canal exclusivo de TV · leitura somente · dados operacionais reais</p>
          <label>
            Usuário
            <input
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </label>
          <label>
            Senha
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          {loginError ? (
            <div role="alert"><AlertTriangle />{loginError}</div>
          ) : null}
          <button type="submit" disabled={loginLoading}>
            <ShieldCheck />
            {loginLoading ? "Validando canal…" : "Acessar painel"}
          </button>
        </form>
      </main>
    );
  }

  if (profilesQuery.isLoading || !profile || !snapshot) {
    return (
      <main className="command-loading-screen" aria-label="Carregando Vulcan Command Center">
        <Image src="/vulcan-symbol.svg" alt="" width={86} height={86} priority />
        <span />
        <p>
          {profilesQuery.error || snapshotQuery.error
            ? "Não foi possível carregar a configuração."
            : "Sincronizando telemetria real…"}
        </p>
        {profilesQuery.error || snapshotQuery.error ? (
          <button type="button" onClick={logout}>Voltar ao acesso</button>
        ) : null}
      </main>
    );
  }

  const ageSeconds = Math.max(
    0,
    (clock.getTime() - new Date(snapshot.generatedAt).getTime()) / 1_000
  );
  const connectionState: ConnectionState = !browserOnline
    ? "offline"
    : snapshotQuery.error
      ? "stale"
      : snapshotQuery.isFetching
        ? "updating"
        : sseConnected
          ? "live"
          : sseAttempt > 0
            ? "reconnecting"
            : ageSeconds > Math.max(120, profile.refreshSeconds * 4)
              ? "stale"
              : "reconnecting";
  const elapsedSeconds = Math.max(0, (clock.getTime() - itemStartedAt) / 1_000);
  const itemProgress = rotationPaused
    ? Math.min(100, (elapsedSeconds / itemDurationSeconds) * 100)
    : Math.min(100, (elapsedSeconds / itemDurationSeconds) * 100);

  return (
    <CommandCenterShell
      type={type}
      profile={profile}
      activeItem={activeItem}
      itemIndex={itemIndex}
      itemCount={items.length}
      itemProgress={itemProgress}
      scene={activeScene}
      sceneIndex={sceneIndex}
      sceneCount={scenes.length}
      config={config}
      connectionState={connectionState}
      generatedAt={snapshot.generatedAt}
      clock={clock}
      paused={paused}
      controlsDisabled={items.length < 2}
      metrics={metrics}
      error={
        snapshotQuery.error
          ? "Conexão interrompida. Exibindo a última informação válida."
          : healthQuery.error
            ? "A telemetria principal está ativa, mas o health do Vulcan está temporariamente indisponível."
            : null
      }
      alerts={criticalAlerts}
      burnInShift={burnInShift}
      onPrevious={() => selectItem(-1)}
      onNext={() => selectItem(1)}
      onTogglePause={togglePaused}
      onFullscreen={() => void document.documentElement.requestFullscreen?.()}
      onLogout={logout}
      onDismissCritical={(id) =>
        setDismissedCritical((current) => new Set([...current, id]))
      }
    >
      {type === "workforce" ? (
        <WorkforceScene scene={activeScene} snapshot={snapshot} />
      ) : (
        <InfrastructureScene
          scene={activeScene}
          snapshot={snapshot}
          health={healthQuery.data ?? null}
          version={versionQuery.data ?? null}
          metrics={metrics}
          visible={visible}
          onContextLost={() =>
            setMetrics((current) => ({
              ...current,
              webglAvailable: false,
              effectiveQuality: "low"
            }))
          }
        />
      )}
    </CommandCenterShell>
  );
}
