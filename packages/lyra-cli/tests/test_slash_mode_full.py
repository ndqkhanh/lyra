"""Wave-C Task 7 + v3.6.0 update: full ``/mode`` dispatcher.

Behaviour exercised here:

* ``/mode list``   — enumerates every valid v3.6 mode + its short blurb.
* ``/mode toggle`` — advances through the same rotation as Tab.
* ``/mode edit_automatically`` — warns when the active permission mode
  is ``yolo``, since flipping to ``edit_automatically`` opens the
  full-access execution surface.
* ``/mode <bad>``  — preserves the v1 friendly error path.
* ``/mode``        — preserves the v1 "current mode" readout.
* ``/mode <legacy>`` — accepts every prior taxonomy name (v3.2:
  agent/plan/debug/ask; pre-v3.2: build/run/explore/retro) and remaps
  to the canonical v3.6 mode.
"""
from __future__ import annotations

from pathlib import Path

from lyra_cli.interactive.session import InteractiveSession


def test_mode_status_unchanged(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path, mode="plan_mode")
    out = s.dispatch("/mode").output
    assert "plan_mode" in out


def test_mode_set_valid_changes_mode(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path, mode="plan_mode")
    out = s.dispatch("/mode ask_before_edits").output
    assert s.mode == "ask_before_edits"
    assert "ask_before_edits" in out


def test_mode_list_enumerates_each_mode(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/mode list").output
    for name in ("edit_automatically", "ask_before_edits", "plan_mode", "auto_mode"):
        assert name in out


def test_mode_toggle_advances_one_step(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path, mode="plan_mode")
    out = s.dispatch("/mode toggle").output
    assert s.mode != "plan_mode"
    assert "→" in out or "->" in out


def test_mode_edit_automatically_warns_when_permission_yolo(tmp_path: Path) -> None:
    """Switching to ``edit_automatically`` while permissions are wide
    open is a footgun the dispatcher flags (v3.6 equivalent of the
    pre-v3.6 ``/mode agent`` yolo warning)."""
    s = InteractiveSession(repo_root=tmp_path, mode="plan_mode")
    s.permission_mode = "yolo"
    out = s.dispatch("/mode edit_automatically").output
    assert s.mode == "edit_automatically"
    # The warning must mention either "permission" or "yolo" so the
    # user notices the switch is unguarded.
    assert "permission" in out.lower() or "yolo" in out.lower()


def test_mode_build_alias_remaps_to_edit_automatically(tmp_path: Path) -> None:
    """Pre-v3.2 ``/mode build`` keeps working — remaps to v3.6
    ``edit_automatically`` and surfaces a one-line rename notice."""
    s = InteractiveSession(repo_root=tmp_path, mode="plan_mode")
    out = s.dispatch("/mode build").output
    assert s.mode == "edit_automatically"
    # User sees the rename so old muscle memory doesn't silently land
    # them in a different conceptual mode.
    # v3.7+: legacy aliases remap silently — the user typed a name they
    # know, the dispatcher honours it, no explanatory paragraph required.
    assert out.startswith("mode:")


def test_mode_agent_alias_remaps_to_edit_automatically(tmp_path: Path) -> None:
    """v3.2 ``/mode agent`` keeps working — remaps to v3.6
    ``edit_automatically`` and surfaces the rename notice."""
    s = InteractiveSession(repo_root=tmp_path, mode="plan_mode")
    out = s.dispatch("/mode agent").output
    assert s.mode == "edit_automatically"
    # v3.7+: legacy aliases remap silently — the user typed a name they
    # know, the dispatcher honours it, no explanatory paragraph required.
    assert out.startswith("mode:")


def test_mode_debug_alias_remaps_to_auto_mode(tmp_path: Path) -> None:
    """v3.2 ``/mode debug`` no longer exists; it's an alias of
    ``auto_mode`` so old muscle memory still lands somewhere live."""
    s = InteractiveSession(repo_root=tmp_path, mode="plan_mode")
    out = s.dispatch("/mode debug").output
    assert s.mode == "auto_mode"
    # v3.7+: legacy aliases remap silently — the user typed a name they
    # know, the dispatcher honours it, no explanatory paragraph required.
    assert out.startswith("mode:")


def test_mode_ask_alias_remaps_to_plan_mode(tmp_path: Path) -> None:
    """v3.2 ``/mode ask`` (read-only Q&A) remaps to ``plan_mode`` —
    the closest preserved read-only behaviour. (``ask_before_edits``
    is *not* the right target because it actively edits.)"""
    s = InteractiveSession(repo_root=tmp_path, mode="edit_automatically")
    out = s.dispatch("/mode ask").output
    assert s.mode == "plan_mode"
    # v3.7+: legacy aliases remap silently — the user typed a name they
    # know, the dispatcher honours it, no explanatory paragraph required.
    assert out.startswith("mode:")
