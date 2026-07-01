from sqlalchemy.ext.asyncio import AsyncSession

from app.delivery.models.delivery_log import ReportDeliveryLog


class DeliveryLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        report_name: str,
        channel: str,
        recipient: str,
        status: str,
        error_message: str | None = None,
    ) -> ReportDeliveryLog:
        log = ReportDeliveryLog(
            report_name=report_name,
            channel=channel,
            recipient=recipient,
            status=status,
            error_message=error_message,
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log
