"""Tests for Effort-Aware Model Routing (P3-B3)."""
from __future__ import annotations

import pytest

from lyra_harness_core.providers import ProviderKind
from lyra_harness_core.routing.effort_router import (
    EffortConfig,
    EffortDecision,
    EffortRouter,
    EffortTier,
    infer_effort,
)


# ---------------------------------------------------------------------------
# EffortTier
# ---------------------------------------------------------------------------


class TestEffortTier:
    def test_five_tiers(self):
        assert len(EffortTier) == 5

    def test_values(self):
        assert EffortTier.LOW.value == "low"
        assert EffortTier.MEDIUM.value == "medium"
        assert EffortTier.HIGH.value == "high"
        assert EffortTier.XHIGH.value == "xhigh"
        assert EffortTier.MAX.value == "max"


# ---------------------------------------------------------------------------
# EffortConfig
# ---------------------------------------------------------------------------


class TestEffortConfig:
    def test_defaults_has_all_tiers(self):
        configs = EffortConfig.defaults()
        assert set(configs.keys()) == set(EffortTier)

    def test_low_tier_prefers_deepseek(self):
        configs = EffortConfig.defaults()
        assert configs[EffortTier.LOW].preferred == ProviderKind.DEEPSEEK

    def test_medium_tier_prefers_anthropic(self):
        configs = EffortConfig.defaults()
        assert configs[EffortTier.MEDIUM].preferred == ProviderKind.ANTHROPIC

    def test_max_tokens_increase_with_effort(self):
        configs = EffortConfig.defaults()
        tokens = [configs[t].max_tokens for t in EffortTier]
        assert tokens == sorted(tokens)

    def test_fallback_ordering(self):
        configs = EffortConfig.defaults()
        med = configs[EffortTier.MEDIUM]
        assert med.fallbacks[0] == ProviderKind.DEEPSEEK
        assert med.fallbacks[1] == ProviderKind.OPENAI

    def test_custom_config(self):
        cfg = EffortConfig(
            tier=EffortTier.HIGH,
            preferred=ProviderKind.QWEN,
            max_tokens=5000,
            fallbacks=(ProviderKind.MOCK,),
            description="test",
        )
        assert cfg.tier == EffortTier.HIGH
        assert cfg.preferred == ProviderKind.QWEN
        assert cfg.max_tokens == 5000
        assert cfg.description == "test"

    def test_frozen(self):
        cfg = EffortConfig.defaults()[EffortTier.LOW]
        with pytest.raises(Exception):
            cfg.max_tokens = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# EffortDecision
# ---------------------------------------------------------------------------


class TestEffortDecision:
    def test_default_not_fallback(self):
        d = EffortDecision(
            effort=EffortTier.MEDIUM,
            provider=ProviderKind.ANTHROPIC,
            max_tokens=4096,
        )
        assert d.is_fallback is False

    def test_fallback_decision(self):
        d = EffortDecision(
            effort=EffortTier.HIGH,
            provider=ProviderKind.OPENAI,
            max_tokens=8192,
            is_fallback=True,
            reason="anthropic unavailable",
        )
        assert d.is_fallback is True
        assert "anthropic" in d.reason

    def test_frozen(self):
        d = EffortDecision(
            effort=EffortTier.LOW,
            provider=ProviderKind.DEEPSEEK,
            max_tokens=1024,
        )
        with pytest.raises(Exception):
            d.provider = ProviderKind.MOCK  # type: ignore[misc]


# ---------------------------------------------------------------------------
# EffortRouter
# ---------------------------------------------------------------------------


