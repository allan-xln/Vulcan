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
            enabled: selected.enabled,
            refreshSeconds: selected.refreshSeconds,
            fullscreen: selected.fullscreen,
            nightMode: selected.nightMode,
            burnInPrevention: selected.burnInPrevention,
            showClock: selected.showClock,
            showLastUpdate: selected.showLastUpdate,
            showConnectionStatus: selected.showConnectionStatus
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
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return <label className="flex items-center gap-2 text-sm text-zinc-300"><input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} className="h-4 w-4 accent-orange-500" />{label}</label>;
}

function NumberField({ label, value, min, max, onChange, compact = false }: { label: string; value: number; min: number; max: number; onChange: (value: number) => void; compact?: boolean }) {
  return <label className={`${compact ? "text-xs" : "text-sm"} text-zinc-400`}>{label}<input type="number" min={min} max={max} value={value} onChange={(event) => onChange(Math.min(max, Math.max(min, Number(event.target.value))))} className="mt-2 h-11 w-full border border-zinc-700 bg-black px-3 text-zinc-200" /></label>;
}
