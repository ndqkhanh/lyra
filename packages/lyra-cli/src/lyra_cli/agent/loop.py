"""Agent loop module - Claude Code-style execution with hooks.

This module implements the core agent loop inspired by Claude Code's
architecture, with a comprehensive hook system for extensibility.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Callable

from lyra_cli.cli.messages import AssistantMessage, Message, ToolMessage, UserMessage


@dataclass(frozen=True)
class RunContext:
    """Immutable context for a single agent run."""

    session_id: str | None
    run_id: str
    agent_name: str
    session_created_at: float | None = None


@dataclass
class AgentState:
    """Mutable state for agent execution."""

    messages: list[Message]
    system_prompt: str
    capabilities: dict[str, Any]
    metadata: dict[str, Any]

    def __init__(
        self,
        messages: list[Message],
        system_prompt: str,
        capabilities: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.messages = messages
        self.system_prompt = system_prompt
        self.capabilities = capabilities or {}
        self.metadata = metadata or {}


@dataclass(frozen=True)
class ModelRequest:
    """Immutable snapshot of a model request."""

    messages: tuple[Message, ...]
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int | None = None


async def run_agent_loop(
    messages: list[Message],
    system_prompt: str,
    hooks: list[Any],
    checkpointer: Any,
    config: dict[str, Any] | None = None,
    interrupt_event: asyncio.Event | None = None,
) -> list[Message]:
    """Execute agent loop with hook integration.

    Args:
        messages: Initial message history
        system_prompt: System prompt for the agent
        hooks: List of hook instances
        checkpointer: Checkpointer for persistence
        config: Optional configuration
        interrupt_event: Optional event for cancellation

    Returns:
        Updated message list
    """
    config = config or {}
    max_iterations = config.get("max_iterations", 10)
    agent_name = config.get("agent_name", "agent")
    session_id = config.get("session_id")

    # Build immutable context
    ctx = RunContext(
        session_id=session_id,
        run_id=_generate_run_id(),
        agent_name=agent_name,
        session_created_at=time.time(),
    )

    # Build mutable state
    state = AgentState(
        messages=messages,
        system_prompt=system_prompt,
        capabilities=config.get("capabilities", {}),
        metadata=config.get("metadata", {}),
    )

    # Fire before_agent hooks
    for hook in hooks:
        if hasattr(hook, "before_agent"):
            await hook.before_agent(ctx, state)

    iteration = 0
    while iteration < max_iterations:
        iteration += 1

        # Build model request (immutable snapshot)
        model_request = ModelRequest(
            messages=tuple(state.messages),
            system_prompt=state.system_prompt,
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens"),
        )

        # before_model hooks (can modify request)
        for hook in hooks:
            if hasattr(hook, "before_model"):
                updated = await hook.before_model(ctx, state, model_request)
                if updated:
                    model_request = updated

        # Sync point 1: After before_model
        await checkpointer.sync(ctx, state)

        # Stream LLM response
        assistant_msg = await _stream_and_assemble(
            model_request, ctx, state, hooks, interrupt_event, config
        )
        state.messages.append(assistant_msg)

        # after_model hooks
        for hook in hooks:
            if hasattr(hook, "after_model"):
                await hook.after_model(ctx, state, assistant_msg)

        # Sync point 2: After after_model
        await checkpointer.sync(ctx, state)

        # Check if final answer (no tool calls)
        if not assistant_msg.tool_calls:
            break

        # Pre-dispatch interrupt check
        if interrupt_event and interrupt_event.is_set():
            for tc in assistant_msg.tool_calls:
                state.messages.append(
                    ToolMessage(
                        content="Cancelled by user.",
                        tool_call_id=tc["id"],
                    )
                )
            break

        # Execute tools with hook wrapping
        tool_chain = _build_tool_chain(hooks, _execute_tool)
        results = await _gather_or_cancel(
            [
                tool_chain(ctx, state, tc, config)
                for tc in assistant_msg.tool_calls
            ],
            interrupt_event,
        )

        for tc, result in results:
            state.messages.append(
                ToolMessage(
                    content=result,
                    tool_call_id=tc["id"],
                )
            )

        # Sync point 3: After tool execution
        await checkpointer.sync(ctx, state)

    # after_agent hooks
    for hook in hooks:
        if hasattr(hook, "after_agent"):
            await hook.after_agent(ctx, state, state.messages[-1])

    # Sync point 4: Final sync
    await checkpointer.sync(ctx, state)

    return state.messages


async def _stream_and_assemble(
    request: ModelRequest,
    ctx: RunContext,
    state: AgentState,
    hooks: list[Any],
    interrupt_event: asyncio.Event | None,
    config: dict[str, Any],
) -> AssistantMessage:
    """Stream LLM response and assemble into message.

    Args:
        request: Model request
        ctx: Run context
        state: Agent state
        hooks: Hook instances
        interrupt_event: Optional cancellation event
        config: Configuration

    Returns:
        Assembled assistant message
    """
    # TODO: Implement actual LLM streaming
    # For now, return mock response
    _ = request, ctx, state, interrupt_event, config

    content = "Mock response from agent loop"
    tool_calls = None

    # Fire on_model_delta hooks
    for hook in hooks:
        if hasattr(hook, "on_model_delta"):
            await hook.on_model_delta(ctx, state, {"text": content})

    return AssistantMessage(content=content, tool_calls=tool_calls)


def _build_tool_chain(
    hooks: list[Any], executor: Callable
) -> Callable:
    """Build nested tool execution chain with hooks.

    Args:
        hooks: Hook instances
        executor: Base tool executor

    Returns:
        Wrapped tool executor
    """
    chain = executor

    for hook in reversed(hooks):
        if hasattr(hook, "wrap_tool_call"):
            prev_chain = chain

            async def chain(
                ctx: RunContext,
                state: AgentState,
                tc: dict[str, Any],
                config: dict[str, Any],
                h: Any = hook,
                next_fn: Callable = prev_chain,
            ) -> str:
                return await h.wrap_tool_call(ctx, state, tc, next_fn, config)

    return chain


async def _execute_tool(
    ctx: RunContext,
    state: AgentState,
    tool_call: dict[str, Any],
    config: dict[str, Any],
) -> str:
    """Execute a single tool call.

    Args:
        ctx: Run context
        state: Agent state
        tool_call: Tool call dict
        config: Configuration

    Returns:
        Tool result string
    """
    # TODO: Implement actual tool execution
    _ = ctx, state, config

    tool_name = tool_call.get("name", "unknown")
    return f"Mock result from {tool_name}"


async def _gather_or_cancel(
    tasks: list[Any], interrupt_event: asyncio.Event | None
) -> list[tuple[dict[str, Any], str]]:
    """Gather tasks with cancellation support.

    Args:
        tasks: List of coroutines
        interrupt_event: Optional cancellation event

    Returns:
        List of (tool_call, result) tuples
    """
    if not interrupt_event:
        return await asyncio.gather(*tasks)

    # TODO: Implement proper cancellation
    return await asyncio.gather(*tasks)


def _generate_run_id() -> str:
    """Generate unique run ID."""
    import uuid

    return str(uuid.uuid4())
