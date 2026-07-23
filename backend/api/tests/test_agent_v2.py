import base64
import hashlib
from datetime import datetime, timezone

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.agent_security import (
    PolicySigner,
    canonical_json,
    default_policy,
    request_signature_payload,
    validate_policy_document,
    verify_request_signature,
)
from app.agent_repository import _event_data_origin
from app.agent_schemas import CanonicalAgentEvent


def public_key_base64(private_key: Ed25519PrivateKey) -> str:
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return base64.b64encode(raw).decode("ascii")


def test_agent_request_signature_covers_method_path_time_nonce_and_body() -> None:
    private_key = Ed25519PrivateKey.generate()
    body = b'{"status":"online"}'
    timestamp = "1784779200"
    nonce = "nonce-with-enough-entropy"
    body_hash = hashlib.sha256(body).hexdigest()
    signature = private_key.sign(
        request_signature_payload("POST", "/agent/v2/heartbeat", timestamp, nonce, body_hash)
    )

    verify_request_signature(
        public_key=public_key_base64(private_key),
        signature=base64.b64encode(signature).decode("ascii"),
        method="POST",
        path="/agent/v2/heartbeat",
        timestamp=timestamp,
        nonce=nonce,
        body_hash=body_hash,
    )

    with pytest.raises(InvalidSignature):
        verify_request_signature(
            public_key=public_key_base64(private_key),
            signature=base64.b64encode(signature).decode("ascii"),
            method="POST",
            path="/agent/v2/events",
            timestamp=timestamp,
            nonce=nonce,
            body_hash=body_hash,
        )


def test_policy_signing_key_is_persistent_and_signature_is_verifiable(tmp_path) -> None:
    key_path = tmp_path / "agent-policy-signing.key"
    signer = PolicySigner(key_path)
    issued_at = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
    envelope = signer.sign_policy(
        tenant_id="00000000-0000-0000-0000-000000000301",
        agent_id="00000000-0000-0000-0000-000000000501",
        revision=7,
        policy=default_policy("workstation"),
        issued_at=issued_at,
    )

    signed_payload = {
        key: envelope[key]
        for key in ("schemaVersion", "tenantId", "agentId", "revision", "issuedAt", "policy")
    }
    public_key = base64.b64decode(signer.public_key_base64())
    signature = base64.b64decode(envelope["signature"])
    signer_public_key = Ed25519PrivateKey.from_private_bytes(key_path.read_bytes()).public_key()
    assert signer_public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ) == public_key
    signer_public_key.verify(signature, canonical_json(signed_payload))
    assert key_path.stat().st_mode & 0o077 == 0
    assert PolicySigner(key_path).public_key_base64() == signer.public_key_base64()


def test_safe_policy_defaults_disable_visual_capture_and_arbitrary_discovery() -> None:
    workstation = default_policy("workstation")
    server = default_policy("server")
    collector = default_policy("collector")

    assert workstation["modules"]["activity"]["enabled"] is True
    assert server["modules"]["activity"]["enabled"] is False
    assert collector["modules"]["discovery"]["readOnly"] is True
    assert collector["modules"]["discovery"]["allowedNetworks"] == []
    assert collector["modules"]["discovery"]["portScan"] is False
    assert workstation["modules"]["visual"]["screenCapture"] is False
    assert workstation["privacy"]["collectTypedContent"] is False


def test_policy_validator_rejects_invasive_or_profile_incompatible_modules() -> None:
    invasive = default_policy("workstation")
    invasive["modules"]["keylogger"] = {"enabled": True}
    with pytest.raises(ValueError, match="forbidden"):
        validate_policy_document(invasive, "workstation")

    server_activity = default_policy("server")
    server_activity["modules"]["activity"]["enabled"] = True
    with pytest.raises(ValueError, match="workstation"):
        validate_policy_document(server_activity, "server")

    unbounded_queue = default_policy("workstation")
    unbounded_queue["queue"]["maxBytes"] = 50_000_000_000
    with pytest.raises(ValueError, match="maxBytes"):
        validate_policy_document(unbounded_queue, "workstation")


def test_simulated_agent_events_are_explicitly_classified() -> None:
    base = {
        "eventId": "00000000-0000-0000-0000-000000000801",
        "eventType": "simulation.agent.metric",
        "category": "simulation",
        "occurredAt": "2026-07-23T12:00:00Z",
        "message": "Evento simulado para teste de carga.",
        "fingerprint": "simulation-agent-0001",
    }
    simulated = CanonicalAgentEvent.model_validate(
        {**base, "extensions": {"dataOrigin": "simulated"}}
    )
    real = CanonicalAgentEvent.model_validate(base)

    assert _event_data_origin(simulated) == "simulated"
    assert _event_data_origin(real) == "real"
