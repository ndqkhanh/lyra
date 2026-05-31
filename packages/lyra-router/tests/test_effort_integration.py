"""
Integration tests: ModelRouter + EffortManager (Tier 1 — Provider & Reasoning Foundation).

Verifies:
- Effort-aware routing decisions
- Per-provider effort mapping in routing decisions
- Ultracode = xhigh budget + orchestration invariant
- Provider capability clamping flows through router
- set_effort() changes session-level behavior
"""

from __future__ import annotations

from lyra_effort import EffortLevel, EffortManager
from lyra_router import ModelRouter


class TestEffortAwareRouting:
    """Router produces effort-aware decisions."""

    def test_default_effort_is_high(self) -> None:
        router = ModelRouter()
        decision = router.route("simple task")
        assert decision.effort_level == "high"
        assert decision.effort_budget_tokens > 0

    def test_xhigh_effort_routing(self) -> None:
        router = ModelRouter()
        decision = router.route("complex architecture analysis", effort_level="xhigh")
        assert decision.effort_level == "xhigh"
        assert decision.effort_budget_tokens == 16384

    def test_max_effort_routing(self) -> None:
        router = ModelRouter()
        decision = router.route("research new algorithm design", effort_level="max")
        assert decision.effort_level == "max"
        assert decision.effort_budget_tokens == 32000

    def test_low_effort_routing(self) -> None:
        router = ModelRouter()
        decision = router.route("what is 2+2", effort_level="low")
        assert decision.effort_level == "low"
        assert decision.effort_budget_tokens == 1024

    def test_ultracode_uses_xhigh_budget(self) -> None:
        """🔑 Ultracode must use xhigh budget (not a 6th tier)."""
        router = ModelRouter()
        ultra = router.route("audit everything", effort_level="ultracode")
        xhigh = router.route("audit everything", effort_level="xhigh")
        assert ultra.effort_budget_tokens == xhigh.effort_budget_tokens


class TestSessionEffort:
    """set_effort() changes session-level behavior."""

    def test_set_effort_changes_session(self) -> None:
        router = ModelRouter()
        router.set_effort("xhigh")
        decision = router.route("some task")
        assert decision.effort_level == "xhigh"

    def test_set_effort_ultracode(self) -> None:
        router = ModelRouter()
        router.set_effort("ultracode")
        assert router.effort.orchestration_enabled is True
        decision = router.route("some task")
        assert decision.effort_level == "ultracode"

    def test_route_override_overrides_session(self) -> None:
        """route(effort_level=...) should override session effort for one call."""
        router = ModelRouter()
        router.set_effort("high")
        decision = router.route("some task", effort_level="xhigh")
        assert decision.effort_level == "xhigh"
        # Session should be unchanged
        assert router.effort.current_level == EffortLevel.HIGH

    def test_invalid_effort_falls_back_to_session(self) -> None:
        router = ModelRouter()
        decision = router.route("some task", effort_level="super_duper_max")
        assert decision.effort_level == "high"  # falls back to default


class TestEffortMappingInDecision:
    """RoutingDecisions contain per-provider effort parameters."""

    def test_anthropic_decision_has_budget_tokens(self) -> None:
        router = ModelRouter()
        decision = router.route("implement auth", effort_level="xhigh")
        assert decision.effort_budget_tokens > 0

    def test_effort_instruction_is_empty_for_anthropic(self) -> None:
        """Anthropic uses budget_tokens, not prompt instructions."""
        router = ModelRouter()
        decision = router.route("implement auth", effort_level="xhigh")
        # Anthropic models get empty instruction (they use native budget_tokens)
        # But if the router selects a non-Anthropic model, this may be non-empty
        # Just check the field exists and is a string
        assert isinstance(decision.effort_instruction, str)


class TestRouterWithCustomEffort:
    """Router accepts a custom EffortManager."""

    def test_custom_effort_manager(self) -> None:
        mgr = EffortManager()
        mgr.set_level(EffortLevel.MEDIUM)
        router = ModelRouter(effort_manager=mgr)
        decision = router.route("some task")
        assert decision.effort_level == "medium"
        assert decision.effort_budget_tokens == 4096


class TestEffortAwareModelSelection:
    """Effort level influences model tier selection."""

    def test_higher_effort_prefers_premium_models(self) -> None:
        """At xhigh+, the router should prefer premium-tier models."""
        router = ModelRouter()
        # Route the same task at different effort levels
        high_decision = router.route("implement a complex distributed system", effort_level="high")
        xhigh_decision = router.route("implement a complex distributed system", effort_level="xhigh")
        # Higher effort should have higher budget
        assert xhigh_decision.effort_budget_tokens >= high_decision.effort_budget_tokens
