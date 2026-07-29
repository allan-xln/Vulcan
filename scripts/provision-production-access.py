from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def required(name: str) -> str:
    file_path = os.getenv(f"{name}_FILE", "").strip()
    if file_path:
        try:
            value = Path(file_path).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise SystemExit(f"{name}_FILE could not be read") from exc
    else:
        value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is required")
    return value


def ensure_user(
    conn: psycopg.Connection,
    *,
    email: str,
    login: str,
    password: str,
    display_name: str,
    rotate_password: bool,
) -> UUID:
    existing = conn.execute(
        "select id from auth.users where lower(email::text) = lower(%s) limit 1",
        (email,),
    ).fetchone()
    user_id = UUID(str(existing["id"])) if existing else uuid4()
    conn.execute(
        """
        insert into auth.users (
          id, aud, role, email, encrypted_password, email_confirmed_at,
          raw_app_meta_data, raw_user_meta_data, is_sso_user, is_anonymous,
          created_at, updated_at
        )
        values (
          %s, 'authenticated', 'authenticated', %s,
          crypt(%s, gen_salt('bf')), timezone('utc', now()),
          %s, %s, false, false, timezone('utc', now()), timezone('utc', now())
        )
        on conflict (id) do update
        set email = excluded.email,
            encrypted_password = case
              when %s then excluded.encrypted_password
              else auth.users.encrypted_password
            end,
            raw_app_meta_data = excluded.raw_app_meta_data,
            raw_user_meta_data = excluded.raw_user_meta_data,
            deleted_at = null,
            banned_until = null,
            updated_at = timezone('utc', now())
        """,
        (
            user_id,
            email,
            password,
            Jsonb({"provider": "vulcan-database"}),
            Jsonb(
                {
                    "name": display_name,
                    "login": login,
                    "product": "Vulcan",
                    "passwordTemporary": True,
                    "createdBy": "provision-production-access",
                }
            ),
            rotate_password,
        ),
    )
    conn.execute(
        """
        insert into public.user_profiles (
          user_id, primary_email, display_name, locale, timezone, metadata
        )
        values (%s, %s, %s, 'pt-BR', 'America/Sao_Paulo', %s)
        on conflict (user_id) do update
        set primary_email = excluded.primary_email,
            display_name = excluded.display_name,
            metadata = coalesce(public.user_profiles.metadata, '{}'::jsonb) || excluded.metadata,
            updated_at = timezone('utc', now())
        """,
        (user_id, email, display_name, Jsonb({"login": login, "passwordTemporary": True})),
    )
    return user_id


def ensure_membership(
    conn: psycopg.Connection,
    *,
    tenant_id: UUID,
    user_id: UUID,
    role_slug: str,
    email: str,
    display_name: str,
    title: str,
) -> UUID:
    role = conn.execute(
        "select id from public.roles where tenant_id = %s and slug = %s",
        (tenant_id, role_slug),
    ).fetchone()
    if not role:
        raise SystemExit(f"required tenant role is missing: {role_slug}")
    existing = conn.execute(
        "select id from public.memberships where tenant_id = %s and user_id = %s",
        (tenant_id, user_id),
    ).fetchone()
    membership_id = UUID(str(existing["id"])) if existing else uuid4()
    conn.execute(
        """
        insert into public.memberships (
          id, tenant_id, user_id, role_id, status, full_name, work_email,
          title, hierarchy_level, joined_at, metadata
        )
        values (
          %s, %s, %s, %s, 'active', %s, %s, %s, 0,
          timezone('utc', now()), %s
        )
        on conflict (id) do update
        set role_id = excluded.role_id,
            status = 'active',
            full_name = excluded.full_name,
            work_email = excluded.work_email,
            title = excluded.title,
            metadata = coalesce(public.memberships.metadata, '{}'::jsonb) || excluded.metadata,
            updated_at = timezone('utc', now())
        """,
        (
            membership_id,
            tenant_id,
            user_id,
            role["id"],
            display_name,
            email,
            title,
            Jsonb({"source": "provision-production-access", "passwordTemporary": True}),
        ),
    )
    return membership_id


