"""Tests for agent metadata."""
import pytest
from lyra_cli.core.agent_metadata import AgentMetadata


def test_agent_metadata_creation():
    """Test creating agent metadata."""
    agent = AgentMetadata(
        name="test-agent",
        description="Test agent description",
        tools=["Read", "Write"],
        model="sonnet",
        origin="ECC"
    )

    assert agent.name == "test-agent"
    assert agent.description == "Test agent description"
    assert agent.tools == ["Read", "Write"]
    assert agent.model == "sonnet"
    assert agent.origin == "ECC"
    assert agent.file_path is None


def test_agent_metadata_with_file_path():
    """Test agent metadata with file path."""
    agent = AgentMetadata(
        name="test-agent",
        description="Test description",
        tools=["Read"],
        model="haiku",
        origin="lyra",
        file_path="/path/to/agent.md"
    )

    assert agent.file_path == "/path/to/agent.md"
