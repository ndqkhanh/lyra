"""Phase 0 — RED for the hermes-style skill self-creation loop.

Contract (plan Phase 3):

- AgentLoop has a ``_iters_since_skill`` counter that increments each
  tool-loop iteration when ``skill_manage`` is in active tools.
- When the user turn ends, if the counter exceeds
  ``skill_nudge_interval`` (default 8), AgentLoop schedules a
  *background review*.
- The review is a ``ReviewJob`` submitted to ``AgentLoop.review_executor``
  — a ``concurrent.futures.Executor`` stored on the loop so tests can
  swap it for a synchronous one.
- Using ``skill_manage`` inside the loop resets the counter to 0.
- ``spawn_skill_review(loop)`` in ``lyra_skills.review.background``
  runs a forked AgentLoop with the ``_SKILL_REVIEW_PROMPT`` system
  message and returns the final text.
"""
from __future__ import annotations

from concurrent.futures import Executor, Future
from typing import Any, Callable

import pytest


def _import_pieces():
    try:
        from lyra_core.agent.loop import AgentLoop, IterationBudget
    except ModuleNotFoundError as exc:
        pytest.fail(f"lyra_core.agent.loop must exist ({exc})")
    try:
        from lyra_skills.review.background import spawn_skill_review
    except ModuleNotFoundError as exc:
        pytest.fail(f"lyra_skills.review.background.spawn_skill_review must exist ({exc})")
    return AgentLoop, IterationBudget, spawn_skill_review


class _SyncExecutor(Executor):
    """Runs submitted callables inline so the tests are deterministic."""

    def __init__(self) -> None:
        self.submitted: list[Callable] = []

    def submit(self, fn, /, *args, **kwargs) -> Future:  # noqa: D401
        self.submitted.append(fn)
        f: Future = Future()
        try:
            f.set_result(fn(*args, **kwargs))
        except BaseException as exc:  # noqa: BLE001
            f.set_exception(exc)
        return f


class _ScriptedLLM:
    def __init__(self, queue: list[dict]) -> None:
        self.queue = queue

    def generate(self, **kwargs) -> dict:
        if not self.queue:
            return {"role": "assistant", "content": "done", "stop_reason": "end_turn"}
        return self.queue.pop(0)


class _MinimalStore:
    def start_session(self, **_: Any) -> None: ...
    def append_message(self, **_: Any) -> None: ...


def _build_loop(queue: list[dict], tools: dict, *, nudge_interval: int, executor):
    AgentLoop, IterationBudget, _ = _import_pieces()
    return AgentLoop(
        llm=_ScriptedLLM(queue),
        tools=tools,
        store=_MinimalStore(),
        plugins=[],
        budget=IterationBudget(max=20),
        skill_nudge_interval=nudge_interval,
        review_executor=executor,
    )


def test_iters_since_skill_increments_on_each_tool_call():
    AgentLoop, _, _ = _import_pieces()
    queue = [
        {
            "role": "assistant", "content": "", "stop_reason": "tool_use",
            "tool_calls": [{"id": "c1", "name": "echo", "arguments": {}}],
        },
        {
            "role": "assistant", "content": "", "stop_reason": "tool_use",
            "tool_calls": [{"id": "c2", "name": "echo", "arguments": {}}],
        },
        {"role": "assistant", "content": "ok", "stop_reason": "end_turn"},
    ]
    tools = {"echo": lambda: "x", "skill_manage": lambda **_: "noop"}
    loop = _build_loop(queue, tools, nudge_interval=10, executor=_SyncExecutor())

    loop.run_conversation("go", session_id="s1")
    assert loop._iters_since_skill == 2


def test_skill_manage_tool_call_resets_counter():
    queue = [
        {
            "role": "assistant", "content": "", "stop_reason": "tool_use",
            "tool_calls": [{"id": "c1", "name": "echo", "arguments": {}}],
        },
        {
            "role": "assistant", "content": "", "stop_reason": "tool_use",
            "tool_calls": [{"id": "c2", "name": "skill_manage", "arguments": {"op": "list"}}],
        },
        {"role": "assistant", "content": "done", "stop_reason": "end_turn"},
    ]
    tools = {"echo": lambda: "x", "skill_manage": lambda **_: "ok"}
    loop = _build_loop(queue, tools, nudge_interval=10, executor=_SyncExecutor())

    loop.run_conversation("go", session_id="s1")
    assert loop._iters_since_skill == 0


def test_background_review_fires_when_counter_crosses_threshold():
    queue = [
        {
            "role": "assistant", "content": "", "stop_reason": "tool_use",
            "tool_calls": [{"id": f"c{i}", "name": "echo", "arguments": {}}],
        }
        for i in range(3)
    ] + [{"role": "assistant", "content": "done", "stop_reason": "end_turn"}]

    executor = _SyncExecutor()
    loop = _build_loop(
        queue,
        tools={"echo": lambda: "x", "skill_manage": lambda **_: "ok"},
        nudge_interval=2,  # very low so 3 iters definitely exceed
        executor=executor,
    )
    loop.run_conversation("go", session_id="s1")
    assert executor.submitted, (
        "AgentLoop must submit a background skill-review job when iters_since_skill "
        "exceeds skill_nudge_interval."
    )


def test_no_review_when_skill_manage_not_in_tools():
    queue = [
        {
            "role": "assistant", "content": "", "stop_reason": "tool_use",
            "tool_calls": [{"id": f"c{i}", "name": "echo", "arguments": {}}],
        }
        for i in range(3)
    ] + [{"role": "assistant", "content": "done", "stop_reason": "end_turn"}]

    executor = _SyncExecutor()
    loop = _build_loop(
        queue,
        tools={"echo": lambda: "x"},  # skill_manage intentionally absent
        nudge_interval=1,
        executor=executor,
    )
    loop.run_conversation("go", session_id="s1")
    assert executor.submitted == [], (
        "Without skill_manage wired in, the nudge counter must not trigger reviews."
    )


def test_spawn_skill_review_runs_forked_loop():
    _, _, spawn_skill_review = _import_pieces()
    queue = [{"role": "assistant", "content": "learned", "stop_reason": "end_turn"}]
    loop = _build_loop(
        queue, tools={"skill_manage": lambda **_: "ok"},
        nudge_interval=1, executor=_SyncExecutor(),
    )
    out = spawn_skill_review(loop, session_id="parent")
    assert isinstance(out, str)
    assert out  # non-empty
