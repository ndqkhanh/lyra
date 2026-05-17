"""Tests for CommandDispatcher."""

import pytest
from pathlib import Path
from lyra_cli.core.command_dispatcher import CommandDispatcher, CommandResult
from lyra_cli.core.command_registry import CommandRegistry


@pytest.fixture
def commands_dir(tmp_path):
    """Create a temporary commands directory with test commands."""
    commands_dir = tmp_path / "commands"
    commands_dir.mkdir()

    # Create plan.md
    plan_md = commands_dir / "plan.md"
    plan_md.write_text("""---
name: plan
description: Create implementation plan
agent: planner
---

# /plan Command

Creates an implementation plan.
""")

    return commands_dir


@pytest.fixture
def dispatcher(commands_dir):
    """Create a CommandDispatcher with loaded commands."""
    registry = CommandRegistry([commands_dir])
    registry.load_commands()
    return CommandDispatcher(registry)


def test_dispatch_existing_command(dispatcher):
    """Test dispatching an existing command."""
    result = dispatcher.dispatch("plan")

    assert isinstance(result, CommandResult)
    assert result.success is True
    assert "plan" in result.output


def test_dispatch_nonexistent_command(dispatcher):
    """Test dispatching a command that doesn't exist."""
    result = dispatcher.dispatch("nonexistent")

    assert isinstance(result, CommandResult)
    assert result.success is False
    assert "not found" in result.error


def test_dispatch_with_args(dispatcher):
    """Test dispatching command with arguments."""
    result = dispatcher.dispatch("plan", {"feature": "auth"})

    assert isinstance(result, CommandResult)
    assert result.success is True
