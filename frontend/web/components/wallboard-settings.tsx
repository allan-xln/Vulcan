"use client";

import {
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  ExternalLink,
  LoaderCircle,
  MonitorUp,
  RefreshCw,
  Save,
  ShieldCheck
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  INFRASTRUCTURE_SCENES,
  SCENE_LABELS,
  WORKFORCE_SCENES
} from "./command-center/config";

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
  schedule: Record<string, unknown>;
  alertPriorityEnabled: boolean;
  autoReturnSeconds: number;
  items: PlaylistItem[];
};

type Profile = {
  id: string;
  name: string;
  wallboardType: "workforce" | "infrastructure";
  enabled: boolean;
  refreshSeconds: number;
  fullscreen: boolean;
  nightMode: boolean;
  burnInPrevention: boolean;
  showClock: boolean;
  showLastUpdate: boolean;
  showConnectionStatus: boolean;
  config: Record<string, unknown>;
  playlists: Playlist[];
};

type Props = {
  apiUrl: string;
  tenantId: string;
  token: string;
};

async function requestJson<T>(
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
  return (await response.json()) as T;
}

export function WallboardSettings({ apiUrl, tenantId, token }: Props) {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const selected = useMemo(
    () => profiles.find((profile) => profile.id === selectedId) ?? profiles[0] ?? null,
    [profiles, selectedId]
  );
  const playlist = selected?.playlists.find((item) => item.enabled) ?? selected?.playlists[0] ?? null;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await requestJson<Profile[]>(apiUrl, "/wallboards/profiles", token, tenantId);
      setProfiles(next);
      setSelectedId((current) => current || next[0]?.id || "");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível carregar os Wallboards.");
    } finally {
      setLoading(false);
    }
  }, [apiUrl, tenantId, token]);

  useEffect(() => {
    void load();
  }, [load]);

  function updateSelected(patch: Partial<Profile>) {
    if (!selected) return;
    setProfiles((current) =>
      current.map((profile) => (profile.id === selected.id ? { ...profile, ...patch } : profile))
    );
  }

  function updateCommandConfig(patch: Record<string, unknown>) {
    if (!selected) return;
    updateSelected({ config: { ...selected.config, ...patch } });
  }

  function updatePlaylist(patch: Partial<Playlist>) {
    if (!selected || !playlist) return;
    setProfiles((current) =>
      current.map((profile) =>
        profile.id !== selected.id
          ? profile
          : {
              ...profile,
              playlists: profile.playlists.map((item) =>
                item.id === playlist.id ? { ...item, ...patch } : item
              )
            }
      )
    );
  }

  function moveItem(index: number, direction: -1 | 1) {
    if (!playlist) return;
    const target = index + direction;
    if (target < 0 || target >= playlist.items.length) return;
    const items = [...playlist.items].sort((a, b) => a.position - b.position);
    [items[index], items[target]] = [items[target], items[index]];
    updatePlaylist({ items: items.map((item, position) => ({ ...item, position })) });
  }

  function updateItem(itemId: string, patch: Partial<PlaylistItem>) {
    if (!playlist) return;
    updatePlaylist({
      items: playlist.items.map((item) => (item.id === itemId ? { ...item, ...patch } : item))
    });
  }

  async function save() {
    if (!selected || !playlist) return;
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await requestJson(
        apiUrl,
        `/wallboards/profiles/${selected.id}`,
        token,
        tenantId,
        {
          method: "PATCH",
          body: JSON.stringify({
            tenantId,
            name: selected.name,
            enabled: selected.enabled,
            refreshSeconds: selected.refreshSeconds,
            fullscreen: selected.fullscreen,
            nightMode: selected.nightMode,
            burnInPrevention: selected.burnInPrevention,
            showClock: selected.showClock,
            showLastUpdate: selected.showLastUpdate,
            showConnectionStatus: selected.showConnectionStatus,
            config: selected.config
          })
        }
      );
      await requestJson(
        apiUrl,
        `/wallboards/playlists/${playlist.id}`,
        token,
        tenantId,
        {
          method: "PATCH",
          body: JSON.stringify({
            tenantId,
            enabled: playlist.enabled,
            rotationEnabled: playlist.rotationEnabled,
            defaultDurationSeconds: playlist.defaultDurationSeconds,
            transition: playlist.transition,
            schedule: playlist.schedule,
            alertPriorityEnabled: playlist.alertPriorityEnabled,
            autoReturnSeconds: playlist.autoReturnSeconds
          })
        }
      );
      await requestJson(
        apiUrl,
        `/wallboards/playlists/${playlist.id}/items`,
        token,
        tenantId,
        {
          method: "PATCH",
          body: JSON.stringify({
            tenantId,
            items: [...playlist.items]
              .sort((a, b) => a.position - b.position)
              .map((item, position) => ({
                id: item.id,
                position,
                durationSeconds: item.durationSeconds,
                enabled: item.enabled
              }))
          })
        }
      );
      setSuccess("Perfil, rotação e painéis salvos com auditoria.");
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível salvar o Wallboard.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className="mt-5 flex min-h-72 items-center justify-center border border-zinc-800 bg-zinc-950"><LoaderCircle className="h-6 w-6 animate-spin text-orange-400" /></div>;
  }

  return (
    <section className="mt-5 space-y-5" aria-labelledby="wallboards-settings-title">
      <header className="border border-zinc-800 bg-zinc-950 p-6">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-orange-400">Administração de TVs</p>
            <h1 id="wallboards-settings-title" className="mt-2 text-3xl font-semibold text-white">Wallboards e playlists</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-400">
              Configuração persistida no tenant. A TV usa conta somente leitura e não recebe controles administrativos.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <a href="/wallboard/workforce" target="_blank" className="flex items-center gap-2 border border-zinc-700 px-4 py-2 text-sm text-zinc-200 hover:border-orange-500">
              Workforce <ExternalLink className="h-4 w-4" />
            </a>
            <a href="/wallboard/infra" target="_blank" className="flex items-center gap-2 border border-zinc-700 px-4 py-2 text-sm text-zinc-200 hover:border-orange-500">
              Infra <ExternalLink className="h-4 w-4" />
            </a>
            <button onClick={() => void load()} className="grid h-10 w-10 place-items-center border border-zinc-700 text-zinc-300" aria-label="Atualizar">
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>
      </header>

      {error ? <p className="border border-red-900 bg-red-950/30 p-4 text-sm text-red-300">{error}</p> : null}
      {success ? <p className="flex items-center gap-2 border border-emerald-900 bg-emerald-950/30 p-4 text-sm text-emerald-300"><CheckCircle2 className="h-4 w-4" />{success}</p> : null}

      {!profiles.length || !selected || !playlist ? (
        <div className="border border-dashed border-zinc-800 p-10 text-center text-sm text-zinc-500">
          Nenhum perfil de Wallboard foi provisionado para este tenant.
        </div>
      ) : (
        <div className="grid gap-5 xl:grid-cols-[300px_1fr]">
          <aside className="border border-zinc-800 bg-zinc-950 p-3">
            {profiles.map((profile) => (
              <button
                key={profile.id}
                onClick={() => setSelectedId(profile.id)}
                className={`mb-2 w-full border p-4 text-left ${selected.id === profile.id ? "border-orange-500 bg-orange-950/20" : "border-zinc-800 bg-black"}`}
              >
                <p className="text-sm font-semibold text-white">{profile.name}</p>
                <p className="mt-1 text-xs text-zinc-500">{profile.wallboardType === "workforce" ? "Workforce" : "Infrastructure"} · {profile.refreshSeconds}s</p>
              </button>
            ))}
          </aside>

          <div className="space-y-5">
            <article className="border border-zinc-800 bg-zinc-950 p-5">
              <div className="mb-5 flex items-center gap-3 border-b border-zinc-800 pb-4">
                <MonitorUp className="h-5 w-5 text-orange-400" />
                <div><h2 className="font-semibold text-white">Comportamento da TV</h2><p className="text-xs text-zinc-500">Mudanças entram na próxima atualização do perfil.</p></div>
              </div>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <TextField
                  label="Nome do perfil / TV"
                  value={selected.name}
                  maxLength={120}
                  onChange={(name) => updateSelected({ name })}
                />
                <NumberField label="Atualização (segundos)" value={selected.refreshSeconds} min={5} max={3600} onChange={(value) => updateSelected({ refreshSeconds: value })} />
                <NumberField label="Rotação padrão (segundos)" value={playlist.defaultDurationSeconds} min={10} max={3600} onChange={(value) => updatePlaylist({ defaultDurationSeconds: value })} />
                <label className="text-sm text-zinc-400">Transição
                  <select value={playlist.transition} onChange={(event) => updatePlaylist({ transition: event.target.value as Playlist["transition"] })} className="mt-2 h-11 w-full border border-zinc-700 bg-black px-3 text-zinc-200">
                    <option value="none">Sem animação</option><option value="fade">Suave</option><option value="slide">Deslizamento</option>
                  </select>
                </label>
              </div>
              <div className="mt-5 flex flex-wrap gap-4">
                <Toggle label="Perfil habilitado" checked={selected.enabled} onChange={(enabled) => updateSelected({ enabled })} />
                <Toggle label="Rotação habilitada" checked={playlist.rotationEnabled} onChange={(rotationEnabled) => updatePlaylist({ rotationEnabled })} />
                <Toggle label="Tela cheia" checked={selected.fullscreen} onChange={(fullscreen) => updateSelected({ fullscreen })} />
                <Toggle label="Relógio" checked={selected.showClock} onChange={(showClock) => updateSelected({ showClock })} />
                <Toggle label="Última atualização" checked={selected.showLastUpdate} onChange={(showLastUpdate) => updateSelected({ showLastUpdate })} />
                <Toggle label="Estado da conexão" checked={selected.showConnectionStatus} onChange={(showConnectionStatus) => updateSelected({ showConnectionStatus })} />
                <Toggle label="Prevenção de burn-in" checked={selected.burnInPrevention} onChange={(burnInPrevention) => updateSelected({ burnInPrevention })} />
                <Toggle label="Alerta prioritário" checked={playlist.alertPriorityEnabled} onChange={(alertPriorityEnabled) => updatePlaylist({ alertPriorityEnabled })} />
              </div>
            </article>

            <article className="border border-zinc-800 bg-zinc-950 p-5">
              <div className="mb-5 flex items-center gap-3 border-b border-zinc-800 pb-4">
                <MonitorUp className="h-5 w-5 text-orange-400" />
                <div>
                  <h2 className="font-semibold text-white">Vulcan Command System</h2>
                  <p className="text-xs text-zinc-500">
                    Qualidade, movimento, abertura e fallback persistidos no perfil.
                  </p>
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <SelectField
                  label="Qualidade gráfica"
                  value={configText(selected.config.quality, "auto")}
                  options={[
                    ["auto", "Automática"],
                    ["low", "Low"],
                    ["balanced", "Balanced"],
                    ["cinematic", "Cinematic"],
                    ["4k", "4K Cinematic"]
                  ]}
                  onChange={(quality) => updateCommandConfig({ quality })}
                />
                <SelectField
                  label="Intensidade de movimento"
                  value={configText(selected.config.motionIntensity, "balanced")}
                  options={[
                    ["minimal", "Mínima"],
                    ["balanced", "Equilibrada"],
                    ["cinematic", "Cinematográfica"]
                  ]}
                  onChange={(motionIntensity) => updateCommandConfig({ motionIntensity })}
                />
                <SelectField
                  label="Transição de cena"
                  value={configText(selected.config.transitionStyle, "scan")}
                  options={[
                    ["scan", "Varredura"],
                    ["focus", "Mudança de foco"],
                    ["energy", "Linha de energia"],
                    ["rebuild", "Reconstrução de grid"]
                  ]}
                  onChange={(transitionStyle) => updateCommandConfig({ transitionStyle })}
                />
                <SelectField
                  label="Fallback gráfico"
                  value={configText(selected.config.fallbackMode, "automatic")}
                  options={[
                    ["automatic", "Automático"],
                    ["always-2d", "Sempre 2D"]
                  ]}
                  onChange={(fallbackMode) => updateCommandConfig({ fallbackMode })}
                />
                <NumberField
                  label="Intensidade visual (%)"
                  value={configNumber(selected.config.visualIntensity, 70)}
                  min={20}
                  max={100}
                  onChange={(visualIntensity) => updateCommandConfig({ visualIntensity })}
                />
                <NumberField
                  label="FPS alvo"
                  value={configNumber(selected.config.targetFps, 60)}
                  min={30}
                  max={60}
                  onChange={(targetFps) =>
                    updateCommandConfig({ targetFps: targetFps >= 45 ? 60 : 30 })
                  }
                />
                <NumberField
                  label="Abertura (segundos)"
                  value={configNumber(selected.config.openingDurationSeconds, 3)}
                  min={2}
                  max={5}
                  onChange={(openingDurationSeconds) =>
                    updateCommandConfig({ openingDurationSeconds })
                  }
                />
                <NumberField
                  label="Ocultar controles (segundos)"
                  value={configNumber(selected.config.controlsAutoHideSeconds, 5)}
                  min={2}
                  max={30}
                  onChange={(controlsAutoHideSeconds) =>
                    updateCommandConfig({ controlsAutoHideSeconds })
                  }
                />
                <NumberField
                  label="Takeover crítico (segundos)"
                  value={configNumber(selected.config.alertTakeoverSeconds, 45)}
                  min={10}
                  max={600}
                  onChange={(alertTakeoverSeconds) =>
                    updateCommandConfig({ alertTakeoverSeconds })
                  }
                />
                <SelectField
                  label="Modo da abertura"
                  value={configText(selected.config.openingMode, "full")}
                  options={[
                    ["full", "Completa"],
                    ["reduced", "Reduzida"]
                  ]}
                  onChange={(openingMode) => updateCommandConfig({ openingMode })}
                />
                <SelectField
                  label="Resolução-alvo"
                  value={configText(selected.config.targetResolution, "auto")}
                  options={[
                    ["auto", "Automática"],
                    ["1920x1080", "1920 × 1080"],
                    ["2560x1440", "2560 × 1440"],
                    ["3840x2160", "3840 × 2160"]
                  ]}
                  onChange={(targetResolution) => updateCommandConfig({ targetResolution })}
                />
                <TextField
                  label="Identificação física da TV"
                  value={configText(selected.config.displayName, "")}
                  maxLength={80}
                  placeholder="Ex.: TV Sala de Operações"
                  onChange={(displayName) => updateCommandConfig({ displayName })}
                />
              </div>
              <div className="mt-5 flex flex-wrap gap-4">
                <Toggle
                  label="Abertura cinematográfica"
                  checked={configBoolean(selected.config.openingEnabled, true)}
                  onChange={(openingEnabled) => updateCommandConfig({ openingEnabled })}
                />
                <Toggle
                  label="Critical Event Takeover"
                  checked={configBoolean(selected.config.alertTakeoverEnabled, true)}
                  onChange={(alertTakeoverEnabled) =>
                    updateCommandConfig({ alertTakeoverEnabled })
                  }
                />
                <Toggle
                  label="Mostrar logo"
                  checked={configBoolean(selected.config.showLogo, true)}
                  onChange={(showLogo) => updateCommandConfig({ showLogo })}
                />
                <Toggle
                  label="Mostrar filial"
                  checked={configBoolean(selected.config.showSite, true)}
                  onChange={(showSite) => updateCommandConfig({ showSite })}
                />
              </div>
              <p className="mt-4 border-l border-zinc-700 pl-3 text-xs leading-5 text-zinc-500">
                Áudio permanece desativado por padrão e não é habilitado por esta versão.
                AUTO reduz a qualidade quando o FPS cai e tenta recuperar gradualmente.
              </p>
            </article>

            <article className="border border-zinc-800 bg-zinc-950 p-5">
              <div className="mb-5 flex items-center gap-3 border-b border-zinc-800 pb-4">
                <MonitorUp className="h-5 w-5 text-orange-400" />
                <div>
                  <h2 className="font-semibold text-white">Janela de exibição</h2>
                  <p className="text-xs text-zinc-500">
                    Horário operacional persistido para a TV, no fuso America/Sao_Paulo.
                  </p>
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                <TextField
                  label="Início"
                  type="time"
                  value={configText(playlist.schedule.start, "00:00")}
                  onChange={(start) =>
                    updatePlaylist({ schedule: { ...playlist.schedule, start } })
                  }
                />
                <TextField
                  label="Fim"
                  type="time"
                  value={configText(playlist.schedule.end, "23:59")}
                  onChange={(end) =>
                    updatePlaylist({ schedule: { ...playlist.schedule, end } })
                  }
                />
                <NumberField
                  label="Retorno após alerta (segundos)"
                  value={playlist.autoReturnSeconds}
                  min={10}
                  max={86400}
                  onChange={(autoReturnSeconds) => updatePlaylist({ autoReturnSeconds })}
                />
              </div>
              <p className="mt-4 text-xs leading-5 text-zinc-500">
                A playlist continua segura fora da janela: esta versão registra a agenda para
                ativação controlada, sem desligar ou reiniciar a TV automaticamente.
              </p>
            </article>

            <article className="border border-zinc-800 bg-zinc-950">
              <div className="border-b border-zinc-800 p-5">
                <h2 className="font-semibold text-white">Cenas do Command Center</h2>
                <p className="mt-1 text-xs text-zinc-500">
                  Ordem e visibilidade persistidas no perfil; ao menos uma cena permanece ativa.
                </p>
              </div>
              <div className="divide-y divide-zinc-800">
                {orderedScenes(selected).map((scene, index, scenes) => {
                  const enabledScenes = configuredScenes(selected);
                  const enabled = enabledScenes.includes(scene);
                  const enabledIndex = enabledScenes.indexOf(scene);
                  return (
                    <div
                      key={scene}
                      className="grid gap-3 p-4 md:grid-cols-[auto_1fr_auto] md:items-center"
                    >
                      <div className="flex gap-1">
                        <button
                          disabled={!enabled || enabledIndex === 0}
                          onClick={() => moveScene(selected, scene, -1)}
                          className="grid h-9 w-9 place-items-center border border-zinc-700 text-zinc-300 disabled:opacity-30"
                          aria-label={`Subir ${SCENE_LABELS[scene]}`}
                        >
                          <ArrowUp className="h-4 w-4" />
                        </button>
                        <button
                          disabled={!enabled || enabledIndex === enabledScenes.length - 1}
                          onClick={() => moveScene(selected, scene, 1)}
                          className="grid h-9 w-9 place-items-center border border-zinc-700 text-zinc-300 disabled:opacity-30"
                          aria-label={`Descer ${SCENE_LABELS[scene]}`}
                        >
                          <ArrowDown className="h-4 w-4" />
                        </button>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white">
                          {SCENE_LABELS[scene] ?? scene}
                        </p>
                        <p className="mt-1 text-xs text-zinc-500">
                          Cena {String(index + 1).padStart(2, "0")} de {scenes.length}
                        </p>
                      </div>
                      <Toggle
                        label="Ativa"
                        checked={enabled}
                        onChange={(checked) => toggleScene(selected, scene, checked)}
                      />
                    </div>
                  );
                })}
              </div>
            </article>

            <article className="border border-zinc-800 bg-zinc-950">
              <div className="border-b border-zinc-800 p-5">
                <h2 className="font-semibold text-white">{playlist.name}</h2>
                <p className="mt-1 text-xs text-zinc-500">Ordem, filial, duração e visibilidade persistidas.</p>
              </div>
              <div className="divide-y divide-zinc-800">
                {[...playlist.items].sort((a, b) => a.position - b.position).map((item, index) => (
                  <div key={item.id} className="grid gap-3 p-4 md:grid-cols-[auto_1fr_150px_auto] md:items-center">
                    <div className="flex gap-1">
                      <button disabled={index === 0} onClick={() => moveItem(index, -1)} className="grid h-9 w-9 place-items-center border border-zinc-700 text-zinc-300 disabled:opacity-30" aria-label={`Subir ${item.title}`}><ArrowUp className="h-4 w-4" /></button>
                      <button disabled={index === playlist.items.length - 1} onClick={() => moveItem(index, 1)} className="grid h-9 w-9 place-items-center border border-zinc-700 text-zinc-300 disabled:opacity-30" aria-label={`Descer ${item.title}`}><ArrowDown className="h-4 w-4" /></button>
                    </div>
                    <div><p className="text-sm font-medium text-white">{item.title}</p><p className="mt-1 text-xs text-zinc-500">{item.siteName ?? "Todas as filiais"} · {item.panelKey}</p></div>
                    <NumberField label="Duração (s)" value={item.durationSeconds ?? playlist.defaultDurationSeconds} min={10} max={3600} onChange={(durationSeconds) => updateItem(item.id, { durationSeconds })} compact />
                    <Toggle label="Visível" checked={item.enabled} onChange={(enabled) => updateItem(item.id, { enabled })} />
                  </div>
                ))}
              </div>
            </article>

            <div className="flex items-center justify-between gap-4">
              <p className="flex items-center gap-2 text-xs text-zinc-500"><ShieldCheck className="h-4 w-4 text-emerald-400" />Alterações administrativas são auditadas.</p>
              <button onClick={() => void save()} disabled={saving} className="flex h-11 items-center gap-2 bg-orange-500 px-5 font-semibold text-black hover:bg-orange-400 disabled:opacity-50">
                {saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}Salvar configuração
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );

  function moveScene(profile: Profile, scene: string, direction: -1 | 1) {
    const scenes = configuredScenes(profile);
    const index = scenes.indexOf(scene);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= scenes.length) return;
    const next = [...scenes];
    [next[index], next[target]] = [next[target], next[index]];
    updateCommandConfig({ sceneSequence: next });
  }

  function toggleScene(profile: Profile, scene: string, enabled: boolean) {
    const scenes = configuredScenes(profile);
    if (!enabled && scenes.length === 1) return;
    const next = enabled
      ? [...scenes, scene]
      : scenes.filter((candidate) => candidate !== scene);
    updateCommandConfig({ sceneSequence: [...new Set(next)] });
  }
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return <label className="flex items-center gap-2 text-sm text-zinc-300"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="h-4 w-4 accent-orange-500" />{label}</label>;
}

