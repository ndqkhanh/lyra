"""Slash-command coverage for the picker's programmatic siblings.

The interactive ``run_skills_dialog`` needs a TTY, but
``/skills enable <id>``, ``/skills disable <id>``, and ``/skills state``
should work everywhere — they're how scripts and headless sessions
flip a skill's state.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from lyra_cli.interactive.session import (
    InteractiveSession,
    SLASH_COMMANDS,
)
from lyra_skills.state import SkillsState, load_state


def _write_skill(root: Path, sid: str, description: str = "do work.") -> None:
    sdir = root / sid
    sdir.mkdir(parents=True, exist_ok=True)
    (sdir / "SKILL.md").write_text(
        f"---\nid: {sid}\nname: {sid}\ndescription: {description}\n---\nbody.\n",
        encoding="utf-8",
    )


def _make_session(repo_root: Path) -> InteractiveSession:
    return InteractiveSession(mode="ask", model="mock", repo_root=repo_root)


def _cmd_skills():
    """Resolve the slash-command handler. Tests pre-existing wiring."""
    return SLASH_COMMANDS["skills"]


def _isolated_lyra_home(tmp_path: Path, monkeypatch: Any) -> Path:
    """Point ``$LYRA_HOME`` at a tmp dir so state tests don't touch ``~``."""
    lyra_home = tmp_path / "lyra_home"
    lyra_home.mkdir()
    monkeypatch.setenv("LYRA_HOME", str(lyra_home))
    return lyra_home


def test_disable_subcommand_writes_state_and_invalidates_cache(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    project = tmp_path / "repo"
    project_skills = project / ".lyra" / "skills"
    project_skills.mkdir(parents=True)
    _write_skill(project_skills, "alpha")
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._packaged_pack_root",
        lambda: None,
    )
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._user_skill_root",
        lambda: None,
    )
    _isolated_lyra_home(tmp_path, monkeypatch)

    session = _make_session(project)
    session._cached_skill_block = "stale"

    result = _cmd_skills()(session, "disable alpha")
    assert "alpha" in result.output
    assert "disabled" in result.output

    state = load_state()
    assert "alpha" in state.disabled
    # Cache invalidated so the next turn re-renders
    assert session._cached_skill_block is None


def test_enable_subcommand_clears_disabled_entry(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    project = tmp_path / "repo"
    project_skills = project / ".lyra" / "skills"
    project_skills.mkdir(parents=True)
    _write_skill(project_skills, "alpha")
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._packaged_pack_root",
        lambda: None,
    )
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._user_skill_root",
        lambda: None,
    )
    _isolated_lyra_home(tmp_path, monkeypatch)

    session = _make_session(project)
    _cmd_skills()(session, "disable alpha")
    result = _cmd_skills()(session, "enable alpha")

    assert "alpha" in result.output
    assert load_state().disabled == frozenset()


def test_disable_unknown_skill_friendly_error(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    project = tmp_path / "repo"
    project.mkdir()
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._packaged_pack_root",
        lambda: None,
    )
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._user_skill_root",
        lambda: None,
    )
    _isolated_lyra_home(tmp_path, monkeypatch)

    session = _make_session(project)
    result = _cmd_skills()(session, "disable does-not-exist")
    assert "not found" in result.output.lower()


def test_disable_locked_skill_refuses(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """A packaged (locked) skill cannot be disabled via /skills disable."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    _write_skill(pkg, "shipped")
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._packaged_pack_root",
        lambda: pkg,
    )
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._user_skill_root",
        lambda: None,
    )
    _isolated_lyra_home(tmp_path, monkeypatch)

    session = _make_session(tmp_path / "repo-empty")
    (tmp_path / "repo-empty").mkdir()
    result = _cmd_skills()(session, "disable shipped")

    assert "bundled" in result.output.lower()
    assert "lyra skill remove" in result.output
    assert load_state().disabled == frozenset()


def test_state_subcommand_default_is_pristine(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    _isolated_lyra_home(tmp_path, monkeypatch)
    project = tmp_path / "repo"
    project.mkdir()
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._packaged_pack_root",
        lambda: None,
    )
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._user_skill_root",
        lambda: None,
    )

    session = _make_session(project)
    result = _cmd_skills()(session, "state")
    assert "no skill overrides" in result.output.lower()


def test_state_subcommand_lists_disabled(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    project = tmp_path / "repo"
    project_skills = project / ".lyra" / "skills"
    project_skills.mkdir(parents=True)
    _write_skill(project_skills, "alpha")
    _write_skill(project_skills, "beta")
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._packaged_pack_root",
        lambda: None,
    )
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._user_skill_root",
        lambda: None,
    )
    _isolated_lyra_home(tmp_path, monkeypatch)

    session = _make_session(project)
    _cmd_skills()(session, "disable alpha")
    _cmd_skills()(session, "disable beta")
    result = _cmd_skills()(session, "state")

    assert "alpha" in result.output
    assert "beta" in result.output
    assert "disabled" in result.output


def test_unknown_subcommand_lists_picker_options(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """The error text should advertise the new /skills pick verb."""
    _isolated_lyra_home(tmp_path, monkeypatch)
    session = _make_session(tmp_path)
    result = _cmd_skills()(session, "kaboom")
    assert "pick" in result.output
    assert "enable" in result.output
