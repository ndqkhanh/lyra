"""
Intent Detector

Detects user intent: exploratory vs goal-oriented.
"""

from dataclasses import dataclass
from typing import Dict, Any
from enum import Enum


class IntentType(Enum):
    """User intent types"""
    EXPLORATORY = "exploratory"
    GOAL_ORIENTED = "goal_oriented"


@dataclass
class Intent:
    """Detected intent with confidence"""
    type: IntentType
    confidence: float  # 0.0 to 1.0
    indicators: Dict[str, int]  # Keyword counts


class IntentDetector:
    """
    Detect user intent from query

    Distinguishes between exploratory (learning-focused) and
    goal-oriented (task-focused) queries.
    """

    def __init__(self):
        """Initialize intent detector"""
        # Exploratory indicators
        self.exploratory_keywords = [
            "explore", "understand", "learn about", "what is",
            "how does", "why", "curious", "investigate",
            "explain", "tell me about", "interested in",
            "wondering", "help me understand"
        ]

        # Goal-oriented indicators
        self.goal_keywords = [
            "find", "search", "list", "compare", "best",
            "recommend", "which", "should i", "need to",
            "want to", "looking for", "help me", "show me",
            "get", "obtain", "achieve"
        ]

    def detect(self, query: str, context: Dict[str, Any] = None) -> Intent:
        """
        Detect intent from query

        Args:
            query: User query
            context: Optional context (not used yet)

        Returns:
            Intent with type and confidence
        """
        query_lower = query.lower()

        # Count keyword matches
        exploratory_count = sum(
            1 for kw in self.exploratory_keywords
            if kw in query_lower
        )

        goal_count = sum(
            1 for kw in self.goal_keywords
            if kw in query_lower
        )

        # Calculate confidence
        total_matches = exploratory_count + goal_count
        if total_matches == 0:
            # No clear indicators - default to goal-oriented with low confidence
            return Intent(
                type=IntentType.GOAL_ORIENTED,
                confidence=0.5,
                indicators={"exploratory": 0, "goal": 0}
            )

        # Determine intent type
        if exploratory_count > goal_count:
            intent_type = IntentType.EXPLORATORY
            confidence = exploratory_count / total_matches
        else:
            intent_type = IntentType.GOAL_ORIENTED
            confidence = goal_count / total_matches

        return Intent(
            type=intent_type,
            confidence=confidence,
            indicators={
                "exploratory": exploratory_count,
                "goal": goal_count
            }
        )

    def is_exploratory(self, query: str, threshold: float = 0.5) -> bool:
        """
        Check if query is exploratory

        Args:
            query: User query
            threshold: Confidence threshold

        Returns:
            True if exploratory with confidence >= threshold
        """
        intent = self.detect(query)
        return (
            intent.type == IntentType.EXPLORATORY and
            intent.confidence >= threshold
        )

    def is_goal_oriented(self, query: str, threshold: float = 0.5) -> bool:
        """
        Check if query is goal-oriented

        Args:
            query: User query
            threshold: Confidence threshold

        Returns:
            True if goal-oriented with confidence >= threshold
        """
        intent = self.detect(query)
        return (
            intent.type == IntentType.GOAL_ORIENTED and
            intent.confidence >= threshold
        )
