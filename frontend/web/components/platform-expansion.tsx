"use client";

import {
  Activity,
  AlertTriangle,
  Boxes,
  Building2,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  Clock3,
  Database,
  Gauge,
  Globe2,
  LoaderCircle,
  Network,
  Plus,
  Radar,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  Sparkles,
  Unplug,
  X
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

type DataOrigin = "real" | "simulated" | "imported";

type InfrastructureOverview = {
  tenantId: string;
  dataOrigin: "real" | "simulated";
  generatedAt: string;
  sites: number;
  networks: number;
  assets: number;
  onlineAssets: number;
  degradedAssets: number;
  offlineAssets: number;
  unknownAssets: number;
  openIncidents: number;
  eventsLast24h: number;
  pendingDiscoveries: number;
  healthScore: number | null;
  scoreComponents: {
    key: string;
    label: string;
    value: number;
    maxPoints: number;
    points: number;
    formula: string;
  }[];
};

type Site = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  timezone: string;
  status: string;
  tags: string[];
  dataOrigin: DataOrigin;
};

type InfrastructureNetwork = {
  id: string;
  siteId: string;
  siteName: string | null;
  name: string;
  networkCidr: string;
  gateway: string | null;
  vlanId: number | null;
  discoveryAllowed: boolean;
  status: string;
  dataOrigin: DataOrigin;
};

type Asset = {
  id: string;
  siteId: string | null;
  siteName: string | null;
  networkId: string | null;
  networkName: string | null;
  assetType: string;
  name: string;
  hostname: string | null;
  manufacturer: string | null;
  model: string | null;
  ipAddress: string | null;
  status: string;
  criticality: string;
  lastSeenAt: string | null;
  dataOrigin: DataOrigin;
};

type DiscoveryPolicy = {
  id: string;
  siteId: string;
  siteName: string | null;
  name: string;
  enabled: boolean;
  readOnly: boolean;
  safeMode: boolean;
  allowedNetworks: string[];
  allowedProtocols: string[];
  frequencyMinutes: number;
  maxTargets: number;
  dataOrigin: DataOrigin;
};

type DiscoveryRun = {
  id: string;
  policyId: string;
  policyName: string | null;
  status: string;
  mode: "read_only";
  targetsPlanned: number;
  targetsScanned: number;
  findingsCount: number;
  errorCount: number;
  createdAt: string;
  dataOrigin: DataOrigin;
};

type IntegrationAdapter = {
  adapterType: string;
  name: string;
  description: string;
  capabilities: string[];
  readOnly: boolean;
  implemented: boolean;
};

type Incident = {
  id: string;
  title: string;
  summary: string;
  impact: string;
  severity: string;
  status: string;
  probableCause: string | null;
  confidence: number | null;
  recommendation: string | null;
  firstOccurredAt: string;
  lastOccurredAt: string;
  source: string;
};

type PlatformHealth = {
  status: "ok" | "degraded" | "unavailable";
  service: string;
  timestamp: string;
  dataOrigin: "real" | "simulated";
  checks: {
    name: string;
    status: "ok" | "degraded" | "unavailable" | "disabled";
    detail: string;
    latencyMs: number | null;
  }[];
};

type VersionInfo = {
  product: "Vulcan";
  service: string;
  version: string;
  commit: string;
  build: string;
  eventSchemaVersion: string;
};

export type TimelineEvent = {
  eventId: string;
  siteId: string | null;
  assetId: string | null;
  agentId: string | null;
  source: string;
  sourceType: string;
  eventType: string;
  category: string;
  severity: string;
  occurredAt: string;
  receivedAt: string;
  clockDriftMs: number | null;
  offlineBuffered: boolean;
  actor: Record<string, unknown>;
  device: Record<string, unknown>;
  context: Record<string, unknown>;
  metrics: Record<string, unknown>;
  message: string;
  technicalMessage: string | null;
  correlationId: string | null;
  confidence: number | null;
  privacyClassification: string;
  dataOrigin: DataOrigin;
};

type TimelinePage = {
  items: TimelineEvent[];
  nextCursor: string | null;
  hasMore: boolean;
  dataOrigin: "real" | "simulated";
};

type InfrastructureSection = "overview" | "inventory" | "discovery" | "incidents" | "integrations" | "platform";
type CreateMode = "site" | "network" | "asset" | "discovery" | null;

type PlatformProps = {
  apiUrl: string;
  tenantId: string;
  token: string;
};

const assetTypeLabels: Record<string, string> = {
  workstation: "Estação",
  server: "Servidor",
  switch: "Switch",
  access_point: "Ponto de acesso",
  firewall: "Firewall",
  printer: "Impressora",
  ups: "Nobreak",
  controller: "Controlador",
  gateway: "Gateway",
  service: "Serviço",
  application: "Aplicação",
  storage: "Storage",
  virtual_machine: "Máquina virtual",
  container: "Container",
  other: "Outro"
};

const assetTypes = Object.entries(assetTypeLabels);

function apiHeaders(token: string, tenantId: string, json = false): HeadersInit {
  return {
    Authorization: `Bearer ${token}`,
    "X-Tenant-Id": tenantId,
    ...(json ? { "Content-Type": "application/json" } : {})
  };
}

async function readApiError(response: Response): Promise<string> {
  const payload = (await response.json().catch(() => null)) as { detail?: unknown } | null;
  if (typeof payload?.detail === "string") {
    return payload.detail;
  }
  if (Array.isArray(payload?.detail)) {
    return payload.detail
      .map((item) => (typeof item === "object" && item && "msg" in item ? String(item.msg) : String(item)))
      .join(" ");
  }
  return `A API respondeu com status ${response.status}.`;
}

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
      ...apiHeaders(token, tenantId, Boolean(init?.body)),
      ...init?.headers
    }
  });
  if (!response.ok) {
    throw new Error(await readApiError(response));
  }
  return (await response.json()) as T;
}

