from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.config import Settings, get_settings
from app.email_channels import EmailNotificationService
from app.whatsapp import WhatsAppNotificationService


@dataclass(frozen=True)
class NotificationPayload:
    title: str
    message: str
    tenant_id: str
    destination: str | None = None


@dataclass(frozen=True)
class NotificationDelivery:
    status: str
    provider_result: str


class NotificationProvider(Protocol):
    name: str

    def send(self, payload: NotificationPayload) -> NotificationDelivery: ...


class WindowsProvider:
    name = "windows"

    def send(self, payload: NotificationPayload) -> NotificationDelivery:
        return NotificationDelivery(status="mocked", provider_result=f"windows:agent-queue:{payload.tenant_id}")


class EmailProvider:
    name = "email"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, payload: NotificationPayload) -> NotificationDelivery:
        delivery = EmailNotificationService(self._settings).send_test(
            to=payload.destination,
            subject=payload.title,
            message=payload.message,
            provider=self._settings.email_provider,
        )
        return NotificationDelivery(status=delivery.status, provider_result=delivery.provider_result)


class WhatsAppProvider:
    name = "whatsapp"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, payload: NotificationPayload) -> NotificationDelivery:
        delivery = WhatsAppNotificationService(self._settings).send_alert(
            tenant_id=payload.tenant_id,
            title=payload.title,
            message=payload.message,
            to=payload.destination,
        )
        return NotificationDelivery(status=delivery.status, provider_result=delivery.provider_result)


class PushProvider:
    name = "push"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, payload: NotificationPayload) -> NotificationDelivery:
        if self._settings.fcm_server_key or self._settings.fcm_vapid_key:
            return NotificationDelivery(status="ready", provider_result=f"fcm:ready:{payload.tenant_id}")
        return NotificationDelivery(status="missing_credentials", provider_result=f"push:missing_credentials:{payload.tenant_id}")


class SystemProvider:
    def __init__(self, name: str) -> None:
        self.name = name

    def send(self, payload: NotificationPayload) -> NotificationDelivery:
        return NotificationDelivery(status="ready", provider_result=f"{self.name}:queued:{payload.tenant_id}")


class NotificationService:
    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        self.providers: dict[str, NotificationProvider] = {
            "system": SystemProvider("system"),
            "windows": WindowsProvider(),
            "whatsapp": WhatsAppProvider(settings),
            "email": EmailProvider(settings),
            "push": PushProvider(settings),
        }

    def send(self, channel: str, payload: NotificationPayload) -> NotificationDelivery:
        provider = self.providers.get(channel)
        if provider is None:
            raise ValueError(f"unknown notification channel: {channel}")
        return provider.send(payload)
