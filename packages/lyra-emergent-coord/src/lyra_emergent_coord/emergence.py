"""Emergent behavior detection: pattern recognition, novelty detection, and strategy amplification."""

from __future__ import annotations

import logging
import math
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class EmergenceError(Exception):
    """Base exception for emergence-related errors."""


class InsufficientDataError(EmergenceError):
    """Raised when there is not enough data for emergence detection."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return uuid4().hex[:12]


def _now() -> float:
    return time.monotonic()


# ---------------------------------------------------------------------------
# Dataclass models
# ---------------------------------------------------------------------------


@dataclass
class InteractionPattern:
    """A detected pattern in agent interactions.

    Attributes:
        pattern_id: Unique pattern identifier.
        agents_involved: Agents participating in the pattern.
        pattern_type: Category of the pattern (cooperation, competition, specialization).
        frequency: How often the pattern occurs (count).
        confidence: 0.0-1.0 confidence that this is a real pattern.
        first_observed: When the pattern was first seen.
        last_observed: When the pattern was most recently seen.
        metadata: Additional pattern data.
    """

    pattern_id: str = field(default_factory=_new_id)
    agents_involved: list[str] = field(default_factory=list)
    pattern_type: str = "unknown"
    frequency: int = 0
    confidence: float = 0.0
    first_observed: float = field(default_factory=_now)
    last_observed: float = field(default_factory=_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_significant(self) -> bool:
        """Pattern is significant if it appears frequently with high confidence."""
        return self.frequency >= 3 and self.confidence >= 0.3

    @property
    def recency(self) -> float:
        """How recently was this pattern observed (seconds ago)."""
        return _now() - self.last_observed


@dataclass
class EmergentBehavior:
    """An identified emergent behavior in the agent colony.

    Attributes:
        behavior_id: Unique behavior identifier.
        name: Human-readable name.
        description: Description of the emergent behavior.
        source_patterns: Underlying patterns that combined to produce this.
        complexity: How complex the behavior is (1-10).
        utility: Estimated utility of the behavior (0.0-1.0).
        stability: How stable/reproducible the behavior is.
        detected_at: When it was first detected.
        metadata: Additional behavior data.
    """

    behavior_id: str = field(default_factory=_new_id)
    name: str = ""
    description: str = ""
    source_patterns: list[str] = field(default_factory=list)
    complexity: int = 1
    utility: float = 0.0
    stability: float = 0.0
    detected_at: float = field(default_factory=_now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class NoveltyScore:
    """Quantifies how novel an agent behavior is.

    Attributes:
        agent_id: Which agent.
        behavior_signature: Hash or embedding of the behavior.
        novelty: 0.0 (common) to 1.0 (entirely novel).
        surprise: How unexpected the behavior was.
        timestamp: When the novelty was detected.
    """

    agent_id: str
    behavior_signature: str
    novelty: float = 0.0
    surprise: float = 0.0
    timestamp: float = field(default_factory=_now)


# ---------------------------------------------------------------------------
# Emergence Detector
# ---------------------------------------------------------------------------


class EmergenceDetector:
    """Detects emergent behaviors through interaction pattern analysis,
    novelty detection, and strategy amplification.

    Monitors agent interactions to identify:
    - Recurring interaction patterns (cooperation, competition, specialization)
    - Novel behaviors that deviate from established patterns
    - Emergent strategies that produce better-than-expected outcomes
    - Metrics quantifying the degree of emergent coordination
    """

    def __init__(
        self,
        *,
        pattern_min_frequency: int = 3,
        novelty_threshold: float = 0.7,
        emergence_threshold: float = 0.5,
        history_window: int = 10_000,
    ) -> None:
        self._pattern_min_frequency = pattern_min_frequency
        self._novelty_threshold = novelty_threshold
        self._emergence_threshold = emergence_threshold
        self._history_window = history_window

        # Interaction history
        self._interactions: list[dict[str, Any]] = []
        self._interaction_pairs: dict[tuple[str, str], int] = defaultdict(int)

        # Detected patterns and behaviors
        self._patterns: dict[str, InteractionPattern] = {}
        self._emergent_behaviors: dict[str, EmergentBehavior] = {}
        self._novelty_scores: list[NoveltyScore] = []

        # Behavior signatures for novelty detection
        self._behavior_history: dict[str, list[str]] = defaultdict(list)

        # Strategy tracking
        self._strategy_performance: dict[str, list[float]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Interaction recording
    # ------------------------------------------------------------------

    def record_interaction(
        self,
        from_agent: str,
        to_agent: str,
        interaction_type: str,
        outcome: dict[str, Any] | None = None,
    ) -> None:
        """Record an interaction between two agents."""
        entry = {
            "from": from_agent,
            "to": to_agent,
            "type": interaction_type,
            "outcome": outcome or {},
            "timestamp": _now(),
        }
        self._interactions.append(entry)
        self._interaction_pairs[(from_agent, to_agent)] += 1

        # Prune history
        if len(self._interactions) > self._history_window:
            self._interactions = self._interactions[-self._history_window:]

    # ------------------------------------------------------------------
    # Pattern detection
    # ------------------------------------------------------------------

    def detect_patterns(self) -> list[InteractionPattern]:
        """Analyze interaction history and detect recurring patterns.

        Categories: cooperation (bidirectional exchanges), competition
        (conflicting interactions), specialization (repeated task types).
        """
        if len(self._interactions) < self._pattern_min_frequency:
            return []

        # Detect cooperation patterns (bidirectional interaction pairs)
        new_patterns: list[InteractionPattern] = []
        coop_pairs = self._find_bidirectional_pairs()
        for pair, count in coop_pairs.items():
            if count >= self._pattern_min_frequency:
                pattern = self._get_or_create_pattern(
                    agents=list(pair),
                    pattern_type="cooperation",
                    frequency=count,
                    confidence=min(1.0, count / 10),
                )
                new_patterns.append(pattern)

        # Detect specialization (agents repeatedly doing the same task type)
        specialization = self._find_specialization()
        for agent_id, (task_type, count) in specialization.items():
            if count >= self._pattern_min_frequency:
                pattern = self._get_or_create_pattern(
                    agents=[agent_id],
                    pattern_type="specialization",
                    frequency=count,
                    confidence=min(1.0, count / 5),
                    metadata={"task_type": task_type},
                )
                new_patterns.append(pattern)

        return new_patterns

    def _find_bidirectional_pairs(self) -> dict[tuple[str, str], int]:
        """Find agent pairs with bidirectional interaction."""
        pairs: dict[tuple[str, str], int] = {}
        for (a, b), count in self._interaction_pairs.items():
            reverse_count = self._interaction_pairs.get((b, a), 0)
            if reverse_count > 0:
                key = tuple(sorted([a, b]))  # type: ignore[arg-type]
                pairs[key] = count + reverse_count
        return pairs

    def _find_specialization(self) -> dict[str, tuple[str, int]]:
        """Find agents specializing in particular task types."""
        task_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for interaction in self._interactions:
            task_type = interaction.get("type", "unknown")
            task_counts[interaction["from"]][task_type] += 1

        specialization: dict[str, tuple[str, int]] = {}
        for agent_id, tasks in task_counts.items():
            if len(tasks) >= 2:
                continue  # generalist
            dominant = max(tasks, key=tasks.get)  # type: ignore[arg-type]
            specialization[agent_id] = (dominant, tasks[dominant])
        return specialization

    def _get_or_create_pattern(
        self,
        agents: list[str],
        pattern_type: str,
        frequency: int,
        confidence: float,
        metadata: dict[str, Any] | None = None,
    ) -> InteractionPattern:
        """Get existing pattern or create a new one for overlapping agents."""
        # Check for existing overlapping pattern
        for pid, pattern in self._patterns.items():
            if (
                pattern.pattern_type == pattern_type
                and set(agents) & set(pattern.agents_involved)
            ):
                pattern.frequency = max(pattern.frequency, frequency)
                pattern.last_observed = _now()
                pattern.confidence = max(pattern.confidence, confidence)
                return pattern

        # Create new
        pattern = InteractionPattern(
            agents_involved=agents,
            pattern_type=pattern_type,
            frequency=frequency,
            confidence=confidence,
            metadata=metadata or {},
        )
        self._patterns[pattern.pattern_id] = pattern
        return pattern

    # ------------------------------------------------------------------
    # Emergent strategy identification
    # ------------------------------------------------------------------

    def identify_emergent_strategies(self) -> list[EmergentBehavior]:
        """Identify emergent strategies from observed patterns.

        An emergent strategy is a combination of patterns that produces
        outcomes better than what individual agents could achieve.
        """
        detected: list[EmergentBehavior] = []

        # Look for patterns that co-occur
        significant = [p for p in self._patterns.values() if p.is_significant]
        if len(significant) < 2:
            return detected

        # Check for pattern combinations
        for i, p1 in enumerate(significant):
            for p2 in significant[i + 1 :]:
                # Patterns involving overlapping agents are more likely to be emergent
                overlap = set(p1.agents_involved) & set(p2.agents_involved)
                if not overlap:
                    continue

                behavior = EmergentBehavior(
                    name=f"{p1.pattern_type}-{p2.pattern_type} synergy",
                    description=f"Emergent coordination between {p1.pattern_type} and {p2.pattern_type} patterns",
                    source_patterns=[p1.pattern_id, p2.pattern_id],
                    complexity=min(10, p1.frequency + p2.frequency),
                    utility=(p1.confidence + p2.confidence) / 2,
                    stability=min(p1.confidence, p2.confidence),
                )
                self._emergent_behaviors[behavior.behavior_id] = behavior
                detected.append(behavior)

        return detected

    # ------------------------------------------------------------------
    # Novelty detection
    # ------------------------------------------------------------------

    def record_behavior(self, agent_id: str, behavior_signature: str) -> NoveltyScore:
        """Record an agent behavior and compute its novelty."""
        history = self._behavior_history.get(agent_id, [])
        novelty = 1.0
        surprise = 0.0

        if history:
            # Novelty: how different from past behaviors
            matches = sum(1 for b in history if self._signature_similarity(b, behavior_signature) > 0.5)
            novelty = 1.0 - (matches / len(history))

            # Surprise: how unexpected given recent behavior
            recent = history[-5:]
            recent_matches = sum(1 for b in recent if self._signature_similarity(b, behavior_signature) > 0.3)
            expected = recent_matches / max(len(recent), 1)
            surprise = abs(1.0 - novelty - expected)

        score = NoveltyScore(
            agent_id=agent_id,
            behavior_signature=behavior_signature,
            novelty=novelty,
            surprise=surprise,
        )
        self._novelty_scores.append(score)

        # Update history
        history.append(behavior_signature)
        if len(history) > 100:
            history = history[-100:]
        self._behavior_history[agent_id] = history

        if novelty >= self._novelty_threshold:
            logger.info("Novel behavior detected: agent %s (novelty=%.2f)", agent_id, novelty)

        return score

    def get_novel_behaviors(
        self,
        threshold: float | None = None,
        limit: int = 20,
    ) -> list[NoveltyScore]:
        """Return recent behaviors with high novelty."""
        thresh = threshold or self._novelty_threshold
        novel = [n for n in self._novelty_scores if n.novelty >= thresh]
        novel.sort(key=lambda n: n.novelty, reverse=True)
        return novel[-limit:]

    @staticmethod
    def _signature_similarity(a: str, b: str) -> float:
        """Compute simple similarity between two behavior signatures."""
        if not a or not b:
            return 0.0
        # Jaccard-like: shared bigrams / total bigrams
        bigrams_a = set(a[i : i + 2] for i in range(len(a) - 1))
        bigrams_b = set(b[i : i + 2] for i in range(len(b) - 1))
        if not bigrams_a or not bigrams_b:
            return 0.0
        intersection = bigrams_a & bigrams_b
        union = bigrams_a | bigrams_b
        return len(intersection) / len(union)

    # ------------------------------------------------------------------
    # Strategy amplification
    # ------------------------------------------------------------------

    def record_strategy_outcome(self, strategy_id: str, score: float) -> None:
        """Record the outcome of a strategy for amplification decisions."""
        self._strategy_performance[strategy_id].append(score)
        if len(self._strategy_performance[strategy_id]) > 100:
            self._strategy_performance[strategy_id] = self._strategy_performance[strategy_id][-100:]

    def amplify_strategies(self) -> list[str]:
        """Identify strategies to amplify based on performance.

        Returns strategy IDs that should be promoted/amplified.
        """
        to_amplify: list[str] = []
        for sid, scores in self._strategy_performance.items():
            if len(scores) < 5:
                continue
            avg = sum(scores) / len(scores)
            if avg >= self._emergence_threshold:
                # Check if performance is trending up
                recent_avg = sum(scores[-5:]) / 5 if len(scores) >= 5 else avg
                if recent_avg >= avg - 1e-10:
                    to_amplify.append(sid)
                    logger.info("Amplifying strategy %s (avg=%.2f, recent=%.2f)", sid, avg, recent_avg)

        return to_amplify

    # ------------------------------------------------------------------
    # Emergence metrics
    # ------------------------------------------------------------------

    def compute_emergence_metrics(self) -> dict[str, Any]:
        """Compute metrics quantifying the degree of emergent coordination."""
        patterns = self.detect_patterns()
        strategies = self.identify_emergent_strategies()

        # Pattern diversity
        unique_types = len(set(p.pattern_type for p in self._patterns.values()))
        total_patterns = len(self._patterns)

        # Novelty rate
        recent_scores = self._novelty_scores[-100:] if self._novelty_scores else []
        novelty_rate = sum(1 for n in recent_scores if n.novelty >= self._novelty_threshold) / max(len(recent_scores), 1)

        # Emergence score: composite measure
        emergence_score = (
            (total_patterns / max(1, total_patterns)) * 0.3
            + (novelty_rate) * 0.3
            + (len(strategies) / max(1, len(strategies) + 5)) * 0.4
        )

        return {
            "total_patterns": total_patterns,
            "unique_pattern_types": unique_types,
            "significant_patterns": len(patterns),
            "emergent_behaviors": len(strategies),
            "novelty_rate": novelty_rate,
            "emergence_score": emergence_score,
            "amplified_strategies": self.amplify_strategies(),
        }

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_pattern(self, pattern_id: str) -> InteractionPattern | None:
        """Retrieve a pattern by ID."""
        return self._patterns.get(pattern_id)

    def get_behavior(self, behavior_id: str) -> EmergentBehavior | None:
        """Retrieve an emergent behavior by ID."""
        return self._emergent_behaviors.get(behavior_id)

    def get_patterns_by_type(self, pattern_type: str) -> list[InteractionPattern]:
        """Retrieve all patterns of a given type."""
        return [p for p in self._patterns.values() if p.pattern_type == pattern_type]

    def snapshot(self) -> dict[str, Any]:
        """Return current state snapshot."""
        return {
            "total_patterns": len(self._patterns),
            "emergent_behaviors": len(self._emergent_behaviors),
            "total_interactions": len(self._interactions),
            "novel_behaviors": len(self.get_novel_behaviors()),
            "emergence_metrics": self.compute_emergence_metrics(),
        }
