"""Wave-F Task 7 — trigger-description auto-optimizer contract."""
from __future__ import annotations

from lyra_core.skills import (
    HybridSkillRouter,
    RouterDecision,
    Skill,
    SkillRegistry,
    TriggerOptimizer,
)


def _seed() -> SkillRegistry:
    r = SkillRegistry()
    r.register(
        Skill(
            id="find-regression",
            description="find the commit that broke a test",
            triggers=("bisect regression",),
        )
    )
    r.register(
        Skill(
            id="rename-symbol",
            description="rename a function across the repo",
            triggers=("rename symbol", "rename function"),
        )
    )
    return r


# ---- on_miss -------------------------------------------------------


def test_on_miss_adds_new_trigger() -> None:
    r = _seed()
    opt = TriggerOptimizer(registry=r)
    report = opt.on_miss(
        skill_id="find-regression",
        user_query="please find the commit that broke my test",
    )
    assert len(report.added_triggers) == 1
    skill = r.get("find-regression")
    assert any("commit" in t for t in skill.triggers)
    assert any("broke" in t for t in skill.triggers)


def test_on_miss_refuses_to_add_subset_of_existing() -> None:
    r = _seed()
    opt = TriggerOptimizer(registry=r)
    report = opt.on_miss(
        skill_id="rename-symbol",
        user_query="please rename symbol",  # same normalised form
    )
    assert report.added_triggers == ()


def test_on_miss_skips_below_minimum_tokens() -> None:
    r = _seed()
    opt = TriggerOptimizer(registry=r, min_trigger_words=3)
    report = opt.on_miss(
        skill_id="find-regression",
        user_query="short?",
    )
    assert report.added_triggers == ()


def test_on_miss_improves_router_next_time() -> None:
    r = _seed()
    router = HybridSkillRouter(registry=r, reuse_threshold=0.5)
    # Before optimisation, synthesise because "find commit broke"
    # isn't near the original trigger "bisect regression".
    decision, _ = router.decide("please find the commit that broke my test")
    assert decision is RouterDecision.SYNTHESISE
    opt = TriggerOptimizer(registry=r)
    opt.on_miss(
        skill_id="find-regression",
        user_query="please find the commit that broke my test",
    )
    decision2, match2 = router.decide("please find the commit that broke my test")
    assert decision2 is RouterDecision.REUSE
    assert match2 is not None
    assert match2.skill.id == "find-regression"


# ---- on_false_positive --------------------------------------------


def test_on_false_positive_removes_overreaching_trigger() -> None:
    r = SkillRegistry()
    r.register(
        Skill(
            id="run-tests",
            description="run the test suite",
            triggers=("tests", "run tests"),
        )
    )
    opt = TriggerOptimizer(registry=r)
    report = opt.on_false_positive(
        skill_id="run-tests",
        misfiring_query="tests please",
    )
    assert "tests" in report.removed_triggers
    skill = r.get("run-tests")
    assert "tests" not in [t.lower() for t in skill.triggers]
    assert "run tests" in [t.lower() for t in skill.triggers]


def test_on_false_positive_keeps_at_least_one_trigger() -> None:
    r = SkillRegistry()
    r.register(
        Skill(
            id="only-one",
            description="…",
            triggers=("foo",),
        )
    )
    opt = TriggerOptimizer(registry=r)
    opt.on_false_positive(skill_id="only-one", misfiring_query="foo")
    skill = r.get("only-one")
    assert len(skill.triggers) >= 1


def test_report_serialises() -> None:
    r = _seed()
    opt = TriggerOptimizer(registry=r)
    report = opt.on_miss(
        skill_id="find-regression",
        user_query="which commit broke my test suite",
    )
    data = report.to_dict()
    assert data["skill_id"] == "find-regression"
    assert isinstance(data["added_triggers"], list)
