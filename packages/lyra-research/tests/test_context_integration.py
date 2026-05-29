"""Integration tests for layered context with full orchestrator.

Tests the integration of:
- LayeredContextManager with ResearchOrchestrator
- ContextBoundary with multi-agent coordination
- Context isolation for discovery/analysis/synthesis agents
- Budget enforcement across full pipeline
- Provenance tracking through full research flow
"""
from __future__ import annotations

import pytest
from lyra_core.context.isolation import (
    ContextBoundary,
    IsolationPolicy,
)
from lyra_core.context.layered_context import (
    ContextLayer,
    LayerBudget,
    LayeredContextManager,
)
from lyra_core.context.provenance import ContextAuditTrail
from lyra_research.discovery import ResearchSource, SourceType
from lyra_research.orchestrator import ResearchOrchestrator

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def context_manager():
    """Create context manager with audit trail."""
    manager = LayeredContextManager(max_tokens=100_000)
    manager.audit_trail = ContextAuditTrail()
    return manager


@pytest.fixture
def orchestrator(tmp_path):
    """Create orchestrator with mocked dependencies."""
    return ResearchOrchestrator(output_dir=tmp_path)


@pytest.fixture
def mock_sources():
    """Create mock research sources."""
    return [
        ResearchSource(
            id=f"paper_{i}",
            title=f"Paper {i}",
            url=f"https://arxiv.org/abs/{i}",
            abstract=f"Abstract for paper {i}",
            source_type=SourceType.PAPER,
            citations=100 - i * 10,
            stars=0,
            metadata={"year": 2024, "venue": "NeurIPS"},
        )
        for i in range(10)
    ]


# ============================================================================
# Test: Basic Integration
# ============================================================================


def test_orchestrator_with_layered_context(context_manager, orchestrator):
    """Test orchestrator can use layered context."""
    # Add context to orchestrator
    orchestrator.context_manager = context_manager

    # Add system context
    context_manager.add(
        ContextLayer.SYSTEM,
        "You are a research assistant",
        source="system_prompt",
        priority=10,
    )

    # Add task context
    context_manager.add(
        ContextLayer.TASK,
        "Research topic: Deep Learning",
        source="user_query",
        priority=8,
    )

    # Verify context is assembled correctly
    context = context_manager.assemble()
    assert "SYSTEM LAYER" in context
    assert "TASK LAYER" in context
    assert "research assistant" in context
    assert "Deep Learning" in context


def test_orchestrator_budget_enforcement(context_manager):
    """Test budget enforcement during research."""
    # Fill up TASK layer beyond budget
    for i in range(100):
        context_manager.add(
            ContextLayer.TASK,
            f"Task entry {i}: " + "x" * 1000,
            source=f"task_{i}",
            priority=5,
        )

    # Assemble should trigger budget enforcement
    context = context_manager.assemble()

    # Verify budget is enforced
    usage = context_manager.get_budget_usage()
    assert usage[ContextLayer.TASK] <= LayerBudget.TASK
    assert context_manager.current_tokens <= context_manager.max_tokens


def test_orchestrator_provenance_tracking(context_manager):
    """Test provenance tracking through research pipeline."""
    # Add entries from different sources
    context_manager.add(
        ContextLayer.TOOL,
        "Paper: Deep Learning Advances",
        source="tool:arxiv_search",
        priority=7,
    )

    context_manager.add(
        ContextLayer.MEMORY,
        "Previous finding: Transformers are effective",
        source="memory:retrieval",
        priority=6,
    )

    # Query provenance
    results = context_manager.get_provenance("Deep Learning")
    assert len(results) == 1
    assert results[0].source == "tool:arxiv_search"
    assert results[0].layer == ContextLayer.TOOL


# ============================================================================
# Test: Discovery Agent Integration
# ============================================================================


def test_discovery_agent_isolation(context_manager):
    """Test discovery agents use isolated context."""
    # Setup parent context
    context_manager.add(ContextLayer.SYSTEM, "System prompt", "system", priority=10)
    context_manager.add(ContextLayer.USER, "User prefs", "user", priority=8)
    context_manager.add(ContextLayer.PROJECT, "Project context", "project", priority=8)
    context_manager.add(ContextLayer.SESSION, "Session state", "session", priority=6)
    context_manager.add(ContextLayer.TASK, "Current task", "task", priority=7)

    parent_tokens = context_manager.current_tokens

    # Create discovery boundary
    boundary = ContextBoundary(
        context_manager,
        IsolationPolicy.for_discovery_agent(),
    )

    # Spawn discovery child
    child = boundary.spawn_child("discovery_1")

    # Verify child has minimal context
    child_tokens = child.current_tokens
    assert child_tokens < parent_tokens

    # Verify child only inherited SYSTEM and PROJECT
    assert len(child.get_layer(ContextLayer.SYSTEM)) > 0
    assert len(child.get_layer(ContextLayer.PROJECT)) > 0
    assert len(child.get_layer(ContextLayer.USER)) == 0  # Not inherited
    assert len(child.get_layer(ContextLayer.SESSION)) == 0  # Not inherited
    assert len(child.get_layer(ContextLayer.TASK)) == 0  # Not inherited

    # Get isolation stats
    stats = boundary.get_isolation_stats("discovery_1")
    assert stats.tokens_saved > 0
    assert stats.reduction_percent > 40  # At least 40% reduction


