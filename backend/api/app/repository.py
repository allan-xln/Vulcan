from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import Settings, get_settings
from app.data import ACTIVITY_EVENTS, DEVICES, HIERARCHY, INSIGHTS, METRICS, NOTIFICATIONS, TENANTS, USERS
from app.schemas import (
    ActivityEventCreate,
    ActivityEventCreateResponse,
    AgentEnrollRequest,
    AgentEnrollResponse,
    AgentEventsRequest,
    AgentEventsResponse,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentLogsRequest,
    DeviceOwnerUpdate,
    MembershipCreate,
    MembershipUpdate,
    NotificationSendRequest,
    NotificationSendResponse,
)
from app.security import AuthContext


DEMO_TEST_MEMBERSHIP_ID = UUID("00000000-0000-0000-0000-000000300005")
DEMO_TENANT_ID = UUID("00000000-0000-0000-0000-000000000301")


@dataclass(frozen=True)
class AccessScope:
    tenant_id: UUID
    user_id: str
    membership_id: UUID | None
    scope: str
    is_root: bool
    local_test: bool = False


class VulcanRepository:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.database_url) and not self.settings.mock_data

    def _connect(self) -> psycopg.Connection:
        if not self.settings.database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        return psycopg.connect(self.settings.database_url, row_factory=dict_row)

    def _access(self, conn: psycopg.Connection, context: AuthContext) -> AccessScope:
        if context.provider == "local":
            membership = conn.execute(
                """
                select m.id, coalesce(r.scope, 'self') as scope
                from public.memberships m
                left join public.roles r on r.id = m.role_id
                where m.tenant_id = %s
                  and m.user_id = %s::uuid
                  and m.status = 'active'
                limit 1
                """,
                (context.tenant_id, context.user_id),
            ).fetchone()
            if membership:
                return AccessScope(
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    membership_id=membership["id"],
                    scope="tenant" if context.role in {"tenant_admin", "owner", "root"} else membership["scope"],
                    is_root=False,
                    local_test=False,
                )
            if context.role == "user":
                return AccessScope(
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    membership_id=None,
                    scope="self",
                    is_root=False,
                    local_test=False,
                )
            return AccessScope(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                membership_id=None,
                scope="tenant",
                is_root=False,
            )

        root = conn.execute(
            "select exists(select 1 from public.vulcan_root_users where user_id = %s::uuid)",
            (context.user_id,),
        ).fetchone()
        if root and root["exists"]:
            return AccessScope(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                membership_id=None,
                scope="global",
                is_root=True,
            )

        membership = conn.execute(
            """
            select m.id, coalesce(r.scope, 'self') as scope
            from public.memberships m
            left join public.roles r on r.id = m.role_id
            where m.tenant_id = %s
              and m.user_id = %s::uuid
              and m.status = 'active'
            limit 1
            """,
            (context.tenant_id, context.user_id),
        ).fetchone()

        if not membership:
            return AccessScope(
                tenant_id=context.tenant_id,
                user_id=context.user_id,
                membership_id=None,
                scope="self",
                is_root=False,
            )

        return AccessScope(
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            membership_id=membership["id"],
            scope=membership["scope"],
            is_root=False,
        )

    def _membership_filter(self, access: AccessScope, alias: str = "m") -> tuple[str, tuple[object, ...]]:
        if access.is_root:
            return "true", ()
        if access.scope in {"tenant", "global"}:
            return f"{alias}.tenant_id = %s", (access.tenant_id,)
        if access.membership_id is None:
            return "false", ()
        return (
            f"""{alias}.tenant_id = %s and {alias}.id in (
                select descendant_membership_id
                from public.membership_closure
                where tenant_id = %s and ancestor_membership_id = %s
            )""",
            (access.tenant_id, access.tenant_id, access.membership_id),
        )

    def _owner_filter(self, access: AccessScope, owner_column: str, tenant_column: str = "tenant_id") -> tuple[str, tuple[object, ...]]:
        if access.is_root:
            return "true", ()
        if access.scope in {"tenant", "global"}:
            return f"{tenant_column} = %s", (access.tenant_id,)
        if access.membership_id is None:
            return "false", ()
        return (
            f"""{tenant_column} = %s and (
                {owner_column} in (
                    select descendant_membership_id
                    from public.membership_closure
                    where tenant_id = %s and ancestor_membership_id = %s
                )
            )""",
            (access.tenant_id, access.tenant_id, access.membership_id),
        )

    def _real_agent_data_filter(self, access: AccessScope, alias: str) -> str:
        if not access.local_test:
            return "true"
        return f"coalesce({alias}.metadata ->> 'seed', '') <> 'vulcan-demo'"

    def _resolve_agent_membership(
        self,
        conn: psycopg.Connection,
        tenant_id: UUID,
        requested_membership_id: UUID | None,
        linked_user: str | None = None,
        os_user: str | None = None,
    ) -> UUID | None:
        if requested_membership_id:
            row = conn.execute(
                "select id from public.memberships where tenant_id = %s and id = %s and status = 'active'",
                (tenant_id, requested_membership_id),
            ).fetchone()
            return requested_membership_id if row else None

        candidates = [value.strip() for value in [linked_user, os_user] if value and value.strip()]
        if tenant_id == DEMO_TENANT_ID and any(value.lower() == "teste" for value in candidates):
            row = conn.execute(
                "select id from public.memberships where tenant_id = %s and id = %s and status = 'active'",
                (tenant_id, DEMO_TEST_MEMBERSHIP_ID),
            ).fetchone()
            if row:
                return DEMO_TEST_MEMBERSHIP_ID

        for candidate in candidates:
            row = conn.execute(
                """
                select id
                from public.memberships
                where tenant_id = %s
                  and status = 'active'
                  and (
                    lower(full_name) = lower(%s)
                    or lower(coalesce(work_email::text, '')) = lower(%s)
                    or lower(coalesce(metadata ->> 'linkedUser', '')) = lower(%s)
                  )
                order by updated_at desc nulls last
                limit 1
                """,
                (tenant_id, candidate, candidate, candidate),
            ).fetchone()
            if row:
                return row["id"]
        return None

    def _repair_local_test_agent_scope(self, conn: psycopg.Connection, access: AccessScope) -> None:
        if not access.local_test or access.tenant_id != DEMO_TENANT_ID:
            return

        membership_id = self._resolve_agent_membership(
            conn,
            access.tenant_id,
            access.membership_id,
            linked_user="teste",
        )
        if not membership_id:
            return

        linked_devices = conn.execute(
            """
            update public.devices
            set owner_membership_id = %s,
                metadata = metadata || %s,
                updated_at = timezone('utc', now())
            where tenant_id = %s
              and owner_membership_id is distinct from %s
              and coalesce(metadata ->> 'seed', '') <> 'vulcan-demo'
              and coalesce(metadata ->> 'source', '') = 'vulcan-agent'
              and lower(coalesce(metadata ->> 'linkedUser', '')) = 'teste'
            returning id
            """,
            (
                membership_id,
                Jsonb({"autoLinkedMembershipId": str(membership_id), "autoLinkedReason": "local-test-linked-user"}),
                access.tenant_id,
                membership_id,
            ),
        ).fetchall()

        linked_events = conn.execute(
            """
            update public.activity_events e
            set membership_id = %s,
                metadata = e.metadata || %s
            where e.tenant_id = %s
              and e.membership_id is null
              and coalesce(e.metadata ->> 'seed', '') <> 'vulcan-demo'
              and coalesce(e.metadata ->> 'source', '') = 'vulcan-agent'
              and exists (
                select 1
                from public.devices d
                where d.tenant_id = e.tenant_id
                  and d.id = e.device_id
                  and d.owner_membership_id = %s
              )
            returning id
            """,
            (
                membership_id,
                Jsonb({"autoLinkedMembershipId": str(membership_id), "autoLinkedReason": "local-test-device-owner"}),
                access.tenant_id,
                membership_id,
            ),
        ).fetchall()

        linked_metrics = conn.execute(
            """
            update public.operational_metrics om
            set membership_id = %s,
                metadata = om.metadata || %s
            where om.tenant_id = %s
              and om.membership_id is null
              and coalesce(om.metadata ->> 'seed', '') <> 'vulcan-demo'
              and coalesce(om.metadata ->> 'source', '') = 'vulcan-agent'
              and exists (
                select 1
                from public.activity_events e
                where e.tenant_id = om.tenant_id
                  and e.membership_id = %s
                  and e.metadata ->> 'eventId' = om.metadata ->> 'eventId'
              )
            returning id
            """,
            (
                membership_id,
                Jsonb({"autoLinkedMembershipId": str(membership_id), "autoLinkedReason": "local-test-event-match"}),
                access.tenant_id,
                membership_id,
            ),
        ).fetchall()

        if linked_devices or linked_events or linked_metrics:
            self.write_agent_audit(
                conn,
                access.tenant_id,
                "agent.local_test_scope_repaired",
                "membership",
                membership_id,
                {
                    "devices": len(linked_devices),
                    "events": len(linked_events),
                    "metrics": len(linked_metrics),
                },
            )
            conn.commit()

    def list_tenants(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return TENANTS
        with self._connect() as conn:
            access = self._access(conn, context)
            if access.is_root:
                rows = conn.execute(
                    "select id, display_name as name, slug, plan, region, status from public.tenants order by display_name"
                ).fetchall()
            else:
                rows = conn.execute(
                    "select id, display_name as name, slug, plan, region, status from public.tenants where id = %s",
                    (access.tenant_id,),
                ).fetchall()
            return list(rows)

    def list_departments(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            condition = "true" if access.is_root else "tenant_id = %s"
            params = () if access.is_root else (access.tenant_id,)
            return list(conn.execute(
                f"""
                select id, tenant_id as "tenantId", parent_department_id as "parentDepartmentId",
                       name, slug, description
                from public.departments
                where {condition}
                order by name
                """,
                params,
            ).fetchall())

    def list_roles(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            condition = "tenant_id is null" if not access.is_root else "true"
            params: tuple[object, ...] = ()
            if not access.is_root:
                condition = "(tenant_id is null or tenant_id = %s)"
                params = (access.tenant_id,)
            return list(conn.execute(
                f"""
                select id, tenant_id as "tenantId", slug, name, description,
                       coalesce(scope, 'tenant') as scope,
                       coalesce(is_system, false) as "isSystem"
                from public.roles
                where {condition}
                order by is_system desc, name
                """,
                params,
            ).fetchall())

    def list_memberships(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._membership_filter(access)
            return list(conn.execute(
                f"""
                select m.id, m.tenant_id as "tenantId", m.user_id as "userId",
                       m.role_id as "roleId", m.department_id as "departmentId",
                       m.direct_manager_membership_id as "directManagerMembershipId",
                       m.status, m.full_name as "fullName", m.work_email as "workEmail",
                       m.phone, m.whatsapp, m.title, m.hierarchy_level as "hierarchyLevel"
                from public.memberships m
                where m.status = 'active' and {condition}
                order by m.hierarchy_level nulls last, m.full_name
                """,
                params,
            ).fetchall())

    def _ensure_tenant_write(self, access: AccessScope, tenant_id: UUID) -> None:
        if access.is_root:
            return
        if access.tenant_id != tenant_id or access.scope not in {"tenant", "global"}:
            raise ValueError("write access requires tenant admin scope")

    def _assert_membership_visible(self, conn: psycopg.Connection, access: AccessScope, membership_id: UUID) -> None:
        condition, params = self._membership_filter(access)
        row = conn.execute(
            f"select id from public.memberships m where m.id = %s and m.status = 'active' and {condition}",
            (membership_id, *params),
        ).fetchone()
        if not row:
            raise ValueError("membership outside visible hierarchy")

    def _fetch_manager_level(self, conn: psycopg.Connection, tenant_id: UUID, manager_id: UUID | None) -> int | None:
        if manager_id is None:
            return None
        row = conn.execute(
            "select hierarchy_level from public.memberships where tenant_id = %s and id = %s and status = 'active'",
            (tenant_id, manager_id),
        ).fetchone()
        if not row:
            raise ValueError("manager membership does not exist in tenant")
        return int(row["hierarchy_level"] or 0)

    def _ensure_hierarchy_write(
        self,
        conn: psycopg.Connection,
        access: AccessScope,
        tenant_id: UUID,
        target_membership_id: UUID | None,
        manager_id: UUID | None,
        hierarchy_level: int | None,
        deleting: bool = False,
    ) -> None:
        if not access.is_root and access.tenant_id != tenant_id:
            raise ValueError("tenant outside current context")
        if not access.is_root and access.scope == "self":
            raise ValueError("hierarchy write requires manager scope")

        if target_membership_id is not None:
            self._assert_membership_visible(conn, access, target_membership_id)

        if manager_id is not None:
            self._assert_membership_visible(conn, access, manager_id)
            manager_level = self._fetch_manager_level(conn, tenant_id, manager_id)
            if hierarchy_level is not None and manager_level is not None and hierarchy_level <= manager_level:
                raise ValueError("new member level must stay below the selected manager")
        elif not access.is_root and access.scope not in {"tenant", "global"}:
            raise ValueError("hierarchy manager is required")

        if deleting and access.membership_id and target_membership_id == access.membership_id:
            raise ValueError("membership cannot delete itself")

    def _role_scope(self, conn: psycopg.Connection, role_id: UUID | None) -> str:
        if role_id is None:
            return "self"
        row = conn.execute("select coalesce(scope, 'self') as scope from public.roles where id = %s", (role_id,)).fetchone()
        return str(row["scope"]) if row else "self"

    def _upsert_auth_user(
        self,
        conn: psycopg.Connection,
        *,
        user_id: UUID | None,
        email: str | None,
        full_name: str,
        username: str | None,
        password: str | None,
    ) -> UUID:
        login = (username or email or full_name).strip().lower()
        primary_email = (email or f"{login}@vulcan.local").strip().lower()
        existing = conn.execute(
            """
            select id
            from auth.users
            where (%s::uuid is not null and id = %s::uuid)
               or lower(email) = lower(%s)
               or lower(coalesce(raw_user_meta_data ->> 'login', '')) = lower(%s)
            order by created_at
            limit 1
            """,
            (user_id, user_id, primary_email, login),
        ).fetchone()
        resolved_user_id = UUID(str(existing["id"])) if existing else (user_id or uuid4())
        password_value = password or uuid4().hex
        encrypted_update = "excluded.encrypted_password" if password else "auth.users.encrypted_password"
        conn.execute(
            f"""
            insert into auth.users (
              id, aud, role, email, encrypted_password, email_confirmed_at,
              raw_app_meta_data, raw_user_meta_data, is_sso_user, is_anonymous,
              created_at, updated_at
            )
            values (%s, 'authenticated', 'authenticated', %s, crypt(%s, gen_salt('bf')), timezone('utc', now()),
                    %s, %s, false, false, timezone('utc', now()), timezone('utc', now()))
            on conflict (id) do update
            set email = excluded.email,
                encrypted_password = {encrypted_update},
                raw_user_meta_data = excluded.raw_user_meta_data,
                updated_at = timezone('utc', now())
            """,
            (
                resolved_user_id,
                primary_email,
                password_value,
                Jsonb({"provider": "vulcan-local"}),
                Jsonb({"name": full_name, "login": login, "product": "Vulcan", "createdBy": "hierarchy-crud"}),
            ),
        )
        conn.execute(
            """
            insert into public.user_profiles (user_id, primary_email, display_name, locale, timezone, metadata)
            values (%s, %s, %s, 'pt-BR', 'America/Sao_Paulo', %s)
            on conflict (user_id) do update
            set primary_email = excluded.primary_email,
                display_name = excluded.display_name,
                metadata = public.user_profiles.metadata || excluded.metadata,
                updated_at = timezone('utc', now())
            """,
            (resolved_user_id, primary_email, full_name, Jsonb({"login": login, "source": "hierarchy-crud"})),
        )
        return resolved_user_id

    def _assert_manager_is_safe(
        self,
        conn: psycopg.Connection,
        tenant_id: UUID,
        membership_id: UUID | None,
        manager_id: UUID | None,
    ) -> None:
        if manager_id is None:
            return
        manager = conn.execute(
            "select id from public.memberships where tenant_id = %s and id = %s",
            (tenant_id, manager_id),
        ).fetchone()
        if not manager:
            raise ValueError("manager membership does not exist in tenant")
        if membership_id is None:
            return
        if manager_id == membership_id:
            raise ValueError("membership cannot manage itself")
        cycle = conn.execute(
            """
            select exists(
              select 1 from public.membership_closure
              where tenant_id = %s
                and ancestor_membership_id = %s
                and descendant_membership_id = %s
                and depth > 0
            )
            """,
            (tenant_id, membership_id, manager_id),
        ).fetchone()
        if cycle and cycle["exists"]:
            raise ValueError("manager assignment would create a hierarchy cycle")

    def _fetch_membership(self, conn: psycopg.Connection, membership_id: UUID) -> dict | None:
        return conn.execute(
            """
            select m.id, m.tenant_id as "tenantId", m.user_id as "userId",
                   m.role_id as "roleId", m.department_id as "departmentId",
                   m.direct_manager_membership_id as "directManagerMembershipId",
                   m.status, m.full_name as "fullName", m.work_email as "workEmail",
                   m.phone, m.whatsapp, m.title, m.hierarchy_level as "hierarchyLevel"
            from public.memberships m
            where m.id = %s
            """,
            (membership_id,),
        ).fetchone()

    def create_membership(self, context: AuthContext, request: MembershipCreate) -> dict:
        if not self.enabled:
            raise ValueError("membership writes require Supabase/Postgres")
        with self._connect() as conn:
            access = self._access(conn, context)
            self._ensure_hierarchy_write(
                conn,
                access,
                request.tenant_id,
                None,
                request.direct_manager_membership_id,
                request.hierarchy_level,
            )
            self._assert_manager_is_safe(conn, request.tenant_id, None, request.direct_manager_membership_id)
            user_id = self._upsert_auth_user(
                conn,
                user_id=request.user_id,
                email=request.work_email,
                full_name=request.full_name,
                username=request.username,
                password=request.password,
            )
            row = conn.execute(
                """
                insert into public.memberships (
                  tenant_id, user_id, role_id, department_id, direct_manager_membership_id,
                  status, full_name, work_email, phone, whatsapp, title, hierarchy_level, joined_at, metadata
                )
                values (%s, %s, %s, %s, %s, 'active', %s, %s, %s, %s, %s, %s, timezone('utc', now()), %s)
                returning id
                """,
                (
                    request.tenant_id,
                    user_id,
                    request.role_id,
                    request.department_id,
                    request.direct_manager_membership_id,
                    request.full_name,
                    request.work_email,
                    request.phone,
                    request.whatsapp,
                    request.title,
                    request.hierarchy_level,
                    Jsonb({"source": "api", "username": request.username, "notificationEmail": request.work_email, "notificationWhatsapp": request.whatsapp}),
                ),
            ).fetchone()
            conn.execute("select public.vulcan_refresh_membership_closure(%s)", (request.tenant_id,))
            self.write_audit(conn, context, request.tenant_id, "membership.created", "membership", row["id"], {"full_name": request.full_name})
            conn.commit()
            membership = self._fetch_membership(conn, row["id"])
            if not membership:
                raise ValueError("membership was not persisted")
            return dict(membership)

    def update_membership(self, context: AuthContext, membership_id: UUID, request: MembershipUpdate) -> dict | None:
        if not self.enabled:
            return None
        with self._connect() as conn:
            access = self._access(conn, context)
            existing = conn.execute(
                "select tenant_id, user_id, direct_manager_membership_id, hierarchy_level, full_name, work_email from public.memberships where id = %s and status = 'active'",
                (membership_id,),
            ).fetchone()
            if not existing:
                return None
            tenant_id = existing["tenant_id"]
            manager_was_sent = "direct_manager_membership_id" in request.model_fields_set
            manager_id = request.direct_manager_membership_id if manager_was_sent else existing["direct_manager_membership_id"]
            hierarchy_level = request.hierarchy_level if request.hierarchy_level is not None else existing["hierarchy_level"]
            self._ensure_hierarchy_write(conn, access, tenant_id, membership_id, manager_id, hierarchy_level)
            self._assert_manager_is_safe(conn, tenant_id, membership_id, manager_id)
            if request.username or request.password or request.work_email or request.full_name:
                self._upsert_auth_user(
                    conn,
                    user_id=existing["user_id"],
                    email=request.work_email or existing["work_email"],
                    full_name=request.full_name or existing["full_name"],
                    username=request.username,
                    password=request.password,
                )
            row = conn.execute(
                """
                update public.memberships
                set role_id = coalesce(%s, role_id),
                    department_id = coalesce(%s, department_id),
                    direct_manager_membership_id = case when %s then %s else direct_manager_membership_id end,
                    status = coalesce(%s, status),
                    full_name = coalesce(%s, full_name),
                    work_email = coalesce(%s, work_email),
                    phone = coalesce(%s, phone),
                    whatsapp = coalesce(%s, whatsapp),
                    title = coalesce(%s, title),
                    hierarchy_level = coalesce(%s, hierarchy_level),
                    updated_at = timezone('utc', now())
                where id = %s
                returning id, tenant_id
                """,
                (
                    request.role_id,
                    request.department_id,
                    manager_was_sent,
                    manager_id,
                    request.status,
                    request.full_name,
                    request.work_email,
                    request.phone,
                    request.whatsapp,
                    request.title,
                    request.hierarchy_level,
                    membership_id,
                ),
            ).fetchone()
            if not row:
                return None
            conn.execute("select public.vulcan_refresh_membership_closure(%s)", (tenant_id,))
            audit_fields = request.model_dump(exclude_none=True, mode="json")
            if "password" in audit_fields:
                audit_fields["password"] = "***"
            self.write_audit(conn, context, tenant_id, "membership.updated", "membership", membership_id, {"fields": audit_fields})
            conn.commit()
            membership = self._fetch_membership(conn, membership_id)
            return dict(membership) if membership else None

    def delete_membership(self, context: AuthContext, membership_id: UUID) -> dict | None:
        if not self.enabled:
            return None
        with self._connect() as conn:
            access = self._access(conn, context)
            existing = conn.execute(
                """
                select id, tenant_id, user_id, direct_manager_membership_id, hierarchy_level, full_name
                from public.memberships
                where id = %s and status = 'active'
                """,
                (membership_id,),
            ).fetchone()
            if not existing:
                return None
            tenant_id = existing["tenant_id"]
            self._ensure_hierarchy_write(
                conn,
                access,
                tenant_id,
                membership_id,
                existing["direct_manager_membership_id"],
                existing["hierarchy_level"],
                deleting=True,
            )
            conn.execute(
                """
                update public.memberships
                set direct_manager_membership_id = %s,
                    updated_at = timezone('utc', now())
                where tenant_id = %s
                  and direct_manager_membership_id = %s
                  and status = 'active'
                """,
                (existing["direct_manager_membership_id"], tenant_id, membership_id),
            )
            conn.execute(
                """
                update public.devices
                set owner_membership_id = null,
                    metadata = metadata || %s,
                    updated_at = timezone('utc', now())
                where tenant_id = %s and owner_membership_id = %s
                """,
                (Jsonb({"ownerRemovedByHierarchyDelete": str(membership_id)}), tenant_id, membership_id),
            )
            row = conn.execute(
                """
                update public.memberships
                set status = 'revoked',
                    direct_manager_membership_id = null,
                    metadata = metadata || %s,
                    updated_at = timezone('utc', now())
                where id = %s
                returning id, tenant_id as "tenantId", user_id as "userId",
                          role_id as "roleId", department_id as "departmentId",
                          direct_manager_membership_id as "directManagerMembershipId",
                          status::text, full_name as "fullName", work_email as "workEmail",
                          phone, whatsapp, title, hierarchy_level as "hierarchyLevel"
                """,
                (Jsonb({"deletedAt": datetime.now(timezone.utc).isoformat(), "deletedBy": context.user_id}), membership_id),
            ).fetchone()
            conn.execute("select public.vulcan_refresh_membership_closure(%s)", (tenant_id,))
            self.write_audit(conn, context, tenant_id, "membership.deleted", "membership", membership_id, {"full_name": existing["full_name"]})
            conn.commit()
            return dict(row) if row else None

    def update_membership_manager(self, context: AuthContext, membership_id: UUID, manager_id: UUID | None) -> dict | None:
        return self.update_membership(
            context,
            membership_id,
            MembershipUpdate(directManagerMembershipId=manager_id),
        )

    def list_users(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return USERS
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._membership_filter(access)
            return list(conn.execute(
                f"""
                select m.user_id as id,
                       m.tenant_id as "tenantId",
                       m.full_name as name,
                       coalesce(m.work_email::text, au.email, '') as email,
                       m.phone,
                       m.whatsapp,
                       m.title,
                       m.hierarchy_level as "hierarchyLevel",
                       m.direct_manager_membership_id as "managerId",
                       coalesce(r.slug, r.name, 'member') as role,
                       m.status::text as status
                from public.memberships m
                left join auth.users au on au.id = m.user_id
                left join public.roles r on r.id = m.role_id
                where m.status = 'active' and {condition}
                order by m.hierarchy_level nulls last, m.full_name
                """,
                params,
            ).fetchall())

    def list_hierarchy(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return HIERARCHY
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._membership_filter(access)
            return list(conn.execute(
                f"""
                select m.id,
                       m.tenant_id as "tenantId",
                       m.user_id as "userId",
                       m.direct_manager_membership_id as "parentId",
                       m.full_name as name,
                       coalesce(m.title, 'Member') as title,
                       coalesce(d.name, 'Unassigned') as department,
                       coalesce(m.work_email::text, au.email, '') as email,
                       m.phone,
                       m.whatsapp,
                       coalesce(m.hierarchy_level, 0) as "hierarchyLevel",
                       (
                         select count(*)
                         from public.memberships child
                         where child.tenant_id = m.tenant_id
                           and child.direct_manager_membership_id = m.id
                           and child.status = 'active'
                       )::int as "directReports",
                       case
                         when coalesce(r.scope, 'self') = 'global' then 'global'
                         when coalesce(r.scope, 'self') = 'tenant' then 'tenant'
                         when coalesce(r.scope, 'self') = 'hierarchy' then 'subtree'
                         else 'self'
                       end as "visibleScope"
                from public.memberships m
                left join auth.users au on au.id = m.user_id
                left join public.departments d on d.id = m.department_id
                left join public.roles r on r.id = m.role_id
                where m.status = 'active' and {condition}
                order by coalesce(m.hierarchy_level, 0), m.full_name
                """,
                params,
            ).fetchall())

    def list_devices(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return DEVICES
        with self._connect() as conn:
            access = self._access(conn, context)
            self._repair_local_test_agent_scope(conn, access)
            condition, params = self._owner_filter(access, "d.owner_membership_id", "d.tenant_id")
            real_data_condition = self._real_agent_data_filter(access, "d")
            agent_only_condition = "and coalesce(d.metadata ->> 'source', '') = 'vulcan-agent' and left(d.hostname, 12) <> 'VULCAN-DEMO-'" if access.local_test else ""
            return list(conn.execute(
                f"""
                select d.id, d.tenant_id as "tenantId",
                       d.owner_membership_id as "ownerMembershipId",
                       coalesce(m.full_name, 'Unassigned') as owner,
                       d.hostname, d.os, d.status,
                       coalesce(d.last_seen_at, d.created_at)::text as "lastSeenAt",
                       d.metadata ->> 'collectionQuality' as "collectionQuality",
                       coalesce((d.metadata ->> 'queueDepth')::int, 0) as "queueDepth",
                       nullif(d.metadata ->> 'lastError', '') as "lastError",
                       d.metadata ->> 'localIp' as "localIp",
                       d.metadata ->> 'agentVersion' as "agentVersion"
                from public.devices d
                left join public.memberships m on m.id = d.owner_membership_id
                where {condition}
                  and {real_data_condition}
                  {agent_only_condition}
                order by d.last_seen_at desc nulls last, d.hostname
                limit 100
                """,
                params,
            ).fetchall())

    def update_device_owner(self, context: AuthContext, device_id: UUID, request: DeviceOwnerUpdate) -> dict | None:
        if not self.enabled:
            return None
        with self._connect() as conn:
            access = self._access(conn, context)
            if not access.is_root and request.tenant_id != access.tenant_id:
                raise ValueError("device tenant outside current context")

            condition, params = self._owner_filter(access, "d.owner_membership_id", "d.tenant_id")
            device = conn.execute(
                f"""
                select d.id, d.tenant_id, d.owner_membership_id
                from public.devices d
                where d.tenant_id = %s
                  and d.id = %s
                  and {condition}
                limit 1
                """,
                (request.tenant_id, device_id, *params),
            ).fetchone()
            if not device:
                return None

            if request.owner_membership_id:
                target_condition, target_params = self._membership_filter(access)
                target = conn.execute(
                    f"""
                    select m.id
                    from public.memberships m
                    where m.tenant_id = %s
                      and m.id = %s
                      and {target_condition}
                    limit 1
                    """,
                    (request.tenant_id, request.owner_membership_id, *target_params),
                ).fetchone()
                if not target:
                    raise ValueError("target membership outside visible hierarchy")

            conn.execute(
                """
                update public.devices
                set owner_membership_id = %s,
                    metadata = metadata || %s,
                    updated_at = timezone('utc', now())
                where tenant_id = %s and id = %s
                """,
                (
                    request.owner_membership_id,
                    Jsonb(
                        {
                            "ownerChangedAt": datetime.now(timezone.utc).isoformat(),
                            "ownerChangedBy": context.user_id,
                            "previousOwnerMembershipId": str(device["owner_membership_id"]) if device["owner_membership_id"] else None,
                        }
                    ),
                    request.tenant_id,
                    device_id,
                ),
            )
            self.write_audit(
                conn,
                context,
                request.tenant_id,
                "device.owner.updated",
                "device",
                device_id,
                {
                    "previous_owner_membership_id": str(device["owner_membership_id"]) if device["owner_membership_id"] else None,
                    "owner_membership_id": str(request.owner_membership_id) if request.owner_membership_id else None,
                },
            )
            conn.commit()

        refreshed = self.list_devices(context)
        for item in refreshed:
            if item["id"] == device_id:
                return item
        return None

    def list_activity_events(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return ACTIVITY_EVENTS
        with self._connect() as conn:
            access = self._access(conn, context)
            self._repair_local_test_agent_scope(conn, access)
            condition, params = self._owner_filter(access, "e.membership_id", "e.tenant_id")
            real_data_condition = self._real_agent_data_filter(access, "e")
            return list(conn.execute(
                f"""
                select e.id, e.tenant_id as "tenantId",
                       e.event_type as "eventType",
                       coalesce(e.app_name, 'Unknown') as "appName",
                       coalesce(d.name, 'Operations') as department,
                       e.occurred_at::text as "occurredAt",
                       greatest(1, ceil(coalesce(e.duration_seconds, 0)::numeric / 60))::int as "durationMinutes"
                from public.activity_events e
                left join public.memberships m on m.id = e.membership_id
                left join public.departments d on d.id = m.department_id
                where {condition}
                  and {real_data_condition}
                order by e.occurred_at desc
                limit 200
                """,
                params,
            ).fetchall())

    def list_dashboard_metrics(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return METRICS
        with self._connect() as conn:
            access = self._access(conn, context)
            self._repair_local_test_agent_scope(conn, access)
            membership_condition, membership_params = self._membership_filter(access, "m")
            event_condition, event_params = self._owner_filter(access, "membership_id", "tenant_id")
            insight_condition, insight_params = self._owner_filter(access, "membership_id", "tenant_id")
            event_real_filter = self._real_agent_data_filter(access, "activity_events")
            insight_real_filter = self._real_agent_data_filter(access, "ai_insights")
            active_users = conn.execute(
                f"select count(*) as count from public.memberships m where {membership_condition} and m.status = 'active'",
                membership_params,
            ).fetchone()["count"]
            events = conn.execute(
                f"select count(*) as count from public.activity_events where {event_condition} and {event_real_filter}",
                event_params,
            ).fetchone()["count"]
            insight_row = conn.execute(
                f"""
                select
                  count(*) filter (where impact in ('high', 'critical')) as bottlenecks,
                  count(*) as insights,
                  coalesce(sum(automation_savings_hours), 0) as automation
                from public.ai_insights
                where {insight_condition}
                  and {insight_real_filter}
                """,
                insight_params,
            ).fetchone()
            return [
                {"id": "active-users", "label": "Usuários ativos", "value": str(active_users), "trend": "escopo visível", "tone": "positive"},
                {"id": "events", "label": "Eventos processados", "value": f"{events}", "trend": "dados reais do agente", "tone": "neutral"},
                {"id": "bottlenecks", "label": "Gargalos detectados", "value": str(insight_row["bottlenecks"]), "trend": "alto impacto", "tone": "warning"},
                {"id": "insights", "label": "Insights de IA", "value": str(insight_row["insights"]), "trend": "IA híbrida", "tone": "positive"},
                {"id": "automation", "label": "Potencial de automação", "value": f"{float(insight_row['automation']):.0f}h", "trend": "estimativa mensal", "tone": "critical"},
            ]

    def agent_enroll(self, request: AgentEnrollRequest) -> AgentEnrollResponse:
        if not self.enabled:
            return AgentEnrollResponse(
                accepted=True,
                tenantId=request.tenant_id,
                deviceId=request.device_id or UUID("00000000-0000-0000-0000-000000500001"),
                heartbeatIntervalSeconds=60,
                syncIntervalSeconds=30,
            )
        with self._connect() as conn:
            membership_id = self._resolve_agent_membership(
                conn,
                request.tenant_id,
                request.membership_id,
                linked_user=request.linked_user,
                os_user=request.os_user,
            )
            row = conn.execute(
                """
                insert into public.devices (
                  id, tenant_id, owner_membership_id, hostname, os,
                  device_fingerprint, status, last_seen_at, metadata
                )
                values (
                  coalesce(%s, gen_random_uuid()), %s, %s, %s, %s,
                  %s, 'online', timezone('utc', now()), %s
                )
                on conflict (tenant_id, device_fingerprint) do update
                set owner_membership_id = coalesce(excluded.owner_membership_id, public.devices.owner_membership_id),
                    hostname = excluded.hostname,
                    os = excluded.os,
                    status = 'online',
                    last_seen_at = timezone('utc', now()),
                    metadata = public.devices.metadata || excluded.metadata,
                    updated_at = timezone('utc', now())
                returning id
                """,
                (
                    request.device_id,
                    request.tenant_id,
                    membership_id,
                    request.hostname,
                    request.os_version or "Windows",
                    request.machine_fingerprint,
                    Jsonb(
                        {
                            "source": "vulcan-agent",
                            "agentVersion": request.agent_version,
                            "linkedUser": request.linked_user,
                            "osUser": request.os_user,
                            "roleLevel": request.role_level,
                            "department": request.department,
                            "managerMembershipId": str(request.manager_membership_id) if request.manager_membership_id else None,
                            "note": request.note,
                        }
                    ),
                ),
            ).fetchone()
            self.write_agent_audit(
                conn,
                request.tenant_id,
                "agent.enrolled",
                "device",
                row["id"],
                {"hostname": request.hostname, "machine_fingerprint": request.machine_fingerprint, "membership_id": str(membership_id) if membership_id else None},
            )
            conn.commit()
            return AgentEnrollResponse(
                accepted=True,
                tenantId=request.tenant_id,
                deviceId=row["id"],
                heartbeatIntervalSeconds=60,
                syncIntervalSeconds=30,
            )

    def agent_heartbeat(self, request: AgentHeartbeatRequest) -> AgentHeartbeatResponse:
        if self.enabled:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    update public.devices
                    set status = %s,
                        hostname = %s,
                        last_seen_at = timezone('utc', now()),
                        metadata = metadata || %s,
                        updated_at = timezone('utc', now())
                    where tenant_id = %s
                      and (
                        (%s::uuid is not null and id = %s)
                        or device_fingerprint = %s
                      )
                    returning id, owner_membership_id, metadata
                    """,
                    (
                        request.status if request.status in {"online", "offline", "syncing"} else "online",
                        request.hostname,
                        Jsonb(
                            {
                                "agentVersion": request.agent_version,
                                "queueDepth": request.queue_depth,
                                "lastError": request.last_error,
                                **request.metadata,
                            }
                        ),
                        request.tenant_id,
                        request.device_id,
                        request.device_id,
                        request.machine_fingerprint,
                    ),
                ).fetchone()
                if row and row["owner_membership_id"] is None:
                    metadata = row["metadata"] or {}
                    membership_id = self._resolve_agent_membership(
                        conn,
                        request.tenant_id,
                        None,
                        linked_user=metadata.get("linkedUser"),
                        os_user=metadata.get("osUser"),
                    )
                    if membership_id:
                        conn.execute(
                            """
                            update public.devices
                            set owner_membership_id = %s,
                                metadata = metadata || %s,
                                updated_at = timezone('utc', now())
                            where tenant_id = %s and id = %s
                            """,
                            (
                                membership_id,
                                Jsonb({"autoLinkedMembershipId": str(membership_id)}),
                                request.tenant_id,
                                row["id"],
                            ),
                        )
                self.write_agent_audit(
                    conn,
                    request.tenant_id,
                    "agent.heartbeat",
                    "device",
                    request.device_id,
                    {"hostname": request.hostname, "queue_depth": request.queue_depth},
                )
                conn.commit()
        return AgentHeartbeatResponse(accepted=True, serverTime=datetime.now(timezone.utc))

    def agent_events(self, request: AgentEventsRequest) -> AgentEventsResponse:
        if not self.enabled:
            return AgentEventsResponse(accepted=True, received=len(request.events), stored=len(request.events))
        stored = 0
        with self._connect() as conn:
            device = conn.execute(
                """
                select id, owner_membership_id, metadata
                from public.devices
                where tenant_id = %s
                  and (
                    (%s::uuid is not null and id = %s)
                    or device_fingerprint = %s
                  )
                limit 1
                """,
                (request.tenant_id, request.device_id, request.device_id, request.machine_fingerprint),
            ).fetchone()
            device_id = device["id"] if device else request.device_id
            event_membership_id = request.membership_id or (device["owner_membership_id"] if device else None)
            if event_membership_id is None and device and (device["metadata"] or {}).get("linkedUser") == "teste":
                event_membership_id = self._resolve_agent_membership(conn, request.tenant_id, None, linked_user="teste")
                if event_membership_id and device_id:
                    conn.execute(
                        """
                        update public.devices
                        set owner_membership_id = %s,
                            metadata = metadata || %s,
                            updated_at = timezone('utc', now())
                        where tenant_id = %s and id = %s
                        """,
                        (
                            event_membership_id,
                            Jsonb({"autoLinkedMembershipId": str(event_membership_id)}),
                            request.tenant_id,
                            device_id,
                        ),
                    )
            inserted_events = 0
            duplicate_events = 0
            event_type_counts: dict[str, int] = defaultdict(int)
            for event in request.events:
                event_type = event.event_type or "app_focus_ended"
                row = conn.execute(
                    """
                    insert into public.activity_events (
                      tenant_id, membership_id, device_id, source_event_id, event_type, app_name,
                      window_title, category, duration_seconds, occurred_at, metadata
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (tenant_id, source_event_id) where source_event_id is not null do nothing
                    returning id
                    """,
                    (
                        request.tenant_id,
                        event_membership_id,
                        device_id,
                        event.event_id,
                        event_type,
                        event.app_name,
                        event.window_title,
                        event.category,
                        event.duration_seconds,
                        event.started_at,
                        Jsonb(
                            {
                                **event.metadata,
                                "source": "vulcan-agent",
                                "eventId": event.event_id,
                                "eventType": event_type,
                                "endedAt": event.ended_at.isoformat(),
                                "hostname": request.hostname,
                                "osUser": event.os_user,
                                "machineFingerprint": request.machine_fingerprint,
                            }
                        ),
                    ),
                ).fetchone()
                if not row:
                    duplicate_events += 1
                    continue
                for metric_key, metric_label, metric_value in self._metrics_for_agent_event(event_type, event):
                    conn.execute(
                        """
                        insert into public.operational_metrics (
                          tenant_id, membership_id, metric_key, metric_label,
                          value_numeric, period_start, period_end, metadata
                        )
                        values (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            request.tenant_id,
                            event_membership_id,
                            metric_key,
                            metric_label,
                            metric_value,
                            event.started_at,
                            event.ended_at,
                            Jsonb({"source": "vulcan-agent", "eventId": event.event_id, "category": event.category, "eventType": event_type}),
                        ),
                    )
                inserted_events += 1
                event_type_counts[event_type] += 1
                stored += 1
            if device_id:
                conn.execute(
                    """
                    update public.devices
                    set status = 'syncing',
                        last_seen_at = timezone('utc', now()),
                        metadata = metadata || %s,
                        updated_at = timezone('utc', now())
                    where id = %s and tenant_id = %s
                    """,
                    (
                        Jsonb(
                            {
                                "lastSyncAt": datetime.now(timezone.utc).isoformat(),
                                "lastSyncedEvents": stored,
                                "lastDuplicateEvents": duplicate_events,
                            }
                        ),
                        device_id,
                        request.tenant_id,
                    ),
                )
            self.write_agent_audit(
                conn,
                request.tenant_id,
                "agent.events.batch_stored",
                "device",
                device_id,
                {
                    "hostname": request.hostname,
                    "received": len(request.events),
                    "inserted": inserted_events,
                    "duplicates": duplicate_events,
                    "event_type_counts": dict(event_type_counts),
                },
            )
            conn.commit()
        return AgentEventsResponse(accepted=True, received=len(request.events), stored=len(request.events))

    def _metrics_for_agent_event(self, event_type: str, event: AgentEvent) -> list[tuple[str, str, float]]:
        duration = float(event.duration_seconds or 0)
        label = event.app_name or "Vulcan Agent"
        if event_type in {"app_focus_ended", "foreground_application_usage", "foreground_application_change"} and duration > 0:
            return [("app_usage_seconds", label, duration), ("active_seconds", "Tempo ativo", duration)]
        if event_type == "idle_ended" and duration > 0:
            return [("idle_seconds", "Tempo ocioso", duration)]
        if event_type == "context_switch":
            return [("context_switch_count", "Trocas de contexto", 1.0)]
        if event_type == "agent_error":
            return [("agent_error_count", "Erros do agente", 1.0)]
        if event_type == "collection_quality":
            score = {"high": 3.0, "medium": 2.0, "low": 1.0, "blocked_by_os": 0.0}.get(str(event.metadata.get("quality")), 0.0)
            return [("collection_quality_score", str(event.metadata.get("quality") or "desconhecida"), score)]
        if event_type == "agent_health":
            value = float(event.metadata.get("agentMemoryMb") or 0)
            return [("agent_memory_mb", "Memória do agente", value)]
        return []

    def agent_logs(self, request: AgentLogsRequest) -> AgentEventsResponse:
        if self.enabled:
            with self._connect() as conn:
                for entry in request.logs:
                    self.write_agent_audit(
                        conn,
                        request.tenant_id,
                        f"agent.log.{entry.level.lower()}",
                        "agent_log",
                        request.device_id,
                        {
                            "message": entry.message,
                            "createdAt": entry.created_at.isoformat(),
                            "machineFingerprint": request.machine_fingerprint,
                            **entry.metadata,
                        },
                    )
                conn.commit()
        return AgentEventsResponse(accepted=True, received=len(request.logs), stored=len(request.logs))

    def list_operational_metrics(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            self._repair_local_test_agent_scope(conn, access)
            condition, params = self._owner_filter(access, "om.membership_id", "om.tenant_id")
            real_data_condition = self._real_agent_data_filter(access, "om")
            return list(conn.execute(
                f"""
                select om.id, om.tenant_id as "tenantId", om.membership_id as "membershipId",
                       om.department_id as "departmentId", om.metric_key as "metricKey",
                       om.metric_label as "metricLabel", om.value_numeric as "valueNumeric",
                       om.value_text as "valueText", om.period_start as "periodStart", om.period_end as "periodEnd"
                from public.operational_metrics om
                where {condition}
                  and {real_data_condition}
                order by om.period_start desc
                limit 200
                """,
                params,
            ).fetchall())

    def operational_intelligence(self, context: AuthContext) -> dict:
        now = datetime.now(timezone.utc)
        if not self.enabled:
            return self._empty_operational_intelligence(now, "Últimas 24 horas")

        with self._connect() as conn:
            access = self._access(conn, context)
            self._repair_local_test_agent_scope(conn, access)
            condition, params = self._owner_filter(access, "e.membership_id", "e.tenant_id")
            real_data_condition = self._real_agent_data_filter(access, "e")
            rows = conn.execute(
                f"""
                select e.id::text,
                       e.event_type,
                       coalesce(e.app_name, 'Desconhecido') as app_name,
                       nullif(e.window_title, '') as window_title,
                       nullif(e.category, '') as category,
                       coalesce(e.duration_seconds, 0)::float as duration_seconds,
                       e.occurred_at,
                       coalesce(e.metadata, '{{}}'::jsonb) as metadata
                from public.activity_events e
                where {condition}
                  and {real_data_condition}
                  and e.occurred_at >= timezone('utc', now()) - interval '24 hours'
                order by e.occurred_at asc
                limit 5000
                """,
                params,
            ).fetchall()

            device_condition, device_params = self._owner_filter(access, "d.owner_membership_id", "d.tenant_id")
            device_real_condition = self._real_agent_data_filter(access, "d")
            devices = conn.execute(
                f"""
                select d.hostname,
                       d.status,
                       coalesce(d.last_seen_at, d.created_at)::text as last_seen_at,
                       d.metadata ->> 'collectionQuality' as collection_quality,
                       coalesce((d.metadata ->> 'queueDepth')::int, 0) as queue_depth,
                       nullif(d.metadata ->> 'lastError', '') as last_error
                from public.devices d
                where {device_condition}
                  and {device_real_condition}
                  and coalesce(d.metadata ->> 'source', '') = 'vulcan-agent'
                order by d.last_seen_at desc nulls last
                limit 50
                """,
                device_params,
            ).fetchall()

        return self._build_operational_intelligence(rows, devices, now)

    def _empty_operational_intelligence(self, now: datetime, period_label: str) -> dict:
        return {
            "generatedAt": now,
            "periodLabel": period_label,
            "totalEvents": 0,
            "totalActiveSeconds": 0.0,
            "totalIdleSeconds": 0.0,
            "unidentifiedSeconds": 0.0,
            "trackedSeconds": 0.0,
            "idleRate": 0.0,
            "focusScore": 0,
            "distractionScore": 0,
            "contextSwitches": 0,
            "contextSwitchesPerHour": 0.0,
            "longestFocusSeconds": 0.0,
            "fragmentedSeconds": 0.0,
            "currentActivity": "Aguardando eventos do agente",
            "aiSummary": "Ainda não há volume suficiente de eventos reais para gerar diagnóstico operacional.",
            "aiRecommendations": [
                "Reinicie ou instale o Vulcan Agent e aguarde alguns minutos de uso real.",
                "Confirme se o dispositivo está vinculado ao usuário correto na Hierarquia.",
            ],
            "topApps": [],
            "topWindows": [],
            "timeline": [],
            "qualitySignals": [],
        }

    def _build_operational_intelligence(self, rows: list[dict], devices: list[dict], now: datetime) -> dict:
        if not rows:
            summary = self._empty_operational_intelligence(now, "Últimas 24 horas")
            summary["qualitySignals"] = self._quality_signals(devices)
            return summary

        app_totals: dict[str, dict] = defaultdict(
            lambda: {
                "activeSeconds": 0.0,
                "idleSeconds": 0.0,
                "events": 0,
                "contextSwitches": 0,
                "category": "desconhecido",
                "lastSeenAt": None,
            }
        )
        window_totals: dict[tuple[str, str], dict] = defaultdict(lambda: {"activeSeconds": 0.0, "events": 0})
        timeline: dict[str, dict] = defaultdict(lambda: {"activeSeconds": 0.0, "idleSeconds": 0.0, "unidentifiedSeconds": 0.0, "contextSwitches": 0, "events": 0})

        total_active = 0.0
        total_idle = 0.0
        unidentified_seconds = 0.0
        context_switches = 0
        longest_focus = 0.0
        fragmented_seconds = 0.0
        potentially_dispersed_seconds = 0.0
        latest_activity = "Aguardando atividade"
        latest_activity_at: datetime | None = None
        saw_window_title = False

        for row in rows:
            event_type = row["event_type"]
            app_name = self._normalize_operational_label(row["app_name"])
            if self._is_technical_process(app_name) and event_type in {"app_focus_ended", "foreground_application_usage", "foreground_application_change", "context_switch"}:
                continue
            category = self._operational_category(app_name, row.get("category"))
            duration = max(0.0, float(row["duration_seconds"] or 0))
            occurred_at = row["occurred_at"]
            label = occurred_at.astimezone(timezone.utc).strftime("%Hh")
            timeline[label]["events"] += 1

            if self._is_limited_graphical_marker(app_name):
                if event_type in {"app_focus_ended", "foreground_application_usage", "foreground_application_change"} and duration > 0:
                    unidentified_seconds += duration
                    timeline[label]["unidentifiedSeconds"] += duration
                continue

            if event_type == "context_switch":
                context_switches += 1
                timeline[label]["contextSwitches"] += 1
                app_totals[app_name]["contextSwitches"] += 1
                app_totals[app_name]["category"] = category
                app_totals[app_name]["lastSeenAt"] = occurred_at
                continue

            if event_type == "idle_ended":
                total_idle += duration
                timeline[label]["idleSeconds"] += duration
                app_totals["Ociosidade"]["idleSeconds"] += duration
                app_totals["Ociosidade"]["events"] += 1
                app_totals["Ociosidade"]["category"] = "ocioso"
                app_totals["Ociosidade"]["lastSeenAt"] = occurred_at
                continue

            if event_type in {"app_focus_ended", "foreground_application_usage", "foreground_application_change"} and duration > 0:
                total_active += duration
                timeline[label]["activeSeconds"] += duration
                app_totals[app_name]["activeSeconds"] += duration
                app_totals[app_name]["events"] += 1
                app_totals[app_name]["category"] = category
                app_totals[app_name]["lastSeenAt"] = occurred_at
                longest_focus = max(longest_focus, duration)
                if duration < 120:
                    fragmented_seconds += duration
                if category in {"comunicação", "navegador", "entretenimento", "desconhecido"}:
                    potentially_dispersed_seconds += duration
                window_title = self._normalize_operational_label(row.get("window_title") or "")
                if window_title:
                    saw_window_title = True
                    window_totals[(app_name, window_title)]["activeSeconds"] += duration
                    window_totals[(app_name, window_title)]["events"] += 1
                if latest_activity_at is None or occurred_at > latest_activity_at:
                    latest_activity_at = occurred_at
                    latest_activity = f"{app_name} · {category}"

        tracked = total_active + total_idle + unidentified_seconds
        active_hours = max(total_active / 3600, 0.01)
        idle_rate = total_idle / tracked if tracked else 0.0
        switch_rate = context_switches / active_hours
        fragmented_rate = fragmented_seconds / total_active if total_active else 0.0
        dispersed_rate = potentially_dispersed_seconds / total_active if total_active else 0.0
        distraction_score = round(min(100.0, idle_rate * 35 + min(switch_rate, 60) * 0.9 + fragmented_rate * 30 + dispersed_rate * 20))
        focus_score = max(0, min(100, 100 - distraction_score))

        top_apps = []
        for app, totals in sorted(app_totals.items(), key=lambda item: item[1]["activeSeconds"] + item[1]["idleSeconds"], reverse=True)[:12]:
            seconds = float(totals["activeSeconds"] or totals["idleSeconds"] or 0)
            if seconds <= 0:
                continue
            denominator = total_idle if app == "Ociosidade" else total_active
            percent = (seconds / denominator * 100) if denominator else 0.0
            top_apps.append(
                {
                    "app": app,
                    "category": totals["category"],
                    "activeSeconds": float(totals["activeSeconds"]),
                    "idleSeconds": float(totals["idleSeconds"]),
                    "events": int(totals["events"]),
                    "contextSwitches": int(totals["contextSwitches"]),
                    "percent": round(percent, 1),
                    "lastSeenAt": totals["lastSeenAt"],
                    "focusLabel": self._focus_label(totals["category"], int(totals["contextSwitches"]), float(totals["activeSeconds"])),
                }
            )

        top_windows = []
        if saw_window_title:
            for (app, title), totals in sorted(window_totals.items(), key=lambda item: item[1]["activeSeconds"], reverse=True)[:10]:
                seconds = float(totals["activeSeconds"])
                top_windows.append(
                    {
                        "title": title,
                        "app": app,
                        "activeSeconds": seconds,
                        "events": int(totals["events"]),
                        "percent": round((seconds / total_active * 100) if total_active else 0.0, 1),
                        "collectionNote": "Título coletado por política habilitada e com redaction ativa.",
                    }
                )
        else:
            top_windows.append(
                {
                    "title": "Títulos de janela não coletados",
                    "app": "Privacidade",
                    "activeSeconds": 0.0,
                    "events": 0,
                    "percent": 0.0,
                    "collectionNote": "A política atual protege títulos de janela. Ative collectWindowTitle apenas com consentimento.",
                }
            )

        ordered_timeline = [
            {
                "label": label,
                "activeSeconds": values["activeSeconds"],
                "idleSeconds": values["idleSeconds"],
                "unidentifiedSeconds": values["unidentifiedSeconds"],
                "contextSwitches": int(values["contextSwitches"]),
                "events": int(values["events"]),
            }
            for label, values in sorted(timeline.items())
        ]

        quality_signals = self._quality_signals(devices, unidentified_seconds)
        recommendations = self._operational_recommendations(
            total_active=total_active,
            idle_rate=idle_rate,
            switch_rate=switch_rate,
            fragmented_rate=fragmented_rate,
            quality_signals=quality_signals,
        )
        ai_summary = self._operational_ai_summary(
            total_active=total_active,
            total_idle=total_idle,
            switch_rate=switch_rate,
            focus_score=focus_score,
            distraction_score=distraction_score,
            top_apps=top_apps,
        )

        return {
            "generatedAt": now,
            "periodLabel": "Últimas 24 horas",
            "totalEvents": len(rows),
            "totalActiveSeconds": round(total_active, 2),
            "totalIdleSeconds": round(total_idle, 2),
            "unidentifiedSeconds": round(unidentified_seconds, 2),
            "trackedSeconds": round(tracked, 2),
            "idleRate": round(idle_rate, 4),
            "focusScore": focus_score,
            "distractionScore": distraction_score,
            "contextSwitches": context_switches,
            "contextSwitchesPerHour": round(switch_rate, 2),
            "longestFocusSeconds": round(longest_focus, 2),
            "fragmentedSeconds": round(fragmented_seconds, 2),
            "currentActivity": latest_activity,
            "aiSummary": ai_summary,
            "aiRecommendations": recommendations,
            "topApps": top_apps,
            "topWindows": top_windows,
            "timeline": ordered_timeline,
            "qualitySignals": quality_signals,
        }

    def _quality_signals(self, devices: list[dict], unidentified_seconds: float = 0.0) -> list[dict]:
        signals = []
        if unidentified_seconds > 0:
            signals.append(
                {
                    "device": "todos",
                    "quality": "limited_graphical_environment",
                    "message": f"{round(unidentified_seconds / 60)} min não foram atribuídos a um app porque o ambiente gráfico bloqueou a janela ativa.",
                    "lastSeenAt": None,
                }
            )
        for device in devices:
            quality = device.get("collection_quality") or "desconhecida"
            queue_depth = int(device.get("queue_depth") or 0)
            last_error = device.get("last_error")
            if quality in {"blocked_by_os", "low", "desconhecida"}:
                message = "Coleta limitada pelo ambiente gráfico." if quality == "blocked_by_os" else "Qualidade de coleta precisa de atenção."
                signals.append({"device": device["hostname"], "quality": quality, "message": message, "lastSeenAt": device.get("last_seen_at")})
            if queue_depth > 0:
                signals.append({"device": device["hostname"], "quality": "fila", "message": f"{queue_depth} evento(s) aguardando sincronização.", "lastSeenAt": device.get("last_seen_at")})
            if last_error:
                signals.append({"device": device["hostname"], "quality": "erro", "message": last_error, "lastSeenAt": device.get("last_seen_at")})
        return signals

    def _normalize_operational_label(self, value: str) -> str:
        label = " ".join((value or "").strip().split())
        if not label:
            return ""
        lowered = label.lower()
        if "desktop" in lowered and any(token in lowered for token in ["gnome", "zorin", "kde", "xfce"]):
            return "Ambiente gráfico limitado"
        return label[:96]

    def _is_limited_graphical_marker(self, app_name: str) -> bool:
        lowered = app_name.strip().lower()
        return lowered in {"ambiente gráfico limitado", "ambiente grafico limitado"} or (
            "desktop" in lowered and any(token in lowered for token in ["gnome", "zorin", "kde", "xfce"])
        )

    def _is_technical_process(self, app_name: str) -> bool:
        lowered = app_name.strip().lower()
        technical = {
            "ps",
            "runc",
            "sleep",
            "sh",
            "bash",
            "zsh",
            "python",
            "python3",
            "node",
            "npm",
            "pnpm",
            "next-server",
            "git",
            "ssh",
            "rg",
            "grep",
            "sed",
            "cat",
            "curl",
            "wget",
            "ls",
            "find",
            "cpuusage.sh",
            "systemctl",
            "journalctl",
            "dbus-daemon",
            "systemd",
            "pipewire",
            "wireplumber",
            "vulcan_agent.py",
        }
        technical_prefixes = ("runc", "containerd", "docker-proxy", "vulcan", "systemd")
        return lowered in technical or any(lowered.startswith(prefix) for prefix in technical_prefixes)

    def _operational_category(self, app_name: str, explicit_category: str | None) -> str:
        if explicit_category:
            normalized = explicit_category.strip().lower()
            if normalized in {"operational", "uncategorized", "unknown", "desconhecido"}:
                explicit_category = None
            else:
                dictionary = {
                    "browser": "navegador",
                    "communication": "comunicação",
                    "development": "desenvolvimento",
                    "documents": "produtividade",
                    "productivity": "produtividade",
                    "system": "sistema",
                    "business": "gestão",
                    "idle": "ocioso",
                    "erp/crm": "gestão",
                }
                return dictionary.get(normalized, normalized)
        app = app_name.lower()
        if any(token in app for token in ["chrome", "chromium", "firefox", "edge", "brave", "safari"]):
            return "navegador"
        if any(token in app for token in ["whatsapp", "slack", "teams", "telegram", "discord", "zoom", "meet"]):
            return "comunicação"
        if any(token in app for token in ["code", "terminal", "bash", "zsh", "powershell", "pycharm", "intellij"]):
            return "desenvolvimento"
        if any(token in app for token in ["libreoffice", "excel", "word", "calc", "writer", "sheets", "docs"]):
            return "produtividade"
        if any(token in app for token in ["erp", "sap", "totvs", "jira", "notion", "crm"]):
            return "gestão"
        if any(token in app for token in ["gnome", "zorin", "desktop", "shell", "nautilus", "system", "ambiente gráfico"]):
            return "sistema"
        return "desconhecido"

    def _focus_label(self, category: str, switches: int, active_seconds: float) -> str:
        if category == "ocioso":
            return "sem atividade"
        if active_seconds and active_seconds < 120:
            return "fragmentado"
        if switches >= 10:
            return "muitas trocas"
        if category in {"desenvolvimento", "produtividade", "gestão"}:
            return "foco operacional"
        if category in {"comunicação", "navegador"}:
            return "atenção distribuída"
        return "neutro"

    def _operational_ai_summary(self, total_active: float, total_idle: float, switch_rate: float, focus_score: int, distraction_score: int, top_apps: list[dict]) -> str:
        productive_apps = [item for item in top_apps if item["category"] != "ocioso"]
        top = productive_apps[0]["app"] if productive_apps else "nenhum aplicativo dominante"
        active_minutes = round(total_active / 60)
        idle_minutes = round(total_idle / 60)
        return (
            f"Nas últimas 24 horas, o Vulcan identificou {active_minutes} min ativos e {idle_minutes} min ociosos. "
            f"O principal foco operacional foi {top}. A taxa de troca ficou em {switch_rate:.1f} por hora, "
            f"com score de foco {focus_score}/100 e dispersão operacional estimada em {distraction_score}/100."
        )

    def _operational_recommendations(self, total_active: float, idle_rate: float, switch_rate: float, fragmented_rate: float, quality_signals: list[dict]) -> list[str]:
        recommendations: list[str] = []
        if total_active == 0:
            recommendations.append("Ainda não há tempo ativo suficiente. Gere alguns minutos de uso real e sincronize o agente.")
        if idle_rate > 0.25:
            recommendations.append("Existe ociosidade relevante. Verifique pausas longas, bloqueio de sessão e períodos sem atividade operacional.")
        if switch_rate > 25:
            recommendations.append("Há muitas trocas de contexto por hora. Agrupe tarefas parecidas e reduza alternância entre sistemas.")
        if fragmented_rate > 0.35:
            recommendations.append("O tempo está fragmentado em sessões curtas. Procure blocos de foco contínuo acima de 15 minutos.")
        if quality_signals:
            recommendations.append("A qualidade de coleta precisa de atenção em pelo menos um dispositivo. Revise política, ambiente gráfico e dependências do agente.")
        if not recommendations:
            recommendations.append("O padrão atual parece estável. Continue coletando para gerar baseline por dia, semana e setor.")
        return recommendations[:5]

    def list_insights(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return INSIGHTS
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._owner_filter(access, "i.membership_id", "i.tenant_id")
            real_data_condition = self._real_agent_data_filter(access, "i")
            return list(conn.execute(
                f"""
                select i.id::text, i.title,
                       case when i.impact = 'critical' then 'high' else i.impact::text end as impact,
                       i.summary, coalesce(i.recommendation, '') as recommendation,
                       coalesce(i.automation_savings_hours, 0)::int as "automationSavingsHours"
                from public.ai_insights i
                where {condition}
                  and {real_data_condition}
                order by i.created_at desc
                limit 100
                """,
                params,
            ).fetchall())

    def list_notifications(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return NOTIFICATIONS
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._owner_filter(access, "n.recipient_membership_id", "n.tenant_id")
            real_data_condition = self._real_agent_data_filter(access, "n")
            return list(conn.execute(
                f"""
                select n.id::text,
                       n.tenant_id as "tenantId",
                       n.recipient_membership_id as "recipientMembershipId",
                       coalesce(m.full_name, n.metadata ->> 'recipient', 'Não definido') as recipient,
                       n.channel::text,
                       n.status::text,
                       n.notification_type as "notificationType",
                       n.title,
                       n.message,
                       coalesce((n.metadata ->> 'attempts')::int, 0) as attempts,
                       n.metadata ->> 'error' as error,
                       n.created_at::text as "createdAt"
                from public.notifications n
                left join public.memberships m on m.id = n.recipient_membership_id
                where {condition}
                  and {real_data_condition}
                order by n.created_at desc
                limit 100
                """,
                params,
            ).fetchall())

    def list_notification_preferences(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._owner_filter(access, "membership_id")
            return list(conn.execute(
                f"""
                select id, tenant_id as "tenantId", membership_id as "membershipId",
                       channel::text, notification_type as "notificationType", enabled
                from public.notification_preferences
                where {condition}
                order by notification_type, channel
                """,
                params,
            ).fetchall())

    def list_ai_provider_configs(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            condition = "true" if access.is_root else "(tenant_id is null or tenant_id = %s)"
            params = () if access.is_root else (access.tenant_id,)
            return list(conn.execute(
                f"""
                select id, tenant_id as "tenantId", provider, purpose, model,
                       base_url as "baseUrl", enabled
                from public.ai_provider_configs
                where {condition}
                order by purpose, provider
                """,
                params,
            ).fetchall())

    def list_audit_logs(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return []
        with self._connect() as conn:
            access = self._access(conn, context)
            condition = "true" if access.is_root else "tenant_id = %s"
            params = () if access.is_root else (access.tenant_id,)
            return list(conn.execute(
                f"""
                select id, tenant_id as "tenantId", actor_user_id as "actorUserId",
                       action, resource_type as "resourceType", resource_id as "resourceId",
                       created_at as "createdAt"
                from public.audit_logs
                where {condition}
                order by created_at desc
                limit 200
                """,
                params,
            ).fetchall())

    def create_activity_event(self, context: AuthContext, request: ActivityEventCreate) -> ActivityEventCreateResponse:
        if not self.enabled:
            return ActivityEventCreateResponse(id=UUID("20000000-0000-0000-0000-000000000001"), tenantId=request.tenant_id, metricUpdated=True)
        with self._connect() as conn:
            access = self._access(conn, context)
            if not access.is_root and request.tenant_id != access.tenant_id:
                raise ValueError("tenant mismatch")

            membership_id = request.membership_id
            if membership_id is None and request.user_id is not None:
                row = conn.execute(
                    "select id from public.memberships where tenant_id = %s and user_id = %s limit 1",
                    (request.tenant_id, request.user_id),
                ).fetchone()
                membership_id = row["id"] if row else None

            if access.scope not in {"tenant", "global"} and access.membership_id and membership_id != access.membership_id:
                visible = conn.execute(
                    """
                    select exists(
                      select 1 from public.membership_closure
                      where tenant_id = %s and ancestor_membership_id = %s and descendant_membership_id = %s
                    )
                    """,
                    (request.tenant_id, access.membership_id, membership_id),
                ).fetchone()
                if not visible or not visible["exists"]:
                    raise ValueError("membership outside visible hierarchy")

            event = conn.execute(
                """
                insert into public.activity_events (
                  tenant_id, membership_id, device_id, event_type, app_name, window_title,
                  category, duration_seconds, occurred_at, metadata
                )
                values (%s, %s, %s, 'foreground_application_change', %s, %s, %s, %s, %s, %s)
                returning id
                """,
                (
                    request.tenant_id,
                    membership_id,
                    request.device_id,
                    request.app_name,
                    request.window_title,
                    request.category,
                    request.duration_seconds,
                    request.started_at,
                    Jsonb(request.metadata),
                ),
            ).fetchone()

            conn.execute(
                """
                insert into public.operational_metrics (
                  tenant_id, membership_id, metric_key, metric_label,
                  value_numeric, period_start, period_end, metadata
                )
                values (%s, %s, 'app_usage_seconds', %s, %s, %s, %s, %s)
                """,
                (
                    request.tenant_id,
                    membership_id,
                    request.app_name,
                    request.duration_seconds,
                    request.started_at,
                    request.ended_at,
                    Jsonb({"app_name": request.app_name, "category": request.category}),
                ),
            )

            self.write_audit(
                conn,
                context,
                request.tenant_id,
                "activity_event.created",
                "activity_event",
                event["id"],
                {"app_name": request.app_name, "duration_seconds": request.duration_seconds},
            )
            conn.commit()
            return ActivityEventCreateResponse(id=event["id"], tenantId=request.tenant_id, metricUpdated=True)

    def create_notification_record(self, context: AuthContext, request: NotificationSendRequest, status: str, provider_result: str) -> NotificationSendResponse:
        if not self.enabled:
            return NotificationSendResponse(id=None, channel=request.channel, status=status, providerResult=provider_result)
        with self._connect() as conn:
            access = self._access(conn, context)
            if not access.is_root and request.tenant_id != access.tenant_id:
                raise ValueError("tenant mismatch")
            db_status = status if status in {"queued", "sent", "failed", "ready", "mocked", "missing_credentials", "disabled"} else "failed"
            row = conn.execute(
                """
                insert into public.notifications (
                  tenant_id, recipient_membership_id, channel, notification_type,
                  status, title, message, provider, provider_message_id, metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, 'vulcan-notification-service', %s, %s)
                returning id
                """,
                (
                    request.tenant_id,
                    request.recipient_membership_id,
                    request.channel,
                    request.notification_type,
                    db_status,
                    request.title,
                    request.message,
                    provider_result,
                    Jsonb(
                        {
                            "attempts": 1,
                            "deliveryStatus": status,
                            "error": provider_result if db_status == "failed" else None,
                            "recipient": str(request.recipient_membership_id) if request.recipient_membership_id else None,
                        }
                    ),
                ),
            ).fetchone()
            self.write_audit(conn, context, request.tenant_id, "notification.created", "notification", row["id"], {"channel": request.channel})
            conn.commit()
            return NotificationSendResponse(id=row["id"], channel=request.channel, status=db_status, providerResult=provider_result)

    def update_notification_preference(self, context: AuthContext, preference_id: UUID, enabled: bool) -> dict | None:
        if not self.enabled:
            return None
        with self._connect() as conn:
            access = self._access(conn, context)
            condition, params = self._owner_filter(access, "membership_id")
            row = conn.execute(
                f"""
                update public.notification_preferences
                set enabled = %s, updated_at = timezone('utc', now())
                where id = %s and {condition}
                returning id, tenant_id as "tenantId", membership_id as "membershipId",
                          channel::text, notification_type as "notificationType", enabled
                """,
                (enabled, preference_id, *params),
            ).fetchone()
            if row:
                self.write_audit(conn, context, row["tenantId"], "notification_preference.updated", "notification_preference", row["id"], {"enabled": enabled})
            conn.commit()
            return dict(row) if row else None

    def write_audit(
        self,
        conn: psycopg.Connection,
        context: AuthContext,
        tenant_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: UUID | None,
        metadata: dict,
    ) -> None:
        actor_user_id: str | None = None
        if context.provider != "local":
            try:
                UUID(context.user_id)
                actor_user_id = context.user_id
            except ValueError:
                actor_user_id = None
        conn.execute(
            """
            insert into public.audit_logs (
              tenant_id, actor_user_id, action,
              entity_table, entity_id, change_summary,
              resource_type, resource_id, metadata, created_at
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                tenant_id,
                actor_user_id,
                action,
                resource_type,
                resource_id,
                Jsonb(metadata),
                resource_type,
                resource_id,
                Jsonb(metadata),
                datetime.now(timezone.utc),
            ),
        )

    def write_agent_audit(
        self,
        conn: psycopg.Connection,
        tenant_id: UUID,
        action: str,
        resource_type: str,
        resource_id: UUID | None,
        metadata: dict,
    ) -> None:
        conn.execute(
            """
            insert into public.audit_logs (
              tenant_id, actor_user_id, action,
              entity_table, entity_id, change_summary,
              resource_type, resource_id, metadata, created_at
            )
            values (%s, null, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                tenant_id,
                action,
                resource_type,
                resource_id,
                Jsonb(metadata),
                resource_type,
                resource_id,
                Jsonb(metadata),
                datetime.now(timezone.utc),
            ),
        )


def get_repository() -> VulcanRepository:
    return VulcanRepository()
