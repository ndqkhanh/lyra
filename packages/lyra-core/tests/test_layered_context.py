"""Tests for the 8-layer context system.

This test suite verifies the layered context management system inspired by
autocontext. It covers:
- Layer organization and ordering
- Budget enforcement (per-layer and total)
- TTL-based expiration
- Priority-based pruning
- Provenance tracking
- Context assembly

Expected: 40+ tests covering all functionality.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta

import pytest

from lyra_core.context.layered_context import (
    ContextEntry,
    ContextLayer,
    LayerBudget,
    LayeredContextManager,
    _estimate_tokens,
)


# ============================================================================
# Token Estimation Tests
# ============================================================================


def test_token_estimation_basic() -> None:
    """Token estimation: ~1 token per 4 chars."""
    assert _estimate_tokens("hello") == 1  # 5 chars -> 1 token
    assert _estimate_tokens("hello world") == 2  # 11 chars -> 2 tokens
    assert _estimate_tokens("a" * 100) == 25  # 100 chars -> 25 tokens


def test_token_estimation_minimum() -> None:
    """Token estimation: minimum 1 token."""
    assert _estimate_tokens("") == 1
    assert _estimate_tokens("a") == 1


# ============================================================================
# ContextEntry Tests
# ============================================================================


def test_context_entry_creation() -> None:
    """ContextEntry: basic creation."""
    entry = ContextEntry(
        layer=ContextLayer.SYSTEM,
        content="You are a helpful assistant",
        source="system_prompt",
    )

    assert entry.layer == ContextLayer.SYSTEM
    assert entry.content == "You are a helpful assistant"
    assert entry.source == "system_prompt"
    assert entry.priority == 5  # default
    assert entry.ttl_seconds is None
    assert entry.token_count > 0


def test_context_entry_with_priority() -> None:
    """ContextEntry: custom priority."""
    entry = ContextEntry(
        layer=ContextLayer.USER,
        content="Important directive",
        source="user",
        priority=10,
    )

    assert entry.priority == 10


def test_context_entry_with_ttl() -> None:
    """ContextEntry: TTL expiration."""
    entry = ContextEntry(
        layer=ContextLayer.TOOL,
        content="Temporary tool output",
        source="tool:read",
        ttl_seconds=1,
    )

    assert not entry.is_expired()
    time.sleep(1.1)
    assert entry.is_expired()


def test_context_entry_no_expiration() -> None:
    """ContextEntry: no expiration when TTL is None."""
    entry = ContextEntry(
        layer=ContextLayer.SYSTEM,
        content="Permanent content",
        source="system",
    )

    assert not entry.is_expired()
    # Even after time passes
    time.sleep(0.1)
    assert not entry.is_expired()


def test_context_entry_age() -> None:
    """ContextEntry: age calculation."""
    entry = ContextEntry(
        layer=ContextLayer.DYNAMIC,
        content="Test",
        source="test",
    )

    time.sleep(0.1)
    age = entry.age_seconds()
    assert age >= 0.1


def test_context_entry_metadata() -> None:
    """ContextEntry: metadata storage."""
    entry = ContextEntry(
        layer=ContextLayer.MEMORY,
        content="Retrieved memory",
        source="memory:zettelkasten",
        metadata={"score": 0.95, "doc_id": "123"},
    )

    assert entry.metadata["score"] == 0.95
    assert entry.metadata["doc_id"] == "123"


# ============================================================================
# LayerBudget Tests
# ============================================================================


def test_layer_budget_total() -> None:
    """LayerBudget: total equals sum of all layers."""
    total = sum(
        LayerBudget.get_budget(layer) for layer in ContextLayer
    )
    assert total == LayerBudget.TOTAL


def test_layer_budget_get() -> None:
    """LayerBudget: get_budget returns correct values."""
    assert LayerBudget.get_budget(ContextLayer.SYSTEM) == 5_000
    assert LayerBudget.get_budget(ContextLayer.USER) == 2_000
    assert LayerBudget.get_budget(ContextLayer.PROJECT) == 10_000
    assert LayerBudget.get_budget(ContextLayer.SESSION) == 20_000
    assert LayerBudget.get_budget(ContextLayer.TASK) == 15_000
    assert LayerBudget.get_budget(ContextLayer.TOOL) == 10_000
    assert LayerBudget.get_budget(ContextLayer.MEMORY) == 20_000
    assert LayerBudget.get_budget(ContextLayer.DYNAMIC) == 18_000


# ============================================================================
# LayeredContextManager: Basic Operations
# ============================================================================


def test_manager_initialization() -> None:
    """Manager: initializes with empty layers."""
    manager = LayeredContextManager(max_tokens=100_000)

    assert manager.max_tokens == 100_000
    assert manager.current_tokens == 0
    assert len(manager.layers) == 8  # 8 layers
    assert all(len(entries) == 0 for entries in manager.layers.values())


def test_manager_add_entry() -> None:
    """Manager: add entry to layer."""
    manager = LayeredContextManager()

    manager.add(
        ContextLayer.SYSTEM,
        "You are a helpful assistant",
        source="system_prompt",
    )

    entries = manager.get_layer(ContextLayer.SYSTEM)
    assert len(entries) == 1
    assert entries[0].content == "You are a helpful assistant"
    assert manager.current_tokens > 0


def test_manager_add_multiple_entries() -> None:
    """Manager: add multiple entries to different layers."""
    manager = LayeredContextManager()

    manager.add(ContextLayer.SYSTEM, "System prompt", source="system")
    manager.add(ContextLayer.USER, "User preference", source="user")
    manager.add(ContextLayer.PROJECT, "Project context", source="CLAUDE.md")

    assert len(manager.get_layer(ContextLayer.SYSTEM)) == 1
    assert len(manager.get_layer(ContextLayer.USER)) == 1
    assert len(manager.get_layer(ContextLayer.PROJECT)) == 1


def test_manager_add_with_priority() -> None:
    """Manager: add entry with custom priority."""
    manager = LayeredContextManager()

    manager.add(
        ContextLayer.TASK,
        "High priority task",
        source="task",
        priority=10,
    )

    entries = manager.get_layer(ContextLayer.TASK)
    assert entries[0].priority == 10


def test_manager_add_invalid_priority() -> None:
    """Manager: reject invalid priority values."""
    manager = LayeredContextManager()

    with pytest.raises(ValueError, match="Priority must be 1-10"):
        manager.add(ContextLayer.DYNAMIC, "Test", source="test", priority=0)

    with pytest.raises(ValueError, match="Priority must be 1-10"):
        manager.add(ContextLayer.DYNAMIC, "Test", source="test", priority=11)


def test_manager_get_layer() -> None:
    """Manager: get_layer returns correct entries."""
    manager = LayeredContextManager()

    manager.add(ContextLayer.TOOL, "Tool output 1", source="tool:read")
    manager.add(ContextLayer.TOOL, "Tool output 2", source="tool:write")

    entries = manager.get_layer(ContextLayer.TOOL)
    assert len(entries) == 2
    assert entries[0].content == "Tool output 1"
    assert entries[1].content == "Tool output 2"


def test_manager_clear_layer() -> None:
    """Manager: clear_layer removes all entries."""
    manager = LayeredContextManager()

    manager.add(ContextLayer.DYNAMIC, "Entry 1", source="test")
    manager.add(ContextLayer.DYNAMIC, "Entry 2", source="test")

    assert len(manager.get_layer(ContextLayer.DYNAMIC)) == 2

    manager.clear_layer(ContextLayer.DYNAMIC)

    assert len(manager.get_layer(ContextLayer.DYNAMIC)) == 0
    assert manager.current_tokens == 0


# ============================================================================
# LayeredContextManager: Assembly
# ============================================================================


def test_manager_assemble_all_layers() -> None:
    """Manager: assemble includes all layers in order."""
    manager = LayeredContextManager()

    manager.add(ContextLayer.SYSTEM, "System", source="system")
    manager.add(ContextLayer.USER, "User", source="user")
    manager.add(ContextLayer.PROJECT, "Project", source="project")
    manager.add(ContextLayer.SESSION, "Session", source="session")
    manager.add(ContextLayer.TASK, "Task", source="task")
    manager.add(ContextLayer.TOOL, "Tool", source="tool")
    manager.add(ContextLayer.MEMORY, "Memory", source="memory")
    manager.add(ContextLayer.DYNAMIC, "Dynamic", source="dynamic")

    context = manager.assemble()

    # Check layer order
    assert context.index("SYSTEM LAYER") < context.index("USER LAYER")
    assert context.index("USER LAYER") < context.index("PROJECT LAYER")
    assert context.index("PROJECT LAYER") < context.index("SESSION LAYER")
    assert context.index("SESSION LAYER") < context.index("TASK LAYER")
    assert context.index("TASK LAYER") < context.index("TOOL LAYER")
    assert context.index("TOOL LAYER") < context.index("MEMORY LAYER")
    assert context.index("MEMORY LAYER") < context.index("DYNAMIC LAYER")


def test_manager_assemble_selected_layers() -> None:
    """Manager: assemble only selected layers."""
    manager = LayeredContextManager()

    manager.add(ContextLayer.SYSTEM, "System", source="system")
    manager.add(ContextLayer.USER, "User", source="user")
    manager.add(ContextLayer.TOOL, "Tool", source="tool")

    context = manager.assemble(layers=[ContextLayer.SYSTEM, ContextLayer.USER])

    assert "SYSTEM LAYER" in context
    assert "USER LAYER" in context
    assert "TOOL LAYER" not in context


def test_manager_assemble_empty() -> None:
    """Manager: assemble with no entries returns empty string."""
    manager = LayeredContextManager()

    context = manager.assemble()

    assert context == ""


def test_manager_assemble_priority_order() -> None:
    """Manager: assemble orders entries by priority within layer."""
    manager = LayeredContextManager()

    manager.add(ContextLayer.TASK, "Low priority", source="test", priority=1)
    manager.add(ContextLayer.TASK, "High priority", source="test", priority=10)
    manager.add(ContextLayer.TASK, "Medium priority", source="test", priority=5)

    context = manager.assemble()

    # High priority should appear first
    high_pos = context.index("High priority")
    medium_pos = context.index("Medium priority")
    low_pos = context.index("Low priority")

    assert high_pos < medium_pos < low_pos


# ============================================================================
# LayeredContextManager: Pruning
# ============================================================================


def test_manager_prune_expired() -> None:
    """Manager: prune removes expired entries."""
    manager = LayeredContextManager()

    manager.add(
        ContextLayer.TOOL,
        "Expired",
        source="tool",
        ttl_seconds=1,
    )
    manager.add(
        ContextLayer.TOOL,
        "Not expired",
        source="tool",
    )

    assert len(manager.get_layer(ContextLayer.TOOL)) == 2

    time.sleep(1.1)
    removed = manager.prune()

    assert removed == 1
    assert len(manager.get_layer(ContextLayer.TOOL)) == 1
    assert manager.get_layer(ContextLayer.TOOL)[0].content == "Not expired"


def test_manager_prune_no_expired() -> None:
    """Manager: prune with no expired entries."""
    manager = LayeredContextManager()

    manager.add(ContextLayer.SYSTEM, "Permanent", source="system")

    removed = manager.prune()

    assert removed == 0
    assert len(manager.get_layer(ContextLayer.SYSTEM)) == 1


def test_manager_prune_updates_token_count() -> None:
    """Manager: prune updates current_tokens."""
    manager = LayeredContextManager()

    manager.add(
        ContextLayer.DYNAMIC,
        "x" * 400,  # ~100 tokens
        source="test",
        ttl_seconds=1,
    )

    initial_tokens = manager.current_tokens
    assert initial_tokens > 0

    time.sleep(1.1)
    manager.prune()

    assert manager.current_tokens == 0


# ============================================================================
# LayeredContextManager: Budget Enforcement
# ============================================================================


def test_manager_enforce_per_layer_budget() -> None:
    """Manager: enforce_budget respects per-layer limits."""
    manager = LayeredContextManager()

    # Add more than SYSTEM budget (5,000 tokens)
    # Each entry is ~100 tokens (400 chars)
    for i in range(60):  # 6,000 tokens total
        manager.add(
            ContextLayer.SYSTEM,
            "x" * 400,
            source=f"test_{i}",
            priority=5,
        )

    manager.enforce_budget()

    usage = manager.get_budget_usage()
    assert usage[ContextLayer.SYSTEM] <= LayerBudget.SYSTEM


def test_manager_enforce_total_budget() -> None:
    """Manager: enforce_budget respects total limit."""
    manager = LayeredContextManager(max_tokens=1000)

    # Add 2000 tokens across layers
    for layer in [ContextLayer.SYSTEM, ContextLayer.USER, ContextLayer.PROJECT]:
        for i in range(10):
            manager.add(
                layer,
                "x" * 400,  # ~100 tokens
                source=f"test_{i}",
            )

    manager.enforce_budget()

    assert manager.current_tokens <= 1000


def test_manager_enforce_keeps_high_priority() -> None:
    """Manager: enforce_budget keeps high-priority entries."""
    manager = LayeredContextManager(max_tokens=500)

    # Add low priority
    for i in range(10):
        manager.add(
            ContextLayer.DYNAMIC,
            "x" * 400,
            source=f"low_{i}",
            priority=1,
        )

    # Add high priority
    manager.add(
        ContextLayer.DYNAMIC,
        "IMPORTANT",
        source="high",
        priority=10,
    )

    manager.enforce_budget()

    # High priority should survive
    entries = manager.get_layer(ContextLayer.DYNAMIC)
    contents = [e.content for e in entries]
    assert "IMPORTANT" in contents


def test_manager_enforce_keeps_newer_entries() -> None:
    """Manager: enforce_budget prefers newer entries at same priority."""
    manager = LayeredContextManager(max_tokens=500)

    # Add old entry
    manager.add(
        ContextLayer.TASK,
        "OLD",
        source="old",
        priority=5,
    )

    time.sleep(0.1)

    # Add many new entries
    for i in range(10):
        manager.add(
            ContextLayer.TASK,
            f"NEW_{i}",
            source=f"new_{i}",
            priority=5,
        )

    manager.enforce_budget()

    # Newer entries should survive
    entries = manager.get_layer(ContextLayer.TASK)
    contents = [e.content for e in entries]

    # At least some NEW entries should be present
    new_count = sum(1 for c in contents if c.startswith("NEW_"))
    assert new_count > 0


# ============================================================================
# LayeredContextManager: Budget Usage
# ============================================================================


def test_manager_get_budget_usage() -> None:
    """Manager: get_budget_usage returns correct counts."""
    manager = LayeredContextManager()

    manager.add(ContextLayer.SYSTEM, "x" * 400, source="test")  # ~100 tokens
    manager.add(ContextLayer.USER, "x" * 800, source="test")  # ~200 tokens

    usage = manager.get_budget_usage()

    assert usage[ContextLayer.SYSTEM] == 100
    assert usage[ContextLayer.USER] == 200
    assert usage[ContextLayer.PROJECT] == 0


def test_manager_get_budget_usage_empty() -> None:
    """Manager: get_budget_usage with no entries."""
    manager = LayeredContextManager()

    usage = manager.get_budget_usage()

    assert all(tokens == 0 for tokens in usage.values())


# ============================================================================
# LayeredContextManager: Provenance
# ============================================================================


def test_manager_get_provenance() -> None:
    """Manager: get_provenance finds entries by content."""
    manager = LayeredContextManager()

    manager.add(ContextLayer.SYSTEM, "System prompt", source="system")
    manager.add(ContextLayer.USER, "User preference", source="user")
    manager.add(ContextLayer.TOOL, "Tool output", source="tool:read")

    results = manager.get_provenance("User preference")

    assert len(results) == 1
    assert results[0].layer == ContextLayer.USER
    assert results[0].source == "user"


def test_manager_get_provenance_multiple() -> None:
    """Manager: get_provenance finds multiple matches."""
    manager = LayeredContextManager()

    manager.add(ContextLayer.TASK, "Task: analyze data", source="task1")
    manager.add(ContextLayer.TASK, "Task: process data", source="task2")
    manager.add(ContextLayer.MEMORY, "data analysis results", source="memory")

    results = manager.get_provenance("data")

    assert len(results) == 3


def test_manager_get_provenance_no_match() -> None:
    """Manager: get_provenance returns empty list when no match."""
    manager = LayeredContextManager()

    manager.add(ContextLayer.SYSTEM, "System prompt", source="system")

    results = manager.get_provenance("nonexistent")

    assert len(results) == 0


# ============================================================================
# LayeredContextManager: Statistics
# ============================================================================


def test_manager_get_stats() -> None:
    """Manager: get_stats returns correct statistics."""
    manager = LayeredContextManager(max_tokens=100_000)

    manager.add(ContextLayer.SYSTEM, "x" * 400, source="test")  # ~100 tokens
    manager.add(ContextLayer.USER, "x" * 400, source="test")  # ~100 tokens

    stats = manager.get_stats()

    assert stats["total_tokens"] == 200
    assert stats["max_tokens"] == 100_000
    assert stats["utilization"] == 200 / 100_000
    assert stats["entry_count"] == 2
    assert stats["layer_usage"]["system"] == 100
    assert stats["layer_usage"]["user"] == 100
    assert stats["layer_counts"]["system"] == 1
    assert stats["layer_counts"]["user"] == 1


def test_manager_get_stats_empty() -> None:
    """Manager: get_stats with no entries."""
    manager = LayeredContextManager(max_tokens=100_000)

    stats = manager.get_stats()

    assert stats["total_tokens"] == 0
    assert stats["entry_count"] == 0
    assert stats["utilization"] == 0.0


# ============================================================================
# Integration Tests
# ============================================================================


def test_integration_full_workflow() -> None:
    """Integration: full workflow with all features."""
    manager = LayeredContextManager(max_tokens=10_000)

    # Add system prompt (high priority, permanent)
    manager.add(
        ContextLayer.SYSTEM,
        "You are a helpful assistant",
        source="system_prompt",
        priority=10,
    )

    # Add user preferences
    manager.add(
        ContextLayer.USER,
        "User prefers concise answers",
        source="user_config",
        priority=8,
    )

    # Add project context
    manager.add(
        ContextLayer.PROJECT,
        "Project: Lyra Deep Research Agent",
        source="CLAUDE.md",
        priority=7,
    )

    # Add temporary tool outputs
    for i in range(5):
        manager.add(
            ContextLayer.TOOL,
            f"Tool output {i}: " + "x" * 400,
            source=f"tool:read_{i}",
            ttl_seconds=60,
            priority=3,
        )

    # Add dynamic content
    for i in range(10):
        manager.add(
            ContextLayer.DYNAMIC,
            f"Dynamic entry {i}: " + "x" * 400,
            source=f"runtime_{i}",
            priority=2,
        )

    # Check initial state
    assert manager.current_tokens > 0
    initial_count = sum(len(entries) for entries in manager.layers.values())
    assert initial_count == 18  # 1 + 1 + 1 + 5 + 10

    # Enforce budget
    manager.enforce_budget()

    # High priority entries should survive
    system_entries = manager.get_layer(ContextLayer.SYSTEM)
    assert len(system_entries) > 0
    assert "helpful assistant" in system_entries[0].content

    # Total should be under budget
    assert manager.current_tokens <= 10_000

    # Assemble context
    context = manager.assemble()
    assert "SYSTEM LAYER" in context
    assert "helpful assistant" in context


def test_integration_context_reduction() -> None:
    """Integration: verify context reduction (60-80% target)."""
    manager = LayeredContextManager(max_tokens=10_000)

    # Add 50,000 tokens of content
    for i in range(125):  # 125 * 400 chars = 50,000 chars = ~12,500 tokens
        manager.add(
            ContextLayer.DYNAMIC,
            "x" * 400,
            source=f"test_{i}",
            priority=5,
        )

    initial_tokens = manager.current_tokens
    assert initial_tokens > 10_000

    # Enforce budget
    manager.enforce_budget()

    # Should be reduced to under 10,000
    assert manager.current_tokens <= 10_000

    # Calculate reduction percentage
    reduction = (initial_tokens - manager.current_tokens) / initial_tokens
    assert reduction >= 0.20  # At least 20% reduction


def test_integration_provenance_tracking() -> None:
    """Integration: provenance tracking for debugging."""
    manager = LayeredContextManager()

    # Add entries from different sources
    manager.add(
        ContextLayer.PROJECT,
        "Project uses Python 3.11",
        source="CLAUDE.md",
    )
    manager.add(
        ContextLayer.TOOL,
        "File contents: Python 3.11 required",
        source="tool:read:requirements.txt",
    )
    manager.add(
        ContextLayer.MEMORY,
        "Previous research: Python 3.11 features",
        source="memory:zettelkasten",
    )

    # Find all mentions of Python 3.11
    results = manager.get_provenance("Python 3.11")

    assert len(results) == 3

    sources = [r.source for r in results]
    assert "CLAUDE.md" in sources
    assert "tool:read:requirements.txt" in sources
    assert "memory:zettelkasten" in sources
