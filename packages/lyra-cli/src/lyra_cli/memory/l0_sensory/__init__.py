"""
L0: Sensory Memory Layer - Fast noise filtering with 95% reduction.

This layer acts as the first filter for incoming observations, aggressively
removing noise and irrelevant information before passing to short-term memory.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import deque


@dataclass
class SensoryObservation:
    """A raw observation from the environment."""

    observation_id: str
    content: str
    timestamp: str
    source: str  # "user", "tool", "system", etc.
    metadata: Dict[str, Any] = field(default_factory=dict)
    relevance_score: float = 0.0  # 0.0 to 1.0
    filtered: bool = False
    filter_reason: Optional[str] = None


class SensoryMemoryStore:
    """
    Fast, aggressive noise filtering layer.

    Filters out:
    - Duplicate observations
    - Low-information content (too short, repetitive)
    - System noise (status messages, progress bars)
    - Irrelevant tool outputs

    Retention: Very short (seconds to minutes)
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 300,  # 5 minutes
        min_relevance: float = 0.1,
        min_length: int = 10,
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.min_relevance = min_relevance
        self.min_length = min_length

        # Use deque for fast FIFO operations
        self.observations: deque = deque(maxlen=max_size)
        self.seen_hashes: set = set()  # For duplicate detection

        # Statistics
        self.total_received = 0
        self.total_filtered = 0
        self.filter_reasons: Dict[str, int] = {}

    def add_observation(
        self,
        observation: SensoryObservation
    ) -> bool:
        """
        Add observation with aggressive filtering.

        Returns True if observation was kept, False if filtered.
        """
        self.total_received += 1

        # Filter 1: Duplicate detection
        content_hash = hash(observation.content)
        if content_hash in self.seen_hashes:
            observation.filtered = True
            observation.filter_reason = "duplicate"
            self._record_filter("duplicate")
            return False

        # Filter 2: Too short (likely noise)
        if len(observation.content.strip()) < self.min_length:
            observation.filtered = True
            observation.filter_reason = "too_short"
            self._record_filter("too_short")
            return False

        # Filter 3: System noise patterns
        if self._is_system_noise(observation.content):
            observation.filtered = True
            observation.filter_reason = "system_noise"
            self._record_filter("system_noise")
            return False

        # Filter 4: Low relevance score
        if observation.relevance_score < self.min_relevance:
            observation.filtered = True
            observation.filter_reason = "low_relevance"
            self._record_filter("low_relevance")
            return False

        # Filter 5: Repetitive content
        if self._is_repetitive(observation.content):
            observation.filtered = True
            observation.filter_reason = "repetitive"
            self._record_filter("repetitive")
            return False

        # Passed all filters - keep it
        self.observations.append(observation)
        self.seen_hashes.add(content_hash)

        # Cleanup old observations
        self._cleanup_expired()

        return True

    def _is_system_noise(self, content: str) -> bool:
        """Detect system noise patterns."""
        noise_patterns = [
            "...",
            "loading",
            "processing",
            "please wait",
            "█",  # Progress bar characters
            "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",  # Spinner characters
        ]

        content_lower = content.lower()
        return any(pattern in content_lower for pattern in noise_patterns)

    def _is_repetitive(self, content: str) -> bool:
        """Detect repetitive content."""
        # Check if content is mostly repeated characters
        if len(content) < 20:
            return False

        # Count unique characters
        unique_ratio = len(set(content)) / len(content)
        return unique_ratio < 0.3  # Less than 30% unique characters

    def _cleanup_expired(self):
        """Remove observations older than TTL."""
        if not self.observations:
            return

        cutoff_time = datetime.now() - timedelta(seconds=self.ttl_seconds)

        # Remove from front (oldest) until we hit non-expired
        while self.observations:
            oldest = self.observations[0]
            obs_time = datetime.fromisoformat(oldest.timestamp)

            if obs_time < cutoff_time:
                removed = self.observations.popleft()
                # Remove from seen hashes
                self.seen_hashes.discard(hash(removed.content))
            else:
                break

    def _record_filter(self, reason: str):
        """Record filter statistics."""
        self.total_filtered += 1
        self.filter_reasons[reason] = self.filter_reasons.get(reason, 0) + 1

    def get_recent(self, limit: int = 100) -> List[SensoryObservation]:
        """Get recent non-filtered observations."""
        return list(self.observations)[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get filtering statistics."""
        total_kept = len(self.observations)
        filter_rate = (
            self.total_filtered / self.total_received
            if self.total_received > 0
            else 0.0
        )

        return {
            "total_received": self.total_received,
            "total_filtered": self.total_filtered,
            "total_kept": total_kept,
            "filter_rate": filter_rate,
            "current_size": len(self.observations),
            "filter_reasons": self.filter_reasons,
        }

    def clear(self):
        """Clear all observations."""
        self.observations.clear()
        self.seen_hashes.clear()

    def set_relevance_threshold(self, threshold: float):
        """Update minimum relevance threshold."""
        self.min_relevance = max(0.0, min(1.0, threshold))
