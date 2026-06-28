from __future__ import annotations

import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage

from app.config import Settings, get_settings


@dataclass(frozen=True)
class EmailProviderStatus:
    provider: str
    configured: bool
    can_send: bool
    can_read: bool
    status: str
    message: str
    required_items: list[str]
    last_checked_at: datetime


@dataclass(frozen=True)
class EmailDelivery:
    ok: bool
    status: str
    provider_result: str
    message: str


class SmtpProvider:
    name = "smtp"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def status(self) -> EmailProviderStatus:
        required = []
        if not self.settings.smtp_host:
            required.append("SMTP_HOST")
        if not self.settings.smtp_port:
            required.append("SMTP_PORT")
        if not self.settings.smtp_user:
            required.append("SMTP_USER")
        if not self.settings.smtp_pass:
            required.append("SMTP_PASS")
        if not self.settings.email_from:
            required.append("EMAIL_FROM")
        configured = not required
        return EmailProviderStatus(
            provider=self.name,
            configured=configured,
            can_send=configured,
            can_read=False,
            status="pronto" if configured else "pendente",
            message="SMTP pronto para envio." if configured else "Preencha host, porta, usuário, senha e remetente.",
            required_items=required,
            last_checked_at=datetime.now(timezone.utc),
        )

    def test(self) -> EmailDelivery:
        status = self.status()
        if not status.configured:
            return EmailDelivery(False, "missing_credentials", "smtp:configuracao_pendente", status.message)
        if self.settings.email_delivery_mode != "live":
            return EmailDelivery(True, "mocked", "smtp:mock_validado", "SMTP configurado; teste real bloqueado por EMAIL_DELIVERY_MODE=mock.")
        try:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port or 587, timeout=8) as client:
                client.ehlo()
                client.starttls()
                client.login(self.settings.smtp_user or "", self.settings.smtp_pass or "")
            return EmailDelivery(True, "ready", "smtp:conexao_ok", "Conexão SMTP validada.")
        except Exception as exc:  # pragma: no cover - depends on external SMTP
            return EmailDelivery(False, "failed", "smtp:falha_conexao", f"Falha SMTP: {exc}")


class GmailProvider:
    name = "gmail"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def status(self) -> EmailProviderStatus:
        required = []
        if not self.settings.gmail_client_id:
            required.append("GMAIL_CLIENT_ID")
        if not self.settings.gmail_client_secret:
            required.append("GMAIL_CLIENT_SECRET")
        if not self.settings.gmail_redirect_uri:
            required.append("GMAIL_REDIRECT_URI")
        if not self.settings.gmail_refresh_token:
            required.append("GMAIL_REFRESH_TOKEN")
        configured = not required
        return EmailProviderStatus(
            provider=self.name,
            configured=configured,
            can_send=configured,
            can_read=True,
            status="oauth_pronto" if configured else "oauth_pendente",
            message="Gmail OAuth preparado para envio." if configured else "Configure OAuth do Google para ativar Gmail.",
            required_items=required,
            last_checked_at=datetime.now(timezone.utc),
        )


class OutlookProvider:
    name = "outlook"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def status(self) -> EmailProviderStatus:
        required = []
        if not self.settings.outlook_tenant_id:
            required.append("OUTLOOK_TENANT_ID")
        if not self.settings.outlook_client_id:
            required.append("OUTLOOK_CLIENT_ID")
        if not self.settings.outlook_client_secret:
            required.append("OUTLOOK_CLIENT_SECRET")
        if not self.settings.outlook_redirect_uri:
            required.append("OUTLOOK_REDIRECT_URI")
        if not self.settings.outlook_refresh_token:
            required.append("OUTLOOK_REFRESH_TOKEN")
        configured = not required
        return EmailProviderStatus(
            provider=self.name,
            configured=configured,
            can_send=configured,
            can_read=True,
            status="oauth_pronto" if configured else "oauth_pendente",
            message="Microsoft 365 OAuth preparado para envio." if configured else "Configure OAuth da Microsoft para ativar Outlook.",
            required_items=required,
            last_checked_at=datetime.now(timezone.utc),
        )


