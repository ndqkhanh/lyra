"""Tests for agent loop integration."""

import pytest

from lyra_cli.eager_tools import ToolRegistry, tool
from lyra_cli.eager_tools.integration import EagerAgentLoop
from lyra_cli.eager_tools.types import StreamChunk


@tool(idempotent=True)
async def mock_read(path: str) -> str:
    """Mock read tool."""
    return f"contents of {path}"


@tool(idempotent=False)
async def mock_write(path: str, content: str) -> None:
    """Mock write tool."""
    pass


class MockStream:
    """Mock streaming response."""

    def __init__(self, chunks: list[StreamChunk]):
        self.chunks = chunks

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.chunks:
            raise StopAsyncIteration
        return self.chunks.pop(0)


@pytest.mark.anyio
async def test_eager_dispatch_in_agent_loop():
    """Idempotent tools are eagerly dispatched during streaming."""
    registry = ToolRegistry()
    registry.register("mock_read", mock_read, idempotent=True)

    loop = EagerAgentLoop(registry)

    # Simulate stream with tool calls
    chunks = [
        StreamChunk(tool_call_id="tool_1", name="mock_read"),
        StreamChunk(tool_call_id="tool_1", arguments={"path": "test.py"}),
        StreamChunk(tool_call_id="tool_2", name="mock_read"),  # Seals tool_1
        StreamChunk(text="Done"),
    ]

    result = await loop.run_with_eager_dispatch(MockStream(chunks))

    assert result["text"] == "Done"
    assert len(result["tool_results"]) == 1
    assert len(result["sealed_tools"]) == 1


@pytest.mark.anyio
async def test_non_idempotent_not_dispatched():
    """Non-idempotent tools are not eagerly dispatched."""
    registry = ToolRegistry()
    registry.register("mock_write", mock_write, idempotent=False)

    loop = EagerAgentLoop(registry)

    chunks = [
        StreamChunk(tool_call_id="tool_1", name="mock_write"),
        StreamChunk(tool_call_id="tool_2", name="mock_write"),  # Seals tool_1
    ]

    result = await loop.run_with_eager_dispatch(MockStream(chunks))

    # Not dispatched (non-idempotent)
    assert len(result["tool_results"]) == 0
    assert len(result["sealed_tools"]) == 1
