"""
L1: Short-term Memory Layer - Topic-based grouping with 10-minute TTL.

This layer groups sensory observations by topic and summarizes them
before promoting to episodic memory (L2).
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict


@dataclass
class TopicGroup:
    """A group of related observations."""

    topic_id: str
    topic_name: str
    observations: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    summary: Optional[str] = None
    importance: float = 0.5  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_observation(self, content: str):
        """Add an observation to this topic group."""
        self.observations.append(content)
        self.last_updated = datetime.now().isoformat()

    def get_age_seconds(self) -> float:
        """Get age of this topic group in seconds."""
        created = datetime.fromisoformat(self.created_at)
        return (datetime.now() - created).total_seconds()


class ShortTermMemoryStore:
    """
    Topic-based grouping with short TTL.

    Groups observations by topic and maintains them for ~10 minutes.
    Promotes important groups to episodic memory (L2).
    """

    def __init__(
        self,
        ttl_seconds: int = 600,  # 10 minutes
        max_groups: int = 50,
        promotion_threshold: float = 0.7,
    ):
        self.ttl_seconds = ttl_seconds
        self.max_groups = max_groups
        self.promotion_threshold = promotion_threshold

        self.topic_groups: Dict[str, TopicGroup] = {}
        self.topic_index: Dict[str, List[str]] = defaultdict(list)  # keyword -> topic_ids

        # Statistics
        self.total_observations = 0
        self.total_promotions = 0

    def add_observation(
        self,
        content: str,
        topic_keywords: List[str],
        importance: float = 0.5
    ) -> str:
        """
        Add observation to appropriate topic group.

        Returns the topic_id where observation was added.
        """
        self.total_observations += 1

        # Find or create topic group
        topic_id = self._find_or_create_topic(topic_keywords, importance)

        # Add observation to group
        if topic_id in self.topic_groups:
            self.topic_groups[topic_id].add_observation(content)

        # Cleanup expired groups
        self._cleanup_expired()

        # Check if group should be promoted
        if self._should_promote(topic_id):
            self._mark_for_promotion(topic_id)

        return topic_id

    def _find_or_create_topic(
        self,
        keywords: List[str],
        importance: float
    ) -> str:
        """Find existing topic or create new one."""
        # Try to find existing topic with overlapping keywords
        for keyword in keywords:
            if keyword in self.topic_index:
                # Return first matching topic
                topic_ids = self.topic_index[keyword]
                if topic_ids:
                    return topic_ids[0]

        # Create new topic
        topic_id = f"topic_{len(self.topic_groups):04d}"
        topic_name = "_".join(keywords[:3])  # Use first 3 keywords

        topic_group = TopicGroup(
            topic_id=topic_id,
            topic_name=topic_name,
            importance=importance,
        )

        self.topic_groups[topic_id] = topic_group

        # Index keywords
        for keyword in keywords:
            self.topic_index[keyword].append(topic_id)

        return topic_id

    def _cleanup_expired(self):
        """Remove topic groups older than TTL."""
        expired_ids = []

        for topic_id, group in self.topic_groups.items():
            if group.get_age_seconds() > self.ttl_seconds:
                expired_ids.append(topic_id)

        # Remove expired groups
        for topic_id in expired_ids:
            group = self.topic_groups.pop(topic_id)

            # Remove from index
            for keyword_list in self.topic_index.values():
                if topic_id in keyword_list:
                    keyword_list.remove(topic_id)

    def _should_promote(self, topic_id: str) -> bool:
        """Check if topic group should be promoted to L2."""
        if topic_id not in self.topic_groups:
            return False

        group = self.topic_groups[topic_id]

        # Promote if:
        # 1. High importance
        # 2. Many observations
        # 3. Approaching TTL expiry

        if group.importance >= self.promotion_threshold:
            return True

        if len(group.observations) >= 10:
            return True

        if group.get_age_seconds() > (self.ttl_seconds * 0.8):
            return True

        return False

    def _mark_for_promotion(self, topic_id: str):
        """Mark topic group for promotion to L2."""
        if topic_id in self.topic_groups:
            group = self.topic_groups[topic_id]
            group.metadata["promote_to_l2"] = True
            self.total_promotions += 1

    def get_topic_group(self, topic_id: str) -> Optional[TopicGroup]:
        """Get a topic group by ID."""
        return self.topic_groups.get(topic_id)

    def get_all_groups(self) -> List[TopicGroup]:
        """Get all active topic groups."""
        return list(self.topic_groups.values())

    def get_groups_for_promotion(self) -> List[TopicGroup]:
        """Get topic groups marked for promotion to L2."""
        return [
            group for group in self.topic_groups.values()
            if group.metadata.get("promote_to_l2", False)
        ]

    def summarize_group(self, topic_id: str, summary: str):
        """Add summary to topic group."""
        if topic_id in self.topic_groups:
            self.topic_groups[topic_id].summary = summary

    def search_by_keyword(self, keyword: str) -> List[TopicGroup]:
        """Search topic groups by keyword."""
        topic_ids = self.topic_index.get(keyword, [])
        return [
            self.topic_groups[tid]
            for tid in topic_ids
            if tid in self.topic_groups
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            "total_observations": self.total_observations,
            "total_promotions": self.total_promotions,
            "active_groups": len(self.topic_groups),
            "pending_promotion": len(self.get_groups_for_promotion()),
            "avg_observations_per_group": (
                sum(len(g.observations) for g in self.topic_groups.values()) /
                len(self.topic_groups)
                if self.topic_groups else 0
            ),
        }

    def clear(self):
        """Clear all topic groups."""
        self.topic_groups.clear()
        self.topic_index.clear()
