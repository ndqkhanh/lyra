"""Behaviour-shape guardrails (v3.13 — P0-3).

Steals from ``nousresearch/hermes-agent``'s ``agent/tool_guardrails.py``
(see ``docs/context-engineering-deep-research-v2.md`` §3.2 + §7 P0-3):
budget envelopes alone are too coarse to catch the failure modes
that actually plague long agent loops — the agent calling the same
tool with the same args and getting the same error eight times in a
row, or grinding through twenty iterations without changing any
observable state.

This module is **pure decision**. It owns no state, never emits side
effects, and never executes a tool. It takes a recent slice of trace
events and returns a verdict; callers (the agent loop, the contract
machine, a ``/doctor`` slash) react.

The thresholds mirror Hermes' defaults exactly (the v2 plan's P0-3
section names them):

* ``exact_failure_warn_after = 2`` / ``block_after = 5``
* ``same_tool_failure_warn_after = 3`` / ``halt_after = 8``
* ``no_progress_warn_after = 2`` / ``block_after = 5``

The *exact* streak fires when the same error signature recurs;
the *same-tool* streak fires when the tool name repeats with any
error; the *no-progress* streak fires when the caller's progress
heuristic returns False. All three are computed from the trailing
event run only — a single successful interruption resets the streak.

Why not just extend ``BudgetEnvelope``? Two reasons:

1. ``BudgetEnvelope`` is frozen (its identity is the contract's
   cost contract); behaviour thresholds are operational tuning
   that should be reconfigurable without rebuilding the contract.
2. Guardrails do not "violate" the contract — they advise. The
   contract machine still owns terminal causes; the guardrail
   verdict is upstream of that decision.
"""
from __future__ import annotations

import enum
from collections.abc import Sequence
from dataclasses import dataclass


class GuardrailVerdict(str, enum.Enum):
    """Three-tier verdict.

    * ``OK`` — no concerning streak.
    * ``WARN`` — caller should surface a notice but may continue.
    * ``HALT`` — caller should stop the loop and hand control back
      to the human (or escalate to a fallback strategy).
    """

    OK = "ok"
    WARN = "warn"
    HALT = "halt"


# Verdict priority for "worst wins" selection when multiple streaks
# fire on the same event.
_PRIORITY: dict[GuardrailVerdict, int] = {
    GuardrailVerdict.OK: 0,
    GuardrailVerdict.WARN: 1,
    GuardrailVerdict.HALT: 2,
}


@dataclass(frozen=True)
class TraceEvent:
    """One observed step in the agent loop.

    Built by the agent loop, not by this module. Fields:

    * ``tool`` — tool name, or empty string for non-tool events.
    * ``failed`` — True iff the tool call raised, returned an error
      payload, or otherwise did not produce its intended output.
    * ``error_signature`` — a short, canonical string identifying
      the error (e.g. ``"FileNotFoundError:/tmp/x"``). Empty on
      success. The exactness check compares this verbatim, so the
      caller is responsible for canonicalising messages (strip
      paths, line numbers, etc.) before recording.
    * ``produced_progress`` — caller's verdict on whether this step
      moved the task forward (touched a new file, surfaced new
      tool output, ran a test that gave new information). Default
      True so optional callers don't accidentally trip the
      no-progress signal.
    """

    tool: str = ""
    failed: bool = False
    error_signature: str = ""
    produced_progress: bool = True


@dataclass(frozen=True)
class BehaviourEnvelope:
    """Guardrail thresholds. Defaults match Hermes' canonical set.

    Tune via configuration; passing a different envelope is the
    intended customisation point. All fields are integers (event
    counts), unitless and model-independent.
    """

    exact_failure_warn_after: int = 2
    exact_failure_block_after: int = 5
    same_tool_failure_warn_after: int = 3
    same_tool_failure_halt_after: int = 8
    no_progress_warn_after: int = 2
    no_progress_block_after: int = 5

    def __post_init__(self) -> None:
        # Cheap sanity: warn must trip before block on every axis.
        if self.exact_failure_warn_after > self.exact_failure_block_after:
            raise ValueError(
                "exact_failure_warn_after must be ≤ "
                "exact_failure_block_after"
            )
        if (
            self.same_tool_failure_warn_after
            > self.same_tool_failure_halt_after
        ):
            raise ValueError(
                "same_tool_failure_warn_after must be ≤ "
                "same_tool_failure_halt_after"
            )
        if self.no_progress_warn_after > self.no_progress_block_after:
            raise ValueError(
                "no_progress_warn_after must be ≤ "
                "no_progress_block_after"
            )


