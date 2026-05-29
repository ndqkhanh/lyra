"""Hindsight Experience Replay — cross-session learning from past outcomes.

Stores execution trajectories with outcomes and enables retrospective
analysis: "Given what I know now, what should I have done differently?"

Based on Hindsight Experience Replay (HER) adapted for agent trajectories.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum


class OutcomeType(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ABORTED = "aborted"


@dataclass(frozen=True)
class TrajectoryStep:
    step_index: int
    action: str
    observation: str
    reward: float
    timestamp: float


@dataclass(frozen=True)
class Trajectory:
    trajectory_id: str
    goal: str
    steps: tuple[TrajectoryStep, ...]
    outcome: OutcomeType
    final_score: float
    session_id: str
    started_at: float
    completed_at: float
    tags: tuple[str, ...]

    @property
    def step_count(self) -> int:
        return len(self.steps)

    @property
    def total_reward(self) -> float:
        return sum(s.reward for s in self.steps)


@dataclass(frozen=True)
class HindsightLesson:
    """A lesson derived from hindsight analysis of a trajectory."""

    lesson_id: str
    trajectory_id: str
    goal: str
    insight: str
    alternative_action: str
    expected_improvement: float
    confidence: float
    extracted_at: float
    tags: tuple[str, ...]


@dataclass
class HindsightConfig:
    min_trajectory_steps: int = 2
    lesson_min_confidence: float = 0.3
    max_lessons_per_trajectory: int = 3
    similarity_threshold: float = 0.6


class HindsightEngine:
    """Cross-session hindsight experience replay engine.

    Stores completed trajectories and extracts lessons by retrospectively
    analyzing what could have been done differently given the final outcome.
    Lessons are indexed by goal similarity for cross-session retrieval.
    """

    def __init__(self, config: HindsightConfig | None = None) -> None:
        self.config = config or HindsightConfig()
        self._trajectories: dict[str, Trajectory] = {}
        self._lessons: dict[str, HindsightLesson] = {}
        self._goal_index: dict[str, list[str]] = defaultdict(list)
        self._counter: int = 0

    def store(self, trajectory: Trajectory) -> None:
        self._trajectories[trajectory.trajectory_id] = trajectory
        goal_key = _normalize_goal(trajectory.goal)
        self._goal_index[goal_key].append(trajectory.trajectory_id)

    def extract_lessons(self, trajectory_id: str) -> list[HindsightLesson]:
        """Extract hindsight lessons from a completed trajectory.

        Analyzes each step where reward was negative or suboptimal and
        generates alternative action suggestions.
        """
        trajectory = self._trajectories.get(trajectory_id)
        if not trajectory or trajectory.step_count < self.config.min_trajectory_steps:
            return []

        lessons: list[HindsightLesson] = []
        best_step_idx = max(range(len(trajectory.steps)), key=lambda i: trajectory.steps[i].reward)

        for i, step in enumerate(trajectory.steps):
            if len(lessons) >= self.config.max_lessons_per_trajectory:
                break

            if step.reward >= 0:
                continue

            best_step = trajectory.steps[best_step_idx]
            confidence = min(0.9, abs(step.reward) / max(abs(best_step.reward), 0.01))

            if confidence < self.config.lesson_min_confidence:
                continue

            self._counter += 1
            lesson = HindsightLesson(
                lesson_id=f"hl-{self._counter:06d}",
                trajectory_id=trajectory_id,
                goal=trajectory.goal,
                insight=f"Step {i}: '{step.action}' led to negative reward. "
                        f"Consider using approach similar to step {best_step_idx}: '{best_step.action}'",
                alternative_action=best_step.action,
                expected_improvement=abs(step.reward - best_step.reward),
                confidence=round(confidence, 4),
                extracted_at=time.time(),
                tags=trajectory.tags,
            )
            lessons.append(lesson)
            self._lessons[lesson.lesson_id] = lesson

        return lessons

    def query_lessons(self, goal: str, limit: int = 5) -> list[HindsightLesson]:
        """Retrieve relevant hindsight lessons for a given goal.

        Matches by normalized goal key similarity and returns lessons sorted
        by expected improvement (highest first).
        """
        goal_key = _normalize_goal(goal)
        candidate_ids: list[str] = []

        for key, traj_ids in self._goal_index.items():
            if _goal_similarity(goal_key, key) >= self.config.similarity_threshold:
                candidate_ids.extend(traj_ids)

        relevant: list[HindsightLesson] = []
        for lesson in self._lessons.values():
            if lesson.trajectory_id in candidate_ids:
                relevant.append(lesson)

        relevant.sort(key=lambda x: x.expected_improvement, reverse=True)
        return relevant[:limit]

    def get_lessons_for_goal(self, goal: str) -> list[HindsightLesson]:
        """Get all lessons extracted from trajectories with the same goal."""
        goal_key = _normalize_goal(goal)
        traj_ids = self._goal_index.get(goal_key, [])
        return [lesson for lesson in self._lessons.values() if lesson.trajectory_id in traj_ids]

    @property
    def trajectory_count(self) -> int:
        return len(self._trajectories)

    @property
    def lesson_count(self) -> int:
        return len(self._lessons)

    def stats(self) -> dict:
        if not self._trajectories:
            return {"trajectories": 0, "lessons": 0, "success_rate": 0.0}

        success_count = sum(1 for t in self._trajectories.values() if t.outcome == OutcomeType.SUCCESS)
        return {
            "trajectories": len(self._trajectories),
            "lessons": len(self._lessons),
            "success_rate": round(success_count / len(self._trajectories), 4),
            "mean_steps": round(sum(t.step_count for t in self._trajectories.values()) / len(self._trajectories), 2),
        }


def _normalize_goal(goal: str) -> str:
    return goal.strip().lower()


def _goal_similarity(a: str, b: str) -> float:
    """Simple word-overlap similarity between two goal strings."""
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    return len(intersection) / max(len(words_a), len(words_b))
