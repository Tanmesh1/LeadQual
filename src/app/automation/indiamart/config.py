import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FieldSelectors(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_name: list[str] = Field(default_factory=list)
    product_category: list[str] = Field(default_factory=list)
    quantity: list[str] = Field(default_factory=list)
    order_value: list[str] = Field(default_factory=list)
    purpose: list[str] = Field(default_factory=list)
    lead_time: list[str] = Field(default_factory=list)
    buyer_name: list[str] = Field(default_factory=list)
    business_name: list[str] = Field(default_factory=list)
    years_active: list[str] = Field(default_factory=list)
    requirements_count: list[str] = Field(default_factory=list)
    replies_count: list[str] = Field(default_factory=list)
    city: list[str] = Field(default_factory=list)
    state: list[str] = Field(default_factory=list)
    phone_available: list[str] = Field(default_factory=list)
    email_available: list[str] = Field(default_factory=list)
    whatsapp_available: list[str] = Field(default_factory=list)
    business_available: list[str] = Field(default_factory=list)
    address_available: list[str] = Field(default_factory=list)
    external_lead_id: list[str] = Field(default_factory=list)


class BuyLeadsSelectors(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login_url: str
    buy_leads_url: str
    username_input: list[str]
    password_input: list[str]
    submit_button: list[str]
    logged_in_marker: list[str]
    logged_out_marker: list[str] = Field(default_factory=list)
    lead_card: list[str]
    lead_detail_click: list[str] = Field(default_factory=list)
    detail_close_button: list[str] = Field(default_factory=list)
    next_page_button: list[str]
    next_page_disabled: list[str] = Field(default_factory=list)
    fields: FieldSelectors


def load_selectors(path: Path) -> BuyLeadsSelectors:
    with path.open(encoding="utf-8") as file:
        raw: dict[str, Any] = json.load(file)
    return BuyLeadsSelectors.model_validate(raw)