@dataclass(frozen=True)
class GuardrailResult:
    """The verdict surfaced to the caller.

    ``reason`` is a human-readable, single-line string suitable for
    appending to a slash-command output or a HIR event payload.
    ``streak`` is the length of the trailing streak that triggered
    the verdict — useful for telemetry.
    """

    verdict: GuardrailVerdict
    reason: str
    streak: int


_OK_RESULT = GuardrailResult(
    verdict=GuardrailVerdict.OK, reason="", streak=0
)


# ---------------------------------------------------------- streak helpers


def _trailing_exact_failure_streak(events: Sequence[TraceEvent]) -> int:
    """Count consecutive trailing failed events with the same
    ``error_signature`` as the most recent event."""
    if not events:
        return 0
    last = events[-1]
    if not last.failed or not last.error_signature:
        return 0
    streak = 0
    for e in reversed(events):
        if e.failed and e.error_signature == last.error_signature:
            streak += 1
        else:
            break
    return streak


def _trailing_same_tool_failure_streak(events: Sequence[TraceEvent]) -> int:
    """Count consecutive trailing failed events whose ``tool``
    matches the most recent event."""
    if not events:
        return 0
    last = events[-1]
    if not last.failed or not last.tool:
        return 0
    streak = 0
    for e in reversed(events):
        if e.failed and e.tool == last.tool:
            streak += 1
        else:
            break
    return streak


def _trailing_no_progress_streak(events: Sequence[TraceEvent]) -> int:
    """Count consecutive trailing events where
    ``produced_progress`` is False (most-recent-first)."""
    if not events or events[-1].produced_progress:
        return 0
    streak = 0
    for e in reversed(events):
        if not e.produced_progress:
            streak += 1
        else:
            break
    return streak


# --------------------------------------------------------------- evaluate


def evaluate(
    events: Sequence[TraceEvent],
    envelope: BehaviourEnvelope | None = None,
) -> GuardrailResult:
    """Pure decision over the trailing run of events.

    Returns the worst verdict triggered by any of the three signals
    (exact-failure / same-tool / no-progress). ``HALT`` beats
    ``WARN`` beats ``OK``. The accompanying ``reason`` and
    ``streak`` describe the *winning* signal so the caller has one
    actionable line.

    ``envelope=None`` uses the canonical defaults.
    """
    if envelope is None:
        envelope = BehaviourEnvelope()
    if not events:
        return _OK_RESULT

    candidates: list[GuardrailResult] = []

    exact = _trailing_exact_failure_streak(events)
    if exact >= envelope.exact_failure_block_after:
        candidates.append(
            GuardrailResult(
                verdict=GuardrailVerdict.HALT,
                reason=f"same error repeated {exact}× in a row",
                streak=exact,
            )
        )
    elif exact >= envelope.exact_failure_warn_after:
        candidates.append(
            GuardrailResult(
                verdict=GuardrailVerdict.WARN,
                reason=f"same error repeated {exact}× in a row",
                streak=exact,
            )
        )

    tool_run = _trailing_same_tool_failure_streak(events)
    if tool_run >= envelope.same_tool_failure_halt_after:
        candidates.append(
            GuardrailResult(
                verdict=GuardrailVerdict.HALT,
                reason=(
                    f"tool {events[-1].tool!r} failed {tool_run}× "
                    "in a row"
                ),
                streak=tool_run,
            )
        )
    elif tool_run >= envelope.same_tool_failure_warn_after:
        candidates.append(
            GuardrailResult(
                verdict=GuardrailVerdict.WARN,
                reason=(
                    f"tool {events[-1].tool!r} failed {tool_run}× "
                    "in a row"
                ),
                streak=tool_run,
            )
        )

    np_run = _trailing_no_progress_streak(events)
    if np_run >= envelope.no_progress_block_after:
        candidates.append(
            GuardrailResult(
                verdict=GuardrailVerdict.HALT,
                reason=f"no progress for {np_run} steps",
                streak=np_run,
            )
        )
    elif np_run >= envelope.no_progress_warn_after:
        candidates.append(
            GuardrailResult(
                verdict=GuardrailVerdict.WARN,
                reason=f"no progress for {np_run} steps",
                streak=np_run,
            )
        )

    if not candidates:
        return _OK_RESULT

    candidates.sort(key=lambda r: _PRIORITY[r.verdict], reverse=True)
    return candidates[0]


__all__ = [
    "BehaviourEnvelope",
    "GuardrailResult",
    "GuardrailVerdict",
    "TraceEvent",
    "evaluate",
]
