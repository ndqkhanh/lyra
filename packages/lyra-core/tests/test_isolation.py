"""Tests for child-task context isolation.

This test suite verifies the context isolation system for multi-agent coordination.
It covers:
- Context scope creation and inheritance
- Isolation policies (discovery, analysis, synthesis)
- Context boundaries (spawn, merge)
- Merge strategies (append, replace, selective, none)
- Integration with TaskGraph
- Isolation statistics

Expected: 30+ tests covering all functionality.
"""
from __future__ import annotations

from lyra_core.context.isolation import (
    ContextBoundary,
    ContextMerger,
    ContextScope,
    IsolationPolicy,
    IsolationStats,
    MergeResult,
    MergeStrategy,
)
from lyra_core.context.layered_context import (
    ContextLayer,
    LayeredContextManager,
)
from lyra_research.coordination import Task

# ============================================================================
# Merge Strategy Tests
# ============================================================================


def test_merge_strategy_enum() -> None:
    """MergeStrategy enum has all expected values."""
    assert MergeStrategy.APPEND.value == "append"
    assert MergeStrategy.REPLACE.value == "replace"
    assert MergeStrategy.SELECTIVE.value == "selective"
    assert MergeStrategy.NONE.value == "none"


def test_merge_result_initialization() -> None:
    """MergeResult initializes with correct defaults."""
    result = MergeResult()
    assert result.entries_merged == 0
    assert result.tokens_merged == 0
    assert result.layers_affected == []
    assert result.skipped_entries == 0


def test_context_merger_none_strategy() -> None:
    """ContextMerger with NONE strategy merges nothing."""
    parent = LayeredContextManager(max_tokens=100_000)
    child = LayeredContextManager(max_tokens=50_000)

    # Add content to child
    child.add(ContextLayer.MEMORY, "child discovery", source="child_agent", priority=8)

    # Merge with NONE strategy
    merger = ContextMerger()
    result = merger.merge(
        parent=parent,
        child=child,
        layers=[ContextLayer.MEMORY],
        strategy=MergeStrategy.NONE,
    )

    assert result.entries_merged == 0
    assert result.tokens_merged == 0
    assert len(parent.get_layer(ContextLayer.MEMORY)) == 0


def test_context_merger_append_strategy() -> None:
    """ContextMerger with APPEND strategy adds all entries."""
    parent = LayeredContextManager(max_tokens=100_000)
    child = LayeredContextManager(max_tokens=50_000)

    # Add content to parent
    parent.add(ContextLayer.MEMORY, "parent memory", source="parent", priority=5)

    # Add content to child
    child.add(ContextLayer.MEMORY, "child discovery", source="child_agent", priority=8)

    # Merge with APPEND strategy
    merger = ContextMerger()
    result = merger.merge(
        parent=parent,
        child=child,
        layers=[ContextLayer.MEMORY],
        strategy=MergeStrategy.APPEND,
    )

    assert result.entries_merged == 1
    assert result.tokens_merged > 0
    assert ContextLayer.MEMORY in result.layers_affected
    assert len(parent.get_layer(ContextLayer.MEMORY)) == 2  # parent + child


def test_context_merger_replace_strategy() -> None:
    """ContextMerger with REPLACE strategy replaces parent entries."""
    parent = LayeredContextManager(max_tokens=100_000)
    child = LayeredContextManager(max_tokens=50_000)

    # Add content to parent
    parent.add(ContextLayer.MEMORY, "parent memory", source="parent", priority=5)

    # Add content to child
    child.add(ContextLayer.MEMORY, "child discovery", source="child_agent", priority=8)

    # Merge with REPLACE strategy
    merger = ContextMerger()
    result = merger.merge(
        parent=parent,
        child=child,
        layers=[ContextLayer.MEMORY],
        strategy=MergeStrategy.REPLACE,
    )

    assert result.entries_merged == 1
    assert len(parent.get_layer(ContextLayer.MEMORY)) == 1  # Only child entry
    assert "child discovery" in parent.get_layer(ContextLayer.MEMORY)[0].content


