"""Tests for Counterfactual package."""

import asyncio
from lyra_counterfactual import CounterfactualEngine, Intervention
from lyra_causal_graph import CausalGraph, EntityNode, ActionEdge, OutcomeNode


def _make_engine():
    g = CausalGraph()
    g.add_entity(EntityNode(id="tool", name="git", entity_type="tool"))
    g.add_entity(EntityNode(id="file", name="main.py", entity_type="file"))
    a = ActionEdge(id="a1", source_id="tool", target_id="file", action_type="execute", timestamp=1.0)
    g.add_action(a)
    g.add_outcome(OutcomeNode(id="o1", result="success", success=True, latency=0.3))
    a.outcome_id = "o1"
    return CounterfactualEngine(g)


class TestCounterfactualEngine:
    def test_simulate(self):
        engine = _make_engine()
        intervention = Intervention(action_type="execute", source_id="tool", target_id="file")
        result = asyncio.run(engine.simulate(intervention))
        assert result.predicted_outcome is not None
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.causal_path, list)

    def test_simulate_unknown(self):
        engine = _make_engine()
        intervention = Intervention(action_type="read", source_id="unknown", target_id="unknown")
        result = asyncio.run(engine.simulate(intervention))
        assert result.causal_path is not None
