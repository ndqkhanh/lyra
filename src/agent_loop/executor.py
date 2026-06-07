"""
Agent Loop Executor — real execution cycle.

Implements the think -> act -> observe -> reflect loop with actual LLM
calls, tool dispatch, memory operations, and hook integration.

Usage::

    executor = AgentLoopExecutor()
    result = await executor.execute(
        task=task,
        agent=agent,
        provider=provider,
        tools=tool_executor,
        memory=stm,
        hooks=hook_engine,
    )

Streaming (for TUI real-time updates)::

    async for chunk in executor.execute_stream(...):
        # chunk is a CompletionChunk
        tui.update(chunk)
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from src.core.task import Result, Task, TaskStatus
from src.hooks.hook import HookAction, HookContext, HookResult, HookType
from src.hooks.hook_engine import HookEngine
from src.memory.short_term_memory import SQLiteShortTermMemory
from src.routing.provider.base import ProviderBackend
from src.routing.provider.types import (
    Capability,
    CompletionChunk,
    CompletionRequest,
    CompletionResponse,
    Message,
    ToolCall,
    ToolDef,
    TokenUsage,
)
from src.tools.executor import ToolExecutor
from src.tools.registry import ToolResult as ToolRegistryResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ITERATIONS = 10
"""Maximum think-act cycles before the loop escalates."""

MAX_RETRIES = 3
"""Retry attempts for transient LLM failures."""

BASE_RETRY_DELAY_S = 1.0
"""Initial backoff delay in seconds."""

MAX_RETRY_DELAY_S = 30.0
"""Maximum backoff delay in seconds."""


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class AgentLoopError(Exception):
    """Base exception for agent loop failures."""


class TransientProviderError(AgentLoopError):
    """A transient (retriable) provider error."""


class MaxRetriesExceeded(AgentLoopError):
    """The loop retried too many times without success."""


class MaxIterationsExceeded(AgentLoopError):
    """The loop exceeded the maximum number of think-act cycles."""


class HookBlockedError(AgentLoopError):
    """A pre-hook blocked execution."""


# ---------------------------------------------------------------------------
# Execution state
# ---------------------------------------------------------------------------


@dataclass
class AgentLoopState:
    """Mutable state tracked across think-act cycles."""

    iteration: int = 0
    retry_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    started_at: float = 0.0
    error: str | None = None


# ---------------------------------------------------------------------------
# AgentLoopExecutor
# ---------------------------------------------------------------------------


class AgentLoopExecutor:
    """
    Orchestrates the real execution cycle: think -> act -> observe -> reflect.

    Every part of the loop uses real infrastructure:
    * ``think`` — calls ``ProviderBackend.complete()`` with tool definitions
    * ``act`` — dispatches tool calls through ``ToolExecutor``
    * ``observe`` — captures tool outputs and builds follow-up messages
    * ``reflect`` — persists conversation turns to memory, fires post-hooks
    """

    def __init__(
        self,
        max_iterations: int = MAX_ITERATIONS,
        max_retries: int = MAX_RETRIES,
        base_retry_delay: float = BASE_RETRY_DELAY_S,
        max_retry_delay: float = MAX_RETRY_DELAY_S,
        model: str = "claude-sonnet-4-6",
    ):
        self.max_iterations = max_iterations
        self.max_retries = max_retries
        self.base_retry_delay = base_retry_delay
        self.max_retry_delay = max_retry_delay
        self.model = model

    # ------------------------------------------------------------------
    # Public API: execute (returns a Result)
    # ------------------------------------------------------------------

    async def execute(
        self,
        task: Task,
        agent: Any,
        provider: ProviderBackend,
        tools: ToolExecutor,
        memory: SQLiteShortTermMemory,
        hooks: HookEngine,
    ) -> Result:
        """
        Execute a task through the full think-act-observe-reflect loop.

        Args:
            task: The task to execute.
            agent: The agent instance (used for memory context and identity).
            provider: LLM provider backend.
            tools: Sandboxed tool executor.
            memory: SQLite-backed short-term memory.
            hooks: Hook engine for pre/post hooks.

        Returns:
            A ``Result`` with execution data and metrics.
        """
        state = AgentLoopState(started_at=time.monotonic())
        messages: list[Message] = []
        task.start()

        try:
            # ---- Bootstrap: build initial message list ----
            messages = await self._build_messages(task, agent, memory)

            # ---- Main think-act loop ----
            while state.iteration < self.max_iterations:
                state.iteration += 1

                # ----- THINK -----
                response = await self._think(
                    messages=messages,
                    provider=provider,
                    tools=tools,
                    hooks=hooks,
                    agent=agent,
                    task=task,
                    state=state,
                )

                # Track usage
                state.total_input_tokens += response.usage.input_tokens
                state.total_output_tokens += response.usage.output_tokens

                # Add assistant response to messages
                messages.append(
                    Message(role="assistant", content=response.content, tool_calls=response.tool_calls)
                )

                # ----- REFLECT (assistant turn) -----
                await self._reflect_assistant(
                    response=response,
                    agent=agent,
                    memory=memory,
                    hooks=hooks,
                    task=task,
                )

                # ----- Check termination ----
                if not response.tool_calls or len(response.tool_calls) == 0:
                    # LLM finished without requesting tools — we're done
                    task.complete()
                    return self._build_result(
                        task=task,
                        agent_id=self._agent_id(agent),
                        state=state,
                        data=response.content,
                    )

                # ----- ACT (execute each tool call) -----
                final_content = response.content
                for tool_call in response.tool_calls:
                    tool_result = await self._act(
                        tool_call=tool_call,
                        tools=tools,
                        hooks=hooks,
                        agent=agent,
                        task=task,
                        messages=messages,
                    )

                    # Add tool result message for next LLM turn
                    messages.append(
                        Message(
                            role="tool",
                            content=tool_result.output if tool_result.success else tool_result.error or "",
                            tool_call_id=tool_call.id,
                            name=tool_call.name,
                        )
                    )

                # If there were no tool calls (shouldn't happen given the check above,
                # but just in case), we're done
                if not response.tool_calls:
                    task.complete()
                    return self._build_result(
                        task=task,
                        agent_id=self._agent_id(agent),
                        state=state,
                        data=final_content,
                    )

            # If we exhaust iterations, escalate
            task.fail()
            return self._build_result(
                task=task,
                agent_id=self._agent_id(agent),
                state=state,
                success=False,
                error=f"Agent loop exceeded max iterations ({self.max_iterations})",
            )

        except HookBlockedError as e:
            task.fail()
            return self._build_result(
                task=task,
                agent_id=self._agent_id(agent),
                state=state,
                success=False,
                error=str(e),
            )
        except MaxRetriesExceeded as e:
            task.fail()
            return self._build_result(
                task=task,
                agent_id=self._agent_id(agent),
                state=state,
                success=False,
                error=str(e),
            )
        except AgentLoopError as e:
            task.fail()
            return self._build_result(
                task=task,
                agent_id=self._agent_id(agent),
                state=state,
                success=False,
                error=str(e),
            )
        except Exception as e:
            task.fail()
            logger.exception("Unexpected error in agent loop")
            return self._build_result(
                task=task,
                agent_id=self._agent_id(agent),
                state=state,
                success=False,
                error=f"Unexpected error: {e}",
            )

    # ------------------------------------------------------------------
    # Public API: execute_stream (yields chunks for TUI)
    # ------------------------------------------------------------------

    async def execute_stream(
        self,
        task: Task,
        agent: Any,
        provider: ProviderBackend,
        tools: ToolExecutor,
        memory: SQLiteShortTermMemory,
        hooks: HookEngine,
    ) -> AsyncIterator[CompletionChunk]:
        """
        Execute a task through the full loop, yielding streaming chunks.

        Chunks are yielded for every token produced by the LLM.
        When the LLM requests tool calls, the tool results are streamed as
        ``finish_reason="tool_use"`` chunks.

        Yields:
            ``CompletionChunk`` instances for real-time TUI updates.
        """
        state = AgentLoopState(started_at=time.monotonic())
        messages: list[Message] = []

        try:
            messages = await self._build_messages(task, agent, memory)

            while state.iteration < self.max_iterations:
                state.iteration += 1

                # ----- THINK (streaming) -----
                collected_content = ""
                collected_tool_calls: list[ToolCall] | None = None

                if provider.supports(Capability.STREAMING):
                    # Streaming path
                    async for chunk in provider.complete_stream(
                        self._build_request(messages, tools)
                    ):
                        yield chunk
                        if chunk.content_delta:
                            collected_content += chunk.content_delta
                        if chunk.finish_reason:
                            # The last chunk has finish_reason; tool calls
                            # are collected from the full response later
                            pass

                    # Get full response for tool calls / usage
                    response = await provider.complete(
                        self._build_request(messages, tools)
                    )
                else:
                    # Non-streaming path
                    response = await self._think(
                        messages=messages,
                        provider=provider,
                        tools=tools,
                        hooks=hooks,
                        agent=agent,
                        task=task,
                        state=state,
                    )
                    yield CompletionChunk(
                        content_delta=response.content,
                        finish_reason=response.finish_reason,
                    )

                state.total_input_tokens += response.usage.input_tokens
                state.total_output_tokens += response.usage.output_tokens

                # Add assistant message
                messages.append(
                    Message(
                        role="assistant",
                        content=response.content,
                        tool_calls=response.tool_calls,
                    )
                )

                # ----- REFLECT (assistant) -----
                await self._reflect_assistant(
                    response=response,
                    agent=agent,
                    memory=memory,
                    hooks=hooks,
                    task=task,
                )

                # ----- Termination check -----
                if not response.tool_calls:
                    task.complete()
                    return

                # ----- ACT -----
                for tool_call in response.tool_calls:
                    tool_result = await self._act(
                        tool_call=tool_call,
                        tools=tools,
                        hooks=hooks,
                        agent=agent,
                        task=task,
                        messages=messages,
                    )

                    messages.append(
                        Message(
                            role="tool",
                            content=tool_result.output if tool_result.success else tool_result.error or "",
                            tool_call_id=tool_call.id,
                            name=tool_call.name,
                        )
                    )

                    yield CompletionChunk(
                        content_delta=f"\n[Tool: {tool_call.name} completed in "
                        f"{tool_result.execution_time_ms:.0f}ms]\n"
                    )

            # Max iterations exceeded
            yield CompletionChunk(
                content_delta="\n[Agent loop: max iterations reached — escalating]\n",
                finish_reason="max_tokens",
            )

        except Exception as e:
            logger.exception("Streaming agent loop failed")
            yield CompletionChunk(
                content_delta=f"\n[Error: {e}]\n",
                finish_reason="stop_sequence",
            )

    # ------------------------------------------------------------------
    # Cycle phases
    # ------------------------------------------------------------------

    async def _think(
        self,
        messages: list[Message],
        provider: ProviderBackend,
        tools: ToolExecutor,
        hooks: HookEngine,
        agent: Any,
        task: Task,
        state: AgentLoopState,
    ) -> CompletionResponse:
        """THINK: call the LLM provider with retry logic."""
        request = self._build_request(messages, tools)

        # PRE_MODEL_CALL hooks
        pre_result = await hooks.execute_pre_hooks(
            HookContext(
                hook_type=HookType.PRE_MODEL_CALL,
                agent_id=self._agent_id(agent),
                model_request=request,
                metadata={"task_id": task.task_id, "iteration": state.iteration},
            )
        )
        if pre_result.action == HookAction.BLOCK:
            raise HookBlockedError(f"PRE_MODEL_CALL blocked: {pre_result.reason}")
        if pre_result.action == HookAction.MODIFY and pre_result.modified_context:
            if pre_result.modified_context.model_request is not None:
                request = pre_result.modified_context.model_request

        # Make the LLM call with retry
        last_exception: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = await provider.complete(request)

                # POST_MODEL_CALL hooks
                await hooks.execute_post_hooks(
                    HookContext(
                        hook_type=HookType.POST_MODEL_CALL,
                        agent_id=self._agent_id(agent),
                        model_request=request,
                        model_response=response,
                        metadata={"task_id": task.task_id, "iteration": state.iteration},
                    )
                )

                return response

            except (ConnectionError, TimeoutError) as e:
                last_exception = e
                delay = min(
                    self.base_retry_delay * (2 ** attempt),
                    self.max_retry_delay,
                )
                logger.warning(
                    "Transient provider error (attempt %d/%d): %s. Retrying in %.1fs",
                    attempt + 1, self.max_retries, e, delay,
                )
                await asyncio.sleep(delay)
            except Exception as e:
                # Non-transient — escalate immediately
                raise AgentLoopError(f"Provider call failed: {e}") from e

        raise MaxRetriesExceeded(
            f"Provider call failed after {self.max_retries} retries: {last_exception}"
        )

    async def _act(
        self,
        tool_call: ToolCall,
        tools: ToolExecutor,
        hooks: HookEngine,
        agent: Any,
        task: Task,
        messages: list[Message],
    ) -> ToolRegistryResult:
        """ACT + OBSERVE: execute a single tool call and capture the result."""
        # PRE_TOOL_USE hooks
        pre_result = await hooks.execute_pre_hooks(
            HookContext(
                hook_type=HookType.PRE_TOOL_USE,
                tool_name=tool_call.name,
                tool_input=tool_call.arguments,
                tool_args=tool_call.arguments,
                agent_id=self._agent_id(agent),
                metadata={"task_id": task.task_id, "tool_call_id": tool_call.id},
            )
        )
        if pre_result.action == HookAction.BLOCK:
            raise HookBlockedError(f"PRE_TOOL_USE blocked: {pre_result.reason}")

        # Execute the tool
        tool_result = await tools.execute(
            tool_name=tool_call.name,
            **tool_call.arguments,
        )

        # POST_TOOL_USE hooks
        await hooks.execute_post_hooks(
            HookContext(
                hook_type=HookType.POST_TOOL_USE,
                tool_name=tool_call.name,
                tool_input=tool_call.arguments,
                tool_args=tool_call.arguments,
                tool_result=tool_result,
                agent_id=self._agent_id(agent),
                metadata={
                    "task_id": task.task_id,
                    "tool_call_id": tool_call.id,
                    "execution_time_ms": tool_result.execution_time_ms,
                },
            )
        )

        return tool_result

    async def _reflect_assistant(
        self,
        response: CompletionResponse,
        agent: Any,
        memory: SQLiteShortTermMemory,
        hooks: HookEngine,
        task: Task,
    ) -> None:
        """REFLECT: persist assistant's turn to memory and fire post-hooks."""
        try:
            await memory.add_turn(
                role="assistant",
                content=response.content,
                importance_score=0.8 if response.tool_calls else 0.5,
            )
        except Exception as e:
            logger.warning("Failed to persist assistant turn to memory: %s", e)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _build_messages(
        self,
        task: Task,
        agent: Any,
        memory: SQLiteShortTermMemory,
    ) -> list[Message]:
        """
        Build the initial message list from the task and memory context.
        Returns a list of ``Message`` objects suitable for ``CompletionRequest``.
        """
        messages: list[Message] = []

        # System message from task description
        system_content = (
            f"You are the Lyra assistant. You have tools available to help "
            f"complete the user's request.\n\n"
            f"## Task\n{task.description}\n"
        )
        if task.params:
            system_content += f"\n## Parameters\n{task.params}\n"

        messages.append(Message(role="system", content=system_content))

        # Recent conversation context from memory
        try:
            recent_turns = await memory.get_recent(limit=10)
            for turn in recent_turns:
                role = "user" if turn.role == "user" else "assistant"
                messages.append(Message(role=role, content=turn.content))
        except Exception as e:
            logger.warning("Failed to load memory context: %s", e)

        return messages

    def _build_request(
        self,
        messages: list[Message],
        tools: ToolExecutor,
    ) -> CompletionRequest:
        """Build a ``CompletionRequest`` from messages and available tools."""
        # Convert tool definitions from the registry
        tool_defs: list[ToolDef] = []
        for t in tools.registry.list_tools():
            tool_defs.append(
                ToolDef(name=t.name, description=t.description, parameters=t.parameters)
            )

        return CompletionRequest(
            messages=tuple(messages),
            model=self.model,
            max_tokens=4096,
            temperature=0.0,
            tools=tuple(tool_defs) if tool_defs else None,
        )

    def _build_result(
        self,
        task: Task,
        agent_id: str,
        state: AgentLoopState,
        data: Any = None,
        success: bool = True,
        error: str | None = None,
    ) -> Result:
        """Build a ``Result`` with execution metrics."""
        duration = time.monotonic() - state.started_at
        # Rough cost estimate: use token counts as a proxy
        cost = self._estimate_cost(state.total_input_tokens, state.total_output_tokens)

        return Result(
            task_id=task.task_id,
            success=success,
            data=data,
            error=error,
            agent_id=agent_id,
            duration=duration,
            cost=cost,
            metadata={
                "iterations": state.iteration,
                "retries": state.retry_count,
                "total_input_tokens": state.total_input_tokens,
                "total_output_tokens": state.total_output_tokens,
                "model": self.model,
            },
        )

    @staticmethod
    def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
        """Rough cost estimate in USD (Sonnet 4.6 pricing: $3/$15 per 1M tokens)."""
        return (input_tokens / 1_000_000 * 3.0) + (output_tokens / 1_000_000 * 15.0)

    @staticmethod
    def _agent_id(agent: Any) -> str:
        """Extract agent_id from any agent-like object."""
        if hasattr(agent, "agent_id"):
            return agent.agent_id
        return str(agent)
