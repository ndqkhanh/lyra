"""Agentic Lifelong Learning Protocol — SkillFlow pattern for continuous skill improvement.

Agents start without skills, externalize lessons from their trajectories,
carry an updated skill library, and evaluate improvements through benchmarking.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .exceptions import PatchError
from .skill_benchmark import SkillBenchmark
from .trajectory_patcher import Skill, TrajectoryPatch, TrajectoryPatcher


@dataclass(frozen=True)
class LearningConfig:
    """Configuration for a lifelong learning cycle.

    Attributes:
        max_patches_per_cycle: Maximum patches to apply in a single cycle.
        min_improvement: Minimum benchmark score improvement required (fraction).
        rollback_on_regression: Whether to rollback if score decreases.
    """

    max_patches_per_cycle: int = 10
    min_improvement: float = 0.01
    rollback_on_regression: bool = True


@dataclass(frozen=True)
class LearningCycle:
    """Record of a completed learning cycle.

    Attributes:
        cycle_id: Unique identifier for this cycle.
        start_version: Skill version at cycle start.
        end_version: Skill version at cycle end.
        patches_applied: Number of patches applied during the cycle.
        score_delta: Change in benchmark score (fraction, can be negative).
    """

    cycle_id: str
    start_version: str
    end_version: str
    patches_applied: int
    score_delta: float


@dataclass(frozen=True)
class LearningState:
    """Current state of the lifelong learning system.

    Attributes:
        current_version: Current skill version string.
        history: Ordered list of completed learning cycles.
        total_improvement: Cumulative benchmark score improvement.
    """

    current_version: str = "0.1.0"
    history: list[LearningCycle] = field(default_factory=list)
    total_improvement: float = 0.0


class LifelongLearner:
    """Agentic Lifelong Learning Protocol engine.

    Implements the SkillFlow learning loop:
    1. Agents execute tasks using current skills
    2. Trajectories are analyzed to extract lessons
    3. Lessons are externalized as skill patches
    4. Patched skills are evaluated against benchmarks
    5. Successful patches are committed; regressions trigger rollback
    """

    def __init__(
        self,
        config: LearningConfig | None = None,
        benchmark: SkillBenchmark | None = None,
        patcher: TrajectoryPatcher | None = None,
    ) -> None:
        self.config = config or LearningConfig()
        self.benchmark = benchmark or SkillBenchmark()
        self.patcher = patcher or TrajectoryPatcher()
        self.state = LearningState()
        self._trajectory_cache: list[dict[str, Any]] = []

    def run_learning_cycle(
        self,
        agent_traces: list[dict[str, Any]],
        current_skills: list[Skill],
        task_filter: str | None = None,
    ) -> LearningCycle:
        """Execute one complete learning cycle.

        Args:
            agent_traces: List of agent trajectory dictionaries.
            current_skills: Current set of skills to improve.
            task_filter: Optional benchmark task filter.

        Returns:
            A LearningCycle record with the results.

        Raises:
            EvolutionError: If the learning cycle fails.
        """
        cycle_id = f"cycle_{int(time.time())}"
        self._trajectory_cache.extend(agent_traces)

        # Phase 1: Externalize lessons from trajectories
        patches = self.patcher.extract_patches(agent_traces)
        patches = patches[:self.config.max_patches_per_cycle]

        if not patches:
            return LearningCycle(
                cycle_id=cycle_id,
                start_version=self.state.current_version,
                end_version=self.state.current_version,
                patches_applied=0,
                score_delta=0.0,
            )

        # Phase 2: Apply patches (one skill at a time)
        patched_skills: list[Skill] = []
        patches_applied = 0
        for skill in current_skills:
            skill_patches = [p for p in patches if p.skill_id == skill.skill_id]
            if skill_patches:
                try:
                    patched = self.patcher.batch_apply(skill, skill_patches)
                    patched_skills.append(patched)
                    patches_applied += len(skill_patches)
                except PatchError:
                    patched_skills.append(skill)
            else:
                patched_skills.append(skill)

        # Phase 3: Evaluate against benchmark
        before_report = self.benchmark.run_benchmark(current_skills, task_filter)
        after_report = self.benchmark.run_benchmark(patched_skills, task_filter)

        score_delta = after_report.overall_score - before_report.overall_score

        # Phase 4: Handle regression if needed
        end_version = self.state.current_version
        if score_delta < -0.01 and self.config.rollback_on_regression:
            end_version = self.state.current_version
            patched_skills = current_skills
        elif score_delta > 0:
            end_version = self._bump_version(self.state.current_version)

        cycle = LearningCycle(
            cycle_id=cycle_id,
            start_version=self.state.current_version,
            end_version=end_version,
            patches_applied=patches_applied,
            score_delta=score_delta,
        )

        self.state = LearningState(
            current_version=end_version,
            history=[*self.state.history, cycle],
            total_improvement=self.state.total_improvement + score_delta,
        )

        return cycle

    def externalize_lessons(self, traces: list[dict[str, Any]]) -> list[TrajectoryPatch]:
        """Externalize lessons from agent traces as skill patches.

        Args:
            traces: List of agent trajectory dictionaries.

        Returns:
            List of TrajectoryPatch instances extracted from the traces.
        """
        return self.patcher.extract_patches(traces)

    def evaluate_cycle(
        self,
        before_skills: list[Skill],
        after_skills: list[Skill],
        benchmark: SkillBenchmark | None = None,
    ) -> float:
        """Evaluate the score delta between two skill sets.

        Args:
            before_skills: Skills before the cycle.
            after_skills: Skills after the cycle.
            benchmark: Optional benchmark instance. Uses self.benchmark if None.

        Returns:
            Score delta (after score - before score).
        """
        bm = benchmark or self.benchmark
        before_report = bm.run_benchmark(before_skills)
        after_report = bm.run_benchmark(after_skills)
        return after_report.overall_score - before_report.overall_score

    def _bump_version(self, version: str) -> str:
        """Bump a semver patch version.

        Args:
            version: Current version string.

        Returns:
            Bumped version string.
        """
        parts = version.split(".")
        if len(parts) == 3:
            parts[2] = str(int(parts[2]) + 1)
        return ".".join(parts)
