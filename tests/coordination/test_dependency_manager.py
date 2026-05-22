"""
Tests for Dependency Manager.
"""

import pytest
from src.coordination import DependencyManager, DependencyType
from src.core.task import Task, TaskType, TaskStatus


class TestDependencyManager:
    """Test DependencyManager class."""

    def test_dependency_manager_creation(self):
        """Test dependency manager creation."""
        manager = DependencyManager()
        
        assert len(manager.dependencies) == 0
        assert len(manager.graph.nodes) == 0

    def test_add_dependency(self):
        """Test adding a dependency."""
        manager = DependencyManager()
        
        task1 = Task(type=TaskType.CODE_GENERATION, description="Task 1")
        task2 = Task(type=TaskType.CODE_ANALYSIS, description="Task 2")
        
        manager.add_dependency(task2, task1)
        
        assert task2.task_id in manager.dependencies
        assert len(manager.dependencies[task2.task_id]) == 1

    def test_add_multiple_dependencies(self):
        """Test adding multiple dependencies."""
        manager = DependencyManager()
        
        task1 = Task(type=TaskType.CODE_GENERATION, description="Task 1")
        task2 = Task(type=TaskType.CODE_ANALYSIS, description="Task 2")
        task3 = Task(type=TaskType.CODE_REVIEW, description="Task 3")
        
        manager.add_dependency(task3, task1)
        manager.add_dependency(task3, task2)
        
        assert len(manager.dependencies[task3.task_id]) == 2

    def test_get_dependencies(self):
        """Test getting task dependencies."""
        manager = DependencyManager()
        
        task1 = Task(type=TaskType.CODE_GENERATION, description="Task 1")
        task2 = Task(type=TaskType.CODE_ANALYSIS, description="Task 2")
        
        manager.add_dependency(task2, task1)
        
        deps = manager.get_dependencies(task2)
        
        assert len(deps) == 1
        assert deps[0].depends_on == task1.task_id

    def test_get_dependencies_none(self):
        """Test getting dependencies for task with none."""
        manager = DependencyManager()
        
        task = Task(type=TaskType.CODE_GENERATION, description="Task")
        deps = manager.get_dependencies(task)
        
        assert len(deps) == 0

    def test_get_dependents(self):
        """Test getting tasks that depend on a task."""
        manager = DependencyManager()
        
        task1 = Task(type=TaskType.CODE_GENERATION, description="Task 1")
        task2 = Task(type=TaskType.CODE_ANALYSIS, description="Task 2")
        task3 = Task(type=TaskType.CODE_REVIEW, description="Task 3")
        
        manager.add_dependency(task2, task1)
        manager.add_dependency(task3, task1)
        
        dependents = manager.get_dependents(task1)
        
        assert len(dependents) == 2
        assert task2.task_id in dependents
        assert task3.task_id in dependents

    def test_is_ready_no_dependencies(self):
        """Test task is ready when no dependencies."""
        manager = DependencyManager()
        
        task = Task(type=TaskType.CODE_GENERATION, description="Task")
        
        assert manager.is_ready(task) is True

    def test_is_ready_with_completed_dependency(self):
        """Test task is ready when dependency completed."""
        manager = DependencyManager()
        
        task1 = Task(type=TaskType.CODE_GENERATION, description="Task 1")
        task2 = Task(type=TaskType.CODE_ANALYSIS, description="Task 2")
        
        task1.status = TaskStatus.COMPLETED
        
        manager.add_dependency(task2, task1)
        
        assert manager.is_ready(task2) is True

    def test_is_ready_with_pending_dependency(self):
        """Test task is not ready when dependency pending."""
        manager = DependencyManager()
        
        task1 = Task(type=TaskType.CODE_GENERATION, description="Task 1")
        task2 = Task(type=TaskType.CODE_ANALYSIS, description="Task 2")
        
        manager.add_dependency(task2, task1)
        
        assert manager.is_ready(task2) is False

    def test_get_ready_tasks(self):
        """Test getting all ready tasks."""
        manager = DependencyManager()
        
        task1 = Task(type=TaskType.CODE_GENERATION, description="Task 1")
        task2 = Task(type=TaskType.CODE_ANALYSIS, description="Task 2")
        task3 = Task(type=TaskType.CODE_REVIEW, description="Task 3")
        
        task1.status = TaskStatus.COMPLETED
        
        manager.add_dependency(task2, task1)
        # task3 has no dependencies
        
        ready = manager.get_ready_tasks([task1, task2, task3])
        
        assert len(ready) == 2
        assert task2 in ready
        assert task3 in ready

    def test_get_execution_order(self):
        """Test getting execution order."""
        manager = DependencyManager()
        
        task1 = Task(type=TaskType.CODE_GENERATION, description="Task 1")
        task2 = Task(type=TaskType.CODE_ANALYSIS, description="Task 2")
        task3 = Task(type=TaskType.CODE_REVIEW, description="Task 3")
        
        manager.add_dependency(task2, task1)
        manager.add_dependency(task3, task2)
        
        batches = manager.get_execution_order([task1, task2, task3])
        
        assert len(batches) == 3
        assert task1 in batches[0]
        assert task2 in batches[1]
        assert task3 in batches[2]

    def test_get_execution_order_parallel(self):
        """Test execution order with parallel tasks."""
        manager = DependencyManager()
        
        task1 = Task(type=TaskType.CODE_GENERATION, description="Task 1")
        task2 = Task(type=TaskType.CODE_ANALYSIS, description="Task 2")
        task3 = Task(type=TaskType.CODE_REVIEW, description="Task 3")
        
        manager.add_dependency(task3, task1)
        manager.add_dependency(task3, task2)
        
        batches = manager.get_execution_order([task1, task2, task3])
        
        assert len(batches) == 2
        assert len(batches[0]) == 2  # task1 and task2 can run in parallel
        assert task3 in batches[1]

    def test_detect_circular_dependencies(self):
        """Test detecting circular dependencies."""
        manager = DependencyManager()
        
        task1 = Task(type=TaskType.CODE_GENERATION, description="Task 1")
        task2 = Task(type=TaskType.CODE_ANALYSIS, description="Task 2")
        task3 = Task(type=TaskType.CODE_REVIEW, description="Task 3")
        
        manager.add_dependency(task2, task1)
        manager.add_dependency(task3, task2)
        manager.add_dependency(task1, task3)  # Creates cycle
        
        cycle = manager.detect_circular_dependencies([task1, task2, task3])
        
        assert cycle is not None
        assert len(cycle) > 0

    def test_detect_no_circular_dependencies(self):
        """Test no circular dependencies detected."""
        manager = DependencyManager()
        
        task1 = Task(type=TaskType.CODE_GENERATION, description="Task 1")
        task2 = Task(type=TaskType.CODE_ANALYSIS, description="Task 2")
        
        manager.add_dependency(task2, task1)
        
        cycle = manager.detect_circular_dependencies([task1, task2])
        
        assert cycle is None

    def test_get_critical_path(self):
        """Test finding critical path."""
        manager = DependencyManager()
        
        task1 = Task(type=TaskType.CODE_GENERATION, description="Task 1")
        task2 = Task(type=TaskType.CODE_ANALYSIS, description="Task 2")
        task3 = Task(type=TaskType.CODE_REVIEW, description="Task 3")
        
        manager.add_dependency(task2, task1)
        manager.add_dependency(task3, task2)
        
        critical_path = manager.get_critical_path([task1, task2, task3])
        
        assert len(critical_path) == 3
        assert critical_path[0] == task1
        assert critical_path[1] == task2
        assert critical_path[2] == task3

    def test_get_statistics(self):
        """Test getting dependency statistics."""
        manager = DependencyManager()
        
        task1 = Task(type=TaskType.CODE_GENERATION, description="Task 1")
        task2 = Task(type=TaskType.CODE_ANALYSIS, description="Task 2")
        task3 = Task(type=TaskType.CODE_REVIEW, description="Task 3")
        
        manager.add_dependency(task2, task1)
        manager.add_dependency(task3, task1)
        manager.add_dependency(task3, task2)
        
        stats = manager.get_statistics()
        
        assert stats["total_tasks"] == 3
        assert stats["total_dependencies"] == 3
        assert "dependency_types" in stats

    def test_clear(self):
        """Test clearing all dependencies."""
        manager = DependencyManager()
        
        task1 = Task(type=TaskType.CODE_GENERATION, description="Task 1")
        task2 = Task(type=TaskType.CODE_ANALYSIS, description="Task 2")
        
        manager.add_dependency(task2, task1)
        
        assert len(manager.dependencies) > 0
        
        manager.clear()
        
        assert len(manager.dependencies) == 0
        assert len(manager.graph.nodes) == 0
