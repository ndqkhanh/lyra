"""Child-Task Context Isolation for Lyra Deep Research.

This module implements context isolation for child tasks, preventing context
pollution and enabling efficient multi-agent coordination. Key features:

- ContextScope: Defines what context a child task can access
- IsolationPolicy: Defines inheritance and merge rules
- ContextBoundary: Enforces boundaries between parent and child contexts
- MergeStrategy: Controls how child results are merged back to parent

Expected Impact:
    - Prevent child tasks from polluting parent context
    - Reduce context overhead for child tasks (inherit only what's needed)
    - Enable selective merging of child discoveries back to parent
    - Foundation for multi-agent coordination with isolated contexts
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from lyra_core.context.layered_context import (
    ContextEntry,
    ContextLayer,
    LayeredContextManager,
)

# ============================================================================
# Merge Strategies
# ============================================================================


class MergeStrategy(Enum):
    """Defines how child context is merged back to parent."""

    APPEND = "append"  # Add child entries to parent
    REPLACE = "replace"  # Replace parent entries with child
    SELECTIVE = "selective"  # Merge only high-priority entries (priority >= 7)
    NONE = "none"  # Don't merge (full isolation)


@dataclass
class MergeResult:
    """Result of merging child context into parent."""

    entries_merged: int = 0
    tokens_merged: int = 0
    layers_affected: list[ContextLayer] = field(default_factory=list)
    skipped_entries: int = 0  # Entries not merged due to strategy


class ContextMerger:
    """Handles merging child context into parent context."""

    def merge(
        self,
        parent: LayeredContextManager,
        child: LayeredContextManager,
        layers: list[ContextLayer],
        strategy: MergeStrategy,
    ) -> MergeResult:
        """Merge child context into parent using strategy.

        Args:
            parent: Parent context manager
            child: Child context manager
            layers: Which layers to merge
            strategy: How to merge (append, replace, selective, none)

        Returns:
            MergeResult with statistics
        """
        if strategy == MergeStrategy.NONE:
            return MergeResult()

        result = MergeResult()

        for layer in layers:
            child_entries = child.get_layer(layer)

            if not child_entries:
                continue

            # Filter entries based on strategy
            entries_to_merge = self._filter_entries(child_entries, strategy)

            if not entries_to_merge:
                result.skipped_entries += len(child_entries)
                continue

            # Apply merge strategy
            if strategy == MergeStrategy.REPLACE:
                parent.clear_layer(layer)

            # Add entries to parent
            for entry in entries_to_merge:
                parent.add(
                    layer=layer,
                    content=entry.content,
                    source=f"child:{entry.source}",
                    priority=entry.priority,
                    ttl_seconds=entry.ttl_seconds,
                    metadata={**entry.metadata, "from_child": True},
                )
                result.entries_merged += 1
                result.tokens_merged += entry.token_count

            if layer not in result.layers_affected:
                result.layers_affected.append(layer)

            result.skipped_entries += len(child_entries) - len(entries_to_merge)

        return result

    def _filter_entries(
        self, entries: list[ContextEntry], strategy: MergeStrategy
    ) -> list[ContextEntry]:
        """Filter entries based on merge strategy.

        Args:
            entries: Entries to filter
            strategy: Merge strategy

        Returns:
            Filtered list of entries
        """
        if strategy == MergeStrategy.APPEND or strategy == MergeStrategy.REPLACE:
            return entries

        if strategy == MergeStrategy.SELECTIVE:
            # Only merge high-priority entries (priority >= 7)
            return [e for e in entries if e.priority >= 7]

        return []


# ============================================================================
# Isolation Policy
# ============================================================================


@dataclass
class IsolationPolicy:
    """Defines inheritance and merge rules for child tasks.

    Attributes:
        inherit_layers: Which layers to inherit from parent
        merge_layers: Which layers to merge back to parent
        merge_strategy: How to merge child results
        max_tokens: Maximum tokens for child context
    """

    inherit_layers: list[ContextLayer]
    merge_layers: list[ContextLayer]
    merge_strategy: MergeStrategy = MergeStrategy.SELECTIVE
    max_tokens: int = 50_000

    # Default policies
    DEFAULT_INHERIT = [ContextLayer.SYSTEM, ContextLayer.USER, ContextLayer.PROJECT]
    DEFAULT_MERGE = [ContextLayer.MEMORY, ContextLayer.DYNAMIC]

    @staticmethod
    def for_discovery_agent() -> IsolationPolicy:
        """Policy for discovery agents (inherit minimal, merge discoveries).

        Discovery agents explore the codebase/docs and return findings.
        They need minimal context and should merge their discoveries.
        """
        return IsolationPolicy(
            inherit_layers=[ContextLayer.SYSTEM, ContextLayer.PROJECT],
            merge_layers=[ContextLayer.MEMORY, ContextLayer.DYNAMIC],
            merge_strategy=MergeStrategy.SELECTIVE,
            max_tokens=30_000,
        )

    @staticmethod
    def for_analysis_agent() -> IsolationPolicy:
        """Policy for analysis agents (inherit more, merge analyses).

        Analysis agents need more context to understand what they're analyzing.
        They should merge their analysis results back.
        """
        return IsolationPolicy(
            inherit_layers=[
                ContextLayer.SYSTEM,
                ContextLayer.USER,
                ContextLayer.PROJECT,
                ContextLayer.TASK,
            ],
            merge_layers=[ContextLayer.MEMORY, ContextLayer.DYNAMIC],
            merge_strategy=MergeStrategy.SELECTIVE,
            max_tokens=50_000,
        )

    @staticmethod
    def for_synthesis_agent() -> IsolationPolicy:
        """Policy for synthesis agents (inherit all, merge report).

        Synthesis agents need full context to synthesize results.
        They should merge their final report back.
        """
        return IsolationPolicy(
            inherit_layers=[
                ContextLayer.SYSTEM,
                ContextLayer.USER,
                ContextLayer.PROJECT,
                ContextLayer.SESSION,
                ContextLayer.TASK,
                ContextLayer.MEMORY,
            ],
            merge_layers=[ContextLayer.DYNAMIC],
            merge_strategy=MergeStrategy.APPEND,
            max_tokens=80_000,
        )

    @staticmethod
    def default() -> IsolationPolicy:
        """Default isolation policy."""
        return IsolationPolicy(
            inherit_layers=IsolationPolicy.DEFAULT_INHERIT,
            merge_layers=IsolationPolicy.DEFAULT_MERGE,
            merge_strategy=MergeStrategy.SELECTIVE,
            max_tokens=50_000,
        )


# ============================================================================
# Context Scope
# ============================================================================


class ContextScope:
    """Defines what context a child task can access.

    A ContextScope creates an isolated child context that inherits only
    specified layers from the parent. This prevents child tasks from
    accessing or polluting the parent's full context.
    """

    def __init__(
        self,
        parent_context: LayeredContextManager,
        inherit_layers: list[ContextLayer],
        max_tokens: int = 50_000,
    ) -> None:
        """Initialize context scope.

        Args:
            parent_context: Parent context manager
            inherit_layers: Which layers to inherit from parent
            max_tokens: Maximum tokens for child context
        """
        self.parent_context = parent_context
        self.inherit_layers = inherit_layers
        self.max_tokens = max_tokens
        self.child_context = LayeredContextManager(max_tokens=max_tokens)

    def create_child_context(self) -> LayeredContextManager:
        """Create isolated child context with inherited layers.

        Returns:
            New LayeredContextManager with inherited content
        """
        # Copy entries from inherited layers
        for layer in self.inherit_layers:
            parent_entries = self.parent_context.get_layer(layer)

            for entry in parent_entries:
                # Skip expired entries
                if entry.is_expired():
                    continue

                # Add to child context with provenance
                self.child_context.add(
                    layer=layer,
                    content=entry.content,
                    source=f"parent:{entry.source}",
                    priority=entry.priority,
                    ttl_seconds=entry.ttl_seconds,
                    metadata={**entry.metadata, "inherited": True},
                )

        return self.child_context

    def merge_child_results(
        self,
        child_context: LayeredContextManager,
        merge_layers: list[ContextLayer],
        strategy: MergeStrategy = MergeStrategy.SELECTIVE,
    ) -> MergeResult:
        """Merge child results back to parent (selective).

        Args:
            child_context: Child context manager
            merge_layers: Which layers to merge
            strategy: How to merge

        Returns:
            MergeResult with statistics
        """
        merger = ContextMerger()
        return merger.merge(
            parent=self.parent_context,
            child=child_context,
            layers=merge_layers,
            strategy=strategy,
        )


# ============================================================================
# Isolation Statistics
# ============================================================================


@dataclass
class IsolationStats:
    """Statistics about context isolation."""

    parent_tokens: int
    child_tokens: int
    tokens_saved: int  # parent_tokens - child_tokens
    layers_inherited: int
    layers_isolated: int
    entries_inherited: int
    entries_isolated: int
    reduction_percent: float  # (tokens_saved / parent_tokens) * 100


# ============================================================================
# Context Boundary
# ============================================================================


class ContextBoundary:
    """Enforces boundaries between parent and child contexts.

    A ContextBoundary manages the lifecycle of child contexts:
    1. Spawn child with policy-based inheritance
    2. Track active children
    3. Merge child results back to parent
    4. Collect isolation statistics
    """

    def __init__(
        self, parent: LayeredContextManager, policy: IsolationPolicy
    ) -> None:
        """Initialize context boundary.

        Args:
            parent: Parent context manager
            policy: Isolation policy to enforce
        """
        self.parent = parent
        self.policy = policy
        self.children: dict[str, LayeredContextManager] = {}
        self.scopes: dict[str, ContextScope] = {}

    def spawn_child(self, task_id: str) -> LayeredContextManager:
        """Create child context with policy-based inheritance.

        Args:
            task_id: Unique identifier for the child task

        Returns:
            New LayeredContextManager for the child task
        """
        # Create scope with policy
        scope = ContextScope(
            parent_context=self.parent,
            inherit_layers=self.policy.inherit_layers,
            max_tokens=self.policy.max_tokens,
        )

        # Create child context
        child = scope.create_child_context()

        # Track child and scope
        self.children[task_id] = child
        self.scopes[task_id] = scope

        return child

    def merge_child(self, child: LayeredContextManager, task_id: str) -> MergeResult:
        """Merge child results back to parent.

        Args:
            child: Child context manager
            task_id: Task identifier

        Returns:
            MergeResult with statistics
        """
        # Get scope for this task
        scope = self.scopes.get(task_id)
        if scope is None:
            # Create temporary scope if not found
            scope = ContextScope(
                parent_context=self.parent,
                inherit_layers=self.policy.inherit_layers,
                max_tokens=self.policy.max_tokens,
            )

        # Merge using policy
        result = scope.merge_child_results(
            child_context=child,
            merge_layers=self.policy.merge_layers,
            strategy=self.policy.merge_strategy,
        )

        # Clean up tracking
        self.children.pop(task_id, None)
        self.scopes.pop(task_id, None)

        return result

    def get_isolation_stats(self, task_id: str | None = None) -> IsolationStats:
        """Get statistics on context isolation.

        Args:
            task_id: Specific task to get stats for (None = aggregate all children)

        Returns:
            IsolationStats with token savings and layer information
        """
        parent_tokens = self.parent.current_tokens

        if task_id is not None:
            # Stats for specific child
            child = self.children.get(task_id)
            if child is None:
                return IsolationStats(
                    parent_tokens=parent_tokens,
                    child_tokens=0,
                    tokens_saved=parent_tokens,
                    layers_inherited=0,
                    layers_isolated=0,
                    entries_inherited=0,
                    entries_isolated=0,
                    reduction_percent=100.0,
                )

            child_tokens = child.current_tokens
            tokens_saved = parent_tokens - child_tokens

            # Count inherited vs isolated
            inherited_count = sum(
                len(child.get_layer(layer)) for layer in self.policy.inherit_layers
            )
            total_parent_entries = sum(
                len(self.parent.get_layer(layer)) for layer in ContextLayer
            )
            isolated_count = total_parent_entries - inherited_count

            return IsolationStats(
                parent_tokens=parent_tokens,
                child_tokens=child_tokens,
                tokens_saved=tokens_saved,
                layers_inherited=len(self.policy.inherit_layers),
                layers_isolated=len(ContextLayer) - len(self.policy.inherit_layers),
                entries_inherited=inherited_count,
                entries_isolated=isolated_count,
                reduction_percent=(tokens_saved / parent_tokens * 100)
                if parent_tokens > 0
                else 0.0,
            )

        # Aggregate stats for all children
        if not self.children:
            return IsolationStats(
                parent_tokens=parent_tokens,
                child_tokens=0,
                tokens_saved=parent_tokens,
                layers_inherited=0,
                layers_isolated=0,
                entries_inherited=0,
                entries_isolated=0,
                reduction_percent=100.0,
            )

        total_child_tokens = sum(child.current_tokens for child in self.children.values())
        avg_child_tokens = total_child_tokens // len(self.children)
        tokens_saved = parent_tokens - avg_child_tokens

        return IsolationStats(
            parent_tokens=parent_tokens,
            child_tokens=avg_child_tokens,
            tokens_saved=tokens_saved,
            layers_inherited=len(self.policy.inherit_layers),
            layers_isolated=len(ContextLayer) - len(self.policy.inherit_layers),
            entries_inherited=0,  # Would need to aggregate
            entries_isolated=0,  # Would need to aggregate
            reduction_percent=(tokens_saved / parent_tokens * 100)
            if parent_tokens > 0
            else 0.0,
        )

    def get_active_children(self) -> list[str]:
        """Get list of active child task IDs.

        Returns:
            List of task IDs with active child contexts
        """
        return list(self.children.keys())
