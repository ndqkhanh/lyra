"""Tests for lyra-beliefs."""
from lyra_beliefs import BeliefSystem, BeliefSource


class TestBeliefSystem:
    def test_encode_expert(self):
        b = BeliefSystem()
        belief = b.encode_expert("python", "Prefer list comprehensions over map()")
        assert belief.id == "belief_1"
        assert belief.domain == "python"
        assert belief.source == BeliefSource.EXPERT_ENCODED

    def test_extract(self):
        b = BeliefSystem()
        belief = b.extract("APIs should have consistent error formats", ["trace_1", "trace_2"])
        assert belief.domain == "api_design"
        assert belief.source == BeliefSource.EXTRACTED

    def test_query(self):
        b = BeliefSystem()
        b.encode_expert("security", "Never log credentials")
        b.encode_expert("python", "Use type hints")
        results = b.query("Write a Python API")
        assert len(results) >= 1

    def test_verify_expert(self):
        b = BeliefSystem()
        bel = b.encode_expert("test", "Expert knowledge is always true")
        assert b.verify(bel.id)
