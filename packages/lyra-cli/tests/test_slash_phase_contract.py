"""Wave-F Task 1 — ``/phase`` slash command contract."""
from __future__ import annotations

from pathlib import Path

from lyra_cli.interactive.session import InteractiveSession


def _session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(repo_root=tmp_path)


def test_phase_status_default_is_idle(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = s.dispatch("/phase")
    assert "tdd phase: idle" in res.output
    assert "legal next" in res.output


def test_phase_set_plan_lenient_mode(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = s.dispatch("/phase set plan")
    assert "tdd phase: plan" in res.output


def test_phase_set_unknown_is_friendly(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = s.dispatch("/phase set cosmic")
    assert "unknown phase" in res.output


def test_phase_next_legal_lists_plan_from_idle(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = s.dispatch("/phase next-legal")
    assert res.output.strip() == "plan"


def test_phase_reset_returns_to_idle(tmp_path: Path) -> None:
    s = _session(tmp_path)
    s.dispatch("/phase set plan")
    res = s.dispatch("/phase reset")
    assert "idle" in res.output


def test_phase_unknown_arg_shows_usage(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = s.dispatch("/phase wobble")
    assert "usage" in res.output
