"""Tests for SprintPipeline — agent team sprint orchestration."""

import time

import pytest

from lyra_core.teams.sprint_pipeline import (
    Sprint,
    SprintPhase,
    SprintPipeline,
    SprintTask,
    TaskPriority,
    TaskStatus,
)


class TestTaskStatus:
    def test_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.BLOCKED.value == "blocked"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.SKIPPED.value == "skipped"


class TestTaskPriority:
    def test_values(self):
        assert TaskPriority.CRITICAL.value == "critical"
        assert TaskPriority.HIGH.value == "high"


class TestSprintPhase:
    def test_values(self):
        assert SprintPhase.PLANNING.value == "planning"
        assert SprintPhase.DECOMPOSITION.value == "decomposition"
        assert SprintPhase.EXECUTION.value == "execution"
        assert SprintPhase.REVIEW.value == "review"
        assert SprintPhase.RETROSPECTIVE.value == "retrospective"


class TestSprintTask:
    def test_create(self):
        task = SprintTask(
            task_id="t1",
            title="Design auth schema",
            description="Design the authentication database schema",
            assigned_agent="sentinel",
            priority=TaskPriority.HIGH,
            estimated_effort_min=30.0,
        )
        assert task.task_id == "t1"
        assert task.status == TaskStatus.PENDING
        assert not task.is_blocked
        assert not task.is_completed

    def test_immutable(self):
        task = SprintTask(
            task_id="t", title="T", description="D",
            assigned_agent="a", priority=TaskPriority.MEDIUM,
            estimated_effort_min=1.0,
        )
        with pytest.raises(Exception):
            task.title = "hacked"  # type: ignore[misc]

    def test_is_blocked(self):
        task = SprintTask(
            task_id="t", title="T", description="D",
            assigned_agent="a", priority=TaskPriority.MEDIUM,
            estimated_effort_min=1.0, status=TaskStatus.BLOCKED,
        )
        assert task.is_blocked

    def test_is_completed(self):
        task = SprintTask(
            task_id="t", title="T", description="D",
            assigned_agent="a", priority=TaskPriority.MEDIUM,
            estimated_effort_min=1.0, status=TaskStatus.COMPLETED,
        )
        assert task.is_completed


class TestSprint:
    def test_create(self):
        sprint = Sprint(
            sprint_id="s1",
            goal="Implement auth flow",
            phase=SprintPhase.PLANNING,
            tasks=[],
            team_agents=["sentinel", "hephaestus"],
            created_at=time.time(),
        )
        assert sprint.sprint_id == "s1"
        assert sprint.goal == "Implement auth flow"
        assert not sprint.is_active
        assert sprint.progress_pct == 100.0  # no tasks = 100%

    def test_progress_pct(self):
        t1 = SprintTask(
            task_id="t1", title="T1", description="D1",
            assigned_agent="a", priority=TaskPriority.HIGH,
            estimated_effort_min=10.0, status=TaskStatus.COMPLETED,
        )
        t2 = SprintTask(
            task_id="t2", title="T2", description="D2",
            assigned_agent="b", priority=TaskPriority.MEDIUM,
            estimated_effort_min=10.0, status=TaskStatus.PENDING,
        )
        sprint = Sprint(
            sprint_id="s", goal="G", phase=SprintPhase.EXECUTION,
            tasks=[t1, t2], team_agents=["a", "b"],
            created_at=time.time(), started_at=time.time(),
        )
        assert sprint.progress_pct == 50.0

    def test_is_active(self):
        sprint = Sprint(
            sprint_id="s", goal="G", phase=SprintPhase.EXECUTION,
            tasks=[], team_agents=["a"],
            created_at=time.time(), started_at=time.time(),
        )
        assert sprint.is_active

    def test_blocked_tasks(self):
        t1 = SprintTask(
            task_id="t1", title="T1", description="D1",
            assigned_agent="a", priority=TaskPriority.HIGH,
            estimated_effort_min=10.0, status=TaskStatus.BLOCKED,
        )
        t2 = SprintTask(
            task_id="t2", title="T2", description="D2",
            assigned_agent="b", priority=TaskPriority.MEDIUM,
            estimated_effort_min=10.0,
        )
        sprint = Sprint(
            sprint_id="s", goal="G", phase=SprintPhase.EXECUTION,
            tasks=[t1, t2], team_agents=["a", "b"],
            created_at=time.time(),
        )
        assert len(sprint.blocked_tasks) == 1