def main() -> None:
    database_url = required("DATABASE_URL")
    root_password = required("VULCAN_ROOT_INITIAL_PASSWORD")
    admin_password = required("ERS_ADMIN_INITIAL_PASSWORD")
    wallboard_password = required("ERS_WALLBOARD_INITIAL_PASSWORD")
    root_email = os.getenv("VULCAN_ROOT_EMAIL", "root@vulcan.local").strip().lower()
    admin_email = os.getenv("ERS_ADMIN_EMAIL", "admin.ers@erstransportes.local").strip().lower()
    wallboard_email = os.getenv("ERS_WALLBOARD_EMAIL", "wallboard@erstransportes.local").strip().lower()
    rotate_passwords = os.getenv("VULCAN_ROTATE_PROVISIONED_PASSWORDS", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        conn.execute(
            """
            insert into public.tenants (
              slug, legal_name, display_name, status, country_code, timezone, plan, region, metadata
            )
            values (
              'ers-transportes', 'ERS Transportes', 'ERS Transportes', 'active',
              'BR', 'America/Sao_Paulo', 'pilot', 'BR', %s
            )
            on conflict (slug) do update
            set legal_name = excluded.legal_name,
                display_name = excluded.display_name,
                status = 'active',
                timezone = excluded.timezone,
                metadata = coalesce(public.tenants.metadata, '{}'::jsonb) || excluded.metadata,
                updated_at = timezone('utc', now())
            """,
            (Jsonb({"customer": "ERS Transportes", "production": True}),),
        )
        tenant = conn.execute(
            "select id from public.tenants where slug = 'ers-transportes' and status = 'active'"
        ).fetchone()
        if not tenant:
            raise SystemExit("active tenant ers-transportes was not found")
        tenant_id = UUID(str(tenant["id"]))

        root_user_id = ensure_user(
            conn,
            email=root_email,
            login="vulcan-root",
            password=root_password,
            display_name="Root Vulcan",
            rotate_password=rotate_passwords,
        )
        conn.execute(
            "insert into public.vulcan_root_users (user_id) values (%s) on conflict (user_id) do nothing",
            (root_user_id,),
        )

        admin_user_id = ensure_user(
            conn,
            email=admin_email,
            login="ers-admin",
            password=admin_password,
            display_name="Administrador ERS",
            rotate_password=rotate_passwords,
        )
        admin_membership_id = ensure_membership(
            conn,
            tenant_id=tenant_id,
            user_id=admin_user_id,
            role_slug="tenant_admin",
            email=admin_email,
            display_name="Administrador ERS",
            title="Administrador do tenant",
        )

        wallboard_user_id = ensure_user(
            conn,
            email=wallboard_email,
            login="ers-wallboard",
            password=wallboard_password,
            display_name="Wallboard ERS",
            rotate_password=rotate_passwords,
        )
        wallboard_membership_id = ensure_membership(
            conn,
            tenant_id=tenant_id,
            user_id=wallboard_user_id,
            role_slug="read_only",
            email=wallboard_email,
            display_name="Wallboard ERS",
            title="Wallboard somente leitura",
        )

        conn.execute(
            """
            update public.tenant_modules
            set enabled = module_key in (
                  'workforce', 'infrastructure', 'assets', 'timeline',
                  'agents', 'print', 'intelligence', 'wallboard',
                  'automations', 'compliance', 'administration'
                ),
                enabled_at = case
                  when module_key in (
                    'workforce', 'infrastructure', 'assets', 'timeline',
                    'agents', 'print', 'intelligence', 'wallboard',
                    'automations', 'compliance', 'administration'
                  ) then coalesce(enabled_at, timezone('utc', now()))
                  else null
                end,
                limits = case
                  when module_key = 'automations'
                    then jsonb_set(limits, '{mode}', '"read_only"'::jsonb, true)
                  else limits
                end,
                plan_source = case when module_key = 'workforce' then 'system' else 'tenant' end
            where tenant_id = %s
            """,
            (tenant_id,),
        )
        conn.execute("select public.vulcan_refresh_membership_closure(%s)", (tenant_id,))
        conn.execute(
            """
            insert into public.audit_logs (
              tenant_id, actor_user_id, action, entity_table, entity_id,
              change_summary, resource_type, resource_id, metadata, created_at
            )
            values
              (%s, %s, 'production_access.provisioned', 'membership', %s, %s,
               'membership', %s, %s, timezone('utc', now())),
              (%s, %s, 'wallboard_access.provisioned', 'membership', %s, %s,
               'membership', %s, %s, timezone('utc', now()))
            """,
            (
                tenant_id,
                root_user_id,
                admin_membership_id,
                Jsonb({"role": "tenant_admin", "password": "***"}),
                admin_membership_id,
                Jsonb({"source": "production-release"}),
                tenant_id,
                root_user_id,
                wallboard_membership_id,
                Jsonb({"role": "read_only", "password": "***"}),
                wallboard_membership_id,
                Jsonb({"source": "production-release"}),
            ),
        )
        conn.commit()

    print(
        "Production access ready "
        f"tenant={tenant_id} root={root_email} admin={admin_email} wallboard={wallboard_email}"
    )


if __name__ == "__main__":
    main()
