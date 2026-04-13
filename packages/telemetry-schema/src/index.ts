export const TELEMETRY_SCHEMA_VERSION_V1 = "2026-04-telemetry.v1";

export const telemetryEventTypes = [
  "heartbeat",
  "session_lock",
  "session_unlock",
  "session_login",
  "session_logout",
  "idle_start",
  "idle_end",
  "foreground_application_change",
  "process_start",
  "process_stop"
] as const;

export type TelemetryEventType = (typeof telemetryEventTypes)[number];

export type TelemetryBatchRequest = {
  schemaVersion: typeof TELEMETRY_SCHEMA_VERSION_V1;
  batchId?: string;
  sentAt: string;
  events: TelemetryEvent[];
};

export type TelemetrySourceContext = {
  workstationId: string;
  agentInstallationId?: string;
  agentVersion?: string;
};

type BaseTelemetryEvent = {
  eventId: string;
  occurredAt: string;
  source: TelemetrySourceContext;
};

export type HeartbeatEvent = BaseTelemetryEvent & {
  eventType: "heartbeat";
  payload: {
    status: "online";
    queueDepth: number;
  };
};

export type SessionBoundaryEvent = BaseTelemetryEvent & {
  eventType: "session_lock" | "session_unlock" | "session_login" | "session_logout";
  payload: {
    sessionId: string;
    username?: string;
  };
};

export type IdleEvent = BaseTelemetryEvent & {
  eventType: "idle_start" | "idle_end";
  payload: {
    sessionId: string;
    idleThresholdSeconds: number;
  };
};

export type ForegroundApplicationChangeEvent = BaseTelemetryEvent & {
  eventType: "foreground_application_change";
  payload: {
    sessionId?: string;
    appName: string;
    executablePath?: string;
    windowTitle?: string;
  };
};

export type ProcessEvent = BaseTelemetryEvent & {
  eventType: "process_start" | "process_stop";
  payload: {
    processName: string;
    executablePath?: string;
    pid?: number;
  };
};

export type TelemetryEvent =
  | HeartbeatEvent
  | SessionBoundaryEvent
  | IdleEvent
  | ForegroundApplicationChangeEvent
  | ProcessEvent;
