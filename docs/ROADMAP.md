# Roadmap

## Foundation

- Complete Vulcan monorepo restructuring.
- Keep one PostgreSQL database.
- Enforce tenant-scoped jobs.
- Complete enterprise documentation.
- Integrate hybrid GPT + Llama AI routing.

## SaaS Core

- Harden Supabase Auth for production onboarding.
- Add tenant onboarding wizard with company, users, hierarchy and notification recipients.
- Finish role and permission management UI beyond the current demo hierarchy.
- Persist tenant settings from the guided settings screen.
- Convert demo action buttons into backend jobs for simulation, insight generation and alert triggering.
- Add self-service agent enrollment flow with signed tenant tokens.

## Operational Intelligence

- Promote current demo metrics into production rollups.
- Add configurable productive/improductive app taxonomy per tenant.
- Add bottleneck detection with thresholds by department and role.
- Add daily, weekly and monthly automatic report jobs.
- Add automation opportunity scoring with financial estimates by tenant.
- Add explainable recommendations through GPT only for premium/complex cases.

## Agent

- Test Windows package on a real Windows machine and validate mass deployment through GPO/Intune/RMM.
- Add macOS collector implementation.
- Add signed sync payloads and server-side replay protection.
- Improve GNOME/Wayland opt-in collection diagnostics without bypassing OS privacy controls.
- Add user-facing tray/status UI for pause, privacy status and sync health.

## Supabase Production Hardening

- Apply Supabase migrations to production.
- Replace local development auth with Supabase Auth.
- Add Storage buckets, RLS storage policies, and optional Realtime feeds.
- Add production Auth providers and redirect URLs.

## Demo Comercial

- Keep `corepack pnpm seed:demo` idempotent and realistic.
- Expand demo scenarios with more departments and tenant variants.
- Add Playwright tests for every demo profile.
- Add commercial story mode for "before/after" operational improvements.
