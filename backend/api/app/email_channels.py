from __future__ import annotations

import smtplib
from html import escape
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import formataddr

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
            email["From"] = formataddr((self.settings.root_whatsapp_name or "Vulcan", self.settings.email_from or self.settings.smtp_user or ""))
            email["To"] = to
            email["Subject"] = subject
            email.set_content(message)
            email.add_alternative(_render_vulcan_email_html(subject, message), subtype="html")
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port or 587, timeout=12) as client:
                client.ehlo()
                client.starttls()
                client.login(self.settings.smtp_user or "", self.settings.smtp_pass or "")
                client.send_message(email)
            return EmailDelivery(True, "sent", f"smtp:sent:{to}", f"E-mail de teste enviado para {to}.")
        except Exception as exc:  # pragma: no cover - depends on external SMTP
            return EmailDelivery(False, "failed", "smtp:falha_envio", f"Falha ao enviar e-mail SMTP: {exc}")


def _render_vulcan_email_html(subject: str, message: str) -> str:
    content_html = _render_message_body_html(message)
    safe_subject = escape(subject)
    checked_at = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    return f"""<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{safe_subject}</title>
  </head>
  <body style="margin:0;background:#08080b;color:#f8fafc;font-family:Inter,Arial,sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#08080b;padding:28px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:680px;border-collapse:collapse;">
            <tr>
              <td style="border:1px solid #26222a;background:#111015;border-radius:20px;overflow:hidden;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td style="padding:28px;background:linear-gradient(135deg,#120d0a 0%,#1a1218 52%,#08080b 100%);border-bottom:1px solid #2c2024;">
                      <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                        <tr>
                          <td style="vertical-align:middle;">
                            <table role="presentation" cellspacing="0" cellpadding="0">
                              <tr>
                                <td style="width:54px;height:54px;border-radius:16px;background:linear-gradient(135deg,#ffb15e,#ff7a1a 48%,#d6026c);text-align:center;color:white;font-weight:900;font-size:30px;line-height:54px;box-shadow:0 10px 30px rgba(255,122,26,.32);">V</td>
                                <td style="padding-left:14px;">
                                  <div style="font-size:28px;font-weight:900;letter-spacing:.2px;color:#ffffff;">Vulcan</div>
                                  <div style="font-size:11px;font-weight:700;letter-spacing:3px;color:#ff9a3c;text-transform:uppercase;">Operation Engine</div>
                                </td>
                              </tr>
                            </table>
                          </td>
                          <td align="right" style="vertical-align:middle;">
                            <span style="display:inline-block;border:1px solid rgba(255,177,94,.38);background:rgba(255,122,26,.12);border-radius:999px;padding:8px 12px;color:#ffd6ad;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;">Notificacao raiz</span>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding:28px;">
                      <div style="font-size:13px;text-transform:uppercase;letter-spacing:2.4px;color:#ff9a3c;font-weight:800;margin-bottom:10px;">Alerta operacional</div>
                      <h1 style="margin:0 0 16px;font-size:28px;line-height:1.16;color:#ffffff;">{safe_subject}</h1>
                      <div style="background:#17151b;border:1px solid #2b2731;border-radius:16px;padding:22px;color:#d7dae2;font-size:15px;line-height:1.68;">
                        {content_html}
                      </div>
                      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:18px;">
                        <tr>
                          <td width="33.33%" style="padding-right:8px;">
                            <div style="border:1px solid #2d2630;border-radius:14px;padding:14px;background:#100f14;">
                              <div style="font-size:11px;color:#898390;text-transform:uppercase;letter-spacing:1.6px;">Origem</div>
                              <div style="font-size:15px;color:#fff;font-weight:800;margin-top:6px;">Canal raiz</div>
                            </div>
                          </td>
                          <td width="33.33%" style="padding:0 4px;">
                            <div style="border:1px solid #2d2630;border-radius:14px;padding:14px;background:#100f14;">
                              <div style="font-size:11px;color:#898390;text-transform:uppercase;letter-spacing:1.6px;">Prioridade</div>
                              <div style="font-size:15px;color:#ffcf9f;font-weight:800;margin-top:6px;">Alta</div>
                            </div>
                          </td>
                          <td width="33.33%" style="padding-left:8px;">
                            <div style="border:1px solid #2d2630;border-radius:14px;padding:14px;background:#100f14;">
                              <div style="font-size:11px;color:#898390;text-transform:uppercase;letter-spacing:1.6px;">Check</div>
                              <div style="font-size:15px;color:#fff;font-weight:800;margin-top:6px;">{escape(checked_at)}</div>
                            </div>
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                  <tr>
                    <td style="padding:20px 28px;border-top:1px solid #26222a;background:#0d0c11;color:#8f8896;font-size:12px;line-height:1.55;">
                      Mensagem automatizada do Vulcan. Dados operacionais simulados podem aparecer em testes internos. Em producao, o conteudo respeita tenant, hierarquia, preferencias e escopo de permissao.
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def _render_message_body_html(message: str) -> str:
    lines = [line.strip() for line in message.replace("\r\n", "\n").split("\n")]
    blocks: list[str] = []
    list_items: list[str] = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            blocks.append("<ul style=\"margin:10px 0 16px;padding-left:20px;\">" + "".join(list_items) + "</ul>")
            list_items = []

    for line in lines:
        if not line:
            flush_list()
            continue
        if line.startswith("- "):
            list_items.append(f"<li style=\"margin:6px 0;color:#f3f0ec;\">{escape(line[2:])}</li>")
            continue
        flush_list()
        if line.endswith(":") and len(line) <= 48:
            blocks.append(f"<h2 style=\"margin:18px 0 8px;font-size:15px;color:#ffb15e;text-transform:uppercase;letter-spacing:1.6px;\">{escape(line[:-1])}</h2>")
        else:
            blocks.append(f"<p style=\"margin:0 0 14px;color:#d7dae2;\">{escape(line)}</p>")
    flush_list()
    return "".join(blocks) or "<p style=\"margin:0;color:#d7dae2;\">Mensagem Vulcan.</p>"
