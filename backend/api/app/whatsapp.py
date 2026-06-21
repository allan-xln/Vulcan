from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

import httpx

from app.config import Settings, get_settings


EVOLUTION_EVENTS = [
    "CONNECTION_UPDATE",
    "QRCODE_UPDATED",
    "SEND_MESSAGE",
    "SEND_MESSAGE_UPDATE",
    "MESSAGES_UPDATE",
    "LOGOUT_INSTANCE",
]


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
    service_reachable: bool = False
    instance_name: str | None = None
    unofficial: bool = False


@dataclass(frozen=True)
class SystemWhatsAppChannel:
    enabled: bool
    provider: str
    number: str | None
    name: str

    @property
    def configured(self) -> bool:
        return self.enabled and bool(self.provider) and is_e164_phone(self.number)


@dataclass(frozen=True)
class WhatsAppDelivery:
    ok: bool
    status: str
    provider_result: str
    message: str
    provider_message_id: str | None = None


@dataclass(frozen=True)
class EvolutionHttpResult:
    ok: bool
    status: str
    payload: dict[str, Any]
    message: str
    http_status: int | None = None


class EvolutionWhatsAppProvider:
    name = "evolution"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.evolution_enabled
            and self.settings.evolution_base_url
            and self.settings.evolution_api_key
            and self.settings.evolution_instance_name
            and self.settings.whatsapp_enable_unofficial_provider
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        safe_retry: bool = False,
    ) -> EvolutionHttpResult:
        if not self.settings.evolution_base_url:
            return EvolutionHttpResult(False, "missing_credentials", {}, "EVOLUTION_BASE_URL não configurada.")
        if path != "/" and not self.settings.evolution_api_key:
            return EvolutionHttpResult(False, "missing_credentials", {}, "EVOLUTION_API_KEY não configurada.")

        attempts = self.settings.evolution_max_retries if safe_retry else 1
        url = f"{self.settings.evolution_base_url.rstrip('/')}{path}"
        headers = {"Accept": "application/json"}
        if self.settings.evolution_request_origin:
            headers["Origin"] = self.settings.evolution_request_origin
        if path != "/":
            headers["apikey"] = self.settings.evolution_api_key or ""

        for attempt in range(attempts):
            try:
                response = httpx.request(
                    method,
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.settings.evolution_request_timeout_seconds,
                )
            except httpx.TimeoutException:
                result = EvolutionHttpResult(False, "unavailable", {}, "Timeout ao acessar a Evolution API.")
            except httpx.HTTPError:
                result = EvolutionHttpResult(False, "unavailable", {}, "Evolution API indisponível na URL configurada.")
            else:
                try:
                    body = response.json() if response.content else {}
                except ValueError:
                    body = {}
                if not isinstance(body, dict):
                    body = {"data": body}
                if response.status_code < 400:
                    return EvolutionHttpResult(True, "ok", body, "Evolution API respondeu.", response.status_code)
                if response.status_code in {401, 403}:
                    return EvolutionHttpResult(False, "missing_credentials", body, "Evolution API recusou a API key.", response.status_code)
                if response.status_code == 404:
                    return EvolutionHttpResult(False, "not_found", body, "Instância Evolution não encontrada.", response.status_code)
                if response.status_code == 429:
                    return EvolutionHttpResult(False, "rate_limited", body, "Evolution API limitou temporariamente a requisição.", response.status_code)
                result = EvolutionHttpResult(
                    False,
                    "failed",
                    body,
                    f"Evolution API respondeu HTTP {response.status_code}.",
                    response.status_code,
                )

            if attempt + 1 < attempts:
                time.sleep(self.settings.evolution_retry_backoff_seconds * (2**attempt))
        return result

    def health(self) -> EvolutionHttpResult:
        return self._request("GET", "/", safe_retry=True)

    def connection_state(self) -> EvolutionHttpResult:
        instance = self.settings.evolution_instance_name
        return self._request("GET", f"/instance/connectionState/{instance}", safe_retry=True)

    def session(self, tenant_id: UUID | None = None, include_qr: bool = False) -> WhatsAppSession:
        now = datetime.now(timezone.utc)
        if not self.settings.whatsapp_enable_unofficial_provider:
            return WhatsAppSession(
                tenant_id,
                self.name,
                "disabled",
                False,
                False,
                None,
                None,
                now,
                ["Provider não oficial bloqueado por WHATSAPP_ENABLE_UNOFFICIAL_PROVIDER."],
                instance_name=self.settings.evolution_instance_name,
                unofficial=True,
            )
        if not self.settings.evolution_enabled:
            return WhatsAppSession(
                tenant_id,
                self.name,
                "disabled",
                False,
                False,
                None,
                None,
                now,
                ["Evolution desativada por EVOLUTION_ENABLED."],
                instance_name=self.settings.evolution_instance_name,
                unofficial=True,
            )
        if not self.settings.evolution_api_key or not self.settings.evolution_base_url:
            return WhatsAppSession(
                tenant_id,
                self.name,
                "missing_credentials",
                False,
                False,
                None,
                None,
                now,
                ["Preencha EVOLUTION_BASE_URL e EVOLUTION_API_KEY."],
                instance_name=self.settings.evolution_instance_name,
                unofficial=True,
            )

        health = self.health()
        if not health.ok:
            status = "unofficial_rate_limited" if health.status == "rate_limited" else "unofficial_failed"
            return WhatsAppSession(
                tenant_id,
                self.name,
                status,
                False,
                False,
                None,
                None,
                now,
                [health.message],
                instance_name=self.settings.evolution_instance_name,
                unofficial=True,
            )

        state_result = self.connection_state()
        if state_result.status == "missing_credentials":
            return WhatsAppSession(
                tenant_id,
                self.name,
                "missing_credentials",
                False,
                False,
                None,
                None,
                now,
                [state_result.message],
                service_reachable=True,
                instance_name=self.settings.evolution_instance_name,
                unofficial=True,
            )
        if state_result.status == "rate_limited":
            return WhatsAppSession(
                tenant_id,
                self.name,
                "unofficial_rate_limited",
                False,
                False,
                None,
                None,
                now,
                [state_result.message],
                service_reachable=True,
                instance_name=self.settings.evolution_instance_name,
                unofficial=True,
            )

        state = _find_value(state_result.payload, ("state", "status", "connectionStatus"))
        normalized_state = str(state or "").strip().lower()
        if normalized_state == "open":
            return WhatsAppSession(
                tenant_id,
                self.name,
                "unofficial_connected",
                True,
                False,
                None,
                now,
                now,
                ["Evolution API alcançável.", "Instância Baileys conectada."],
                service_reachable=True,
                instance_name=self.settings.evolution_instance_name,
                unofficial=True,
            )

        qr_code = None
        qr_required = normalized_state in {"connecting", "close", "closed", ""} or state_result.status == "not_found"
        if include_qr and qr_required:
            qr_result = self.get_qr_code(create_if_missing=True)
            qr_code = _extract_qr(qr_result.payload) if qr_result.ok else None
        return WhatsAppSession(
            tenant_id,
            self.name,
            "unofficial_qr_required" if qr_required else "unofficial_disconnected",
            False,
            qr_required,
            qr_code,
            None,
            now,
            ["Evolution API alcançável.", "A instância precisa ser conectada por QR Code." if qr_required else "Instância desconectada."],
            service_reachable=True,
            instance_name=self.settings.evolution_instance_name,
            unofficial=True,
        )

    def ensure_instance(self) -> EvolutionHttpResult:
        state = self.connection_state()
        if state.ok:
            return state
        if state.status not in {"not_found"}:
            return state

        webhook: dict[str, Any] = {"enabled": False, "events": []}
        if self.settings.evolution_webhook_url and self.settings.evolution_webhook_token:
            webhook = {
                "enabled": True,
                "url": self.settings.evolution_webhook_url,
                "events": EVOLUTION_EVENTS,
                "headers": {"X-Vulcan-Webhook-Token": self.settings.evolution_webhook_token},
                "byEvents": False,
                "base64": True,
            }
        return self._request(
            "POST",
            "/instance/create",
            payload={
                "instanceName": self.settings.evolution_instance_name,
                "integration": "WHATSAPP-BAILEYS",
                "qrcode": True,
                "rejectCall": True,
                "msgCall": "Chamadas não são atendidas pelo canal automático Vulcan.",
                "groupsIgnore": True,
                "alwaysOnline": False,
                "readMessages": False,
                "readStatus": False,
                "syncFullHistory": False,
                "webhook": webhook,
            },
        )

    def configure_webhook(self) -> EvolutionHttpResult:
        if not self.settings.evolution_webhook_url or not self.settings.evolution_webhook_token:
            return EvolutionHttpResult(False, "missing_credentials", {}, "EVOLUTION_WEBHOOK_URL/TOKEN não configurados.")
        return self._request(
            "POST",
            f"/webhook/set/{self.settings.evolution_instance_name}",
            payload={
                "webhook": {
                    "enabled": True,
                    "url": self.settings.evolution_webhook_url,
                    "events": EVOLUTION_EVENTS,
                    "headers": {"X-Vulcan-Webhook-Token": self.settings.evolution_webhook_token},
                    "byEvents": False,
                    "base64": True,
                }
            },
        )

    def get_qr_code(self, create_if_missing: bool = True) -> EvolutionHttpResult:
        if create_if_missing:
            instance = self.ensure_instance()
            if not instance.ok and instance.status != "not_found":
                return instance
            created_qr = _extract_qr(instance.payload)
            if created_qr:
                return instance
            if instance.ok:
                self.configure_webhook()
        return self._request("GET", f"/instance/connect/{self.settings.evolution_instance_name}", safe_retry=True)

    def reconnect(self) -> EvolutionHttpResult:
        instance = self.ensure_instance()
        if not instance.ok:
            return instance
        self.configure_webhook()
        return self._request("GET", f"/instance/connect/{self.settings.evolution_instance_name}", safe_retry=True)

    def send_text(self, destination: str, message: str) -> WhatsAppDelivery:
        session = self.session()
        if not session.connected:
            if session.status == "unofficial_qr_required":
                return WhatsAppDelivery(False, "qr_required", "evolution:qr_required", "Evolution requer conexão por QR Code.")
            if session.status == "unofficial_rate_limited":
                return WhatsAppDelivery(False, "rate_limited", "evolution:rate_limited", "Evolution limitou temporariamente o envio.")
            if session.status == "missing_credentials":
                return WhatsAppDelivery(False, "missing_credentials", "evolution:missing_credentials", "Credenciais Evolution incompletas.")
            return WhatsAppDelivery(False, "provider_unavailable", "evolution:unavailable", "Evolution/Baileys está indisponível ou desconectada.")

        result = self._request(
            "POST",
            f"/message/sendText/{self.settings.evolution_instance_name}",
            payload={"number": destination, "text": message[:4096], "linkPreview": False},
        )
        if result.ok:
            message_id = _find_value(result.payload, ("id", "messageId"))
            return WhatsAppDelivery(
                True,
                "sent",
                "evolution:sent",
                "Mensagem aceita pela Evolution API.",
                str(message_id) if message_id else None,
            )
        status_map = {
            "missing_credentials": "missing_credentials",
            "rate_limited": "rate_limited",
            "unavailable": "provider_unavailable",
            "not_found": "qr_required",
        }
        status = status_map.get(result.status, "failed")
        return WhatsAppDelivery(False, status, f"evolution:{result.status}", result.message)


