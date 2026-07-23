from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status

from app.agent_repository import (
    AgentAuthorizationError,
    AgentConflictError,
    AgentPrincipal,
    AgentV2Repository,
)
from app.agent_schemas import (
    AgentCommandCreate,
    AgentCommandResult,
    AgentEnrollV2Request,
    AgentEnrollV2Response,
    AgentEventsV2Request,
    AgentEventsV2Response,
    AgentHeartbeatV2Request,
    AgentHeartbeatV2Response,
    AgentIdentityAction,
    AgentPolicyCreate,
    AgentPolicySummary,
    AgentV2Status,
    EnrollmentTokenCreate,
    EnrollmentTokenCreated,
    EnrollmentTokenSummary,
    ManagedAgent,
    SignedPolicyEnvelope,
)
from app.security import AuthContext, Authenticated


router = APIRouter(prefix="/agent/v2", tags=["Vulcan Agent v2"])


def repository() -> AgentV2Repository:
    return AgentV2Repository()


async def authenticated_agent(
    request: Request,
    x_vulcan_agent_id: Annotated[str, Header(alias="X-Vulcan-Agent-Id")],
    x_vulcan_timestamp: Annotated[str, Header(alias="X-Vulcan-Timestamp")],
    x_vulcan_nonce: Annotated[str, Header(alias="X-Vulcan-Nonce")],
    x_vulcan_content_sha256: Annotated[str, Header(alias="X-Vulcan-Content-SHA256")],
    x_vulcan_signature: Annotated[str, Header(alias="X-Vulcan-Signature")],
    agent_repository: AgentV2Repository = Depends(repository),
) -> AgentPrincipal:
    try:
        agent_id = UUID(x_vulcan_agent_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid agent identity") from exc
    try:
        return agent_repository.authenticate(
            agent_id=agent_id,
            timestamp=x_vulcan_timestamp,
            nonce=x_vulcan_nonce,
            body_hash=x_vulcan_content_sha256,
            signature=x_vulcan_signature,
            method=request.method,
            path=request.url.path,
            body=await request.body(),
        )
    except AgentAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def _admin_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AgentAuthorizationError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, AgentConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, RuntimeError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/status", response_model=AgentV2Status)
def agent_v2_status(agent_repository: AgentV2Repository = Depends(repository)) -> AgentV2Status:
    return AgentV2Status(
        status="ok",
        service="vulcan-agent-gateway",
        protocolVersion="v2",
        enrollment="one-time-token",
        authentication="Ed25519",
        policySigningPublicKey=agent_repository.signer.public_key_base64(),
    )


@router.post("/enroll", response_model=AgentEnrollV2Response, status_code=status.HTTP_201_CREATED)
def enroll_agent(
    payload: AgentEnrollV2Request,
    agent_repository: AgentV2Repository = Depends(repository),
) -> AgentEnrollV2Response:
    try:
        return AgentEnrollV2Response.model_validate(agent_repository.enroll(payload))
    except AgentAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AgentConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise _admin_error(exc) from exc


@router.get("/policy", response_model=SignedPolicyEnvelope)
def effective_policy(
    principal: AgentPrincipal = Depends(authenticated_agent),
    agent_repository: AgentV2Repository = Depends(repository),
) -> SignedPolicyEnvelope:
    return SignedPolicyEnvelope.model_validate(agent_repository.policy(principal))


@router.post("/heartbeat", response_model=AgentHeartbeatV2Response)
def heartbeat(
    payload: AgentHeartbeatV2Request,
    http_request: Request,
    principal: AgentPrincipal = Depends(authenticated_agent),
    agent_repository: AgentV2Repository = Depends(repository),
) -> AgentHeartbeatV2Response:
    remote_ip = http_request.client.host if http_request.client else None
    return AgentHeartbeatV2Response.model_validate(
        agent_repository.heartbeat(principal, payload, remote_ip)
    )


@router.post("/events", response_model=AgentEventsV2Response)
def store_events(
    payload: AgentEventsV2Request,
    principal: AgentPrincipal = Depends(authenticated_agent),
    agent_repository: AgentV2Repository = Depends(repository),
) -> AgentEventsV2Response:
    return AgentEventsV2Response.model_validate(agent_repository.store_events(principal, payload))


@router.post(
    "/commands/{command_id}/result",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def command_result(
    command_id: UUID,
    payload: AgentCommandResult,
    principal: AgentPrincipal = Depends(authenticated_agent),
    agent_repository: AgentV2Repository = Depends(repository),
) -> Response:
    try:
        agent_repository.complete_command(principal, command_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/unenroll",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def unenroll_agent(
    payload: AgentIdentityAction,
    principal: AgentPrincipal = Depends(authenticated_agent),
    agent_repository: AgentV2Repository = Depends(repository),
) -> Response:
    try:
        agent_repository.self_revoke(principal, payload.reason)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/admin/agents", response_model=list[ManagedAgent])
def list_agents(
    profile: str | None = Query(default=None),
    agent_status: str | None = Query(default=None, alias="status"),
    context: AuthContext = Authenticated,
    agent_repository: AgentV2Repository = Depends(repository),
) -> list[ManagedAgent]:
    try:
        return [
            ManagedAgent.model_validate(row)
            for row in agent_repository.list_agents(context, profile=profile, status=agent_status)
        ]
    except Exception as exc:
        raise _admin_error(exc) from exc


@router.get("/admin/enrollment-tokens", response_model=list[EnrollmentTokenSummary])
def list_enrollment_tokens(
    context: AuthContext = Authenticated,
    agent_repository: AgentV2Repository = Depends(repository),
) -> list[EnrollmentTokenSummary]:
    try:
        return [
            EnrollmentTokenSummary.model_validate(row)
            for row in agent_repository.list_enrollment_tokens(context)
        ]
    except Exception as exc:
        raise _admin_error(exc) from exc


@router.post(
    "/admin/enrollment-tokens",
    response_model=EnrollmentTokenCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_enrollment_token(
    payload: EnrollmentTokenCreate,
    context: AuthContext = Authenticated,
    agent_repository: AgentV2Repository = Depends(repository),
) -> EnrollmentTokenCreated:
    try:
        return EnrollmentTokenCreated.model_validate(
            agent_repository.create_enrollment_token(context, payload)
        )
    except Exception as exc:
        raise _admin_error(exc) from exc


@router.post(
    "/admin/enrollment-tokens/{token_id}/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def revoke_enrollment_token(
    token_id: UUID,
    payload: AgentIdentityAction,
    context: AuthContext = Authenticated,
    agent_repository: AgentV2Repository = Depends(repository),
) -> Response:
    try:
        agent_repository.revoke_enrollment_token(context, token_id, payload.reason)
    except Exception as exc:
        raise _admin_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/admin/policies", response_model=list[AgentPolicySummary])
def list_policies(
    context: AuthContext = Authenticated,
    agent_repository: AgentV2Repository = Depends(repository),
) -> list[AgentPolicySummary]:
    try:
        return [
            AgentPolicySummary.model_validate(row)
            for row in agent_repository.list_policies(context)
        ]
    except Exception as exc:
        raise _admin_error(exc) from exc


@router.post("/admin/policies", response_model=AgentPolicySummary, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: AgentPolicyCreate,
    context: AuthContext = Authenticated,
    agent_repository: AgentV2Repository = Depends(repository),
) -> AgentPolicySummary:
    try:
        return AgentPolicySummary.model_validate(agent_repository.create_policy(context, payload))
    except Exception as exc:
        raise _admin_error(exc) from exc


@router.post(
    "/admin/agents/{agent_id}/approve",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def approve_agent(
    agent_id: UUID,
    payload: AgentIdentityAction,
    context: AuthContext = Authenticated,
    agent_repository: AgentV2Repository = Depends(repository),
) -> Response:
    try:
        agent_repository.set_identity_status(
            context,
            agent_id,
            status="approved",
            reason=payload.reason,
        )
    except Exception as exc:
        raise _admin_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/admin/agents/{agent_id}/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
)
def revoke_agent(
    agent_id: UUID,
    payload: AgentIdentityAction,
    context: AuthContext = Authenticated,
    agent_repository: AgentV2Repository = Depends(repository),
) -> Response:
    try:
        agent_repository.set_identity_status(
            context,
            agent_id,
            status="revoked",
            reason=payload.reason,
        )
    except Exception as exc:
        raise _admin_error(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/admin/agents/{agent_id}/commands", status_code=status.HTTP_201_CREATED)
def create_command(
    agent_id: UUID,
    payload: AgentCommandCreate,
    context: AuthContext = Authenticated,
    agent_repository: AgentV2Repository = Depends(repository),
) -> dict:
    try:
        row = agent_repository.create_command(context, agent_id, payload)
        return {
            "commandId": str(row["id"]),
            "status": row["status"],
            "commandType": row["command_type"],
            "expiresAt": row["expires_at"],
        }
    except Exception as exc:
        raise _admin_error(exc) from exc
