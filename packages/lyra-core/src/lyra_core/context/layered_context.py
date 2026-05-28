"""8-layer context system inspired by autocontext.

This module implements a layered context management system that solves the O(n²)
context growth problem by organizing context into 8 distinct layers with explicit
ownership, persistence policies, and budget enforcement.

Layers (in assembly order):
    1. SYSTEM    — System prompts, capabilities (static, always loaded)
    2. USER      — User preferences, directives (session-scoped)
    3. PROJECT   — Project context, CLAUDE.md (project-scoped)
    4. SESSION   — Current session state (session-scoped)
    5. TASK      — Current task context (task-scoped)
    6. TOOL      — Tool results, outputs (ephemeral)
    7. MEMORY    — Retrieved memories (query-scoped)
    8. DYNAMIC   — Runtime additions (ephemeral)

Key Features:
    - Provenance tracking: Every entry knows its source
    - Budget enforcement: Per-layer and total token limits
    - TTL support: Automatic expiration of ephemeral content
    - Priority-based pruning: Keep high-priority content when over budget
    - Layer-specific assembly: Build context from selected layers only

Expected Impact:
    - 60-80% context reduction (from autocontext benchmarks)
    - O(1) context growth instead of O(n²)
    - Foundation for multi-agent coordination
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


class ContextLayer(str, enum.Enum):
    """8-layer context hierarchy."""

    SYSTEM = "system"  # System prompts, capabilities (static)
    USER = "user"  # User preferences, directives (session-scoped)
    PROJECT = "project"  # Project context, CLAUDE.md (project-scoped)
    SESSION = "session"  # Current session state (session-scoped)
    TASK = "task"  # Current task context (task-scoped)
    TOOL = "tool"  # Tool results, outputs (ephemeral)
    MEMORY = "memory"  # Retrieved memories (query-scoped)
    DYNAMIC = "dynamic"  # Runtime additions (ephemeral)


# Assembly order (top to bottom)
_LAYER_ORDER = [
    ContextLayer.SYSTEM,
    ContextLayer.USER,
    ContextLayer.PROJECT,
    ContextLayer.SESSION,
    ContextLayer.TASK,
    ContextLayer.TOOL,
    ContextLayer.MEMORY,
    ContextLayer.DYNAMIC,
]


class LayerBudget:
    """Token budget allocation per layer.

    Total budget: 100,000 tokens
    Distribution based on autocontext analysis and Lyra's needs.
    """

    SYSTEM = 5_000
    USER = 2_000
    PROJECT = 10_000
    SESSION = 20_000
    TASK = 15_000
    TOOL = 10_000
    MEMORY = 20_000
    DYNAMIC = 18_000
    TOTAL = 100_000

    @classmethod
    def get_budget(cls, layer: ContextLayer) -> int:
        """Get token budget for a specific layer."""
        return {
            ContextLayer.SYSTEM: cls.SYSTEM,
            ContextLayer.USER: cls.USER,
            ContextLayer.PROJECT: cls.PROJECT,
            ContextLayer.SESSION: cls.SESSION,
            ContextLayer.TASK: cls.TASK,
            ContextLayer.TOOL: cls.TOOL,
            ContextLayer.MEMORY: cls.MEMORY,
            ContextLayer.DYNAMIC: cls.DYNAMIC,
        }[layer]


def _estimate_tokens(text: str) -> int:
    """Cheap token estimate: ~1 token per 4 chars, min 1.

    This is a rough heuristic. Production builds can swap in tiktoken
    without contract changes.
    """
    return max(1, len(text) // 4)


@dataclass
class ContextEntry:
    """A single entry in the layered context system.

    Attributes:
        layer: Which layer this entry belongs to
        content: The actual content (text)
        source: Where this came from (e.g., "CLAUDE.md", "tool:read", "user_input")
        timestamp: When this entry was created
        token_count: Estimated token count (computed on creation)
        priority: 1-10, higher = more important (default: 5)
        ttl_seconds: Time to live in seconds (None = no expiration)
        metadata: Additional metadata for debugging/provenance
    """

    layer: ContextLayer
    content: str
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    token_count: int = field(init=False)
    priority: int = 5
    ttl_seconds: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Compute token count after initialization."""
        self.token_count = _estimate_tokens(self.content)

    def is_expired(self, now: datetime | None = None) -> bool:
        """Check if this entry has expired based on TTL."""
        if self.ttl_seconds is None:
            return False
        if now is None:
            now = datetime.now()
        expiry = self.timestamp + timedelta(seconds=self.ttl_seconds)
        return now >= expiry

    def age_seconds(self, now: datetime | None = None) -> float:
        """Get age of this entry in seconds."""
        if now is None:
            now = datetime.now()
        return (now - self.timestamp).total_seconds()


