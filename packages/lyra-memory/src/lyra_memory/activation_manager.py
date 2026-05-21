"""
ACT-R-inspired activation and decay manager.

Implements the ACT-R (Adaptive Control of Thought-Rational) base-level
activation equation with retrieval strengthening. Based on 40+ years of
cognitive architecture research from Carnegie Mellon.

Key principles:
1. Memories decay over time (power law)
2. Retrieval strengthens activation
3. Importance provides baseline boost
4. Memories below threshold become inaccessible
"""

import math
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ActivationRecord:
    """
    Activation state for a memory.
    
    Tracks retrieval history and computes ACT-R activation.
    
    Attributes:
        memory_id: ID of the memory this tracks
        importance: Base importance score (0.0-1.0)
        retrieval_history: Timestamps of all retrievals
        created_at: When memory was created
        last_accessed: Last retrieval timestamp
        access_count: Total number of retrievals
    """
    memory_id: str
    importance: float = 0.5
    retrieval_history: List[float] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_accessed: float = 0.0
    access_count: int = 0
    
    def __post_init__(self):
        """Initialize last_accessed if not set."""
        if self.last_accessed == 0.0:
            self.last_accessed = self.created_at


class ActivationManager:
    """
    Manages memory activation using ACT-R principles.
    
    ACT-R Base-Level Activation Formula:
        A(t) = ln(Σ t_i^(-d)) + β·I + ε
    
    Where:
        t_i = time since i-th retrieval
        d = decay rate (default 0.5)
        β = importance weight (default 2.0)
        I = importance score
        ε = noise term (default 0.0)
    
    Memories below the retrieval threshold become inaccessible (soft delete).
    """
    
    def __init__(
        self,
        decay_rate: float = 0.5,
        importance_weight: float = 2.0,
        retrieval_threshold: float = -1.0,
        noise: float = 0.0,
    ):
        """
        Initialize activation manager.
        
        Args:
            decay_rate: Power law decay parameter (typically 0.5)
            importance_weight: Weight for importance boost
            retrieval_threshold: Minimum activation for accessibility
            noise: Random noise term (for stochastic retrieval)
        """
        self.decay_rate = decay_rate
        self.importance_weight = importance_weight
        self.retrieval_threshold = retrieval_threshold
        self.noise = noise
        
        # In-memory activation cache
        self._activation_cache: dict[str, ActivationRecord] = {}
    
    def compute_activation(
        self,
        memory_id: str,
        importance: float = 0.5,
        retrieval_history: Optional[List[float]] = None,
        created_at: Optional[float] = None,
        current_time: Optional[float] = None,
    ) -> float:
        """
        Compute current activation level for a memory.
        
        Args:
            memory_id: Memory identifier
            importance: Importance score (0.0-1.0)
            retrieval_history: List of retrieval timestamps
            created_at: When memory was created
            current_time: Current timestamp (defaults to now)
            
        Returns:
            Activation level (can be negative)
        """
        now = current_time if current_time is not None else time.time()
        retrieval_history = retrieval_history or []
        created_at = created_at or now
        
        # If never retrieved, use creation time as single "retrieval"
        if not retrieval_history:
            retrieval_history = [created_at]
        
        # Compute base-level activation: ln(Σ t_i^(-d))
        activation_sum = 0.0
        for retrieval_time in retrieval_history:
            time_since = now - retrieval_time
            if time_since > 0:
                activation_sum += time_since ** (-self.decay_rate)
        
        # Handle edge case: no valid retrievals
        if activation_sum <= 0:
            base_activation = -10.0  # Very low activation
        else:
            base_activation = math.log(activation_sum)
        
        # Importance boost: β·I
        importance_boost = self.importance_weight * importance
        
        # Final activation
        activation = base_activation + importance_boost + self.noise
        
        return activation
    
    def is_accessible(
        self,
        memory_id: str,
        importance: float = 0.5,
        retrieval_history: Optional[List[float]] = None,
        created_at: Optional[float] = None,
        current_time: Optional[float] = None,
    ) -> bool:
        """
        Check if memory is above retrieval threshold.
        
        Args:
            memory_id: Memory identifier
            importance: Importance score
            retrieval_history: List of retrieval timestamps
            created_at: When memory was created
            current_time: Current timestamp
            
        Returns:
            True if memory is accessible (above threshold)
        """
        activation = self.compute_activation(
            memory_id=memory_id,
            importance=importance,
            retrieval_history=retrieval_history,
            created_at=created_at,
            current_time=current_time,
        )
        return activation > self.retrieval_threshold
    
    def on_retrieval(
        self,
        memory_id: str,
        importance: float = 0.5,
        retrieval_time: Optional[float] = None,
    ) -> ActivationRecord:
        """
        Update activation state when memory is retrieved.
        
        Args:
            memory_id: Memory identifier
            importance: Current importance score
            retrieval_time: When retrieval occurred (defaults to now)
            
        Returns:
            Updated ActivationRecord
        """
        now = retrieval_time if retrieval_time is not None else time.time()
        
        # Get or create activation record
        if memory_id in self._activation_cache:
            record = self._activation_cache[memory_id]
        else:
            record = ActivationRecord(
                memory_id=memory_id,
                importance=importance,
                created_at=now,
            )
            self._activation_cache[memory_id] = record
        
        # Update retrieval history
        record.retrieval_history.append(now)
        record.last_accessed = now
        record.access_count += 1
        record.importance = importance  # Update importance
        
        return record
    
    def get_activation_record(self, memory_id: str) -> Optional[ActivationRecord]:
        """Get activation record for a memory."""
        return self._activation_cache.get(memory_id)
    
    def set_activation_record(self, record: ActivationRecord) -> None:
        """Store activation record."""
        self._activation_cache[record.memory_id] = record
    
    def compute_decay_factor(
        self,
        age_seconds: float,
        importance: float = 0.5,
    ) -> float:
        """
        Compute decay factor for a memory of given age.
        
        Returns value between 0.0 (fully decayed) and 1.0 (no decay).
        High importance memories decay slower.
        
        Args:
            age_seconds: Age of memory in seconds
            importance: Importance score (0.0-1.0)
            
        Returns:
            Decay factor (0.0-1.0)
        """
        if age_seconds <= 0:
            return 1.0
        
        # Base decay: t^(-d)
        base_decay = age_seconds ** (-self.decay_rate)
        
        # Importance slows decay
        importance_factor = 1.0 + importance * self.importance_weight
        
        # Combined decay (normalized to 0-1 range)
        decay_factor = base_decay * importance_factor
        
        # Clamp to [0, 1]
        return min(1.0, max(0.0, decay_factor))
    
    def find_dormant_memories(
        self,
        memory_records: List[tuple[str, float, List[float], float]],
        current_time: Optional[float] = None,
    ) -> List[str]:
        """
        Find memories that have fallen below retrieval threshold.
        
        Args:
            memory_records: List of (memory_id, importance, retrieval_history, created_at)
            current_time: Current timestamp
            
        Returns:
            List of memory IDs that are dormant (below threshold)
        """
        dormant = []
        
        for memory_id, importance, retrieval_history, created_at in memory_records:
            if not self.is_accessible(
                memory_id=memory_id,
                importance=importance,
                retrieval_history=retrieval_history,
                created_at=created_at,
                current_time=current_time,
            ):
                dormant.append(memory_id)
        
        return dormant
    
    def clear_cache(self) -> None:
        """Clear activation cache."""
        self._activation_cache.clear()


__all__ = [
    "ActivationRecord",
    "ActivationManager",
]