class WhatsAppConnection:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.system_channel = SystemWhatsAppChannel(
            enabled=self.settings.root_whatsapp_enabled,
            provider=self.settings.root_whatsapp_provider,
            number=self.settings.root_whatsapp_number,
            name=self.settings.root_whatsapp_name,
        )

    def session(self, tenant_id: UUID | None = None, include_qr: bool = False) -> WhatsAppSession:
        now = datetime.now(timezone.utc)
        provider = (self.system_channel.provider or self.settings.whatsapp_provider or "mock").strip().lower()
        if not self.system_channel.enabled:
            return WhatsAppSession(tenant_id, provider, "disabled", False, False, None, None, now, ["Canal raiz desativado."])
        if not is_e164_phone(self.system_channel.number):
            return WhatsAppSession(
                tenant_id,
                provider,
                "missing_credentials",
                False,
                False,
                None,
                None,
                now,
                ["ROOT_WHATSAPP_NUMBER deve estar em E.164 somente com dígitos."],
            )
        if self.settings.root_whatsapp_mock_mode or provider == "mock":
            return WhatsAppSession(
                tenant_id,
                provider,
                "mock",
                False,
                False,
                None,
                None,
                now,
                ["Mock explícito ativo; nenhuma mensagem real será enviada."],
            )
        if provider == "evolution":
            return EvolutionWhatsAppProvider(self.settings).session(tenant_id, include_qr=include_qr)

        if provider in {"meta_cloud_future", "meta-future", "meta_future"}:
            return WhatsAppSession(
                tenant_id,
                provider,
                "official_ready_future",
                False,
                False,
                None,
                None,
                now,
                ["Adapter oficial Meta Cloud API preparado para migração futura."],
            )

        if provider in {"meta", "cloud-api", "whatsapp-business-api", "whatsapp_business_api"}:
            ready = bool(self.settings.whatsapp_access_token and self.settings.whatsapp_phone_number_id)
            return WhatsAppSession(
                tenant_id,
                provider,
                "connected" if ready else "official_ready_future",
                ready,
                False,
                None,
                now if ready else None,
                now,
                ["Provider oficial Meta configurado." if ready else "Adapter oficial preparado para credenciais futuras."],
            )
        if provider in {"http", "relay", "bridge"}:
            ready = bool(self.settings.root_whatsapp_base_url and self.settings.root_whatsapp_api_key)
            return WhatsAppSession(
                tenant_id,
                provider,
                "connected" if ready else "missing_credentials",
                ready,
                False,
                None,
                now if ready else None,
                now,
                ["Relay HTTP configurado." if ready else "Relay HTTP requer URL e API key."],
            )
        return WhatsAppSession(tenant_id, provider, "unofficial_failed", False, False, None, None, now, ["Provider desconhecido."])

    def test_connection(self, tenant_id: UUID | None = None) -> WhatsAppDelivery:
        session = self.session(tenant_id)
        if session.connected:
            return WhatsAppDelivery(True, session.status, f"{session.provider}:connected", "Canal WhatsApp raiz pronto para envio.")
        if session.status == "mock":
            return WhatsAppDelivery(True, "mock", f"{session.provider}:mock", "Mock explícito ativo; nenhuma mensagem real será enviada.")
        return WhatsAppDelivery(False, session.status, f"{session.provider}:{session.status}", session.logs[-1])


