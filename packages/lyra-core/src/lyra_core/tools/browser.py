"""Wave-D Task 9: ``browser`` tool.

Wraps Playwright when it is installed; degrades gracefully when it
isn't. The contract is intentionally narrow: the LLM never drives a
full browser DOM, it only asks "open this URL and tell me the
title + text content". Page interactions (click, fill, screenshot)
land in Wave-E once the safety story for in-page JS is settled.

Why a thin wrapper?

* **Optional dependency.** ``playwright`` is a multi-hundred-MB
  install with a separate ``playwright install`` step. Most Lyra
  users won't need it — gating it behind ``lyra[browser]`` keeps
  the base install lean.
* **One-line remediation.** When Playwright is missing the tool
  returns a *typed* :class:`BrowserPage` with the install command
  in ``text`` so the agent can self-correct ("install ``lyra[browser]``
  and try again") instead of hard-failing.
* **Scheme allow-list.** ``javascript:``, ``data:``, ``vbscript:``,
  etc. are rejected up front. Only ``http``, ``https``, and
  ``file`` are honoured.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


BrowserStatus = Literal["ok", "rejected", "unavailable", "error"]


_ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https", "file"})


@dataclass
class BrowserPage:
    """One snapshot of a navigated page (or its failure mode)."""

    url: str
    status: BrowserStatus
    title: str = ""
    text: str = ""
    html: str = ""


def ensure_playwright() -> bool:
    """Return ``True`` when ``playwright.sync_api`` is importable."""
    try:
        import playwright.sync_api  # noqa: F401
    except Exception:
        return False
    return True


def _scheme_of(url: str) -> str:
    if "://" not in url:
        return ""
    return url.split("://", 1)[0].lower()


def browser_open(url: str, *, timeout_ms: int = 15_000) -> BrowserPage:
    """Open ``url`` and return a :class:`BrowserPage` snapshot.

    Behaviour matrix:

    * Disallowed scheme → ``status="rejected"`` (no network).
    * Playwright unavailable → ``status="unavailable"`` with the
      install command in ``text``.
    * Playwright available but navigation fails → ``status="error"``
      with the exception message in ``text``.
    * Happy path → ``status="ok"`` with title / text / html populated.
    """
    scheme = _scheme_of(url)
    if scheme not in _ALLOWED_SCHEMES:
        return BrowserPage(
            url=url,
            status="rejected",
            text=(
                f"rejected: scheme {scheme!r} not in allow-list "
                f"{sorted(_ALLOWED_SCHEMES)!r}"
            ),
        )

    if not ensure_playwright():
        return BrowserPage(
            url=url,
            status="unavailable",
            text=(
                "browser tool unavailable: playwright is not installed.\n"
                "Run `pip install lyra[browser]` and then "
                "`playwright install chromium` to enable it."
            ),
        )

    # Lazy import — keeps headless test envs (and the base install)
    # free of the heavyweight playwright stack.
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - defensive
        return BrowserPage(
            url=url,
            status="error",
            text=f"playwright import failed: {exc}",
        )

    try:  # pragma: no cover - exercised under integration only
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                ctx = browser.new_context()
                page = ctx.new_page()
                page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                title = page.title() or ""
                html = page.content() or ""
                text = page.evaluate("() => document.body && document.body.innerText || ''") or ""
                return BrowserPage(
                    url=url, status="ok", title=title, text=text, html=html
                )
            finally:
                browser.close()
    except Exception as exc:  # pragma: no cover - exercised under integration only
        return BrowserPage(
            url=url,
            status="error",
            text=f"browser navigation failed: {type(exc).__name__}: {exc}",
        )


__all__ = [
    "BrowserPage",
    "BrowserStatus",
    "browser_open",
    "ensure_playwright",
]
