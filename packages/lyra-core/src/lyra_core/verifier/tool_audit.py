"""Tool-call verification — closing the knowing-doing gap.

Agents frequently *know* which tool to call but fail to *do* it correctly (or
call a tool they *shouldn't* need given what they already know). This module
implements a structured audit pipeline that:

1. **Records** every tool call as a :class:`ToolCallRecord` with the tool name,
   parameters, the reason the agent gave for calling it, and whether it
   succeeded.
2. **Audits** planned-vs-actual tool usage, producing an :class:`AuditFindings`
   report that surfaces unnecessary calls, missing calls, and confidence gaps.
3. **Probes** the agent's hidden-state confidence *before* a tool executes,
   estimating whether the call is truly necessary (the "knowing-doing gap").
4. **Gates** execution behind a configurable confidence threshold via
   :meth:`ToolAuditor.should_execute` so low-confidence calls can be rejected
   before they waste tokens.
5. **Recommends** tool pruning by task context, helping the platform's
   tool-discovery layer deprecate under-used or misused tools.

The knowing-doing gap is captured as a :class:`KnowingDoingGap` — a four-way
classification that distinguishes "doesn't know" from "knows but doesn't
execute correctly".
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Optional


__all__ = [
    "AuditFindings",
    "ConfidenceProbe",
    "ExecutionGate",
    "KnowingDoingGap",
    "ToolAuditor",
    "ToolCallRecord",
    "ToolRemovalSuggestion",
]


# ---------------------------------------------------------------------------
# Core data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolCallRecord:
    """A single tool invocation, logged before and after execution.

    ``reason_given`` is the agent's stated justification for the call — this
    is the primary input for the knowing-doing gap analysis. ``actual_necessity``
    is populated post-hoc by :meth:`ToolAuditor.audit_tool_calls` when the
    auditor can determine whether the call was truly needed.

    ``execution_time_ms`` and ``success`` capture the outcome at the most
    granular level available to the caller.
    """

    tool_name: str
    parameters: dict[str, object] = field(default_factory=dict)
    reason_given: str = ""
    actual_necessity: bool = True
    confidence_score: float = 1.0
    execution_time_ms: float = 0.0
    success: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "reason_given": self.reason_given,
            "actual_necessity": self.actual_necessity,
            "confidence_score": self.confidence_score,
            "execution_time_ms": self.execution_time_ms,
            "success": self.success,
        }


@dataclass(frozen=True)
class KnowingDoingGap:
    """A four-way classification of how the agent handled a tool.

    The four states are:

    * ``recognized=True, executed_correctly=True`` — **No gap**. The agent
      knew about the tool and used it correctly. This is the ideal state.
    * ``recognized=True, executed_correctly=False`` — **Classic knowing-doing
      gap**. The agent knew the tool was needed but made an error in the call
      (wrong parameters, bad order, etc.).
    * ``recognized=False, executed_correctly=False`` — **Ignorance gap**. The
      agent didn't know the tool existed and consequently didn't call it.
    * ``recognized=False, executed_correctly=True`` — **Accidental success**.
      The agent didn't know the tool but got the right outcome through luck or
      an alternative path.

    ``gap_description`` is a human-readable explanation of the gap state.
    """

    tool_name: str
    recognized: bool
    executed_correctly: bool
    gap_description: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "tool_name": self.tool_name,
            "recognized": self.recognized,
            "executed_correctly": self.executed_correctly,
            "gap_description": self.gap_description,
        }


@dataclass(frozen=True)
class AuditFindings:
    """Aggregate audit result for a single plan execution.

    ``unnecessary_calls`` are tools that were invoked but not needed (the
    agent already had the information or could have derived it without a
    tool call). ``missing_calls`` are tools that were needed but not invoked.
    ``confidence_gaps`` are calls whose pre-execution confidence was below a
    meaningful threshold. ``overall_score`` is a 0-1 quality score (1 = perfect)
    computed from the ratio of correct calls.

    The score is computed as::

        1 - (unnecessary + missing + low_confidence) / total_expected

    where ``total_expected`` is the maximum of planned calls and actual calls.
    When no calls were planned or made the score is 1.0 (vacuously perfect).
    """

    unnecessary_calls: tuple[ToolCallRecord, ...]
    missing_calls: tuple[str, ...]
    confidence_gaps: tuple[KnowingDoingGap, ...]
    overall_score: float

    @property
    def total_unnecessary(self) -> int:
        return len(self.unnecessary_calls)

    @property
    def total_missing(self) -> int:
        return len(self.missing_calls)

    @property
    def total_gaps(self) -> int:
        return len(self.confidence_gaps)

    def to_dict(self) -> dict[str, object]:
        return {
            "overall_score": self.overall_score,
            "total_unnecessary": self.total_unnecessary,
            "total_missing": self.total_missing,
            "total_gaps": self.total_gaps,
            "unnecessary_calls": [r.to_dict() for r in self.unnecessary_calls],
            "missing_calls": list(self.missing_calls),
            "confidence_gaps": [g.to_dict() for g in self.confidence_gaps],
        }


@dataclass(frozen=True)
class ToolRemovalSuggestion:
    """A recommendation to prune a tool for a specific task context.

    ``reason`` explains why the tool is a candidate for removal (e.g. never
    used, always fails, always gated). ``confidence`` is the auditor's
    certainty in this recommendation.
    """

    tool_name: str
    task_context: str
    reason: str
    confidence: float


# ---------------------------------------------------------------------------
# Type aliases for pluggable components
# ---------------------------------------------------------------------------

ConfidenceProbe = Callable[
    [ToolCallRecord, str],
    float,
]
"""``(tool_call, context) -> confidence in [0, 1]``.

