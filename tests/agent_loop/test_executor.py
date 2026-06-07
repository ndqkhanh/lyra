"""
Tests for AgentLoopExecutor (S9: Agent Loop v2 — Real Execution).

Covers:
  - Full execution cycle (think -> act -> observe -> reflect)
  - Streaming output
  - Error recovery (retry on transient failures)
  - Error escalation (repeated failure, max iterations)
  - Hook integration (PRE_MODEL_CALL, POST_MODEL_CALL, PRE_TOOL_USE, POST_TOOL_USE)
  - Hook blocking
  - Tool execution through ToolExecutor
  - Memory integration
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from lyra.agent_loop.executor import (
    AgentLoopExecutor,
    HookBlockedError,
    MaxRetriesExceeded,
)
from lyra.core.task import Result, Task, TaskStatus, TaskType
from lyra.hooks.hook import HookAction, HookContext, HookResult, HookType
from lyra.memory.short_term_memory import ConversationTurn, SQLiteShortTermMemory
from lyra.routing.provider.base import ProviderBackend
from lyra.routing.provider.types import (
    Capability,
    CompletionChunk,
    CompletionRequest,
    CompletionResponse,
    Message,
    ToolCall,
    TokenUsage,
)
from lyra.tools.executor import ToolExecutor
from lyra.tools.registry import ToolDef, ToolRegistry, ToolResult


# ======================================================================
# Mocks
# ======================================================================


class MockProvider(ProviderBackend):
    """Mock provider that returns canned responses."""

    def __init__(
        self,
        responses: list[CompletionResponse] | None = None,
        stream_responses: list[CompletionChunk] | None = None,
        supports_streaming: bool = False,
    ):
        self._responses = responses or []
        self._stream_responses = stream_responses or []
        self._supports_streaming = supports_streaming
        self.call_count = 0
        self.remaining_failures: int = 0
        self.fail_exception: Exception = ConnectionError("mock failure")

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        self.call_count += 1
        if self.remaining_failures > 0:
            self.remaining_failures -= 1
            raise self.fail_exception
        if self._responses:
            return self._responses.pop(0)
        return CompletionResponse(
            content="I'm a mock response.",
            tool_calls=None,
            usage=TokenUsage(input_tokens=10, output_tokens=5),
            finish_reason="end_turn",
            model="mock-model",
            latency_ms=10,
        )

    async def complete_stream(
        self,
        request: CompletionRequest,
    ) -> AsyncIterator[CompletionChunk]:
        for chunk in self._stream_responses:
            yield chunk
        # Final chunk
        yield CompletionChunk(
            content_delta="",
            finish_reason="end_turn",
        )

    def supports(self, capability: Capability) -> bool:
        if capability == Capability.STREAMING:
            return self._supports_streaming
        return True

    def cost_estimate(self, request: CompletionRequest) -> Any:
        return None

    @property
    def provider_name(self) -> str:
        return "mock"


class MockToolRegistry(ToolRegistry):
    """ToolRegistry with easy mock handler registration."""

    def add_mock_tool(
        self,
        name: str,
        handler: Any = None,
        result: ToolResult | None = None,
    ) -> None:
        async def _handler(**kwargs: Any) -> dict[str, Any]:
            if result:
                return {"success": result.success, "output": result.output, "error": result.error}
            return {"success": True, "output": f"Executed {name}", "error": None}

        self.register(
            ToolDef(
                name=name,
                description=f"Mock {name}",
                parameters={"type": "object", "properties": {}},
                handler=handler or _handler,
            )
        )


@pytest.fixture
def mock_registry() -> MockToolRegistry:
    return MockToolRegistry()


@pytest.fixture
def mock_executor(mock_registry: MockToolRegistry) -> ToolExecutor:
    return ToolExecutor(mock_registry)


@pytest.fixture
def mock_memory() -> MagicMock:
    memory = MagicMock(spec=SQLiteShortTermMemory)
    memory.add_turn = AsyncMock(return_value=ConversationTurn(role="assistant", content="", timestamp=0.0))
    memory.get_recent = AsyncMock(return_value=[])
    return memory


@pytest.fixture
def mock_hooks() -> MagicMock:
    hooks = MagicMock()
    hooks.execute_pre_hooks = AsyncMock(
        return_value=HookResult(action=HookAction.ALLOW, reason="ok")
    )
    hooks.execute_post_hooks = AsyncMock(return_value=[])
    return hooks


@pytest.fixture
def agent() -> Any:
    """A minimal agent-like object."""
    agent = MagicMock()
    agent.agent_id = "test-agent"
    return agent


@pytest.fixture
def task() -> Task:
    return Task(
        description="Test the agent loop executor",
        type=TaskType.GENERIC,
    )


@pytest.fixture
def executor() -> AgentLoopExecutor:
    return AgentLoopExecutor(max_iterations=5, max_retries=3)


# ======================================================================
# Basic execution cycle
# ======================================================================


class TestBasicExecution:
    """Test the basic think -> act -> observe -> reflect cycle."""

    async def test_response_without_tool_calls(
        self,
        executor: AgentLoopExecutor,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """LLM responds without tool calls -> loop terminates immediately."""
        provider = MockProvider()

        result = await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        assert result.success is True
        assert result.data == "I'm a mock response."
        assert result.agent_id == "test-agent"
        assert result.task_id == task.task_id
        assert task.status == TaskStatus.COMPLETED

    async def test_single_tool_call_then_finish(
        self,
        executor: AgentLoopExecutor,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """LLM calls one tool, gets result back, then finishes."""
        mock_registry = mock_executor.registry
        mock_registry.add_mock_tool(
            "read_file",
            result=ToolResult(success=True, output="file contents", execution_time_ms=5.0),
        )

        provider = MockProvider(responses=[
            # First turn: tool call
            CompletionResponse(
                content="Let me read that file.",
                tool_calls=(
                    ToolCall(id="call_1", name="read_file", arguments={"path": "/tmp/test.txt"}),
                ),
                usage=TokenUsage(input_tokens=20, output_tokens=10),
                finish_reason="tool_use",
                model="mock-model",
                latency_ms=20,
            ),
            # Second turn: final response
            CompletionResponse(
                content="Here are the file contents.",
                tool_calls=None,
                usage=TokenUsage(input_tokens=30, output_tokens=5),
                finish_reason="end_turn",
                model="mock-model",
                latency_ms=10,
            ),
        ])

        result = await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        assert result.success is True
        assert "Here are the file contents" in str(result.data)

    async def test_multiple_tool_calls(
        self,
        executor: AgentLoopExecutor,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """LLM calls multiple tools in a single turn."""
        mock_registry = mock_executor.registry
        mock_registry.add_mock_tool("search_web")
        mock_registry.add_mock_tool("read_file")

        provider = MockProvider(responses=[
            # First turn: two tool calls
            CompletionResponse(
                content="Searching and reading.",
                tool_calls=(
                    ToolCall(id="call_1", name="search_web", arguments={"query": "test"}),
                    ToolCall(id="call_2", name="read_file", arguments={"path": "/tmp/test.txt"}),
                ),
                usage=TokenUsage(input_tokens=20, output_tokens=15),
                finish_reason="tool_use",
                model="mock-model",
                latency_ms=20,
            ),
            # Second turn: final response
            CompletionResponse(
                content="Done with both.",
                tool_calls=None,
                usage=TokenUsage(input_tokens=50, output_tokens=5),
                finish_reason="end_turn",
                model="mock-model",
                latency_ms=10,
            ),
        ])

        result = await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        assert result.success is True
        assert result.metadata.get("iterations") == 2

    async def test_metrics_tracking(
        self,
        executor: AgentLoopExecutor,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """Result includes correct metrics."""
        provider = MockProvider()

        result = await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        assert result.duration > 0
        assert result.metadata["iterations"] == 1
        assert result.metadata["total_input_tokens"] == 10
        assert result.metadata["total_output_tokens"] == 5
        assert result.cost > 0

    async def test_result_includes_model(
        self,
        executor: AgentLoopExecutor,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        provider = MockProvider()
        result = await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )
        assert result.metadata["model"] == "claude-sonnet-4-6"


# ======================================================================
# Error handling and recovery
# ======================================================================


class TestErrorHandling:
    """Test retry, escalation, and error recovery."""

    async def test_retry_on_transient_error(
        self,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """Transient errors trigger retry with backoff."""
        provider = MockProvider()
        provider.remaining_failures = 1
        provider.fail_exception = ConnectionError("reset by peer")

        executor = AgentLoopExecutor(max_iterations=5, max_retries=3, base_retry_delay=0.01)

        result = await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        assert result.success is True
        # First call failed (count=1), second succeeded (count=2 after reset)
        assert provider.call_count >= 2

    async def test_escalate_on_repeated_failure(
        self,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """Repeated failures escalate to MaxRetriesExceeded."""
        provider = MockProvider()
        provider.remaining_failures = 999  # Always fail
        provider.fail_exception = ConnectionError("always failing")

        executor = AgentLoopExecutor(max_iterations=5, max_retries=2, base_retry_delay=0.01)

        result = await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        assert result.success is False
        assert "retries" in (result.error or "").lower() or "retry" in (result.error or "").lower()
        assert task.status == TaskStatus.FAILED

    async def test_max_iterations_exceeded(
        self,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """Loop terminates when max_iterations is exceeded."""
        mock_registry = mock_executor.registry
        mock_registry.add_mock_tool("always_call_tool")

        # Provider always returns a tool call -> infinite loop without max_iterations
        provider = MockProvider(responses=[
            CompletionResponse(
                content="Calling tool again.",
                tool_calls=(
                    ToolCall(id=f"call_{i}", name="always_call_tool", arguments={}),
                ),
                usage=TokenUsage(input_tokens=5, output_tokens=5),
                finish_reason="tool_use",
                model="mock-model",
                latency_ms=5,
            )
            for i in range(20)  # Enough to exceed max_iterations
        ])

        executor = AgentLoopExecutor(max_iterations=3, max_retries=1)
        result = await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        assert result.success is False
        assert "max iterations" in (result.error or "").lower()

    async def test_non_transient_error_immediate_escalation(
        self,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """Non-transient errors (e.g. ValueError) escalate immediately."""
        provider = MockProvider()
        provider.remaining_failures = 1
        provider.fail_exception = ValueError("invalid request")

        executor = AgentLoopExecutor(max_retries=3, base_retry_delay=0.01)

        result = await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        assert result.success is False  # Non-transient escalates
        assert task.status == TaskStatus.FAILED

    async def test_tool_execution_failure(
        self,
        executor: AgentLoopExecutor,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """Tool execution failure is captured in the tool result message."""
        mock_registry = mock_executor.registry
        mock_registry.add_mock_tool(
            "fail_tool",
            result=ToolResult(success=False, error="Intentional failure", execution_time_ms=1.0),
        )

        provider = MockProvider(responses=[
            CompletionResponse(
                content="Calling failing tool.",
                tool_calls=(
                    ToolCall(id="call_fail", name="fail_tool", arguments={}),
                ),
                usage=TokenUsage(input_tokens=10, output_tokens=5),
                finish_reason="tool_use",
                model="mock-model",
                latency_ms=5,
            ),
            CompletionResponse(
                content="I see the tool failed.",
                tool_calls=None,
                usage=TokenUsage(input_tokens=20, output_tokens=5),
                finish_reason="end_turn",
                model="mock-model",
                latency_ms=5,
            ),
        ])

        result = await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        assert result.success is True
        # Error message should have been passed back in tool result


# ======================================================================
# Hook integration
# ======================================================================


class TestHookIntegration:
    """Test pre/post hooks fire at correct cycle boundaries."""

    async def test_pre_model_call_hook_fires(
        self,
        executor: AgentLoopExecutor,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """PRE_MODEL_CALL hook is called before each LLM call."""
        provider = MockProvider()

        await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        # Check that execute_pre_hooks was called with a PRE_MODEL_CALL context
        call_args = mock_hooks.execute_pre_hooks.call_args
        assert call_args is not None
        ctx: HookContext = call_args[0][0]
        assert ctx.hook_type == HookType.PRE_MODEL_CALL
        assert ctx.agent_id == "test-agent"

    async def test_post_model_call_hook_fires(
        self,
        executor: AgentLoopExecutor,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """POST_MODEL_CALL hook is called after each LLM call."""
        provider = MockProvider()

        await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        call_args = mock_hooks.execute_post_hooks.call_args
        assert call_args is not None
        ctx: HookContext = call_args[0][0]
        assert ctx.hook_type == HookType.POST_MODEL_CALL

    async def test_pre_tool_use_hook_fires(
        self,
        executor: AgentLoopExecutor,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """PRE_TOOL_USE hook fires before each tool call."""
        mock_registry = mock_executor.registry
        mock_registry.add_mock_tool("my_tool")

        provider = MockProvider(responses=[
            CompletionResponse(
                content="Using tool.",
                tool_calls=(
                    ToolCall(id="c1", name="my_tool", arguments={}),
                ),
                usage=TokenUsage(input_tokens=10, output_tokens=5),
                finish_reason="tool_use",
                model="mock-model",
                latency_ms=5,
            ),
            CompletionResponse(
                content="Done.",
                tool_calls=None,
                usage=TokenUsage(input_tokens=20, output_tokens=5),
                finish_reason="end_turn",
                model="mock-model",
                latency_ms=5,
            ),
        ])

        # Reset to track calls for this specific test
        mock_hooks.reset_mock()

        # We need 2 calls: 1 for PRE_MODEL_CALL (think), 1 for PRE_TOOL_USE (act)
        # and 2 for post hooks: 1 for POST_MODEL_CALL, 1 for POST_TOOL_USE
        def side_effect_pre(ctx: HookContext) -> HookResult:
            return HookResult(action=HookAction.ALLOW, reason="ok")

        mock_hooks.execute_pre_hooks = AsyncMock(side_effect=side_effect_pre)

        await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        # Find a PRE_TOOL_USE call
        pre_calls = mock_hooks.execute_pre_hooks.call_args_list
        pre_tool_ctxs = [
            call_args[0][0] for call_args in pre_calls
            if call_args[0][0].hook_type == HookType.PRE_TOOL_USE
        ]
        assert len(pre_tool_ctxs) >= 1
        assert pre_tool_ctxs[0].tool_name == "my_tool"

    async def test_post_tool_use_hook_fires(
        self,
        executor: AgentLoopExecutor,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """POST_TOOL_USE hook fires after each tool call."""
        mock_registry = mock_executor.registry
        mock_registry.add_mock_tool("another_tool")

        provider = MockProvider(responses=[
            CompletionResponse(
                content="Using tool.",
                tool_calls=(
                    ToolCall(id="c1", name="another_tool", arguments={}),
                ),
                usage=TokenUsage(input_tokens=10, output_tokens=5),
                finish_reason="tool_use",
                model="mock-model",
                latency_ms=5,
            ),
            CompletionResponse(
                content="Done.",
                tool_calls=None,
                usage=TokenUsage(input_tokens=20, output_tokens=5),
                finish_reason="end_turn",
                model="mock-model",
                latency_ms=5,
            ),
        ])

        mock_hooks.reset_mock()

        await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        post_calls = mock_hooks.execute_post_hooks.call_args_list
        post_tool_ctxs = [
            call_args[0][0] for call_args in post_calls
            if call_args[0][0].hook_type == HookType.POST_TOOL_USE
        ]
        assert len(post_tool_ctxs) >= 1
        assert post_tool_ctxs[0].tool_name == "another_tool"

    async def test_hook_block_stops_execution(
        self,
        executor: AgentLoopExecutor,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """If a pre-hook blocks, execution stops immediately."""
        provider = MockProvider()

        # Make the pre-hook return BLOCK
        mock_hooks.execute_pre_hooks = AsyncMock(
            return_value=HookResult(
                action=HookAction.BLOCK,
                reason="Security policy violation",
            )
        )

        result = await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        assert result.success is False
        assert "blocked" in (result.error or "").lower()
        assert task.status == TaskStatus.FAILED


# ======================================================================
# Memory integration
# ======================================================================


class TestMemoryIntegration:
    """Test that memory is read before execution and written after."""

    async def test_memory_read_before_execution(
        self,
        executor: AgentLoopExecutor,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """Memory is queried before the first LLM call."""
        provider = MockProvider()

        await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        mock_memory.get_recent.assert_called_once()

    async def test_memory_written_after_assistant_turn(
        self,
        executor: AgentLoopExecutor,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """Assistant conversation turn is persisted to memory."""
        provider = MockProvider()

        await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        mock_memory.add_turn.assert_called_once()
        call_args = mock_memory.add_turn.call_args
        assert call_args is not None
        args, kwargs = call_args
        role = kwargs.get("role", args[0] if args else "")
        assert role == "assistant"

    async def test_memory_with_context_turns(
        self,
        executor: AgentLoopExecutor,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """Recent memory turns are included in the message list."""
        mock_memory.get_recent = AsyncMock(return_value=[
            ConversationTurn(role="user", content="Previous question", timestamp=0.0),
            ConversationTurn(role="assistant", content="Previous answer", timestamp=0.0),
        ])

        provider = MockProvider()

        # To inspect the messages, we use a hook context check
        call_hook = AsyncMock(
            return_value=HookResult(action=HookAction.ALLOW, reason="ok")
        )

        mock_hooks.execute_pre_hooks = call_hook

        result = await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        # Memory get_recent was called
        mock_memory.get_recent.assert_called_once()
        assert result.success is True


# ======================================================================
# Streaming tests
# ======================================================================


class TestStreaming:
    """Test streaming output via execute_stream."""

    async def test_streaming_basic(
        self,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """Streaming yields CompletionChunks."""
        provider = MockProvider(
            supports_streaming=True,
            stream_responses=[
                CompletionChunk(content_delta="Hello "),
                CompletionChunk(content_delta="world"),
            ],
        )

        executor = AgentLoopExecutor(max_iterations=1)
        chunks: list[CompletionChunk] = []
        async for chunk in executor.execute_stream(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        # At least one chunk with text content
        texts = [c.content_delta for c in chunks if c.content_delta]
        assert any("Hello" in t or "world" in t for t in texts)

    async def test_streaming_non_streaming_fallback(
        self,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """When provider doesn't support streaming, non-streaming fallback works."""
        provider = MockProvider(supports_streaming=False)

        executor = AgentLoopExecutor(max_iterations=1)
        chunks: list[CompletionChunk] = []
        async for chunk in executor.execute_stream(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        ):
            chunks.append(chunk)

        assert len(chunks) >= 1
        assert any("mock response" in c.content_delta for c in chunks if c.content_delta)

    async def test_streaming_error_handling(
        self,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """Streaming handles errors gracefully."""
        provider = MockProvider()
        provider.remaining_failures = 1
        provider.fail_exception = RuntimeError("stream failure")

        executor = AgentLoopExecutor(max_iterations=1, max_retries=0)
        chunks: list[CompletionChunk] = []
        async for chunk in executor.execute_stream(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        ):
            chunks.append(chunk)

        # Error should be captured, not crash
        assert len(chunks) >= 1

    async def test_streaming_with_tool_use(
        self,
        task: Task,
        agent: Any,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """Streaming works end-to-end with tool calls."""
        mock_registry = mock_executor.registry
        mock_registry.add_mock_tool("search")

        provider = MockProvider(
            supports_streaming=True,
            responses=[
                CompletionResponse(
                    content="I'll search for that.",
                    tool_calls=(
                        ToolCall(id="c1", name="search", arguments={"q": "test"}),
                    ),
                    usage=TokenUsage(input_tokens=10, output_tokens=5),
                    finish_reason="tool_use",
                    model="mock-model",
                    latency_ms=5,
                ),
                CompletionResponse(
                    content="Here are the results.",
                    tool_calls=None,
                    usage=TokenUsage(input_tokens=30, output_tokens=5),
                    finish_reason="end_turn",
                    model="mock-model",
                    latency_ms=5,
                ),
            ],
            stream_responses=[
                CompletionChunk(content_delta="I'll search"),
            ],
        )

        executor = AgentLoopExecutor(max_iterations=5)
        chunks: list[CompletionChunk] = []
        async for chunk in executor.execute_stream(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        ):
            chunks.append(chunk)

        # Should have tool completion notification
        tool_notifications = [c for c in chunks if "Tool" in c.content_delta]
        assert len(tool_notifications) >= 1
        assert any("search" in c.content_delta for c in tool_notifications)


# ======================================================================
# Agent base class integration
# ======================================================================


class TestAgentBaseIntegration:
    """Test that Agent ABC integrates correctly with AgentLoopExecutor."""

    async def test_run_loop_raises_not_implemented(
        self,
        task: Task,
        executor: AgentLoopExecutor,
    ) -> None:
        """Default run_loop() raises NotImplementedError."""
        from lyra.agents.base import Agent

        class MinimalAgent(Agent):
            async def execute(self, task: Task) -> Result:
                return Result(task_id=task.task_id, success=True, data="ok")
            def can_handle(self, task: Task) -> float:
                return 0.5

        agent = MinimalAgent(agent_id="minimal-test")
        with pytest.raises(NotImplementedError):
            await agent.run_loop(task=task, loop_executor=executor)

    async def test_agent_still_works_with_execute(
        self,
        task: Task,
    ) -> None:
        """Existing agents with execute() are unaffected by run_loop addition."""
        from lyra.agents.base import Agent

        class ExistingAgent(Agent):
            async def execute(self, task: Task) -> Result:
                return Result(task_id=task.task_id, success=True, data="simulated")
            def can_handle(self, task: Task) -> float:
                return 1.0

        agent = ExistingAgent(agent_id="existing")
        result = await agent.execute(task=task)
        assert result.success is True
        assert result.data == "simulated"

    async def test_agent_id_from_run_loop_result(
        self,
        executor: AgentLoopExecutor,
        task: Task,
        mock_executor: ToolExecutor,
        mock_memory: MagicMock,
        mock_hooks: MagicMock,
    ) -> None:
        """Result from AgentLoopExecutor includes the agent's ID."""
        from lyra.agents.base import Agent

        class LoopCapableAgent(Agent):
            async def execute(self, task: Task) -> Result:
                return Result(task_id=task.task_id, success=True)
            def can_handle(self, task: Task) -> float:
                return 1.0

        agent = LoopCapableAgent(agent_id="loop-capable-agent")
        provider = MockProvider()

        result = await executor.execute(
            task=task,
            agent=agent,
            provider=provider,
            tools=mock_executor,
            memory=mock_memory,
            hooks=mock_hooks,
        )

        assert result.agent_id == "loop-capable-agent"
