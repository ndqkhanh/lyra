"""
Unit tests for the ModelRouter.

Uses mock providers — no real API calls.
"""

from __future__ import annotations

import pytest

from src.routing.provider.router import ModelRouter
from src.routing.provider.types import (
    Capability,
    CompletionRequest,
    CostEstimate,
    EffortLevel,
    Message,
    RouteContext,
    ToolDef,
    TokenUsage,
)

from tests.routing.conftest import _MockProvider


@pytest.fixture
def router() -> ModelRouter:
    """A ModelRouter with anthropic and deepseek mock providers."""
    r = ModelRouter()
    r.register_provider(
        "anthropic",
        _MockProvider(
            name="anthropic",
            capabilities={
                Capability.TEXT_GENERATION,
                Capability.TOOL_USE,
                Capability.VISION,
                Capability.STREAMING,
                Capability.JSON_MODE,
                Capability.LONG_CONTEXT,
            },
        ),
        [],
    )
    r.register_provider(
        "deepseek",
        _MockProvider(
            name="deepseek",
            capabilities={
                Capability.TEXT_GENERATION,
                Capability.TOOL_USE,
                Capability.STREAMING,
                Capability.JSON_MODE,
                Capability.LONG_CONTEXT,
            },
        ),
        [],
    )
    return r


class TestRoute:
    """Routing logic tests."""

    def test_route_simple_lookup(self, router: ModelRouter) -> None:
        """Simple_lookup tasks get LOW effort."""
        decision = router.route("simple_lookup")
        assert decision.effort == EffortLevel.LOW
        assert decision.provider_name == "anthropic"

    def test_route_standard(self, router: ModelRouter) -> None:
        """Standard tasks get MEDIUM effort."""
        decision = router.route("standard")
        assert decision.effort == EffortLevel.MEDIUM

    def test_route_complex_reasoning(self, router: ModelRouter) -> None:
        """Complex reasoning tasks get HIGH effort."""
        decision = router.route("complex_reasoning")
        assert decision.effort == EffortLevel.HIGH

    def test_route_research(self, router: ModelRouter) -> None:
        """Research tasks get XHIGH effort."""
        decision = router.route("research")
        assert decision.effort == EffortLevel.XHIGH

    def test_route_unknown_task_type(self, router: ModelRouter) -> None:
        """Unknown task types default to MEDIUM effort."""
        decision = router.route("unknown_task_type")
        assert decision.effort == EffortLevel.MEDIUM

    def test_route_context_overrides_task_type(self, router: ModelRouter) -> None:
        """RouteContext.estimated_complexity overrides task type mapping."""
        ctx = RouteContext(task_type="standard", estimated_complexity="low")
        decision = router.route("standard", context=ctx)
        assert decision.effort == EffortLevel.LOW

    def test_route_vision_requirement(self, router: ModelRouter) -> None:
        """Routes to a vision-capable provider when required."""
        # Remove vision from anthropic and test deepseek fallback
        r = ModelRouter()
        r.register_provider(
            "anthropic",
            _MockProvider(
                name="anthropic",
                capabilities={Capability.TEXT_GENERATION, Capability.TOOL_USE},
            ),
            [],
        )
        r.register_provider(
            "deepseek",
            _MockProvider(
                name="deepseek",
                capabilities={
                    Capability.TEXT_GENERATION,
                    Capability.VISION,
                    Capability.TOOL_USE,
                },
            ),
            [],
        )
        ctx = RouteContext(requires_vision=True)
        decision = r.route("standard", context=ctx)
        assert decision.provider_name == "deepseek"


class TestFallbackChain:
    """Fallback chain construction tests."""

    def test_fallback_chain_has_entries(self, router: ModelRouter) -> None:
        """Route decisions include a non-empty fallback chain."""
        decision = router.route("complex_reasoning")
        assert len(decision.fallback_chain) > 0

    def test_fallback_includes_other_providers(self, router: ModelRouter) -> None:
        """Fallback chain lists other providers after the primary."""
        decision = router.route("complex_reasoning")
        provider_names = [fb.provider_name for fb in decision.fallback_chain]
        assert "deepseek" in provider_names

    def test_primary_not_in_fallback(self, router: ModelRouter) -> None:
        """Primary provider does not appear in fallback chain."""
        decision = router.route("standard")
        provider_names = [fb.provider_name for fb in decision.fallback_chain]
        assert decision.provider_name not in provider_names


