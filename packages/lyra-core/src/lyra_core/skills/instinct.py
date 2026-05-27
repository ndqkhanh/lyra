"""Instinct System — ECC-inspired continual learning for skills.

Observes agent interactions, detects patterns, and automatically creates or
refines skill documents. Part of Plan 31's 6-phase lifecycle (LEARN → EVOLVE).

Architecture:
    Observations → Pattern Detection → Confidence Accumulation →
    Skill Proposal → Validation Gate → Auto-Curate

Pattern types detected:
- repeated_tool_sequence: Same tool calls in consistent order
- error_recovery: Successful fix after specific error
- user_correction: Pattern in user steering/corrections
- optimization_pattern: Performance improvement sequence
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ObservationType(str, Enum):
    TOOL_CALL = "tool_call"
    ERROR = "error"
    USER_CORRECTION = "user_correction"
    SUCCESS = "success"
    COMPLETION = "completion"


class PatternType(str, Enum):
    REPEATED_TOOL_SEQUENCE = "repeated_tool_sequence"
    ERROR_RECOVERY = "error_recovery"
    USER_CORRECTION = "user_correction"
    OPTIMIZATION_PATTERN = "optimization_pattern"


@dataclass
class Observation:
    """A single interaction observation."""

    obs_type: ObservationType
    session_id: str
    timestamp: float
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class DetectedPattern:
    """A detected behavioral pattern that may become a skill."""

    pattern_type: PatternType
    name: str
    description: str
    observations: list[str]  # observation references
    confidence: float  # 0.0 → 1.0
    suggested_skill: str = ""  # formatted skill candidate

    @property
    def is_ready(self) -> bool:
        return self.confidence >= 0.7


@dataclass
class InstinctReport:
    """Report from an instinct processing cycle."""

    observations_processed: int
    patterns_detected: int
    patterns_ready: int  # confidence >= threshold
    skills_proposed: int


class InstinctSystem:
    """Detect behavioral patterns and propose new skills automatically.

    Usage::

        instinct = InstinctSystem(min_confidence=0.7)
        instinct.observe(Observation(ObservationType.TOOL_CALL, ...))
        report = instinct.process_cycle()
        for pattern in instinct.ready_patterns():
            proposed_skill = pattern.suggested_skill
    """

    def __init__(self, min_confidence: float = 0.7, window_size: int = 100):
        self.min_confidence = min_confidence
        self.window_size = window_size
        self._observations: list[Observation] = []
        self._patterns: dict[str, DetectedPattern] = {}
        self._tool_sequence_freq: dict[str, int] = defaultdict(int)
        self._error_recovery_freq: dict[str, int] = defaultdict(int)
        self._correction_freq: dict[str, int] = defaultdict(int)

    def observe(self, obs: Observation) -> None:
        """Record an observation."""
        self._observations.append(obs)
        if len(self._observations) > self.window_size * 2:
            self._observations = self._observations[-self.window_size :]

    def process_cycle(self) -> InstinctReport:
        """Process accumulated observations to detect patterns."""
        recent = self._observations[-self.window_size :]
        detected = 0

        detected += self._detect_tool_sequences(recent)
        detected += self._detect_error_recoveries(recent)
        detected += self._detect_correction_patterns(recent)

        ready = sum(1 for p in self._patterns.values() if p.is_ready)
        return InstinctReport(
            observations_processed=len(recent),
            patterns_detected=detected,
            patterns_ready=ready,
            skills_proposed=ready,
        )

    def ready_patterns(self) -> list[DetectedPattern]:
        """Return patterns that have reached confidence threshold."""
        return [p for p in self._patterns.values() if p.is_ready]

    def all_patterns(self) -> list[DetectedPattern]:
        return list(self._patterns.values())

    def reset(self) -> None:
        self._observations.clear()
        self._patterns.clear()
        self._tool_sequence_freq.clear()
        self._error_recovery_freq.clear()
        self._correction_freq.clear()

    def _detect_tool_sequences(self, observations: list[Observation]) -> int:
        """Detect repeated tool call sequences."""
        tool_calls = [
            o for o in observations
            if o.obs_type == ObservationType.TOOL_CALL
        ]
        if len(tool_calls) < 3:
            return 0

        detected = 0
        for i in range(len(tool_calls) - 2):
            seq: list[str] = []
            for j in range(i, min(i + 5, len(tool_calls))):
                name = tool_calls[j].data.get("tool_name", "")
                if name:
                    seq.append(name)

            if len(seq) >= 3:
                key = " → ".join(seq)
                self._tool_sequence_freq[key] += 1
                count = self._tool_sequence_freq[key]

                if count >= 2 and key not in self._patterns:
                    confidence = min(0.95, 0.4 + count * 0.15)
                    self._patterns[key] = DetectedPattern(
                        pattern_type=PatternType.REPEATED_TOOL_SEQUENCE,
                        name=f"sequence-{hash(key) & 0xFFFF:04x}",
                        description=f"Repeated tool sequence: {key}",
                        observations=[],
                        confidence=confidence,
                        suggested_skill=self._format_tool_sequence_skill(key, count),
                    )
                    detected += 1
                elif count >= 2:
                    self._patterns[key].confidence = min(0.95, 0.4 + count * 0.15)

        return detected

    def _detect_error_recoveries(self, observations: list[Observation]) -> int:
        """Detect error → recovery patterns."""
        detected = 0
        for i in range(len(observations) - 1):
            curr = observations[i]
            next_obs = observations[i + 1]

            if curr.obs_type == ObservationType.ERROR and next_obs.obs_type == ObservationType.SUCCESS:
                error_msg = curr.data.get("message", "")[:60]
                recovery = next_obs.data.get("action", "")
                key = f"ERROR:{error_msg} → {recovery}"

                self._error_recovery_freq[key] += 1
                count = self._error_recovery_freq[key]

                if count >= 2 and key not in self._patterns:
                    self._patterns[key] = DetectedPattern(
                        pattern_type=PatternType.ERROR_RECOVERY,
                        name=f"recovery-{hash(key) & 0xFFFF:04x}",
                        description=f"Error recovery: {error_msg} → {recovery}",
                        observations=[],
                        confidence=min(0.9, 0.5 + count * 0.2),
                        suggested_skill=f"## Error Recovery: {error_msg}\nWhen this error occurs, try: {recovery}",
                    )
                    detected += 1

        return detected

    def _detect_correction_patterns(self, observations: list[Observation]) -> int:
        """Detect user correction patterns."""
        corrections = [
            o for o in observations
            if o.obs_type == ObservationType.USER_CORRECTION
        ]
        detected = 0

        for corr in corrections[-20:]:
            topic = corr.data.get("topic", "")[:80]
            if not topic:
                continue
            self._correction_freq[topic] += 1
            count = self._correction_freq[topic]

            if count >= 3 and topic not in self._patterns:
                self._patterns[topic] = DetectedPattern(
                    pattern_type=PatternType.USER_CORRECTION,
                    name=f"correction-{hash(topic) & 0xFFFF:04x}",
                    description=f"Frequent correction on: {topic}",
                    observations=[],
                    confidence=min(0.85, 0.4 + count * 0.15),
                    suggested_skill=f"## Best Practice: {topic}\nBased on repeated user feedback, ensure: {topic}",
                )
                detected += 1
            elif count >= 3:
                self._patterns[topic].confidence = min(0.85, 0.4 + count * 0.15)

        return detected

    def _format_tool_sequence_skill(self, sequence: str, frequency: int) -> str:
        return (
            f"## Automated Workflow (used {frequency}x)\n"
            f"Execute the following tool sequence for this task type:\n"
            f"{sequence}"
        )
