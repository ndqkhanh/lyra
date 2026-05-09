"""Plan Mode auto-skip heuristics.

See ``docs/blocks/02-plan-mode.md`` §Plan complexity heuristic (auto-skip).

Rule of thumb: we only *skip* the plan when the task is short AND clearly
low-stakes. The word "plan" in the task always forces a plan.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_LOW_STAKES_KEYWORDS = re.compile(
    r"\b(typo|fix\s+comment|rename\s+variable|add\s+log|log\s+line|docstring|comment)\b",
    re.IGNORECASE,
)
_FORCE_PLAN_KEYWORDS = re.compile(
    r"\b(plan|design|architect|refactor|migrate|implement|feature|overhaul)\b",
    re.IGNORECASE,
)
_SHORT_TASK_MAX_CHARS = 80
_RECENT_EDITS_FLOW_THRESHOLD = 20


@dataclass
class SkipDecision:
    skip: bool
    reason: str = ""
    signals: list[str] = field(default_factory=list)


def plan_skip_decision(task: str, *, recent_edits_count: int = 0) -> SkipDecision:
    """Return whether Plan Mode should be auto-skipped for this task.

    Args:
        task: The user task text.
        recent_edits_count: Number of files edited in the last 24h window.
            Used as a weak signal for ``already_in_flow``.
    """
    task_lc = task.lower().strip()

    # Hard-force plan if the task explicitly mentions planning / design / refactor.
    m = _FORCE_PLAN_KEYWORDS.search(task_lc)
    if m:
        return SkipDecision(
            skip=False,
            reason=f"force_plan: task mentions {m.group(0)!r}",
            signals=["force_plan_keyword"],
        )

    signals: list[str] = []
    if len(task) < _SHORT_TASK_MAX_CHARS:
        signals.append("short_task")
    if _LOW_STAKES_KEYWORDS.search(task):
        signals.append("low_stakes_keywords")
    if recent_edits_count >= _RECENT_EDITS_FLOW_THRESHOLD:
        signals.append("already_in_flow")

    skip = len(signals) >= 2
    reason = (
        f"signals={signals}; skip={'yes' if skip else 'no'}"
        if signals
        else "no skip signals matched"
    )
    return SkipDecision(skip=skip, reason=reason, signals=signals)
