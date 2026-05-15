"""v3.12 ``WebSearch`` orchestrator — multi-provider, reranked, cached.

Public surface stays compatible with v3.11: ``make_web_search_tool()``
returns a callable taking ``query`` + ``max_results`` and returning
``{"results": [...], "count": N}``. New optional kwargs:

* ``provider``   — pin a specific backend ("tavily", "exa", "serper",
  "brave", "google_cse", "duckduckgo"). Omit for the smart chain.
* ``time_range`` — ``"day"`` / ``"week"`` / ``"month"`` / ``"year"``.
  Pass-through to providers that support it.
* ``domains_allow`` / ``domains_block`` — substring matches against
  result URLs. Applied after the provider call so they work even when
  the chosen provider doesn't natively support filtering.
* ``rerank`` (default ``True``) — re-order results with a tiny BM25-ish
  scorer that weights title + snippet against the query terms.
* ``cache`` (default ``True``) — read/write the SQLite cache.

Backwards compat: the v3.11 ``provider=<callable>`` keyword still
works. When passed, it bypasses the registry chain entirely —
mirrors the v3.11 test contract.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Optional

from . import web_search_cache as _cache
from . import web_search_providers as _providers
from ..lsp_backend.errors import FeatureUnavailable


# Time-range → TTL: queries that ask for recent data shouldn't be
# cached as long as evergreen ones. ``None`` falls back to the
# cache module's 1-hour default.
_TTL_BY_RANGE = {
    "day":   600,    # 10 min
    "week":  1800,   # 30 min
    "month": 3600,   # 1 hour
    "year":  3600,   # 1 hour
}


_WORD_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    """Lowercase word-character tokens — cheap, deterministic, dependency-free."""
    return [t for t in _WORD_RE.findall(text.lower()) if len(t) > 1]


def _bm25_score(
    query_terms: list[str],
    doc_text: str,
    *,
    k1: float = 1.5,
    b: float = 0.75,
    avg_doc_len: float = 50.0,
) -> float:
    """Single-document BM25-flavoured score against pre-tokenised query.

    Not a "real" BM25 (we don't have a corpus to learn IDF from at
    query time) but the tf+length-normalisation shape carries the
    intuition: a document that mentions every query term once outranks
    a document that mentions one term ten times. Cheap, deterministic,
    and good enough to fix the "DuckDuckGo returned the right page in
    slot 5" problem.
    """
    doc_terms = _tokenize(doc_text)
    if not doc_terms:
        return 0.0
    doc_len = len(doc_terms)
    counts: dict[str, int] = {}
    for term in doc_terms:
        counts[term] = counts.get(term, 0) + 1
    score = 0.0
    for term in query_terms:
        tf = counts.get(term, 0)
        if tf == 0:
            continue
        norm = 1 - b + b * (doc_len / max(avg_doc_len, 1.0))
        score += (tf * (k1 + 1)) / (tf + k1 * norm)
    # Mild boost for diversity — a doc hitting many distinct query
    # terms beats one that hammers one term repeatedly.
    distinct_hits = sum(1 for t in query_terms if counts.get(t, 0) > 0)
    if query_terms:
        score *= 1.0 + 0.1 * (distinct_hits / len(query_terms))
    return score


def _rerank(
    hits: list[dict[str, Any]], query: str
) -> list[dict[str, Any]]:
    """Return ``hits`` sorted by BM25-style score (highest first).

    Stable on ties — preserves the provider's order when scores match.
    Skip-no-op when there are fewer than 2 hits.
    """
    if len(hits) < 2:
        return hits
    query_terms = _tokenize(query)
    if not query_terms:
        return hits
    scored: list[tuple[float, int, dict[str, Any]]] = []
    for idx, hit in enumerate(hits):
        doc_text = " ".join(
            [hit.get("title") or "", hit.get("snippet") or ""]
        )
        score = _bm25_score(query_terms, doc_text)
        scored.append((-score, idx, hit))
    scored.sort()
    return [item[2] for item in scored]


def _apply_filters(
    hits: list[dict[str, Any]],
    *,
    domains_allow: Optional[list[str]],
    domains_block: Optional[list[str]],
) -> list[dict[str, Any]]:
    """Substring-match URL filters applied after the provider call.

    Substring (not exact) so ``example.com`` matches ``www.example.com``
    and ``blog.example.com`` — the typical user mental model. Block
    wins over allow when both lists hit, because the safer outcome
    on a conflict is to drop.
    """
    if not domains_allow and not domains_block:
        return hits
    out: list[dict[str, Any]] = []
    for hit in hits:
        url = (hit.get("url") or "").lower()
        if domains_block and any(d.lower() in url for d in domains_block):
            continue
        if domains_allow and not any(d.lower() in url for d in domains_allow):
            continue
        out.append(hit)
    return out


def _normalise_opts(opts: dict[str, Any]) -> dict[str, Any]:
    """Strip unknown opts so providers don't choke on extras.

    Whitelisting (rather than blacklisting) keeps the surface
    predictable when a caller passes an opt that some providers
    recognise and others don't.
    """
    keep = (
        "time_range", "domains_allow", "domains_block",
    )
    return {k: v for k, v in opts.items() if k in keep and v is not None}


# Circuit breaker — module-level so it survives across tool calls.
# Per-provider failure counts; reset on next successful call to that
# provider. Tiny memory footprint and good enough to skip a flaky
# provider for the duration of the session.
_CIRCUIT_BREAKER: dict[str, int] = {}
_BREAKER_TRIP_THRESHOLD = 3


def _try_provider(
    provider: _providers._Provider,
    query: str,
    max_results: int,
    opts: dict[str, Any],
) -> Optional[list[dict[str, Any]]]:
    """Call ``provider`` once; return None on failure (logged via breaker)."""
    if _CIRCUIT_BREAKER.get(provider.name, 0) >= _BREAKER_TRIP_THRESHOLD:
        return None
    try:
        hits = provider.call(query, max_results, opts=opts)
    except FeatureUnavailable:
        # Missing deps — count as breaker-failure so we stop trying.
        _CIRCUIT_BREAKER[provider.name] = (
            _CIRCUIT_BREAKER.get(provider.name, 0) + 1
        )
        return None
    except Exception:
        _CIRCUIT_BREAKER[provider.name] = (
            _CIRCUIT_BREAKER.get(provider.name, 0) + 1
        )
        return None
    # Success — reset the breaker.
    _CIRCUIT_BREAKER[provider.name] = 0
    return [h.to_dict() for h in hits]


def reset_circuit_breaker() -> None:
    """Clear the in-memory per-provider failure counts.

    Useful in tests (each test wants a clean breaker) and in long
    sessions where the user *wants* to retry a previously-flaky
    provider (transient cloud outage).
    """
    _CIRCUIT_BREAKER.clear()


def make_web_search_tool(
    *,
    provider: Callable[[str, int], list[dict]] | None = None,
) -> Callable[..., dict]:
    """Build the LLM-callable ``WebSearch`` tool.

    v3.11 contract preserved: when ``provider`` is a callable, it
    bypasses the registry chain and is used as-is. This is the test
    seam — every existing test that mocks the provider via this
    keyword still works.

    When ``provider`` is ``None`` (the default), the tool walks the
    registry chain (configured providers first by priority, then the
    no-key DuckDuckGo scraper) until one returns results.
    """

    def web_search(
        *,
        query: str,
        max_results: int = 5,
        provider_name: Optional[str] = None,
        time_range: Optional[str] = None,
        domains_allow: Optional[list[str]] = None,
        domains_block: Optional[list[str]] = None,
        rerank: bool = True,
        cache: bool = True,
    ) -> dict:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if max_results <= 0:
            raise ValueError("max_results must be positive")

        # Back-compat: v3.11 injected callable wins over the registry.
        # Contract: preserve exact pass-through of {title, url, snippet}
        # so existing tool-test seams continue to work unchanged.
        if provider is not None:
            raw = provider(query.strip(), max_results)
            normalised = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("snippet", ""),
                }
                for r in raw[:max_results]
            ]
            if domains_allow or domains_block:
                normalised = _apply_filters(
                    normalised,
                    domains_allow=domains_allow,
                    domains_block=domains_block,
                )
            if rerank:
                normalised = _rerank(normalised, query.strip())
            return {"results": normalised, "count": len(normalised)}

        opts = _normalise_opts(
            {
                "time_range": time_range,
                "domains_allow": domains_allow,
                "domains_block": domains_block,
            }
        )

        # Decide provider order.
        if provider_name:
            pinned = _providers.get_provider(provider_name)
            if pinned is None:
                raise ValueError(
                    f"unknown provider {provider_name!r}; "
                    f"valid: {[p.name for p in _providers.all_providers()]}"
                )
            chain = [pinned]
        else:
            chain = _providers.configured_providers()

        # Cache check happens *per provider in the chain* because the
        # cache key includes the provider name — pinning vs falling
        # through should pull different cached payloads even for the
        # same query.
        ttl = _TTL_BY_RANGE.get(time_range or "", 3600)

        last_results: list[dict[str, Any]] | None = None
        used_provider = ""
        for prov in chain:
            if cache:
                cached = _cache.get_cached(
                    prov.name, query.strip(), max_results, opts
                )
                if cached is not None:
                    last_results = cached
                    used_provider = prov.name
                    break

            hits = _try_provider(prov, query.strip(), max_results, opts)
            if hits is None:
                continue

            hits = _apply_filters(
                hits,
                domains_allow=domains_allow,
                domains_block=domains_block,
            )

            if rerank:
                hits = _rerank(hits, query.strip())

            if cache:
                _cache.put_cached(
                    prov.name,
                    query.strip(),
                    max_results,
                    opts,
                    hits,
                    ttl_seconds=ttl,
                )
            last_results = hits
            used_provider = prov.name
            break

        if last_results is None:
            return {
                "results": [],
                "count": 0,
                "provider": "(none)",
                "error": (
                    "no provider returned results. "
                    "Configure one of TAVILY_API_KEY, EXA_API_KEY, "
                    "SERPER_API_KEY, BRAVE_API_KEY, or "
                    "GOOGLE_CSE_API_KEY+GOOGLE_CSE_ID — or check "
                    "the DuckDuckGo HTML scraper isn't being rate-limited."
                ),
            }

        return {
            "results": last_results[:max_results],
            "count": min(len(last_results), max_results),
            "provider": used_provider,
        }

    web_search.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "WebSearch",
        "description": (
            "Run a web search across configured providers (Tavily, Exa, "
            "Serper, Brave, Google CSE, DuckDuckGo) with reranking, "
            "caching, and optional time / domain filters."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 5},
                "provider_name": {
                    "type": "string",
                    "description": (
                        "Pin a specific provider. Omit to let the "
                        "fallback chain pick."
                    ),
                },
                "time_range": {
                    "type": "string",
                    "enum": ["day", "week", "month", "year"],
                },
                "domains_allow": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "domains_block": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "rerank": {"type": "boolean", "default": True},
                "cache": {"type": "boolean", "default": True},
            },
            "required": ["query"],
        },
    }
    return web_search


class WebSearchTool:
    """Tool wrapper for WebSearch compatible with harness_core.tools.ToolRegistry."""

    name = "WebSearch"
    description = "Search the web and return ranked snippets with URLs."
    risk = "low"
    writes = False

    def __init__(self, *, provider: Any = None) -> None:
        self._search = make_web_search_tool(provider=provider)

    def run(self, args: Any) -> str:
        """Execute the web search and return formatted results."""
        result = self._search(**args)
        results = result.get("results", [])
        count = result.get("count", 0)

        if count == 0:
            return f"WebSearch found no results for: {args.get('query', '')}"

        lines = [f"WebSearch found {count} result{'s' if count != 1 else ''}:\n"]
        for i, hit in enumerate(results, 1):
            title = hit.get("title", "")
            url = hit.get("url", "")
            snippet = hit.get("snippet", "")
            source = hit.get("source", "")
            lines.append(f"{i}. {title}")
            lines.append(f"   URL: {url}")
            if snippet:
                lines.append(f"   {snippet}")
            if source:
                lines.append(f"   (via {source})")
            lines.append("")

        return "\n".join(lines)

    def to_schema(self) -> dict:
        """Return the tool schema for LLM consumption."""
        return getattr(self._search, "__tool_schema__", {})


__all__ = [
    "_apply_filters",
    "_bm25_score",
    "_rerank",
    "make_web_search_tool",
    "reset_circuit_breaker",
    "WebSearchTool",
]
