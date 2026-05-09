"""Phase 0 — RED for the hermes-style AgentLoop in ``lyra_core``.

Contract (plan Phase 2):

- ``AgentLoop`` lives at ``lyra_core.agent.loop``.
- It is constructed with ``llm``, ``tools``, ``store``, ``plugins`` and a
  ``budget: IterationBudget``.
- ``run_conversation(user_text, *, session_id)`` returns a ``TurnResult``
  with at least ``final_text: str``, ``iterations: int``, and
  ``tool_calls: list[dict]``.
- Plugin hooks fire at deterministic seams: ``on_session_start`` before
  the first turn, ``pre_llm_call`` before every LLM call,
  ``pre_tool_call`` before every tool dispatch, ``on_session_end`` after
  the turn completes.
- ``IterationBudget(max=N)`` caps the LLM-call count; exceeding it marks
  the TurnResult with ``stopped_by="budget"``.
- A user interrupt (simulated by a plugin raising ``KeyboardInterrupt``
  from ``pre_tool_call``) stops the loop cleanly and marks the
  TurnResult with ``stopped_by="interrupt"``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest


def _import_loop():
    try:
        from lyra_core.agent.loop import AgentLoop, IterationBudget, TurnResult
    except ModuleNotFoundError as exc:
        pytest.fail(f"lyra_core.agent.loop must exist ({exc})")
    return AgentLoop, IterationBudget, TurnResult


# --- Fakes shared across tests ---------------------------------------- #


@dataclass
class _ScriptedLLM:
    """A fake LLM that returns a queued list of responses."""
    queue: list[dict]
    calls: list[dict] = field(default_factory=list)

    def generate(self, *, messages, tools=None, **kwargs) -> dict:  # noqa: D401
        self.calls.append({"messages": messages, "tools": tools, "kwargs": kwargs})
        if not self.queue:
            return {"role": "assistant", "content": "done", "stop_reason": "end_turn"}
        return self.queue.pop(0)


@dataclass
class _InMemoryStore:
    sessions: dict[str, list[dict]] = field(default_factory=dict)

    def start_session(self, *, session_id: str, **_: Any) -> None:
        self.sessions.setdefault(session_id, [])

    def append_message(self, *, session_id: str, role: str, content: str,
                       tool_calls: list | None = None, **_: Any) -> None:
        self.sessions.setdefault(session_id, []).append(
            {"role": role, "content": content, "tool_calls": tool_calls or []}
        )


class _RecordingPlugin:
    """Records every hook call in order for assertions."""
    def __init__(self) -> None:
        self.events: list[str] = []
        self.post_tool_results: list[tuple[str, Any]] = []

    def on_session_start(self, ctx) -> None:
        self.events.append("on_session_start")

    def pre_llm_call(self, ctx) -> None:
        self.events.append("pre_llm_call")

    def pre_tool_call(self, ctx) -> None:
        self.events.append(f"pre_tool_call:{ctx.tool_name}")

    def post_tool_call(self, ctx) -> None:
        self.events.append(f"post_tool_call:{ctx.tool_name}")
        self.post_tool_results.append((ctx.tool_name, ctx.result))

    def on_session_end(self, ctx) -> None:
        self.events.append("on_session_end")


# --- Tests ------------------------------------------------------------ #


def test_run_conversation_simple_end_turn():
    AgentLoop, IterationBudget, _ = _import_loop()
    llm = _ScriptedLLM(queue=[
        {"role": "assistant", "content": "hello world", "stop_reason": "end_turn"},
    ])
    store = _InMemoryStore()
    loop = AgentLoop(llm=llm, tools={}, store=store, plugins=[],
                     budget=IterationBudget(max=5))

    result = loop.run_conversation("hi", session_id="s1")

    assert result.final_text == "hello world"
    assert result.iterations == 1
    assert result.tool_calls == []
    assert result.stopped_by in ("end_turn", "complete")
    # User message + assistant message recorded.
    assert len(store.sessions["s1"]) == 2


def test_run_conversation_fires_plugin_hooks_in_order():
    AgentLoop, IterationBudget, _ = _import_loop()
    llm = _ScriptedLLM(queue=[
        {"role": "assistant", "content": "ok", "stop_reason": "end_turn"},
    ])
    plugin = _RecordingPlugin()
    loop = AgentLoop(llm=llm, tools={}, store=_InMemoryStore(),
                     plugins=[plugin], budget=IterationBudget(max=3))

    loop.run_conversation("hi", session_id="s1")

    assert plugin.events[0] == "on_session_start"
    assert "pre_llm_call" in plugin.events
    assert plugin.events[-1] == "on_session_end"


def test_run_conversation_dispatches_tool_calls_and_continues():
    AgentLoop, IterationBudget, _ = _import_loop()
    llm = _ScriptedLLM(queue=[
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "c1", "name": "echo", "arguments": {"text": "hi"}}],
            "stop_reason": "tool_use",
        },
        {"role": "assistant", "content": "echoed", "stop_reason": "end_turn"},
    ])

    def echo(text: str) -> str:
        return f"ECHO:{text}"

    loop = AgentLoop(llm=llm, tools={"echo": echo}, store=_InMemoryStore(),
                     plugins=[], budget=IterationBudget(max=5))

    result = loop.run_conversation("hi", session_id="s1")
    assert result.final_text == "echoed"
    assert result.iterations == 2
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "echo"


def test_iteration_budget_caps_loop():
    AgentLoop, IterationBudget, _ = _import_loop()
    # An LLM that never yields end_turn.
    llm = _ScriptedLLM(queue=[
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": f"c{i}", "name": "echo", "arguments": {"text": "x"}}],
            "stop_reason": "tool_use",
        }
        for i in range(20)
    ])
    loop = AgentLoop(llm=llm, tools={"echo": lambda text: text},
                     store=_InMemoryStore(), plugins=[],
                     budget=IterationBudget(max=3))

    result = loop.run_conversation("go", session_id="s1")
    assert result.iterations <= 3
    assert result.stopped_by == "budget"


def test_post_tool_call_fires_with_result_after_each_tool_dispatch():
    """Hermes parity: ``post_tool_call(ctx)`` must fire after every dispatch.

    Contract (hermes-agent VALID_HOOKS): for every tool the loop runs,
    the plugin's ``post_tool_call`` is called exactly once *after* the
    dispatch returns, with:

    - ``ctx.tool_name``    — the tool that ran (same as the pre hook).
    - ``ctx.arguments``    — the args the tool was called with.
    - ``ctx.result``       — whatever the tool returned (or the
      ``{"error": ...}`` dict the loop synthesises on failure).
    - ``ctx.call_id``      — carried through from the pre hook so a
      plugin can correlate pre→post.

    The hook fires even when the tool raised — the loop turns that into
    a result dict, and the post hook still sees it. ``pre_tool_call``
    and ``post_tool_call`` must always appear in matched pairs.
    """
    AgentLoop, IterationBudget, _ = _import_loop()
    llm = _ScriptedLLM(queue=[
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "c1", "name": "echo", "arguments": {"text": "hi"}},
                {"id": "c2", "name": "echo", "arguments": {"text": "bye"}},
            ],
            "stop_reason": "tool_use",
        },
        {"role": "assistant", "content": "ok", "stop_reason": "end_turn"},
    ])

    def echo(text: str) -> str:
        return f"ECHO:{text}"

    plugin = _RecordingPlugin()
    loop = AgentLoop(
        llm=llm,
        tools={"echo": echo},
        store=_InMemoryStore(),
        plugins=[plugin],
        budget=IterationBudget(max=5),
    )

    loop.run_conversation("go", session_id="s1")

    # Two dispatches → two matched pre/post pairs.
    pre_events = [e for e in plugin.events if e.startswith("pre_tool_call:")]
    post_events = [e for e in plugin.events if e.startswith("post_tool_call:")]
    assert len(pre_events) == 2, (
        f"expected 2 pre_tool_call events, got {pre_events}"
    )
    assert len(post_events) == 2, (
        f"expected 2 post_tool_call events, got {post_events}"
    )

    # Ordering invariant: post always follows its pre, not before it.
    # Walk the event stream and assert alternation for tool events.
    tool_events = [e for e in plugin.events if ":" in e and e.split(":", 1)[0].endswith("_tool_call")]
    for i in range(0, len(tool_events), 2):
        assert tool_events[i].startswith("pre_tool_call:"), (
            f"pre must precede post in event stream, got {tool_events}"
        )
        assert tool_events[i + 1].startswith("post_tool_call:"), (
            f"post must follow pre in event stream, got {tool_events}"
        )

    # Result payload is delivered to the post hook.
    assert plugin.post_tool_results == [
        ("echo", "ECHO:hi"),
        ("echo", "ECHO:bye"),
    ]


def test_post_tool_call_fires_even_when_tool_raises():
    """A tool that raises still yields a post_tool_call with the error dict.

    The loop synthesises ``{"error": ..., "type": ...}`` for failures;
    plugins observing post hooks can therefore record every outcome,
    which is the entire reason hermes-agent exposes the hook.
    """
    AgentLoop, IterationBudget, _ = _import_loop()
    llm = _ScriptedLLM(queue=[
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "c1", "name": "boom", "arguments": {}}],
            "stop_reason": "tool_use",
        },
        {"role": "assistant", "content": "ok", "stop_reason": "end_turn"},
    ])

    def boom() -> str:
        raise ValueError("kaboom")

    plugin = _RecordingPlugin()
    loop = AgentLoop(
        llm=llm,
        tools={"boom": boom},
        store=_InMemoryStore(),
        plugins=[plugin],
        budget=IterationBudget(max=3),
    )

    loop.run_conversation("go", session_id="s1")

    assert any(e.startswith("post_tool_call:boom") for e in plugin.events), (
        "post_tool_call must still fire when the tool body raises"
    )
    # The result the hook saw is the synthesised error dict.
    assert plugin.post_tool_results, "post hook saw no result"
    name, result = plugin.post_tool_results[-1]
    assert name == "boom"
    assert isinstance(result, dict) and result.get("error") == "kaboom"


def test_keyboard_interrupt_from_plugin_stops_cleanly():
    AgentLoop, IterationBudget, _ = _import_loop()
    llm = _ScriptedLLM(queue=[
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "c1", "name": "echo", "arguments": {}}],
            "stop_reason": "tool_use",
        },
    ])

    class InterruptPlugin:
        def pre_tool_call(self, ctx) -> None:
            raise KeyboardInterrupt

    loop = AgentLoop(llm=llm, tools={"echo": lambda: "x"},
                     store=_InMemoryStore(), plugins=[InterruptPlugin()],
                     budget=IterationBudget(max=5))

    result = loop.run_conversation("go", session_id="s1")
    assert result.stopped_by == "interrupt"
