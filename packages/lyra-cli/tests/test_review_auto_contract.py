"""Wave-F Task 9 — ``/review --auto`` post-turn verifier contract."""
from __future__ import annotations

from pathlib import Path

from lyra_cli.interactive.session import InteractiveSession, run_auto_review


def _session(tmp_path: Path) -> InteractiveSession:
    return InteractiveSession(repo_root=tmp_path)


def test_review_once_still_works(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = s.dispatch("/review")
    assert "post-turn /review" in res.output


def test_auto_status_default_off(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = s.dispatch("/review --auto status")
    assert "auto-review: off" in res.output


def test_auto_on_sets_flag(tmp_path: Path) -> None:
    s = _session(tmp_path)
    s.dispatch("/review --auto on")
    assert s.auto_review is True


def test_auto_off_clears_flag(tmp_path: Path) -> None:
    s = _session(tmp_path)
    s.dispatch("/review --auto on")
    s.dispatch("/review --auto off")
    assert s.auto_review is False


def test_auto_bad_arg_returns_usage(tmp_path: Path) -> None:
    s = _session(tmp_path)
    res = s.dispatch("/review --auto wobble")
    assert "usage" in res.output.lower()


def test_run_auto_review_returns_none_when_off(tmp_path: Path) -> None:
    s = _session(tmp_path)
    assert run_auto_review(s) is None


def test_run_auto_review_returns_banner_when_on(tmp_path: Path) -> None:
    s = _session(tmp_path)
    s.dispatch("/review --auto on")
    banner = run_auto_review(s)
    assert banner is not None
    assert "post-turn /review" in banner
