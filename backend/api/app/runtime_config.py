from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RUNTIME_CONFIG_PATH = PROJECT_ROOT / ".runtime" / "integration-secrets.json"

ALLOWED_RUNTIME_KEYS = {
    "EVOLUTION_API_KEY",
    "EVOLUTION_BASE_URL",
    "EVOLUTION_ENABLED",
    "EVOLUTION_INSTANCE_NAME",
    "EVOLUTION_WEBHOOK_TOKEN",
    "ROOT_WHATSAPP_ENABLED",
    "ROOT_WHATSAPP_MOCK_MODE",
    "ROOT_WHATSAPP_NAME",
    "ROOT_WHATSAPP_NUMBER",
    "ROOT_WHATSAPP_PROVIDER",
    "WHATSAPP_EMAIL_FALLBACK_ENABLED",
    "WHATSAPP_IN_APP_FALLBACK_ENABLED",
    "WHATSAPP_REQUIRE_OPT_IN",
}


def runtime_config_path() -> Path:
    configured = os.getenv("VULCAN_RUNTIME_CONFIG_FILE")
    return Path(configured).expanduser().resolve() if configured else DEFAULT_RUNTIME_CONFIG_PATH


def load_runtime_config() -> dict[str, Any]:
    path = runtime_config_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return {key: value for key, value in payload.items() if key in ALLOWED_RUNTIME_KEYS}


def update_runtime_config(values: dict[str, Any]) -> None:
    invalid = sorted(set(values) - ALLOWED_RUNTIME_KEYS)
    if invalid:
        raise ValueError(f"runtime configuration key not allowed: {', '.join(invalid)}")

    path = runtime_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    current = load_runtime_config()
    for key, value in values.items():
        if value is None or value == "":
            current.pop(key, None)
        else:
            current[key] = value

    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(current, temporary, ensure_ascii=True, indent=2, sort_keys=True)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.chmod(0o600)
    temporary_path.replace(path)
    path.chmod(0o600)


def masked_runtime_config() -> dict[str, Any]:
    values = load_runtime_config()
    return {
        **{key: value for key, value in values.items() if key not in {"EVOLUTION_API_KEY", "EVOLUTION_WEBHOOK_TOKEN"}},
        "EVOLUTION_API_KEY_CONFIGURED": bool(values.get("EVOLUTION_API_KEY") or os.getenv("EVOLUTION_API_KEY")),
        "EVOLUTION_WEBHOOK_TOKEN_CONFIGURED": bool(
            values.get("EVOLUTION_WEBHOOK_TOKEN") or os.getenv("EVOLUTION_WEBHOOK_TOKEN")
        ),
    }