A value of 1.0 means the probe is certain the tool call is necessary and
correct. A value near 0.0 means the probe believes the call is unnecessary
or likely to fail. Production implementations typically query the agent's
internal logits or a small auxiliary model.
"""

ExecutionGate = Callable[
    [ToolCallRecord, float, float],
    bool,
]
"""``(tool_call, confidence, threshold) -> allow_execution``.

When ``True`` the tool call proceeds. When ``False`` it is blocked and
recorded as a confidence gap.
"""


# ---------------------------------------------------------------------------
# Tool auditor
# ---------------------------------------------------------------------------


def _default_confidence_probe(_tool_call: ToolCallRecord, _context: str) -> float:
    """Default probe that always returns 1.0 (unconditional trust).

    Production callers **must** replace this with a real probe — otherwise
    every call passes the confidence gate and the knowing-doing gap is never
    detected.
    """
    return 1.0


def _default_execution_gate(
    _tool_call: ToolCallRecord,
    confidence: float,
    threshold: float,
) -> bool:
    """Default gate: allow when confidence meets or exceeds threshold."""
    return confidence >= threshold


class ToolAuditor:
    """Verifies tool-call correctness and detects the knowing-doing gap.

    The auditor operates in two modes:

    * **Post-hoc audit** — compare a plan's declared tool calls against what
      actually happened. This produces an :class:`AuditFindings` report.
    * **Pre-flight gate** — probe the agent's confidence *before* executing a
      tool call, and optionally block calls that fall below a threshold.

    Both modes feed into the same gap analysis, so callers get a unified
    picture of where the agent's tool-use quality is breaking down.
    """

    def __init__(
        self,
        *,
        confidence_probe: Optional[ConfidenceProbe] = None,
        execution_gate: Optional[ExecutionGate] = None,
    ) -> None:
        self._confidence_probe: ConfidenceProbe = (
            confidence_probe or _default_confidence_probe
        )
        self._execution_gate: ExecutionGate = (
            execution_gate or _default_execution_gate
        )

    # ---- post-hoc audit ---------------------------------------------------

    def audit_tool_calls(
        self,
        plan: Sequence[str],
        actual_calls: Sequence[ToolCallRecord],
    ) -> AuditFindings:
        """Compare planned vs actual tool usage and return findings.

        Args:
            plan: Tool names that the plan declared would be needed
                (e.g. ``["read_file", "search_code", "write_file"]``).
            actual_calls: The :class:`ToolCallRecord` instances that were
                actually invoked during execution.

        Returns:
            An :class:`AuditFindings` report with unnecessary calls,
            missing calls, confidence gaps, and an overall score.
        """
        planned_set = set(plan)
        actual_names = {c.tool_name for c in actual_calls}
        actual_map: dict[str, list[ToolCallRecord]] = {}
        for c in actual_calls:
            actual_map.setdefault(c.tool_name, []).append(c)

        # Unnecessary: called but not planned.
        unnecessary = [
            c
            for c in actual_calls
            if c.tool_name not in planned_set
        ]

        # Missing: planned but not called.
        missing = sorted(planned_set - actual_names)

        # Confidence gaps: calls whose probe score is below 0.7 at execution
        # time (regardless of whether they were planned).  We reconstruct
        # what the probe *would* have returned by re-probing against a
        # synthetic context since we don't have the live context here.
        # In production the auditor should receive the pre-execution probe
        # scores via the record's ``confidence_score`` field.
        gaps: list[KnowingDoingGap] = []
        for c in actual_calls:
            if c.confidence_score < 0.7:
                gaps.append(
                    KnowingDoingGap(
                        tool_name=c.tool_name,
                        recognized=c.tool_name in planned_set,
                        executed_correctly=c.success,
                        gap_description=(
                            f"Confidence {c.confidence_score:.2f} < 0.7 "
                            f"threshold for tool '{c.tool_name}'. "
                            f"Agent called it anyway but the probe disagreed."
                        ),
                    )
                )
            # Also flag tools the plan expected but didn't appear.
        for name in sorted(planned_set - actual_names):
            gaps.append(
                KnowingDoingGap(
                    tool_name=name,
                    recognized=True,
                    executed_correctly=False,
                    gap_description=(
                        f"Tool '{name}' was planned but never called. "
                        f"The agent recognised it was needed but did not "
                        f"execute it."
                    ),
                )
            )

        # Overall score — each issue type is counted once (no double-count).
        # Missing tools appear in `missing` but their gap entry is explanatory
        # only. Confidence gaps are only counted for calls that were actually
        # made (not for planned-but-missing tools).
        total_expected = max(len(plan), len(actual_calls))
        if total_expected == 0:
            overall_score = 1.0
        else:
            missing_set = set(missing)
            actual_gap_deductions = len(
                [
                    g
                    for g in gaps
                    if not g.executed_correctly
                    and g.tool_name not in missing_set
                ]
            )
            deductions = len(unnecessary) + len(missing) + actual_gap_deductions
            overall_score = max(0.0, 1.0 - deductions / total_expected)

        return AuditFindings(
            unnecessary_calls=tuple(unnecessary),
            missing_calls=tuple(missing),
            confidence_gaps=tuple(gaps),
            overall_score=round(overall_score, 4),
        )

    # ---- pre-flight confidence probe --------------------------------------

    def probe_confidence(
        self,
        tool_call: ToolCallRecord,
        context: str,
    ) -> float:
        """Estimate the agent's confidence before this tool executes.

        The probe is a privacy-safe *internal* signal — it does not require
        running the tool or inspecting its output. A low score suggests the
        agent is outside its competence boundary for this call.

        Args:
            tool_call: The tool call being considered.
            context: The current task context (narration, latest plan step,
                etc.) that the probe can use to assess necessity.

        Returns:
            A float in [0, 1] where higher means more confident the call
            is necessary and correct.
        """
        return self._confidence_probe(tool_call, context)

    # ---- execution gate ---------------------------------------------------

    def should_execute(
        self,
        tool_call: ToolCallRecord,
        *,
        threshold: float = 0.7,
    ) -> bool:
        """Confidence-thresholded execution gate.

        Calls the confidence probe with the tool call's reason as context,
        then checks the result against *threshold*. When the gate returns
        ``False`` the caller should **not** execute the tool and should
        instead log the call as a confidence gap for post-hoc audit.

        Args:
            tool_call: The tool call to evaluate.
            threshold: Minimum confidence score required to proceed.
                Defaults to 0.7.

        Returns:
            ``True`` if the call should execute, ``False`` if it should be
            blocked.
        """
        context = (
            f"Tool: {tool_call.tool_name}\n"
            f"Reason: {tool_call.reason_given}\n"
            f"Parameters: {tool_call.parameters}"
        )
        confidence = self.probe_confidence(tool_call, context)
        return self._execution_gate(tool_call, confidence, threshold)

    # ---- tool pruning -----------------------------------------------------

    def recommend_tool_removal(
        self,
        task_context: str,
        *,
        history: Sequence[ToolCallRecord] = (),
        threshold: float = 0.7,
    ) -> list[ToolRemovalSuggestion]:
        """Suggest tools to prune for this task type.

        Tools are candidates for removal when:

        * They appear in *history* but were never necessary (all
          ``actual_necessity=False``).
        * They appear in *history* but always failed (all ``success=False``).
        * Their average confidence score across all recorded calls is below
          *threshold*.

        Args:
            task_context: A description of the task type (e.g. ``"code review"``,
                ``"test generation"``). Used to contextualise the suggestion.
            history: Historical tool-call records for this task type. When
                empty no suggestions are returned.
            threshold: Confidence threshold below which a tool is considered
                a removal candidate.

        Returns:
            A list of :class:`ToolRemovalSuggestion` sorted by confidence
            (lowest first — strongest candidates at the top).
        """
        if not history:
            return []

        # Group by tool name.
        groups: dict[str, list[ToolCallRecord]] = {}
        for rec in history:
            groups.setdefault(rec.tool_name, []).append(rec)

        suggestions: list[ToolRemovalSuggestion] = []
        for tool_name, records in groups.items():
            all_unnecessary = all(not r.actual_necessity for r in records)
            all_failed = all(not r.success for r in records)
            avg_confidence = sum(r.confidence_score for r in records) / len(records)

            reasons: list[str] = []
            if all_unnecessary:
                reasons.append("never necessary (all calls unnecessary)")
            if all_failed:
                reasons.append("always fails (all calls unsuccessful)")
            if avg_confidence < threshold:
                reasons.append(
                    f"low average confidence ({avg_confidence:.2f} < {threshold})"
                )

            if not reasons:
                continue

            removal_confidence = 1.0 - avg_confidence
            suggestions.append(
                ToolRemovalSuggestion(
                    tool_name=tool_name,
                    task_context=task_context,
                    reason="; ".join(reasons),
                    confidence=round(removal_confidence, 4),
                )
            )

        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions
