"""L312-2 — `lyra ralph` runner.

Anchor: ``docs/165-ralph-autonomous-loop.md`` (snarktank reference) and
``docs/307-ralph-loop-variations-2026.md`` (snarktank vs frankbria vs
vercel-labs comparison).

A Lyra-native re-implementation of the Ralph pattern: fresh-context
iteration over a structured PRD, file-based memory in
``prd.json + progress.txt + git``, completion signalled via either
``<promise>COMPLETE</promise>`` (snarktank) or ``EXIT_SIGNAL: true``
(frankbria), wrapped in an L312-4 :class:`AgentContract` envelope.

Three load-bearing differences from snarktank's bash version:

1. **Refuses ``--dangerously-skip-permissions``.** The runtime relies
   on Lyra's permission bridge + path quarantine + cost guard instead.
2. **Worktree isolation per iteration.** A corrupted iteration cannot
   dirty the parent repo.
3. **Contract-bounded total spend.** Per-iteration cost AND aggregate
   cost are bounded by the contract envelope.
"""
from __future__ import annotations

from .completion import (
    CompletionSignal,
    parse_completion,
    PROMISE_COMPLETE_PATTERN,
    EXIT_SIGNAL_PATTERN,
)
from .prd import Prd, UserStory, load_prd, save_prd
from .progress import ProgressLog
from .runner import RalphRunner, RalphIterationResult


__all__ = [
    "CompletionSignal",
    "EXIT_SIGNAL_PATTERN",
    "PROMISE_COMPLETE_PATTERN",
    "Prd",
    "ProgressLog",
    "RalphIterationResult",
    "RalphRunner",
    "UserStory",
    "load_prd",
    "parse_completion",
    "save_prd",
]
