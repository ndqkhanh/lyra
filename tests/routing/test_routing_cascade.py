"""
Unit tests for CascadeRouter, DifficultyEstimator, and cost-sensitive cascade routing.

Uses mock providers — no real API calls.
"""

from __future__ import annotations

import pytest

from lyra.routing.cascade import CascadeConfig, CascadeRouter, OutcomeStats
from lyra.routing.difficulty import DifficultyEstimator, DifficultyScore
from lyra.routing.provider.types import (
    Capability,
    CompletionRequest,
    CompletionResponse,
    CostEstimate,
    EffortLevel,
    Message,
    RouteContext,
    TokenUsage,
)

from tests.routing.conftest import _MockProvider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cascade_router() -> CascadeRouter:
    """A CascadeRouter with three mock providers at different cost tiers."""
    r = CascadeRouter(
        cascade_config=CascadeConfig(
            max_budget=10.0,
            confidence_threshold=0.5,
            escalation_policy="always",
            max_cascade_depth=5,
        ),
    )

    # Cheapest provider
    cheap = _MockProvider(name="cheap-provider")
    cheap._cost_override = CostEstimate(0.001, 0.002, 0.003)

    # Mid-cost provider
    mid = _MockProvider(name="mid-provider")
    mid._cost_override = CostEstimate(0.01, 0.02, 0.03)

    # Expensive provider
    expensive = _MockProvider(name="expensive-provider")
    expensive._cost_override = CostEstimate(0.1, 0.2, 0.3)

    r.register_provider("cheap-provider", cheap, [])
    r.register_provider("mid-provider", mid, [])
    r.register_provider("expensive-provider", expensive, [])
    return r


@pytest.fixture
def sample_request() -> CompletionRequest:
    """Standard completion request for cascade tests."""
    return CompletionRequest(
        messages=(Message(role="user", content="hello"),),
        model="test-model",
        max_tokens=50,
    )


@pytest.fixture
def diffs_estimator() -> DifficultyEstimator:
    """Default DifficultyEstimator."""
    return DifficultyEstimator()


# ===========================================================================
# DifficultyEstimator tests
# ===========================================================================


