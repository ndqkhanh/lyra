"""Tests for Hindsight Experience Replay — cross-session learning from past outcomes."""

import time

import pytest
from lyra_core.safety.hindsight import (
    HindsightConfig,
    HindsightEngine,
    HindsightLesson,
    OutcomeType,
    Trajectory,
    TrajectoryStep,
)


class TestOutcomeType:
    def test_outcome_values(self):
        assert OutcomeType.SUCCESS.value == "success"
        assert OutcomeType.FAILURE.value == "failure"
        assert OutcomeType.PARTIAL.value == "partial"
        assert OutcomeType.TIMEOUT.value == "timeout"
        assert OutcomeType.ABORTED.value == "aborted"


class TestTrajectoryStep:
    def test_step_creation(self):
        step = TrajectoryStep(
            step_index=1,
            action="read_file",
            observation="file contents here",
            reward=0.5,
            timestamp=1000.0,
        )
        assert step.step_index == 1
        assert step.action == "read_file"
        assert step.reward == 0.5

    def test_step_negative_reward(self):
        step = TrajectoryStep(
            step_index=3,
            action="delete_file",
            observation="error: permission denied",
            reward=-0.8,
            timestamp=2000.0,
        )
        assert step.reward < 0

    def test_step_immutable(self):
        s = TrajectoryStep(1, "read", "ok", 1.0, 0.0)
        with pytest.raises(Exception):
            s.reward = -1.0


class TestTrajectory:
    def test_successful_trajectory(self):
        steps = (
            TrajectoryStep(0, "plan", "made plan", 0.3, 1.0),
            TrajectoryStep(1, "execute", "ran command", 0.7, 2.0),
        )
        traj = Trajectory(
            trajectory_id="traj-001",
            goal="list files in directory",
            steps=steps,
            outcome=OutcomeType.SUCCESS,
            final_score=1.0,
            session_id="session-1",
            started_at=0.0,
            completed_at=10.0,
            tags=(),
        )
        assert traj.outcome == OutcomeType.SUCCESS
        assert traj.step_count == 2
        assert traj.total_reward == 1.0

    def test_failed_trajectory(self):
        steps = (
            TrajectoryStep(0, "attempt", "tried", -0.5, 1.0),
            TrajectoryStep(1, "error", "failed", -1.0, 2.0),
        )
        traj = Trajectory(
            trajectory_id="traj-002",
            goal="deploy production",
            steps=steps,
            outcome=OutcomeType.FAILURE,
            final_score=-1.5,
            session_id="s2",
            started_at=5.0,
            completed_at=10.0,
            tags=("critical",),
        )
        assert traj.outcome == OutcomeType.FAILURE
        assert traj.total_reward == -1.5

    def test_trajectory_immutable(self):
        t = Trajectory("t1", "goal", (), OutcomeType.SUCCESS, 1.0, "s1", 0.0, 1.0, ())
        with pytest.raises(Exception):
            t.outcome = OutcomeType.FAILURE


class TestHindsightLesson:
    def test_lesson_creation(self):
        lesson = HindsightLesson(
            lesson_id="hl-001",
            trajectory_id="traj-005",
            goal="read config file",
            insight="Used wrong path; use absolute paths instead",
            alternative_action="use_absolute_path",
            expected_improvement=0.5,
            confidence=0.8,
            extracted_at=time.time(),
            tags=(),
        )
        assert lesson.insight is not None
        assert lesson.confidence == 0.8

    def test_lesson_immutable(self):
        h = HindsightLesson("h1", "t1", "goal", "insight", "alt", 0.5, 0.8, 0.0, ())
        with pytest.raises(Exception):
            h.confidence = 0.1


class TestHindsightConfig:
    def test_default_config(self):
        config = HindsightConfig()
        assert config.min_trajectory_steps == 2
        assert config.lesson_min_confidence == 0.3
        assert config.max_lessons_per_trajectory == 3

    def test_custom_config(self):
        config = HindsightConfig(min_trajectory_steps=3, max_lessons_per_trajectory=5)
        assert config.min_trajectory_steps == 3


class TestHindsightEngine:
    def test_store_trajectory(self):
        engine = HindsightEngine()
        steps = (TrajectoryStep(0, "action", "obs", 0.5, 0.0),)
        traj = Trajectory("t1", "goal", steps, OutcomeType.SUCCESS, 0.5, "s1", 0.0, 1.0, ())
        engine.store(traj)
        assert engine.trajectory_count == 1

    def test_extract_lessons_from_failure(self):
        engine = HindsightEngine()
        steps = (
            TrajectoryStep(0, "action", "observation", -0.3, 1.0),
            TrajectoryStep(1, "better_action", "good result", 0.9, 2.0),
        )
        traj = Trajectory("t-fail", "deploy app", steps, OutcomeType.FAILURE, -1.2, "s1", 0.0, 1.0, ())
        engine.store(traj)
        lessons = engine.extract_lessons("t-fail")
        assert isinstance(lessons, list)

    def test_extract_lessons_unknown_id(self):
        engine = HindsightEngine()
        lessons = engine.extract_lessons("unknown_id")
        assert lessons == []

    def test_get_lessons_for_goal(self):
        engine = HindsightEngine()
        steps = (
            TrajectoryStep(0, "bad", "oops", -0.5, 0.0),
            TrajectoryStep(1, "good", "yay", 0.9, 1.0),
        )
        traj = Trajectory("t-g", "install package", steps, OutcomeType.FAILURE, -0.5, "s1", 0.0, 1.0, ())
        engine.store(traj)
        engine.extract_lessons("t-g")
        lessons = engine.get_lessons_for_goal("install package")
        assert isinstance(lessons, list)

    def test_store_multiple_trajectories(self):
        engine = HindsightEngine()
        for i in range(5):
            steps = (TrajectoryStep(0, f"action_{i}", "obs", 0.5, float(i)),)
            traj = Trajectory(f"t-{i}", "goal", steps, OutcomeType.SUCCESS, 0.5, f"s{i}", 0.0, 1.0, ())
            engine.store(traj)
        assert engine.trajectory_count == 5

    def test_stats(self):
        engine = HindsightEngine()
        steps = (TrajectoryStep(0, "a", "o", 0.5, 0.0),)
        engine.store(Trajectory("t1", "goal", steps, OutcomeType.SUCCESS, 0.5, "s1", 0.0, 1.0, ()))
        stats = engine.stats()
        assert "trajectories" in stats
        assert "lessons" in stats
        assert "success_rate" in stats

    def test_stats_empty(self):
        engine = HindsightEngine()
        stats = engine.stats()
        assert stats["trajectories"] == 0

    def test_query_lessons(self):
        engine = HindsightEngine()
        steps = (
            TrajectoryStep(0, "bad", "err", -0.5, 0.0),
            TrajectoryStep(1, "good", "ok", 0.8, 1.0),
        )
        traj = Trajectory("t-query", "deploy to production", steps, OutcomeType.FAILURE, -0.3, "s1", 0.0, 1.0, ())
        engine.store(traj)
        engine.extract_lessons("t-query")
        lessons = engine.query_lessons("deploy production")
        assert isinstance(lessons, list)
