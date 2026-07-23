from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


POLICY_SIGNING_ALGORITHM = "Ed25519"


def canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def public_key_fingerprint(public_key: bytes) -> str:
    return sha256_hex(public_key)


def decode_public_key(encoded: str) -> Ed25519PublicKey:
    raw = base64.b64decode(encoded, validate=True)
    if len(raw) != 32:
        raise ValueError("Ed25519 public key must contain 32 bytes")
    return Ed25519PublicKey.from_public_bytes(raw)


def request_signature_payload(method: str, path: str, timestamp: str, nonce: str, body_hash: str) -> bytes:
    return "\n".join((method.upper(), path, timestamp, nonce, body_hash)).encode("utf-8")


def verify_request_signature(
    *,
    public_key: str,
    signature: str,
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    body_hash: str,
) -> None:
    decoded_signature = base64.b64decode(signature, validate=True)
    decode_public_key(public_key).verify(
        decoded_signature,
        request_signature_payload(method, path, timestamp, nonce, body_hash),
    )


def validate_policy_document(document: dict[str, Any], profile: str) -> dict[str, Any]:
    if document.get("schemaVersion", "v1") != "v1":
        raise ValueError("unsupported policy schemaVersion")
    if document.get("profile", profile) != profile:
        raise ValueError("policy profile does not match target profile")
    modules = document.get("modules")
    if modules is not None and not isinstance(modules, dict):
        raise ValueError("policy modules must be an object")
    forbidden = {"screenCapture", "keylogger", "microphone", "webcam", "remoteShell"}
    enabled_forbidden = sorted(
        name
        for name in forbidden
        if isinstance((modules or {}).get(name), dict) and (modules or {})[name].get("enabled")
    )
    if enabled_forbidden:
        raise ValueError(f"forbidden modules cannot be enabled: {', '.join(enabled_forbidden)}")
    visual = (modules or {}).get("visual", {})
    if isinstance(visual, dict) and any(
        bool(visual.get(name)) for name in ("screenCapture", "liveSupport")
    ):
        raise ValueError("visual evidence and live support remain disabled in this release")
    if profile != "workstation" and isinstance((modules or {}).get("activity"), dict):
        if (modules or {})["activity"].get("enabled"):
            raise ValueError("activity collection is available only to workstation profile")
    intervals = document.get("intervals", {})
    if not isinstance(intervals, dict):
        raise ValueError("policy intervals must be an object")
    for name, value in intervals.items():
        if not isinstance(value, int) or value < 5 or value > 604800:
            raise ValueError(f"interval {name} must be between 5 and 604800 seconds")
    allowed_commands = document.get("allowedCommands", [])
    supported_commands = {
        "request_inventory",
        "request_diagnostics",
        "refresh_policy",
        "restart_agent",
        "rotate_credentials",
        "collect_logs",
        "run_health_check",
        "update_agent",
    }
    if not isinstance(allowed_commands, list) or not set(allowed_commands).issubset(supported_commands):
        raise ValueError("policy contains an unsupported command")
    queue = document.get("queue", {})
    if not isinstance(queue, dict):
        raise ValueError("policy queue must be an object")
    queue_limits = {
        "maxEvents": (100, 1_000_000),
        "maxBytes": (1_048_576, 10_737_418_240),
        "retentionHours": (1, 720),
        "batchSize": (1, 500),
    }
    for name, (minimum, maximum) in queue_limits.items():
        value = queue.get(name)
        if value is not None and (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < minimum
            or value > maximum
        ):
            raise ValueError(f"queue {name} must be between {minimum} and {maximum}")
    return document


def default_policy(profile: str) -> dict[str, Any]:
    workstation = profile == "workstation"
    server = profile == "server"
    collector = profile == "collector"
    return {
        "schemaVersion": "v1",
        "profile": profile,
        "modules": {
            "selfHealth": {"enabled": True},
            "inventory": {"enabled": True, "diffOnly": True},
            "systemMetrics": {"enabled": True},
            "network": {"enabled": True, "activeTests": False},
            "activity": {
                "enabled": workstation,
                "windowTitles": False,
                "idle": workstation,
                "privacyFilters": ["password", "senha", "auth", "bank", "banco"],
            },
            "printing": {"enabled": False, "documentNames": False},
            "serverChecks": {"enabled": server, "checks": []},
            "discovery": {
                "enabled": collector,
                "readOnly": True,
                "allowedNetworks": [],
                "deniedNetworks": [],
                "portScan": False,
            },
            "visual": {
                "screenCapture": False,
                "liveSupport": False,
                "privacyGuard": True,
            },
        },
        "intervals": {
            "selfHealth": 60,
            "systemMetrics": 60,
            "network": 300,
            "inventory": 21600,
            "sync": 30,
        },
        "queue": {
            "maxEvents": 10000,
            "maxBytes": 104857600,
            "retentionHours": 168,
            "batchSize": 100,
        },
        "privacy": {
            "collectTypedContent": False,
            "collectClipboard": False,
            "collectCredentials": False,
            "windowTitles": False,
        },
        "allowedCommands": [
            "request_inventory",
            "request_diagnostics",
            "refresh_policy",
            "restart_agent",
        ],
        "update": {"channel": "stable", "automatic": False},
    }


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class PolicySigner:
    def __init__(self, key_path: str | Path) -> None:
        self.key_path = Path(key_path).expanduser().resolve()

    def _load_or_create(self) -> Ed25519PrivateKey:
        if self.key_path.exists():
            raw = self.key_path.read_bytes()
            if len(raw) != 32:
                raise RuntimeError("invalid Vulcan agent policy signing key")
            return Ed25519PrivateKey.from_private_bytes(raw)

        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        private_key = Ed25519PrivateKey.generate()
        raw = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        with NamedTemporaryFile("wb", dir=self.key_path.parent, delete=False) as temporary:
            temporary.write(raw)
            temporary_path = Path(temporary.name)
        temporary_path.chmod(0o600)
        try:
            temporary_path.replace(self.key_path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
        self.key_path.chmod(0o600)
        return private_key

    def public_key_base64(self) -> str:
        raw = self._load_or_create().public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return base64.b64encode(raw).decode("ascii")

    def sign_policy(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        revision: int,
        policy: dict[str, Any],
        issued_at: datetime | None = None,
    ) -> dict[str, Any]:
        issued_at = (issued_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        payload = {
            "schemaVersion": "v1",
            "tenantId": tenant_id,
            "agentId": agent_id,
            "revision": revision,
            "issuedAt": issued_at.isoformat().replace("+00:00", "Z"),
            "policy": policy,
        }
        signature = self._load_or_create().sign(canonical_json(payload))
        return {
            **payload,
            "signatureAlgorithm": POLICY_SIGNING_ALGORITHM,
            "signature": base64.b64encode(signature).decode("ascii"),
        }


def default_policy_signing_key_path() -> str:
    return os.getenv(
        "VULCAN_AGENT_POLICY_SIGNING_KEY_FILE",
        str(Path(__file__).resolve().parents[3] / ".runtime" / "agent-policy-signing.key"),
    )
