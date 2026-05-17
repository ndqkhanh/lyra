"""Tests for CommandRegistry."""

import pytest
from pathlib import Path
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

Creates an implementation plan for a feature or task.
""")

    # Create tdd.md
    tdd_md = commands_dir / "tdd.md"
    tdd_md.write_text("""---
name: tdd
description: Test-driven development
agent: tdd-guide
skill: tdd-workflow
---

# /tdd Command

Guides test-driven development workflow.
""")

    return commands_dir


def test_load_commands(commands_dir):
    """Test loading commands from directory."""
    registry = CommandRegistry([commands_dir])
    registry.load_commands()

    assert len(registry._commands) == 2
    assert "plan" in registry._commands
    assert "tdd" in registry._commands


def test_get_command(commands_dir):
    """Test getting a command by name."""
    registry = CommandRegistry([commands_dir])
    registry.load_commands()

    cmd = registry.get_command("plan")
    assert cmd is not None
    assert cmd.name == "plan"
    assert cmd.agent == "planner"


def test_get_nonexistent_command(commands_dir):
    """Test getting a command that doesn't exist."""
    registry = CommandRegistry([commands_dir])
    registry.load_commands()

    cmd = registry.get_command("nonexistent")
    assert cmd is None


def test_search_commands(commands_dir):
    """Test searching commands."""
    registry = CommandRegistry([commands_dir])
    registry.load_commands()

    results = registry.search_commands("test")
    assert len(results) == 1
    assert results[0].name == "tdd"


def test_list_commands(commands_dir):
    """Test listing all commands."""
    registry = CommandRegistry([commands_dir])
    registry.load_commands()

    commands = registry.list_commands()
    assert len(commands) == 2
    assert any(c.name == "plan" for c in commands)
    assert any(c.name == "tdd" for c in commands)
