"""
Self-Diagnosing Harness — Real-time trajectory monitoring, anomaly detection,
and automated repair for Lyra agent sessions.

Integrates with:
- ErrorProbe failure taxonomy (verification/error_probe.py) via MAST (14 modes, 3 families)
- TracingProvider spans (verification/tracing_provider.py)
- MetricsDashboard observability (observability/dashboard.py)
- RetryPolicy, CircuitBreaker, CheckpointManager (reliability/)
- MutationVerifier (reliability/mutation_verifier.py)
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator

from lyra.observability.dashboard import MetricsDashboard, SessionMetrics
from lyra.reliability.circuit_breaker import CircuitBreaker
from lyra.reliability.gardening_agents import (
    CodeGardeningAgent,
    DocGardeningAgent,
    GardeningReport,
    GardeningSchedule,
    GardeningSystem,
    TestGardeningAgent,
)
from lyra.reliability.retry import RetryPolicy, retry
from lyra.verification.error_probe import (
    Anomaly,
    AnomalyDetector,
    BackwardTracer,
    ErrorProbe,
    ExecutionStep,
    FailureAttribution,
    FailureType,
    Symptom,
    ValidationTeam,
)
from lyra.verification.tracing_provider import TracingProvider


# ---------------------------------------------------------------------------
# MAST Taxonomy — 14 Modes, 3 Families
# ---------------------------------------------------------------------------

class MASTFamily(str, Enum):
    """The three families of the MAST (Multi-Agent Self-diagnosing Taxonomy)."""

    LOCAL_DETECTION = "local_detection"
    BACKWARD_TRACING = "backward_tracing"
    MULTI_AGENT_VALIDATION = "multi_agent_validation"


class MASTMode(str, Enum):
    """All 14 modes of the MAST taxonomy, mapped to the family that owns them."""

    # -- Local Detection family (6 modes) --
    REPEATED_ERRORS = "repeated_errors"               # >=3 consecutive failures
    CIRCULAR_REASONING = "circular_reasoning"           # repeated same action <5 apart
    MEMORY_INCONSISTENCY = "memory_inconsistency"       # write then overwrite with diff
    TOOL_FAILURE_CASCADE = "tool_failure_cascade"       # >=2 related tool fails
    CONFIDENCE_DROP = "confidence_drop"                # >30% confidence drop
    INFINITE_LOOP = "infinite_loop"                    # identical trajectory signature

    # -- Backward Tracing family (4 modes) --
    SYMPTOM_CHAIN = "symptom_chain"                    # dependent failures trace chain
    DATA_FLOW_BREAK = "data_flow_break"                # missing dependency output
    TIMING_VIOLATION = "timing_violation"              # operation order violation
    RESOURCE_EXHAUSTION = "resource_exhaustion"         # token / budget depletion

    # -- Multi-Agent Validation family (4 modes) --
    VALIDATION_MISMATCH = "validation_mismatch"         # validators disagree
    ATTRIBUTION_CONFLICT = "attribution_conflict"       # multiple root causes proposed
    RECOMMENDATION_OVERRIDE = "recommendation_override" # repair was overridden
    ESCALATION_REQUIRED = "escalation_required"         # human must decide

    @classmethod
    def family_of(cls, mode: MASTMode) -> MASTFamily:
        """Return the family that *mode* belongs to."""
        if mode in {
            cls.REPEATED_ERRORS,
            cls.CIRCULAR_REASONING,
            cls.MEMORY_INCONSISTENCY,
            cls.TOOL_FAILURE_CASCADE,
            cls.CONFIDENCE_DROP,
            cls.INFINITE_LOOP,
        }:
            return MASTFamily.LOCAL_DETECTION
        if mode in {
            cls.SYMPTOM_CHAIN,
            cls.DATA_FLOW_BREAK,
            cls.TIMING_VIOLATION,
            cls.RESOURCE_EXHAUSTION,
        }:
            return MASTFamily.BACKWARD_TRACING
        return MASTFamily.MULTI_AGENT_VALIDATION


# ---------------------------------------------------------------------------
# WhoAndWhen protocol
# ---------------------------------------------------------------------------


@dataclass
class WhoAndWhen:
    """Pinpoint which agent caused a failure and when.

    Attributes
    ----------
    agent_id:
        Unique identifier of the agent that caused the failure.
    agent_type:
        Role or type of the agent (e.g. ``"primary"``, ``"researcher"``,
        ``"executor"``).
    step_id:
        The :attr:`ExecutionStep.step_id` where the failure occurred.
    timestamp:
        When the failure was recorded.
    trace_id:
        Optional OpenTelemetry trace ID for cross-reference.
    span_id:
        Optional OpenTelemetry span ID for cross-reference.
    """

    agent_id: str
    agent_type: str
    step_id: str
    timestamp: datetime
    trace_id: str | None = None
    span_id: str | None = None


# ---------------------------------------------------------------------------
# TrajectoryDiff
# ---------------------------------------------------------------------------


@dataclass
class TrajectoryDiff:
    """Difference between a current trajectory and a known-good baseline.

    Attributes
    ----------
    session_id:
        The session being compared.
    baseline_id:
        Identifier of the baseline trajectory.
    added_steps:
        Steps in the current trajectory that don't appear in baseline.
    missing_steps:
        Steps that existed in baseline but are absent now.
    divergent_actions:
        Steps where the action signature differs from baseline.
    similarity:
        Overall similarity score (0-1, 1 = identical).
    anomaly_count:
        Number of anomalies in the current trajectory vs baseline.
    """

    session_id: str
    baseline_id: str
    added_steps: list[ExecutionStep]
    missing_steps: list[ExecutionStep]
    divergent_actions: list[ExecutionStep]
    similarity: float
    anomaly_count: int


# ---------------------------------------------------------------------------
# RootCauseAnalysis
# ---------------------------------------------------------------------------


@dataclass
class RootCauseAnalysis:
    """A trace from failure back to the originating action.

    Attributes
    ----------
    failure_step_id:
        The step where the failure was observed.
    root_cause_step_id:
        The originating step that caused the failure.
    failure_type:
        The classified failure type.
    confidence:
        How confident we are in the attribution (0-1).
    chain:
        Ordered list of step IDs from root cause to failure.
    explanation:
        Human-readable description of the causal chain.
    who_and_when:
        Optional agent attribution.
    recommendations:
        Suggested repair actions.
    """

    failure_step_id: str
    root_cause_step_id: str
    failure_type: FailureType
    confidence: float
    chain: list[str]
    explanation: str
    who_and_when: WhoAndWhen | None = None
    recommendations: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Anomaly / Repair types (enhanced)
# ---------------------------------------------------------------------------


class AnomalyType(str, Enum):
    """Anomaly types for the self-diagnosing harness.

    Extends the base taxonomy with regression and repair-specific types.
    """

    HALLUCINATION = "hallucination"
    TOOL_ERROR = "tool_error"
    INFINITE_LOOP = "infinite_loop"
    COST_SPIKE = "cost_spike"
    LATENCY_SPIKE = "latency_spike"
    OUTPUT_REGRESSION = "output_regression"
    MAST_ANOMALY = "mast_anomaly"  # catch-all for MAST-detected anomalies


class RepairActionType(str, Enum):
    """Supported repair action types, ordered from cheapest to most expensive.

    Enhanced for v8.3 with all five auto-repair strategies.
    """

    RETRY_SAME = "retry_same"
    RETRY_CHEAPER = "retry_cheaper"
    RETRY_WITH_COMPACTION = "retry_with_compaction"
    ESCALATE = "escalate"
    ABORT = "abort"

    # Aliases for backward compatibility
    RETRY_SAME_MODEL = "retry_same"
    RETRY_CHEAPER_MODEL = "retry_cheaper"
    RETRY_WITH_CONTEXT_COMPACTION = "retry_with_compaction"
    ESCALATE_TO_HUMAN = "escalate"
    ABORT_SESSION = "abort"


@dataclass
class RepairAction:
    """A single repair action triggered by anomaly detection."""

    action_type: RepairActionType
    anomaly: AnomalyType
    session_id: str
    timestamp: datetime
    description: str
    success: bool | None = None
    recovery_time_seconds: float | None = None
    mast_mode: MASTMode | None = None  # which MAST mode triggered this


@dataclass
class HealthEvent:
    """A single health event pushed into a HealthStream."""

    timestamp: datetime
    event_type: str
    session_id: str
    detail: dict[str, Any] = field(default_factory=dict)


class HealthStream:
    """Async stream of health events for a single session.

    Supports both push-based ingestion and async iteration::

        stream = HealthStream("session-1")
        async for event in stream:
            print(event.event_type, event.detail)
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._events: list[HealthEvent] = []
        self._listeners: list[asyncio.Future] = []
        self._closed = False

    def push(self, event: HealthEvent) -> None:
        """Push a new event into the stream."""
        if self._closed:
            return
        self._events.append(event)
        for future in self._listeners:
            if not future.done():
                future.set_result(event)
        self._listeners = [f for f in self._listeners if not f.done()]

    def close(self) -> None:
        """Signal end of stream."""
        self._closed = True
        for future in self._listeners:
            if not future.done():
                future.cancel()

    async def __aiter__(self) -> AsyncIterator[HealthEvent]:
        """Iterate over health events as they arrive (blocking on empty)."""
        while not self._closed:
            if self._events:
                while self._events:
                    yield self._events.pop(0)
            else:
                future = asyncio.get_event_loop().create_future()
                self._listeners.append(future)
                try:
                    event = await asyncio.wait_for(future, timeout=60.0)
                    yield event
                except asyncio.TimeoutError:
                    yield HealthEvent(
                        timestamp=datetime.now(timezone.utc),
                        event_type="heartbeat",
                        session_id=self.session_id,
                    )
        while self._events:
            yield self._events.pop(0)

    @property
    def recent_events(self, n: int = 10) -> list[HealthEvent]:
        return self._events[-n:]

    @property
    def event_count(self) -> int:
        return len(self._events)