class TestDifficultyEstimator:
    """Heuristic-based difficulty estimation."""

    def test_simple_task_by_type(self, diffs_estimator: DifficultyEstimator) -> None:
        """simple_lookup returns SIMPLE."""
        assert diffs_estimator.estimate("simple_lookup") == DifficultyScore.SIMPLE

    def test_moderate_task_by_type(self, diffs_estimator: DifficultyEstimator) -> None:
        """Standard and code_generation return MODERATE."""
        assert diffs_estimator.estimate("standard") == DifficultyScore.MODERATE
        assert diffs_estimator.estimate("code_generation") == DifficultyScore.MODERATE

    def test_complex_task_by_type(self, diffs_estimator: DifficultyEstimator) -> None:
        """debugging and code_review return COMPLEX."""
        assert diffs_estimator.estimate("debugging") == DifficultyScore.COMPLEX
        assert diffs_estimator.estimate("code_review") == DifficultyScore.COMPLEX

    def test_very_complex_task_by_type(
        self,
        diffs_estimator: DifficultyEstimator,
    ) -> None:
        """research and agentic return VERY_COMPLEX."""
        assert diffs_estimator.estimate("research") == DifficultyScore.VERY_COMPLEX
        assert diffs_estimator.estimate("agentic") == DifficultyScore.VERY_COMPLEX

    def test_unknown_task_defaults_to_moderate(
        self,
        diffs_estimator: DifficultyEstimator,
    ) -> None:
        """Unknown task types default to MODERATE."""
        assert diffs_estimator.estimate("unknown_type") == DifficultyScore.MODERATE

    def test_very_long_message_escalates(
        self,
        diffs_estimator: DifficultyEstimator,
    ) -> None:
        """A very long message escalates to VERY_COMPLEX."""
        # 26_000 * "word " = 130_000 chars / 4 = 32_500 tokens > 32_000
        msg = Message(role="user", content="word " * 26_000)
        score = diffs_estimator.estimate("simple_lookup", messages=(msg,))
        assert score == DifficultyScore.VERY_COMPLEX

    def test_long_message_escalates(
        self,
        diffs_estimator: DifficultyEstimator,
    ) -> None:
        """A long message escalates to COMPLEX."""
        # 7_000 * "word " = 35_000 chars / 4 = 8_750 tokens — between 8k and 32k
        msg = Message(role="user", content="word " * 7_000)
        score = diffs_estimator.estimate("simple_lookup", messages=(msg,))
        assert score == DifficultyScore.COMPLEX

    def test_complexity_keywords_escalate(
        self,
        diffs_estimator: DifficultyEstimator,
    ) -> None:
        """VERY_COMPLEX keywords in messages escalate the score."""
        msg = Message(role="user", content="I need a comprehensive research analysis")
        score = diffs_estimator.estimate("standard", messages=(msg,))
        assert score == DifficultyScore.VERY_COMPLEX

    def test_multi_step_patterns_escalate(
        self,
        diffs_estimator: DifficultyEstimator,
    ) -> None:
        """Multiple step patterns escalate to VERY_COMPLEX."""
        msg = Message(
            role="user",
            content="First do X. Then do Y. Finally do Z. Step 4 is cleanup.",
        )
        score = diffs_estimator.estimate("standard", messages=(msg,))
        assert score == DifficultyScore.VERY_COMPLEX

    def test_to_float_conversion(
        self,
        diffs_estimator: DifficultyEstimator,
    ) -> None:
        """to_float returns values in expected ranges."""
        assert diffs_estimator.to_float(DifficultyScore.SIMPLE) == 0.1
        assert diffs_estimator.to_float(DifficultyScore.MODERATE) == 0.3
        assert diffs_estimator.to_float(DifficultyScore.COMPLEX) == 0.6
        assert diffs_estimator.to_float(DifficultyScore.VERY_COMPLEX) == 0.9

    def test_from_float_conversion(
        self,
        diffs_estimator: DifficultyEstimator,
    ) -> None:
        """from_float maps to the correct enum value."""
        assert diffs_estimator.from_float(0.1) == DifficultyScore.SIMPLE
        assert diffs_estimator.from_float(0.3) == DifficultyScore.MODERATE
        assert diffs_estimator.from_float(0.6) == DifficultyScore.COMPLEX
        assert diffs_estimator.from_float(0.9) == DifficultyScore.VERY_COMPLEX


# ===========================================================================
# CascadeRouter tests
# ===========================================================================


