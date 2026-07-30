from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from app.platform_repository import PlatformAuthorizationError, PlatformRepository, get_platform_repository
from app.platform_schemas import (
    Asset,
    AssetCreate,
    CanonicalEventCreate,
    CanonicalEventResult,
    DiscoveryPolicy,
    DiscoveryPolicyCreate,
    DiscoveryPolicyStateUpdate,
    DiscoveryRun,
    DiscoveryRunCreate,
    EventSimulationRequest,
    EventSimulationResponse,
    Incident,
    InfrastructureNetwork,
    InfrastructureNetworkCreate,
    InfrastructureOverview,
    IntegrationAdapterDefinition,
    IntegrationSyncResult,
    PlatformHealth,
    Site,
    SiteCreate,
    SiteUpdate,
    TenantModule,
    TimelinePage,
    VersionInfo,
    WallboardPlaylist,
    WallboardPlaylistItemsUpdate,
    WallboardPlaylistUpdate,
    WallboardProfile,
    WallboardProfileUpdate,
    WallboardSnapshot,
)
from app.security import AuthContext, Authenticated


router = APIRouter(tags=["Vulcan Platform"])


def platform_repository() -> PlatformRepository:
    return get_platform_repository()


def _bad_request(exc: ValueError) -> HTTPException:
    error_status = (
        status.HTTP_403_FORBIDDEN
        if isinstance(exc, PlatformAuthorizationError)
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=error_status, detail=str(exc))


@router.get("/healthz", response_model=PlatformHealth)
def healthz(repo: PlatformRepository = Depends(platform_repository)) -> PlatformHealth:
    return repo.health()


@router.get("/livez", response_model=PlatformHealth)
def livez() -> PlatformHealth:
    from app.platform_schemas import DependencyCheck

    return PlatformHealth(
        status="ok",
        service="vulcan-api",
        timestamp=datetime.now(timezone.utc),
        dataOrigin="real",
        checks=[DependencyCheck(name="process", status="ok", detail="Processo FastAPI está respondendo.")],
    )


@router.get("/readyz", response_model=PlatformHealth)
def readyz(repo: PlatformRepository = Depends(platform_repository)):
    health = repo.health()
    if health.status == "unavailable":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health.model_dump(mode="json", by_alias=True),
        )
    return health


@router.get("/version", response_model=VersionInfo)
def version() -> VersionInfo:
    return VersionInfo(
        service="vulcan-api",
        version=os.getenv("VULCAN_BUILD_VERSION", "0.2.0-dev"),
        commit=os.getenv("VULCAN_COMMIT_SHA", "local"),
        build=os.getenv("VULCAN_BUILD_ID", "development"),
    )


