import json
from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    environment: str
    admin_username: str
    admin_password: str
    local_test_auth_enabled: bool
    local_test_username: str
    local_test_password: str
    mock_auth: bool
    mock_data: bool
    api_allowed_origins: tuple[str, ...]
    api_allowed_origin_regex: str | None
    openai_configured: bool
    llama_provider: str
    llama_base_url: str | None
    llama_model: str
    ai_complex_model: str
    ai_operational_model: str
    auth_provider: str
    supabase_url: str | None
    supabase_rest_url: str | None
    supabase_project_ref: str | None
    supabase_publishable_key: str | None
    supabase_anon_key: str | None
    supabase_service_role_key: str | None
    supabase_secret_key: str | None
    database_url: str | None
    smtp_host: str | None
    smtp_port: int | None
    smtp_user: str | None
    smtp_pass: str | None
    email_from: str | None
    email_provider: str
    email_delivery_mode: str
    resend_api_key: str | None
    sendgrid_api_key: str | None
    gmail_client_id: str | None
    gmail_client_secret: str | None
    gmail_redirect_uri: str | None
    gmail_refresh_token: str | None
    outlook_tenant_id: str | None
    outlook_client_id: str | None
    outlook_client_secret: str | None
    outlook_redirect_uri: str | None
    outlook_refresh_token: str | None
    imap_host: str | None
    imap_port: int | None
    imap_user: str | None
    imap_pass: str | None
    imap_ssl: bool
    pop3_host: str | None
    pop3_port: int | None
    pop3_user: str | None
    pop3_pass: str | None
    pop3_ssl: bool
    whatsapp_provider: str | None
    whatsapp_access_token: str | None
    whatsapp_phone_number_id: str | None
    whatsapp_business_account_id: str | None
    whatsapp_webhook_verify_token: str | None
    whatsapp_default_recipient: str | None
    root_whatsapp_enabled: bool
    root_whatsapp_provider: str
    root_whatsapp_number: str | None
    root_whatsapp_name: str
    fcm_server_key: str | None
    fcm_vapid_key: str | None
    agent_enrollment_token: str


def _bool_env(name: str, default: bool = False) -> bool:
    value = getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _origin_list_env(names: tuple[str, ...], default: tuple[str, ...]) -> tuple[str, ...]:
    value = next((getenv(name) for name in names if getenv(name)), None)
    if value is None:
        return default
    raw_value = value.strip()
    if raw_value.startswith("["):
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, list):
                items = tuple(str(item).strip() for item in parsed if str(item).strip())
                return items or default
        except json.JSONDecodeError:
            raw_value = raw_value.strip("[]")
    items = tuple(item.strip().strip("[]") for item in raw_value.split(",") if item.strip().strip("[]"))
    return items or default


def _vercel_origin() -> tuple[str, ...]:
    vercel_url = getenv("VERCEL_URL") or getenv("NEXT_PUBLIC_VERCEL_URL")
    if not vercel_url:
        return ()
    origin = vercel_url.strip()
    if not origin:
        return ()
    if not origin.startswith(("http://", "https://")):
        origin = f"https://{origin}"
    return (origin.rstrip("/"),)


