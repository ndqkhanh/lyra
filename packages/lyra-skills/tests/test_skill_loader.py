"""Red tests for the skill loader.

Contract:
    - Recursively walks ``search_paths``; for each directory that contains a
      ``SKILL.md``, parses YAML-frontmatter into ``SkillManifest`` and carries
      the body.
    - Later roots shadow earlier roots at the same skill id (user > workspace > shipped).
    - Skills without a frontmatter or with duplicate ids within a root error loudly.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_skills.loader import SkillLoaderError, load_skills


def _make_skill(root: Path, skill_path: str, *, name: str, description: str,
                body: str = "body", skill_id: str = "") -> None:
    d = root / skill_path
    d.mkdir(parents=True, exist_ok=True)
    sid = skill_id or d.name
    (d / "SKILL.md").write_text(
        f"---\nid: {sid}\nname: {name}\ndescription: {description}\n---\n{body}\n"
    )


def test_loader_discovers_single_skill(tmp_path: Path) -> None:
    _make_skill(tmp_path, "atomic/edit", name="Edit", description="small edits")
    skills = load_skills([tmp_path])
    assert len(skills) == 1
    assert skills[0].id == "edit"
    assert skills[0].name == "Edit"


def test_loader_discovers_multiple(tmp_path: Path) -> None:
    _make_skill(tmp_path, "a/edit", name="Edit", description="x", skill_id="edit")
    _make_skill(tmp_path, "a/review", name="Review", description="y", skill_id="review")
    skills = load_skills([tmp_path])
    assert {s.id for s in skills} == {"edit", "review"}


def test_user_root_shadows_shipped(tmp_path: Path) -> None:
    shipped = tmp_path / "shipped"
    user = tmp_path / "user"
    _make_skill(shipped, "edit", name="Shipped Edit", description="a", skill_id="edit")
    _make_skill(user, "edit", name="User Edit", description="b", skill_id="edit")
    skills = load_skills([shipped, user])  # later wins
    assert len(skills) == 1
    assert skills[0].name == "User Edit"


def test_missing_frontmatter_errors(tmp_path: Path) -> None:
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "SKILL.md").write_text("no frontmatter here")
    with pytest.raises(SkillLoaderError):
        load_skills([tmp_path])


def test_duplicate_id_in_same_root_errors(tmp_path: Path) -> None:
    _make_skill(tmp_path, "a/edit", name="a", description="z", skill_id="edit")
    _make_skill(tmp_path, "b/edit", name="b", description="z", skill_id="edit")
    with pytest.raises(SkillLoaderError):
        load_skills([tmp_path])