class TestEffortRouter:
    @pytest.fixture
    def router(self):
        return EffortRouter()

    def test_route_low(self, router):
        d = router.route(EffortTier.LOW)
        assert d.effort == EffortTier.LOW
        assert d.provider == ProviderKind.DEEPSEEK
        assert d.max_tokens == 1024
        assert not d.is_fallback

    def test_route_medium(self, router):
        d = router.route(EffortTier.MEDIUM)
        assert d.provider == ProviderKind.ANTHROPIC
        assert d.max_tokens == 4096

    def test_route_high(self, router):
        d = router.route(EffortTier.HIGH)
        assert d.provider == ProviderKind.ANTHROPIC
        assert d.max_tokens == 8192

    def test_route_xhigh(self, router):
        d = router.route(EffortTier.XHIGH)
        assert d.provider == ProviderKind.ANTHROPIC
        assert d.max_tokens == 16384

    def test_route_max(self, router):
        d = router.route(EffortTier.MAX)
        assert d.provider == ProviderKind.ANTHROPIC
        assert d.max_tokens == 32768

    def test_fallback_when_preferred_unavailable(self, router):
        router.unavailable.add(ProviderKind.ANTHROPIC)
        d = router.route(EffortTier.MEDIUM)
        assert d.is_fallback
        assert d.provider == ProviderKind.DEEPSEEK  # first fallback

    def test_fallback_chain(self, router):
        router.unavailable.add(ProviderKind.ANTHROPIC)
        router.unavailable.add(ProviderKind.DEEPSEEK)
        d = router.route(EffortTier.MEDIUM)
        assert d.provider == ProviderKind.OPENAI  # second fallback

    def test_no_available_provider_raises(self, router):
        router.unavailable.add(ProviderKind.ANTHROPIC)
        router.unavailable.add(ProviderKind.DEEPSEEK)
        router.unavailable.add(ProviderKind.OPENAI)
        with pytest.raises(ValueError, match="no available provider"):
            router.route(EffortTier.MEDIUM)

    def test_route_with_override_provider(self, router):
        d = router.route_with_override(EffortTier.LOW, preferred_override=ProviderKind.OPENAI)
        assert d.provider == ProviderKind.OPENAI
        assert d.max_tokens == 1024  # still uses tier budget

    def test_route_with_override_tokens(self, router):
        d = router.route_with_override(EffortTier.MEDIUM, max_tokens_override=2000)
        assert d.max_tokens == 2000

    def test_route_with_override_both(self, router):
        d = router.route_with_override(
            EffortTier.HIGH,
            preferred_override=ProviderKind.QWEN,
            max_tokens_override=10000,
        )
        assert d.provider == ProviderKind.QWEN
        assert d.max_tokens == 10000

    def test_override_unavailable_falls_back(self, router):
        router.unavailable.add(ProviderKind.OPENAI)
        d = router.route_with_override(EffortTier.MEDIUM, preferred_override=ProviderKind.OPENAI)
        assert d.is_fallback
        assert d.provider == ProviderKind.ANTHROPIC  # tier default is available

    def test_mark_unavailable(self, router):
        router.mark_unavailable(ProviderKind.ANTHROPIC)
        assert ProviderKind.ANTHROPIC in router.unavailable

    def test_mark_available(self, router):
        router.mark_unavailable(ProviderKind.ANTHROPIC)
        router.mark_available(ProviderKind.ANTHROPIC)
        assert ProviderKind.ANTHROPIC not in router.unavailable

    def test_available_providers(self, router):
        available = router.available_providers()
        assert ProviderKind.ANTHROPIC in available
        assert ProviderKind.DEEPSEEK in available
        router.mark_unavailable(ProviderKind.ANTHROPIC)
        assert ProviderKind.ANTHROPIC not in router.available_providers()

    def test_get_config(self, router):
        cfg = router.get_config(EffortTier.LOW)
        assert cfg is not None
        assert cfg.tier == EffortTier.LOW

    def test_get_config_unknown_tier(self, router):
        assert router.get_config(EffortTier.MAX) is not None

    def test_empty_unavailable_default(self, router):
        assert len(router.unavailable) == 0

    def test_multiple_tiers_independent(self, router):
        router.mark_unavailable(ProviderKind.ANTHROPIC)
        # LOW still works (prefers DEEPSEEK)
        d_low = router.route(EffortTier.LOW)
        assert d_low.provider == ProviderKind.DEEPSEEK
        assert not d_low.is_fallback
        # MEDIUM falls back
        d_med = router.route(EffortTier.MEDIUM)
        assert d_med.is_fallback


# ---------------------------------------------------------------------------
# infer_effort
# ---------------------------------------------------------------------------


class TestInferEffort:
    def test_trivial_is_low(self):
        assert infer_effort("fix a typo") == EffortTier.LOW

    def test_format_is_low(self):
        assert infer_effort("format the output as JSON") == EffortTier.LOW

    def test_implement_is_medium(self):
        assert infer_effort("implement user authentication") == EffortTier.MEDIUM

    def test_refactor_is_medium(self):
        assert infer_effort("refactor the database layer") == EffortTier.MEDIUM

    def test_design_is_high(self):
        assert infer_effort("design a new caching architecture") == EffortTier.HIGH

    def test_architect_is_high(self):
        assert infer_effort("architect the microservices decomposition") == EffortTier.HIGH

    def test_audit_is_xhigh(self):
        assert infer_effort("audit the authentication module") == EffortTier.XHIGH

    def test_security_is_xhigh(self):
        assert infer_effort("security review of payment processing") == EffortTier.XHIGH

    def test_adversarial_is_max(self):
        assert infer_effort("adversarial verification of safety constraints") == EffortTier.MAX

    def test_short_simple_defaults_low(self):
        assert infer_effort("say hi") == EffortTier.LOW

    def test_unknown_defaults_medium(self):
        assert infer_effort("process the quarterly financial reconciliation report") == EffortTier.MEDIUM

    def test_mixed_keywords_highest_wins(self):
        # "fix" (MEDIUM) + "audit" (XHIGH) → XHIGH wins
        assert infer_effort("audit the codebase and fix all security issues") == EffortTier.XHIGH
