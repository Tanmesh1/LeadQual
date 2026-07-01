"""add indiamart lead scoring fields

Revision ID: 202606110004
Revises: 202606050003
Create Date: 2026-06-11 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202606110004"
down_revision: str | None = "202606050003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("indiamart_leads", sa.Column("lead_score_value", sa.Integer(), nullable=True))
    op.add_column("indiamart_leads", sa.Column("lead_score_category", sa.String(50), nullable=True))
    op.add_column(
        "indiamart_leads",
        sa.Column(
            "lead_score_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "indiamart_leads",
        sa.Column(
            "lead_score_explanation",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "indiamart_leads",
        sa.Column("lead_scored_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_indiamart_leads_lead_score_value_range",
        "indiamart_leads",
        "lead_score_value IS NULL OR (lead_score_value >= 0 AND lead_score_value <= 100)",
    )
    op.create_check_constraint(
        "ck_indiamart_leads_lead_score_category",
        "indiamart_leads",
        "lead_score_category IS NULL OR lead_score_category IN ('HOT', 'WARM', 'COLD')",
    )
    op.create_index(
        "ix_indiamart_leads_lead_score_category",
        "indiamart_leads",
        ["lead_score_category"],
        unique=False,
    )
    op.create_index(
        "ix_indiamart_leads_lead_scored_at",
        "indiamart_leads",
        ["lead_scored_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_indiamart_leads_lead_scored_at", table_name="indiamart_leads")
    op.drop_index("ix_indiamart_leads_lead_score_category", table_name="indiamart_leads")
    op.drop_constraint(
        "ck_indiamart_leads_lead_score_category",
        "indiamart_leads",
        type_="check",
    )
    op.drop_constraint(
        "ck_indiamart_leads_lead_score_value_range",
        "indiamart_leads",
        type_="check",
    )
    op.drop_column("indiamart_leads", "lead_scored_at")
    op.drop_column("indiamart_leads", "lead_score_explanation")
    op.drop_column("indiamart_leads", "lead_score_reasons")
    op.drop_column("indiamart_leads", "lead_score_category")
    op.drop_column("indiamart_leads", "lead_score_value")
