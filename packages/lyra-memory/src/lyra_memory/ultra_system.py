"""
Ultra Memory System - Integrated cognitive memory architecture.

Combines all components into a unified self-managed memory system:
- Importance scoring
- ACT-R activation & decay
- Multi-graph knowledge store
- Offline consolidation
- Budget management

Based on research from Auto-Dreamer, MAGMA, ACT-R, and cognitive psychology.
"""

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from lyra_memory.activation_manager import ActivationManager, ActivationRecord
from lyra_memory.budget_controller import (
    BudgetStatus,
    MemoryBudgetController,
)
from lyra_memory.consolidation_engine import (
    ConsolidationEngine,
    ConsolidationResult,
)
from lyra_memory.importance_scorer import ImportanceScorer
from lyra_memory.multi_graph import MultiGraphStore
from lyra_memory.schema import MemoryRecord, MemoryScope, MemoryType
from lyra_memory.store import MemoryStore


@dataclass
class UltraMemoryConfig:
    """
    Configuration for ultra memory system.

    Attributes:
        capacity_limit: Maximum number of memories
        decay_rate: ACT-R decay parameter
        importance_weight: Weight for importance in activation
        retrieval_threshold: Minimum activation for accessibility
        consolidation_interval_hours: Hours between consolidations
        enable_auto_consolidation: Whether to run consolidation automatically
        enable_auto_pruning: Whether to prune automatically when needed
    """
    capacity_limit: int = 10000
    decay_rate: float = 0.5
    importance_weight: float = 2.0
    retrieval_threshold: float = -1.0
    consolidation_interval_hours: int = 6
    enable_auto_consolidation: bool = True
    enable_auto_pruning: bool = True


@dataclass
class MemoryStats:
    """
    Statistics about the memory system.

    Attributes:
        total_memories: Total number of memories
        active_memories: Memories above activation threshold
        dormant_memories: Memories below threshold
        budget_status: Current budget status
        last_consolidation: When consolidation last ran
        avg_importance: Average importance score
        avg_activation: Average activation level
    """
    total_memories: int
    active_memories: int
    dormant_memories: int
    budget_status: BudgetStatus
    last_consolidation: datetime | None
    avg_importance: float
    avg_activation: float


