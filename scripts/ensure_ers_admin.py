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


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def main() -> None:
    database_url = require_env("DATABASE_URL")
    initial_password = require_env("ERS_INITIAL_PASSWORD")
    now = datetime.now(timezone.utc).isoformat()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        conn.execute(
            """
            insert into public.tenants (id, slug, legal_name, display_name, status, country_code, timezone, plan, region, metadata)
            values (%s, 'ers-transportes', 'ERS Transportes', 'ERS Transportes', 'active', 'BR', 'America/Sao_Paulo', 'pilot', 'BR', %s)
            on conflict (id) do update
            set slug = excluded.slug,
                legal_name = excluded.legal_name,
                display_name = excluded.display_name,
                status = 'active',
                timezone = excluded.timezone,
                plan = excluded.plan,
                region = excluded.region,
                metadata = coalesce(public.tenants.metadata, '{}'::jsonb) || excluded.metadata,
                updated_at = timezone('utc', now())
            """,
            (TENANT_ID, Jsonb({"customer": "ERS", "managedBy": "Vulcan", "updatedBy": "ensure_ers_admin", "updatedAt": now})),
        )
        conn.execute(
            """
            insert into public.roles (id, tenant_id, slug, name, description, scope, is_system)
            values (%s, %s, 'ers', 'ERS', 'Administrador máximo do tenant ERS.', 'tenant', true)
            on conflict (id) do update
            set tenant_id = excluded.tenant_id,
                slug = excluded.slug,
                name = excluded.name,
                description = excluded.description,
                scope = excluded.scope,
                is_system = true,
                updated_at = timezone('utc', now())
            """,
            (ERS_ROLE_ID, TENANT_ID),
        )
        conn.execute(
            """
            insert into public.departments (id, tenant_id, parent_department_id, name, slug, description, metadata)
            values (%s, %s, null, 'ERS', 'ers', 'Administração máxima ERS.', %s)
            on conflict (id) do update
            set tenant_id = excluded.tenant_id,
                parent_department_id = null,
                name = excluded.name,
                slug = excluded.slug,
                description = excluded.description,
                metadata = coalesce(public.departments.metadata, '{}'::jsonb) || excluded.metadata,
                updated_at = timezone('utc', now())
            """,
            (ERS_DEPARTMENT_ID, TENANT_ID, Jsonb({"source": "ensure_ers_admin"})),
        )
        conn.execute(
            """
            insert into auth.users (
              id, aud, role, email, encrypted_password, email_confirmed_at,
              raw_app_meta_data, raw_user_meta_data, is_sso_user, is_anonymous,
              created_at, updated_at
            )
            values (
              %s, 'authenticated', 'authenticated', 'ers@erstransportes.local',
              crypt(%s, gen_salt('bf')), timezone('utc', now()),
              %s, %s, false, false, timezone('utc', now()), timezone('utc', now())
            )
            on conflict (id) do update
            set email = excluded.email,
                encrypted_password = excluded.encrypted_password,
                raw_app_meta_data = excluded.raw_app_meta_data,
                raw_user_meta_data = excluded.raw_user_meta_data,
                updated_at = timezone('utc', now())
            """,
            (
                ERS_USER_ID,
                initial_password,
                Jsonb({"provider": "vulcan-local", "tenantAdmin": True}),
                Jsonb({"name": "ERS", "login": "ers", "product": "Vulcan", "passwordTemporary": True, "createdBy": "ensure_ers_admin"}),
            ),
        )
        conn.execute(
            """
            insert into public.user_profiles (user_id, primary_email, display_name, locale, timezone, metadata)
            values (%s, 'ers@erstransportes.local', 'ERS', 'pt-BR', 'America/Sao_Paulo', %s)
            on conflict (user_id) do update
            set primary_email = excluded.primary_email,
                display_name = excluded.display_name,
                metadata = coalesce(public.user_profiles.metadata, '{}'::jsonb) || excluded.metadata,
                updated_at = timezone('utc', now())
            """,
            (ERS_USER_ID, Jsonb({"login": "ers", "passwordTemporary": True, "source": "ensure_ers_admin"})),
        )
        conn.execute(
            """
            insert into public.memberships (
              id, tenant_id, user_id, role_id, department_id, direct_manager_membership_id,
              status, full_name, work_email, phone, whatsapp, title, hierarchy_level, joined_at, metadata
            )
            values (%s, %s, %s, %s, %s, null, 'active', 'ERS', 'ers@erstransportes.local', null, null, 'ERS', 0, timezone('utc', now()), %s)
            on conflict (id) do update
            set tenant_id = excluded.tenant_id,
                user_id = excluded.user_id,
                role_id = excluded.role_id,
                department_id = excluded.department_id,
                direct_manager_membership_id = null,
                status = 'active',
                full_name = excluded.full_name,
                work_email = excluded.work_email,
                title = excluded.title,
                hierarchy_level = 0,
                metadata = coalesce(public.memberships.metadata, '{}'::jsonb) || excluded.metadata,
                updated_at = timezone('utc', now())
            """,
            (
                ERS_MEMBERSHIP_ID,
                TENANT_ID,
                ERS_USER_ID,
                ERS_ROLE_ID,
                ERS_DEPARTMENT_ID,
                Jsonb({"source": "ensure_ers_admin", "passwordTemporary": True, "lgpdPolicy": "corporate-operational"}),
            ),
        )
        conn.execute("select public.vulcan_refresh_membership_closure(%s)", (TENANT_ID,))
        conn.execute(
            """
            insert into public.audit_logs (
              tenant_id, actor_user_id, action,
              entity_table, entity_id, change_summary,
              resource_type, resource_id, metadata, created_at
            )
            values
              (%s, null, 'ers_admin.ensured', 'membership', %s, %s, 'membership', %s, %s, timezone('utc', now())),
              (%s, null, 'role.ers.ensured', 'role', %s, %s, 'role', %s, %s, timezone('utc', now()))
            """,
            (
                TENANT_ID,
                ERS_MEMBERSHIP_ID,
                Jsonb({"login": "ERS", "password": "***", "passwordTemporary": True}),
                ERS_MEMBERSHIP_ID,
                Jsonb({"login": "ERS", "password": "***", "passwordTemporary": True}),
                TENANT_ID,
                ERS_ROLE_ID,
                Jsonb({"slug": "ers", "scope": "tenant"}),
                ERS_ROLE_ID,
                Jsonb({"slug": "ers", "scope": "tenant"}),
            ),
        )
        conn.commit()

    print(f"ERS admin ready tenant={TENANT_ID} user=ERS membership={ERS_MEMBERSHIP_ID} role={ERS_ROLE_ID}")


if __name__ == "__main__":
    main()
