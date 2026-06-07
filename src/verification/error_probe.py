"""
ErrorProbe — Three-stage failure attribution pipeline.

Based on ErrorProbe (arXiv:2604.17658):
1. Local anomaly detection
2. Symptom-driven backward tracing
3. Multi-agent validation team

Includes verified-before-write memory gate to prevent memory corruption.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal


class FailureType(Enum):
    """Types of failures."""

    REASONING_ERROR = "reasoning_error"
    TOOL_ERROR = "tool_error"
    PROVIDER_ERROR = "provider_error"
    MEMORY_ERROR = "memory_error"
    PLANNING_ERROR = "planning_error"
    VERIFICATION_ERROR = "verification_error"
    UNKNOWN = "unknown"


@dataclass
class Anomaly:
    """Detected anomaly in agent execution."""

    step_id: str
    timestamp: datetime
    anomaly_type: str
    confidence: float
    evidence: dict[str, Any] = field(default_factory=dict)
    severity: Literal["low", "medium", "high", "critical"] = "medium"


@dataclass
class Symptom:
    """Symptom leading to failure."""

    description: str
    step_id: str
    related_steps: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class FailureAttribution:
    """Attribution of failure to root cause."""

    failure_type: FailureType
    root_cause_step: str
    contributing_steps: list[str]
    confidence: float
    explanation: str
    symptoms: list[Symptom] = field(default_factory=list)
    anomalies: list[Anomaly] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class ExecutionStep:
    """A single execution step in agent trace."""

    step_id: str
    timestamp: datetime
    action: str  # "tool_call", "reasoning", "memory_access", etc.
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    success: bool
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AnomalyDetector:
    """Detect anomalies in execution trace."""

    def __init__(self):
        """Initialize anomaly detector."""
        self.detection_rules = [
            self._detect_repeated_errors,
            self._detect_circular_reasoning,
            self._detect_memory_inconsistency,
            self._detect_tool_failure_cascade,
            self._detect_confidence_drop,
        ]

    def detect(self, steps: list[ExecutionStep]) -> list[Anomaly]:
        """
        Detect anomalies in execution steps.

        Args:
            steps: Execution trace

        Returns:
            List of detected anomalies
        """
        anomalies: list[Anomaly] = []

        for rule in self.detection_rules:
            detected = rule(steps)
            anomalies.extend(detected)

        return anomalies

    def _detect_repeated_errors(self, steps: list[ExecutionStep]) -> list[Anomaly]:
        """Detect repeated errors in consecutive steps."""
        anomalies = []
        error_streak = 0
        error_steps = []

        for step in steps:
            if not step.success and step.error:
                error_streak += 1
                error_steps.append(step.step_id)

                if error_streak >= 3:
                    anomalies.append(
                        Anomaly(
                            step_id=step.step_id,
                            timestamp=step.timestamp,
                            anomaly_type="repeated_errors",
                            confidence=0.9,
                            evidence={
                                "error_count": error_streak,
                                "error_steps": error_steps[-3:],
                                "last_error": step.error,
                            },
                            severity="high",
                        )
                    )
            else:
                error_streak = 0
                error_steps = []

        return anomalies

    def _detect_circular_reasoning(self, steps: list[ExecutionStep]) -> list[Anomaly]:
        """Detect circular reasoning patterns."""
        anomalies = []
        seen_actions = {}

        for i, step in enumerate(steps):
            action_hash = hash((step.action, str(step.input_data)[:100]))

            if action_hash in seen_actions:
                prev_idx = seen_actions[action_hash]
                if i - prev_idx < 5:  # Within 5 steps
                    anomalies.append(
                        Anomaly(
                            step_id=step.step_id,
                            timestamp=step.timestamp,
                            anomaly_type="circular_reasoning",
                            confidence=0.7,
                            evidence={
                                "repeated_action": step.action,
                                "previous_step": steps[prev_idx].step_id,
                                "steps_apart": i - prev_idx,
                            },
                            severity="medium",
                        )
                    )

            seen_actions[action_hash] = i

        return anomalies

    def _detect_memory_inconsistency(
        self, steps: list[ExecutionStep]
    ) -> list[Anomaly]:
        """Detect memory inconsistencies."""
        anomalies = []
        memory_writes = {}

        for step in steps:
            if step.action == "memory_write":
                key = step.input_data.get("key")
                value = step.input_data.get("value")

                if key in memory_writes:
                    prev_value = memory_writes[key]
                    if value != prev_value:
                        anomalies.append(
                            Anomaly(
                                step_id=step.step_id,
                                timestamp=step.timestamp,
                                anomaly_type="memory_inconsistency",
                                confidence=0.6,
                                evidence={
                                    "key": key,
                                    "previous_value": prev_value,
                                    "new_value": value,
                                },
                                severity="medium",
                            )
                        )

                memory_writes[key] = value

        return anomalies

    def _detect_tool_failure_cascade(
        self, steps: list[ExecutionStep]
    ) -> list[Anomaly]:
        """Detect cascading tool failures."""
        anomalies = []
        tool_failures = []

        for step in steps:
            if step.action == "tool_call" and not step.success:
                tool_failures.append(step)

                if len(tool_failures) >= 2:
                    # Check if failures are related
                    if self._are_failures_related(tool_failures[-2:]):
                        anomalies.append(
                            Anomaly(
                                step_id=step.step_id,
                                timestamp=step.timestamp,
                                anomaly_type="tool_failure_cascade",
                                confidence=0.8,
                                evidence={
                                    "failed_tools": [
                                        s.input_data.get("tool_name")
                                        for s in tool_failures[-2:]
                                    ],
                                    "failure_count": len(tool_failures),
                                },
                                severity="high",
                            )
                        )
            elif step.success:
                tool_failures = []

        return anomalies

    def _detect_confidence_drop(self, steps: list[ExecutionStep]) -> list[Anomaly]:
        """Detect sudden confidence drops."""
        anomalies = []

        for i in range(1, len(steps)):
            prev_conf = steps[i - 1].metadata.get("confidence", 1.0)
            curr_conf = steps[i].metadata.get("confidence", 1.0)

            if prev_conf - curr_conf > 0.3:  # >30% drop
                anomalies.append(
                    Anomaly(
                        step_id=steps[i].step_id,
                        timestamp=steps[i].timestamp,
                        anomaly_type="confidence_drop",
                        confidence=0.5,
                        evidence={
                            "previous_confidence": prev_conf,
                            "current_confidence": curr_conf,
                            "drop": prev_conf - curr_conf,
                        },
                        severity="low",
                    )
                )

        return anomalies

    def _are_failures_related(self, failures: list[ExecutionStep]) -> bool:
        """Check if tool failures are related."""
        if len(failures) < 2:
            return False

        # Check if errors are similar
        errors = [f.error or "" for f in failures]
        if errors[0] and errors[1]:
            # Simple similarity check
            common_words = set(errors[0].split()) & set(errors[1].split())
            return len(common_words) > 2

        return False


class BackwardTracer:
    """Trace backward from failure to find symptoms."""

    def trace(
        self, steps: list[ExecutionStep], failure_step: str
    ) -> list[Symptom]:
        """
        Trace backward from failure step to find symptoms.

        Args:
            steps: Execution trace
            failure_step: ID of the failure step

        Returns:
            List of symptoms
        """
        symptoms: list[Symptom] = []

        # Find failure step
        failure_idx = None
        for i, step in enumerate(steps):
            if step.step_id == failure_step:
                failure_idx = i
                break

        if failure_idx is None:
            return symptoms

        # Trace backward
        for i in range(failure_idx - 1, max(0, failure_idx - 10), -1):
            step = steps[i]

            # Check if this step contributed to failure
            if not step.success:
                symptoms.append(
                    Symptom(
                        description=f"Failed action: {step.action}",
                        step_id=step.step_id,
                        related_steps=[failure_step],
                        evidence={"error": step.error, "action": step.action},
                    )
                )

            # Check for dependency
            if self._is_dependent(steps[failure_idx], step):
                symptoms.append(
                    Symptom(
                        description=f"Dependent action: {step.action}",
                        step_id=step.step_id,
                        related_steps=[failure_step],
                        evidence={
                            "action": step.action,
                            "dependency_type": "data_flow",
                        },
                    )
                )

        return symptoms

    def _is_dependent(self, later_step: ExecutionStep, earlier_step: ExecutionStep) -> bool:
        """Check if later step depends on earlier step."""
        # Simple heuristic: check if output of earlier is in input of later
        earlier_output = str(earlier_step.output_data)
        later_input = str(later_step.input_data)

        # Check for data flow
        if earlier_output and earlier_output in later_input:
            return True

        return False


class ValidationTeam:
    """Multi-agent validation team for failure attribution."""

    def __init__(self):
        """Initialize validation team."""
        self.validators = [
            self._reasoning_validator,
            self._tool_validator,
            self._memory_validator,
        ]

    async def validate(
        self,
        steps: list[ExecutionStep],
        anomalies: list[Anomaly],
        symptoms: list[Symptom],
    ) -> FailureAttribution:
        """
        Validate failure attribution using multiple agents.

        Args:
            steps: Execution trace
            anomalies: Detected anomalies
            symptoms: Traced symptoms

        Returns:
            Failure attribution
        """
        # Run validators in parallel
        votes: list[FailureAttribution] = []

        for validator in self.validators:
            attribution = validator(steps, anomalies, symptoms)
            votes.append(attribution)

        # Aggregate votes
        return self._aggregate(votes)

    def _reasoning_validator(
        self,
        steps: list[ExecutionStep],
        anomalies: list[Anomaly],
        symptoms: list[Symptom],
    ) -> FailureAttribution:
        """Validate from reasoning perspective."""
        # Check for reasoning errors
        reasoning_anomalies = [
            a for a in anomalies if "reasoning" in a.anomaly_type
        ]

        if reasoning_anomalies:
            return FailureAttribution(
                failure_type=FailureType.REASONING_ERROR,
                root_cause_step=reasoning_anomalies[0].step_id,
                contributing_steps=[a.step_id for a in reasoning_anomalies[1:]],
                confidence=0.7,
                explanation="Circular reasoning detected",
                symptoms=symptoms,
                anomalies=anomalies,
            )

        return FailureAttribution(
            failure_type=FailureType.UNKNOWN,
            root_cause_step="",
            contributing_steps=[],
            confidence=0.3,
            explanation="No reasoning errors found",
        )

    def _tool_validator(
        self,
        steps: list[ExecutionStep],
        anomalies: list[Anomaly],
        symptoms: list[Symptom],
    ) -> FailureAttribution:
        """Validate from tool perspective."""
        tool_anomalies = [a for a in anomalies if "tool" in a.anomaly_type]

        if tool_anomalies:
            return FailureAttribution(
                failure_type=FailureType.TOOL_ERROR,
                root_cause_step=tool_anomalies[0].step_id,
                contributing_steps=[a.step_id for a in tool_anomalies[1:]],
                confidence=0.8,
                explanation="Tool failure cascade detected",
                symptoms=symptoms,
                anomalies=anomalies,
            )

        return FailureAttribution(
            failure_type=FailureType.UNKNOWN,
            root_cause_step="",
            contributing_steps=[],
            confidence=0.3,
            explanation="No tool errors found",
        )

    def _memory_validator(
        self,
        steps: list[ExecutionStep],
        anomalies: list[Anomaly],
        symptoms: list[Symptom],
    ) -> FailureAttribution:
        """Validate from memory perspective."""
        memory_anomalies = [a for a in anomalies if "memory" in a.anomaly_type]

        if memory_anomalies:
            return FailureAttribution(
                failure_type=FailureType.MEMORY_ERROR,
                root_cause_step=memory_anomalies[0].step_id,
                contributing_steps=[a.step_id for a in memory_anomalies[1:]],
                confidence=0.6,
                explanation="Memory inconsistency detected",
                symptoms=symptoms,
                anomalies=anomalies,
            )

        return FailureAttribution(
            failure_type=FailureType.UNKNOWN,
            root_cause_step="",
            contributing_steps=[],
            confidence=0.3,
            explanation="No memory errors found",
        )

    def _aggregate(self, votes: list[FailureAttribution]) -> FailureAttribution:
        """Aggregate votes from validators."""
        # Simple majority voting
        failure_types = [v.failure_type for v in votes]
        failure_type_counts = {}

        for ft in failure_types:
            failure_type_counts[ft] = failure_type_counts.get(ft, 0) + 1

        # Find most common
        most_common = max(failure_type_counts, key=failure_type_counts.get)

        # Get votes for most common
        common_votes = [v for v in votes if v.failure_type == most_common]

        if not common_votes:
            return votes[0]

        # Return highest confidence
        return max(common_votes, key=lambda v: v.confidence)


class VerifiedMemoryGate:
    """
    Verified-before-write memory gate.

    Prevents memory corruption from failed traces.
    """

    def __init__(self):
        """Initialize memory gate."""
        self.pending_writes: dict[str, Any] = {}

    def stage_write(self, key: str, value: Any, step_id: str):
        """
        Stage a memory write for verification.

        Args:
            key: Memory key
            value: Value to write
            step_id: Step that generated this write
        """
        self.pending_writes[key] = {"value": value, "step_id": step_id, "verified": False}

    def verify_write(self, key: str, verified: bool):
        """
        Mark a staged write as verified or rejected.

        Args:
            key: Memory key
            verified: Whether write is verified
        """
        if key in self.pending_writes:
            self.pending_writes[key]["verified"] = verified

    def commit_writes(self, memory_store: Any) -> int:
        """
        Commit all verified writes to memory store.

        Args:
            memory_store: Memory store to write to

        Returns:
            Number of writes committed
        """
        committed = 0

        for key, data in self.pending_writes.items():
            if data["verified"]:
                memory_store.set(key, data["value"])
                committed += 1

        # Clear pending writes
        self.pending_writes.clear()

        return committed


class ErrorProbe:
    """
    Three-stage failure attribution pipeline.

    1. Local anomaly detection
    2. Symptom-driven backward tracing
    3. Multi-agent validation team
    """

    def __init__(self):
        """Initialize ErrorProbe."""
        self.detector = AnomalyDetector()
        self.tracer = BackwardTracer()
        self.validators = ValidationTeam()
        self.memory_gate = VerifiedMemoryGate()

    async def diagnose(
        self, steps: list[ExecutionStep], failure_step: str | None = None
    ) -> FailureAttribution:
        """
        Diagnose failure and attribute to root cause.

        Args:
            steps: Execution trace
            failure_step: ID of failure step (auto-detected if None)

        Returns:
            Failure attribution
        """
        # Auto-detect failure if not provided
        if failure_step is None:
            for step in reversed(steps):
                if not step.success:
                    failure_step = step.step_id
                    break

        if failure_step is None:
            return FailureAttribution(
                failure_type=FailureType.UNKNOWN,
                root_cause_step="",
                contributing_steps=[],
                confidence=0.0,
                explanation="No failure detected",
            )

        # Stage 1: Detect anomalies
        anomalies = self.detector.detect(steps)

        # Stage 2: Backward trace
        symptoms = self.tracer.trace(steps, failure_step)

        # Stage 3: Multi-agent validation
        attribution = await self.validators.validate(steps, anomalies, symptoms)

        # Generate recommendations
        attribution.recommendations = self._generate_recommendations(attribution)

        return attribution

    def _generate_recommendations(self, attribution: FailureAttribution) -> list[str]:
        """Generate recommendations based on failure type."""
        recommendations = []

        if attribution.failure_type == FailureType.TOOL_ERROR:
            recommendations.append("Add retry logic with exponential backoff")
            recommendations.append("Validate tool inputs before execution")

        elif attribution.failure_type == FailureType.REASONING_ERROR:
            recommendations.append("Add explicit reasoning checkpoints")
            recommendations.append("Implement circular reasoning detection")

        elif attribution.failure_type == FailureType.MEMORY_ERROR:
            recommendations.append("Enable verified-before-write memory gate")
            recommendations.append("Add memory consistency checks")

        elif attribution.failure_type == FailureType.PROVIDER_ERROR:
            recommendations.append("Implement provider fallback strategy")
            recommendations.append("Add circuit breaker pattern")

        return recommendations
