"""Tests for agent orchestrator."""
import pytest
from pathlib import Path
from lyra_cli.core.agent_orchestrator import AgentOrchestrator, AgentResult
from lyra_cli.core.agent_registry import AgentRegistry


@pytest.fixture
def temp_agent_dir(tmp_path):
    """Create temporary agent directory with test agents."""
    agent_dir = tmp_path / "agents"
    agent_dir.mkdir()

    agent_file = agent_dir / "test-agent.md"
    agent_file.write_text("""---
name: test-agent
description: Test agent
tools: [Read, Write]
model: sonnet
origin: test
---

# Test Agent
""")

    return agent_dir


@pytest.fixture
def orchestrator(temp_agent_dir):
    """Create orchestrator with test registry."""
    registry = AgentRegistry(agent_dirs=[temp_agent_dir])
    registry.load_agents()
    return AgentOrchestrator(registry)


def test_orchestrator_initialization(orchestrator):
    """Test orchestrator initialization."""
    assert orchestrator.registry is not None


def test_delegate_existing_agent(orchestrator):
    """Test delegating to existing agent."""
    result = orchestrator.delegate("test-agent", "Test task")

    assert isinstance(result, AgentResult)
    assert result.success is True
    assert result.error is None
    assert "test-agent" in result.output


def test_delegate_nonexistent_agent(orchestrator):
    """Test delegating to nonexistent agent."""
    result = orchestrator.delegate("nonexistent", "Test task")

    assert isinstance(result, AgentResult)
    assert result.success is False
    assert result.error is not None
    assert "not found" in result.error


def test_auto_delegate(orchestrator):
    """Test auto-delegation."""
    result = orchestrator.auto_delegate("Test task")

    assert isinstance(result, AgentResult)
    assert result.success is True
