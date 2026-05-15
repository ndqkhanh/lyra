"""AgentLoop plugins for investigate mode.

Two plugins, both duck-typed against
:class:`lyra_core.agent.loop.AgentLoop`'s hook protocol:

* :class:`InvestigationBudgetPlugin` — ticks the per-turn counter on
  every ``pre_tool_call`` and (for the ``execute_code`` tool) the
  bash counter, then raises :class:`KeyboardInterrupt` on breach so
  the loop's existing dispatch path propagates it as
  ``stopped_by="interrupt"``.
* :class:`TrajectoryLedgerPlugin` — collects every tool call's name,
  arguments, and result for ``on_session_end`` dumping. The output
  shape mirrors DCI-Agent-Lite's ``outputs/runs/<ts>/conversation_full.json``.

Both plugins keep their own state — they do not mutate the AgentLoop
or its store. The runner constructs them, hands them to the loop,
and reads the ledger off the plugin after ``run_conversation``
returns.

Cite: arXiv:2605.05242 §3.5; DCI-Agent-Lite README "outputs/runs/<ts>/".
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..agent.loop import SessionCtx, ToolCtx, ToolResultCtx
from .budget import BudgetExceeded, InvestigationBudget


@dataclass
class InvestigationBudgetPlugin:
    """Enforce the per-turn axis of :class:`InvestigationBudget`.

    The bash and bytes axes are ticked by the tools themselves at
    point of use (the tool knows the byte count; the plugin would
    have to introspect the result). The plugin owns the **turns**
    axis because only the loop sees the dispatch flow.
    """

    budget: InvestigationBudget

    def pre_tool_call(self, ctx: ToolCtx) -> None:
        try:
            self.budget.record_turn()
        except BudgetExceeded as exc:
            raise KeyboardInterrupt(str(exc)) from exc
        try:
            self.budget.check_wall_clock()
        except BudgetExceeded as exc:
            raise KeyboardInterrupt(str(exc)) from exc


@dataclass
class TrajectoryLedgerPlugin:
    """Capture every tool call into a ledger and dump on session end.

    Attributes:
        out_path: When set, ``on_session_end`` writes the ledger as
            JSON. When ``None``, the ledger lives in memory only and
            can be read via :attr:`entries` after the turn.
    """

    out_path: Path | None = None
    entries: list[dict[str, Any]] = field(default_factory=list)

    def post_tool_call(self, ctx: ToolResultCtx) -> None:
        self.entries.append(
            {
                "call_id": ctx.call_id,
                "tool": ctx.tool_name,
                "arguments": dict(ctx.arguments)
                if isinstance(ctx.arguments, Mapping)
                else ctx.arguments,
                "result": ctx.result,
            }
        )

    def on_session_end(self, ctx: SessionCtx) -> None:
        if self.out_path is None:
            return
        payload = {
            "session_id": ctx.session_id,
            "user_text": ctx.user_text,
            "tool_calls": self.entries,
        }
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        self.out_path.write_text(json.dumps(payload, default=str, indent=2))


__all__ = ["InvestigationBudgetPlugin", "TrajectoryLedgerPlugin"]
