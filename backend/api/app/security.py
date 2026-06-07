from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import Depends, Header, HTTPException, status

from app.config import Settings, get_settings
from app.schemas import LoginRequest, LoginResponse


DEV_TOKEN = "dev-vulcan-admin-token"
TEST_DEV_TOKEN = "dev-vulcan-test-token"
LOCAL_TENANT_ID = UUID("00000000-0000-0000-0000-000000000301")

DEMO_LOCAL_ACCOUNTS = {
    "diretor": {
        "password": "diretor",
        "token": "dev-vulcan-diretor-token",
        "id": "00000000-0000-0000-0000-000000400001",
        "name": "Diretor Operacional",
        "email": "diretor@vulcan.local",
        "role": "hierarchy",
    },
    "coordenador": {
        "password": "coordenador",
        "token": "dev-vulcan-coordenador-token",
        "id": "00000000-0000-0000-0000-000000400002",
        "name": "Coordenador de Operações",
        "email": "coordenador@vulcan.local",
        "role": "hierarchy",
    },
    "gerente": {
        "password": "gerente",
        "token": "dev-vulcan-gerente-token",
        "id": "00000000-0000-0000-0000-000000400003",
        "name": "Gerente Financeiro",
        "email": "gerente@vulcan.local",
        "role": "hierarchy",
    },
    "supervisor": {
        "password": "supervisor",
        "token": "dev-vulcan-supervisor-token",
        "id": "00000000-0000-0000-0000-000000400004",
        "name": "Supervisor de Faturamento",
        "email": "supervisor@vulcan.local",
        "role": "hierarchy",
    },
    "lider": {
        "password": "lider",
        "token": "dev-vulcan-lider-token",
        "id": "00000000-0000-0000-0000-000000400008",
        "name": "Líder Operacional",
        "email": "lider@vulcan.local",
        "role": "hierarchy",
    },
    "operador1": {
        "password": "operador1",
        "token": "dev-vulcan-operador1-token",
        "id": "00000000-0000-0000-0000-000000400006",
        "name": "Operador 1",
        "email": "operador1@vulcan.local",
        "role": "user",
    },
    "operador2": {
        "password": "operador2",
        "token": "dev-vulcan-operador2-token",
        "id": "00000000-0000-0000-0000-000000400007",
        "name": "Operador 2",
        "email": "operador2@vulcan.local",
        "role": "user",
    },
    "operador3": {
        "password": "operador3",
        "token": "dev-vulcan-operador3-token",
        "id": "00000000-0000-0000-0000-000000400009",
        "name": "Operador 3",
        "email": "operador3@vulcan.local",
        "role": "user",
    },
    "teste": {
        "password": "teste",
        "token": TEST_DEV_TOKEN,
        "id": "00000000-0000-0000-0000-000000400005",
        "name": "teste",
        "email": "teste@vulcan.local",
        "role": "tenant_admin",
    },
}


@dataclass(frozen=True)
class AuthContext:
    user_id: str
    email: str | None
    tenant_id: UUID
    role: str
    provider: str


def _local_development_auth_enabled(settings: Settings) -> bool:
    return settings.auth_provider == "local" or settings.mock_auth or settings.local_test_auth_enabled


def login_with_local_admin(request: LoginRequest, settings: Settings | None = None) -> LoginResponse:
    settings = settings or get_settings()
    if not _local_development_auth_enabled(settings):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="local development auth is disabled",
        )

    local_accounts = {
        settings.admin_username: {
            "password": settings.admin_password,
            "token": DEV_TOKEN,
            "id": "11111111-1111-1111-1111-111111111111",
            "name": "Vulcan Local Admin",
            "email": "admin@vulcan.local",
            "role": "owner",
            "warning": "Local admin auth is for development only. Replace with Supabase Auth before production.",
        },
    }
    for login, demo_account in DEMO_LOCAL_ACCOUNTS.items():
        local_accounts[login] = {
            **demo_account,
            "warning": "Demo local auth is for commercial testing only. Replace with Supabase Auth before production.",
        }
        local_accounts[demo_account["email"]] = {
            **demo_account,
            "warning": "Demo local auth is for commercial testing only. Replace with Supabase Auth before production.",
        }

    username = request.username.strip().lower()
    account = local_accounts.get(username) or local_accounts.get(request.username)

    if not account or request.password != account["password"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid local credentials",
        )

    return LoginResponse(
        accessToken=str(account["token"]),
        tokenType="bearer",
        user={
            "id": account["id"],
            "name": account["name"],
            "email": account["email"],
            "role": account["role"],
        },
        warning=str(account["warning"]),
    )


def _validate_supabase_token(token: str, settings: Settings, tenant_id: UUID) -> AuthContext:
    if not settings.supabase_url:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Supabase URL is not configured")

    api_key = settings.supabase_publishable_key or settings.supabase_anon_key
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Supabase API key is not configured")

    try:
        response = httpx.get(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
            headers={"apikey": api_key, "Authorization": f"Bearer {token}"},
            timeout=6,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Supabase Auth is unreachable") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid Supabase token")

    payload = response.json()
    return AuthContext(
        user_id=str(payload.get("id", "")),
        email=payload.get("email"),
        tenant_id=tenant_id,
        role="supabase_user",
        provider="supabase",
    )


def require_auth(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
) -> AuthContext:
    tenant_id = UUID(x_tenant_id) if x_tenant_id else LOCAL_TENANT_ID

    settings = get_settings()

    demo_tokens = {
        f"Bearer {account['token']}": account
        for account in DEMO_LOCAL_ACCOUNTS.values()
    }

    if authorization in {f"Bearer {DEV_TOKEN}", *demo_tokens.keys()} and _local_development_auth_enabled(settings):
        account = demo_tokens.get(authorization)
        if account:
            return AuthContext(
                user_id=str(account["id"]),
                email=str(account["email"]),
                tenant_id=tenant_id,
                role=str(account["role"]),
                provider="local",
            )
        return AuthContext(
            user_id="11111111-1111-1111-1111-111111111111",
            email="admin@vulcan.local",
            tenant_id=tenant_id,
            role="tenant_admin",
            provider="local",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid authorization token",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if settings.auth_provider == "supabase":
        return _validate_supabase_token(token, settings, tenant_id)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="missing or invalid local development token",
    )


Authenticated = Depends(require_auth)