class ImapProvider:
    name = "imap"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def status(self) -> EmailProviderStatus:
        required = []
        if not self.settings.imap_host:
            required.append("IMAP_HOST")
        if not self.settings.imap_port:
            required.append("IMAP_PORT")
        if not self.settings.imap_user:
            required.append("IMAP_USER")
        if not self.settings.imap_pass:
            required.append("IMAP_PASS")
        configured = not required
        return EmailProviderStatus(
            provider=self.name,
            configured=configured,
            can_send=False,
            can_read=configured,
            status="consulta_pronta" if configured else "consulta_pendente",
            message="IMAP serve para leitura/consulta; não é canal de envio." if configured else "Configure IMAP para leitura/consulta.",
            required_items=required,
            last_checked_at=datetime.now(timezone.utc),
        )


class Pop3Provider:
    name = "pop3"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def status(self) -> EmailProviderStatus:
        required = []
        if not self.settings.pop3_host:
            required.append("POP3_HOST")
        if not self.settings.pop3_port:
            required.append("POP3_PORT")
        if not self.settings.pop3_user:
            required.append("POP3_USER")
        if not self.settings.pop3_pass:
            required.append("POP3_PASS")
        configured = not required
        return EmailProviderStatus(
            provider=self.name,
            configured=configured,
            can_send=False,
            can_read=configured,
            status="consulta_pronta" if configured else "consulta_pendente",
            message="POP3 serve para leitura/consulta; não é canal de envio." if configured else "Configure POP3 para leitura/consulta.",
            required_items=required,
            last_checked_at=datetime.now(timezone.utc),
        )


class EmailNotificationService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.smtp = SmtpProvider(self.settings)
        self.gmail = GmailProvider(self.settings)
        self.outlook = OutlookProvider(self.settings)
        self.imap = ImapProvider(self.settings)
        self.pop3 = Pop3Provider(self.settings)

    def statuses(self) -> list[EmailProviderStatus]:
        return [self.smtp.status(), self.gmail.status(), self.outlook.status(), self.imap.status(), self.pop3.status()]

    def test(self, provider: str | None = None) -> EmailDelivery:
        selected = (provider or self.settings.email_provider or "smtp").lower()
        if selected == "smtp":
            return self.smtp.test()
        status_by_provider = {item.provider: item for item in self.statuses()}
        status = status_by_provider.get(selected)
        if not status:
            return EmailDelivery(False, "unknown_provider", f"{selected}:desconhecido", "Provedor de e-mail desconhecido.")
        if status.configured:
            return EmailDelivery(True, "ready", f"{selected}:configuracao_pronta", status.message)
        return EmailDelivery(False, "missing_credentials", f"{selected}:configuracao_pendente", status.message)

    def send_test(self, to: str | None, subject: str, message: str, provider: str | None = None) -> EmailDelivery:
        delivery = self.test(provider)
        if not delivery.ok:
            return delivery
        if not to:
            return EmailDelivery(False, "missing_destination", "email:sem_destinatario", "Informe um destinatário de e-mail.")
        if self.settings.email_delivery_mode != "live":
            return EmailDelivery(True, "mocked", f"email:teste_preparado:{to}", f"E-mail de teste preparado para {to}: {subject} - {message[:100]}")
        if (provider or self.settings.email_provider or "smtp").lower() != "smtp":
            return EmailDelivery(False, "unsupported_provider", "email:envio_real_indisponivel", "Envio real está implementado para SMTP.")
        try:
            email = EmailMessage()
            email["From"] = self.settings.email_from or self.settings.smtp_user or ""
            email["To"] = to
            email["Subject"] = subject
            email.set_content(message)
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port or 587, timeout=12) as client:
                client.ehlo()
                client.starttls()
                client.login(self.settings.smtp_user or "", self.settings.smtp_pass or "")
                client.send_message(email)
            return EmailDelivery(True, "sent", f"smtp:sent:{to}", f"E-mail de teste enviado para {to}.")
        except Exception as exc:  # pragma: no cover - depends on external SMTP
            return EmailDelivery(False, "failed", "smtp:falha_envio", f"Falha ao enviar e-mail SMTP: {exc}")
