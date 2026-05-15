"""InvestigationRunner — thin wrapper around AgentLoop for DCI mode.

The runner is intentionally small: it takes a :class:`CorpusMount`, an
:class:`InvestigationBudget`, a :class:`ContextLevel`, an LLM, and an
optional output directory, and returns an :class:`InvestigationResult`.
No new loop, no new dispatch path — the runner builds the three
investigate-mode tools, attaches two plugins, and drives the existing
:class:`AgentLoop`.

The seam recommendation from the architect review:

- **Tool binding** via closure factory (mirrors ``make_codesearch_tool``).
- **Budget enforcement** via plugin (``pre_tool_call`` raises
  ``KeyboardInterrupt`` on breach).
- **Trajectory ledger** via plugin (``on_session_end`` writes JSON).
- **Context-level plan** carried on the runner; full strategy
  composition lives in a follow-up bundle (the existing compactor /
  NGC / grid strategies take session state, not raw messages — wiring
  them into the live AgentLoop is a separate seam).

Cite: arXiv:2605.05242; DCI-Agent-Lite ``outputs/runs/<ts>/``.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..agent.loop import AgentLoop, IterationBudget, TurnResult
from .budget import InvestigationBudget
from .compactor import CompactionReport, Summarizer, compact_messages
from .corpus import CorpusMount
from .levels import ContextLevel, ContextLevelPlan, plan_for_level
from .plugin import InvestigationBudgetPlugin, TrajectoryLedgerPlugin
from .prompt import build_system_prompt
from .tools import make_investigate_tools


@dataclass(frozen=True)
class InvestigationResult:
    """The result surface of one investigation turn.

    Mirrors DCI-Agent-Lite's per-run output bundle: the final answer,
    the trajectory ledger, the stop reason, and budget counters at end
    of turn.
    """

    final_text: str
    stopped_by: str
    iterations: int
    tool_calls: tuple[dict[str, Any], ...]
    turns_used: int
    bash_calls_used: int
    bytes_read_used: int
    wall_clock_used: float
    output_dir: Path | None = None
    compaction_reports: tuple[CompactionReport, ...] = ()


@dataclass
class InvestigationRunner:
    """Drive one DCI-style investigation against a corpus mount.

    Attributes:
        llm: Anything with a ``generate(messages, tools)`` method or a
            callable equivalent. Same contract as ``AgentLoop.llm``.
        mount: Read-only corpus mount that bounds all tool calls.
        budget: Per-axis caps. Tests can inject a fast clock.
        context_level: One of ``ContextLevel.OFF..FULL``. The plan
            is carried on the result for inspection; full pipeline
            application is a follow-up bundle.
        output_dir: When set, the trajectory ledger lands at
            ``<output_dir>/conversation_full.json`` and the final
            text at ``<output_dir>/final.txt``.
    """

    llm: Any
    mount: CorpusMount
    budget: InvestigationBudget = field(default_factory=InvestigationBudget)
    context_level: ContextLevel = ContextLevel.TRUNCATE_PLUS_COMPACT
    output_dir: Path | None = None
    summarizer: Summarizer | None = None
    max_tool_outputs_kept: int = 6

    @property
    def context_plan(self) -> ContextLevelPlan:
        """The strategy plan for the current :attr:`context_level`."""
        return plan_for_level(self.context_level)

    def run(self, question: str, *, session_id: str | None = None) -> InvestigationResult:
        """Run one investigation against *question*. Always returns a result.

        The runner never raises :class:`BudgetExceeded`; budget breaches
        terminate the turn with ``stopped_by="interrupt"``.
        """
        sid = session_id or f"investigate-{int(time.time())}"
        tools = make_investigate_tools(mount=self.mount, budget=self.budget)
        out_path = (
            self.output_dir / "conversation_full.json"
            if self.output_dir is not None
            else None
        )
        ledger = TrajectoryLedgerPlugin(out_path=out_path)
        budget_plugin = InvestigationBudgetPlugin(budget=self.budget)

        system_prompt = build_system_prompt(self.mount)
        user_text = f"{system_prompt}\n\nQuestion: {question}"

        # Wrap the LLM so every generate(messages,tools) call first
        # runs the messages through the level0..4 compactor. Reports
        # are accumulated on the wrapper for the result surface.
        level_llm = _LevelAwareLLM(
            inner=self.llm,
            plan=self.context_plan,
            summarizer=self.summarizer,
            max_tool_outputs_kept=self.max_tool_outputs_kept,
        )

        loop = AgentLoop(
            llm=level_llm,
            tools=tools,
            store=_NullStore(),
            plugins=[budget_plugin, ledger],
            budget=IterationBudget(max=self.budget.max_turns),
        )
        turn = loop.run_conversation(user_text, session_id=sid)

        if self.output_dir is not None:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            (self.output_dir / "final.txt").write_text(turn.final_text)
            (self.output_dir / "question.txt").write_text(question)

        return _result_from_turn(
            turn, self.budget, self.output_dir, tuple(level_llm.reports),
        )


class _NullStore:
    """Minimal store stub — AgentLoop reaches for ``append_message`` and ``start_session``."""

    def start_session(self, *, session_id: str) -> None:
        return None

    def append_message(self, *, session_id: str, role: str, content: str, **_: Any) -> None:
        return None


def _result_from_turn(
    turn: TurnResult,
    budget: InvestigationBudget,
    output_dir: Path | None,
    compaction_reports: tuple[CompactionReport, ...] = (),
) -> InvestigationResult:
    return InvestigationResult(
        final_text=turn.final_text,
        stopped_by=turn.stopped_by,
        iterations=turn.iterations,
        tool_calls=tuple(turn.tool_calls),
        turns_used=budget.turns_used,
        bash_calls_used=budget.bash_calls_used,
        bytes_read_used=budget.bytes_read_used,
        wall_clock_used=budget.wall_clock_used,
        output_dir=output_dir,
        compaction_reports=compaction_reports,
    )


@dataclass
class _LevelAwareLLM:
    """LLM shim that applies :func:`compact_messages` on every call.

    Architect-recommended seam: the AgentLoop's :meth:`_invoke_llm`
    calls ``self.llm.generate(messages=..., tools=...)``. Wrapping the
    LLM (not the AgentLoop) keeps the compaction logic on a clean
    boundary without touching any seam inside the loop.
    """

    inner: Any
    plan: ContextLevelPlan
    summarizer: Summarizer | None = None
    max_tool_outputs_kept: int = 6
    reports: list[CompactionReport] = field(default_factory=list)

    def generate(self, *, messages: list[dict], tools: list[dict]) -> Any:
        compacted, report = compact_messages(
            messages,
            self.plan,
            max_tool_outputs_kept=self.max_tool_outputs_kept,
            summarizer=self.summarizer,
        )
        self.reports.append(report)
        return self.inner.generate(messages=compacted, tools=tools)


__all__ = ["InvestigationResult", "InvestigationRunner"]