def test_discovery_agent_merge_results(context_manager):
    """Test discovery results are merged back to parent."""
    # Setup parent
    context_manager.add(ContextLayer.SYSTEM, "System", "system", priority=10)
    context_manager.add(ContextLayer.PROJECT, "Project", "project", priority=8)

    # Create boundary and spawn child
    boundary = ContextBoundary(
        context_manager,
        IsolationPolicy.for_discovery_agent(),
    )
    child = boundary.spawn_child("discovery_1")

    # Child discovers sources
    child.add(
        ContextLayer.MEMORY,
        "Found paper: Attention Is All You Need",
        source="discovery:arxiv",
        priority=8,
    )
    child.add(
        ContextLayer.DYNAMIC,
        "Found repo: transformers",
        source="discovery:github",
        priority=7,
    )

    # Merge back to parent
    result = boundary.merge_child(child, "discovery_1")

    # Verify merge
    assert result.entries_merged == 2
    assert result.tokens_merged > 0
    assert ContextLayer.MEMORY in result.layers_affected
    assert ContextLayer.DYNAMIC in result.layers_affected

    # Verify parent has discoveries
    memory_entries = context_manager.get_layer(ContextLayer.MEMORY)
    assert len(memory_entries) == 1
    assert "Attention Is All You Need" in memory_entries[0].content


def test_multiple_discovery_agents_parallel(context_manager):
    """Test multiple discovery agents running in parallel."""
    # Setup parent
    context_manager.add(ContextLayer.SYSTEM, "System", "system", priority=10)
    context_manager.add(ContextLayer.PROJECT, "Project", "project", priority=8)

    # Create boundary
    boundary = ContextBoundary(
        context_manager,
        IsolationPolicy.for_discovery_agent(),
    )

    # Spawn 6 discovery agents (like real orchestrator)
    children = []
    for i in range(6):
        child = boundary.spawn_child(f"discovery_{i}")
        children.append((f"discovery_{i}", child))

    # Each child discovers sources
    for task_id, child in children:
        child.add(
            ContextLayer.MEMORY,
            f"Discovery from {task_id}",
            source=f"discovery:{task_id}",
            priority=7,
        )

    # Merge all children back
    total_merged = 0
    for task_id, child in children:
        result = boundary.merge_child(child, task_id)
        total_merged += result.entries_merged

    # Verify all discoveries merged
    assert total_merged == 6
    memory_entries = context_manager.get_layer(ContextLayer.MEMORY)
    assert len(memory_entries) == 6


# ============================================================================
# Test: Analysis Agent Integration
# ============================================================================


def test_analysis_agent_isolation(context_manager):
    """Test analysis agents use more context than discovery."""
    # Setup parent with full context
    context_manager.add(ContextLayer.SYSTEM, "System", "system", priority=10)
    context_manager.add(ContextLayer.USER, "User", "user", priority=8)
    context_manager.add(ContextLayer.PROJECT, "Project", "project", priority=8)
    context_manager.add(ContextLayer.SESSION, "Session", "session", priority=6)
    context_manager.add(ContextLayer.TASK, "Task", "task", priority=7)

    parent_tokens = context_manager.current_tokens

    # Create analysis boundary
    boundary = ContextBoundary(
        context_manager,
        IsolationPolicy.for_analysis_agent(),
    )

    # Spawn analysis child
    child = boundary.spawn_child("analysis_1")
    child_tokens = child.current_tokens

    # Analysis agents inherit more than discovery
    # They get SYSTEM, USER, PROJECT, TASK
    assert len(child.get_layer(ContextLayer.SYSTEM)) > 0
    assert len(child.get_layer(ContextLayer.USER)) > 0
    assert len(child.get_layer(ContextLayer.PROJECT)) > 0
    assert len(child.get_layer(ContextLayer.TASK)) > 0
    assert len(child.get_layer(ContextLayer.SESSION)) == 0  # Not inherited

    # Still saves tokens compared to parent
    stats = boundary.get_isolation_stats("analysis_1")
    assert stats.tokens_saved > 0
    assert stats.reduction_percent >= 20  # At least 20% reduction (inclusive)


