"""Wave-F Task 6 — reuse-first hybrid skill router contract."""
from __future__ import annotations

import pytest

from lyra_core.skills import (
    HybridSkillRouter,
    RouterDecision,
    Skill,
    SkillAlreadyExists,
    SkillNotFound,
    SkillRegistry,
)


def _seed_registry() -> SkillRegistry:
    r = SkillRegistry()
    r.register(
        Skill(
            id="git-blame",
            description="explain who changed a line",
            triggers=("git blame for", "who changed this line", "git blame"),
        )
    )
    r.register(
        Skill(
            id="refactor-rename",
            description="safely rename a symbol",
            triggers=("rename symbol", "rename variable across files"),
        )
    )
    r.register(
        Skill(
            id="bisect-regression",
            description="run git bisect on a failing test",
            triggers=("bisect regression", "find commit that broke test"),
        )
    )
    return r


# ---- registry ------------------------------------------------------


def test_register_rejects_duplicates() -> None:
    r = SkillRegistry()
    r.register(Skill(id="x", description="a", triggers=("t",)))
    with pytest.raises(SkillAlreadyExists):
        r.register(Skill(id="x", description="b", triggers=("t2",)))


def test_get_raises_on_missing() -> None:
    r = SkillRegistry()
    with pytest.raises(SkillNotFound):
        r.get("ghost")


def test_success_rate_updates() -> None:
    r = _seed_registry()
    r.record_success("git-blame")
    r.record_success("git-blame")
    r.record_miss("git-blame")
    skill = r.get("git-blame")
    assert skill.success_rate == pytest.approx(2 / 3)


def test_find_by_trigger_case_insensitive() -> None:
    r = _seed_registry()
    hits = r.find_by_trigger("GIT BLAME for main.py")
    assert any(s.id == "git-blame" for s in hits)


def test_remove_deletes_skill() -> None:
    r = _seed_registry()
    assert "git-blame" in r
    r.remove("git-blame")
    assert "git-blame" not in r


# ---- router decision -----------------------------------------------


def test_decide_reuses_strong_match() -> None:
    r = _seed_registry()
    router = HybridSkillRouter(registry=r, reuse_threshold=0.5)
    decision, match = router.decide("git blame for main.py")
    assert decision is RouterDecision.REUSE
    assert match.skill.id == "git-blame"


def test_decide_synthesises_when_nothing_matches() -> None:
    r = _seed_registry()
    router = HybridSkillRouter(registry=r, reuse_threshold=0.5)
    decision, match = router.decide("analyse pandas dataframe to parquet")
    assert decision is RouterDecision.SYNTHESISE


def test_decide_on_empty_registry_always_synthesises() -> None:
    router = HybridSkillRouter(registry=SkillRegistry())
    decision, match = router.decide("anything")
    assert decision is RouterDecision.SYNTHESISE
    assert match is None


def test_success_rate_breaks_ties() -> None:
    r = SkillRegistry()
    r.register(Skill(id="a", description="…", triggers=("run tests",)))
    r.register(Skill(id="b", description="…", triggers=("run tests",)))
    r.record_success("b")
    r.record_success("b")
    router = HybridSkillRouter(registry=r, reuse_threshold=0.1)
    decision, match = router.decide("run tests")
    assert decision is RouterDecision.REUSE
    assert match.skill.id == "b"


def test_rank_returns_sorted() -> None:
    r = _seed_registry()
    router = HybridSkillRouter(registry=r)
    ranked = router.rank("git blame for main")
    assert ranked[0].skill.id == "git-blame"
    # Scores must be monotone non-increasing.
    scores = [m.score for m in ranked]
    assert all(a >= b for a, b in zip(scores, scores[1:]))


def test_invalid_threshold_rejected() -> None:
    with pytest.raises(ValueError):
        HybridSkillRouter(registry=SkillRegistry(), reuse_threshold=1.5)


def test_skill_match_serialises() -> None:
    r = _seed_registry()
    router = HybridSkillRouter(registry=r)
    _, match = router.decide("git blame for main")
    assert match is not None
    data = match.to_dict()
    assert data["skill_id"] == "git-blame"
    assert 0.0 <= data["score"] <= 1.0
    assert "overlap" in data["rationale"]
