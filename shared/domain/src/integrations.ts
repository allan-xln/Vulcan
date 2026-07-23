export const integrationCapabilities = [
  "inventory",
  "metrics",
  "events",
  "health",
  "topology",
  "discovery"
] as const;

export type IntegrationCapability = (typeof integrationCapabilities)[number];

export type IntegrationContext = {
  tenantId: string;
  siteId?: string | null;
  integrationId: string;
  secretReferenceId?: string | null;
  readOnly: true;
};

export type IntegrationResult<T> = {
  status: "ok" | "partial" | "failed" | "rate_limited";
  data: T;
  warnings: string[];
  retryAfterSeconds?: number;
};

export interface VulcanInfrastructureAdapter<TInventory = unknown, TMetric = unknown, TEvent = unknown> {
  readonly adapterType: string;
  readonly capabilities: readonly IntegrationCapability[];
  authenticate(context: IntegrationContext): Promise<IntegrationResult<{ authenticated: boolean }>>;
  testConnection(context: IntegrationContext): Promise<IntegrationResult<{ reachable: boolean }>>;
  discover(context: IntegrationContext): Promise<IntegrationResult<TInventory[]>>;
  collectInventory(context: IntegrationContext): Promise<IntegrationResult<TInventory[]>>;
  collectMetrics(context: IntegrationContext): Promise<IntegrationResult<TMetric[]>>;
  collectEvents(context: IntegrationContext): Promise<IntegrationResult<TEvent[]>>;
  getHealth(context: IntegrationContext): Promise<IntegrationResult<Record<string, unknown>>>;
  getTopology(context: IntegrationContext): Promise<IntegrationResult<Record<string, unknown>>>;
  normalize(input: unknown): TEvent;
  mapAssets(inventory: TInventory[]): Promise<IntegrationResult<string[]>>;
  handleRateLimit(retryAfterSeconds?: number): Promise<void>;
  handleRetry(attempt: number, error: unknown): Promise<void>;
  audit(action: string, details: Record<string, unknown>): Promise<void>;
}
