"""
Unit tests for the Lyra Effort Scale (lyra_effort).

Covers:
- EffortLevel enum properties (persistence, budgets, orchestration)
- EffortManager per-provider mapping
- Provider capability clamping
- Ultracode = xhigh + orchestration invariant
- Dynamic calibration
"""

from __future__ import annotations

import pytest

from lyra_effort import (
    EffortConfig,
    EffortLevel,
    EffortManager,
    EffortMapping,
    OrchestrationConfig,
    ProviderEffortCapability,
)


# ────────────────────────────────────────────────────────────────────
# EffortLevel enum tests
# ────────────────────────────────────────────────────────────────────


class TestEffortLevel:
    """Tests for the EffortLevel enum."""

    def test_six_levels_exist(self) -> None:
        """All six effort levels from the /effort menu must be defined."""
        assert len(list(EffortLevel)) == 6
        assert EffortLevel.LOW.value == "low"
        assert EffortLevel.MEDIUM.value == "medium"
        assert EffortLevel.HIGH.value == "high"
        assert EffortLevel.XHIGH.value == "xhigh"
        assert EffortLevel.MAX.value == "max"
        assert EffortLevel.ULTRACODE.value == "ultracode"

    def test_persistence_rules(self) -> None:
        """low-xhigh persist; max and ultracode are session-only."""
        assert EffortLevel.LOW.is_persistent is True
        assert EffortLevel.MEDIUM.is_persistent is True
        assert EffortLevel.HIGH.is_persistent is True
        assert EffortLevel.XHIGH.is_persistent is True
        assert EffortLevel.MAX.is_persistent is False
        assert EffortLevel.ULTRACODE.is_persistent is False

    def test_reasoning_budgets(self) -> None:
        """Budgets must follow the plan spec: low=1024, medium=4096, high=8192,
        xhigh=16384, max=32000, ultracode=16384."""
        assert EffortLevel.LOW.reasoning_budget == 1024
        assert EffortLevel.MEDIUM.reasoning_budget == 4096
        assert EffortLevel.HIGH.reasoning_budget == 8192
        assert EffortLevel.XHIGH.reasoning_budget == 16384
        assert EffortLevel.MAX.reasoning_budget == 32000
        assert EffortLevel.ULTRACODE.reasoning_budget == 16384

    def test_ultracode_budget_equals_xhigh(self) -> None:
        """🔑 INVARIANT: ultracode = xhigh + orchestration, NOT a 6th API tier."""
        assert EffortLevel.ULTRACODE.reasoning_budget == EffortLevel.XHIGH.reasoning_budget

    def test_only_ultracode_has_orchestration(self) -> None:
        """Only ultracode should have orchestration_enabled = True."""
        assert EffortLevel.LOW.orchestration_enabled is False
        assert EffortLevel.HIGH.orchestration_enabled is False
        assert EffortLevel.XHIGH.orchestration_enabled is False
        assert EffortLevel.MAX.orchestration_enabled is False
        assert EffortLevel.ULTRACODE.orchestration_enabled is True


# ────────────────────────────────────────────────────────────────────
# EffortManager tests
# ────────────────────────────────────────────────────────────────────