class TestSprintPipeline:
    def test_create_sprint(self):
        pipeline = SprintPipeline()
        sprint = pipeline.create_sprint(
            goal="Implement user auth",
            team_agents=["sentinel", "hephaestus", "hermes"],
        )
        assert sprint.goal == "Implement user auth"
        assert len(sprint.team_agents) == 3
        assert sprint.phase == SprintPhase.PLANNING
        assert len(sprint.sprint_id) == 16

    def test_decompose_goal(self):
        pipeline = SprintPipeline()
        sprint = pipeline.create_sprint(
            goal="Build API", team_agents=["hephaestus"],
        )
        tasks = pipeline.decompose_goal(
            sprint.sprint_id,
            [
                ("Design schema", "hephaestus", TaskPriority.HIGH, 30.0),
                ("Implement endpoint", "hephaestus", TaskPriority.CRITICAL, 60.0),
                ("Write tests", "hephaestus", TaskPriority.MEDIUM, 45.0),
            ],
        )
        assert len(tasks) == 3
        sprint_updated = pipeline.get_sprint(sprint.sprint_id)
        assert sprint_updated is not None
        assert sprint_updated.phase == SprintPhase.DECOMPOSITION

    def test_decompose_nonexistent_sprint(self):
        pipeline = SprintPipeline()
        with pytest.raises(KeyError):
            pipeline.decompose_goal("fake-id", [])

    def test_add_dependency(self):
        pipeline = SprintPipeline()
        sprint = pipeline.create_sprint(goal="G", team_agents=["a"])
        tasks = pipeline.decompose_goal(
            sprint.sprint_id,
            [
                ("Task 1", "a", TaskPriority.HIGH, 10.0),
                ("Task 2", "a", TaskPriority.HIGH, 10.0),
            ],
        )
        assert pipeline.add_dependency(sprint.sprint_id, tasks[1].task_id, tasks[0].task_id)
        # Task 2 should now depend on Task 1
        sprint_updated = pipeline.get_sprint(sprint.sprint_id)
        assert sprint_updated is not None
        task2 = [t for t in sprint_updated.tasks if t.title == "Task 2"][0]
        assert tasks[0].task_id in task2.depends_on

    def test_add_dependency_nonexistent(self):
        pipeline = SprintPipeline()
        assert pipeline.add_dependency("fake", "t1", "t2") is False

    def test_start_sprint(self):
        pipeline = SprintPipeline()
        sprint = pipeline.create_sprint(goal="G", team_agents=["a"])
        started = pipeline.start(sprint.sprint_id)
        assert started is not None
        assert started.phase == SprintPhase.EXECUTION
        assert started.started_at is not None

    def test_start_nonexistent(self):
        pipeline = SprintPipeline()
        assert pipeline.start("fake") is None

    def test_update_task_status(self):
        pipeline = SprintPipeline()
        sprint = pipeline.create_sprint(goal="G", team_agents=["a"])
        tasks = pipeline.decompose_goal(
            sprint.sprint_id,
            [("Task 1", "a", TaskPriority.HIGH, 10.0)],
        )
        pipeline.start(sprint.sprint_id)
        updated = pipeline.update_task_status(
            sprint.sprint_id, tasks[0].task_id, TaskStatus.COMPLETED, output="Done!",
        )
        assert updated is not None
        assert updated.status == TaskStatus.COMPLETED
        assert updated.output == "Done!"
        assert updated.completed_at is not None

    def test_update_task_nonexistent(self):
        pipeline = SprintPipeline()
        assert pipeline.update_task_status("fake", "t1", TaskStatus.COMPLETED) is None

    def test_auto_advance_to_review(self):
        pipeline = SprintPipeline()
        sprint = pipeline.create_sprint(goal="G", team_agents=["a"])
        tasks = pipeline.decompose_goal(
            sprint.sprint_id,
            [("Task 1", "a", TaskPriority.HIGH, 10.0)],
        )
        pipeline.start(sprint.sprint_id)
        pipeline.update_task_status(sprint.sprint_id, tasks[0].task_id, TaskStatus.COMPLETED)
        sprint_updated = pipeline.get_sprint(sprint.sprint_id)
        assert sprint_updated is not None
        assert sprint_updated.phase == SprintPhase.REVIEW

    def test_complete_sprint(self):
        pipeline = SprintPipeline()
        sprint = pipeline.create_sprint(goal="G", team_agents=["a"])
        pipeline.start(sprint.sprint_id)
        completed = pipeline.complete_sprint(
            sprint.sprint_id, retrospective_notes="Went well, need better tests"
        )
        assert completed is not None
        assert completed.phase == SprintPhase.RETROSPECTIVE
        assert completed.completed_at is not None
        assert completed.retrospective_notes == "Went well, need better tests"

    def test_complete_nonexistent(self):
        pipeline = SprintPipeline()
        assert pipeline.complete_sprint("fake") is None

    def test_get_active_sprints(self):
        pipeline = SprintPipeline()
        s1 = pipeline.create_sprint(goal="Active", team_agents=["a"])
        s2 = pipeline.create_sprint(goal="Inactive", team_agents=["a"])
        pipeline.start(s1.sprint_id)
        active = pipeline.get_active_sprints()
        assert len(active) == 1
        assert active[0].goal == "Active"

    def test_get_next_available_tasks(self):
        pipeline = SprintPipeline()
        sprint = pipeline.create_sprint(goal="G", team_agents=["a"])
        tasks = pipeline.decompose_goal(
            sprint.sprint_id,
            [
                ("Dep task", "a", TaskPriority.HIGH, 10.0),
                ("Main task", "a", TaskPriority.HIGH, 10.0),
            ],
        )
        pipeline.add_dependency(sprint.sprint_id, tasks[1].task_id, tasks[0].task_id)

        # Before completing dep — only dep task is available
        available = pipeline.get_next_available_tasks(sprint.sprint_id)
        assert len(available) == 1
        assert available[0].title == "Dep task"

        # Complete dep task
        pipeline.update_task_status(sprint.sprint_id, tasks[0].task_id, TaskStatus.COMPLETED)

        # Now main task should be available
        available = pipeline.get_next_available_tasks(sprint.sprint_id)
        assert len(available) == 1
        assert available[0].title == "Main task"

    def test_stats(self):
        pipeline = SprintPipeline()
        s = pipeline.create_sprint(goal="G", team_agents=["a"])
        pipeline.start(s.sprint_id)
        pipeline.complete_sprint(s.sprint_id)
        stats = pipeline.stats()
        assert stats["total_sprints"] == 1
        assert stats["active_sprints"] == 0
        assert stats["completed_sprints"] == 1
