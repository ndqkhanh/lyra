"""Wave-D Task 9: ``browser`` tool — real Playwright with graceful fallback.

Playwright is an *optional* dependency (``lyra[browser]``). When
installed, ``browser_open(url)`` returns a real
:class:`BrowserPage` with the rendered HTML title + a text snapshot.
When not installed, it returns a :class:`BrowserPage` with
``status="unavailable"`` and a clear remediation message — never
raises, never blocks the caller.

Five RED tests:

1. ``ensure_playwright`` reflects whether the package is importable.
2. With Playwright unavailable, ``browser_open`` returns a typed
   ``status="unavailable"`` page.
3. URL validation rejects schemes other than ``http(s)`` /
   ``file:`` *before* attempting any navigation.
4. ``BrowserPage`` carries the pieces ``/web`` will render
   (``url``, ``title``, ``text``, ``html``, ``status``).
5. The fallback path mentions ``pip install lyra[browser]`` so a
   user gets one-line remediation.
"""
from __future__ import annotations

import pytest


def test_ensure_playwright_returns_bool() -> None:
    from lyra_core.tools.browser import ensure_playwright

    out = ensure_playwright()
    assert isinstance(out, bool)


def test_browser_open_unavailable_returns_typed_page(monkeypatch) -> None:
    from lyra_core.tools import browser

    monkeypatch.setattr(browser, "ensure_playwright", lambda: False)
    page = browser.browser_open("https://example.com")
    assert page.status == "unavailable"
    assert page.url == "https://example.com"
    assert "pip install" in page.text.lower()


def test_browser_open_rejects_dangerous_scheme() -> None:
    from lyra_core.tools.browser import BrowserPage, browser_open

    page: BrowserPage = browser_open("javascript:alert(1)")
    assert page.status == "rejected"
    assert "scheme" in page.text.lower() or "rejected" in page.text.lower()


def test_browser_page_shape() -> None:
    from lyra_core.tools.browser import BrowserPage

    page = BrowserPage(
        url="https://example.com",
        status="ok",
        title="Example",
        text="hello",
        html="<html></html>",
    )
    assert page.url and page.title and page.text and page.html


def test_unavailable_message_mentions_install_extra(monkeypatch) -> None:
    from lyra_core.tools import browser

    monkeypatch.setattr(browser, "ensure_playwright", lambda: False)
    page = browser.browser_open("https://example.com")
    assert "lyra[browser]" in page.text