def test_context_merger_selective_strategy() -> None:
    """ContextMerger with SELECTIVE strategy merges only high-priority entries."""
    parent = LayeredContextManager(max_tokens=100_000)
    child = LayeredContextManager(max_tokens=50_000)

    # Add low-priority entry to child
    child.add(ContextLayer.MEMORY, "low priority", source="child", priority=5)

    # Add high-priority entry to child
    child.add(ContextLayer.MEMORY, "high priority", source="child", priority=8)

    # Merge with SELECTIVE strategy
    merger = ContextMerger()
    result = merger.merge(
        parent=parent,
        child=child,
        layers=[ContextLayer.MEMORY],
        strategy=MergeStrategy.SELECTIVE,
    )

    assert result.entries_merged == 1  # Only high-priority entry
    assert result.skipped_entries == 1  # Low-priority entry skipped
    assert "high priority" in parent.get_layer(ContextLayer.MEMORY)[0].content


def test_context_merger_multiple_layers() -> None:
    """ContextMerger can merge multiple layers at once."""
    parent = LayeredContextManager(max_tokens=100_000)
    child = LayeredContextManager(max_tokens=50_000)

    # Add content to multiple layers in child
    child.add(ContextLayer.MEMORY, "memory content", source="child", priority=8)
    child.add(ContextLayer.DYNAMIC, "dynamic content", source="child", priority=9)

    # Merge both layers
    merger = ContextMerger()
    result = merger.merge(
        parent=parent,
        child=child,
        layers=[ContextLayer.MEMORY, ContextLayer.DYNAMIC],
        strategy=MergeStrategy.APPEND,
    )

    assert result.entries_merged == 2
    assert len(result.layers_affected) == 2
    assert ContextLayer.MEMORY in result.layers_affected
    assert ContextLayer.DYNAMIC in result.layers_affected


# ============================================================================
# Isolation Policy Tests
# ============================================================================


def test_isolation_policy_default() -> None:
    """Default isolation policy has expected values."""
    policy = IsolationPolicy.default()

    assert ContextLayer.SYSTEM in policy.inherit_layers
    assert ContextLayer.USER in policy.inherit_layers
    assert ContextLayer.PROJECT in policy.inherit_layers
    assert ContextLayer.MEMORY in policy.merge_layers
    assert ContextLayer.DYNAMIC in policy.merge_layers
    assert policy.merge_strategy == MergeStrategy.SELECTIVE
    assert policy.max_tokens == 50_000


def test_isolation_policy_discovery_agent() -> None:
    """Discovery agent policy inherits minimal context."""
    policy = IsolationPolicy.for_discovery_agent()

    assert ContextLayer.SYSTEM in policy.inherit_layers
    assert ContextLayer.PROJECT in policy.inherit_layers
    assert ContextLayer.USER not in policy.inherit_layers  # Minimal context
    assert ContextLayer.MEMORY in policy.merge_layers
    assert policy.merge_strategy == MergeStrategy.SELECTIVE
    assert policy.max_tokens == 30_000  # Smaller budget


def test_isolation_policy_analysis_agent() -> None:
    """Analysis agent policy inherits more context."""
    policy = IsolationPolicy.for_analysis_agent()

    assert ContextLayer.SYSTEM in policy.inherit_layers
    assert ContextLayer.USER in policy.inherit_layers
    assert ContextLayer.PROJECT in policy.inherit_layers
    assert ContextLayer.TASK in policy.inherit_layers
    assert ContextLayer.MEMORY in policy.merge_layers
    assert policy.merge_strategy == MergeStrategy.SELECTIVE
    assert policy.max_tokens == 50_000


def test_isolation_policy_synthesis_agent() -> None:
    """Synthesis agent policy inherits full context."""
    policy = IsolationPolicy.for_synthesis_agent()

    assert ContextLayer.SYSTEM in policy.inherit_layers
    assert ContextLayer.USER in policy.inherit_layers
    assert ContextLayer.PROJECT in policy.inherit_layers
    assert ContextLayer.SESSION in policy.inherit_layers
    assert ContextLayer.TASK in policy.inherit_layers
    assert ContextLayer.MEMORY in policy.inherit_layers
    assert ContextLayer.DYNAMIC in policy.merge_layers
    assert policy.merge_strategy == MergeStrategy.APPEND
    assert policy.max_tokens == 80_000  # Larger budget


