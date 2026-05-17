"""Tests for agent registry."""
import pytest
from pathlib import Path
from lyra_cli.core.agent_registry import AgentRegistry
from lyra_cli.core.agent_metadata import AgentMetadata


@pytest.fixture
def temp_agent_dir(tmp_path):
    """Create temporary agent directory with test agents."""
    agent_dir = tmp_path / "agents"
    agent_dir.mkdir()

    # Create test agent file
    agent_file = agent_dir / "test-agent.md"
    agent_file.write_text("""---
name: test-agent
description: Test agent for testing
tools: [Read, Write]
model: sonnet
origin: test
---

# Test Agent

This is a test agent.
""")

    return agent_dir


def test_agent_registry_initialization():
    """Test agent registry initialization."""
    registry = AgentRegistry()
    assert registry.agent_dirs == []
    assert registry._agents == {}


def test_agent_registry_with_dirs():
    """Test agent registry with directories."""
    dirs = [Path("/path/to/agents")]
    registry = AgentRegistry(agent_dirs=dirs)
    assert registry.agent_dirs == dirs


def test_load_agents(temp_agent_dir):
    """Test loading agents from directory."""
    registry = AgentRegistry(agent_dirs=[temp_agent_dir])
    agents = registry.load_agents()

    assert len(agents) == 1
    assert "test-agent" in agents

    agent = agents["test-agent"]
    assert agent.name == "test-agent"
    assert agent.description == "Test agent for testing"
    assert agent.tools == ["Read", "Write"]
    assert agent.model == "sonnet"
    assert agent.origin == "test"


def test_get_agent(temp_agent_dir):
    """Test getting agent by name."""
    registry = AgentRegistry(agent_dirs=[temp_agent_dir])
    registry.load_agents()

    agent = registry.get_agent("test-agent")
    assert agent is not None
    assert agent.name == "test-agent"

    missing = registry.get_agent("nonexistent")
    assert missing is None


def test_search_agents(temp_agent_dir):
    """Test searching agents."""
    registry = AgentRegistry(agent_dirs=[temp_agent_dir])
    registry.load_agents()

    results = registry.search_agents("test")
    assert len(results) == 1
    assert results[0].name == "test-agent"

    results = registry.search_agents("testing")
    assert len(results) == 1

    results = registry.search_agents("nonexistent")
    assert len(results) == 0


def test_list_agents(temp_agent_dir):
    """Test listing all agents."""
    registry = AgentRegistry(agent_dirs=[temp_agent_dir])
    registry.load_agents()

    agents = registry.list_agents()
    assert len(agents) == 1
    assert agents[0].name == "test-agent"
