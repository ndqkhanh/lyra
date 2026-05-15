"""Reuse-first hybrid skill router.

Tier 0 (description / trigger overlap) is implemented inline.
L38-1 (Argus tier-cascade) layers a Tier-1 BM25 stage on top via the
optional ``bm25_tier`` constructor argument; when it's attached the
``rank`` blend uses three signals (overlap + BM25 + telemetry) instead
of two. Without it the router stays bit-compatible with the legacy
2-signal blend.

This is a classic "prefer retrieval over generation" pattern from
the agent-loop literature — reuse is cheaper, faster, and has a
known success rate, while synthesis has unknown quality and costs
tokens.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Sequence, TYPE_CHECKING

from .registry import Skill, SkillRegistry

if TYPE_CHECKING:  # pragma: no cover — import-cycle dodge
    from .bm25_tier import BM25Tier


__all__ = [
    "HybridSkillRouter",
    "RouterDecision",
    "SkillMatch",
]


class RouterDecision(str, Enum):
    REUSE = "reuse"
    SYNTHESISE = "synthesise"


@dataclass(frozen=True)
class SkillMatch:
    skill: Skill
    score: float        # [0, 1]
    rationale: str

    def to_dict(self) -> dict[str, object]:
        return {
            "skill_id": self.skill.id,
            "score": self.score,
            "rationale": self.rationale,
        }


@dataclass
class HybridSkillRouter:
    """Reuse-first router with optional Argus L38-1 BM25 tier."""

    registry: SkillRegistry
    reuse_threshold: float = 0.6
    bm25_tier: Optional["BM25Tier"] = None
    # Blend weights — must sum to 1.0 when all three signals are live.
    overlap_weight: float = 0.5
    bm25_weight: float = 0.3
    telemetry_weight: float = 0.2
    # Half-life for the decayed-rate signal (L38-2). Ignored when the
    # registry has no telemetry store attached.
    telemetry_half_life_days: float = 14.0

    def __post_init__(self) -> None:
        if not (0.0 <= self.reuse_threshold <= 1.0):
            raise ValueError("reuse_threshold must be in [0, 1]")

    # ---- scoring --------------------------------------------------

    @staticmethod
    def _trigger_overlap(query: str, triggers: Sequence[str]) -> float:
        q = set(query.lower().split())
        if not q:
            return 0.0
        best = 0.0
        for trigger in triggers:
            t = set(trigger.lower().split())
            if not t:
                continue
            overlap = len(q & t) / max(len(t), 1)
            if overlap > best:
                best = overlap
        return best

    def _telemetry_score(self, skill: Skill) -> float:
        """Pick the strongest telemetry signal available for *skill*.

        Decayed rate (L38-2) wins when the registry has a store
        attached and the skill has events; otherwise we fall through
        to the legacy in-memory ``success_rate`` so ranking still
        differentiates skills with hand-set counts.
        """
        decayed = self.registry.decayed_rate(
            skill.id, half_life_days=self.telemetry_half_life_days
        )
        if decayed is not None and not decayed.is_cold:
            return decayed.rate
        return skill.success_rate

    def rank(self, query: str) -> list[SkillMatch]:
        """Score every registered skill against ``query``.

        Without ``bm25_tier``: 70 % trigger-overlap + 30 % telemetry
        (legacy 2-signal blend, byte-compatible with prior versions).

        With ``bm25_tier``: 50 % overlap + 30 % BM25 + 20 % telemetry
        (Argus L38-1 3-signal blend). A skill missing from the BM25
        substrate gets ``bm25=0`` so it can still win on a strong
        trigger match — the cascade degrades, never excludes.
        """
        bm25_scores: dict[str, float] = (
            self.bm25_tier.score_map(query) if self.bm25_tier is not None else {}
        )
        cascade_active = self.bm25_tier is not None

        matches: list[SkillMatch] = []
        for skill in self.registry.all():
            overlap = self._trigger_overlap(query, skill.triggers)
            telemetry = self._telemetry_score(skill)
            if cascade_active:
                bm25 = bm25_scores.get(skill.id, 0.0)
                score = (
                    self.overlap_weight * overlap
                    + self.bm25_weight * bm25
                    + self.telemetry_weight * telemetry
                )
                rationale = (
                    f"overlap={overlap:.2f}, "
                    f"bm25={bm25:.2f}, "
                    f"telemetry={telemetry:.2f}"
                )
            else:
                score = 0.7 * overlap + 0.3 * telemetry
                rationale = (
                    f"overlap={overlap:.2f}, "
                    f"success_rate={telemetry:.2f}"
                )
            matches.append(SkillMatch(skill=skill, score=score, rationale=rationale))
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches

    # ---- decision -------------------------------------------------

    def decide(self, query: str) -> tuple[RouterDecision, SkillMatch | None]:
        ranked = self.rank(query)
        if ranked and ranked[0].score >= self.reuse_threshold:
            return RouterDecision.REUSE, ranked[0]
        return RouterDecision.SYNTHESISE, ranked[0] if ranked else None
