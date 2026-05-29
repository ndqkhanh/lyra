"""Tests for the dynamic pricing engine."""
from __future__ import annotations

from lyra_core.routing.dynamic_pricing import (
    DynamicPricingEngine,
    PricingTier,
    ProviderQuote,
)


class TestProviderQuote:
    def test_quote_is_frozen(self):
        quote = ProviderQuote(
            provider_id="test-model",
            tier=PricingTier.STANDARD,
            input_cost_per_1m=3.0,
            output_cost_per_1m=15.0,
            estimated_total_usd=0.01,
            est_input_tokens=1000,
            est_output_tokens=500,
            load_factor=0.5,
            latency_estimate_ms=800.0,
            timestamp=1000.0,
        )
        with pytest.raises(Exception):
            quote.estimated_total_usd = 0.50  # type: ignore[misc]

    def test_quote_contains_provider_info(self):
        quote = ProviderQuote(
            provider_id="claude-sonnet-4-6",
            tier=PricingTier.STANDARD,
            input_cost_per_1m=3.0,
            output_cost_per_1m=15.0,
            estimated_total_usd=0.01,
            est_input_tokens=1000,
            est_output_tokens=500,
            load_factor=0.5,
            latency_estimate_ms=800.0,
            timestamp=1000.0,
        )
        assert quote.provider_id == "claude-sonnet-4-6"
        assert quote.tier == PricingTier.STANDARD


import pytest  # noqa: E402


class TestDynamicPricingEngine:
    def test_estimate_known_provider(self):
        engine = DynamicPricingEngine()
        quote = engine.estimate("claude-sonnet-4-6", input_tokens=1000000, output_tokens=0)
        assert quote is not None
        assert quote.estimated_total_usd == pytest.approx(3.0, rel=0.1)

    def test_estimate_unknown_provider(self):
        engine = DynamicPricingEngine()
        quote = engine.estimate("nonexistent-model")
        assert quote is None

    def test_snapshot_returns_all_providers(self):
        engine = DynamicPricingEngine()
        snapshot = engine.snapshot(input_tokens=1000, output_tokens=500)
        assert len(snapshot.quotes) > 0
        assert snapshot.cheapest is not None
        assert snapshot.recommended is not None

    def test_cheapest_is_least_expensive(self):
        engine = DynamicPricingEngine()
        snapshot = engine.snapshot(input_tokens=1000, output_tokens=500)
        quotes = list(snapshot.quotes)
        quotes.sort(key=lambda q: q.estimated_total_usd)
        assert snapshot.cheapest is not None
        assert snapshot.cheapest.estimated_total_usd == quotes[0].estimated_total_usd

    def test_budget_pressure_affects_recommendation(self):
        engine = DynamicPricingEngine()
        engine.budget_pressure = 0.0
        snap_normal = engine.snapshot(input_tokens=1000, output_tokens=500)
        engine.budget_pressure = 0.9
        snap_tight = engine.snapshot(input_tokens=1000, output_tokens=500)
        assert snap_normal.recommended is not None
        assert snap_tight.recommended is not None

    def test_update_load(self):
        engine = DynamicPricingEngine()
        engine.update_load("claude-haiku-4-5", 0.9)
        quote = engine.estimate("claude-haiku-4-5")
        assert quote is not None
        assert quote.load_factor == 0.9

    def test_update_pricing(self):
        engine = DynamicPricingEngine()
        engine.update_pricing("custom-model", 1.0, 5.0)
        quote = engine.estimate("custom-model")
        assert quote is not None
        assert quote.input_cost_per_1m == 1.0

    def test_cost_for_tier_fast(self):
        engine = DynamicPricingEngine()
        cost = engine.cost_for_tier("fast", input_tokens=1000000, output_tokens=0)
        assert cost <= 1.0  # budget tier

    def test_cost_for_tier_advisor(self):
        engine = DynamicPricingEngine()
        cost = engine.cost_for_tier("advisor", input_tokens=1000000, output_tokens=0)
        assert cost > 1.0  # premium tier

    def test_set_budget_pressure_clamps(self):
        engine = DynamicPricingEngine()
        engine.set_budget_pressure(1.5)
        assert engine.budget_pressure == 1.0
        engine.set_budget_pressure(-0.5)
        assert engine.budget_pressure == 0.0

    def test_providers_property(self):
        engine = DynamicPricingEngine()
        providers = engine.providers
        assert len(providers) >= 4

    def test_snapshot_is_frozen(self):
        engine = DynamicPricingEngine()
        snap = engine.snapshot()
        with pytest.raises(Exception):
            snap.budget_pressure = 1.0  # type: ignore[misc]

    def test_pricing_tier_enum_values(self):
        assert PricingTier.BUDGET.value == "budget"
        assert PricingTier.STANDARD.value == "standard"
        assert PricingTier.PREMIUM.value == "premium"
