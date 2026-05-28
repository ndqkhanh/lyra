"""Phase 13.3 — Intent-Based Behavioral Security.

Continuous monitoring of action sequences for intent deviation and
behavioural anomalies. Records every action across sessions and flags
deviations from expected patterns, learned baselines, or statistical
norms.
"""
from __future__ import annotations

import time
import uuid
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = [
    "ActionRecord",
    "BehavioralBaseline",
    "IntentDeviation",
    "IntentMonitor",
]


@dataclass(frozen=True)
class ActionRecord:
    """A single tool call recorded for behavioural monitoring."""

    action_id: str
    tool_name: str
    parameters: tuple[tuple[str, str], ...]
    timestamp: float
    stated_goal: str
    session_id: str


@dataclass(frozen=True)
class IntentDeviation:
    """A detected deviation from expected behaviour."""

    deviation_id: str
    expected_pattern: str
    actual_actions: tuple[str, ...]
    severity: float  # 0.0 … 1.0
    description: str
    detected_at: float


@dataclass(frozen=True)
class BehavioralBaseline:
    """Statistical baseline of expected behaviour for a task type."""

    task_type: str
    typical_tools: tuple[str, ...]
    typical_sequence_length: int
    avg_tool_calls_per_task: float
    anomaly_threshold: float = 2.0


