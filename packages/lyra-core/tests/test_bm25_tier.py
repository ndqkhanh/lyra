"""L38-1 — Argus Tier-1 BM25 wrapper + cascade integration tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from lyra_core.memory.procedural import ProceduralMemory, SkillRecord
from lyra_core.skills.bm25_tier import BM25Hit, BM25Tier
from lyra_core.skills.registry import Skill, SkillRegistry
from lyra_core.skills.router import HybridSkillRouter, RouterDecision


# ----- substrate ------------------------------------------------------


@pytest.fixture
def memory(tmp_path: Path) -> ProceduralMemory:
    m = ProceduralMemory(tmp_path / "skills.sqlite")
    m.put(SkillRecord(
        id="edit",
        name="edit-file",
        description="modify a file in place",
        body="Open the file, mutate the lines, write it back atomically.",
    ))
    m.put(SkillRecord(
        id="review",
        name="review-diff",
        description="review a unified diff for correctness",
        body="Walk the hunks, check semantics, flag risky changes.",
    ))
    m.put(SkillRecord(
        id="localize",
        name="locate-symbol",
        description="find where a symbol is defined or referenced",
        body="Grep, ast-grep, or LSP — pick the cheapest tool that works.",
    ))
    return m


# ----- BM25Tier in isolation -----------------------------------------


def test_bm25_tier_empty_query_returns_empty(memory: ProceduralMemory) -> None:
    tier = BM25Tier(memory=memory)
    assert tier.score("") == []
    assert tier.score("   ") == []


def test_bm25_tier_ranks_relevant_skill_higher(memory: ProceduralMemory) -> None:
    tier = BM25Tier(memory=memory)
    hits = tier.score("review the diff")
    assert hits, "expected non-empty BM25 hits"
    assert hits[0].skill_id == "review"
    # Confidence in the documented (0, 1] range.
    assert 0.0 < hits[0].score <= 1.0


def test_bm25_tier_score_map_keyed_by_skill_id(memory: ProceduralMemory) -> None:
    tier = BM25Tier(memory=memory)
    sm = tier.score_map("modify file")
    assert "edit" in sm
    assert sm["edit"] > 0.0


def test_bm25_tier_known_ids_lists_substrate(memory: ProceduralMemory) -> None:
    tier = BM25Tier(memory=memory)
    assert tier.known_ids() == {"edit", "review", "localize"}


def test_bm25_tier_top_k_truncates(memory: ProceduralMemory) -> None:
    tier = BM25Tier(memory=memory, top_k=1)
    hits = tier.score("file diff symbol")  # broad query — multi-hit
    assert len(hits) <= 1


def test_bm25_normalise_is_monotonic_decreasing() -> None:
    """Smaller raw BM25 (better match) must produce a higher confidence."""
    a = BM25Tier.normalise(0.0)
    b = BM25Tier.normalise(1.0)
    c = BM25Tier.normalise(10.0)
    assert a > b > c
    assert 0.0 < c <= 1.0


# ----- cascade integration -------------------------------------------


def _registered(reg: SkillRegistry, skill_id: str, triggers: tuple[str, ...]) -> None:
    reg.register(Skill(id=skill_id, description=skill_id, triggers=triggers))


def test_router_without_bm25_tier_uses_legacy_blend(
    memory: ProceduralMemory,
) -> None:
    reg = SkillRegistry()
    _registered(reg, "edit", ("modify", "edit", "patch"))
    _registered(reg, "review", ("review", "audit"))
    router = HybridSkillRouter(registry=reg)

    ranked = router.rank("modify the file")
    assert ranked[0].skill.id == "edit"
    # Legacy 2-signal rationale must NOT mention bm25.
    assert "bm25" not in ranked[0].rationale


def test_router_with_bm25_tier_blends_three_signals(
    memory: ProceduralMemory,
) -> None:
    reg = SkillRegistry()
    _registered(reg, "edit", ("modify", "edit", "patch"))
    _registered(reg, "review", ("review", "audit"))
    _registered(reg, "localize", ("locate", "find"))
    tier = BM25Tier(memory=memory)
    router = HybridSkillRouter(registry=reg, bm25_tier=tier)

    ranked = router.rank("review the diff")
    assert "bm25" in ranked[0].rationale
    assert ranked[0].skill.id == "review"


def test_router_skills_missing_from_substrate_still_score(
    memory: ProceduralMemory,
) -> None:
    """A registry skill with no procedural-memory record should still
    be ranked via Tier 0 + telemetry — BM25 contribution is 0 but the
    cascade does not exclude it."""
    reg = SkillRegistry()
    _registered(reg, "edit", ("modify",))
    # ``ghosttrigger`` is a single FTS5 token — using a hyphenated form
    # would be parsed as a NOT operator. The cascade contract is what
    # we're testing here, not FTS5 query syntax.
    _registered(reg, "ghost", ("ghosttrigger",))  # not in memory
    tier = BM25Tier(memory=memory)
    router = HybridSkillRouter(registry=reg, bm25_tier=tier)

    ranked = router.rank("ghosttrigger")
    ids = [m.skill.id for m in ranked]
    assert "ghost" in ids
    ghost_match = next(m for m in ranked if m.skill.id == "ghost")
    assert "bm25=0.00" in ghost_match.rationale


def test_router_decision_threshold_holds_with_cascade(
    memory: ProceduralMemory,
) -> None:
    reg = SkillRegistry()
    _registered(reg, "edit", ("modify", "edit"))
    tier = BM25Tier(memory=memory)
    router = HybridSkillRouter(
        registry=reg, bm25_tier=tier, reuse_threshold=0.5
    )
    decision, top = router.decide("modify the file")
    assert decision == RouterDecision.REUSE
    assert top is not None and top.skill.id == "edit"
