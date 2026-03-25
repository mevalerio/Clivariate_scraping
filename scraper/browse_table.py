from __future__ import annotations

import re
import time
from random import uniform
from dataclasses import dataclass, field
from urllib.parse import urljoin

from playwright.sync_api import BrowserContext, Page

from scraper.models import CrawlState, JournalRow


@dataclass
class Selectors:
    row: str = "mat-table mat-row, table tbody tr"
    next_button: str = "button[aria-label*='Next'], .pagination-next button, .mat-paginator-navigation-next"
    loading_spinner: str = ".loading, .spinner, .mat-progress-spinner"
    title_cell_link: str = "a, td a, mat-cell a"
    cookie_accept_buttons: tuple[str, ...] = field(
        default_factory=lambda: (
            "button:has-text('Accept')",
            "button:has-text('I Agree')",
            "button:has-text('Agree')",
            "button:has-text('Allow all')",
            "#onetrust-accept-btn-handler",
            "button#accept-recommended-btn-handler",
        )
    )


class BrowseTableScraper:
    def __init__(
        self,
        context: BrowserContext,
        start_url: str,
        selectors: Selectors | None = None,
        max_empty_pages: int = 2,
        min_delay_seconds: float = 0.6,
        max_delay_seconds: float = 1.8,
    ):
        self.context = context
        self.page = context.new_page()
        self.start_url = start_url
        self.selectors = selectors or Selectors()
        self.max_empty_pages = max_empty_pages
        self.min_delay_seconds = min_delay_seconds
        self.max_delay_seconds = max_delay_seconds

    def open(self) -> None:
        self.page.goto(self.start_url, wait_until="domcontentloaded")
        self.page.wait_for_timeout(1500)
        self._dismiss_cookie_banner()

    def collect_table_rows(
        self,
        state: CrawlState,
        max_table_pages: int | None = None,
        enqueue_detail_urls: bool = True,
    ) -> list[JournalRow]:
        self.open()
        new_rows: list[JournalRow] = []
        empty_streak = 0
        current_page = 1

        while True:
            self._wait_table_ready()
            rows = self.page.locator(self.selectors.row)
            row_count = rows.count()

            if row_count == 0:
                empty_streak += 1
                if empty_streak > self.max_empty_pages:
                    break
                self.page.reload(wait_until="domcontentloaded")
                self._dismiss_cookie_banner()
                continue

            empty_streak = 0
            for i in range(row_count):
                parsed = self._parse_row(rows.nth(i), current_page)
                if not parsed:
                    continue
                if parsed.key in state.seen_keys:
                    continue
                state.seen_keys.add(parsed.key)
                if enqueue_detail_urls:
                    state.pending_detail_urls.append(parsed.detail_url)
                new_rows.append(parsed)

            if max_table_pages is not None and current_page >= max_table_pages:
                break

            if not self._go_to_next_page():
                break

            current_page += 1
            state.next_table_page = current_page

        return new_rows

    def scrape_journal_details(
        self,
        state: CrawlState,
        max_retries: int = 3,
        max_detail_urls: int | None = None,
    ) -> list[dict[str, str]]:
        details: list[dict[str, str]] = []
        processed = 0

        while state.pending_detail_urls:
            if max_detail_urls is not None and processed >= max_detail_urls:
                break
            url = state.pending_detail_urls.pop(0)
            if url in state.completed_detail_urls:
                continue

            try:
                page = self.context.new_page()
                self._human_delay()
                page.goto(url, wait_until="domcontentloaded", timeout=45_000)
                page.wait_for_timeout(1000)
                detail = self._extract_detail_table(page)
                detail["detail_url"] = url
                details.append(detail)
                state.completed_detail_urls.add(url)
                processed += 1
                page.close()
            except Exception:
                attempts = state.failed_detail_urls.get(url, 0) + 1
                state.failed_detail_urls[url] = attempts
                if attempts < max_retries:
                    state.pending_detail_urls.append(url)
                time.sleep(min(attempts * 1.5, 6.0))

        return details

    def _wait_table_ready(self) -> None:
        self._dismiss_cookie_banner()
        self._human_delay()
        self.page.wait_for_timeout(700)
        spinner = self.page.locator(self.selectors.loading_spinner)
        if spinner.count() > 0:
            self.page.wait_for_timeout(1500)

    def _parse_row(self, row_locator, page_number: int) -> JournalRow | None:
        link = row_locator.locator(self.selectors.title_cell_link).first
        if link.count() == 0:
            return None

        title = link.inner_text().strip()
        href = link.get_attribute("href")
        detail_url = urljoin(self.page.url, href or "")
        if not detail_url:
            return None

        cells = [c.strip() for c in row_locator.locator("td, mat-cell, .mat-mdc-cell").all_inner_texts()]
        if not cells:
            text = row_locator.inner_text().strip()
            if text:
                cells = [part.strip() for part in text.split("\n") if part.strip()]
        issn = self._extract_issn(cells)
        key = issn or self._normalize_key(title)
        return JournalRow(
            key=key,
            title=title,
            detail_url=detail_url,
            issn=issn,
            table_page=page_number,
            raw={"cells": cells},
        )

    def _go_to_next_page(self) -> bool:
        next_btn = self.page.locator(self.selectors.next_button).first
        if next_btn.count() == 0:
            return False

        disabled = next_btn.get_attribute("disabled") is not None
        aria_disabled = (next_btn.get_attribute("aria-disabled") or "").lower() == "true"
        if disabled or aria_disabled:
            return False

        before = self.page.locator(self.selectors.row).first.inner_text() if self.page.locator(self.selectors.row).count() else ""
        self._human_delay()
        next_btn.click()
        self.page.wait_for_timeout(1200)
        self.page.wait_for_load_state("domcontentloaded")

        for _ in range(8):
            now = self.page.locator(self.selectors.row).first.inner_text() if self.page.locator(self.selectors.row).count() else ""
            if now and now != before:
                return True
            self.page.wait_for_timeout(300)
        return True

    @staticmethod
    def _normalize_key(title: str) -> str:
        return re.sub(r"\W+", "_", title.lower()).strip("_")

    @staticmethod
    def _extract_issn(cells: list[str]) -> str | None:
        for cell in cells:
            match = re.search(r"\b\d{4}-\d{3}[\dXx]\b", cell)
            if match:
                return match.group(0).upper()
        return None

    @staticmethod
    def _extract_detail_table(page: Page) -> dict[str, str]:
        data: dict[str, str] = {}
        h1 = page.locator("h1")
        if h1.count() > 0:
            data["detail_title"] = h1.first.inner_text().strip()

        rows = page.locator("table tr")
        for i in range(min(rows.count(), 120)):
            th = rows.nth(i).locator("th,td").first
            td = rows.nth(i).locator("td").last
            if th.count() == 0 or td.count() == 0:
                continue
            key = th.inner_text().strip().strip(":").lower().replace(" ", "_")
            value = td.inner_text().strip()
            if key and value:
                data[key] = value
        return data

    def _human_delay(self) -> None:
        minimum = max(0.0, self.min_delay_seconds)
        maximum = max(minimum, self.max_delay_seconds)
        time.sleep(uniform(minimum, maximum))

    def _dismiss_cookie_banner(self) -> bool:
        for selector in self.selectors.cookie_accept_buttons:
            button = self.page.locator(selector).first
            if button.count() == 0:
                continue
            try:
                if button.is_visible():
                    button.click(timeout=2_000)
                    self.page.wait_for_timeout(500)
                    return True
            except Exception:
                continue
        return False
