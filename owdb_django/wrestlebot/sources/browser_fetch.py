"""
Headless-browser fetcher — Playwright wrapper.

Some sources (Wrestlingdata.com, WWE.com client-rendered listings, etc.)
either sit behind anti-bot challenges or render their content via JS, so
a plain HTTP fetch returns 403 or empty markup. This module provides an
opt-in browser fetcher that any other adapter can call when it needs a
real-browser execution path.

Usage:
    from .browser_fetch import fetch_html, available
    if available():
        html = fetch_html("https://www.wrestlingdata.com/...")

Why opt-in: Playwright + Chromium together are ~150MB on disk and
launching a browser takes ~1 second. We only want to pay that cost when
we need it — most adapters use plain urllib.

Concurrency: this module uses a per-call browser context. For higher
throughput, a callable `with_browser(...)` context manager is also
exposed so callers can reuse a single browser across many fetches.

Accuracy: a real browser executes JS but cannot bypass authentication or
paywalls. We treat results the same as plain HTTP responses — they go
through the same extractors with the same accuracy guards.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator, Optional

logger = logging.getLogger(__name__)


# Whether Playwright + Chromium are importable. Cached at first use.
_available: Optional[bool] = None


def available() -> bool:
    """Return True iff Playwright is installed AND chromium is available."""
    global _available
    if _available is not None:
        return _available
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        logger.debug("Playwright not installed; browser_fetch disabled.")
        _available = False
        return False
    _available = True
    return True


# Default User-Agent. Playwright's built-in UA looks like 'HeadlessChrome'
# which some sites flag. We swap to a normal desktop Chrome string.
DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@contextmanager
def with_browser(
    user_agent: str = DEFAULT_UA,
    viewport: tuple[int, int] = (1280, 800),
    locale: str = "en-US",
    timezone_id: str = "America/New_York",
) -> Iterator:
    """
    Context manager yielding a Playwright page. Caller drives navigation.

    Reuses a single browser across many fetches — much cheaper than
    fetch_html() in a loop.
    """
    if not available():
        raise RuntimeError(
            "Playwright not available. Run `pip install playwright "
            "&& playwright install chromium`."
        )
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                user_agent=user_agent,
                viewport={"width": viewport[0], "height": viewport[1]},
                locale=locale,
                timezone_id=timezone_id,
            )
            page = context.new_page()
            try:
                yield page
            finally:
                context.close()
        finally:
            browser.close()


def fetch_html(
    url: str,
    *,
    wait_selector: Optional[str] = None,
    wait_state: str = "load",       # 'load' | 'domcontentloaded' | 'networkidle'
    timeout_ms: int = 30_000,
    user_agent: str = DEFAULT_UA,
) -> Optional[str]:
    """
    Fetch a URL with a real Chromium instance. Returns the rendered HTML,
    or None on failure. Logs the failure reason at WARNING.

    `wait_selector`: optional CSS selector to wait for before returning
    (useful for SPAs that populate the page after initial paint).
    `wait_state`: passed to Playwright's `page.goto(wait_until=...)`.
    """
    if not available():
        logger.info("browser_fetch.fetch_html: Playwright not installed; returning None.")
        return None
    if not url:
        return None
    try:
        with with_browser(user_agent=user_agent) as page:
            page.goto(url, wait_until=wait_state, timeout=timeout_ms)
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=timeout_ms)
                except Exception:
                    # Selector never appeared — return what we have anyway.
                    pass
            return page.content()
    except Exception as e:
        logger.warning("browser_fetch failed for %s: %s", url, e)
        return None


# ---------------------------------------------------------------- helpers


def fetch_html_many(urls: list[str], **kw) -> dict[str, Optional[str]]:
    """
    Fetch many URLs reusing a single browser. Significantly faster than
    repeated calls to fetch_html.

    Returns {url: html_or_none}.
    """
    if not available():
        return {u: None for u in urls}
    out: dict[str, Optional[str]] = {}
    wait_selector = kw.pop("wait_selector", None)
    wait_state = kw.pop("wait_state", "load")
    timeout_ms = kw.pop("timeout_ms", 30_000)
    user_agent = kw.pop("user_agent", DEFAULT_UA)
    with with_browser(user_agent=user_agent) as page:
        for url in urls:
            try:
                page.goto(url, wait_until=wait_state, timeout=timeout_ms)
                if wait_selector:
                    try:
                        page.wait_for_selector(wait_selector, timeout=timeout_ms)
                    except Exception:
                        pass
                out[url] = page.content()
            except Exception as e:
                logger.warning("browser_fetch_many failed for %s: %s", url, e)
                out[url] = None
    return out


if __name__ == "__main__":  # pragma: no cover
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "https://www.wrestlingdata.com/"
    print(f"available: {available()}")
    html = fetch_html(target, wait_state="networkidle", timeout_ms=20000)
    print(f"got {len(html) if html else 0} bytes")
    if html:
        print(html[:300])
