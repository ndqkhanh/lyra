"""L5 Persona — communication style learning from interaction history.

Learns and adapts to the user's preferred communication patterns:
verbosity, formality, technical depth, response structure, etc.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum


class StyleDimension(StrEnum):
    VERBOSITY = "verbosity"
    FORMALITY = "formality"
    TECHNICAL_DEPTH = "technical_depth"
    CONCISENESS = "conciseness"
    CODE_PREFERENCE = "code_preference"
    EXPLANATION_STYLE = "explanation_style"


@dataclass(frozen=True)
class StylePreference:
    pref_id: str
    dimension: StyleDimension
    value: float
    sample_count: int
    last_observed: float


class StyleLearner:
    """Learns communication style preferences from interaction feedback.

    Tracks style preferences across 6 dimensions, adapting through
    implicit feedback (what the user accepts) rather than explicit
    ratings.
    """

    def __init__(self, learning_rate: float = 0.1) -> None:
        self.learning_rate = learning_rate
        self._preferences: dict[str, StylePreference] = {}

    def observe(self, dimension: StyleDimension, value: float) -> StylePreference:
        """Record an observed style preference."""
        clamped = max(0.0, min(1.0, value))
        key = dimension.value
        pref_id = hashlib.sha256(key.encode()).hexdigest()[:8]

        if pref_id in self._preferences:
            existing = self._preferences[pref_id]
            n = existing.sample_count + 1
            new_val = existing.value + self.learning_rate * (clamped - existing.value)
            updated = StylePreference(
                pref_id=pref_id,
                dimension=dimension,
                value=round(new_val, 4),
                sample_count=n,
                last_observed=time.time(),
            )
        else:
            updated = StylePreference(
                pref_id=pref_id,
                dimension=dimension,
                value=round(clamped, 4),
                sample_count=1,
                last_observed=time.time(),
            )

        self._preferences[pref_id] = updated
        return updated

    def get_style_vector(self) -> dict[StyleDimension, float]:
        """Return the current style profile as a dimension→value map."""
        result: dict[StyleDimension, float] = {}
        for pref in self._preferences.values():
            result[pref.dimension] = pref.value
        for dim in StyleDimension:
            if dim not in result:
                result[dim] = 0.5
        return result

    def is_confident(self, dimension: StyleDimension, min_samples: int = 5) -> bool:
        pref = self._preferences.get(hashlib.sha256(dimension.value.encode()).hexdigest()[:8])
        return pref is not None and pref.sample_count >= min_samples

    def stats(self) -> dict:
        vec = self.get_style_vector()
        return {
            "dimensions_learned": sum(1 for p in self._preferences.values() if p.sample_count >= 3),
            "total_observations": sum(p.sample_count for p in self._preferences.values()),
            "style_vector": {k.value: v for k, v in vec.items()},
        }
