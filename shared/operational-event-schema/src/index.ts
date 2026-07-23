export const OPERATIONAL_EVENT_SCHEMA_VERSION_V1 = "2026-06-operational-events.v1";
export const VULCAN_EVENT_SCHEMA_VERSION_V1 = "2026-07-vulcan-event.v1";

export const operationalEventTypes = [
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

export type OperationalEventType = (typeof operationalEventTypes)[number];

export type OperationalEventBatchRequest = {
  schemaVersion: typeof OPERATIONAL_EVENT_SCHEMA_VERSION_V1;
  batchId?: string;
  sentAt: string;
  events: OperationalEvent[];
};

export type OperationalEventSourceContext = {
  workstationId: string;
  agentInstallationId?: string;
  agentVersion?: string;
};

type BaseOperationalEvent = {
  eventId: string;
  occurredAt: string;
  source: OperationalEventSourceContext;
};

export type HeartbeatEvent = BaseOperationalEvent & {
  eventType: "heartbeat";
  payload: {
    status: "online";
    queueDepth: number;
  };
};

export type SessionBoundaryEvent = BaseOperationalEvent & {
  eventType: "session_lock" | "session_unlock" | "session_login" | "session_logout";
  payload: {
    sessionId: string;
    username?: string;
  };
};

export type IdleEvent = BaseOperationalEvent & {
  eventType: "idle_start" | "idle_end";
  payload: {
    sessionId: string;
    idleThresholdSeconds: number;
  };
};

export type ForegroundApplicationChangeEvent = BaseOperationalEvent & {
  eventType: "foreground_application_change";
  payload: {
    sessionId?: string;
    appName: string;
    executablePath?: string;
    windowTitle?: string;
  };
};

export type ProcessEvent = BaseOperationalEvent & {
  eventType: "process_start" | "process_stop";
  payload: {
    processName: string;
    executablePath?: string;
    pid?: number;
  };
};

export type OperationalEvent =
  | HeartbeatEvent
  | SessionBoundaryEvent
  | IdleEvent
  | ForegroundApplicationChangeEvent
  | ProcessEvent;

export type JsonValue = null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };

export const vulcanEventSeverities = [
  "debug",
  "info",
  "notice",
  "warning",
  "error",
  "critical"
] as const;

export const vulcanPrivacyClassifications = [
  "public",
  "operational",
  "personal",
  "sensitive",
  "restricted"
] as const;

export type VulcanEventSeverity = (typeof vulcanEventSeverities)[number];
export type VulcanPrivacyClassification = (typeof vulcanPrivacyClassifications)[number];

export type VulcanEventV1 = {
  eventId: string;
  tenantId: string;
  schemaVersion: typeof VULCAN_EVENT_SCHEMA_VERSION_V1;
  siteId?: string | null;
  assetId?: string | null;
  agentId?: string | null;
  source: string;
  sourceType: string;
  sourceEventId: string;
  eventType: string;
  category: string;
  severity: VulcanEventSeverity;
  occurredAt: string;
  deviceOccurredAt?: string | null;
  receivedAt: string;
  clockDriftMs?: number | null;
  offlineBuffered: boolean;
  actor: JsonObject;
  device: JsonObject;
  context: JsonObject;
  metrics: JsonObject;
  message: string;
  technicalMessage?: string | null;
  fingerprint: string;
  correlationId?: string | null;
  causationId?: string | null;
  confidence?: number | null;
  privacyClassification: VulcanPrivacyClassification;
  retentionPolicy: string;
  trustedOrigin: boolean;
  dataOrigin: "real" | "simulated" | "imported";
  extensions: JsonObject;
};
