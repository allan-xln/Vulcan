from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


TENANT_ID = UUID(os.getenv("ERS_TENANT_ID", "00000000-0000-0000-0000-000000000301"))
ERS_USER_ID = UUID(os.getenv("ERS_USER_ID", "00000000-0000-0000-0000-000000400101"))
ERS_MEMBERSHIP_ID = UUID(os.getenv("ERS_MEMBERSHIP_ID", "00000000-0000-0000-0000-000000300101"))
ERS_ROLE_ID = UUID(os.getenv("ERS_ROLE_ID", "00000000-0000-0000-0000-000000100101"))
ERS_DEPARTMENT_ID = UUID(os.getenv("ERS_DEPARTMENT_ID", "00000000-0000-0000-0000-000000200101"))


DELETE_ORDER = [
    "whatsapp_delivery_logs",
    "whatsapp_delivery_queue",
    "notifications",
    "notification_preferences",
    "notification_schedules",
    "ai_insights",
    "tenant_usage",
    "daily_user_operational_metrics",
    "daily_metric_runs",
    "operational_metrics",
    "application_usage_facts",
    "idle_windows",
    "session_slices",
    "normalized_operational_events",
    "raw_operational_event_intake",
    "activity_events",
    "normalization_runs",
    "operational_fact_runs",
    "agent_installations",
    "devices",
    "workstations",
    "team_members",
    "teams",
    "employee_profiles",
    "membership_closure",
    "org_closure",
    "org_edges",
    "org_nodes",
    "audit_logs",
    "feature_flags",
    "ingestion_api_keys",
    "operational_event_policies",
    "root_whatsapp_templates",
]


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def tenant_counts(conn: psycopg.Connection[dict_row]) -> dict[str, int]:
    rows = conn.execute(
        """
        select table_name
          from information_schema.columns
         where table_schema = 'public'
           and column_name = 'tenant_id'
         order by table_name
        """
    ).fetchall()
    counts: dict[str, int] = {}
    for row in rows:
        table_name = row["table_name"]
        result = conn.execute(f"select count(*) as count from public.{table_name} where tenant_id = %s", (TENANT_ID,)).fetchone()
        counts[table_name] = int(result["count"])
    return counts


def main() -> None:
    database_url = require_env("DATABASE_URL")
    now = datetime.now(timezone.utc).isoformat()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        before = tenant_counts(conn)
        for table_name in DELETE_ORDER:
            conn.execute(f"delete from public.{table_name} where tenant_id = %s", (TENANT_ID,))
        conn.execute(
            """
            delete from public.memberships
             where tenant_id = %s
               and id <> %s
            """,
            (TENANT_ID, ERS_MEMBERSHIP_ID),
        )
        conn.execute(
            """
            delete from public.roles
             where tenant_id = %s
               and id <> %s
            """,
            (TENANT_ID, ERS_ROLE_ID),
        )
        conn.execute(
            """
            delete from public.departments
             where tenant_id = %s
               and id <> %s
            """,
            (TENANT_ID, ERS_DEPARTMENT_ID),
        )
        conn.execute(
            """
            update public.tenants
               set status = 'active',
                   plan = 'pilot',
                   metadata = jsonb_build_object(
                     'customer', 'ERS',
                     'managedBy', 'Vulcan',
                     'cleanPilot', true,
                     'resetBy', 'reset_ers_tenant',
                     'resetAt', %s::text
                   ),
                   updated_at = timezone('utc', now())
             where id = %s
            """,
            (now, TENANT_ID),
        )
        conn.execute(
            """
            insert into public.audit_logs (
              tenant_id, actor_user_id, action,
              entity_table, entity_id, change_summary,
              resource_type, resource_id, metadata, created_at
            )
            values (%s, %s, 'tenant.ers.reset_clean_pilot', 'tenant', %s, %s, 'tenant', %s, %s, timezone('utc', now()))
            """,
            (
                TENANT_ID,
                ERS_USER_ID,
                TENANT_ID,
                Jsonb({"preservedUser": "ERS", "purpose": "clean customer pilot"}),
                TENANT_ID,
                Jsonb({"resetAt": now}),
            ),
        )
        conn.commit()
        after = tenant_counts(conn)
    print({"tenantId": str(TENANT_ID), "before": before, "after": after})


if __name__ == "__main__":
    main()
