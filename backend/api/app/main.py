from __future__ import annotations

import logging
import hmac
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from psycopg import Error as PsycopgError

from app.ai_router import analyze_facts, answer_copilot
from app.config import get_settings
from app.email_channels import EmailNotificationService
from app.notifications import NotificationPayload, NotificationService
from app.repository import VulcanRepository, get_repository
from app.schemas import (
    AIProviderConfig,
    AIStatus,
    ActivityEvent,
    ActivityEventCreate,
    ActivityEventCreateResponse,
    AgentEnrollRequest,
    AgentEnrollResponse,
    AgentEventsRequest,
    AgentEventsResponse,
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentLogsRequest,
    AgentStatusResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    AuditLog,
    CopilotRequest,
    CopilotResponse,
    ConnectionTestRequest,
    ConnectionTestResponse,
    Department,
    Device,
    DeviceAdoptionRequest,
    DeviceAdoptionResponse,
    DeviceMoveRequest,
    DeviceOwnerUpdate,
    EmailProviderStatusResponse,
    EvolutionActionResponse,
    EvolutionConfigurationRequest,
    EvolutionStatus,
    EvolutionWebhookResponse,
    HealthResponse,
    HierarchyNode,
    IntegrationStatus,
    Insight,
    InsightActionRequest,
    InsightAskRequest,
    InsightAskResponse,
    InsightGenerateRequest,
    LoginRequest,
    LoginResponse,
    Membership,
    MembershipCreate,
    MembershipManagerUpdate,
    MembershipUpdate,
    Metric,
    MetricsDetailedRow,
    Notification,
    NotificationActionResponse,
    NotificationPreference,
    NotificationPreferenceUpdate,
    NotificationScheduleCreate,
    NotificationSendRequest,
    NotificationSendResponse,
    NotificationSchedule,
    NotificationSummary,
    NotificationTemplate,
    NotificationTemplatePreviewRequest,
    NotificationTemplatePreviewResponse,
    NotificationTypeDefinition,
    RootWhatsAppLog,
    RootWhatsAppQueueItem,
    RootWhatsAppRecipient,
    RootWhatsAppSendRequest,
    RootWhatsAppSendResponse,
    OperationalIntelligence,
    OperationalMetric,
    ReportTemplate,
    Role,
    SettingsActionResponse,
    SettingsResponse,
    SettingsSection,
    SettingsSectionUpdate,
    SettingsSummary,
    SupabaseStatus,
    Tenant,
    Team,
    TeamCreate,
    TeamMember,
    TeamMemberCreate,
    TeamUpdate,
    User,
    WhatsAppStatus,
)
from app.security import AuthContext, Authenticated, login_with_local_admin
from app.supabase import supabase_status
from app.runtime_config import masked_runtime_config, update_runtime_config
from app.whatsapp import (
    EvolutionWhatsAppProvider,
    WhatsAppConnection,
    WhatsAppNotificationService,
    normalize_evolution_webhook,
)


app = FastAPI(title="Vulcan API", version="0.1.0")
AGENT_GATEWAY_VERSION = "0.1.0"
settings = get_settings()
logger = logging.getLogger("vulcan.api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.api_allowed_origins),
    allow_origin_regex=settings.api_allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PsycopgError)
async def database_exception_handler(request: Request, exc: PsycopgError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": "Banco de dados indisponível. Verifique DATABASE_URL, pooler Supabase ou conectividade de rede.",
            "code": "database_unavailable",
        },
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="vulcan-api",
        product="Vulcan",
        timestamp=datetime.now(timezone.utc),
    )


@app.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    return login_with_local_admin(request)


def repository() -> VulcanRepository:
    return get_repository()


def require_agent_enrollment_token(enrollment_token: str) -> None:
    settings = get_settings()
    if enrollment_token != settings.agent_enrollment_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid agent enrollment token")


@app.get("/agent/status", response_model=AgentStatusResponse)
def agent_status() -> AgentStatusResponse:
    settings = get_settings()
    return AgentStatusResponse(
        status="ok",
        service="vulcan-agent-gateway",
        version=AGENT_GATEWAY_VERSION,
        enrollmentEnabled=bool(settings.agent_enrollment_token),
    )


