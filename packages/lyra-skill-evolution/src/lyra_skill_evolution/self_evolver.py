"""Self-Evolving Skills Engine -- execution trace capture, trace comparison,
improvement distillation, held-out validation, and skill safety auditing.

Implements the TF-TTCL Explore-Reflect-Steer pattern:
1. Explore -- capture execution traces from skill invocations
2. Reflect -- compare successful vs failed traces to identify improvement
   opportunities
3. Steer -- distill improvements into bounded skill edits (SkillOpt pattern)
4. Validate -- verify improvements on held-out test cases before promotion
5. Audit -- Proteus-inspired safety checks: prompt injection, dangerous tools,
   data exfiltration, harmful capabilities
"""

from __future__ import annotations

import re
import time
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .exceptions import EvolutionError
from .trajectory_patcher import Skill, TrajectoryPatch, TrajectoryPatcher


# ── Exceptions ─────────────────────────────────────────────────────────────


class SelfEvolverError(EvolutionError):
    """Base exception for self-evolver errors."""


class SafetyAuditError(SelfEvolverError):
    """Raised when a skill safety audit fails."""


class ValidationError(SelfEvolverError):
    """Raised when improvement validation fails."""


# ── Enums ──────────────────────────────────────────────────────────────────


class TraceOutcome(Enum):
    """Outcome of a skill invocation trace."""

    SUCCESS = auto()
    FAILURE = auto()
    PARTIAL = auto()


class AuditSeverity(Enum):
    """Severity of a safety audit finding."""

    CRITICAL = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()
    PASS = auto()


# ── Execution Trace System ─────────────────────────────────────────────────


@dataclass(frozen=True)
class ExecutionTrace:
    """A single execution trace from a skill invocation.

    Attributes:
        trace_id: Unique identifier for this trace.
        skill_id: The skill that was invoked.
        timestamp: Unix timestamp of the invocation.
        outcome: Whether the invocation succeeded or failed.
        events: Ordered list of event dictionaries.
        duration_ms: Duration of the invocation in milliseconds.
        error: Error message if the invocation failed.
        input_context: Input context provided to the skill.
        output_summary: Summary of the output produced.
    """

    trace_id: str
    skill_id: str
    timestamp: float
    outcome: TraceOutcome
    events: tuple[dict[str, Any], ...] = ()
    duration_ms: float = 0.0
    error: str = ""
    input_context: str = ""
    output_summary: str = ""


@dataclass(frozen=True)
class TraceComparison:
    """Comparison between successful and failed traces for a skill.

    Attributes:
        skill_id: The skill being analyzed.
        failure_patterns: Patterns commonly found in failed traces.
        success_patterns: Patterns commonly found in successful traces.
        divergence_points: Event indices where successful/failed traces differ.
        failure_frequency: Fraction of traces that failed (0.0 to 1.0).
    """

    skill_id: str
    failure_patterns: list[str] = field(default_factory=list)
    success_patterns: list[str] = field(default_factory=list)
    divergence_points: list[int] = field(default_factory=list)
    failure_frequency: float = 0.0


# ── Improvement Distillation ──────────────────────────────────────────────


@dataclass(frozen=True)
class BoundedEdit:
    """A bounded, targeted edit to a skill.

    Attributes:
        edit_id: Unique identifier for this edit.
        skill_id: The skill to edit.
        target_key: The key in skill.content to edit.
        edit_type: Type of edit ('add', 'modify', 'remove').
        old_value: The value being replaced (for modify/remove).
        new_value: The new value (for add/modify).
        justification: Why this edit improves the skill.
    """

    edit_id: str
    skill_id: str
    target_key: str
    edit_type: str
    old_value: Any = None
    new_value: Any = None
    justification: str = ""


@dataclass(frozen=True)
class SkillImprovement:
    """A distilled improvement suggestion for a skill.

    Attributes:
        improvement_id: Unique identifier for this improvement.
        skill_id: The skill to improve.
        trace_refs: Trace IDs that informed this improvement.
        description: Human-readable description of the improvement.
        bounded_edits: List of bounded, targeted edits.
        confidence: Confidence score (0.0 to 1.0).
        estimated_impact: Estimated impact on skill quality (0.0 to 1.0).
    """

    improvement_id: str
    skill_id: str
    trace_refs: tuple[str, ...]
    description: str
    bounded_edits: tuple[BoundedEdit, ...] = ()
    confidence: float = 0.0
    estimated_impact: float = 0.0


# ── Validation ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ValidationResult:
    """Result of validating an improvement on held-out test cases.

    Attributes:
        improvement_id: The improvement that was validated.
        passed: Whether validation passed.
        held_out_tests_passed: Count of passed held-out tests.
        held_out_tests_total: Total count of held-out tests.
        regression_tests_passed: Count of passed regression tests.
        regression_tests_total: Total count of regression tests.
        details: Detailed validation messages.
    """

    improvement_id: str
    passed: bool
    held_out_tests_passed: int = 0
    held_out_tests_total: int = 0
    regression_tests_passed: int = 0
    regression_tests_total: int = 0
    details: tuple[str, ...] = ()