# ============================================================================
# Context Scope Tests
# ============================================================================


def test_context_scope_initialization() -> None:
    """ContextScope initializes correctly."""
    parent = LayeredContextManager(max_tokens=100_000)
    scope = ContextScope(
        parent_context=parent,
        inherit_layers=[ContextLayer.SYSTEM, ContextLayer.PROJECT],
        max_tokens=50_000,
    )

    assert scope.parent_context is parent
    assert scope.inherit_layers == [ContextLayer.SYSTEM, ContextLayer.PROJECT]
    assert scope.max_tokens == 50_000
    assert scope.child_context.max_tokens == 50_000


def test_context_scope_create_child_empty_parent() -> None:
    """ContextScope creates empty child when parent is empty."""
    parent = LayeredContextManager(max_tokens=100_000)
    scope = ContextScope(
        parent_context=parent,
        inherit_layers=[ContextLayer.SYSTEM],
        max_tokens=50_000,
    )

    child = scope.create_child_context()

    assert child.current_tokens == 0
    assert len(child.get_layer(ContextLayer.SYSTEM)) == 0


def test_context_scope_create_child_inherits_layers() -> None:
    """ContextScope creates child that inherits specified layers."""
    parent = LayeredContextManager(max_tokens=100_000)

    # Add content to parent
    parent.add(ContextLayer.SYSTEM, "system prompt", source="system", priority=10)
    parent.add(ContextLayer.PROJECT, "project context", source="CLAUDE.md", priority=8)
    parent.add(ContextLayer.SESSION, "session state", source="session", priority=5)

    # Create scope that inherits SYSTEM and PROJECT only
    scope = ContextScope(
        parent_context=parent,
        inherit_layers=[ContextLayer.SYSTEM, ContextLayer.PROJECT],
        max_tokens=50_000,
    )

    child = scope.create_child_context()

    # Child should have SYSTEM and PROJECT
    assert len(child.get_layer(ContextLayer.SYSTEM)) == 1
    assert len(child.get_layer(ContextLayer.PROJECT)) == 1
    assert "system prompt" in child.get_layer(ContextLayer.SYSTEM)[0].content
    assert "project context" in child.get_layer(ContextLayer.PROJECT)[0].content

    # Child should NOT have SESSION
    assert len(child.get_layer(ContextLayer.SESSION)) == 0


def test_context_scope_child_has_provenance() -> None:
    """Child context entries have provenance from parent."""
    parent = LayeredContextManager(max_tokens=100_000)
    parent.add(ContextLayer.SYSTEM, "system prompt", source="system", priority=10)

    scope = ContextScope(
        parent_context=parent,
        inherit_layers=[ContextLayer.SYSTEM],
        max_tokens=50_000,
    )

    child = scope.create_child_context()
    entry = child.get_layer(ContextLayer.SYSTEM)[0]

    assert entry.source == "parent:system"
    assert entry.metadata.get("inherited") is True


def test_context_scope_skips_expired_entries() -> None:
    """ContextScope skips expired entries when creating child."""
    parent = LayeredContextManager(max_tokens=100_000)

    # Add expired entry
    parent.add(
        ContextLayer.TOOL,
        "expired tool output",
        source="tool:read",
        priority=5,
        ttl_seconds=-1,  # Already expired
    )

    scope = ContextScope(
        parent_context=parent,
        inherit_layers=[ContextLayer.TOOL],
        max_tokens=50_000,
    )

    child = scope.create_child_context()

    # Child should not have expired entry
    assert len(child.get_layer(ContextLayer.TOOL)) == 0