# ---------------------------------------------------------------------------
# Reliability Report
# ---------------------------------------------------------------------------


@dataclass
class ReliabilityReport:
    """Aggregated reliability metrics for a session."""

    session_id: str
    uptime: float
    error_rate: float
    mean_time_to_recovery: float
    cost_efficiency: float
    total_operations: int = 0
    total_errors: int = 0
    total_recovery_time: float = 0.0
    total_cost: float = 0.0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime | None = None
    anomaly_breakdown: dict[str, int] = field(default_factory=dict)
    repair_success_rate: float = 0.0
    mast_breakdown: dict[str, int] = field(default_factory=dict)
    who_and_when_events: list[WhoAndWhen] = field(default_factory=list)

    @classmethod
    def from_session(
        cls,
        session_id: str,
        dashboard: MetricsDashboard,
        repairs: list[RepairAction],
        anomalies: list,
    ) -> ReliabilityReport:
        """Build a report from a MetricsDashboard session and repair history."""
        metrics = dashboard.get_session(session_id)
        if not metrics:
            return cls(
                session_id=session_id,
                uptime=1.0,
                error_rate=0.0,
                mean_time_to_recovery=0.0,
                cost_efficiency=0.0,
            )

        total_ops = max(metrics.tool_calls, 1)
        total_errors = metrics.errors
        error_rate = total_errors / total_ops

        successful_repairs = [r for r in repairs if r.success is True]
        total_recovery = sum(
            (r.recovery_time_seconds or 0.0) for r in successful_repairs
        )
        mttr = total_recovery / len(successful_repairs) if successful_repairs else 0.0

        cost_efficiency = (
            (metrics.total_tokens * (1.0 - error_rate)) / metrics.total_cost
            if metrics.total_cost > 0
            else 0.0
        )

        uptime = 1.0 - error_rate

        breakdown: dict[str, int] = {}
        mast_breakdown: dict[str, int] = {}
        for a in anomalies:
            if isinstance(a, tuple) and len(a) == 2 and isinstance(a[1], MASTMode):
                mast_breakdown[a[1].value] = mast_breakdown.get(a[1].value, 0) + 1
            else:
                key = a.value if isinstance(a, AnomalyType) else str(a)
                breakdown[key] = breakdown.get(key, 0) + 1

        completed_repairs = [r for r in repairs if r.success is not None]
        repair_success_rate = (
            sum(1 for r in completed_repairs if r.success) / len(completed_repairs)
            if completed_repairs
            else 0.0
        )

        return cls(
            session_id=session_id,
            uptime=uptime,
            error_rate=error_rate,
            mean_time_to_recovery=mttr,
            cost_efficiency=cost_efficiency,
            total_operations=metrics.tool_calls,
            total_errors=total_errors,
            total_recovery_time=total_recovery,
            total_cost=metrics.total_cost,
            anomaly_breakdown=breakdown,
            repair_success_rate=repair_success_rate,
            mast_breakdown=mast_breakdown,
        )


