from __future__ import annotations

from datetime import datetime
from ipaddress import ip_address, ip_network
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class PlatformModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


class TenantModule(PlatformModel):
    id: UUID
    tenant_id: UUID
    module_key: str
    enabled: bool
    plan_source: str
    limits: dict[str, Any] = Field(default_factory=dict)
    enabled_at: datetime | None = None


class ScoreComponent(PlatformModel):
    key: str
    label: str
    value: float
    max_points: float
    points: float
    formula: str


class InfrastructureOverview(PlatformModel):
    tenant_id: UUID
    data_origin: Literal["real", "simulated"]
    generated_at: datetime
    sites: int
    networks: int
    assets: int
    online_assets: int
    degraded_assets: int
    offline_assets: int
    unknown_assets: int
    open_incidents: int
    events_last_24h: int
    pending_discoveries: int
    health_score: int | None
    score_components: list[ScoreComponent] = Field(default_factory=list)


class SiteCreate(PlatformModel):
    tenant_id: UUID
    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
    name: str = Field(min_length=2, max_length=160)
    slug: str | None = Field(default=None, min_length=2, max_length=160, pattern=r"^[a-z0-9][a-z0-9-]*$")
    description: str | None = Field(default=None, max_length=1000)
    city: str | None = Field(default=None, max_length=160)
    state: str | None = Field(default=None, min_length=2, max_length=80)
    address: dict[str, Any] = Field(default_factory=dict)
    timezone: str = Field(default="America/Sao_Paulo", min_length=3, max_length=80)
    display_order: int = Field(default=0, ge=0, le=10000)
    semantic_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    rotation_enabled: bool = True
    rotation_seconds: int = Field(default=30, ge=10, le=3600)
    visible: bool = True
    tags: list[str] = Field(default_factory=list, max_length=50)


class SiteUpdate(PlatformModel):
    tenant_id: UUID
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    city: str | None = Field(default=None, max_length=160)
    state: str | None = Field(default=None, min_length=2, max_length=80)
    timezone: str | None = Field(default=None, min_length=3, max_length=80)
    status: Literal["active", "maintenance", "inactive"] | None = None
    display_order: int | None = Field(default=None, ge=0, le=10000)
    semantic_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    rotation_enabled: bool | None = None
    rotation_seconds: int | None = Field(default=None, ge=10, le=3600)
    visible: bool | None = None
    tags: list[str] | None = Field(default=None, max_length=50)


class Site(PlatformModel):
    id: UUID
    tenant_id: UUID
    code: str
    slug: str
    name: str
    description: str | None = None
    city: str | None = None
    state: str | None = None
    address: dict[str, Any] = Field(default_factory=dict)
    timezone: str
    status: str
    display_order: int
    semantic_color: str | None = None
    rotation_enabled: bool
    rotation_seconds: int
    visible: bool
    tags: list[str] = Field(default_factory=list)
    source: str = "manual"
    data_origin: Literal["real", "simulated", "imported"] = "real"
    created_at: datetime
    updated_at: datetime


class InfrastructureNetworkCreate(PlatformModel):
    tenant_id: UUID
    site_id: UUID
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    network_cidr: str
    gateway: str | None = None
    vlan_id: int | None = Field(default=None, ge=1, le=4094)
    dns_servers: list[str] = Field(default_factory=list, max_length=8)
    dhcp_enabled: bool = False
    discovery_allowed: bool = False
    tags: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_network(self) -> "InfrastructureNetworkCreate":
        network = ip_network(self.network_cidr, strict=True)
        if self.gateway and ip_address(self.gateway) not in network:
            raise ValueError("gateway must belong to networkCidr")
        for server in self.dns_servers:
            ip_address(server)
        return self


