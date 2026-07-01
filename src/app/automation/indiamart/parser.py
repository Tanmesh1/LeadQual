import re
from typing import Any


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def parse_int(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"\d+", value.replace(",", ""))
    return int(match.group(0)) if match else None


def truthy_presence(value: str | None) -> bool:
    if not value:
        return False
    normalized = value.lower()
    unavailable_tokens = ("not available", "unavailable", "hidden", "no ")
    if any(token in normalized for token in unavailable_tokens):
        return False
    return True


def compact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value not in (None, "", [], {})}