@dataclass
class GardenHealth:
    """Garden health metrics for the harness.

    Attributes
    ----------
    report:
        The most recent :class:`GardeningReport` generated.
    last_cycle:
        When the last gardening cycle completed.
    cycles_run:
        Total number of gardening cycles executed.
    issues_resolved:
        Cumulative count of issues auto-fixed across all cycles.
    """

    report: GardeningReport | None = None
    last_cycle: datetime | None = None
    cycles_run: int = 0
    issues_resolved: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to a plain dict for serialisation."""
        return {
            "last_cycle": self.last_cycle.isoformat() if self.last_cycle else None,
            "cycles_run": self.cycles_run,
            "issues_resolved": self.issues_resolved,
            "last_report": self.report.to_dict() if self.report else None,
        }


# ---------------------------------------------------------------------------
# TrajectoryBaseline — known-good trajectory store
# ---------------------------------------------------------------------------


@dataclass
class TrajectoryBaseline:
    """A stored known-good trajectory used for comparison."""

    baseline_id: str
    session_id: str
    steps: list[ExecutionStep]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def signature(self) -> str:
        """Produce a deterministic hash of the trajectory action sequence."""
        raw = "|".join(
            f"{s.action}:{str(s.input_data.get('tool_name', ''))[:40]}"
            for s in self.steps
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Self-Diagnosing Harness
# ---------------------------------------------------------------------------


class SelfDiagnosingHarness:
    """Real-time anomaly detection and automated repair for agent sessions.

    v8.3 enhancements:
    - MAST taxonomy (14 modes, 3 families) via ErrorProbe integration
    - WhoAndWhen agent attribution protocol
    - TrajectoryDiff comparisons against known-good baselines
    - RootCauseAnalysis from failure to originating action
    - Five auto-repair strategies: retry_same, retry_cheaper, retry_with_compaction,
      escalate, abort
    - Gardening agents for automated entropy management (doc, code, test)
    """

    def __init__(
        self,
        dashboard: MetricsDashboard | None = None,
        tracer: TracingProvider | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        retry_policy: RetryPolicy | None = None,
        docs_path: str | None = None,
        src_path: str | None = None,
        test_path: str | None = None,
    ) -> None:
        self.dashboard = dashboard or MetricsDashboard()
        self.tracer = tracer
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=3, recovery_timeout=30.0
        )
        self.retry_policy = retry_policy or RetryPolicy(
            max_retries=3, base_delay=1.0, max_delay=30.0, jitter=True
        )

        # Internal state
        self._streams: dict[str, HealthStream] = {}
        self._repair_history: dict[str, list[RepairAction]] = {}
        self._anomaly_history: dict[str, list] = {}
        self._baselines: dict[str, TrajectoryBaseline] = {}

        # MAST (ErrorProbe) integration
        self._error_probe = ErrorProbe()

        # Tunable thresholds
        self.cost_spike_threshold: float = 0.50
        self.latency_spike_threshold: float = 30.0
        self.loop_detection_window: int = 5
        self.error_rate_threshold: float = 0.3

        # Gardening agents for entropy management
        self._docs_path = docs_path
        self._src_path = src_path or "src"
        self._test_path = test_path or "tests"
        self._garden_system: GardeningSystem | None = None
        self._garden_health = GardenHealth()

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def monitor(self, session_id: str) -> HealthStream:
        """Start real-time health monitoring for *session_id*."""
        if session_id not in self._streams:
            self._streams[session_id] = HealthStream(session_id)
            self._repair_history[session_id] = []
            self._anomaly_history[session_id] = []
        return self._streams[session_id]

    def close_stream(self, session_id: str) -> None:
        """Close and remove the health stream for *session_id*."""
        stream = self._streams.pop(session_id, None)
        if stream:
            stream.close()

    def active_sessions(self) -> list[str]:
        """Return session IDs currently being monitored."""
        return list(self._streams.keys())

    # ------------------------------------------------------------------
    # Anomaly Detection (enhanced with MAST)
    # ------------------------------------------------------------------

    def detect_anomalies(
        self,
        trajectory: list[ExecutionStep],
        session_id: str | None = None,
    ) -> list[AnomalyType]:
        """Classify anomalies in *trajectory* using ErrorProbe MAST taxonomy.

        Runs the three-stage ErrorProbe pipeline behind the scenes and maps
        detected MAST modes to the high-level AnomalyType enum.

        When *session_id* is provided, anomalies are pushed onto the session's
        HealthStream.
        """
        detected: list[AnomalyType] = []

        # -- Legacy heuristics (backward compat) --
        if self._detect_hallucination(trajectory):
            detected.append(AnomalyType.HALLUCINATION)
        if self._detect_tool_error(trajectory):
            detected.append(AnomalyType.TOOL_ERROR)
        if self._detect_infinite_loop(trajectory):
            detected.append(AnomalyType.INFINITE_LOOP)
        if self._detect_cost_spike(trajectory, session_id):
            detected.append(AnomalyType.COST_SPIKE)
        if self._detect_latency_spike(trajectory):
            detected.append(AnomalyType.LATENCY_SPIKE)
        if self._detect_output_regression(trajectory, session_id):
            detected.append(AnomalyType.OUTPUT_REGRESSION)

        # -- MAST (ErrorProbe) integration --
        mast_modes = self._detect_mast_modes(trajectory)
        if mast_modes:
            detected.append(AnomalyType.MAST_ANOMALY)

        if session_id and session_id in self._anomaly_history:
            # Store both AnomalyType and MASTMode as tuples
            for mm in mast_modes:
                self._anomaly_history[session_id].append(
                    (AnomalyType.MAST_ANOMALY, mm)
                )
            self._anomaly_history[session_id].extend(detected)
            stream = self._streams.get(session_id)
            if stream:
                for anomaly in detected:
                    stream.push(
                        HealthEvent(
                            timestamp=datetime.now(timezone.utc),
                            event_type="anomaly_detected",
                            session_id=session_id,
                            detail={"anomaly_type": anomaly.value},
                        )
                    )

        return detected

    def _detect_mast_modes(self, trajectory: list[ExecutionStep]) -> list[MASTMode]:
        """Run ErrorProbe's AnomalyDetector and map to MAST modes."""
        mast_modes: list[MASTMode] = []

        # Stage 1: ErrorProbe local anomaly detection
        anomalies = self._error_probe.detector.detect(trajectory)
        for a in anomalies:
            mode = self._map_anomaly_to_mast(a)
            if mode:
                mast_modes.append(mode)

        return mast_modes

    @staticmethod
    def _map_anomaly_to_mast(anomaly: Anomaly) -> MASTMode | None:
        """Map an ErrorProbe anomaly type to a MAST mode."""
        mapping = {
            "repeated_errors": MASTMode.REPEATED_ERRORS,
            "circular_reasoning": MASTMode.CIRCULAR_REASONING,
            "memory_inconsistency": MASTMode.MEMORY_INCONSISTENCY,
            "tool_failure_cascade": MASTMode.TOOL_FAILURE_CASCADE,
            "confidence_drop": MASTMode.CONFIDENCE_DROP,
        }
        return mapping.get(anomaly.anomaly_type)

    # ------------------------------------------------------------------
    # WhoAndWhen — Agent Attribution
    # ------------------------------------------------------------------

    def who_and_when(
        self,
        trajectory: list[ExecutionStep],
        failure_step_id: str,
        agent_id: str = "unknown",
        agent_type: str = "unknown",
    ) -> WhoAndWhen | None:
        """Pinpoint which agent caused a failure and when.

        Parameters
        ----------
        trajectory:
            The full execution trace.
        failure_step_id:
            The step where the failure occurred.
        agent_id:
            Unique identifier of the suspected agent.
        agent_type:
            Role of the suspected agent.

        Returns
        -------
        A :class:`WhoAndWhen` for the failure step, or ``None`` if the step
        cannot be found.
        """
        for step in trajectory:
            if step.step_id == failure_step_id:
                return WhoAndWhen(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    step_id=failure_step_id,
                    timestamp=step.timestamp,
                    trace_id=step.metadata.get("trace_id"),
                    span_id=step.metadata.get("span_id"),
                )
        return None

    # ------------------------------------------------------------------
    # TrajectoryDiff — Baseline Comparison
    # ------------------------------------------------------------------

    def store_baseline(
        self, session_id: str, trajectory: list[ExecutionStep]
    ) -> TrajectoryBaseline:
        """Store a known-good trajectory as a baseline for future comparisons."""
        b = TrajectoryBaseline(
            baseline_id=f"bl-{session_id}-{int(time.time())}",
            session_id=session_id,
            steps=trajectory,
        )
        self._baselines[b.baseline_id] = b
        return b

    def get_baseline(self, baseline_id: str) -> TrajectoryBaseline | None:
        """Retrieve a stored baseline by ID."""
        return self._baselines.get(baseline_id)

    def diff_against_baseline(
        self,
        trajectory: list[ExecutionStep],
        baseline_id: str,
        session_id: str = "",
    ) -> TrajectoryDiff | None:
        """Compare *trajectory* against a stored baseline.

        Returns a :class:`TrajectoryDiff` describing additions, deletions,
        diversions, and an overall similarity score.
        """
        baseline = self._baselines.get(baseline_id)
        if baseline is None:
            return None

        # Build lookup maps
        baseline_map: dict[str, ExecutionStep] = {s.step_id: s for s in baseline.steps}
        current_map: dict[str, ExecutionStep] = {s.step_id: s for s in trajectory}

        baseline_ids = set(baseline_map.keys())
        current_ids = set(current_map.keys())

        added = [current_map[sid] for sid in current_ids - baseline_ids]
        missing = [baseline_map[sid] for sid in baseline_ids - current_ids]

        # Divergent: same step_id but different action signature
        divergent: list[ExecutionStep] = []
        common_ids = baseline_ids & current_ids
        for sid in common_ids:
            bs = baseline_map[sid]
            cs = current_map[sid]
            if bs.action != cs.action:
                divergent.append(cs)

        # Similarity: fraction of common steps with matching actions
        total = max(len(baseline_ids | current_ids), 1)
        matching = len(common_ids) - len(divergent)
        similarity = matching / total

        # Anomaly count in current divergent/added steps via ErrorProbe
        anomaly_count = len(
            self._error_probe.detector.detect(divergent + added)
        )

        return TrajectoryDiff(
            session_id=session_id or baseline.session_id,
            baseline_id=baseline_id,
            added_steps=added,
            missing_steps=missing,
            divergent_actions=divergent,
            similarity=similarity,
            anomaly_count=anomaly_count,
        )

    # ------------------------------------------------------------------
    # RootCauseAnalysis — Failure Tracing
    # ------------------------------------------------------------------

    async def root_cause_analysis(
        self,
        trajectory: list[ExecutionStep],
        failure_step_id: str | None = None,
        agent_id: str = "unknown",
        agent_type: str = "unknown",
    ) -> RootCauseAnalysis | None:
        """Trace a failure back to its originating action.

        Uses ErrorProbe's three-stage pipeline (anomaly detection, backward
        tracing, multi-agent validation) to produce a root cause analysis.

        Parameters
        ----------
        trajectory:
            The full execution trace.
        failure_step_id:
            The step where the failure was observed. If None, auto-detected.
        agent_id:
            Agent identifier for WhoAndWhen attribution.
        agent_type:
            Agent role for WhoAndWhen attribution.

        Returns
        -------
        A :class:`RootCauseAnalysis` or ``None`` if no failure is found.
        """
        # Let ErrorProbe do the heavy lifting
        attribution = await self._error_probe.diagnose(
            steps=trajectory, failure_step=failure_step_id
        )
        if not attribution.root_cause_step:
            return None

        # Build causal chain
        chain = self._build_causal_chain(trajectory, attribution)

        # Generate WhoAndWhen
        waw = self.who_and_when(
            trajectory=trajectory,
            failure_step_id=attribution.root_cause_step,
            agent_id=agent_id,
            agent_type=agent_type,
        )

        # MAST mode classification
        root_mode = None
        if attribution.anomalies:
            root_mode = self._map_anomaly_to_mast(attribution.anomalies[0])

        # Recommendations (from ErrorProbe + harness)
        recommendations = list(attribution.recommendations)
        if root_mode:
            recommendations.append(
                f"Consider repair for MAST mode: {root_mode.value} "
                f"(family: {MASTMode.family_of(root_mode).value})"
            )

        return RootCauseAnalysis(
            failure_step_id=failure_step_id or attribution.root_cause_step,
            root_cause_step_id=attribution.root_cause_step,
            failure_type=attribution.failure_type,
            confidence=attribution.confidence,
            chain=chain,
            explanation=attribution.explanation,
            who_and_when=waw,
            recommendations=recommendations,
        )

    @staticmethod
    def _build_causal_chain(
        trajectory: list[ExecutionStep], attribution: FailureAttribution
    ) -> list[str]:
        """Build an ordered list of step IDs from root cause to failure."""
        chain: list[str] = []
        if attribution.root_cause_step:
            chain.append(attribution.root_cause_step)
        chain.extend(
            s for s in attribution.contributing_steps if s not in chain
        )
        if attribution.root_cause_step and (
            not chain or chain[-1] != attribution.root_cause_step
        ):
            chain.append(attribution.root_cause_step)
        return chain

    # ------------------------------------------------------------------
    # Repair (enhanced with 5 strategies)
    # ------------------------------------------------------------------

    async def trigger_repair(
        self,
        anomaly: AnomalyType,
        session_id: str,
        context: dict[str, Any] | None = None,
    ) -> RepairAction:
        """Trigger the most appropriate repair for *anomaly*.

        The repair action is selected by :meth:`_select_repair_action` and
        then executed.  The result is recorded and pushed onto the session's
        HealthStream.
        """
        context = context or {}
        action_type = self._select_repair_action(anomaly, context)
        start_time = time.monotonic()

        action = RepairAction(
            action_type=action_type,
            anomaly=anomaly,
            session_id=session_id,
            timestamp=datetime.now(timezone.utc),
            description=self._repair_description(action_type, anomaly),
        )

        try:
            success = await self._execute_repair(action, context)
        except Exception:
            success = False

        action.success = success
        action.recovery_time_seconds = time.monotonic() - start_time

        if session_id in self._repair_history:
            self._repair_history[session_id].append(action)

        stream = self._streams.get(session_id)
        if stream:
            stream.push(
                HealthEvent(
                    timestamp=datetime.now(timezone.utc),
                    event_type="repair_succeeded" if success else "repair_failed",
                    session_id=session_id,
                    detail={
                        "anomaly_type": anomaly.value,
                        "action_type": action_type.value,
                        "recovery_time": action.recovery_time_seconds,
                    },
                )
            )

        return action

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def generate_report(self, session_id: str) -> ReliabilityReport:
        """Generate a reliability report for *session_id*."""
        repairs = self._repair_history.get(session_id, [])
        anomalies = self._anomaly_history.get(session_id, [])
        return ReliabilityReport.from_session(
            session_id=session_id,
            dashboard=self.dashboard,
            repairs=repairs,
            anomalies=anomalies,
        )

    def global_report(self) -> dict[str, ReliabilityReport]:
        """Generate reliability reports for all tracked sessions."""
        return {sid: self.generate_report(sid) for sid in self._streams}

    def health_check(self) -> dict[str, Any]:
        """Return the harness's own health status."""
        total_repairs = sum(len(r) for r in self._repair_history.values())
        completed_repairs = [
            r
            for repairs in self._repair_history.values()
            for r in repairs
            if r.success is not None
        ]
        success_rate = (
            sum(1 for r in completed_repairs if r.success) / len(completed_repairs)
            if completed_repairs
            else 1.0
        )

        return {
            "status": "healthy",
            "active_sessions": len(self._streams),
            "total_repairs": total_repairs,
            "repair_success_rate": success_rate,
            "total_anomalies": sum(len(a) for a in self._anomaly_history.values()),
            "circuit_breaker_state": self.circuit_breaker.state.name,
            "circuit_breaker_failures": self.circuit_breaker.failure_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Gardening — Automated Entropy Management
    # ------------------------------------------------------------------

    @property
    def garden_health(self) -> GardenHealth:
        """Return the current garden health state."""
        return self._garden_health

    def garden(self) -> GardeningReport | None:
        """Run a single gardening cycle against doc, code, and test paths.

        Lazily initialises the :class:`GardeningSystem` on first call using
        the ``docs_path``, ``src_path``, and ``test_path`` passed at
        construction time.  Subsequent calls return ``None`` if the schedule
        has not elapsed, or run a new cycle and update
        :attr:`garden_health`.

        Returns
        -------
        A :class:`GardeningReport` if a cycle was run, or ``None`` if
        the schedule prevents a run.
        """
        # Lazy init
        if self._garden_system is None:
            doc_agent = (
                DocGardeningAgent(self._docs_path)
                if self._docs_path
                else None
            )
            code_agent = CodeGardeningAgent(self._src_path)
            test_agent = TestGardeningAgent(self._src_path, self._test_path)

            if doc_agent:
                self._garden_system = GardeningSystem(
                    doc_agent=doc_agent,
                    code_agent=code_agent,
                    test_agent=test_agent,
                )
            else:
                # Build a minimal doc agent pointed at the src root so
                # we can still run code/test gardening without docs.
                self._garden_system = GardeningSystem(
                    doc_agent=DocGardeningAgent(self._src_path),
                    code_agent=code_agent,
                    test_agent=test_agent,
                )

        if not self._garden_system.should_run():
            return None

        report = self._garden_system.run_cycle()
        self._garden_system.mark_run()

        self._garden_health = GardenHealth(
            report=report,
            last_cycle=report.timestamp,
            cycles_run=self._garden_health.cycles_run + 1,
            issues_resolved=self._garden_health.issues_resolved + report.auto_fixed,
        )

        return report

    # ------------------------------------------------------------------
    # Repair internals
    # ------------------------------------------------------------------

    _REPAIR_PRIORITY: dict[AnomalyType, list[RepairActionType]] = {
        AnomalyType.HALLUCINATION: [
            RepairActionType.RETRY_WITH_COMPACTION,
            RepairActionType.RETRY_SAME,
            RepairActionType.ESCALATE,
        ],
        AnomalyType.TOOL_ERROR: [
            RepairActionType.RETRY_SAME,
            RepairActionType.RETRY_CHEAPER,
            RepairActionType.ABORT,
        ],
        AnomalyType.INFINITE_LOOP: [
            RepairActionType.RETRY_WITH_COMPACTION,
            RepairActionType.RETRY_SAME,
            RepairActionType.ESCALATE,
        ],
        AnomalyType.COST_SPIKE: [
            RepairActionType.RETRY_CHEAPER,
            RepairActionType.RETRY_WITH_COMPACTION,
            RepairActionType.ABORT,
        ],
        AnomalyType.LATENCY_SPIKE: [
            RepairActionType.RETRY_CHEAPER,
            RepairActionType.RETRY_WITH_COMPACTION,
            RepairActionType.ABORT,
        ],
        AnomalyType.OUTPUT_REGRESSION: [
            RepairActionType.RETRY_SAME,
            RepairActionType.RETRY_WITH_COMPACTION,
            RepairActionType.ESCALATE,
        ],
        AnomalyType.MAST_ANOMALY: [
            RepairActionType.RETRY_WITH_COMPACTION,
            RepairActionType.RETRY_SAME,
            RepairActionType.ESCALATE,
            RepairActionType.ABORT,
        ],
    }

    def _select_repair_action(
        self, anomaly: AnomalyType, context: dict[str, Any]
    ) -> RepairActionType:
        """Select the best untried repair action for *anomaly*."""
        options = self._REPAIR_PRIORITY.get(
            anomaly, [RepairActionType.RETRY_SAME]
        )

        session_repairs = self._repair_history.get(
            context.get("session_id", ""), []
        )
        recent_types = {r.action_type for r in session_repairs[-3:]}

        for option in options:
            if option not in recent_types:
                return option

        return RepairActionType.ESCALATE

    async def _execute_repair(
        self, action: RepairAction, context: dict[str, Any]
    ) -> bool:
        """Dispatch *action* to the appropriate handler."""
        dispatcher = {
            RepairActionType.RETRY_SAME: self._retry_with_policy,
            RepairActionType.RETRY_CHEAPER: self._retry_with_cheaper_model,
            RepairActionType.RETRY_WITH_COMPACTION: self._retry_with_compaction,
            RepairActionType.ESCALATE: self._escalate,
            RepairActionType.ABORT: self._abort,
        }
        handler = dispatcher.get(action.action_type)
        if handler is None:
            return False
        return await handler(context)

    async def _retry_with_policy(self, context: dict[str, Any]) -> bool:
        fn = context.get("retry_fn")
        if fn is None:
            return False
        try:
            await retry(fn, policy=self.retry_policy)
            return True
        except Exception:
            return False

    async def _retry_with_cheaper_model(self, context: dict[str, Any]) -> bool:
        fn = context.get("retry_fn")
        if fn is None:
            return False
        try:
            if self.tracer:
                with self.tracer.span("repair.cheaper_model", "repair"):
                    await retry(fn, policy=RetryPolicy(max_retries=2))
            else:
                await retry(fn, policy=RetryPolicy(max_retries=2))
            return True
        except Exception:
            return False

    async def _retry_with_compaction(self, context: dict[str, Any]) -> bool:
        fn = context.get("retry_fn")
        if fn is None:
            return False
        try:
            if self.tracer:
                with self.tracer.span("repair.context_compaction", "repair"):
                    await retry(fn, policy=RetryPolicy(max_retries=2, base_delay=0.5))
            else:
                await retry(fn, policy=RetryPolicy(max_retries=2, base_delay=0.5))
            return True
        except Exception:
            return False

    async def _escalate(self, context: dict[str, Any]) -> bool:
        return True

    async def _abort(self, context: dict[str, Any]) -> bool:
        sid = context.get("session_id", "unknown")
        self.close_stream(sid)
        return True

    # ------------------------------------------------------------------
    # Detection internals
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_hallucination(trajectory: list[ExecutionStep]) -> bool:
        for step in trajectory:
            if step.action == "reasoning":
                confidence = step.metadata.get("confidence", 1.0)
                if isinstance(confidence, (int, float)) and confidence < 0.3:
                    return True
                output_lower = str(step.output_data).lower()
                hedging = [
                    "i think",
                    "i believe",
                    "it might be",
                    "probably",
                    "i'm not sure but",
                    "to the best of my knowledge",
                ]
                if any(indicator in output_lower for indicator in hedging):
                    return True
        return False

    @staticmethod
    def _detect_tool_error(trajectory: list[ExecutionStep]) -> bool:
        consecutive = 0
        for step in trajectory:
            if step.action == "tool_call" and not step.success:
                consecutive += 1
                if consecutive >= 2:
                    return True
            else:
                consecutive = 0
        return False

    def _detect_infinite_loop(self, trajectory: list[ExecutionStep]) -> bool:
        recent: list[tuple] = []
        for step in trajectory:
            sig = (step.action, str(step.input_data.get("tool_name", ""))[:50])
            recent.append(sig)
            if len(recent) > self.loop_detection_window:
                recent.pop(0)
            if len(recent) == self.loop_detection_window and all(
                a == recent[0] for a in recent
            ):
                return True
        return False

    def _detect_cost_spike(
        self, trajectory: list[ExecutionStep], session_id: str | None = None
    ) -> bool:
        if not session_id:
            return False
        session = self.dashboard.get_session(session_id)
        if not session:
            return False
        for step in trajectory:
            step_cost = step.metadata.get("cost", 0.0)
            if isinstance(step_cost, (int, float)) and step_cost > self.cost_spike_threshold:
                return True
        return False

    def _detect_latency_spike(self, trajectory: list[ExecutionStep]) -> bool:
        for step in trajectory:
            duration_ms = step.metadata.get("duration_ms", 0.0)
            if isinstance(duration_ms, (int, float)):
                duration_sec = duration_ms / 1000.0
                if duration_sec > self.latency_spike_threshold:
                    return True
        return False

    def _detect_output_regression(
        self, trajectory: list[ExecutionStep], session_id: str | None = None
    ) -> bool:
        if not session_id:
            return False
        session = self.dashboard.get_session(session_id)
        if not session:
            return False
        total_ops = max(session.tool_calls, 1)
        error_rate = session.errors / total_ops
        return error_rate >= self.error_rate_threshold

    @staticmethod
    def _repair_description(
        action_type: RepairActionType, anomaly: AnomalyType
    ) -> str:
        descriptions = {
            RepairActionType.RETRY_SAME: f"Retrying same model after {anomaly.value}",
            RepairActionType.RETRY_CHEAPER: f"Falling back to cheaper model after {anomaly.value}",
            RepairActionType.RETRY_WITH_COMPACTION: f"Retrying with context compaction after {anomaly.value}",
            RepairActionType.ESCALATE: f"Escalating {anomaly.value} to human operator",
            RepairActionType.ABORT: f"Aborting session due to unrecoverable {anomaly.value}",
        }
        return descriptions.get(action_type, f"Repairing {anomaly.value}")