class UltraMemorySystem:
    """
    Self-managed cognitive memory system.

    Integrates all ultra memory components into a unified system that:
    - Automatically scores importance on write
    - Tracks activation and decay
    - Maintains multi-graph relationships
    - Runs periodic consolidation
    - Manages storage budget autonomously
    """

    def __init__(
        self,
        db_path: Path,
        config: UltraMemoryConfig | None = None,
    ):
        """
        Initialize ultra memory system.

        Args:
            db_path: Path to memory database
            config: Optional configuration
        """
        self.config = config or UltraMemoryConfig()

        # Core components
        self.store = MemoryStore(db_path)
        self.importance_scorer = ImportanceScorer()
        self.activation_manager = ActivationManager(
            decay_rate=self.config.decay_rate,
            importance_weight=self.config.importance_weight,
            retrieval_threshold=self.config.retrieval_threshold,
        )
        self.multi_graph = MultiGraphStore()
        self.consolidation_engine = ConsolidationEngine()
        self.budget_controller = MemoryBudgetController(
            capacity_limit=self.config.capacity_limit,
        )

        # State tracking
        self.last_consolidation: datetime | None = None
        self._activation_cache: dict[str, ActivationRecord] = {}

    def write(
        self,
        content: str,
        scope: MemoryScope,
        type: MemoryType,
        metadata: dict | None = None,
        user_flagged: bool = False,
    ) -> MemoryRecord:
        """
        Write a memory with automatic importance scoring.

        Args:
            content: Memory content
            scope: Memory scope
            type: Memory type
            metadata: Optional metadata
            user_flagged: Whether user explicitly flagged as important

        Returns:
            Created MemoryRecord with importance score
        """
        metadata = metadata or {}

        # Score importance
        if user_flagged:
            metadata['user_flagged'] = True

        importance_score = self.importance_scorer.score(
            content=content,
            memory_type=type,
            metadata=metadata,
            created_at=datetime.now(),
        )

        # Add importance to metadata
        metadata['importance'] = importance_score.final_score
        metadata['importance_category'] = importance_score.category.value

        # Write to store
        memory = self.store.write(
            content=content,
            scope=scope,
            type=type,
            metadata=metadata,
        )

        # Initialize activation record
        activation_record = ActivationRecord(
            memory_id=memory.id,
            importance=importance_score.final_score,
            created_at=time.time(),
        )
        self._activation_cache[memory.id] = activation_record

        # Check if consolidation or pruning needed
        if self.config.enable_auto_consolidation:
            self._maybe_consolidate()

        if self.config.enable_auto_pruning:
            self._maybe_prune()

        return memory

    def retrieve(
        self,
        query: str,
        scope: MemoryScope | None = None,
        type: MemoryType | None = None,
        top_k: int = 20,
        use_graph: bool = True,
    ) -> list[MemoryRecord]:
        """
        Retrieve memories with activation-based ranking.

        Args:
            query: Search query
            scope: Optional scope filter
            type: Optional type filter
            top_k: Number of results
            use_graph: Whether to use graph traversal

        Returns:
            List of memories ranked by activation
        """
        # Get initial results from store
        results = self.store.retrieve(
            query=query,
            scope=scope,
            type=type,
            limit=top_k * 2,  # Get more for filtering
        )

        # Filter by activation threshold
        accessible_results = []
        now = time.time()

        for memory in results:
            # Get activation record
            activation_record = self._activation_cache.get(memory.id)
            if not activation_record:
                # Create new record
                importance = memory.metadata.get('importance', 0.5)
                activation_record = ActivationRecord(
                    memory_id=memory.id,
                    importance=importance,
                    created_at=memory.created_at.timestamp(),
                )
                self._activation_cache[memory.id] = activation_record

            # Check if accessible
            activation = self.activation_manager.compute_activation(
                memory_id=memory.id,
                importance=activation_record.importance,
                retrieval_history=activation_record.retrieval_history,
                created_at=activation_record.created_at,
                current_time=now,
            )

            if activation > self.config.retrieval_threshold:
                # Update retrieval history
                activation_record.retrieval_history.append(now)
                activation_record.last_accessed = now
                activation_record.access_count += 1

                # Store activation for ranking
                memory.metadata['_activation'] = activation
                accessible_results.append(memory)

        # Sort by activation
        accessible_results.sort(
            key=lambda m: m.metadata.get('_activation', 0.0),
            reverse=True,
        )

        # Optionally expand with graph
        if use_graph and accessible_results:
            graph_results = self._expand_with_graph(accessible_results[:5])
            # Merge and deduplicate
            seen = {m.id for m in accessible_results}
            for mem in graph_results:
                if mem.id not in seen:
                    accessible_results.append(mem)
                    seen.add(mem.id)

        return accessible_results[:top_k]

    def consolidate(self, deep: bool = False) -> ConsolidationResult:
        """
        Run memory consolidation.

        Args:
            deep: Whether to run deep consolidation

        Returns:
            ConsolidationResult with statistics
        """
        # Get all memories
        all_memories = self._get_all_memories()

        if deep:
            result, patterns = self.consolidation_engine.deep_consolidation(
                memories=all_memories,
            )

            # Store discovered patterns as new memories
            for pattern in patterns:
                self.write(
                    content=pattern.description,
                    scope=MemoryScope.GLOBAL,
                    type=MemoryType.SEMANTIC,
                    metadata={
                        'pattern': True,
                        'confidence': pattern.confidence,
                        'source_count': len(pattern.source_memory_ids),
                    },
                )
        else:
            result = self.consolidation_engine.light_consolidation(
                memories=all_memories,
            )

        self.last_consolidation = datetime.now()
        return result

    def get_stats(self) -> MemoryStats:
        """
        Get memory system statistics.

        Returns:
            MemoryStats with current state
        """
        all_memories = self._get_all_memories()
        total = len(all_memories)

        # Count active vs dormant
        active = 0
        dormant = 0
        total_importance = 0.0
        total_activation = 0.0
        now = time.time()

        for memory in all_memories:
            activation_record = self._activation_cache.get(memory.id)
            if activation_record:
                activation = self.activation_manager.compute_activation(
                    memory_id=memory.id,
                    importance=activation_record.importance,
                    retrieval_history=activation_record.retrieval_history,
                    created_at=activation_record.created_at,
                    current_time=now,
                )

                if activation > self.config.retrieval_threshold:
                    active += 1
                else:
                    dormant += 1

                total_importance += activation_record.importance
                total_activation += activation

        # Get budget status
        budget_status = self.budget_controller.check_budget(total)

        return MemoryStats(
            total_memories=total,
            active_memories=active,
            dormant_memories=dormant,
            budget_status=budget_status,
            last_consolidation=self.last_consolidation,
            avg_importance=total_importance / max(1, total),
            avg_activation=total_activation / max(1, total),
        )

    def prune(self, target_count: int | None = None) -> int:
        """
        Prune low-value memories.

        Args:
            target_count: Number to prune (auto-calculated if None)

        Returns:
            Number of memories pruned
        """
        all_memories = self._get_all_memories()

        if target_count is None:
            # Auto-calculate based on budget
            budget_status = self.budget_controller.check_budget(len(all_memories))
            target_count = budget_status.memories_to_prune

        if target_count <= 0:
            return 0

        # Get activation scores
        activation_scores = {}
        now = time.time()
        for memory in all_memories:
            activation_record = self._activation_cache.get(memory.id)
            if activation_record:
                activation = self.activation_manager.compute_activation(
                    memory_id=memory.id,
                    importance=activation_record.importance,
                    retrieval_history=activation_record.retrieval_history,
                    created_at=activation_record.created_at,
                    current_time=now,
                )
                activation_scores[memory.id] = activation

        # Select memories to prune
        to_prune = self.budget_controller.select_memories_to_prune(
            memories=all_memories,
            target_count=target_count,
            activation_scores=activation_scores,
        )

        # Archive them (soft delete)
        for memory_id in to_prune:
            # Mark as archived in metadata
            # In production, would move to cold storage
            if memory_id in self._activation_cache:
                del self._activation_cache[memory_id]

        return len(to_prune)

    def close(self):
        """Close the memory system."""
        self.store.close()

    def _get_all_memories(self) -> list[MemoryRecord]:
        """Get all memories from store."""
        # This is a simplified version
        # In production, would paginate or use cursor
        return self.store.retrieve("", limit=100000)

    def _maybe_consolidate(self):
        """Run consolidation if interval elapsed."""
        if not self.config.enable_auto_consolidation:
            return

        if self.last_consolidation is None:
            return

        hours_since = (datetime.now() - self.last_consolidation).total_seconds() / 3600
        if hours_since >= self.config.consolidation_interval_hours:
            self.consolidate(deep=False)

    def _maybe_prune(self):
        """Prune if budget exceeded."""
        if not self.config.enable_auto_pruning:
            return

        all_memories = self._get_all_memories()
        budget_status = self.budget_controller.check_budget(len(all_memories))

        if budget_status.action_required:
            self.prune()

    def _expand_with_graph(
        self,
        seed_memories: list[MemoryRecord],
    ) -> list[MemoryRecord]:
        """Expand results using graph traversal."""
        expanded_ids = set()

        for memory in seed_memories:
            # Get related memories from graph
            related = self.multi_graph.get_related_memories(
                memory_id=memory.id,
                max_results=5,
            )
            expanded_ids.update(mem_id for mem_id, _ in related)

        # Fetch expanded memories
        # In production, would batch fetch
        expanded = []
        for mem_id in expanded_ids:
            # Would fetch from store
            pass

        return expanded


__all__ = [
    "UltraMemoryConfig",
    "MemoryStats",
    "UltraMemorySystem",
]
