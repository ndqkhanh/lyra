"""State-filter coverage for the SKILL.md injection layer.

Phase /skills picker (this branch): adds an optional ``state`` kwarg
to :func:`render_skill_block` and
:func:`render_skill_block_with_activations` so per-skill overrides
written by the picker are honoured before the advertised list and
activation block are computed.

Invariants pinned here:

* a skill in ``state.disabled`` is *not* in the rendered block,
* a locked skill (path under the packaged-pack root) is rendered
  even if it appears in ``state.disabled`` (defensive — the picker
  hides the toggle, so a value there can only come from a hand-edit),
* ``state=None`` keeps the legacy default-on behaviour (back-compat).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from lyra_cli.interactive.skills_inject import (
    render_skill_block,
    render_skill_block_with_activations,
)
from lyra_skills.state import SkillsState


def _write_skill(root: Path, sid: str, description: str = "do work.") -> None:
    sdir = root / sid
    sdir.mkdir(parents=True, exist_ok=True)
    (sdir / "SKILL.md").write_text(
        f"---\nid: {sid}\nname: {sid}\ndescription: {description}\n---\nbody.\n",
        encoding="utf-8",
    )


def test_disabled_skill_is_filtered_from_block(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """A skill in ``state.disabled`` must not appear in the advertised list."""
    project_skills = tmp_path / ".lyra" / "skills"
    project_skills.mkdir(parents=True)
    _write_skill(project_skills, "alpha")
    _write_skill(project_skills, "beta")
    # Hide packaged + user roots so only the project skills are surfaced.
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._packaged_pack_root",
        lambda: None,
    )
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._user_skill_root",
        lambda: None,
    )

    state = SkillsState(disabled=frozenset({"beta"}))
    block = render_skill_block(tmp_path, state=state)

    assert "- alpha" in block
    assert "- beta" not in block


def test_state_none_keeps_legacy_behaviour(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """``state=None`` (or omitted) means default-on for everything."""
    project_skills = tmp_path / ".lyra" / "skills"
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

    block_default = render_skill_block(tmp_path)
    block_explicit = render_skill_block(tmp_path, state=None)
    assert "- alpha" in block_default
    assert block_default == block_explicit


def test_locked_skill_cannot_be_disabled(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """Even if a packaged skill ends up in ``disabled`` (hand-edit), it
    is still advertised — the picker hides its toggle."""
    packaged_root = tmp_path / "pkg"
    packaged_root.mkdir()
    _write_skill(packaged_root, "shipped")

    project_skills = tmp_path / ".lyra" / "skills"
    project_skills.mkdir(parents=True)
    _write_skill(project_skills, "userland")

    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._packaged_pack_root",
        lambda: packaged_root,
    )
    monkeypatch.setattr(
        "lyra_cli.interactive.skills_inject._user_skill_root",
        lambda: None,
    )

    state = SkillsState(disabled=frozenset({"shipped", "userland"}))
    block = render_skill_block(tmp_path, state=state)

    assert "- shipped" in block, "locked skill must remain advertised"
    assert "- userland" not in block, "user skill in disabled is filtered"


def test_with_activations_path_also_honours_state(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    """The telemetry/ledger path uses the same filter."""
    project_skills = tmp_path / ".lyra" / "skills"
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

    state = SkillsState(disabled=frozenset({"alpha"}))
    result = render_skill_block_with_activations(tmp_path, state=state)

    assert "- alpha" not in result.text
    assert "- beta" in result.text
