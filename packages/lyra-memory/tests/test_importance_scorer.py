"""
Tests for importance scoring system.
"""

from datetime import datetime

import pytest

from lyra_memory.importance_scorer import (
    ImportanceCategory,
    ImportanceScorer,
)
from lyra_memory.schema import MemoryType


class TestImportanceScorer:
    """Test importance scoring functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scorer = ImportanceScorer()

    def test_critical_preference_scoring(self):
        """Test that user preferences get high importance."""
        score = self.scorer.score(
            content="My name is Alice and I prefer TypeScript over JavaScript",
            memory_type=MemoryType.PREFERENCE,
        )

        assert score.final_score >= 0.9
        assert score.category == ImportanceCategory.CRITICAL

    def test_noise_filtering(self):
        """Test that greetings get low importance."""
        score = self.scorer.score(
            content="Hello! How are you?",
            memory_type=MemoryType.EPISODIC,
        )

        assert score.final_score <= 0.3
        assert score.category == ImportanceCategory.NOISE

    def test_emotional_salience_boost(self):
        """Test that emotional content gets boosted."""
        score = self.scorer.score(
            content=(
                "The authentication system keeps failing and I'm really frustrated with debugging"
                "this issue"
            ),
            memory_type=MemoryType.FAILURE,
        )

        assert score.emotional_salience > 0.0
        # FAILURE type already gets high base score, emotional salience adds to it
        assert score.final_score > 0.3  # Should be boosted above noise level

    def test_user_flag_boost(self):
        """Test that user-flagged memories get boosted."""
        score = self.scorer.score(
            content=(
                "The deployment process requires running npm build followed by npm run deploy to"
                "production"
            ),
            memory_type=MemoryType.PROCEDURAL,
            metadata={"user_flagged": True},
        )

        assert score.user_flag_boost == 0.2
        assert score.final_score >= 0.9  # Procedural + user flag should be very high

    def test_recency_boost(self):
        """Test that recent memories get temporary boost."""
        score = self.scorer.score(
            content="Just learned something new",
            memory_type=MemoryType.SEMANTIC,
            created_at=datetime.now(),
        )

        assert score.recency_boost > 0.0

    def test_failure_memory_importance(self):
        """Test that failures get high importance."""
        score = self.scorer.score(
            content="Deployment failed due to missing environment variable",
            memory_type=MemoryType.FAILURE,
        )

        assert score.final_score >= 0.8

    def test_procedural_memory_importance(self):
        """Test that procedures get high importance."""
        score = self.scorer.score(
            content="To deploy: run npm build, then npm run deploy",
            memory_type=MemoryType.PROCEDURAL,
        )

        assert score.final_score >= 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
