from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import UUID

from psycopg.rows import dict_row

from app.config import get_settings

if TYPE_CHECKING:
    from psycopg import Connection


@dataclass(frozen=True)
class AuthContext:
    user_id: UUID
    tenant_id: UUID


class AuthorizationError(PermissionError):
    pass


class PostgresQueryRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or get_settings().database_url

    def _connect(self) -> "Connection":
        from psycopg import connect

        return connect(self._database_url, row_factory=dict_row)

    def assert_member(self, user_id: UUID, tenant_id: UUID) -> AuthContext:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    select 1
                    from public.memberships
                    where user_id = %(user_id)s
                      and tenant_id = %(tenant_id)s
                      and status = 'active'
                    limit 1
                    """,
                    {"user_id": user_id, "tenant_id": tenant_id},
                )
                if cursor.fetchone() is None:
                    raise AuthorizationError("user is not an active member of the tenant")

        return AuthContext(user_id=user_id, tenant_id=tenant_id)

    def _fetch_rows(
        self,
        *,
        auth: AuthContext,
        count_sql: str,
        data_sql: str,
        params: dict[str, Any],
    ) -> tuple[int, list[dict[str, Any]]]:
        with self._connect() as conn:
            with conn.transaction():
                with conn.cursor() as cursor:
                    cursor.execute("set local role authenticated")
                    cursor.execute("select set_config('request.jwt.claim.sub', %(user_id)s, true)", {"user_id": str(auth.user_id)})
                    cursor.execute(count_sql, params)
                    total = cursor.fetchone()["total"]
                    cursor.execute(data_sql, params)
                    items = cursor.fetchall()
        return total, items

    def get_daily_metrics(
        self,
        *,
        auth: AuthContext,
        date_from,
        date_to,
        workstation_id,
        username,
        limit: int,
        offset: int,
    ) -> tuple[int, list[dict[str, Any]]]:
        filters = [
            "tenant_id = %(tenant_id)s",
            "(%(date_from)s::date is null or metric_date >= %(date_from)s::date)",
            "(%(date_to)s::date is null or metric_date <= %(date_to)s::date)",
            "(%(workstation_id)s::uuid is null or workstation_id = %(workstation_id)s::uuid)",
            "(%(username)s::text is null or username = %(username)s::text)",
        ]
        where_clause = " and ".join(filters)
        params = {
            "tenant_id": auth.tenant_id,
            "date_from": date_from,
            "date_to": date_to,
            "workstation_id": workstation_id,
            "username": username,
            "limit": limit,
            "offset": offset,
        }
        count_sql = f"select count(*)::int as total from public.daily_user_operational_metrics where {where_clause}"
        data_sql = f"""
            select *
            from public.daily_user_operational_metrics
            where {where_clause}
            order by metric_date desc, username nulls last, workstation_id nulls last
            limit %(limit)s offset %(offset)s
        """
        return self._fetch_rows(auth=auth, count_sql=count_sql, data_sql=data_sql, params=params)

    def get_session_slices(
        self,
        *,
        auth: AuthContext,
        date_from,
        date_to,
        workstation_id,
        username,
        limit: int,
        offset: int,
    ) -> tuple[int, list[dict[str, Any]]]:
        filters = [
            "tenant_id = %(tenant_id)s",
            "(%(date_from)s::date is null or started_at::date >= %(date_from)s::date)",
            "(%(date_to)s::date is null or started_at::date <= %(date_to)s::date)",
            "(%(workstation_id)s::uuid is null or workstation_id = %(workstation_id)s::uuid)",
            "(%(username)s::text is null or username = %(username)s::text)",
        ]
        where_clause = " and ".join(filters)
        params = {
            "tenant_id": auth.tenant_id,
            "date_from": date_from,
            "date_to": date_to,
            "workstation_id": workstation_id,
            "username": username,
            "limit": limit,
            "offset": offset,
        }
        count_sql = f"select count(*)::int as total from public.session_slices where {where_clause}"
        data_sql = f"""
            select *
            from public.session_slices
            where {where_clause}
            order by started_at desc, id desc
            limit %(limit)s offset %(offset)s
        """
        return self._fetch_rows(auth=auth, count_sql=count_sql, data_sql=data_sql, params=params)

    def get_idle_windows(
        self,
        *,
        auth: AuthContext,
        date_from,
        date_to,
        workstation_id,
        username,
        limit: int,
        offset: int,
    ) -> tuple[int, list[dict[str, Any]]]:
        filters = [
            "iw.tenant_id = %(tenant_id)s",
            "(%(date_from)s::date is null or iw.started_at::date >= %(date_from)s::date)",
            "(%(date_to)s::date is null or iw.started_at::date <= %(date_to)s::date)",
            "(%(workstation_id)s::uuid is null or iw.workstation_id = %(workstation_id)s::uuid)",
            "(%(username)s::text is null or ss.username = %(username)s::text)",
        ]
        where_clause = " and ".join(filters)
        params = {
            "tenant_id": auth.tenant_id,
            "date_from": date_from,
            "date_to": date_to,
            "workstation_id": workstation_id,
            "username": username,
            "limit": limit,
            "offset": offset,
        }
        join_sql = """
            from public.idle_windows iw
            left join public.session_slices ss
              on ss.tenant_id = iw.tenant_id
             and ss.workstation_id is not distinct from iw.workstation_id
             and ss.session_id = iw.session_id
             and iw.started_at >= ss.started_at
             and (ss.ended_at is null or iw.started_at <= ss.ended_at)
        """
        count_sql = f"select count(*)::int as total {join_sql} where {where_clause}"
        data_sql = f"""
            select
              iw.id,
              iw.tenant_id,
              iw.workstation_id,
              iw.session_id,
              iw.started_at,
              iw.ended_at,
              iw.duration_seconds,
              iw.idle_threshold_seconds,
              iw.closure_reason,
              iw.is_open
            {join_sql}
            where {where_clause}
            order by iw.started_at desc, iw.id desc
            limit %(limit)s offset %(offset)s
        """
        return self._fetch_rows(auth=auth, count_sql=count_sql, data_sql=data_sql, params=params)

    def get_application_usage_facts(
        self,
        *,
        auth: AuthContext,
        date_from,
        date_to,
        workstation_id,
        username,
        limit: int,
        offset: int,
    ) -> tuple[int, list[dict[str, Any]]]:
        filters = [
            "auf.tenant_id = %(tenant_id)s",
            "(%(date_from)s::date is null or auf.started_at::date >= %(date_from)s::date)",
            "(%(date_to)s::date is null or auf.started_at::date <= %(date_to)s::date)",
            "(%(workstation_id)s::uuid is null or auf.workstation_id = %(workstation_id)s::uuid)",
            "(%(username)s::text is null or ss.username = %(username)s::text)",
        ]
        where_clause = " and ".join(filters)
        params = {
            "tenant_id": auth.tenant_id,
            "date_from": date_from,
            "date_to": date_to,
            "workstation_id": workstation_id,
            "username": username,
            "limit": limit,
            "offset": offset,
        }
        join_sql = """
            from public.application_usage_facts auf
            left join public.session_slices ss
              on ss.tenant_id = auf.tenant_id
             and ss.workstation_id is not distinct from auf.workstation_id
             and ss.session_id is not distinct from auf.session_id
             and auf.started_at >= ss.started_at
             and (ss.ended_at is null or auf.started_at <= ss.ended_at)
        """
        count_sql = f"select count(*)::int as total {join_sql} where {where_clause}"
        data_sql = f"""
            select
              auf.id,
              auf.tenant_id,
              auf.workstation_id,
              auf.session_id,
              auf.app_name,
              auf.process_name,
              auf.started_at,
              auf.ended_at,
              auf.duration_seconds,
              auf.end_reason,
              auf.is_open
            {join_sql}
            where {where_clause}
            order by auf.started_at desc, auf.id desc
            limit %(limit)s offset %(offset)s
        """
        return self._fetch_rows(auth=auth, count_sql=count_sql, data_sql=data_sql, params=params)

