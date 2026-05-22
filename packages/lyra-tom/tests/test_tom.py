"""Tests for lyra-tom."""
from lyra_tom import TheoryOfMind
class TestTheoryOfMind:
    def test_register_and_teach(self):
        t = TheoryOfMind(); t.register("agent_1")
        assert not t.knows("agent_1", "secret")
        t.teach("agent_1", "secret")
        assert t.knows("agent_1", "secret")
