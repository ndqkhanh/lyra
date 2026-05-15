"""Skill registry: stores every reusable skill with its trigger terms.

A :class:`Skill` is the minimal shape the router needs to match
and rank — a unique id, a human-readable description, a set of
trigger phrases the router searches against, and a mutable
``success_rate`` that updates as the skill is used.

L38-2 (Argus telemetry persistence) added an optional
:class:`SkillTelemetryStore` constructor argument. When provided,
``record_success`` / ``record_miss`` append to a SQLite event
ledger, the in-memory ints are restored from that ledger on
construction, and ``decayed_rate(skill_id)`` exposes the half-life-
weighted score for the cascade router. Callers that don't pass a
store keep the legacy in-memory-only behaviour bit-for-bit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover — import-cycle dodge
    from .telemetry import DecayedRate, SkillTelemetryStore


__all__ = [
    "Skill",
    "SkillAlreadyExists",
    "SkillNotFound",
    "SkillRegistry",
]


class SkillAlreadyExists(ValueError):
    pass


class SkillNotFound(KeyError):
    pass


@dataclass
class Skill:
    """One entry in the registry."""

    id: str
    description: str
    triggers: tuple[str, ...]
    success_count: int = 0
    miss_count: int = 0
    synthesised: bool = False

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.miss_count
        if total == 0:
            return 0.0
        return self.success_count / total


@dataclass
class SkillRegistry:
    _skills: dict[str, Skill] = field(default_factory=dict)
    telemetry_store: Optional["SkillTelemetryStore"] = None

    # ---- CRUD ----------------------------------------------------

    def register(self, skill: Skill) -> None:
        if skill.id in self._skills:
            raise SkillAlreadyExists(f"skill {skill.id!r} already registered")
        # L38-2 — when a telemetry store is attached, restore the lifetime
        # success / miss counts from the ledger so a process restart
        # never loses ranking history. The decayed rate is exposed
        # separately via ``decayed_rate``; the in-memory ints stay
        # correct for the legacy ``success_rate`` property.
        if self.telemetry_store is not None:
            s, m = self.telemetry_store.counts(skill.id)
            if s or m:
                skill.success_count = max(skill.success_count, s)
                skill.miss_count = max(skill.miss_count, m)
        self._skills[skill.id] = skill

    def update(self, skill: Skill) -> None:
        if skill.id not in self._skills:
            raise SkillNotFound(skill.id)
        self._skills[skill.id] = skill

    def remove(self, skill_id: str) -> None:
        if skill_id not in self._skills:
            raise SkillNotFound(skill_id)
        del self._skills[skill_id]

    def get(self, skill_id: str) -> Skill:
        try:
            return self._skills[skill_id]
        except KeyError as exc:
            raise SkillNotFound(skill_id) from exc

    def __contains__(self, skill_id: str) -> bool:
        return skill_id in self._skills

    def __len__(self) -> int:
        return len(self._skills)

    def all(self) -> tuple[Skill, ...]:
        return tuple(self._skills.values())

    # ---- stats ---------------------------------------------------

    def record_success(self, skill_id: str) -> Skill:
        skill = self.get(skill_id)
        skill.success_count += 1
        if self.telemetry_store is not None:
            self.telemetry_store.record_success(skill_id)
        return skill

    def record_miss(self, skill_id: str) -> Skill:
        skill = self.get(skill_id)
        skill.miss_count += 1
        if self.telemetry_store is not None:
            self.telemetry_store.record_miss(skill_id)
        return skill

    def decayed_rate(
        self,
        skill_id: str,
        *,
        half_life_days: float = 14.0,
    ) -> "DecayedRate | None":
        """L38-2 — half-life-weighted success rate from the ledger.

        Returns ``None`` when no telemetry store is attached so callers
        can fall back to the in-memory ``Skill.success_rate`` cleanly.
        """
        if self.telemetry_store is None:
            return None
        self.get(skill_id)  # surfaces SkillNotFound for unknown ids
        return self.telemetry_store.decayed_rate(
            skill_id, half_life_days=half_life_days
        )

    # ---- queries -------------------------------------------------

    def find_by_trigger(self, query: str) -> list[Skill]:
        """Case-insensitive substring match against triggers."""
        q = query.lower().strip()
        if not q:
            return []
        hits: list[Skill] = []
        for skill in self._skills.values():
            for trigger in skill.triggers:
                if q in trigger.lower() or trigger.lower() in q:
                    hits.append(skill)
                    break
        return hits