def test_context_scope_merge_child_results() -> None:
    """ContextScope can merge child results back to parent."""
    parent = LayeredContextManager(max_tokens=100_000)
    scope = ContextScope(
        parent_context=parent,
        inherit_layers=[ContextLayer.SYSTEM],
        max_tokens=50_000,
    )

    child = scope.create_child_context()

    # Child makes a discovery
    child.add(ContextLayer.MEMORY, "important discovery", source="child_agent", priority=9)

    # Merge back to parent
    result = scope.merge_child_results(
        child_context=child,
        merge_layers=[ContextLayer.MEMORY],
        strategy=MergeStrategy.APPEND,
    )

    assert result.entries_merged == 1
    assert len(parent.get_layer(ContextLayer.MEMORY)) == 1
    assert "important discovery" in parent.get_layer(ContextLayer.MEMORY)[0].content


# ============================================================================
# Context Boundary Tests
# ============================================================================


def test_context_boundary_initialization() -> None:
    """ContextBoundary initializes correctly."""
    parent = LayeredContextManager(max_tokens=100_000)
    policy = IsolationPolicy.default()
    boundary = ContextBoundary(parent=parent, policy=policy)

    assert boundary.parent is parent
    assert boundary.policy is policy
    assert len(boundary.children) == 0
    assert len(boundary.scopes) == 0


def test_context_boundary_spawn_child() -> None:
    """ContextBoundary can spawn child context."""
    parent = LayeredContextManager(max_tokens=100_000)
    parent.add(ContextLayer.SYSTEM, "system prompt", source="system", priority=10)

    policy = IsolationPolicy.default()
    boundary = ContextBoundary(parent=parent, policy=policy)

    # Spawn child
    child = boundary.spawn_child(task_id="task-1")

    assert child is not None
    assert child.max_tokens == policy.max_tokens
    assert "task-1" in boundary.children
    assert "task-1" in boundary.scopes

    # Child should have inherited SYSTEM layer
    assert len(child.get_layer(ContextLayer.SYSTEM)) == 1


def test_context_boundary_spawn_multiple_children() -> None:
    """ContextBoundary can spawn multiple children."""
    parent = LayeredContextManager(max_tokens=100_000)
    policy = IsolationPolicy.default()
    boundary = ContextBoundary(parent=parent, policy=policy)

    # Spawn multiple children
    child1 = boundary.spawn_child(task_id="task-1")
    child2 = boundary.spawn_child(task_id="task-2")

    assert child1 is not child2
    assert len(boundary.children) == 2
    assert "task-1" in boundary.children
    assert "task-2" in boundary.children


def test_context_boundary_merge_child() -> None:
    """ContextBoundary can merge child results back to parent."""
    parent = LayeredContextManager(max_tokens=100_000)
    policy = IsolationPolicy.default()
    boundary = ContextBoundary(parent=parent, policy=policy)

    # Spawn child
    child = boundary.spawn_child(task_id="task-1")

    # Child makes a discovery
    child.add(ContextLayer.MEMORY, "important finding", source="child", priority=9)

    # Merge back to parent
    result = boundary.merge_child(child=child, task_id="task-1")

    assert result.entries_merged == 1
    assert len(parent.get_layer(ContextLayer.MEMORY)) == 1

    # Child should be cleaned up
    assert "task-1" not in boundary.children
    assert "task-1" not in boundary.scopes


def test_context_boundary_merge_without_spawn() -> None:
    """ContextBoundary can merge child even if not spawned through boundary."""
    parent = LayeredContextManager(max_tokens=100_000)
    policy = IsolationPolicy.default()
    boundary = ContextBoundary(parent=parent, policy=policy)

    # Create child manually (not through boundary)
    child = LayeredContextManager(max_tokens=50_000)
    child.add(ContextLayer.MEMORY, "external discovery", source="external", priority=8)

    # Merge should still work
    result = boundary.merge_child(child=child, task_id="external-task")

    assert result.entries_merged == 1
    assert len(parent.get_layer(ContextLayer.MEMORY)) == 1


def test_context_boundary_get_active_children() -> None:
    """ContextBoundary tracks active children."""
    parent = LayeredContextManager(max_tokens=100_000)
    policy = IsolationPolicy.default()
    boundary = ContextBoundary(parent=parent, policy=policy)

    # Initially no children
    assert boundary.get_active_children() == []

    # Spawn children
    boundary.spawn_child(task_id="task-1")
    boundary.spawn_child(task_id="task-2")

    active = boundary.get_active_children()
    assert len(active) == 2
    assert "task-1" in active
    assert "task-2" in active