function OriginBadge({ origin }: { origin: DataOrigin }) {
  const simulated = origin === "simulated";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${
        simulated
          ? "border-amber-400/30 bg-amber-400/10 text-amber-200"
          : "border-emerald-400/25 bg-emerald-400/10 text-emerald-200"
      }`}
    >
      <CircleDot className="h-3 w-3" />
      {simulated ? "Simulado" : origin === "imported" ? "Importado" : "Real"}
    </span>
  );
}

function StatusPill({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const tone = ["online", "completed", "active", "healthy", "implemented"].includes(normalized)
    ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-200"
    : ["degraded", "warning", "queued", "running", "pending_review"].includes(normalized)
      ? "border-amber-400/25 bg-amber-400/10 text-amber-200"
      : ["offline", "failed", "critical", "error"].includes(normalized)
        ? "border-red-400/25 bg-red-400/10 text-red-200"
        : "border-zinc-700 bg-zinc-900 text-zinc-300";
  return (
    <span className={`inline-flex rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] ${tone}`}>
      {status.replaceAll("_", " ")}
    </span>
  );
}

function EmptyState({
  icon: Icon,
  title,
  description,
  action
}: {
  icon: typeof Boxes;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="grid min-h-52 place-items-center rounded-2xl border border-dashed border-zinc-800 bg-black/20 px-6 py-10 text-center">
      <div>
        <Icon className="mx-auto h-8 w-8 text-orange-300" />
        <h3 className="mt-4 text-base font-semibold text-white">{title}</h3>
        <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-zinc-400">{description}</p>
        {action ? <div className="mt-5">{action}</div> : null}
      </div>
    </div>
  );
}

function LoadingSurface() {
  return (
    <div className="grid gap-4 md:grid-cols-3" aria-label="Carregando infraestrutura">
      {[0, 1, 2, 3, 4, 5].map((item) => (
        <div key={item} className="h-32 animate-pulse rounded-2xl border border-zinc-800 bg-zinc-900/55" />
      ))}
    </div>
  );
}

function Field({
  label,
  children
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="grid gap-2 text-xs font-medium uppercase tracking-[0.12em] text-zinc-400">
      {label}
      {children}
    </label>
  );
}

const inputClass =
  "h-11 w-full rounded-xl border border-zinc-700 bg-black/55 px-3 text-sm text-white outline-none transition placeholder:text-zinc-600 focus:border-orange-400/60 focus:ring-2 focus:ring-orange-400/10";

function CreatePanel({
  mode,
  sites,
  networks,
  busy,
  error,
  onClose,
  onSubmit
}: {
  mode: Exclude<CreateMode, null>;
  sites: Site[];
  networks: InfrastructureNetwork[];
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (payload: Record<string, unknown>) => Promise<void>;
}) {
  const [siteId, setSiteId] = useState(sites[0]?.id ?? "");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (mode === "site") {
      await onSubmit({
        code: String(form.get("code") ?? ""),
        name: String(form.get("name") ?? ""),
        description: String(form.get("description") ?? "") || null,
        timezone: "America/Sao_Paulo",
        address: {},
        tags: []
      });
      return;
    }
    if (mode === "network") {
      const vlan = String(form.get("vlanId") ?? "");
      await onSubmit({
        siteId: String(form.get("siteId") ?? ""),
        name: String(form.get("name") ?? ""),
        networkCidr: String(form.get("networkCidr") ?? ""),
        gateway: String(form.get("gateway") ?? "") || null,
        vlanId: vlan ? Number(vlan) : null,
        dnsServers: [],
        dhcpEnabled: false,
        discoveryAllowed: false,
        tags: []
      });
      return;
    }
    if (mode === "asset") {
      const selectedSite = String(form.get("siteId") ?? "") || null;
      const selectedNetwork = String(form.get("networkId") ?? "") || null;
      await onSubmit({
        siteId: selectedSite,
        networkId: selectedNetwork,
        assetType: String(form.get("assetType") ?? "other"),
        name: String(form.get("name") ?? ""),
        hostname: String(form.get("hostname") ?? "") || null,
        ipAddress: String(form.get("ipAddress") ?? "") || null,
        manufacturer: String(form.get("manufacturer") ?? "") || null,
        model: String(form.get("model") ?? "") || null,
        status: String(form.get("status") ?? "unknown"),
        criticality: String(form.get("criticality") ?? "medium"),
        tags: []
      });
      return;
    }
    await onSubmit({
      siteId: String(form.get("siteId") ?? ""),
      name: String(form.get("name") ?? ""),
      enabled: false,
      allowedNetworks: [String(form.get("networkCidr") ?? "")],
      deniedNetworks: [],
      excludedAddresses: [],
      allowedProtocols: ["icmp", "dns", "reverse_dns"],
      allowedTcpPorts: [],
      frequencyMinutes: 60,
      concurrency: 8,
      timeoutMs: 750,
      maxTargets: Number(form.get("maxTargets") ?? 256)
    });
  }

  const title = {
    site: "Cadastrar site",
    network: "Cadastrar rede",
    asset: "Cadastrar ativo",
    discovery: "Criar política segura"
  }[mode];
  const selectedSiteNetworks = networks.filter((network) => !siteId || network.siteId === siteId);

  return (
    <div className="fixed inset-0 z-[80] grid place-items-center bg-black/80 p-4 backdrop-blur-sm">
      <form
        className="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-orange-400/20 bg-[#101010] p-6 shadow-2xl"
        onSubmit={(event) => void submit(event)}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-orange-300">Vulcan Infrastructure</p>
            <h2 className="mt-2 text-xl font-semibold text-white">{title}</h2>
          </div>
          <button type="button" onClick={onClose} className="rounded-lg border border-zinc-800 p-2 text-zinc-400 hover:text-white" aria-label="Fechar">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {mode === "site" ? (
            <>
              <Field label="Código">
                <input className={inputClass} name="code" placeholder="SJP-01" minLength={2} required />
              </Field>
              <Field label="Nome">
                <input className={inputClass} name="name" placeholder="Unidade São José" minLength={2} required />
              </Field>
              <div className="sm:col-span-2">
                <Field label="Descrição">
                  <input className={inputClass} name="description" placeholder="Função operacional da unidade" />
                </Field>
              </div>
            </>
          ) : null}

          {mode === "network" || mode === "discovery" ? (
            <>
              <Field label="Site">
                <select className={inputClass} name="siteId" value={siteId} onChange={(event) => setSiteId(event.target.value)} required>
                  <option value="">Selecione</option>
                  {sites.map((site) => (
                    <option key={site.id} value={site.id}>{site.name}</option>
                  ))}
                </select>
              </Field>
              <Field label={mode === "network" ? "Nome da rede" : "Nome da política"}>
                <input className={inputClass} name="name" placeholder={mode === "network" ? "Rede corporativa" : "Descoberta controlada"} minLength={2} required />
              </Field>
              <Field label="Rede permitida (CIDR)">
                <input className={inputClass} name="networkCidr" placeholder="192.168.10.0/24" required />
              </Field>
              {mode === "network" ? (
                <>
                  <Field label="Gateway">
                    <input className={inputClass} name="gateway" placeholder="192.168.10.1" />
                  </Field>
                  <Field label="VLAN">
                    <input className={inputClass} name="vlanId" type="number" min={1} max={4094} placeholder="10" />
                  </Field>
                </>
              ) : (
                <Field label="Limite de endereços">
                  <input className={inputClass} name="maxTargets" type="number" min={1} max={4096} defaultValue={256} required />
                </Field>
              )}
            </>
          ) : null}

          {mode === "asset" ? (
            <>
              <Field label="Nome">
                <input className={inputClass} name="name" placeholder="Servidor ERP" minLength={2} required />
              </Field>
              <Field label="Tipo">
                <select className={inputClass} name="assetType" defaultValue="workstation">
                  {assetTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              </Field>
              <Field label="Site">
                <select className={inputClass} name="siteId" value={siteId} onChange={(event) => setSiteId(event.target.value)}>
                  <option value="">Sem vínculo</option>
                  {sites.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}
                </select>
              </Field>
              <Field label="Rede">
                <select className={inputClass} name="networkId">
                  <option value="">Sem vínculo</option>
                  {selectedSiteNetworks.map((network) => <option key={network.id} value={network.id}>{network.name}</option>)}
                </select>
              </Field>
              <Field label="Hostname">
                <input className={inputClass} name="hostname" placeholder="SRV-ERP-01" />
              </Field>
              <Field label="Endereço IP">
                <input className={inputClass} name="ipAddress" placeholder="192.168.10.20" />
              </Field>
              <Field label="Fabricante">
                <input className={inputClass} name="manufacturer" placeholder="Dell, HP, Cisco..." />
              </Field>
              <Field label="Modelo">
                <input className={inputClass} name="model" placeholder="Modelo do equipamento" />
              </Field>
              <Field label="Estado atual">
                <select className={inputClass} name="status" defaultValue="unknown">
                  <option value="unknown">Desconhecido</option>
                  <option value="online">Online</option>
                  <option value="degraded">Degradado</option>
                  <option value="offline">Offline</option>
                  <option value="maintenance">Manutenção</option>
                </select>
              </Field>
              <Field label="Criticidade">
                <select className={inputClass} name="criticality" defaultValue="medium">
                  <option value="low">Baixa</option>
                  <option value="medium">Média</option>
                  <option value="high">Alta</option>
                  <option value="critical">Crítica</option>
                </select>
              </Field>
            </>
          ) : null}
        </div>

        {mode === "discovery" ? (
          <div className="mt-5 rounded-xl border border-emerald-400/20 bg-emerald-400/5 p-4 text-sm leading-6 text-emerald-100">
            A política será criada desativada, em modo seguro e somente leitura. Nenhuma varredura começa automaticamente.
          </div>
        ) : null}
        {error ? <p className="mt-4 rounded-xl border border-red-400/20 bg-red-400/10 p-3 text-sm text-red-200">{error}</p> : null}

        <div className="mt-6 flex justify-end gap-3">
          <button type="button" onClick={onClose} className="h-11 rounded-xl border border-zinc-700 px-4 text-sm text-zinc-300 hover:border-zinc-500">
            Cancelar
          </button>
          <button disabled={busy} className="flex h-11 items-center gap-2 rounded-xl bg-orange-500 px-5 text-sm font-semibold text-black disabled:opacity-50">
            {busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
            Salvar
          </button>
        </div>
      </form>
    </div>
  );
}

export function InfrastructureView({ apiUrl, tenantId, token }: PlatformProps) {
  const [section, setSection] = useState<InfrastructureSection>("overview");
  const [overview, setOverview] = useState<InfrastructureOverview | null>(null);
  const [sites, setSites] = useState<Site[]>([]);
  const [networks, setNetworks] = useState<InfrastructureNetwork[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [policies, setPolicies] = useState<DiscoveryPolicy[]>([]);
  const [runs, setRuns] = useState<DiscoveryRun[]>([]);
  const [adapters, setAdapters] = useState<IntegrationAdapter[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [health, setHealth] = useState<PlatformHealth | null>(null);
  const [version, setVersion] = useState<VersionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createMode, setCreateMode] = useState<CreateMode>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const load = useCallback(async (quiet = false) => {
    if (quiet) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const [
        nextOverview,
        nextSites,
        nextNetworks,
        nextAssets,
        nextPolicies,
        nextRuns,
        nextAdapters,
        nextIncidents,
        nextHealth,
        nextVersion
      ] =
        await Promise.all([
          fetchJson<InfrastructureOverview>(apiUrl, "/infrastructure/overview", token, tenantId),
          fetchJson<Site[]>(apiUrl, "/infrastructure/sites", token, tenantId),
          fetchJson<InfrastructureNetwork[]>(apiUrl, "/infrastructure/networks", token, tenantId),
          fetchJson<Asset[]>(apiUrl, "/infrastructure/assets", token, tenantId),
          fetchJson<DiscoveryPolicy[]>(apiUrl, "/infrastructure/discovery/policies", token, tenantId),
          fetchJson<DiscoveryRun[]>(apiUrl, "/infrastructure/discovery/runs?limit=20", token, tenantId),
          fetchJson<IntegrationAdapter[]>(apiUrl, "/infrastructure/integrations/catalog", token, tenantId),
          fetchJson<Incident[]>(apiUrl, "/incidents", token, tenantId),
          fetchJson<PlatformHealth>(apiUrl, "/healthz", token, tenantId),
          fetchJson<VersionInfo>(apiUrl, "/version", token, tenantId)
        ]);
      setOverview(nextOverview);
      setSites(nextSites);
      setNetworks(nextNetworks);
      setAssets(nextAssets);
      setPolicies(nextPolicies);
      setRuns(nextRuns);
      setAdapters(nextAdapters);
      setIncidents(nextIncidents);
      setHealth(nextHealth);
      setVersion(nextVersion);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível carregar a infraestrutura.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [apiUrl, tenantId, token]);

  useEffect(() => {
    void load();
  }, [load]);

  const filteredAssets = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("pt-BR");
    if (!normalized) return assets;
    return assets.filter((asset) =>
      [asset.name, asset.hostname, asset.ipAddress, asset.siteName, asset.manufacturer, asset.assetType]
        .filter(Boolean)
        .some((value) => String(value).toLocaleLowerCase("pt-BR").includes(normalized))
    );
  }, [assets, query]);

  async function create(payload: Record<string, unknown>) {
    if (!createMode) return;
    setSaving(true);
    setSaveError(null);
    const endpoint = {
      site: "/infrastructure/sites",
      network: "/infrastructure/networks",
      asset: "/infrastructure/assets",
      discovery: "/infrastructure/discovery/policies"
    }[createMode];
    try {
      await fetchJson(apiUrl, endpoint, token, tenantId, {
        method: "POST",
        body: JSON.stringify({ tenantId, ...payload })
      });
      setCreateMode(null);
      await load(true);
    } catch (reason) {
      setSaveError(reason instanceof Error ? reason.message : "Não foi possível salvar.");
    } finally {
      setSaving(false);
    }
  }

  async function queueDiscovery(policy: DiscoveryPolicy) {
    setError(null);
    try {
      await fetchJson(apiUrl, "/infrastructure/discovery/runs", token, tenantId, {
        method: "POST",
        body: JSON.stringify({ tenantId, policyId: policy.id })
      });
      await load(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível agendar a descoberta.");
    }
  }

  async function updateDiscoveryState(policy: DiscoveryPolicy) {
    const enabling = !policy.enabled;
    if (
      enabling
      && !window.confirm(
        `Aprovar a política "${policy.name}"? Ela continuará somente leitura e ainda dependerá do serviço global de descoberta.`
      )
    ) {
      return;
    }
    setError(null);
    try {
      await fetchJson(apiUrl, `/infrastructure/discovery/policies/${policy.id}`, token, tenantId, {
        method: "PATCH",
        body: JSON.stringify({ tenantId, enabled: enabling })
      });
      await load(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível alterar a política.");
    }
  }

  const navigation: { key: InfrastructureSection; label: string; icon: typeof Gauge }[] = [
    { key: "overview", label: "Visão geral", icon: Gauge },
    { key: "inventory", label: "Ativos e redes", icon: Boxes },
    { key: "discovery", label: "Descoberta", icon: Radar },
    { key: "incidents", label: "Incidentes", icon: AlertTriangle },
    { key: "integrations", label: "Integrações", icon: Unplug },
    { key: "platform", label: "Saúde da plataforma", icon: Activity }
  ];

  return (
    <section className="mt-5 space-y-5" aria-labelledby="infrastructure-title">
      <div className="overflow-hidden rounded-3xl border border-zinc-800 bg-[radial-gradient(circle_at_top_right,rgba(249,115,22,0.12),transparent_35%),rgba(10,10,10,0.88)] p-6 md:p-8">
        <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-orange-300">Vulcan Infrastructure</p>
              {overview ? <OriginBadge origin={overview.dataOrigin} /> : null}
            </div>
            <h1 id="infrastructure-title" className="mt-3 max-w-3xl text-2xl font-semibold tracking-tight text-white md:text-4xl">
              Infraestrutura explicada pelo impacto na operação
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-400">
              Sites, redes e ativos no mesmo contexto das pessoas e do trabalho. Descoberta permanece desativada até aprovação explícita.
            </p>
          </div>
          <button
            onClick={() => void load(true)}
            disabled={refreshing}
            className="flex h-11 items-center justify-center gap-2 rounded-xl border border-zinc-700 bg-black/30 px-4 text-sm text-zinc-200 hover:border-orange-400/40 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            Atualizar
          </button>
        </div>
        <nav className="mt-7 flex gap-2 overflow-x-auto pb-1" aria-label="Áreas de infraestrutura">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                onClick={() => setSection(item.key)}
                className={`flex shrink-0 items-center gap-2 rounded-xl border px-4 py-2.5 text-sm transition ${
                  section === item.key
                    ? "border-orange-400/40 bg-orange-400/12 text-orange-100"
                    : "border-zinc-800 bg-black/25 text-zinc-400 hover:text-white"
                }`}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </button>
            );
          })}
        </nav>
      </div>

      {error ? (
        <div role="alert" className="flex items-start gap-3 rounded-2xl border border-red-400/20 bg-red-400/8 p-4 text-sm text-red-100">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div><strong>Falha ao consultar a plataforma.</strong><p className="mt-1 text-red-200/80">{error}</p></div>
        </div>
      ) : null}

      {loading ? <LoadingSurface /> : null}

      {!loading && section === "overview" && overview ? (
        <div className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
            {[
              { label: "Sites", value: overview.sites, icon: Building2 },
              { label: "Ativos", value: overview.assets, icon: Server },
              { label: "Online", value: overview.onlineAssets, icon: CheckCircle2 },
              { label: "Degradados", value: overview.degradedAssets, icon: AlertTriangle },
              { label: "Incidentes", value: overview.openIncidents, icon: Activity },
              { label: "Eventos 24h", value: overview.eventsLast24h, icon: Clock3 }
            ].map((metric) => {
              const Icon = metric.icon;
              return (
                <article key={metric.label} className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-4">
                  <Icon className="h-4 w-4 text-orange-300" />
                  <p className="mt-5 text-2xl font-semibold text-white">{metric.value.toLocaleString("pt-BR")}</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.14em] text-zinc-500">{metric.label}</p>
                </article>
              );
            })}
          </div>

          <div className="grid gap-5 xl:grid-cols-[0.8fr_1.2fr]">
            <article className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">Saúde transparente</p>
                  <p className="mt-2 text-4xl font-semibold text-white">{overview.healthScore ?? "—"}</p>
                </div>
                <Gauge className="h-7 w-7 text-orange-300" />
              </div>
              {overview.healthScore === null ? (
                <p className="mt-5 text-sm leading-6 text-zinc-400">Cadastre ativos e envie telemetria para calcular a saúde. O Vulcan não atribui uma nota sem evidências.</p>
              ) : (
                <div className="mt-5 h-2 overflow-hidden rounded-full bg-zinc-900">
                  <div className="h-full rounded-full bg-gradient-to-r from-orange-500 to-amber-300" style={{ width: `${overview.healthScore}%` }} />
                </div>
              )}
            </article>
            <article className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-6">
              <p className="text-xs uppercase tracking-[0.18em] text-zinc-500">Como a nota é calculada</p>
              {overview.scoreComponents.length ? (
                <div className="mt-4 divide-y divide-zinc-800">
                  {overview.scoreComponents.map((component) => (
                    <div key={component.key} className="grid gap-2 py-4 first:pt-0 md:grid-cols-[1fr_auto]">
                      <div><p className="text-sm font-medium text-white">{component.label}</p><p className="mt-1 text-xs leading-5 text-zinc-500">{component.formula}</p></div>
                      <p className="text-sm text-orange-200">{component.points.toLocaleString("pt-BR")} / {component.maxPoints}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-sm text-zinc-400">Os componentes aparecerão quando existirem ativos monitorados.</p>
              )}
            </article>
          </div>

          <div className="grid gap-5 lg:grid-cols-3">
            <article className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-5">
              <p className="text-xs uppercase tracking-[0.16em] text-zinc-500">Organização</p>
              <p className="mt-3 text-sm leading-6 text-zinc-300">{overview.sites} sites e {overview.networks} redes cadastradas.</p>
              <button onClick={() => setSection("inventory")} className="mt-5 flex items-center gap-2 text-sm text-orange-300">Gerenciar inventário <ChevronRight className="h-4 w-4" /></button>
            </article>
            <article className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-5">
              <p className="text-xs uppercase tracking-[0.16em] text-zinc-500">Descobertas pendentes</p>
              <p className="mt-3 text-sm leading-6 text-zinc-300">{overview.pendingDiscoveries} identificações aguardando revisão humana.</p>
              <button onClick={() => setSection("discovery")} className="mt-5 flex items-center gap-2 text-sm text-orange-300">Abrir descoberta <ChevronRight className="h-4 w-4" /></button>
            </article>
            <article className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-5">
              <p className="text-xs uppercase tracking-[0.16em] text-zinc-500">Impacto operacional</p>
              <p className="mt-3 text-sm leading-6 text-zinc-300">Eventos de pessoas e infraestrutura já compartilham a mesma timeline canônica.</p>
              <div className="mt-5 flex items-center gap-2 text-sm text-emerald-300"><ShieldCheck className="h-4 w-4" /> Isolado por tenant</div>
            </article>
          </div>
        </div>
      ) : null}

      {!loading && section === "inventory" ? (
        <div className="space-y-5">
          <div className="flex flex-col justify-between gap-3 rounded-2xl border border-zinc-800 bg-zinc-950/70 p-4 sm:flex-row sm:items-center">
            <div className="relative min-w-0 flex-1 sm:max-w-md">
              <Search className="absolute left-3 top-3.5 h-4 w-4 text-zinc-500" />
              <input value={query} onChange={(event) => setQuery(event.target.value)} className={`${inputClass} pl-10`} placeholder="Buscar ativo, hostname, IP ou site" />
            </div>
            <div className="flex flex-wrap gap-2">
              <button onClick={() => setCreateMode("site")} className="flex h-10 items-center gap-2 rounded-xl border border-zinc-700 px-3 text-xs text-zinc-200"><Plus className="h-4 w-4" /> Site</button>
              <button onClick={() => setCreateMode("network")} disabled={!sites.length} className="flex h-10 items-center gap-2 rounded-xl border border-zinc-700 px-3 text-xs text-zinc-200 disabled:opacity-40"><Plus className="h-4 w-4" /> Rede</button>
              <button onClick={() => setCreateMode("asset")} className="flex h-10 items-center gap-2 rounded-xl bg-orange-500 px-3 text-xs font-semibold text-black"><Plus className="h-4 w-4" /> Ativo</button>
            </div>
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <article className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-5">
              <div className="flex items-center justify-between"><h2 className="font-semibold text-white">Sites</h2><span className="text-xs text-zinc-500">{sites.length}</span></div>
              {sites.length ? <div className="mt-4 space-y-2">{sites.map((site) => (
                <div key={site.id} className="flex items-center justify-between gap-4 rounded-xl border border-zinc-800 bg-black/30 p-3">
                  <div className="min-w-0"><p className="truncate text-sm font-medium text-white">{site.name}</p><p className="mt-1 text-xs text-zinc-500">{site.code} · {site.timezone}</p></div>
                  <OriginBadge origin={site.dataOrigin} />
                </div>
              ))}</div> : <p className="mt-4 text-sm text-zinc-500">Nenhum site cadastrado.</p>}
            </article>
            <article className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-5">
              <div className="flex items-center justify-between"><h2 className="font-semibold text-white">Redes</h2><span className="text-xs text-zinc-500">{networks.length}</span></div>
              {networks.length ? <div className="mt-4 space-y-2">{networks.map((network) => (
                <div key={network.id} className="flex items-center justify-between gap-4 rounded-xl border border-zinc-800 bg-black/30 p-3">
                  <div className="min-w-0"><p className="truncate text-sm font-medium text-white">{network.name}</p><p className="mt-1 text-xs text-zinc-500">{network.networkCidr}{network.vlanId ? ` · VLAN ${network.vlanId}` : ""} · {network.siteName}</p></div>
                  <StatusPill status={network.discoveryAllowed ? "discovery allowed" : "manual"} />
                </div>
              ))}</div> : <p className="mt-4 text-sm text-zinc-500">Nenhuma rede cadastrada.</p>}
            </article>
          </div>

          <article className="overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-950/70">
            <div className="flex items-center justify-between border-b border-zinc-800 p-5"><h2 className="font-semibold text-white">Inventário de ativos</h2><span className="text-xs text-zinc-500">{filteredAssets.length} resultados</span></div>
            {filteredAssets.length ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[800px] text-left text-sm">
                  <thead className="bg-black/35 text-[10px] uppercase tracking-[0.16em] text-zinc-500"><tr><th className="px-5 py-3">Ativo</th><th className="px-5 py-3">Local</th><th className="px-5 py-3">Rede</th><th className="px-5 py-3">Criticidade</th><th className="px-5 py-3">Estado</th><th className="px-5 py-3">Origem</th></tr></thead>
                  <tbody className="divide-y divide-zinc-800">
                    {filteredAssets.map((asset) => (
                      <tr key={asset.id} className="hover:bg-white/[0.02]">
                        <td className="px-5 py-4"><p className="font-medium text-white">{asset.name}</p><p className="mt-1 text-xs text-zinc-500">{assetTypeLabels[asset.assetType] ?? asset.assetType} · {asset.hostname ?? asset.ipAddress ?? "sem identificação técnica"}</p></td>
                        <td className="px-5 py-4 text-zinc-300">{asset.siteName ?? "Não vinculado"}</td>
                        <td className="px-5 py-4 text-zinc-300">{asset.networkName ?? "Não vinculada"}</td>
                        <td className="px-5 py-4"><StatusPill status={asset.criticality} /></td>
                        <td className="px-5 py-4"><StatusPill status={asset.status} /></td>
                        <td className="px-5 py-4"><OriginBadge origin={asset.dataOrigin} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState icon={Server} title="Nenhum ativo encontrado" description={assets.length ? "A busca não encontrou ativos." : "Cadastre o primeiro ativo para formar o inventário operacional."} action={!assets.length ? <button onClick={() => setCreateMode("asset")} className="rounded-xl bg-orange-500 px-4 py-2 text-sm font-semibold text-black">Cadastrar ativo</button> : null} />
            )}
          </article>
        </div>
      ) : null}

      {!loading && section === "discovery" ? (
        <div className="space-y-5">
          <div className="flex flex-col justify-between gap-4 rounded-2xl border border-emerald-400/15 bg-emerald-400/[0.04] p-5 sm:flex-row sm:items-center">
            <div className="flex gap-3"><ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-emerald-300" /><div><h2 className="font-semibold text-white">Somente leitura por desenho</h2><p className="mt-1 text-sm leading-6 text-zinc-400">Ping, DNS e conexões TCP limitadas. Sem alteração remota e sem aprovação automática de ativos.</p></div></div>
            <button disabled={!sites.length} onClick={() => setCreateMode("discovery")} className="flex h-10 shrink-0 items-center justify-center gap-2 rounded-xl bg-orange-500 px-4 text-xs font-semibold text-black disabled:opacity-40"><Plus className="h-4 w-4" /> Nova política</button>
          </div>
          {policies.length ? (
            <div className="grid gap-4 lg:grid-cols-2">
              {policies.map((policy) => (
                <article key={policy.id} className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-5">
                  <div className="flex items-start justify-between gap-3"><div><h3 className="font-medium text-white">{policy.name}</h3><p className="mt-1 text-xs text-zinc-500">{policy.siteName}</p></div><StatusPill status={policy.enabled ? "active" : "disabled"} /></div>
                  <div className="mt-4 grid gap-2 text-xs text-zinc-400 sm:grid-cols-2"><p>Escopo: <span className="text-zinc-200">{policy.allowedNetworks.join(", ")}</span></p><p>Limite: <span className="text-zinc-200">{policy.maxTargets} alvos</span></p><p>Protocolos: <span className="text-zinc-200">{policy.allowedProtocols.join(", ")}</span></p><p>Modo: <span className="text-emerald-200">somente leitura</span></p></div>
                  <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                    <OriginBadge origin={policy.dataOrigin} />
                    <div className="flex gap-2">
                      <button onClick={() => void updateDiscoveryState(policy)} className="rounded-xl border border-zinc-700 px-3 py-2 text-xs text-zinc-200">
                        {policy.enabled ? "Desativar" : "Aprovar e ativar"}
                      </button>
                      <button disabled={!policy.enabled} onClick={() => void queueDiscovery(policy)} className="rounded-xl border border-zinc-700 px-3 py-2 text-xs text-zinc-200 disabled:cursor-not-allowed disabled:opacity-35">Agendar execução</button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState icon={Radar} title="Nenhuma política de descoberta" description="Defina explicitamente o site, a rede permitida e o limite. A política nasce desativada e auditada." />
          )}
          <article className="overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-950/70">
            <div className="border-b border-zinc-800 p-5"><h2 className="font-semibold text-white">Execuções recentes</h2></div>
            {runs.length ? <div className="divide-y divide-zinc-800">{runs.map((run) => (
              <div key={run.id} className="grid gap-3 p-5 text-sm md:grid-cols-[1fr_auto_auto_auto] md:items-center"><div><p className="text-white">{run.policyName ?? "Política removida"}</p><p className="mt-1 text-xs text-zinc-500">{new Date(run.createdAt).toLocaleString("pt-BR")}</p></div><StatusPill status={run.status} /><p className="text-zinc-400">{run.targetsScanned}/{run.targetsPlanned} consultados</p><p className="text-zinc-400">{run.findingsCount} achados</p></div>
            ))}</div> : <p className="p-5 text-sm text-zinc-500">Nenhuma execução foi iniciada.</p>}
          </article>
        </div>
      ) : null}

      {!loading && section === "integrations" ? (
        adapters.length ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {adapters.map((adapter) => (
              <article key={adapter.adapterType} className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-5">
                <div className="flex items-start justify-between gap-3"><div className="rounded-xl border border-orange-400/20 bg-orange-400/10 p-2"><Database className="h-5 w-5 text-orange-300" /></div><StatusPill status={adapter.implemented ? "implemented" : "planned"} /></div>
                <h2 className="mt-5 font-semibold text-white">{adapter.name}</h2>
                <p className="mt-2 min-h-12 text-sm leading-6 text-zinc-400">{adapter.description}</p>
                <div className="mt-4 flex flex-wrap gap-1.5">{adapter.capabilities.map((capability) => <span key={capability} className="rounded-md bg-zinc-900 px-2 py-1 text-[10px] text-zinc-400">{capability}</span>)}</div>
                <p className="mt-5 flex items-center gap-2 text-xs text-zinc-500"><ShieldCheck className="h-3.5 w-3.5 text-emerald-300" /> {adapter.readOnly ? "Contrato somente leitura" : "Requer revisão de permissão"}</p>
              </article>
            ))}
          </div>
        ) : <EmptyState icon={Unplug} title="Catálogo indisponível" description="A API não retornou adapters de integração." />
      ) : null}

      {!loading && section === "incidents" ? (
        incidents.length ? (
          <div className="space-y-4">
            {incidents.map((incident) => (
              <article key={incident.id} className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-5">
                <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusPill status={incident.severity} />
                      <StatusPill status={incident.status} />
                      {incident.confidence !== null ? <span className="text-xs text-zinc-500">Confiança {Math.round(incident.confidence * 100)}%</span> : null}
                    </div>
                    <h2 className="mt-4 text-lg font-semibold text-white">{incident.title}</h2>
                    <p className="mt-2 max-w-4xl text-sm leading-6 text-zinc-400">{incident.summary}</p>
                  </div>
                  <div className="shrink-0 text-xs leading-5 text-zinc-500">
                    <p>Primeiro sinal: {new Date(incident.firstOccurredAt).toLocaleString("pt-BR")}</p>
                    <p>Último sinal: {new Date(incident.lastOccurredAt).toLocaleString("pt-BR")}</p>
                  </div>
                </div>
                <div className="mt-5 grid gap-3 md:grid-cols-3">
                  <div className="rounded-xl border border-zinc-800 bg-black/25 p-3"><p className="text-[10px] uppercase tracking-[0.14em] text-zinc-600">Impacto</p><p className="mt-2 text-sm text-zinc-300">{incident.impact}</p></div>
                  <div className="rounded-xl border border-zinc-800 bg-black/25 p-3"><p className="text-[10px] uppercase tracking-[0.14em] text-zinc-600">Causa provável</p><p className="mt-2 text-sm text-zinc-300">{incident.probableCause ?? "Ainda sem evidência suficiente."}</p></div>
                  <div className="rounded-xl border border-zinc-800 bg-black/25 p-3"><p className="text-[10px] uppercase tracking-[0.14em] text-zinc-600">Recomendação</p><p className="mt-2 text-sm text-zinc-300">{incident.recommendation ?? "Continuar coletando evidências."}</p></div>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState icon={CheckCircle2} title="Nenhum incidente aberto" description="O Vulcan não cria incidentes sem evidências. Eventos continuam disponíveis na timeline e a correlação determinística será adicionada na fase seguinte." />
        )
      ) : null}

      {!loading && section === "platform" ? (
        health && version ? (
          <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
            <article className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-5">
              <div className="flex items-start justify-between gap-4">
                <div><p className="text-xs uppercase tracking-[0.16em] text-zinc-500">Dependências</p><h2 className="mt-2 text-xl font-semibold text-white">{health.service}</h2></div>
                <StatusPill status={health.status} />
              </div>
              <div className="mt-5 divide-y divide-zinc-800">
                {health.checks.map((check) => (
                  <div key={check.name} className="grid gap-3 py-4 first:pt-0 sm:grid-cols-[1fr_auto] sm:items-center">
                    <div><p className="text-sm font-medium text-white">{check.name.replaceAll("_", " ")}</p><p className="mt-1 text-xs leading-5 text-zinc-500">{check.detail}</p></div>
                    <div className="flex items-center gap-3"><StatusPill status={check.status} />{check.latencyMs !== null ? <span className="text-xs text-zinc-500">{check.latencyMs.toLocaleString("pt-BR")} ms</span> : null}</div>
                  </div>
                ))}
              </div>
            </article>
            <article className="rounded-2xl border border-zinc-800 bg-zinc-950/70 p-5">
              <p className="text-xs uppercase tracking-[0.16em] text-zinc-500">Build em execução</p>
              <h2 className="mt-3 text-2xl font-semibold text-white">{version.product} {version.version}</h2>
              <dl className="mt-6 grid gap-4 text-sm">
                <div><dt className="text-xs text-zinc-600">Serviço</dt><dd className="mt-1 text-zinc-300">{version.service}</dd></div>
                <div><dt className="text-xs text-zinc-600">Commit</dt><dd className="mt-1 break-all font-mono text-xs text-zinc-300">{version.commit}</dd></div>
                <div><dt className="text-xs text-zinc-600">Build</dt><dd className="mt-1 break-all font-mono text-xs text-zinc-300">{version.build}</dd></div>
                <div><dt className="text-xs text-zinc-600">Contrato de eventos</dt><dd className="mt-1 break-all font-mono text-xs text-orange-200">{version.eventSchemaVersion}</dd></div>
              </dl>
              <div className="mt-6"><OriginBadge origin={health.dataOrigin} /></div>
            </article>
          </div>
        ) : <EmptyState icon={Activity} title="Saúde indisponível" description="A API não retornou diagnóstico ou versão da plataforma." />
      ) : null}

      {createMode ? <CreatePanel mode={createMode} sites={sites} networks={networks} busy={saving} error={saveError} onClose={() => { setCreateMode(null); setSaveError(null); }} onSubmit={create} /> : null}
    </section>
  );
}

function severityTone(severity: string) {
  if (["critical", "error"].includes(severity)) return "bg-red-400";
  if (severity === "warning") return "bg-amber-300";
  if (severity === "notice") return "bg-sky-300";
  return "bg-emerald-300";
}

function mergeEvents(current: TimelineEvent[], incoming: TimelineEvent[]) {
  const events = new Map(current.map((event) => [event.eventId, event]));
  incoming.forEach((event) => events.set(event.eventId, event));
  return [...events.values()].sort((left, right) => Date.parse(right.occurredAt) - Date.parse(left.occurredAt));
}

export function UnifiedTimelineView({ apiUrl, tenantId, token }: PlatformProps) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [dataOrigin, setDataOrigin] = useState<"real" | "simulated">("real");
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamState, setStreamState] = useState<"connecting" | "live" | "offline">("connecting");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [severity, setSeverity] = useState("");
  const [source, setSource] = useState("");
  const [simulating, setSimulating] = useState(false);
  const streamController = useRef<AbortController | null>(null);

  const queryString = useCallback((nextCursor?: string | null) => {
    const params = new URLSearchParams({ limit: "80" });
    if (nextCursor) params.set("cursor", nextCursor);
    if (search.trim()) params.set("search", search.trim());
    if (category) params.set("category", category);
    if (severity) params.set("severity", severity);
    if (source.trim()) params.set("source", source.trim());
    return params.toString();
  }, [category, search, severity, source]);

  const load = useCallback(async (append = false, nextCursor?: string | null) => {
    append ? setLoadingMore(true) : setLoading(true);
    setError(null);
    try {
      const page = await fetchJson<TimelinePage>(apiUrl, `/timeline?${queryString(nextCursor)}`, token, tenantId);
      setEvents((current) => append ? mergeEvents(current, page.items) : page.items);
      setCursor(page.nextCursor);
      setHasMore(page.hasMore);
      setDataOrigin(page.dataOrigin);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível carregar a timeline.");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [apiUrl, queryString, tenantId, token]);

  useEffect(() => {
    const timeout = window.setTimeout(() => void load(), 250);
    return () => window.clearTimeout(timeout);
  }, [load]);

  useEffect(() => {
    const controller = new AbortController();
    streamController.current?.abort();
    streamController.current = controller;
    let buffer = "";

    async function connect() {
      setStreamState("connecting");
      try {
        const response = await fetch(`${apiUrl}/realtime/events`, {
          headers: apiHeaders(token, tenantId),
          signal: controller.signal
        });
        if (!response.ok || !response.body) throw new Error(await readApiError(response));
        setStreamState("live");
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        while (!controller.signal.aborted) {
          const result = await reader.read();
          if (result.done) break;
          buffer += decoder.decode(result.value, { stream: true });
          const frames = buffer.split("\n\n");
          buffer = frames.pop() ?? "";
          frames.forEach((frame) => {
            const eventType = frame.split("\n").find((line) => line.startsWith("event:"))?.slice(6).trim();
            const data = frame.split("\n").find((line) => line.startsWith("data:"))?.slice(5).trim();
            if (eventType === "timeline" && data) {
              try {
                const event = JSON.parse(data) as TimelineEvent;
                setEvents((current) => mergeEvents(current, [event]));
              } catch {
                setStreamState("offline");
              }
            }
          });
        }
      } catch (reason) {
        if (!controller.signal.aborted) {
          setStreamState("offline");
          setError(reason instanceof Error ? `Tempo real indisponível: ${reason.message}` : "Tempo real indisponível.");
        }
      }
    }
    void connect();
    return () => controller.abort();
  }, [apiUrl, tenantId, token]);

  const categories = useMemo(() => [...new Set(events.map((event) => event.category))].sort(), [events]);
  const sources = useMemo(() => [...new Set(events.map((event) => event.source))].sort(), [events]);

  async function simulate() {
    setSimulating(true);
    setError(null);
    try {
      const result = await fetchJson<{ events: TimelineEvent[] }>(apiUrl, "/events/simulate", token, tenantId, {
        method: "POST",
        body: JSON.stringify({ tenantId, scenario: "workforce_infrastructure_impact", count: 4 })
      });
      setEvents((current) => mergeEvents(current, result.events));
      setDataOrigin("simulated");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível gerar o cenário.");
    } finally {
      setSimulating(false);
    }
  }

  return (
    <section className="mt-5 space-y-5" aria-labelledby="timeline-title">
      <div className="rounded-3xl border border-zinc-800 bg-[radial-gradient(circle_at_top_right,rgba(249,115,22,0.12),transparent_35%),rgba(10,10,10,0.88)] p-6 md:p-8">
        <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-orange-300">Vulcan Timeline</p>
              <OriginBadge origin={dataOrigin} />
              <span className={`inline-flex items-center gap-2 text-xs ${streamState === "live" ? "text-emerald-300" : streamState === "connecting" ? "text-amber-200" : "text-red-300"}`}>
                <span className={`h-2 w-2 rounded-full ${streamState === "live" ? "animate-pulse bg-emerald-300" : streamState === "connecting" ? "bg-amber-300" : "bg-red-300"}`} />
                {streamState === "live" ? "Tempo real conectado" : streamState === "connecting" ? "Conectando" : "Tempo real indisponível"}
              </span>
            </div>
            <h1 id="timeline-title" className="mt-3 max-w-3xl text-2xl font-semibold tracking-tight text-white md:text-4xl">Tudo o que aconteceu, em uma única sequência</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-zinc-400">Trabalho, agentes e infraestrutura correlacionados pelo tempo, com origem, confiança e detalhes técnicos expansíveis.</p>
          </div>
          <button onClick={() => void simulate()} disabled={simulating} className="flex h-11 shrink-0 items-center justify-center gap-2 rounded-xl border border-amber-400/25 bg-amber-400/8 px-4 text-sm text-amber-100 disabled:opacity-50">
            {simulating ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Gerar cenário de desenvolvimento
          </button>
        </div>
      </div>

      <form onSubmit={(event) => { event.preventDefault(); void load(); }} className="grid gap-3 rounded-2xl border border-zinc-800 bg-zinc-950/70 p-4 md:grid-cols-[2fr_1fr_1fr_1fr_auto]">
        <div className="relative"><Search className="absolute left-3 top-3.5 h-4 w-4 text-zinc-500" /><input className={`${inputClass} pl-10`} value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Buscar mensagem ou detalhe" /></div>
        <select className={inputClass} value={category} onChange={(event) => setCategory(event.target.value)}><option value="">Todas as categorias</option>{categories.map((item) => <option key={item} value={item}>{item}</option>)}</select>
        <select className={inputClass} value={severity} onChange={(event) => setSeverity(event.target.value)}><option value="">Toda severidade</option><option value="info">Informação</option><option value="notice">Atenção</option><option value="warning">Alerta</option><option value="error">Erro</option><option value="critical">Crítico</option></select>
        <select className={inputClass} value={source} onChange={(event) => setSource(event.target.value)}><option value="">Todas as origens</option>{sources.map((item) => <option key={item} value={item}>{item}</option>)}</select>
        <button className="h-11 rounded-xl bg-orange-500 px-5 text-sm font-semibold text-black">Filtrar</button>
      </form>

      {error ? <div role="alert" className="flex gap-3 rounded-2xl border border-red-400/20 bg-red-400/8 p-4 text-sm text-red-100"><AlertTriangle className="h-4 w-4 shrink-0" />{error}</div> : null}

      {loading ? <LoadingSurface /> : events.length ? (
        <div className="rounded-2xl border border-zinc-800 bg-zinc-950/70 px-4 py-2 md:px-6">
          {events.map((event, index) => {
            const hostname = typeof event.device.hostname === "string" ? event.device.hostname : null;
            const username = typeof event.actor.username === "string" ? event.actor.username : null;
            return (
              <article key={event.eventId} className="relative grid gap-4 border-b border-zinc-800 py-6 last:border-0 md:grid-cols-[150px_22px_1fr]">
                <time className="text-xs leading-5 text-zinc-500">{new Date(event.occurredAt).toLocaleDateString("pt-BR")}<br /><span className="text-zinc-300">{new Date(event.occurredAt).toLocaleTimeString("pt-BR")}</span></time>
                <div className="relative hidden md:block"><span className={`absolute left-[7px] top-1 h-2.5 w-2.5 rounded-full ring-4 ring-zinc-950 ${severityTone(event.severity)}`} />{index < events.length - 1 ? <span className="absolute bottom-[-24px] left-[11px] top-4 w-px bg-zinc-800" /> : null}</div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2"><StatusPill status={event.severity} /><span className="text-xs uppercase tracking-[0.12em] text-zinc-500">{event.category}</span><OriginBadge origin={event.dataOrigin} /></div>
                  <h2 className="mt-3 text-base font-medium leading-7 text-white">{event.message}</h2>
                  <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-xs text-zinc-500"><span>Origem: <strong className="font-medium text-zinc-300">{event.source}</strong></span>{hostname ? <span>Dispositivo: <strong className="font-medium text-zinc-300">{hostname}</strong></span> : null}{username ? <span>Pessoa: <strong className="font-medium text-zinc-300">{username}</strong></span> : null}{event.confidence !== null ? <span>Confiança: <strong className="font-medium text-zinc-300">{Math.round(event.confidence * 100)}%</strong></span> : null}</div>
                  <details className="mt-4 rounded-xl border border-zinc-800 bg-black/25 p-3 text-xs text-zinc-400">
                    <summary className="cursor-pointer select-none text-zinc-300">Detalhes técnicos e contexto</summary>
                    <div className="mt-3 grid gap-3 lg:grid-cols-2">
                      <div><p className="uppercase tracking-[0.12em] text-zinc-600">Evento</p><p className="mt-1 break-all">{event.eventType}</p>{event.technicalMessage ? <p className="mt-2 text-zinc-500">{event.technicalMessage}</p> : null}</div>
                      <div><p className="uppercase tracking-[0.12em] text-zinc-600">Identificadores</p><p className="mt-1 break-all">ID: {event.eventId}</p>{event.correlationId ? <p className="mt-1 break-all">Correlação: {event.correlationId}</p> : null}</div>
                      <pre className="max-h-44 overflow-auto whitespace-pre-wrap rounded-lg bg-zinc-950 p-3 text-[11px] text-zinc-500 lg:col-span-2">{JSON.stringify({ actor: event.actor, device: event.device, context: event.context, metrics: event.metrics }, null, 2)}</pre>
                    </div>
                  </details>
                </div>
              </article>
            );
          })}
          {hasMore ? <div className="flex justify-center border-t border-zinc-800 py-5"><button disabled={loadingMore} onClick={() => void load(true, cursor)} className="flex items-center gap-2 rounded-xl border border-zinc-700 px-4 py-2 text-sm text-zinc-300 disabled:opacity-50">{loadingMore ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Clock3 className="h-4 w-4" />}Carregar eventos anteriores</button></div> : null}
        </div>
      ) : (
        <EmptyState icon={Globe2} title="Nenhum evento neste filtro" description="A timeline exibirá eventos reais assim que os agentes ou integrações enviarem dados. Para validar o fluxo local, use o cenário de desenvolvimento claramente identificado como simulado." />
      )}
    </section>
  );
}
