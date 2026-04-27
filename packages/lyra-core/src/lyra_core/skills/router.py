"""Reuse-first hybrid skill router.

The router walks the registry first. If a skill's trigger terms
match the query with confidence ``>= reuse_threshold`` the router
returns ``REUSE``.  Otherwise it returns ``SYNTHESISE`` so the
caller can dispatch Task 8's in-session skill synthesiser.

This is a classic "prefer retrieval over generation" pattern from
the agent-loop literature — reuse is cheaper, faster, and has a
known success rate, while synthesis has unknown quality and costs
tokens.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence

from .registry import Skill, SkillRegistry


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
    """Reuse-first router."""

    registry: SkillRegistry
    reuse_threshold: float = 0.6

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

    def rank(self, query: str) -> list[SkillMatch]:
        """Score every registered skill against ``query``.

        Returns matches sorted highest → lowest score.  Score blends
        trigger-overlap (70%) with historical success rate (30%), so
        a skill with no history can still win on a strong trigger
        match but a skill that repeatedly missed gets a penalty.
        """
        matches: list[SkillMatch] = []
        for skill in self.registry.all():
            overlap = self._trigger_overlap(query, skill.triggers)
            score = 0.7 * overlap + 0.3 * skill.success_rate
            rationale = (
                f"overlap={overlap:.2f}, "
                f"success_rate={skill.success_rate:.2f}"
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
