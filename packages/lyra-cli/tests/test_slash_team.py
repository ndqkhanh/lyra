"""Phase J (v3.1.0): ``/team`` — MetaGPT-pattern role orchestration.

Locked surface:

1. ``/team`` lists every registered role with title + toolset.
2. ``/team show <name>`` describes one role's persona + SOP.
3. ``/team plan`` shows the default 5-step pipeline
   (PM → Architect → Engineer → Reviewer → QA).
4. ``/team run <task>`` assembles a multi-role brief spanning every
   role in the default plan, threading the user's task into the first
   role and the previous role's brief into the next.
5. ``/team show ghost`` is friendly; ``/team`` with bogus subcommand
   prints a usage hint.
"""
from __future__ import annotations

from pathlib import Path

from lyra_cli.interactive.session import InteractiveSession


def test_team_list_shows_all_roles(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/team")
    text = out.output
    for role in ("pm", "architect", "engineer", "reviewer", "qa"):
        assert role in text, f"missing role {role!r} in /team output"
    assert "Product Manager" in text
    assert "usage:" in text.lower()


def test_team_show_known_role_includes_sop(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/team show engineer")
    text = out.output
    assert "Engineer" in text
    assert "SOP:" in text
    assert "smallest" in text.lower()
    assert "toolset:" in text.lower()


def test_team_show_unknown_role_is_friendly(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/team show ghost")
    assert "unknown role" in out.output.lower()


def test_team_plan_lists_five_steps(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/team plan")
    text = out.output
    assert "team plan:" in text.lower()
    for step in ("pm", "architect", "engineer", "reviewer", "qa"):
        assert step in text


def test_team_run_assembles_multi_role_brief(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/team run build me a 2048 game")
    text = out.output
    assert "Team handoff brief" in text
    for title in (
        "Product Manager",
        "System Architect",
        "Engineer",
        "Reviewer",
        "QA / Tester",
    ):
        assert title in text
    assert "build me a 2048 game" in text
    assert text.count("---") >= 5


def test_team_run_requires_task(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/team run")
    assert "usage:" in out.output.lower()


def test_team_unknown_subcommand_is_friendly(tmp_path: Path) -> None:
    s = InteractiveSession(repo_root=tmp_path)
    out = s.dispatch("/team nonsense")
    assert "usage:" in out.output.lower()
