"""Concept abstraction — distills concrete memory episodes into abstract knowledge.

Transforms specific experiences ("user rejected PR #342 for missing tests")
into general concepts ("user prioritizes test coverage in code review").
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum


class AbstractionLevel(StrEnum):
    CONCRETE = "concrete"
    PATTERN = "pattern"
    PRINCIPLE = "principle"
    AXIOM = "axiom"


@dataclass(frozen=True)
class AbstractConcept:
    concept_id: str
    label: str
    level: AbstractionLevel
    source_episodes: list[str]
    confidence: float
    last_reinforced: float
    abstraction_count: int


class ConceptAbstractor:
    """Distills concrete memory episodes into progressively abstract concepts.

    Levels:
    - CONCRETE: raw episode (e.g., "user said X on Tuesday")
    - PATTERN: recurring observation (e.g., "user frequently asks about Y")
    - PRINCIPLE: general rule (e.g., "user values Z over W")
    - AXIOM: fundamental truth (e.g., "correctness is the user's top priority")
    """

    def __init__(self, min_confidence: float = 0.6) -> None:
        self.min_confidence = min_confidence
        self._concepts: dict[str, AbstractConcept] = {}

    def abstract(
        self,
        label: str,
        episodes: list[str],
        current_level: AbstractionLevel | None = None,
    ) -> AbstractConcept:
        concept_id = hashlib.sha256(label.encode()).hexdigest()[:12]

        if concept_id in self._concepts:
            existing = self._concepts[concept_id]
            return self._reinforce(existing, episodes)

        level = current_level or AbstractionLevel.CONCRETE
        concept = AbstractConcept(
            concept_id=concept_id,
            label=label,
            level=level,
            source_episodes=episodes,
            confidence=0.5 if level == AbstractionLevel.CONCRETE else 0.3,
            last_reinforced=time.time(),
            abstraction_count=1,
        )
        self._concepts[concept_id] = concept
        return concept

    def promote(self, concept_id: str) -> AbstractConcept | None:
        concept = self._concepts.get(concept_id)
        if concept is None:
            return None

        levels = list(AbstractionLevel)
        current_idx = levels.index(concept.level)
        if current_idx >= len(levels) - 1:
            return concept

        if concept.confidence < self.min_confidence:
            return concept

        promoted = AbstractConcept(
            concept_id=concept.concept_id,
            label=concept.label,
            level=levels[current_idx + 1],
            source_episodes=concept.source_episodes,
            confidence=concept.confidence * 0.8,
            last_reinforced=time.time(),
            abstraction_count=concept.abstraction_count + 1,
        )
        self._concepts[concept_id] = promoted
        return promoted

    def get_by_level(self, level: AbstractionLevel) -> list[AbstractConcept]:
        return [c for c in self._concepts.values() if c.level == level]

    def get_principles(self) -> list[AbstractConcept]:
        return self.get_by_level(AbstractionLevel.PRINCIPLE)

    def _reinforce(
        self, existing: AbstractConcept, new_episodes: list[str]
    ) -> AbstractConcept:
        updated = AbstractConcept(
            concept_id=existing.concept_id,
            label=existing.label,
            level=existing.level,
            source_episodes=list(set(existing.source_episodes + new_episodes)),
            confidence=min(1.0, existing.confidence + 0.1),
            last_reinforced=time.time(),
            abstraction_count=existing.abstraction_count + 1,
        )
        self._concepts[existing.concept_id] = updated
        return updated

    def stats(self) -> dict:
        return {
            "total_concepts": len(self._concepts),
            "by_level": {
                lvl.value: sum(1 for c in self._concepts.values() if c.level == lvl)
                for lvl in AbstractionLevel
            },
        }
