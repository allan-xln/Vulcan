from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
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
    HealthResponse,
    HierarchyNode,
    IntegrationStatus,
    Insight,
    LoginRequest,
    LoginResponse,
    Membership,
    MembershipCreate,
    MembershipManagerUpdate,
    MembershipUpdate,
    Metric,
    MetricsDetailedRow,
    Notification,
    NotificationPreference,
    NotificationPreferenceUpdate,
    NotificationSendRequest,
    NotificationSendResponse,
    NotificationSchedule,
    OperationalIntelligence,
    OperationalMetric,
    ReportTemplate,
    Role,
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
from app.whatsapp import WhatsAppConnection, WhatsAppNotificationService


app = FastAPI(title="Vulcan API", version="0.1.0")
AGENT_GATEWAY_VERSION = "0.1.0"
settings = get_settings()

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
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="agent persistence unavailable") from exc


@app.post("/agent/heartbeat", response_model=AgentHeartbeatResponse)
def agent_heartbeat(request: AgentHeartbeatRequest, repo: VulcanRepository = Depends(repository)) -> AgentHeartbeatResponse:
    require_agent_enrollment_token(request.enrollment_token)
    try:
        return repo.agent_heartbeat(request)
    except PsycopgError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="agent persistence unavailable") from exc


@app.post("/agent/events", response_model=AgentEventsResponse)
def agent_events(request: AgentEventsRequest, repo: VulcanRepository = Depends(repository)) -> AgentEventsResponse:
    require_agent_enrollment_token(request.enrollment_token)
    try:
        return repo.agent_events(request)
    except PsycopgError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="agent persistence unavailable") from exc


@app.post("/agent/sync", response_model=AgentEventsResponse)
def agent_sync(request: AgentEventsRequest, repo: VulcanRepository = Depends(repository)) -> AgentEventsResponse:
    require_agent_enrollment_token(request.enrollment_token)
    try:
        return repo.agent_events(request)
    except PsycopgError as exc:
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
    app: str | None = Query(default=None),
) -> list[MetricsDetailedRow]:
    rows = repo.list_detailed_metrics(context, period=period, team_id=team_id, membership_id=membership_id, device_id=device_id, app=app)
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
    app: str | None = Query(default=None),
) -> Response:
    if format not in {"csv", "excel"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="format must be csv or excel")
    content = repo.export_metrics_csv(context, period=period, team_id=team_id, membership_id=membership_id, device_id=device_id, app=app)
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


@app.get("/notifications", response_model=list[Notification])
def list_notifications(context: AuthContext = Authenticated, repo: VulcanRepository = Depends(repository)) -> list[Notification]:
    return [Notification.model_validate(item) for item in repo.list_notifications(context)]


@app.post("/notifications/test", response_model=NotificationSendResponse)
def test_notification(
    request: NotificationSendRequest,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> NotificationSendResponse:
    service = NotificationService()
    delivery = service.send(request.channel, NotificationPayload(title=request.title, message=request.message, tenant_id=str(request.tenant_id)))
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
    service = NotificationService()
    delivery = service.send(request.channel, NotificationPayload(title=request.title, message=request.message, tenant_id=str(request.tenant_id)))
    try:
        return repo.create_notification_record(context, request, delivery.status, delivery.provider_result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


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
def whatsapp_test(request: ConnectionTestRequest, context: AuthContext = Authenticated) -> ConnectionTestResponse:
    service = WhatsAppNotificationService()
    delivery = service.send_alert(
        tenant_id=str(request.tenant_id),
        title="Teste do Vulcan",
        message=request.message or "Mensagem de teste do Canal Oficial Vulcan.",
        to=request.destination,
    )
    return ConnectionTestResponse(ok=delivery.ok, status=delivery.status, providerResult=delivery.provider_result, message=delivery.message)


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


@app.get("/notifications/schedules", response_model=list[NotificationSchedule])
def notification_schedules(context: AuthContext = Authenticated) -> list[NotificationSchedule]:
    return [
        NotificationSchedule(
            id="imediato-alertas",
            name="Alertas críticos em tempo real",
            recurrence="Imediatamente",
            timezone="America/Sao_Paulo",
            daysOfWeek=["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"],
            times=["tempo real"],
            reportType="alerta_tempo_real",
            recipients=["Supervisor", "Gerente", "Diretor"],
            channels=["sistema", "windows", "whatsapp", "email"],
            enabled=True,
        ),
        NotificationSchedule(
            id="resumo-diario",
            name="Resumo operacional diário",
            recurrence="Diário",
            timezone="America/Sao_Paulo",
            daysOfWeek=["segunda", "terça", "quarta", "quinta", "sexta"],
            times=["08:00", "18:00"],
            reportType="resumo_operacional_diario",
            recipients=["Gerente", "Coordenador"],
            channels=["whatsapp", "email"],
            enabled=True,
        ),
        NotificationSchedule(
            id="executivo-semanal",
            name="Resumo executivo semanal",
            recurrence="Semanal",
            timezone="America/Sao_Paulo",
            daysOfWeek=["segunda"],
            times=["07:30"],
            reportType="resumo_executivo_semanal",
            recipients=["Diretor", "Dono da empresa"],
            channels=["whatsapp", "email"],
            enabled=True,
        ),
    ]


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


@app.put("/notifications/preferences/{preference_id}", response_model=NotificationPreference)
def update_notification_preference(
    preference_id: UUID,
    request: NotificationPreferenceUpdate,
    context: AuthContext = Authenticated,
    repo: VulcanRepository = Depends(repository),
) -> NotificationPreference:
    updated = repo.update_notification_preference(context, preference_id, request.enabled)
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
