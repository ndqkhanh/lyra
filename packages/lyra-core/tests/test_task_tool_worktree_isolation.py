"""Worktree isolation contract for the ``task`` tool (v1 Phase 7 block 10).

A forked subagent should optionally run inside a git worktree that the
parent repo allocates for it, so that any file writes, failed patches
or half-finished state do not contaminate the parent checkout. Cleanup
must be deterministic even when the subagent raises.

This test locks the *contract* — not the real git behaviour (a real
``git init`` is unavailable in sandboxed CI temp dirs). We inject a
fake manager that records ``allocate`` / ``cleanup`` in order.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

from lyra_core.tools.task import make_task_tool


# -- fakes ------------------------------------------------------------------

@dataclass
class _FakeWorktree:
    scope_id: str
    path: Path
    branch: str


@dataclass
class _FakeManager:
    repo_root: Path
    calls: list[tuple[str, str]] = field(default_factory=list)

    def allocate(self, *, scope_id: str) -> _FakeWorktree:
        self.calls.append(("allocate", scope_id))
        wt_path = self.repo_root / f".lyra/worktrees/{scope_id}"
        wt_path.mkdir(parents=True, exist_ok=True)
        return _FakeWorktree(scope_id=scope_id, path=wt_path, branch=f"lyra/{scope_id}")

    def cleanup(self, wt: _FakeWorktree) -> None:
        self.calls.append(("cleanup", wt.scope_id))


class _StubLLM:
    def generate(self, *, messages, tools=None, **kwargs):  # noqa: D401 - stub
        return {"role": "assistant", "content": "done", "stop_reason": "end_turn"}


class _StubStore:
    def __init__(self) -> None:
        self.sessions: dict[str, list[dict]] = {}

    def start_session(self, *, session_id: str, **_: Any) -> None:
        self.sessions.setdefault(session_id, [])

    def append_message(self, *, session_id: str, role: str, content: str,
                       tool_calls=None, **_: Any) -> None:
        self.sessions.setdefault(session_id, []).append(
            {"role": role, "content": content, "tool_calls": tool_calls or []}
        )


# -- tests ------------------------------------------------------------------

def test_task_tool_accepts_worktree_flag_and_allocates(tmp_path: Path) -> None:
    mgr = _FakeManager(repo_root=tmp_path)
    tool = make_task_tool(
        llm=_StubLLM(),
        tools=None,
        store=_StubStore(),
        worktree_manager=mgr,
    )
    result = tool("triage perf regression", worktree=True)
    assert "stopped_by" in result
    scopes_allocated = [s for op, s in mgr.calls if op == "allocate"]
    assert len(scopes_allocated) == 1, mgr.calls


def test_task_tool_cleans_up_worktree_on_success(tmp_path: Path) -> None:
    mgr = _FakeManager(repo_root=tmp_path)
    tool = make_task_tool(
        llm=_StubLLM(),
        tools=None,
        store=_StubStore(),
        worktree_manager=mgr,
    )
    tool("simple task", worktree=True)
    ops = [op for op, _ in mgr.calls]
    assert ops == ["allocate", "cleanup"], ops


def test_task_tool_cleans_up_worktree_on_failure(tmp_path: Path) -> None:
    class _BoomLLM:
        def generate(self, *, messages, tools=None, **kwargs):
            raise RuntimeError("llm blew up")

    mgr = _FakeManager(repo_root=tmp_path)
    tool = make_task_tool(
        llm=_BoomLLM(),
        tools=None,
        store=_StubStore(),
        worktree_manager=mgr,
    )
    with pytest.raises(RuntimeError):
        tool("doomed task", worktree=True)

    ops = [op for op, _ in mgr.calls]
    assert ops == ["allocate", "cleanup"], (
        "cleanup MUST run even when the child agent raises; "
        f"got: {ops}"
    )


def test_task_tool_no_worktree_no_manager_calls(tmp_path: Path) -> None:
    """Back-compat: worktree=False (default) must never touch the manager."""
    mgr = _FakeManager(repo_root=tmp_path)
    tool = make_task_tool(
        llm=_StubLLM(),
        tools=None,
        store=_StubStore(),
        worktree_manager=mgr,
    )
    tool("no isolation needed")
    assert mgr.calls == []


def test_task_tool_worktree_without_manager_raises_clear_error(tmp_path: Path) -> None:
    """If the caller asks for isolation but didn't wire a manager, fail loudly."""
    tool = make_task_tool(llm=_StubLLM(), tools=None, store=_StubStore())
    with pytest.raises(ValueError, match="worktree_manager"):
        tool("need isolation but no manager", worktree=True)
