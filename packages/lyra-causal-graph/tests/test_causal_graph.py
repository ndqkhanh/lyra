"""Tests for Causal Graph package."""

import pytest
import numpy as np
from lyra_causal_graph import CausalGraph, EntityNode, ActionEdge, OutcomeNode, LatentVariable


class TestCausalGraph:
    def test_add_entity(self):
        g = CausalGraph()
        n = EntityNode(id="e1", name="file.py", entity_type="file")
        g.add_entity(n)
        assert len(g.entities) == 1
        assert g.entities["e1"].name == "file.py"

    def test_add_action_and_outcome(self):
        g = CausalGraph()
        g.add_entity(EntityNode(id="e1", name="tool_x", entity_type="tool"))
        g.add_entity(EntityNode(id="e2", name="file_y", entity_type="file"))
        a = ActionEdge(id="a1", source_id="e1", target_id="e2", action_type="write", timestamp=1.0)
        g.add_action(a)
        o = OutcomeNode(id="o1", result="success", success=True, latency=0.5)
        g.add_outcome(o)
        a.outcome_id = "o1"
        assert g.stats["actions"] == 1
        assert g.stats["outcomes"] == 1

    def test_query_entity(self):
        g = CausalGraph()
        g.add_entity(EntityNode(id="e1", name="test", entity_type="concept"))
        assert g.query_entity("e1") is not None
        assert g.query_entity("nonexistent") is None

    def test_li_cte_no_data(self):
        g = CausalGraph()
        te = g.compute_li_cte("src", "tgt")
        assert te == 0.0

    def test_explain_nonexistent(self):
        g = CausalGraph()
        result = g.explain("no_such_outcome")
        assert "error" in result
