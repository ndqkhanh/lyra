"""Tests for :mod:`lyra_skills.activation`."""
from __future__ import annotations

import pytest

from lyra_skills.activation import (
    ActivatedSkill,
    match_explicit_invocations,
    match_keywords,
    render_active_block,
    select_active_skills,
)
from lyra_skills.loader import SkillManifest


def _skill(
    sid: str,
    *,
    progressive: bool = True,
    keywords: list[str] | None = None,
    body: str = "",
) -> SkillManifest:
    return SkillManifest(
        id=sid,
        name=sid.title(),
        description=f"{sid} skill",
        body=body or f"# {sid}\n\nbody for {sid}\n",
        path=f"/skills/{sid}/SKILL.md",
        version="1.0.0",
        keywords=keywords or [],
        progressive=progressive,
    )


# ---------------------------------------------------------------------------
# match_keywords
# ---------------------------------------------------------------------------


def test_match_keywords_returns_first_hit_only() -> None:
    s = _skill("triage", keywords=["security", "triage"])
    matches = match_keywords("Please run a security triage", [s])
    assert len(matches) == 1
    assert matches[0][0].id == "triage"


def test_match_keywords_is_case_insensitive() -> None:
    s = _skill("tdd", keywords=["TDD"])
    assert match_keywords("apply tdd here", [s])
    assert match_keywords("APPLY TDD HERE", [s])


def test_match_keywords_skips_skills_without_keywords() -> None:
    s = _skill("plain", keywords=[])
    assert match_keywords("anything goes", [s]) == []


def test_match_keywords_empty_prompt_returns_empty() -> None:
    s = _skill("x", keywords=["x"])
    assert match_keywords("", [s]) == []
    assert match_keywords("   ", [s]) == []


# ---------------------------------------------------------------------------
# match_explicit_invocations
# ---------------------------------------------------------------------------


def test_explicit_invocation_finds_skill() -> None:
    s = _skill("surgical-changes", keywords=[])
    matches = match_explicit_invocations(
        "USE SKILL: surgical-changes", [s],
    )
    assert len(matches) == 1
    assert matches[0][0].id == "surgical-changes"


def test_explicit_invocation_handles_lowercase_directive() -> None:
    s = _skill("foo")
    matches = match_explicit_invocations("use skill: foo", [s])
    assert len(matches) == 1


def test_explicit_invocation_supports_multiple_directives() -> None:
    s1 = _skill("a")
    s2 = _skill("b")
    matches = match_explicit_invocations(
        "USE SKILL: a then USE SKILL: b", [s1, s2],
    )
    ids = {m[0].id for m in matches}
    assert ids == {"a", "b"}


def test_explicit_invocation_ignores_unknown_ids() -> None:
    s = _skill("foo")
    assert match_explicit_invocations("USE SKILL: bar", [s]) == []


# ---------------------------------------------------------------------------
# select_active_skills
# ---------------------------------------------------------------------------


def test_select_skips_non_progressive_by_default() -> None:
    """Non-progressive skills stay description-only (pre-N.7 behaviour)."""
    pinned = _skill("pinned", progressive=False, keywords=[])
    active = select_active_skills(prompt="", skills=[pinned])
    assert active == []


def test_select_force_id_overrides_progressive_flag() -> None:
    """Force activation honours the caller even for non-progressive skills."""
    pinned = _skill("pinned", progressive=False, keywords=[])
    active = select_active_skills(
        prompt="", skills=[pinned], force_ids=["pinned"],
    )
    assert len(active) == 1
    assert active[0].manifest.id == "pinned"


def test_select_activates_progressive_on_keyword() -> None:
    s = _skill("triage", progressive=True, keywords=["security"])
    active = select_active_skills(prompt="security audit please", skills=[s])
    assert len(active) == 1
    assert "matched keyword" in active[0].reason


def test_select_does_not_activate_progressive_without_keyword() -> None:
    s = _skill("triage", progressive=True, keywords=["security"])
    active = select_active_skills(prompt="just a hi", skills=[s])
    assert active == []


def test_select_force_activation_works_for_progressive() -> None:
    s = _skill("foo", progressive=True, keywords=[])
    active = select_active_skills(
        prompt="anything", skills=[s], force_ids=["foo"],
    )
    assert len(active) == 1
    assert "force-activated" in active[0].reason


def test_select_explicit_directive_activates_progressive() -> None:
    s = _skill("foo", progressive=True, keywords=[])
    active = select_active_skills(
        prompt="USE SKILL: foo", skills=[s],
    )
    assert len(active) == 1
    assert "explicit" in active[0].reason


def test_select_dedupes_by_skill_id() -> None:
    """Same skill matched by both keyword & directive must appear once."""
    s = _skill("foo", progressive=True, keywords=["bar"])
    active = select_active_skills(
        prompt="USE SKILL: foo and bar", skills=[s],
    )
    assert len(active) == 1


