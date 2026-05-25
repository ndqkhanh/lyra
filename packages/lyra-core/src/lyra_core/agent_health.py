"""Agent Health and Self-Diagnosis — runtime introspection and anomaly detection.

Provides the ``AgentHealthMonitor`` class that tracks agent vitals, runs
periodic health checks, detects degradation signals (error rate spikes,
response-time regression, memory-growth patterns, infinite loops), and
produces actionable intervention recommendations.

The module is designed to run alongside any agent loop without introducing
tight coupling — it only requires the caller to call ``record_action`` after
each agent step.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Constants                                                          #
# ------------------------------------------------------------------ #

_DEFAULT_ACTION_WINDOW: int = 500
"""Number of recent actions retained for pattern detection."""

_DEGRADATION_WINDOW_SECONDS: float = 300.0
"""Time window (seconds) used for error-rate and latency computations."""

_LOOP_MIN_REPETITIONS: int = 4
"""Minimum repetitions of the same action pattern to flag as a loop."""

_ERROR_RATE_THRESHOLD: float = 0.15
"""Error rate above this threshold triggers a DEGRADED or CRITICAL signal."""

_LATENCY_DEGRADATION_FACTOR: float = 2.0
"""Factor above baseline avg latency that triggers a degradation signal."""

_MEMORY_GROWTH_SAMPLES: int = 5
"""Number of consecutive upward samples required to suggest a leak."""

_CRITICAL_ERROR_RATE: float = 0.40
"""Error rate above this level yields a CRITICAL overall status."""


# ------------------------------------------------------------------ #
# Enums                                                              #
# ------------------------------------------------------------------ #


class HealthStatus(Enum):
    """Overall agent health level."""

    HEALTHY = auto()
    DEGRADED = auto()
    CRITICAL = auto()
    UNKNOWN = auto()


# ------------------------------------------------------------------ #
# Data containers (all immutable)                                     #
# ------------------------------------------------------------------ #


@dataclass(frozen=True)
class AnomalySignal:
    """Description of a single detected anomaly.

    Attributes
    ----------
    signal_type : str
        Categorical label such as ``"error_rate_spike"``,
        ``"response_time_degradation"``, ``"memory_leak"``,
        ``"infinite_loop"``, or ``"unexpected_behaviour"``.
    severity : float
        Normalised severity in [0.0, 1.0].
    detected_at : float
        Unix timestamp of detection.
    context : dict
        Arbitrary key-value context (e.g. current error rate, latency value).
    description : str
        Human-readable description of the anomaly.
    """

    signal_type: str
    severity: float
    detected_at: float
    context: dict[str, Any]
    description: str


@dataclass(frozen=True)
class HealthCheck:
    """Result of a single health check probe.

    Attributes
    ----------
    check_id : str
        Unique identifier for this check.
    name : str
        Human-readable check name (e.g. ``"responsiveness"``).
    status : HealthStatus
        Outcome of the check.
    details : str
        Free-text details or error message.
    last_checked : float
        Unix timestamp of the check.
    latency_ms : float
        How long the check took to run in milliseconds.
    """

    check_id: str
    name: str
    status: HealthStatus
    details: str
    last_checked: float
    latency_ms: float


@dataclass(frozen=True)
class AgentVitals:
    """Snapshot of core agent runtime metrics.

    Attributes
    ----------
    agent_id : str
        Unique agent identifier.
    uptime_seconds : float
        Seconds since the monitor was created.
    total_actions : int
        Total number of actions recorded.
    error_rate : float
        Error rate in [0.0, 1.0] over the recent window.
    avg_response_time_ms : float
        Average response time in milliseconds over the recent window.
    memory_usage_estimate : int
        Estimated memory usage in bytes (heuristic).
    loop_detection_active : bool
        Whether the loop detection heuristic has fired.
    consecutive_failures : int
        Number of consecutive failed actions.
    """

    agent_id: str
    uptime_seconds: float
    total_actions: int
    error_rate: float
    avg_response_time_ms: float
    memory_usage_estimate: int
    loop_detection_active: bool
    consecutive_failures: int


@dataclass(frozen=True)
class HealthReport:
    """Comprehensive health assessment snapshot.

    Attributes
    ----------
    vitals : AgentVitals
        Core runtime metrics.
    checks : tuple[HealthCheck, ...]
        Results of individual health check probes.
    anomalies : tuple[AnomalySignal, ...]
        Active anomalies detected during this assessment.
    overall_status : HealthStatus
        Aggregated health status.
    recommendations : tuple[str, ...]
        Ordered list of actionable recommendations.
    """

    vitals: AgentVitals
    checks: tuple[HealthCheck, ...]
    anomalies: tuple[AnomalySignal, ...]
    overall_status: HealthStatus
    recommendations: tuple[str, ...]


# ------------------------------------------------------------------ #
# In-memory action record (not exported)                              #
# ------------------------------------------------------------------ #


@dataclass
class _ActionRecord:
    """Internal mutable record for a single agent action."""

    success: bool
    response_time_ms: float
    action_type: str
    timestamp: float


# ------------------------------------------------------------------ #
# Health monitor                                                     #
# ------------------------------------------------------------------ #


class AgentHealthMonitor:
    """Runtime health tracker for a single agent.

    Call ``record_action`` after each agent step to feed the monitor.
    Call ``check_health`` periodically (e.g. every N steps) to obtain a
    :class:`HealthReport` with diagnostics and recommendations.

    The monitor is intentionally stateless with respect to the caller's
    business logic — it only tracks action outcomes and timing.

    Parameters
    ----------
    agent_id : str
        Unique identifier for the monitored agent.
    action_window : int, optional
        Maximum number of recent actions retained for analysis.
    """

    def __init__(
        self,
        agent_id: str,
        action_window: int = _DEFAULT_ACTION_WINDOW,
    ) -> None:
        self._agent_id: str = agent_id
        self._action_window: int = action_window
        self._start_time: float = time.time()
        self._actions: deque[_ActionRecord] = deque(maxlen=action_window)
        self._all_actions: int = 0
        self._consecutive_failures: int = 0
        self._loop_detection_active: bool = False
        self._last_memory_samples: deque[int] = deque(maxlen=_MEMORY_GROWTH_SAMPLES + 1)
        self._last_report: Optional[HealthReport] = None

    # ── Public API ─────────────────────────────────────────────

    def record_action(
        self,
        success: bool,
        response_time_ms: float,
        action_type: str,
    ) -> None:
        """Record the outcome of a single agent action.

        Parameters
        ----------
        success : bool
            Whether the action completed without error.
        response_time_ms : float
            Wall-clock duration of the action in milliseconds.
        action_type : str
            Short label describing the action (e.g. ``"llm_call"``,
            ``"file_edit"``, ``"tool_use"``).
        """
        record = _ActionRecord(
            success=success,
            response_time_ms=response_time_ms,
            action_type=action_type,
            timestamp=time.time(),
        )
        self._actions.append(record)
        self._all_actions += 1

        if success:
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1

    def check_health(self) -> HealthReport:
        """Comprehensive health assessment.

        Runs all internal probes, collects anomaly signals, and produces
        a report with an overall status and intervention recommendations.

        Returns
        -------
        HealthReport
            Snapshot of agent health at the current time.
        """
        start_check = time.perf_counter()

        # 1. Collect vitals.
        vitals = self.get_vitals()

        # 2. Run individual checks.
        responsiveness_check = self._check_responsiveness(vitals)
        error_rate_check = self._check_error_rate(vitals)
        loop_check = self._check_for_loop()
        memory_check = self._check_memory()

        checks: tuple[HealthCheck, ...] = (
            responsiveness_check,
            error_rate_check,
            loop_check,
            memory_check,
        )

        # 3. Detect anomalies.
        anomalies = self.detect_degradation(vitals)

        # 4. Compute overall status.
        overall = self._compute_overall_status(checks, anomalies)

        # 5. Generate recommendations.
        recommendations = tuple(self.recommend_intervention(vitals, anomalies))

        _ = (time.perf_counter() - start_check) * 1000.0

        report = HealthReport(
            vitals=vitals,
            checks=checks,
            anomalies=tuple(anomalies),
            overall_status=overall,
            recommendations=recommendations,
        )
        self._last_report = report
        return report

    def detect_loops(self, recent_actions: Optional[list[str]] = None) -> bool:
        """Detect repetitive action patterns that suggest an infinite loop.

        Scans the recent action type sequence for repeated back-to-back
        patterns of length 1, 2, or 3.

        Parameters
        ----------
        recent_actions : list[str], optional
            Action type labels to analyse. Defaults to stored actions.

        Returns
        -------
        bool
            ``True`` if a repetitive pattern is detected.
        """
        types = recent_actions if recent_actions is not None else [
            r.action_type for r in self._actions
        ]
        if len(types) < _LOOP_MIN_REPETITIONS * 2:
            return False

        # If all actions are the same type, it is a batch not a loop.
        if len(set(types)) == 1:
            self._loop_detection_active = False
            return False

        for pattern_len in (1, 2, 3):
            min_repeats = _LOOP_MIN_REPETITIONS
            if pattern_len == 1:
                # Single-action repetition only counts as a loop when there
                # are also failures — many legitimate workflows call the same
                # tool many times in sequence (e.g. batch LLM calls).
                if self._consecutive_failures == 0:
                    continue
                min_repeats = max(_LOOP_MIN_REPETITIONS, 6)
            if pattern_len * min_repeats > len(types):
                continue
            pattern = types[-pattern_len:]
            # Check that the tail matches the pattern repeatedly.
            match = True
            for i in range(min_repeats):
                start = len(types) - (i + 1) * pattern_len
                if types[start:start + pattern_len] != pattern:
                    match = False
                    break
            if match:
                self._loop_detection_active = True
                return True

        self._loop_detection_active = False
        return False

    def detect_degradation(self, vitals: Optional[AgentVitals] = None) -> list[AnomalySignal]:
        """Detect performance and reliability anomalies.

        Checks for error rate spikes, response time degradation, memory
        growth patterns, and infinite loops.

        Parameters
        ----------
        vitals : AgentVitals, optional
            Pre-computed vitals. Fetched fresh if ``None``.

        Returns
        -------
        list[AnomalySignal]
            All detected anomalies (empty list if healthy).
        """
        if vitals is None:
            vitals = self.get_vitals()

        signals: list[AnomalySignal] = []
        now = time.time()

        # Error rate spike.
        if vitals.error_rate > _CRITICAL_ERROR_RATE:
            signals.append(AnomalySignal(
                signal_type="error_rate_spike",
                severity=min(1.0, vitals.error_rate),
                detected_at=now,
                context={"error_rate": vitals.error_rate, "consecutive_failures": vitals.consecutive_failures},
                description=f"Error rate at {vitals.error_rate:.1%} exceeds critical threshold {_CRITICAL_ERROR_RATE:.0%}.",
            ))
        elif vitals.error_rate > _ERROR_RATE_THRESHOLD:
            signals.append(AnomalySignal(
                signal_type="error_rate_spike",
                severity=vitals.error_rate / _CRITICAL_ERROR_RATE,
                detected_at=now,
                context={"error_rate": vitals.error_rate},
                description=f"Error rate at {vitals.error_rate:.1%} exceeds warning threshold {_ERROR_RATE_THRESHOLD:.0%}.",
            ))

        # Response time degradation.
        if vitals.avg_response_time_ms > 0:
            baseline = self._compute_baseline_latency()
            if baseline > 0 and vitals.avg_response_time_ms > baseline * _LATENCY_DEGRADATION_FACTOR:
                ratio = vitals.avg_response_time_ms / baseline
                signals.append(AnomalySignal(
                    signal_type="response_time_degradation",
                    severity=min(1.0, (ratio - 1.0) / _LATENCY_DEGRADATION_FACTOR),
                    detected_at=now,
                    context={
                        "current_avg_ms": vitals.avg_response_time_ms,
                        "baseline_ms": baseline,
                        "ratio": round(ratio, 2),
                    },
                    description=(
                        f"Avg response time {vitals.avg_response_time_ms:.0f}ms is "
                        f"{ratio:.1f}x the baseline {baseline:.0f}ms."
                    ),
                ))

        # Memory growth / leak heuristic.
        if self._detect_memory_leak():
            signals.append(AnomalySignal(
                signal_type="memory_leak",
                severity=0.6,
                detected_at=now,
                context={"recent_samples": list(self._last_memory_samples)},
                description="Consecutive memory growth pattern detected — possible leak.",
            ))

        # Loop detection.
        if self.detect_loops():
            signals.append(AnomalySignal(
                signal_type="infinite_loop",
                severity=0.8,
                detected_at=now,
                context={"consecutive_failures": vitals.consecutive_failures},
                description="Repetitive action pattern detected — possible infinite loop.",
            ))

        # Consecutive failures.
        if vitals.consecutive_failures >= 3:
            signals.append(AnomalySignal(
                signal_type="consecutive_failures",
                severity=min(1.0, vitals.consecutive_failures / 10.0),
                detected_at=now,
                context={"count": vitals.consecutive_failures},
                description=f"{vitals.consecutive_failures} consecutive failures recorded.",
            ))

        return signals

    def get_vitals(self) -> AgentVitals:
        """Return a snapshot of current agent vitals.

        Returns
        -------
        AgentVitals
            Immutable vitals snapshot.
        """
        now = time.time()
        uptime = now - self._start_time
        error_rate = self._compute_error_rate(_DEGRADATION_WINDOW_SECONDS)
        avg_latency = self._compute_avg_latency(_DEGRADATION_WINDOW_SECONDS)
        memory_estimate = self._estimate_memory_usage()
        consecutive = self._consecutive_failures

        return AgentVitals(
            agent_id=self._agent_id,
            uptime_seconds=round(uptime, 1),
            total_actions=self._all_actions,
            error_rate=round(error_rate, 4),
            avg_response_time_ms=round(avg_latency, 1),
            memory_usage_estimate=memory_estimate,
            loop_detection_active=self._loop_detection_active,
            consecutive_failures=consecutive,
        )

    def recommend_intervention(
        self,
        vitals: AgentVitals,
        anomalies: list[AnomalySignal],
    ) -> list[str]:
        """Generate actionable recommendations based on vitals and anomalies.

        Parameters
        ----------
        vitals : AgentVitals
            Current agent vitals.
        anomalies : list[AnomalySignal]
            Active anomaly signals.

        Returns
        -------
        list[str]
            Ordered list of recommendation strings.
        """
        recommendations: list[str] = []

        # Classify anomaly types present.
        signal_types = {a.signal_type for a in anomalies}

        if "infinite_loop" in signal_types:
            recommendations.append(
                "BREAKING LOOP: Reset agent state or apply action diversity heuristic."
            )

        if "error_rate_spike" in signal_types:
            rec = (
                "ESCALATE: Investigate error source immediately."
                if vitals.error_rate > _CRITICAL_ERROR_RATE
                else "INVESTIGATE: Review recent errors for patterns."
            )
            recommendations.append(rec)

        if "response_time_degradation" in signal_types:
            recommendations.append(
                "OPTIMIZE: Profile slow actions. Consider model downgrade or caching."
            )

        if "memory_leak" in signal_types:
            recommendations.append(
                "GC: Trigger garbage collection. Check for unbounded caches or listeners."
            )

        if vitals.consecutive_failures >= 3:
            recommendations.append(
                f"BACKOFF: Apply exponential backoff ({vitals.consecutive_failures} consecutive failures)."
            )

        if vitals.uptime_seconds > 3600 and vitals.total_actions > 0:
            recommendations.append(
                "MAINTENANCE: Consider periodic state reset for long-running agents."
            )

        if not recommendations:
            recommendations.append("NO_ACTION: Agent is healthy.")

        return recommendations

    # ── Internal probes ────────────────────────────────────────

    def _compute_error_rate(self, window_seconds: float) -> float:
        """Error rate over the recent time window.

        Parameters
        ----------
        window_seconds : float
            Look-back window in seconds.

        Returns
        -------
        float
            Error rate in [0.0, 1.0].
        """
        now = time.time()
        cutoff = now - window_seconds
        recent = [r for r in self._actions if r.timestamp >= cutoff]

        if not recent:
            return 0.0

        errors = sum(1 for r in recent if not r.success)
        return errors / len(recent)

    def _compute_avg_latency(self, window_seconds: float) -> float:
        """Average response time over the recent time window.

        Parameters
        ----------
        window_seconds : float
            Look-back window in seconds.

        Returns
        -------
        float
            Mean latency in milliseconds.
        """
        now = time.time()
        cutoff = now - window_seconds
        recent = [r for r in self._actions if r.timestamp >= cutoff]

        if not recent:
            return 0.0

        return sum(r.response_time_ms for r in recent) / len(recent)

    def _compute_baseline_latency(self) -> float:
        """Compute baseline latency as the median of all stored actions.

        Uses the full action history to establish a stable baseline that
        is resistant to short-term spikes.

        Returns
        -------
        float
            Median latency in milliseconds.
        """
        if not self._actions:
            return 0.0
        sorted_latencies = sorted(r.response_time_ms for r in self._actions)
        n = len(sorted_latencies)
        mid = n // 2
        if n % 2 == 1:
            return sorted_latencies[mid]
        return (sorted_latencies[mid - 1] + sorted_latencies[mid]) / 2.0

    def _estimate_memory_usage(self) -> int:
        """Heuristic estimate of the monitor's internal memory usage in bytes.

        This is a rough measure of the action buffer size, not the agent's
        total memory footprint.

        Returns
        -------
        int
            Estimated bytes consumed by the action buffer.
        """
        # Approximate per-record size: timestamps, strings, bool -> ~200 bytes.
        return len(self._actions) * 200

    def _detect_memory_leak(self) -> bool:
        """Heuristic memory-leak detection based on queue growth pattern.

        Checks whether the number of retained action records has grown
        monotonically over the last N samples, which suggests the caller
        may not be respecting the maxlen limit (unlikely) or that external
        memory is leaking.

        Returns
        -------
        bool
            ``True`` when a growth pattern is detected.
        """
        sample = len(self._actions)
        self._last_memory_samples.append(sample)

        if len(self._last_memory_samples) < _MEMORY_GROWTH_SAMPLES:
            return False

        samples = list(self._last_memory_samples)
        # Check monotonic increase.
        for i in range(1, len(samples)):
            if samples[i] <= samples[i - 1]:
                return False
        return True

    def _check_responsiveness(self, vitals: AgentVitals) -> HealthCheck:
        """Check whether the agent is responding within expected time.

        Parameters
        ----------
        vitals : AgentVitals
            Current agent vitals.

        Returns
        -------
        HealthCheck
        """
        check_id = f"responsiveness_{int(time.time())}"
        baseline = self._compute_baseline_latency()

        if vitals.total_actions == 0:
            return HealthCheck(
                check_id=check_id,
                name="responsiveness",
                status=HealthStatus.UNKNOWN,
                details="No actions recorded yet.",
                last_checked=time.time(),
                latency_ms=0.0,
            )

        if baseline > 0 and vitals.avg_response_time_ms > baseline * 3.0:
            status = HealthStatus.CRITICAL
            details = f"Avg latency {vitals.avg_response_time_ms:.0f}ms is 3x+ baseline {baseline:.0f}ms."
        elif baseline > 0 and vitals.avg_response_time_ms > baseline * _LATENCY_DEGRADATION_FACTOR:
            status = HealthStatus.DEGRADED
            details = f"Avg latency {vitals.avg_response_time_ms:.0f}ms exceeds 2x baseline {baseline:.0f}ms."
        else:
            status = HealthStatus.HEALTHY
            details = f"Avg latency {vitals.avg_response_time_ms:.0f}ms within expected range."

        return HealthCheck(
            check_id=check_id,
            name="responsiveness",
            status=status,
            details=details,
            last_checked=time.time(),
            latency_ms=vitals.avg_response_time_ms,
        )

    def _check_error_rate(self, vitals: AgentVitals) -> HealthCheck:
        """Check whether the current error rate is acceptable.

        Parameters
        ----------
        vitals : AgentVitals
            Current agent vitals.

        Returns
        -------
        HealthCheck
        """
        check_id = f"error_rate_{int(time.time())}"
        rate = vitals.error_rate

        if vitals.total_actions == 0:
            return HealthCheck(
                check_id=check_id,
                name="error_rate",
                status=HealthStatus.UNKNOWN,
                details="No actions recorded yet.",
                last_checked=time.time(),
                latency_ms=0.0,
            )

        if rate > _CRITICAL_ERROR_RATE:
            status = HealthStatus.CRITICAL
            details = f"Error rate {rate:.1%} exceeds critical threshold {_CRITICAL_ERROR_RATE:.0%}."
        elif rate > _ERROR_RATE_THRESHOLD:
            status = HealthStatus.DEGRADED
            details = f"Error rate {rate:.1%} exceeds warning threshold {_ERROR_RATE_THRESHOLD:.0%}."
        else:
            status = HealthStatus.HEALTHY
            details = f"Error rate {rate:.1%} within acceptable range."

        return HealthCheck(
            check_id=check_id,
            name="error_rate",
            status=status,
            details=details,
            last_checked=time.time(),
            latency_ms=0.0,
        )

    def _check_for_loop(self) -> HealthCheck:
        """Check for repetitive action patterns suggesting an infinite loop.

        Returns
        -------
        HealthCheck
        """
        check_id = f"loop_detection_{int(time.time())}"
        is_loop = self.detect_loops()

        return HealthCheck(
            check_id=check_id,
            name="loop_detection",
            status=HealthStatus.CRITICAL if is_loop else HealthStatus.HEALTHY,
            details="Repetitive action pattern detected." if is_loop else "No loop detected.",
            last_checked=time.time(),
            latency_ms=0.0,
        )

    def _check_memory(self) -> HealthCheck:
        """Check for memory-related anomalies.

        Returns
        -------
        HealthCheck
        """
        check_id = f"memory_{int(time.time())}"
        leak = self._detect_memory_leak()

        return HealthCheck(
            check_id=check_id,
            name="memory",
            status=HealthStatus.DEGRADED if leak else HealthStatus.HEALTHY,
            details="Possible memory leak detected." if leak else "Memory stable.",
            last_checked=time.time(),
            latency_ms=0.0,
        )

    def _compute_overall_status(
        self,
        checks: tuple[HealthCheck, ...],
        anomalies: list[AnomalySignal],
    ) -> HealthStatus:
        """Aggregate individual checks and anomalies into a single status.

        Order of precedence: CRITICAL > DEGRADED > UNKNOWN > HEALTHY.

        Parameters
        ----------
        checks : tuple[HealthCheck, ...]
            Individual health check results.
        anomalies : list[AnomalySignal]
            Detected anomaly signals.

        Returns
        -------
        HealthStatus
        """
        if any(c.status == HealthStatus.CRITICAL for c in checks):
            return HealthStatus.CRITICAL
        if any(a.severity > 0.7 for a in anomalies):
            return HealthStatus.CRITICAL
        if any(c.status == HealthStatus.DEGRADED for c in checks):
            return HealthStatus.DEGRADED
        if anomalies:
            return HealthStatus.DEGRADED
        if any(c.status == HealthStatus.UNKNOWN for c in checks):
            return HealthStatus.UNKNOWN
        return HealthStatus.HEALTHY


__all__ = [
    "HealthStatus",
    "AnomalySignal",
    "HealthCheck",
    "AgentVitals",
    "HealthReport",
    "AgentHealthMonitor",
]
