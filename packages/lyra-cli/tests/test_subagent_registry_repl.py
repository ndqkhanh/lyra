"""Wave-D Task 2: ``/agents`` becomes a live process table.

Today ``/agents`` prints a static set of *kinds* of subagents
("explore", "plan", …). Wave-D promotes it to a live process table
backed by :class:`lyra_core.subagent.SubagentRegistry`:

- :class:`InteractiveSession` gains a ``subagent_registry`` field.
- ``/agents`` (no args) lists every spawned record with id, state,
  description, and (when present) the running ETA.
- ``/agents kill <id>`` cancels a *pending* record (matches the
  registry's :meth:`SubagentRegistry.cancel` semantics).
- ``Ctrl+F`` (``c-f``) re-focuses the foreground subagent — the
  ``focus_foreground_subagent`` helper in :mod:`._keybinds` updates
  ``InteractiveSession.focused_subagent`` to the most recent record,
  or to ``None`` when there are no live agents.

These are the 5 RED tests the Wave-D plan committed to.
"""
from __future__ import annotations

from pathlib import Path

from lyra_core.subagent import SubagentRegistry

from lyra_cli.interactive.keybinds import focus_foreground_subagent
from lyra_cli.interactive.session import InteractiveSession


def _seed_registry(*, count: int = 2) -> SubagentRegistry:
    def _task(desc: str, **_kw: object) -> dict:
        return {"final_text": f"done: {desc}", "stopped_by": "end_turn"}

    reg = SubagentRegistry(task=_task)
    for n in range(count):
        reg.spawn(f"task #{n + 1}")
    return reg


def _new_session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(repo_root=tmp_path)


def test_session_carries_subagent_registry(tmp_path: Path) -> None:
    """``InteractiveSession`` exposes a ``subagent_registry`` field."""
    s = _new_session(tmp_path)
    assert hasattr(s, "subagent_registry")
    s.subagent_registry = _seed_registry(count=1)
    assert s.subagent_registry.list_all()[0].state == "done"


def test_slash_agents_lists_live_records(tmp_path: Path) -> None:
    """``/agents`` renders one row per spawned record (id, state, desc)."""
    s = _new_session(tmp_path)
    s.subagent_registry = _seed_registry(count=2)
    out = s.dispatch("/agents").output
    assert "sub-0001" in out
    assert "sub-0002" in out
    assert "done" in out
    assert "task #1" in out


def test_slash_agents_kill_cancels_pending(tmp_path: Path) -> None:
    """``/agents kill <id>`` flips a pending record to ``cancelled``."""
    s = _new_session(tmp_path)
    reg = SubagentRegistry(task=lambda *_a, **_kw: {"final_text": "x"})
    rec = reg.reserve("slow task")  # pending, never dispatched
    s.subagent_registry = reg
    out = s.dispatch(f"/agents kill {rec.id}").output
    assert "cancelled" in out.lower() or "killed" in out.lower()
    assert reg.get(rec.id).state == "cancelled"


def test_slash_agents_kill_unknown_id_is_friendly(tmp_path: Path) -> None:
    s = _new_session(tmp_path)
    s.subagent_registry = _seed_registry(count=1)
    out = s.dispatch("/agents kill sub-9999").output.lower()
    assert "no such" in out or "unknown" in out


def test_focus_foreground_subagent_picks_most_recent_running(
    tmp_path: Path,
) -> None:
    """``focus_foreground_subagent`` (Ctrl+F handler) sets ``.focused_subagent``."""
    s = _new_session(tmp_path)
    reg = SubagentRegistry(task=lambda *_a, **_kw: {"final_text": "x"})
    a = reg.reserve("a")  # pending
    b = reg.reserve("b")  # pending
    s.subagent_registry = reg
    focus_foreground_subagent(s)
    assert s.focused_subagent in (a.id, b.id)
    assert s.focused_subagent == b.id  # most recent wins
