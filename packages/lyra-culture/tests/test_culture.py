"""Tests for lyra-culture."""
from lyra_culture import AgentCulture


class TestAgentCulture:
    def test_establish_norm(self):
        c = AgentCulture()
        norm = c.establish_norm("review_before_merge", "Always review code before merging")
        assert norm.name == "review_before_merge"
        assert c.stats["active_norms"] == 1

    def test_detect_violation(self):
        c = AgentCulture()
        c.establish_norm("test_before_deploy", "Run tests before deploying")
        c.detect_violation("agent_1", "test_before_deploy", "deployed without testing")
        assert c.stats["total_violations"] == 1

    def test_enforce_norm(self):
        c = AgentCulture()
        c.establish_norm("document_changes", "Document all changes")
        c.enforce_norm("document_changes")
        assert c.norms["document_changes"].adherence > 0.5

    def test_evolve_culture(self):
        c = AgentCulture()
        c.establish_norm("old_norm", "This will dissolve")
        c.norms["old_norm"].adherence = 0.1
        evolved = c.evolve_culture([{"pattern": "new_workflow", "description": "New way of working"}])
        assert len(evolved) >= 1
        assert "old_norm" not in c.norms
