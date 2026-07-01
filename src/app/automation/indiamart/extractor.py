import logging
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from playwright.async_api import BrowserContext, Locator, Page, TimeoutError, async_playwright

from app.automation.indiamart.api_client import IndiaMartLeadApiClient
from app.automation.indiamart.config import load_selectors
from app.automation.indiamart.parser import clean_text, compact_payload, parse_int, truthy_presence
from app.automation.indiamart.retry import retry_async
from app.automation.indiamart.settings import IndiaMartAutomationSettings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


class IndiaMartLeadExtractor:
    def __init__(self, settings: IndiaMartAutomationSettings) -> None:
        self.settings = settings
        self.selectors = load_selectors(settings.indiamart_selectors_path)
        self.api_client = IndiaMartLeadApiClient(
            base_url=settings.indiamart_api_base_url,
            attempts=settings.indiamart_retry_attempts,
            backoff_seconds=settings.indiamart_retry_backoff_seconds,
        )

    async def run(self) -> None:
        configure_logging()
        self.settings.indiamart_session_state_path.parent.mkdir(parents=True, exist_ok=True)
        await self.api_client.ensure_available()

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=self.settings.indiamart_headless,
                slow_mo=self.settings.indiamart_slow_mo_ms,
            )
            context_kwargs: dict[str, Any] = {}
            if self.settings.indiamart_session_state_path.exists():
                context_kwargs["storage_state"] = str(self.settings.indiamart_session_state_path)

            context = await browser.new_context(**context_kwargs)
            context.set_default_timeout(self.settings.indiamart_timeout_ms)

            try:
                page = await context.new_page()
                await self._ensure_logged_in(page, context)
                await self._extract_paginated(page)
            finally:
                await context.close()
                await browser.close()

    async def _ensure_logged_in(self, page: Page, context: BrowserContext) -> None:
        await page.goto(self.selectors.buy_leads_url, wait_until="domcontentloaded")
        if await self._is_authenticated_buy_leads_page(page, timeout_ms=5_000):
            logger.info("using existing IndiaMART session")
            return

        logger.info("IndiaMART session unavailable; starting login")
        await page.goto(self.selectors.login_url, wait_until="domcontentloaded")

        mobile_number = self.settings.indiamart_mobile_number or self.settings.indiamart_username
        if mobile_number:
            if await self._try_fill_first(page, self.selectors.username_input, mobile_number):
                await self._try_click_first(page, self.selectors.submit_button)
            else:
                logger.warning("unable to auto-fill IndiaMART mobile input; waiting for manual login")

        timeout_ms = self.settings.indiamart_manual_login_timeout_seconds * 1_000
        if not await self._wait_for_login_complete(page, timeout_ms=timeout_ms):
            logger.error(
                "IndiaMART manual login timed out",
                extra={"current_url": page.url},
            )
            raise RuntimeError(
                "IndiaMART login did not complete. Run headed mode and complete mobile OTP login."
            )

        await context.storage_state(path=str(self.settings.indiamart_session_state_path))
        logger.info("saved IndiaMART storage state")

    async def _is_authenticated_buy_leads_page(self, page: Page, *, timeout_ms: int) -> bool:
        if await self._any_visible(page, self.selectors.logged_out_marker, timeout_ms=1_000):
            return False
        if await self._any_visible(page, self.selectors.lead_card, timeout_ms=timeout_ms):
            return True
        if self._is_buy_leads_url(page.url):
            return True
        return await self._any_visible(
            page,
            self.selectors.logged_in_marker,
            timeout_ms=timeout_ms,
        )

    def _is_buy_leads_url(self, url: str) -> bool:
        return "/bltxn/" in url or url.rstrip("/").endswith("/bltxn")

    async def _wait_for_login_complete(self, page: Page, *, timeout_ms: int) -> bool:
        deadline = time.monotonic() + (timeout_ms / 1_000)
        last_logged_remaining: int | None = None
        logger.info(
            "waiting for IndiaMART manual login",
            extra={"timeout_seconds": timeout_ms // 1_000},
        )
        while time.monotonic() < deadline:
            await page.wait_for_load_state("domcontentloaded")
            if await self._is_authenticated_buy_leads_page(page, timeout_ms=1_000):
                logger.info("IndiaMART manual login completed", extra={"current_url": page.url})
                return True

            remaining_seconds = int(deadline - time.monotonic())
            if (
                last_logged_remaining is None
                or remaining_seconds <= 10
                or remaining_seconds // 15 != last_logged_remaining // 15
            ):
                logger.info(
                    "still waiting for IndiaMART manual login",
                    extra={"remaining_seconds": max(remaining_seconds, 0), "current_url": page.url},
                )
                last_logged_remaining = remaining_seconds
            await page.wait_for_timeout(1_000)
        return False

    async def _extract_paginated(self, page: Page) -> None:
        await page.goto(self.selectors.buy_leads_url, wait_until="domcontentloaded")
        total_extracted = 0

        for page_number in range(1, self.settings.indiamart_max_pages + 1):
            logger.info("extracting IndiaMART buy leads page", extra={"page": page_number})
            page_leads = await self._extract_current_page(page)
            total_extracted += len(page_leads)
            await self._post_in_batches(page_leads)

            if page_number >= self.settings.indiamart_max_pages:
                break
            if not await self._go_next_page(page):
                break

        logger.info("IndiaMART extraction completed", extra={"total_extracted": total_extracted})

    async def _extract_current_page(self, page: Page) -> list[dict[str, Any]]:
        wait_ms = self.settings.indiamart_lead_list_wait_seconds * 1_000
        lead_card = await self._wait_for_first_locator(
            page,
            self.selectors.lead_card,
            timeout_ms=wait_ms,
        )
        if lead_card is None:
            await self._save_diagnostics(page, reason="no-lead-cards")
            logger.warning(
                "no IndiaMART lead cards found",
                extra={
                    "current_url": page.url,
                    "wait_seconds": self.settings.indiamart_lead_list_wait_seconds,
                    "selectors": self.selectors.lead_card,
                },
            )
            return []

        count = await lead_card.count()
        leads: list[dict[str, Any]] = []
        for index in range(count):
            card = lead_card.nth(index)

            async def operation(current_card: Locator = card) -> dict[str, Any]:
                return await self._extract_card(page, current_card)

            try:
                lead = await retry_async(
                    operation,
                    attempts=self.settings.indiamart_retry_attempts,
                    backoff_seconds=self.settings.indiamart_retry_backoff_seconds,
                    retry_exceptions=(TimeoutError, RuntimeError),
                )
            except Exception:
                logger.exception("failed to extract IndiaMART lead card", extra={"index": index})
                continue

            leads.append(lead)

        return leads

    async def _extract_card(self, page: Page, card: Locator) -> dict[str, Any]:
        root: Page | Locator = card
        if self.settings.indiamart_open_lead_details and self.selectors.lead_detail_click:
            detail_target = await self._first_locator(card, self.selectors.lead_detail_click)
            if detail_target is not None and await detail_target.count():
                await detail_target.first.click()
                await page.wait_for_load_state("domcontentloaded")
                root = page

        raw = {
            "external_lead_id": await self._text_from(root, self.selectors.fields.external_lead_id),
            "product_name": await self._text_from(root, self.selectors.fields.product_name),
            "product_category": await self._text_from(root, self.selectors.fields.product_category),
            "quantity": await self._text_from(root, self.selectors.fields.quantity),
            "order_value": await self._text_from(root, self.selectors.fields.order_value),
            "purpose": await self._text_from(root, self.selectors.fields.purpose),
            "lead_time": await self._text_from(root, self.selectors.fields.lead_time),
            "buyer_name": await self._text_from(root, self.selectors.fields.buyer_name),
            "business_name": await self._text_from(root, self.selectors.fields.business_name),
            "years_active": await self._text_from(root, self.selectors.fields.years_active),
            "requirements_count": await self._text_from(
                root,
                self.selectors.fields.requirements_count,
            ),
            "replies_count": await self._text_from(root, self.selectors.fields.replies_count),
            "city": await self._text_from(root, self.selectors.fields.city),
            "state": await self._text_from(root, self.selectors.fields.state),
            "phone_available": await self._text_from(root, self.selectors.fields.phone_available),
            "email_available": await self._text_from(root, self.selectors.fields.email_available),
            "whatsapp_available": await self._text_from(
                root,
                self.selectors.fields.whatsapp_available,
            ),
            "business_available": await self._text_from(
                root,
                self.selectors.fields.business_available,
            ),
            "address_available": await self._text_from(
                root,
                self.selectors.fields.address_available,
            ),
        }

        if self.selectors.detail_close_button:
            close_button = await self._first_locator(page, self.selectors.detail_close_button)
            if close_button is not None and await close_button.count():
                await close_button.first.click()

        return compact_payload(
            {
                "external_lead_id": raw["external_lead_id"],
                "product_name": raw["product_name"],
                "product_category": raw["product_category"],
                "quantity": raw["quantity"],
                "order_value": raw["order_value"],
                "purpose": raw["purpose"],
                "lead_time": raw["lead_time"],
                "buyer_name": raw["buyer_name"],
                "business_name": raw["business_name"],
                "phone_available": truthy_presence(raw["phone_available"]),
                "email_available": truthy_presence(raw["email_available"]),
                "whatsapp_available": truthy_presence(raw["whatsapp_available"]),
                "business_available": truthy_presence(raw["business_available"]),
                "address_available": truthy_presence(raw["address_available"]),
                "years_active": parse_int(raw["years_active"]),
                "requirements_count": parse_int(raw["requirements_count"]),
                "replies_count": parse_int(raw["replies_count"]),
                "city": raw["city"],
                "state": raw["state"],
                "source_url": page.url,
                "raw_payload": compact_payload(raw),
                "extracted_at": datetime.now(UTC).isoformat(),
            }
        )

    async def _post_in_batches(self, leads: list[dict[str, Any]]) -> None:
        for batch in self._chunks(leads, self.settings.indiamart_batch_size):
            await self.api_client.post_batch(list(batch))

    async def _go_next_page(self, page: Page) -> bool:
        if self.selectors.next_page_disabled and await self._any_visible(
            page,
            self.selectors.next_page_disabled,
            timeout_ms=1_000,
        ):
            return False

        next_button = await self._first_locator(page, self.selectors.next_page_button)
        if next_button is None or await next_button.count() == 0:
            return False

        await next_button.first.click()
        await page.wait_for_load_state("domcontentloaded")
        return True

    async def _fill_first(self, root: Page | Locator, selectors: list[str], value: str) -> None:
        locator = await self._first_locator(root, selectors)
        if locator is None:
            raise RuntimeError(f"Unable to find input for selectors: {selectors}")
        await locator.first.fill(value)

    async def _click_first(self, root: Page | Locator, selectors: list[str]) -> None:
        locator = await self._first_locator(root, selectors)
        if locator is None:
            raise RuntimeError(f"Unable to find button for selectors: {selectors}")
        await locator.first.click()

    async def _try_fill_first(self, root: Page | Locator, selectors: list[str], value: str) -> bool:
        locator = await self._first_locator(root, selectors)
        if locator is None:
            return False
        await locator.first.fill(value)
        return True

    async def _try_click_first(self, root: Page | Locator, selectors: list[str]) -> bool:
        locator = await self._first_locator(root, selectors)
        if locator is None:
            return False
        await locator.first.click()
        return True

    async def _text_from(self, root: Page | Locator, selectors: list[str]) -> str | None:
        locator = await self._first_locator(root, selectors)
        if locator is None or await locator.count() == 0:
            return None

        first = locator.first
        text = clean_text(await first.inner_text())
        if text:
            return text

        for attribute in ("data-lead-id", "data-testid", "aria-label", "title"):
            value = clean_text(await first.get_attribute(attribute))
            if value:
                return value

        return None

    async def _wait_for_first_locator(
        self,
        page: Page,
        selectors: list[str],
        *,
        timeout_ms: int,
    ) -> Locator | None:
        deadline = time.monotonic() + (timeout_ms / 1_000)
        while time.monotonic() < deadline:
            locator = await self._first_locator(page, selectors)
            if locator is not None and await locator.count() > 0:
                return locator
            await page.wait_for_timeout(1_000)
        return await self._first_locator(page, selectors)

    async def _save_diagnostics(self, page: Page, *, reason: str) -> None:
        self.settings.indiamart_diagnostics_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        safe_reason = "".join(char if char.isalnum() or char == "-" else "-" for char in reason)
        base_path = self.settings.indiamart_diagnostics_path / f"{timestamp}-{safe_reason}"
        html_path = base_path.with_suffix(".html")
        screenshot_path = base_path.with_suffix(".png")

        html_path.write_text(await page.content(), encoding="utf-8")
        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
        except Exception:
            logger.exception("failed to save IndiaMART diagnostic screenshot")
            screenshot_path = None

        logger.info(
            "saved IndiaMART diagnostics",
            extra={
                "html_path": str(html_path),
                "screenshot_path": str(screenshot_path) if screenshot_path else None,
            },
        )

    async def _first_locator(
        self,
        root: Page | Locator,
        selectors: list[str],
    ) -> Locator | None:
        for selector in selectors:
            locator = root.locator(selector)
            try:
                if await locator.count() > 0:
                    return locator
            except TimeoutError:
                continue
        return None

    async def _any_visible(
        self,
        root: Page | Locator,
        selectors: list[str],
        *,
        timeout_ms: int,
    ) -> bool:
        for selector in selectors:
            try:
                await root.locator(selector).first.wait_for(state="visible", timeout=timeout_ms)
                return True
            except TimeoutError:
                continue
        return False

    @staticmethod
    def _chunks(items: list[dict[str, Any]], size: int) -> Iterable[list[dict[str, Any]]]:
        for index in range(0, len(items), size):
            yield items[index : index + size]


async def run_from_settings(settings_path: Path | None = None) -> None:
    extractor_settings = IndiaMartAutomationSettings()
    if settings_path:
        extractor_settings.indiamart_selectors_path = settings_path

    extractor = IndiaMartLeadExtractor(extractor_settings)
    await extractor.run()
