"""Tests for AEVO core."""

import pytest

from lyra_cli.aevo import AEVOLoop, EvolutionConfig, MetaAgent, ProtectedHarness


def test_protected_harness_budget():
    """Harness tracks budget correctly."""
    config = EvolutionConfig(budget_usd=100.0)
    harness = ProtectedHarness(config)

    assert harness.can_afford(50.0)
    harness.deduct_cost(50.0)
    assert harness.budget_remaining == 50.0


def test_protected_harness_insufficient_budget():
    """Harness prevents overspending."""
    config = EvolutionConfig(budget_usd=10.0)
    harness = ProtectedHarness(config)

    with pytest.raises(ValueError):
        harness.deduct_cost(20.0)


@pytest.mark.anyio
async def test_meta_agent_propose_edit():
    """Meta-agent proposes edits."""
    meta = MetaAgent()
    observation = {"round": 1}
    evolver = {"population_size": 20}

    edit = await meta.propose_edit(observation, evolver)

    assert "type" in edit
    assert "rationale" in edit


def test_meta_agent_apply_edit():
    """Meta-agent applies edits."""
    meta = MetaAgent()
    evolver = {"population_size": 20}
    edit = {"type": "config", "target": "population_size", "value": 25}

    new_evolver = meta.apply_edit(evolver, edit)

    assert new_evolver["population_size"] == 25
    assert evolver["population_size"] == 20  # Original unchanged


@pytest.mark.anyio
async def test_aevo_loop_run_round():
    """AEVO loop runs complete round."""
    config = EvolutionConfig()
    harness = ProtectedHarness(config)
    meta = MetaAgent()
    loop = AEVOLoop(harness, meta)

    evolver = {"population_size": 20}
    result = await loop.run_round(evolver)

    assert result["round"] == 1
    assert "evolver" in result
    assert "best_candidate" in result
    assert "edit" in result
