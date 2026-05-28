"""L5 Persona — identity and trait modeling for agent personalization.

Captures stable identity traits, communication style preferences,
and behavioral tendencies that persist across sessions.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum


class TraitCategory(StrEnum):
    COMMUNICATION = "communication"
    PROBLEM_SOLVING = "problem_solving"
    RISK_TOLERANCE = "risk_tolerance"
    AUTONOMY = "autonomy"
    COLLABORATION = "collaboration"


@dataclass(frozen=True)
class IdentityTrait:
    trait_id: str
    category: TraitCategory
    name: str
    value: float
    confidence: float
    evidence_count: int
    last_updated: float

    @property
    def is_stable(self) -> bool:
        return self.confidence >= 0.8 and self.evidence_count >= 5


class IdentityModel:
    """Models agent identity as a collection of weighted, evolving traits.

    Traits are learned from interaction patterns and stabilized over
    repeated observations. Supports trait extraction, confidence
    calibration, and persona snapshot serialization.
    """

    def __init__(self) -> None:
        self._traits: dict[str, IdentityTrait] = {}

    def observe(
        self,
        category: TraitCategory,
        name: str,
        value: float,
    ) -> IdentityTrait:
        key = f"{category.value}|{name}"
        trait_id = hashlib.sha256(key.encode()).hexdigest()[:10]
        clamped = max(0.0, min(1.0, value))

        if trait_id in self._traits:
            existing = self._traits[trait_id]
            n = existing.evidence_count + 1
            new_val = (existing.value * existing.evidence_count + clamped) / n
            updated = IdentityTrait(
                trait_id=trait_id,
                category=category,
                name=name,
                value=round(new_val, 4),
                confidence=min(1.0, existing.confidence + 0.02),
                evidence_count=n,
                last_updated=time.time(),
            )
        else:
            updated = IdentityTrait(
                trait_id=trait_id,
                category=category,
                name=name,
                value=round(clamped, 4),
                confidence=0.3,
                evidence_count=1,
                last_updated=time.time(),
            )

        self._traits[trait_id] = updated
        return updated

    def get_profile(self) -> dict[TraitCategory, list[IdentityTrait]]:
        profile: dict[TraitCategory, list[IdentityTrait]] = {}
        for trait in self._traits.values():
            profile.setdefault(trait.category, []).append(trait)
        return profile

    def get_stable_traits(self) -> list[IdentityTrait]:
        return [t for t in self._traits.values() if t.is_stable]

    def stats(self) -> dict:
        stable = len(self.get_stable_traits())
        return {
            "total_traits": len(self._traits),
            "stable_traits": stable,
            "stability_pct": round(stable / max(len(self._traits), 1) * 100, 1),
        }
