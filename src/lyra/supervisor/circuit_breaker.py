"""
ConfidenceCircuitBreaker — monitors session confidence and trips when
consecutive low-confidence steps exceed a threshold.

Prevents cascading failures by pausing, falling back, or aborting
sessions that have entered a low-confidence spiral.

CircuitState transitions::

    CLOSED ──(trip)──> OPEN ──(timeout)──> HALF_OPEN
      ^                                        │
      └──────────(recovery)────────────────────┘
      ^                                        │
      └──────────(manual_reset)────────────────┘

Usage::

    breaker = ConfidenceCircuitBreaker(trip_threshold=3, auto_reset_minutes=5)
    breaker.monitor_loop("session-1")   # runs in background thread
    health = breaker.session_health("session-1")  # check state
    breaker.trip("session-1", TripAction.PAUSE_AND_ASK)
"""

from __future__ import annotations

import datetime
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CircuitState(str, Enum):
    """Current state of the circuit breaker for a session.

    CLOSED (normal):       Confidence is healthy; steps proceed normally.
    OPEN (tripped):        Confidence has dropped below threshold; action
                           is being taken (pause, fallback, or abort).
    HALF_OPEN (recovery):  After auto-reset timeout; a single test step
                           is allowed. If it passes, the circuit closes.
    """

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class TripAction(str, Enum):
    """What action to take when the circuit breaker trips.

    PAUSE_AND_ASK:   Pause the session and escalate to a human.
    FALLBACK_MODEL:  Switch to a fallback model (e.g. Haiku -> Opus).
    ABORT_SESSION:   Abort the session entirely.
    """

    PAUSE_AND_ASK = "pause_and_ask"
    FALLBACK_MODEL = "fallback_model"
    ABORT_SESSION = "abort_session"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LoopHealth:
    """Health snapshot of a monitored session loop.

    Attributes:
        session_id: The session being monitored.
        circuit_state: Current circuit breaker state.
        consecutive_low: Number of consecutive low-confidence steps.
        last_confidence: The most recent confidence score (0.0-1.0).
        trip_count: Total number of times the breaker has tripped.
        last_trip_at: When the last trip occurred, or None.
        auto_reset_at: When auto-reset will transition to HALF_OPEN, or None.
        action: The active TripAction if tripped, or None.
    """

    session_id: str
    circuit_state: CircuitState
    consecutive_low: int
    last_confidence: float
    trip_count: int
    last_trip_at: datetime.datetime | None = None
    auto_reset_at: datetime.datetime | None = None
    action: TripAction | None = None


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Configuration for the confidence circuit breaker.

    Attributes:
        trip_threshold: Number of consecutive low-confidence steps before tripping.
        low_confidence_threshold: Confidence score below this is "low" (0.0-1.0).
        auto_reset_minutes: Minutes after trip before auto-reset to HALF_OPEN.
            Set to 0 to disable auto-reset (manual intervention only).
        max_trips: Maximum number of trips before abort is forced.
        default_action: The default TripAction when no specific action is provided.
    """

    trip_threshold: int = 3
    low_confidence_threshold: float = 0.4
    auto_reset_minutes: int = 5
    max_trips: int = 5
    default_action: TripAction = TripAction.PAUSE_AND_ASK


# ---------------------------------------------------------------------------
# ConfidenceCircuitBreaker
# ---------------------------------------------------------------------------


class ConfidenceCircuitBreaker:
    """Monitors session confidence and trips when consecutive low-confidence
    steps exceed the configured threshold.

    Thread-safe: all mutable state is guarded by a lock.
    """

    def __init__(
        self,
        config: CircuitBreakerConfig | None = None,
        on_trip: Callable[[str, TripAction], None] | None = None,
        on_reset: Callable[[str], None] | None = None,
    ) -> None:
        """
        Args:
            config: Circuit breaker configuration. Uses defaults if not provided.
            on_trip: Optional callback invoked when a circuit trips.
                Receives ``(session_id, action)``.
            on_reset: Optional callback invoked when a circuit resets.
                Receives ``(session_id)``.
        """
        self._config = config or CircuitBreakerConfig()
        self._on_trip = on_trip
        self._on_reset = on_reset
        self._lock = threading.Lock()

        # Per-session state
        self._states: dict[str, CircuitState] = {}
        self._consecutive_low: dict[str, int] = {}
        self._last_confidence: dict[str, float] = {}
        self._trip_counts: dict[str, int] = {}
        self._last_trip_at: dict[str, datetime.datetime] = {}
        self._last_step_at: dict[str, datetime.datetime] = {}
        self._actions: dict[str, TripAction] = {}
        self._background_threads: dict[str, threading.Thread] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_step(self, session_id: str, confidence: float) -> None:
        """Record a confidence score for a session step.

        If the circuit is HALF_OPEN and confidence is healthy, the circuit
        resets to CLOSED. If HALF_OPEN and confidence is low, it re-opens.

        Args:
            session_id: The session identifier.
            confidence: Confidence score (0.0 to 1.0).
        """
        is_low = confidence < self._config.low_confidence_threshold
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        with self._lock:
            self._last_confidence[session_id] = confidence
            self._last_step_at[session_id] = now

            if session_id not in self._states:
                self._states[session_id] = CircuitState.CLOSED
                self._consecutive_low[session_id] = 0
                self._trip_counts[session_id] = 0

            current_state = self._states[session_id]

            if current_state == CircuitState.HALF_OPEN:
                if is_low:
                    # Re-trip immediately
                    self._do_trip(session_id, now)
                else:
                    # Recovery successful — close the circuit
                    self._do_reset(session_id, now)
                return

            if current_state == CircuitState.OPEN:
                # While open, just track confidence but don't change state
                # (monitor_loop will handle auto-reset timing)
                self._consecutive_low[session_id] = (
                    self._consecutive_low[session_id] + 1 if is_low else 0
                )
                return

            # CLOSED state
            if is_low:
                self._consecutive_low[session_id] += 1
                if self._consecutive_low[session_id] >= self._config.trip_threshold:
                    self._do_trip(session_id, now)
            else:
                self._consecutive_low[session_id] = 0

    def monitor_loop(self, session_id: str) -> LoopHealth:
        """Check the health of a monitored session.

        An auto-reset check is performed: if the circuit is OPEN and the
        auto-reset duration has elapsed, the state transitions to HALF_OPEN.

        Args:
            session_id: The session to check.

        Returns:
            A LoopHealth snapshot for the session.
        """
        now = datetime.datetime.now(tz=datetime.timezone.utc)

        with self._lock:
            state = self._states.get(session_id, CircuitState.CLOSED)
            last_trip = self._last_trip_at.get(session_id)

            # Auto-reset: OPEN -> HALF_OPEN after timeout
            if (
                state == CircuitState.OPEN
                and self._config.auto_reset_minutes > 0
                and last_trip is not None
            ):
                elapsed = (now - last_trip).total_seconds()
                if elapsed >= self._config.auto_reset_minutes * 60:
                    self._states[session_id] = CircuitState.HALF_OPEN
                    self._consecutive_low[session_id] = 0
                    state = CircuitState.HALF_OPEN
                    logger.info(
                        "circuit_auto_reset",
                        session_id=session_id,
                        elapsed_minutes=round(elapsed / 60, 1),
                    )

            health = self._build_health(session_id, state, now)

        return health

    def trip(
        self,
        session_id: str,
        action: TripAction | None = None,
    ) -> None:
        """Manually trip a circuit breaker for a session.

        Args:
            session_id: The session to trip.
            action: Action to take. Uses config default if not provided.
        """
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        with self._lock:
            self._do_trip(session_id, now, action)

    def reset(self, session_id: str) -> None:
        """Manually reset a tripped circuit breaker.

        Args:
            session_id: The session to reset.
        """
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        with self._lock:
            self._do_reset(session_id, now)

    def session_health(self, session_id: str) -> LoopHealth | None:
        """Return the current health snapshot for a session.

        Returns None if the session is not tracked.
        """
        with self._lock:
            state = self._states.get(session_id)
            if state is None:
                return None
            return self._build_health(
                session_id, state, datetime.datetime.now(tz=datetime.timezone.utc)
            )

    def all_sessions_health(self) -> list[LoopHealth]:
        """Return health snapshots for all tracked sessions."""
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        with self._lock:
            return [
                self._build_health(sid, st, now)
                for sid, st in self._states.items()
            ]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def config(self) -> CircuitBreakerConfig:
        """Return the current configuration."""
        return self._config

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _do_trip(
        self,
        session_id: str,
        now: datetime.datetime,
        action: TripAction | None = None,
    ) -> None:
        """Internal: transition to OPEN state."""
        self._states[session_id] = CircuitState.OPEN
        self._trip_counts[session_id] = self._trip_counts.get(session_id, 0) + 1
        self._last_trip_at[session_id] = now
        trip_action = action or self._config.default_action
        self._actions[session_id] = trip_action

        # Force abort if max trips exceeded
        if self._trip_counts[session_id] >= self._config.max_trips:
            self._actions[session_id] = TripAction.ABORT_SESSION

        logger.warning(
            "circuit_tripped",
            session_id=session_id,
            action=self._actions[session_id].value,
            trip_count=self._trip_counts[session_id],
            consecutive_low=self._consecutive_low.get(session_id, 0),
        )

        if self._on_trip is not None:
            try:
                self._on_trip(session_id, self._actions[session_id])
            except Exception:
                logger.exception("on_trip callback failed", session_id=session_id)

    def _do_reset(
        self,
        session_id: str,
        now: datetime.datetime,
    ) -> None:
        """Internal: transition to CLOSED state."""
        old_state = self._states.get(session_id)
        self._states[session_id] = CircuitState.CLOSED
        self._consecutive_low[session_id] = 0
        self._actions.pop(session_id, None)
        self._last_trip_at.pop(session_id, None)

        if old_state != CircuitState.CLOSED:
            logger.info(
                "circuit_reset",
                session_id=session_id,
                previous_state=old_state.value if old_state else "UNKNOWN",
            )

            if self._on_reset is not None:
                try:
                    self._on_reset(session_id)
                except Exception:
                    logger.exception("on_reset callback failed", session_id=session_id)

    def _build_health(
        self,
        session_id: str,
        state: CircuitState,
        now: datetime.datetime,
    ) -> LoopHealth:
        """Build a LoopHealth snapshot from internal state."""
        last_trip = self._last_trip_at.get(session_id)
        auto_reset_at: datetime.datetime | None = None
        if (
            state == CircuitState.OPEN
            and last_trip is not None
            and self._config.auto_reset_minutes > 0
        ):
            auto_reset_at = last_trip + datetime.timedelta(
                minutes=self._config.auto_reset_minutes
            )

        return LoopHealth(
            session_id=session_id,
            circuit_state=state,
            consecutive_low=self._consecutive_low.get(session_id, 0),
            last_confidence=self._last_confidence.get(session_id, 1.0),
            trip_count=self._trip_counts.get(session_id, 0),
            last_trip_at=last_trip,
            auto_reset_at=auto_reset_at,
            action=self._actions.get(session_id),
        )
