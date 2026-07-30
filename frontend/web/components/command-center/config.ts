import {
  CommandCenterConfig,
  MotionIntensity,
  QualityPreset,
  RuntimeMetrics,
  TransitionStyle,
  WallboardProfile,
  WallboardType
} from "./types";

export const WORKFORCE_SCENES = [
  "command",
  "pulse",
  "teams",
  "applications",
  "branches",
  "collection"
] as const;

export const INFRASTRUCTURE_SCENES = [
  "command",
  "topology",
  "connectivity",
  "proxmox",
  "servers",
  "unifi",
  "printing",
  "platform"
] as const;

export const SCENE_LABELS: Record<string, string> = {
  command: "Comando geral",
  pulse: "Pulso operacional",
  teams: "Equipes e filiais",
  applications: "Aplicações",
  branches: "Unidades operacionais",
  collection: "Saúde da coleta",
  topology: "Topologia Vulcan",
  connectivity: "Links e conectividade",
  proxmox: "Cluster Proxmox",
  servers: "Servidores",
  unifi: "Rede e UniFi",
  printing: "Frota de impressão",
  platform: "Saúde do Vulcan"
};

export const QUALITY_CAPABILITIES = {
  low: {
    webgl: false,
    pixelRatio: 1,
    particles: 0,
    antialias: false,
    cameraMotion: false
  },
  balanced: {
    webgl: true,
    pixelRatio: 1.25,
    particles: 22,
    antialias: true,
    cameraMotion: true
  },
  cinematic: {
    webgl: true,
    pixelRatio: 1.5,
    particles: 44,
    antialias: true,
    cameraMotion: true
  },
  "4k": {
    webgl: true,
    pixelRatio: 1.5,
    particles: 64,
    antialias: true,
    cameraMotion: true
  }
} as const;

const DEFAULT_CONFIG: Omit<CommandCenterConfig, "sceneSequence"> = {
  quality: "auto",
  motionIntensity: "balanced",
  transitionStyle: "scan",
  visualIntensity: 70,
  targetFps: 60,
  openingEnabled: true,
  openingDurationSeconds: 3.2,
  openingMode: "full",
  alertTakeoverEnabled: true,
  alertTakeoverSeconds: 45,
  controlsAutoHideSeconds: 5,
  showLogo: true,
  showSite: true,
  audioEnabled: false,
  fallbackMode: "automatic"
};

function enumValue<T extends string>(value: unknown, allowed: readonly T[], fallback: T): T {
  return typeof value === "string" && allowed.includes(value as T) ? (value as T) : fallback;
}

function boundedNumber(value: unknown, fallback: number, min: number, max: number) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.min(max, Math.max(min, parsed)) : fallback;
}

function booleanValue(value: unknown, fallback: boolean) {
  return typeof value === "boolean" ? value : fallback;
}

export function commandCenterConfig(
  profile: WallboardProfile | null,
  type: WallboardType
): CommandCenterConfig {
  const raw = profile?.config ?? {};
  const availableScenes =
    type === "workforce" ? [...WORKFORCE_SCENES] : [...INFRASTRUCTURE_SCENES];
  const configuredScenes = Array.isArray(raw.sceneSequence)
    ? raw.sceneSequence.filter(
        (scene): scene is string =>
          typeof scene === "string" && availableScenes.includes(scene as never)
      )
    : [];

  return {
    quality: enumValue<QualityPreset>(
      raw.quality,
      ["auto", "low", "balanced", "cinematic", "4k"],
      DEFAULT_CONFIG.quality
    ),
    motionIntensity: enumValue<MotionIntensity>(
      raw.motionIntensity,
      ["minimal", "balanced", "cinematic"],
      DEFAULT_CONFIG.motionIntensity
    ),
    transitionStyle: enumValue<TransitionStyle>(
      raw.transitionStyle,
      ["scan", "focus", "energy", "rebuild"],
      DEFAULT_CONFIG.transitionStyle
    ),
    visualIntensity: boundedNumber(raw.visualIntensity, DEFAULT_CONFIG.visualIntensity, 20, 100),
    targetFps: boundedNumber(raw.targetFps, DEFAULT_CONFIG.targetFps, 30, 60) >= 45 ? 60 : 30,
    openingEnabled: booleanValue(raw.openingEnabled, DEFAULT_CONFIG.openingEnabled),
    openingDurationSeconds: boundedNumber(
      raw.openingDurationSeconds,
      DEFAULT_CONFIG.openingDurationSeconds,
      1.5,
      5
    ),
    openingMode: enumValue(
      raw.openingMode,
      ["full", "reduced"],
      DEFAULT_CONFIG.openingMode
    ),
    alertTakeoverEnabled: booleanValue(
      raw.alertTakeoverEnabled,
      DEFAULT_CONFIG.alertTakeoverEnabled
    ),
    alertTakeoverSeconds: boundedNumber(
      raw.alertTakeoverSeconds,
      DEFAULT_CONFIG.alertTakeoverSeconds,
      10,
      600
    ),
    controlsAutoHideSeconds: boundedNumber(
      raw.controlsAutoHideSeconds,
      DEFAULT_CONFIG.controlsAutoHideSeconds,
      2,
      30
    ),
    showLogo: booleanValue(raw.showLogo, DEFAULT_CONFIG.showLogo),
    showSite: booleanValue(raw.showSite, DEFAULT_CONFIG.showSite),
    audioEnabled: false,
    fallbackMode: enumValue(
      raw.fallbackMode,
      ["automatic", "always-2d"],
      DEFAULT_CONFIG.fallbackMode
    ),
    sceneSequence: configuredScenes.length ? configuredScenes : availableScenes
  };
}

function webglSupported() {
  try {
    const canvas = document.createElement("canvas");
    const context =
      canvas.getContext("webgl2", { failIfMajorPerformanceCaveat: true }) ??
      canvas.getContext("webgl", { failIfMajorPerformanceCaveat: true });
    context?.getExtension("WEBGL_lose_context")?.loseContext();
    return Boolean(context);
  } catch {
    return false;
  }
}

export function initialRuntimeMetrics(config: CommandCenterConfig): RuntimeMetrics {
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const webglAvailable = webglSupported();
  let effectiveQuality: RuntimeMetrics["effectiveQuality"];
  if (
    reducedMotion ||
    !webglAvailable ||
    config.fallbackMode === "always-2d" ||
    config.quality === "low"
  ) {
    effectiveQuality = "low";
  } else if (config.quality !== "auto") {
    effectiveQuality = config.quality;
  } else if (window.innerWidth >= 3000 && window.devicePixelRatio <= 2) {
    effectiveQuality = "4k";
  } else if ((navigator.hardwareConcurrency ?? 4) >= 8) {
    effectiveQuality = "cinematic";
  } else {
    effectiveQuality = "balanced";
  }
  return { fps: null, effectiveQuality, webglAvailable, reducedMotion };
}
