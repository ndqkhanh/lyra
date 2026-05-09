"""Phase I (v3.0.0): ``/redo`` — opencode parity for ``revert/unrevert``.

Locked surface:

1. ``redo_one`` returns the snapshot popped by ``rewind_one`` and
   restores ``mode/turn/cost/tokens/pending_task`` to the post-turn
   state.
2. ``/redo`` with an empty stack is a friendly no-op.
3. A new plain-text turn drains the redo stack so a stale ``/redo``
   can never resurrect the pre-divergence state.
4. ``/rewind`` followed by ``/redo`` round-trips persisted JSONL — the
   on-disk turn count must end equal to the pre-rewind count.
"""
from __future__ import annotations

from pathlib import Path

from lyra_cli.interactive.session import InteractiveSession


def test_redo_empty_stack_is_friendly(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/redo")
    assert "nothing to redo" in out.output.lower()


def test_redo_replays_rewind(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("alpha")
    s.dispatch("beta")
    pre_turn = s.turn
    s.dispatch("/rewind")
    assert s.turn == pre_turn - 1
    out = s.dispatch("/redo")
    assert "redid turn" in out.output.lower()
    assert s.turn == pre_turn, "redo must advance back to the pre-rewind turn"


def test_new_turn_drains_redo_stack(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("alpha")
    s.dispatch("/rewind")
    s.dispatch("beta")  # divergence — drains redo
    out = s.dispatch("/redo")
    assert "nothing to redo" in out.output.lower()


def test_redo_preserves_jsonl_count(tmp_path: Path) -> None:
    sessions_root = tmp_path / ".lyra" / "sessions"
    s = InteractiveSession(
        repo_root=tmp_path,
        sessions_root=sessions_root,
        session_id="sess-redo",
    )
    s.dispatch("alpha")
    s.dispatch("beta")
    s.dispatch("gamma")
    log = sessions_root / "sess-redo" / "turns.jsonl"
    pre = sum(1 for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip())
    s.dispatch("/rewind")
    s.dispatch("/redo")
    post = sum(1 for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip())
    assert pre == post, "rewind→redo must round-trip the persisted log"


def test_redo_alias_unrewind(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("alpha")
    s.dispatch("/rewind")
    out = s.dispatch("/unrewind")
    assert "redid turn" in out.output.lower()


def test_resume_drops_stale_redo_stack(tmp_path: Path) -> None:
    """A resumed session must not redo into the previous timeline."""
    sessions_root = tmp_path / ".lyra" / "sessions"
    a = InteractiveSession(
        repo_root=tmp_path,
        sessions_root=sessions_root,
        session_id="sess-a",
    )
    a.dispatch("alpha")
    a.dispatch("/rewind")
    assert a._redo_log, "rewind must populate the redo stack"

    # Build a second session on disk so /resume has a real target.
    b = InteractiveSession(
        repo_root=tmp_path,
        sessions_root=sessions_root,
        session_id="sess-b",
    )
    b.dispatch("beta")
    b.dispatch("gamma")

    a.dispatch("/resume sess-b")
    assert a._redo_log == [], "resume must drain the live redo stack"
    out = a.dispatch("/redo")
    assert "nothing to redo" in out.output.lower()