@app.post("/agent/enroll", response_model=AgentEnrollResponse)
def agent_enroll(request: AgentEnrollRequest, repo: VulcanRepository = Depends(repository)) -> AgentEnrollResponse:
    require_agent_enrollment_token(request.enrollment_token)
    try:
        return repo.agent_enroll(request)
    except PsycopgError as exc:
        logger.exception("agent enrollment persistence failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="agent persistence unavailable") from exc


@app.post("/agent/heartbeat", response_model=AgentHeartbeatResponse)
def agent_heartbeat(request: AgentHeartbeatRequest, repo: VulcanRepository = Depends(repository)) -> AgentHeartbeatResponse:
    require_agent_enrollment_token(request.enrollment_token)
    try:
        return repo.agent_heartbeat(request)
    except PsycopgError as exc:
        logger.exception("agent heartbeat persistence failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="agent persistence unavailable") from exc


@app.post("/agent/events", response_model=AgentEventsResponse)
def agent_events(request: AgentEventsRequest, repo: VulcanRepository = Depends(repository)) -> AgentEventsResponse:
    require_agent_enrollment_token(request.enrollment_token)
    try:
        return repo.agent_events(request)
    except PsycopgError as exc:
        logger.exception("agent events persistence failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="agent persistence unavailable") from exc


@app.post("/agent/sync", response_model=AgentEventsResponse)
def agent_sync(request: AgentEventsRequest, repo: VulcanRepository = Depends(repository)) -> AgentEventsResponse:
    require_agent_enrollment_token(request.enrollment_token)
    try:
        return repo.agent_events(request)
    except PsycopgError as exc:
        logger.exception("agent sync persistence failed")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="agent persistence unavailable") from exc


@app.post("/agent/logs", response_model=AgentEventsResponse)
def agent_logs(request: AgentLogsRequest, repo: VulcanRepository = Depends(repository)) -> AgentEventsResponse:
    require_agent_enrollment_token(request.enrollment_token)
    try:
        return repo.agent_logs(request)
    except PsycopgError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="agent persistence unavailable") from exc


@app.get("/tenants", response_model=list[Tenant])
def list_tenants(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[Tenant]:
    return [Tenant.model_validate(item) for item in repo.list_tenants(context)]


@app.get("/departments", response_model=list[Department])
def list_departments(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[Department]:
    return [Department.model_validate(item) for item in repo.list_departments(context)]


@app.get("/roles", response_model=list[Role])
def list_roles(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[Role]:
    return [Role.model_validate(item) for item in repo.list_roles(context)]


@app.get("/teams", response_model=list[Team])
def list_teams(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[Team]:
    return [Team.model_validate(item) for item in repo.list_teams(context)]


@app.post("/teams", response_model=Team)
def create_team(
    request: TeamCreate,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> Team:
    try:
        return Team.model_validate(repo.create_team(context, request))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@app.put("/teams/{team_id}", response_model=Team)
def update_team(
    team_id: UUID,
    request: TeamUpdate,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> Team:
    try:
        updated = repo.update_team(context, team_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="team not found")
    return Team.model_validate(updated)


@app.delete("/teams/{team_id}", response_model=Team)
def delete_team(
    team_id: UUID,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> Team:
    try:
        deleted = repo.delete_team(context, team_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="team not found")
    return Team.model_validate(deleted)


@app.get("/teams/{team_id}/members", response_model=list[TeamMember])
def list_team_members(
    team_id: UUID,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> list[TeamMember]:
    return [TeamMember.model_validate(item) for item in repo.list_team_members(context, team_id)]


@app.post("/teams/{team_id}/members", response_model=TeamMember)
def add_team_member(
    team_id: UUID,
    request: TeamMemberCreate,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> TeamMember:
    try:
        return TeamMember.model_validate(repo.add_team_member(context, team_id, request))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@app.delete("/teams/{team_id}/members/{membership_id}", response_model=Team)
def remove_team_member(
    team_id: UUID,
    membership_id: UUID,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> Team:
    try:
        updated = repo.remove_team_member(context, team_id, membership_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="team member not found")
    return Team.model_validate(updated)


@app.get("/memberships", response_model=list[Membership])
def list_memberships(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[Membership]:
    return [Membership.model_validate(item) for item in repo.list_memberships(context)]


@app.post("/memberships", response_model=Membership)
def create_membership(
    request: MembershipCreate,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> Membership:
    try:
        return Membership.model_validate(repo.create_membership(context, request))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@app.put("/memberships/{membership_id}", response_model=Membership)
def update_membership(
    membership_id: UUID,
    request: MembershipUpdate,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> Membership:
    try:
        updated = repo.update_membership(context, membership_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="membership not found")
    return Membership.model_validate(updated)


@app.put("/memberships/{membership_id}/manager", response_model=Membership)
def update_membership_manager(
    membership_id: UUID,
    request: MembershipManagerUpdate,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> Membership:
    try:
        updated = repo.update_membership_manager(context, membership_id, request.direct_manager_membership_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="membership not found")
    return Membership.model_validate(updated)


@app.delete("/memberships/{membership_id}", response_model=Membership)
def delete_membership(
    membership_id: UUID,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> Membership:
    try:
        deleted = repo.delete_membership(context, membership_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="membership not found")
    return Membership.model_validate(deleted)


@app.get("/users", response_model=list[User])
def list_users(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[User]:
    return [User.model_validate(item) for item in repo.list_users(context)]


@app.get("/hierarchy", response_model=list[HierarchyNode])
def list_hierarchy(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[HierarchyNode]:
    return [HierarchyNode.model_validate(item) for item in repo.list_hierarchy(context)]


@app.get("/devices", response_model=list[Device])
def list_devices(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[Device]:
    return [Device.model_validate(item) for item in repo.list_devices(context)]


@app.get("/devices/pending-adoption", response_model=list[Device])
def list_pending_devices(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[Device]:
    return [Device.model_validate(item) for item in repo.list_pending_adoption_devices(context)]


@app.post("/devices/{device_id}/adopt", response_model=DeviceAdoptionResponse)
def adopt_device(
    device_id: UUID,
    request: DeviceAdoptionRequest,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> DeviceAdoptionResponse:
    try:
        return DeviceAdoptionResponse.model_validate(repo.adopt_device(context, device_id, request))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@app.post("/devices/{device_id}/link-user", response_model=Device)
def link_device_user(
    device_id: UUID,
    request: DeviceOwnerUpdate,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> Device:
    try:
        updated = repo.update_device_owner(context, device_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device not found")
    return Device.model_validate(updated)


@app.post("/devices/{device_id}/unlink-user", response_model=Device)
def unlink_device_user(
    device_id: UUID,
    request: DeviceOwnerUpdate,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> Device:
    try:
        updated = repo.update_device_owner(context, device_id, DeviceOwnerUpdate(tenantId=request.tenant_id, ownerMembershipId=None))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device not found")
    return Device.model_validate(updated)


@app.post("/devices/{device_id}/move", response_model=Device)
def move_device(
    device_id: UUID,
    request: DeviceMoveRequest,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> Device:
    try:
        moved = repo.move_device(context, device_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if not moved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device not found")
    return Device.model_validate(moved)


@app.put("/devices/{device_id}/owner", response_model=Device)
def update_device_owner(
    device_id: UUID,
    request: DeviceOwnerUpdate,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> Device:
    try:
        updated = repo.update_device_owner(context, device_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="device not found")
    return Device.model_validate(updated)


@app.get("/activity-events", response_model=list[ActivityEvent])
def list_activity_events(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[ActivityEvent]:
    return [ActivityEvent.model_validate(item) for item in repo.list_activity_events(context)]


@app.post("/activity-events", response_model=ActivityEventCreateResponse)
def create_activity_event(
    request: ActivityEventCreate,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> ActivityEventCreateResponse:
    try:
        return repo.create_activity_event(context, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@app.get("/metrics", response_model=list[Metric])
def list_metrics(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[Metric]:
    return [Metric.model_validate(item) for item in repo.list_dashboard_metrics(context)]


@app.get("/operational-metrics", response_model=list[OperationalMetric])
def list_operational_metrics(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[OperationalMetric]:
    return [OperationalMetric.model_validate(item) for item in repo.list_operational_metrics(context)]


@app.get("/metrics/detailed", response_model=list[MetricsDetailedRow])
def detailed_metrics(
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
    period: str = Query(default="24h"),
    team_id: UUID | None = Query(default=None, alias="teamId"),
    membership_id: UUID | None = Query(default=None, alias="membershipId"),
    device_id: UUID | None = Query(default=None, alias="deviceId"),
    supervisor_id: UUID | None = Query(default=None, alias="supervisorId"),
    department: str | None = Query(default=None),
    title: str | None = Query(default=None),
    os_name: str | None = Query(default=None, alias="os"),
    category: str | None = Query(default=None),
    agent_status: str | None = Query(default=None, alias="agentStatus"),
    metric_type: str | None = Query(default=None, alias="metricType"),
    app: str | None = Query(default=None),
) -> list[MetricsDetailedRow]:
    rows = repo.list_detailed_metrics(
        context,
        period=period,
        team_id=team_id,
        membership_id=membership_id,
        device_id=device_id,
        supervisor_id=supervisor_id,
        department=department,
        title=title,
        os_name=os_name,
        category=category,
        agent_status=agent_status,
        metric_type=metric_type,
        app=app,
    )
    return [MetricsDetailedRow.model_validate(row) for row in rows]


@app.get("/metrics/export")
def export_metrics(
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
    format: str = Query(default="csv"),
    period: str = Query(default="24h"),
    team_id: UUID | None = Query(default=None, alias="teamId"),
    membership_id: UUID | None = Query(default=None, alias="membershipId"),
    device_id: UUID | None = Query(default=None, alias="deviceId"),
    supervisor_id: UUID | None = Query(default=None, alias="supervisorId"),
    department: str | None = Query(default=None),
    title: str | None = Query(default=None),
    os_name: str | None = Query(default=None, alias="os"),
    category: str | None = Query(default=None),
    agent_status: str | None = Query(default=None, alias="agentStatus"),
    metric_type: str | None = Query(default=None, alias="metricType"),
    app: str | None = Query(default=None),
) -> Response:
    if format not in {"csv", "excel"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="format must be csv or excel")
    content = repo.export_metrics_csv(
        context,
        period=period,
        team_id=team_id,
        membership_id=membership_id,
        device_id=device_id,
        supervisor_id=supervisor_id,
        department=department,
        title=title,
        os_name=os_name,
        category=category,
        agent_status=agent_status,
        metric_type=metric_type,
        app=app,
    )
    filename = "vulcan-metricas.csv" if format == "csv" else "vulcan-metricas-excel.csv"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/operational-intelligence", response_model=OperationalIntelligence)
def operational_intelligence(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> OperationalIntelligence:
    return OperationalIntelligence.model_validate(repo.operational_intelligence(context))


@app.get("/insights", response_model=list[Insight])
def list_insights(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[Insight]:
    return [Insight.model_validate(item) for item in repo.list_insights(context)]


@app.get("/insights/{insight_id}", response_model=Insight)
def get_insight(insight_id: UUID, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> Insight:
    insight = repo.get_insight(context, insight_id)
    if not insight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="insight not found")
    return Insight.model_validate(insight)


@app.post("/insights/generate", response_model=Insight)
def generate_insight(request: InsightGenerateRequest, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> Insight:
    try:
        return Insight.model_validate(repo.generate_insight(context, request.tenant_id, request.period))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@app.post("/insights/{insight_id}/ask", response_model=InsightAskResponse)
def ask_insight(insight_id: UUID, request: InsightAskRequest, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> InsightAskResponse:
    try:
        return InsightAskResponse.model_validate(repo.ask_insight(context, insight_id, request.question))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.post("/insights/{insight_id}/send-whatsapp", response_model=Insight)
def send_insight_whatsapp(insight_id: UUID, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> Insight:
    insight = repo.get_insight(context, insight_id)
    if not insight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="insight not found")
    request = RootWhatsAppSendRequest(
        tenantId=insight["tenantId"],
        notificationType="insight_critico" if insight.get("impact") in {"high", "critical"} else "insight",
        title=insight["title"],
        message=f"{insight['summary']}\n\nAção recomendada: {insight['recommendation']}",
        audience="auto",
        priority="critico" if insight.get("impact") == "critical" else "alto",
        schedule="imediato",
        variables={
            "resumo": insight["summary"],
            "recomendacao": insight["recommendation"],
            "economia_estimada": f"{insight.get('automationSavingsHours') or 0}h",
            "impacto": insight.get("impact") or "alto",
        },
        idempotencyKey=f"insight:{insight_id}:whatsapp",
    )
    items = repo.queue_root_whatsapp_messages(context, request)
    if items:
        queue_ids = [item["id"] for item in items]
        items = repo.dispatch_root_whatsapp_queue(context, queue_ids=queue_ids, limit=len(queue_ids)) or items
    statuses = [str(item.get("status")) for item in items]
    updated = repo.update_insight_metadata(
        context,
        insight_id,
        {
            "sentToWhatsapp": any(status in {"sent", "delivered", "mocked"} for status in statuses),
            "whatsappStatus": statuses[0] if statuses else "skipped",
            "lastSentAt": datetime.now(timezone.utc).isoformat(),
            "recipients": [str(item.get("recipient") or item.get("recipientMembershipId")) for item in items],
            "lastWhatsappResult": f"root_whatsapp:{len(items)} destinatário(s)",
        },
        "insight.sent_whatsapp",
    )
    return Insight.model_validate(updated or insight)


@app.post("/insights/{insight_id}/send-email", response_model=Insight)
def send_insight_email(insight_id: UUID, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> Insight:
    insight = repo.get_insight(context, insight_id)
    if not insight:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="insight not found")
    service = EmailNotificationService()
    delivery = service.send_test(
        None,
        insight["title"],
        f"{insight['summary']}\n\nAção recomendada: {insight['recommendation']}",
    )
    updated = repo.update_insight_metadata(
        context,
        insight_id,
        {
            "sentToEmail": delivery.ok,
            "emailStatus": delivery.status,
            "lastSentAt": datetime.now(timezone.utc).isoformat(),
            "lastEmailResult": delivery.provider_result,
        },
        "insight.sent_email",
    )
    return Insight.model_validate(updated or insight)


@app.post("/insights/{insight_id}/resolve", response_model=Insight)
def resolve_insight(insight_id: UUID, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> Insight:
    updated = repo.update_insight_metadata(context, insight_id, {"status": "resolved"}, "insight.resolved")
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="insight not found")
    return Insight.model_validate(updated)


@app.post("/insights/{insight_id}/create-action", response_model=Insight)
def create_insight_action(insight_id: UUID, request: InsightActionRequest, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> Insight:
    updated = repo.create_insight_action(
        context,
        insight_id,
        {
            "title": request.title,
            "owner_membership_id": request.owner_membership_id,
            "priority": request.priority,
            "due_date": request.due_date,
            "note": request.note,
        },
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="insight not found")
    return Insight.model_validate(updated)


@app.get("/notifications", response_model=list[Notification])
def list_notifications(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[Notification]:
    return [Notification.model_validate(item) for item in repo.list_notifications(context)]


@app.get("/notifications/summary", response_model=NotificationSummary)
def notification_summary(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> NotificationSummary:
    return NotificationSummary.model_validate(repo.notification_summary(context))


@app.post("/notifications/test", response_model=NotificationSendResponse)
def test_notification(
    request: NotificationSendRequest,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> NotificationSendResponse:
    service = NotificationService()
    delivery = service.send(request.channel, NotificationPayload(title=request.title, message=request.message, tenant_id=str(request.tenant_id), destination=request.destination))
    try:
        return repo.create_notification_record(context, request, delivery.status, delivery.provider_result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@app.post("/notifications/send", response_model=NotificationSendResponse)
def send_notification(
    request: NotificationSendRequest,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> NotificationSendResponse:
    if request.channel == "whatsapp":
        try:
            root_request = RootWhatsAppSendRequest(
                tenantId=request.tenant_id,
                notificationType=request.notification_type,
                title=request.title,
                message=request.message,
                audience="custom" if request.recipient_membership_id else "auto",
                recipientMembershipIds=[request.recipient_membership_id] if request.recipient_membership_id else [],
                priority=request.priority,
                schedule="imediato" if request.scheduled_for is None else "personalizado",
                scheduledFor=request.scheduled_for,
                maxAttempts=3,
                actionUrl=request.action_url,
                idempotencyKey=f"notification:{request.tenant_id}:{request.notification_type}:{request.recipient_membership_id or request.destination or request.title}",
            )
            items = repo.queue_root_whatsapp_messages(context, root_request)
            if request.scheduled_for is None and items:
                queue_ids = [item["id"] for item in items]
                items = repo.dispatch_root_whatsapp_queue(context, queue_ids=queue_ids, limit=len(queue_ids)) or items
            first = items[0] if items else None
            return NotificationSendResponse(
                id=first.get("notificationId") if first else None,
                channel="whatsapp",
                status=first.get("status", "skipped") if first else "skipped",
                providerResult=f"root_whatsapp:{len(items)} destinatário(s)",
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    service = NotificationService()
    delivery = service.send(request.channel, NotificationPayload(title=request.title, message=request.message, tenant_id=str(request.tenant_id), destination=request.destination))
    try:
        return repo.create_notification_record(context, request, delivery.status, delivery.provider_result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@app.post("/notifications/{notification_id}/retry", response_model=Notification)
def retry_notification(notification_id: UUID, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> Notification:
    updated = repo.retry_notification(context, notification_id)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notification not found")
    return Notification.model_validate(updated)


@app.post("/notifications/{notification_id}/cancel", response_model=NotificationActionResponse)
def cancel_notification(notification_id: UUID, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> NotificationActionResponse:
    updated = repo._patch_notification_metadata(context, notification_id, {"deliveryStatus": "cancelled", "cancelledAt": datetime.now(timezone.utc).isoformat()}, "notification.cancelled", "disabled")
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notification not found")
    return NotificationActionResponse(id=str(notification_id), status="cancelled", message="Notificação cancelada.")


@app.post("/notifications/{notification_id}/mark-read", response_model=NotificationActionResponse)
def mark_notification_read(notification_id: UUID, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> NotificationActionResponse:
    updated = repo._patch_notification_metadata(context, notification_id, {"readAt": datetime.now(timezone.utc).isoformat()}, "notification.read")
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notification not found")
    return NotificationActionResponse(id=str(notification_id), status="read", message="Notificação marcada como lida.")


@app.post("/notifications/{notification_id}/resolve", response_model=NotificationActionResponse)
def resolve_notification(notification_id: UUID, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> NotificationActionResponse:
    updated = repo._patch_notification_metadata(context, notification_id, {"deliveryStatus": "resolved", "resolvedAt": datetime.now(timezone.utc).isoformat()}, "notification.resolved")
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notification not found")
    return NotificationActionResponse(id=str(notification_id), status="resolved", message="Notificação resolvida.")


@app.get("/notification-types", response_model=list[NotificationTypeDefinition])
def notification_types(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[NotificationTypeDefinition]:
    return [NotificationTypeDefinition.model_validate(item) for item in repo.list_notification_types(context)]


@app.get("/integrations/whatsapp/status", response_model=WhatsAppStatus)
def whatsapp_status(context: AuthContext = Authenticated) -> WhatsAppStatus:
    settings = get_settings()
    connection = WhatsAppConnection(settings)
    session = connection.session(context.tenant_id)
    return WhatsAppStatus(
        rootChannelEnabled=settings.root_whatsapp_enabled,
        rootChannelName=settings.root_whatsapp_name,
        rootChannelNumber=settings.root_whatsapp_number,
        provider=session.provider,
        connected=session.connected,
        status=session.status,
        qrRequired=session.qr_required,
        qrCode=session.qr_code,
        lastConnectionAt=session.last_connection_at,
        lastSyncAt=session.last_sync_at,
        logs=session.logs,
    )


@app.post("/integrations/whatsapp/test", response_model=ConnectionTestResponse)
def whatsapp_test(
    request: ConnectionTestRequest,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> ConnectionTestResponse:
    repo.assert_can_manage_integrations(context)
    if request.tenant_id != context.tenant_id and context.role != "root":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant mismatch")
    service = WhatsAppNotificationService()
    delivery = service.send_alert(
        tenant_id=str(request.tenant_id),
        title="Teste do Vulcan",
        message=request.message or "Mensagem de teste do Canal Oficial Vulcan.",
        to=request.destination,
    )
    return ConnectionTestResponse(ok=delivery.ok, status=delivery.status, providerResult=delivery.provider_result, message=delivery.message)


def _evolution_status_payload(include_qr: bool = False) -> EvolutionStatus:
    settings = get_settings()
    session = WhatsAppConnection(settings).session(include_qr=include_qr)
    runtime = masked_runtime_config()
    return EvolutionStatus(
        provider=session.provider,
        status=session.status,
        connected=session.connected,
        unofficial=session.unofficial or session.provider == "evolution",
        serviceReachable=session.service_reachable,
        instanceName=settings.evolution_instance_name,
        baseUrl=settings.evolution_base_url,
        rootNumber=settings.root_whatsapp_number,
        rootName=settings.root_whatsapp_name,
        qrRequired=session.qr_required,
        qrCode=session.qr_code,
        apiKeyConfigured=bool(settings.evolution_api_key or runtime.get("EVOLUTION_API_KEY_CONFIGURED")),
        webhookConfigured=bool(settings.evolution_webhook_url and settings.evolution_webhook_token),
        mockMode=settings.root_whatsapp_mock_mode,
        requireOptIn=settings.whatsapp_require_opt_in,
        emailFallbackEnabled=settings.whatsapp_email_fallback_enabled,
        inAppFallbackEnabled=settings.whatsapp_in_app_fallback_enabled,
        logs=session.logs,
    )


@app.get("/integrations/whatsapp/evolution/status", response_model=EvolutionStatus)
def evolution_status(
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> EvolutionStatus:
    repo.assert_can_manage_integrations(context)
    return _evolution_status_payload()


@app.put("/integrations/whatsapp/evolution/config", response_model=EvolutionStatus)
def evolution_configure(
    request: EvolutionConfigurationRequest,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> EvolutionStatus:
    repo.assert_can_manage_integrations(context)
    settings = get_settings()
    if not settings.allow_runtime_integration_config:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="runtime integration configuration is disabled; configure the production secret store",
        )
    values = {
        "ROOT_WHATSAPP_ENABLED": request.enabled,
        "ROOT_WHATSAPP_PROVIDER": request.provider,
        "ROOT_WHATSAPP_NUMBER": request.root_number,
        "ROOT_WHATSAPP_NAME": request.root_name,
        "ROOT_WHATSAPP_MOCK_MODE": request.mock_mode or request.provider == "mock",
        "EVOLUTION_ENABLED": request.enabled and request.provider == "evolution",
        "EVOLUTION_BASE_URL": request.base_url,
        "EVOLUTION_INSTANCE_NAME": request.instance_name,
        "WHATSAPP_REQUIRE_OPT_IN": request.require_opt_in,
        "WHATSAPP_EMAIL_FALLBACK_ENABLED": request.email_fallback_enabled,
        "WHATSAPP_IN_APP_FALLBACK_ENABLED": request.in_app_fallback_enabled,
    }
    if request.api_key:
        values["EVOLUTION_API_KEY"] = request.api_key
    update_runtime_config(values)
    return _evolution_status_payload()


@app.post("/integrations/whatsapp/evolution/test", response_model=EvolutionActionResponse)
def evolution_test(
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> EvolutionActionResponse:
    repo.assert_can_manage_integrations(context)
    delivery = WhatsAppConnection(get_settings()).test_connection(context.tenant_id)
    return EvolutionActionResponse(ok=delivery.ok, status=delivery.status, message=delivery.message)


@app.get("/integrations/whatsapp/evolution/qr", response_model=EvolutionActionResponse)
def evolution_qr(
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> EvolutionActionResponse:
    repo.assert_can_manage_integrations(context)
    settings = get_settings()
    if settings.root_whatsapp_provider != "evolution" or settings.root_whatsapp_mock_mode:
        return EvolutionActionResponse(ok=False, status="disabled", message="Ative Evolution com mock desligado para gerar QR Code.")
    result = EvolutionWhatsAppProvider(settings).get_qr_code(create_if_missing=True)
    status_payload = _evolution_status_payload(include_qr=True)
    return EvolutionActionResponse(
        ok=result.ok or status_payload.connected,
        status=status_payload.status,
        message="WhatsApp já está conectado." if status_payload.connected else result.message,
        qrCode=status_payload.qr_code,
    )


@app.post("/integrations/whatsapp/evolution/reconnect", response_model=EvolutionActionResponse)
def evolution_reconnect(
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> EvolutionActionResponse:
    repo.assert_can_manage_integrations(context)
    result = EvolutionWhatsAppProvider(get_settings()).reconnect()
    status_payload = _evolution_status_payload(include_qr=True)
    return EvolutionActionResponse(
        ok=result.ok,
        status=status_payload.status,
        message=result.message,
        qrCode=status_payload.qr_code,
    )


@app.post("/integrations/whatsapp/evolution/send-test", response_model=ConnectionTestResponse)
def evolution_send_test(
    request: ConnectionTestRequest,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> ConnectionTestResponse:
    return whatsapp_test(request, context, repo)


@app.post("/integrations/whatsapp/evolution/webhook", response_model=EvolutionWebhookResponse)
async def evolution_webhook(
    request: Request,
    x_vulcan_webhook_token: str | None = Header(default=None, alias="X-Vulcan-Webhook-Token"),
    repo: VulcanRepository = Depends(repository),
) -> EvolutionWebhookResponse:
    expected = get_settings().evolution_webhook_token
    if not expected or not x_vulcan_webhook_token or not hmac.compare_digest(expected, x_vulcan_webhook_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid evolution webhook token")
    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid webhook payload")
    event, provider_message_id, normalized_status = normalize_evolution_webhook(payload)
    accepted = bool(provider_message_id and repo.apply_root_whatsapp_webhook(provider_message_id, normalized_status, payload))
    return EvolutionWebhookResponse(
        accepted=accepted or normalized_status.startswith("unofficial_"),
        event=event,
        status=normalized_status,
        providerMessageId=provider_message_id,
    )


@app.get("/integrations/whatsapp/root/recipients", response_model=list[RootWhatsAppRecipient])
def root_whatsapp_recipients(
    notification_type: str = Query(default="alerta", alias="notificationType"),
    audience: str = Query(default="auto"),
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> list[RootWhatsAppRecipient]:
    recipients = repo.resolve_root_whatsapp_recipients(context, notification_type=notification_type, audience=audience)
    return [RootWhatsAppRecipient.model_validate(item) for item in recipients]


@app.get("/integrations/whatsapp/root/queue", response_model=list[RootWhatsAppQueueItem])
def root_whatsapp_queue(
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[RootWhatsAppQueueItem]:
    return [RootWhatsAppQueueItem.model_validate(item) for item in repo.list_root_whatsapp_queue(context, limit=limit)]


@app.get("/integrations/whatsapp/root/logs", response_model=list[RootWhatsAppLog])
def root_whatsapp_logs(
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[RootWhatsAppLog]:
    return [RootWhatsAppLog.model_validate(item) for item in repo.list_root_whatsapp_logs(context, limit=limit)]


@app.post("/integrations/whatsapp/root/queue/{queue_id}/retry", response_model=RootWhatsAppQueueItem)
def root_whatsapp_retry_queue_item(
    queue_id: UUID,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> RootWhatsAppQueueItem:
    item = repo.retry_root_whatsapp_queue_item(context, queue_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="queue item not found")
    return RootWhatsAppQueueItem.model_validate(item)


@app.post("/integrations/whatsapp/root/send", response_model=RootWhatsAppSendResponse)
def root_whatsapp_send(
    request: RootWhatsAppSendRequest,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> RootWhatsAppSendResponse:
    try:
        recipients = repo.resolve_root_whatsapp_recipients(
            context,
            notification_type=request.notification_type,
            audience=request.audience,
            recipient_membership_ids=request.recipient_membership_ids,
        )
        items = repo.queue_root_whatsapp_messages(context, request)
        should_dispatch = request.schedule == "imediato" and request.scheduled_for is None and not request.dry_run
        if should_dispatch and items:
            queue_ids = [item["id"] for item in items]
            dispatched = repo.dispatch_root_whatsapp_queue(context, queue_ids=queue_ids, limit=len(queue_ids))
            if dispatched:
                by_id = {str(item["id"]): item for item in dispatched}
                items = [by_id.get(str(item["id"]), item) for item in items]
        mode = WhatsAppConnection(get_settings()).session(context.tenant_id).status
        return RootWhatsAppSendResponse.model_validate(repo.summarize_root_whatsapp_result(items, recipients, mode))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@app.post("/integrations/whatsapp/root/process-queue", response_model=RootWhatsAppSendResponse)
def root_whatsapp_process_queue(
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
    limit: int = Query(default=25, ge=1, le=100),
) -> RootWhatsAppSendResponse:
    items = repo.dispatch_root_whatsapp_queue(context, limit=limit)
    mode = WhatsAppConnection(get_settings()).session(context.tenant_id).status
    return RootWhatsAppSendResponse.model_validate(repo.summarize_root_whatsapp_result(items, [], mode))


@app.get("/integrations/email/status", response_model=list[EmailProviderStatusResponse])
def email_status(context: AuthContext = Authenticated) -> list[EmailProviderStatusResponse]:
    return [EmailProviderStatusResponse.model_validate(item.__dict__) for item in EmailNotificationService().statuses()]


@app.post("/integrations/email/test", response_model=ConnectionTestResponse)
def email_test(request: ConnectionTestRequest, context: AuthContext = Authenticated) -> ConnectionTestResponse:
    delivery = EmailNotificationService().send_test(
        to=request.destination,
        subject="Teste do Vulcan",
        message=request.message or "Mensagem de teste das notificações por e-mail do Vulcan.",
        provider=request.provider,
    )
    return ConnectionTestResponse(ok=delivery.ok, status=delivery.status, providerResult=delivery.provider_result, message=delivery.message)


@app.get("/integrations/status", response_model=list[IntegrationStatus])
def integrations_status(context: AuthContext = Authenticated) -> list[IntegrationStatus]:
    settings = get_settings()
    whatsapp = WhatsAppConnection(settings).session(context.tenant_id)
    email_statuses = EmailNotificationService(settings).statuses()
    now = datetime.now(timezone.utc)
    return [
        IntegrationStatus(
            name="WhatsApp",
            provider=whatsapp.provider,
            configured=whatsapp.connected,
            status=whatsapp.status,
            mode="canal_raiz",
            lastCheckedAt=whatsapp.last_sync_at or now,
            requiredItems=[] if whatsapp.connected else ["ROOT_WHATSAPP_ENABLED", "ROOT_WHATSAPP_PROVIDER", "ROOT_WHATSAPP_NUMBER"],
            details={"canal": settings.root_whatsapp_name, "numero": settings.root_whatsapp_number},
        ),
        *[
            IntegrationStatus(
                name=f"E-mail {item.provider.upper()}",
                provider=item.provider,
                configured=item.configured,
                status=item.status,
                mode="envio" if item.can_send else "consulta",
                lastCheckedAt=item.last_checked_at,
                requiredItems=item.required_items,
                details={"podeEnviar": item.can_send, "podeLer": item.can_read, "mensagem": item.message},
            )
            for item in email_statuses
        ],
    ]


@app.get("/settings", response_model=SettingsResponse)
def settings_center(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> SettingsResponse:
    return SettingsResponse.model_validate(repo.get_settings_center(context))


@app.get("/settings/summary", response_model=SettingsSummary)
def settings_summary(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> SettingsSummary:
    return SettingsSummary.model_validate(repo.get_settings_center(context)["summary"])


@app.get("/settings/{section_id}", response_model=SettingsSection)
def settings_section(section_id: str, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> SettingsSection:
    response = repo.get_settings_center(context)
    section = next((item for item in response["sections"] if item["id"] == section_id), None)
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="settings section not found")
    return SettingsSection.model_validate(section)


@app.put("/settings/{section_id}", response_model=SettingsActionResponse)
def update_settings_section(
    section_id: str,
    request: SettingsSectionUpdate,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> SettingsActionResponse:
    try:
        response = repo.update_settings_section(context, section_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    section = next((item for item in response["sections"] if item["id"] == section_id), None)
    return SettingsActionResponse(section=section_id, status=section["status"] if section else "ok", message="Configuração salva e auditada.", saved=True, sectionData=section)


@app.post("/settings/{section_id}/test", response_model=SettingsActionResponse)
def test_settings_section(section_id: str, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> SettingsActionResponse:
    try:
        return SettingsActionResponse.model_validate(repo.test_settings_section(context, section_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.post("/settings/{section_id}/reset", response_model=SettingsActionResponse)
def reset_settings_section(section_id: str, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> SettingsActionResponse:
    try:
        response = repo.update_settings_section(context, section_id, SettingsSectionUpdate(values={}))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    section = next((item for item in response["sections"] if item["id"] == section_id), None)
    return SettingsActionResponse(section=section_id, status=section["status"] if section else "ok", message="Seção restaurada para defaults conhecidos.", saved=True, sectionData=section)


@app.get("/notifications/schedules", response_model=list[NotificationSchedule])
def notification_schedules(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[NotificationSchedule]:
    return [NotificationSchedule.model_validate(item) for item in repo.list_notification_schedules(context)]


@app.post("/notification-schedules", response_model=NotificationSchedule)
def create_notification_schedule(request: NotificationScheduleCreate, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> NotificationSchedule:
    return NotificationSchedule.model_validate(repo.create_notification_schedule(context, request))


@app.put("/notification-schedules/{schedule_id}", response_model=NotificationActionResponse)
def update_notification_schedule(schedule_id: UUID, request: NotificationScheduleCreate, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> NotificationActionResponse:
    updated = repo.update_notification_schedule(context, schedule_id, request.model_dump(by_alias=True))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="schedule not found")
    return NotificationActionResponse(id=str(schedule_id), status="updated", message="Agendamento atualizado.")


@app.delete("/notification-schedules/{schedule_id}", response_model=NotificationActionResponse)
def delete_notification_schedule(schedule_id: UUID, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> NotificationActionResponse:
    updated = repo._patch_notification_metadata(context, schedule_id, {"enabled": False, "deliveryStatus": "cancelled"}, "notification_schedule.deleted", "disabled")
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="schedule not found")
    return NotificationActionResponse(id=str(schedule_id), status="deleted", message="Agendamento desativado.")


@app.post("/notification-schedules/{schedule_id}/pause", response_model=NotificationActionResponse)
def pause_notification_schedule(schedule_id: UUID, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> NotificationActionResponse:
    updated = repo._patch_notification_metadata(context, schedule_id, {"enabled": False}, "notification_schedule.paused", "disabled")
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="schedule not found")
    return NotificationActionResponse(id=str(schedule_id), status="paused", message="Agendamento pausado.")


@app.post("/notification-schedules/{schedule_id}/resume", response_model=NotificationActionResponse)
def resume_notification_schedule(schedule_id: UUID, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> NotificationActionResponse:
    updated = repo._patch_notification_metadata(context, schedule_id, {"enabled": True, "deliveryStatus": "queued"}, "notification_schedule.resumed", "queued")
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="schedule not found")
    return NotificationActionResponse(id=str(schedule_id), status="resumed", message="Agendamento reativado.")


@app.get("/notification-templates", response_model=list[NotificationTemplate])
def notification_templates(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[NotificationTemplate]:
    return [NotificationTemplate.model_validate(item) for item in repo.list_notification_templates(context)]


@app.post("/notification-templates/{template_id}/preview", response_model=NotificationTemplatePreviewResponse)
def preview_notification_template(template_id: str, request: NotificationTemplatePreviewRequest, repo: VulcanRepository = Depends(repository)) -> NotificationTemplatePreviewResponse:
    preview = repo.preview_notification_template(template_id, request.variables)
    if not preview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="template not found")
    return NotificationTemplatePreviewResponse.model_validate(preview)


@app.post("/notification-templates/{template_id}/test", response_model=NotificationSendResponse)
def test_notification_template(template_id: str, request: NotificationTemplatePreviewRequest, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> NotificationSendResponse:
    preview = repo.preview_notification_template(template_id, request.variables)
    template = next((item for item in repo.list_notification_templates(context) if item["id"] == template_id), None)
    if not preview or not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="template not found")
    send_request = NotificationSendRequest(
        tenantId=context.tenant_id,
        channel=template["channel"],
        notificationType=template["notificationType"],
        title=preview["title"],
        message=preview["body"],
        priority="medio",
    )
    delivery = NotificationService().send(send_request.channel, NotificationPayload(title=send_request.title, message=send_request.message, tenant_id=str(send_request.tenant_id)))
    return repo.create_notification_record(context, send_request, delivery.status, delivery.provider_result)


@app.get("/reports/templates", response_model=list[ReportTemplate])
def report_templates(context: AuthContext = Authenticated) -> list[ReportTemplate]:
    return [
        ReportTemplate(
            id="resumo-operacional-diario",
            name="Resumo Operacional Diário",
            description="Principais métricas, gargalos, agentes offline e alertas do dia.",
            cadence="Diário",
            channels=["whatsapp", "email", "sistema"],
            enabled=True,
        ),
        ReportTemplate(
            id="resumo-executivo-semanal",
            name="Resumo Executivo Semanal",
            description="Tendências, eficiência, produtividade e oportunidades de automação.",
            cadence="Semanal",
            channels=["whatsapp", "email"],
            enabled=True,
        ),
        ReportTemplate(
            id="relatorio-mensal",
            name="Relatório Mensal",
            description="Evolução operacional, comparação por período, ranking de equipes e recomendações da IA.",
            cadence="Mensal",
            channels=["email", "whatsapp"],
            enabled=True,
        ),
        ReportTemplate(
            id="alertas-tempo-real",
            name="Alertas em Tempo Real",
            description="Agente caiu, sincronização falhou, gargalo crítico ou anomalia operacional.",
            cadence="Tempo real",
            channels=["sistema", "windows", "whatsapp", "email"],
            enabled=True,
        ),
    ]


@app.get("/notifications/preferences", response_model=list[NotificationPreference])
def list_notification_preferences(
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> list[NotificationPreference]:
    return [NotificationPreference.model_validate(item) for item in repo.list_notification_preferences(context)]


@app.get("/notifications/{notification_id}", response_model=Notification)
def get_notification(notification_id: UUID, context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> Notification:
    notification = repo.get_notification(context, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notification not found")
    return Notification.model_validate(notification)


@app.put("/notifications/preferences/{preference_id}", response_model=NotificationPreference)
def update_notification_preference(
    preference_id: UUID,
    request: NotificationPreferenceUpdate,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> NotificationPreference:
    updated = repo.update_notification_preference(context, preference_id, request.enabled, request.quiet_hours, request.frequency)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notification preference not found")
    return NotificationPreference.model_validate(updated)


@app.get("/ai/status", response_model=AIStatus)
def ai_status(context: AuthContext = Authenticated) -> AIStatus:
    settings = get_settings()
    return AIStatus(
        provider="hybrid",
        openaiConfigured=settings.openai_configured,
        llamaConfigured=bool(settings.llama_base_url),
        llamaProvider=settings.llama_provider,
        complexModel=settings.ai_complex_model,
        operationalModel=settings.ai_operational_model,
        routePolicy="operational->llama; executive|critical->gpt",
    )


@app.post("/ai/analyze", response_model=AnalyzeResponse)
def ai_analyze(request: AnalyzeRequest, context: AuthContext = Authenticated) -> AnalyzeResponse:
    return analyze_facts(request)


@app.post("/ai/insights/generate", response_model=AnalyzeResponse)
def ai_generate_insight(request: AnalyzeRequest, context: AuthContext = Authenticated) -> AnalyzeResponse:
    return analyze_facts(request)


@app.post("/ai/copilot", response_model=CopilotResponse)
def ai_copilot(request: CopilotRequest, context: AuthContext = Authenticated) -> CopilotResponse:
    return answer_copilot(request)


@app.get("/ai-provider-configs", response_model=list[AIProviderConfig])
def list_ai_provider_configs(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[AIProviderConfig]:
    return [AIProviderConfig.model_validate(item) for item in repo.list_ai_provider_configs(context)]


@app.get("/audit-logs", response_model=list[AuditLog])
def list_audit_logs(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[AuditLog]:
    return [AuditLog.model_validate(item) for item in repo.list_audit_logs(context)]


@app.get("/supabase/status", response_model=SupabaseStatus)
def get_supabase_status(context: AuthContext = Authenticated) -> SupabaseStatus:
    return supabase_status(get_settings())
