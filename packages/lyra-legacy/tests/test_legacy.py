"""Tests for lyra-legacy."""
from lyra_legacy import AgentLegacy


class TestAgentLegacy:
    def test_record_achievement(self):
        l = AgentLegacy("agent_1")
        l.record_achievement("Fixed critical bug", impact=0.9)
        assert l.stats["achievements"] == 1

    def test_update_reputation(self):
        l = AgentLegacy("agent_1")
        l.update_reputation("trustworthiness", 0.3)
        assert l.reputation.trustworthiness == 0.8

    def test_preserve_knowledge(self):
        l = AgentLegacy("agent_1")
        l.preserve_knowledge("python_pattern", "Use list comprehensions")
        assert l.stats["knowledge"] == 1

    def test_retire(self):
        l = AgentLegacy("agent_1")
        l.record_achievement("Built the system")
        archive = l.retire()
        assert archive["achievements"] == 1
        assert l.stats["retired"]
