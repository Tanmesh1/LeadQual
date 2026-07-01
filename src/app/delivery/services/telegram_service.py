from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from app.delivery.services.result import DeliveryResult

LOGGER = logging.getLogger(__name__)


class TelegramService:
    def __init__(
        self,
        *,
        bot_token: str,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 2,
        bot: Any | None = None,
    ) -> None:
        self.bot_token = bot_token
        self.retry_attempts = max(1, retry_attempts)
        self.retry_backoff_seconds = max(0, retry_backoff_seconds)
        self._bot = bot

    async def send_report(
        self,
        *,
        chat_ids: list[str],
        message: str,
        attachment_path: Path,
    ) -> list[DeliveryResult]:
        return [
            await self._send_with_retry(chat_id, message, attachment_path)
            for chat_id in chat_ids
        ]

    async def _send_with_retry(
        self,
        chat_id: str,
        message: str,
        attachment_path: Path,
    ) -> DeliveryResult:
        last_error: Exception | None = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                await self._send_once(chat_id, message, attachment_path)
                return DeliveryResult(recipient=chat_id, success=True, attempts=attempt)
            except Exception as exc:
                last_error = exc
                LOGGER.exception("Telegram delivery failed for %s on attempt %s", chat_id, attempt)
                if attempt < self.retry_attempts:
                    await asyncio.sleep(self.retry_backoff_seconds * attempt)

        return DeliveryResult(
            recipient=chat_id,
            success=False,
            attempts=self.retry_attempts,
            error_message=str(last_error) if last_error else "Unknown Telegram delivery error",
        )

    async def _send_once(self, chat_id: str, message: str, attachment_path: Path) -> None:
        bot = self._get_bot()
        await bot.send_message(chat_id=chat_id, text=message)
        with attachment_path.open("rb") as report_file:
            await bot.send_document(
                chat_id=chat_id,
                document=report_file,
                filename=attachment_path.name,
                caption="Lead Intelligence Report",
            )

    def _get_bot(self) -> Any:
        if self._bot is None:
            from telegram import Bot

            self._bot = Bot(token=self.bot_token)
        return self._bot
