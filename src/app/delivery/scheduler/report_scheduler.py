from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.delivery.services.delivery_agent import ReportDeliveryAgent

LOGGER = logging.getLogger(__name__)


class ReportScheduler:
    def __init__(
        self,
        *,
        delivery_agent: ReportDeliveryAgent | None = None,
        scheduler: Any | None = None,
    ) -> None:
        self.delivery_agent = delivery_agent or ReportDeliveryAgent()
        self.scheduler = scheduler

    def start(self) -> None:
        if not settings.report_scheduler_enabled:
            LOGGER.info("Report scheduler is disabled")
            return

        if self.scheduler is None:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler

            self.scheduler = AsyncIOScheduler(timezone=settings.report_scheduler_timezone)

        self._add_jobs()
        self.scheduler.start()
        LOGGER.info("Report scheduler started")

    def shutdown(self) -> None:
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            LOGGER.info("Report scheduler stopped")

    def _add_jobs(self) -> None:
        hour, minute = _parse_hhmm(settings.daily_report_time)

        self.scheduler.add_job(
            self.delivery_agent.deliver_report,
            trigger="cron",
            hour=hour,
            minute=minute,
            id="daily_lead_intelligence_report",
            replace_existing=True,
            max_instances=1,
        )
        self.scheduler.add_job(
            self.delivery_agent.deliver_report,
            trigger="cron",
            day_of_week=settings.weekly_report_day,
            hour=hour,
            minute=minute,
            id="weekly_lead_intelligence_report",
            replace_existing=True,
            max_instances=1,
        )
        self.scheduler.add_job(
            self.delivery_agent.deliver_report,
            trigger="cron",
            day=settings.monthly_report_day,
            hour=hour,
            minute=minute,
            id="monthly_lead_intelligence_report",
            replace_existing=True,
            max_instances=1,
        )


def _parse_hhmm(value: str) -> tuple[int, int]:
    raw_hour, raw_minute = value.split(":", maxsplit=1)
    hour = int(raw_hour)
    minute = int(raw_minute)
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("Report time must be in HH:MM 24-hour format")
    return hour, minute