def test_select_respects_max_active_cap() -> None:
    skills = [
        _skill(f"s{i}", progressive=True, keywords=[f"kw{i}"])
        for i in range(10)
    ]
    prompt = " ".join(f"kw{i}" for i in range(10))
    active = select_active_skills(prompt=prompt, skills=skills, max_active=3)
    assert len(active) == 3


def test_select_truncates_long_bodies() -> None:
    long_body = "x" * 10_000
    s = _skill("verbose", progressive=True, keywords=["go"], body=long_body)
    active = select_active_skills(
        prompt="go go go", skills=[s], max_body_chars=200,
    )
    assert len(active) == 1
    assert len(active[0].body) <= 200
    assert active[0].body.endswith("…")


# ---------------------------------------------------------------------------
# render_active_block
# ---------------------------------------------------------------------------


def test_render_empty_returns_empty_string() -> None:
    assert render_active_block([]) == ""


def test_render_emits_header_and_body() -> None:
    s = _skill("foo", body="# Foo\n\nUse foo carefully.")
    active = [ActivatedSkill(manifest=s, reason="testing", body=s.body.strip())]
    out = render_active_block(active)
    assert "Active skills" in out
    assert "Foo" in out
    assert "Use foo carefully" in out
    assert "testing" in out


# ---------------------------------------------------------------------------
# Phase O.6 — utility-aware activation tie-breaks
# ---------------------------------------------------------------------------


def test_select_prefers_higher_utility_when_capped() -> None:
    """When ``max_active`` is hit, highest ledger utility wins.

    Two skills match the same prompt but ``max_active=1`` only
    permits one. The skill with higher utility (more historical
    successes vs failures) must be chosen — that's the
    Memento-style "Read" half of Read-Write Reflective Learning:
    pick the skill the agent has already proven works.
    """
    a = _skill("alpha", progressive=True, keywords=["go"])
    b = _skill("beta", progressive=True, keywords=["go"])
    c = _skill("gamma", progressive=True, keywords=["go"])

    utility = {"alpha": 0.1, "beta": 0.95, "gamma": -0.5}
    active = select_active_skills(
        prompt="please go now",
        skills=[a, b, c],
        max_active=1,
        utility_resolver=lambda sid: utility.get(sid, 0.0),
    )
    assert [act.manifest.id for act in active] == ["beta"]


def test_select_breaks_keyword_tie_by_utility() -> None:
    """All three match the same keyword and fit under cap, but order matters.

    Even when all skills fit, the ordering of activations should
    prefer high-utility skills first so renderers (and the
    skills.activated event payload) reflect what the model is
    most likely to lean on.
    """
    a = _skill("alpha", progressive=True, keywords=["test"])
    b = _skill("beta", progressive=True, keywords=["test"])
    c = _skill("gamma", progressive=True, keywords=["test"])

    utility = {"alpha": -0.4, "beta": 0.5, "gamma": 0.9}
    active = select_active_skills(
        prompt="run tests",
        skills=[a, b, c],
        max_active=3,
        utility_resolver=lambda sid: utility.get(sid, 0.0),
    )
    assert [act.manifest.id for act in active] == ["gamma", "beta", "alpha"]


def test_select_force_ids_still_win_over_utility() -> None:
    """``force_ids`` is explicit caller intent and outranks utility.

    A force-activated skill must appear regardless of how poorly
    the ledger rates it — utility-aware ranking only reorders
    *implicit* matches.
    """
    a = _skill("alpha", progressive=True, keywords=["go"])
    b = _skill("beta", progressive=True, keywords=["go"])

    utility = {"alpha": 0.99, "beta": -0.99}
    active = select_active_skills(
        prompt="go now",
        skills=[a, b],
        force_ids=["beta"],
        max_active=1,
        utility_resolver=lambda sid: utility.get(sid, 0.0),
    )
    # force-activated beta must be present even though alpha has
    # vastly higher utility.
    assert active[0].manifest.id == "beta"


def test_select_no_resolver_falls_back_to_iteration_order() -> None:
    """Without a resolver, behaviour matches pre-O.6 (insertion order)."""
    a = _skill("first", progressive=True, keywords=["kw"])
    b = _skill("second", progressive=True, keywords=["kw"])
    active = select_active_skills(
        prompt="kw kw",
        skills=[a, b],
        max_active=1,
    )
    assert active[0].manifest.id == "first"


def test_select_resolver_failure_does_not_break_activation() -> None:
    """A buggy resolver must not crash skill activation.

    Telemetry must never break a chat turn — if the ledger is
    corrupt or the resolver raises, fall back to pre-O.6 ordering
    rather than aborting.
    """
    a = _skill("alpha", progressive=True, keywords=["go"])
    b = _skill("beta", progressive=True, keywords=["go"])

    def boom(_sid: str) -> float:
        raise RuntimeError("ledger corrupt")

    active = select_active_skills(
        prompt="go go",
        skills=[a, b],
        max_active=2,
        utility_resolver=boom,
    )
    assert {act.manifest.id for act in active} == {"alpha", "beta"}
