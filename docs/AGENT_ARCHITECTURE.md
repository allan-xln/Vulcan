# Vulcan Agent Architecture

## Product boundary

Vulcan Agent is the policy-controlled endpoint component of Vulcan Workforce and Vulcan
Infrastructure. It does not replace either product area and does not operate as a separate
monitoring product.

Three profiles share one core:

- `workstation`: user sessions, activity context, endpoint health, inventory, network and
  printing when policy permits;
- `server`: health, inventory, services and approved application probes, without employee
  productivity;
- `collector`: safe discovery and approved infrastructure probes, without productivity.

The agent never implements a keylogger, password capture, arbitrary clipboard capture,
screenshots, microphone, webcam or a generic remote shell.

## Architecture found on 2026-07-23

### Windows

`agentes/windows/agent` is a functional Go agent. It installs a Windows service and a
scheduled user-session collector, captures policy-controlled foreground activity, keeps a
JSONL offline queue and sends data to the existing FastAPI gateway.

The implementation is concentrated in one Go file of approximately 66 KB. It builds for
Windows, but has no automated tests and `go vet` reports a possible context cancellation
leak in the service loop.

### Linux

`agentes/linux/vulcan_agent.py` is a functional Python agent installed as a user systemd
service. It was active on the authorized development machine during the audit and was
delivering real health and session-quality events.

The Python implementation keeps the shared enrollment token in its local configuration and
uses the legacy HTTP contract.

### Backend

The legacy endpoints `/agent/enroll`, `/agent/heartbeat`, `/agent/events`, `/agent/sync` and
`/agent/logs` use one environment enrollment token for both enrollment and ongoing
communication. The repository provides tenant filters and idempotent event storage, but the
client supplies `tenantId` on every request.

This contract remains available temporarily for installed agents. New installations use the
v2 contract described below.

## Target architecture

```text
vulcan-agent
├── cmd/vulcan-agent
├── internal
│   ├── app            lifecycle and profile assembly
│   ├── collectors     common collector contract and modules
│   ├── config         protected, atomic local configuration
│   ├── contracts      versioned API and event contracts
│   ├── diagnostics    redacted local diagnostics
│   ├── identity       Ed25519 installation identity
│   ├── logging        structured rotating logs
│   ├── policy         signed policy validation and rollback
│   ├── queue          encrypted SQLite offline queue
│   ├── scheduler      adaptive collector scheduling
│   ├── service        Windows service/systemd integration
│   └── transport      HTTPS, signatures, batching and retry
└── packaging
    ├── linux
    └── windows
```

Every collector implements the same lifecycle:

```go
type Collector interface {
    Name() string
    Profiles() []Profile
    Supported(context.Context) bool
    Configure(Policy) error
    Collect(context.Context) ([]Event, error)
    Health(context.Context) Health
}
```

Collectors do not send data directly. They emit canonical events to the encrypted local
queue. A separate sender batches and signs uploads.

## Enrollment v2

1. An authenticated tenant administrator creates a short-lived one-time token.
2. Only the token hash and prefix are stored in PostgreSQL.
3. The agent generates an Ed25519 key pair locally.
4. The enrollment request contains the public key, device fingerprint and requested
   profile.
5. The server resolves the tenant from the token record, never from a client-asserted
   tenant for subsequent requests.
6. The server registers the device and installation identity.
7. The response contains stable identity IDs, server policy-signing public key and a signed
   effective policy.
8. The raw enrollment token is discarded by the agent.

Re-enrollment requires a new valid token and creates an auditable identity transition.
The previous identity is revoked in the same transaction, retained as history and replaced
under a partial unique active-device constraint. Revocation disables the installation
without moving it silently to another tenant.

## Signed transport

After enrollment, each request contains:

- `X-Vulcan-Agent-Id`;
- `X-Vulcan-Timestamp`;
- `X-Vulcan-Nonce`;
- `X-Vulcan-Content-SHA256`;
- `X-Vulcan-Signature`.

The Ed25519 signature covers method, path, timestamp, nonce and body hash. The server checks
the registered public key, clock window, content hash, revocation state and unique nonce
before resolving tenant/device identity.

HTTPS certificate verification is mandatory by default. Plain HTTP is accepted for
explicit loopback development or, mediante `--allow-insecure-private-network`, somente
quando o hostname é um endereço IP privado. O bypass é persistido, aparece no diagnóstico
e nunca autoriza HTTP público.

## Policies

Policies are JSON documents with schema version, revision, scope and module settings. The
server signs the canonical policy envelope with a persistent Ed25519 key stored outside the
database business records in the protected runtime secret directory.

The agent:

- verifies the signature and schema;
- checks profile compatibility and safe limits;
- writes a staged policy;
- atomically activates it;
- keeps the previous valid policy for rollback;
- reports revision and apply status in heartbeat;
- rejects unsigned or invalid policy outside explicit loopback development.

Policy precedence is device, site, tenant and built-in safe defaults. The effective response
records the source of each override.

## Offline queue

