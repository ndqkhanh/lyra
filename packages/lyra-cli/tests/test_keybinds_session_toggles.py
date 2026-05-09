"""Wave-C Task 6: keybind handlers as pure session-toggle helpers.

Why pure helpers?
The prompt_toolkit binding layer is TTY-only and unhappy in CI. By
extracting each binding's *effect* into a pure function we can drive
the same behaviour from a test (and from the slash dispatcher when
someone wants ``/cycle-mode`` from a script). The TTY layer simply
imports these helpers and routes the key events to them.

Bindings under test:

* ``Ctrl+T`` → :func:`toggle_task_panel`
* ``Ctrl+O`` → :func:`toggle_verbose_tool_output`
* ``Esc Esc`` → :func:`rewind_one_persisted`
* ``Tab`` → :func:`cycle_mode` (edit_automatically → plan_mode →
  ask_before_edits → auto_mode → edit_automatically)
* ``Alt+T`` → :func:`toggle_deep_think`
* ``Alt+M`` → :func:`toggle_permission_mode`
"""
from __future__ import annotations

from pathlib import Path

from lyra_cli.interactive.keybinds import (
    cycle_mode,
    rewind_one_persisted,
    toggle_deep_think,
    toggle_permission_mode,
    toggle_task_panel,
    toggle_verbose_tool_output,
)
from lyra_cli.interactive.session import InteractiveSession


def test_toggle_task_panel_flips_bool(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path, task_panel=False)
    toast = toggle_task_panel(s)
    assert s.task_panel is True
    assert "task panel" in toast.lower()
    toggle_task_panel(s)
    assert s.task_panel is False


def test_toggle_verbose_tool_output_flips_bool(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path, verbose=False)
    toast = toggle_verbose_tool_output(s)
    assert s.verbose is True
    assert "verbose" in toast.lower()


def test_cycle_mode_iterates_full_taxonomy(tmp_path: Path) -> None:
    """Four ``Tab`` presses advance through the v3.6 4-mode rotation back to start."""
    s = InteractiveSession(repo_root=tmp_path, mode="edit_automatically")
    sequence = [s.mode]
    for _ in range(4):
        cycle_mode(s)
        sequence.append(s.mode)
    # The cycle must contain every valid v3.6 mode and return to the
    # start after exactly len(MODE_CYCLE) presses.
    assert {
        "edit_automatically",
        "plan_mode",
        "ask_before_edits",
        "auto_mode",
    } <= set(sequence)
    assert sequence[0] == sequence[-1] == "edit_automatically"


def test_toggle_deep_think(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path, deep_think=False)
    toggle_deep_think(s)
    assert s.deep_think is True


def test_toggle_permission_mode_cycles_strict_normal_yolo(tmp_path: Path) -> None:
    """``Alt+M`` cycles permission mode through three states."""
    s = InteractiveSession(repo_root=tmp_path)
    seen = {getattr(s, "permission_mode", "normal")}
    for _ in range(3):
        toggle_permission_mode(s)
        seen.add(s.permission_mode)
    # All three settings must appear within three rotations.
    assert {"strict", "normal", "yolo"} <= seen


def test_rewind_one_persisted_falls_back_when_log_empty(tmp_path: Path) -> None:
    """``Esc Esc`` on a virgin session is a no-op with friendly toast."""
    s = InteractiveSession(repo_root=tmp_path)
    msg = rewind_one_persisted(s)
    assert "nothing" in msg.lower()


def test_rewind_one_persisted_replays_a_real_turn(tmp_path: Path) -> None:
    """``Esc Esc`` after a dispatched turn pops it (and shrinks JSONL)."""
    sessions_root = tmp_path / ".lyra" / "sessions"
    s = InteractiveSession(
        repo_root=tmp_path,
        sessions_root=sessions_root,
        session_id="kb-rewind",
    )
    s.dispatch("first")
    s.dispatch("second")
    msg = rewind_one_persisted(s)
    assert s.turn == 1
    assert "rewound" in msg.lower() or "rewind" in msg.lower()
    log = sessions_root / "kb-rewind" / "turns.jsonl"
    text = log.read_text(encoding="utf-8")
    assert "second" not in text
