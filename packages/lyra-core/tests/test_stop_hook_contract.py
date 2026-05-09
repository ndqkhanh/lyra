"""L312-1 — contract for the on_stop / ContinueLoop seam.

Anchor: ``docs/306-stop-hook-auto-continue-pattern.md``.

The seam fires after the LLM returns a message with no tool calls,
before ``run_conversation`` returns. A plugin's ``on_stop`` may raise
:class:`ContinueLoop` to re-feed the loop with a synthetic user turn,
up to :attr:`AgentLoop.max_stop_extensions` times.

Contract:

- ``StopCtx`` carries ``session_id``, ``iteration``, ``final_text``,
  ``stop_extensions``, and ``stop_hook_active``.
- First fire: ``stop_hook_active=False``, ``stop_extensions=0``.
- After a re-feed: next fire has ``stop_hook_active=True`` and
  ``stop_extensions=N``.
- Cap: a hook that always denies stops at ``max_stop_extensions`` and
  ``TurnResult.stopped_by == "stop_cap"``.
- Allow: a hook that does nothing → ``stopped_by == "end_turn"``.
- ``TurnResult.stop_extensions`` records how many re-feeds happened.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from lyra_core.agent.loop import (
    AgentLoop,
    ContinueLoop,
    IterationBudget,
    StopCtx,
    TurnResult,
)


@dataclass
class _ScriptedLLM:
    queue: list[dict]
    calls: list[dict] = field(default_factory=list)

    def generate(self, *, messages, tools=None, **kwargs) -> dict:
        self.calls.append({"messages": list(messages), "tools": tools})
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


def _make_llm_that_always_ends(content_per_turn: list[str]) -> _ScriptedLLM:
    """Return an LLM that emits one end_turn message per call from the given list."""
    return _ScriptedLLM(queue=[
        {"role": "assistant", "content": text, "stop_reason": "end_turn"}
        for text in content_per_turn
    ])


# --- 1. The seam exists and fires on natural end of turn ----------------- #


def test_on_stop_fires_when_model_returns_without_tool_calls():
    seen: list[StopCtx] = []

    class _Plugin:
        def on_stop(self, ctx: StopCtx) -> None:
            seen.append(ctx)

    llm = _make_llm_that_always_ends(["all done"])
    loop = AgentLoop(llm=llm, tools={}, store=_InMemoryStore(),
                     plugins=[_Plugin()], budget=IterationBudget(max=5))

    result = loop.run_conversation("hi", session_id="s1")

    assert result.stopped_by == "end_turn"
    assert result.stop_extensions == 0
    assert len(seen) == 1
    assert seen[0].session_id == "s1"
    assert seen[0].final_text == "all done"
    assert seen[0].stop_extensions == 0
    assert seen[0].stop_hook_active is False


# --- 2. ContinueLoop re-feeds the loop with the synthetic user turn ------ #


def test_continue_loop_re_feeds_with_user_message():
    fires: list[StopCtx] = []

    class _Plugin:
        def __init__(self) -> None:
            self._fired = 0

        def on_stop(self, ctx: StopCtx) -> None:
            fires.append(ctx)
            self._fired += 1
            if self._fired == 1:
                raise ContinueLoop(
                    user_message="Verify and continue.",
                    reason="auto-continue",
                )

    llm = _make_llm_that_always_ends(["I'm done", "OK actually done"])
    loop = AgentLoop(llm=llm, tools={}, store=_InMemoryStore(),
                     plugins=[_Plugin()], budget=IterationBudget(max=10))

    result = loop.run_conversation("go", session_id="s1")

    assert result.stop_extensions == 1
    assert result.stopped_by == "end_turn"
    # Two fires of on_stop.
    assert len(fires) == 2
    assert fires[0].stop_hook_active is False
    assert fires[0].stop_extensions == 0
    assert fires[1].stop_hook_active is True
    assert fires[1].stop_extensions == 1


# --- 3. Synthetic user message reaches the LLM messages -------------------- #


def test_continue_loop_message_visible_to_next_llm_call():
    class _Plugin:
        def __init__(self) -> None:
            self._fired = 0

        def on_stop(self, ctx: StopCtx) -> None:
            self._fired += 1
            if self._fired == 1:
                raise ContinueLoop(user_message="ACTUALLY-CONTINUE-PROBE")

    llm = _make_llm_that_always_ends(["first done", "second done"])
    loop = AgentLoop(llm=llm, tools={}, store=_InMemoryStore(),
                     plugins=[_Plugin()], budget=IterationBudget(max=5))
    loop.run_conversation("hi", session_id="s1")

    # Second LLM call should have seen the synthetic user turn.
    second_call_messages = llm.calls[1]["messages"]
    assert any(
        m["role"] == "user" and m["content"] == "ACTUALLY-CONTINUE-PROBE"
        for m in second_call_messages
    )


# --- 4. Infinite-deny → cap triggers, stopped_by=stop_cap ----------------- #


def test_buggy_always_continue_hook_caps_at_max_stop_extensions():
    """The canonical anti-infinite-loop guard."""
    class _BuggyPlugin:
        def on_stop(self, ctx: StopCtx) -> None:
            raise ContinueLoop(user_message="keep going")

    llm = _make_llm_that_always_ends(["done"] * 50)
    loop = AgentLoop(
        llm=llm, tools={}, store=_InMemoryStore(),
        plugins=[_BuggyPlugin()],
        budget=IterationBudget(max=100),
        max_stop_extensions=3,
    )

    result = loop.run_conversation("go", session_id="s1")

    assert result.stop_extensions == 3
    assert result.stopped_by == "stop_cap"


# --- 5. stop_hook_active=True on second-entry — hook can self-disable ----- #


def test_hook_self_disables_when_stop_hook_active_is_true():
    """The 2026 best-practice: check stop_hook_active and short-circuit."""
    fires: list[StopCtx] = []

    class _GoodPlugin:
        def on_stop(self, ctx: StopCtx) -> None:
            fires.append(ctx)
            if ctx.stop_hook_active:
                # Already extended once — let the loop terminate.
                return
            raise ContinueLoop(user_message="check verifier")

    llm = _make_llm_that_always_ends(["done", "done again"])
    loop = AgentLoop(llm=llm, tools={}, store=_InMemoryStore(),
                     plugins=[_GoodPlugin()], budget=IterationBudget(max=10),
                     max_stop_extensions=10)

    result = loop.run_conversation("go", session_id="s1")

    # First fire deny → re-feed; second fire allow → terminate.
    assert len(fires) == 2
    assert result.stop_extensions == 1
    assert result.stopped_by == "end_turn"


# --- 6. No on_stop hook → loop terminates as before ----------------------- #


def test_no_on_stop_plugin_terminates_immediately():
    llm = _make_llm_that_always_ends(["done"])
    loop = AgentLoop(llm=llm, tools={}, store=_InMemoryStore(),
                     plugins=[], budget=IterationBudget(max=5))
    result = loop.run_conversation("go", session_id="s1")
    assert result.stopped_by == "end_turn"
    assert result.stop_extensions == 0


# --- 7. Plugin returning normally (no raise) → loop terminates ------------ #


def test_on_stop_returning_none_lets_loop_terminate():
    class _PassivePlugin:
        def on_stop(self, ctx: StopCtx) -> None:
            return None

    llm = _make_llm_that_always_ends(["done"])
    loop = AgentLoop(llm=llm, tools={}, store=_InMemoryStore(),
                     plugins=[_PassivePlugin()], budget=IterationBudget(max=5))
    result = loop.run_conversation("go", session_id="s1")
    assert result.stopped_by == "end_turn"


# --- 8. Multiple plugins — first ContinueLoop wins, others not consulted -- #


def test_first_plugin_to_raise_continue_loop_wins():
    record: list[str] = []

    class _A:
        def on_stop(self, ctx: StopCtx) -> None:
            record.append("a")
            raise ContinueLoop(user_message="from-a")

    class _B:
        def on_stop(self, ctx: StopCtx) -> None:
            record.append("b")

    llm = _make_llm_that_always_ends(["done", "ok"])
    loop = AgentLoop(llm=llm, tools={}, store=_InMemoryStore(),
                     plugins=[_A(), _B()], budget=IterationBudget(max=5))
    loop.run_conversation("go", session_id="s1")

    # First call: A raised, B never ran. Second call: A re-checks.
    # Assert A always fires; B fires *zero* times (A short-circuits via raise).
    assert "a" in record
    assert "b" not in record


# --- 9. Cap-exhaustion does not affect budget accounting ------------------ #


def test_cap_exhaustion_preserves_iteration_count():
    class _AlwaysContinue:
        def on_stop(self, ctx: StopCtx) -> None:
            raise ContinueLoop(user_message="more")

    llm = _make_llm_that_always_ends(["x"] * 20)
    loop = AgentLoop(llm=llm, tools={}, store=_InMemoryStore(),
                     plugins=[_AlwaysContinue()], budget=IterationBudget(max=10),
                     max_stop_extensions=4)
    result = loop.run_conversation("go", session_id="s1")
    assert result.stop_extensions == 4
    assert result.stopped_by == "stop_cap"
    # 1 initial + 4 re-feeds = 5 LLM calls.
    assert result.iterations == 5


# --- 10. stop_extensions field on TurnResult is exposed ------------------- #


def test_turn_result_exposes_stop_extensions_field():
    assert "stop_extensions" in TurnResult().__dict__
    assert TurnResult().stop_extensions == 0


# --- 11. ContinueLoop carries reason for postmortem ----------------------- #


def test_continue_loop_carries_reason():
    err = ContinueLoop(user_message="x", reason="auto-continue: tests red")
    assert err.user_message == "x"
    assert err.reason == "auto-continue: tests red"


# --- 12. AgentLoop default max_stop_extensions matches plan --------------- #


def test_default_max_stop_extensions_is_five():
    llm = _make_llm_that_always_ends(["done"])
    loop = AgentLoop(llm=llm, tools={}, store=_InMemoryStore(), plugins=[],
                     budget=IterationBudget(max=5))
    assert loop.max_stop_extensions == 5
