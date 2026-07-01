"""create indiamart leads table

Revision ID: 202606050003
Revises: 202606050002
Create Date: 2026-06-05 14:35:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202606050003"
down_revision: str | None = "202606050002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "indiamart_leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("external_lead_id", sa.String(length=255), nullable=True),
        sa.Column("product_name", sa.String(length=255), nullable=True),
        sa.Column("product_category", sa.String(length=255), nullable=True),
        sa.Column("quantity", sa.String(length=255), nullable=True),
        sa.Column("order_value", sa.String(length=255), nullable=True),
        sa.Column("purpose", sa.String(length=255), nullable=True),
        sa.Column("lead_time", sa.String(length=255), nullable=True),
        sa.Column("buyer_name", sa.String(length=255), nullable=True),
        sa.Column("business_name", sa.String(length=255), nullable=True),
        sa.Column("phone_available", sa.Boolean(), nullable=False),
        sa.Column("email_available", sa.Boolean(), nullable=False),
        sa.Column("whatsapp_available", sa.Boolean(), nullable=False),
        sa.Column("business_available", sa.Boolean(), nullable=False),
        sa.Column("address_available", sa.Boolean(), nullable=False),
        sa.Column("years_active", sa.Integer(), nullable=True),
        sa.Column("requirements_count", sa.Integer(), nullable=True),
        sa.Column("replies_count", sa.Integer(), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column(
            "raw_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.CheckConstraint(
            "years_active IS NULL OR years_active >= 0",
            name="ck_indiamart_leads_years_active_non_negative",
        ),
        sa.CheckConstraint(
            "requirements_count IS NULL OR requirements_count >= 0",
            name="ck_indiamart_leads_requirements_count_non_negative",
        ),
        sa.CheckConstraint(
            "replies_count IS NULL OR replies_count >= 0",
            name="ck_indiamart_leads_replies_count_non_negative",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lead_fingerprint", name="uq_indiamart_leads_fingerprint"),
    )
    op.create_index(
        "ix_indiamart_leads_product_name",
        "indiamart_leads",
        ["product_name"],
        unique=False,
    )
    op.create_index(
        "ix_indiamart_leads_product_category",
        "indiamart_leads",
        ["product_category"],
        unique=False,
    )
    op.create_index(
        "ix_indiamart_leads_buyer_name",
        "indiamart_leads",
        ["buyer_name"],
        unique=False,
    )
    op.create_index(
        "ix_indiamart_leads_business_name",
        "indiamart_leads",
        ["business_name"],
        unique=False,
    )
    op.create_index(
        "ix_indiamart_leads_city_state",
        "indiamart_leads",
        ["city", "state"],
        unique=False,
    )
    op.create_index(
        "ix_indiamart_leads_extracted_at",
        "indiamart_leads",
        ["extracted_at"],
        unique=False,
    )
    op.create_index(
        "ix_indiamart_leads_raw_payload_gin",
        "indiamart_leads",
        ["raw_payload"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_indiamart_leads_raw_payload_gin", table_name="indiamart_leads")
    op.drop_index("ix_indiamart_leads_extracted_at", table_name="indiamart_leads")
    op.drop_index("ix_indiamart_leads_city_state", table_name="indiamart_leads")
    op.drop_index("ix_indiamart_leads_business_name", table_name="indiamart_leads")
    op.drop_index("ix_indiamart_leads_buyer_name", table_name="indiamart_leads")
    op.drop_index("ix_indiamart_leads_product_category", table_name="indiamart_leads")
    op.drop_index("ix_indiamart_leads_product_name", table_name="indiamart_leads")
    op.drop_table("indiamart_leads")
