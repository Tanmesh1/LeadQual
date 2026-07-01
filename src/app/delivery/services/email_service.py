from __future__ import annotations

import asyncio
import logging
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path

from app.delivery.services.result import DeliveryResult

LOGGER = logging.getLogger(__name__)


class EmailService:
    def __init__(
        self,
        *,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        sender: str,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 2,
        use_tls: bool = True,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.sender = sender
        self.retry_attempts = max(1, retry_attempts)
        self.retry_backoff_seconds = max(0, retry_backoff_seconds)
        self.use_tls = use_tls

    async def send_report(
        self,
        *,
        recipients: list[str],
        subject: str,
        html_body: str,
        attachment_path: Path,
    ) -> list[DeliveryResult]:
        return [
            await asyncio.to_thread(
                self._send_with_retry,
                recipient,
                subject,
                html_body,
                attachment_path,
            )
            for recipient in recipients
        ]

    def _send_with_retry(
        self,
        recipient: str,
        subject: str,
        html_body: str,
        attachment_path: Path,
    ) -> DeliveryResult:
        last_error: Exception | None = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                self._send_once(recipient, subject, html_body, attachment_path)
                return DeliveryResult(recipient=recipient, success=True, attempts=attempt)
            except Exception as exc:
                last_error = exc
                LOGGER.exception("Email delivery failed for %s on attempt %s", recipient, attempt)
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_backoff_seconds * attempt)

        return DeliveryResult(
            recipient=recipient,
            success=False,
            attempts=self.retry_attempts,
            error_message=str(last_error) if last_error else "Unknown email delivery error",
        )

    def _send_once(
        self,
        recipient: str,
        subject: str,
        html_body: str,
        attachment_path: Path,
    ) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(_html_to_text(html_body))
        message.add_alternative(html_body, subtype="html")
        message.add_attachment(
            attachment_path.read_bytes(),
            maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=attachment_path.name,
        )

        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username:
                smtp.login(self.username, self.password)
            smtp.send_message(message)


def _html_to_text(html_body: str) -> str:
    return (
        html_body.replace("<br>", "\n")
        .replace("<br/>", "\n")
        .replace("<br />", "\n")
        .replace("</p>", "\n")
        .replace("</li>", "\n")
        .replace("<li>", "- ")
        .replace("<h2>", "")
        .replace("</h2>", "\n")
        .replace("<ul>", "")
        .replace("</ul>", "")
        .replace("<strong>", "")
        .replace("</strong>", "")
        .replace("<p>", "")
    )
