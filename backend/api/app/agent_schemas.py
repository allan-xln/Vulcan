from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class AgentModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        from_attributes=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )


AgentProfile = Literal["workstation", "server", "collector"]


class AgentV2Status(AgentModel):
    status: Literal["ok"]
    service: str
    protocol_version: str
    enrollment: str
    authentication: str
    policy_signing_public_key: str


class EnrollmentTokenCreate(AgentModel):
    tenant_id: UUID
    profile: AgentProfile = "workstation"
    site_id: UUID | None = None
    department_id: UUID | None = None
    tags: list[str] = Field(default_factory=list, max_length=50)
    approval_mode: Literal["automatic", "manual"] = "automatic"
    expires_in_minutes: int = Field(default=60, ge=5, le=10080)
    max_uses: int = Field(default=1, ge=1, le=10000)


class EnrollmentTokenCreated(AgentModel):
    id: UUID
    tenant_id: UUID
    token: str
    token_prefix: str
    profile: AgentProfile
    expires_at: datetime
    max_uses: int
    warning: str


class EnrollmentTokenSummary(AgentModel):
    id: UUID
    tenant_id: UUID
    token_prefix: str
    profile: AgentProfile
    site_id: UUID | None = None
    department_id: UUID | None = None
    tags: list[str] = Field(default_factory=list)
    approval_mode: Literal["automatic", "manual"]
    expires_at: datetime
    max_uses: int
    use_count: int
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime


class AgentEnrollV2Request(AgentModel):
    enrollment_token: SecretStr
    public_key: str = Field(min_length=40, max_length=128)
    public_key_fingerprint: str = Field(min_length=32, max_length=128, pattern=r"^[0-9a-f]+$")
    device_fingerprint: str = Field(min_length=16, max_length=256)
    hostname: str = Field(min_length=1, max_length=255)
    operating_system: str = Field(min_length=1, max_length=255)
    architecture: str = Field(default="unknown", max_length=32)
    agent_version: str = Field(min_length=1, max_length=64)
    profile: AgentProfile
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def limit_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(str(value)) > 32768:
            raise ValueError("metadata is too large")
        return value


class SignedPolicyEnvelope(AgentModel):
    schema_version: str
    tenant_id: UUID
    agent_id: UUID
    revision: int
    issued_at: datetime
    policy: dict[str, Any]
    signature_algorithm: Literal["Ed25519"] = "Ed25519"
    signature: str


class AgentEnrollV2Response(AgentModel):
    accepted: bool
    tenant_id: UUID
    device_id: UUID
    agent_id: UUID
    status: str
    server_time: datetime
    policy_signing_public_key: str
    policy: SignedPolicyEnvelope


class AgentHeartbeatV2Request(AgentModel):
    status: Literal["online", "offline", "syncing", "degraded"] = "online"
    agent_version: str = Field(min_length=1, max_length=64)
    queue_depth: int = Field(default=0, ge=0)
    policy_revision: int = Field(default=0, ge=0)
    policy_status: Literal["pending", "applied", "rejected", "rollback"] = "pending"
    local_ip: str | None = Field(default=None, max_length=64)
    last_error: str | None = Field(default=None, max_length=2000)
    modules: dict[str, str] = Field(default_factory=dict)
    performance: dict[str, float] = Field(default_factory=dict)


class AgentCommand(AgentModel):
    command_id: UUID
    command_type: Literal[
        "request_inventory",
        "request_diagnostics",
        "refresh_policy",
        "restart_agent",
        "rotate_credentials",
        "collect_logs",
        "run_health_check",
        "update_agent",
    ]
    reason: str
    payload: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime


class AgentHeartbeatV2Response(AgentModel):
    accepted: bool
    server_time: datetime
    policy: SignedPolicyEnvelope | None = None
    commands: list[AgentCommand] = Field(default_factory=list)


class CanonicalAgentEvent(AgentModel):
    event_id: UUID
    schema_version: str = "2026-07-vulcan-event.v1"
    event_type: str = Field(min_length=2, max_length=160, pattern=r"^[a-z0-9][a-z0-9_.-]+$")
    category: str = Field(min_length=2, max_length=80)
    severity: Literal["debug", "info", "notice", "warning", "error", "critical"] = "info"
    occurred_at: datetime
    actor: dict[str, Any] = Field(default_factory=dict)
    device: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    message: str = Field(min_length=1, max_length=4000)
    technical_message: str | None = Field(default=None, max_length=8000)
    fingerprint: str = Field(min_length=8, max_length=256)
    correlation_id: str | None = Field(default=None, max_length=256)
    causation_id: str | None = Field(default=None, max_length=256)
    confidence: float | None = Field(default=None, ge=0, le=1)
    privacy_classification: Literal["operational", "personal", "sensitive", "restricted"] = "operational"
    retention_policy: str = Field(default="standard", min_length=1, max_length=80)
    offline_buffered: bool = False
    extensions: dict[str, Any] = Field(default_factory=dict)


class AgentEventsV2Request(AgentModel):
    batch_id: UUID
    events: list[CanonicalAgentEvent] = Field(min_length=1, max_length=500)


class AgentEventsV2Response(AgentModel):
    accepted: bool
    received: int
    stored: int
    duplicates: int
    acknowledged_event_ids: list[UUID]
    server_time: datetime


class AgentPolicyCreate(AgentModel):
    tenant_id: UUID
    name: str = Field(min_length=2, max_length=160)
    profile: AgentProfile
    scope_type: Literal["tenant", "site", "department", "device"] = "tenant"
    site_id: UUID | None = None
    department_id: UUID | None = None
    device_id: UUID | None = None
    document: dict[str, Any]
    enabled: bool = True


class AgentPolicySummary(AgentModel):
    id: UUID
    tenant_id: UUID
    name: str
    profile: AgentProfile
    scope_type: str
    site_id: UUID | None = None
    department_id: UUID | None = None
    device_id: UUID | None = None
    revision: int
    schema_version: str
    document: dict[str, Any]
    enabled: bool
    created_at: datetime
    updated_at: datetime


class ManagedAgent(AgentModel):
    id: UUID
    tenant_id: UUID
    device_id: UUID
    hostname: str
    profile: AgentProfile
    operating_system: str
    architecture: str | None = None
    agent_version: str | None = None
    status: str
    policy_revision: int
    policy_status: str
    queue_depth: int
    last_seen_at: datetime | None = None
    last_ip: str | None = None
    site_id: UUID | None = None
    site_name: str | None = None
    owner: str | None = None
    department: str | None = None
    modules: dict[str, str] = Field(default_factory=dict)
    last_error: str | None = None
    created_at: datetime


class AgentCommandCreate(AgentModel):
    tenant_id: UUID
    command_type: Literal[
        "request_inventory",
        "request_diagnostics",
        "refresh_policy",
        "restart_agent",
        "rotate_credentials",
        "collect_logs",
        "run_health_check",
        "update_agent",
    ]
    reason: str = Field(min_length=5, max_length=1000)
    payload: dict[str, Any] = Field(default_factory=dict)
    expires_in_minutes: int = Field(default=15, ge=1, le=1440)


class AgentCommandResult(AgentModel):
    status: Literal["running", "succeeded", "failed"]
    output_summary: str | None = Field(default=None, max_length=16000)


class AgentIdentityAction(AgentModel):
    reason: str = Field(min_length=5, max_length=1000)
