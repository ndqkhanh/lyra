"""Tests for the 4-tier model cascade executor."""
import pytest
from lyra_model_router import (
    Budget,
    IntelligentModelRouter,
    ModelProvider,
    ModelSpec,
    ModelTier,
    RoutingStrategy,
)

from lyra_cli.tui_gateway.cascade_executor import (
    CascadeResult,
    CostRecord,
    ModelCascadeExecutor,
)


class TestCascadeExecutor:
    def test_initial_state(self):
        ex = ModelCascadeExecutor()
        assert ex.strategy == RoutingStrategy.COST_OPTIMAL
        assert isinstance(ex.router, IntelligentModelRouter)
        assert ex.cost_summary()["total_calls"] == 0

    def test_strategy_switch(self):
        ex = ModelCascadeExecutor()
        ex.strategy = RoutingStrategy.PERFORMANCE_MAX
        assert ex.strategy == RoutingStrategy.PERFORMANCE_MAX

    def test_execute_success_first_tier(self):
        ex = ModelCascadeExecutor()

        def fake_exec(model: str, prompt: str) -> str:
            return f"Response from {model}"

        result = ex.execute("test prompt", exec_fn=fake_exec, complexity=0.2)
        assert result.content == f"Response from {result.model_used}"
        assert result.attempts == 1
        assert not result.escalated
        assert result.total_cost_usd > 0
        assert result.total_latency_ms >= 0

    def test_execute_escalation_on_failure(self):
        ex = ModelCascadeExecutor()
        call_order: list[str] = []

        def fake_exec(model: str, prompt: str) -> str:
            call_order.append(model)
            if len(call_order) < 2:
                raise RuntimeError("simulated failure")
            return f"Response from {model}"

        result = ex.execute("test prompt", exec_fn=fake_exec)
        assert result.attempts == 2
        assert result.escalated
        assert len(call_order) == 2
        assert call_order[0] != call_order[1]

    def test_execute_all_tiers_fail(self):
        ex = ModelCascadeExecutor()

        def fake_exec(model: str, prompt: str) -> str:
            raise RuntimeError("always fails")

        with pytest.raises(RuntimeError, match="All .* cascade tiers failed"):
            ex.execute("test prompt", exec_fn=fake_exec, max_escalations=1)

    def test_cost_tracking(self):
        ex = ModelCascadeExecutor()

        def fake_exec(model: str, prompt: str) -> str:
            return "ok"

        ex.execute("test prompt", exec_fn=fake_exec)
        summary = ex.cost_summary()
        assert summary["total_calls"] == 1
        assert summary["total_cost_usd"] > 0
        assert len(summary["by_model"]) == 1

    def test_snapshot(self):
        ex = ModelCascadeExecutor()

        def fake_exec(model: str, prompt: str) -> str:
            return "ok"

        ex.execute("test prompt", exec_fn=fake_exec)
        snap = ex.snapshot()
        assert snap["strategy"] == "cost_optimal"
        assert "router" in snap
        assert "costs" in snap

    def test_custom_router(self):
        router = IntelligentModelRouter()
        ex = ModelCascadeExecutor(router=router)
        assert ex.router is router

    def test_budget_constrained(self):
        ex = ModelCascadeExecutor()
        budget = Budget(max_cost=0.001, max_tokens=1000)

        def fake_exec(model: str, prompt: str) -> str:
            return "ok"

        result = ex.execute("test", exec_fn=fake_exec, budget=budget)
        assert result.content == "ok"

    def test_cascade_result_dataclass(self):
        r = CascadeResult(
            model_used="claude-haiku-4.5",
            provider="anthropic",
            tier="fast",
            content="test response",
            attempts=1,
            total_cost_usd=0.0005,
            total_latency_ms=50.0,
            escalated=False,
        )
        assert r.model_used == "claude-haiku-4.5"
        assert not r.escalated

    def test_cost_record_accumulation(self):
        spec = ModelSpec(
            name="test-model",
            provider=ModelProvider.ANTHROPIC,
            tier=ModelTier.FAST,
            cost_per_1k_tokens=0.001,
            latency_ms=100.0,
            accuracy_estimate=0.80,
        )
        rec = CostRecord(model=spec.name, provider=spec.provider.value)
        rec.call_count += 1
        rec.total_cost += 0.005
        rec.total_latency_ms += 100.0
        assert rec.call_count == 1
        assert rec.total_cost == 0.005