def get_settings() -> Settings:
    environment = getenv("NEXT_PUBLIC_ENVIRONMENT", "local")
    default_origin_regex = None if environment == "production" else r"^https?://(localhost|127\.0\.0\.1):[0-9]+$"
    return Settings(
        host=getenv("LOCAL_API_HOST", "0.0.0.0"),
        port=int(getenv("LOCAL_API_PORT", "3001")),
        environment=environment,
        admin_username=getenv("LOCAL_ADMIN_USERNAME", "admin"),
        admin_password=getenv("LOCAL_ADMIN_PASSWORD", "admin"),
        local_test_auth_enabled=_bool_env("LOCAL_TEST_AUTH_ENABLED", getenv("NEXT_PUBLIC_ENVIRONMENT", "local") != "production"),
        local_test_username=getenv("LOCAL_TEST_USERNAME", "teste"),
        local_test_password=getenv("LOCAL_TEST_PASSWORD", "teste"),
        mock_auth=_bool_env("MOCK_AUTH", False),
        mock_data=_bool_env("MOCK_DATA", False),
        api_allowed_origins=_origin_list_env(
            ("API_ALLOWED_ORIGINS", "ALLOWED_ORIGINS"),
            (
                "http://localhost:3000",
                "http://localhost:3001",
                "http://localhost:3002",
                "http://localhost:3003",
                "http://localhost:3004",
                "http://localhost:3102",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
                "http://127.0.0.1:3002",
                "http://127.0.0.1:3003",
                "http://127.0.0.1:3004",
                "http://127.0.0.1:3102",
                "https://vulcan.lanfuture.dev",
                "https://vulcan-demo.lanfuture.dev",
                "https://vulcan-staging.lanfuture.dev",
                *_vercel_origin(),
            ),
        ),
        api_allowed_origin_regex=getenv("API_ALLOWED_ORIGIN_REGEX", default_origin_regex) or None,
        openai_configured=bool(getenv("OPENAI_API_KEY")),
        llama_provider=getenv("LLAMA_PROVIDER", "openai-compatible"),
        llama_base_url=getenv("LLAMA_BASE_URL") or None,
        llama_model=getenv("LLAMA_MODEL", "llama-4-maverick"),
        ai_complex_model=getenv("AI_COMPLEX_MODEL", getenv("OPENAI_MODEL", "gpt-5.5")),
        ai_operational_model=getenv("AI_OPERATIONAL_MODEL", getenv("LLAMA_MODEL", "llama-4-maverick")),
        auth_provider=getenv("AUTH_PROVIDER", "local"),
        supabase_url=getenv("SUPABASE_URL", getenv("NEXT_PUBLIC_SUPABASE_URL", "")) or None,
        supabase_rest_url=getenv("SUPABASE_REST_URL") or None,
        supabase_project_ref=getenv("SUPABASE_PROJECT_REF") or None,
        supabase_publishable_key=getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY") or None,
        supabase_anon_key=getenv("SUPABASE_ANON_KEY", getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")) or None,
        supabase_service_role_key=getenv("SUPABASE_SERVICE_ROLE_KEY") or None,
        supabase_secret_key=getenv("SUPABASE_SECRET_KEY") or None,
        database_url=getenv("DATABASE_URL") or None,
        smtp_host=getenv("SMTP_HOST") or None,
        smtp_port=int(getenv("SMTP_PORT", "0")) or None,
        smtp_user=getenv("SMTP_USER") or None,
        smtp_pass=getenv("SMTP_PASS") or None,
        email_from=getenv("EMAIL_FROM") or None,
        email_provider=getenv("EMAIL_PROVIDER", "smtp"),
        email_delivery_mode=getenv("EMAIL_DELIVERY_MODE", "mock"),
        resend_api_key=getenv("RESEND_API_KEY") or None,
        sendgrid_api_key=getenv("SENDGRID_API_KEY") or None,
        gmail_client_id=getenv("GMAIL_CLIENT_ID") or None,
        gmail_client_secret=getenv("GMAIL_CLIENT_SECRET") or None,
        gmail_redirect_uri=getenv("GMAIL_REDIRECT_URI") or None,
        gmail_refresh_token=getenv("GMAIL_REFRESH_TOKEN") or None,
        outlook_tenant_id=getenv("OUTLOOK_TENANT_ID") or None,
        outlook_client_id=getenv("OUTLOOK_CLIENT_ID") or None,
        outlook_client_secret=getenv("OUTLOOK_CLIENT_SECRET") or None,
        outlook_redirect_uri=getenv("OUTLOOK_REDIRECT_URI") or None,
        outlook_refresh_token=getenv("OUTLOOK_REFRESH_TOKEN") or None,
        imap_host=getenv("IMAP_HOST") or None,
        imap_port=int(getenv("IMAP_PORT", "0")) or None,
        imap_user=getenv("IMAP_USER") or None,
        imap_pass=getenv("IMAP_PASS") or None,
        imap_ssl=_bool_env("IMAP_SSL", True),
        pop3_host=getenv("POP3_HOST") or None,
        pop3_port=int(getenv("POP3_PORT", "0")) or None,
        pop3_user=getenv("POP3_USER") or None,
        pop3_pass=getenv("POP3_PASS") or None,
        pop3_ssl=_bool_env("POP3_SSL", True),
        whatsapp_provider=getenv("WHATSAPP_PROVIDER") or None,
        whatsapp_access_token=getenv("WHATSAPP_ACCESS_TOKEN") or None,
        whatsapp_phone_number_id=getenv("WHATSAPP_PHONE_NUMBER_ID") or None,
        whatsapp_business_account_id=getenv("WHATSAPP_BUSINESS_ACCOUNT_ID") or None,
        whatsapp_webhook_verify_token=getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN") or None,
        whatsapp_default_recipient=getenv("WHATSAPP_DEFAULT_RECIPIENT") or None,
        root_whatsapp_enabled=_bool_env("ROOT_WHATSAPP_ENABLED", False),
        root_whatsapp_provider=getenv("ROOT_WHATSAPP_PROVIDER", "lanchat"),
        root_whatsapp_number=getenv("ROOT_WHATSAPP_NUMBER") or None,
        root_whatsapp_name=getenv("ROOT_WHATSAPP_NAME", "Notificações Vulcan"),
        fcm_server_key=getenv("FCM_SERVER_KEY") or None,
        fcm_vapid_key=getenv("FCM_VAPID_KEY") or None,
        agent_enrollment_token=getenv("AGENT_ENROLLMENT_TOKEN", "vulcan-local-enrollment-token"),
    )