class InfrastructureNetwork(PlatformModel):
    id: UUID
    tenant_id: UUID
    site_id: UUID
    site_name: str | None = None
    name: str
    description: str | None = None
    network_cidr: str
    gateway: str | None = None
    vlan_id: int | None = None
    dns_servers: list[str] = Field(default_factory=list)
    dhcp_enabled: bool
    discovery_allowed: bool
    status: str
    tags: list[str] = Field(default_factory=list)
    source: str = "manual"
    source_key: str | None = None
    data_origin: Literal["real", "simulated", "imported"] = "real"
    created_at: datetime
    updated_at: datetime


AssetType = Literal[
    "workstation",
    "server",
    "switch",
    "access_point",
    "firewall",
    "printer",
    "ups",
    "controller",
    "gateway",
    "service",
    "application",
    "storage",
    "virtual_machine",
    "container",
    "proxmox_cluster",
    "virtualization_host",
    "backup_server",
    "backup_job",
    "wan_link",
    "vpn_tunnel",
    "nat_service",
    "network_service",
    "other",
]


class AssetCreate(PlatformModel):
    tenant_id: UUID
    site_id: UUID | None = None
    network_id: UUID | None = None
    parent_asset_id: UUID | None = None
    owner_membership_id: UUID | None = None
    department_id: UUID | None = None
    asset_type: AssetType
    name: str = Field(min_length=2, max_length=200)
    hostname: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    manufacturer: str | None = Field(default=None, max_length=160)
    model: str | None = Field(default=None, max_length=160)
    serial_number: str | None = Field(default=None, max_length=255)
    asset_tag: str | None = Field(default=None, max_length=120)
    ip_address: str | None = None
    mac_address: str | None = Field(default=None, pattern=r"(?i)^([0-9a-f]{2}[:-]){5}[0-9a-f]{2}$")
    operating_system: str | None = Field(default=None, max_length=255)
    status: Literal["online", "degraded", "offline", "unknown", "maintenance", "retired"] = "unknown"
    criticality: Literal["low", "medium", "high", "critical"] = "medium"
    responsible: str | None = Field(default=None, max_length=255)
    physical_location: str | None = Field(default=None, max_length=255)
    rack: str | None = Field(default=None, max_length=80)
    rack_position: str | None = Field(default=None, max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=50)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, value: str | None) -> str | None:
        if value:
            ip_address(value)
        return value

    @field_validator("mac_address")
    @classmethod
    def normalize_mac_address(cls, value: str | None) -> str | None:
        return value.replace("-", ":").lower() if value else value


class Asset(PlatformModel):
    id: UUID
    tenant_id: UUID
    site_id: UUID | None = None
    site_name: str | None = None
    network_id: UUID | None = None
    network_name: str | None = None
    parent_asset_id: UUID | None = None
    owner_membership_id: UUID | None = None
    department_id: UUID | None = None
    endpoint_device_id: UUID | None = None
    asset_type: str
    name: str
    hostname: str | None = None
    description: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    asset_tag: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    operating_system: str | None = None
    status: str
    criticality: str
    lifecycle_state: str
    responsible: str | None = None
    physical_location: str | None = None
    rack: str | None = None
    rack_position: str | None = None
    tags: list[str] = Field(default_factory=list)
    source: str
    source_key: str | None = None
    confidence: float | None = None
    discovered_at: datetime | None = None
    last_seen_at: datetime | None = None
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    data_origin: Literal["real", "simulated", "imported"] = "real"
    created_at: datetime
    updated_at: datetime


class TimelineEvent(PlatformModel):
    event_id: UUID
    tenant_id: UUID
    schema_version: str
    site_id: UUID | None = None
    asset_id: UUID | None = None
    agent_id: UUID | None = None
    source: str
    source_type: str
    source_event_id: str
    event_type: str
    category: str
    severity: str
    occurred_at: datetime
    device_occurred_at: datetime | None = None
    received_at: datetime
    clock_drift_ms: int | None = None
    offline_buffered: bool
    actor: dict[str, Any] = Field(default_factory=dict)
    device: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    message: str
    technical_message: str | None = None
    fingerprint: str
    correlation_id: str | None = None
    causation_id: str | None = None
    confidence: float | None = None
    privacy_classification: str
    retention_policy: str
    trusted_origin: bool
    data_origin: Literal["real", "simulated", "imported"]
    extensions: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class TimelinePage(PlatformModel):
    items: list[TimelineEvent]
    next_cursor: str | None = None
    has_more: bool
    data_origin: Literal["real", "simulated"]


