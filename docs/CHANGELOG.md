# Changelog

## Unreleased

- Added the unified Go Vulcan Agent with Workstation, Server and Collector profiles.
- Added v2 one-time enrollment, Ed25519 request/policy signatures and replay protection.
- Added encrypted SQLite offline queue, real canonical event ingestion and typed commands.
- Added tenant-scoped agent identities, policies, releases and audit migration.
- Added agent management/policy/installation UI and MSI/DEB/SBOM release pipeline.
- Reorganized product into `/home/allan/Dev/Vulcan`.
- Renamed product identity to Vulcan.
- Added GPT/OpenAI configuration and AI insight endpoint.
- Added hybrid GPT + Llama AI architecture.
- Added Supabase as the official platform layer.
- Added Supabase validation and migration scripts.
- Applied SaaS multi-tenant hierarchy/RLS migrations to the configured Supabase project.
- Added backend Supabase status and Supabase Auth token validation path.
- Added dynamic hierarchy endpoint and premium hierarchy dashboard view.
- Moved frontend, backend, AI, agent, shared packages, database assets, Docker config, and fixtures into the Vulcan structure.
- Removed generated source artifacts from the active project tree.
- Updated local Docker composition to keep PostgreSQL as the only active database.
- Made job run tables tenant-specific.
- Added enterprise documentation set.
