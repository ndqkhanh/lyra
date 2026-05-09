"""Skill registry: stores every reusable skill with its trigger terms.

A :class:`Skill` is the minimal shape the router needs to match
and rank — a unique id, a human-readable description, a set of
trigger phrases the router searches against, and a mutable
``success_rate`` that updates as the skill is used.

The registry is intentionally thin: no eviction policy yet
(Task 10 will add that) and no persistence layer (it's held in
memory; callers snapshot to JSON if they want durability).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


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

    # ---- CRUD ----------------------------------------------------

    def register(self, skill: Skill) -> None:
        if skill.id in self._skills:
            raise SkillAlreadyExists(f"skill {skill.id!r} already registered")
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
        return skill

    def record_miss(self, skill_id: str) -> Skill:
        skill = self.get(skill_id)
        skill.miss_count += 1
        return skill

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
