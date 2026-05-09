"""Subagent durability — EternalAgentLoop as drop-in for AgentLoop."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from lyra_cli.eternal_factory import make_eternal_loop, make_eternal_loop_factory


class _NoopStore:
    def append_message(self, **_) -> None:
        return None


class _StubLLM:
    def __init__(self, content: str = "subagent reply"):
        self._content = content
        self.calls = 0

    def generate(self, *, messages, **kwargs):
        self.calls += 1
        return {"content": self._content, "tool_calls": [], "stop_reason": "end_turn"}


class _StubLoop:
    """AgentLoop-shaped stub with a plain ``run_conversation`` method."""

    def __init__(self, llm=None, tools=None, store=None, reply: str = "ok"):
        self.llm = llm if llm is not None else _StubLLM(reply)
        self.tools = tools if tools is not None else {}
        self.store = store if store is not None else _NoopStore()
        self._reply = reply

    def run_conversation(self, user_text: str, *, session_id: str):
        class TR:
            final_text = f"sub:{user_text[:8]}:{self._reply}"
            iterations = 1
            tool_calls = []
            stopped_by = "end_turn"

        return TR


# ---------------------------------------------------------------------------
# EternalAgentLoop duck-types as AgentLoop
# ---------------------------------------------------------------------------


def test_eternal_loop_has_run_conversation_method(tmp_path: Path) -> None:
    eternal = make_eternal_loop(_StubLoop(), state_dir=tmp_path)
    assert hasattr(eternal, "run_conversation")
    assert hasattr(eternal, "run_conversation_durable")


def test_run_conversation_returns_turn_view(tmp_path: Path) -> None:
    eternal = make_eternal_loop(_StubLoop(reply="hello"), state_dir=tmp_path)
    view = eternal.run_conversation("test", session_id="s")
    assert hasattr(view, "final_text")
    assert hasattr(view, "iterations")
    assert hasattr(view, "tool_calls")
    assert hasattr(view, "stopped_by")
    # The view's final_text comes from the underlying _StubLoop.
    assert view.final_text.startswith("sub:test")


def test_run_conversation_reflects_quarantine_in_view(tmp_path: Path) -> None:
    """When the breaker quarantines the workflow, the AgentLoop-shaped view
    surfaces ``stopped_by="quarantined"`` rather than crashing the caller."""
    from harness_eternal import CircuitBreaker
    from lyra_core.agent.eternal_turn import EternalAgentLoop
    from harness_eternal.restate import LocalRuntime

    runtime = LocalRuntime(tmp_path / "rt")
    breaker = CircuitBreaker(after=1)
    breaker.record_failure("lyra.test")  # pre-trip the breaker

    eternal = EternalAgentLoop(
        loop=_StubLoop(),
        runtime=runtime,
        breaker=breaker,
        deadline_per_turn_s=10,
        workflow_name="lyra.test",
    )
    view = eternal.run_conversation("hi", session_id="s")
    assert view.stopped_by == "quarantined"
    assert view.final_text == ""


# ---------------------------------------------------------------------------
# make_eternal_loop_factory
# ---------------------------------------------------------------------------


def test_factory_returns_callable(tmp_path: Path) -> None:
    factory = make_eternal_loop_factory(
        lambda: _StubLoop(), state_dir=tmp_path, workflow_name="lyra.spawn"
    )
    assert callable(factory)
    eternal = factory()
    assert eternal.workflow_name == "lyra.spawn"


def test_factory_shares_runtime_across_calls(tmp_path: Path) -> None:
    """Two spawns from the same factory journal into the same SQLite."""
    factory = make_eternal_loop_factory(
        lambda: _StubLoop(reply="a"), state_dir=tmp_path,
    )
    e1 = factory()
    e2 = factory()
    e1.run_conversation("first", session_id="s1")
    e2.run_conversation("second", session_id="s2")

    db = tmp_path / "restate" / "journal.sqlite3"
    conn = sqlite3.connect(db.as_posix())
    inv_count = conn.execute("SELECT COUNT(*) FROM invocations").fetchone()[0]
    conn.close()
    assert inv_count == 2


# ---------------------------------------------------------------------------
# End-to-end with SubagentRunner
# ---------------------------------------------------------------------------


def test_subagent_runner_works_with_eternal_factory(tmp_path: Path) -> None:
    """The crucial integration test: SubagentRunner doesn't know it's
    getting an EternalAgentLoop — but every spawn journals."""
    from lyra_core.subagent.runner import SubagentRunner, SubagentRunSpec

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    state_dir = tmp_path / "eternal"

    factory = make_eternal_loop_factory(
        lambda: _StubLoop(reply="spawn-ok"),
        state_dir=state_dir,
        workflow_name="lyra.spawn",
    )

    runner = SubagentRunner(
        loop_factory=factory,
        repo_root=repo_root,
        worktree_root=repo_root / ".lyra" / "worktrees",
        use_git_worktree=False,  # avoid git dependency in tmp_path
    )

    result = runner.run(SubagentRunSpec(
        scope_id="sub-001",
        description="investigate the failing test",
    ))
    assert result.status == "ok"
    assert "sub:" in result.final_text or "spawn-ok" in result.final_text

    # Verify journal contains the spawn.
    db = state_dir / "restate" / "journal.sqlite3"
    assert db.exists()
    conn = sqlite3.connect(db.as_posix())
    workflows = [
        row[0] for row in conn.execute("SELECT DISTINCT workflow_name FROM invocations")
    ]
    conn.close()
    assert "lyra.spawn" in workflows


def test_subagent_runner_records_each_spawn_separately(tmp_path: Path) -> None:
    """Each /spawn run is its own invocation — three spawns → three rows."""
    from lyra_core.subagent.runner import SubagentRunner, SubagentRunSpec

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    state_dir = tmp_path / "eternal"

    factory = make_eternal_loop_factory(
        lambda: _StubLoop(reply="ok"), state_dir=state_dir,
    )
    runner = SubagentRunner(
        loop_factory=factory, repo_root=repo_root,
        worktree_root=repo_root / ".lyra" / "worktrees", use_git_worktree=False,
    )

    for i in range(3):
        runner.run(SubagentRunSpec(
            scope_id=f"sub-{i:03d}", description=f"task-{i}",
        ))

    db = state_dir / "restate" / "journal.sqlite3"
    conn = sqlite3.connect(db.as_posix())
    inv_count = conn.execute("SELECT COUNT(*) FROM invocations").fetchone()[0]
    conn.close()
    assert inv_count == 3
