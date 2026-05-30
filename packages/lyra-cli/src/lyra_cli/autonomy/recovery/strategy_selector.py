"""Recovery Strategy Selector - Selects optimal recovery strategy based on error patterns."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lyra_cli.autonomy.recovery.pattern_recognizer import ErrorCategory, ErrorPattern


class RecoveryAction(StrEnum):
    """Possible recovery actions."""

    RETRY = "retry"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    FALLBACK = "fallback"
    REPLAN = "replan"
    ESCALATE = "escalate"
    ABORT = "abort"
    IGNORE = "ignore"
    ROLLBACK = "rollback"


@dataclass(frozen=True)
class RecoveryStrategy:
    """A recovery strategy with configuration."""

    action: RecoveryAction
    category: ErrorCategory
    max_retries: int = 3
    backoff_base_ms: int = 1000
    backoff_factor: float = 2.0
    fallback_operation: str | None = None
    reason: str = ""


class StrategySelector:
    """Selects optimal recovery strategy based on error classification.

    Features:
    - Category-based strategy mapping
    - History-informed strategy selection
    - Pattern-based recovery suggestions
    - Fallback chain management
    """

    def __init__(self):
        self._success_history: dict[str, int] = {}  # {strategy_key: success_count}
        self._failure_history: dict[str, int] = {}  # {strategy_key: failure_count}

    def select(
        self,
        error: Exception,
        category: ErrorCategory,
        pattern: ErrorPattern | None = None,
        attempt: int = 0,
    ) -> RecoveryStrategy:
        """Select the best recovery strategy.

        Args:
            error: The exception
            category: Error category
            pattern: Recognized error pattern (if any)
            attempt: Current attempt number

        Returns:
            RecoveryStrategy
        """
        # If we have a known pattern with a successful history
        if pattern and pattern.occurrence_count > 5:
            action = self._get_best_action_for_pattern(pattern)
            if action:
                return RecoveryStrategy(
                    action=action,
                    category=category,
                    reason=f"Known pattern (seen {pattern.occurrence_count}x)",
                )

        # Category-based strategy
        strategies = {
            ErrorCategory.TRANSIENT: RecoveryAction.RETRY_WITH_BACKOFF,
            ErrorCategory.TIMEOUT: RecoveryAction.RETRY_WITH_BACKOFF,
            ErrorCategory.PERMANENT: RecoveryAction.ESCALATE,
            ErrorCategory.DEPENDENCY: RecoveryAction.FALLBACK,
            ErrorCategory.RESOURCE: RecoveryAction.RETRY_WITH_BACKOFF,
            ErrorCategory.LOGIC: RecoveryAction.REPLAN,
            ErrorCategory.PERMISSION: RecoveryAction.ESCALATE,
            ErrorCategory.VALIDATION: RecoveryAction.FALLBACK,
            ErrorCategory.UNKNOWN: RecoveryAction.ESCALATE,
        }

        action = strategies.get(category, RecoveryAction.ESCALATE)

        # Escalate on too many retries
        max_retries = 3
        if action in (RecoveryAction.RETRY, RecoveryAction.RETRY_WITH_BACKOFF):
            if attempt >= max_retries:
                action = RecoveryAction.ESCALATE
                reason = f"Max retries ({max_retries}) exceeded"
            else:
                reason = f"Retry attempt {attempt + 1}/{max_retries}"
        else:
            reason = f"Category-based strategy for {category.value}"

        return RecoveryStrategy(
            action=action,
            category=category,
            max_retries=3,
            reason=reason,
        )

    def record_success(self, category: ErrorCategory, action: RecoveryAction) -> None:
        """Record a successful recovery."""
        key = f"{category.value}:{action.value}"
        self._success_history[key] = self._success_history.get(key, 0) + 1

    def record_failure(self, category: ErrorCategory, action: RecoveryAction) -> None:
        """Record a failed recovery."""
        key = f"{category.value}:{action.value}"
        self._failure_history[key] = self._failure_history.get(key, 0) + 1

    def get_success_rate(self, category: ErrorCategory, action: RecoveryAction) -> float:
        """Get success rate for a strategy."""
        key = f"{category.value}:{action.value}"
        successes = self._success_history.get(key, 0)
        failures = self._failure_history.get(key, 0)
        total = successes + failures
        return successes / total if total > 0 else 0.0

    def _get_best_action_for_pattern(self, pattern: ErrorPattern) -> RecoveryAction | None:
        """Find best action for known pattern."""
        best_action = None
        best_rate = 0.0

        for action in RecoveryAction:
            rate = self.get_success_rate(pattern.category, action)
            if rate > best_rate:
                best_rate = rate
                best_action = action

        if best_action and best_rate > 0.5:
            return best_action
        return None

    def get_fallback_chain(self, primary: RecoveryAction) -> list[RecoveryAction]:
        """Get fallback chain for a primary action."""
        chains = {
            RecoveryAction.RETRY: [
                RecoveryAction.RETRY_WITH_BACKOFF,
                RecoveryAction.FALLBACK,
                RecoveryAction.REPLAN,
            ],
            RecoveryAction.RETRY_WITH_BACKOFF: [
                RecoveryAction.FALLBACK,
                RecoveryAction.REPLAN,
                RecoveryAction.ESCALATE,
            ],
            RecoveryAction.FALLBACK: [
                RecoveryAction.REPLAN,
                RecoveryAction.ESCALATE,
            ],
            RecoveryAction.REPLAN: [
                RecoveryAction.ESCALATE,
            ],
        }
        return chains.get(primary, [RecoveryAction.ESCALATE])
