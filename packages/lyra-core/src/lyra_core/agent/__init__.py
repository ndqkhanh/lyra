"""Hermes-style agent primitives for lyra.

``lyra_core.agent`` provides the canonical run-loop the CLI and
subagent fork both use. The public surface is intentionally tiny so the
REPL driver and task-tool can share the same iteration contract:

- :class:`AgentLoop` — main ``run_conversation`` loop with plugin seams.
- :class:`IterationBudget` — hard cap on LLM calls per turn.
- :class:`TurnResult` — structured result returned to callers.

These live in :mod:`lyra_core.agent.loop`; this package init
re-exports them for convenience.
"""

from __future__ import annotations

from .loop import AgentLoop, IterationBudget, TurnResult

__all__ = ["AgentLoop", "IterationBudget", "TurnResult"]
