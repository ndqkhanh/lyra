"""Tests for the Intelligent Goal Decomposer."""
from __future__ import annotations

import pytest

from lyra_cli.autonomy.intelligent_decomposer import (
    CyclicDependencyError,
    EffortLevel,
    ExecutionWave,
    IntelligentDecomposer,
    IntelligentPlan,
    IntelligentSubtask,
    Priority,
)


class TestIntelligentSubtask:
    def test_create_subtask(self):
        st = IntelligentSubtask(
            id="task_1",
            description="Test task",
            effort=EffortLevel.MEDIUM,
            priority=Priority.HIGH,
        )
        assert st.id == "task_1"
        assert st.effort == EffortLevel.MEDIUM
        assert st.estimated_minutes == 15
        assert st.parallel_group == 0

    def test_subtask_with_dependencies(self):
        st = IntelligentSubtask(
            id="task_2", description="Dependent task",
            effort=EffortLevel.HIGH, priority=Priority.CRITICAL,
            depends_on=("task_1", "task_0"),
        )
        assert len(st.depends_on) == 2

    def test_subtask_is_frozen(self):
        st = IntelligentSubtask(
            id="t1", description="test", effort=EffortLevel.LOW,
            priority=Priority.LOW,
        )
        with pytest.raises(Exception):
            st.description = "changed"  # type: ignore[misc]


class TestIntelligentDecomposer:
    def test_decompose_default_goal(self):
        dec = IntelligentDecomposer()
        plan = dec.decompose("GOAL-1", "Build a general system")
        assert isinstance(plan, IntelligentPlan)
        assert plan.subtask_count == 5
        assert plan.total_estimated_minutes > 0
        assert plan.critical_path_minutes > 0

    def test_decompose_auth_goal(self):
        dec = IntelligentDecomposer()
        plan = dec.decompose("AUTH-1", "Implement user authentication system")
        assert plan.subtask_count == 6
        assert len(plan.waves) >= 1

    def test_decompose_api_goal(self):
        dec = IntelligentDecomposer()
        plan = dec.decompose("API-1", "Build REST API endpoint for users")
        assert plan.subtask_count == 6
        assert any("middleware" in s.description.lower() for s in plan.subtasks)

    def test_decompose_migration_goal(self):
        dec = IntelligentDecomposer()
        plan = dec.decompose("MIG-1", "Database schema migration for v2")
        assert plan.subtask_count == 5
        assert any("rollback" in s.description.lower() for s in plan.subtasks)

    def test_waves_have_increasing_indices(self):
        dec = IntelligentDecomposer()
        plan = dec.decompose("G-1", "Build auth system")
        for i in range(len(plan.waves) - 1):
            assert plan.waves[i].wave_index < plan.waves[i + 1].wave_index

    def test_wave_0_has_no_dependencies(self):
        dec = IntelligentDecomposer()
        plan = dec.decompose("G-1", "Build auth system")
        wave0_ids = set(plan.waves[0].subtask_ids)
        for sid in wave0_ids:
            st = plan.subtask_by_id(sid)
            assert st is not None
            assert len(st.depends_on) == 0

    def test_no_duplicate_ids_in_waves(self):
        dec = IntelligentDecomposer()
        plan = dec.decompose("G-1", "Build auth system")
        all_ids: list[str] = []
        for wave in plan.waves:
            all_ids.extend(wave.subtask_ids)
        assert len(all_ids) == len(set(all_ids))

    def test_progress_starts_at_zero(self):
        dec = IntelligentDecomposer()
        plan = dec.decompose("G-1", "Build auth system")
        assert plan.progress == 0.0

    def test_mark_complete_updates_progress(self):
        dec = IntelligentDecomposer()
        plan = dec.decompose("G-1", "Build auth system")
        first_id = plan.subtasks[0].id
        plan = dec.mark_complete(plan, first_id)
        assert plan.progress > 0.0
        assert plan.subtask_by_id(first_id).metadata.get("completed") is True  # type: ignore[union-attr]

    def test_mark_complete_is_immutable(self):
        dec = IntelligentDecomposer()
        plan = dec.decompose("G-1", "Build auth system")
        first_id = plan.subtasks[0].id
        plan2 = dec.mark_complete(plan, first_id)
        assert plan.subtask_by_id(first_id).metadata.get("completed") is not True  # type: ignore[union-attr]
        assert plan2.subtask_by_id(first_id).metadata.get("completed") is True  # type: ignore[union-attr]

    def test_cyclic_dependency_detected(self):
        dec = IntelligentDecomposer()
        # Manually create a cycle
        dec._generate_subtasks = lambda _g, _d, _c: [  # type: ignore[assignment]
            IntelligentSubtask("a", "Task A", EffortLevel.LOW, Priority.LOW, depends_on=("b",)),
            IntelligentSubtask("b", "Task B", EffortLevel.LOW, Priority.LOW, depends_on=("a",)),
        ]
        with pytest.raises(CyclicDependencyError):
            dec.decompose("CYCLE-1", "Cycle test")

    def test_unknown_dependency_detected(self):
        dec = IntelligentDecomposer()
        dec._generate_subtasks = lambda _g, _d, _c: [  # type: ignore[assignment]
            IntelligentSubtask("a", "Task A", EffortLevel.LOW, Priority.LOW, depends_on=("nonexistent",)),
        ]
        with pytest.raises(CyclicDependencyError, match="unknown"):
            dec.decompose("BAD-1", "Bad dep test")

    def test_subtask_by_id_found(self):
        dec = IntelligentDecomposer()
        plan = dec.decompose("G-1", "Build auth system")
        st = plan.subtask_by_id(plan.subtasks[0].id)
        assert st is not None

    def test_subtask_by_id_not_found(self):
        dec = IntelligentDecomposer()
        plan = dec.decompose("G-1", "Build auth system")
        assert plan.subtask_by_id("nonexistent") is None

    def test_execution_wave_attributes(self):
        wave = ExecutionWave(wave_index=2, subtask_ids=("a", "b", "c"), total_effort_minutes=90)
        assert wave.wave_index == 2
        assert len(wave.subtask_ids) == 3
        assert wave.total_effort_minutes == 90

    def test_critical_path_no_shorter_than_longest_chain(self):
        dec = IntelligentDecomposer()
        plan = dec.decompose("G-1", "Build auth system")
        assert plan.critical_path_minutes > 0

    def test_effort_level_enum(self):
        assert EffortLevel.LOW.value == "low"
        assert EffortLevel.MEDIUM.value == "medium"
        assert EffortLevel.HIGH.value == "high"

    def test_priority_enum(self):
        assert Priority.CRITICAL.value == "critical"
        assert Priority.HIGH.value == "high"