class TestEffortManager:
    """Tests for the EffortManager class."""

    def test_default_level_is_high(self) -> None:
        """Default effort level should be HIGH."""
        mgr = EffortManager()
        assert mgr.current_level == EffortLevel.HIGH

    def test_set_level(self) -> None:
        """Setting the effort level should update current_level."""
        mgr = EffortManager()
        mgr.set_level(EffortLevel.XHIGH)
        assert mgr.current_level == EffortLevel.XHIGH

    def test_set_ultracode_enables_orchestration(self) -> None:
        """🔑 Setting ultracode MUST enable orchestration."""
        mgr = EffortManager()
        mgr.set_level(EffortLevel.ULTRACODE)
        assert mgr.current_level == EffortLevel.ULTRACODE
        assert mgr.orchestration_enabled is True

    def test_set_non_ultracode_does_not_enable_orchestration(self) -> None:
        """Setting any level other than ultracode should NOT enable orchestration."""
        mgr = EffortManager()
        mgr.set_level(EffortLevel.XHIGH)
        assert mgr.orchestration_enabled is False
        mgr.set_level(EffortLevel.MAX)
        assert mgr.orchestration_enabled is False

    def test_set_orchestration_directly(self) -> None:
        """Orchestration should be configurable separately from effort level."""
        mgr = EffortManager()
        mgr.set_orchestration(True, auto_trigger_threshold="high")
        assert mgr.orchestration_enabled is True
        assert mgr.config.orchestration.auto_trigger_threshold == "high"

    # ── Per-provider mapping ───────────────────────────────────

    def test_map_anthropic_uses_budget_tokens(self) -> None:
        """Anthropic gets native budget_tokens."""
        mgr = EffortManager()
        mapping = mgr.map_effort(EffortLevel.XHIGH, provider="anthropic")
        assert mapping.budget_tokens == 16384
        assert mapping.thinking_instruction == ""
        assert mapping.orchestration_enabled is False

    def test_map_deepseek_uses_thinking_instruction(self) -> None:
        """DeepSeek has no budget_tokens API — gets a prompt instruction instead."""
        mgr = EffortManager()
        mapping = mgr.map_effort(EffortLevel.HIGH, provider="deepseek")
        assert mapping.thinking_instruction == "Think step by step before answering."
        assert mapping.budget_tokens == 8192  # advisory, still present

    def test_map_openai_uses_reasoning_effort(self) -> None:
        """OpenAI gets reasoning_effort parameter."""
        mgr = EffortManager()
        mapping = mgr.map_effort(EffortLevel.HIGH, provider="openai")
        assert mapping.reasoning_effort == "medium"

    def test_map_ultracode_preserves_orchestration_flag(self) -> None:
        """🔑 Ultracode mapping must have orchestration_enabled=True for ALL providers."""
        mgr = EffortManager()
        for provider in ["anthropic", "deepseek", "openai", "google"]:
            mapping = mgr.map_effort(EffortLevel.ULTRACODE, provider=provider)
            assert mapping.orchestration_enabled is True, (
                f"ultracode orchestration not enabled for {provider}"
            )
            # Budget must equal xhigh (not a 6th tier)
            xhigh_mapping = mgr.map_effort(EffortLevel.XHIGH, provider=provider)
            assert mapping.budget_tokens == xhigh_mapping.budget_tokens, (
                f"ultracode budget differs from xhigh for {provider}"
            )

    def test_map_uses_session_level_when_none_given(self) -> None:
        """map_effort() with level=None uses the current session level."""
        mgr = EffortManager()
        mgr.set_level(EffortLevel.MEDIUM)
        mapping = mgr.map_effort(level=None, provider="anthropic")
        assert mapping.level == EffortLevel.MEDIUM

    # ── Provider capability clamping ───────────────────────────

    def test_clamp_deepseek_max_to_xhigh(self) -> None:
        """DeepSeek doesn't support MAX — should clamp to XHIGH."""
        mgr = EffortManager()
        mapping = mgr.map_effort(EffortLevel.MAX, provider="deepseek")
        assert mapping.level == EffortLevel.XHIGH

    def test_clamp_google_max_to_high(self) -> None:
        """Google doesn't support XHIGH/MAX — should clamp to HIGH."""
        mgr = EffortManager()
        mapping = mgr.map_effort(EffortLevel.XHIGH, provider="google")
        assert mapping.level == EffortLevel.HIGH

    def test_no_clamp_when_within_capability(self) -> None:
        """Anthropic supports MAX — no clamping needed."""
        mgr = EffortManager()
        mapping = mgr.map_effort(EffortLevel.MAX, provider="anthropic")
        assert mapping.level == EffortLevel.MAX

    # ── Max tokens per turn ────────────────────────────────────

    def test_max_tokens_per_turn_by_level(self) -> None:
        """Each effort level has a hard cap on output tokens."""
        mgr = EffortManager()
        assert mgr.map_effort(EffortLevel.LOW, provider="anthropic").max_tokens_per_turn == 2048
        assert mgr.map_effort(EffortLevel.MEDIUM, provider="anthropic").max_tokens_per_turn == 4096
        assert mgr.map_effort(EffortLevel.HIGH, provider="anthropic").max_tokens_per_turn == 8192
        assert mgr.map_effort(EffortLevel.XHIGH, provider="anthropic").max_tokens_per_turn == 16384
        assert mgr.map_effort(EffortLevel.MAX, provider="anthropic").max_tokens_per_turn == 32768

    # ── Calibration ────────────────────────────────────────────

    def test_record_calibration_stores_data(self) -> None:
        """Calibration data should be recorded and retrievable."""
        mgr = EffortManager()
        mgr.record_calibration("anthropic", EffortLevel.HIGH, accuracy=0.85, tokens_used=7000, latency_ms=1200)
        # Should not raise
        mgr.record_calibration("deepseek", EffortLevel.HIGH, accuracy=0.82, tokens_used=9000, latency_ms=800)

    def test_calibration_increases_budget_when_below_target(self) -> None:
        """When accuracy is below target, budget should increase."""
        mgr = EffortManager()
        # Record accuracy below target (0.688 < 0.88 target for HIGH)
        mgr.record_calibration("anthropic", EffortLevel.HIGH, accuracy=0.70, tokens_used=8192, latency_ms=1500)
        mapping = mgr.map_effort(EffortLevel.HIGH, provider="anthropic")
        # Budget should be higher than default 8192
        assert mapping.budget_tokens > 8192

    # ── Provider listing ───────────────────────────────────────

    def test_list_providers(self) -> None:
        """list_providers() returns all known providers."""
        providers = EffortManager.list_providers()
        assert "anthropic" in providers
        assert "deepseek" in providers
        assert "openai" in providers
        assert "google" in providers
        assert "openrouter" in providers
        assert "openweights" in providers

    def test_get_provider_capability(self) -> None:
        """get_provider_capability() returns the right capabilities."""
        mgr = EffortManager()
        cap = mgr.get_provider_capability("anthropic")
        assert cap is not None
        assert cap.supports_budget_tokens is True

        cap = mgr.get_provider_capability("deepseek")
        assert cap is not None
        assert cap.supports_budget_tokens is False

    def test_unknown_provider_returns_none(self) -> None:
        """Unknown providers get None for capability."""
        mgr = EffortManager()
        assert mgr.get_provider_capability("nonexistent") is None


