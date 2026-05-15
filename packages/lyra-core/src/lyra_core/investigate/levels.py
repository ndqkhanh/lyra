"""ContextLevel — the DCI level0..level4 thermostat on top of Lyra's compactors.

DCI-Agent-Lite ships a five-rung context-management ladder:

* **level0** — no management.
* **level1** — light truncation, drop oldest tool outputs first.
* **level2** — stronger truncation.
* **level3** — truncation + compaction. *Headline 62.9 % BCP run uses this.*
* **level4** — truncation + compaction + per-window summarisation.

Lyra already has the engine for every step of that ladder
(``lyra_core/context/compactor.py``, ``ngc.py``, ``grid.py``,
``relevance.py``). The missing piece is a single dial ops can turn
without rewiring the pipeline. This module is that dial.

A :class:`ContextLevel` value maps to a :class:`ContextLevelPlan`
naming the strategies to compose. The runner reads the plan and
instantiates the strategies; tests verify the mapping directly
without touching the LLM.

Cite: arXiv:2605.05242 §4.5 (RQ5 — context management); DCI-Agent-Lite
README "Context Management Levels".
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ContextLevel(int, Enum):
    """One of the five DCI context-management rungs."""

    OFF = 0
    TRUNCATE_LIGHT = 1
    TRUNCATE_HARD = 2
    TRUNCATE_PLUS_COMPACT = 3
    FULL = 4


@dataclass(frozen=True)
class ContextLevelPlan:
    """The set of strategies a runner must compose for a given level.

    Each flag names a real strategy already shipped in Lyra:

    * ``truncate_oldest_tool_outputs`` -> ``context/compactor.py``
    * ``relevance_filter_tool_outputs`` -> ``context/relevance.py``
    * ``ngc_running_summary`` -> ``context/ngc.py``
    * ``per_window_summary`` -> ``context/grid.py`` window summariser
    """

    level: ContextLevel
    truncate_oldest_tool_outputs: bool
    relevance_filter_tool_outputs: bool
    ngc_running_summary: bool
    per_window_summary: bool

    @property
    def is_no_op(self) -> bool:
        return not any(
            (
                self.truncate_oldest_tool_outputs,
                self.relevance_filter_tool_outputs,
                self.ngc_running_summary,
                self.per_window_summary,
            )
        )


_PLANS: dict[ContextLevel, ContextLevelPlan] = {
    ContextLevel.OFF: ContextLevelPlan(
        level=ContextLevel.OFF,
        truncate_oldest_tool_outputs=False,
        relevance_filter_tool_outputs=False,
        ngc_running_summary=False,
        per_window_summary=False,
    ),
    ContextLevel.TRUNCATE_LIGHT: ContextLevelPlan(
        level=ContextLevel.TRUNCATE_LIGHT,
        truncate_oldest_tool_outputs=True,
        relevance_filter_tool_outputs=False,
        ngc_running_summary=False,
        per_window_summary=False,
    ),
    ContextLevel.TRUNCATE_HARD: ContextLevelPlan(
        level=ContextLevel.TRUNCATE_HARD,
        truncate_oldest_tool_outputs=True,
        relevance_filter_tool_outputs=True,
        ngc_running_summary=False,
        per_window_summary=False,
    ),
    ContextLevel.TRUNCATE_PLUS_COMPACT: ContextLevelPlan(
        level=ContextLevel.TRUNCATE_PLUS_COMPACT,
        truncate_oldest_tool_outputs=True,
        relevance_filter_tool_outputs=True,
        ngc_running_summary=True,
        per_window_summary=False,
    ),
    ContextLevel.FULL: ContextLevelPlan(
        level=ContextLevel.FULL,
        truncate_oldest_tool_outputs=True,
        relevance_filter_tool_outputs=True,
        ngc_running_summary=True,
        per_window_summary=True,
    ),
}


def plan_for_level(level: ContextLevel) -> ContextLevelPlan:
    """Return the (immutable) plan for *level*.

    Raises:
        KeyError: if *level* is not a known :class:`ContextLevel`.
    """
    return _PLANS[level]


__all__ = ["ContextLevel", "ContextLevelPlan", "plan_for_level"]
