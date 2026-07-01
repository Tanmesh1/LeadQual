import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReportDeliveryLog(Base):
    __tablename__ = "report_delivery_logs"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('email', 'telegram')",
            name="ck_report_delivery_logs_channel",
        ),
        CheckConstraint(
            "status IN ('sent', 'failed')",
            name="ck_report_delivery_logs_status",
        ),
        Index("ix_report_delivery_logs_report_name", "report_name"),
        Index("ix_report_delivery_logs_channel", "channel"),
        Index("ix_report_delivery_logs_status", "status"),
        Index("ix_report_delivery_logs_sent_at", "sent_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    report_name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
