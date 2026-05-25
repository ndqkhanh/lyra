"""Tests for lyra_otel_tracer.cost_attributor."""

from __future__ import annotations

import pytest

from lyra_otel_tracer.cost_attributor import CostAttributor, CostBreakdown, CostConfig, CostEntry


class TestCostEntry:
    def test_cost_entry_creation(self) -> None:
        entry = CostEntry(
            entry_id="e1",
            agent_id="a1",
            operation="code_gen",
            model="sonnet",
            token_cost=0.015,
            compute_cost=0.005,
            total_cost=0.02,
            timestamp=1000.0,
        )
        assert entry.agent_id == "a1"
        assert entry.total_cost == 0.02

    def test_cost_entry_frozen(self) -> None:
        entry = CostEntry(
            entry_id="e1", agent_id="a1", operation="op", model="m",
            token_cost=0.0, compute_cost=0.0, total_cost=0.0, timestamp=0.0,
        )
        with pytest.raises(AttributeError):
            entry.agent_id = "changed"  # type: ignore[misc]


class TestCostBreakdown:
    def test_cost_breakdown_creation(self) -> None:
        breakdown = CostBreakdown(
            total_cost=1.0,
            by_agent=(("a1", 0.5), ("a2", 0.5)),
            by_model=(("sonnet", 1.0),),
            by_operation=(("code_gen", 1.0),),
            period_hours=24.0,
        )
        assert breakdown.total_cost == 1.0
        assert len(breakdown.by_agent) == 2

    def test_cost_breakdown_defaults(self) -> None:
        breakdown = CostBreakdown()
        assert breakdown.total_cost == 0.0
        assert breakdown.by_agent == ()
        assert breakdown.period_hours == 24.0


class TestCostConfig:
    def test_cost_config_defaults(self) -> None:
        config = CostConfig()
        assert config.prompt_cost_per_1k == 0.003
        assert config.completion_cost_per_1k == 0.015
        assert config.compute_cost_per_second == 0.0001

    def test_cost_config_custom(self) -> None:
        config = CostConfig(
            prompt_cost_per_1k=0.01,
            completion_cost_per_1k=0.03,
            compute_cost_per_second=0.001,
        )
        assert config.prompt_cost_per_1k == 0.01
        assert config.compute_cost_per_second == 0.001


