from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.config import Settings


class AuthTokenError(ValueError):
    pass


def load_signing_key(settings: Settings) -> bytes:
    if not settings.auth_signing_key_file:
        raise AuthTokenError("database auth signing key file is not configured")
    try:
        key = Path(settings.auth_signing_key_file).read_bytes().strip()
    except OSError as exc:
        raise AuthTokenError("database auth signing key file is unavailable") from exc
    if len(key) < 32:
        raise AuthTokenError("database auth signing key must contain at least 32 bytes")
    return key


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError) as exc:
        raise AuthTokenError("invalid token encoding") from exc


def create_access_token(
    settings: Settings,
    *,
    user_id: str,
    email: str,
    tenant_id: str,
    role: str,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "tenant_id": tenant_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.auth_token_ttl_minutes)).timestamp()),
        "iss": settings.auth_issuer,
        "aud": settings.auth_audience,
    }
    header_segment = _b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload_segment = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_segment}.{payload_segment}".encode()
    signature = hmac.new(load_signing_key(settings), signing_input, hashlib.sha256).digest()
    return f"{header_segment}.{payload_segment}.{_b64encode(signature)}"


def decode_access_token(settings: Settings, token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthTokenError("invalid token format")
    header_segment, payload_segment, signature_segment = parts
    signing_input = f"{header_segment}.{payload_segment}".encode()
    expected_signature = hmac.new(load_signing_key(settings), signing_input, hashlib.sha256).digest()
    supplied_signature = _b64decode(signature_segment)
    if not hmac.compare_digest(expected_signature, supplied_signature):
        raise AuthTokenError("invalid token signature")
    try:
        header = json.loads(_b64decode(header_segment))
        payload = json.loads(_b64decode(payload_segment))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AuthTokenError("invalid token payload") from exc
    if header != {"alg": "HS256", "typ": "JWT"}:
        raise AuthTokenError("unsupported token header")
    now = int(datetime.now(timezone.utc).timestamp())
    if payload.get("iss") != settings.auth_issuer or payload.get("aud") != settings.auth_audience:
        raise AuthTokenError("invalid token issuer or audience")
    if not isinstance(payload.get("exp"), int) or payload["exp"] <= now:
        raise AuthTokenError("token expired")
    if not all(isinstance(payload.get(key), str) and payload[key] for key in ("sub", "email", "tenant_id", "role")):
        raise AuthTokenError("token identity is incomplete")
    return payload