class WhatsAppProvider:
    name = "whatsapp"

    def __init__(self, settings: Settings | None = None) -> None:
        self.connection = WhatsAppConnection(settings)

    def send(self, tenant_id: str, message: str, to: str | None = None, metadata: dict[str, Any] | None = None) -> WhatsAppDelivery:
        destination = normalize_phone(to or self.connection.settings.whatsapp_default_recipient, self.connection.settings.whatsapp_default_country)
        session = self.connection.session(UUID(tenant_id) if tenant_id else None)
        if session.status == "disabled":
            return WhatsAppDelivery(False, "disabled", f"{session.provider}:disabled", "Canal WhatsApp raiz desativado.")
        if not destination or not is_e164_phone(destination):
            return WhatsAppDelivery(False, "missing_destination", f"{session.provider}:invalid_destination", "Destinatário WhatsApp inválido ou ausente.")
        if session.status == "mock":
            return WhatsAppDelivery(
                True,
                "mocked",
                f"{session.provider}:mock:{destination}",
                f"Mock explícito registrado para {destination}; nenhuma mensagem real foi enviada.",
                f"mock-{tenant_id}-{int(datetime.now(timezone.utc).timestamp())}",
            )

        provider = session.provider.strip().lower()
        if provider == "evolution":
            return EvolutionWhatsAppProvider(self.connection.settings).send_text(destination, message)
        if provider in {"meta", "cloud-api", "whatsapp-business-api", "whatsapp_business_api"}:
            return self._send_meta_text(destination, message)
        if provider in {"http", "relay", "bridge"}:
            return self._send_http_relay(destination, message, metadata or {})
        return WhatsAppDelivery(False, "unknown_provider", f"{provider}:unknown", "Provider configurado não possui adapter.")

    def _send_meta_text(self, destination: str, message: str) -> WhatsAppDelivery:
        settings = self.connection.settings
        if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
            return WhatsAppDelivery(False, "missing_credentials", "meta:missing_credentials", "Credenciais Meta ausentes.")
        url = f"https://graph.facebook.com/{settings.whatsapp_graph_api_version}/{settings.whatsapp_phone_number_id}/messages"
        try:
            response = httpx.post(
                url,
                headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
                json={"messaging_product": "whatsapp", "to": destination, "type": "text", "text": {"preview_url": False, "body": message[:4096]}},
                timeout=settings.whatsapp_request_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            message_id = body.get("messages", [{}])[0].get("id") if isinstance(body, dict) else None
            return WhatsAppDelivery(True, "sent", "meta:sent", "Mensagem aceita pela WhatsApp Cloud API.", message_id)
        except (httpx.HTTPError, ValueError):
            return WhatsAppDelivery(False, "failed", "meta:failed", "Falha no envio pela WhatsApp Cloud API.")

    def _send_http_relay(self, destination: str, message: str, metadata: dict[str, Any]) -> WhatsAppDelivery:
        settings = self.connection.settings
        if not settings.root_whatsapp_base_url or not settings.root_whatsapp_api_key:
            return WhatsAppDelivery(False, "missing_credentials", "relay:missing_credentials", "Relay HTTP incompleto.")
        try:
            response = httpx.post(
                f"{settings.root_whatsapp_base_url.rstrip('/')}/messages",
                headers={"Authorization": f"Bearer {settings.root_whatsapp_api_key}"},
                json={"to": destination, "message": message, "metadata": metadata},
                timeout=settings.whatsapp_request_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json() if response.content else {}
            return WhatsAppDelivery(True, "sent", "relay:sent", "Mensagem aceita pelo relay.", str(body.get("id") or body.get("messageId") or "") or None)
        except (httpx.HTTPError, ValueError):
            return WhatsAppDelivery(False, "failed", "relay:failed", "Falha no relay HTTP.")


class WhatsAppWebhook:
    def verify(self, token: str, settings: Settings | None = None) -> bool:
        settings = settings or get_settings()
        return bool(settings.whatsapp_webhook_verify_token and token == settings.whatsapp_webhook_verify_token)


class WhatsAppNotificationService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.provider = WhatsAppProvider(settings)

    def send_alert(self, tenant_id: str, title: str, message: str, to: str | None = None) -> WhatsAppDelivery:
        return self.provider.send(tenant_id, f"{title}\n\n{message}", to)


def normalize_phone(value: str | None, default_country: str = "BR") -> str | None:
    if not value:
        return None
    digits = "".join(char for char in value if char.isdigit())
    if default_country.upper() == "BR" and len(digits) in {10, 11}:
        digits = f"55{digits}"
    return digits or None


def is_e164_phone(value: str | None) -> bool:
    return bool(value and value.isdigit() and 10 <= len(value) <= 15 and not value.startswith("0"))


def normalize_evolution_webhook(payload: dict[str, Any]) -> tuple[str, str | None, str]:
    event = str(payload.get("event") or "unknown").strip().lower().replace("_", ".").replace("-", ".")
    message_id = _find_value(payload.get("data") if isinstance(payload.get("data"), dict) else payload, ("id", "messageId"))
    raw_status = str(_find_value(payload, ("status", "state", "connection")) or "").strip().lower()
    if event in {"connection.update", "logout.instance"}:
        status = "unofficial_connected" if raw_status == "open" else "unofficial_disconnected"
    elif event == "qrcode.updated":
        status = "unofficial_qr_required"
    elif any(token in raw_status for token in ("delivery", "delivered", "read", "played")):
        status = "delivered"
    elif any(token in raw_status for token in ("error", "failed")):
        status = "failed"
    else:
        status = "sent" if event in {"send.message", "send.message.update", "messages.update"} else raw_status or "received"
    return event, str(message_id) if message_id else None, status


def valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.hostname)


def _extract_qr(payload: dict[str, Any]) -> str | None:
    value = _find_value(payload, ("base64", "qrcode", "qrCode", "code"))
    if isinstance(value, dict):
        value = _find_value(value, ("base64", "code"))
    if not value:
        return None
    text = str(value)
    if text.startswith("data:image"):
        return text
    if len(text) > 200 and not text.startswith(("http://", "https://")):
        return f"data:image/png;base64,{text}"
    return text


def _find_value(payload: Any, keys: tuple[str, ...]) -> Any:
    if isinstance(payload, dict):
        for key in keys:
            if key in payload:
                candidate = payload[key]
                if candidate is not None and candidate != "":
                    return candidate
        for value in payload.values():
            found = _find_value(value, keys)
            if found is not None and found != "":
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_value(value, keys)
            if found is not None and found != "":
                return found
    return None