@router.get("/platform/modules", response_model=list[TenantModule])
def list_modules(
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> list[TenantModule]:
    return [TenantModule.model_validate(item) for item in repo.list_modules(context)]


@router.get("/infrastructure/overview", response_model=InfrastructureOverview)
def infrastructure_overview(
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> InfrastructureOverview:
    try:
        return repo.infrastructure_overview(context)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/infrastructure/sites", response_model=list[Site])
def list_sites(
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> list[Site]:
    try:
        return [Site.model_validate(item) for item in repo.list_sites(context)]
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/infrastructure/sites", response_model=Site, status_code=status.HTTP_201_CREATED)
def create_site(
    request: SiteCreate,
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> Site:
    try:
        return Site.model_validate(repo.create_site(context, request))
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.patch("/infrastructure/sites/{site_id}", response_model=Site)
def update_site(
    site_id: UUID,
    request: SiteUpdate,
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> Site:
    try:
        return Site.model_validate(repo.update_site(context, site_id, request))
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/infrastructure/networks", response_model=list[InfrastructureNetwork])
def list_networks(
    site_id: UUID | None = Query(default=None, alias="siteId"),
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> list[InfrastructureNetwork]:
    try:
        return [InfrastructureNetwork.model_validate(item) for item in repo.list_networks(context, site_id)]
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/infrastructure/networks", response_model=InfrastructureNetwork, status_code=status.HTTP_201_CREATED)
def create_network(
    request: InfrastructureNetworkCreate,
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> InfrastructureNetwork:
    try:
        return InfrastructureNetwork.model_validate(repo.create_network(context, request))
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/infrastructure/assets", response_model=list[Asset])
def list_assets(
    site_id: UUID | None = Query(default=None, alias="siteId"),
    asset_type: str | None = Query(default=None, alias="assetType"),
    asset_status: str | None = Query(default=None, alias="status"),
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> list[Asset]:
    try:
        return [
            Asset.model_validate(item)
            for item in repo.list_assets(context, site_id=site_id, asset_type=asset_type, status=asset_status)
        ]
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/infrastructure/assets", response_model=Asset, status_code=status.HTTP_201_CREATED)
def create_asset(
    request: AssetCreate,
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> Asset:
    try:
        return Asset.model_validate(repo.create_asset(context, request))
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/timeline", response_model=TimelinePage)
def timeline(
    limit: int = Query(default=100, ge=1, le=500),
    cursor: str | None = None,
    site_id: UUID | None = Query(default=None, alias="siteId"),
    asset_id: UUID | None = Query(default=None, alias="assetId"),
    agent_id: UUID | None = Query(default=None, alias="agentId"),
    membership_id: UUID | None = Query(default=None, alias="membershipId"),
    incident_id: UUID | None = Query(default=None, alias="incidentId"),
    category: str | None = None,
    severity: str | None = None,
    source: str | None = None,
    search: str | None = Query(default=None, max_length=200),
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> TimelinePage:
    try:
        return repo.list_timeline(
            context,
            limit=limit,
            cursor=cursor,
            site_id=site_id,
            asset_id=asset_id,
            agent_id=agent_id,
            membership_id=membership_id,
            incident_id=incident_id,
            category=category,
            severity=severity,
            source=source,
            search=search,
        )
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/events", response_model=CanonicalEventResult)
def ingest_canonical_event(
    request: CanonicalEventCreate,
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> CanonicalEventResult:
    try:
        return repo.ingest_event(context, request)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post("/events/simulate", response_model=EventSimulationResponse)
def simulate_events(
    request: EventSimulationRequest,
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> EventSimulationResponse:
    try:
        return repo.simulate_events(context, request)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/realtime/events")
async def realtime_events(
    http_request: Request,
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> StreamingResponse:
    poll_seconds = max(0.5, min(float(os.getenv("VULCAN_REALTIME_POLL_SECONDS", "2")), 30))

    async def stream():
        cursor_time = datetime.now(timezone.utc)
        cursor_id = UUID(int=0)
        ready_payload = json.dumps(
            {"status": "ready", "tenantId": str(context.tenant_id), "timestamp": cursor_time.isoformat()}
        )
        yield f"event: ready\ndata: {ready_payload}\n\n"
        while not await http_request.is_disconnected():
            events = repo.received_events_after(context, cursor_time, cursor_id)
            for event in events:
                cursor_time = event.created_at
                cursor_id = event.event_id
                payload = event.model_dump_json(by_alias=True)
                yield f"id: {event.event_id}\nevent: timeline\ndata: {payload}\n\n"
            if not events:
                yield ": keepalive\n\n"
            await asyncio.sleep(poll_seconds)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/infrastructure/discovery/policies", response_model=list[DiscoveryPolicy])
def list_discovery_policies(
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> list[DiscoveryPolicy]:
    try:
        return [DiscoveryPolicy.model_validate(item) for item in repo.list_discovery_policies(context)]
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post(
    "/infrastructure/discovery/policies",
    response_model=DiscoveryPolicy,
    status_code=status.HTTP_201_CREATED,
)
def create_discovery_policy(
    request: DiscoveryPolicyCreate,
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> DiscoveryPolicy:
    try:
        return DiscoveryPolicy.model_validate(repo.create_discovery_policy(context, request))
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.patch(
    "/infrastructure/discovery/policies/{policy_id}",
    response_model=DiscoveryPolicy,
)
def update_discovery_policy_state(
    policy_id: UUID,
    request: DiscoveryPolicyStateUpdate,
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> DiscoveryPolicy:
    try:
        return DiscoveryPolicy.model_validate(repo.update_discovery_policy_state(context, policy_id, request))
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/infrastructure/discovery/runs", response_model=list[DiscoveryRun])
def list_discovery_runs(
    limit: int = Query(default=100, ge=1, le=500),
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> list[DiscoveryRun]:
    try:
        return [DiscoveryRun.model_validate(item) for item in repo.list_discovery_runs(context, limit)]
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.post(
    "/infrastructure/discovery/runs",
    response_model=DiscoveryRun,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_discovery_run(
    request: DiscoveryRunCreate,
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> DiscoveryRun:
    try:
        return DiscoveryRun.model_validate(repo.create_discovery_run(context, request))
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/infrastructure/integrations/catalog", response_model=list[IntegrationAdapterDefinition])
def integration_catalog(
    _context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> list[IntegrationAdapterDefinition]:
    return [IntegrationAdapterDefinition.model_validate(item) for item in repo.adapter_catalog()]


@router.post(
    "/infrastructure/integrations/{adapter_type}/sync",
    response_model=IntegrationSyncResult,
)
def sync_integration(
    adapter_type: str,
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> IntegrationSyncResult:
    try:
        return repo.sync_integration(context, adapter_type)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/wallboards/profiles", response_model=list[WallboardProfile])
def list_wallboard_profiles(
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> list[WallboardProfile]:
    try:
        return repo.list_wallboard_profiles(context)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.patch("/wallboards/profiles/{profile_id}", response_model=WallboardProfile)
def update_wallboard_profile(
    profile_id: UUID,
    request: WallboardProfileUpdate,
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> WallboardProfile:
    try:
        return repo.update_wallboard_profile(context, profile_id, request)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.patch("/wallboards/playlists/{playlist_id}", response_model=WallboardPlaylist)
def update_wallboard_playlist(
    playlist_id: UUID,
    request: WallboardPlaylistUpdate,
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> WallboardPlaylist:
    try:
        repo.update_wallboard_playlist(context, playlist_id, request)
        profiles = repo.list_wallboard_profiles(context)
        for profile in profiles:
            for playlist in profile.playlists:
                if playlist.id == playlist_id:
                    return playlist
        raise ValueError("wallboard playlist not found in active tenant")
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.patch("/wallboards/playlists/{playlist_id}/items", response_model=WallboardPlaylist)
def update_wallboard_playlist_items(
    playlist_id: UUID,
    request: WallboardPlaylistItemsUpdate,
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> WallboardPlaylist:
    try:
        repo.update_wallboard_playlist_items(context, playlist_id, request)
        profiles = repo.list_wallboard_profiles(context)
        for profile in profiles:
            for playlist in profile.playlists:
                if playlist.id == playlist_id:
                    return playlist
        raise ValueError("wallboard playlist not found in active tenant")
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/wallboards/snapshot", response_model=WallboardSnapshot)
def wallboard_snapshot(
    wallboard_type: str = Query(default="workforce", alias="type"),
    site_id: UUID | None = Query(default=None, alias="siteId"),
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> WallboardSnapshot:
    try:
        return repo.wallboard_snapshot(context, wallboard_type, site_id)
    except ValueError as exc:
        raise _bad_request(exc) from exc


@router.get("/incidents", response_model=list[Incident])
def list_incidents(
    incident_status: str | None = Query(default=None, alias="status"),
    context: AuthContext = Authenticated,
    repo: PlatformRepository = Depends(platform_repository),
) -> list[Incident]:
    try:
        return [Incident.model_validate(item) for item in repo.list_incidents(context, incident_status)]
    except ValueError as exc:
        raise _bad_request(exc) from exc
