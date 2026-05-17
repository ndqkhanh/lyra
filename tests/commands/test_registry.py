"""Tests for command registry."""

import pytest

from lyra_cli.commands.registry import CommandRegistry, command


async def mock_handler(args: str, context: dict) -> str:
    """Mock command handler."""
    return f"Executed with {args}"


def test_register_command():
    """Commands can be registered."""
    registry = CommandRegistry()
    registry.register("test", mock_handler, "Test command")

    cmd = registry.get("test")
    assert cmd is not None
    assert cmd.name == "test"
    assert cmd.description == "Test command"


@pytest.mark.anyio
async def test_execute_command():
    """Commands can be executed."""
    registry = CommandRegistry()
    registry.register("test", mock_handler, "Test command")

    result = await registry.execute("test", "arg1", {})

    assert result["success"] is True
    assert "Executed with arg1" in result["output"]


@pytest.mark.anyio
async def test_execute_unknown_command():
    """Unknown commands raise KeyError."""
    registry = CommandRegistry()

    with pytest.raises(KeyError):
        await registry.execute("unknown", "", {})


def test_list_commands():
    """All commands can be listed."""
    registry = CommandRegistry()
    registry.register("cmd1", mock_handler, "Command 1")
    registry.register("cmd2", mock_handler, "Command 2")

    commands = registry.list_commands()
    assert len(commands) == 2


def test_command_decorator():
    """Command decorator adds metadata."""

    @command("test", "Test command")
    async def test_cmd(args: str, context: dict) -> str:
        return "result"

    assert hasattr(test_cmd, "_command_metadata")
    assert test_cmd._command_metadata["name"] == "test"