def test_analysis_agent_merge_results(context_manager):
    """Test analysis results are merged back."""
    # Setup parent
    context_manager.add(ContextLayer.SYSTEM, "System", "system", priority=10)
    context_manager.add(ContextLayer.TASK, "Analyze papers", "task", priority=8)

    # Create boundary and spawn child
    boundary = ContextBoundary(
        context_manager,
        IsolationPolicy.for_analysis_agent(),
    )
    child = boundary.spawn_child("analysis_1")

    # Child analyzes paper
    child.add(
        ContextLayer.MEMORY,
        "Analysis: Paper introduces novel architecture",
        source="analysis:paper_1",
        priority=8,
    )

    # Merge back
    result = boundary.merge_child(child, "analysis_1")

    # Verify merge
    assert result.entries_merged == 1
    memory_entries = context_manager.get_layer(ContextLayer.MEMORY)
    assert len(memory_entries) == 1
    assert "novel architecture" in memory_entries[0].content


# ============================================================================
# Test: Synthesis Agent Integration
# ============================================================================


def test_synthesis_agent_full_context(context_manager):
    """Test synthesis agents get full context."""
    # Setup parent with full context
    for layer in ContextLayer:
        context_manager.add(
            layer,
            f"Content for {layer.value}",
            source=f"{layer.value}_source",
            priority=7,
        )

    parent_tokens = context_manager.current_tokens

    # Create synthesis boundary
    boundary = ContextBoundary(
        context_manager,
        IsolationPolicy.for_synthesis_agent(),
    )

    # Spawn synthesis child
    child = boundary.spawn_child("synthesis_1")
    child_tokens = child.current_tokens

    # Synthesis agents inherit most layers
    policy = IsolationPolicy.for_synthesis_agent()
    for layer in policy.inherit_layers:
        assert len(child.get_layer(layer)) > 0

    # Still some reduction (TOOL and DYNAMIC not inherited)
    stats = boundary.get_isolation_stats("synthesis_1")
    assert stats.reduction_percent < 50  # Less than 50% reduction (needs most context)


def test_synthesis_agent_merge_report(context_manager):
    """Test synthesis report is merged back."""
    # Setup parent
    context_manager.add(ContextLayer.SYSTEM, "System", "system", priority=10)

    # Create boundary and spawn child
    boundary = ContextBoundary(
        context_manager,
        IsolationPolicy.for_synthesis_agent(),
    )
    child = boundary.spawn_child("synthesis_1")

    # Child generates report
    child.add(
        ContextLayer.DYNAMIC,
        "Final Report: Deep Learning advances in 2024...",
        source="synthesis:report",
        priority=9,
    )

    # Merge back with APPEND strategy
    result = boundary.merge_child(child, "synthesis_1")

    # Verify merge
    assert result.entries_merged == 1
    dynamic_entries = context_manager.get_layer(ContextLayer.DYNAMIC)
    assert len(dynamic_entries) == 1
    assert "Final Report" in dynamic_entries[0].content


# ============================================================================
# Test: Full Pipeline Integration
# ============================================================================


def test_full_pipeline_context_flow(context_manager):
    """Test context flows through full discovery -> analysis -> synthesis pipeline."""
    # Phase 1: Setup
    context_manager.add(
        ContextLayer.SYSTEM,
        "You are a research assistant",
        source="system",
        priority=10,
    )
    context_manager.add(
        ContextLayer.TASK,
        "Research: Transformer architectures",
        source="user_query",
        priority=9,
    )

    initial_tokens = context_manager.current_tokens

    # Phase 2: Discovery (6 parallel agents)
    discovery_boundary = ContextBoundary(
        context_manager,
        IsolationPolicy.for_discovery_agent(),
    )

    for i in range(6):
        child = discovery_boundary.spawn_child(f"discovery_{i}")
        child.add(
            ContextLayer.MEMORY,
            f"Found source {i}",
            source=f"discovery_{i}",
            priority=7,
        )
        discovery_boundary.merge_child(child, f"discovery_{i}")

    after_discovery_tokens = context_manager.current_tokens
    assert after_discovery_tokens > initial_tokens  # Added discoveries

    # Phase 3: Analysis (parallel agents)
    analysis_boundary = ContextBoundary(
        context_manager,
        IsolationPolicy.for_analysis_agent(),
    )

    for i in range(3):
        child = analysis_boundary.spawn_child(f"analysis_{i}")
        child.add(
            ContextLayer.MEMORY,
            f"Analysis result {i}",
            source=f"analysis_{i}",
            priority=8,
        )
        analysis_boundary.merge_child(child, f"analysis_{i}")

    after_analysis_tokens = context_manager.current_tokens
    assert after_analysis_tokens > after_discovery_tokens  # Added analyses

    # Phase 4: Synthesis
    synthesis_boundary = ContextBoundary(
        context_manager,
        IsolationPolicy.for_synthesis_agent(),
    )

    child = synthesis_boundary.spawn_child("synthesis_1")
    child.add(
        ContextLayer.DYNAMIC,
        "Final report synthesizing all findings",
        source="synthesis",
        priority=9,
    )
    synthesis_boundary.merge_child(child, "synthesis_1")

    final_tokens = context_manager.current_tokens
    assert final_tokens > after_analysis_tokens  # Added report

    # Verify all phases contributed
    memory_entries = context_manager.get_layer(ContextLayer.MEMORY)
    assert len(memory_entries) == 9  # 6 discoveries + 3 analyses

    dynamic_entries = context_manager.get_layer(ContextLayer.DYNAMIC)
    assert len(dynamic_entries) == 1  # 1 report


