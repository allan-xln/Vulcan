from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.config import Settings, get_settings


@dataclass(frozen=True)
class WhatsAppSession:
    tenant_id: UUID | None
    provider: str
    status: str
    connected: bool
    qr_required: bool
    qr_code: str | None
    last_connection_at: datetime | None
    last_sync_at: datetime | None
    logs: list[str]


@dataclass(frozen=True)
class SystemWhatsAppChannel:
    enabled: bool
    provider: str
    number: str | None
    name: str

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.provider) and bool(self.number)


@dataclass(frozen=True)
class WhatsAppDelivery:
    ok: bool
    status: str
    provider_result: str
    message: str


class WhatsAppConnection:
    """Vulcan-owned WhatsApp connection boundary.

    Inspired by LanChat's concept of runtime session status, QR/session state,
    reconnect and send endpoints, but implemented independently in Vulcan.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.system_channel = SystemWhatsAppChannel(
            enabled=self.settings.root_whatsapp_enabled,
            provider=self.settings.root_whatsapp_provider,
            number=self.settings.root_whatsapp_number,
            name=self.settings.root_whatsapp_name,
        )

    def session(self, tenant_id: UUID | None = None) -> WhatsAppSession:
        business_api_ready = bool(self.settings.whatsapp_access_token and self.settings.whatsapp_phone_number_id)
        lanchat_style_ready = self.system_channel.configured and self.system_channel.provider == "lanchat"
        connected = business_api_ready or lanchat_style_ready
        status = "conectado" if connected else "aguardando_configuracao"
        qr_required = self.system_channel.provider == "lanchat" and not connected
        return WhatsAppSession(
            tenant_id=tenant_id,
            provider=self.system_channel.provider or self.settings.whatsapp_provider or "whatsapp-business-api",
            status=status,
            connected=connected,
            qr_required=qr_required,
            qr_code="vulcan://whatsapp/root/session/qr-pendente" if qr_required else None,
            last_connection_at=datetime.now(timezone.utc) if connected else None,
            last_sync_at=datetime.now(timezone.utc),
            logs=[
                "Canal raiz configurado." if self.system_channel.configured else "Canal raiz aguardando ROOT_WHATSAPP_*.",
                "Credenciais WhatsApp Business detectadas." if business_api_ready else "WhatsApp Business API aguardando token e phone number id.",
                "Modo sessão/QR preparado no padrão LanChat, sem dependência direta." if self.system_channel.provider == "lanchat" else "Modo provedor HTTP/API preparado.",
            ],
        )

    def test_connection(self, tenant_id: UUID | None = None) -> WhatsAppDelivery:
        session = self.session(tenant_id)
        if session.connected:
            return WhatsAppDelivery(
                ok=True,
                status="ready",
                provider_result=f"{session.provider}:canal_raiz_pronto",
                message="Canal WhatsApp raiz pronto para envio.",
            )
        return WhatsAppDelivery(
            ok=False,
            status="missing_credentials",
            provider_result=f"{session.provider}:configuracao_pendente",
            message="Configure ROOT_WHATSAPP_* ou credenciais WhatsApp Business API.",
        )


class WhatsAppProvider:
    name = "whatsapp"

    def __init__(self, settings: Settings | None = None) -> None:
        self.connection = WhatsAppConnection(settings)

    def send(self, tenant_id: str, message: str, to: str | None = None) -> WhatsAppDelivery:
        session = self.connection.session(UUID(tenant_id) if tenant_id else None)
        destination = to or self.connection.settings.whatsapp_default_recipient
        if not session.connected:
            return WhatsAppDelivery(
                ok=False,
                status="missing_credentials",
                provider_result=f"{session.provider}:sem_conexao",
                message="Envio WhatsApp não realizado: canal raiz ou credenciais ainda não configurados.",
            )
        if not destination:
            return WhatsAppDelivery(
                ok=False,
                status="missing_destination",
                provider_result=f"{session.provider}:sem_destinatario",
                message="Informe um destinatário WhatsApp para envio.",
            )
        return WhatsAppDelivery(
            ok=True,
            status="ready",
            provider_result=f"{session.provider}:mock_envio_preparado:{destination}",
            message=f"Mensagem preparada para {destination}: {message[:120]}",
        )


class WhatsAppWebhook:
    def verify(self, token: str, settings: Settings | None = None) -> bool:
        settings = settings or get_settings()
        return bool(settings.whatsapp_webhook_verify_token and token == settings.whatsapp_webhook_verify_token)


class WhatsAppNotificationService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.provider = WhatsAppProvider(settings)

    def send_alert(self, tenant_id: str, title: str, message: str, to: str | None = None) -> WhatsAppDelivery:
        return self.provider.send(tenant_id, f"{title}\n\n{message}", to)
