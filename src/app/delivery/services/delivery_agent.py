from __future__ import annotations

import asyncio
import logging
from datetime import date
from pathlib import Path

from app.core.config import settings
from app.db.session import get_session_factory
from app.delivery.repositories.delivery_log_repository import DeliveryLogRepository
from app.delivery.services.email_service import EmailService
from app.delivery.services.result import DeliveryResult
from app.delivery.services.summary_generator import SummaryGenerator
from app.delivery.services.telegram_service import TelegramService
from app.reports.excel_report import DataFetcher, ExcelReportGenerator

LOGGER = logging.getLogger(__name__)


class ReportDeliveryAgent:
    def __init__(
        self,
        *,
        report_generator: ExcelReportGenerator | None = None,
        data_fetcher: DataFetcher | None = None,
        summary_generator: SummaryGenerator | None = None,
        email_service: EmailService | None = None,
        telegram_service: TelegramService | None = None,
        email_recipients: list[str] | None = None,
        telegram_chat_ids: list[str] | None = None,
    ) -> None:
        self.report_generator = report_generator or ExcelReportGenerator(
            output_path=settings.report_output_path
        )
        self.data_fetcher = data_fetcher or DataFetcher()
        self.summary_generator = summary_generator or SummaryGenerator()
        self.email_service = email_service or _build_email_service()
        self.telegram_service = telegram_service or _build_telegram_service()
        self.email_recipients = email_recipients or _split_csv(settings.report_email_recipients)
        self.telegram_chat_ids = telegram_chat_ids or _telegram_chat_ids()

    async def deliver_report(self) -> Path:
        report_path = await asyncio.to_thread(self.report_generator.generate_report)
        self._validate_report(report_path)

        leads = getattr(self.report_generator, "last_generated_leads", None)
        if leads is None:
            leads = await asyncio.to_thread(self.data_fetcher.fetch_leads)
        summary = self.summary_generator.generate(leads)
        subject = f"Lead Intelligence Report - {date.today().isoformat()}"

        if self.email_recipients:
            email_results = await self.email_service.send_report(
                recipients=self.email_recipients,
                subject=subject,
                html_body=summary.as_email_html(),
                attachment_path=report_path,
            )
            await self._log_results(report_path.name, "email", email_results)
        else:
            LOGGER.info("Skipping email report delivery because no recipients are configured")

        if self.telegram_chat_ids:
            telegram_results = await self.telegram_service.send_report(
                chat_ids=self.telegram_chat_ids,
                message=summary.as_telegram_text(),
                attachment_path=report_path,
            )
            await self._log_results(report_path.name, "telegram", telegram_results)
        else:
            LOGGER.info("Skipping Telegram report delivery because no chat IDs are configured")

        return report_path

    @staticmethod
    def _validate_report(report_path: Path) -> None:
        if not report_path.exists():
            raise FileNotFoundError(f"Report file does not exist: {report_path}")
        if report_path.stat().st_size == 0:
            raise ValueError(f"Report file is empty: {report_path}")

    @staticmethod
    async def _log_results(report_name: str, channel: str, results: list[DeliveryResult]) -> None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            repository = DeliveryLogRepository(session)
            for result in results:
                await repository.create(
                    report_name=report_name,
                    channel=channel,
                    recipient=result.recipient,
                    status=result.status,
                    error_message=result.error_message,
                )


def _build_email_service() -> EmailService:
    return EmailService(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        sender=settings.smtp_sender,
        retry_attempts=settings.report_delivery_retry_attempts,
        retry_backoff_seconds=settings.report_delivery_retry_backoff_seconds,
        use_tls=settings.smtp_use_tls,
    )


def _build_telegram_service() -> TelegramService:
    return TelegramService(
        bot_token=settings.telegram_bot_token,
        retry_attempts=settings.report_delivery_retry_attempts,
        retry_backoff_seconds=settings.report_delivery_retry_backoff_seconds,
    )


def _telegram_chat_ids() -> list[str]:
    return _split_csv(settings.telegram_chat_ids or settings.telegram_chat_id)


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
