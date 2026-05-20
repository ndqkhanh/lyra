"""Tests for EventBus emissions in AgentLoop."""
from __future__ import annotations

from lyra_core.agent.loop import AgentLoop, IterationBudget
from lyra_core.observability import (
    LLMCallFinished,
    LLMCallStarted,
    ToolCallFinished,
    ToolCallStarted,
    get_event_bus,
    reset_event_bus,
)


class _FakeLLM:
    def generate(self, messages: list, tools: list) -> dict:
        return {
            "content": "Hello, I'll use a tool",
            "tool_calls": [{"name": "test_tool", "arguments": {"arg": "value"}}],
        }


class _FakeLLMNoTools:
    def generate(self, messages: list, tools: list) -> dict:
        return {"content": "Done", "tool_calls": []}


def test_agent_loop_emits_llm_events() -> None:
    reset_event_bus()
    bus = get_event_bus()
    events: list = []
    bus.add_listener(lambda e: events.append(e))

    llm = _FakeLLMNoTools()
    tools = {}
    loop = AgentLoop(llm=llm, tools=tools, store=None, budget=IterationBudget(max=1))

    loop.run_conversation("test", session_id="sess-1")

    # Should have LLMCallStarted and LLMCallFinished
    llm_started = [e for e in events if isinstance(e, LLMCallStarted)]
    llm_finished = [e for e in events if isinstance(e, LLMCallFinished)]

    assert len(llm_started) == 1
    assert len(llm_finished) == 1
    assert llm_started[0].session_id == "sess-1"
    assert llm_finished[0].session_id == "sess-1"


def test_agent_loop_emits_tool_events() -> None:
    reset_event_bus()
    bus = get_event_bus()
    events: list = []
    bus.add_listener(lambda e: events.append(e))

    def test_tool(arg: str) -> str:
        return f"result: {arg}"

    llm = _FakeLLM()
    tools = {"test_tool": test_tool}
    loop = AgentLoop(llm=llm, tools=tools, store=None, budget=IterationBudget(max=2))

    loop.run_conversation("test", session_id="sess-2")

    # Should have ToolCallStarted and ToolCallFinished
    tool_started = [e for e in events if isinstance(e, ToolCallStarted)]
    tool_finished = [e for e in events if isinstance(e, ToolCallFinished)]

    assert len(tool_started) >= 1
    assert len(tool_finished) >= 1
    assert tool_started[0].session_id == "sess-2"
    assert tool_started[0].tool_name == "test_tool"
    assert tool_finished[0].session_id == "sess-2"
    assert tool_finished[0].tool_name == "test_tool"
    assert tool_finished[0].is_error is False


def test_agent_loop_emits_tool_error_events() -> None:
    reset_event_bus()
    bus = get_event_bus()
    events: list = []
    bus.add_listener(lambda e: events.append(e))

    def failing_tool(arg: str) -> str:
        raise ValueError("Tool failed")

    llm = _FakeLLM()
    tools = {"test_tool": failing_tool}
    loop = AgentLoop(llm=llm, tools=tools, store=None, budget=IterationBudget(max=2))

    loop.run_conversation("test", session_id="sess-3")

    # Should have ToolCallFinished with is_error=True
    tool_finished = [e for e in events if isinstance(e, ToolCallFinished)]

    assert len(tool_finished) >= 1
    assert tool_finished[0].session_id == "sess-3"
    assert tool_finished[0].is_error is True


def test_agent_loop_multiple_iterations() -> None:
    reset_event_bus()
    bus = get_event_bus()
    events: list = []
    bus.add_listener(lambda e: events.append(e))

    call_count = 0

    class _MultiIterLLM:
        def generate(self, messages: list, tools: list) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "content": "First call",
                    "tool_calls": [{"name": "tool1", "arguments": {}}],
                }
            return {"content": "Done", "tool_calls": []}

    def tool1() -> str:
        return "tool1 result"

    llm = _MultiIterLLM()
    tools = {"tool1": tool1}
    loop = AgentLoop(llm=llm, tools=tools, store=None, budget=IterationBudget(max=5))

    loop.run_conversation("test", session_id="sess-4")

    # Should have 2 LLM calls (first with tool, second without)
    llm_started = [e for e in events if isinstance(e, LLMCallStarted)]
    llm_finished = [e for e in events if isinstance(e, LLMCallFinished)]
    tool_started = [e for e in events if isinstance(e, ToolCallStarted)]
    tool_finished = [e for e in events if isinstance(e, ToolCallFinished)]

    assert len(llm_started) == 2
    assert len(llm_finished) == 2
    assert len(tool_started) == 1
    assert len(tool_finished) == 1
    assert all(e.session_id == "sess-4" for e in events if hasattr(e, "session_id"))
