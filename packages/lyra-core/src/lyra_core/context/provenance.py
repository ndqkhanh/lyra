"""Enhanced provenance tracking and debugging tools for layered context system.

This module provides comprehensive debugging and analysis capabilities for the
8-layer context system, including:
- Context diff visualization (before/after comparisons)
- Context inspection (query by source, age, priority)
- Audit trail (complete history of all operations)
- Debugging tools (why was something pruned? find duplicates)

These tools are essential for understanding context behavior, debugging issues,
and optimizing context usage in production.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from lyra_core.context.layered_context import (
    ContextEntry,
    ContextLayer,
    LayeredContextManager,
)


class AuditEventType(str, Enum):
    """Types of audit events."""

    ADD = "add"
    REMOVE = "remove"
    PRUNE = "prune"
    BUDGET_ENFORCEMENT = "budget_enforcement"


@dataclass
class AuditEvent:
    """A single event in the audit trail.

    Attributes:
        event_type: Type of event (add, remove, prune, budget_enforcement)
        timestamp: When the event occurred
        entry: The context entry involved (if applicable)
        reason: Human-readable reason for the event
        metadata: Additional event-specific data
    """

    event_type: AuditEventType
    timestamp: datetime
    entry: ContextEntry | None = None
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "entry": {
                "layer": self.entry.layer.value,
                "source": self.entry.source,
                "content_preview": self.entry.content[:100],
                "token_count": self.entry.token_count,
                "priority": self.entry.priority,
            }
            if self.entry
            else None,
            "reason": self.reason,
            "metadata": self.metadata,
        }


@dataclass
class AuditStatistics:
    """Statistics about audit trail activity.

    Attributes:
        total_events: Total number of events
        adds: Number of add events
        removes: Number of remove events
        prunes: Number of prune events
        budget_enforcements: Number of budget enforcement events
        entries_added: Total entries added
        entries_removed: Total entries removed
        entries_pruned: Total entries pruned
    """

    total_events: int = 0
    adds: int = 0
    removes: int = 0
    prunes: int = 0
    budget_enforcements: int = 0
    entries_added: int = 0
    entries_removed: int = 0
    entries_pruned: int = 0


class ContextAuditTrail:
    """Records all operations on the context manager for debugging.

    The audit trail maintains a complete history of all add/remove/prune
    operations, enabling post-hoc analysis and debugging.
    """

    def __init__(self) -> None:
        """Initialize empty audit trail."""
        self._events: list[AuditEvent] = []

    def record_add(self, entry: ContextEntry) -> None:
        """Record an add operation.

        Args:
            entry: The entry that was added
        """
        event = AuditEvent(
            event_type=AuditEventType.ADD,
            timestamp=datetime.now(),
            entry=entry,
            reason="Entry added to context",
        )
        self._events.append(event)

    def record_remove(self, entry: ContextEntry, reason: str) -> None:
        """Record a remove operation.

        Args:
            entry: The entry that was removed
            reason: Why it was removed
        """
        event = AuditEvent(
            event_type=AuditEventType.REMOVE,
            timestamp=datetime.now(),
            entry=entry,
            reason=reason,
        )
        self._events.append(event)

    def record_prune(self, entries: list[ContextEntry], reason: str) -> None:
        """Record a prune operation (multiple entries removed).

        Args:
            entries: The entries that were pruned
            reason: Why they were pruned
        """
        for entry in entries:
            event = AuditEvent(
                event_type=AuditEventType.PRUNE,
                timestamp=datetime.now(),
                entry=entry,
                reason=reason,
            )
            self._events.append(event)

    def record_budget_enforcement(
        self, before: int, after: int, pruned: list[ContextEntry]
    ) -> None:
        """Record a budget enforcement operation.

        Args:
            before: Token count before enforcement
            after: Token count after enforcement
            pruned: Entries that were pruned
        """
        event = AuditEvent(
            event_type=AuditEventType.BUDGET_ENFORCEMENT,
            timestamp=datetime.now(),
            reason=f"Budget enforcement: {before} -> {after} tokens",
            metadata={
                "before_tokens": before,
                "after_tokens": after,
                "pruned_count": len(pruned),
            },
        )
        self._events.append(event)

        # Record individual pruned entries
        for entry in pruned:
            self.record_prune([entry], "Budget enforcement")

    def get_history(self, limit: int = 100) -> list[AuditEvent]:
        """Get recent audit events.

        Args:
            limit: Maximum number of events to return (most recent first)

        Returns:
            List of audit events
        """
        return list(reversed(self._events[-limit:]))

    def export_to_file(self, filepath: Path) -> None:
        """Export audit trail to JSON file.

        Args:
            filepath: Path to write JSON file
        """
        data = {
            "exported_at": datetime.now().isoformat(),
            "total_events": len(self._events),
            "events": [event.to_dict() for event in self._events],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def get_statistics(self) -> AuditStatistics:
        """Get statistics about audit trail activity.

        Returns:
            Statistics object with counts
        """
        stats = AuditStatistics(total_events=len(self._events))

        for event in self._events:
            if event.event_type == AuditEventType.ADD:
                stats.adds += 1
                stats.entries_added += 1
            elif event.event_type == AuditEventType.REMOVE:
                stats.removes += 1
                stats.entries_removed += 1
            elif event.event_type == AuditEventType.PRUNE:
                stats.prunes += 1
                stats.entries_pruned += 1
            elif event.event_type == AuditEventType.BUDGET_ENFORCEMENT:
                stats.budget_enforcements += 1

        return stats


@dataclass
class LayerInspection:
    """Inspection results for a single layer.

    Attributes:
        layer: The layer being inspected
        entry_count: Number of entries
        token_count: Total tokens used
        sources: Unique sources in this layer
        priority_distribution: Count of entries by priority
        age_distribution: Count of entries by age bucket
    """

    layer: ContextLayer
    entry_count: int
    token_count: int
    sources: list[str]
    priority_distribution: dict[int, int]
    age_distribution: dict[str, int]


class ContextInspector:
    """Inspect and query the context manager.

    Provides various query methods to understand what's in the context,
    where it came from, and how it's distributed.
    """

    def __init__(self, context_manager: LayeredContextManager) -> None:
        """Initialize inspector.

        Args:
            context_manager: The context manager to inspect
        """
        self._manager = context_manager

    def inspect_layer(self, layer: ContextLayer) -> LayerInspection:
        """Inspect a specific layer.

        Args:
            layer: The layer to inspect

        Returns:
            Inspection results
        """
        entries = self._manager.get_layer(layer)

        # Collect sources
        sources = sorted({e.source for e in entries})

        # Priority distribution
        priority_dist: dict[int, int] = {}
        for entry in entries:
            priority_dist[entry.priority] = priority_dist.get(entry.priority, 0) + 1

        # Age distribution (buckets: <1min, <5min, <1hr, <1day, >1day)
        age_dist = {
            "<1min": 0,
            "<5min": 0,
            "<1hr": 0,
            "<1day": 0,
            ">1day": 0,
        }

        for entry in entries:
            age = entry.age_seconds()
            if age < 60:
                age_dist["<1min"] += 1
            elif age < 300:
                age_dist["<5min"] += 1
            elif age < 3600:
                age_dist["<1hr"] += 1
            elif age < 86400:
                age_dist["<1day"] += 1
            else:
                age_dist[">1day"] += 1

        return LayerInspection(
            layer=layer,
            entry_count=len(entries),
            token_count=sum(e.token_count for e in entries),
            sources=sources,
            priority_distribution=priority_dist,
            age_distribution=age_dist,
        )

    def find_by_source(self, source: str) -> list[ContextEntry]:
        """Find all entries from a specific source.

        Args:
            source: Source identifier to search for

        Returns:
            List of matching entries
        """
        results: list[ContextEntry] = []

        for layer in ContextLayer:
            for entry in self._manager.get_layer(layer):
                if entry.source == source:
                    results.append(entry)

        return results

    def find_by_age(self, min_age_seconds: int) -> list[ContextEntry]:
        """Find all entries older than a specific age.

        Args:
            min_age_seconds: Minimum age in seconds

        Returns:
            List of matching entries
        """
        results: list[ContextEntry] = []

        for layer in ContextLayer:
            for entry in self._manager.get_layer(layer):
                if entry.age_seconds() >= min_age_seconds:
                    results.append(entry)

        return results

    def find_by_priority(self, min_priority: int) -> list[ContextEntry]:
        """Find all entries with priority >= min_priority.

        Args:
            min_priority: Minimum priority (1-10)

        Returns:
            List of matching entries
        """
        results: list[ContextEntry] = []

        for layer in ContextLayer:
            for entry in self._manager.get_layer(layer):
                if entry.priority >= min_priority:
                    results.append(entry)

        return results

    def get_timeline(self) -> list[tuple[datetime, str, ContextEntry]]:
        """Get chronological timeline of all entries.

        Returns:
            List of (timestamp, layer_name, entry) tuples, sorted by time
        """
        timeline: list[tuple[datetime, str, ContextEntry]] = []

        for layer in ContextLayer:
            for entry in self._manager.get_layer(layer):
                timeline.append((entry.timestamp, layer.value, entry))

        # Sort by timestamp
        timeline.sort(key=lambda x: x[0])

        return timeline

    def get_token_distribution(self) -> dict[ContextLayer, float]:
        """Get percentage of tokens used by each layer.

        Returns:
            Dictionary mapping layer to percentage (0.0-100.0)
        """
        total = self._manager.current_tokens
        if total == 0:
            return dict.fromkeys(ContextLayer, 0.0)

        usage = self._manager.get_budget_usage()
        return {layer: (tokens / total) * 100.0 for layer, tokens in usage.items()}

    def detect_bloat(self) -> list[str]:
        """Detect potential issues with context usage.

        Returns:
            List of warning messages
        """
        warnings: list[str] = []

        # Check for layers over budget (before enforcement)
        # We check the raw layer usage, not after budget enforcement
        from lyra_core.context.layered_context import LayerBudget

        for layer in ContextLayer:
            entries = self._manager.get_layer(layer)
            tokens = sum(e.token_count for e in entries)
            budget = LayerBudget.get_budget(layer)
            if tokens > budget:
                warnings.append(
                    f"{layer.value} layer over budget: {tokens}/{budget} tokens"
                )

        # Check for duplicate content
        all_entries: list[ContextEntry] = []
        for layer in ContextLayer:
            all_entries.extend(self._manager.get_layer(layer))

        content_map: dict[str, list[ContextEntry]] = {}
        for entry in all_entries:
            content_map.setdefault(entry.content, []).append(entry)

        duplicates = [entries for entries in content_map.values() if len(entries) > 1]
        if duplicates:
            warnings.append(
                f"Found {len(duplicates)} duplicate content blocks across layers"
            )

        # Check for very old entries
        old_entries = self.find_by_age(86400)  # 1 day
        if old_entries:
            warnings.append(f"Found {len(old_entries)} entries older than 1 day")

        # Check total utilization
        utilization = (self._manager.current_tokens / self._manager.max_tokens) * 100
        if utilization > 90:
            warnings.append(f"High context utilization: {utilization:.1f}%")

        return warnings


@dataclass
class ChurnAnalysis:
    """Analysis of how often entries are added/removed.

    Attributes:
        total_adds: Total number of add operations
        total_removes: Total number of remove operations
        churn_rate: Ratio of removes to adds
        most_churned_sources: Sources with highest churn
        most_churned_layers: Layers with highest churn
    """

    total_adds: int
    total_removes: int
    churn_rate: float
    most_churned_sources: list[tuple[str, int]]
    most_churned_layers: list[tuple[str, int]]


class ContextDebugger:
    """Advanced debugging tools for context system.

    Combines context manager and audit trail to answer questions like:
    - Why was this content pruned?
    - What's the full lifecycle of an entry?
    - Are there duplicate entries?
    - How often is content being added/removed?
    """

    def __init__(
        self,
        context_manager: LayeredContextManager,
        audit_trail: ContextAuditTrail,
    ) -> None:
        """Initialize debugger.

        Args:
            context_manager: The context manager to debug
            audit_trail: The audit trail with operation history
        """
        self._manager = context_manager
        self._audit = audit_trail

    def why_pruned(self, content_snippet: str) -> str | None:
        """Explain why content was pruned.

        Args:
            content_snippet: Text to search for in pruned entries

        Returns:
            Explanation string, or None if not found in audit trail
        """
        # Search audit trail for prune events matching this content
        for event in reversed(self._audit._events):
            if event.event_type in (AuditEventType.PRUNE, AuditEventType.REMOVE):
                if event.entry and content_snippet in event.entry.content:
                    return (
                        f"Content pruned at {event.timestamp.isoformat()}\n"
                        f"Reason: {event.reason}\n"
                        f"Layer: {event.entry.layer.value}\n"
                        f"Source: {event.entry.source}\n"
                        f"Priority: {event.entry.priority}\n"
                        f"Token count: {event.entry.token_count}"
                    )

        return None

    def trace_entry(self, entry_id: str) -> list[AuditEvent]:
        """Get full lifecycle of an entry.

        Args:
            entry_id: Identifier to search for (source or content snippet)

        Returns:
            List of audit events related to this entry
        """
        results: list[AuditEvent] = []

        for event in self._audit._events:
            if event.entry:
                # Match by source or content
                if (
                    event.entry.source == entry_id
                    or entry_id in event.entry.content
                ):
                    results.append(event)

        return results

    def find_duplicates(self) -> list[list[ContextEntry]]:
        """Find duplicate content across all layers.

        Returns:
            List of duplicate groups (each group has 2+ entries with same content)
        """
        all_entries: list[ContextEntry] = []
        for layer in ContextLayer:
            all_entries.extend(self._manager.get_layer(layer))

        # Group by content
        content_map: dict[str, list[ContextEntry]] = {}
        for entry in all_entries:
            content_map.setdefault(entry.content, []).append(entry)

        # Return only groups with duplicates
        return [entries for entries in content_map.values() if len(entries) > 1]

    def analyze_churn(self) -> ChurnAnalysis:
        """Analyze how often entries are added/removed.

        Returns:
            Churn analysis with statistics
        """
        stats = self._audit.get_statistics()

        # Count by source
        source_adds: dict[str, int] = {}
        source_removes: dict[str, int] = {}

        for event in self._audit._events:
            if not event.entry:
                continue

            source = event.entry.source

            if event.event_type == AuditEventType.ADD:
                source_adds[source] = source_adds.get(source, 0) + 1
            elif event.event_type in (AuditEventType.REMOVE, AuditEventType.PRUNE):
                source_removes[source] = source_removes.get(source, 0) + 1

        # Calculate churn per source
        source_churn: dict[str, int] = {}
        for source in set(source_adds.keys()) | set(source_removes.keys()):
            adds = source_adds.get(source, 0)
            removes = source_removes.get(source, 0)
            source_churn[source] = adds + removes

        # Count by layer
        layer_adds: dict[str, int] = {}
        layer_removes: dict[str, int] = {}

        for event in self._audit._events:
            if not event.entry:
                continue

            layer = event.entry.layer.value

            if event.event_type == AuditEventType.ADD:
                layer_adds[layer] = layer_adds.get(layer, 0) + 1
            elif event.event_type in (AuditEventType.REMOVE, AuditEventType.PRUNE):
                layer_removes[layer] = layer_removes.get(layer, 0) + 1

        # Calculate churn per layer
        layer_churn: dict[str, int] = {}
        for layer in set(layer_adds.keys()) | set(layer_removes.keys()):
            adds = layer_adds.get(layer, 0)
            removes = layer_removes.get(layer, 0)
            layer_churn[layer] = adds + removes

        # Sort by churn
        top_sources = sorted(source_churn.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]
        top_layers = sorted(layer_churn.items(), key=lambda x: x[1], reverse=True)[:5]

        churn_rate = (
            stats.entries_removed / stats.entries_added
            if stats.entries_added > 0
            else 0.0
        )

        return ChurnAnalysis(
            total_adds=stats.entries_added,
            total_removes=stats.entries_removed,
            churn_rate=churn_rate,
            most_churned_sources=top_sources,
            most_churned_layers=top_layers,
        )

    def suggest_optimizations(self) -> list[str]:
        """Suggest optimizations based on usage patterns.

        Returns:
            List of optimization suggestions
        """
        suggestions: list[str] = []

        # Check for high churn
        churn = self.analyze_churn()
        if churn.churn_rate > 0.5:
            suggestions.append(
                f"High churn rate ({churn.churn_rate:.2f}): "
                "Consider increasing TTL or priority for frequently pruned content"
            )

        # Check for duplicates
        duplicates = self.find_duplicates()
        if duplicates:
            suggestions.append(
                f"Found {len(duplicates)} duplicate content blocks: "
                "Consider deduplication before adding to context"
            )

        # Check for bloat
        inspector = ContextInspector(self._manager)
        warnings = inspector.detect_bloat()
        if warnings:
            suggestions.extend(warnings)

        # Check for low-priority content taking up space
        low_priority = inspector.find_by_priority(1)
        if low_priority:
            total_tokens = sum(e.token_count for e in low_priority)
            suggestions.append(
                f"Found {len(low_priority)} low-priority entries ({total_tokens} tokens): "
                "Consider removing or increasing priority"
            )

        return suggestions


class ContextDiff:
    """Compare two context manager states.

    Useful for understanding what changed between two points in time.
    """

    def __init__(
        self, before: LayeredContextManager, after: LayeredContextManager
    ) -> None:
        """Initialize diff.

        Args:
            before: Context manager state before changes
            after: Context manager state after changes
        """
        self._before = before
        self._after = after

    def get_added_entries(self) -> list[ContextEntry]:
        """Get entries that were added.

        Returns:
            List of entries present in 'after' but not in 'before'
        """
        before_contents = self._get_all_contents(self._before)
        after_entries = self._get_all_entries(self._after)

        return [e for e in after_entries if e.content not in before_contents]

    def get_removed_entries(self) -> list[ContextEntry]:
        """Get entries that were removed.

        Returns:
            List of entries present in 'before' but not in 'after'
        """
        after_contents = self._get_all_contents(self._after)
        before_entries = self._get_all_entries(self._before)

        return [e for e in before_entries if e.content not in after_contents]

    def get_modified_entries(self) -> list[tuple[ContextEntry, ContextEntry]]:
        """Get entries that were modified.

        Note: This implementation considers entries with same source but different
        content as modified. In practice, entries are immutable, so this will
        typically return an empty list unless entries are replaced.

        Returns:
            List of (before, after) tuples for modified entries
        """
        # Group by source
        before_by_source: dict[str, ContextEntry] = {}
        for entry in self._get_all_entries(self._before):
            before_by_source[entry.source] = entry

        after_by_source: dict[str, ContextEntry] = {}
        for entry in self._get_all_entries(self._after):
            after_by_source[entry.source] = entry

        # Find entries with same source but different content
        modified: list[tuple[ContextEntry, ContextEntry]] = []
        for source in set(before_by_source.keys()) & set(after_by_source.keys()):
            before_entry = before_by_source[source]
            after_entry = after_by_source[source]

            if before_entry.content != after_entry.content:
                modified.append((before_entry, after_entry))

        return modified

    def visualize(self) -> str:
        """Generate human-readable diff.

        Returns:
            Formatted diff string
        """
        lines: list[str] = []

        lines.append("# Context Diff")
        lines.append("")

        # Summary
        added = self.get_added_entries()
        removed = self.get_removed_entries()
        modified = self.get_modified_entries()

        lines.append(f"Added: {len(added)} entries")
        lines.append(f"Removed: {len(removed)} entries")
        lines.append(f"Modified: {len(modified)} entries")
        lines.append("")

        # Added entries
        if added:
            lines.append("## Added Entries")
            for entry in added:
                lines.append(
                    f"+ [{entry.layer.value}] {entry.source} "
                    f"({entry.token_count} tokens, priority={entry.priority})"
                )
                lines.append(f"  {entry.content[:100]}...")
            lines.append("")

        # Removed entries
        if removed:
            lines.append("## Removed Entries")
            for entry in removed:
                lines.append(
                    f"- [{entry.layer.value}] {entry.source} "
                    f"({entry.token_count} tokens, priority={entry.priority})"
                )
                lines.append(f"  {entry.content[:100]}...")
            lines.append("")

        # Modified entries
        if modified:
            lines.append("## Modified Entries")
            for before, after in modified:
                lines.append(f"~ [{before.layer.value}] {before.source}")
                lines.append(f"  Before: {before.content[:100]}...")
                lines.append(f"  After:  {after.content[:100]}...")
            lines.append("")

        return "\n".join(lines)

    def to_json(self) -> dict[str, Any]:
        """Generate machine-readable diff.

        Returns:
            Dictionary with diff data
        """
        added = self.get_added_entries()
        removed = self.get_removed_entries()
        modified = self.get_modified_entries()

        return {
            "summary": {
                "added_count": len(added),
                "removed_count": len(removed),
                "modified_count": len(modified),
            },
            "added": [
                {
                    "layer": e.layer.value,
                    "source": e.source,
                    "token_count": e.token_count,
                    "priority": e.priority,
                    "content_preview": e.content[:100],
                }
                for e in added
            ],
            "removed": [
                {
                    "layer": e.layer.value,
                    "source": e.source,
                    "token_count": e.token_count,
                    "priority": e.priority,
                    "content_preview": e.content[:100],
                }
                for e in removed
            ],
            "modified": [
                {
                    "layer": before.layer.value,
                    "source": before.source,
                    "before_preview": before.content[:100],
                    "after_preview": after.content[:100],
                }
                for before, after in modified
            ],
        }

    def _get_all_entries(self, manager: LayeredContextManager) -> list[ContextEntry]:
        """Get all entries from a context manager."""
        entries: list[ContextEntry] = []
        for layer in ContextLayer:
            entries.extend(manager.get_layer(layer))
        return entries

    def _get_all_contents(self, manager: LayeredContextManager) -> set[str]:
        """Get all content strings from a context manager."""
        return {e.content for e in self._get_all_entries(manager)}
