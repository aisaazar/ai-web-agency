"""Notification provider contract with offline and SMTP implementations."""
from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol


@dataclass(frozen=True)
class Notification:
    to: str
    subject: str
    body: str


class NotifyProvider(Protocol):
    name: str

    def send(self, notification: Notification) -> None: ...


@dataclass(frozen=True)
class ConsoleNotifyProvider:
    name: str = "console"

    def send(self, notification: Notification) -> None:
        print(
            f"[notification] to={notification.to} "
            f"subject={notification.subject!r}"
        )


class SMTPNotifyProvider:
    name = "smtp"

    def __init__(self) -> None:
        self.host = os.getenv("AGENCY_SMTP_HOST", "")
        self.port = int(os.getenv("AGENCY_SMTP_PORT", "587"))
        self.username = os.getenv("AGENCY_SMTP_USERNAME", "")
        self.password = os.getenv("AGENCY_SMTP_PASSWORD", "")
        self.sender = os.getenv("AGENCY_SMTP_FROM", self.username)
        if not self.host or not self.sender:
            raise RuntimeError("SMTP notification provider is not configured")

    def send(self, notification: Notification) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = notification.to
        message["Subject"] = notification.subject
        message.set_content(notification.body)

        with smtplib.SMTP(self.host, self.port, timeout=15) as client:
            client.starttls()
            if self.username:
                client.login(self.username, self.password)
            client.send_message(message)


_NOTIFY_REGISTRY = {
    "console": ConsoleNotifyProvider,
    "smtp": SMTPNotifyProvider,
}


def get_notify_provider(name: str | None = None) -> NotifyProvider:
    provider_name = name or os.getenv("AGENCY_NOTIFY_PROVIDER", "console")
    try:
        return _NOTIFY_REGISTRY[provider_name]()
    except KeyError as exc:
        raise NotImplementedError(
            f"Notification provider '{provider_name}' is not registered"
        ) from exc
