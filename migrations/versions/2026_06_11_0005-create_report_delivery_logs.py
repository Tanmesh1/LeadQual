"""create report delivery logs table

Revision ID: 202606110005
Revises: 202606110004
Create Date: 2026-06-11 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202606110005"
down_revision: str | None = "202606110004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_delivery_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_name", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("recipient", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "channel IN ('email', 'telegram')",
            name="ck_report_delivery_logs_channel",
        ),
        sa.CheckConstraint(
            "status IN ('sent', 'failed')",
            name="ck_report_delivery_logs_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_report_delivery_logs_report_name",
        "report_delivery_logs",
        ["report_name"],
        unique=False,
    )
    op.create_index(
        "ix_report_delivery_logs_channel",
        "report_delivery_logs",
        ["channel"],
        unique=False,
    )
    op.create_index(
        "ix_report_delivery_logs_status",
        "report_delivery_logs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_report_delivery_logs_sent_at",
        "report_delivery_logs",
        ["sent_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_report_delivery_logs_sent_at", table_name="report_delivery_logs")
    op.drop_index("ix_report_delivery_logs_status", table_name="report_delivery_logs")
    op.drop_index("ix_report_delivery_logs_channel", table_name="report_delivery_logs")
    op.drop_index("ix_report_delivery_logs_report_name", table_name="report_delivery_logs")
    op.drop_table("report_delivery_logs")
