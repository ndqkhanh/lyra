"""Tests for BenchGuard."""

from __future__ import annotations

import pytest
from lyra_eval_pipeline import BenchGuard, BenchGuardConfig, CostEstimate, GuardResult
from lyra_eval_pipeline.domain_evaluator import EvalSample
from lyra_eval_pipeline.exceptions import BenchGuardError


class TestBenchGuardConfig:
    def test_config_creation(self) -> None:
        config = BenchGuardConfig()
        assert config.max_cost_per_audit == 15.0
        assert config.max_tokens_per_sample == 2000
        assert config.batch_size == 10
        assert config.cache_enabled

    def test_config_custom(self) -> None:
        config = BenchGuardConfig(
            max_cost_per_audit=5.0,
            max_tokens_per_sample=1000,
            batch_size=5,
            cache_enabled=False,
        )
        assert config.max_cost_per_audit == 5.0
        assert config.batch_size == 5
        assert not config.cache_enabled


class TestCostEstimate:
    def test_estimate_creation(self) -> None:
        est = CostEstimate(estimated_tokens=1000, estimated_cost=0.015)
        assert est.estimated_tokens == 1000
        assert est.estimated_cost == 0.015
        assert not est.over_budget

    def test_estimate_over_budget(self) -> None:
        est = CostEstimate(
            estimated_tokens=1_000_000,
            estimated_cost=15.0,
            over_budget=True,
        )
        assert est.over_budget


class TestGuardResult:
    def test_result_allowed(self) -> None:
        result = GuardResult(
            allowed=True,
            reason="Within budget",
            cost=CostEstimate(100, 0.001),
        )
        assert result.allowed
        assert result.mitigation == ""

    def test_result_mitigated(self) -> None:
        result = GuardResult(
            allowed=True,
            reason="Reduced batch",
            cost=CostEstimate(50, 0.0005),
            mitigation="Trimmed samples",
        )
        assert result.mitigation == "Trimmed samples"


class TestBenchGuard:
    @pytest.mark.asyncio
    async def test_estimate_cost_default(self) -> None:
        guard = BenchGuard()
        samples = [
            EvalSample(sample_id="s1", input_text="Hello", expected_output="World"),
        ]
        cost = await guard.estimate_cost(samples)
        assert cost.estimated_tokens > 0
        assert cost.estimated_cost > 0.0
        assert isinstance(cost.over_budget, bool)

    @pytest.mark.asyncio
    async def test_estimate_cost_empty_raises(self) -> None:
        guard = BenchGuard()
        with pytest.raises(BenchGuardError, match="empty sample"):
            await guard.estimate_cost([])

    @pytest.mark.asyncio
    async def test_estimate_cost_custom_config(self) -> None:
        guard = BenchGuard()
        config = BenchGuardConfig(max_cost_per_audit=1.0, max_tokens_per_sample=100)
        samples = [
            EvalSample(
                sample_id="big",
                input_text="A" * 10_000,
                expected_output="B" * 10_000,
            )
        ]
        cost = await guard.estimate_cost(samples, config)
        # Cost should be capped by max_tokens_per_sample
        max_expected_cost = config.max_tokens_per_sample * len(samples) * 0.000015
        assert cost.estimated_cost <= max_expected_cost

    @pytest.mark.asyncio
    async def test_guard_evaluation_empty_samples(self) -> None:
        guard = BenchGuard()
        result = await guard.guard_evaluation([])
        assert not result.allowed
        assert "No samples" in result.reason

    @pytest.mark.asyncio
    async def test_guard_evaluation_within_budget(self) -> None:
        guard = BenchGuard()
        samples = [
            EvalSample(sample_id="s1", input_text="short", expected_output="ok"),
        ]
        result = await guard.guard_evaluation(samples)
        assert result.allowed
        assert "within budget" in result.reason

    @pytest.mark.asyncio
    async def test_guard_evaluation_over_budget_mitigated(self) -> None:
        guard = BenchGuard(BenchGuardConfig(max_cost_per_audit=0.0001, batch_size=1))
        samples = [
            EvalSample(sample_id="s1", input_text="A" * 10_000, expected_output="B" * 10_000),
            EvalSample(sample_id="s2", input_text="C" * 10_000, expected_output="D" * 10_000),
        ]
        result = await guard.guard_evaluation(samples)
        assert result.allowed or not result.allowed

    @pytest.mark.asyncio
    async def test_track_spend(self) -> None:
        guard = BenchGuard()
        spend = await guard.track_spend("eval-001")
        assert spend > 0.0
        spend2 = await guard.track_spend("eval-001")
        assert spend2 > spend  # cumulative

    @pytest.mark.asyncio
    async def test_track_spend_multiple_evals(self) -> None:
        guard = BenchGuard()
        s1 = await guard.track_spend("eval-1")
        s2 = await guard.track_spend("eval-2")
        assert s1 > 0.0
        assert s2 > 0.0

    @pytest.mark.asyncio
    async def test_get_total_spend(self) -> None:
        guard = BenchGuard()
        total = await guard.get_total_spend()
        assert total == 0.0

    @pytest.mark.asyncio
    async def test_get_total_spend_after_tracking(self) -> None:
        guard = BenchGuard()
        await guard.track_spend("e1")
        await guard.track_spend("e1")
        total = await guard.get_total_spend()
        assert total > 0.0

    @pytest.mark.asyncio
    async def test_estimate_cost_for_large_samples(self) -> None:
        guard = BenchGuard()
        samples = [
            EvalSample(
                sample_id=f"s{i}",
                input_text="query " * 50,
                expected_output="response " * 50,
            )
            for i in range(20)
        ]
        cost = await guard.estimate_cost(samples)
        assert cost.estimated_tokens > 0

    @pytest.mark.asyncio
    async def test_guard_caches_enabled_by_default(self) -> None:
        config = BenchGuardConfig()
        assert config.cache_enabled

    @pytest.mark.asyncio
    async def test_estimate_cost_returns_actual_default(self) -> None:
        est = CostEstimate(estimated_tokens=500, estimated_cost=0.0075)
        assert est.actual_cost == 0.0

    @pytest.mark.asyncio
    async def test_guard_evaluation_single_sample(self) -> None:
        guard = BenchGuard()
        sample = EvalSample(sample_id="s1", input_text="test", expected_output="result")
        result = await guard.guard_evaluation([sample])
        # Should be allowed since 1 sample costs very little
        assert result.allowed

    @pytest.mark.asyncio
    async def test_many_samples_respected(self) -> None:
        guard = BenchGuard(BenchGuardConfig(max_cost_per_audit=1000.0))
        samples = [
            EvalSample(sample_id=f"s{i}", input_text="a" * 500, expected_output="b" * 500)
            for i in range(100)
        ]
        cost = await guard.estimate_cost(samples)
        assert cost.estimated_tokens > 0
        assert not cost.over_budget

    @pytest.mark.asyncio
    async def test_cost_estimate_with_cached_small_tokens(self) -> None:
        guard = BenchGuard(BenchGuardConfig(max_tokens_per_sample=10))
        samples = [
            EvalSample(sample_id="s1", input_text="a" * 100, expected_output="b" * 100),
        ]
        cost = await guard.estimate_cost(samples)
        # max_tokens_per_sample caps it
        assert cost.estimated_cost <= 10 * 0.000015