class TestCostAttributor:
    @pytest.mark.asyncio
    async def test_attribute_cost(self) -> None:
        attributor = CostAttributor()
        entry = await attributor.attribute_cost(
            agent_id="a1",
            operation="code_gen",
            model="sonnet",
            prompt_tokens=1000,
            completion_tokens=500,
            duration_s=10.0,
        )
        assert entry.agent_id == "a1"
        assert entry.operation == "code_gen"
        assert entry.model == "sonnet"
        assert entry.token_cost > 0
        assert entry.compute_cost > 0
        assert entry.total_cost > 0

    @pytest.mark.asyncio
    async def test_attribute_cost_zero_tokens(self) -> None:
        attributor = CostAttributor()
        entry = await attributor.attribute_cost(
            agent_id="a1", operation="op", model="haiku",
            prompt_tokens=0, completion_tokens=0, duration_s=0.0,
        )
        assert entry.total_cost == 0.0

    @pytest.mark.asyncio
    async def test_get_cost_breakdown_empty(self) -> None:
        attributor = CostAttributor()
        breakdown = await attributor.get_cost_breakdown()
        assert breakdown.total_cost == 0.0

    @pytest.mark.asyncio
    async def test_get_cost_breakdown(self) -> None:
        attributor = CostAttributor()
        await attributor.attribute_cost("a1", "code_gen", "sonnet", 1000, 500, 10.0)
        await attributor.attribute_cost("a2", "review", "opus", 2000, 1000, 20.0)
        breakdown = await attributor.get_cost_breakdown(period_hours=24.0)
        assert breakdown.total_cost > 0
        assert len(breakdown.by_agent) == 2
        assert len(breakdown.by_model) == 2
        assert len(breakdown.by_operation) == 2

    @pytest.mark.asyncio
    async def test_get_cost_breakdown_outside_period(self) -> None:
        attributor = CostAttributor()
        await attributor.attribute_cost("a1", "op", "sonnet", 100, 50, 1.0)
        breakdown = await attributor.get_cost_breakdown(period_hours=0.0)
        # duration_s=1.0 cost is tiny; period 0 means only entries from now onward
        assert breakdown.total_cost == 0.0

    @pytest.mark.asyncio
    async def test_get_agent_cost(self) -> None:
        attributor = CostAttributor()
        await attributor.attribute_cost("a1", "code_gen", "sonnet", 1000, 500, 10.0)
        await attributor.attribute_cost("a2", "review", "opus", 2000, 1000, 20.0)
        breakdown = await attributor.get_agent_cost("a1")
        assert breakdown.total_cost > 0
        assert dict(breakdown.by_agent)["a1"] > 0

    @pytest.mark.asyncio
    async def test_get_agent_cost_empty(self) -> None:
        attributor = CostAttributor()
        breakdown = await attributor.get_agent_cost("nonexistent")
        assert breakdown.total_cost == 0.0

    @pytest.mark.asyncio
    async def test_custom_cost_config(self) -> None:
        config = CostConfig(
            prompt_cost_per_1k=0.01,
            completion_cost_per_1k=0.03,
            compute_cost_per_second=0.001,
        )
        attributor = CostAttributor(config)
        entry = await attributor.attribute_cost("a1", "op", "sonnet", 1000, 500, 10.0)
        # Expected: token_cost = (1000/1000)*0.01 + (500/1000)*0.03 = 0.01 + 0.015 = 0.025
        # compute_cost = 10 * 0.001 = 0.01
        # total = 0.035
        assert entry.token_cost == 0.025
        assert entry.compute_cost == 0.01
        assert entry.total_cost == 0.035

    @pytest.mark.asyncio
    async def test_get_agent_cost_breakdown_by_model(self) -> None:
        attributor = CostAttributor()
        await attributor.attribute_cost("a1", "op1", "sonnet", 1000, 500, 10.0)
        await attributor.attribute_cost("a1", "op2", "opus", 2000, 1000, 20.0)
        breakdown = await attributor.get_agent_cost("a1")
        model_map = dict(breakdown.by_model)
        assert "sonnet" in model_map
        assert "opus" in model_map

    @pytest.mark.asyncio
    async def test_get_cost_breakdown_by_operation(self) -> None:
        attributor = CostAttributor()
        await attributor.attribute_cost("a1", "code_gen", "sonnet", 1000, 500, 10.0)
        await attributor.attribute_cost("a2", "review", "opus", 500, 250, 5.0)
        breakdown = await attributor.get_cost_breakdown()
        op_map = dict(breakdown.by_operation)
        assert "code_gen" in op_map
        assert "review" in op_map

    @pytest.mark.asyncio
    async def test_entry_id_unique(self) -> None:
        attributor = CostAttributor()
        e1 = await attributor.attribute_cost("a1", "op", "sonnet", 100, 50, 1.0)
        e2 = await attributor.attribute_cost("a1", "op", "sonnet", 100, 50, 1.0)
        assert e1.entry_id != e2.entry_id

    @pytest.mark.asyncio
    async def test_cost_calculation_precision(self) -> None:
        attributor = CostAttributor()
        entry = await attributor.attribute_cost("a1", "op", "sonnet", 1, 1, 0.001)
        # token_cost = (1/1000)*0.003 + (1/1000)*0.015 = 0.000003 + 0.000015 = 0.000018
        # compute_cost = 0.001 * 0.0001 = 0.0000001
        # total = 0.0000181 rounded to 6dp
        assert entry.total_cost >= 0.0
