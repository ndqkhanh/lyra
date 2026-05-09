"""Wave-D Task 1: ``SubagentRunner`` contract.

The runner is the *user-facing* thing the REPL spawns:

- One :class:`SubagentRunner` per spawned subagent.
- Wraps a freshly-built :class:`AgentLoop` with a worktree-isolated
  CWD so file edits land under
  ``<repo>/.lyra/worktrees/<scope-id>/`` instead of the user's main
  checkout.
- Captures stdio (stdout / stderr) emitted during the loop into the
  :class:`SubagentRunResult` so the parent REPL can show them in
  ``/agents <id>``.
- Captures HIR events emitted during the loop into the same result
  so ``/blame`` / ``/trace`` see exactly what the child saw.
- Surfaces a typed status (``ok | failed | cancelled``) plus the
  child's :class:`TurnResult`.

These are the 6 RED tests the plan committed to.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from lyra_core.agent.loop import AgentLoop, IterationBudget


# ---------------------------------------------------------------------------
# Helpers — a deterministic LLM that emits one tool call then ends the turn.
# ---------------------------------------------------------------------------


class _ScriptedLLM:
    """LLM stub that returns a sequence of pre-baked responses."""

    def __init__(self, responses: list[dict]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def generate(self, messages: list[dict], **_kw: Any) -> dict:
        self.calls += 1
        if not self._responses:
            return {"content": "", "tool_calls": [], "stop_reason": "end_turn"}
        return self._responses.pop(0)


class _NoopStore:
    def append(self, *_a: Any, **_kw: Any) -> None:  # pragma: no cover
        pass


def _agent_loop_factory(
    llm: Any,
    tools: dict | None = None,
) -> AgentLoop:
    return AgentLoop(
        llm=llm,
        tools=tools or {},
        store=_NoopStore(),
        budget=IterationBudget(max=5),
    )


# ---------------------------------------------------------------------------
# Tests — every one references the runner via the public facade so a future
# refactor of the internals can't break the contract surface.
# ---------------------------------------------------------------------------


def test_runner_happy_path_returns_typed_result(tmp_path: Path) -> None:
    """A clean run completes with status=ok, captures the final text."""
    from lyra_core.subagent.runner import SubagentRunner, SubagentRunSpec

    llm = _ScriptedLLM([{"content": "all done", "tool_calls": [], "stop_reason": "end_turn"}])
    runner = SubagentRunner(
        loop_factory=lambda: _agent_loop_factory(llm),
        repo_root=tmp_path,
        worktree_root=tmp_path / "wt",
    )
    result = runner.run(SubagentRunSpec(scope_id="sub-001", description="say hi"))

    assert result.status == "ok"
    assert result.final_text == "all done"
    assert result.turn is not None
    assert result.turn.iterations == 1


def test_runner_creates_isolated_workdir(tmp_path: Path) -> None:
    """The runner allocates a worktree-style dir and exposes its path.

    We don't require a real ``git worktree`` here (sandbox blocks it);
    the runner accepts a ``worktree_root`` and creates a per-scope
    sub-directory under it.
    """
    from lyra_core.subagent.runner import SubagentRunner, SubagentRunSpec

    llm = _ScriptedLLM([{"content": "ok", "tool_calls": [], "stop_reason": "end_turn"}])
    runner = SubagentRunner(
        loop_factory=lambda: _agent_loop_factory(llm),
        repo_root=tmp_path,
        worktree_root=tmp_path / "wt",
    )
    result = runner.run(SubagentRunSpec(scope_id="sub-007", description="x"))

    assert result.workdir is not None
    assert result.workdir.exists()
    assert "sub-007" in result.workdir.name
    # The workdir lives under the configured root, not under repo_root.
    assert tmp_path / "wt" in result.workdir.parents


def test_runner_cancellation_yields_cancelled_status(tmp_path: Path) -> None:
    """A cancelled runner returns status=cancelled with no LLM round-trip."""
    from lyra_core.subagent.runner import SubagentRunner, SubagentRunSpec

    llm = _ScriptedLLM([{"content": "should not see", "tool_calls": [], "stop_reason": "end_turn"}])
    runner = SubagentRunner(
        loop_factory=lambda: _agent_loop_factory(llm),
        repo_root=tmp_path,
        worktree_root=tmp_path / "wt",
    )
    runner.cancel()
    result = runner.run(SubagentRunSpec(scope_id="sub-cancel", description="x"))

    assert result.status == "cancelled"
    assert llm.calls == 0


def test_runner_captures_tool_output(tmp_path: Path) -> None:
    """Tool calls executed inside the loop are exposed as ``tool_calls``."""
    from lyra_core.subagent.runner import SubagentRunner, SubagentRunSpec

    def _echo(text: str = "") -> dict:
        return {"echoed": text}

    llm = _ScriptedLLM([
        {
            "content": "calling tool",
            "tool_calls": [
                {"id": "c1", "name": "echo", "arguments": {"text": "hello"}},
            ],
            "stop_reason": "tool_use",
        },
        {"content": "did it", "tool_calls": [], "stop_reason": "end_turn"},
    ])
    runner = SubagentRunner(
        loop_factory=lambda: _agent_loop_factory(llm, tools={"echo": _echo}),
        repo_root=tmp_path,
        worktree_root=tmp_path / "wt",
    )
    result = runner.run(SubagentRunSpec(scope_id="sub-tool", description="x"))

    assert result.status == "ok"
    assert any(c.get("name") == "echo" for c in result.turn.tool_calls)


def test_runner_propagates_loop_failure_as_failed(tmp_path: Path) -> None:
    """A loop that explodes surfaces status=failed + an error message."""
    from lyra_core.subagent.runner import SubagentRunner, SubagentRunSpec

    class _ExplodingLLM:
        def generate(self, *_a: Any, **_kw: Any) -> dict:
            raise RuntimeError("kaboom")

    runner = SubagentRunner(
        loop_factory=lambda: _agent_loop_factory(_ExplodingLLM()),
        repo_root=tmp_path,
        worktree_root=tmp_path / "wt",
    )
    result = runner.run(SubagentRunSpec(scope_id="sub-boom", description="x"))

    assert result.status == "failed"
    assert "kaboom" in (result.error or "")


def test_runner_scopes_hir_events_to_session_id(tmp_path: Path) -> None:
    """Every HIR event emitted during the run carries the runner's session id.

    The runner installs its scope_id as the session id so the global
    HIR ring buffer (Wave-C T4) can filter to "events from sub-X" via
    a single attribute query, no per-call plumbing.
    """
    from lyra_core.hir.events import RingBuffer, emit
    from lyra_core.subagent.runner import SubagentRunner, SubagentRunSpec

    ring = RingBuffer(cap=64)
    try:
        llm = _ScriptedLLM([{"content": "ok", "tool_calls": [], "stop_reason": "end_turn"}])

        def _factory() -> AgentLoop:
            emit("test.runner.heartbeat", note="inside loop")
            return _agent_loop_factory(llm)

        runner = SubagentRunner(
            loop_factory=_factory,
            repo_root=tmp_path,
            worktree_root=tmp_path / "wt",
        )
        runner.run(SubagentRunSpec(scope_id="sub-hir", description="x"))

        matched = [
            ev for ev in ring.snapshot()
            if ev["attrs"].get("scope_id") == "sub-hir"
        ]
        assert matched, (
            f"expected at least one event scoped to sub-hir, saw: "
            f"{ring.snapshot()!r}"
        )
    finally:
        ring.detach()
