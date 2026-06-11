#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = os.environ.get("API_URL", "http://localhost:3001").rstrip("/")
TENANT_ID = os.environ.get("TENANT_ID", "00000000-0000-0000-0000-000000000301")
TIMEOUT_SECONDS = float(os.environ.get("DEMO_VALIDATE_TIMEOUT_SECONDS", "12"))


@dataclass(frozen=True)
class ProfileExpectation:
    username: str
    password: str
    visible_names: set[str]
    min_devices: int


ALL_BUSINESS_NAMES = {
    "Root Demo Vulcan",
    "Diretor Operacional",
    "Coordenador de Operações",
    "Gerente Financeiro",
    "Supervisor de Faturamento",
    "Líder Operacional",
    "Operador 1",
    "Operador 2",
    "Operador 3",
}

EXPECTATIONS = [
    ProfileExpectation(
        "teste",
        "teste",
        ALL_BUSINESS_NAMES,
        1,
    ),
    ProfileExpectation(
        "diretor",
        "diretor",
        {
            "Diretor Operacional",
            "Coordenador de Operações",
            "Gerente Financeiro",
            "Supervisor de Faturamento",
            "Líder Operacional",
            "Operador 1",
            "Operador 2",
            "Operador 3",
        },
        1,
    ),
    ProfileExpectation(
        "coordenador",
        "coordenador",
        {
            "Coordenador de Operações",
            "Gerente Financeiro",
            "Supervisor de Faturamento",
            "Líder Operacional",
            "Operador 1",
            "Operador 2",
            "Operador 3",
        },
        1,
    ),
    ProfileExpectation(
        "gerente",
        "gerente",
        {
            "Gerente Financeiro",
            "Supervisor de Faturamento",
            "Líder Operacional",
            "Operador 1",
            "Operador 2",
            "Operador 3",
        },
        1,
    ),
    ProfileExpectation(
        "supervisor",
        "supervisor",
        {"Supervisor de Faturamento", "Líder Operacional", "Operador 1", "Operador 2", "Operador 3"},
        1,
    ),
    ProfileExpectation("lider", "lider", {"Líder Operacional", "Operador 1", "Operador 2", "Operador 3"}, 1),
    ProfileExpectation("operador1", "operador1", {"Operador 1"}, 1),
    ProfileExpectation("operador2", "operador2", {"Operador 2"}, 1),
    ProfileExpectation("operador3", "operador3", {"Operador 3"}, 1),
]


def _request(method: str, path: str, token: str | None = None, payload: dict[str, Any] | None = None) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json", "X-Tenant-Id": TENANT_ID}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{API_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"{method} {path} failed: {exc.reason}") from exc
    return json.loads(raw) if raw else None


def _login(username: str, password: str) -> str:
    payload = _request("POST", "/auth/login", payload={"username": username, "password": password})
    token = payload.get("accessToken")
    if not token:
        raise RuntimeError(f"{username}: login did not return accessToken")
    return str(token)


def _assert_contract(username: str, intelligence: dict[str, Any]) -> None:
    required_keys = [
        "totalEvents",
        "totalActiveSeconds",
        "totalIdleSeconds",
        "contextSwitchesPerHour",
        "focusScore",
        "distractionScore",
        "topApps",
        "qualitySignals",
        "aiRecommendations",
    ]
    missing = [key for key in required_keys if key not in intelligence]
    if missing:
        raise RuntimeError(f"{username}: operational-intelligence missing keys: {', '.join(missing)}")
    if not isinstance(intelligence["topApps"], list):
        raise RuntimeError(f"{username}: topApps must be a list")
    if not isinstance(intelligence["aiRecommendations"], list):
        raise RuntimeError(f"{username}: aiRecommendations must be a list")


def validate_profile(expectation: ProfileExpectation) -> tuple[int, int, int]:
    token = _login(expectation.username, expectation.password)

    hierarchy = _request("GET", "/hierarchy", token=token)
    devices = _request("GET", "/devices", token=token)
    intelligence = _request("GET", "/operational-intelligence", token=token)
    notifications = _request("GET", "/notifications", token=token)

    visible_names = {str(item.get("name")) for item in hierarchy}
    missing_names = expectation.visible_names - visible_names
    extra_business_names = (visible_names & ALL_BUSINESS_NAMES) - expectation.visible_names
    if missing_names:
        raise RuntimeError(f"{expectation.username}: missing hierarchy names: {sorted(missing_names)}")
    if extra_business_names:
        raise RuntimeError(f"{expectation.username}: hierarchy leak: {sorted(extra_business_names)}")

    device_owners = {str(item.get("owner")) for item in devices if item.get("owner") and item.get("owner") != "Unassigned"}
    leaked_owners = (device_owners & ALL_BUSINESS_NAMES) - expectation.visible_names
    if leaked_owners:
        raise RuntimeError(f"{expectation.username}: device owner leak: {sorted(leaked_owners)}")
    if len(devices) < expectation.min_devices:
        raise RuntimeError(f"{expectation.username}: expected at least {expectation.min_devices} device(s), saw {len(devices)}")

    _assert_contract(expectation.username, intelligence)

    if not isinstance(notifications, list):
        raise RuntimeError(f"{expectation.username}: notifications endpoint must return a list")

    return len(hierarchy), len(devices), int(intelligence.get("totalEvents") or 0)


def main() -> int:
    print(f"Validando MVP comercial em {API_URL}")
    print(f"Tenant: {TENANT_ID}")
    print()

    try:
        _request("GET", "/health")
        for expectation in EXPECTATIONS:
            hierarchy_count, devices_count, event_count = validate_profile(expectation)
            print(
                f"{expectation.username:<12} hierarquia={hierarchy_count:<2} "
                f"dispositivos={devices_count:<2} eventos24h={event_count}"
            )
    except RuntimeError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    print()
    print("Validação comercial concluída sem vazamento de hierarquia ou dispositivos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