# ============================================================================
# Isolation Statistics Tests
# ============================================================================


def test_isolation_stats_initialization() -> None:
    """IsolationStats initializes correctly."""
    stats = IsolationStats(
        parent_tokens=100_000,
        child_tokens=30_000,
        tokens_saved=70_000,
        layers_inherited=3,
        layers_isolated=5,
        entries_inherited=10,
        entries_isolated=50,
        reduction_percent=70.0,
    )

    assert stats.parent_tokens == 100_000
    assert stats.child_tokens == 30_000
    assert stats.tokens_saved == 70_000
    assert stats.reduction_percent == 70.0


def test_context_boundary_isolation_stats_no_children() -> None:
    """ContextBoundary returns stats when no children exist."""
    parent = LayeredContextManager(max_tokens=100_000)
    parent.add(ContextLayer.SYSTEM, "system prompt", source="system", priority=10)

    policy = IsolationPolicy.default()
    boundary = ContextBoundary(parent=parent, policy=policy)

    stats = boundary.get_isolation_stats()

    assert stats.parent_tokens > 0
    assert stats.child_tokens == 0
    assert stats.tokens_saved == stats.parent_tokens
    assert stats.reduction_percent == 100.0


def test_context_boundary_isolation_stats_with_child() -> None:
    """ContextBoundary returns stats for specific child."""
    parent = LayeredContextManager(max_tokens=100_000)

    # Add substantial content to parent
    parent.add(ContextLayer.SYSTEM, "system prompt" * 100, source="system", priority=10)
    parent.add(ContextLayer.SESSION, "session state" * 100, source="session", priority=5)

    policy = IsolationPolicy.for_discovery_agent()  # Inherits minimal context
    boundary = ContextBoundary(parent=parent, policy=policy)

    # Spawn child
    child = boundary.spawn_child(task_id="task-1")

    # Get stats for this child
    stats = boundary.get_isolation_stats(task_id="task-1")

    assert stats.parent_tokens > 0
    assert stats.child_tokens > 0
    assert stats.child_tokens < stats.parent_tokens  # Child has less context
    assert stats.tokens_saved > 0
    assert stats.reduction_percent > 0


def test_context_boundary_isolation_stats_aggregate() -> None:
    """ContextBoundary returns aggregate stats for all children."""
    parent = LayeredContextManager(max_tokens=100_000)
    parent.add(ContextLayer.SYSTEM, "system prompt" * 100, source="system", priority=10)

    policy = IsolationPolicy.for_discovery_agent()
    boundary = ContextBoundary(parent=parent, policy=policy)

    # Spawn multiple children
    boundary.spawn_child(task_id="task-1")
    boundary.spawn_child(task_id="task-2")

    # Get aggregate stats
    stats = boundary.get_isolation_stats()

    assert stats.parent_tokens > 0
    assert stats.child_tokens > 0
    assert stats.layers_inherited == len(policy.inherit_layers)
    assert stats.layers_isolated == len(ContextLayer) - len(policy.inherit_layers)


# ============================================================================
# Integration with Task Tests
# ============================================================================


def test_task_has_context_boundary_field() -> None:
    """Task has context_boundary field."""
    task = Task()
    assert hasattr(task, "context_boundary")
    assert task.context_boundary is None


def test_task_with_context_boundary() -> None:
    """Task can be created with context_boundary."""
    parent = LayeredContextManager(max_tokens=100_000)
    policy = IsolationPolicy.default()
    boundary = ContextBoundary(parent=parent, policy=policy)

    task = Task(context_boundary=boundary)

    assert task.context_boundary is boundary


def test_task_spawn_child_context() -> None:
    """Task can spawn child context through boundary."""
    parent = LayeredContextManager(max_tokens=100_000)
    parent.add(ContextLayer.SYSTEM, "system prompt", source="system", priority=10)

    policy = IsolationPolicy.default()
    boundary = ContextBoundary(parent=parent, policy=policy)

    task = Task(context_boundary=boundary)

    # Spawn child context for this task
    child = task.context_boundary.spawn_child(task_id=task.id)

    assert child is not None
    assert task.id in boundary.children


