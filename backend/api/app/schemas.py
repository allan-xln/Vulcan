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
    user_id: UUID | None = Field(default=None, alias="userId")
    username: str | None = Field(default=None, min_length=3)
    password: str | None = Field(default=None, min_length=4)
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

    username: str | None = Field(default=None, min_length=3)
    password: str | None = Field(default=None, min_length=4)
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
    os_user: str | None = Field(default=None, alias="osUser")
    adoption_status: str | None = Field(default=None, alias="adoptionStatus")
    adoption_code: str | None = Field(default=None, alias="adoptionCode")
    team_id: UUID | None = Field(default=None, alias="teamId")
    team_name: str | None = Field(default=None, alias="teamName")


class DeviceOwnerUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: UUID = Field(alias="tenantId")
    owner_membership_id: UUID | None = Field(default=None, alias="ownerMembershipId")


class Team(ApiModel):
    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    name: str
    description: str | None = None
    color: str
    members_count: int = Field(default=0, alias="membersCount")
    devices_count: int = Field(default=0, alias="devicesCount")
    active_seconds: float = Field(default=0, alias="activeSeconds")
    idle_seconds: float = Field(default=0, alias="idleSeconds")


class TeamCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: UUID = Field(alias="tenantId")
    name: str = Field(min_length=2)
    description: str | None = None
    color: str = "#f97316"


class TeamUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, min_length=2)
    description: str | None = None
    color: str | None = None
    status: str | None = None


class TeamMember(ApiModel):
    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    team_id: UUID = Field(alias="teamId")
    membership_id: UUID = Field(alias="membershipId")
    role_in_team: str = Field(alias="roleInTeam")
    member_name: str = Field(alias="memberName")
    member_title: str | None = Field(default=None, alias="memberTitle")


class TeamMemberCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: UUID = Field(alias="tenantId")
    membership_id: UUID = Field(alias="membershipId")
    role_in_team: str = Field(default="membro", alias="roleInTeam")


class DeviceAdoptionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: UUID = Field(alias="tenantId")
    mode: Literal["existing_user", "new_user", "dry"] = "existing_user"
    membership_id: UUID | None = Field(default=None, alias="membershipId")
    team_id: UUID | None = Field(default=None, alias="teamId")
    policy: str = "standard"
    user: MembershipCreate | None = None


class DeviceAdoptionResponse(ApiModel):
    device: Device
    membership: Membership | None = None
    team: Team | None = None
    adopted: bool


class DeviceMoveRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: UUID = Field(alias="tenantId")
    owner_membership_id: UUID | None = Field(default=None, alias="ownerMembershipId")
    team_id: UUID | None = Field(default=None, alias="teamId")


