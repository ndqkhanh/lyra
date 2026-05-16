"""Search tool providers for Lyra deep research engine.

Provider priority (auto-detected at runtime):
  1. Exa          — neural search + full content  (needs EXA_API_KEY)
  2. Firecrawl    — search + JS-rendered scraping (needs FIRECRAWL_API_KEY)
  3. DuckDuckGo   — zero-key fallback             (pip install duckduckgo-search)

All providers implement the same async interface so the pipeline is provider-agnostic.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass


@dataclass
class SearchResult:
    """A single search result with optional scraped full content."""
    title: str
    url: str
    snippet: str
    content: str = ""        # Populated by scrape()
    score: float = 0.0
    published: str = ""
    source_idx: int = 0      # Citation index [N] assigned by pipeline


class SearchError(Exception):
    pass


# ── Provider implementations ───────────────────────────────────────────────

class ExaProvider:
    """Exa neural search — best quality, requires EXA_API_KEY."""

    name = "exa"

    def __init__(self, api_key: str) -> None:
        from exa_py import Exa  # type: ignore[import]
        self._client = Exa(api_key=api_key)

    async def search(self, query: str, num_results: int = 8) -> list[SearchResult]:
        loop = asyncio.get_event_loop()

        def _run() -> list[SearchResult]:
            resp = self._client.search_and_contents(
                query,
                num_results=num_results,
                text={"max_characters": 600},
                highlights={"num_sentences": 3, "highlights_per_url": 1},
            )
            results = []
            for r in resp.results:
                highlights = getattr(r, "highlights", None) or []
                snippet = " ".join(highlights) if highlights else (r.text or "")[:300]
                results.append(SearchResult(
                    title=r.title or "",
                    url=r.url or "",
                    snippet=snippet,
                    content=r.text or "",
                    score=float(getattr(r, "score", 0) or 0),
                    published=str(getattr(r, "published_date", "") or ""),
                ))
            return results

        try:
            return await loop.run_in_executor(None, _run)
        except Exception as e:
            raise SearchError(f"Exa search failed: {e}") from e

    async def scrape(self, url: str, max_chars: int = 5000) -> str:
        loop = asyncio.get_event_loop()

        def _run() -> str:
            resp = self._client.get_contents([url], text={"max_characters": max_chars})
            if resp.results:
                return resp.results[0].text or ""
            return ""

        try:
            return await loop.run_in_executor(None, _run)
        except Exception:
            return ""


class FirecrawlProvider:
    """Firecrawl — search + JavaScript-rendered page scraping."""

    name = "firecrawl"

    def __init__(self, api_key: str) -> None:
        from firecrawl import FirecrawlApp  # type: ignore[import]
        self._client = FirecrawlApp(api_key=api_key)

    async def search(self, query: str, num_results: int = 8) -> list[SearchResult]:
        loop = asyncio.get_event_loop()

        def _run() -> list[SearchResult]:
            resp = self._client.search(
                query,
                limit=num_results,
                scrapeOptions={"formats": ["markdown"]},
            )
            data = resp.data if hasattr(resp, "data") else (resp if isinstance(resp, list) else [])
            results = []
            for r in data:
                meta = getattr(r, "metadata", {}) or {}
                md = getattr(r, "markdown", "") or ""
                results.append(SearchResult(
                    title=meta.get("title", ""),
                    url=meta.get("sourceURL") or meta.get("url", ""),
                    snippet=md[:400],
                    content=md,
                ))
            return results

        try:
            return await loop.run_in_executor(None, _run)
        except Exception as e:
            raise SearchError(f"Firecrawl search failed: {e}") from e

    async def scrape(self, url: str, max_chars: int = 5000) -> str:
        loop = asyncio.get_event_loop()

        def _run() -> str:
            resp = self._client.scrape_url(url, formats=["markdown"])
            return (getattr(resp, "markdown", "") or "")[:max_chars]

        try:
            return await loop.run_in_executor(None, _run)
        except Exception:
            return ""


class DuckDuckGoProvider:
    """DuckDuckGo — zero-key fallback. Best-effort scrape via httpx."""

    name = "duckduckgo"

    async def search(self, query: str, num_results: int = 8) -> list[SearchResult]:
        loop = asyncio.get_event_loop()

        def _run() -> list[SearchResult]:
            try:
                from ddgs import DDGS  # type: ignore[import]  # new package name
            except ImportError:
                from duckduckgo_search import DDGS  # type: ignore[import]  # legacy name
            with DDGS() as ddgs:
                raw = list(ddgs.text(query, max_results=num_results))
            return [
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", ""),
                    content=r.get("body", ""),
                )
                for r in raw
            ]

        try:
            return await loop.run_in_executor(None, _run)
        except Exception as e:
            raise SearchError(f"DuckDuckGo search failed: {e}") from e

    async def scrape(self, url: str, max_chars: int = 5000) -> str:
        try:
            import httpx
            async with httpx.AsyncClient(
                timeout=12, follow_redirects=True
            ) as client:
                resp = await client.get(
                    url, headers={"User-Agent": "Mozilla/5.0 (Lyra-Research-Bot/1.0)"}
                )
                html = resp.text
            # Strip HTML tags and collapse whitespace
            text = re.sub(r"<[^>]+>", " ", html)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:max_chars]
        except Exception:
            return ""


# ── Provider factory ───────────────────────────────────────────────────────

def build_provider(cred_mgr=None) -> "ExaProvider | FirecrawlProvider | DuckDuckGoProvider":
    """Auto-detect the best available search provider.

    Tries in order: Exa → Firecrawl → DuckDuckGo.
    Raises RuntimeError with install instructions if nothing is available.
    """
    import os

    # ── Exa ────────────────────────────────────────────────────────────────
    try:
        import exa_py  # noqa: F401 — just test availability
        key = ""
        if cred_mgr:
            creds = cred_mgr.get_provider("exa") or {}
            key = creds.get("api_key", "")
        key = key or os.environ.get("EXA_API_KEY", "")
        if key:
            return ExaProvider(api_key=key)
    except ImportError:
        pass

    # ── Firecrawl ──────────────────────────────────────────────────────────
    try:
        import firecrawl  # noqa: F401
        key = ""
        if cred_mgr:
            creds = cred_mgr.get_provider("firecrawl") or {}
            key = creds.get("api_key", "")
        key = key or os.environ.get("FIRECRAWL_API_KEY", "")
        if key:
            return FirecrawlProvider(api_key=key)
    except ImportError:
        pass

    # ── DuckDuckGo (zero-key) ──────────────────────────────────────────────
    try:
        # `ddgs` is the current package name; `duckduckgo_search` is the legacy alias.
        # DuckDuckGoProvider._run() tries both at runtime.
        import ddgs  # noqa: F401
        return DuckDuckGoProvider()
    except ImportError:
        pass

    raise RuntimeError(
        "No search provider available.\n"
        "Install one of:\n"
        "  pip install exa-py   # Best quality  (needs EXA_API_KEY)\n"
        "  pip install ddgs     # Zero-key fallback\n"
        "Then set the env var or run: /credentials exa"
    )
