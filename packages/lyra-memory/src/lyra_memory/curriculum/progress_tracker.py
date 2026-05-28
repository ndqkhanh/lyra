"""Progress tracking for curriculum-based memory learning.

Tracks competency across skill domains and manages phase transitions
as learners advance through the curriculum.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum


class CurriculumPhase(StrEnum):
    FOUNDATIONAL = "foundational"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    MASTERY = "mastery"


@dataclass(frozen=True)
class CompetencyMap:
    session_id: str
    skill_scores: dict[str, float]
    current_phase: CurriculumPhase
    tasks_completed: int
    tasks_total: int
    updated_at: float

    @property
    def completion_pct(self) -> float:
        if self.tasks_total == 0:
            return 0.0
        return round(self.tasks_completed / self.tasks_total * 100, 1)

    @property
    def average_competency(self) -> float:
        if not self.skill_scores:
            return 0.0
        return round(sum(self.skill_scores.values()) / len(self.skill_scores), 2)


class ProgressTracker:
    """Tracks learner progress through the curriculum phases.

    Maintains competency scores per skill domain and manages
    phase transitions based on demonstrated mastery thresholds.
    """

    PHASE_THRESHOLDS: dict[CurriculumPhase, float] = {
        CurriculumPhase.FOUNDATIONAL: 0.0,
        CurriculumPhase.INTERMEDIATE: 0.4,
        CurriculumPhase.ADVANCED: 0.7,
        CurriculumPhase.MASTERY: 0.9,
    }

    def __init__(self) -> None:
        self._competency_maps: dict[str, CompetencyMap] = {}
        self._phase_history: dict[str, list[tuple[CurriculumPhase, float]]] = {}

    def initialize(self, session_id: str, skill_names: list[str]) -> CompetencyMap:
        cm = CompetencyMap(
            session_id=session_id,
            skill_scores={s: 0.0 for s in skill_names},
            current_phase=CurriculumPhase.FOUNDATIONAL,
            tasks_completed=0,
            tasks_total=0,
            updated_at=time.time(),
        )
        self._competency_maps[session_id] = cm
        self._phase_history[session_id] = [(CurriculumPhase.FOUNDATIONAL, time.time())]
        return cm

    def update_skill(self, session_id: str, skill_name: str, score: float) -> CompetencyMap:
        current = self._competency_maps.get(session_id)
        if current is None:
            return self.initialize(session_id, [skill_name])

        new_scores = {**current.skill_scores, skill_name: min(1.0, max(0.0, score))}
        avg = sum(new_scores.values()) / max(len(new_scores), 1)
        new_phase = self._evaluate_phase(avg)

        if new_phase != current.current_phase:
            self._phase_history.setdefault(session_id, []).append(
                (new_phase, time.time())
            )

        cm = CompetencyMap(
            session_id=session_id,
            skill_scores=new_scores,
            current_phase=new_phase,
            tasks_completed=current.tasks_completed + 1,
            tasks_total=current.tasks_total,
            updated_at=time.time(),
        )
        self._competency_maps[session_id] = cm
        return cm

    def set_task_count(self, session_id: str, total: int) -> None:
        current = self._competency_maps.get(session_id)
        if current:
            self._competency_maps[session_id] = CompetencyMap(
                session_id=session_id,
                skill_scores=current.skill_scores,
                current_phase=current.current_phase,
                tasks_completed=current.tasks_completed,
                tasks_total=total,
                updated_at=time.time(),
            )

    def get_progress(self, session_id: str) -> CompetencyMap | None:
        return self._competency_maps.get(session_id)

    def get_phase_history(self, session_id: str) -> list[tuple[CurriculumPhase, float]]:
        return self._phase_history.get(session_id, [])

    def _evaluate_phase(self, average_score: float) -> CurriculumPhase:
        if average_score >= self.PHASE_THRESHOLDS[CurriculumPhase.MASTERY]:
            return CurriculumPhase.MASTERY
        if average_score >= self.PHASE_THRESHOLDS[CurriculumPhase.ADVANCED]:
            return CurriculumPhase.ADVANCED
        if average_score >= self.PHASE_THRESHOLDS[CurriculumPhase.INTERMEDIATE]:
            return CurriculumPhase.INTERMEDIATE
        return CurriculumPhase.FOUNDATIONAL

    def stats(self) -> dict:
        phases = [cm.current_phase for cm in self._competency_maps.values()]
        return {
            "sessions_tracked": len(self._competency_maps),
            "by_phase": {p.value: phases.count(p) for p in CurriculumPhase},
        }
