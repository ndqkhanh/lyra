"""Tests for tool registry."""

import pytest

from lyra_cli.eager_tools.registry import ToolRegistry, tool


async def read_file(path: str) -> str:
    """Mock read file tool."""
    return f"contents of {path}"


async def write_file(path: str, content: str) -> None:
    """Mock write file tool."""
    pass


def test_register_tool():
    """Tools can be registered."""
    registry = ToolRegistry()
    registry.register("read_file", read_file, idempotent=True)

    tool_meta = registry.get("read_file")
    assert tool_meta is not None
    assert tool_meta.name == "read_file"
    assert tool_meta.idempotent is True


def test_default_not_idempotent():
    """Default is not idempotent (safe default)."""
    registry = ToolRegistry()
    registry.register("write_file", write_file)

    assert registry.is_idempotent("write_file") is False


def test_is_idempotent():
    """Check if tool is idempotent."""
    registry = ToolRegistry()
    registry.register("read_file", read_file, idempotent=True)
    registry.register("write_file", write_file, idempotent=False)

    assert registry.is_idempotent("read_file") is True
    assert registry.is_idempotent("write_file") is False
    assert registry.is_idempotent("unknown") is False


def test_get_function():
    """Get tool function by name."""
    registry = ToolRegistry()
    registry.register("read_file", read_file, idempotent=True)

    fn = registry.get_function("read_file")
    assert fn is read_file


def test_list_tools():
    """List all registered tools."""
    registry = ToolRegistry()
    registry.register("read_file", read_file, idempotent=True)
    registry.register("write_file", write_file, idempotent=False)

    tools = registry.list_tools()
    assert len(tools) == 2


def test_list_idempotent():
    """List only idempotent tools."""
    registry = ToolRegistry()
    registry.register("read_file", read_file, idempotent=True)
    registry.register("write_file", write_file, idempotent=False)

    idempotent = registry.list_idempotent()
    assert len(idempotent) == 1
    assert idempotent[0].name == "read_file"


def test_tool_decorator():
    """Tool decorator adds metadata."""

    @tool(idempotent=True, description="Read a file")
    async def decorated_tool(path: str) -> str:
        return f"contents of {path}"

    assert hasattr(decorated_tool, "_tool_metadata")
    assert decorated_tool._tool_metadata["idempotent"] is True
    assert decorated_tool._tool_metadata["description"] == "Read a file"
