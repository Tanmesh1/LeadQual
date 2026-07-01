"""lead qualification platform schema

Revision ID: 202606050002
Revises: 202606040001
Create Date: 2026-06-05 00:02:00.000000
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202606050002"
down_revision: str | None = "202606040001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_BUYER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def upgrade() -> None:
    op.create_table(
        "buyers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("website_url", sa.String(length=500), nullable=True),
        sa.Column("industry", sa.String(length=150), nullable=True),
        sa.Column("employee_count_min", sa.Integer(), nullable=True),
        sa.Column("employee_count_max", sa.Integer(), nullable=True),
        sa.Column("annual_revenue_usd", sa.Numeric(18, 2), nullable=True),
        sa.Column(
            "target_markets",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "ideal_customer_profile",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
            "employee_count_min IS NULL OR employee_count_min >= 0",
            name="ck_buyers_employee_count_min_non_negative",
        ),
        sa.CheckConstraint(
            "employee_count_max IS NULL OR employee_count_max >= employee_count_min",
            name="ck_buyers_employee_count_range",
        ),
        sa.CheckConstraint(
            "annual_revenue_usd IS NULL OR annual_revenue_usd >= 0",
            name="ck_buyers_annual_revenue_non_negative",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_buyers_name", "buyers", ["name"], unique=False)
    op.create_index("ix_buyers_domain", "buyers", ["domain"], unique=True)
    op.create_index("ix_buyers_industry", "buyers", ["industry"], unique=False)

    op.execute(
        sa.text(
            """
            INSERT INTO buyers (id, name, is_active)
            VALUES (:buyer_id, 'Default Buyer', true)
            ON CONFLICT (id) DO NOTHING
            """
        ).bindparams(buyer_id=DEFAULT_BUYER_ID)
    )

    op.drop_index(op.f("ix_leads_email"), table_name="leads")
    op.add_column(
        "leads",
        sa.Column("buyer_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("leads", sa.Column("job_title", sa.String(length=255), nullable=True))
    op.add_column("leads", sa.Column("phone", sa.String(length=50), nullable=True))
    op.add_column("leads", sa.Column("linkedin_url", sa.String(length=500), nullable=True))
    op.add_column("leads", sa.Column("source", sa.String(length=100), nullable=True))
    op.add_column(
        "leads",
        sa.Column("status", sa.String(length=50), server_default="new", nullable=False),
    )
    op.add_column("leads", sa.Column("company_domain", sa.String(length=255), nullable=True))
    op.add_column(
        "leads",
        sa.Column("company_website_url", sa.String(length=500), nullable=True),
    )
    op.add_column("leads", sa.Column("company_industry", sa.String(length=150), nullable=True))
    op.add_column("leads", sa.Column("company_employee_count", sa.Integer(), nullable=True))
    op.add_column(
        "leads",
        sa.Column("company_annual_revenue_usd", sa.Numeric(18, 2), nullable=True),
    )
    op.add_column("leads", sa.Column("country", sa.String(length=100), nullable=True))
    op.add_column("leads", sa.Column("region", sa.String(length=100), nullable=True))
    op.add_column("leads", sa.Column("city", sa.String(length=100), nullable=True))
    op.add_column("leads", sa.Column("timezone", sa.String(length=100), nullable=True))
    op.add_column(
        "leads",
        sa.Column(
            "raw_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.execute(
        sa.text("UPDATE leads SET buyer_id = :buyer_id WHERE buyer_id IS NULL").bindparams(
            buyer_id=DEFAULT_BUYER_ID
        )
    )
    op.alter_column(
        "leads",
        "buyer_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_leads_buyer_id_buyers",
        "leads",
        "buyers",
        ["buyer_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_leads_status",
        "leads",
        "status IN ('new', 'contacted', 'qualified', 'disqualified', 'converted', 'archived')",
    )
    op.create_check_constraint(
        "ck_leads_company_employee_count_non_negative",
        "leads",
        "company_employee_count IS NULL OR company_employee_count >= 0",
    )
    op.create_check_constraint(
        "ck_leads_company_annual_revenue_non_negative",
        "leads",
        "company_annual_revenue_usd IS NULL OR company_annual_revenue_usd >= 0",
    )
    op.create_unique_constraint("uq_leads_buyer_email", "leads", ["buyer_id", "email"])
    op.create_index("ix_leads_email", "leads", ["email"], unique=False)
    op.create_index("ix_leads_buyer_id", "leads", ["buyer_id"], unique=False)
    op.create_index("ix_leads_status", "leads", ["status"], unique=False)
    op.create_index("ix_leads_source", "leads", ["source"], unique=False)
    op.create_index("ix_leads_created_at", "leads", ["created_at"], unique=False)

    op.create_table(
        "lead_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score_value", sa.Numeric(5, 2), nullable=False),
        sa.Column("score_band", sa.String(length=50), nullable=True),
        sa.Column("scoring_method", sa.String(length=100), nullable=False),
        sa.Column("model_name", sa.String(length=150), nullable=True),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column(
            "feature_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column(
            "scored_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "score_value >= 0 AND score_value <= 100",
            name="ck_lead_scores_score_value_range",
        ),
        sa.CheckConstraint(
            "score_band IS NULL OR score_band IN ('cold', 'warm', 'hot', 'qualified')",
            name="ck_lead_scores_score_band",
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_scores_lead_id", "lead_scores", ["lead_id"], unique=False)
    op.create_index("ix_lead_scores_scored_at", "lead_scores", ["scored_at"], unique=False)
    op.create_index(
        "ix_lead_scores_model",
        "lead_scores",
        ["model_name", "model_version"],
        unique=False,
    )
    op.create_index(
        "ix_lead_scores_lead_scored_at",
        "lead_scores",
        ["lead_id", "scored_at"],
        unique=False,
    )
    op.create_index(
        "ix_lead_scores_feature_snapshot_gin",
        "lead_scores",
        ["feature_snapshot"],
        unique=False,
        postgresql_using="gin",
    )

    op.create_table(
        "lead_activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("activity_type", sa.String(length=100), nullable=False),
        sa.Column("actor_type", sa.String(length=50), nullable=False),
        sa.Column("actor_id", sa.String(length=255), nullable=True),
        sa.Column("channel", sa.String(length=50), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column(
            "activity_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "actor_type IN ('system', 'user', 'lead', 'buyer', 'integration')",
            name="ck_lead_activity_logs_actor_type",
        ),
        sa.CheckConstraint(
            "channel IS NULL OR channel IN ('email', 'phone', 'sms', 'web', 'chat', 'crm', "
            "'social', 'event', 'other')",
            name="ck_lead_activity_logs_channel",
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lead_activity_logs_lead_id",
        "lead_activity_logs",
        ["lead_id"],
        unique=False,
    )
    op.create_index(
        "ix_lead_activity_logs_activity_type",
        "lead_activity_logs",
        ["activity_type"],
        unique=False,
    )
    op.create_index(
        "ix_lead_activity_logs_channel",
        "lead_activity_logs",
        ["channel"],
        unique=False,
    )
    op.create_index(
        "ix_lead_activity_logs_occurred_at",
        "lead_activity_logs",
        ["occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_lead_activity_logs_lead_occurred_at",
        "lead_activity_logs",
        ["lead_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_lead_activity_logs_metadata_gin",
        "lead_activity_logs",
        ["activity_metadata"],
        unique=False,
        postgresql_using="gin",
    )

    op.create_table(
        "lead_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outcome_type", sa.String(length=50), nullable=False),
        sa.Column("outcome_reason", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("deal_value_usd", sa.Numeric(18, 2), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("label_source", sa.String(length=100), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "outcome_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
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
            "outcome_type IN ('qualified', 'disqualified', 'converted', 'lost', 'nurture', "
            "'duplicate', 'invalid')",
            name="ck_lead_outcomes_outcome_type",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_lead_outcomes_confidence_range",
        ),
        sa.CheckConstraint(
            "deal_value_usd IS NULL OR deal_value_usd >= 0",
            name="ck_lead_outcomes_deal_value_non_negative",
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lead_outcomes_lead_id", "lead_outcomes", ["lead_id"], unique=False)
    op.create_index(
        "ix_lead_outcomes_outcome_type",
        "lead_outcomes",
        ["outcome_type"],
        unique=False,
    )
    op.create_index("ix_lead_outcomes_closed_at", "lead_outcomes", ["closed_at"], unique=False)
    op.create_index(
        "ix_lead_outcomes_label_source",
        "lead_outcomes",
        ["label_source"],
        unique=False,
    )
    op.create_index(
        "uq_lead_outcomes_current_lead",
        "lead_outcomes",
        ["lead_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
    )
    op.create_index(
        "ix_lead_outcomes_metadata_gin",
        "lead_outcomes",
        ["outcome_metadata"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_lead_outcomes_metadata_gin", table_name="lead_outcomes")
    op.drop_index("uq_lead_outcomes_current_lead", table_name="lead_outcomes")
    op.drop_index("ix_lead_outcomes_label_source", table_name="lead_outcomes")
    op.drop_index("ix_lead_outcomes_closed_at", table_name="lead_outcomes")
    op.drop_index("ix_lead_outcomes_outcome_type", table_name="lead_outcomes")
    op.drop_index("ix_lead_outcomes_lead_id", table_name="lead_outcomes")
    op.drop_table("lead_outcomes")

    op.drop_index("ix_lead_activity_logs_metadata_gin", table_name="lead_activity_logs")
    op.drop_index("ix_lead_activity_logs_lead_occurred_at", table_name="lead_activity_logs")
    op.drop_index("ix_lead_activity_logs_occurred_at", table_name="lead_activity_logs")
    op.drop_index("ix_lead_activity_logs_channel", table_name="lead_activity_logs")
    op.drop_index("ix_lead_activity_logs_activity_type", table_name="lead_activity_logs")
    op.drop_index("ix_lead_activity_logs_lead_id", table_name="lead_activity_logs")
    op.drop_table("lead_activity_logs")

    op.drop_index("ix_lead_scores_feature_snapshot_gin", table_name="lead_scores")
    op.drop_index("ix_lead_scores_lead_scored_at", table_name="lead_scores")
    op.drop_index("ix_lead_scores_model", table_name="lead_scores")
    op.drop_index("ix_lead_scores_scored_at", table_name="lead_scores")
    op.drop_index("ix_lead_scores_lead_id", table_name="lead_scores")
    op.drop_table("lead_scores")

    op.drop_index("ix_leads_created_at", table_name="leads")
    op.drop_index("ix_leads_source", table_name="leads")
    op.drop_index("ix_leads_status", table_name="leads")
    op.drop_index("ix_leads_buyer_id", table_name="leads")
    op.drop_index("ix_leads_email", table_name="leads")
    op.drop_constraint("uq_leads_buyer_email", "leads", type_="unique")
    op.drop_constraint("ck_leads_company_annual_revenue_non_negative", "leads", type_="check")
    op.drop_constraint("ck_leads_company_employee_count_non_negative", "leads", type_="check")
    op.drop_constraint("ck_leads_status", "leads", type_="check")
    op.drop_constraint("fk_leads_buyer_id_buyers", "leads", type_="foreignkey")
    op.drop_column("leads", "raw_payload")
    op.drop_column("leads", "timezone")
    op.drop_column("leads", "city")
    op.drop_column("leads", "region")
    op.drop_column("leads", "country")
    op.drop_column("leads", "company_annual_revenue_usd")
    op.drop_column("leads", "company_employee_count")
    op.drop_column("leads", "company_industry")
    op.drop_column("leads", "company_website_url")
    op.drop_column("leads", "company_domain")
    op.drop_column("leads", "status")
    op.drop_column("leads", "source")
    op.drop_column("leads", "linkedin_url")
    op.drop_column("leads", "phone")
    op.drop_column("leads", "job_title")
    op.drop_column("leads", "buyer_id")
    op.create_index(op.f("ix_leads_email"), "leads", ["email"], unique=True)

    op.drop_index("ix_buyers_industry", table_name="buyers")
    op.drop_index("ix_buyers_domain", table_name="buyers")
    op.drop_index("ix_buyers_name", table_name="buyers")
    op.drop_table("buyers")
