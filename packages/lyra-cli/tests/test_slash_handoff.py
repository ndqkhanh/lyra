"""Wave-C Task 8: ``/handoff`` produces a paste-able PR description.

The render helper assembles four sections:

1. Title — the most recent user prompt (truncated at 80 chars).
2. Summary — the most recent plain-text turn (the v1 stub already
   tracked the turn; we now surface it).
3. Test plan — every history line containing ``test_*`` paths so a
   reviewer can replay the TDD trail.
4. Changelog bullet — ``git diff --stat``, gracefully degraded to
   "(no git in this environment)" outside a checkout.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_cli.interactive.handoff import render_handoff
from lyra_cli.interactive.session import InteractiveSession


def test_render_handoff_includes_all_four_sections(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("plan: investigate the failing test_login flow")
    s.dispatch("plan: write reproducer test_login_session_expiry")
    text = render_handoff(s, git_available=False)
    assert "## Title" in text or "# " in text
    assert "Summary" in text
    assert "Test plan" in text
    assert "Changelog" in text
    # The actual user prompts surface in the body somewhere.
    assert "test_login" in text


def test_render_handoff_no_git_falls_back_friendly(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    s.dispatch("plan: ship the fix")
    text = render_handoff(s, git_available=False)
    assert "no git" in text.lower() or "git unavailable" in text.lower()


def test_render_handoff_empty_session_warns(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    text = render_handoff(s, git_available=False)
    assert "no turns" in text.lower() or "empty session" in text.lower()


def test_render_handoff_truncates_long_title(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    huge = "plan: " + ("supercalifragilistic " * 30).strip()
    s.dispatch(huge)
    text = render_handoff(s, git_available=False, title_cap=80)
    title_line = next(
        line for line in text.splitlines() if line.startswith("## Title") or line.startswith("# ")
    )
    # The title body must not exceed the cap (one trailing ellipsis OK).
    title_body = title_line.split(":", 1)[-1].strip().lstrip("# ").strip()
    assert len(title_body) <= 85  # cap + a few chars for ellipsis
