"""Tests for lyra-explain."""
from lyra_explain import ExplanationEngine


class TestExplanationEngine:
    def test_explain(self):
        ee = ExplanationEngine()
        exp = ee.explain({"action": "write_file", "context": "writing code", "score": 0.9, "alternatives": ["read", "delete"]})
        assert exp.decision_id.startswith("dec_")
        assert len(exp.reasoning_steps) == 3
        assert exp.confidence == 0.9

    def test_counterfactual(self):
        ee = ExplanationEngine()
        cf = ee.counterfactual({"action": "write", "score": 0.8}, "delete")
        assert cf.alternative_action == "delete"
        assert cf.delta != 0

    def test_confidence_breakdown(self):
        ee = ExplanationEngine()
        breakdown = ee.confidence_breakdown({})
        assert len(breakdown) == 4
