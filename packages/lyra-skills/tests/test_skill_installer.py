"""Tests for :mod:`lyra_skills.installer` (Phase N.3)."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_skills.installer import (
    InstallResult,
    SkillInstallError,
    install_from_path,
    list_installed,
    remove_installed,
)


def _write_skill(
    src: Path, *, sid: str, name: str = "T", desc: str = "d",
    extra_fm: str = "", body: str = "body",
) -> None:
    """Build ``src/<sid>/SKILL.md`` with optional extra frontmatter lines."""
    skill_dir = src / sid
    skill_dir.mkdir(parents=True, exist_ok=True)
    fm = f"id: {sid}\nname: {name}\ndescription: {desc}\n"
    if extra_fm:
        fm += extra_fm.rstrip("\n") + "\n"
    (skill_dir / "SKILL.md").write_text(f"---\n{fm}---\n{body}\n")


# ---------------------------------------------------------------------------
# Frontmatter — extended fields
# ---------------------------------------------------------------------------


def test_loader_parses_extended_frontmatter(tmp_path: Path) -> None:
    """All Phase N.3 fields populate the manifest correctly."""
    from lyra_skills.loader import load_skills

    extra = (
        "version: 1.2.3\n"
        "keywords: [refactor, shrink, surgical]\n"
        "applies_to: [\"**/*.py\", \"tests/**\"]\n"
        "requires: [pytest, black]\n"
        "progressive: true\n"
        "custom_field: kept\n"
    )
    _write_skill(tmp_path, sid="surgery", extra_fm=extra)
    skills = load_skills([tmp_path])
    assert len(skills) == 1
    s = skills[0]
    assert s.id == "surgery"
    assert s.version == "1.2.3"
    assert s.keywords == ["refactor", "shrink", "surgical"]
    assert s.applies_to == ["**/*.py", "tests/**"]
    assert s.requires == ["pytest", "black"]
    assert s.progressive is True
    assert s.extras == {"custom_field": "kept"}


def test_loader_accepts_scalar_keywords(tmp_path: Path) -> None:
    """Scalar form ``keywords: foo`` is sugar for ``keywords: [foo]``."""
    from lyra_skills.loader import load_skills

    _write_skill(tmp_path, sid="solo", extra_fm="keywords: just-one")
    skills = load_skills([tmp_path])
    assert skills[0].keywords == ["just-one"]


def test_loader_rejects_invalid_keyword_types(tmp_path: Path) -> None:
    """A non-string keyword is a hard error, not a silent skip."""
    from lyra_skills.loader import SkillLoaderError, load_skills

    _write_skill(tmp_path, sid="bad", extra_fm="keywords: [42]")
    with pytest.raises(SkillLoaderError):
        load_skills([tmp_path])


def test_loader_rejects_non_bool_progressive(tmp_path: Path) -> None:
    from lyra_skills.loader import SkillLoaderError, load_skills

    _write_skill(tmp_path, sid="bad", extra_fm="progressive: maybe")
    with pytest.raises(SkillLoaderError):
        load_skills([tmp_path])


# ---------------------------------------------------------------------------
# install_from_path
# ---------------------------------------------------------------------------


def test_install_from_path_copies_skill_directory(tmp_path: Path) -> None:
    src = tmp_path / "src"
    target = tmp_path / "skills"
    _write_skill(src, sid="skill-a", name="A", desc="x")
    # An auxiliary file alongside SKILL.md must be carried over.
    (src / "skill-a" / "extra.txt").write_text("companion data")

    result = install_from_path(src / "skill-a", target_root=target)

    assert isinstance(result, InstallResult)
    assert result.skill_id == "skill-a"
    assert result.installed_path == target / "skill-a"
    assert (target / "skill-a" / "SKILL.md").is_file()
    assert (target / "skill-a" / "extra.txt").is_file()
    assert result.replaced is False


def test_install_from_path_finds_nested_skill_md(tmp_path: Path) -> None:
    """Source can be a parent dir; installer locates the lone ``SKILL.md``."""
    src = tmp_path / "src"
    target = tmp_path / "skills"
    _write_skill(src / "wrapper", sid="nested", name="N", desc="z")

    result = install_from_path(src, target_root=target)
    assert result.skill_id == "nested"
    assert (target / "nested" / "SKILL.md").is_file()


def test_install_rejects_multiple_skills_in_source(tmp_path: Path) -> None:
    src = tmp_path / "src"
    target = tmp_path / "skills"
    _write_skill(src, sid="one")
    _write_skill(src, sid="two")
    with pytest.raises(SkillInstallError, match="multiple SKILL.md"):
        install_from_path(src, target_root=target)


def test_install_rejects_collision_without_force(tmp_path: Path) -> None:
    src = tmp_path / "src"
    target = tmp_path / "skills"
    _write_skill(src, sid="dup")
    install_from_path(src / "dup", target_root=target)
    with pytest.raises(SkillInstallError, match="already installed"):
        install_from_path(src / "dup", target_root=target)


def test_install_force_replaces_and_keeps_backup(tmp_path: Path) -> None:
    src = tmp_path / "src"
    target = tmp_path / "skills"
    _write_skill(src, sid="dup", desc="v1")
    install_from_path(src / "dup", target_root=target)

    # Same id, different description.
    src2 = tmp_path / "src2"
    _write_skill(src2, sid="dup", desc="v2")
    result = install_from_path(src2 / "dup", target_root=target, overwrite=True)

    assert result.replaced is True
    assert result.manifest.description == "v2"
    backups = list(target.glob("dup.bak-*"))
    assert len(backups) == 1


def test_install_rejects_unsafe_id(tmp_path: Path) -> None:
    src = tmp_path / "src"
    target = tmp_path / "skills"
    skill_dir = src / "x"
    skill_dir.mkdir(parents=True)
    # YAML frontmatter forces id with path separators.
    (skill_dir / "SKILL.md").write_text(
        "---\nid: ../escape\nname: bad\ndescription: x\n---\nbody\n"
    )
    with pytest.raises(SkillInstallError, match="must match"):
        install_from_path(skill_dir, target_root=target)


def test_install_missing_skill_md_errors(tmp_path: Path) -> None:
    target = tmp_path / "skills"
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(SkillInstallError, match="no SKILL.md"):
        install_from_path(empty, target_root=target)


# ---------------------------------------------------------------------------
# list_installed / remove_installed
# ---------------------------------------------------------------------------


def test_list_installed_returns_manifests(tmp_path: Path) -> None:
    src = tmp_path / "src"
    target = tmp_path / "skills"
    _write_skill(src, sid="a", desc="alpha")
    _write_skill(src, sid="b", desc="beta")
    install_from_path(src / "a", target_root=target)
    install_from_path(src / "b", target_root=target)
    installed = list_installed(target)
    assert {m.id for m in installed} == {"a", "b"}


def test_list_installed_empty_root(tmp_path: Path) -> None:
    assert list_installed(tmp_path / "empty") == []


def test_remove_installed_deletes_skill(tmp_path: Path) -> None:
    src = tmp_path / "src"
    target = tmp_path / "skills"
    _write_skill(src, sid="zap")
    install_from_path(src / "zap", target_root=target)
    removed = remove_installed("zap", target_root=target)
    assert not removed.exists()


def test_remove_installed_unknown_errors(tmp_path: Path) -> None:
    with pytest.raises(SkillInstallError):
        remove_installed("missing", target_root=tmp_path)


def test_remove_installed_validates_id(tmp_path: Path) -> None:
    with pytest.raises(SkillInstallError, match="must match"):
        remove_installed("../escape", target_root=tmp_path)
