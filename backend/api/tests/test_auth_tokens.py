import base64
import hashlib
import hmac
import json
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.auth_tokens import AuthTokenError, create_access_token, decode_access_token
from app.config import get_settings


def _settings(tmp_path):
    key_file = tmp_path / "auth-signing.key"
    key_file.write_bytes(b"vulcan-test-auth-key-with-at-least-32-bytes")
    return replace(
        get_settings(),
        auth_provider="database",
        auth_signing_key_file=str(key_file),
        auth_issuer="vulcan-test",
        auth_audience="vulcan-test-web",
    )


def _encode(value: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).decode().rstrip("=")


def _expired_token(settings) -> str:
    header = _encode({"alg": "HS256", "typ": "JWT"})
    payload = _encode(
        {
            "sub": "00000000-0000-0000-0000-000000000001",
            "email": "test@example.invalid",
            "tenant_id": "00000000-0000-0000-0000-000000000301",
            "role": "read_only",
            "iat": 1,
            "exp": int(datetime.now(timezone.utc).timestamp()) - 1,
            "iss": settings.auth_issuer,
            "aud": settings.auth_audience,
        }
    )
    signing_input = f"{header}.{payload}".encode()
    signature = hmac.new(
        b"vulcan-test-auth-key-with-at-least-32-bytes",
        signing_input,
        hashlib.sha256,
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{header}.{payload}.{encoded_signature}"


def test_database_access_token_round_trip(tmp_path) -> None:
    settings = _settings(tmp_path)
    token = create_access_token(
        settings,
        user_id="00000000-0000-0000-0000-000000000001",
        email="test@example.invalid",
        tenant_id="00000000-0000-0000-0000-000000000301",
        role="read_only",
    )

    payload = decode_access_token(settings, token)

    assert payload["tenant_id"] == "00000000-0000-0000-0000-000000000301"
    assert payload["role"] == "read_only"


def test_database_access_token_rejects_tampering(tmp_path) -> None:
    settings = _settings(tmp_path)
    token = create_access_token(
        settings,
        user_id="00000000-0000-0000-0000-000000000001",
        email="test@example.invalid",
        tenant_id="00000000-0000-0000-0000-000000000301",
        role="read_only",
    )
    parts = token.split(".")
    parts[1] = parts[1][:-1] + ("A" if parts[1][-1] != "A" else "B")

    with pytest.raises(AuthTokenError, match="signature"):
        decode_access_token(settings, ".".join(parts))


def test_database_access_token_rejects_expiration(tmp_path) -> None:
    settings = _settings(tmp_path)

    with pytest.raises(AuthTokenError, match="expired"):
        decode_access_token(settings, _expired_token(settings))


def test_database_access_token_requires_strong_file_key(tmp_path) -> None:
    key_file = tmp_path / "short.key"
    key_file.write_text("short")
    settings = replace(get_settings(), auth_signing_key_file=str(key_file))

    with pytest.raises(AuthTokenError, match="at least 32 bytes"):
        create_access_token(
            settings,
            user_id="00000000-0000-0000-0000-000000000001",
            email="test@example.invalid",
            tenant_id="00000000-0000-0000-0000-000000000301",
            role="read_only",
        )
