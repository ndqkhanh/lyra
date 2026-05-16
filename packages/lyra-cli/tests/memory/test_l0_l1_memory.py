"""Tests for L0 Sensory Memory and L1 Short-term Memory."""

import pytest
from datetime import datetime, timedelta

from lyra_cli.memory.l0_sensory import SensoryObservation, SensoryMemoryStore
from lyra_cli.memory.l1_shortterm import TopicGroup, ShortTermMemoryStore


class TestL0SensoryMemory:
    """Tests for L0 Sensory Memory Layer."""

    def test_add_observation(self):
        """Test adding observations."""
        store = SensoryMemoryStore()

        obs = SensoryObservation(
            observation_id="obs_001",
            content="User asked about Python",
            timestamp=datetime.now().isoformat(),
            source="user",
            relevance_score=0.8,
        )

        result = store.add_observation(obs)
        assert result is True
        assert len(store.observations) == 1

    def test_filter_duplicate(self):
        """Test duplicate filtering."""
        store = SensoryMemoryStore()

        obs1 = SensoryObservation(
            observation_id="obs_001",
            content="Same content",
            timestamp=datetime.now().isoformat(),
            source="user",
            relevance_score=0.8,
        )

        obs2 = SensoryObservation(
            observation_id="obs_002",
            content="Same content",
            timestamp=datetime.now().isoformat(),
            source="user",
            relevance_score=0.8,
        )

        assert store.add_observation(obs1) is True
        assert store.add_observation(obs2) is False  # Duplicate
        assert len(store.observations) == 1

    def test_filter_too_short(self):
        """Test filtering short content."""
        store = SensoryMemoryStore(min_length=10)

        obs = SensoryObservation(
            observation_id="obs_001",
            content="Hi",  # Too short
            timestamp=datetime.now().isoformat(),
            source="user",
            relevance_score=0.8,
        )

        result = store.add_observation(obs)
        assert result is False
        assert obs.filter_reason == "too_short"

    def test_filter_system_noise(self):
        """Test filtering system noise."""
        store = SensoryMemoryStore()

        obs = SensoryObservation(
            observation_id="obs_001",
            content="Loading... please wait",
            timestamp=datetime.now().isoformat(),
            source="system",
            relevance_score=0.8,
        )

        result = store.add_observation(obs)
        assert result is False
        assert obs.filter_reason == "system_noise"

    def test_filter_low_relevance(self):
        """Test filtering low relevance."""
        store = SensoryMemoryStore(min_relevance=0.5)

        obs = SensoryObservation(
            observation_id="obs_001",
            content="Some content here",
            timestamp=datetime.now().isoformat(),
            source="user",
            relevance_score=0.2,  # Too low
        )

        result = store.add_observation(obs)
        assert result is False
        assert obs.filter_reason == "low_relevance"

    def test_get_stats(self):
        """Test statistics."""
        store = SensoryMemoryStore(min_relevance=0.0)  # Accept all relevance scores

        # Add some observations
        for i in range(10):
            obs = SensoryObservation(
                observation_id=f"obs_{i:03d}",
                content=f"This is content number {i}",  # Longer content
                timestamp=datetime.now().isoformat(),
                source="user",
                relevance_score=0.8,
            )
            store.add_observation(obs)

        stats = store.get_stats()
        assert stats["total_received"] == 10
        assert stats["total_kept"] == 10
        assert stats["filter_rate"] == 0.0

    def test_filter_rate(self):
        """Test filter rate calculation."""
        store = SensoryMemoryStore()

        # Add 5 good observations
        for i in range(5):
            obs = SensoryObservation(
                observation_id=f"obs_{i:03d}",
                content=f"Good content {i}",
                timestamp=datetime.now().isoformat(),
                source="user",
                relevance_score=0.8,
            )
            store.add_observation(obs)

        # Add 5 bad observations (too short)
        for i in range(5):
            obs = SensoryObservation(
                observation_id=f"obs_{i+5:03d}",
                content="Hi",
                timestamp=datetime.now().isoformat(),
                source="user",
                relevance_score=0.8,
            )
            store.add_observation(obs)

        stats = store.get_stats()
        assert stats["total_received"] == 10
        assert stats["total_filtered"] == 5
        assert stats["filter_rate"] == 0.5


class TestL1ShortTermMemory:
    """Tests for L1 Short-term Memory Layer."""

    def test_add_observation(self):
        """Test adding observations."""
        store = ShortTermMemoryStore()

        topic_id = store.add_observation(
            content="User asked about Python",
            topic_keywords=["python", "programming"],
            importance=0.8,
        )

        assert topic_id is not None
        assert len(store.topic_groups) == 1

    def test_topic_grouping(self):
        """Test that related observations are grouped."""
        store = ShortTermMemoryStore()

        # Add observations with same keywords
        topic_id1 = store.add_observation(
            content="Python is great",
            topic_keywords=["python"],
            importance=0.8,
        )

        topic_id2 = store.add_observation(
            content="Python has good libraries",
            topic_keywords=["python"],
            importance=0.8,
        )

        # Should be in same topic
        assert topic_id1 == topic_id2
        assert len(store.topic_groups) == 1

        group = store.get_topic_group(topic_id1)
        assert len(group.observations) == 2

    def test_promotion_by_importance(self):
        """Test promotion based on importance."""
        store = ShortTermMemoryStore(promotion_threshold=0.7)

        topic_id = store.add_observation(
            content="Important observation",
            topic_keywords=["important"],
            importance=0.9,  # High importance
        )

        promoted = store.get_groups_for_promotion()
        assert len(promoted) == 1
        assert promoted[0].topic_id == topic_id

    def test_promotion_by_count(self):
        """Test promotion based on observation count."""
        store = ShortTermMemoryStore()

        topic_id = None
        # Add 10 observations to same topic
        for i in range(10):
            topic_id = store.add_observation(
                content=f"Observation {i}",
                topic_keywords=["test"],
                importance=0.5,
            )

        promoted = store.get_groups_for_promotion()
        assert len(promoted) == 1
        assert promoted[0].topic_id == topic_id

    def test_search_by_keyword(self):
        """Test searching by keyword."""
        store = ShortTermMemoryStore()

        store.add_observation(
            content="Python content",
            topic_keywords=["python"],
            importance=0.5,
        )

        store.add_observation(
            content="JavaScript content",
            topic_keywords=["javascript"],
            importance=0.5,
        )

        results = store.search_by_keyword("python")
        assert len(results) == 1
        assert "python" in results[0].topic_name

    def test_get_stats(self):
        """Test statistics."""
        store = ShortTermMemoryStore()

        # Add observations
        for i in range(5):
            store.add_observation(
                content=f"Content {i}",
                topic_keywords=["test"],
                importance=0.5,
            )

        stats = store.get_stats()
        assert stats["total_observations"] == 5
        assert stats["active_groups"] >= 1