class MetricsDetailedRow(ApiModel):
    id: str
    tenant_id: UUID = Field(alias="tenantId")
    membership_id: UUID | None = Field(default=None, alias="membershipId")
    user_name: str = Field(alias="userName")
    user_title: str | None = Field(default=None, alias="userTitle")
    supervisor_id: UUID | None = Field(default=None, alias="supervisorId")
    supervisor_name: str | None = Field(default=None, alias="supervisorName")
    team_id: UUID | None = Field(default=None, alias="teamId")
    team_name: str | None = Field(default=None, alias="teamName")
    department: str
    device_id: UUID | None = Field(default=None, alias="deviceId")
    device: str
    os: str
    agent_status: str | None = Field(default=None, alias="agentStatus")
    app: str
    category: str
    event_type: str = Field(alias="eventType")
    duration_seconds: int = Field(alias="durationSeconds")
    occurred_at: str = Field(alias="occurredAt")
    collection_quality: str | None = Field(default=None, alias="collectionQuality")


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
    tenant_id: UUID | None = Field(default=None, alias="tenantId")
    membership_id: UUID | None = Field(default=None, alias="membershipId")
    department_id: UUID | None = Field(default=None, alias="departmentId")
    scope_type: str = Field(default="tenant", alias="scopeType")
    scope_id: str | None = Field(default=None, alias="scopeId")
    target_user_id: UUID | None = Field(default=None, alias="targetUserId")
    target_team_id: UUID | None = Field(default=None, alias="targetTeamId")
    target_department_id: UUID | None = Field(default=None, alias="targetDepartmentId")
    role_visibility: list[str] = Field(default_factory=list, alias="roleVisibility")
    insight_type: str = Field(default="recomendacao_processo", alias="insightType")
    title: str
    impact: Literal["high", "medium", "low"]
    summary: str
    diagnosis: str = ""
    recommendation: str
    evidence: list[str] = Field(default_factory=list)
    metrics_used: list[str] = Field(default_factory=list, alias="metricsUsed")
    affected_users: list[str] = Field(default_factory=list, alias="affectedUsers")
    affected_teams: list[str] = Field(default_factory=list, alias="affectedTeams")
    severity: str = "medium"
    confidence: float | None = None
    estimated_time_loss: float = Field(default=0, alias="estimatedTimeLoss")
    estimated_cost_loss: float = Field(default=0, alias="estimatedCostLoss")
    estimated_savings: float = Field(default=0, alias="estimatedSavings")
    period_start: datetime | None = Field(default=None, alias="periodStart")
    period_end: datetime | None = Field(default=None, alias="periodEnd")
    status: str = "open"
    source_route: str | None = Field(default=None, alias="sourceRoute")
    sent_to_whatsapp: bool = Field(default=False, alias="sentToWhatsapp")
    sent_to_email: bool = Field(default=False, alias="sentToEmail")
    whatsapp_status: str = Field(default="not_sent", alias="whatsappStatus")
    email_status: str = Field(default="not_sent", alias="emailStatus")
    last_sent_at: datetime | None = Field(default=None, alias="lastSentAt")
    recipients: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list, alias="suggestedQuestions")
    action_status: str | None = Field(default=None, alias="actionStatus")
    created_at: datetime | None = Field(default=None, alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")
    automation_savings_hours: int = Field(alias="automationSavingsHours")


class InsightAskRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question: str = Field(min_length=2)


class InsightAskResponse(ApiModel):
    insight_id: str = Field(alias="insightId")
    question: str
    answer: str
    ai_mode: str = Field(alias="aiMode")
    suggested_actions: list[str] = Field(default_factory=list, alias="suggestedActions")


class InsightGenerateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: UUID = Field(alias="tenantId")
    period: str = "24h"
    scope_type: str = Field(default="auto", alias="scopeType")
    force: bool = False


class InsightActionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str | None = None
    owner_membership_id: UUID | None = Field(default=None, alias="ownerMembershipId")
    priority: str = "alta"
    due_date: datetime | None = Field(default=None, alias="dueDate")
    note: str | None = None


class Notification(ApiModel):
    id: str
    tenant_id: UUID | None = Field(default=None, alias="tenantId")
    channel: Literal["system", "push", "windows", "whatsapp", "email"]
    status: Literal["pending", "queued", "sending", "sent", "delivered", "failed", "cancelled", "skipped", "retrying", "ready", "mocked", "missing_credentials", "missing_destination", "unknown_provider", "disabled", "resolved"]
    title: str
    message: str
    recipient: str | None = None
    recipient_membership_id: UUID | None = Field(default=None, alias="recipientMembershipId")
    notification_type: str | None = Field(default=None, alias="notificationType")
    priority: Literal["informativo", "baixo", "medio", "alto", "critico"] = "medio"
    attempts: int = 0
    max_attempts: int = Field(default=3, alias="maxAttempts")
    error: str | None = None
    provider: str | None = None
    provider_message_id: str | None = Field(default=None, alias="providerMessageId")
    scheduled_for: datetime | None = Field(default=None, alias="scheduledFor")
    sent_at: datetime | None = Field(default=None, alias="sentAt")
    delivered_at: datetime | None = Field(default=None, alias="deliveredAt")
    read_at: datetime | None = Field(default=None, alias="readAt")
    resolved_at: datetime | None = Field(default=None, alias="resolvedAt")
    action_url: str | None = Field(default=None, alias="actionUrl")
    requires_ack: bool = Field(default=False, alias="requiresAck")
    created_at: str = Field(alias="createdAt")


class NotificationSummary(ApiModel):
    total: int
    pending: int
    sent: int
    failed: int
    critical: int
    unread: int
    whatsapp_ready: bool = Field(alias="whatsappReady")
    email_ready: bool = Field(alias="emailReady")
    agent_ready: bool = Field(alias="agentReady")
    next_schedule_at: str | None = Field(default=None, alias="nextScheduleAt")
    by_channel: dict[str, int] = Field(default_factory=dict, alias="byChannel")
    by_status: dict[str, int] = Field(default_factory=dict, alias="byStatus")
    by_priority: dict[str, int] = Field(default_factory=dict, alias="byPriority")


class NotificationTypeDefinition(ApiModel):
    id: str
    name: str
    description: str
    default_priority: str = Field(alias="defaultPriority")
    allowed_channels: list[str] = Field(alias="allowedChannels")
    default_audience: str = Field(alias="defaultAudience")
    default_frequency: str = Field(alias="defaultFrequency")
    template: str
    can_disable: bool = Field(alias="canDisable")
    requires_permission: bool = Field(alias="requiresPermission")
    critical: bool
    enabled: bool = True


class NotificationPreference(ApiModel):
    id: UUID
    tenant_id: UUID = Field(alias="tenantId")
    membership_id: UUID = Field(alias="membershipId")
    channel: Literal["system", "push", "windows", "whatsapp", "email"]
    notification_type: str = Field(alias="notificationType")
    enabled: bool
    quiet_hours: dict[str, Any] = Field(default_factory=dict, alias="quietHours")
    frequency: str = "imediato"


class NotificationPreferenceUpdate(BaseModel):
    enabled: bool | None = None
    quiet_hours: dict[str, Any] | None = Field(default=None, alias="quietHours")
    frequency: str | None = None


class NotificationSendRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: UUID = Field(alias="tenantId")
    channel: Literal["system", "push", "windows", "whatsapp", "email"]
    notification_type: str = Field(alias="notificationType")
    title: str
    message: str
    recipient_membership_id: UUID | None = Field(default=None, alias="recipientMembershipId")
    destination: str | None = None
    priority: str = "medio"
    scheduled_for: datetime | None = Field(default=None, alias="scheduledFor")
    action_url: str | None = Field(default=None, alias="actionUrl")


class NotificationSendResponse(ApiModel):
    id: UUID | None = None
    channel: str
    status: str
    provider_result: str = Field(alias="providerResult")


class NotificationActionResponse(ApiModel):
    id: str
    status: str
    message: str


class NotificationScheduleCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    recurrence: str
    timezone: str = "America/Sao_Paulo"
    days_of_week: list[str] = Field(default_factory=list, alias="daysOfWeek")
    times: list[str] = Field(default_factory=lambda: ["08:00"])
    report_type: str = Field(default="operational_summary", alias="reportType")
    recipients: list[str] = Field(default_factory=list)
    channels: list[str] = Field(default_factory=lambda: ["system"])
    enabled: bool = True


class NotificationTemplate(ApiModel):
    id: str
    channel: Literal["system", "push", "windows", "whatsapp", "email"]
    notification_type: str = Field(alias="notificationType")
    title: str
    body: str
    variables: list[str]
    language: str = "pt-BR"
    version: int = 1
    active: bool = True


class NotificationTemplatePreviewRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    variables: dict[str, Any] = Field(default_factory=dict)


class NotificationTemplatePreviewResponse(ApiModel):
    title: str
    body: str
    variables_used: dict[str, Any] = Field(alias="variablesUsed")


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


class SettingsField(ApiModel):
    key: str
    label: str
    value: Any = None
    value_type: Literal["text", "number", "boolean", "select", "multiselect", "json", "secret", "readonly"] = Field(alias="valueType")
    description: str
    status: Literal["ok", "attention", "missing", "error", "mock", "readonly", "disabled"] = "ok"
    required: bool = False
    is_secret: bool = Field(default=False, alias="isSecret")
    editable: bool = True
    options: list[str] = Field(default_factory=list)
    placeholder: str | None = None
    unit: str | None = None


class SettingsSection(ApiModel):
    id: str
    title: str
    description: str
    scope: Literal["system", "tenant", "team", "user", "agent"] = "tenant"
    status: Literal["ok", "attention", "missing", "error", "mock", "readonly", "disabled"] = "ok"
    can_edit: bool = Field(alias="canEdit")
    last_updated_at: datetime | None = Field(default=None, alias="lastUpdatedAt")
    fields: list[SettingsField]


class SettingsSummary(ApiModel):
    tenant_id: UUID = Field(alias="tenantId")
    environment: str
    can_edit: bool = Field(alias="canEdit")
    total_sections: int = Field(alias="totalSections")
    ok: int
    attention: int
    missing: int
    error: int
    mock: int
    last_updated_at: datetime | None = Field(default=None, alias="lastUpdatedAt")
    critical_pending: list[str] = Field(default_factory=list, alias="criticalPending")
    statuses: dict[str, str] = Field(default_factory=dict)


class SettingsResponse(ApiModel):
    summary: SettingsSummary
    sections: list[SettingsSection]


class SettingsSectionUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    values: dict[str, Any] = Field(default_factory=dict)


class SettingsActionResponse(ApiModel):
    section: str
    status: str
    message: str
    saved: bool = False
    tested: bool = False
    section_data: SettingsSection | None = Field(default=None, alias="sectionData")


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
    database_reachable: bool | None = Field(default=None, alias="databaseReachable")
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
