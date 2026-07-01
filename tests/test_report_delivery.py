from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.delivery.scheduler.report_scheduler import ReportScheduler
from app.delivery.services.email_service import EmailService
from app.delivery.services.summary_generator import SummaryGenerator
from app.delivery.services.telegram_service import TelegramService
from app.reports.excel_report import LeadReportRow


def _lead(
    *,
    lead_id: str,
    product_name: str,
    business_name: str,
    score: int,
    category: str,
    revenue: str,
    converted: bool = False,
) -> LeadReportRow:
    now = datetime.now(UTC)
    return LeadReportRow(
        lead_id=lead_id,
        product_name=product_name,
        product_category="Pooja Items",
        quantity="10 Pieces",
        order_value=Decimal(revenue),
        lead_created_date=now,
        lead_updated_date=now,
        lead_extracted_at=now,
        buyer_name=business_name,
        business_name=business_name,
        city="Mumbai",
        state="Maharashtra",
        years_active=5,
        phone_available=True,
        email_available=True,
        whatsapp_available=True,
        address_available=True,
        business_verified=True,
        requirements_count=8,
        replies_count=2,
        qualification_score=score,
        lead_category=category,
        qualification_reasons=["Direct contact channel is available."],
        contacted=True,
        whatsapp_sent=False,
        catalog_shared=False,
        follow_up_done=False,
        negotiation_started=False,
        order_received=False,
        converted=converted,
        last_activity=now,
    )


def test_summary_generator_builds_business_summary() -> None:
    summary = SummaryGenerator().generate(
        [
            _lead(
                lead_id="L-001",
                product_name="German Silver Pooja Thali",
                business_name="ABC Traders",
                score=91,
                category="HOT",
                revenue="85000",
            ),
            _lead(
                lead_id="L-002",
                product_name="German Silver Pooja Thali",
                business_name="XYZ Stores",
                score=61,
                category="WARM",
                revenue="15000",
                converted=True,
            ),
        ],
        report_date=date(2026, 6, 11),
    )

    assert summary.total_leads == 2
    assert summary.hot_leads == 1
    assert summary.warm_leads == 1
    assert summary.conversion_rate == 50
    assert summary.top_product == "German Silver Pooja Thali"
    assert summary.top_opportunity_name == "ABC Traders"
    assert summary.estimated_revenue == Decimal("100000")
    assert "ABC Traders with 91% qualification score" in summary.as_plain_text()


def test_email_service_retries_failed_delivery(tmp_path: Path) -> None:
    report_path = tmp_path / "Lead_Intelligence_Report.xlsx"
    report_path.write_bytes(b"xlsx")

    class FlakyEmailService(EmailService):
        def __init__(self) -> None:
            super().__init__(
                smtp_host="smtp.example.com",
                smtp_port=587,
                username="user",
                password="password",
                sender="sender@example.com",
                retry_attempts=2,
                retry_backoff_seconds=0,
            )
            self.calls = 0

        def _send_once(
            self,
            recipient: str,
            subject: str,
            html_body: str,
            attachment_path: Path,
        ) -> None:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary smtp failure")

    service = FlakyEmailService()

    result = service._send_with_retry(
        "owner@example.com",
        "Lead Intelligence Report",
        "<p>Summary</p>",
        report_path,
    )

    assert result.success is True
    assert result.attempts == 2
    assert service.calls == 2


@pytest.mark.asyncio
async def test_telegram_service_retries_failed_delivery(tmp_path: Path) -> None:
    report_path = tmp_path / "Lead_Intelligence_Report.xlsx"
    report_path.write_bytes(b"xlsx")

    class FakeBot:
        def __init__(self) -> None:
            self.message_calls = 0
            self.document_calls = 0

        async def send_message(self, *, chat_id: str, text: str) -> None:
            self.message_calls += 1
            if self.message_calls == 1:
                raise RuntimeError("temporary telegram failure")

        async def send_document(
            self,
            *,
            chat_id: str,
            document,
            filename: str,
            caption: str,
        ) -> None:
            self.document_calls += 1

    bot = FakeBot()
    service = TelegramService(
        bot_token="token",
        retry_attempts=2,
        retry_backoff_seconds=0,
        bot=bot,
    )

    results = await service.send_report(
        chat_ids=["123"],
        message="Lead Intelligence Report",
        attachment_path=report_path,
    )

    assert results[0].success is True
    assert results[0].attempts == 2
    assert bot.message_calls == 2
    assert bot.document_calls == 1


def test_report_scheduler_registers_daily_weekly_and_monthly_jobs(monkeypatch) -> None:
    class FakeScheduler:
        running = False

        def __init__(self) -> None:
            self.jobs = []
            self.started = False

        def add_job(self, func, **kwargs) -> None:
            self.jobs.append(kwargs)

        def start(self) -> None:
            self.started = True
            self.running = True

    class FakeDeliveryAgent:
        async def deliver_report(self) -> Path:
            return Path("Lead_Intelligence_Report.xlsx")

    fake_scheduler = FakeScheduler()
    monkeypatch.setattr(
        "app.delivery.scheduler.report_scheduler.settings.report_scheduler_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.delivery.scheduler.report_scheduler.settings.daily_report_time",
        "08:30",
    )
    monkeypatch.setattr(
        "app.delivery.scheduler.report_scheduler.settings.weekly_report_day",
        "fri",
    )
    monkeypatch.setattr(
        "app.delivery.scheduler.report_scheduler.settings.monthly_report_day",
        15,
    )

    scheduler = ReportScheduler(delivery_agent=FakeDeliveryAgent(), scheduler=fake_scheduler)

    scheduler.start()

    assert fake_scheduler.started is True
    assert [job["id"] for job in fake_scheduler.jobs] == [
        "daily_lead_intelligence_report",
        "weekly_lead_intelligence_report",
        "monthly_lead_intelligence_report",
    ]
    assert fake_scheduler.jobs[0]["hour"] == 8
    assert fake_scheduler.jobs[0]["minute"] == 30
    assert fake_scheduler.jobs[1]["day_of_week"] == "fri"
    assert fake_scheduler.jobs[2]["day"] == 15
