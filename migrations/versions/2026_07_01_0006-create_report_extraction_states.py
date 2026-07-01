"""create report extraction states table

Revision ID: 202607010006
Revises: 202606110005
Create Date: 2026-07-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202607010006"
down_revision: str | None = "202606110005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_extraction_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_name", sa.String(length=255), nullable=False),
        sa.Column("last_extracted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_report_extraction_states_report_name",
        "report_extraction_states",
        ["report_name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_report_extraction_states_report_name",
        table_name="report_extraction_states",
    )
    op.drop_table("report_extraction_states")
