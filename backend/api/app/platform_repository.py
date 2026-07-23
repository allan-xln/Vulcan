from __future__ import annotations

import base64
import hashlib
import os
from datetime import datetime, timedelta, timezone
from ipaddress import ip_network
from time import perf_counter
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from app.config import Settings, get_settings
from app.integration_adapters import ADAPTER_CATALOG
from app.platform_schemas import (
    AssetCreate,
    CanonicalEventCreate,
    CanonicalEventResult,
    DependencyCheck,
    DiscoveryPolicyCreate,
    DiscoveryPolicyStateUpdate,
    DiscoveryRunCreate,
    EventSimulationRequest,
    EventSimulationResponse,
    InfrastructureNetworkCreate,
    InfrastructureOverview,
    PlatformHealth,
    ScoreComponent,
    SiteCreate,
    TimelineEvent,
    TimelinePage,
)
from app.repository import VulcanRepository
from app.security import AuthContext


SIMULATED_SITE_ID = UUID("00000000-0000-0000-0000-000000700001")
SIMULATED_NETWORK_ID = UUID("00000000-0000-0000-0000-000000700101")
SIMULATED_ASSET_ID = UUID("00000000-0000-0000-0000-000000700201")


class PlatformAuthorizationError(ValueError):
    pass


class PlatformRepository:
    def __init__(self, settings: Settings | None = None, base_repository: VulcanRepository | None = None) -> None:
        self.settings = settings or get_settings()
        self.base = base_repository or VulcanRepository(self.settings)

    @property
    def enabled(self) -> bool:
        return self.base.enabled

    def _access(self, conn, context: AuthContext):
        return self.base._access(conn, context)

    @staticmethod
    def _assert_active_tenant(context: AuthContext, tenant_id: UUID) -> None:
        if context.tenant_id != tenant_id:
            raise ValueError("tenant outside active context")

    @staticmethod
    def _assert_admin(access, context: AuthContext) -> None:
        if access is not None and access.is_root:
            return
        effective_role = access.role_slug if access is not None and access.role_slug else context.role
        if effective_role in {
            "admin",
            "owner",
            "root",
            "tenant_owner",
            "tenant_admin",
            "infrastructure_admin",
            "security_admin",
        }:
            return
        raise PlatformAuthorizationError("tenant administration permission required")

    @staticmethod
    def _assert_infrastructure_read(access, context: AuthContext) -> None:
        if access is not None and access.is_root:
            return
        effective_role = access.role_slug if access is not None and access.role_slug else context.role
        if effective_role in {
            "admin",
            "owner",
            "root",
            "tenant_owner",
            "tenant_admin",
            "infrastructure_admin",
            "security_admin",
            "hierarchy",
            "manager",
            "supervisor",
            "auditor",
            "analyst",
            "read_only",
        }:
            return
        raise PlatformAuthorizationError("infrastructure read permission required")

    @staticmethod
    def _apply_timeline_scope(access, conditions: list[str], params: list[object]) -> None:
        if access.is_root or access.scope in {"tenant", "global"}:
            return
        if access.membership_id is None:
            conditions.append("false")
            return
        if access.scope == "hierarchy":
            conditions.append(
                """
                exists (
                  select 1
                  from public.membership_closure visible_membership
                  where visible_membership.tenant_id = event.tenant_id
                    and visible_membership.ancestor_membership_id = %s
                    and visible_membership.descendant_membership_id::text = event.actor ->> 'membershipId'
                )
                """
            )
            params.append(access.membership_id)
            return
        conditions.append("event.actor ->> 'membershipId' = %s")
        params.append(str(access.membership_id))

    def list_modules(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            now = datetime.now(timezone.utc)
            return [
                {
                    "id": uuid4(),
                    "tenant_id": context.tenant_id,
                    "module_key": key,
                    "enabled": key in {"workforce", "infrastructure", "timeline", "assets"},
                    "plan_source": "tenant" if key != "workforce" else "system",
                    "limits": {},
                    "enabled_at": now if key in {"workforce", "infrastructure", "timeline", "assets"} else None,
                }
                for key in (
                    "workforce",
                    "infrastructure",
                    "timeline",
                    "assets",
                    "print",
                    "security",
                    "intelligence",
                    "automations",
                    "compliance",
                    "administration",
                )
            ]
        with self.base._connect() as conn:
            self._access(conn, context)
            return list(
                conn.execute(
                    """
                    select id, tenant_id, module_key, enabled, plan_source, limits, enabled_at
                    from public.tenant_modules
                    where tenant_id = %s
                    order by case when module_key = 'workforce' then 0 else 1 end, module_key
                    """,
                    (context.tenant_id,),
                ).fetchall()
            )

    def infrastructure_overview(self, context: AuthContext) -> InfrastructureOverview:
        now = datetime.now(timezone.utc)
        if not self.enabled:
            self._assert_infrastructure_read(None, context)
            components = [
                ScoreComponent(
                    key="availability",
                    label="Disponibilidade dos ativos",
                    value=0.92,
                    maxPoints=50,
                    points=46,
                    formula="(online + 0,5 × degradados) ÷ ativos monitorados × 50",
                ),
                ScoreComponent(
                    key="incidents",
                    label="Incidentes abertos",
                    value=1,
                    maxPoints=25,
                    points=20,
                    formula="25 - min(incidentes abertos × 5, 25)",
                ),
                ScoreComponent(
                    key="freshness",
                    label="Telemetria recente",
                    value=0.88,
                    maxPoints=25,
                    points=22,
                    formula="ativos vistos nos últimos 15 minutos ÷ ativos monitorados × 25",
                ),
            ]
            return InfrastructureOverview(
                tenantId=context.tenant_id,
                dataOrigin="simulated",
                generatedAt=now,
                sites=1,
                networks=1,
                assets=4,
                onlineAssets=3,
                degradedAssets=1,
                offlineAssets=0,
                unknownAssets=0,
                openIncidents=1,
                eventsLast24h=12,
                pendingDiscoveries=1,
                healthScore=88,
                scoreComponents=components,
            )

        with self.base._connect() as conn:
            access = self._access(conn, context)
            self._assert_infrastructure_read(access, context)
            row = conn.execute(
                """
                select
                  (select count(*) from public.sites where tenant_id = %(tenant_id)s and status <> 'inactive') as sites,
                  (select count(*) from public.infrastructure_networks where tenant_id = %(tenant_id)s and status <> 'inactive') as networks,
                  (select count(*) from public.infrastructure_assets where tenant_id = %(tenant_id)s and status <> 'retired') as assets,
                  (select count(*) from public.infrastructure_assets where tenant_id = %(tenant_id)s and status = 'online') as online_assets,
                  (select count(*) from public.infrastructure_assets where tenant_id = %(tenant_id)s and status = 'degraded') as degraded_assets,
                  (select count(*) from public.infrastructure_assets where tenant_id = %(tenant_id)s and status = 'offline') as offline_assets,
                  (select count(*) from public.infrastructure_assets where tenant_id = %(tenant_id)s and status = 'unknown') as unknown_assets,
                  (select count(*) from public.incidents where tenant_id = %(tenant_id)s and status in ('open', 'investigating', 'monitoring')) as open_incidents,
                  (select count(*) from public.unified_events where tenant_id = %(tenant_id)s and received_at >= timezone('utc', now()) - interval '24 hours') as events_last_24h,
                  (select count(*) from public.discovery_findings where tenant_id = %(tenant_id)s and state in ('discovered', 'identified', 'pending_review')) as pending_discoveries,
                  (
                    select count(*)
                    from public.infrastructure_assets
                    where tenant_id = %(tenant_id)s
                      and status <> 'retired'
                      and last_seen_at >= timezone('utc', now()) - interval '15 minutes'
                  ) as fresh_assets
                """,
                {"tenant_id": context.tenant_id},
            ).fetchone()

        assets = int(row["assets"])
        online = int(row["online_assets"])
        degraded = int(row["degraded_assets"])
        incidents = int(row["open_incidents"])
        fresh = int(row["fresh_assets"])
        if assets:
            availability_value = (online + degraded * 0.5) / assets
            availability_points = round(availability_value * 50, 2)
            incident_points = max(0, 25 - incidents * 5)
            freshness_value = fresh / assets
            freshness_points = round(freshness_value * 25, 2)
            components = [
                ScoreComponent(
                    key="availability",
                    label="Disponibilidade dos ativos",
                    value=availability_value,
                    maxPoints=50,
                    points=availability_points,
                    formula="(online + 0,5 × degradados) ÷ ativos monitorados × 50",
                ),
                ScoreComponent(
                    key="incidents",
                    label="Incidentes abertos",
                    value=incidents,
                    maxPoints=25,
                    points=incident_points,
                    formula="25 - min(incidentes abertos × 5, 25)",
                ),
                ScoreComponent(
                    key="freshness",
                    label="Telemetria recente",
                    value=freshness_value,
                    maxPoints=25,
                    points=freshness_points,
                    formula="ativos vistos nos últimos 15 minutos ÷ ativos monitorados × 25",
                ),
            ]
            health_score = round(sum(component.points for component in components))
        else:
            components = []
            health_score = None

        return InfrastructureOverview(
            tenantId=context.tenant_id,
            dataOrigin="real",
            generatedAt=now,
            healthScore=health_score,
            scoreComponents=components,
            **{key: row[key] for key in (
                "sites",
                "networks",
                "assets",
                "online_assets",
                "degraded_assets",
                "offline_assets",
                "unknown_assets",
                "open_incidents",
                "events_last_24h",
                "pending_discoveries",
            )},
        )

    def list_sites(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            self._assert_infrastructure_read(None, context)
            now = datetime.now(timezone.utc)
            return [
                {
                    "id": SIMULATED_SITE_ID,
                    "tenant_id": context.tenant_id,
                    "code": "DEMO-SJP",
                    "name": "Unidade demonstrativa",
                    "description": "Dados simulados para demonstrar a organização por site.",
                    "address": {"city": "São José dos Pinhais", "country": "BR"},
                    "timezone": "America/Sao_Paulo",
                    "status": "active",
                    "tags": ["simulado"],
                    "data_origin": "simulated",
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        with self.base._connect() as conn:
            access = self._access(conn, context)
            self._assert_infrastructure_read(access, context)
            rows = conn.execute(
                """
                select id, tenant_id, code, name, description, address, timezone, status, tags,
                       'real' as data_origin, created_at, updated_at
                from public.sites
                where tenant_id = %s
                order by status, name
                """,
                (context.tenant_id,),
            ).fetchall()
            return list(rows)

    def create_site(self, context: AuthContext, request: SiteCreate) -> dict:
        self._assert_active_tenant(context, request.tenant_id)
        if not self.enabled:
            self._assert_admin(None, context)
            now = datetime.now(timezone.utc)
            return {
                "id": uuid4(),
                **request.model_dump(),
                "status": "active",
                "data_origin": "simulated",
                "created_at": now,
                "updated_at": now,
            }
        with self.base._connect() as conn:
            access = self._access(conn, context)
            self._assert_admin(access, context)
            row = conn.execute(
                """
                insert into public.sites (tenant_id, code, name, description, address, timezone, tags)
                values (%s, upper(%s), %s, %s, %s, %s, %s)
                returning id, tenant_id, code, name, description, address, timezone, status, tags,
                          'real' as data_origin, created_at, updated_at
                """,
                (
                    request.tenant_id,
                    request.code,
                    request.name,
                    request.description,
                    Jsonb(request.address),
                    request.timezone,
                    request.tags,
                ),
            ).fetchone()
            conn.commit()
            return dict(row)

    def list_networks(self, context: AuthContext, site_id: UUID | None = None) -> list[dict]:
        if not self.enabled:
            self._assert_infrastructure_read(None, context)
            now = datetime.now(timezone.utc)
            if site_id and site_id != SIMULATED_SITE_ID:
                return []
            return [
                {
                    "id": SIMULATED_NETWORK_ID,
                    "tenant_id": context.tenant_id,
                    "site_id": SIMULATED_SITE_ID,
                    "site_name": "Unidade demonstrativa",
                    "name": "Rede corporativa simulada",
                    "description": "Nenhuma varredura real é executada em modo simulado.",
                    "network_cidr": "192.0.2.0/28",
                    "gateway": "192.0.2.1",
                    "vlan_id": 20,
                    "dns_servers": ["192.0.2.2"],
                    "dhcp_enabled": True,
                    "discovery_allowed": False,
                    "status": "active",
                    "tags": ["simulado"],
                    "data_origin": "simulated",
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        with self.base._connect() as conn:
            access = self._access(conn, context)
            self._assert_infrastructure_read(access, context)
            params: list[object] = [context.tenant_id]
            site_filter = ""
            if site_id:
                site_filter = "and network.site_id = %s"
                params.append(site_id)
            rows = conn.execute(
                f"""
                select network.id, network.tenant_id, network.site_id, site.name as site_name,
                       network.name, network.description, network.network_cidr::text as network_cidr,
                       host(network.gateway) as gateway,
                       network.vlan_id,
                       coalesce(array(select host(value) from unnest(network.dns_servers) value), '{{}}') as dns_servers,
                       network.dhcp_enabled, network.discovery_allowed, network.status, network.tags,
                       'real' as data_origin, network.created_at, network.updated_at
                from public.infrastructure_networks network
                join public.sites site on site.tenant_id = network.tenant_id and site.id = network.site_id
                where network.tenant_id = %s {site_filter}
                order by site.name, network.name
                """,
                tuple(params),
            ).fetchall()
            return list(rows)

    def create_network(self, context: AuthContext, request: InfrastructureNetworkCreate) -> dict:
        self._assert_active_tenant(context, request.tenant_id)
        if not self.enabled:
            self._assert_admin(None, context)
            now = datetime.now(timezone.utc)
            return {
                "id": uuid4(),
                **request.model_dump(),
                "site_name": "Unidade simulada",
                "status": "active",
                "data_origin": "simulated",
                "created_at": now,
                "updated_at": now,
            }
        with self.base._connect() as conn:
            access = self._access(conn, context)
            self._assert_admin(access, context)
            site = conn.execute(
                "select name from public.sites where tenant_id = %s and id = %s",
                (request.tenant_id, request.site_id),
            ).fetchone()
            if not site:
                raise ValueError("site not found in active tenant")
            row = conn.execute(
                """
                insert into public.infrastructure_networks (
                  tenant_id, site_id, name, description, network_cidr, gateway, vlan_id,
                  dns_servers, dhcp_enabled, discovery_allowed, tags
                )
                values (%s, %s, %s, %s, %s::cidr, %s::inet, %s, %s::inet[], %s, %s, %s)
                returning id, tenant_id, site_id, name, description, network_cidr::text as network_cidr,
                          host(gateway) as gateway, vlan_id,
                          coalesce(array(select host(value) from unnest(dns_servers) value), '{}') as dns_servers,
                          dhcp_enabled, discovery_allowed, status, tags,
                          'real' as data_origin, created_at, updated_at
                """,
                (
                    request.tenant_id,
                    request.site_id,
                    request.name,
                    request.description,
                    request.network_cidr,
                    request.gateway,
                    request.vlan_id,
                    request.dns_servers,
                    request.dhcp_enabled,
                    request.discovery_allowed,
                    request.tags,
                ),
            ).fetchone()
            conn.commit()
            return {**dict(row), "site_name": site["name"]}

    def list_assets(
        self,
        context: AuthContext,
        site_id: UUID | None = None,
        asset_type: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        if not self.enabled:
            self._assert_infrastructure_read(None, context)
            now = datetime.now(timezone.utc)
            return [
                {
                    "id": SIMULATED_ASSET_ID,
                    "tenant_id": context.tenant_id,
                    "site_id": SIMULATED_SITE_ID,
                    "site_name": "Unidade demonstrativa",
                    "network_id": SIMULATED_NETWORK_ID,
                    "network_name": "Rede corporativa simulada",
                    "asset_type": "switch",
                    "name": "Switch demonstrativo",
                    "hostname": "DEMO-SW-01",
                    "manufacturer": "Fabricante simulado",
                    "model": "Modelo simulado",
                    "ip_address": "192.0.2.3",
                    "mac_address": "02:00:00:00:00:03",
                    "status": "degraded",
                    "criticality": "high",
                    "lifecycle_state": "managed",
                    "tags": ["simulado"],
                    "source": "simulator",
                    "confidence": 1,
                    "last_seen_at": now,
                    "data_origin": "simulated",
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        conditions = ["asset.tenant_id = %s"]
        params: list[object] = [context.tenant_id]
        if site_id:
            conditions.append("asset.site_id = %s")
            params.append(site_id)
        if asset_type:
            conditions.append("asset.asset_type = %s")
            params.append(asset_type)
        if status:
            conditions.append("asset.status = %s")
            params.append(status)
        with self.base._connect() as conn:
            access = self._access(conn, context)
            self._assert_infrastructure_read(access, context)
            rows = conn.execute(
                f"""
                select asset.id, asset.tenant_id, asset.site_id, site.name as site_name,
                       asset.network_id, network.name as network_name, asset.parent_asset_id,
                       asset.owner_membership_id, asset.department_id, asset.endpoint_device_id,
                       asset.asset_type, asset.name, asset.hostname, asset.description,
                       asset.manufacturer, asset.model, asset.serial_number, asset.asset_tag,
                       host(asset.ip_address) as ip_address, asset.mac_address, asset.operating_system,
                       asset.status, asset.criticality, asset.lifecycle_state, asset.responsible,
                       asset.physical_location, asset.rack, asset.rack_position, asset.tags, asset.source,
                       asset.confidence, asset.discovered_at, asset.last_seen_at,
                       'real' as data_origin, asset.created_at, asset.updated_at
                from public.infrastructure_assets asset
                left join public.sites site on site.tenant_id = asset.tenant_id and site.id = asset.site_id
                left join public.infrastructure_networks network
                  on network.tenant_id = asset.tenant_id and network.id = asset.network_id
                where {" and ".join(conditions)}
                order by
                  case asset.status when 'offline' then 0 when 'degraded' then 1 when 'unknown' then 2 else 3 end,
                  asset.name
                limit 1000
                """,
                tuple(params),
            ).fetchall()
            return list(rows)

    def create_asset(self, context: AuthContext, request: AssetCreate) -> dict:
        self._assert_active_tenant(context, request.tenant_id)
        if not self.enabled:
            self._assert_admin(None, context)
            now = datetime.now(timezone.utc)
            return {
                "id": uuid4(),
                **request.model_dump(),
                "lifecycle_state": "managed",
                "source": "manual",
                "data_origin": "simulated",
                "created_at": now,
                "updated_at": now,
            }
        with self.base._connect() as conn:
            access = self._access(conn, context)
            self._assert_admin(access, context)
            if request.site_id and not conn.execute(
                "select 1 from public.sites where tenant_id = %s and id = %s",
                (request.tenant_id, request.site_id),
            ).fetchone():
                raise ValueError("site not found in active tenant")
            if request.network_id and not conn.execute(
                "select 1 from public.infrastructure_networks where tenant_id = %s and id = %s",
                (request.tenant_id, request.network_id),
            ).fetchone():
                raise ValueError("network not found in active tenant")
            row = conn.execute(
                """
                insert into public.infrastructure_assets (
                  tenant_id, site_id, network_id, parent_asset_id, owner_membership_id, department_id,
                  asset_type, name, hostname, description, manufacturer, model, serial_number,
                  asset_tag, ip_address, mac_address, operating_system, status, criticality,
                  responsible, physical_location, rack, rack_position, tags, notes, source
                )
                values (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::inet,
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'manual'
                )
                returning id
                """,
                (
                    request.tenant_id,
                    request.site_id,
                    request.network_id,
                    request.parent_asset_id,
                    request.owner_membership_id,
                    request.department_id,
                    request.asset_type,
                    request.name,
                    request.hostname,
                    request.description,
                    request.manufacturer,
                    request.model,
                    request.serial_number,
                    request.asset_tag,
                    request.ip_address,
                    request.mac_address,
                    request.operating_system,
                    request.status,
                    request.criticality,
                    request.responsible,
                    request.physical_location,
                    request.rack,
                    request.rack_position,
                    request.tags,
                    request.notes,
                ),
            ).fetchone()
            conn.commit()
            asset_id = row["id"]
        return next(item for item in self.list_assets(context) if item["id"] == asset_id)

    @staticmethod
    def _encode_cursor(occurred_at: datetime, event_id: UUID) -> str:
        raw = f"{occurred_at.isoformat()}|{event_id}"
        return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
        try:
            padding = "=" * (-len(cursor) % 4)
            raw = base64.urlsafe_b64decode((cursor + padding).encode()).decode()
            occurred_at, event_id = raw.split("|", 1)
            parsed = datetime.fromisoformat(occurred_at)
            if parsed.tzinfo is None:
                raise ValueError
            return parsed, UUID(event_id)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("invalid timeline cursor") from exc

    @staticmethod
    def _timeline_row(row: dict) -> dict:
        return {
            "event_id": row["id"],
            **{key: value for key, value in row.items() if key != "id"},
        }

    def _simulated_timeline(self, context: AuthContext, limit: int) -> TimelinePage:
        now = datetime.now(timezone.utc)
        templates = [
            (
                "infrastructure.link.degraded",
                "network",
                "warning",
                "A porta 18 do switch demonstrativo apresenta sinais de problema físico e pode causar quedas.",
            ),
            (
                "workforce.application.slow",
                "workforce",
                "notice",
                "A produtividade do setor foi afetada por lentidão do aplicativo operacional.",
            ),
            (
                "network.disconnect",
                "network",
                "warning",
                "A estação perdeu conectividade durante 42 segundos.",
            ),
            (
                "workforce.context_switch",
                "workforce",
                "info",
                "O usuário retomou o fluxo de trabalho após a conexão estabilizar.",
            ),
        ]
        items = []
        for index, (event_type, category, severity, message) in enumerate(templates[:limit]):
            event_id = UUID(f"00000000-0000-0000-0000-{800001 + index:012d}")
            occurred = now - timedelta(minutes=index * 3)
            items.append(
                TimelineEvent(
                    eventId=event_id,
                    tenantId=context.tenant_id,
                    schemaVersion="2026-07-vulcan-event.v1",
                    siteId=SIMULATED_SITE_ID,
                    assetId=SIMULATED_ASSET_ID,
                    source="vulcan-simulator",
                    sourceType="development",
                    sourceEventId=f"simulated-{event_id}",
                    eventType=event_type,
                    category=category,
                    severity=severity,
                    occurredAt=occurred,
                    receivedAt=occurred,
                    offlineBuffered=False,
                    actor={},
                    device={"hostname": "DEMO-SW-01", "ip": "192.0.2.3"},
                    context={"simulation": True},
                    metrics={},
                    message=message,
                    technicalMessage="Evento de demonstração; nenhuma rede real foi consultada.",
                    fingerprint=f"simulated-{event_id}",
                    confidence=0.9,
                    privacyClassification="operational",
                    retentionPolicy="development",
                    trustedOrigin=True,
                    dataOrigin="simulated",
                    extensions={"simulation": True},
                    createdAt=occurred,
                )
            )
        return TimelinePage(items=items, hasMore=False, dataOrigin="simulated")

    def list_timeline(
        self,
        context: AuthContext,
        *,
        limit: int = 100,
        cursor: str | None = None,
        site_id: UUID | None = None,
        asset_id: UUID | None = None,
        agent_id: UUID | None = None,
        membership_id: UUID | None = None,
        incident_id: UUID | None = None,
        category: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        search: str | None = None,
    ) -> TimelinePage:
        if not self.enabled:
            if context.role == "user":
                return TimelinePage(items=[], hasMore=False, dataOrigin="simulated")
            return self._simulated_timeline(context, limit)
        conditions = ["event.tenant_id = %s"]
        params: list[object] = [context.tenant_id]
        filters = {
            "event.site_id": site_id,
            "event.asset_id": asset_id,
            "event.agent_id": agent_id,
            "event.category": category,
            "event.severity": severity,
            "event.source": source,
        }
        for column, value in filters.items():
            if value is not None:
                conditions.append(f"{column} = %s")
                params.append(value)
        if membership_id:
            conditions.append("event.actor ->> 'membershipId' = %s")
            params.append(str(membership_id))
        if incident_id:
            conditions.append(
                "exists (select 1 from public.incident_events link where link.tenant_id = event.tenant_id and link.event_id = event.id and link.incident_id = %s)"
            )
            params.append(incident_id)
        if search:
            conditions.append(
                "(event.message ilike %s or coalesce(event.technical_message, '') ilike %s or event.event_type ilike %s)"
            )
            term = f"%{search[:200]}%"
            params.extend([term, term, term])
        if cursor:
            cursor_time, cursor_id = self._decode_cursor(cursor)
            conditions.append("(event.occurred_at, event.id) < (%s, %s)")
            params.extend([cursor_time, cursor_id])
        with self.base._connect() as conn:
            access = self._access(conn, context)
            self._apply_timeline_scope(access, conditions, params)
            rows = conn.execute(
                f"""
                select event.*
                from public.unified_events event
                where {" and ".join(conditions)}
                order by event.occurred_at desc, event.id desc
                limit %s
                """,
                (*params, limit + 1),
            ).fetchall()
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = None
        if has_more and page_rows:
            next_cursor = self._encode_cursor(page_rows[-1]["occurred_at"], page_rows[-1]["id"])
        return TimelinePage(
            items=[TimelineEvent.model_validate(self._timeline_row(dict(row))) for row in page_rows],
            nextCursor=next_cursor,
            hasMore=has_more,
            dataOrigin="real",
        )

    def received_events_after(
        self,
        context: AuthContext,
        after: datetime,
        after_id: UUID | None = None,
        limit: int = 100,
    ) -> list[TimelineEvent]:
        if not self.enabled:
            return []
        with self.base._connect() as conn:
            access = self._access(conn, context)
            conditions = [
                "event.tenant_id = %s",
                "(event.created_at, event.id) > (%s, %s)",
            ]
            params: list[object] = [
                context.tenant_id,
                after,
                after_id or UUID(int=0),
            ]
            self._apply_timeline_scope(access, conditions, params)
            rows = conn.execute(
                f"""
                select event.*
                from public.unified_events event
                where {" and ".join(conditions)}
                order by event.created_at, event.id
                limit %s
                """,
                (*params, limit),
            ).fetchall()
        return [TimelineEvent.model_validate(self._timeline_row(dict(row))) for row in rows]

    def ingest_event(self, context: AuthContext, request: CanonicalEventCreate) -> CanonicalEventResult:
        self._assert_active_tenant(context, request.tenant_id)
        now = datetime.now(timezone.utc)
        device_time = request.device_occurred_at or request.occurred_at
        clock_drift_ms = round((now - device_time.astimezone(timezone.utc)).total_seconds() * 1000)
        fingerprint = request.fingerprint or hashlib.sha256(
            f"{request.tenant_id}:{request.source}:{request.event_type}:{request.source_event_id}".encode()
        ).hexdigest()
        extensions = dict(request.extensions)
        if abs(clock_drift_ms) > 300_000:
            extensions["clockWarning"] = True
        if not self.enabled:
            self._assert_admin(None, context)
            payload = request.model_dump(exclude={"fingerprint", "extensions"})
            event = TimelineEvent(
                **payload,
                receivedAt=now,
                clockDriftMs=clock_drift_ms,
                fingerprint=fingerprint,
                trustedOrigin=False,
                extensions=extensions,
                createdAt=now,
            )
            return CanonicalEventResult(accepted=True, duplicate=False, event=event)

        with self.base._connect() as conn:
            access = self._access(conn, context)
            self._assert_admin(access, context)
            row = conn.execute(
                """
                insert into public.unified_events (
                  id, tenant_id, schema_version, site_id, asset_id, agent_id, source, source_type,
                  source_event_id, event_type, category, severity, occurred_at, device_occurred_at,
                  received_at, clock_drift_ms, offline_buffered, actor, device, context, metrics,
                  message, technical_message, fingerprint, correlation_id, causation_id, confidence,
                  privacy_classification, retention_policy, trusted_origin, data_origin, extensions
                )
                values (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, %s, %s
                )
                on conflict (tenant_id, source, source_event_id) do nothing
                returning *
                """,
                (
                    request.event_id,
                    request.tenant_id,
                    request.schema_version,
                    request.site_id,
                    request.asset_id,
                    request.agent_id,
                    request.source,
                    request.source_type,
                    request.source_event_id,
                    request.event_type,
                    request.category,
                    request.severity,
                    request.occurred_at,
                    device_time,
                    now,
                    clock_drift_ms,
                    request.offline_buffered,
                    Jsonb(request.actor),
                    Jsonb(request.device),
                    Jsonb(request.context),
                    Jsonb(request.metrics),
                    request.message,
                    request.technical_message,
                    fingerprint,
                    request.correlation_id,
                    request.causation_id,
                    request.confidence,
                    request.privacy_classification,
                    request.retention_policy,
                    request.data_origin,
                    Jsonb(extensions),
                ),
            ).fetchone()
            duplicate = row is None
            if duplicate:
                row = conn.execute(
                    """
                    select * from public.unified_events
                    where tenant_id = %s and source = %s and source_event_id = %s
                    """,
                    (request.tenant_id, request.source, request.source_event_id),
                ).fetchone()
            else:
                self.base.write_audit(
                    conn,
                    context,
                    request.tenant_id,
                    "timeline.event.ingested",
                    "unified_event",
                    request.event_id,
                    {"source": request.source, "eventType": request.event_type, "dataOrigin": request.data_origin},
                )
            conn.commit()
        return CanonicalEventResult(
            accepted=not duplicate,
            duplicate=duplicate,
            event=TimelineEvent.model_validate(self._timeline_row(dict(row))),
        )

    def simulate_events(self, context: AuthContext, request: EventSimulationRequest) -> EventSimulationResponse:
        self._assert_active_tenant(context, request.tenant_id)
        if self.settings.environment == "production":
            raise ValueError("event simulation is disabled in production")
        now = datetime.now(timezone.utc)
        correlation_id = f"simulation:{uuid4()}"
        templates = [
            (
                "workforce.application.slow",
                "workforce",
                "notice",
                "O aplicativo operacional começou a responder mais lentamente.",
            ),
            (
                "infrastructure.uplink.saturation",
                "network",
                "warning",
                "O uplink do site apresentou saturação e pode afetar o trabalho da equipe.",
            ),
            (
                "network.disconnect",
                "network",
                "warning",
                "Várias estações perderam conectividade no mesmo intervalo.",
            ),
            (
                "operations.productivity.impact",
                "intelligence",
                "warning",
                "A produtividade caiu por indisponibilidade de infraestrutura, não por comportamento da equipe.",
            ),
        ]
        generated: list[TimelineEvent] = []
        for index in range(request.count):
            event_type, category, severity, message = templates[index % len(templates)]
            event_id = uuid4()
            result = self.ingest_event(
                context,
                CanonicalEventCreate(
                    eventId=event_id,
                    tenantId=request.tenant_id,
                    siteId=SIMULATED_SITE_ID if not self.enabled else None,
                    assetId=SIMULATED_ASSET_ID if not self.enabled else None,
                    source="vulcan-simulator",
                    sourceType="development",
                    sourceEventId=str(event_id),
                    eventType=event_type,
                    category=category,
                    severity=severity,
                    occurredAt=now + timedelta(milliseconds=index),
                    deviceOccurredAt=now + timedelta(milliseconds=index),
                    actor={},
                    device={"hostname": "SIMULATED-ASSET"},
                    context={"simulation": True, "scenario": request.scenario},
                    metrics={},
                    message=message,
                    technicalMessage="Evento sintético criado pelo gerador de desenvolvimento.",
                    correlationId=correlation_id,
                    confidence=1,
                    privacyClassification="operational",
                    retentionPolicy="development",
                    dataOrigin="simulated",
                    extensions={"simulation": True},
                ),
            )
            generated.append(result.event)
        return EventSimulationResponse(
            generated=len(generated),
            scenario=request.scenario,
            events=generated,
        )

    def list_discovery_policies(self, context: AuthContext) -> list[dict]:
        if not self.enabled:
            self._assert_infrastructure_read(None, context)
            now = datetime.now(timezone.utc)
            return [
                {
                    "id": UUID("00000000-0000-0000-0000-000000700301"),
                    "tenant_id": context.tenant_id,
                    "site_id": SIMULATED_SITE_ID,
                    "site_name": "Unidade demonstrativa",
                    "name": "Discovery demonstrativo desativado",
                    "enabled": False,
                    "read_only": True,
                    "safe_mode": True,
                    "allowed_networks": ["192.0.2.0/28"],
                    "denied_networks": [],
                    "excluded_addresses": [],
                    "allowed_protocols": ["icmp", "dns"],
                    "allowed_tcp_ports": [],
                    "frequency_minutes": 60,
                    "concurrency": 4,
                    "timeout_ms": 750,
                    "max_targets": 14,
                    "data_origin": "simulated",
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        with self.base._connect() as conn:
            access = self._access(conn, context)
            self._assert_infrastructure_read(access, context)
            rows = conn.execute(
                """
                select policy.id, policy.tenant_id, policy.site_id, site.name as site_name,
                       policy.name, policy.enabled, policy.read_only, policy.safe_mode,
                       policy.allowed_networks::text[], policy.denied_networks::text[],
                       coalesce(array(select host(value) from unnest(policy.excluded_addresses) value), '{}') as excluded_addresses,
                       policy.allowed_protocols, policy.allowed_tcp_ports, policy.frequency_minutes,
                       policy.concurrency, policy.timeout_ms, policy.max_targets, policy.last_run_at,
                       policy.next_run_at, 'real' as data_origin, policy.created_at, policy.updated_at
                from public.discovery_policies policy
                join public.sites site on site.tenant_id = policy.tenant_id and site.id = policy.site_id
                where policy.tenant_id = %s
                order by policy.enabled desc, policy.name
                """,
                (context.tenant_id,),
            ).fetchall()
            return list(rows)

    def create_discovery_policy(self, context: AuthContext, request: DiscoveryPolicyCreate) -> dict:
        self._assert_active_tenant(context, request.tenant_id)
        allow_public = os.getenv("DISCOVERY_ALLOW_PUBLIC_NETWORKS", "false").lower() in {"1", "true", "yes"}
        networks = [ip_network(value, strict=True) for value in request.allowed_networks]
        if not allow_public and any(not (network.is_private or network.is_loopback or network.is_link_local) for network in networks):
            raise ValueError("public networks are blocked by discovery policy")
        if not self.enabled:
            self._assert_admin(None, context)
            now = datetime.now(timezone.utc)
            return {
                "id": uuid4(),
                **request.model_dump(),
                "read_only": True,
                "safe_mode": True,
                "site_name": "Unidade simulada",
                "data_origin": "simulated",
                "created_at": now,
                "updated_at": now,
            }
        with self.base._connect() as conn:
            access = self._access(conn, context)
            self._assert_admin(access, context)
            site = conn.execute(
                "select name from public.sites where tenant_id = %s and id = %s",
                (request.tenant_id, request.site_id),
            ).fetchone()
            if not site:
                raise ValueError("site not found in active tenant")
            row = conn.execute(
                """
                insert into public.discovery_policies (
                  tenant_id, site_id, name, enabled, read_only, safe_mode, allowed_networks,
                  denied_networks, excluded_addresses, allowed_protocols, allowed_tcp_ports,
                  frequency_minutes, concurrency, timeout_ms, max_targets
                )
                values (%s, %s, %s, %s, true, true, %s::cidr[], %s::cidr[], %s::inet[], %s, %s, %s, %s, %s, %s)
                returning id, tenant_id, site_id, name, enabled, read_only, safe_mode,
                          allowed_networks::text[], denied_networks::text[],
                          coalesce(array(select host(value) from unnest(excluded_addresses) value), '{}') as excluded_addresses,
                          allowed_protocols, allowed_tcp_ports, frequency_minutes, concurrency,
                          timeout_ms, max_targets, last_run_at, next_run_at,
                          'real' as data_origin, created_at, updated_at
                """,
                (
                    request.tenant_id,
                    request.site_id,
                    request.name,
                    request.enabled,
                    request.allowed_networks,
                    request.denied_networks,
                    request.excluded_addresses,
                    request.allowed_protocols,
                    request.allowed_tcp_ports,
                    request.frequency_minutes,
                    request.concurrency,
                    request.timeout_ms,
                    request.max_targets,
                ),
            ).fetchone()
            conn.commit()
            return {**dict(row), "site_name": site["name"]}

    def update_discovery_policy_state(
        self,
        context: AuthContext,
        policy_id: UUID,
        request: DiscoveryPolicyStateUpdate,
    ) -> dict:
        self._assert_active_tenant(context, request.tenant_id)
        if not self.enabled:
            self._assert_admin(None, context)
            now = datetime.now(timezone.utc)
            item = self.list_discovery_policies(context)[0]
            return {**item, "id": policy_id, "enabled": request.enabled, "updated_at": now}
        with self.base._connect() as conn:
            access = self._access(conn, context)
            self._assert_admin(access, context)
            policy = conn.execute(
                """
                select policy.*, site.name as site_name
                from public.discovery_policies policy
                join public.sites site
                  on site.tenant_id = policy.tenant_id and site.id = policy.site_id
                where policy.tenant_id = %s and policy.id = %s
                for update of policy
                """,
                (request.tenant_id, policy_id),
            ).fetchone()
            if not policy:
                raise ValueError("discovery policy not found in active tenant")
            if not policy["read_only"] or not policy["safe_mode"]:
                raise ValueError("discovery policy must remain read-only and in safe mode")
            row = conn.execute(
                """
                update public.discovery_policies
                set enabled = %s,
                    next_run_at = case
                      when %s then coalesce(next_run_at, timezone('utc', now()))
                      else null
                    end
                where tenant_id = %s and id = %s
                returning id, tenant_id, site_id, name, enabled, read_only, safe_mode,
                          allowed_networks::text[], denied_networks::text[],
                          coalesce(array(select host(value) from unnest(excluded_addresses) value), '{}') as excluded_addresses,
                          allowed_protocols, allowed_tcp_ports, frequency_minutes, concurrency,
                          timeout_ms, max_targets, last_run_at, next_run_at,
                          'real' as data_origin, created_at, updated_at
                """,
                (request.enabled, request.enabled, request.tenant_id, policy_id),
            ).fetchone()
            self.base.write_audit(
                conn,
                context,
                request.tenant_id,
                "discovery.policy.enabled" if request.enabled else "discovery.policy.disabled",
                "discovery_policy",
                policy_id,
                {
                    "enabled": request.enabled,
                    "readOnly": True,
                    "safeMode": True,
                    "allowedNetworks": [str(value) for value in policy["allowed_networks"]],
                },
            )
            conn.commit()
            return {**dict(row), "site_name": policy["site_name"]}

    def list_discovery_runs(self, context: AuthContext, limit: int = 100) -> list[dict]:
        if not self.enabled:
            self._assert_infrastructure_read(None, context)
            return []
        with self.base._connect() as conn:
            access = self._access(conn, context)
            self._assert_infrastructure_read(access, context)
            return list(
                conn.execute(
                    """
                    select run.*, policy.name as policy_name, 'real' as data_origin
                    from public.discovery_runs run
                    join public.discovery_policies policy
                      on policy.tenant_id = run.tenant_id and policy.id = run.policy_id
                    where run.tenant_id = %s
                    order by run.created_at desc
                    limit %s
                    """,
                    (context.tenant_id, limit),
                ).fetchall()
            )

    def create_discovery_run(self, context: AuthContext, request: DiscoveryRunCreate) -> dict:
        self._assert_active_tenant(context, request.tenant_id)
        if not self.enabled:
            raise ValueError("simulated discovery never scans a real network")
        with self.base._connect() as conn:
            access = self._access(conn, context)
            self._assert_admin(access, context)
            policy = conn.execute(
                """
                select id, site_id, name, enabled, read_only, safe_mode
                from public.discovery_policies
                where tenant_id = %s and id = %s
                """,
                (request.tenant_id, request.policy_id),
            ).fetchone()
            if not policy:
                raise ValueError("discovery policy not found in active tenant")
            if not policy["enabled"]:
                raise ValueError("discovery policy is disabled")
            if not policy["read_only"] or not policy["safe_mode"]:
                raise ValueError("discovery policy must remain read-only and in safe mode")
            actor_id = None
            try:
                actor_id = UUID(context.user_id)
            except ValueError:
                pass
            row = conn.execute(
                """
                insert into public.discovery_runs (tenant_id, site_id, policy_id, requested_by)
                values (%s, %s, %s, %s)
                returning *, %s as policy_name, 'real' as data_origin
                """,
                (request.tenant_id, policy["site_id"], request.policy_id, actor_id, policy["name"]),
            ).fetchone()
            conn.commit()
            return dict(row)

    @staticmethod
    def adapter_catalog() -> list[dict]:
        return [dict(item) for item in ADAPTER_CATALOG]

    def list_incidents(self, context: AuthContext, status: str | None = None) -> list[dict]:
        if not self.enabled:
            self._assert_infrastructure_read(None, context)
            return []
        with self.base._connect() as conn:
            access = self._access(conn, context)
            self._assert_infrastructure_read(access, context)
            params: list[object] = [context.tenant_id]
            status_filter = ""
            if status:
                status_filter = "and status = %s"
                params.append(status)
            return list(
                conn.execute(
                    f"""
                    select *
                    from public.incidents
                    where tenant_id = %s {status_filter}
                    order by last_occurred_at desc
                    limit 500
                    """,
                    tuple(params),
                ).fetchall()
            )

    def health(self) -> PlatformHealth:
        now = datetime.now(timezone.utc)
        if not self.enabled:
            return PlatformHealth(
                status="ok",
                service="vulcan-api",
                timestamp=now,
                dataOrigin="simulated",
                checks=[
                    DependencyCheck(
                        name="database",
                        status="disabled",
                        detail="Banco desativado por MOCK_DATA; resposta explicitamente simulada.",
                    )
                ],
            )
        started = perf_counter()
        try:
            with self.base._connect() as conn:
                row = conn.execute(
                    """
                    select
                      to_regclass('public.unified_events') is not null as events_ready,
                      to_regclass('public.infrastructure_assets') is not null as assets_ready,
                      (select count(*) from public.discovery_runs where status = 'queued') as queued_discovery
                    """
                ).fetchone()
            latency_ms = round((perf_counter() - started) * 1000, 2)
            foundation_ready = bool(row["events_ready"] and row["assets_ready"])
            checks = [
                DependencyCheck(
                    name="database",
                    status="ok",
                    detail="PostgreSQL respondeu à consulta de prontidão.",
                    latencyMs=latency_ms,
                ),
                DependencyCheck(
                    name="platform_schema",
                    status="ok" if foundation_ready else "unavailable",
                    detail="Schema da expansão aplicado." if foundation_ready else "Migration da expansão ainda não foi aplicada.",
                ),
                DependencyCheck(
                    name="discovery_queue",
                    status="ok",
                    detail=f"{row['queued_discovery']} execução(ões) aguardando worker.",
                ),
            ]
            return PlatformHealth(
                status="ok" if foundation_ready else "degraded",
                service="vulcan-api",
                timestamp=now,
                dataOrigin="real",
                checks=checks,
            )
        except Exception:
            return PlatformHealth(
                status="unavailable",
                service="vulcan-api",
                timestamp=now,
                dataOrigin="real",
                checks=[
                    DependencyCheck(
                        name="database",
                        status="unavailable",
                        detail="PostgreSQL não respondeu à verificação de prontidão.",
                    )
                ],
            )


def get_platform_repository() -> PlatformRepository:
    return PlatformRepository()
