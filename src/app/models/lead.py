import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Buyer(Base):
    __tablename__ = "buyers"
    __table_args__ = (
        CheckConstraint(
            "employee_count_min IS NULL OR employee_count_min >= 0",
            name="ck_buyers_employee_count_min_non_negative",
        ),
        CheckConstraint(
            "employee_count_max IS NULL OR employee_count_max >= employee_count_min",
            name="ck_buyers_employee_count_range",
        ),
        CheckConstraint(
            "annual_revenue_usd IS NULL OR annual_revenue_usd >= 0",
            name="ck_buyers_annual_revenue_non_negative",
        ),
        Index("ix_buyers_name", "name"),
        Index("ix_buyers_domain", "domain", unique=True),
        Index("ix_buyers_industry", "industry"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255))
    website_url: Mapped[str | None] = mapped_column(String(500))
    industry: Mapped[str | None] = mapped_column(String(150))
    employee_count_min: Mapped[int | None] = mapped_column(Integer)
    employee_count_max: Mapped[int | None] = mapped_column(Integer)
    annual_revenue_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    target_markets: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    ideal_customer_profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    leads: Mapped[list["Lead"]] = relationship(back_populates="buyer")


class Lead(Base):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'contacted', 'qualified', 'disqualified', 'converted', "
            "'archived')",
            name="ck_leads_status",
        ),
        CheckConstraint(
            "company_employee_count IS NULL OR company_employee_count >= 0",
            name="ck_leads_company_employee_count_non_negative",
        ),
        CheckConstraint(
            "company_annual_revenue_usd IS NULL OR company_annual_revenue_usd >= 0",
            name="ck_leads_company_annual_revenue_non_negative",
        ),
        UniqueConstraint("buyer_id", "email", name="uq_leads_buyer_email"),
        Index("ix_leads_buyer_id", "buyer_id"),
        Index("ix_leads_email", "email"),
        Index("ix_leads_company_name", "company_name"),
        Index("ix_leads_status", "status"),
        Index("ix_leads_source", "source"),
        Index("ix_leads_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("buyers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    job_title: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    source: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new")
    company_name: Mapped[str | None] = mapped_column(String(255))
    company_domain: Mapped[str | None] = mapped_column(String(255))
    company_website_url: Mapped[str | None] = mapped_column(String(500))
    company_industry: Mapped[str | None] = mapped_column(String(150))
    company_employee_count: Mapped[int | None] = mapped_column(Integer)
    company_annual_revenue_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    country: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    timezone: Mapped[str | None] = mapped_column(String(100))
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    buyer: Mapped[Buyer] = relationship(back_populates="leads")
    scores: Mapped[list["LeadScore"]] = relationship(back_populates="lead")
    activity_logs: Mapped[list["LeadActivityLog"]] = relationship(back_populates="lead")
    outcomes: Mapped[list["LeadOutcome"]] = relationship(back_populates="lead")


class LeadScore(Base):
    __tablename__ = "lead_scores"
    __table_args__ = (
        CheckConstraint(
            "score_value >= 0 AND score_value <= 100",
            name="ck_lead_scores_score_value_range",
        ),
        CheckConstraint(
            "score_band IS NULL OR score_band IN ('cold', 'warm', 'hot', 'qualified')",
            name="ck_lead_scores_score_band",
        ),
        Index("ix_lead_scores_lead_id", "lead_id"),
        Index("ix_lead_scores_scored_at", "scored_at"),
        Index("ix_lead_scores_model", "model_name", "model_version"),
        Index("ix_lead_scores_lead_scored_at", "lead_id", "scored_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )
    score_value: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    score_band: Mapped[str | None] = mapped_column(String(50))
    scoring_method: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(150))
    model_version: Mapped[str | None] = mapped_column(String(100))
    feature_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    explanation: Mapped[str | None] = mapped_column(Text)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    lead: Mapped[Lead] = relationship(back_populates="scores")


class LeadActivityLog(Base):
    __tablename__ = "lead_activity_logs"
    __table_args__ = (
        CheckConstraint(
            "actor_type IN ('system', 'user', 'lead', 'buyer', 'integration')",
            name="ck_lead_activity_logs_actor_type",
        ),
        CheckConstraint(
            "channel IS NULL OR channel IN ('email', 'phone', 'sms', 'web', 'chat', 'crm', "
            "'social', 'event', 'other')",
            name="ck_lead_activity_logs_channel",
        ),
        Index("ix_lead_activity_logs_lead_id", "lead_id"),
        Index("ix_lead_activity_logs_activity_type", "activity_type"),
        Index("ix_lead_activity_logs_channel", "channel"),
        Index("ix_lead_activity_logs_occurred_at", "occurred_at"),
        Index("ix_lead_activity_logs_lead_occurred_at", "lead_id", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(255))
    channel: Mapped[str | None] = mapped_column(String(50))
    subject: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    external_id: Mapped[str | None] = mapped_column(String(255))
    activity_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    lead: Mapped[Lead] = relationship(back_populates="activity_logs")


class LeadOutcome(Base):
    __tablename__ = "lead_outcomes"
    __table_args__ = (
        CheckConstraint(
            "outcome_type IN ('qualified', 'disqualified', 'converted', 'lost', 'nurture', "
            "'duplicate', 'invalid')",
            name="ck_lead_outcomes_outcome_type",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_lead_outcomes_confidence_range",
        ),
        CheckConstraint(
            "deal_value_usd IS NULL OR deal_value_usd >= 0",
            name="ck_lead_outcomes_deal_value_non_negative",
        ),
        Index("ix_lead_outcomes_lead_id", "lead_id"),
        Index("ix_lead_outcomes_outcome_type", "outcome_type"),
        Index("ix_lead_outcomes_closed_at", "closed_at"),
        Index("ix_lead_outcomes_label_source", "label_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
    )
    outcome_type: Mapped[str] = mapped_column(String(50), nullable=False)
    outcome_reason: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    deal_value_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    label_source: Mapped[str | None] = mapped_column(String(100))
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    outcome_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    lead: Mapped[Lead] = relationship(back_populates="outcomes")


class IndiaMartLead(Base):
    __tablename__ = "indiamart_leads"
    __table_args__ = (
        CheckConstraint(
            "years_active IS NULL OR years_active >= 0",
            name="ck_indiamart_leads_years_active_non_negative",
        ),
        CheckConstraint(
            "requirements_count IS NULL OR requirements_count >= 0",
            name="ck_indiamart_leads_requirements_count_non_negative",
        ),
        CheckConstraint(
            "replies_count IS NULL OR replies_count >= 0",
            name="ck_indiamart_leads_replies_count_non_negative",
        ),
        CheckConstraint(
            "lead_score_value IS NULL OR (lead_score_value >= 0 AND lead_score_value <= 100)",
            name="ck_indiamart_leads_lead_score_value_range",
        ),
        CheckConstraint(
            "lead_score_category IS NULL OR lead_score_category IN ('HOT', 'WARM', 'COLD')",
            name="ck_indiamart_leads_lead_score_category",
        ),
        UniqueConstraint("lead_fingerprint", name="uq_indiamart_leads_fingerprint"),
        Index("ix_indiamart_leads_product_name", "product_name"),
        Index("ix_indiamart_leads_product_category", "product_category"),
        Index("ix_indiamart_leads_buyer_name", "buyer_name"),
        Index("ix_indiamart_leads_business_name", "business_name"),
        Index("ix_indiamart_leads_city_state", "city", "state"),
        Index("ix_indiamart_leads_extracted_at", "extracted_at"),
        Index("ix_indiamart_leads_lead_score_category", "lead_score_category"),
        Index("ix_indiamart_leads_lead_scored_at", "lead_scored_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    lead_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    external_lead_id: Mapped[str | None] = mapped_column(String(255))
    product_name: Mapped[str | None] = mapped_column(String(255))
    product_category: Mapped[str | None] = mapped_column(String(255))
    quantity: Mapped[str | None] = mapped_column(String(255))
    order_value: Mapped[str | None] = mapped_column(String(255))
    purpose: Mapped[str | None] = mapped_column(String(255))
    lead_time: Mapped[str | None] = mapped_column(String(255))
    buyer_name: Mapped[str | None] = mapped_column(String(255))
    business_name: Mapped[str | None] = mapped_column(String(255))
    phone_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    whatsapp_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    business_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    address_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    years_active: Mapped[int | None] = mapped_column(Integer)
    requirements_count: Mapped[int | None] = mapped_column(Integer)
    replies_count: Mapped[int | None] = mapped_column(Integer)
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    lead_score_value: Mapped[int | None] = mapped_column(Integer)
    lead_score_category: Mapped[str | None] = mapped_column(String(50))
    lead_score_reasons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    lead_score_explanation: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    lead_scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ReportExtractionState(Base):
    __tablename__ = "report_extraction_states"
    __table_args__ = (
        Index("ix_report_extraction_states_report_name", "report_name", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    report_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
