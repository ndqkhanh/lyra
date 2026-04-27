"""Wave-C Task 1: persistent ``/rewind`` + real ``/resume``.

The v1 stubs only mutated in-memory state. Wave-C upgrades them so:

1. The in-memory rewind still works (back-compat — existing tests
   that don't pass a ``sessions_root`` keep passing).
2. When a ``sessions_root`` is configured every dispatched turn is
   appended to ``<sessions_root>/<session_id>/turns.jsonl`` and a
   rewind truncates the last line so the JSONL is the single source
   of truth for "what's actually live".
3. ``InteractiveSession.resume_session(id, sessions_root=...)``
   reads the JSONL back and returns a session restored to the last
   recorded turn (mode, turn-counter, pending task, cost, tokens).
4. Asking to resume a non-existent id returns a friendly message
   (``None``-on-miss) instead of crashing.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lyra_cli.interactive.session import InteractiveSession


# ---- 1. Back-compat: in-memory rewind unchanged ----------------------

def test_rewind_in_memory_still_works(tmp_path: Path) -> None:
    """Without a ``sessions_root`` the session never touches disk."""
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("first plan thought")
    s.dispatch("second plan thought")
    snap = s.rewind_one()
    assert snap is not None
    assert snap.line == "second plan thought"
    assert s.turn == 1, "turn counter restored to pre-second state"
    # Nothing was written under ~/.lyra:
    assert not (tmp_path / ".lyra" / "sessions").exists()


# ---- 2. Rewind persisted to disk ------------------------------------

def test_rewind_truncates_persisted_jsonl(tmp_path: Path) -> None:
    """When ``sessions_root`` is set, /rewind shrinks the JSONL by one line."""
    sessions_root = tmp_path / ".lyra" / "sessions"
    s = InteractiveSession(
        repo_root=tmp_path,
        sessions_root=sessions_root,
        session_id="sess-001",
    )
    s.dispatch("alpha")
    s.dispatch("beta")
    s.dispatch("gamma")

    log = sessions_root / "sess-001" / "turns.jsonl"
    assert log.is_file(), "dispatch must persist when sessions_root is set"
    assert log.read_text(encoding="utf-8").strip().count("\n") == 2  # 3 lines

    snap = s.rewind_one()
    assert snap is not None and snap.line == "gamma"

    # File now has 2 lines (alpha + beta) — gamma was truncated.
    text = log.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    assert len(lines) == 2
    assert json.loads(lines[-1])["line"] == "beta"


# ---- 3. /resume restores full state ---------------------------------

def test_resume_session_restores_full_state(tmp_path: Path) -> None:
    """``resume_session`` rebuilds ``mode/turn/pending_task/cost/tokens`` from JSONL."""
    sessions_root = tmp_path / ".lyra" / "sessions"
    a = InteractiveSession(
        repo_root=tmp_path,
        sessions_root=sessions_root,
        session_id="sess-resumed",
    )
    a.dispatch("plan: investigate auth bug")
    a.dispatch("plan: write reproducer")
    a.dispatch("plan: ship fix")
    # Imitate the agent loop accumulating cost / tokens *between* turns
    # so we know the JSONL captured the post-turn state, not the pre.
    a.cost_usd = 0.42
    a.tokens_used = 1234

    # Force one more dispatch so the cost/tokens make it into the log:
    a.dispatch("plan: budget check")

    b = InteractiveSession.resume_session(
        session_id="sess-resumed",
        sessions_root=sessions_root,
        repo_root=tmp_path,
    )
    assert b is not None
    assert b.session_id == "sess-resumed"
    assert b.turn == a.turn, "turn counter restored"
    assert b.mode == a.mode, "mode restored"
    assert b.cost_usd == pytest.approx(a.cost_usd)
    assert b.tokens_used == a.tokens_used


# ---- 4. /resume <missing-id> friendly fallback -----------------------

def test_resume_missing_session_returns_none(tmp_path: Path) -> None:
    """Asking for a session that was never written returns ``None`` cleanly."""
    sessions_root = tmp_path / ".lyra" / "sessions"
    sessions_root.mkdir(parents=True)
    got = InteractiveSession.resume_session(
        session_id="never-existed",
        sessions_root=sessions_root,
        repo_root=tmp_path,
    )
    assert got is None
