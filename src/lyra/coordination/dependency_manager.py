"""
Dependency Manager - Handle task dependencies and execution ordering.
"""

from dataclasses import dataclass, field
from enum import Enum

from lyra.core.task import Task, TaskStatus


class DependencyType(Enum):
    """Types of task dependencies."""
    REQUIRES = "requires"          # Task requires another to complete first
    BLOCKS = "blocks"              # Task blocks another from starting
    RELATED = "related"            # Tasks are related but independent
    SEQUENTIAL = "sequential"      # Tasks must run in sequence


@dataclass
class TaskDependency:
    """Represents a dependency between tasks."""
    task_id: str
    depends_on: str
    dependency_type: DependencyType
    required: bool = True


@dataclass
class DependencyGraph:
    """Dependency graph for tasks."""
    nodes: dict[str, Task] = field(default_factory=dict)
    edges: dict[str, list[str]] = field(default_factory=dict)
    reverse_edges: dict[str, list[str]] = field(default_factory=dict)


class DependencyManager:
    """
    Manage task dependencies and execution ordering.

    Responsibilities:
    - Track task dependencies
    - Detect circular dependencies
    - Determine execution order
    - Identify ready tasks
    """

    def __init__(self):
        """Initialize dependency manager."""
        self.dependencies: dict[str, list[TaskDependency]] = {}
        self.graph = DependencyGraph()

    def add_dependency(
        self,
        task: Task,
        depends_on: Task,
        dependency_type: DependencyType = DependencyType.REQUIRES,
        required: bool = True,
    ):
        """
        Add a dependency between tasks.

        Args:
            task: Task that has the dependency
            depends_on: Task that must complete first
            dependency_type: Type of dependency
            required: Whether dependency is required
        """
        # Add to dependency list
        if task.task_id not in self.dependencies:
            self.dependencies[task.task_id] = []

        dep = TaskDependency(
            task_id=task.task_id,
            depends_on=depends_on.task_id,
            dependency_type=dependency_type,
            required=required,
        )
        self.dependencies[task.task_id].append(dep)

        # Update graph
        self.graph.nodes[task.task_id] = task
        self.graph.nodes[depends_on.task_id] = depends_on

        if task.task_id not in self.graph.edges:
            self.graph.edges[task.task_id] = []
        self.graph.edges[task.task_id].append(depends_on.task_id)

        if depends_on.task_id not in self.graph.reverse_edges:
            self.graph.reverse_edges[depends_on.task_id] = []
        self.graph.reverse_edges[depends_on.task_id].append(task.task_id)

    def get_dependencies(self, task: Task) -> list[TaskDependency]:
        """
        Get all dependencies for a task.

        Args:
            task: Task to get dependencies for

        Returns:
            List of dependencies
        """
        return self.dependencies.get(task.task_id, [])

    def get_dependents(self, task: Task) -> list[str]:
        """
        Get tasks that depend on this task.

        Args:
            task: Task to get dependents for

        Returns:
            List of dependent task IDs
        """
        return self.graph.reverse_edges.get(task.task_id, [])

    def is_ready(self, task: Task) -> bool:
        """
        Check if task is ready to execute (all dependencies met).

        Args:
            task: Task to check

        Returns:
            True if task is ready
        """
        deps = self.get_dependencies(task)

        if not deps:
            return True

        # Check all required dependencies
        for dep in deps:
            if not dep.required:
                continue

            dep_task = self.graph.nodes.get(dep.depends_on)
            if not dep_task:
                continue

            # Dependency must be completed
            if dep_task.status != TaskStatus.COMPLETED:
                return False

        return True

    def get_ready_tasks(self, tasks: list[Task]) -> list[Task]:
        """
        Get all tasks that are ready to execute.

        Args:
            tasks: List of tasks to check

        Returns:
            List of ready tasks
        """
        ready = []

        for task in tasks:
            if task.status == TaskStatus.PENDING and self.is_ready(task):
                ready.append(task)

        return ready

    def get_execution_order(self, tasks: list[Task]) -> list[list[Task]]:
        """
        Determine execution order for tasks (topological sort).

        Args:
            tasks: Tasks to order

        Returns:
            List of task batches (tasks in same batch can run in parallel)
        """
        # Build task map
        task_map = {t.task_id: t for t in tasks}

        # Calculate in-degree for each task
        in_degree = {t.task_id: 0 for t in tasks}
        for task in tasks:
            deps = self.get_dependencies(task)
            in_degree[task.task_id] = len([d for d in deps if d.required])

        # Find tasks with no dependencies
        batches = []
        remaining = set(task_map.keys())

        while remaining:
            # Find tasks with no remaining dependencies
            ready = [
                task_id for task_id in remaining
                if in_degree[task_id] == 0
            ]

            if not ready:
                # Circular dependency detected
                break

            # Add batch
            batch = [task_map[task_id] for task_id in ready]
            batches.append(batch)

            # Remove from remaining
            for task_id in ready:
                remaining.remove(task_id)

                # Update in-degrees for dependents
                dependents = self.get_dependents(task_map[task_id])
                for dep_id in dependents:
                    if dep_id in in_degree:
                        in_degree[dep_id] -= 1

        return batches

    def detect_circular_dependencies(self, tasks: list[Task]) -> list[str] | None:
        """
        Detect circular dependencies in task graph.

        Args:
            tasks: Tasks to check

        Returns:
            List of task IDs in cycle, or None if no cycle
        """
        visited = set()
        rec_stack = set()

        def has_cycle(task_id: str, path: list[str]) -> list[str] | None:
            visited.add(task_id)
            rec_stack.add(task_id)
            path.append(task_id)

            # Check all dependencies
            deps = self.dependencies.get(task_id, [])
            for dep in deps:
                if dep.depends_on not in visited:
                    cycle = has_cycle(dep.depends_on, path.copy())
                    if cycle:
                        return cycle
                elif dep.depends_on in rec_stack:
                    # Found cycle
                    cycle_start = path.index(dep.depends_on)
                    return path[cycle_start:] + [dep.depends_on]

            rec_stack.remove(task_id)
            return None

        # Check each task
        for task in tasks:
            if task.task_id not in visited:
                cycle = has_cycle(task.task_id, [])
                if cycle:
                    return cycle

        return None

    def get_critical_path(self, tasks: list[Task]) -> list[Task]:
        """
        Find critical path (longest path through dependency graph).

        Args:
            tasks: Tasks to analyze

        Returns:
            List of tasks in critical path
        """
        # Build task map
        task_map = {t.task_id: t for t in tasks}

        # Calculate longest path to each task
        longest_path = {t.task_id: 0 for t in tasks}
        predecessors = {t.task_id: None for t in tasks}

        # Get execution order
        batches = self.get_execution_order(tasks)

        for batch in batches:
            for task in batch:
                deps = self.get_dependencies(task)

                if deps:
                    # Find longest path through dependencies
                    max_length = 0
                    max_pred = None

                    for dep in deps:
                        dep_length = longest_path.get(dep.depends_on, 0)
                        if dep_length + 1 > max_length:
                            max_length = dep_length + 1
                            max_pred = dep.depends_on

                    longest_path[task.task_id] = max_length
                    predecessors[task.task_id] = max_pred

        # Find task with longest path
        if not longest_path:
            return []

        end_task_id = max(longest_path.items(), key=lambda x: x[1])[0]

        # Reconstruct path
        path = []
        current = end_task_id

        while current:
            path.append(task_map[current])
            current = predecessors[current]

        path.reverse()
        return path

    def get_statistics(self) -> dict:
        """
        Get dependency statistics.

        Returns:
            Statistics dictionary
        """
        total_tasks = len(self.graph.nodes)
        total_deps = sum(len(deps) for deps in self.dependencies.values())

        # Count dependency types
        dep_types = {}
        for deps in self.dependencies.values():
            for dep in deps:
                dep_type = dep.dependency_type.value
                dep_types[dep_type] = dep_types.get(dep_type, 0) + 1

        # Find tasks with most dependencies
        max_deps = 0
        max_deps_task = None
        for task_id, deps in self.dependencies.items():
            if len(deps) > max_deps:
                max_deps = len(deps)
                max_deps_task = task_id

        return {
            "total_tasks": total_tasks,
            "total_dependencies": total_deps,
            "dependency_types": dep_types,
            "max_dependencies": max_deps,
            "most_dependent_task": max_deps_task,
        }

    def clear(self):
        """Clear all dependencies."""
        self.dependencies.clear()
        self.graph = DependencyGraph()