class CanonicalEventCreate(PlatformModel):
    event_id: UUID
    tenant_id: UUID
    schema_version: Literal["2026-07-vulcan-event.v1"] = "2026-07-vulcan-event.v1"
    site_id: UUID | None = None
    asset_id: UUID | None = None
    agent_id: UUID | None = None
    source: str = Field(min_length=1, max_length=128)
    source_type: str = Field(min_length=1, max_length=64)
    source_event_id: str = Field(min_length=1, max_length=256)
    event_type: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=80)
    severity: Literal["debug", "info", "notice", "warning", "error", "critical"] = "info"
    occurred_at: datetime
    device_occurred_at: datetime | None = None
    offline_buffered: bool = False
    actor: dict[str, Any] = Field(default_factory=dict)
    device: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    message: str = Field(min_length=1, max_length=2000)
    technical_message: str | None = Field(default=None, max_length=4000)
    fingerprint: str | None = Field(default=None, max_length=256)
    correlation_id: str | None = Field(default=None, max_length=256)
    causation_id: str | None = Field(default=None, max_length=256)
    confidence: float | None = Field(default=None, ge=0, le=1)
    privacy_classification: Literal["public", "operational", "personal", "sensitive", "restricted"] = "operational"
    retention_policy: str = Field(default="standard", min_length=1, max_length=80)
    data_origin: Literal["real", "simulated", "imported"] = "real"
    extensions: dict[str, Any] = Field(default_factory=dict)

    @field_validator("occurred_at", "device_occurred_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("event timestamps must include a timezone")
        return value


class CanonicalEventResult(PlatformModel):
    accepted: bool
    duplicate: bool
    event: TimelineEvent


class EventSimulationRequest(PlatformModel):
    tenant_id: UUID
    scenario: Literal["workforce_infrastructure_impact", "network_instability", "service_degradation"] = (
        "workforce_infrastructure_impact"
    )
    count: int = Field(default=4, ge=1, le=20)


class EventSimulationResponse(PlatformModel):
    generated: int
    scenario: str
    data_origin: Literal["simulated"] = "simulated"
    events: list[TimelineEvent]


class DiscoveryPolicyCreate(PlatformModel):
    tenant_id: UUID
    site_id: UUID
    name: str = Field(min_length=2, max_length=160)
    enabled: bool = False
    allowed_networks: list[str] = Field(min_length=1, max_length=32)
    denied_networks: list[str] = Field(default_factory=list, max_length=32)
    excluded_addresses: list[str] = Field(default_factory=list, max_length=256)
    allowed_protocols: list[
        Literal["icmp", "dns", "reverse_dns", "arp", "tcp_connect", "snmp", "lldp", "cdp"]
    ] = Field(default_factory=lambda: ["icmp", "dns"])
    allowed_tcp_ports: list[int] = Field(default_factory=list, max_length=32)
    frequency_minutes: int = Field(default=60, ge=5, le=10080)
    concurrency: int = Field(default=8, ge=1, le=32)
    timeout_ms: int = Field(default=750, ge=100, le=10000)
    max_targets: int = Field(default=256, ge=1, le=4096)

    @model_validator(mode="after")
    def validate_scope(self) -> "DiscoveryPolicyCreate":
        networks = [ip_network(value, strict=True) for value in self.allowed_networks]
        [ip_network(value, strict=True) for value in self.denied_networks]
        [ip_address(value) for value in self.excluded_addresses]
        if sum(max(network.num_addresses - 2, 1) for network in networks) > self.max_targets:
            raise ValueError("allowedNetworks exceed maxTargets")
        if any(port < 1 or port > 65535 for port in self.allowed_tcp_ports):
            raise ValueError("allowedTcpPorts must be between 1 and 65535")
        if self.allowed_tcp_ports and "tcp_connect" not in self.allowed_protocols:
            raise ValueError("tcp_connect must be allowed when allowedTcpPorts are configured")
        return self


class DiscoveryPolicy(PlatformModel):
    id: UUID
    tenant_id: UUID
    site_id: UUID
    site_name: str | None = None
    name: str
    enabled: bool
    read_only: bool
    safe_mode: bool
    allowed_networks: list[str]
    denied_networks: list[str]
    excluded_addresses: list[str]
    allowed_protocols: list[str]
    allowed_tcp_ports: list[int]
    frequency_minutes: int
    concurrency: int
    timeout_ms: int
    max_targets: int
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    data_origin: Literal["real", "simulated"] = "real"
    created_at: datetime
    updated_at: datetime


class DiscoveryPolicyStateUpdate(PlatformModel):
    tenant_id: UUID
    enabled: bool


class DiscoveryRunCreate(PlatformModel):
    tenant_id: UUID
    policy_id: UUID


class DiscoveryRun(PlatformModel):
    id: UUID
    tenant_id: UUID
    site_id: UUID
    policy_id: UUID
    policy_name: str | None = None
    status: str
    mode: Literal["read_only"]
    started_at: datetime | None = None
    finished_at: datetime | None = None
    targets_planned: int
    targets_scanned: int
    findings_count: int
    error_count: int
    error_summary: str | None = None
    result_summary: dict[str, Any] = Field(default_factory=dict)
    data_origin: Literal["real", "simulated"] = "real"
    created_at: datetime
    updated_at: datetime


class IntegrationAdapterDefinition(PlatformModel):
    adapter_type: str
    name: str
    description: str
    capabilities: list[str]
    read_only: bool
    implemented: bool


class Incident(PlatformModel):
    id: UUID
    tenant_id: UUID
    site_id: UUID | None = None
    title: str
    summary: str
    impact: str
    severity: str
    status: str
    probable_cause: str | None = None
    confidence: float | None = None
    recommendation: str | None = None
    affected_entities: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    first_occurred_at: datetime
    last_occurred_at: datetime
    resolution: str | None = None
    resolved_at: datetime | None = None
    source: str
    created_at: datetime
    updated_at: datetime


class WallboardPlaylistItem(PlatformModel):
    id: UUID
    tenant_id: UUID
    playlist_id: UUID
    site_id: UUID | None = None
    site_name: str | None = None
    panel_key: str
    title: str
    position: int
    duration_seconds: int | None = None
    enabled: bool
    config: dict[str, Any] = Field(default_factory=dict)


class WallboardPlaylist(PlatformModel):
    id: UUID
    tenant_id: UUID
    profile_id: UUID
    slug: str
    name: str
    enabled: bool
    rotation_enabled: bool
    default_duration_seconds: int
    transition: Literal["none", "fade", "slide"]
    schedule: dict[str, Any] = Field(default_factory=dict)
    alert_priority_enabled: bool
    auto_return_seconds: int
    items: list[WallboardPlaylistItem] = Field(default_factory=list)


class WallboardProfile(PlatformModel):
    id: UUID
    tenant_id: UUID
    site_id: UUID | None = None
    site_name: str | None = None
    slug: str
    name: str
    wallboard_type: Literal["workforce", "infrastructure"]
    view_mode: str
    enabled: bool
    refresh_seconds: int
    fullscreen: bool
    night_mode: bool
    burn_in_prevention: bool
    show_clock: bool
    show_last_update: bool
    show_connection_status: bool
    config: dict[str, Any] = Field(default_factory=dict)
    playlists: list[WallboardPlaylist] = Field(default_factory=list)


class WallboardProfileUpdate(PlatformModel):
    tenant_id: UUID
    name: str | None = Field(default=None, min_length=2, max_length=120)
    enabled: bool | None = None
    refresh_seconds: int | None = Field(default=None, ge=5, le=3600)
    fullscreen: bool | None = None
    night_mode: bool | None = None
    burn_in_prevention: bool | None = None
    show_clock: bool | None = None
    show_last_update: bool | None = None
    show_connection_status: bool | None = None
    config: dict[str, Any] | None = None


class WallboardPlaylistUpdate(PlatformModel):
    tenant_id: UUID
    enabled: bool | None = None
    rotation_enabled: bool | None = None
    default_duration_seconds: int | None = Field(default=None, ge=10, le=3600)
    transition: Literal["none", "fade", "slide"] | None = None
    schedule: dict[str, Any] | None = None
    alert_priority_enabled: bool | None = None
    auto_return_seconds: int | None = Field(default=None, ge=10, le=86400)


class WallboardPlaylistItemUpdate(PlatformModel):
    id: UUID
    position: int = Field(ge=0)
    duration_seconds: int | None = Field(default=None, ge=10, le=3600)
    enabled: bool = True


class WallboardPlaylistItemsUpdate(PlatformModel):
    tenant_id: UUID
    items: list[WallboardPlaylistItemUpdate] = Field(min_length=1, max_length=100)


class WallboardApplication(PlatformModel):
    name: str
    category: str
    active_seconds: int
    events: int
    last_seen_at: datetime


class WallboardAgent(PlatformModel):
    id: UUID
    hostname: str
    profile: Literal["workstation", "server", "collector"]
    operating_system: str
    agent_version: str | None = None
    effective_status: Literal["online", "delayed", "offline", "pending"]
    queue_depth: int
    policy_status: str
    site_id: UUID | None = None
    site_name: str | None = None
    last_seen_at: datetime | None = None


class WallboardTopologyNode(PlatformModel):
    id: UUID
    site_id: UUID | None = None
    site_name: str | None = None
    name: str
    asset_type: str
    status: str
    criticality: str
    source: str
    ip_address: str | None = None
    last_seen_at: datetime | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class WallboardTopologyLink(PlatformModel):
    id: UUID
    source_asset_id: UUID
    target_asset_id: UUID
    relationship_type: str
    status: str
    confidence: float
    source: str
    observed_at: datetime | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class WallboardSnapshot(PlatformModel):
    tenant_id: UUID
    wallboard_type: Literal["workforce", "infrastructure"]
    data_origin: Literal["real"]
    generated_at: datetime
    site_id: UUID | None = None
    site_name: str | None = None
    kpis: dict[str, int | float | str | None] = Field(default_factory=dict)
    sites: list[dict[str, Any]] = Field(default_factory=list)
    status_groups: list[dict[str, Any]] = Field(default_factory=list)
    activity: list[dict[str, Any]] = Field(default_factory=list)
    alerts: list[dict[str, Any]] = Field(default_factory=list)
    integrations: list[dict[str, Any]] = Field(default_factory=list)
    applications: list[WallboardApplication] = Field(default_factory=list)
    agents: list[WallboardAgent] = Field(default_factory=list)
    topology_nodes: list[WallboardTopologyNode] = Field(default_factory=list)
    topology_links: list[WallboardTopologyLink] = Field(default_factory=list)


class IntegrationSyncResult(PlatformModel):
    adapter_type: str
    status: Literal["ok", "degraded", "unavailable"]
    data_origin: Literal["real"]
    observed_at: datetime
    assets_seen: int = 0
    assets_updated: int = 0
    relationships_updated: int = 0
    warnings: list[str] = Field(default_factory=list)


class DependencyCheck(PlatformModel):
    name: str
    status: Literal["ok", "degraded", "unavailable", "disabled"]
    detail: str
    latency_ms: float | None = None


class PlatformHealth(PlatformModel):
    status: Literal["ok", "degraded", "unavailable"]
    service: str
    timestamp: datetime
    checks: list[DependencyCheck]
    data_origin: Literal["real", "simulated"]


class VersionInfo(PlatformModel):
    product: Literal["Vulcan"] = "Vulcan"
    service: str
    version: str
    commit: str
    build: str
    event_schema_version: Literal["2026-07-vulcan-event.v1"] = "2026-07-vulcan-event.v1"
