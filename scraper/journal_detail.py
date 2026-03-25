from __future__ import annotations

from urllib.parse import urljoin

from playwright.sync_api import Page


def absolute_url(base_url: str, href: str | None) -> str:
    if not href:
        return ""
    return urljoin(base_url, href)


def extract_detail_data(page: Page) -> dict[str, str]:
    data: dict[str, str] = {}

    title = page.locator("h1").first.inner_text(timeout=2_000) if page.locator("h1").count() else ""
    if title:
        data["detail_title"] = title.strip()

    maybe_pairs = page.locator("dt, th")
    for i in range(min(maybe_pairs.count(), 80)):
        label = maybe_pairs.nth(i).inner_text().strip().strip(":")
        if not label:
            continue
        value_locator = maybe_pairs.nth(i).locator("xpath=following-sibling::*[1]")
        if value_locator.count() == 0:
            continue
        value = value_locator.first.inner_text().strip()
        if value:
            data[label.lower().replace(" ", "_")] = value

    return data
