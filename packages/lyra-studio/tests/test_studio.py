"""Tests for lyra-studio."""
from lyra_studio import AgentStudio


class TestAgentStudio:
    def test_create_pipeline(self):
        s = AgentStudio()
        pipe = s.create_pipeline("Test Pipeline")
        assert pipe.name == "Test Pipeline"
        assert s.stats["pipelines"] == 1

    def test_add_node(self):
        s = AgentStudio()
        p = s.create_pipeline("P")
        n = s.add_node(p.id, "llm", "GPT-4", {"model": "gpt-4"})
        assert n is not None
        assert n.node_type == "llm"

    def test_connect_nodes(self):
        s = AgentStudio()
        p = s.create_pipeline("P")
        a = s.add_node(p.id, "input", "In")
        b = s.add_node(p.id, "llm", "LLM")
        assert s.connect(p.id, a.id, b.id, "prompt")

    def test_validate_valid(self):
        s = AgentStudio()
        p = s.create_pipeline("P")
        s.add_node(p.id, "input", "In")
        s.add_node(p.id, "llm", "LLM")
        s.add_node(p.id, "output", "Out")
        result = s.validate(p.id)
        assert result["valid"]

    def test_validate_invalid(self):
        s = AgentStudio()
        p = s.create_pipeline("P")
        result = s.validate(p.id)
        assert not result["valid"]
