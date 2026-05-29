"""L5 Persona — incremental preference accumulation from user interactions.

Accumulates fine-grained user preferences through observation of
choices, rejections, and implicit feedback signals during interactions.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum


class PreferenceSource(StrEnum):
    EXPLICIT = "explicit"
    IMPLICIT_ACCEPT = "implicit_accept"
    IMPLICIT_REJECT = "implicit_reject"
    PATTERN = "pattern"


@dataclass(frozen=True)
class AccumulatedPreference:
    pref_id: str
    key: str
    value: str
    source: PreferenceSource
    weight: float
    observation_count: int
    first_seen: float
    last_seen: float


class PreferenceAccumulator:
    """Accumulates user preferences from multiple interaction signals.

    Preferences are weighted by source reliability (explicit > implicit
    accept > pattern > implicit reject) and decay if not reinforced.
    """

    SOURCE_WEIGHTS: dict[PreferenceSource, float] = {
        PreferenceSource.EXPLICIT: 1.0,
        PreferenceSource.IMPLICIT_ACCEPT: 0.7,
        PreferenceSource.PATTERN: 0.5,
        PreferenceSource.IMPLICIT_REJECT: 0.3,
    }

    def __init__(self, decay_half_life_sec: float = 86400.0) -> None:
        self.decay_half_life_sec = decay_half_life_sec
        self._preferences: dict[str, AccumulatedPreference] = {}

    def record(
        self,
        key: str,
        value: str,
        source: PreferenceSource = PreferenceSource.PATTERN,
    ) -> AccumulatedPreference:
        pref_id = hashlib.sha256(f"{key}|{value}".encode()).hexdigest()[:10]
        src_weight = self.SOURCE_WEIGHTS[source]

        if pref_id in self._preferences:
            existing = self._preferences[pref_id]
            n = existing.observation_count + 1
            new_weight = min(1.0, existing.weight + src_weight * 0.1)
            updated = AccumulatedPreference(
                pref_id=pref_id,
                key=key,
                value=value,
                source=source,
                weight=round(new_weight, 4),
                observation_count=n,
                first_seen=existing.first_seen,
                last_seen=time.time(),
            )
        else:
            updated = AccumulatedPreference(
                pref_id=pref_id,
                key=key,
                value=value,
                source=source,
                weight=round(src_weight * 0.3, 4),
                observation_count=1,
                first_seen=time.time(),
                last_seen=time.time(),
            )

        self._preferences[pref_id] = updated
        return updated

    def get_top(self, key: str | None = None, limit: int = 10) -> list[AccumulatedPreference]:
        now = time.time()
        scored: list[tuple[float, AccumulatedPreference]] = []
        for p in self._preferences.values():
            if key is not None and p.key != key:
                continue
            age = now - p.last_seen
            decay = 0.5 ** (age / self.decay_half_life_sec)
            effective = p.weight * decay
            scored.append((effective, p))
        scored.sort(key=lambda x: -x[0])
        return [p for _, p in scored[:limit]]

    def get(self, key: str) -> list[AccumulatedPreference]:
        return self.get_top(key=key, limit=100)

    def stats(self) -> dict:
        return {
            "total_preferences": len(self._preferences),
            "unique_keys": len({p.key for p in self._preferences.values()}),
        }
