"""Progressive difficulty scheduling for curriculum-based memory learning.

Schedules memory tasks from simple recall through complex synthesis,
adapting difficulty based on measured competency.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum


class DifficultyLevel(StrEnum):
    TRIVIAL = "trivial"
    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"
    EXPERT = "expert"


@dataclass(frozen=True)
class SkillGap:
    skill_name: str
    current_level: DifficultyLevel
    target_level: DifficultyLevel
    gap_score: float
    last_assessed: float


@dataclass(frozen=True)
class TaskCurriculum:
    curriculum_id: str
    skill_name: str
    tasks: list[str]
    difficulty: DifficultyLevel
    prerequisite_ids: list[str]
    created_at: float


class DifficultyScheduler:
    """Schedules memory tasks at progressively increasing difficulty.

    Adapts the curriculum based on measured competency, ensuring
    foundational recall is mastered before advancing to synthesis.
    """

    def __init__(self) -> None:
        self._curricula: dict[str, TaskCurriculum] = {}
        self._completed: dict[str, set[str]] = {}
        self._competency: dict[str, dict[str, float]] = {}

    def schedule(
        self,
        skill_name: str,
        tasks: list[str],
        difficulty: DifficultyLevel,
        prerequisites: list[str] | None = None,
    ) -> TaskCurriculum:
        content = f"{skill_name}|{difficulty.value}|{'|'.join(tasks)}"
        curriculum_id = hashlib.sha256(content.encode()).hexdigest()[:12]

        curriculum = TaskCurriculum(
            curriculum_id=curriculum_id,
            skill_name=skill_name,
            tasks=tasks,
            difficulty=difficulty,
            prerequisite_ids=prerequisites or [],
            created_at=time.time(),
        )
        self._curricula[curriculum_id] = curriculum
        return curriculum

    def get_next(
        self, session_id: str, current_competency: dict[str, float]
    ) -> TaskCurriculum | None:
        completed = self._completed.get(session_id, set())
        available = [
            c
            for c in self._curricula.values()
            if c.curriculum_id not in completed
            and all(p in completed for p in c.prerequisite_ids)
        ]
        if not available:
            return None

        available.sort(
            key=lambda c: (
                self._difficulty_weight(c.difficulty),
                -current_competency.get(c.skill_name, 0.0),
            )
        )
        return available[0]

    def mark_complete(self, session_id: str, curriculum_id: str) -> None:
        self._completed.setdefault(session_id, set()).add(curriculum_id)

    def assess_gap(
        self,
        skill_name: str,
        current_level: DifficultyLevel,
        target_level: DifficultyLevel,
    ) -> SkillGap:
        levels = list(DifficultyLevel)
        current_idx = levels.index(current_level)
        target_idx = levels.index(target_level)
        gap_score = (target_idx - current_idx) / max(len(levels) - 1, 1)

        return SkillGap(
            skill_name=skill_name,
            current_level=current_level,
            target_level=target_level,
            gap_score=round(max(0.0, gap_score), 2),
            last_assessed=time.time(),
        )

    @staticmethod
    def _difficulty_weight(level: DifficultyLevel) -> int:
        return list(DifficultyLevel).index(level)

    def stats(self) -> dict:
        return {
            "total_curricula": len(self._curricula),
            "by_difficulty": {
                d.value: sum(1 for c in self._curricula.values() if c.difficulty == d)
                for d in DifficultyLevel
            },
        }