# ── Safety Audit ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SafetyFinding:
    """A single safety finding from auditing a skill.

    Attributes:
        finding_id: Unique identifier for this finding.
        severity: Severity of the finding.
        category: Category (injection, dangerous_tool, exfiltration, ...).
        description: Human-readable description.
        location: Where in the skill the issue was found.
        snippet: The problematic snippet.
        recommendation: How to fix it.
    """

    finding_id: str
    severity: AuditSeverity
    category: str
    description: str
    location: str = ""
    snippet: str = ""
    recommendation: str = ""


@dataclass(frozen=True)
class SafetyAuditReport:
    """Complete safety audit report for a skill.

    Attributes:
        skill_id: The skill that was audited.
        passed: Whether the audit passed (no CRITICAL or HIGH findings).
        findings: List of safety findings.
        critical_count: Count of CRITICAL findings.
        high_count: Count of HIGH findings.
        medium_count: Count of MEDIUM findings.
    """

    skill_id: str
    passed: bool
    findings: tuple[SafetyFinding, ...] = ()
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0

    @property
    def has_issues(self) -> bool:
        """True if there are any CRITICAL or HIGH findings."""
        return self.critical_count > 0 or self.high_count > 0


# ── Safety Patterns ────────────────────────────────────────────────────────

# Prompt injection patterns: attempts to override system instructions
_PROMPT_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bignore\s+(all\s+)?(prior|previous|above)\s+instructions\b"),
    re.compile(r"(?i)\byou\s+(are\s+)?(now|must\s+act\s+as)\s+"),
    re.compile(
        r"(?i)\bdisregard\s+(all\s+)?(prior|previous)\s+(instructions|directions)\b"
    ),
    re.compile(r"(?i)\bnew\s+指令|忽略\s+之前|系统提示\b"),
    re.compile(r"(?i)\boverride\s+(system|safety|prior)\b"),
    re.compile(r"(?i)\byou\s+are\s+(not\s+)?(claude|an\s+ai|a\s+language\s+model)\b"),
    re.compile(r"(?i)\bpretend\s+(you\s+are|to\s+be)\b"),
    re.compile(r"(?i)\bdo\s+(not\s+)?(say|mention|reveal|state)\s+(your\s+)?"),
]

# Dangerous tool invocations: shell commands that can damage the system
_DANGEROUS_TOOL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)\brm\s+(-rf\b|/|\*|\.\s*-\s*r)"),
    re.compile(r"(?i)\bcurl\s+\S+\s*\|\s*(bash|sh|zsh)\b"),
    re.compile(r"(?i)\bwget\s+\S+\s*-O\s*-\s*\|\s*(bash|sh)\b"),
    re.compile(r"(?i)\bchmod\s+777\b"),
    re.compile(r"(?i)\bdd\s+if=\/dev\/"),
    re.compile(r"(?i)\bmv\s+\/\s+\/dev\/null\b"),
    re.compile(r"(?i)\b:\(\)\s*\{[^}]*\}\s*;\s*:\s*:\s*\(\s*\)"),
    re.compile(r"(?i)\beval\s+\$\([^)]+\)"),
    re.compile(r"(?i)\b>\/dev\/sda\b"),
    re.compile(r"(?i)\bsudo\s+(rm|dd|mkfs|fdisk)\b"),
]

# Data exfiltration: sending data to external hosts
_DATA_EXFILTRATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bcurl\s+(-X\s+)?(POST|PUT)\s+\S+\s+(-d|--data)\b"),
    re.compile(r"(?i)\bwget\s+--post-data\b"),
    re.compile(r"(?i)\bnc\s+\S+\s+\d{1,5}\s+<\s+"),
    re.compile(r"(?i)\b(api_key|secret|token|password)\s*[=:]\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)\bngrok\s+http\b"),
    re.compile(r"(?i)\bssh\s+-R\b"),
    re.compile(r"(?i)\b(env|environ|os\.environ|process\.env)\[.*?api.*?key.*?\]"),
    re.compile(r"(?i)\brequests?\.(post|put)\(['\"]https?://[^'\"]+['\"].*?data="),
    re.compile(
        r"(?i)\bopen\s*\(\s*['\"][^'\"]*\.[jJ][sS][oO][nN]['\"]\s*,\s*['\"]w['\"]\s*\)"
    ),
]

# Harmful capabilities: skill features that should raise flags
_HARMFUL_CAPABILITY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(?i)\b(keylogger|keystroke|ransomware|trojan|backdoor|rootkit)\b"
    ),
    re.compile(r"(?i)\b(sql_injection|xs[st]|buffer_overflow|doxing|doxxing)\b"),
    re.compile(r"(?i)\b(password_crack|crack_hash|rainbow_table)\b"),
    re.compile(r"(?i)\b(spoofing|phishing|social_engineering)\b"),
    re.compile(r"(?i)\b(cryptominer|cryptojack|botnet\s+control)\b"),
]


# ── Self-Evolving Skills Engine ────────────────────────────────────────────


