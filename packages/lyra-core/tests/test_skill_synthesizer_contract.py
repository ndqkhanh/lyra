"""Wave-F Task 8 — in-session skill synthesiser contract."""
from __future__ import annotations

import pytest

from lyra_core.skills import (
    HybridSkillRouter,
    RouterDecision,
    Skill,
    SkillRegistry,
    SkillSynthesizer,
    SynthesisError,
)


def test_synthesises_skill_from_query() -> None:
    r = SkillRegistry()
    synth = SkillSynthesizer(registry=r)
    report = synth.synthesise(
        user_query="summarise the pull request diff",
        description="take a PR diff and produce a short changelog line",
        draft_triggers=("summarise PR", "pull request summary"),
    )
    assert report.skill.synthesised is True
    assert report.skill.triggers == ("summarise PR", "pull request summary")
    assert report.skill.id in r


def test_empty_description_rejected() -> None:
    synth = SkillSynthesizer(registry=SkillRegistry())
    with pytest.raises(SynthesisError):
        synth.synthesise(user_query="x", description="   ")


def test_no_triggers_falls_back_to_query() -> None:
    synth = SkillSynthesizer(registry=SkillRegistry())
    report = synth.synthesise(
        user_query="scrub PII from logs",
        description="strip personal data",
        draft_triggers=None,
    )
    assert report.skill.triggers == ("scrub pii from logs",)


def test_id_slug_is_stable_and_slugified() -> None:
    synth = SkillSynthesizer(registry=SkillRegistry())
    report = synth.synthesise(
        user_query="Find CVEs in my deps!!!",
        description="scan requirements.txt for CVEs",
    )
    assert report.skill.id == "find-cves-in-my-deps"
    assert report.collision_resolved_with_suffix == 0


def test_id_collision_auto_resolves_with_suffix() -> None:
    r = SkillRegistry()
    r.register(
        Skill(id="list-open-prs", description="…", triggers=("list prs",))
    )
    synth = SkillSynthesizer(registry=r)
    report = synth.synthesise(
        user_query="list open PRs",
        description="list open pull requests for current repo",
    )
    assert report.skill.id == "list-open-prs-1"
    assert report.collision_resolved_with_suffix == 1


def test_router_then_synth_pipeline() -> None:
    r = SkillRegistry()
    router = HybridSkillRouter(registry=r, reuse_threshold=0.5)
    synth = SkillSynthesizer(registry=r)
    decision, _ = router.decide("explain circular imports in my package")
    assert decision is RouterDecision.SYNTHESISE
    report = synth.synthesise(
        user_query="explain circular imports",
        description="trace the import graph to find cycles",
        draft_triggers=("circular imports", "import cycle"),
    )
    # After synthesis, the router reuses the new skill.
    decision2, match = router.decide("explain circular imports in my package")
    assert decision2 is RouterDecision.REUSE
    assert match.skill.id == report.skill.id


def test_report_serialises() -> None:
    synth = SkillSynthesizer(registry=SkillRegistry())
    report = synth.synthesise(
        user_query="draft release notes",
        description="produce markdown release notes",
    )
    data = report.to_dict()
    assert data["synthesised"] is True
    assert data["collision_resolved_with_suffix"] == 0
    assert data["skill_id"]


def test_drop_empty_string_in_draft_triggers_raises() -> None:
    synth = SkillSynthesizer(registry=SkillRegistry())
    with pytest.raises(SynthesisError):
        synth.synthesise(
            user_query="x",
            description="…",
            draft_triggers=("", "  "),
        )