SQLite stores encrypted event payloads, priority, occurrence time, attempts and idempotency
key. Payloads use AES-256-GCM with a local random key protected by restrictive filesystem
permissions. Windows packaging also applies ACLs to ProgramData.

Priority order is critical, audit, session, health, productivity and detailed metrics.
Overflow removes the oldest lowest-priority data first. Critical and audit records are
never chosen before lower-priority records; if only protected records remain, enqueue
fails explicitly and the agent reports/logs the failure.

Acknowledged rows are deleted only after a successful server response. `occurredAt` is never
rewritten during replay. A retenção assinada remove eventos locais expirados não críticos;
crítico e auditoria permanecem protegidos e fazem o limite falhar explicitamente se não
houver outro dado descartável.

## Profiles and collectors

| Collector | Workstation | Server | Collector |
| --- | --- | --- | --- |
| agent self-health | yes | yes | yes |
| operating-system inventory | yes | yes | yes |
| CPU/memory/disk | yes | yes | yes |
| network inventory | yes | yes | yes |
| session/activity | policy | no | no |
| server HTTP/TCP probes | no | policy | policy |
| safe network discovery | no | no | policy |
| printing/USB/event logs | contract reserved | contract reserved | no |

Unsupported modules report `unsupported` or `disabled_by_policy`; they do not fabricate
events.

## Commands and updates

The data model permits only typed, signed commands such as policy refresh, diagnostics,
inventory, agent restart, credential rotation and update. There is no arbitrary command,
PowerShell or shell execution endpoint.

The release model stores version, channel, platform, architecture, checksum and manifest
signature. This build produces checksums and a CycloneDX SBOM; publishing signed manifests,
automated replacement and rollback remain disabled until platform-specific release signing
is configured and tested.

## Compatibility and migration

- Legacy Windows and Linux endpoints remain available during controlled migration.
- New agents use `/agent/v2/*`.
- Both flows store into existing `devices`, `activity_events`, `unified_events` and audit
  records.
- The existing Windows scheduled-task change that starts `Vulcan Session Collector`
  immediately after installation is preserved.
- Linux Python remains rollback material until the Go service completes local soak testing.

No database or device data is deleted by the migration.

## Baseline evidence

- Existing API tests: 29 passed.
- Existing Windows cross-build: compiled.
- Existing Windows Go tests: no test files.
- Existing Windows `go vet`: failed on service context cancellation.
- Existing Linux Python service: active for approximately 19 hours.
- Existing Linux resident memory at audit: approximately 14.3 MB.
- Existing Linux device was present in PostgreSQL and delivered real events in the previous
  hour.
- Existing packaging attempted to overwrite files owned by another local build user and was
  therefore isolated instead of deleting those artifacts.

## Delivery status

Implemented and exercised on the authorized Linux development host:

- FastAPI v2 enrollment, signed requests, nonce replay protection, policy and events;
- incremental PostgreSQL migration, tenant-scoped identity and one-time token storage;
- Go core, six collector modules, encrypted SQLite queue and typed commands;
- API outage, offline buffering, restart/reconnection and acknowledged replay;
- duplicate signed request rejection;
- real canonical events visible in `unified_events` and compatible Workforce events;
- incremental guard preventing the compatibility `activity_events` write from generating a
  second canonical v2 event; legacy mirroring remains active;
- non-destructive backfill marking pre-guard mirrors as superseded so timeline/realtime
  suppress only the duplicate representation;
- Agent UI, policy editor, enrollment commands, events and audit;
- Linux/Windows cross-build, `.deb`, MSI, checksums and CycloneDX SBOM.

Final verification evidence on 2026-07-23:

- 58 Python tests passed: API 34, ingestion 3, query 4, jobs 10, AI 2 and
  discovery 5;
- five frontend unit tests and one Chromium end-to-end flow passed, including login,
  Workforce/Infrastructure compatibility, Timeline, the real Agent inventory and installer
  download links;
- frontend lint, strong TypeScript check and optimized production build passed;
- Go race tests and vet passed on Linux and on the Windows amd64 cross-target;
- database validation confirmed RLS/service-only access, hashed enrollment tokens,
  re-enrollment uniqueness and the v2 activity mirror guard;
- the real local protocol exercised enrollment, signed policy, heartbeat, canonical event
  intake, nonce replay rejection, three offline queued events and replay to queue depth zero;
- the development stack answered `200` on health, readiness, liveness, version, Agent v2
  status and frontend/package endpoints with no new traceback or HTTP 500 in reviewed logs.

A short 73-second process sample measured 12.9–13.2 MiB RSS, 0.0% idle CPU, nine threads
and ten open file descriptors. This is evidence for the development host only and does not
replace the pending 24-hour soak.

Not yet claimed as complete:

- runtime installation/SCM validation on a real Windows host;
- `dpkg` installation over the active legacy agent on this host;
- Authenticode/package/manifest signing;
- 24-hour soak and 1,000-agent load;
- printing, detailed Windows events, USB, containers, SNMP, syslog/traps/flows and
  automatic update/rollback.

Unsupported collectors and untested operating-system paths remain explicit limitations.
