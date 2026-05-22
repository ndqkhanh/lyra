"""Tests for lyra-abstract."""
from lyra_abstract import AbstractReasoningAgent
class TestAbstractReasoning:
    def test_induce_rule(self):
        a = AbstractReasoningAgent(); p = a.induce_rule(["apple fruit", "apple pie", "apple juice"])
        assert p is not None
    def test_empty(self):
        a = AbstractReasoningAgent()
        assert a.induce_rule([]) is None
