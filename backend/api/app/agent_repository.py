from __future__ import annotations

import base64
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from psycopg.types.json import Jsonb

from app.agent_schemas import (
    AgentCommandCreate,
    AgentCommandResult,
    AgentEnrollV2Request,
    AgentEventsV2Request,
    AgentHeartbeatV2Request,
    AgentPolicyCreate,
    CanonicalAgentEvent,
    EnrollmentTokenCreate,
)
from app.agent_security import (
    PolicySigner,
    decode_public_key,
    deep_merge,
    default_policy,
    default_policy_signing_key_path,
    public_key_fingerprint,
    sha256_hex,
    validate_policy_document,
    verify_request_signature,
)
from app.config import Settings, get_settings
from app.repository import VulcanRepository
from app.security import AuthContext


def _event_data_origin(event: CanonicalAgentEvent) -> str:
    return "simulated" if event.extensions.get("dataOrigin") == "simulated" else "real"


class AgentAuthorizationError(ValueError):
    pass


class AgentConflictError(ValueError):
    pass


@dataclass(frozen=True)
class AgentPrincipal:
    agent_id: UUID
    tenant_id: UUID
    device_id: UUID
    profile: str
    hostname: str
    public_key: str
    owner_membership_id: UUID | None
    site_id: UUID | None
    department_id: UUID | None


