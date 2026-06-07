export const platformPrinciples = [
  "Multi-tenant isolation from day one",
  "RLS and auditability on every sensitive path",
  "No surveillance, spyware behavior or indiscriminate capture",
  "LLMs explain structured facts; they do not define truth",
  "Scores and metrics must be traceable to source data"
] as const;

export const architectureLayers = [
  {
    name: "Tenant isolation",
    value: "Tenant isolation",
    summary:
      "Supabase and PostgreSQL remain the transactional source of truth with RLS and audit controls."
  },
  {
    name: "Structured truth",
    value: "Structured truth",
    summary:
      "PostgreSQL and ingestion services operate on signed operational events and explicit tenant scope."
  },
  {
    name: "Explainable analytics",
    value: "Explainable analytics",
    summary:
      "AI services consume only structured facts, features, alerts and scores with traceable origin."
  }
] as const;

export type PlatformPrinciple = (typeof platformPrinciples)[number];
export type ArchitectureLayer = (typeof architectureLayers)[number];
