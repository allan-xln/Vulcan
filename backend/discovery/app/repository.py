from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.scanner import ScanPolicy, TargetObservation


@dataclass(frozen=True)
class ClaimedRun:
    id: UUID
    tenant_id: UUID
    site_id: UUID
    policy_id: UUID
    requested_by: UUID | None
    policy: ScanPolicy


class DiscoveryRepository:
    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("DATABASE_URL is required by vulcan-discovery")
        self.database_url = database_url

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row, prepare_threshold=None)

    def claim_next_run(self) -> ClaimedRun | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                select run.id, run.tenant_id, run.site_id, run.policy_id, run.requested_by,
                       policy.allowed_networks::text[], policy.denied_networks::text[],
                       coalesce(array(select host(value) from unnest(policy.excluded_addresses) value), '{}') as excluded_addresses,
                       policy.allowed_protocols, policy.allowed_tcp_ports, policy.concurrency,
                       policy.timeout_ms, policy.max_targets
                from public.discovery_runs run
                join public.discovery_policies policy
                  on policy.tenant_id = run.tenant_id and policy.id = run.policy_id
                where run.status = 'queued'
                  and policy.enabled
                  and policy.read_only
                  and policy.safe_mode
                order by run.created_at
                for update of run skip locked
                limit 1
                """
            ).fetchone()
            if not row:
                return None
            conn.execute(
                """
                update public.discovery_runs
                set status = 'running',
                    started_at = timezone('utc', now()),
                    targets_planned = least(%s, %s)
                where id = %s and tenant_id = %s
                """,
                (row["max_targets"], row["max_targets"], row["id"], row["tenant_id"]),
            )
            conn.commit()
        return ClaimedRun(
            id=row["id"],
            tenant_id=row["tenant_id"],
            site_id=row["site_id"],
            policy_id=row["policy_id"],
            requested_by=row["requested_by"],
            policy=ScanPolicy(
                allowed_networks=tuple(row["allowed_networks"]),
                denied_networks=tuple(row["denied_networks"]),
                excluded_addresses=tuple(row["excluded_addresses"]),
                allowed_protocols=tuple(row["allowed_protocols"]),
                allowed_tcp_ports=tuple(row["allowed_tcp_ports"]),
                concurrency=row["concurrency"],
                timeout_ms=row["timeout_ms"],
                max_targets=row["max_targets"],
            ),
        )

    def complete_run(self, run: ClaimedRun, observations: list[TargetObservation]) -> None:
        findings = [observation for observation in observations if observation.present]
        error_count = sum(len(observation.errors) for observation in observations)
        status = "partial" if error_count and findings else "completed"
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            for observation in findings:
                conn.execute(
                    """
                    insert into public.discovery_findings (
                      tenant_id, run_id, site_id, ip_address, hostname, latency_ms,
                      open_ports, state, observed_at, raw_observation
                    )
                    values (%s, %s, %s, %s::inet, %s, %s, %s, 'discovered', %s, %s)
                    on conflict (tenant_id, run_id, ip_address) do update
                    set hostname = excluded.hostname,
                        latency_ms = excluded.latency_ms,
                        open_ports = excluded.open_ports,
                        observed_at = excluded.observed_at,
                        raw_observation = excluded.raw_observation,
                        updated_at = timezone('utc', now())
                    """,
                    (
                        run.tenant_id,
                        run.id,
                        run.site_id,
                        observation.ip_address,
                        observation.hostname,
                        observation.latency_ms,
                        list(observation.open_ports),
                        now,
                        Jsonb(
                            {
                                "present": observation.present,
                                "errors": list(observation.errors),
                                "collector": "vulcan-discovery",
                                "readOnly": True,
                            }
                        ),
                    ),
                )

            summary = {
                "readOnly": True,
                "targetsScanned": len(observations),
                "findings": len(findings),
                "errors": error_count,
            }
            conn.execute(
                """
                update public.discovery_runs
                set status = %s,
                    finished_at = %s,
                    targets_scanned = %s,
                    findings_count = %s,
                    error_count = %s,
                    result_summary = %s
                where tenant_id = %s and id = %s
                """,
                (
                    status,
                    now,
                    len(observations),
                    len(findings),
                    error_count,
                    Jsonb(summary),
                    run.tenant_id,
                    run.id,
                ),
            )
            conn.execute(
                """
                update public.discovery_policies
                set last_run_at = %s,
                    next_run_at = %s + make_interval(mins => frequency_minutes)
                where tenant_id = %s and id = %s
                """,
                (now, now, run.tenant_id, run.policy_id),
            )
            event_id = uuid4()
            fingerprint = hashlib.sha256(
                f"{run.tenant_id}:discovery:{run.id}".encode()
            ).hexdigest()
            conn.execute(
                """
                insert into public.unified_events (
                  id, tenant_id, site_id, source, source_type, source_event_id, event_type,
                  category, severity, occurred_at, received_at, context, metrics, message,
                  technical_message, fingerprint, privacy_classification, retention_policy,
                  trusted_origin, data_origin, extensions
                )
                values (
                  %s, %s, %s, 'vulcan-discovery', 'discovery', %s, 'discovery.completed',
                  'network', %s, %s, %s, %s, %s, %s, %s, %s, 'operational', 'inventory',
                  true, 'real', %s
                )
                on conflict (tenant_id, source, source_event_id) do nothing
                """,
                (
                    event_id,
                    run.tenant_id,
                    run.site_id,
                    str(run.id),
                    "notice" if findings else "info",
                    now,
                    now,
                    Jsonb({"runId": str(run.id), "policyId": str(run.policy_id), "readOnly": True}),
                    Jsonb(summary),
                    f"Discovery somente leitura concluído: {len(findings)} dispositivo(s) observado(s).",
                    f"{len(observations)} alvos consultados; {error_count} erro(s) não fatal(is).",
                    fingerprint,
                    Jsonb({"discoveryRun": True}),
                ),
            )
            conn.execute(
                """
                insert into public.audit_logs (
                  tenant_id, actor_user_id, action, entity_table, entity_id, change_summary,
                  resource_type, resource_id, metadata
                )
                values (%s, %s, 'discovery.completed', 'discovery_run', %s, %s,
                        'discovery_run', %s, %s)
                """,
                (
                    run.tenant_id,
                    run.requested_by,
                    run.id,
                    Jsonb(summary),
                    run.id,
                    Jsonb(summary),
                ),
            )
            conn.commit()

    def fail_run(self, run: ClaimedRun, error: str) -> None:
        safe_error = error[:1000]
        with self._connect() as conn:
            conn.execute(
                """
                update public.discovery_runs
                set status = 'failed',
                    finished_at = timezone('utc', now()),
                    error_count = error_count + 1,
                    error_summary = %s,
                    result_summary = result_summary || %s
                where tenant_id = %s and id = %s
                """,
                (safe_error, Jsonb({"readOnly": True, "failed": True}), run.tenant_id, run.id),
            )
            conn.execute(
                """
                insert into public.audit_logs (
                  tenant_id, actor_user_id, action, entity_table, entity_id, change_summary,
                  resource_type, resource_id, metadata
                )
                values (%s, %s, 'discovery.failed', 'discovery_run', %s, %s,
                        'discovery_run', %s, %s)
                """,
                (
                    run.tenant_id,
                    run.requested_by,
                    run.id,
                    Jsonb({"error": safe_error, "readOnly": True}),
                    run.id,
                    Jsonb({"error": safe_error, "readOnly": True}),
                ),
            )
            conn.commit()