class AgentV2Repository:
    def __init__(
        self,
        settings: Settings | None = None,
        base_repository: VulcanRepository | None = None,
        signer: PolicySigner | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.base = base_repository or VulcanRepository(self.settings)
        self.signer = signer or PolicySigner(default_policy_signing_key_path())

    @property
    def enabled(self) -> bool:
        return self.base.enabled

    @staticmethod
    def _assert_admin(access, context: AuthContext) -> None:
        role = access.role_slug or context.role
        if access.is_root or role in {
            "admin",
            "owner",
            "root",
            "tenant_owner",
            "tenant_admin",
            "infrastructure_admin",
            "security_admin",
        }:
            return
        raise AgentAuthorizationError("agent administration permission required")

    @staticmethod
    def _assert_read(access, context: AuthContext) -> None:
        role = access.role_slug or context.role
        if access.is_root or role in {
            "admin",
            "owner",
            "root",
            "tenant_owner",
            "tenant_admin",
            "infrastructure_admin",
            "security_admin",
            "manager",
            "supervisor",
            "auditor",
            "analyst",
            "read_only",
        }:
            return
        raise AgentAuthorizationError("agent read permission required")

    @staticmethod
    def _assert_tenant(context: AuthContext, tenant_id: UUID) -> None:
        if context.tenant_id != tenant_id:
            raise AgentAuthorizationError("tenant outside active context")

    @staticmethod
    def _actor_uuid(context: AuthContext) -> UUID | None:
        if context.provider == "local":
            return None
        try:
            return UUID(context.user_id)
        except ValueError:
            return None

    def create_enrollment_token(self, context: AuthContext, request: EnrollmentTokenCreate) -> dict:
        if not self.enabled:
            raise RuntimeError("database is required to create enrollment tokens")
        self._assert_tenant(context, request.tenant_id)
        raw_token = f"vulcan_enroll_{secrets.token_urlsafe(32)}"
        token_hash = sha256_hex(raw_token.encode("utf-8"))
        prefix = raw_token[:18]
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=request.expires_in_minutes)
        with self.base._connect() as conn:
            access = self.base._access(conn, context)
            self._assert_admin(access, context)
            row = conn.execute(
                """
                insert into public.agent_enrollment_tokens (
                  tenant_id, token_prefix, token_hash, profile, site_id, department_id,
                  tags, approval_mode, expires_at, max_uses, created_by
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning id, tenant_id, token_prefix, profile, expires_at, max_uses
                """,
                (
                    request.tenant_id,
                    prefix,
                    token_hash,
                    request.profile,
                    request.site_id,
                    request.department_id,
                    request.tags,
                    request.approval_mode,
                    expires_at,
                    request.max_uses,
                    self._actor_uuid(context),
                ),
            ).fetchone()
            self.base.write_audit(
                conn,
                context,
                request.tenant_id,
                "agent.enrollment_token.created",
                "agent_enrollment_token",
                row["id"],
                {
                    "tokenPrefix": prefix,
                    "profile": request.profile,
                    "expiresAt": expires_at.isoformat(),
                    "maxUses": request.max_uses,
                    "approvalMode": request.approval_mode,
                },
            )
            conn.commit()
            return {
                **row,
                "token": raw_token,
                "warning": "O token bruto é exibido uma única vez e não pode ser recuperado.",
            }

    def list_enrollment_tokens(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return []
        with self.base._connect() as conn:
            access = self.base._access(conn, context)
            self._assert_admin(access, context)
            return list(
                conn.execute(
                    """
                    select id, tenant_id, token_prefix, profile, site_id, department_id,
                           tags, approval_mode, expires_at, max_uses, use_count,
                           last_used_at, revoked_at, created_at
                    from public.agent_enrollment_tokens
                    where tenant_id = %s
                    order by created_at desc
                    limit 100
                    """,
                    (context.tenant_id,),
                ).fetchall()
            )

    def list_agents(self, context: AuthContext, profile: str | None = None, status: str | None = None) -> list[dict]:
        if not self.enabled:
            return []
        with self.base._connect() as conn:
            access = self.base._access(conn, context)
            self._assert_read(access, context)
            conditions = ["identity.tenant_id = %s"]
            params: list[object] = [context.tenant_id]
            if profile:
                conditions.append("identity.profile = %s")
                params.append(profile)
            if status:
                conditions.append("identity.status = %s")
                params.append(status)
            return list(
                conn.execute(
                    f"""
                    select identity.id,
                           identity.tenant_id,
                           identity.device_id,
                           identity.hostname,
                           identity.profile,
                           identity.operating_system,
                           identity.architecture,
                           identity.agent_version,
                           identity.status,
                           identity.policy_revision,
                           identity.policy_status,
                           identity.queue_depth,
                           identity.last_seen_at,
                           identity.last_ip::text as last_ip,
                           nullif(device.metadata ->> 'siteId', '')::uuid as site_id,
                           site.name as site_name,
                           membership.full_name as owner,
                           department.name as department,
                           coalesce(identity.metadata -> 'modules', '{{}}'::jsonb) as modules,
                           nullif(identity.metadata ->> 'lastError', '') as last_error,
                           identity.created_at
                    from public.agent_identities identity
                    join public.devices device
                      on device.tenant_id = identity.tenant_id and device.id = identity.device_id
                    left join public.memberships membership on membership.id = device.owner_membership_id
                    left join public.departments department on department.id = membership.department_id
                    left join public.sites site
                      on site.tenant_id = identity.tenant_id
                     and site.id = nullif(device.metadata ->> 'siteId', '')::uuid
                    where {' and '.join(conditions)}
                    order by identity.last_seen_at desc nulls last, identity.hostname
                    limit 500
                    """,
                    params,
                ).fetchall()
            )

    def create_policy(self, context: AuthContext, request: AgentPolicyCreate) -> dict:
        if not self.enabled:
            raise RuntimeError("database is required to create agent policies")
        self._assert_tenant(context, request.tenant_id)
        validate_policy_document(request.document, request.profile)
        expected_scope_value = {
            "tenant": None,
            "site": request.site_id,
            "department": request.department_id,
            "device": request.device_id,
        }[request.scope_type]
        if request.scope_type != "tenant" and expected_scope_value is None:
            raise ValueError(f"{request.scope_type} scope requires its identifier")
        if request.scope_type == "tenant" and any((request.site_id, request.department_id, request.device_id)):
            raise ValueError("tenant scope cannot include site, department or device")
        with self.base._connect() as conn:
            access = self.base._access(conn, context)
            self._assert_admin(access, context)
            revision = conn.execute(
                """
                select coalesce(max(revision), 0) + 1 as revision
                from public.agent_policies
                where tenant_id = %s
                  and profile = %s
                  and scope_type = %s
                  and site_id is not distinct from %s
                  and department_id is not distinct from %s
                  and device_id is not distinct from %s
                """,
                (
                    request.tenant_id,
                    request.profile,
                    request.scope_type,
                    request.site_id,
                    request.department_id,
                    request.device_id,
                ),
            ).fetchone()["revision"]
            row = conn.execute(
                """
                insert into public.agent_policies (
                  tenant_id, name, profile, scope_type, site_id, department_id,
                  device_id, revision, schema_version, document, enabled,
                  created_by, updated_by
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, 'v1', %s, %s, %s, %s)
                returning *
                """,
                (
                    request.tenant_id,
                    request.name,
                    request.profile,
                    request.scope_type,
                    request.site_id,
                    request.department_id,
                    request.device_id,
                    revision,
                    Jsonb(request.document),
                    request.enabled,
                    self._actor_uuid(context),
                    self._actor_uuid(context),
                ),
            ).fetchone()
            self.base.write_audit(
                conn,
                context,
                request.tenant_id,
                "agent.policy.created",
                "agent_policy",
                row["id"],
                {
                    "name": request.name,
                    "profile": request.profile,
                    "scopeType": request.scope_type,
                    "revision": revision,
                },
            )
            conn.commit()
            return dict(row)

    def list_policies(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            return []
        with self.base._connect() as conn:
            access = self.base._access(conn, context)
            self._assert_read(access, context)
            return list(
                conn.execute(
                    """
                    select id, tenant_id, name, profile, scope_type, site_id,
                           department_id, device_id, revision, schema_version,
                           document, enabled, created_at, updated_at
                    from public.agent_policies
                    where tenant_id = %s
                    order by updated_at desc, revision desc
                    limit 500
                    """,
                    (context.tenant_id,),
                ).fetchall()
            )

    def _effective_policy(self, conn, principal: AgentPrincipal) -> tuple[int, dict]:
        policy = default_policy(principal.profile)
        rows = conn.execute(
            """
            select document, updated_at
            from public.agent_policies
            where tenant_id = %s
              and profile = %s
              and enabled
              and (
                scope_type = 'tenant'
                or (scope_type = 'site' and site_id = %s)
                or (scope_type = 'department' and department_id = %s)
                or (scope_type = 'device' and device_id = %s)
              )
            order by
              case scope_type
                when 'tenant' then 1
                when 'site' then 2
                when 'department' then 3
                when 'device' then 4
              end,
              revision
            """,
            (
                principal.tenant_id,
                principal.profile,
                principal.site_id,
                principal.department_id,
                principal.device_id,
            ),
        ).fetchall()
        revision = 1
        for row in rows:
            policy = deep_merge(policy, row["document"])
            revision = max(revision, int(row["updated_at"].timestamp() * 1000))
        return revision, validate_policy_document(policy, principal.profile)

    def _signed_policy(self, conn, principal: AgentPrincipal) -> dict:
        revision, policy = self._effective_policy(conn, principal)
        return self.signer.sign_policy(
            tenant_id=str(principal.tenant_id),
            agent_id=str(principal.agent_id),
            revision=revision,
            policy=policy,
        )

    def policy(self, principal: AgentPrincipal) -> dict:
        with self.base._connect() as conn:
            return self._signed_policy(conn, principal)

    @staticmethod
    def _principal_from_row(row: dict) -> AgentPrincipal:
        metadata = row.get("device_metadata") or {}
        site_id = metadata.get("siteId")
        return AgentPrincipal(
            agent_id=row["id"],
            tenant_id=row["tenant_id"],
            device_id=row["device_id"],
            profile=row["profile"],
            hostname=row["hostname"],
            public_key=row["public_key"],
            owner_membership_id=row.get("owner_membership_id"),
            site_id=UUID(site_id) if site_id else None,
            department_id=row.get("department_id"),
        )

    def enroll(self, request: AgentEnrollV2Request) -> dict:
        if not self.enabled:
            raise RuntimeError("database is required for agent enrollment")
        raw_token = request.enrollment_token.get_secret_value()
        token_hash = sha256_hex(raw_token.encode("utf-8"))
        try:
            raw_public_key = base64.b64decode(request.public_key, validate=True)
            decode_public_key(request.public_key)
        except (ValueError, TypeError) as exc:
            raise AgentAuthorizationError("invalid agent public key") from exc
        if public_key_fingerprint(raw_public_key) != request.public_key_fingerprint:
            raise AgentAuthorizationError("public key fingerprint mismatch")

        with self.base._connect() as conn:
            token = conn.execute(
                """
                select *
                from public.agent_enrollment_tokens
                where token_hash = %s
                for update
                """,
                (token_hash,),
            ).fetchone()
            if not token:
                raise AgentAuthorizationError("invalid enrollment token")

            retry = conn.execute(
                """
                select identity.*, device.owner_membership_id,
                       membership.department_id,
                       device.metadata as device_metadata
                from public.agent_identities identity
                join public.devices device
                  on device.tenant_id = identity.tenant_id and device.id = identity.device_id
                left join public.memberships membership on membership.id = device.owner_membership_id
                where identity.enrollment_token_id = %s
                  and identity.public_key_fingerprint = %s
                limit 1
                """,
                (token["id"], request.public_key_fingerprint),
            ).fetchone()
            if retry:
                principal = self._principal_from_row(retry)
                return self._enrollment_response(conn, principal, retry["status"])

            now = datetime.now(timezone.utc)
            if token["revoked_at"] or token["expires_at"] <= now or token["use_count"] >= token["max_uses"]:
                raise AgentAuthorizationError("expired, revoked or exhausted enrollment token")
            if token["profile"] != request.profile:
                raise AgentAuthorizationError("agent profile does not match enrollment token")

            existing_key = conn.execute(
                "select id from public.agent_identities where public_key_fingerprint = %s",
                (request.public_key_fingerprint,),
            ).fetchone()
            if existing_key:
                raise AgentConflictError("public key is already enrolled; generate a new identity for re-enrollment")

            device = conn.execute(
                """
                insert into public.devices (
                  tenant_id, hostname, os, device_fingerprint, status, last_seen_at, metadata
                )
                values (%s, %s, %s, %s, %s, timezone('utc', now()), %s)
                on conflict (tenant_id, device_fingerprint) do update
                set hostname = excluded.hostname,
                    os = excluded.os,
                    status = excluded.status,
                    last_seen_at = timezone('utc', now()),
                    metadata = public.devices.metadata || excluded.metadata,
                    updated_at = timezone('utc', now())
                returning id, owner_membership_id, metadata
                """,
                (
                    token["tenant_id"],
                    request.hostname,
                    request.operating_system,
                    request.device_fingerprint,
                    "online" if token["approval_mode"] == "automatic" else "pending",
                    Jsonb(
                        {
                            "source": "vulcan-agent-v2",
                            "agentVersion": request.agent_version,
                            "profile": request.profile,
                            "siteId": str(token["site_id"]) if token["site_id"] else None,
                            "tags": token["tags"],
                            "approvalStatus": token["approval_mode"],
                            **request.metadata,
                        }
                    ),
                ),
            ).fetchone()

            conn.execute(
                """
                update public.agent_identities
                set status = 'revoked',
                    revoked_at = timezone('utc', now()),
                    revocation_reason = 'secure re-enrollment',
                    updated_at = timezone('utc', now())
                where tenant_id = %s
                  and device_id = %s
                  and status not in ('revoked', 'retired')
                """,
                (token["tenant_id"], device["id"]),
            )
            identity = conn.execute(
                """
                insert into public.agent_identities (
                  tenant_id, device_id, enrollment_token_id, profile, public_key,
                  public_key_fingerprint, device_fingerprint, hostname,
                  operating_system, architecture, agent_version, status, metadata
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning *
                """,
                (
                    token["tenant_id"],
                    device["id"],
                    token["id"],
                    request.profile,
                    request.public_key,
                    request.public_key_fingerprint,
                    request.device_fingerprint,
                    request.hostname,
                    request.operating_system,
                    request.architecture,
                    request.agent_version,
                    "approved" if token["approval_mode"] == "automatic" else "pending",
                    Jsonb({"enrollmentProtocol": "v2", "tags": token["tags"]}),
                ),
            ).fetchone()
            conn.execute(
                """
                update public.agent_enrollment_tokens
                set use_count = use_count + 1,
                    last_used_at = timezone('utc', now()),
                    updated_at = timezone('utc', now())
                where id = %s
                """,
                (token["id"],),
            )
            self.base.write_agent_audit(
                conn,
                token["tenant_id"],
                "agent.v2.enrolled",
                "agent_identity",
                identity["id"],
                {
                    "deviceId": str(device["id"]),
                    "hostname": request.hostname,
                    "profile": request.profile,
                    "tokenPrefix": token["token_prefix"],
                    "approvalMode": token["approval_mode"],
                },
            )
            principal = AgentPrincipal(
                agent_id=identity["id"],
                tenant_id=token["tenant_id"],
                device_id=device["id"],
                profile=request.profile,
                hostname=request.hostname,
                public_key=request.public_key,
                owner_membership_id=device["owner_membership_id"],
                site_id=token["site_id"],
                department_id=token["department_id"],
            )
            response = self._enrollment_response(conn, principal, identity["status"])
            conn.commit()
            return response

    def _enrollment_response(self, conn, principal: AgentPrincipal, status: str) -> dict:
        return {
            "accepted": True,
            "tenant_id": principal.tenant_id,
            "device_id": principal.device_id,
            "agent_id": principal.agent_id,
            "status": status,
            "server_time": datetime.now(timezone.utc),
            "policy_signing_public_key": self.signer.public_key_base64(),
            "policy": self._signed_policy(conn, principal),
        }

    def authenticate(
        self,
        *,
        agent_id: UUID,
        timestamp: str,
        nonce: str,
        body_hash: str,
        signature: str,
        method: str,
        path: str,
        body: bytes,
    ) -> AgentPrincipal:
        if not self.enabled:
            raise AgentAuthorizationError("agent v2 authentication requires database")
        if sha256_hex(body) != body_hash:
            raise AgentAuthorizationError("request body hash mismatch")
        if len(nonce) < 16 or len(nonce) > 128:
            raise AgentAuthorizationError("invalid request nonce")
        try:
            request_time = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
        except (ValueError, OverflowError) as exc:
            raise AgentAuthorizationError("invalid request timestamp") from exc
        now = datetime.now(timezone.utc)
        if abs((now - request_time).total_seconds()) > 300:
            raise AgentAuthorizationError("request timestamp outside allowed clock window")

        with self.base._connect() as conn:
            row = conn.execute(
                """
                select identity.*, device.owner_membership_id,
                       membership.department_id,
                       device.metadata as device_metadata
                from public.agent_identities identity
                join public.devices device
                  on device.tenant_id = identity.tenant_id and device.id = identity.device_id
                left join public.memberships membership on membership.id = device.owner_membership_id
                where identity.id = %s
                  and identity.status not in ('revoked', 'retired')
                  and identity.revoked_at is null
                limit 1
                """,
                (agent_id,),
            ).fetchone()
            if not row:
                raise AgentAuthorizationError("unknown or revoked agent identity")
            try:
                verify_request_signature(
                    public_key=row["public_key"],
                    signature=signature,
                    method=method,
                    path=path,
                    timestamp=timestamp,
                    nonce=nonce,
                    body_hash=body_hash,
                )
            except (InvalidSignature, ValueError, TypeError) as exc:
                raise AgentAuthorizationError("invalid agent request signature") from exc
            try:
                conn.execute(
                    """
                    insert into public.agent_request_nonces (
                      tenant_id, agent_identity_id, nonce, request_timestamp, expires_at
                    )
                    values (%s, %s, %s, %s, %s)
                    """,
                    (
                        row["tenant_id"],
                        row["id"],
                        nonce,
                        request_time,
                        now + timedelta(minutes=10),
                    ),
                )
                conn.execute(
                    "delete from public.agent_request_nonces where expires_at < timezone('utc', now())"
                )
                conn.commit()
            except Exception as exc:
                conn.rollback()
                if getattr(exc, "sqlstate", None) == "23505":
                    raise AgentAuthorizationError("replayed request nonce") from exc
                raise
            return self._principal_from_row(row)

    def heartbeat(
        self,
        principal: AgentPrincipal,
        request: AgentHeartbeatV2Request,
        remote_ip: str | None,
    ) -> dict:
        with self.base._connect() as conn:
            signed_policy = self._signed_policy(conn, principal)
            effective_revision = signed_policy["revision"]
            status = "online" if request.status in {"online", "syncing"} else request.status
            conn.execute(
                """
                update public.agent_identities
                set status = %s,
                    agent_version = %s,
                    queue_depth = %s,
                    policy_revision = %s,
                    policy_status = %s,
                    last_seen_at = timezone('utc', now()),
                    last_ip = %s,
                    metadata = metadata || %s,
                    updated_at = timezone('utc', now())
                where tenant_id = %s and id = %s
                """,
                (
                    status,
                    request.agent_version,
                    request.queue_depth,
                    request.policy_revision,
                    request.policy_status,
                    remote_ip,
                    Jsonb(
                        {
                            "modules": request.modules,
                            "performance": request.performance,
                            "lastError": request.last_error,
                            "localIp": request.local_ip,
                        }
                    ),
                    principal.tenant_id,
                    principal.agent_id,
                ),
            )
            conn.execute(
                """
                update public.devices
                set status = case when owner_membership_id is null then 'pending' else %s end,
                    last_seen_at = timezone('utc', now()),
                    metadata = metadata || %s,
                    updated_at = timezone('utc', now())
                where tenant_id = %s and id = %s
                """,
                (
                    "syncing" if status == "online" else status,
                    Jsonb(
                        {
                            "agentVersion": request.agent_version,
                            "queueDepth": request.queue_depth,
                            "lastError": request.last_error,
                            "localIp": request.local_ip,
                            "agentIdentityId": str(principal.agent_id),
                            "profile": principal.profile,
                        }
                    ),
                    principal.tenant_id,
                    principal.device_id,
                ),
            )
            allowed_commands = set(signed_policy["policy"].get("allowedCommands", []))
            commands = list(
                conn.execute(
                    """
                    select id as command_id, command_type, reason, payload, expires_at
                    from public.agent_commands
                    where tenant_id = %s
                      and agent_identity_id = %s
                      and status = 'pending'
                      and expires_at > timezone('utc', now())
                    order by created_at
                    limit 20
                    """,
                    (principal.tenant_id, principal.agent_id),
                ).fetchall()
            )
            commands = [command for command in commands if command["command_type"] in allowed_commands]
            if commands:
                conn.execute(
                    """
                    update public.agent_commands
                    set status = 'delivered',
                        delivered_at = timezone('utc', now()),
                        updated_at = timezone('utc', now())
                    where tenant_id = %s and id = any(%s)
                    """,
                    (principal.tenant_id, [command["command_id"] for command in commands]),
                )
            conn.commit()
            return {
                "accepted": True,
                "server_time": datetime.now(timezone.utc),
                "policy": signed_policy if request.policy_revision != effective_revision else None,
                "commands": commands,
            }

    def store_events(self, principal: AgentPrincipal, request: AgentEventsV2Request) -> dict:
        stored = 0
        duplicates = 0
        acknowledged: list[UUID] = []
        now = datetime.now(timezone.utc)
        with self.base._connect() as conn:
            _, effective_policy = self._effective_policy(conn, principal)
            allow_window_titles = bool(effective_policy.get("privacy", {}).get("windowTitles", False))
            for event in request.events:
                event_context = dict(event.context)
                if not allow_window_titles:
                    event_context.pop("windowTitle", None)
                    event_context.pop("window_title", None)
                clock_drift_ms = int((now - event.occurred_at).total_seconds() * 1000)
                unified = conn.execute(
                    """
                    insert into public.unified_events (
                      id, tenant_id, schema_version, agent_id, source, source_type,
                      source_event_id, event_type, category, severity, occurred_at,
                      device_occurred_at, received_at, clock_drift_ms, offline_buffered,
                      actor, device, context, metrics, message, technical_message,
                      fingerprint, correlation_id, causation_id, confidence,
                      privacy_classification, retention_policy, trusted_origin,
                      data_origin, extensions
                    )
                    values (
                      %s, %s, %s, %s, 'vulcan-agent', %s,
                      %s, %s, %s, %s, %s,
                      %s, timezone('utc', now()), %s, %s,
                      %s, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s,
                      %s, %s, true,
                      %s, %s
                    )
                    on conflict (tenant_id, source, source_event_id) do nothing
                    returning id
                    """,
                    (
                        event.event_id,
                        principal.tenant_id,
                        event.schema_version,
                        principal.agent_id,
                        {"workstation": "endpoint", "server": "server", "collector": "collector"}[principal.profile],
                        str(event.event_id),
                        event.event_type,
                        event.category,
                        event.severity,
                        event.occurred_at,
                        event.occurred_at,
                        clock_drift_ms,
                        event.offline_buffered,
                        Jsonb(
                            {
                                **event.actor,
                                "membershipId": str(principal.owner_membership_id)
                                if principal.owner_membership_id
                                else None,
                            }
                        ),
                        Jsonb(
                            {
                                **event.device,
                                "deviceId": str(principal.device_id),
                                "hostname": principal.hostname,
                            }
                        ),
                        Jsonb(event_context),
                        Jsonb(event.metrics),
                        event.message,
                        event.technical_message,
                        event.fingerprint,
                        event.correlation_id,
                        event.causation_id,
                        event.confidence,
                        event.privacy_classification,
                        event.retention_policy,
                        _event_data_origin(event),
                        Jsonb(
                            {
                                **event.extensions,
                                "batchId": str(request.batch_id),
                                "agentIdentityId": str(principal.agent_id),
                                "clockDriftDetected": abs(clock_drift_ms) > 300000,
                            }
                        ),
                    ),
                ).fetchone()
                if unified:
                    stored += 1
                    app_name = event_context.get("appName") or event_context.get("processName")
                    window_title = event_context.get("windowTitle") if allow_window_titles else None
                    duration = event.metrics.get("durationSeconds")
                    conn.execute(
                        """
                        insert into public.activity_events (
                          tenant_id, membership_id, device_id, source_event_id,
                          event_type, app_name, window_title, category,
                          duration_seconds, occurred_at, metadata
                        )
                        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        on conflict (tenant_id, source_event_id)
                          where source_event_id is not null do nothing
                        """,
                        (
                            principal.tenant_id,
                            principal.owner_membership_id,
                            principal.device_id,
                            str(event.event_id),
                            event.event_type,
                            app_name,
                            window_title,
                            event.category,
                            int(duration) if isinstance(duration, (int, float)) and duration >= 0 else None,
                            event.occurred_at,
                            Jsonb(
                                {
                                    "source": "vulcan-agent-v2",
                                    "agentIdentityId": str(principal.agent_id),
                                    "offlineQueued": event.offline_buffered,
                                    "dataOrigin": _event_data_origin(event),
                                    "message": event.message,
                                    "metrics": event.metrics,
                                }
                            ),
                        ),
                    )
                else:
                    duplicates += 1
                acknowledged.append(event.event_id)
            conn.execute(
                """
                update public.agent_identities
                set status = 'online',
                    last_seen_at = timezone('utc', now()),
                    metadata = metadata || %s,
                    updated_at = timezone('utc', now())
                where tenant_id = %s and id = %s
                """,
                (
                    Jsonb(
                        {
                            "lastBatchId": str(request.batch_id),
                            "lastBatchReceived": len(request.events),
                            "lastBatchStored": stored,
                            "lastBatchDuplicates": duplicates,
                        }
                    ),
                    principal.tenant_id,
                    principal.agent_id,
                ),
            )
            self.base.write_agent_audit(
                conn,
                principal.tenant_id,
                "agent.v2.events.stored",
                "agent_identity",
                principal.agent_id,
                {
                    "batchId": str(request.batch_id),
                    "received": len(request.events),
                    "stored": stored,
                    "duplicates": duplicates,
                },
            )
            conn.commit()
        return {
            "accepted": True,
            "received": len(request.events),
            "stored": stored,
            "duplicates": duplicates,
            "acknowledged_event_ids": acknowledged,
            "server_time": datetime.now(timezone.utc),
        }

    def create_command(
        self,
        context: AuthContext,
        agent_id: UUID,
        request: AgentCommandCreate,
    ) -> dict:
        if not self.enabled:
            raise RuntimeError("database is required to create agent commands")
        self._assert_tenant(context, request.tenant_id)
        with self.base._connect() as conn:
            access = self.base._access(conn, context)
            self._assert_admin(access, context)
            row = conn.execute(
                """
                insert into public.agent_commands (
                  tenant_id, agent_identity_id, command_type, reason, payload,
                  requested_by, expires_at
                )
                select %s, identity.id, %s, %s, %s, %s, %s
                from public.agent_identities identity
                where identity.tenant_id = %s
                  and identity.id = %s
                  and identity.status not in ('revoked', 'retired')
                returning *
                """,
                (
                    request.tenant_id,
                    request.command_type,
                    request.reason,
                    Jsonb(request.payload),
                    self._actor_uuid(context),
                    datetime.now(timezone.utc) + timedelta(minutes=request.expires_in_minutes),
                    request.tenant_id,
                    agent_id,
                ),
            ).fetchone()
            if not row:
                raise ValueError("agent not found")
            self.base.write_audit(
                conn,
                context,
                request.tenant_id,
                "agent.command.created",
                "agent_command",
                row["id"],
                {
                    "agentId": str(agent_id),
                    "commandType": request.command_type,
                    "reason": request.reason,
                },
            )
            conn.commit()
            return dict(row)

    def set_identity_status(
        self,
        context: AuthContext,
        agent_id: UUID,
        *,
        status: str,
        reason: str,
    ) -> None:
        if status not in {"approved", "revoked"}:
            raise ValueError("unsupported identity status transition")
        if not self.enabled:
            raise RuntimeError("database is required to manage agent identities")
        with self.base._connect() as conn:
            access = self.base._access(conn, context)
            self._assert_admin(access, context)
            row = conn.execute(
                """
                update public.agent_identities
                set status = %s,
                    revoked_at = case when %s = 'revoked' then timezone('utc', now()) else null end,
                    revocation_reason = case when %s = 'revoked' then %s else null end,
                    updated_at = timezone('utc', now())
                where tenant_id = %s and id = %s
                returning device_id
                """,
                (status, status, status, reason, context.tenant_id, agent_id),
            ).fetchone()
            if not row:
                raise ValueError("agent not found")
            conn.execute(
                """
                update public.devices
                set status = %s,
                    updated_at = timezone('utc', now())
                where tenant_id = %s and id = %s
                """,
                ("pending" if status == "approved" else "offline", context.tenant_id, row["device_id"]),
            )
            self.base.write_audit(
                conn,
                context,
                context.tenant_id,
                f"agent.identity.{status}",
                "agent_identity",
                agent_id,
                {"reason": reason},
            )
            conn.commit()

    def revoke_enrollment_token(self, context: AuthContext, token_id: UUID, reason: str) -> None:
        if not self.enabled:
            raise RuntimeError("database is required to manage enrollment tokens")
        with self.base._connect() as conn:
            access = self.base._access(conn, context)
            self._assert_admin(access, context)
            row = conn.execute(
                """
                update public.agent_enrollment_tokens
                set revoked_at = timezone('utc', now()),
                    updated_at = timezone('utc', now())
                where tenant_id = %s and id = %s and revoked_at is null
                returning id
                """,
                (context.tenant_id, token_id),
            ).fetchone()
            if not row:
                raise ValueError("active enrollment token not found")
            self.base.write_audit(
                conn,
                context,
                context.tenant_id,
                "agent.enrollment_token.revoked",
                "agent_enrollment_token",
                token_id,
                {"reason": reason},
            )
            conn.commit()

    def complete_command(
        self,
        principal: AgentPrincipal,
        command_id: UUID,
        request: AgentCommandResult,
    ) -> None:
        with self.base._connect() as conn:
            row = conn.execute(
                """
                update public.agent_commands
                set status = %s,
                    output_summary = %s,
                    completed_at = case when %s in ('succeeded', 'failed')
                      then timezone('utc', now()) else completed_at end,
                    updated_at = timezone('utc', now())
                where tenant_id = %s
                  and agent_identity_id = %s
                  and id = %s
                  and status in ('delivered', 'running')
                returning id
                """,
                (
                    request.status,
                    request.output_summary,
                    request.status,
                    principal.tenant_id,
                    principal.agent_id,
                    command_id,
                ),
            ).fetchone()
            if not row:
                raise ValueError("command not found or transition rejected")
            self.base.write_agent_audit(
                conn,
                principal.tenant_id,
                "agent.command.result",
                "agent_command",
                command_id,
                {"status": request.status},
            )
            conn.commit()

    def self_revoke(self, principal: AgentPrincipal, reason: str) -> None:
        with self.base._connect() as conn:
            row = conn.execute(
                """
                update public.agent_identities
                set status = 'revoked',
                    revoked_at = timezone('utc', now()),
                    revocation_reason = %s,
                    updated_at = timezone('utc', now())
                where tenant_id = %s
                  and id = %s
                  and status not in ('revoked', 'retired')
                returning device_id
                """,
                (reason, principal.tenant_id, principal.agent_id),
            ).fetchone()
            if not row:
                raise ValueError("agent identity is already revoked")
            conn.execute(
                """
                update public.devices
                set status = 'offline',
                    updated_at = timezone('utc', now())
                where tenant_id = %s and id = %s
                """,
                (principal.tenant_id, row["device_id"]),
            )
            self.base.write_agent_audit(
                conn,
                principal.tenant_id,
                "agent.v2.unenrolled",
                "agent_identity",
                principal.agent_id,
                {"reason": reason},
            )
            conn.commit()