class TestCascadeRouting:
    """Cost-sensitive cascade routing logic."""

    @pytest.mark.asyncio
    async def test_cascade_uses_cheapest_first(
        self,
        cascade_router: CascadeRouter,
        sample_request: CompletionRequest,
    ) -> None:
        """The cheapest provider is tried first."""
        response = await cascade_router.route_with_cost(sample_request)
        assert response is not None
        assert response.content == "mock response"

    @pytest.mark.asyncio
    async def test_cascade_escalates_on_failure(
        self,
        sample_request: CompletionRequest,
    ) -> None:
        """When the cheapest provider fails, escalate to the next."""
        r = CascadeRouter(
            cascade_config=CascadeConfig(max_cascade_depth=5),
        )
        failing = _MockProvider(name="fails", fail=True)
        passes = _MockProvider(name="passes", fail=False)
        failing._cost_override = CostEstimate(0.001, 0.002, 0.003)
        passes._cost_override = CostEstimate(0.01, 0.02, 0.03)

        r.register_provider("fails", failing, [])
        r.register_provider("passes", passes, [])

        response = await r.route_with_cost(sample_request, budget=10.0)
        assert response.content == "mock response"

    @pytest.mark.asyncio
    async def test_cascade_exhausts_all_candidates(
        self,
        sample_request: CompletionRequest,
    ) -> None:
        """When all candidates fail, raise RuntimeError."""
        r = CascadeRouter(
            cascade_config=CascadeConfig(max_cascade_depth=5),
        )
        a = _MockProvider(name="a", fail=True)
        b = _MockProvider(name="b", fail=True)
        a._cost_override = CostEstimate(0.001, 0.002, 0.003)
        b._cost_override = CostEstimate(0.01, 0.02, 0.03)
        r.register_provider("a", a, [])
        r.register_provider("b", b, [])

        with pytest.raises(RuntimeError, match="Cascade exhausted"):
            await r.route_with_cost(sample_request, budget=10.0)

    @pytest.mark.asyncio
    async def test_budget_skips_expensive_models(
        self,
        sample_request: CompletionRequest,
    ) -> None:
        """Models exceeding the budget are skipped."""
        r = CascadeRouter(
            cascade_config=CascadeConfig(max_budget=0.01, max_cascade_depth=5),
        )
        cheap = _MockProvider(name="cheap")
        cheap._cost_override = CostEstimate(0.001, 0.002, 0.003)
        expensive = _MockProvider(name="expensive")
        expensive._cost_override = CostEstimate(0.1, 0.2, 0.3)

        r.register_provider("cheap", cheap, [])
        r.register_provider("expensive", expensive, [])

        response = await r.route_with_cost(sample_request)
        assert response.content == "mock response"

    @pytest.mark.asyncio
    async def test_no_affordable_models_raises(
        self,
        sample_request: CompletionRequest,
    ) -> None:
        """When all models exceed the budget, raise RuntimeError."""
        r = CascadeRouter(
            cascade_config=CascadeConfig(max_budget=0.001, max_cascade_depth=5),
        )
        p = _MockProvider(name="pricey")
        p._cost_override = CostEstimate(0.5, 1.0, 1.5)
        r.register_provider("pricey", p, [])

        with pytest.raises(RuntimeError, match="No affordable models"):
            await r.route_with_cost(sample_request, budget=0.001)

    @pytest.mark.asyncio
    async def test_cascade_depth_limits_attempts(
        self,
        sample_request: CompletionRequest,
    ) -> None:
        """max_cascade_depth limits the number of attempts."""
        r = CascadeRouter(
            cascade_config=CascadeConfig(max_budget=10.0, max_cascade_depth=1),
        )
        a = _MockProvider(name="a", fail=True)
        b = _MockProvider(name="b", fail=False)
        a._cost_override = CostEstimate(0.001, 0.002, 0.003)
        b._cost_override = CostEstimate(0.01, 0.02, 0.03)
        r.register_provider("a", a, [])
        r.register_provider("b", b, [])

        with pytest.raises(RuntimeError):
            await r.route_with_cost(sample_request, budget=10.0)


class TestCascadeDifficultyPolicy:
    """Difficulty-based escalation policy."""

    @pytest.mark.asyncio
    async def test_difficulty_policy_skips_first_tiers_for_hard_tasks(
        self,
        sample_request: CompletionRequest,
    ) -> None:
        """With difficulty policy, hard tasks skip the cheapest models."""
        r = CascadeRouter(
            cascade_config=CascadeConfig(
                max_budget=10.0,
                escalation_policy="difficulty",
                max_cascade_depth=5,
            ),
        )

        cheated = _MockProvider(name="cheated-fail", fail=True)
        cheated._cost_override = CostEstimate(0.001, 0.002, 0.003)
        passed = _MockProvider(name="passed")
        passed._cost_override = CostEstimate(0.1, 0.2, 0.3)

        r.register_provider("cheated-fail", cheated, [])
        r.register_provider("passed", passed, [])

        # Very complex task should jump past the cheap model
        request = CompletionRequest(
            messages=(
                Message(
                    role="user",
                    content="Conduct a thorough research investigation into this topic",
                ),
            ),
            model="test-model",
            max_tokens=50,
        )

        response = await r.route_with_cost(request, budget=10.0)
        assert response.content == "mock response"


