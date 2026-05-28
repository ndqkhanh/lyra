"""L5 Persona — persistent persona storage with versioning and snapshots.

Provides durable storage for agent persona state including identity
traits, style preferences, and accumulated preferences.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from .identity_traits import IdentityModel, TraitCategory
from .preference_accumulator import PreferenceAccumulator
from .style_learner import StyleDimension, StyleLearner


@dataclass(frozen=True)
class PersonaSnapshot:
    snapshot_id: str
    agent_id: str
    traits: dict[str, float]
    style_vector: dict[str, float]
    preference_keys: list[str]
    created_at: float
    version: int


class PersonaStore:
    """Persistent persona storage with versioned snapshots.

    Aggregates identity traits, style preferences, and accumulated
    preferences into versioned persona snapshots that can be loaded,
    compared, and rolled back.
    """

    def __init__(self, agent_id: str = "default") -> None:
        self.agent_id = agent_id
        self.identity = IdentityModel()
        self.style = StyleLearner()
        self.preferences = PreferenceAccumulator()
        self._snapshots: list[PersonaSnapshot] = []
        self._version: int = 0

    def snapshot(self) -> PersonaSnapshot:
        """Create an immutable snapshot of the current persona state."""
        self._version += 1
        trait_map: dict[str, float] = {}
        for t in self.identity.get_stable_traits():
            trait_map[t.name] = t.value

        snap = PersonaSnapshot(
            snapshot_id=hashlib.sha256(
                f"{self.agent_id}|{self._version}|{time.time()}".encode()
            ).hexdigest()[:16],
            agent_id=self.agent_id,
            traits=trait_map,
            style_vector={
                k.value: v
                for k, v in self.style.get_style_vector().items()
            },
            preference_keys=[
                p.key for p in self.preferences.get_top(limit=20)
            ],
            created_at=time.time(),
            version=self._version,
        )
        self._snapshots.append(snap)
        return snap

    def get_latest_snapshot(self) -> PersonaSnapshot | None:
        return self._snapshots[-1] if self._snapshots else None

    def compare_snapshots(
        self, v1: int, v2: int
    ) -> dict[str, dict[str, float]]:
        """Compute delta between two persona versions."""
        s1 = next((s for s in self._snapshots if s.version == v1), None)
        s2 = next((s for s in self._snapshots if s.version == v2), None)
        if s1 is None or s2 is None:
            return {}

        all_keys = set(s1.traits) | set(s2.traits)
        deltas: dict[str, dict[str, float]] = {"traits": {}, "style": {}}
        for k in all_keys:
            deltas["traits"][k] = s2.traits.get(k, 0.0) - s1.traits.get(k, 0.0)
        all_style = set(s1.style_vector) | set(s2.style_vector)
        for k in all_style:
            deltas["style"][k] = s2.style_vector.get(k, 0.0) - s1.style_vector.get(k, 0.0)
        return deltas

    def stats(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "snapshots": len(self._snapshots),
            "version": self._version,
            "traits": self.identity.stats(),
            "style": self.style.stats(),
            "preferences": self.preferences.stats(),
        }
