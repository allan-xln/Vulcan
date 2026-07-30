export type WallboardType = "workforce" | "infrastructure";
export type QualityPreset = "auto" | "low" | "balanced" | "cinematic" | "4k";
export type MotionIntensity = "minimal" | "balanced" | "cinematic";
export type TransitionStyle = "scan" | "focus" | "energy" | "rebuild";
export type ConnectionState =
  | "live"
  | "updating"
  | "stale"
  | "reconnecting"
  | "offline"
  | "error";

export type PlaylistItem = {
  id: string;
  siteId: string | null;
  siteName: string | null;
  panelKey: string;
  title: string;
  position: number;
  durationSeconds: number | null;
  enabled: boolean;
  config: Record<string, unknown>;
};

export type Playlist = {
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

export type WallboardProfile = {
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
  config: Record<string, unknown>;
  playlists: Playlist[];
};

export type SnapshotRow = Record<string, unknown>;

export type WallboardApplication = {
  name: string;
  category: string;
  activeSeconds: number;
  events: number;
  lastSeenAt: string;
};

export type WallboardAgent = {
  id: string;
  hostname: string;
  profile: "workstation" | "server" | "collector";
  operatingSystem: string;
  agentVersion: string | null;
  effectiveStatus: "online" | "delayed" | "offline" | "pending";
  queueDepth: number;
  policyStatus: string;
  siteId: string | null;
  siteName: string | null;
  lastSeenAt: string | null;
};

export type TopologyNode = {
  id: string;
  siteId: string | null;
  siteName: string | null;
  name: string;
  assetType: string;
  status: string;
  criticality: string;
  source: string;
  ipAddress: string | null;
  lastSeenAt: string | null;
  details: Record<string, unknown>;
};

export type TopologyLink = {
  id: string;
  sourceAssetId: string;
  targetAssetId: string;
  relationshipType: string;
  status: string;
  confidence: number;
  source: string;
  observedAt: string | null;
  details: Record<string, unknown>;
};

export type WallboardSnapshot = {
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
  applications: WallboardApplication[];
  agents: WallboardAgent[];
  topologyNodes: TopologyNode[];
  topologyLinks: TopologyLink[];
};

export type HealthCheck = {
  name: string;
  status: "ok" | "degraded" | "unavailable" | "disabled";
  detail: string;
  latencyMs: number | null;
};

export type PlatformHealth = {
  status: "ok" | "degraded" | "unavailable";
  timestamp: string;
  checks: HealthCheck[];
  dataOrigin: "real";
};

export type PlatformVersion = {
  product: "Vulcan";
  service: string;
  version: string;
  commit: string;
  build: string;
  eventSchemaVersion: string;
};

export type CommandCenterConfig = {
  quality: QualityPreset;
  motionIntensity: MotionIntensity;
  transitionStyle: TransitionStyle;
  visualIntensity: number;
  targetFps: 30 | 60;
  openingEnabled: boolean;
  openingDurationSeconds: number;
  openingMode: "full" | "reduced";
  alertTakeoverEnabled: boolean;
  alertTakeoverSeconds: number;
  controlsAutoHideSeconds: number;
  showLogo: boolean;
  showSite: boolean;
  audioEnabled: false;
  fallbackMode: "automatic" | "always-2d";
  sceneSequence: string[];
};

export type RuntimeMetrics = {
  fps: number | null;
  effectiveQuality: Exclude<QualityPreset, "auto">;
  webglAvailable: boolean;
  reducedMotion: boolean;
};
