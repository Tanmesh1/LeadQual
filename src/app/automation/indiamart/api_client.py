import logging
from typing import Any

import httpx

from app.automation.indiamart.retry import retry_async

logger = logging.getLogger(__name__)


class IndiaMartLeadApiClient:
    def __init__(
        self,
        *,
        base_url: str,
        attempts: int,
        backoff_seconds: float,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.attempts = attempts
        self.backoff_seconds = backoff_seconds
        self.timeout_seconds = timeout_seconds

    async def ensure_available(self) -> None:
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
            ) as client:
                response = await client.get("/health")
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()
            raise RuntimeError(
                f"IndiaMART API at {self.base_url} returned "
                f"{exc.response.status_code} from /health. "
                f"Response: {detail or '<empty response>'}"
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"IndiaMART API is not reachable at {self.base_url}. "
                "Start the FastAPI server before running extraction."
            ) from exc

    async def post_batch(self, leads: list[dict[str, Any]]) -> dict[str, Any]:
        if not leads:
            return {"items": [], "created": 0, "updated": 0}

        async def operation() -> dict[str, Any]:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
            ) as client:
                response = await client.post("/indiamart/leads/batch", json={"items": leads})
                response.raise_for_status()
                body = response.json()
                logger.info(
                    "posted indiamart leads batch",
                    extra={
                        "count": len(leads),
                        "created_count": body.get("created"),
                        "updated_count": body.get("updated"),
                    },
                )
                return body

        return await retry_async(
            operation,
            attempts=self.attempts,
            backoff_seconds=self.backoff_seconds,
            retry_exceptions=(httpx.HTTPError,),
        )
