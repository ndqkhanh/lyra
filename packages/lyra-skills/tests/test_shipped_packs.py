"""Red tests for shipped skill packs: atomic-skills, tdd-sprint, karpathy, safety."""
from __future__ import annotations

from lyra_skills.loader import load_skills
from lyra_skills.packs import shipped_pack_roots


def test_shipped_pack_roots_exist() -> None:
    roots = shipped_pack_roots()
    assert len(roots) >= 4
    for r in roots:
        assert r.exists(), f"shipped pack root missing: {r}"


def test_atomic_skills_pack_loads() -> None:
    atomic = next(
        r for r in shipped_pack_roots() if r.name == "atomic-skills"
    )
    skills = load_skills([atomic])
    ids = {s.id for s in skills}
    assert {"localize", "edit", "test-gen", "reproduce", "review"} <= ids


def test_karpathy_pack_loads() -> None:
    root = next(r for r in shipped_pack_roots() if r.name == "karpathy")
    skills = load_skills([root])
    ids = {s.id for s in skills}
    assert "think-before-coding" in ids
    assert "simplicity-first" in ids


def test_tdd_sprint_pack_loads() -> None:
    root = next(r for r in shipped_pack_roots() if r.name == "tdd-sprint")
    skills = load_skills([root])
    assert any(s.id == "7-phase" for s in skills)


def test_safety_pack_loads() -> None:
    root = next(r for r in shipped_pack_roots() if r.name == "safety")
    skills = load_skills([root])
    ids = {s.id for s in skills}
    assert "injection-triage" in ids
    assert "secrets-triage" in ids


def test_every_shipped_skill_has_nonempty_description() -> None:
    for root in shipped_pack_roots():
        for skill in load_skills([root]):
            assert skill.description, f"{skill.id} in {root.name} has empty description"
