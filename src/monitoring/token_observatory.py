"""
Token Observatory - Monitor and analyze token usage for cost optimization.

Features:
- 13-category activity classifier
- One-shot rate / retry counter
- Model comparison
- Waste-pattern optimizer
- Git-yield correlation
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ActivityCategory(Enum):
    """Activity categories for token usage classification."""

    CODING = "coding"
    DEBUGGING = "debugging"
    REFACTORING = "refactoring"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    RESEARCH = "research"
    PLANNING = "planning"
    REVIEW = "review"
    CHAT = "chat"
    TOOL_USE = "tool_use"
    ERROR_RECOVERY = "error_recovery"
    EXPLORATION = "exploration"
    OTHER = "other"


class WastePattern(Enum):
    """Waste patterns in token usage."""

    REPEATED_ERRORS = "repeated_errors"
    UNNECESSARY_CONTEXT = "unnecessary_context"
    OVER_GENERATION = "over_generation"
    REDUNDANT_REQUESTS = "redundant_requests"
    INEFFICIENT_MODEL = "inefficient_model"
    MISSING_CACHE = "missing_cache"
    EXCESSIVE_RETRIES = "excessive_retries"


@dataclass
class Turn:
    """A single conversation turn."""

    timestamp: datetime
    role: str
    content: str
    tokens: int
    model: str
    cost: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Activity:
    """Classified activity."""

    category: ActivityCategory
    turns: list[Turn]
    tokens: int
    cost: float
    duration: float
    success: bool


@dataclass
class WasteInstance:
    """Instance of waste pattern."""

    pattern: WastePattern
    turns: list[Turn]
    wasted_tokens: int
    wasted_cost: float
    description: str
    recommendation: str


@dataclass
class BurnReport:
    """Token usage report."""

    session_id: str
    start_time: datetime
    end_time: datetime
    total_tokens: int
    total_cost: float
    activities: list[Activity]
    one_shot_rate: float
    retry_count: int
    waste_patterns: list[WasteInstance]
    recommendations: list[str]
    model_breakdown: dict[str, dict[str, float]]


class ActivityClassifier:
    """
    Classify conversation turns into activity categories.

    Uses keyword matching and pattern recognition to identify
    the type of activity being performed.
    """

    def __init__(self):
        """Initialize activity classifier."""
        self.keywords = {
            ActivityCategory.CODING: [
                "implement",
                "write code",
                "create function",
                "add feature",
                "build",
            ],
            ActivityCategory.DEBUGGING: [
                "debug",
                "fix bug",
                "error",
                "issue",
                "problem",
                "not working",
            ],
            ActivityCategory.REFACTORING: [
                "refactor",
                "clean up",
                "improve",
                "optimize",
                "restructure",
            ],
            ActivityCategory.TESTING: [
                "test",
                "verify",
                "check",
                "validate",
                "coverage",
            ],
            ActivityCategory.DOCUMENTATION: [
                "document",
                "write docs",
                "readme",
                "comment",
                "explain",
            ],
            ActivityCategory.RESEARCH: [
                "research",
                "investigate",
                "explore",
                "find out",
                "learn about",
            ],
            ActivityCategory.PLANNING: [
                "plan",
                "design",
                "architecture",
                "strategy",
                "approach",
            ],
            ActivityCategory.REVIEW: [
                "review",
                "analyze",
                "assess",
                "evaluate",
                "inspect",
            ],
            ActivityCategory.CHAT: ["chat", "discuss", "talk about", "tell me"],
            ActivityCategory.TOOL_USE: [
                "run",
                "execute",
                "call",
                "use tool",
                "invoke",
            ],
            ActivityCategory.ERROR_RECOVERY: [
                "retry",
                "try again",
                "fix error",
                "recover",
            ],
            ActivityCategory.EXPLORATION: [
                "explore",
                "browse",
                "look at",
                "show me",
                "what is",
            ],
        }

    def classify(self, turn: Turn) -> ActivityCategory:
        """
        Classify a turn into an activity category.

        Args:
            turn: Turn to classify

        Returns:
            Activity category
        """
        content_lower = turn.content.lower()

        # Check for keywords
        for category, keywords in self.keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    return category

        # Check metadata
        if "tool_use" in turn.metadata:
            return ActivityCategory.TOOL_USE

        if "error" in turn.metadata:
            return ActivityCategory.ERROR_RECOVERY

        return ActivityCategory.OTHER


class WasteAnalyzer:
    """
    Analyze token usage for waste patterns.

    Identifies inefficiencies and provides recommendations
    for optimization.
    """

    def __init__(self):
        """Initialize waste analyzer."""
        self.patterns = {
            WastePattern.REPEATED_ERRORS: self._detect_repeated_errors,
            WastePattern.UNNECESSARY_CONTEXT: self._detect_unnecessary_context,
            WastePattern.OVER_GENERATION: self._detect_over_generation,
            WastePattern.REDUNDANT_REQUESTS: self._detect_redundant_requests,
            WastePattern.INEFFICIENT_MODEL: self._detect_inefficient_model,
            WastePattern.MISSING_CACHE: self._detect_missing_cache,
            WastePattern.EXCESSIVE_RETRIES: self._detect_excessive_retries,
        }

    def find_waste(self, turns: list[Turn]) -> list[WasteInstance]:
        """
        Find waste patterns in turns.

        Args:
            turns: List of turns to analyze

        Returns:
            List of waste instances
        """
        waste = []

        for _pattern, detector in self.patterns.items():
            instances = detector(turns)
            waste.extend(instances)

        return waste

    def _detect_repeated_errors(self, turns: list[Turn]) -> list[WasteInstance]:
        """Detect repeated errors."""
        waste = []
        error_turns = [t for t in turns if "error" in t.metadata]

        if len(error_turns) > 3:
            wasted_tokens = sum(t.tokens for t in error_turns[3:])
            wasted_cost = sum(t.cost for t in error_turns[3:])

            waste.append(
                WasteInstance(
                    pattern=WastePattern.REPEATED_ERRORS,
                    turns=error_turns,
                    wasted_tokens=wasted_tokens,
                    wasted_cost=wasted_cost,
                    description=f"Repeated errors ({len(error_turns)} times)",
                    recommendation="Review error handling and add validation",
                )
            )

        return waste

    def _detect_unnecessary_context(self, turns: list[Turn]) -> list[WasteInstance]:
        """Detect unnecessary context."""
        waste = []

        for turn in turns:
            if turn.tokens > 10000:
                # Estimate wasted tokens (assume 30% could be compressed)
                wasted_tokens = int(turn.tokens * 0.3)
                wasted_cost = turn.cost * 0.3

                waste.append(
                    WasteInstance(
                        pattern=WastePattern.UNNECESSARY_CONTEXT,
                        turns=[turn],
                        wasted_tokens=wasted_tokens,
                        wasted_cost=wasted_cost,
                        description=f"Large context ({turn.tokens} tokens)",
                        recommendation="Enable context compression",
                    )
                )

        return waste

    def _detect_over_generation(self, turns: list[Turn]) -> list[WasteInstance]:
        """Detect over-generation."""
        waste = []

        for turn in turns:
            if turn.role == "assistant" and turn.tokens > 2000:
                # Estimate wasted tokens (assume 20% over-generation)
                wasted_tokens = int(turn.tokens * 0.2)
                wasted_cost = turn.cost * 0.2

                waste.append(
                    WasteInstance(
                        pattern=WastePattern.OVER_GENERATION,
                        turns=[turn],
                        wasted_tokens=wasted_tokens,
                        wasted_cost=wasted_cost,
                        description=f"Long response ({turn.tokens} tokens)",
                        recommendation="Set appropriate max_tokens limit",
                    )
                )

        return waste

    def _detect_redundant_requests(self, turns: list[Turn]) -> list[WasteInstance]:
        """Detect redundant requests."""
        waste = []
        seen_content = {}

        for turn in turns:
            content_hash = hash(turn.content[:100])

            if content_hash in seen_content:
                prev_turn = seen_content[content_hash]
                wasted_tokens = turn.tokens
                wasted_cost = turn.cost

                waste.append(
                    WasteInstance(
                        pattern=WastePattern.REDUNDANT_REQUESTS,
                        turns=[prev_turn, turn],
                        wasted_tokens=wasted_tokens,
                        wasted_cost=wasted_cost,
                        description="Duplicate request",
                        recommendation="Cache responses or avoid redundant queries",
                    )
                )
            else:
                seen_content[content_hash] = turn

        return waste

    def _detect_inefficient_model(self, turns: list[Turn]) -> list[WasteInstance]:
        """Detect inefficient model usage."""
        waste = []

        for turn in turns:
            # Check if using Opus for simple tasks
            if turn.model == "claude-opus-4.7" and turn.tokens < 500:
                # Estimate savings with Haiku
                haiku_cost = turn.cost * 0.05  # Haiku is ~20x cheaper
                wasted_cost = turn.cost - haiku_cost

                waste.append(
                    WasteInstance(
                        pattern=WastePattern.INEFFICIENT_MODEL,
                        turns=[turn],
                        wasted_tokens=0,
                        wasted_cost=wasted_cost,
                        description=f"Using Opus for simple task ({turn.tokens} tokens)",
                        recommendation="Use Haiku for simple tasks",
                    )
                )

        return waste

    def _detect_missing_cache(self, turns: list[Turn]) -> list[WasteInstance]:
        """Detect missing cache opportunities."""
        waste = []

        for turn in turns:
            if turn.tokens > 1000 and not turn.metadata.get("cached", False):
                # Estimate savings with caching (90% reduction)
                wasted_tokens = int(turn.tokens * 0.9)
                wasted_cost = turn.cost * 0.9

                waste.append(
                    WasteInstance(
                        pattern=WastePattern.MISSING_CACHE,
                        turns=[turn],
                        wasted_tokens=wasted_tokens,
                        wasted_cost=wasted_cost,
                        description=f"Large uncached context ({turn.tokens} tokens)",
                        recommendation="Enable prompt caching",
                    )
                )

        return waste

    def _detect_excessive_retries(self, turns: list[Turn]) -> list[WasteInstance]:
        """Detect excessive retries."""
        waste = []
        retry_turns = [t for t in turns if "retry" in t.metadata]

        if len(retry_turns) > 5:
            wasted_tokens = sum(t.tokens for t in retry_turns[5:])
            wasted_cost = sum(t.cost for t in retry_turns[5:])

            waste.append(
                WasteInstance(
                    pattern=WastePattern.EXCESSIVE_RETRIES,
                    turns=retry_turns,
                    wasted_tokens=wasted_tokens,
                    wasted_cost=wasted_cost,
                    description=f"Excessive retries ({len(retry_turns)} times)",
                    recommendation="Improve error handling and validation",
                )
            )

        return waste


class TokenObservatory:
    """
    Token observatory for monitoring and analyzing token usage.

    Provides insights into token consumption, identifies waste patterns,
    and generates recommendations for optimization.
    """

    def __init__(self):
        """Initialize token observatory."""
        self.classifier = ActivityClassifier()
        self.analyzer = WasteAnalyzer()

    def parse_jsonl(self, log_path: Path) -> list[Turn]:
        """
        Parse JSONL session log.

        Args:
            log_path: Path to JSONL log file

        Returns:
            List of turns
        """
        turns = []

        with open(log_path) as f:
            for line in f:
                data = json.loads(line)

                turn = Turn(
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    role=data["role"],
                    content=data["content"],
                    tokens=data["tokens"],
                    model=data.get("model", "unknown"),
                    cost=data.get("cost", 0.0),
                    metadata=data.get("metadata", {}),
                )

                turns.append(turn)

        return turns

    def analyze_session(self, session_log: Path) -> BurnReport:
        """
        Analyze session token usage.

        Args:
            session_log: Path to session log file

        Returns:
            Burn report with analysis
        """
        # Parse log
        turns = self.parse_jsonl(session_log)

        if not turns:
            raise ValueError("No turns found in session log")

        # Calculate basic metrics
        total_tokens = sum(t.tokens for t in turns)
        total_cost = sum(t.cost for t in turns)

        # Classify activities
        activities = self._group_activities(turns)

        # Calculate one-shot rate
        one_shot_rate = self._calculate_one_shot_rate(turns)

        # Count retries
        retry_count = len([t for t in turns if "retry" in t.metadata])

        # Find waste patterns
        waste_patterns = self.analyzer.find_waste(turns)

        # Generate recommendations
        recommendations = self._generate_recommendations(waste_patterns)

        # Model breakdown
        model_breakdown = self._calculate_model_breakdown(turns)

        return BurnReport(
            session_id=session_log.stem,
            start_time=turns[0].timestamp,
            end_time=turns[-1].timestamp,
            total_tokens=total_tokens,
            total_cost=total_cost,
            activities=activities,
            one_shot_rate=one_shot_rate,
            retry_count=retry_count,
            waste_patterns=waste_patterns,
            recommendations=recommendations,
            model_breakdown=model_breakdown,
        )

    def _group_activities(self, turns: list[Turn]) -> list[Activity]:
        """Group turns into activities."""
        activities = []
        current_activity = None
        current_turns = []

        for turn in turns:
            category = self.classifier.classify(turn)

            if current_activity != category:
                # Save previous activity
                if current_turns:
                    activities.append(
                        Activity(
                            category=current_activity,
                            turns=current_turns,
                            tokens=sum(t.tokens for t in current_turns),
                            cost=sum(t.cost for t in current_turns),
                            duration=(
                                current_turns[-1].timestamp
                                - current_turns[0].timestamp
                            ).total_seconds(),
                            success="error" not in current_turns[-1].metadata,
                        )
                    )

                # Start new activity
                current_activity = category
                current_turns = [turn]
            else:
                current_turns.append(turn)

        # Save last activity
        if current_turns:
            activities.append(
                Activity(
                    category=current_activity,
                    turns=current_turns,
                    tokens=sum(t.tokens for t in current_turns),
                    cost=sum(t.cost for t in current_turns),
                    duration=(
                        current_turns[-1].timestamp - current_turns[0].timestamp
                    ).total_seconds(),
                    success="error" not in current_turns[-1].metadata,
                )
            )

        return activities

    def _calculate_one_shot_rate(self, turns: list[Turn]) -> float:
        """Calculate one-shot success rate."""
        user_turns = [t for t in turns if t.role == "user"]
        successful_turns = [
            t for t in user_turns if "error" not in t.metadata and "retry" not in t.metadata
        ]

        if not user_turns:
            return 0.0

        return len(successful_turns) / len(user_turns)

    def _generate_recommendations(
        self, waste_patterns: list[WasteInstance]
    ) -> list[str]:
        """Generate recommendations from waste patterns."""
        recommendations = set()

        for waste in waste_patterns:
            recommendations.add(waste.recommendation)

        return sorted(recommendations)

    def _calculate_model_breakdown(
        self, turns: list[Turn]
    ) -> dict[str, dict[str, float]]:
        """Calculate token and cost breakdown by model."""
        breakdown = {}

        for turn in turns:
            if turn.model not in breakdown:
                breakdown[turn.model] = {"tokens": 0, "cost": 0.0}

            breakdown[turn.model]["tokens"] += turn.tokens
            breakdown[turn.model]["cost"] += turn.cost

        return breakdown