# ────────────────────────────────────────────────────────────────────
# EffortConfig tests
# ────────────────────────────────────────────────────────────────────


class TestEffortConfig:
    """Tests for the EffortConfig dataclass."""

    def test_default_config(self) -> None:
        """Default config: HIGH effort, no orchestration."""
        config = EffortConfig()
        assert config.current_level == EffortLevel.HIGH
        assert config.orchestration.enabled is False
        assert config.orchestration.auto_trigger_threshold == "medium"
        assert config.provider_overrides == {}

    def test_custom_config(self) -> None:
        """Custom config with overrides."""
        config = EffortConfig(
            current_level=EffortLevel.XHIGH,
            orchestration=OrchestrationConfig(enabled=True, auto_trigger_threshold="high"),
            provider_overrides={"deepseek": EffortLevel.HIGH},
        )
        assert config.current_level == EffortLevel.XHIGH
        assert config.orchestration.enabled is True
        assert config.provider_overrides["deepseek"] == EffortLevel.HIGH

    def test_from_config_roundtrip(self) -> None:
        """EffortManager.from_config() should restore state."""
        original = EffortConfig(
            current_level=EffortLevel.MEDIUM,
            orchestration=OrchestrationConfig(enabled=True),
        )
        mgr = EffortManager.from_config(original)
        assert mgr.current_level == EffortLevel.MEDIUM
        assert mgr.orchestration_enabled is True


# ────────────────────────────────────────────────────────────────────
# ProviderEffortCapability tests
# ────────────────────────────────────────────────────────────────────


class TestProviderEffortCapability:
    """Tests for the ProviderEffortCapability dataclass."""

    def test_anthropic_capability(self) -> None:
        cap = ProviderEffortCapability(
            provider="anthropic",
            supports_budget_tokens=True,
            max_effort_level=EffortLevel.MAX,
        )
        assert cap.provider == "anthropic"
        assert cap.supports_budget_tokens is True
        assert cap.max_effort_level == EffortLevel.MAX

    def test_openweights_capability(self) -> None:
        cap = ProviderEffortCapability(
            provider="openweights",
            supports_budget_tokens=False,
            supports_reasoning_effort=False,
            max_effort_level=EffortLevel.HIGH,
        )
        assert cap.supports_budget_tokens is False
        assert cap.supports_prompt_instructions is True  # default


# ────────────────────────────────────────────────────────────────────
# Cross-provider invariant tests
# ────────────────────────────────────────────────────────────────────


class TestCrossProviderInvariants:
    """🔑 Tests that must pass for EVERY provider."""

    ALL_PROVIDERS = ["anthropic", "deepseek", "openai", "google", "openrouter", "openweights"]

    @pytest.mark.parametrize("provider", ALL_PROVIDERS)
    def test_ultracode_orchestration_enabled_for_all_providers(self, provider: str) -> None:
        """Ultracode must enable orchestration regardless of provider."""
        mgr = EffortManager()
        mapping = mgr.map_effort(EffortLevel.ULTRACODE, provider=provider)
        assert mapping.orchestration_enabled is True

    @pytest.mark.parametrize("provider", ALL_PROVIDERS)
    def test_ultracode_and_xhigh_have_same_budget_for_all_providers(self, provider: str) -> None:
        """The ultracode = xhigh + orchestration invariant must hold for all providers."""
        mgr = EffortManager()
        ultra = mgr.map_effort(EffortLevel.ULTRACODE, provider=provider)
        xhigh = mgr.map_effort(EffortLevel.XHIGH, provider=provider)
        assert ultra.budget_tokens == xhigh.budget_tokens, (
            f"ultracode budget ({ultra.budget_tokens}) != xhigh budget ({xhigh.budget_tokens}) "
            f"for {provider}"
        )

    @pytest.mark.parametrize("provider", ALL_PROVIDERS)
    def test_every_provider_has_a_mapping(self, provider: str) -> None:
        """Every known provider must produce a valid EffortMapping."""
        mgr = EffortManager()
        for level in EffortLevel:
            mapping = mgr.map_effort(level, provider=provider)
            assert isinstance(mapping, EffortMapping)
            assert mapping.provider == provider
            assert mapping.level is not None
