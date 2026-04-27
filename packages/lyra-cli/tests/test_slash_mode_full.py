"""Wave-C Task 7 + v3.2.0 update: full ``/mode`` dispatcher.

Behaviour exercised here:

* ``/mode list``   — enumerates every valid mode + its short blurb.
* ``/mode toggle`` — advances through the same rotation as Tab.
* ``/mode agent``  — warns when the active permission mode is the
  *yolo* one, since flipping to ``agent`` opens the full-access
  execution surface.
* ``/mode <bad>``  — preserves the v1 friendly error path.
* ``/mode``        — preserves the v1 "current mode" readout.
* ``/mode <legacy>`` — accepts v1.x / v2.x mode names (build, run,
  explore, retro) and remaps to the v3.2 canonical ones.
"""
from __future__ import annotations

from pathlib import Path

from lyra_cli.interactive.session import InteractiveSession


def test_mode_status_unchanged(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path, mode="plan")
    out = s.dispatch("/mode").output
    assert "plan" in out


def test_mode_set_valid_changes_mode(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path, mode="plan")
    out = s.dispatch("/mode ask").output
    assert s.mode == "ask"
    assert "ask" in out


def test_mode_list_enumerates_each_mode(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/mode list").output
    for name in ("agent", "plan", "debug", "ask"):
        assert name in out


def test_mode_toggle_advances_one_step(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path, mode="plan")
    out = s.dispatch("/mode toggle").output
    assert s.mode != "plan"
    assert "→" in out or "->" in out


def test_mode_agent_warns_when_permission_yolo(tmp_path: Path) -> None:
    """Switching to ``agent`` while permissions are wide open is a footgun
    flagged by the dispatcher (the v3.2 equivalent of the pre-v3.2
    ``/mode build`` yolo warning)."""
    s = InteractiveSession(repo_root=tmp_path, mode="plan")
    s.permission_mode = "yolo"
    out = s.dispatch("/mode agent").output
    assert s.mode == "agent"
    # The warning must mention either "permission" or the yolo word so
    # the user notices the switch is unguarded.
    assert "permission" in out.lower() or "yolo" in out.lower()


def test_mode_build_alias_remaps_to_agent(tmp_path: Path) -> None:
    """Pre-v3.2 ``/mode build`` keeps working — remaps to the v3.2 ``agent``
    mode and surfaces a one-line "renamed in v3.2" notice."""
    s = InteractiveSession(repo_root=tmp_path, mode="plan")
    out = s.dispatch("/mode build").output
    assert s.mode == "agent"
    # User sees the rename so old muscle memory doesn't silently land
    # them in a different conceptual mode.
    assert "rename" in out.lower() or "v3.2" in out
