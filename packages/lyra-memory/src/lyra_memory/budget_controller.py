"""
Memory budget controller for autonomous memory management.

Manages memory storage capacity and performs intelligent pruning when
limits are approached. Implements tiered budget management with
progressive consolidation and archival strategies.
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

from lyra_memory.schema import MemoryRecord


class BudgetTier(str, Enum):
    """Memory budget tiers."""
    HOT = "hot"        # 0-70% capacity - Normal operation
    WARM = "warm"      # 70-85% capacity - Light consolidation
    COLD = "cold"      # 85-95% capacity - Aggressive pruning
    CRITICAL = "critical"  # 95-100% capacity - Emergency archival


@dataclass
class BudgetStatus:
    """
    Current memory budget status.
    
    Attributes:
        total_memories: Total number of memories
        capacity_limit: Maximum allowed memories
        usage_percent: Current usage percentage
        tier: Current budget tier
        memories_to_prune: Suggested number to prune
        action_required: Whether action is needed
    """
    total_memories: int
    capacity_limit: int
    usage_percent: float
    tier: BudgetTier
    memories_to_prune: int = 0
    action_required: bool = False


@dataclass
class PruneCandidate:
    """
    A memory candidate for pruning.
    
    Attributes:
        memory_id: Memory identifier
        prune_score: Score for pruning (lower = more likely to prune)
        reason: Why this memory is a candidate
    """
    memory_id: str
    prune_score: float
    reason: str


class MemoryBudgetController:
    """
    Controls memory budget and performs autonomous pruning.
    
    Implements tiered budget management:
    - Hot tier (0-70%): Normal operation, no action
    - Warm tier (70-85%): Light consolidation triggered
    - Cold tier (85-95%): Aggressive pruning
    - Critical tier (95-100%): Emergency archival
    """
    
    def __init__(
        self,
        capacity_limit: int = 10000,
        hot_threshold: float = 0.70,
        warm_threshold: float = 0.85,
        cold_threshold: float = 0.95,
        min_importance_for_keep: float = 0.7,
    ):
        """
        Initialize budget controller.
        
        Args:
            capacity_limit: Maximum number of memories
            hot_threshold: Threshold for hot tier (0.0-1.0)
            warm_threshold: Threshold for warm tier
            cold_threshold: Threshold for cold tier
            min_importance_for_keep: Never prune above this importance
        """
        self.capacity_limit = capacity_limit
        self.hot_threshold = hot_threshold
        self.warm_threshold = warm_threshold
        self.cold_threshold = cold_threshold
        self.min_importance_for_keep = min_importance_for_keep
    
    def check_budget(self, total_memories: int) -> BudgetStatus:
        """
        Check current budget status.
        
        Args:
            total_memories: Current number of memories
            
        Returns:
            BudgetStatus with current state
        """
        usage_percent = total_memories / self.capacity_limit
        
        # Determine tier
        if usage_percent < self.hot_threshold:
            tier = BudgetTier.HOT
            action_required = False
            memories_to_prune = 0
        elif usage_percent < self.warm_threshold:
            tier = BudgetTier.WARM
            action_required = True
            # Prune back to 60%
            target = int(self.capacity_limit * 0.60)
            memories_to_prune = max(0, total_memories - target)
        elif usage_percent < self.cold_threshold:
            tier = BudgetTier.COLD
            action_required = True
            # Prune back to 50%
            target = int(self.capacity_limit * 0.50)
            memories_to_prune = max(0, total_memories - target)
        else:
            tier = BudgetTier.CRITICAL
            action_required = True
            # Prune back to 40%
            target = int(self.capacity_limit * 0.40)
            memories_to_prune = max(0, total_memories - target)
        
        return BudgetStatus(
            total_memories=total_memories,
            capacity_limit=self.capacity_limit,
            usage_percent=usage_percent,
            tier=tier,
            memories_to_prune=memories_to_prune,
            action_required=action_required,
        )
    
    def compute_prune_scores(
        self,
        memories: List[MemoryRecord],
        activation_scores: Optional[dict[str, float]] = None,
    ) -> List[PruneCandidate]:
        """
        Compute pruning scores for all memories.
        
        Pruning score formula:
            P = 0.5·A + 0.3·I + 0.2·min(access_count/10, 1) - 0.1·(age/365)
        
        Where:
            A = activation level
            I = importance score
            access_count = number of retrievals
            age = days since creation
        
        Lower scores are pruned first.
        
        Args:
            memories: List of memories to score
            activation_scores: Optional pre-computed activation scores
            
        Returns:
            List of PruneCandidate sorted by score (lowest first)
        """
        activation_scores = activation_scores or {}
        candidates = []
        
        now = time.time()
        
        for memory in memories:
            # Skip critical memories
            importance = getattr(memory, 'importance', 0.5)
            if importance >= self.min_importance_for_keep:
                continue
            
            # Get activation score
            activation = activation_scores.get(memory.id, 0.5)
            
            # Get access count
            access_count = getattr(memory, 'access_count', 0)
            access_factor = min(access_count / 10.0, 1.0)
            
            # Calculate age in days
            created_ts = memory.created_at.timestamp()
            age_days = (now - created_ts) / 86400
            age_penalty = (age_days / 365.0) * 0.1
            
            # Compute prune score
            prune_score = (
                0.5 * activation +
                0.3 * importance +
                0.2 * access_factor -
                age_penalty
            )
            
            # Determine reason
            if activation < 0.3:
                reason = "Low activation (rarely accessed)"
            elif importance < 0.3:
                reason = "Low importance"
            elif age_days > 180:
                reason = "Old and rarely used"
            else:
                reason = "Low overall value"
            
            candidates.append(PruneCandidate(
                memory_id=memory.id,
                prune_score=prune_score,
                reason=reason,
            ))
        
        # Sort by prune score (lowest first)
        candidates.sort(key=lambda c: c.prune_score)
        
        return candidates
    
    def select_memories_to_prune(
        self,
        memories: List[MemoryRecord],
        target_count: int,
        activation_scores: Optional[dict[str, float]] = None,
    ) -> List[str]:
        """
        Select memories to prune to reach target count.
        
        Args:
            memories: List of all memories
            target_count: Number of memories to prune
            activation_scores: Optional activation scores
            
        Returns:
            List of memory IDs to prune
        """
        if target_count <= 0:
            return []
        
        # Compute prune scores
        candidates = self.compute_prune_scores(memories, activation_scores)
        
        # Select bottom N
        to_prune = candidates[:target_count]
        
        return [c.memory_id for c in to_prune]
    
    def get_archival_candidates(
        self,
        memories: List[MemoryRecord],
        min_age_days: int = 30,
        max_access_count: int = 2,
    ) -> List[str]:
        """
        Get memories that should be archived (cold storage).
        
        Archival candidates:
        - Old (> min_age_days)
        - Rarely accessed (< max_access_count)
        - Low importance (< 0.5)
        
        Args:
            memories: List of memories
            min_age_days: Minimum age for archival
            max_access_count: Maximum accesses for archival
            
        Returns:
            List of memory IDs to archive
        """
        now = time.time()
        candidates = []
        
        for memory in memories:
            # Check age
            created_ts = memory.created_at.timestamp()
            age_days = (now - created_ts) / 86400
            
            if age_days < min_age_days:
                continue
            
            # Check access count
            access_count = getattr(memory, 'access_count', 0)
            if access_count > max_access_count:
                continue
            
            # Check importance
            importance = getattr(memory, 'importance', 0.5)
            if importance >= 0.5:
                continue
            
            candidates.append(memory.id)
        
        return candidates
    
    def estimate_storage_bytes(self, memories: List[MemoryRecord]) -> int:
        """
        Estimate total storage bytes for memories.
        
        Args:
            memories: List of memories
            
        Returns:
            Estimated bytes
        """
        total_bytes = 0
        
        for memory in memories:
            # Content
            total_bytes += len(memory.content.encode('utf-8'))
            
            # Metadata (rough estimate)
            total_bytes += 500  # ID, timestamps, etc.
            
            # Embeddings (if present)
            if hasattr(memory, 'embedding') and memory.embedding:
                total_bytes += len(memory.embedding) * 4  # float32
        
        return total_bytes


__all__ = [
    "BudgetTier",
    "BudgetStatus",
    "PruneCandidate",
    "MemoryBudgetController",
]
