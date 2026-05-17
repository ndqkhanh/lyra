"""Tests for eager executor pool."""

import asyncio

import pytest

from lyra_cli.eager_tools import ToolSeal
from lyra_cli.eager_tools.executor_pool import EagerExecutorPool


async def mock_tool(arg1: str) -> str:
    """Mock tool for testing."""
    await asyncio.sleep(0.1)  # Simulate work
    return f"result: {arg1}"


async def failing_tool(arg1: str) -> str:
    """Mock tool that fails."""
    raise ValueError("Tool failed")


@pytest.mark.anyio
async def test_executor_dispatches_idempotent_tool():
    """Idempotent tools are dispatched eagerly."""
    registry = {"mock_tool": mock_tool}
    pool = EagerExecutorPool(registry)

    seal = ToolSeal(
        tool_call_id="tool_1",
        tool_name="mock_tool",
        arguments={"arg1": "test"},
        sealed_at=0.0,
    )

    await pool.dispatch(seal, idempotent=True)
    results = await pool.collect_results()

    assert len(results) == 1
    assert results[0].tool_call_id == "tool_1"
    assert "result:" in str(results[0].result)
    assert results[0].error is None


@pytest.mark.anyio
async def test_executor_skips_non_idempotent_tool():
    """Non-idempotent tools are not dispatched."""
    registry = {"mock_tool": mock_tool}
    pool = EagerExecutorPool(registry)

    seal = ToolSeal(
        tool_call_id="tool_1",
        tool_name="mock_tool",
        arguments={"arg1": "test"},
        sealed_at=0.0,
    )

    await pool.dispatch(seal, idempotent=False)
    results = await pool.collect_results()

    assert len(results) == 0  # Not dispatched


@pytest.mark.anyio
async def test_executor_handles_tool_failure():
    """Tool failures are captured in results."""
    registry = {"failing_tool": failing_tool}
    pool = EagerExecutorPool(registry)

    seal = ToolSeal(
        tool_call_id="tool_1",
        tool_name="failing_tool",
        arguments={"arg1": "test"},
        sealed_at=0.0,
    )

    await pool.dispatch(seal, idempotent=True)
    results = await pool.collect_results()

    assert len(results) == 1
    assert results[0].error is not None
    assert "Tool failed" in results[0].error


@pytest.mark.anyio
async def test_executor_parallel_execution():
    """Multiple tools execute in parallel."""
    registry = {"mock_tool": mock_tool}
    pool = EagerExecutorPool(registry)

    # Dispatch 3 tools
    for i in range(3):
        seal = ToolSeal(
            tool_call_id=f"tool_{i}",
            tool_name="mock_tool",
            arguments={"arg1": f"test{i}"},
            sealed_at=0.0,
        )
        await pool.dispatch(seal, idempotent=True)

    results = await pool.collect_results()

    assert len(results) == 3
    assert all(r.error is None for r in results)
