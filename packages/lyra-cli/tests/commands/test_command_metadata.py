"""Tests for CommandMetadata."""

import pytest
from lyra_cli.core.command_metadata import CommandMetadata


def test_command_metadata_creation():
    """Test creating a CommandMetadata instance."""
    cmd = CommandMetadata(
        name="plan",
        description="Create implementation plan",
        agent="planner"
    )
    assert cmd.name == "plan"
    assert cmd.description == "Create implementation plan"
    assert cmd.agent == "planner"
    assert cmd.skill is None
    assert cmd.args == []
    assert cmd.file_path is None


def test_command_metadata_with_skill():
    """Test CommandMetadata with skill reference."""
    cmd = CommandMetadata(
        name="tdd",
        description="Test-driven development",
        agent="tdd-guide",
        skill="tdd-workflow"
    )
    assert cmd.skill == "tdd-workflow"


def test_command_metadata_with_args():
    """Test CommandMetadata with arguments."""
    cmd = CommandMetadata(
        name="verify",
        description="Run verification loop",
        args=["--coverage", "--lint"]
    )
    assert cmd.args == ["--coverage", "--lint"]
