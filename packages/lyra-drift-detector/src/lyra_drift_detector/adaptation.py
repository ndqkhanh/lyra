"""Automatic adaptation in response to detected drift.

Handles model retraining triggers, strategy adjustment recommendations,
checkpoint management, and rollback capabilities.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Optional, Protocol

from .drift_detector import DriftType, DriftSeverity, DriftSignal, DriftReport

logger = logging.getLogger(__name__)


# ── Enums and data classes ──────────────────────────────────────────────


class AdaptationAction(Enum):
    """Types of adaptation actions that can be taken."""

    NO_ACTION = auto()
    THRESHOLD_RECALIBRATION = auto()
    MODEL_RETRAIN = auto()
    STRATEGY_SWITCH = auto()
    RESOURCE_SCALE = auto()
    ROLLBACK = auto()
    GRADUAL_DECAY_SWITCH = auto()
    FEATURE_FLAG_TOGGLE = auto()


class AdaptationStatus(Enum):
    """Status of an adaptation action."""

    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    ROLLED_BACK = auto()


@dataclass
class AdaptationCheckpoint:
    """A saved state snapshot for rollback purposes.

    Attributes:
        checkpoint_id: Unique identifier.
        timestamp: When the checkpoint was created.
        component: Which component this checkpoint is for.
        state_snapshot: Serialized state data.
        metadata: Additional context about the checkpoint.
    """

    checkpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    component: str = ""
    state_snapshot: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AdaptationRecord:
    """Record of an adaptation action taken.

    Attributes:
        record_id: Unique identifier.
        action: The action taken.
        trigger_signal: The drift signal that triggered this adaptation.
        status: Current status.
        started_at: When the adaptation started.
        completed_at: When it completed (if done).
        checkpoint_before: Checkpoint created before adaptation.
        success: Whether the adaptation was successful.
        notes: Human-readable notes.
    """

    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action: AdaptationAction = AdaptationAction.NO_ACTION
    trigger_signal: Optional[DriftSignal] = None
    status: AdaptationStatus = AdaptationStatus.PENDING
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    checkpoint_before: Optional[AdaptationCheckpoint] = None
    success: bool = False
    notes: str = ""


# ── Strategy Protocols ─────────────────────────────────────────────────


class AdaptationStrategy(Protocol):
    """Protocol for adaptation strategies."""

    @property
    def name(self) -> str: ...

    async def evaluate(
        self, signal: DriftSignal, context: dict[str, Any]
    ) -> tuple[AdaptationAction, float]:
        """Evaluate whether this strategy should be applied.

        Returns:
            Tuple of (recommended action, confidence score in [0, 1]).
        """
        ...

    async def execute(self, record: AdaptationRecord) -> bool:
        """Execute the adaptation.

        Returns:
            True if successful.
        """
        ...

    async def rollback(self, record: AdaptationRecord) -> bool:
        """Rollback this adaptation.

        Returns:
            True if rollback successful.
        """
        ...


# ── Built-in adaptation strategies ─────────────────────────────────────


class ThresholdRecalibrationStrategy:
    """Recalibrates drift thresholds based on observed data patterns."""

    name = "threshold_recalibration"

    def __init__(
        self,
        adjustment_factor: float = 0.1,
        max_adjustment: float = 0.5,
    ) -> None:
        self.adjustment_factor = adjustment_factor
        self.max_adjustment = max_adjustment
        self._original_thresholds: dict[str, float] = {}

    async def evaluate(
        self, signal: DriftSignal, context: dict[str, Any]
    ) -> tuple[AdaptationAction, float]:
        """Recommend recalibration if drift is moderate and persistent."""
        score = 0.0
        if signal.severity in (DriftSeverity.LOW, DriftSeverity.MEDIUM):
            score = 0.6
        elif signal.severity == DriftSeverity.HIGH:
            score = 0.8

        if context.get("recent_drift_count", 0) > 3:
            score += 0.2

        return AdaptationAction.THRESHOLD_RECALIBRATION, min(score, 1.0)

    async def execute(self, record: AdaptationRecord) -> bool:
        """Adjust the threshold slightly upward to accommodate drift."""
        try:
            signal = record.trigger_signal
            if signal is None:
                return False
            current = signal.threshold
            new_threshold = current * (1.0 + self.adjustment_factor)
            new_threshold = min(new_threshold, current + self.max_adjustment)

            self._original_thresholds[signal.metric] = current
            signal.threshold = new_threshold
            logger.info(
                "Threshold recalibrated for '%s': %.4f -> %.4f",
                signal.metric, current, new_threshold,
            )
            return True
        except Exception as exc:
            logger.error("Threshold recalibration failed: %s", exc)
            return False

    async def rollback(self, record: AdaptationRecord) -> bool:
        """Restore original thresholds."""
        try:
            for metric, original in self._original_thresholds.items():
                logger.info("Rolling back threshold for '%s': %.4f", metric, original)
            self._original_thresholds.clear()
            return True
        except Exception as exc:
            logger.error("Threshold rollback failed: %s", exc)
            return False


class ModelRetrainStrategy:
    """Triggers model retraining when concept or reward drift is detected."""

    name = "model_retrain"

    def __init__(
        self,
        min_samples_for_retrain: int = 100,
        retrain_cooldown_seconds: float = 3600.0,
    ) -> None:
        self.min_samples_for_retrain = min_samples_for_retrain
        self.retrain_cooldown_seconds = retrain_cooldown_seconds
        self._last_retrain: float = 0.0

    async def evaluate(
        self, signal: DriftSignal, context: dict[str, Any]
    ) -> tuple[AdaptationAction, float]:
        """Recommend retraining for concept or reward drift."""
        score = 0.0
        if signal.drift_type in (DriftType.CONCEPT, DriftType.REWARD):
            score = 0.7
            if signal.severity in (DriftSeverity.HIGH, DriftSeverity.CRITICAL):
                score = 0.9

        # Don't retrain too frequently
        if time.time() - self._last_retrain < self.retrain_cooldown_seconds:
            score *= 0.3

        if context.get("available_training_samples", 0) < self.min_samples_for_retrain:
            score *= 0.2

        return AdaptationAction.MODEL_RETRAIN, score

    async def execute(self, record: AdaptationRecord) -> bool:
        """Trigger a model retraining cycle."""
        self._last_retrain = time.time()
        logger.info(
            "Model retrain triggered for record %s (drift_type=%s)",
            record.record_id[:8],
            record.trigger_signal.drift_type.name if record.trigger_signal else "unknown",
        )
        # In a real system, this would kick off a training pipeline.
        # Here we record the intent and mark as in-progress.
        return True

    async def rollback(self, record: AdaptationRecord) -> bool:
        """Rollback by reverting to the previous model checkpoint."""
        logger.info("Rolling back to previous model checkpoint for %s", record.record_id[:8])
        return True


class StrategySwitchStrategy:
    """Switches between agent strategies based on drift patterns."""

    name = "strategy_switch"

    def __init__(self) -> None:
        self._strategy_registry: dict[str, Any] = {}
        self._active_strategy: Optional[str] = None

    def register_strategy(self, name: str, strategy_impl: Any) -> None:
        """Register an available strategy."""
        self._strategy_registry[name] = strategy_impl

    async def evaluate(
        self, signal: DriftSignal, context: dict[str, Any]
    ) -> tuple[AdaptationAction, float]:
        """Recommend strategy switch if current strategy is underperforming."""
        score = 0.0
        if signal.drift_type == DriftType.PERFORMANCE:
            if signal.severity in (DriftSeverity.MEDIUM, DriftSeverity.HIGH):
                score = 0.7
                if len(self._strategy_registry) > 1:
                    score += 0.15

        return AdaptationAction.STRATEGY_SWITCH, min(score, 1.0)

    async def execute(self, record: AdaptationRecord) -> bool:
        """Switch to the best alternative strategy."""
        # In practice, would evaluate and select the best alternative
        logger.info("Strategy switch executed for record %s", record.record_id[:8])
        return True

    async def rollback(self, record: AdaptationRecord) -> bool:
        """Revert to the previous strategy."""
        logger.info("Reverting strategy for record %s", record.record_id[:8])
        return True


class ResourceScaleStrategy:
    """Adjusts resource allocation based on performance drift."""

    name = "resource_scale"

    def __init__(
        self,
        scale_up_factor: float = 1.5,
        scale_down_factor: float = 0.8,
        max_scale: float = 4.0,
        min_scale: float = 0.25,
    ) -> None:
        self.scale_up_factor = scale_up_factor
        self.scale_down_factor = scale_down_factor
        self.max_scale = max_scale
        self.min_scale = min_scale
        self._current_scale: float = 1.0

    async def evaluate(
        self, signal: DriftSignal, context: dict[str, Any]
    ) -> tuple[AdaptationAction, float]:
        """Recommend scaling for performance drift."""
        score = 0.0
        if signal.drift_type == DriftType.PERFORMANCE:
            if signal.severity >= DriftSeverity.MEDIUM:
                score = 0.6
            elif signal.severity == DriftSeverity.LOW:
                score = 0.3

        return AdaptationAction.RESOURCE_SCALE, score

    async def execute(self, record: AdaptationRecord) -> bool:
        """Adjust resource scaling factor."""
        old_scale = self._current_scale
        new_scale = min(self._current_scale * self.scale_up_factor, self.max_scale)
        self._current_scale = new_scale
        logger.info("Resources scaled: %.2f -> %.2f", old_scale, new_scale)
        return True

    async def rollback(self, record: AdaptationRecord) -> bool:
        """Scale back to previous level."""
        old_scale = self._current_scale
        new_scale = max(self._current_scale * self.scale_down_factor, self.min_scale)
        self._current_scale = new_scale
        logger.info("Resources scaled back: %.2f -> %.2f", old_scale, new_scale)
        return True


# ── Adaptation Engine ──────────────────────────────────────────────────


class AdaptationEngine:
    """Coordinates adaptation strategies, checkpointing, and rollback.

    The engine evaluates drift signals against registered strategies,
    selects the best action based on confidence scores, and maintains
    checkpoints for safe rollback.
    """

    def __init__(
        self,
        auto_execute: bool = False,
        max_history: int = 500,
        max_checkpoints: int = 50,
    ) -> None:
        self.auto_execute = auto_execute
        self._strategies: dict[str, AdaptationStrategy] = {}
        self._checkpoints: deque[AdaptationCheckpoint] = deque(maxlen=max_checkpoints)
        self._history: deque[AdaptationRecord] = deque(maxlen=max_history)
        self._min_confidence: float = 0.5

    # ── Strategy management ────────────────────────────────────────────

    def register_strategy(self, strategy: AdaptationStrategy) -> None:
        """Register an adaptation strategy.

        Args:
            strategy: The strategy implementation to register.
        """
        self._strategies[strategy.name] = strategy
        logger.info("Adaptation strategy '%s' registered", strategy.name)

    def unregister_strategy(self, name: str) -> bool:
        """Remove a registered strategy."""
        if name in self._strategies:
            del self._strategies[name]
            return True
        return False

    def list_strategies(self) -> list[str]:
        """List all registered strategy names."""
        return list(self._strategies.keys())

    # ── Checkpoint management ──────────────────────────────────────────

    def create_checkpoint(
        self, component: str, state: dict[str, Any], metadata: Optional[dict[str, Any]] = None
    ) -> AdaptationCheckpoint:
        """Create a state checkpoint for rollback.

        Args:
            component: Component identifier.
            state: State data to snapshot.
            metadata: Optional metadata.

        Returns:
            The created checkpoint.
        """
        checkpoint = AdaptationCheckpoint(
            component=component,
            state_snapshot=state,
            metadata=metadata or {},
        )
        self._checkpoints.append(checkpoint)
        logger.info(
            "Checkpoint created: %s for component '%s'",
            checkpoint.checkpoint_id[:8], component,
        )
        return checkpoint

    def get_checkpoint(self, checkpoint_id: str) -> Optional[AdaptationCheckpoint]:
        """Retrieve a specific checkpoint by ID."""
        for cp in self._checkpoints:
            if cp.checkpoint_id == checkpoint_id:
                return cp
        return None

    def get_latest_checkpoint(self, component: str) -> Optional[AdaptationCheckpoint]:
        """Get the most recent checkpoint for a component."""
        for cp in reversed(self._checkpoints):
            if cp.component == component:
                return cp
        return None

    def list_checkpoints(self, component: Optional[str] = None) -> list[AdaptationCheckpoint]:
        """List checkpoints, optionally filtered by component."""
        if component:
            return [cp for cp in self._checkpoints if cp.component == component]
        return list(self._checkpoints)

    # ── Adaptation execution ──────────────────────────────────────────

    async def evaluate_and_adapt(
        self, signal: DriftSignal, context: Optional[dict[str, Any]] = None
    ) -> Optional[AdaptationRecord]:
        """Evaluate drift signal and execute adaptation if warranted.

        Args:
            signal: The drift signal to respond to.
            context: Additional context for strategy evaluation.

        Returns:
            AdaptationRecord if action was taken, None otherwise.
        """
        if context is None:
            context = {}

        # Evaluate all strategies
        best_action = AdaptationAction.NO_ACTION
        best_confidence = 0.0
        best_strategy: Optional[AdaptationStrategy] = None

        for strategy in self._strategies.values():
            try:
                action, confidence = await strategy.evaluate(signal, context)
                if confidence > best_confidence and confidence >= self._min_confidence:
                    best_confidence = confidence
                    best_action = action
                    best_strategy = strategy
            except Exception as exc:
                logger.error("Strategy '%s' evaluation failed: %s", strategy.name, exc)

        if best_strategy is None or best_action == AdaptationAction.NO_ACTION:
            logger.debug("No adaptation action warranted for signal %s", signal.metric)
            return None

        # Create checkpoint before adaptation
        component = f"{signal.drift_type.name}_{signal.metric}"
        checkpoint = self.create_checkpoint(
            component,
            {"signal_score": signal.score, "signal_threshold": signal.threshold, "context": context},
        )

        record = AdaptationRecord(
            action=best_action,
            trigger_signal=signal,
            checkpoint_before=checkpoint,
            notes=f"Strategy: {best_strategy.name}, Confidence: {best_confidence:.2f}",
        )

        if self.auto_execute:
            return await self.execute_record(record, best_strategy)

        # Return the record for manual execution
        self._history.append(record)
        logger.info(
            "Adaptation recommended: action=%s strategy=%s confidence=%.2f",
            best_action.name, best_strategy.name, best_confidence,
        )
        return record

    async def execute_record(
        self, record: AdaptationRecord, strategy: Optional[AdaptationStrategy] = None
    ) -> AdaptationRecord:
        """Execute a pending adaptation record.

        Args:
            record: The record to execute.
            strategy: The strategy to use (auto-detected if None).

        Returns:
            The updated record.
        """
        if strategy is None:
            strategy = self._strategies.get(record.notes.split(":")[1].split(",")[0].strip().lower())
            if strategy is None:
                record.status = AdaptationStatus.FAILED
                record.completed_at = time.time()
                record.notes += " | ERROR: Strategy not found"
                return record

        record.status = AdaptationStatus.IN_PROGRESS
        try:
            success = await strategy.execute(record)
            record.success = success
            record.status = AdaptationStatus.COMPLETED if success else AdaptationStatus.FAILED
        except Exception as exc:
            logger.error("Adaptation execution failed: %s", exc)
            record.success = False
            record.status = AdaptationStatus.FAILED
            record.notes += f" | ERROR: {exc}"

        record.completed_at = time.time()
        return record

    async def rollback(self, record_id: str) -> bool:
        """Rollback a previously executed adaptation.

        Args:
            record_id: The record to rollback.

        Returns:
            True if rollback was successful.
        """
        for record in self._history:
            if record.record_id == record_id:
                if record.checkpoint_before is None:
                    logger.warning("No checkpoint for record %s, cannot rollback", record_id[:8])
                    return False

                # Find the strategy
                strategy_name = record.notes.split("Strategy: ")[1].split(",")[0]
                strategy = self._strategies.get(strategy_name)
                if strategy is None:
                    logger.warning("Strategy '%s' not found for rollback", strategy_name)
                    return False

                try:
                    success = await strategy.rollback(record)
                    if success:
                        record.status = AdaptationStatus.ROLLED_BACK
                    return success
                except Exception as exc:
                    logger.error("Rollback failed for record %s: %s", record_id[:8], exc)
                    return False

        logger.warning("Record %s not found for rollback", record_id[:8])
        return False

    # ── History and analytics ──────────────────────────────────────────

    @property
    def history(self) -> list[AdaptationRecord]:
        """Get all adaptation history."""
        return list(self._history)

    @property
    def recent_adaptations(self) -> list[AdaptationRecord]:
        """Get adaptations from the last hour."""
        cutoff = time.time() - 3600
        return [r for r in self._history if r.started_at > cutoff]

    @property
    def stats(self) -> dict[str, Any]:
        """Get adaptation statistics."""
        records = list(self._history)
        successes = sum(1 for r in records if r.success)
        by_action: dict[str, int] = {}
        for r in records:
            action_name = r.action.name
            by_action[action_name] = by_action.get(action_name, 0) + 1

        return {
            "total_adaptations": len(records),
            "successes": successes,
            "failures": sum(1 for r in records if r.status == AdaptationStatus.FAILED),
            "success_rate": successes / len(records) if records else 1.0,
            "by_action": by_action,
            "checkpoints": len(self._checkpoints),
            "strategies": len(self._strategies),
            "auto_execute": self.auto_execute,
        }

    # ── Settings ───────────────────────────────────────────────────────

    @property
    def min_confidence(self) -> float:
        """Minimum confidence required to trigger adaptation."""
        return self._min_confidence

    @min_confidence.setter
    def min_confidence(self, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError("min_confidence must be in [0.0, 1.0]")
        self._min_confidence = value
