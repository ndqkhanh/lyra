"""
Tests for monitoring module.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from monitoring.token_observatory import (
    Activity,
    ActivityCategory,
    ActivityClassifier,
    BurnReport,
    TokenObservatory,
    Turn,
    WasteAnalyzer,
    WasteInstance,
    WastePattern,
)


class TestActivityCategory:
    """Tests for ActivityCategory enum."""

    def test_activity_categories(self):
        """Test all activity categories exist."""
        assert ActivityCategory.CODING.value == "coding"
        assert ActivityCategory.DEBUGGING.value == "debugging"
        assert ActivityCategory.REFACTORING.value == "refactoring"
        assert ActivityCategory.TESTING.value == "testing"
        assert ActivityCategory.DOCUMENTATION.value == "documentation"
        assert ActivityCategory.RESEARCH.value == "research"
        assert ActivityCategory.PLANNING.value == "planning"
        assert ActivityCategory.REVIEW.value == "review"
        assert ActivityCategory.CHAT.value == "chat"
        assert ActivityCategory.TOOL_USE.value == "tool_use"
        assert ActivityCategory.ERROR_RECOVERY.value == "error_recovery"
        assert ActivityCategory.EXPLORATION.value == "exploration"
        assert ActivityCategory.OTHER.value == "other"


class TestWastePattern:
    """Tests for WastePattern enum."""

    def test_waste_patterns(self):
        """Test all waste patterns exist."""
        assert WastePattern.REPEATED_ERRORS.value == "repeated_errors"
        assert WastePattern.UNNECESSARY_CONTEXT.value == "unnecessary_context"
        assert WastePattern.OVER_GENERATION.value == "over_generation"
        assert WastePattern.REDUNDANT_REQUESTS.value == "redundant_requests"
        assert WastePattern.INEFFICIENT_MODEL.value == "inefficient_model"
        assert WastePattern.MISSING_CACHE.value == "missing_cache"
        assert WastePattern.EXCESSIVE_RETRIES.value == "excessive_retries"


class TestTurn:
    """Tests for Turn dataclass."""

    def test_turn_creation(self):
        """Test creating a turn."""
        turn = Turn(
            timestamp=datetime.now(),
            role="user",
            content="Test message",
            tokens=100,
            model="claude-sonnet-4.6",
            cost=0.001,
        )

        assert turn.role == "user"
        assert turn.content == "Test message"
        assert turn.tokens == 100
        assert turn.model == "claude-sonnet-4.6"
        assert turn.cost == 0.001
        assert turn.metadata == {}

    def test_turn_with_metadata(self):
        """Test turn with metadata."""
        turn = Turn(
            timestamp=datetime.now(),
            role="assistant",
            content="Response",
            tokens=200,
            model="claude-sonnet-4.6",
            cost=0.002,
            metadata={"tool_use": True, "cached": False},
        )

        assert turn.metadata["tool_use"] is True
        assert turn.metadata["cached"] is False


class TestActivity:
    """Tests for Activity dataclass."""

    def test_activity_creation(self):
        """Test creating an activity."""
        turns = [
            Turn(
                timestamp=datetime.now(),
                role="user",
                content="Write code",
                tokens=50,
                model="claude-sonnet-4.6",
                cost=0.0005,
            )
        ]

        activity = Activity(
            category=ActivityCategory.CODING,
            turns=turns,
            tokens=50,
            cost=0.0005,
            duration=10.0,
            success=True,
        )

        assert activity.category == ActivityCategory.CODING
        assert len(activity.turns) == 1
        assert activity.tokens == 50
        assert activity.cost == 0.0005
        assert activity.duration == 10.0
        assert activity.success is True


class TestWasteInstance:
    """Tests for WasteInstance dataclass."""

    def test_waste_instance_creation(self):
        """Test creating a waste instance."""
        turns = [
            Turn(
                timestamp=datetime.now(),
                role="user",
                content="Test",
                tokens=100,
                model="claude-opus-4.7",
                cost=0.01,
            )
        ]

        waste = WasteInstance(
            pattern=WastePattern.INEFFICIENT_MODEL,
            turns=turns,
            wasted_tokens=0,
            wasted_cost=0.009,
            description="Using Opus for simple task",
            recommendation="Use Haiku for simple tasks",
        )

        assert waste.pattern == WastePattern.INEFFICIENT_MODEL
        assert len(waste.turns) == 1
        assert waste.wasted_tokens == 0
        assert waste.wasted_cost == 0.009
        assert "Opus" in waste.description
        assert "Haiku" in waste.recommendation


class TestActivityClassifier:
    """Tests for ActivityClassifier."""

    def test_classifier_creation(self):
        """Test creating classifier."""
        classifier = ActivityClassifier()

        assert classifier is not None
        assert len(classifier.keywords) == 12

    def test_classify_coding(self):
        """Test classifying coding activity."""
        classifier = ActivityClassifier()

        turn = Turn(
            timestamp=datetime.now(),
            role="user",
            content="Implement a new feature",
            tokens=50,
            model="claude-sonnet-4.6",
            cost=0.0005,
        )

        category = classifier.classify(turn)
        assert category == ActivityCategory.CODING

    def test_classify_debugging(self):
        """Test classifying debugging activity."""
        classifier = ActivityClassifier()

        turn = Turn(
            timestamp=datetime.now(),
            role="user",
            content="Debug this error in the code",
            tokens=50,
            model="claude-sonnet-4.6",
            cost=0.0005,
        )

        category = classifier.classify(turn)
        assert category == ActivityCategory.DEBUGGING

    def test_classify_testing(self):
        """Test classifying testing activity."""
        classifier = ActivityClassifier()

        turn = Turn(
            timestamp=datetime.now(),
            role="user",
            content="Write tests for this function",
            tokens=50,
            model="claude-sonnet-4.6",
            cost=0.0005,
        )

        category = classifier.classify(turn)
        assert category == ActivityCategory.TESTING

    def test_classify_documentation(self):
        """Test classifying documentation activity."""
        classifier = ActivityClassifier()

        turn = Turn(
            timestamp=datetime.now(),
            role="user",
            content="Write documentation for the API",
            tokens=50,
            model="claude-sonnet-4.6",
            cost=0.0005,
        )

        category = classifier.classify(turn)
        assert category == ActivityCategory.DOCUMENTATION

    def test_classify_tool_use(self):
        """Test classifying tool use activity."""
        classifier = ActivityClassifier()

        turn = Turn(
            timestamp=datetime.now(),
            role="user",
            content="Execute the command",
            tokens=50,
            model="claude-sonnet-4.6",
            cost=0.0005,
            metadata={"tool_use": True},
        )

        category = classifier.classify(turn)
        assert category == ActivityCategory.TOOL_USE

    def test_classify_error_recovery(self):
        """Test classifying error recovery activity."""
        classifier = ActivityClassifier()

        turn = Turn(
            timestamp=datetime.now(),
            role="user",
            content="Try again",
            tokens=50,
            model="claude-sonnet-4.6",
            cost=0.0005,
            metadata={"error": True},
        )

        category = classifier.classify(turn)
        assert category == ActivityCategory.ERROR_RECOVERY

    def test_classify_other(self):
        """Test classifying other activity."""
        classifier = ActivityClassifier()

        turn = Turn(
            timestamp=datetime.now(),
            role="user",
            content="Random text",
            tokens=50,
            model="claude-sonnet-4.6",
            cost=0.0005,
        )

        category = classifier.classify(turn)
        assert category == ActivityCategory.OTHER


class TestWasteAnalyzer:
    """Tests for WasteAnalyzer."""

    def test_analyzer_creation(self):
        """Test creating analyzer."""
        analyzer = WasteAnalyzer()

        assert analyzer is not None
        assert len(analyzer.patterns) == 7

    def test_detect_repeated_errors(self):
        """Test detecting repeated errors."""
        analyzer = WasteAnalyzer()

        turns = [
            Turn(
                timestamp=datetime.now(),
                role="user",
                content=f"Attempt {i}",
                tokens=100,
                model="claude-sonnet-4.6",
                cost=0.001,
                metadata={"error": True},
            )
            for i in range(5)
        ]

        waste = analyzer._detect_repeated_errors(turns)

        assert len(waste) == 1
        assert waste[0].pattern == WastePattern.REPEATED_ERRORS
        assert waste[0].wasted_tokens > 0

    def test_detect_unnecessary_context(self):
        """Test detecting unnecessary context."""
        analyzer = WasteAnalyzer()

        turns = [
            Turn(
                timestamp=datetime.now(),
                role="user",
                content="Test",
                tokens=15000,
                model="claude-sonnet-4.6",
                cost=0.045,
            )
        ]

        waste = analyzer._detect_unnecessary_context(turns)

        assert len(waste) == 1
        assert waste[0].pattern == WastePattern.UNNECESSARY_CONTEXT
        assert waste[0].wasted_tokens > 0

    def test_detect_over_generation(self):
        """Test detecting over-generation."""
        analyzer = WasteAnalyzer()

        turns = [
            Turn(
                timestamp=datetime.now(),
                role="assistant",
                content="Long response",
                tokens=3000,
                model="claude-sonnet-4.6",
                cost=0.045,
            )
        ]

        waste = analyzer._detect_over_generation(turns)

        assert len(waste) == 1
        assert waste[0].pattern == WastePattern.OVER_GENERATION
        assert waste[0].wasted_tokens > 0

    def test_detect_redundant_requests(self):
        """Test detecting redundant requests."""
        analyzer = WasteAnalyzer()

        turns = [
            Turn(
                timestamp=datetime.now(),
                role="user",
                content="Same request",
                tokens=100,
                model="claude-sonnet-4.6",
                cost=0.001,
            ),
            Turn(
                timestamp=datetime.now(),
                role="user",
                content="Same request",
                tokens=100,
                model="claude-sonnet-4.6",
                cost=0.001,
            ),
        ]

        waste = analyzer._detect_redundant_requests(turns)

        assert len(waste) == 1
        assert waste[0].pattern == WastePattern.REDUNDANT_REQUESTS

    def test_detect_inefficient_model(self):
        """Test detecting inefficient model usage."""
        analyzer = WasteAnalyzer()

        turns = [
            Turn(
                timestamp=datetime.now(),
                role="user",
                content="Simple task",
                tokens=100,
                model="claude-opus-4.7",
                cost=0.015,
            )
        ]

        waste = analyzer._detect_inefficient_model(turns)

        assert len(waste) == 1
        assert waste[0].pattern == WastePattern.INEFFICIENT_MODEL
        assert waste[0].wasted_cost > 0

    def test_detect_missing_cache(self):
        """Test detecting missing cache opportunities."""
        analyzer = WasteAnalyzer()

        turns = [
            Turn(
                timestamp=datetime.now(),
                role="user",
                content="Large context",
                tokens=2000,
                model="claude-sonnet-4.6",
                cost=0.006,
                metadata={"cached": False},
            )
        ]

        waste = analyzer._detect_missing_cache(turns)

        assert len(waste) == 1
        assert waste[0].pattern == WastePattern.MISSING_CACHE
        assert waste[0].wasted_tokens > 0

    def test_detect_excessive_retries(self):
        """Test detecting excessive retries."""
        analyzer = WasteAnalyzer()

        turns = [
            Turn(
                timestamp=datetime.now(),
                role="user",
                content=f"Retry {i}",
                tokens=100,
                model="claude-sonnet-4.6",
                cost=0.001,
                metadata={"retry": True},
            )
            for i in range(7)
        ]

        waste = analyzer._detect_excessive_retries(turns)

        assert len(waste) == 1
        assert waste[0].pattern == WastePattern.EXCESSIVE_RETRIES
        assert waste[0].wasted_tokens > 0

    def test_find_waste_multiple_patterns(self):
        """Test finding multiple waste patterns."""
        analyzer = WasteAnalyzer()

        turns = [
            # Repeated errors
            Turn(
                timestamp=datetime.now(),
                role="user",
                content=f"Error {i}",
                tokens=100,
                model="claude-sonnet-4.6",
                cost=0.001,
                metadata={"error": True},
            )
            for i in range(5)
        ] + [
            # Large context
            Turn(
                timestamp=datetime.now(),
                role="user",
                content="Large",
                tokens=15000,
                model="claude-sonnet-4.6",
                cost=0.045,
            )
        ]

        waste = analyzer.find_waste(turns)

        assert len(waste) >= 2
        patterns = [w.pattern for w in waste]
        assert WastePattern.REPEATED_ERRORS in patterns
        assert WastePattern.UNNECESSARY_CONTEXT in patterns


class TestTokenObservatory:
    """Tests for TokenObservatory."""

    def test_observatory_creation(self):
        """Test creating observatory."""
        observatory = TokenObservatory()

        assert observatory is not None
        assert observatory.classifier is not None
        assert observatory.analyzer is not None

    def test_parse_jsonl(self, tmp_path):
        """Test parsing JSONL log."""
        observatory = TokenObservatory()

        # Create test log
        log_path = tmp_path / "test.jsonl"
        with open(log_path, "w") as f:
            f.write(
                json.dumps(
                    {
                        "timestamp": "2026-05-22T10:00:00",
                        "role": "user",
                        "content": "Test",
                        "tokens": 100,
                        "model": "claude-sonnet-4.6",
                        "cost": 0.001,
                    }
                )
                + "\n"
            )

        turns = observatory.parse_jsonl(log_path)

        assert len(turns) == 1
        assert turns[0].role == "user"
        assert turns[0].content == "Test"
        assert turns[0].tokens == 100

    def test_analyze_session(self, tmp_path):
        """Test analyzing session."""
        observatory = TokenObservatory()

        # Create test log
        log_path = tmp_path / "session.jsonl"
        with open(log_path, "w") as f:
            for i in range(5):
                f.write(
                    json.dumps(
                        {
                            "timestamp": (
                                datetime.now() + timedelta(seconds=i)
                            ).isoformat(),
                            "role": "user" if i % 2 == 0 else "assistant",
                            "content": f"Message {i}",
                            "tokens": 100,
                            "model": "claude-sonnet-4.6",
                            "cost": 0.001,
                        }
                    )
                    + "\n"
                )

        report = observatory.analyze_session(log_path)

        assert report.session_id == "session"
        assert report.total_tokens == 500
        assert report.total_cost == 0.005
        assert len(report.activities) > 0
        assert 0.0 <= report.one_shot_rate <= 1.0
        assert report.retry_count >= 0

    def test_calculate_one_shot_rate(self):
        """Test calculating one-shot rate."""
        observatory = TokenObservatory()

        turns = [
            Turn(
                timestamp=datetime.now(),
                role="user",
                content="Success",
                tokens=100,
                model="claude-sonnet-4.6",
                cost=0.001,
            ),
            Turn(
                timestamp=datetime.now(),
                role="user",
                content="Error",
                tokens=100,
                model="claude-sonnet-4.6",
                cost=0.001,
                metadata={"error": True},
            ),
            Turn(
                timestamp=datetime.now(),
                role="user",
                content="Success",
                tokens=100,
                model="claude-sonnet-4.6",
                cost=0.001,
            ),
        ]

        rate = observatory._calculate_one_shot_rate(turns)

        assert rate == 2 / 3

    def test_generate_recommendations(self):
        """Test generating recommendations."""
        observatory = TokenObservatory()

        waste = [
            WasteInstance(
                pattern=WastePattern.INEFFICIENT_MODEL,
                turns=[],
                wasted_tokens=0,
                wasted_cost=0.01,
                description="Test",
                recommendation="Use Haiku",
            ),
            WasteInstance(
                pattern=WastePattern.MISSING_CACHE,
                turns=[],
                wasted_tokens=1000,
                wasted_cost=0.003,
                description="Test",
                recommendation="Enable caching",
            ),
        ]

        recommendations = observatory._generate_recommendations(waste)

        assert len(recommendations) == 2
        assert "Use Haiku" in recommendations
        assert "Enable caching" in recommendations

    def test_calculate_model_breakdown(self):
        """Test calculating model breakdown."""
        observatory = TokenObservatory()

        turns = [
            Turn(
                timestamp=datetime.now(),
                role="user",
                content="Test",
                tokens=100,
                model="claude-haiku-4.5",
                cost=0.0001,
            ),
            Turn(
                timestamp=datetime.now(),
                role="user",
                content="Test",
                tokens=200,
                model="claude-sonnet-4.6",
                cost=0.0006,
            ),
            Turn(
                timestamp=datetime.now(),
                role="user",
                content="Test",
                tokens=100,
                model="claude-haiku-4.5",
                cost=0.0001,
            ),
        ]

        breakdown = observatory._calculate_model_breakdown(turns)

        assert "claude-haiku-4.5" in breakdown
        assert "claude-sonnet-4.6" in breakdown
        assert breakdown["claude-haiku-4.5"]["tokens"] == 200
        assert breakdown["claude-sonnet-4.6"]["tokens"] == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
