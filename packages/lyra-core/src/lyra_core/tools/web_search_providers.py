"""Provider implementations for the v3.12 multi-backend WebSearch.

Each provider is a callable ``(query, max_results, **opts) -> list[dict]``
returning ``[{title, url, snippet, source?, published?, score?}]``.

The registry is API-key-aware: providers self-report whether they're
configured (``configured() -> bool``) so the fallback chain skips
un-configured ones without raising. This matches Claude Code's posture
— a missing env var is "use a different backend", not "crash".

Wire order is opinionated:

1. **Tavily** — best research-oriented results when keyed
2. **Exa** — neural search; best for semantic / "find pages like" queries
3. **Serper** — Google SERP proxy; best for current-events / news
4. **Brave** — independent index; best privacy fallback for keyed setups
5. **Google CSE** — when the user has their own Custom Search Engine
6. **DuckDuckGo HTML scraper** — always-available no-key fallback

Each provider is a thin HTTP shim — keeping them tiny means a single
file holds all six, and adding a seventh provider tomorrow is just
another dataclass + ``call()`` method.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable, List, Optional

from ..lsp_backend.errors import FeatureUnavailable


_DEFAULT_TIMEOUT = 10.0


@dataclass(frozen=True)
class SearchHit:
    """One normalised search result.

    Providers may have additional fields (score from Exa, published_date
    from Tavily, etc.); the dict round-trip on ``.to_dict()`` preserves
    them so callers downstream can use richer data without us hardcoding
    a fixed schema in the dataclass.
    """

    title: str
    url: str
    snippet: str
    source: str
    extra: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
        }
        out.update(self.extra)
        return out


class _Provider:
    """Provider base — concrete subclasses implement ``call()``.

    ``name`` is the registry key (lowercase, no spaces). ``priority``
    decides default fallback order — lower wins. ``configured()`` is
    queried by the chain to decide whether to call.
    """

    name: str = ""
    priority: int = 100
    needs: tuple[str, ...] = ()  # required env var names

    def configured(self) -> bool:
        return all(os.environ.get(var) for var in self.needs)

    def call(
        self, query: str, max_results: int, *, opts: dict[str, Any]
    ) -> list[SearchHit]:  # pragma: no cover — abstract
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Tavily — research-grade API with quote spans + publication dates
# ---------------------------------------------------------------------------


class TavilyProvider(_Provider):
    name = "tavily"
    priority = 10
    needs = ("TAVILY_API_KEY",)

    def call(self, query, max_results, *, opts):
        import httpx

        body: dict[str, Any] = {
            "api_key": os.environ["TAVILY_API_KEY"],
            "query": query,
            "max_results": max_results,
            "include_answer": False,
        }
        if "domains_allow" in opts:
            body["include_domains"] = list(opts["domains_allow"])
        if "domains_block" in opts:
            body["exclude_domains"] = list(opts["domains_block"])
        if "time_range" in opts:
            # tavily accepts "day", "week", "month", "year"
            body["search_depth"] = "advanced"
            body["time_range"] = opts["time_range"]
        resp = httpx.post(
            "https://api.tavily.com/search",
            json=body,
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        out: list[SearchHit] = []
        for item in payload.get("results", []):
            out.append(
                SearchHit(
                    title=item.get("title") or "",
                    url=item.get("url") or "",
                    snippet=item.get("content") or "",
                    source="tavily",
                    extra={
                        "published": item.get("published_date"),
                        "score": item.get("score"),
                    },
                )
            )
        return out


# ---------------------------------------------------------------------------
# Exa — neural search, semantic ranking
# ---------------------------------------------------------------------------


class ExaProvider(_Provider):
    name = "exa"
    priority = 20
    needs = ("EXA_API_KEY",)

    def call(self, query, max_results, *, opts):
        import httpx

        body: dict[str, Any] = {
            "query": query,
            "numResults": max_results,
            "useAutoprompt": True,
        }
        if "domains_allow" in opts:
            body["includeDomains"] = list(opts["domains_allow"])
        if "domains_block" in opts:
            body["excludeDomains"] = list(opts["domains_block"])
        if "time_range" in opts and opts["time_range"] == "year":
            # Exa accepts ISO dates; map "year" to last 365 days.
            body["startPublishedDate"] = (
                _time_ago_iso(365)
            )
        resp = httpx.post(
            "https://api.exa.ai/search",
            headers={"x-api-key": os.environ["EXA_API_KEY"]},
            json=body,
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        out: list[SearchHit] = []
        for item in payload.get("results", []):
            out.append(
                SearchHit(
                    title=item.get("title") or "",
                    url=item.get("url") or "",
                    snippet=item.get("text") or item.get("highlights", [""])[0],
                    source="exa",
                    extra={
                        "published": item.get("publishedDate"),
                        "score": item.get("score"),
                    },
                )
            )
        return out


# ---------------------------------------------------------------------------
# Serper — Google SERP proxy
# ---------------------------------------------------------------------------


class SerperProvider(_Provider):
    name = "serper"
    priority = 30
    needs = ("SERPER_API_KEY",)

    def call(self, query, max_results, *, opts):
        import httpx

        body: dict[str, Any] = {"q": query, "num": max_results}
        if "time_range" in opts:
            # serper accepts "qdr:h", "qdr:d", "qdr:w", "qdr:m", "qdr:y"
            mapping = {
                "day": "qdr:d", "week": "qdr:w",
                "month": "qdr:m", "year": "qdr:y",
            }
            tbs = mapping.get(opts["time_range"])
            if tbs:
                body["tbs"] = tbs
        resp = httpx.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": os.environ["SERPER_API_KEY"]},
            json=body,
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        out: list[SearchHit] = []
        for item in payload.get("organic", []):
            out.append(
                SearchHit(
                    title=item.get("title") or "",
                    url=item.get("link") or "",
                    snippet=item.get("snippet") or "",
                    source="serper",
                    extra={"position": item.get("position")},
                )
            )
        return out


# ---------------------------------------------------------------------------
# Brave — independent index
# ---------------------------------------------------------------------------


class BraveProvider(_Provider):
    name = "brave"
    priority = 40
    needs = ("BRAVE_API_KEY",)

    def call(self, query, max_results, *, opts):
        import httpx

        params: dict[str, Any] = {"q": query, "count": max_results}
        if "time_range" in opts:
            mapping = {
                "day": "pd", "week": "pw", "month": "pm", "year": "py",
            }
            freshness = mapping.get(opts["time_range"])
            if freshness:
                params["freshness"] = freshness
        resp = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": os.environ["BRAVE_API_KEY"]},
            params=params,
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        out: list[SearchHit] = []
        for item in (payload.get("web") or {}).get("results", []):
            out.append(
                SearchHit(
                    title=item.get("title") or "",
                    url=item.get("url") or "",
                    snippet=item.get("description") or "",
                    source="brave",
                    extra={"published": item.get("age")},
                )
            )
        return out


# ---------------------------------------------------------------------------
# Google CSE — bring-your-own custom search engine
# ---------------------------------------------------------------------------


class GoogleCseProvider(_Provider):
    name = "google_cse"
    priority = 50
    needs = ("GOOGLE_CSE_API_KEY", "GOOGLE_CSE_ID")

    def call(self, query, max_results, *, opts):
        import httpx

        params: dict[str, Any] = {
            "key": os.environ["GOOGLE_CSE_API_KEY"],
            "cx": os.environ["GOOGLE_CSE_ID"],
            "q": query,
            "num": min(max_results, 10),
        }
        if "time_range" in opts:
            mapping = {
                "day": "d1", "week": "w1", "month": "m1", "year": "y1",
            }
            date_restrict = mapping.get(opts["time_range"])
            if date_restrict:
                params["dateRestrict"] = date_restrict
        resp = httpx.get(
            "https://www.googleapis.com/customsearch/v1",
            params=params,
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        out: list[SearchHit] = []
        for item in payload.get("items", []):
            out.append(
                SearchHit(
                    title=item.get("title") or "",
                    url=item.get("link") or "",
                    snippet=item.get("snippet") or "",
                    source="google_cse",
                    extra={},
                )
            )
        return out


# ---------------------------------------------------------------------------
# DuckDuckGo HTML scraper — always-available zero-key fallback
# ---------------------------------------------------------------------------


class DuckDuckGoProvider(_Provider):
    name = "duckduckgo"
    priority = 90
    needs = ()  # always configured

    def configured(self) -> bool:
        return True

    def call(self, query, max_results, *, opts):
        try:
            import httpx
            from bs4 import BeautifulSoup
        except Exception as exc:
            raise FeatureUnavailable(
                "DuckDuckGo provider needs httpx + beautifulsoup4. "
                "Install with `pip install 'lyra[web]'`."
            ) from exc

        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "lyra-web-search/3.12"},
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        out: list[SearchHit] = []
        for div in soup.select("div.result")[:max_results]:
            a = div.select_one("a.result__a")
            snippet_el = (
                div.select_one("a.result__snippet")
                or div.select_one(".result__snippet")
            )
            if a is None:
                continue
            out.append(
                SearchHit(
                    title=a.get_text(" ", strip=True),
                    url=a.get("href", ""),
                    snippet=snippet_el.get_text(" ", strip=True) if snippet_el else "",
                    source="duckduckgo",
                    extra={},
                )
            )
        return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _time_ago_iso(days: int) -> str:
    """Return an ISO-8601 date string ``days`` days before today."""
    import datetime as _dt
    return (_dt.date.today() - _dt.timedelta(days=days)).isoformat()


# Provider registry — instantiate once so callers don't need to.
_REGISTRY: dict[str, _Provider] = {
    p.name: p for p in (
        TavilyProvider(),
        ExaProvider(),
        SerperProvider(),
        BraveProvider(),
        GoogleCseProvider(),
        DuckDuckGoProvider(),
    )
}


def get_provider(name: str) -> Optional[_Provider]:
    """Look up a registered provider by name (case-insensitive)."""
    return _REGISTRY.get(name.strip().lower())


def all_providers() -> List[_Provider]:
    """Return providers sorted by priority (lowest = tried first)."""
    return sorted(_REGISTRY.values(), key=lambda p: p.priority)


def configured_providers() -> List[_Provider]:
    """Subset of :func:`all_providers` whose env keys are present."""
    return [p for p in all_providers() if p.configured()]


__all__ = [
    "SearchHit",
    "TavilyProvider",
    "ExaProvider",
    "SerperProvider",
    "BraveProvider",
    "GoogleCseProvider",
    "DuckDuckGoProvider",
    "all_providers",
    "configured_providers",
    "get_provider",
]