class TestOutcomeRecording:
    """Outcome statistics tracking."""

    @pytest.mark.asyncio
    async def test_records_success_outcome(
        self,
        cascade_router: CascadeRouter,
        sample_request: CompletionRequest,
    ) -> None:
        """Successful completions are recorded in outcome stats."""
        await cascade_router.route_with_cost(sample_request)
        stats = cascade_router.get_model_stats()
        assert len(stats) > 0
        # At least one model key should have a successful outcome
        successes = [s for s in stats.values() if s.success_count > 0]
        assert len(successes) > 0

    @pytest.mark.asyncio
    async def test_records_failure_outcome(self) -> None:
        """Failed completions update failure counts."""
        r = CascadeRouter(
            cascade_config=CascadeConfig(max_cascade_depth=3),
        )
        fail = _MockProvider(name="fail-all", fail=True)
        fail._cost_override = CostEstimate(0.001, 0.002, 0.003)
        r.register_provider("fail-all", fail, [])

        request = CompletionRequest(
            messages=(Message(role="user", content="hello"),),
            model="test-model",
            max_tokens=50,
        )
        with pytest.raises(RuntimeError):
            await r.route_with_cost(request, budget=10.0)

        stats = r.get_model_stats()
        # There should be at least one entry with failures
        any_failures = any(s.failure_count > 0 for s in stats.values())
        assert any_failures

    def test_outcome_stats_calculations(self) -> None:
        """OutcomeStats computed properties are correct."""
        stats = OutcomeStats(success_count=8, failure_count=2, total_latency_ms=500.0)
        assert stats.total_calls == 10
        assert stats.success_rate == 0.8
        assert stats.avg_latency_ms == 50.0

    def test_empty_outcome_stats(self) -> None:
        """OutcomeStats with no calls returns zero rates."""
        stats = OutcomeStats()
        assert stats.total_calls == 0
        assert stats.success_rate == 0.0
        assert stats.avg_latency_ms == 0.0

    def test_manual_record_outcome(self, cascade_router: CascadeRouter) -> None:
        """record_outcome manually updates stats without routing."""
        cascade_router.record_outcome(
            model="anthropic/claude-sonnet-4-6",
            task_type="standard",
            success=True,
            latency=100.0,
        )
        cascade_router.record_outcome(
            model="anthropic/claude-sonnet-4-6",
            task_type="standard",
            success=False,
            latency=0.0,
        )
        stats = cascade_router.get_model_stats()
        key = "anthropic/claude-sonnet-4-6"
        assert key in stats
        assert stats[key].success_count == 1
        assert stats[key].failure_count == 1
        assert stats[key].success_rate == 0.5

    @pytest.mark.asyncio
    async def test_outcome_records_improve_routing(
        self,
        sample_request: CompletionRequest,
    ) -> None:
        """Multiple failures on a model correctly update its stats."""
        r = CascadeRouter(
            cascade_config=CascadeConfig(max_cascade_depth=5),
        )
        flaky = _MockProvider(name="flaky", fail=True)
        ok = _MockProvider(name="ok", fail=False)
        flaky._cost_override = CostEstimate(0.001, 0.002, 0.003)
        ok._cost_override = CostEstimate(0.01, 0.02, 0.03)

        r.register_provider("flaky", flaky, [])
        r.register_provider("ok", ok, [])

        # First call — flaky fails, ok succeeds
        response = await r.route_with_cost(sample_request, budget=10.0)
        assert response is not None

        stats = r.get_model_stats()
        assert len(stats) > 0


class TestDifficultyEstimation:
    """Difficulty estimation on CascadeRouter."""

    def test_estimate_difficulty_simple(
        self,
        cascade_router: CascadeRouter,
    ) -> None:
        """simple_lookup returns a low difficulty score."""
        score = cascade_router.estimate_difficulty("simple_lookup")
        assert 0.0 <= score <= 0.2

    def test_estimate_difficulty_research(
        self,
        cascade_router: CascadeRouter,
    ) -> None:
        """research returns a high difficulty score."""
        score = cascade_router.estimate_difficulty("research")
        assert score > 0.5

    def test_estimate_difficulty_with_messages(
        self,
        cascade_router: CascadeRouter,
    ) -> None:
        """Messages can escalate difficulty."""
        messages = (
            Message(
                role="user",
                content="I need a comprehensive research analysis of the literature",
            ),
        )
        score = cascade_router.estimate_difficulty("standard", messages)
        assert score >= 0.6


class TestCascadeConfig:
    """CascadeConfig defaults and construction."""

    def test_default_config(self) -> None:
        """CascadeConfig has sensible defaults."""
        cfg = CascadeConfig()
        assert cfg.max_budget == 10.0
        assert cfg.confidence_threshold == 0.7
        assert cfg.escalation_policy == "always"
        assert cfg.max_cascade_depth == 3
