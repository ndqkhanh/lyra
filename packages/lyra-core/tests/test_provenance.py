"""Tests for provenance tracking and debugging tools.

This test suite covers:
- Context diff visualization (before/after comparisons)
- Context inspection (query by source, age, priority)
- Audit trail (recording and retrieval)
- Debugging tools (why_pruned, trace_entry, find_duplicates)
- Integration with LayeredContextManager
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from lyra_core.context.layered_context import (
    ContextEntry,
    ContextLayer,
    LayeredContextManager,
)
from lyra_core.context.provenance import (
    AuditEventType,
    ChurnAnalysis,
    ContextAuditTrail,
    ContextDebugger,
    ContextDiff,
    ContextInspector,
    LayerInspection,
)


class TestContextAuditTrail:
    """Tests for ContextAuditTrail."""

    def test_record_add(self):
        """Test recording add operations."""
        trail = ContextAuditTrail()
        entry = ContextEntry(
            layer=ContextLayer.SYSTEM,
            content="Test content",
            source="test",
        )

        trail.record_add(entry)

        history = trail.get_history()
        assert len(history) == 1
        assert history[0].event_type == AuditEventType.ADD
        assert history[0].entry == entry

    def test_record_remove(self):
        """Test recording remove operations."""
        trail = ContextAuditTrail()
        entry = ContextEntry(
            layer=ContextLayer.TOOL,
            content="Tool output",
            source="tool:read",
        )

        trail.record_remove(entry, "Manual removal")

        history = trail.get_history()
        assert len(history) == 1
        assert history[0].event_type == AuditEventType.REMOVE
        assert history[0].reason == "Manual removal"

    def test_record_prune(self):
        """Test recording prune operations."""
        trail = ContextAuditTrail()
        entries = [
            ContextEntry(
                layer=ContextLayer.DYNAMIC,
                content=f"Content {i}",
                source=f"source_{i}",
            )
            for i in range(3)
        ]

        trail.record_prune(entries, "TTL expiration")

        history = trail.get_history()
        assert len(history) == 3
        assert all(e.event_type == AuditEventType.PRUNE for e in history)
        assert all(e.reason == "TTL expiration" for e in history)

    def test_record_budget_enforcement(self):
        """Test recording budget enforcement."""
        trail = ContextAuditTrail()
        pruned = [
            ContextEntry(
                layer=ContextLayer.MEMORY,
                content="Old memory",
                source="memory:old",
            )
        ]

        trail.record_budget_enforcement(10000, 8000, pruned)

        history = trail.get_history()
        # Should have 1 budget enforcement event + 1 prune event
        assert len(history) >= 2
        budget_events = [e for e in history if e.event_type == AuditEventType.BUDGET_ENFORCEMENT]
        assert len(budget_events) == 1
        assert budget_events[0].metadata["before_tokens"] == 10000
        assert budget_events[0].metadata["after_tokens"] == 8000

    def test_get_history_limit(self):
        """Test history retrieval with limit."""
        trail = ContextAuditTrail()

        # Add 150 events
        for i in range(150):
            entry = ContextEntry(
                layer=ContextLayer.DYNAMIC,
                content=f"Content {i}",
                source=f"source_{i}",
            )
            trail.record_add(entry)

        # Get last 50
        history = trail.get_history(limit=50)
        assert len(history) == 50

        # Most recent should be last added
        assert "149" in history[0].entry.content

    def test_export_to_file(self, tmp_path):
        """Test exporting audit trail to JSON."""
        trail = ContextAuditTrail()
        entry = ContextEntry(
            layer=ContextLayer.SESSION,
            content="Session data",
            source="session",
        )
        trail.record_add(entry)

        filepath = tmp_path / "audit.json"
        trail.export_to_file(filepath)

        assert filepath.exists()

        # Verify JSON structure
        with open(filepath) as f:
            data = json.load(f)

        assert "exported_at" in data
        assert data["total_events"] == 1
        assert len(data["events"]) == 1
        assert data["events"][0]["event_type"] == "add"

    def test_get_statistics(self):
        """Test getting audit statistics."""
        trail = ContextAuditTrail()

        # Add various events
        for i in range(5):
            entry = ContextEntry(
                layer=ContextLayer.TASK,
                content=f"Task {i}",
                source=f"task_{i}",
            )
            trail.record_add(entry)

        for i in range(3):
            entry = ContextEntry(
                layer=ContextLayer.TOOL,
                content=f"Tool {i}",
                source=f"tool_{i}",
            )
            trail.record_remove(entry, "Cleanup")

        stats = trail.get_statistics()
        assert stats.total_events == 8
        assert stats.adds == 5
        assert stats.removes == 3
        assert stats.entries_added == 5
        assert stats.entries_removed == 3


class TestContextInspector:
    """Tests for ContextInspector."""

    def test_inspect_layer(self):
        """Test inspecting a specific layer."""
        manager = LayeredContextManager()
        manager.add(ContextLayer.SYSTEM, "System prompt", source="system", priority=10)
        manager.add(ContextLayer.SYSTEM, "Capabilities", source="system", priority=9)
        manager.add(ContextLayer.USER, "User prefs", source="user", priority=5)

        inspector = ContextInspector(manager)
        inspection = inspector.inspect_layer(ContextLayer.SYSTEM)

        assert inspection.layer == ContextLayer.SYSTEM
        assert inspection.entry_count == 2
        assert inspection.token_count > 0
        assert "system" in inspection.sources
        assert 10 in inspection.priority_distribution
        assert 9 in inspection.priority_distribution

    def test_find_by_source(self):
        """Test finding entries by source."""
        manager = LayeredContextManager()
        manager.add(ContextLayer.TOOL, "File 1", source="tool:read")
        manager.add(ContextLayer.TOOL, "File 2", source="tool:read")
        manager.add(ContextLayer.MEMORY, "Memory", source="memory:search")

        inspector = ContextInspector(manager)
        results = inspector.find_by_source("tool:read")

        assert len(results) == 2
        assert all(e.source == "tool:read" for e in results)

    def test_find_by_age(self):
        """Test finding entries by age."""
        manager = LayeredContextManager()

        # Add old entry
        old_entry = ContextEntry(
            layer=ContextLayer.SESSION,
            content="Old session",
            source="session",
            timestamp=datetime.now() - timedelta(seconds=100),
        )
        manager.layers[ContextLayer.SESSION].append(old_entry)
        manager.current_tokens += old_entry.token_count

        # Add new entry
        manager.add(ContextLayer.SESSION, "New session", source="session")

        inspector = ContextInspector(manager)
        old_results = inspector.find_by_age(50)  # Older than 50 seconds

        assert len(old_results) == 1
        assert old_results[0].content == "Old session"

    def test_find_by_priority(self):
        """Test finding entries by priority."""
        manager = LayeredContextManager()
        manager.add(ContextLayer.SYSTEM, "High priority", source="system", priority=10)
        manager.add(ContextLayer.USER, "Medium priority", source="user", priority=5)
        manager.add(ContextLayer.DYNAMIC, "Low priority", source="dynamic", priority=1)

        inspector = ContextInspector(manager)
        high_priority = inspector.find_by_priority(8)

        assert len(high_priority) == 1
        assert high_priority[0].priority == 10

    def test_get_timeline(self):
        """Test getting chronological timeline."""
        manager = LayeredContextManager()

        # Add entries with slight delays
        manager.add(ContextLayer.SYSTEM, "First", source="system")
        time.sleep(0.01)
        manager.add(ContextLayer.USER, "Second", source="user")
        time.sleep(0.01)
        manager.add(ContextLayer.TASK, "Third", source="task")

        inspector = ContextInspector(manager)
        timeline = inspector.get_timeline()

        assert len(timeline) == 3
        # Should be sorted by timestamp
        assert timeline[0][2].content == "First"
        assert timeline[1][2].content == "Second"
        assert timeline[2][2].content == "Third"

    def test_get_token_distribution(self):
        """Test getting token distribution by layer."""
        manager = LayeredContextManager()
        manager.add(ContextLayer.SYSTEM, "A" * 100, source="system")  # ~25 tokens
        manager.add(ContextLayer.USER, "B" * 100, source="user")  # ~25 tokens

        inspector = ContextInspector(manager)
        distribution = inspector.get_token_distribution()

        # Both layers should have ~50% each
        assert distribution[ContextLayer.SYSTEM] > 40
        assert distribution[ContextLayer.SYSTEM] < 60
        assert distribution[ContextLayer.USER] > 40
        assert distribution[ContextLayer.USER] < 60

    def test_detect_bloat_over_budget(self):
        """Test detecting layers over budget."""
        manager = LayeredContextManager()

        # Add way too much to SYSTEM layer (budget: 5000 tokens)
        # Each entry is ~50 tokens, so 150 entries = ~7500 tokens (over budget)
        for i in range(150):
            manager.add(
                ContextLayer.SYSTEM,
                "X" * 200,  # ~50 tokens each
                source=f"system_{i}",
            )

        inspector = ContextInspector(manager)
        warnings = inspector.detect_bloat()

        # Should warn about SYSTEM layer over budget
        assert any("system" in w.lower() and "over budget" in w.lower() for w in warnings)

    def test_detect_bloat_duplicates(self):
        """Test detecting duplicate content."""
        manager = LayeredContextManager()
        manager.add(ContextLayer.TOOL, "Duplicate content", source="tool1")
        manager.add(ContextLayer.TOOL, "Duplicate content", source="tool2")

        inspector = ContextInspector(manager)
        warnings = inspector.detect_bloat()

        assert any("duplicate" in w.lower() for w in warnings)

    def test_detect_bloat_old_entries(self):
        """Test detecting very old entries."""
        manager = LayeredContextManager()

        # Add old entry
        old_entry = ContextEntry(
            layer=ContextLayer.MEMORY,
            content="Old memory",
            source="memory",
            timestamp=datetime.now() - timedelta(days=2),
        )
        manager.layers[ContextLayer.MEMORY].append(old_entry)
        manager.current_tokens += old_entry.token_count

        inspector = ContextInspector(manager)
        warnings = inspector.detect_bloat()

        assert any("older than 1 day" in w.lower() for w in warnings)

    def test_detect_bloat_high_utilization(self):
        """Test detecting high context utilization."""
        manager = LayeredContextManager(max_tokens=1000)

        # Fill to 95%
        manager.add(ContextLayer.DYNAMIC, "X" * 3800, source="dynamic")  # ~950 tokens

        inspector = ContextInspector(manager)
        warnings = inspector.detect_bloat()

        assert any("utilization" in w.lower() for w in warnings)


class TestContextDebugger:
    """Tests for ContextDebugger."""

    def test_why_pruned(self):
        """Test explaining why content was pruned."""
        manager = LayeredContextManager()
        trail = ContextAuditTrail()
        manager.audit_trail = trail

        entry = ContextEntry(
            layer=ContextLayer.TOOL,
            content="Pruned content",
            source="tool:read",
        )
        trail.record_prune([entry], "TTL expiration")

        debugger = ContextDebugger(manager, trail)
        explanation = debugger.why_pruned("Pruned content")

        assert explanation is not None
        assert "TTL expiration" in explanation
        assert "tool:read" in explanation

    def test_why_pruned_not_found(self):
        """Test why_pruned when content not found."""
        manager = LayeredContextManager()
        trail = ContextAuditTrail()

        debugger = ContextDebugger(manager, trail)
        explanation = debugger.why_pruned("Nonexistent content")

        assert explanation is None

    def test_trace_entry(self):
        """Test tracing full lifecycle of an entry."""
        manager = LayeredContextManager()
        trail = ContextAuditTrail()

        entry = ContextEntry(
            layer=ContextLayer.SESSION,
            content="Session data",
            source="session:123",
        )

        trail.record_add(entry)
        trail.record_remove(entry, "Session ended")

        debugger = ContextDebugger(manager, trail)
        lifecycle = debugger.trace_entry("session:123")

        assert len(lifecycle) == 2
        assert lifecycle[0].event_type == AuditEventType.ADD
        assert lifecycle[1].event_type == AuditEventType.REMOVE

    def test_find_duplicates(self):
        """Test finding duplicate content."""
        manager = LayeredContextManager()
        manager.add(ContextLayer.TOOL, "Duplicate", source="tool1")
        manager.add(ContextLayer.TOOL, "Duplicate", source="tool2")
        manager.add(ContextLayer.MEMORY, "Unique", source="memory")

        trail = ContextAuditTrail()
        debugger = ContextDebugger(manager, trail)
        duplicates = debugger.find_duplicates()

        assert len(duplicates) == 1
        assert len(duplicates[0]) == 2
        assert all(e.content == "Duplicate" for e in duplicates[0])

    def test_find_duplicates_none(self):
        """Test find_duplicates when no duplicates exist."""
        manager = LayeredContextManager()
        manager.add(ContextLayer.SYSTEM, "Unique 1", source="system")
        manager.add(ContextLayer.USER, "Unique 2", source="user")

        trail = ContextAuditTrail()
        debugger = ContextDebugger(manager, trail)
        duplicates = debugger.find_duplicates()

        assert len(duplicates) == 0

    def test_analyze_churn(self):
        """Test analyzing add/remove churn."""
        manager = LayeredContextManager()
        trail = ContextAuditTrail()

        # Add and remove entries
        for i in range(10):
            entry = ContextEntry(
                layer=ContextLayer.TOOL,
                content=f"Tool {i}",
                source="tool:read",
            )
            trail.record_add(entry)

        for i in range(5):
            entry = ContextEntry(
                layer=ContextLayer.TOOL,
                content=f"Tool {i}",
                source="tool:read",
            )
            trail.record_remove(entry, "Cleanup")

        debugger = ContextDebugger(manager, trail)
        churn = debugger.analyze_churn()

        assert churn.total_adds == 10
        assert churn.total_removes == 5
        assert churn.churn_rate == 0.5
        assert len(churn.most_churned_sources) > 0
        assert churn.most_churned_sources[0][0] == "tool:read"

    def test_suggest_optimizations_high_churn(self):
        """Test optimization suggestions for high churn."""
        manager = LayeredContextManager()
        trail = ContextAuditTrail()

        # Create high churn scenario
        for i in range(10):
            entry = ContextEntry(
                layer=ContextLayer.DYNAMIC,
                content=f"Dynamic {i}",
                source="dynamic",
            )
            trail.record_add(entry)
            trail.record_remove(entry, "Frequent removal")

        debugger = ContextDebugger(manager, trail)
        suggestions = debugger.suggest_optimizations()

        assert any("churn" in s.lower() for s in suggestions)

    def test_suggest_optimizations_duplicates(self):
        """Test optimization suggestions for duplicates."""
        manager = LayeredContextManager()
        manager.add(ContextLayer.TOOL, "Duplicate", source="tool1")
        manager.add(ContextLayer.TOOL, "Duplicate", source="tool2")

        trail = ContextAuditTrail()
        debugger = ContextDebugger(manager, trail)
        suggestions = debugger.suggest_optimizations()

        assert any("duplicate" in s.lower() for s in suggestions)


class TestContextDiff:
    """Tests for ContextDiff."""

    def test_get_added_entries(self):
        """Test detecting added entries."""
        before = LayeredContextManager()
        before.add(ContextLayer.SYSTEM, "System prompt", source="system")

        after = LayeredContextManager()
        after.add(ContextLayer.SYSTEM, "System prompt", source="system")
        after.add(ContextLayer.USER, "User prefs", source="user")

        diff = ContextDiff(before, after)
        added = diff.get_added_entries()

        assert len(added) == 1
        assert added[0].content == "User prefs"

    def test_get_removed_entries(self):
        """Test detecting removed entries."""
        before = LayeredContextManager()
        before.add(ContextLayer.SYSTEM, "System prompt", source="system")
        before.add(ContextLayer.TOOL, "Tool output", source="tool")

        after = LayeredContextManager()
        after.add(ContextLayer.SYSTEM, "System prompt", source="system")

        diff = ContextDiff(before, after)
        removed = diff.get_removed_entries()

        assert len(removed) == 1
        assert removed[0].content == "Tool output"

    def test_get_modified_entries(self):
        """Test detecting modified entries."""
        before = LayeredContextManager()
        before.add(ContextLayer.SESSION, "Old session", source="session")

        after = LayeredContextManager()
        after.add(ContextLayer.SESSION, "New session", source="session")

        diff = ContextDiff(before, after)
        modified = diff.get_modified_entries()

        assert len(modified) == 1
        assert modified[0][0].content == "Old session"
        assert modified[0][1].content == "New session"

    def test_visualize(self):
        """Test human-readable diff visualization."""
        before = LayeredContextManager()
        before.add(ContextLayer.SYSTEM, "System", source="system")

        after = LayeredContextManager()
        after.add(ContextLayer.SYSTEM, "System", source="system")
        after.add(ContextLayer.USER, "User", source="user")

        diff = ContextDiff(before, after)
        visualization = diff.visualize()

        assert "Context Diff" in visualization
        assert "Added: 1" in visualization
        assert "[user]" in visualization.lower()

    def test_to_json(self):
        """Test machine-readable diff."""
        before = LayeredContextManager()
        before.add(ContextLayer.SYSTEM, "System", source="system")

        after = LayeredContextManager()
        after.add(ContextLayer.USER, "User", source="user")

        diff = ContextDiff(before, after)
        json_diff = diff.to_json()

        assert json_diff["summary"]["added_count"] == 1
        assert json_diff["summary"]["removed_count"] == 1
        assert len(json_diff["added"]) == 1
        assert len(json_diff["removed"]) == 1


class TestIntegrationWithLayeredContextManager:
    """Tests for integration with LayeredContextManager."""

    def test_audit_trail_integration_add(self):
        """Test that add operations are recorded in audit trail."""
        manager = LayeredContextManager()
        trail = ContextAuditTrail()
        manager.audit_trail = trail

        manager.add(ContextLayer.SYSTEM, "System prompt", source="system")

        history = trail.get_history()
        assert len(history) == 1
        assert history[0].event_type == AuditEventType.ADD

    def test_audit_trail_integration_prune(self):
        """Test that prune operations are recorded in audit trail."""
        manager = LayeredContextManager()
        trail = ContextAuditTrail()
        manager.audit_trail = trail

        # Add entry with short TTL
        manager.add(
            ContextLayer.TOOL,
            "Temporary",
            source="tool",
            ttl_seconds=1,
        )

        # Wait for expiration
        time.sleep(1.1)

        # Prune
        removed = manager.prune()

        assert removed == 1
        history = trail.get_history()
        prune_events = [e for e in history if e.event_type == AuditEventType.PRUNE]
        assert len(prune_events) == 1

    def test_audit_trail_integration_budget_enforcement(self):
        """Test that budget enforcement is recorded in audit trail."""
        manager = LayeredContextManager(max_tokens=100)
        trail = ContextAuditTrail()
        manager.audit_trail = trail

        # Add way too much content
        for i in range(10):
            manager.add(
                ContextLayer.DYNAMIC,
                "X" * 200,  # ~50 tokens each
                source=f"dynamic_{i}",
                priority=1,
            )

        # Trigger budget enforcement
        manager.enforce_budget()

        history = trail.get_history()
        budget_events = [
            e for e in history if e.event_type == AuditEventType.BUDGET_ENFORCEMENT
        ]
        assert len(budget_events) > 0

    def test_get_inspector(self):
        """Test getting inspector from manager."""
        manager = LayeredContextManager()
        manager.add(ContextLayer.SYSTEM, "System", source="system")

        inspector = manager.get_inspector()
        assert isinstance(inspector, ContextInspector)

        # Should be able to use it
        results = inspector.find_by_source("system")
        assert len(results) == 1

    def test_get_debugger(self):
        """Test getting debugger from manager."""
        manager = LayeredContextManager()
        trail = ContextAuditTrail()
        manager.audit_trail = trail

        debugger = manager.get_debugger()
        assert isinstance(debugger, ContextDebugger)

    def test_get_debugger_without_audit_trail(self):
        """Test that get_debugger raises error without audit trail."""
        manager = LayeredContextManager()

        with pytest.raises(ValueError, match="Cannot create debugger without audit_trail"):
            manager.get_debugger()

    def test_end_to_end_debugging_workflow(self):
        """Test complete debugging workflow."""
        # Setup
        manager = LayeredContextManager(max_tokens=500)
        trail = ContextAuditTrail()
        manager.audit_trail = trail

        # Add some content
        manager.add(ContextLayer.SYSTEM, "System prompt", source="system", priority=10)
        manager.add(ContextLayer.USER, "User prefs", source="user", priority=8)
        manager.add(ContextLayer.TOOL, "Tool output 1", source="tool:read", priority=5)
        manager.add(ContextLayer.TOOL, "Tool output 2", source="tool:read", priority=5)

        # Add duplicate
        manager.add(ContextLayer.MEMORY, "Tool output 1", source="memory", priority=3)

        # Add low priority content that will be pruned
        for i in range(10):
            manager.add(
                ContextLayer.DYNAMIC,
                "X" * 200,
                source=f"dynamic_{i}",
                priority=1,
            )

        # Trigger budget enforcement
        before_count = sum(len(entries) for entries in manager.layers.values())
        manager.enforce_budget()
        after_count = sum(len(entries) for entries in manager.layers.values())

        assert after_count < before_count

        # Use inspector
        inspector = manager.get_inspector()
        warnings = inspector.detect_bloat()
        assert len(warnings) > 0  # Should detect duplicates

        # Use debugger
        debugger = manager.get_debugger()
        duplicates = debugger.find_duplicates()
        assert len(duplicates) > 0

        churn = debugger.analyze_churn()
        assert churn.total_adds > 0

        suggestions = debugger.suggest_optimizations()
        assert len(suggestions) > 0

        # Check audit trail
        stats = trail.get_statistics()
        assert stats.total_events > 0
        assert stats.entries_added > 0
