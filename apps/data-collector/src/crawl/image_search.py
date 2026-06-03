from __future__ import annotations

import time
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright

from src.crawl.extractors import extract_bing_candidates


def _bing_url(query: str) -> str:
    return f"https://www.bing.com/images/search?q={quote_plus(query)}"


def fetch_candidates_html(query: str, user_agent: str, timeout_ms: int = 20000) -> str:
    """Open Bing Images for `query` with Playwright, scroll once, return page HTML."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=user_agent)
        try:
            page.goto(_bing_url(query), timeout=timeout_ms, wait_until="domcontentloaded")
            # Bing lazy-loads thumbnails; scroll to trigger a batch.
            for _ in range(3):
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(800)
            return page.content()
        finally:
            browser.close()


def search_query(query: str, user_agent: str, limit: int) -> list[dict]:
    """Return up to `limit` candidate dicts for a single query. Never raises."""
    try:
        html = fetch_candidates_html(query, user_agent)
    except Exception as exc:  # noqa: BLE001 - we log and continue on any crawl failure
        print(f"[crawl] FAILED query={query!r}: {exc}")
        return []
    candidates = extract_bing_candidates(html)
    return candidates[:limit]


def polite_sleep(seconds: float) -> None:
    time.sleep(seconds)