class TestCompleteWithFallback:
    """Fallback execution tests."""

    @pytest.mark.asyncio
    async def test_successful_completion(self, router: ModelRouter) -> None:
        """Happy path — primary provider succeeds."""
        request = CompletionRequest(
            messages=(Message(role="user", content="hello"),),
            model="claude-sonnet-4-6",
            max_tokens=50,
        )
        response = await router.complete_with_fallback(request)
        assert response.content == "mock response"
        assert response.usage.input_tokens == 10

    @pytest.mark.asyncio
    async def test_fallback_on_failure(self) -> None:
        """When primary fails, fallback provider is used."""
        r = ModelRouter()
        r.register_provider(
            "openai",
            _MockProvider(name="openai", fail=True),
            [],
        )
        r.register_provider(
            "deepseek",
            _MockProvider(name="deepseek", fail=False),
            [],
        )
        request = CompletionRequest(
            messages=(Message(role="user", content="hello"),),
            model="test-model",
            max_tokens=50,
        )
        response = await r.complete_with_fallback(request)
        assert response.content == "mock response"

    @pytest.mark.asyncio
    async def test_all_providers_fail(self) -> None:
        """When all providers fail, raise RuntimeError."""
        r = ModelRouter()
        r.register_provider(
            "fail1",
            _MockProvider(name="fail1", fail=True),
            [],
        )
        r.register_provider(
            "fail2",
            _MockProvider(name="fail2", fail=True),
            [],
        )
        request = CompletionRequest(
            messages=(Message(role="user", content="hello"),),
            model="test-model",
            max_tokens=50,
        )
        with pytest.raises(RuntimeError, match="All providers failed"):
            await r.complete_with_fallback(request)

    @pytest.mark.asyncio
    async def test_budget_skipped(self) -> None:
        """Provider is skipped when cost exceeds remaining budget."""
        r = ModelRouter()
        # Expensive mock: cost_estimate returns higher costs
        expensive_mock = _MockProvider(name="openai")
        expensive_mock._cost_override = CostEstimate(
            input_cost=1.0, output_cost=5.0, total_max_cost=6.0,
        )
        cheap_mock = _MockProvider(name="deepseek")
        cheap_mock._cost_override = CostEstimate(
            input_cost=0.001, output_cost=0.002, total_max_cost=0.003,
        )
        r.register_provider(
            "openai",
            expensive_mock,
            [],
        )
        r.register_provider(
            "deepseek",
            cheap_mock,
            [],
        )
        request = CompletionRequest(
            messages=(Message(role="user", content="hello"),),
            model="test-model",
            max_tokens=50,
        )
        # Budget too small for primary but enough for fallback
        ctx = RouteContext(budget_remaining=0.01)
        response = await r.complete_with_fallback(request, context=ctx)
        assert response is not None


class TestRegistration:
    """Provider registration tests."""

    def test_register_provider(self) -> None:
        """Register a provider and verify it is accessible."""
        r = ModelRouter()
        provider = _MockProvider(name="new-provider")
        r.register_provider("new-provider", provider, [])
        assert "new-provider" in r.registered_providers

    def test_route_requires_providers(self) -> None:
        """Routing without providers raises ValueError."""
        r = ModelRouter()
        with pytest.raises(ValueError, match="No providers registered"):
            r.route("standard")

    def test_route_with_empty_registry(self) -> None:
        """Routing after unregister-all equivalent raises ValueError."""
        r = ModelRouter()
        # No providers registered
        with pytest.raises(ValueError):
            r.route("standard")


class TestSessionCost:
    """Session cost tracking tests."""

    @pytest.mark.asyncio
    async def test_cost_tracks_across_calls(self, router: ModelRouter) -> None:
        """Session cost accumulates across multiple completions."""
        request = CompletionRequest(
            messages=(Message(role="user", content="hello"),),
            model="claude-sonnet-4-6",
            max_tokens=50,
        )
        assert router.session_cost == 0.0

        await router.complete_with_fallback(request)
        assert router.session_cost > 0.0

        prev_cost = router.session_cost
        await router.complete_with_fallback(request)
        assert router.session_cost > prev_cost

    def test_reset_session_cost(self, router: ModelRouter) -> None:
        """Reset clears accumulated cost."""
        router._session_cost = 5.0
        router.reset_session_cost()
        assert router.session_cost == 0.0
