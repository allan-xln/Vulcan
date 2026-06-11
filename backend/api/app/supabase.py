from __future__ import annotations

import httpx
import psycopg

from app.config import Settings
from app.schemas import SupabaseStatus


REQUIRED_ITEMS = [
    "NEXT_PUBLIC_SUPABASE_URL",
    "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "DATABASE_URL",
    "DIRECT_DATABASE_URL",
    "SUPABASE_PROJECT_REF",
    "RLS policies applied through database/supabase/migrations",
    "Supabase Auth providers enabled",
    "authorized redirect URLs",
    "Storage buckets and policies",
]


def _rest_url(settings: Settings) -> str | None:
    if settings.supabase_rest_url:
        return settings.supabase_rest_url.rstrip("/")
    if settings.supabase_url:
        return f"{settings.supabase_url.rstrip('/')}/rest/v1"
    return None


def supabase_status(settings: Settings) -> SupabaseStatus:
    rest_url = _rest_url(settings)
    api_key = settings.supabase_publishable_key or settings.supabase_anon_key
    rest_reachable: bool | None = None
    database_reachable: bool | None = None

    if rest_url and api_key:
        try:
            response = httpx.get(
                rest_url,
                headers={"apikey": api_key, "Authorization": f"Bearer {api_key}"},
                timeout=6,
            )
            rest_reachable = response.status_code < 500
        except httpx.HTTPError:
            rest_reachable = False

    if settings.database_url:
        try:
            with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
                conn.execute("select 1").fetchone()
            database_reachable = True
        except psycopg.Error:
            database_reachable = False

    configured = all(
        [
            settings.supabase_url,
            api_key,
            settings.supabase_service_role_key,
            settings.database_url,
        ]
    )

    return SupabaseStatus(
        configured=configured,
        projectRef=settings.supabase_project_ref,
        urlConfigured=settings.supabase_url is not None,
        restUrlConfigured=rest_url is not None,
        publishableKeyConfigured=settings.supabase_publishable_key is not None,
        anonKeyConfigured=settings.supabase_anon_key is not None,
        serviceRoleConfigured=settings.supabase_service_role_key is not None,
        databaseUrlConfigured=settings.database_url is not None,
        restReachable=rest_reachable,
        databaseReachable=database_reachable,
        authProvider=settings.auth_provider,
        requiredItems=REQUIRED_ITEMS,
    )