class IntentMonitor:
    """Continuous intent-deviation monitor.

    Usage::

        monitor = IntentMonitor()
        action = ActionRecord(
            action_id="act-001",
            tool_name="read_file",
            parameters=(("path", "/etc/passwd"),),
            timestamp=time.time(),
            stated_goal="read user database",
            session_id="sess-001",
        )
        monitor.record_action(action)

        deviation = monitor.check_deviation(
            action,
            expected_sequence=["read_file", "grep", "write_file"],
        )
    """

    def __init__(self) -> None:
        self._actions: dict[str, list[ActionRecord]] = defaultdict(list)
        self._deviations: list[IntentDeviation] = []

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record_action(self, action: ActionRecord) -> None:
        """Log an action for monitoring."""
        self._actions[action.session_id].append(action)

    # ------------------------------------------------------------------
    # Deviation detection
    # ------------------------------------------------------------------

    def check_deviation(
        self,
        action: ActionRecord,
        expected_sequence: list[str],
    ) -> IntentDeviation | None:
        """Check if *action* deviates from the expected sequence.

        Returns an ``IntentDeviation`` when:
        * The action's ``tool_name`` is not present in the expected
          sequence.
        * The number of actions recorded for the session exceeds
          twice the length of the expected sequence.
        """
        session_actions = self._actions.get(action.session_id, [])

        # Tool name not expected
        if action.tool_name not in expected_sequence:
            return IntentDeviation(
                deviation_id=f"dev-{uuid.uuid4().hex[:12]}",
                expected_pattern=", ".join(expected_sequence),
                actual_actions=tuple(a.tool_name for a in session_actions),
                severity=0.65,
                description=(
                    f"Unexpected tool {action.tool_name!r} — "
                    f"not in expected sequence."
                ),
                detected_at=time.time(),
            )

        # Sequence length exceeds expected by 2x
        if len(session_actions) > len(expected_sequence) * 2:
            return IntentDeviation(
                deviation_id=f"dev-{uuid.uuid4().hex[:12]}",
                expected_pattern=", ".join(expected_sequence),
                actual_actions=tuple(a.tool_name for a in session_actions),
                severity=0.5,
                description=(
                    f"Session action count ({len(session_actions)}) "
                    f"exceeds 2x expected sequence length "
                    f"({len(expected_sequence)})."
                ),
                detected_at=time.time(),
            )

        return None

    def analyze_session(self, session_id: str) -> list[IntentDeviation]:
        """Post-hoc analysis of a full session for intent deviations.

        Performs statistical checks against any baselines that match
        the actions found in the session and flags tools used that do
        not appear in any known baseline.
        """
        session_actions = self._actions.get(session_id, [])
        if not session_actions:
            return []

        deviations: list[IntentDeviation] = []
        tool_names = [a.tool_name for a in session_actions]
        unique_tools = set(tool_names)

        # Find all tools that appear in the session
        frequent_tools = [
            t for t in unique_tools
            if tool_names.count(t) >= 2
        ]

        # Treat tools used twice as "typical" for this session; flag
        # tools used only once as potentially anomalous (unless they
        # are the only tools used).
        if len(frequent_tools) >= 1:
            for tool in unique_tools:
                if tool not in frequent_tools:
                    deviations.append(
                        IntentDeviation(
                            deviation_id=f"dev-{uuid.uuid4().hex[:12]}",
                            expected_pattern=", ".join(frequent_tools),
                            actual_actions=tuple(tool_names),
                            severity=0.45,
                            description=(
                                f"Tool {tool!r} appears only once in "
                                f"session {session_id!r}; typical tools "
                                f"are: {', '.join(frequent_tools)}."
                            ),
                            detected_at=time.time(),
                        )
                    )

        # Flag sequence length outlier: > 2x the median across sessions
        all_lengths = [
            len(acts) for sid, acts in self._actions.items()
            if sid != session_id
        ]
        if all_lengths:
            median_len = sorted(all_lengths)[len(all_lengths) // 2]
            threshold = median_len * 2
            if len(session_actions) > threshold and threshold > 0:
                deviations.append(
                    IntentDeviation(
                        deviation_id=f"dev-{uuid.uuid4().hex[:12]}",
                        expected_pattern=f"typical sequence length ≤{threshold}",
                        actual_actions=tuple(tool_names),
                        severity=0.55,
                        description=(
                            f"Session {session_id!r} has "
                            f"{len(session_actions)} actions, exceeding "
                            f"2x median ({median_len})."
                        ),
                        detected_at=time.time(),
                    )
                )

        self._deviations.extend(deviations)
        return deviations

    # ------------------------------------------------------------------
    # Baseline learning
    # ------------------------------------------------------------------

    def build_baseline(
        self,
        task_type: str,
        historical_sessions: Sequence[Sequence[ActionRecord]],
    ) -> BehavioralBaseline:
        """Learn typical behavioural patterns from historical sessions.

        Args:
            task_type: A label for the kind of task (e.g. ``"code_review"``).
            historical_sessions: Collection of past action sequences.

        Returns:
            A ``BehavioralBaseline`` capturing the observed norms.
        """
        all_tool_names: list[str] = []
        session_lengths: list[int] = []

        for session in historical_sessions:
            names = [a.tool_name for a in session]
            all_tool_names.extend(names)
            session_lengths.append(len(names))

        typical_tools = tuple(sorted(set(all_tool_names)))
        typical_sequence_length = (
            sorted(session_lengths)[len(session_lengths) // 2]
            if session_lengths
            else 0
        )
        avg_tool_calls = (
            len(all_tool_names) / len(historical_sessions)
            if historical_sessions
            else 0.0
        )

        return BehavioralBaseline(
            task_type=task_type,
            typical_tools=typical_tools,
            typical_sequence_length=typical_sequence_length,
            avg_tool_calls_per_task=avg_tool_calls,
        )

    # ------------------------------------------------------------------
    # Anomaly detection
    # ------------------------------------------------------------------

    def detect_anomalies(
        self,
        actions: Sequence[ActionRecord],
        baseline: BehavioralBaseline,
    ) -> list[IntentDeviation]:
        """Statistical anomaly detection against a learned baseline.

        Flags:
        * Sessions where tool call count exceeds
          ``avg_tool_calls_per_task * anomaly_threshold``.
        * Actions using a tool not present in the baseline's
          ``typical_tools``.
        """
        deviations: list[IntentDeviation] = []
        now = time.time()

        # Length anomaly
        tool_count = len(actions)
        threshold = baseline.avg_tool_calls_per_task * baseline.anomaly_threshold
        if tool_count > threshold and threshold > 0:
            deviations.append(
                IntentDeviation(
                    deviation_id=f"dev-{uuid.uuid4().hex[:12]}",
                    expected_pattern=(
                        f"≤{threshold:.1f} tool calls "
                        f"(baseline: {baseline.avg_tool_calls_per_task:.1f} × "
                        f"threshold: {baseline.anomaly_threshold})"
                    ),
                    actual_actions=tuple(a.tool_name for a in actions),
                    severity=min(1.0, tool_count / (threshold * 2)),
                    description=(
                        f"Session has {tool_count} tool calls, exceeding "
                        f"baseline threshold of {threshold:.1f}."
                    ),
                    detected_at=now,
                )
            )

        # Unexpected tool anomaly
        baseline_tools = set(baseline.typical_tools)
        for action in actions:
            if action.tool_name not in baseline_tools and baseline_tools:
                deviations.append(
                    IntentDeviation(
                        deviation_id=f"dev-{uuid.uuid4().hex[:12]}",
                        expected_pattern=(
                            "tools in {'"
                            + "', '".join(sorted(baseline_tools))
                            + "'}}"
                        ),
                        actual_actions=(action.tool_name,),
                        severity=0.7,
                        description=(
                            f"Tool {action.tool_name!r} is not part of "
                            f"the {baseline.task_type!r} baseline."
                        ),
                        detected_at=now,
                    )
                )

        self._deviations.extend(deviations)
        return deviations

    # ------------------------------------------------------------------
    # Risk scoring
    # ------------------------------------------------------------------

    def get_risk_score(self, session_id: str) -> float:
        """Aggregate risk score for a session, normalised to 0–1.

        The score is derived from the number of deviations multiplied
        by their average severity, capped at 1.0.
        """
        session_deviations = [
            d
            for d in self._deviations
            if any(
                a in d.actual_actions
                for a in self._actions.get(session_id, [])
            )
        ]
        if not session_deviations:
            return 0.0

        deviation_count = len(session_deviations)
        avg_severity = (
            sum(d.severity for d in session_deviations) / deviation_count
        )
        raw = deviation_count * avg_severity
        # Normalise: assume 20 deviations at severity 1.0 = max
        return min(1.0, raw / 20.0)

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, object]:
        """Return aggregate monitoring statistics."""
        total_actions = sum(len(v) for v in self._actions.values())
        return {
            "total_actions": total_actions,
            "deviations_detected": len(self._deviations),
            "avg_risk_score": (
                sum(
                    self.get_risk_score(sid)
                    for sid in self._actions
                )
                / len(self._actions)
                if self._actions
                else 0.0
            ),
            "sessions_monitored": len(self._actions),
        }
