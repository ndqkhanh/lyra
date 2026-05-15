"""Tests for the v3.12 multi-backend WebSearch orchestrator + cache."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from lyra_core.tools import web_search as ws
from lyra_core.tools import web_search_cache as wsc
from lyra_core.tools import web_search_providers as wsp


@pytest.fixture(autouse=True)
def _reset_breaker():
    """Each test starts with a clean per-provider failure breaker."""
    ws.reset_circuit_breaker()
    yield
    ws.reset_circuit_breaker()


# ---------------------------------------------------------------------------
# _bm25_score / _rerank
# ---------------------------------------------------------------------------


class TestRerank:
    def test_term_match_outranks_non_match(self) -> None:
        hits = [
            {"title": "no matches here", "snippet": "lorem ipsum"},
            {"title": "claude api guide", "snippet": "anthropic claude tutorial"},
        ]
        ranked = ws._rerank(hits, "claude api")
        assert ranked[0]["title"] == "claude api guide"

    def test_distinct_term_diversity_bonus(self) -> None:
        # Doc A: mentions both query terms once.
        # Doc B: mentions one term five times.
        # Diversity bonus + tf saturation should keep A ahead.
        hits = [
            {"title": "claude api", "snippet": ""},
            {"title": "claude claude claude claude claude", "snippet": ""},
        ]
        ranked = ws._rerank(hits, "claude api")
        assert ranked[0]["title"] == "claude api"

    def test_skipped_when_fewer_than_two_hits(self) -> None:
        hits = [{"title": "solo", "snippet": ""}]
        assert ws._rerank(hits, "anything") == hits

    def test_no_query_terms_is_noop(self) -> None:
        hits = [{"title": "a"}, {"title": "b"}]
        # Punctuation-only query has zero word tokens → keep order.
        assert ws._rerank(hits, "!!! ???") == hits

    def test_stable_on_ties(self) -> None:
        hits = [
            {"title": "x", "snippet": "x"},
            {"title": "x", "snippet": "x"},
        ]
        ranked = ws._rerank(hits, "x")
        assert ranked == hits


# ---------------------------------------------------------------------------
# _apply_filters — domain allow/block
# ---------------------------------------------------------------------------


class TestApplyFilters:
    def test_block_drops_matching(self) -> None:
        hits = [
            {"url": "https://blog.example.com/a"},
            {"url": "https://other.net/b"},
        ]
        out = ws._apply_filters(
            hits, domains_allow=None, domains_block=["example.com"]
        )
        assert len(out) == 1
        assert out[0]["url"].endswith("/b")

    def test_allow_keeps_only_matching(self) -> None:
        hits = [
            {"url": "https://blog.example.com/a"},
            {"url": "https://other.net/b"},
        ]
        out = ws._apply_filters(
            hits, domains_allow=["example.com"], domains_block=None
        )
        assert len(out) == 1
        assert "example.com" in out[0]["url"]

    def test_block_wins_on_conflict(self) -> None:
        hits = [{"url": "https://example.com/a"}]
        out = ws._apply_filters(
            hits,
            domains_allow=["example.com"],
            domains_block=["example.com"],
        )
        assert out == []

    def test_no_filters_is_passthrough(self) -> None:
        hits = [{"url": "https://example.com/a"}]
        assert (
            ws._apply_filters(hits, domains_allow=None, domains_block=None)
            == hits
        )


# ---------------------------------------------------------------------------
# Cache — round-trip, expiry, purge
# ---------------------------------------------------------------------------


class TestCache:
    def test_put_then_get_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "cache.db"
        payload = [{"title": "x", "url": "u", "snippet": "s", "source": "test"}]
        wsc.put_cached(
            "duckduckgo", "hello", 5, {}, payload,
            ttl_seconds=60, path=path,
        )
        assert wsc.get_cached("duckduckgo", "hello", 5, {}, path=path) == payload

    def test_get_miss_on_unknown_key(self, tmp_path: Path) -> None:
        path = tmp_path / "cache.db"
        # File doesn't exist yet.
        assert wsc.get_cached("duckduckgo", "miss", 5, {}, path=path) is None

    def test_expired_row_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "cache.db"
        wsc.put_cached(
            "duckduckgo", "stale", 5, {}, [{"title": "old"}],
            ttl_seconds=10, path=path,
        )
        # Jump time forward past the TTL.
        real_time = time.time
        monkeypatch.setattr(
            time, "time", lambda: real_time() + 100
        )
        assert wsc.get_cached("duckduckgo", "stale", 5, {}, path=path) is None

    def test_purge_expired_removes_stale(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        path = tmp_path / "cache.db"
        wsc.put_cached(
            "duckduckgo", "a", 5, {}, [{}],
            ttl_seconds=10, path=path,
        )
        wsc.put_cached(
            "duckduckgo", "b", 5, {}, [{}],
            ttl_seconds=10_000, path=path,
        )
        real_time = time.time
        monkeypatch.setattr(time, "time", lambda: real_time() + 100)
        removed = wsc.purge_expired(path=path)
        assert removed == 1

    def test_key_includes_provider(self, tmp_path: Path) -> None:
        """Same query but different providers ⇒ different cache slots."""
        path = tmp_path / "cache.db"
        wsc.put_cached(
            "tavily", "q", 5, {}, [{"title": "T"}], path=path,
        )
        wsc.put_cached(
            "exa", "q", 5, {}, [{"title": "E"}], path=path,
        )
        assert wsc.get_cached("tavily", "q", 5, {}, path=path)[0]["title"] == "T"
        assert wsc.get_cached("exa", "q", 5, {}, path=path)[0]["title"] == "E"


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------


class TestProviderRegistry:
    def test_duckduckgo_always_configured(self) -> None:
        ddg = wsp.get_provider("duckduckgo")
        assert ddg is not None
        assert ddg.configured() is True

    def test_tavily_requires_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        tavily = wsp.get_provider("tavily")
        assert tavily is not None
        assert tavily.configured() is False
        monkeypatch.setenv("TAVILY_API_KEY", "test-key")
        assert tavily.configured() is True

    def test_priority_order_lowest_first(self) -> None:
        ordered = [p.name for p in wsp.all_providers()]
        # Tavily (10) before duckduckgo (90).
        assert ordered.index("tavily") < ordered.index("duckduckgo")

    def test_unknown_provider_returns_none(self) -> None:
        assert wsp.get_provider("yandex") is None

    def test_configured_subset_filters_correctly(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Clear every keyed provider's env.
        for var in (
            "TAVILY_API_KEY", "EXA_API_KEY", "SERPER_API_KEY",
            "BRAVE_API_KEY", "GOOGLE_CSE_API_KEY", "GOOGLE_CSE_ID",
        ):
            monkeypatch.delenv(var, raising=False)
        names = [p.name for p in wsp.configured_providers()]
        # DuckDuckGo is the only always-configured one.
        assert names == ["duckduckgo"]


# ---------------------------------------------------------------------------
# Orchestrator with injected provider (v3.11 contract)
# ---------------------------------------------------------------------------


def test_legacy_injected_provider_still_works() -> None:
    """v3.11 contract: passing ``provider=callable`` short-circuits the chain."""

    def fake_provider(query, max_results):
        return [{"title": "T", "url": "U", "snippet": "S"}]

    tool = ws.make_web_search_tool(provider=fake_provider)
    result = tool(query="anything", max_results=5)
    assert result["count"] == 1
    assert result["results"][0]["title"] == "T"


def test_legacy_provider_applies_filters_and_rerank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy provider path must still honour the new kwargs."""

    def fake_provider(query, max_results):
        return [
            {"title": "spam", "url": "https://blocked.com/x", "snippet": "off-topic"},
            {"title": "claude api docs", "url": "https://anthropic.com/c", "snippet": ""},
        ]

    tool = ws.make_web_search_tool(provider=fake_provider)
    result = tool(
        query="claude api",
        max_results=5,
        domains_block=["blocked.com"],
    )
    urls = [r["url"] for r in result["results"]]
    assert "https://blocked.com/x" not in urls
    assert result["results"][0]["title"] == "claude api docs"


