import math
import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LeadStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"
    CONVERTED = "converted"
    ARCHIVED = "archived"


class LeadSortField(StrEnum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    EMAIL = "email"
    COMPANY_NAME = "company_name"
    STATUS = "status"
    SOURCE = "source"


class LeadBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    buyer_id: uuid.UUID
    email: str = Field(min_length=3, max_length=320)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    job_title: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    linkedin_url: str | None = Field(default=None, max_length=500)
    source: str | None = Field(default=None, max_length=100)
    status: LeadStatus = LeadStatus.NEW
    company_name: str | None = Field(default=None, max_length=255)
    company_domain: str | None = Field(default=None, max_length=255)
    company_website_url: str | None = Field(default=None, max_length=500)
    company_industry: str | None = Field(default=None, max_length=150)
    company_employee_count: int | None = Field(default=None, ge=0)
    company_annual_revenue_usd: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=18,
        decimal_places=2,
    )
    country: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    timezone: str | None = Field(default=None, max_length=100)
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("email must be a valid email address")
        return value.lower()


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    buyer_id: uuid.UUID | None = None
    email: str | None = Field(default=None, min_length=3, max_length=320)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    job_title: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    linkedin_url: str | None = Field(default=None, max_length=500)
    source: str | None = Field(default=None, max_length=100)
    status: LeadStatus | None = None
    company_name: str | None = Field(default=None, max_length=255)
    company_domain: str | None = Field(default=None, max_length=255)
    company_website_url: str | None = Field(default=None, max_length=500)
    company_industry: str | None = Field(default=None, max_length=150)
    company_employee_count: int | None = Field(default=None, ge=0)
    company_annual_revenue_usd: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=18,
        decimal_places=2,
    )
    country: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    timezone: str | None = Field(default=None, max_length=100)
    raw_payload: dict[str, Any] | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("email must be a valid email address")
        return value.lower()


class LeadRead(LeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class LeadListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[LeadRead]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1)
    pages: int = Field(ge=0)

    @classmethod
    def create(
        cls,
        *,
        items: list[LeadRead],
        total: int,
        page: int,
        size: int,
    ) -> "LeadListResponse":
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=math.ceil(total / size) if total else 0,
        )


class LeadFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    buyer_id: uuid.UUID | None = None
    status: LeadStatus | None = None
    source: str | None = Field(default=None, max_length=100)
    company_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    search: str | None = Field(default=None, min_length=1, max_length=255)
    sort_by: LeadSortField = LeadSortField.CREATED_AT
    sort_order: Literal["asc", "desc"] = "desc"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.lower() if value else value
