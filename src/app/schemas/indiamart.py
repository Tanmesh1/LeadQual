import hashlib
import math
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def build_lead_fingerprint(values: dict[str, Any]) -> str:
    parts = [
        values.get("external_lead_id"),
        values.get("product_name"),
        values.get("buyer_name"),
        values.get("business_name"),
        values.get("city"),
        values.get("state"),
    ]
    fingerprint_source = "|".join(str(part or "").strip().lower() for part in parts)
    return hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()


class IndiaMartLeadSortField(str):
    EXTRACTED_AT = "extracted_at"
    PRODUCT_NAME = "product_name"
    BUYER_NAME = "buyer_name"
    BUSINESS_NAME = "business_name"
    CITY = "city"


class IndiaMartLeadBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    lead_fingerprint: str | None = Field(default=None, min_length=16, max_length=64)
    external_lead_id: str | None = Field(default=None, max_length=255)
    product_name: str | None = Field(default=None, max_length=255)
    product_category: str | None = Field(default=None, max_length=255)
    quantity: str | None = Field(default=None, max_length=255)
    order_value: str | None = Field(default=None, max_length=255)
    purpose: str | None = Field(default=None, max_length=255)
    lead_time: str | None = Field(default=None, max_length=255)
    buyer_name: str | None = Field(default=None, max_length=255)
    business_name: str | None = Field(default=None, max_length=255)
    phone_available: bool = False
    email_available: bool = False
    whatsapp_available: bool = False
    business_available: bool = False
    address_available: bool = False
    years_active: int | None = Field(default=None, ge=0)
    requirements_count: int | None = Field(default=None, ge=0)
    replies_count: int | None = Field(default=None, ge=0)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    source_url: str | None = Field(default=None, max_length=1000)
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("lead_fingerprint")
    @classmethod
    def normalize_fingerprint(cls, value: str | None) -> str | None:
        return value.lower() if value else value

    @model_validator(mode="after")
    def populate_fingerprint(self) -> "IndiaMartLeadBase":
        if not self.lead_fingerprint:
            values = self.model_dump(mode="python")
            self.lead_fingerprint = build_lead_fingerprint(values)
        return self


class IndiaMartLeadCreate(IndiaMartLeadBase):
    pass


class IndiaMartLeadRead(IndiaMartLeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lead_score_value: int | None = Field(default=None, ge=0, le=100)
    lead_score_category: str | None = None
    lead_score_reasons: list[str] = Field(default_factory=list)
    lead_score_explanation: dict[str, Any] = Field(default_factory=dict)
    lead_scored_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class IndiaMartLeadBatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[IndiaMartLeadCreate] = Field(min_length=1, max_length=100)


class IndiaMartLeadBatchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[IndiaMartLeadRead]
    created: int = Field(ge=0)
    updated: int = Field(ge=0)


class IndiaMartLeadDeleteAllResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deleted: int = Field(ge=0)


class IndiaMartLeadFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)
    product_name: str | None = Field(default=None, max_length=255)
    buyer_name: str | None = Field(default=None, max_length=255)
    business_name: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    search: str | None = Field(default=None, min_length=1, max_length=255)
    sort_by: Literal["extracted_at", "product_name", "buyer_name", "business_name", "city"] = (
        "extracted_at"
    )
    sort_order: Literal["asc", "desc"] = "desc"


class IndiaMartLeadListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[IndiaMartLeadRead]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1)
    pages: int = Field(ge=0)

    @classmethod
    def create(
        cls,
        *,
        items: list[IndiaMartLeadRead],
        total: int,
        page: int,
        size: int,
    ) -> "IndiaMartLeadListResponse":
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=math.ceil(total / size) if total else 0,
        )
