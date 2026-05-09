"""Phase M.2 - LiteLLM pricing engine + on-disk cache."""
from __future__ import annotations

import json
from decimal import Decimal

import pytest

from lyra_cli.observatory import pricing


@pytest.fixture
def fake_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(pricing, "_CACHE_ROOT", tmp_path)
    return tmp_path


def test_quote_uses_fallback_when_no_cache_and_offline(fake_cache, monkeypatch):
    """No network, no cache - must return the hardcoded fallback for known models."""
    monkeypatch.setattr(pricing, "_fetch_upstream", lambda *a, **k: None)
    q = pricing.quote("deepseek-v4-pro")
    assert q.source == "fallback"
    assert q.input_per_mtoken_usd is not None


def test_quote_returns_unknown_for_unknown_model(fake_cache, monkeypatch):
    monkeypatch.setattr(pricing, "_fetch_upstream", lambda *a, **k: None)
    q = pricing.quote("nonexistent-model-xyz")
    assert q.source == "unknown"
    assert q.input_per_mtoken_usd is None


def test_quote_prefers_cache_over_fallback(fake_cache, monkeypatch):
    cache_payload = {"deepseek-v4-pro": {"input_cost_per_token": 0.000001,
                                          "output_cost_per_token": 0.000004}}
    (fake_cache / "litellm.json").write_text(json.dumps(cache_payload))
    monkeypatch.setattr(pricing, "_fetch_upstream", lambda *a, **k: None)
    q = pricing.quote("deepseek-v4-pro")
    assert q.source == "cache"
    assert q.input_per_mtoken_usd == Decimal("1.0")
    assert q.output_per_mtoken_usd == Decimal("4.0")


def test_quote_refreshes_on_request(fake_cache, monkeypatch):
    fetched: dict[str, int] = {"n": 0}

    def fake_fetch(*a, **k):
        fetched["n"] += 1
        return {"foo": {"input_cost_per_token": 1e-7,
                        "output_cost_per_token": 1e-7}}

    monkeypatch.setattr(pricing, "_fetch_upstream", fake_fetch)
    pricing.quote("foo", refresh=True)
    pricing.quote("foo", refresh=True)
    assert fetched["n"] == 2


def test_quote_writes_cache_after_successful_fetch(fake_cache, monkeypatch):
    monkeypatch.setattr(
        pricing, "_fetch_upstream",
        lambda *a, **k: {"bar": {"input_cost_per_token": 5e-7,
                                 "output_cost_per_token": 5e-7}},
    )
    pricing.quote("bar", refresh=True)
    assert (fake_cache / "litellm.json").exists()


def test_quote_resolves_alias_to_canonical(fake_cache, monkeypatch):
    """Short ``v4-pro`` should resolve to ``deepseek-v4-pro``."""
    monkeypatch.setattr(pricing, "_fetch_upstream", lambda *a, **k: None)
    q = pricing.quote("v4-pro")
    assert q.model == "deepseek-v4-pro"


def test_cost_for_turn_when_prices_known(fake_cache, monkeypatch):
    monkeypatch.setattr(
        pricing, "_fetch_upstream",
        lambda *a, **k: {"deepseek-v4-pro": {
            "input_cost_per_token": 1e-6,
            "output_cost_per_token": 4e-6}},
    )
    row = {"model": "deepseek-v4-pro",
           "tokens_in": 1000, "tokens_out": 500}
    cost = pricing.cost_for_turn(row, refresh=True)
    assert cost == Decimal("0.003000")


def test_cost_for_turn_returns_none_for_unknown(fake_cache, monkeypatch):
    monkeypatch.setattr(pricing, "_fetch_upstream", lambda *a, **k: None)
    row = {"model": "nonexistent", "tokens_in": 1000, "tokens_out": 500}
    assert pricing.cost_for_turn(row) is None


def test_ttl_skips_fetch_when_recent(fake_cache, monkeypatch):
    (fake_cache / "litellm.json").write_text(
        '{"x": {"input_cost_per_token": 1e-6, "output_cost_per_token": 1e-6}}')
    (fake_cache / "litellm.fetched_at").write_text(
        "2099-01-01T00:00:00")
    fetched = {"n": 0}
    monkeypatch.setattr(
        pricing, "_fetch_upstream",
        lambda *a, **k: (fetched.__setitem__("n", fetched["n"] + 1) or {}),
    )
    pricing.quote("x")
    assert fetched["n"] == 0