@dataclass
class LayeredContextManager:
    """Manages context across 8 layers with budget enforcement.

    This is the main interface for the layered context system. It handles:
    - Adding entries to specific layers
    - Assembling context from selected layers
    - Budget enforcement (per-layer and total)
    - Automatic pruning of expired/low-priority content
    - Provenance tracking for debugging

    Example:
        >>> manager = LayeredContextManager(max_tokens=100_000)
        >>> manager.add(
        ...     ContextLayer.SYSTEM,
        ...     "You are a helpful assistant",
        ...     source="system_prompt",
        ...     priority=10
        ... )
        >>> manager.add(
        ...     ContextLayer.TOOL,
        ...     "File contents: ...",
        ...     source="tool:read",
        ...     ttl_seconds=300  # Expire after 5 minutes
        ... )
        >>> context = manager.assemble()
        >>> print(context)
    """

    max_tokens: int = 100_000
    layers: dict[ContextLayer, list[ContextEntry]] = field(default_factory=dict)
    current_tokens: int = field(default=0, init=False)
    audit_trail: Any | None = None  # ContextAuditTrail, avoid circular import

    def __post_init__(self) -> None:
        """Initialize empty lists for each layer."""
        self.layers = {layer: [] for layer in ContextLayer}
        self.current_tokens = 0

    def add(
        self,
        layer: ContextLayer,
        content: str,
        source: str,
        priority: int = 5,
        ttl_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a new entry to the specified layer.

        Args:
            layer: Which layer to add to
            content: The content to add
            source: Where this came from (for provenance)
            priority: 1-10, higher = more important (default: 5)
            ttl_seconds: Time to live in seconds (None = no expiration)
            metadata: Additional metadata for debugging

        Raises:
            ValueError: If priority is out of range [1, 10]
        """
        if not 1 <= priority <= 10:
            raise ValueError(f"Priority must be 1-10, got {priority}")

        entry = ContextEntry(
            layer=layer,
            content=content,
            source=source,
            priority=priority,
            ttl_seconds=ttl_seconds,
            metadata=metadata or {},
        )

        self.layers[layer].append(entry)
        self.current_tokens += entry.token_count

        # Record in audit trail if available
        if self.audit_trail is not None:
            self.audit_trail.record_add(entry)

    def get_layer(self, layer: ContextLayer) -> list[ContextEntry]:
        """Get all entries in a specific layer (including expired ones).

        Args:
            layer: The layer to retrieve

        Returns:
            List of entries in the layer (may be empty)
        """
        return list(self.layers[layer])

    def assemble(
        self, layers: list[ContextLayer] | None = None
    ) -> str:
        """Assemble context from selected layers into a single string.

        Args:
            layers: Which layers to include (None = all layers)

        Returns:
            Assembled context as a single string with layer markers
        """
        if layers is None:
            layers = list(_LAYER_ORDER)

        # Remove expired entries first
        self.prune()

        # Enforce budget before assembly
        self.enforce_budget()

        parts: list[str] = []
        for layer in _LAYER_ORDER:
            if layer not in layers:
                continue

            entries = self.layers[layer]
            if not entries:
                continue

            # Sort by priority (descending) within each layer
            sorted_entries = sorted(entries, key=lambda e: e.priority, reverse=True)

            # Add layer header
            parts.append(f"# {layer.value.upper()} LAYER")

            # Add entries
            for entry in sorted_entries:
                parts.append(entry.content)

        return "\n\n".join(parts)

    def prune(self) -> int:
        """Remove expired entries from all layers.

        Returns:
            Number of entries removed
        """
        now = datetime.now()
        removed = 0
        pruned_entries: list[ContextEntry] = []

        for layer in ContextLayer:
            entries = self.layers[layer]
            before_count = len(entries)

            # Collect expired entries for audit trail
            expired = [e for e in entries if e.is_expired(now)]
            pruned_entries.extend(expired)

            # Keep only non-expired entries
            self.layers[layer] = [e for e in entries if not e.is_expired(now)]

            removed += before_count - len(self.layers[layer])

        # Recompute token count
        self._recompute_tokens()

        # Record in audit trail if available
        if self.audit_trail is not None and pruned_entries:
            self.audit_trail.record_prune(pruned_entries, "TTL expiration")

        return removed

    def get_budget_usage(self) -> dict[ContextLayer, int]:
        """Get current token usage per layer.

        Returns:
            Dictionary mapping layer to token count
        """
        return {
            layer: sum(e.token_count for e in entries)
            for layer, entries in self.layers.items()
        }

    def enforce_budget(self) -> None:
        """Enforce per-layer and total budget limits.

        This method prunes low-priority entries when budgets are exceeded.
        It operates in two phases:
        1. Per-layer budget enforcement
        2. Total budget enforcement (if still over)
        """
        before_tokens = self.current_tokens
        all_pruned: list[ContextEntry] = []

        # Phase 1: Enforce per-layer budgets
        for layer in ContextLayer:
            budget = LayerBudget.get_budget(layer)
            entries = self.layers[layer]

            # Calculate current usage
            current = sum(e.token_count for e in entries)

            if current <= budget:
                continue

            # Sort by priority (descending), then by age (oldest first)
            sorted_entries = sorted(
                entries,
                key=lambda e: (e.priority, -e.age_seconds()),
                reverse=True,
            )

            # Keep entries until budget is reached
            kept: list[ContextEntry] = []
            used = 0

            for entry in sorted_entries:
                if used + entry.token_count <= budget:
                    kept.append(entry)
                    used += entry.token_count
                else:
                    all_pruned.append(entry)

            self.layers[layer] = kept

        # Phase 2: Enforce total budget
        self._recompute_tokens()

        if self.current_tokens <= self.max_tokens:
            # Record budget enforcement if anything was pruned
            if self.audit_trail is not None and all_pruned:
                self.audit_trail.record_budget_enforcement(
                    before_tokens, self.current_tokens, all_pruned
                )
            return

        # Collect all entries with their layer
        all_entries: list[tuple[ContextLayer, ContextEntry]] = []
        for layer in ContextLayer:
            for entry in self.layers[layer]:
                all_entries.append((layer, entry))

        # Sort by priority (descending), then by age (oldest first)
        sorted_all = sorted(
            all_entries,
            key=lambda x: (x[1].priority, -x[1].age_seconds()),
            reverse=True,
        )

        # Rebuild layers keeping only what fits in total budget
        new_layers: dict[ContextLayer, list[ContextEntry]] = {
            layer: [] for layer in ContextLayer
        }
        used = 0

        for layer, entry in sorted_all:
            if used + entry.token_count <= self.max_tokens:
                new_layers[layer].append(entry)
                used += entry.token_count
            else:
                all_pruned.append(entry)

        self.layers = new_layers
        self._recompute_tokens()

        # Record budget enforcement
        if self.audit_trail is not None and all_pruned:
            self.audit_trail.record_budget_enforcement(
                before_tokens, self.current_tokens, all_pruned
            )

    def clear_layer(self, layer: ContextLayer) -> None:
        """Clear all entries from a specific layer.

        Args:
            layer: The layer to clear
        """
        self.layers[layer] = []
        self._recompute_tokens()

    def get_provenance(self, content_snippet: str) -> list[ContextEntry]:
        """Find entries containing a specific content snippet.

        Useful for debugging: "Where did this context come from?"

        Args:
            content_snippet: Text to search for

        Returns:
            List of entries containing the snippet
        """
        results: list[ContextEntry] = []

        for layer in ContextLayer:
            for entry in self.layers[layer]:
                if content_snippet in entry.content:
                    results.append(entry)

        return results

    def _recompute_tokens(self) -> None:
        """Recompute total token count from all layers."""
        self.current_tokens = sum(
            sum(e.token_count for e in entries)
            for entries in self.layers.values()
        )

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the context manager.

        Returns:
            Dictionary with stats (total_tokens, entry_count, layer_usage, etc.)
        """
        usage = self.get_budget_usage()

        return {
            "total_tokens": self.current_tokens,
            "max_tokens": self.max_tokens,
            "utilization": self.current_tokens / self.max_tokens,
            "entry_count": sum(len(entries) for entries in self.layers.values()),
            "layer_usage": {layer.value: tokens for layer, tokens in usage.items()},
            "layer_counts": {
                layer.value: len(entries) for layer, entries in self.layers.items()
            },
        }

    def get_inspector(self) -> Any:
        """Get a ContextInspector for this manager.

        Returns:
            ContextInspector instance (import from provenance module to use)
        """
        from lyra_core.context.provenance import ContextInspector

        return ContextInspector(self)

    def get_debugger(self) -> Any:
        """Get a ContextDebugger for this manager.

        Requires audit_trail to be set.

        Returns:
            ContextDebugger instance (import from provenance module to use)

        Raises:
            ValueError: If audit_trail is not set
        """
        if self.audit_trail is None:
            raise ValueError("Cannot create debugger without audit_trail")

        from lyra_core.context.provenance import ContextDebugger

        return ContextDebugger(self, self.audit_trail)