# ---------------------------------------------------------------------------
# Orchestrator with registry chain (new in v3.12)
# ---------------------------------------------------------------------------


def _stub_provider(monkeypatch, name: str, hits: list[wsp.SearchHit]):
    """Force a registered provider to return ``hits`` and report configured.

    Plumbs through the real ``get_provider`` -> ``call()`` shape so the
    orchestrator's chain-walk logic is exercised end-to-end.
    """
    prov = wsp.get_provider(name)
    assert prov is not None
    monkeypatch.setattr(prov, "configured", lambda: True)
    monkeypatch.setattr(
        prov, "call", lambda q, m, *, opts: hits
    )
    return prov


def test_chain_returns_first_successful_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Make tavily fail; duckduckgo succeed. Pin cache path so the test
    # doesn't pollute the dev box's ~/.lyra.
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    tav = wsp.get_provider("tavily")
    monkeypatch.setattr(tav, "configured", lambda: True)
    monkeypatch.setattr(
        tav, "call",
        lambda q, m, *, opts: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    # Force every other keyed provider OFF so the chain hops straight
    # to duckduckgo after tavily fails.
    for name in ("exa", "serper", "brave", "google_cse"):
        prov = wsp.get_provider(name)
        monkeypatch.setattr(prov, "configured", lambda: False)

    _stub_provider(
        monkeypatch, "duckduckgo",
        [
            wsp.SearchHit(
                title="hit", url="https://x", snippet="",
                source="duckduckgo", extra={},
            )
        ],
    )
    tool = ws.make_web_search_tool()
    result = tool(query="x", max_results=5, cache=False)
    assert result["provider"] == "duckduckgo"
    assert result["count"] == 1


def test_pinned_provider_bypasses_chain(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    _stub_provider(
        monkeypatch, "exa",
        [
            wsp.SearchHit(
                title="exa-only", url="https://x", snippet="",
                source="exa", extra={},
            )
        ],
    )
    tool = ws.make_web_search_tool()
    result = tool(
        query="x", max_results=5, provider_name="exa", cache=False
    )
    assert result["provider"] == "exa"


def test_unknown_pinned_provider_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    tool = ws.make_web_search_tool()
    with pytest.raises(ValueError):
        tool(query="x", max_results=5, provider_name="yandex")


def test_cache_hit_skips_provider_call(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Second identical call within TTL must NOT re-invoke the provider."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    call_count = {"n": 0}

    def counted_call(query, max_results, *, opts):
        call_count["n"] += 1
        return [
            wsp.SearchHit(
                title="t", url="https://u", snippet="s",
                source="duckduckgo", extra={},
            )
        ]

    ddg = wsp.get_provider("duckduckgo")
    monkeypatch.setattr(ddg, "configured", lambda: True)
    monkeypatch.setattr(ddg, "call", counted_call)

    # First keyed providers OFF so we land on ddg.
    for name in ("tavily", "exa", "serper", "brave", "google_cse"):
        monkeypatch.setattr(
            wsp.get_provider(name), "configured", lambda: False
        )

    tool = ws.make_web_search_tool()
    a = tool(query="repeat", max_results=5)
    b = tool(query="repeat", max_results=5)
    assert call_count["n"] == 1
    assert a["count"] == b["count"] == 1


def test_empty_chain_returns_error_payload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    # No providers configured (mock everything off, including ddg).
    for name in (
        "tavily", "exa", "serper", "brave", "google_cse", "duckduckgo",
    ):
        monkeypatch.setattr(
            wsp.get_provider(name), "configured", lambda: False
        )
    tool = ws.make_web_search_tool()
    result = tool(query="x", max_results=5, cache=False)
    assert result["count"] == 0
    assert "error" in result


def test_circuit_breaker_trips_after_threshold(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """After 3 failures, the provider is skipped on subsequent calls."""
    monkeypatch.setenv("LYRA_HOME", str(tmp_path))
    fail_count = {"n": 0}

    def always_fail(query, max_results, *, opts):
        fail_count["n"] += 1
        raise RuntimeError("nope")

    tav = wsp.get_provider("tavily")
    monkeypatch.setattr(tav, "configured", lambda: True)
    monkeypatch.setattr(tav, "call", always_fail)
    # Keep DDG out of the chain for this test.
    for name in ("exa", "serper", "brave", "google_cse", "duckduckgo"):
        monkeypatch.setattr(
            wsp.get_provider(name), "configured", lambda: False
        )

    tool = ws.make_web_search_tool()
    for _ in range(5):
        tool(query="x", max_results=5, cache=False)
    # After the third failure, breaker trips and stops calling.
    assert fail_count["n"] == 3
