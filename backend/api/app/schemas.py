from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(ApiModel):
    access_token: str = Field(alias="accessToken")
    token_type: str = Field(alias="tokenType")
    user: dict[str, Any]
    warning: str


class Tenant(ApiModel):
    id: UUID
    name: str
    slug: str
    plan: str
    region: str
    status: str


class Department(ApiModel):
    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    parent_department_id: UUID | None = Field(default=None, alias="parentDepartmentId")
    name: str
    slug: str
    description: str | None = None


class Role(ApiModel):
    id: UUID
    tenant_id: UUID | None = Field(default=None, alias="tenantId")
    slug: str
    name: str
    description: str | None = None
    scope: Literal["self", "hierarchy", "tenant", "global"]
    is_system: bool = Field(alias="isSystem")


class User(ApiModel):
    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    name: str
    email: str
    phone: str | None = None
    whatsapp: str | None = None
    title: str | None = None
    hierarchy_level: int | None = Field(default=None, alias="hierarchyLevel")
    manager_id: UUID | None = Field(default=None, alias="managerId")
    role: str
    status: str


class Membership(ApiModel):
    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    user_id: UUID = Field(alias="userId")
    role_id: UUID | None = Field(default=None, alias="roleId")
    department_id: UUID | None = Field(default=None, alias="departmentId")
    direct_manager_membership_id: UUID | None = Field(default=None, alias="directManagerMembershipId")
    status: str
    full_name: str = Field(alias="fullName")
    work_email: str | None = Field(default=None, alias="workEmail")
    phone: str | None = None
    whatsapp: str | None = None
    title: str | None = None
    hierarchy_level: int | None = Field(default=None, alias="hierarchyLevel")


class MembershipCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: UUID = Field(alias="tenantId")
    user_id: UUID = Field(alias="userId")
    role_id: UUID | None = Field(default=None, alias="roleId")
    department_id: UUID | None = Field(default=None, alias="departmentId")
    direct_manager_membership_id: UUID | None = Field(default=None, alias="directManagerMembershipId")
    full_name: str = Field(alias="fullName", min_length=1)
    work_email: str | None = Field(default=None, alias="workEmail")
    phone: str | None = None
    whatsapp: str | None = None
    title: str | None = None
    hierarchy_level: int | None = Field(default=None, alias="hierarchyLevel")


class MembershipUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    role_id: UUID | None = Field(default=None, alias="roleId")
    department_id: UUID | None = Field(default=None, alias="departmentId")
    direct_manager_membership_id: UUID | None = Field(default=None, alias="directManagerMembershipId")
    status: str | None = None
    full_name: str | None = Field(default=None, alias="fullName")
    work_email: str | None = Field(default=None, alias="workEmail")
    phone: str | None = None
    whatsapp: str | None = None
    title: str | None = None
    hierarchy_level: int | None = Field(default=None, alias="hierarchyLevel")


class MembershipManagerUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    direct_manager_membership_id: UUID | None = Field(default=None, alias="directManagerMembershipId")


class Device(ApiModel):
    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    owner_membership_id: UUID | None = Field(default=None, alias="ownerMembershipId")
    owner: str
    hostname: str
    os: str
    status: str
    last_seen_at: str = Field(alias="lastSeenAt")
    collection_quality: str | None = Field(default=None, alias="collectionQuality")
    queue_depth: int | None = Field(default=None, alias="queueDepth")
    last_error: str | None = Field(default=None, alias="lastError")
    local_ip: str | None = Field(default=None, alias="localIp")
    agent_version: str | None = Field(default=None, alias="agentVersion")


class DeviceOwnerUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: UUID = Field(alias="tenantId")
    owner_membership_id: UUID | None = Field(default=None, alias="ownerMembershipId")


class ActivityEvent(ApiModel):
    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    event_type: str = Field(alias="eventType")
    app_name: str = Field(alias="appName")
    department: str
    occurred_at: str = Field(alias="occurredAt")
    duration_minutes: int = Field(alias="durationMinutes")


