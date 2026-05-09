"""Real ``WebSearch`` tool — Claude-Code / opencode parity (v1.7.3).

The tool returns a list of ``{title, url, snippet}`` dicts capped at
``max_results`` and forwards the query verbatim to a **provider
callable** so the network boundary stays testable.

The default production provider is a DuckDuckGo-HTML scraper (no key
required). When ``httpx`` isn't installed we lazily import inside the
default provider and raise :class:`FeatureUnavailable` — leaving the
tool usable with any injected provider in tests.
"""
from __future__ import annotations

from typing import Any, Callable

from ..lsp_backend.errors import FeatureUnavailable


def _default_provider() -> Callable[[str, int], list[dict]]:
    """Return a DuckDuckGo HTML provider; raises
    :class:`FeatureUnavailable` if ``httpx`` is missing.
    """
    try:
        import httpx  # type: ignore[import-not-found]
    except Exception as exc:
        raise FeatureUnavailable(
            "WebSearch default provider needs httpx. "
            "Install with `pip install 'lyra[web]'` or pass a custom "
            f"provider to make_web_search_tool(...). (underlying: {exc!r})"
        ) from exc

    try:
        from bs4 import BeautifulSoup  # type: ignore[import-not-found]
    except Exception as exc:
        raise FeatureUnavailable(
            "WebSearch default provider needs beautifulsoup4. "
            "Install with `pip install 'lyra[web]'`."
        ) from exc

    def provider(query: str, max_results: int) -> list[dict]:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "lyra-web-search/1.0"},
            timeout=10.0,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[dict] = []
        for div in soup.select("div.result")[:max_results]:
            a = div.select_one("a.result__a")
            snippet_el = div.select_one("a.result__snippet") or div.select_one(".result__snippet")
            if a is None:
                continue
            results.append(
                {
                    "title": a.get_text(" ", strip=True),
                    "url": a.get("href", ""),
                    "snippet": snippet_el.get_text(" ", strip=True) if snippet_el else "",
                }
            )
        return results

    return provider


def make_web_search_tool(
    *,
    provider: Callable[[str, int], list[dict]] | None = None,
) -> Callable[..., dict]:
    """Build the LLM-callable ``WebSearch`` tool bound to ``provider``."""

    def web_search(*, query: str, max_results: int = 5) -> dict:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if max_results <= 0:
            raise ValueError("max_results must be positive")

        p = provider or _default_provider()
        raw = p(query.strip(), max_results)
        clean = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("snippet", ""),
            }
            for r in raw[:max_results]
        ]
        return {"results": clean, "count": len(clean)}

    web_search.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "WebSearch",
        "description": "Run a web search and return the top results.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    }
    return web_search


__all__ = ["make_web_search_tool"]