def test_task_merge_child_context() -> None:
    """Task can merge child context back through boundary."""
    parent = LayeredContextManager(max_tokens=100_000)
    policy = IsolationPolicy.default()
    boundary = ContextBoundary(parent=parent, policy=policy)

    task = Task(context_boundary=boundary)

    # Spawn and work in child context
    child = task.context_boundary.spawn_child(task_id=task.id)
    child.add(ContextLayer.MEMORY, "task result", source="task_agent", priority=9)

    # Merge back
    result = task.context_boundary.merge_child(child=child, task_id=task.id)

    assert result.entries_merged == 1
    assert len(parent.get_layer(ContextLayer.MEMORY)) == 1


# ============================================================================
# End-to-End Workflow Tests
# ============================================================================


def test_e2e_discovery_agent_workflow() -> None:
    """End-to-end: Discovery agent spawns, discovers, merges back."""
    # Setup parent context
    parent = LayeredContextManager(max_tokens=100_000)
    parent.add(ContextLayer.SYSTEM, "You are a discovery agent", source="system", priority=10)
    parent.add(ContextLayer.PROJECT, "Project: Lyra", source="CLAUDE.md", priority=8)
    parent.add(ContextLayer.SESSION, "Session state", source="session", priority=5)

    # Create boundary with discovery policy
    policy = IsolationPolicy.for_discovery_agent()
    boundary = ContextBoundary(parent=parent, policy=policy)

    # Spawn child for discovery task
    child = boundary.spawn_child(task_id="discovery-1")

    # Child should have minimal context (SYSTEM + PROJECT only)
    assert len(child.get_layer(ContextLayer.SYSTEM)) == 1
    assert len(child.get_layer(ContextLayer.PROJECT)) == 1
    assert len(child.get_layer(ContextLayer.SESSION)) == 0  # Not inherited

    # Child makes discoveries
    child.add(ContextLayer.MEMORY, "Found important pattern", source="discovery", priority=9)
    child.add(ContextLayer.DYNAMIC, "Temporary note", source="discovery", priority=4)

    # Merge back (only high-priority discoveries)
    result = boundary.merge_child(child=child, task_id="discovery-1")

    # Only high-priority entry should be merged
    assert result.entries_merged == 1  # Only priority=9 entry
    assert len(parent.get_layer(ContextLayer.MEMORY)) == 1
    assert "Found important pattern" in parent.get_layer(ContextLayer.MEMORY)[0].content


def test_e2e_parallel_agents_isolated() -> None:
    """End-to-end: Multiple parallel agents with isolated contexts."""
    # Setup parent context
    parent = LayeredContextManager(max_tokens=100_000)
    parent.add(ContextLayer.SYSTEM, "system", source="system", priority=10)

    policy = IsolationPolicy.default()
    boundary = ContextBoundary(parent=parent, policy=policy)

    # Spawn multiple parallel agents
    child1 = boundary.spawn_child(task_id="agent-1")
    child2 = boundary.spawn_child(task_id="agent-2")

    # Each agent works independently
    child1.add(ContextLayer.MEMORY, "agent-1 discovery", source="agent-1", priority=8)
    child2.add(ContextLayer.MEMORY, "agent-2 discovery", source="agent-2", priority=8)

    # Agents should not see each other's work
    assert len(child1.get_layer(ContextLayer.MEMORY)) == 1
    assert len(child2.get_layer(ContextLayer.MEMORY)) == 1
    assert "agent-2" not in child1.get_layer(ContextLayer.MEMORY)[0].content
    assert "agent-1" not in child2.get_layer(ContextLayer.MEMORY)[0].content

    # Merge both back to parent
    boundary.merge_child(child=child1, task_id="agent-1")
    boundary.merge_child(child=child2, task_id="agent-2")

    # Parent should have both discoveries
    assert len(parent.get_layer(ContextLayer.MEMORY)) == 2