class ActivityEventCreate(BaseModel):
    tenant_id: UUID = Field(alias="tenantId")
    user_id: UUID | None = Field(default=None, alias="userId")
    membership_id: UUID | None = Field(default=None, alias="membershipId")
    device_id: UUID | None = Field(default=None, alias="deviceId")
    app_name: str = Field(alias="appName", min_length=1)
    window_title: str | None = Field(default=None, alias="windowTitle")
    category: str | None = None
    started_at: datetime = Field(alias="startedAt")
    ended_at: datetime = Field(alias="endedAt")
    duration_seconds: int = Field(alias="durationSeconds", ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActivityEventCreateResponse(ApiModel):
    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    metric_updated: bool = Field(alias="metricUpdated")


class AgentStatusResponse(ApiModel):
    status: str
    service: str
    version: str
    enrollment_enabled: bool = Field(alias="enrollmentEnabled")


class AgentEnrollRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: UUID = Field(alias="tenantId")
    enrollment_token: str = Field(alias="enrollmentToken", min_length=8)
    hostname: str = Field(min_length=1)
    os_user: str | None = Field(default=None, alias="osUser")
    os_version: str | None = Field(default=None, alias="osVersion")
    device_id: UUID | None = Field(default=None, alias="deviceId")
    machine_fingerprint: str = Field(alias="machineFingerprint", min_length=6)
    agent_version: str = Field(alias="agentVersion")
    linked_user: str | None = Field(default=None, alias="linkedUser")
    user_id: UUID | None = Field(default=None, alias="userId")
    membership_id: UUID | None = Field(default=None, alias="membershipId")
    role_level: str | None = Field(default=None, alias="roleLevel")
    department: str | None = None
    manager_membership_id: UUID | None = Field(default=None, alias="managerMembershipId")
    note: str | None = None


class AgentEnrollResponse(ApiModel):
    accepted: bool
    tenant_id: UUID = Field(alias="tenantId")
    device_id: UUID = Field(alias="deviceId")
    heartbeat_interval_seconds: int = Field(alias="heartbeatIntervalSeconds")
    sync_interval_seconds: int = Field(alias="syncIntervalSeconds")


class AgentHeartbeatRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: UUID = Field(alias="tenantId")
    enrollment_token: str = Field(alias="enrollmentToken", min_length=8)
    device_id: UUID | None = Field(default=None, alias="deviceId")
    machine_fingerprint: str = Field(alias="machineFingerprint", min_length=6)
    hostname: str = Field(min_length=1)
    agent_version: str = Field(alias="agentVersion")
    status: str = "online"
    queue_depth: int = Field(default=0, alias="queueDepth")
    last_error: str | None = Field(default=None, alias="lastError")
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentHeartbeatResponse(ApiModel):
    accepted: bool
    server_time: datetime = Field(alias="serverTime")


class AgentEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: str = Field(alias="eventId")
    event_type: str = Field(default="app_focus_ended", alias="eventType")
    app_name: str = Field(alias="appName", min_length=1)
    window_title: str | None = Field(default=None, alias="windowTitle")
    category: str | None = None
    started_at: datetime = Field(alias="startedAt")
    ended_at: datetime = Field(alias="endedAt")
    duration_seconds: int = Field(alias="durationSeconds", ge=0)
    os_user: str | None = Field(default=None, alias="osUser")
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentEventsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: UUID = Field(alias="tenantId")
    enrollment_token: str = Field(alias="enrollmentToken", min_length=8)
    device_id: UUID | None = Field(default=None, alias="deviceId")
    membership_id: UUID | None = Field(default=None, alias="membershipId")
    machine_fingerprint: str = Field(alias="machineFingerprint", min_length=6)
    hostname: str = Field(min_length=1)
    events: list[AgentEvent] = Field(default_factory=list)


class AgentEventsResponse(ApiModel):
    accepted: bool
    received: int
    stored: int


class AgentLogEntry(BaseModel):
    level: str
    message: str
    created_at: datetime = Field(alias="createdAt")
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentLogsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: UUID = Field(alias="tenantId")
    enrollment_token: str = Field(alias="enrollmentToken", min_length=8)
    device_id: UUID | None = Field(default=None, alias="deviceId")
    machine_fingerprint: str = Field(alias="machineFingerprint", min_length=6)
    logs: list[AgentLogEntry] = Field(default_factory=list)


class Metric(ApiModel):
    id: str
    label: str
    value: str
    trend: str
    tone: Literal["positive", "warning", "critical", "neutral"]


class OperationalMetric(ApiModel):
    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    membership_id: UUID | None = Field(default=None, alias="membershipId")
    department_id: UUID | None = Field(default=None, alias="departmentId")
    metric_key: str = Field(alias="metricKey")
    metric_label: str = Field(alias="metricLabel")
    value_numeric: float | None = Field(default=None, alias="valueNumeric")
    value_text: str | None = Field(default=None, alias="valueText")
    period_start: datetime = Field(alias="periodStart")
    period_end: datetime = Field(alias="periodEnd")


class OperationalAppBreakdown(ApiModel):
    app: str
    category: str
    active_seconds: float = Field(alias="activeSeconds")
    idle_seconds: float = Field(alias="idleSeconds")
    events: int
    context_switches: int = Field(alias="contextSwitches")
    percent: float
    last_seen_at: datetime | None = Field(default=None, alias="lastSeenAt")
    focus_label: str = Field(alias="focusLabel")


class OperationalWindowBreakdown(ApiModel):
    title: str
    app: str
    active_seconds: float = Field(alias="activeSeconds")
    events: int
    percent: float
    collection_note: str = Field(alias="collectionNote")


class OperationalTimelinePoint(ApiModel):
    label: str
    active_seconds: float = Field(alias="activeSeconds")
    idle_seconds: float = Field(alias="idleSeconds")
    unidentified_seconds: float = Field(default=0.0, alias="unidentifiedSeconds")
    context_switches: int = Field(alias="contextSwitches")
    events: int


class OperationalQualitySignal(ApiModel):
    device: str
    quality: str
    message: str
    last_seen_at: str | None = Field(default=None, alias="lastSeenAt")


class OperationalIntelligence(ApiModel):
    generated_at: datetime = Field(alias="generatedAt")
    period_label: str = Field(alias="periodLabel")
    total_events: int = Field(alias="totalEvents")
    total_active_seconds: float = Field(alias="totalActiveSeconds")
    total_idle_seconds: float = Field(alias="totalIdleSeconds")
    unidentified_seconds: float = Field(default=0.0, alias="unidentifiedSeconds")
    tracked_seconds: float = Field(alias="trackedSeconds")
    idle_rate: float = Field(alias="idleRate")
    focus_score: int = Field(alias="focusScore")
    distraction_score: int = Field(alias="distractionScore")
    context_switches: int = Field(alias="contextSwitches")
    context_switches_per_hour: float = Field(alias="contextSwitchesPerHour")
    longest_focus_seconds: float = Field(alias="longestFocusSeconds")
    fragmented_seconds: float = Field(alias="fragmentedSeconds")
    current_activity: str = Field(alias="currentActivity")
    ai_summary: str = Field(alias="aiSummary")
    ai_recommendations: list[str] = Field(alias="aiRecommendations")
    top_apps: list[OperationalAppBreakdown] = Field(alias="topApps")
    top_windows: list[OperationalWindowBreakdown] = Field(alias="topWindows")
    timeline: list[OperationalTimelinePoint]
    quality_signals: list[OperationalQualitySignal] = Field(alias="qualitySignals")


class Insight(ApiModel):
    id: str
    title: str
    impact: Literal["high", "medium", "low"]
    summary: str
    recommendation: str
    automation_savings_hours: int = Field(alias="automationSavingsHours")


class Notification(ApiModel):
    id: str
    tenant_id: UUID | None = Field(default=None, alias="tenantId")
    channel: Literal["system", "push", "windows", "whatsapp", "email"]
    status: Literal["queued", "sent", "failed", "ready", "mocked", "missing_credentials", "disabled"]
    title: str
    message: str
    recipient: str | None = None
    recipient_membership_id: UUID | None = Field(default=None, alias="recipientMembershipId")
    notification_type: str | None = Field(default=None, alias="notificationType")
    attempts: int = 0
    error: str | None = None
    created_at: str = Field(alias="createdAt")


class NotificationPreference(ApiModel):
    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    membership_id: UUID = Field(alias="membershipId")
    channel: Literal["system", "push", "windows", "whatsapp", "email"]
    notification_type: str = Field(alias="notificationType")
    enabled: bool


class NotificationPreferenceUpdate(BaseModel):
    enabled: bool


class NotificationSendRequest(BaseModel):
    tenant_id: UUID = Field(alias="tenantId")
    channel: Literal["system", "push", "windows", "whatsapp", "email"]
    notification_type: str = Field(alias="notificationType")
    title: str
    message: str
    recipient_membership_id: UUID | None = Field(default=None, alias="recipientMembershipId")


class NotificationSendResponse(ApiModel):
    id: UUID | None = None
    channel: str
    status: str
    provider_result: str = Field(alias="providerResult")


class ConnectionTestRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: UUID = Field(alias="tenantId")
    provider: str | None = None
    destination: str | None = None
    message: str | None = None


class ConnectionTestResponse(ApiModel):
    ok: bool
    status: str
    provider_result: str = Field(alias="providerResult")
    message: str


class IntegrationStatus(ApiModel):
    name: str
    provider: str
    configured: bool
    status: str
    mode: str
    last_checked_at: datetime = Field(alias="lastCheckedAt")
    required_items: list[str] = Field(alias="requiredItems")
    details: dict[str, Any] = Field(default_factory=dict)


class WhatsAppStatus(ApiModel):
    root_channel_enabled: bool = Field(alias="rootChannelEnabled")
    root_channel_name: str = Field(alias="rootChannelName")
    root_channel_number: str | None = Field(default=None, alias="rootChannelNumber")
    provider: str
    connected: bool
    status: str
    qr_required: bool = Field(alias="qrRequired")
    qr_code: str | None = Field(default=None, alias="qrCode")
    last_connection_at: datetime | None = Field(default=None, alias="lastConnectionAt")
    last_sync_at: datetime | None = Field(default=None, alias="lastSyncAt")
    logs: list[str]


class EmailProviderStatusResponse(ApiModel):
    provider: str
    configured: bool
    can_send: bool = Field(alias="canSend")
    can_read: bool = Field(alias="canRead")
    status: str
    message: str
    required_items: list[str] = Field(alias="requiredItems")
    last_checked_at: datetime = Field(alias="lastCheckedAt")


class NotificationSchedule(ApiModel):
    id: str
    name: str
    recurrence: str
    timezone: str
    days_of_week: list[str] = Field(alias="daysOfWeek")
    times: list[str]
    report_type: str = Field(alias="reportType")
    recipients: list[str]
    channels: list[str]
    enabled: bool


class ReportTemplate(ApiModel):
    id: str
    name: str
    description: str
    cadence: str
    channels: list[str]
    enabled: bool


class HierarchyNode(ApiModel):
    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    user_id: UUID | None = Field(default=None, alias="userId")
    parent_id: UUID | None = Field(default=None, alias="parentId")
    name: str
    title: str
    department: str
    email: str
    phone: str | None = None
    whatsapp: str | None = None
    hierarchy_level: int = Field(alias="hierarchyLevel")
    direct_reports: int = Field(alias="directReports")
    visible_scope: Literal["self", "subtree", "tenant", "global"] = Field(alias="visibleScope")


class AnalyzeRequest(BaseModel):
    tenant_id: UUID = Field(alias="tenantId")
    facts: list[dict[str, Any]] = Field(min_length=1)
    complexity: Literal["operational", "executive", "critical"] = "operational"


class AnalyzeResponse(ApiModel):
    route: Literal["llama", "gpt"]
    model: str
    summary: str
    recommendations: list[str]


class AIStatus(ApiModel):
    provider: str
    openai_configured: bool = Field(alias="openaiConfigured")
    llama_configured: bool = Field(alias="llamaConfigured")
    llama_provider: str = Field(alias="llamaProvider")
    complex_model: str = Field(alias="complexModel")
    operational_model: str = Field(alias="operationalModel")
    route_policy: str = Field(alias="routePolicy")


class CopilotRequest(BaseModel):
    tenant_id: UUID = Field(alias="tenantId")
    message: str
    context: dict[str, Any] = Field(default_factory=dict)


class CopilotResponse(ApiModel):
    route: Literal["gpt"]
    model: str
    answer: str


class SupabaseStatus(ApiModel):
    configured: bool
    project_ref: str | None = Field(alias="projectRef")
    url_configured: bool = Field(alias="urlConfigured")
    rest_url_configured: bool = Field(alias="restUrlConfigured")
    publishable_key_configured: bool = Field(alias="publishableKeyConfigured")
    anon_key_configured: bool = Field(alias="anonKeyConfigured")
    service_role_configured: bool = Field(alias="serviceRoleConfigured")
    database_url_configured: bool = Field(alias="databaseUrlConfigured")
    rest_reachable: bool | None = Field(alias="restReachable")
    auth_provider: str = Field(alias="authProvider")
    required_items: list[str] = Field(alias="requiredItems")


class AIProviderConfig(ApiModel):
    id: UUID
    tenant_id: UUID | None = Field(default=None, alias="tenantId")
    provider: Literal["openai", "ollama", "openrouter", "together", "groq"]
    purpose: Literal["operational", "executive", "copilot"]
    model: str
    base_url: str | None = Field(default=None, alias="baseUrl")
    enabled: bool


class AuditLog(ApiModel):
    id: UUID
    tenant_id: UUID | None = Field(default=None, alias="tenantId")
    actor_user_id: UUID | None = Field(default=None, alias="actorUserId")
    action: str
    resource_type: str = Field(alias="resourceType")
    resource_id: UUID | None = Field(default=None, alias="resourceId")
    created_at: datetime = Field(alias="createdAt")


class HealthResponse(ApiModel):
    status: str
    service: str
    product: str
    timestamp: datetime