class SelfEvolver:
    """Self-evolving skills engine.

    Implements the TF-TTCL (Explore-Reflect-Steer) pattern:

    1. **Explore** -- capture execution traces from skill invocations
    2. **Reflect** -- compare successful vs failed traces to find patterns
    3. **Steer** -- distill improvements and validate before promotion

    Each evolved skill passes through a Proteus-inspired safety gate
    before promotion.
    """

    def __init__(
        self,
        patcher: TrajectoryPatcher | None = None,
        max_traces_per_skill: int = 100,
        min_traces_for_analysis: int = 3,
        held_out_ratio: float = 0.2,
    ) -> None:
        self._patcher = patcher or TrajectoryPatcher()
        self._max_traces_per_skill = max_traces_per_skill
        self._min_traces_for_analysis = min_traces_for_analysis
        self._held_out_ratio = held_out_ratio

        # In-memory trace store, keyed by skill_id
        self._traces: dict[str, list[ExecutionTrace]] = {}
        # Improvement history
        self._improvements: list[SkillImprovement] = []
        # Validation history
        self._validations: list[ValidationResult] = []
        # Safety audit history
        self._audits: list[SafetyAuditReport] = []

    # ── Trace Capture (Explore) ─────────────────────────────────────────

    def capture_execution_trace(
        self,
        skill_id: str,
        outcome: TraceOutcome,
        events: list[dict[str, Any]] | None = None,
        duration_ms: float = 0.0,
        error: str = "",
        input_context: str = "",
        output_summary: str = "",
    ) -> ExecutionTrace:
        """Capture a single execution trace from a skill invocation.

        Args:
            skill_id: The skill that was invoked.
            outcome: Whether the invocation succeeded or failed.
            events: Ordered list of event dictionaries.
            duration_ms: Duration in milliseconds.
            error: Error message if failed.
            input_context: Input context provided to the skill.
            output_summary: Summary of the output produced.

        Returns:
            The captured ExecutionTrace.
        """
        trace_id = f"trace_{skill_id}_{int(time.time() * 1000000)}"
        trace = ExecutionTrace(
            trace_id=trace_id,
            skill_id=skill_id,
            timestamp=time.time(),
            outcome=outcome,
            events=tuple(events or []),
            duration_ms=duration_ms,
            error=error,
            input_context=input_context,
            output_summary=output_summary,
        )

        if skill_id not in self._traces:
            self._traces[skill_id] = []
        self._traces[skill_id].append(trace)

        # Trim to max traces per skill (ring buffer)
        if len(self._traces[skill_id]) > self._max_traces_per_skill:
            self._traces[skill_id] = self._traces[skill_id][
                -self._max_traces_per_skill:
            ]

        return trace

    def get_traces(
        self,
        skill_id: str | None = None,
        outcome: TraceOutcome | None = None,
        limit: int = 0,
    ) -> list[ExecutionTrace]:
        """Get captured execution traces, optionally filtered.

        Args:
            skill_id: If provided, only return traces for this skill.
            outcome: If provided, only return traces with this outcome.
            limit: Maximum number of traces to return (0 = no limit).

        Returns:
            List of matching ExecutionTrace instances.
        """
        traces: list[ExecutionTrace] = []
        if skill_id:
            traces = list(self._traces.get(skill_id, []))
        else:
            for tlist in self._traces.values():
                traces.extend(tlist)

        if outcome is not None:
            traces = [t for t in traces if t.outcome == outcome]

        if limit > 0:
            traces = traces[-limit:]

        return traces

    def clear_traces(self, skill_id: str | None = None) -> None:
        """Clear captured traces, optionally for a single skill.

        Args:
            skill_id: If provided, only clear traces for this skill.
        """
        if skill_id:
            self._traces.pop(skill_id, None)
        else:
            self._traces.clear()

    # ── Trace Analysis -- Reflect Phase ─────────────────────────────────

    def analyze_traces(self, skill_id: str) -> TraceComparison:
        """Compare successful vs failed traces for a skill.

        Implements the Reflect phase: analyze collected traces to
        identify patterns in successes and failures.

        Args:
            skill_id: The skill to analyze.

        Returns:
            A TraceComparison with identified patterns.

        Raises:
            SelfEvolverError: If there are insufficient traces.
        """
        traces = self._traces.get(skill_id, [])
        if len(traces) < self._min_traces_for_analysis:
            raise SelfEvolverError(
                f"Need at least {self._min_traces_for_analysis} traces for analysis, "
                f"got {len(traces)} for skill '{skill_id}'"
            )

        success_traces = [t for t in traces if t.outcome == TraceOutcome.SUCCESS]
        failure_traces = [t for t in traces if t.outcome == TraceOutcome.FAILURE]

        if not failure_traces:
            return TraceComparison(
                skill_id=skill_id,
                success_patterns=self._extract_success_patterns(success_traces),
                failure_frequency=0.0,
            )

        if not success_traces:
            return TraceComparison(
                skill_id=skill_id,
                failure_patterns=self._extract_failure_patterns(failure_traces),
                failure_frequency=1.0,
            )

        # Extract patterns from both groups
        failure_event_types = self._extract_event_type_patterns(failure_traces)
        success_event_types = self._extract_event_type_patterns(success_traces)

        # Find divergence points
        divergence_points = self._find_divergence_points(
            success_traces, failure_traces
        )

        failure_frequency = len(failure_traces) / max(len(traces), 1)

        # Failure patterns: event types more common in failures
        failure_patterns: list[str] = []
        for event_type, count in failure_event_types.most_common(5):
            success_count = success_event_types.get(event_type, 0)
            if count > success_count:
                failure_patterns.append(
                    f"Event '{event_type}' appears {count}x in failures vs "
                    f"{success_count}x in successes"
                )

        # Success patterns: event types more common in successes
        success_patterns: list[str] = []
        for event_type, count in success_event_types.most_common(5):
            failure_count = failure_event_types.get(event_type, 0)
            if count > failure_count:
                success_patterns.append(
                    f"Event '{event_type}' appears {count}x in successes vs "
                    f"{failure_count}x in failures"
                )

        # Add error message patterns from failures
        error_messages = self._extract_error_messages(failure_traces)
        error_counter: Counter[str] = Counter()
        for msg in error_messages:
            if msg:
                short = msg.split("\n")[0][:80]
                error_counter[short] += 1
        for error_msg, count in error_counter.most_common(3):
            failure_patterns.append(f"Common error ({count}x): {error_msg}")

        return TraceComparison(
            skill_id=skill_id,
            failure_patterns=failure_patterns,
            success_patterns=success_patterns,
            divergence_points=divergence_points,
            failure_frequency=failure_frequency,
        )

    def _extract_event_type_patterns(
        self,
        traces: list[ExecutionTrace],
    ) -> Counter[str]:
        """Extract event type frequency patterns from traces.

        Args:
            traces: List of execution traces.

        Returns:
            Counter of event type -> frequency.
        """
        counter: Counter[str] = Counter()
        for trace in traces:
            for event in trace.events:
                event_type = event.get("event_type", "unknown")
                counter[event_type] += 1
        return counter

    def _extract_error_messages(
        self,
        traces: list[ExecutionTrace],
    ) -> list[str]:
        """Extract error messages from failed traces.

        Args:
            traces: List of execution traces (expected failures).

        Returns:
            List of error message strings.
        """
        messages: list[str] = []
        for trace in traces:
            if trace.error:
                messages.append(trace.error)
            for event in trace.events:
                if event.get("event_type") == "error":
                    data = event.get("data", "")
                    if data:
                        messages.append(str(data))
        return messages

    def _extract_success_patterns(
        self,
        traces: list[ExecutionTrace],
    ) -> list[str]:
        """Extract patterns from successful traces.

        Args:
            traces: Successful execution traces.

        Returns:
            List of pattern descriptions.
        """
        if not traces:
            return []

        patterns: list[str] = []
        event_types = self._extract_event_type_patterns(traces)
        for event_type, count in event_types.most_common(3):
            patterns.append(f"Consistent success step '{event_type}' ({count}x)")

        avg_duration = sum(t.duration_ms for t in traces) / max(len(traces), 1)
        patterns.append(f"Average success duration: {avg_duration:.1f}ms")

        return patterns

    def _extract_failure_patterns(
        self,
        traces: list[ExecutionTrace],
    ) -> list[str]:
        """Extract patterns from failed traces.

        Args:
            traces: Failed execution traces.

        Returns:
            List of pattern descriptions.
        """
        if not traces:
            return []

        patterns: list[str] = []
        error_messages = self._extract_error_messages(traces)
        error_counter: Counter[str] = Counter()
        for msg in error_messages:
            short = msg.split("\n")[0][:80]
            error_counter[short] += 1
        for error_msg, count in error_counter.most_common(3):
            patterns.append(f"Error pattern ({count}x): {error_msg}")

        avg_duration = sum(t.duration_ms for t in traces) / max(len(traces), 1)
        patterns.append(f"Average failure duration: {avg_duration:.1f}ms")

        return patterns

    def _find_divergence_points(
        self,
        success_traces: list[ExecutionTrace],
        failure_traces: list[ExecutionTrace],
    ) -> list[int]:
        """Find event indices where successful and failed traces diverge.

        Compares the event sequences; finds positions where the event
        types differ between groups.

        Args:
            success_traces: Successful execution traces.
            failure_traces: Failed execution traces.

        Returns:
            List of event indices where divergence occurs.
        """
        if not success_traces or not failure_traces:
            return []

        def build_sequence(
            traces: list[ExecutionTrace],
        ) -> list[list[str]]:
            return [
                [e.get("event_type", "") for e in t.events] for t in traces
            ]

        success_seqs = build_sequence(success_traces)
        failure_seqs = build_sequence(failure_traces)

        if not success_seqs or not failure_seqs:
            return []

        max_len = max(
            max(len(s) for s in success_seqs) if success_seqs else 0,
            max(len(f) for f in failure_seqs) if failure_seqs else 0,
        )

        divergence: list[int] = []
        for i in range(max_len):
            success_types: set[str] = set()
            for s in success_seqs:
                if i < len(s):
                    success_types.add(s[i])
                else:
                    success_types.add("__end__")

            failure_types: set[str] = set()
            for f in failure_seqs:
                if i < len(f):
                    failure_types.add(f[i])
                else:
                    failure_types.add("__end__")

            if success_types and failure_types and success_types != failure_types:
                divergence.append(i)

        return divergence

    # ── Improvement Distillation -- Steer Phase ─────────────────────────

    def distill_improvements(
        self,
        skill: Skill,
        comparison: TraceComparison | None = None,
    ) -> list[SkillImprovement]:
        """Distill improvements from trace analysis into bounded edits.

        Implements the Steer phase: convert analysis findings into
        concrete, bounded edits per SkillOpt pattern.

        Args:
            skill: The skill to improve.
            comparison: Optional trace comparison to drive improvements.
                If None, runs analyze_traces internally.

        Returns:
            List of SkillImprovement instances with bounded edits.
        """
        if comparison is None:
            comparison = self.analyze_traces(skill.skill_id)

        improvements: list[SkillImprovement] = []

        # Improvement 1: Add error handling patterns from failures
        if comparison.failure_patterns:
            improvements.append(
                self._distill_error_handling(skill, comparison)
            )

        # Improvement 2: Add success patterns
        if comparison.success_patterns:
            improvements.append(
                self._distill_success_patterns(skill, comparison)
            )

        # Improvement 3: Add validation at divergence points
        if comparison.divergence_points:
            improvements.append(
                self._distill_divergence_fix(skill, comparison)
            )

        # Improvement 4: Check for missing capabilities
        improvements.extend(
            self._distill_missing_capabilities(skill, comparison)
        )

        self._improvements.extend(improvements)
        return improvements

    def _distill_error_handling(
        self,
        skill: Skill,
        comparison: TraceComparison,
    ) -> SkillImprovement:
        """Distill an error handling improvement from failure patterns.

        Args:
            skill: The skill to improve.
            comparison: Trace comparison data.

        Returns:
            A SkillImprovement for adding error handling.
        """
        improvement_id = (
            f"impr_{skill.skill_id}_error_handling_{len(self._improvements)}"
        )

        error_types: set[str] = set()
        for pattern in comparison.failure_patterns:
            for error_kw in [
                "ValueError",
                "TypeError",
                "KeyError",
                "IndexError",
                "AttributeError",
                "RuntimeError",
                "IOError",
                "OSError",
            ]:
                if error_kw in pattern:
                    error_types.add(error_kw)

        edits: list[BoundedEdit] = []
        if error_types:
            edits.append(
                BoundedEdit(
                    edit_id=f"{improvement_id}_add_handling",
                    skill_id=skill.skill_id,
                    target_key="error_handling",
                    edit_type="add",
                    new_value={
                        "handled_errors": sorted(error_types),
                        "pattern": (
                            f"try/except for {', '.join(sorted(error_types))}"
                        ),
                    },
                    justification=(
                        f"Detected {len(error_types)} unhandled error types "
                        f"in failure traces: {', '.join(sorted(error_types))}"
                    ),
                )
            )
        elif comparison.failure_patterns:
            edits.append(
                BoundedEdit(
                    edit_id=f"{improvement_id}_add_generic_handling",
                    skill_id=skill.skill_id,
                    target_key="error_handling",
                    edit_type="add",
                    new_value={
                        "handled_errors": ["generic"],
                        "pattern": "Add comprehensive error handling",
                    },
                    justification="Failure traces detected with no specific error type",
                )
            )

        return SkillImprovement(
            improvement_id=improvement_id,
            skill_id=skill.skill_id,
            trace_refs=(),
            description=(
                f"Add error handling for "
                f"{len(error_types) if error_types else 'generic'} error types"
            ),
            bounded_edits=tuple(edits),
            confidence=0.7 if error_types else 0.5,
            estimated_impact=0.3,
        )

    def _distill_success_patterns(
        self,
        skill: Skill,
        comparison: TraceComparison,
    ) -> SkillImprovement:
        """Distill an improvement from successful trace patterns.

        Args:
            skill: The skill to improve.
            comparison: Trace comparison data.

        Returns:
            A SkillImprovement capturing success patterns.
        """
        improvement_id = (
            f"impr_{skill.skill_id}_success_pattern_{len(self._improvements)}"
        )

        success_events: set[str] = set()
        for pattern in comparison.success_patterns:
            for event_kw in [
                "validation",
                "parse",
                "check",
                "verify",
                "retry",
                "backup",
                "log",
                "caching",
                "timeout",
            ]:
                if event_kw in pattern.lower():
                    success_events.add(event_kw)

        edits: list[BoundedEdit] = []
        if success_events:
            edits.append(
                BoundedEdit(
                    edit_id=f"{improvement_id}_formalize_pattern",
                    skill_id=skill.skill_id,
                    target_key="success_patterns",
                    edit_type="add",
                    new_value={
                        "recommended_steps": sorted(success_events),
                        "pattern": "Apply steps that correlate with success",
                    },
                    justification=(
                        f"These event types correlate with successful executions: "
                        f"{', '.join(sorted(success_events))}"
                    ),
                )
            )

        return SkillImprovement(
            improvement_id=improvement_id,
            skill_id=skill.skill_id,
            trace_refs=(),
            description=f"Formalize {len(success_events)} success-correlated patterns",
            bounded_edits=tuple(edits),
            confidence=0.6,
            estimated_impact=0.2,
        )

    def _distill_divergence_fix(
        self,
        skill: Skill,
        comparison: TraceComparison,
    ) -> SkillImprovement:
        """Distill an improvement for divergence points.

        Args:
            skill: The skill to improve.
            comparison: Trace comparison data.

        Returns:
            A SkillImprovement for handling divergence points.
        """
        improvement_id = (
            f"impr_{skill.skill_id}_divergence_{len(self._improvements)}"
        )

        edits: list[BoundedEdit] = []
        if comparison.divergence_points:
            edits.append(
                BoundedEdit(
                    edit_id=f"{improvement_id}_add_validation",
                    skill_id=skill.skill_id,
                    target_key="validation",
                    edit_type="add",
                    new_value={
                        "checkpoints": comparison.divergence_points,
                        "pattern": "Add pre-condition checks at divergence points",
                    },
                    justification=(
                        f"Executions diverge at steps "
                        f"{comparison.divergence_points}. "
                        "Adding validation may prevent failure paths."
                    ),
                )
            )

        return SkillImprovement(
            improvement_id=improvement_id,
            skill_id=skill.skill_id,
            trace_refs=(),
            description=(
                f"Add validation at {len(comparison.divergence_points)} "
                "divergence points"
            ),
            bounded_edits=tuple(edits),
            confidence=0.5,
            estimated_impact=0.25,
        )

    def _distill_missing_capabilities(
        self,
        skill: Skill,
        comparison: TraceComparison,
    ) -> list[SkillImprovement]:
        """Detect missing capabilities from trace analysis.

        Args:
            skill: The skill to improve.
            comparison: Trace comparison data.

        Returns:
            List of SkillImprovement for missing capabilities.
        """
        improvements: list[SkillImprovement] = []

        if "error_handling" not in skill.content:
            improvement_id = (
                f"impr_{skill.skill_id}_missing_error_handling_"
                f"{len(self._improvements)}"
            )
            improvements.append(
                SkillImprovement(
                    improvement_id=improvement_id,
                    skill_id=skill.skill_id,
                    trace_refs=(),
                    description="Add missing error handling capability",
                    bounded_edits=(
                        BoundedEdit(
                            edit_id=f"{improvement_id}_add_cap",
                            skill_id=skill.skill_id,
                            target_key="error_handling",
                            edit_type="add",
                            new_value={
                                "handled_errors": ["generic"],
                            },
                            justification=(
                                "Skill lacks error handling, which correlates "
                                "with failure traces"
                            ),
                        ),
                    ),
                    confidence=0.4,
                    estimated_impact=0.15,
                )
            )

        return improvements

    # ── Improvement Validation ─────────────────────────────────────────

    def validate_improvement(
        self,
        skill_before: Skill,
        improvement: SkillImprovement,
        skill_after: Skill,
        held_out_cases: list[dict[str, Any]] | None = None,
        regression_cases: list[dict[str, Any]] | None = None,
    ) -> ValidationResult:
        """Validate an improvement on held-out test cases before promotion.

        Args:
            skill_before: The skill before the improvement.
            improvement: The improvement being validated.
            skill_after: The skill after the improvement was applied.
            held_out_cases: Held-out test cases to validate against.
            regression_cases: Regression test cases to validate against.

        Returns:
            A ValidationResult indicating pass/fail.
        """
        held_out_tests_passed = 0
        held_out_tests_total = 0
        regression_tests_passed = 0
        regression_tests_total = 0
        details: list[str] = []

        # Validate on held-out test cases
        if held_out_cases:
            held_out_tests_total = len(held_out_cases)
            for case in held_out_cases:
                if self._evaluate_test_case(skill_after, case):
                    held_out_tests_passed += 1
                else:
                    details.append(
                        f"Held-out test failed: {case.get('description', 'unknown')}"
                    )

        # Validate on regression test cases
        if regression_cases:
            regression_tests_total = len(regression_cases)
            for case in regression_cases:
                before_pass = self._evaluate_test_case(skill_before, case)
                after_pass = self._evaluate_test_case(skill_after, case)

                if before_pass and not after_pass:
                    details.append(
                        f"Regression: test '{case.get('description', 'unknown')}' "
                        "passed before but fails after"
                    )
                elif after_pass:
                    regression_tests_passed += 1

        # Determine pass/fail:
        # Held-out tests must have >= 50% pass rate if any exist
        held_out_ok = True
        if held_out_tests_total > 0:
            held_out_ok = held_out_tests_passed / held_out_tests_total >= 0.5

        # Regression tests must have >= 80% pass rate if any exist
        regression_ok = True
        if regression_tests_total > 0:
            regression_ok = (
                regression_tests_passed / regression_tests_total >= 0.8
            )

        passed = held_out_ok and regression_ok

        if not details and passed:
            details.append("All validation checks passed")

        result = ValidationResult(
            improvement_id=improvement.improvement_id,
            passed=passed,
            held_out_tests_passed=held_out_tests_passed,
            held_out_tests_total=held_out_tests_total,
            regression_tests_passed=regression_tests_passed,
            regression_tests_total=regression_tests_total,
            details=tuple(details),
        )

        self._validations.append(result)
        return result

    def _evaluate_test_case(
        self,
        skill: Skill,
        test_case: dict[str, Any],
    ) -> bool:
        """Evaluate whether a skill passes a single test case.

        A test case passes if the skill's content contains the required
        capability or achieves the expected behavior.

        Args:
            skill: The skill to evaluate.
            test_case: A dict with 'capability' and optional 'description'.

        Returns:
            True if the skill passes the test case.
        """
        capability = test_case.get("capability", "")
        if not capability:
            return True

        content = skill.content
        capabilities = content.get("capabilities", [])
        if isinstance(capabilities, list) and capability in capabilities:
            return True

        # Check in steps and other structured content
        for value in content.values():
            if isinstance(value, str) and capability in value:
                return True
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        if capability in str(item.get("name", "")):
                            return True
                        if capability in str(item.get("code", "")):
                            return True

        return False

    def promote_improvements(
        self,
        skill: Skill,
        improvements: list[SkillImprovement],
        validation_results: list[ValidationResult] | None = None,
    ) -> Skill:
        """Promote validated improvements to a skill.

        Only improvements that passed validation are applied.
        Each improvement is converted to patches and applied via the
        TrajectoryPatcher.

        Args:
            skill: The skill to promote improvements to.
            improvements: List of improvements to consider for promotion.
            validation_results: Corresponding validation results. If provided,
                only improvements with passing validation are promoted.

        Returns:
            The skill with all approved improvements applied.
        """
        if not improvements:
            return skill

        valid_results = validation_results or []
        result_map = {r.improvement_id: r for r in valid_results}

        approved: list[SkillImprovement] = []
        for improvement in improvements:
            if not valid_results:
                approved.append(improvement)
            elif improvement.improvement_id in result_map:
                if result_map[improvement.improvement_id].passed:
                    approved.append(improvement)

        if not approved:
            return skill

        # Convert improvements to TrajectoryPatches
        patches: list[TrajectoryPatch] = []
        for improvement in approved:
            for edit in improvement.bounded_edits:
                patch = TrajectoryPatch(
                    patch_id=edit.edit_id,
                    skill_id=edit.skill_id,
                    trajectory_ref=f"improvement_{improvement.improvement_id}",
                    change_description=improvement.description,
                    before_snippet=str(edit.old_value or ""),
                    after_snippet=str(edit.new_value or ""),
                    confidence=improvement.confidence,
                )
                patches.append(patch)

        return self._patcher.batch_apply(skill, patches)

    # ── Skill Safety Audit (Proteus-inspired) ───────────────────────────

    def audit_skill_safety(self, skill: Skill) -> SafetyAuditReport:
        """Perform a lightweight safety audit on a skill.

        Proteus-inspired audit checks for:
        1. Prompt injection patterns
        2. Dangerous tool invocations
        3. Data exfiltration patterns
        4. Harmful capabilities

        Args:
            skill: The skill to audit.

        Returns:
            A SafetyAuditReport with findings.
        """
        findings: list[SafetyFinding] = []

        # Flatten all string values for pattern matching
        all_strings = self._flatten_content_strings(skill.content)

        # Check 1: Prompt injection patterns
        for pattern in _PROMPT_INJECTION_PATTERNS:
            matches = self._find_matches_in_strings(pattern, all_strings)
            for match_str, location in matches:
                findings.append(
                    SafetyFinding(
                        finding_id=f"injection_{len(findings)}",
                        severity=AuditSeverity.CRITICAL,
                        category="prompt_injection",
                        description=(
                            f"Prompt injection pattern detected: "
                            f"'{pattern.pattern[:60]}'"
                        ),
                        location=location,
                        snippet=match_str[:120],
                        recommendation=(
                            "Remove or neutralize injection attempts "
                            "from skill content"
                        ),
                    )
                )

        # Check 2: Dangerous tool invocations
        for pattern in _DANGEROUS_TOOL_PATTERNS:
            matches = self._find_matches_in_strings(pattern, all_strings)
            for match_str, location in matches:
                findings.append(
                    SafetyFinding(
                        finding_id=f"dangerous_tool_{len(findings)}",
                        severity=AuditSeverity.CRITICAL,
                        category="dangerous_tool",
                        description=(
                            f"Dangerous tool invocation: '{pattern.pattern[:60]}'"
                        ),
                        location=location,
                        snippet=match_str[:120],
                        recommendation=(
                            "Replace with safe alternatives; use sandboxed APIs"
                        ),
                    )
                )

        # Check 3: Data exfiltration patterns
        for pattern in _DATA_EXFILTRATION_PATTERNS:
            matches = self._find_matches_in_strings(pattern, all_strings)
            for match_str, location in matches:
                findings.append(
                    SafetyFinding(
                        finding_id=f"exfiltration_{len(findings)}",
                        severity=AuditSeverity.HIGH,
                        category="data_exfiltration",
                        description=(
                            f"Data exfiltration pattern: '{pattern.pattern[:60]}'"
                        ),
                        location=location,
                        snippet=match_str[:120],
                        recommendation=(
                            "Remove data exfiltration vectors from skill content"
                        ),
                    )
                )

        # Check 4: Harmful capabilities
        for pattern in _HARMFUL_CAPABILITY_PATTERNS:
            matches = self._find_matches_in_strings(pattern, all_strings)
            for match_str, location in matches:
                findings.append(
                    SafetyFinding(
                        finding_id=f"harmful_cap_{len(findings)}",
                        severity=AuditSeverity.HIGH,
                        category="harmful_capability",
                        description=(
                            f"Potentially harmful capability: "
                            f"'{pattern.pattern[:60]}'"
                        ),
                        location=location,
                        snippet=match_str[:120],
                        recommendation=(
                            "Review and remove harmful capabilities from skill"
                        ),
                    )
                )

        # Aggregate
        critical_count = sum(
            1 for f in findings if f.severity == AuditSeverity.CRITICAL
        )
        high_count = sum(
            1 for f in findings if f.severity == AuditSeverity.HIGH
        )
        medium_count = sum(
            1 for f in findings if f.severity == AuditSeverity.MEDIUM
        )

        passed = critical_count == 0 and high_count == 0

        report = SafetyAuditReport(
            skill_id=skill.skill_id,
            passed=passed,
            findings=tuple(findings),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
        )

        self._audits.append(report)
        return report

    def _flatten_content_strings(
        self,
        content: dict[str, Any],
    ) -> list[tuple[str, str]]:
        """Flatten a skill content dict into (string_value, location) pairs.

        Args:
            content: The skill content dictionary.

        Returns:
            List of (string_value, location_key) tuples.
        """
        strings: list[tuple[str, str]] = []

        def flatten(d: Any, prefix: str = "") -> None:  # noqa: ANN401
            if isinstance(d, str):
                strings.append((d, prefix or "root"))
            elif isinstance(d, dict):
                for key, value in d.items():
                    flatten(value, f"{prefix}.{key}" if prefix else key)
            elif isinstance(d, list):
                for i, item in enumerate(d):
                    flatten(item, f"{prefix}[{i}]")
            elif isinstance(d, (int, float, bool)):
                strings.append((str(d), prefix or "root"))

        flatten(content)
        return strings

    def _find_matches_in_strings(
        self,
        pattern: re.Pattern[str],
        strings: list[tuple[str, str]],
    ) -> list[tuple[str, str]]:
        """Find regex matches across a list of strings.

        Args:
            pattern: The compiled regex pattern.
            strings: List of (string_value, location) tuples.

        Returns:
            List of (matching_snippet, location) tuples.
        """
        matches: list[tuple[str, str]] = []
        for value, location in strings:
            if pattern.search(value):
                matches.append((value, location))
        return matches

    # ── Complete Evolution Loop ─────────────────────────────────────────

    def run_evolution_cycle(
        self,
        skill: Skill,
        held_out_cases: list[dict[str, Any]] | None = None,
        regression_cases: list[dict[str, Any]] | None = None,
        require_safety_audit: bool = True,
    ) -> tuple[
        Skill,
        list[SkillImprovement],
        ValidationResult | None,
        SafetyAuditReport | None,
    ]:
        """Run one complete self-evolution cycle for a skill.

        Combines trace analysis, improvement distillation, validation,
        safety audit, and promotion in a single pipeline.

        Args:
            skill: The skill to evolve.
            held_out_cases: Held-out test cases for validation.
            regression_cases: Regression test cases for validation.
            require_safety_audit: Whether to require a passing safety audit.

        Returns:
            Tuple of (evolved_skill, improvements, validation, audit_report).

        Raises:
            SelfEvolverError: If there are insufficient traces.
            SafetyAuditError: If the safety audit fails and is required.
        """
        # Step 1: Analyze traces
        try:
            comparison = self.analyze_traces(skill.skill_id)
        except SelfEvolverError:
            return skill, [], None, None

        # Step 2: Distill improvements
        improvements = self.distill_improvements(skill, comparison)
        if not improvements:
            return skill, [], None, None

        # Step 3: Apply improvements to get the evolved skill
        evolved_skill = self.promote_improvements(skill, improvements)

        # Step 4: Safety audit on the evolved skill
        audit_report = self.audit_skill_safety(evolved_skill)
        if require_safety_audit and not audit_report.passed:
            raise SafetyAuditError(
                f"Skill safety audit failed for '{skill.skill_id}': "
                f"{audit_report.critical_count} critical, "
                f"{audit_report.high_count} high findings"
            )

        # Step 5: Validate improvements
        validation = self.validate_improvement(
            skill_before=skill,
            improvement=improvements[0],
            skill_after=evolved_skill,
            held_out_cases=held_out_cases,
            regression_cases=regression_cases,
        )

        if not validation.passed:
            return skill, improvements, validation, audit_report

        # Step 6: Promote (re-apply since validation passed)
        promoted = self.promote_improvements(
            skill, improvements, [validation]
        )

        return promoted, improvements, validation, audit_report

    # ── Property accessors ──────────────────────────────────────────────

    @property
    def traces(self) -> dict[str, list[ExecutionTrace]]:
        """Get all captured execution traces grouped by skill."""
        return {k: list(v) for k, v in self._traces.items()}

    @property
    def improvements(self) -> list[SkillImprovement]:
        """Get all distilled improvements."""
        return list(self._improvements)

    @property
    def validations(self) -> list[ValidationResult]:
        """Get all validation results."""
        return list(self._validations)

    @property
    def audits(self) -> list[SafetyAuditReport]:
        """Get all safety audit reports."""
        return list(self._audits)
