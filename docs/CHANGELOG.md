# Changelog

## Unreleased

- A instalação de agentes agora gera um único comando por sistema e perfil. No Windows, o
  PowerShell baixa o MSI para uma pasta temporária, valida SHA-256, instala silenciosamente,
  remove o pacote e confirma serviço/status; não há download manual na tela.
- A seleção de perfil foi transformada em opções explícitas de Estação, Servidor e Coletor.
  Trocar o perfil descarta o comando/token anterior para impedir enrollment com perfil
  divergente.

## 0.5.1 — 2026-08-02

- Fixed the Agent installation page to turn the browser-relative `/api` endpoint into the
  official absolute origin before generating installation commands.
- Private HTTP deployments now include `ALLOW_INSECURE_PRIVATE_NETWORK=true` automatically
  in Windows MSI commands and `--allow-insecure-private-network` in Linux enrollment.
- The installation page displays the exact endpoint delivered to the agent before a token
  is generated.

## 0.5.0 — 2026-07-30

- Published to the isolated `VULCAN-PROD01` runtime and revalidated after a controlled
  reboot on 2026-08-01. The official entry point remains
  `http://192.168.200.4:8099`, with the domain controller acting only as the existing
  network forwarder.

- Rebuilt Workforce and Infrastructure Wallboards as the Vulcan Command Center without
  changing the main Workforce-first product navigation.
- Added independent real-data scene engines, GSAP transitions, a session-scoped opening,
  critical incident takeover and TV-safe controls.
- Added real topology contracts and 3D/2D rendering from persisted assets and
  relationships, with no invented nodes, links or traffic.
- Added ECharts/D3/Three.js lazy visualizations and TanStack Query cache/recovery.
- Added `auto`, `low`, `balanced`, `cinematic` and `4k` quality presets with adaptive FPS
  downgrade, reduced-motion behavior, WebGL context-loss recovery and SVG fallback.
- Expanded persisted Wallboard settings for scene order, opening, motion, quality,
  fallback, alert takeover, visual intensity, TV identity, target resolution and schedule.
- Added silent profile/playlist revalidation for already-open TVs without resetting an
  unchanged scene, plus tenant-global critical takeover while a branch panel is active.
- Fixed the session-scoped GSAP opening mount sequence and disabled ECharts animation
  when the operating system requests reduced motion.
- Added real application, agent and topology fields to the tenant/site-scoped Wallboard
  snapshot and kept rolling-deploy compatibility with 0.4.0 responses.
- Added effective Infrastructure status based on a 30-minute observation window and a
  transparent `monitoredAssets` denominator; no recent telemetry now renders as unknown.
- Added 1080p/1440p/4K E2E checks, read-only mutation proof and a continuous soak harness
  for heap, CPU, FPS, listeners, timers, canvases, SSE and reconnection.
- Updated Next.js, Playwright, Sharp and PostCSS to audited patched versions; the
  production dependency audit reports no known vulnerabilities.

## 0.4.0 — 2026-07-30

- Added durable first-class routes for Workforce, Infrastructure, Agents, Timeline,
  Intelligence, Notifications and Settings, preserving session and subsection on reload.
- Added tenant-scoped Workforce and Infrastructure Wallboards with persisted profiles,
  playlists, per-branch rotation, SSE refresh, fullscreen and burn-in prevention.
- Added ERS branch, network, asset, relationship and safe discovery-policy provisioning.
- Added read-only UniFi and Proxmox inventory reconciliation with runtime-only secrets.
- Added dedicated Infrastructure inventory views for servers, virtualization, firewalls,
  switches, access points and printers without fabricated placeholder data.

## Histórico anterior à 0.4.0

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