function NumberField({ label, value, min, max, onChange, compact = false }: { label: string; value: number; min: number; max: number; onChange: (value: number) => void; compact?: boolean }) {
  return <label className={`${compact ? "text-xs" : "text-sm"} text-zinc-400`}>{label}<input type="number" min={min} max={max} value={value} onChange={(event) => onChange(Math.min(max, Math.max(min, Number(event.target.value))))} className="mt-2 h-11 w-full border border-zinc-700 bg-black px-3 text-zinc-200" /></label>;
}

function SelectField({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: string;
  options: Array<[string, string]>;
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-sm text-zinc-400">
      {label}
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 h-11 w-full border border-zinc-700 bg-black px-3 text-zinc-200"
      >
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>{optionLabel}</option>
        ))}
      </select>
    </label>
  );
}

function TextField({
  label,
  value,
  onChange,
  maxLength,
  placeholder,
  type = "text"
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  maxLength?: number;
  placeholder?: string;
  type?: "text" | "time";
}) {
  return (
    <label className="text-sm text-zinc-400">
      {label}
      <input
        type={type}
        value={value}
        maxLength={maxLength}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 h-11 w-full border border-zinc-700 bg-black px-3 text-zinc-200"
      />
    </label>
  );
}

function configText(value: unknown, fallback: string) {
  return typeof value === "string" && value ? value : fallback;
}

function configNumber(value: unknown, fallback: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function configBoolean(value: unknown, fallback: boolean) {
  return typeof value === "boolean" ? value : fallback;
}

function availableScenes(profile: Profile) {
  return profile.wallboardType === "workforce"
    ? [...WORKFORCE_SCENES]
    : [...INFRASTRUCTURE_SCENES];
}

function configuredScenes(profile: Profile) {
  const available = availableScenes(profile);
  if (!Array.isArray(profile.config.sceneSequence)) return available;
  const configured = profile.config.sceneSequence.filter(
    (scene): scene is string =>
      typeof scene === "string" && available.includes(scene as never)
  );
  return configured.length ? configured : available;
}

function orderedScenes(profile: Profile) {
  const configured = configuredScenes(profile);
  return [
    ...configured,
    ...availableScenes(profile).filter((scene) => !configured.includes(scene))
  ];
}
