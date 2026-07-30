"use client";

import { gsap } from "gsap";
import {
  AlertOctagon,
  ArrowLeft,
  ArrowRight,
  Gauge,
  LogOut,
  Maximize2,
  Pause,
  Play,
  Radio,
  RotateCcw
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import Image from "next/image";
import {
  CSSProperties,
  ReactNode,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState
} from "react";
import { SCENE_LABELS } from "./config";
import { DataOriginBadge, StatusMark, formatMoment, text } from "./primitives";
import {
  CommandCenterConfig,
  ConnectionState,
  PlaylistItem,
  RuntimeMetrics,
  SnapshotRow,
  WallboardProfile,
  WallboardType
} from "./types";

const INTRO_SESSION_PREFIX = "vulcan-command-intro:";

const CONNECTION_LABELS: Record<ConnectionState, string> = {
  live: "AO VIVO",
  updating: "ATUALIZANDO",
  stale: "DADOS ATRASADOS",
  reconnecting: "RECONECTANDO",
  offline: "OFFLINE",
  error: "ERRO"
};

export function CommandCenterShell({
  type,
  profile,
  activeItem,
  itemIndex,
  itemCount,
  itemProgress,
  scene,
  sceneIndex,
  sceneCount,
  config,
  connectionState,
  generatedAt,
  clock,
  paused,
  controlsDisabled,
  metrics,
  error,
  alerts,
  burnInShift,
  onPrevious,
  onNext,
  onTogglePause,
  onFullscreen,
  onLogout,
  onDismissCritical,
  children
}: {
  type: WallboardType;
  profile: WallboardProfile;
  activeItem: PlaylistItem | null;
  itemIndex: number;
  itemCount: number;
  itemProgress: number;
  scene: string;
  sceneIndex: number;
  sceneCount: number;
  config: CommandCenterConfig;
  connectionState: ConnectionState;
  generatedAt: string | null;
  clock: Date;
  paused: boolean;
  controlsDisabled: boolean;
  metrics: RuntimeMetrics;
  error: string | null;
  alerts: SnapshotRow[];
  burnInShift: number;
  onPrevious: () => void;
  onNext: () => void;
  onTogglePause: () => void;
  onFullscreen: () => void;
  onLogout: () => void;
  onDismissCritical: (id: string) => void;
  children: ReactNode;
}) {
  const rootRef = useRef<HTMLElement>(null);
  const sceneRef = useRef<HTMLDivElement>(null);
  const introRef = useRef<HTMLDivElement>(null);
  const hideTimer = useRef<number | null>(null);
  const [controlsVisible, setControlsVisible] = useState(true);
  const [introVisible, setIntroVisible] = useState(false);
  const panelHeading =
    activeItem?.panelKey === "overview"
      ? type === "workforce"
        ? "Visão geral das equipes"
        : "Visão geral da infraestrutura"
      : activeItem?.title ?? profile.name;
  const critical = useMemo(
    () =>
      config.alertTakeoverEnabled
        ? alerts.find((alert) => ["critical", "error"].includes(text(alert.severity, ""))) ?? null
        : null,
    [alerts, config.alertTakeoverEnabled]
  );

  const revealControls = useCallback(() => {
    setControlsVisible(true);
    if (hideTimer.current) window.clearTimeout(hideTimer.current);
    hideTimer.current = window.setTimeout(
      () => setControlsVisible(false),
      config.controlsAutoHideSeconds * 1_000
    );
  }, [config.controlsAutoHideSeconds]);

  useEffect(() => {
    revealControls();
    const handleKey = (event: KeyboardEvent) => {
      revealControls();
      if (event.key === "ArrowLeft") onPrevious();
      if (event.key === "ArrowRight") onNext();
      if (event.key.toLowerCase() === "f") onFullscreen();
      if (event.key === " ") {
        event.preventDefault();
        onTogglePause();
      }
    };
    window.addEventListener("pointermove", revealControls, { passive: true });
    window.addEventListener("keydown", handleKey);
    return () => {
      if (hideTimer.current) window.clearTimeout(hideTimer.current);
      window.removeEventListener("pointermove", revealControls);
      window.removeEventListener("keydown", handleKey);
    };
  }, [onFullscreen, onNext, onPrevious, onTogglePause, revealControls]);

  useLayoutEffect(() => {
    if (!sceneRef.current || metrics.reducedMotion) return;
    const context = gsap.context(() => {
      const duration = config.motionIntensity === "cinematic" ? 0.95 : 0.58;
      const style = config.transitionStyle;
      const from =
        style === "focus"
          ? { opacity: 0, scale: 1.025, filter: "brightness(1.6)" }
          : style === "energy"
            ? { opacity: 0, xPercent: 2.4, clipPath: "inset(0 100% 0 0)" }
            : style === "rebuild"
              ? { opacity: 0, y: 18, clipPath: "inset(48% 0 48% 0)" }
              : { opacity: 0, x: 14, clipPath: "inset(0 0 0 100%)" };
      gsap.fromTo(
        sceneRef.current,
        from,
        {
          opacity: 1,
          x: 0,
          y: 0,
          xPercent: 0,
          scale: 1,
          filter: "brightness(1)",
          clipPath: "inset(0 0 0 0)",
          duration,
          ease: "power3.out",
          clearProps: "transform,filter,clipPath"
        }
      );
    }, sceneRef);
    return () => context.revert();
  }, [config.motionIntensity, config.transitionStyle, metrics.reducedMotion, scene]);

  useLayoutEffect(() => {
    const key = `${INTRO_SESSION_PREFIX}${type}`;
    const alreadyShown = window.sessionStorage.getItem(key) === "shown";
    if (
      !config.openingEnabled ||
      alreadyShown ||
      metrics.reducedMotion ||
      critical
    ) {
      setIntroVisible(false);
      return;
    }
    setIntroVisible(true);
    window.sessionStorage.setItem(key, "shown");
  }, [config.openingEnabled, critical, metrics.reducedMotion, type]);

  useLayoutEffect(() => {
    if (!introVisible || !introRef.current) return;
    const duration = config.openingMode === "reduced" ? 1.5 : config.openingDurationSeconds;
    const context = gsap.context(() => {
      const timeline = gsap.timeline({
        onComplete: () => setIntroVisible(false)
      });
      timeline
        .set(".command-opening-line", { scaleX: 0, transformOrigin: "left" })
        .set(".command-opening-logo", { opacity: 0, scale: 0.88 })
        .set(".command-opening-copy > *", { opacity: 0, y: 12 })
        .to(".command-opening-line", { scaleX: 1, duration: duration * 0.24, ease: "power3.inOut" })
        .to(".command-opening-logo", { opacity: 1, scale: 1, duration: duration * 0.2 }, "-=0.12")
        .to(".command-opening-copy > *", { opacity: 1, y: 0, stagger: 0.08, duration: duration * 0.14 })
        .to(introRef.current, { opacity: 0, duration: duration * 0.2, delay: duration * 0.12 });
    }, introRef);
    return () => context.revert();
  }, [
    config.openingDurationSeconds,
    config.openingMode,
    introVisible
  ]);

  useEffect(() => {
    if (!critical) return;
    const timeout = window.setTimeout(
      () => onDismissCritical(String(critical.id)),
      config.alertTakeoverSeconds * 1_000
    );
    return () => window.clearTimeout(timeout);
  }, [config.alertTakeoverSeconds, critical, onDismissCritical]);

  const rootStyle = {
    "--command-burn-x": `${[0, 1, 0, -1][burnInShift] ?? 0}px`,
    "--command-burn-y": `${[0, 0, 1, 0][burnInShift] ?? 0}px`,
    "--command-visual-intensity": config.visualIntensity / 100
  } as CSSProperties;

  return (
    <main
      ref={rootRef}
      className={`vulcan-command-center command-${type}`}
      style={rootStyle}
      data-command-center={type}
      data-scene={scene}
      data-quality={metrics.effectiveQuality}
      data-fps={metrics.fps ?? ""}
      data-connection={connectionState}
    >
      <div className="command-ambient" aria-hidden="true">
        <span className="command-grid-plane" />
        <span className="command-energy-line command-energy-line-a" />
        <span className="command-energy-line command-energy-line-b" />
        <span className="command-vignette" />
      </div>

      <div className="command-viewport">
        <header className="command-header">
          <div className="command-brand">
            {config.showLogo ? (
              <Image src="/vulcan-logo.svg" alt="Vulcan" width={172} height={46} priority />
            ) : null}
            <span className="command-brand-divider" />
            <div>
              <p>VULCAN COMMAND SYSTEM</p>
              <strong>{type === "workforce" ? "WORKFORCE" : "INFRASTRUCTURE"}</strong>
            </div>
          </div>
          <div className="command-title">
            <span>{SCENE_LABELS[scene] ?? activeItem?.title ?? "Command Center"}</span>
            <h1>{panelHeading}</h1>
            {config.showSite ? <p>{activeItem?.siteName ?? "Todas as filiais"} · ERS Transportes</p> : null}
          </div>
          <div className="command-header-status">
            <StatusMark
              status={connectionState}
              label={CONNECTION_LABELS[connectionState]}
            />
            <DataOriginBadge />
            {profile.showClock ? (
              <time dateTime={clock.toISOString()}>
                <strong>{clock.toLocaleTimeString("pt-BR", { timeZone: "America/Sao_Paulo" })}</strong>
                <span>{clock.toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo" })}</span>
              </time>
            ) : null}
          </div>
        </header>

        {error ? (
          <div className="command-stale-banner" role="status">
            <RotateCcw aria-hidden="true" />
            <span>{error}</span>
            <small>A última informação válida permanece identificada como anterior.</small>
          </div>
        ) : null}

        <div ref={sceneRef} className="command-scene">
          {children}
        </div>

        <footer className="command-footer">
          <div className="command-footer-status">
            <Radio aria-hidden="true" />
            <span>
              {profile.showLastUpdate
                ? `Última coleta ${formatMoment(generatedAt)}`
                : "Atualização automática"}
            </span>
            <i />
            <span>{metrics.fps === null ? "FPS calibrando" : `${metrics.fps} FPS`}</span>
            <i />
            <span>{metrics.effectiveQuality.toUpperCase()}</span>
          </div>
          <div className="command-playlist-progress" aria-label="Progresso da playlist">
            <span>
              {String(itemIndex + 1).padStart(2, "0")} / {String(Math.max(1, itemCount)).padStart(2, "0")}
            </span>
            <div>
              <b style={{ width: `${Math.min(100, Math.max(0, itemProgress))}%` }} />
            </div>
            <span>
              CENA {String(sceneIndex + 1).padStart(2, "0")} / {String(Math.max(1, sceneCount)).padStart(2, "0")}
            </span>
          </div>
        </footer>
      </div>

      <AnimatePresence>
        {controlsVisible ? (
          <motion.nav
            className="command-controls"
            aria-label="Controles do Wallboard"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.2 }}
          >
            <Control label="Anterior" onClick={onPrevious} icon={ArrowLeft} disabled={controlsDisabled} />
            <Control
              label={paused ? "Retomar" : "Pausar"}
              onClick={onTogglePause}
              icon={paused ? Play : Pause}
              disabled={controlsDisabled}
            />
            <Control label="Próximo" onClick={onNext} icon={ArrowRight} disabled={controlsDisabled} />
            <Control label="Tela cheia" onClick={onFullscreen} icon={Maximize2} />
            <Control label="Sair" onClick={onLogout} icon={LogOut} />
          </motion.nav>
        ) : null}
      </AnimatePresence>

      <AnimatePresence>
        {critical ? (
          <motion.aside
            className="command-critical-takeover"
            role="alert"
            initial={{ opacity: 0, clipPath: "inset(0 100% 0 0)" }}
            animate={{ opacity: 1, clipPath: "inset(0 0 0 0)" }}
            exit={{ opacity: 0, clipPath: "inset(0 0 0 100%)" }}
            transition={{ duration: metrics.reducedMotion ? 0 : 0.55, ease: "easeOut" }}
          >
            <span className="command-critical-stripe" />
            <AlertOctagon aria-hidden="true" />
            <div>
              <p>CRITICAL EVENT TAKEOVER · DADO CONFIRMADO</p>
              <h2>{text(critical.title, "Evento crítico")}</h2>
              <span>{text(critical.impact, "Impacto em análise")}</span>
              <small>
                {text(
                  critical.siteName ?? critical.site_name,
                  activeItem?.siteName ?? "Todas as filiais"
                )} · {formatMoment(critical.last_occurred_at)}
              </small>
            </div>
            <button type="button" onClick={() => onDismissCritical(String(critical.id))}>
              Reconhecer na TV
            </button>
          </motion.aside>
        ) : null}
      </AnimatePresence>

      {introVisible ? (
        <div ref={introRef} className="command-opening" aria-label="Inicializando Vulcan Command Center">
          <span className="command-opening-line" />
          <div className="command-opening-logo">
            <Image src="/vulcan-symbol.svg" alt="" width={112} height={112} priority />
          </div>
          <div className="command-opening-copy">
            <p>VULCAN COMMAND SYSTEM</p>
            <h2>{activeItem?.siteName ?? "ERS TRANSPORTES"}</h2>
            <span><Gauge /> telemetria confirmada · {CONNECTION_LABELS[connectionState]}</span>
          </div>
        </div>
      ) : null}
    </main>
  );
}

function Control({
  label,
  onClick,
  icon: Icon,
  disabled = false
}: {
  label: string;
  onClick: () => void;
  icon: typeof Pause;
  disabled?: boolean;
}) {
  return (
    <button type="button" onClick={onClick} aria-label={label} title={label} disabled={disabled}>
      <Icon aria-hidden="true" />
    </button>
  );
}