def test_context_budget_across_pipeline(context_manager):
    """Test budget enforcement across full pipeline."""
    # Setup with large entries
    context_manager.add(
        ContextLayer.SYSTEM,
        "System prompt " * 1000,
        source="system",
        priority=10,
    )

    # Add many discoveries
    discovery_boundary = ContextBoundary(
        context_manager,
        IsolationPolicy.for_discovery_agent(),
    )

    for i in range(50):
        child = discovery_boundary.spawn_child(f"discovery_{i}")
        child.add(
            ContextLayer.MEMORY,
            f"Discovery {i}: " + "x" * 500,
            source=f"discovery_{i}",
            priority=6,
        )
        discovery_boundary.merge_child(child, f"discovery_{i}")

    # Assemble should enforce budget
    context = context_manager.assemble()

    # Verify budget is enforced
    assert context_manager.current_tokens <= context_manager.max_tokens

    # Verify high-priority content is kept
    system_entries = context_manager.get_layer(ContextLayer.SYSTEM)
    assert len(system_entries) > 0  # High priority, should be kept


def test_audit_trail_through_pipeline(context_manager):
    """Test audit trail tracks all operations through pipeline."""
    audit = context_manager.audit_trail

    # Add initial context
    context_manager.add(ContextLayer.SYSTEM, "System", "system", priority=10)

    # Discovery phase
    boundary = ContextBoundary(context_manager, IsolationPolicy.for_discovery_agent())
    child = boundary.spawn_child("discovery_1")
    child.add(ContextLayer.MEMORY, "Discovery", "discovery", priority=7)
    boundary.merge_child(child, "discovery_1")

    # Check audit trail has events
    assert audit is not None

    # Verify we can get timeline (which internally uses events)
    inspector = context_manager.get_inspector()
    timeline = inspector.get_timeline()
    assert len(timeline) > 0  # Should have entries from adds


# ============================================================================
# Test: Context Statistics
# ============================================================================


def test_context_statistics_collection(context_manager):
    """Test statistics are collected correctly."""
    # Add content to multiple layers
    context_manager.add(ContextLayer.SYSTEM, "System " * 100, "system", priority=10)
    context_manager.add(ContextLayer.TASK, "Task " * 50, "task", priority=8)
    context_manager.add(ContextLayer.MEMORY, "Memory " * 75, "memory", priority=7)

    # Get stats
    stats = context_manager.get_stats()

    # Verify stats structure
    assert "total_tokens" in stats
    assert "max_tokens" in stats
    assert "utilization" in stats
    assert "entry_count" in stats
    assert "layer_usage" in stats
    assert "layer_counts" in stats

    # Verify values
    assert stats["total_tokens"] > 0
    assert stats["entry_count"] == 3
    assert stats["utilization"] < 1.0
    assert stats["layer_counts"]["system"] == 1
    assert stats["layer_counts"]["task"] == 1
    assert stats["layer_counts"]["memory"] == 1


def test_isolation_statistics_aggregation(context_manager):
    """Test isolation statistics are aggregated correctly."""
    # Setup parent
    for i in range(10):
        context_manager.add(
            ContextLayer.TASK,
            f"Task {i} " * 50,
            source=f"task_{i}",
            priority=7,
        )

    # Create boundary and spawn multiple children
    boundary = ContextBoundary(
        context_manager,
        IsolationPolicy.for_discovery_agent(),
    )

    for i in range(5):
        child = boundary.spawn_child(f"child_{i}")

    # Get aggregate stats
    stats = boundary.get_isolation_stats()

    # Verify aggregation
    assert stats.parent_tokens > 0
    assert stats.child_tokens < stats.parent_tokens
    assert stats.tokens_saved > 0
    assert stats.reduction_percent > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
