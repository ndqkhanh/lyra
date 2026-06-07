"""
Trust calibration — calibrates trust in agent decisions based on outcomes.

Provides TrustCalibrator that maintains a dynamic trust model for different
decision contexts, adjusting trust scores up or down based on decision
outcomes and user feedback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ---------------------------------------------------------------------------
# Trust models
# ---------------------------------------------------------------------------


@dataclass
class TrustEntry:
    """A trust assessment for a specific decision context.

    Attributes:
        context: The decision context (e.g. action type, provider).
        trust_score: Current trust in [0, 1] (0 = no trust, 1 = full trust).
        decision_count: Number of decisions contributing to this entry.
        success_count: Number of successful decisions.
        last_updated: When this entry was last updated.
        history: Recent (success, confidence) pairs.
    """

    context: str
    trust_score: float = 0.5
    decision_count: int = 0
    success_count: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    history: list[tuple[bool, float]] = field(default_factory=list)


@dataclass
class DecisionOutcome:
    """Outcome of a single decision.

    Attributes:
        decision_id: Unique identifier.
        context: Decision context string.
        success: Whether the decision led to a good outcome.
        confidence: System confidence at decision time (0-1).
        details: Additional details about the outcome.
        timestamp: When the outcome occurred.
    """

    decision_id: str
    context: str
    success: bool
    confidence: float = 0.5
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# TrustCalibrator
# ---------------------------------------------------------------------------


class TrustCalibrator:
    """Calibrates trust in agent decisions based on historical outcomes.

    Trust is tracked per context (e.g. action type, provider, task domain).
    Positive outcomes increase trust; negative outcomes decrease it.
    The rate of change depends on the severity of the outcome and the
    number of prior observations.
    """

    def __init__(self, learning_rate: float = 0.1, min_observations: int = 3):
        """Initialize TrustCalibrator.

        Args:
            learning_rate: How quickly trust adjusts per outcome.
            min_observations: Minimum outcomes before trust is reliable.
        """
        self._learning_rate = learning_rate
        self._min_observations = min_observations
        self._trust: dict[str, TrustEntry] = {}
        self._outcomes: list[DecisionOutcome] = []

    def record_outcome(
        self,
        context: str,
        success: bool,
        confidence: float = 0.5,
        details: dict[str, Any] | None = None,
    ) -> str:
        """Record a decision outcome and update trust.

        Args:
            context: Decision context (e.g. "tool_call:write_file").
            success: Whether the outcome was successful.
            confidence: System's confidence at decision time.
            details: Optional additional details.

        Returns:
            Decision outcome ID.
        """
        outcome_id = f"outcome_{len(self._outcomes)}"
        outcome = DecisionOutcome(
            decision_id=outcome_id,
            context=context,
            success=success,
            confidence=confidence,
            details=details or {},
        )
        self._outcomes.append(outcome)

        if context not in self._trust:
            self._trust[context] = TrustEntry(context=context)

        entry = self._trust[context]
        entry.decision_count += 1
        if success:
            entry.success_count += 1
        entry.history.append((success, confidence))
        entry.last_updated = datetime.now(timezone.utc)

        # Update trust score
        self._recompute_trust(entry)

        return outcome_id

    def get_trust(self, context: str) -> float:
        """Get current trust score for a context.

        Args:
            context: Decision context.

        Returns:
            Trust score in [0, 1]. Returns 0.5 for unknown contexts.
        """
        entry = self._trust.get(context)
        if entry is None:
            return 0.5  # Neutral trust for unknown contexts
        return entry.trust_score

    def get_trust_level(self, context: str) -> str:
        """Get a human-readable trust level.

        Args:
            context: Decision context.

        Returns:
            One of "high", "medium", "low", or "unknown".
        """
        score = self.get_trust(context)
        if score >= 0.7:
            return "high"
        elif score >= 0.4:
            return "medium"
        elif score > 0.0:
            return "low"
        return "unknown"

    def should_override(self, context: str, confidence: float = 0.5) -> bool:
        """Determine whether the system should override the agent's decision.

        Overrides when trust is low OR when trust is still being established
        and confidence is also low.

        Args:
            context: Decision context.
            confidence: System confidence in the decision.

        Returns:
            True if the decision should be overridden or flagged for review.
        """
        trust = self.get_trust(context)
        entry = self._trust.get(context)

        # Low trust always triggers override
        if trust < 0.3:
            return True

        # Not enough data and low confidence
        if entry is not None and entry.decision_count < self._min_observations:
            if confidence < 0.6:
                return True

        # Medium trust with very low confidence
        if trust < 0.6 and confidence < 0.4:
            return True

        return False

    def get_context_summary(self, context: str) -> TrustEntry | None:
        """Get detailed trust info for a context.

        Args:
            context: Decision context.

        Returns:
            TrustEntry or None if unknown.
        """
        return self._trust.get(context)

    def get_all_contexts(self) -> list[TrustEntry]:
        """Get trust info for all known contexts.

        Returns:
            List of TrustEntry, sorted by context name.
        """
        return sorted(self._trust.values(), key=lambda e: e.context)

    def get_success_rate(self, context: str) -> float:
        """Get the success rate for a context.

        Args:
            context: Decision context.

        Returns:
            Success rate in [0, 1], or 0.5 if unknown.
        """
        entry = self._trust.get(context)
        if entry is None or entry.decision_count == 0:
            return 0.5
        return entry.success_count / entry.decision_count

    def get_outcomes(
        self, context: str | None = None, limit: int = 100
    ) -> list[DecisionOutcome]:
        """Get recent decision outcomes.

        Args:
            context: Optional filter by context.
            limit: Maximum outcomes to return.

        Returns:
            List of recent DecisionOutcome instances.
        """
        if context:
            filtered = [o for o in self._outcomes if o.context == context]
        else:
            filtered = list(self._outcomes)
        return filtered[-limit:]

    def _recompute_trust(self, entry: TrustEntry) -> None:
        """Recompute trust score for a TrustEntry.

        Uses a Bayesian-like update: base rate adjusted by observed outcomes.
        With fewer observations, trust is pulled toward 0.5.
        """
        n = entry.decision_count
        if n == 0:
            entry.trust_score = 0.5
            return

        success_rate = entry.success_count / n

        # Pull toward 0.5 when observations are few
        prior_weight = max(0, self._min_observations - n) / self._min_observations
        adjusted = (1 - prior_weight) * success_rate + prior_weight * 0.5

        entry.trust_score = max(0.0, min(1.0, adjusted))

    def reset_context(self, context: str) -> bool:
        """Reset trust for a specific context to default.

        Args:
            context: Decision context.

        Returns:
            True if the context was found and reset.
        """
        entry = self._trust.get(context)
        if entry is None:
            return False
        entry.trust_score = 0.5
        entry.decision_count = 0
        entry.success_count = 0
        entry.history.clear()
        return True

    def reset_all(self) -> None:
        """Reset all trust entries."""
        self._trust.clear()
        self._outcomes.clear()


__all__ = [
    "TrustEntry",
    "DecisionOutcome",
    "TrustCalibrator",
]
