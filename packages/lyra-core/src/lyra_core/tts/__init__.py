"""Test-time-scaling (TTS) policies for the Lyra agent loop.

This subpackage hosts the v1.8 *Tournament-Distilled TTS* (Wave-1 §3.1) and
the v2.0 *Intra-attempt MCTS* (Wave-2 §8.1) policies. Both are inference-time
strategies that spend more compute to raise pass-rate on hard tasks.

The contract is:

- A ``TtsPolicy`` consumes a ``Task`` plus a ``Budget`` and returns a
  ``TtsResult`` (best trajectory + a stable summary of the explored space).
- Every policy is composable. ``--tts tournament`` and ``--tts mcts`` can be
  chained as ``--tts tournament+mcts`` so the outer tournament chooses
  between leaves produced by inner MCTS searches.
- Every policy is observable. Each attempt becomes an HIR event so the
  ReasoningBank (``..memory.reasoning_bank``) can distill it later.

This file only re-exports the Phase-0 contracts; concrete policies are
populated from v1.8 onward.
"""
from __future__ import annotations

from .tournament import (
    Attempt,
    AttemptGenerator,
    AttemptResult,
    Discriminator,
    TournamentRound,
    TournamentTts,
    TtsBudget,
    TtsResult,
)

__all__ = [
    "Attempt",
    "AttemptGenerator",
    "AttemptResult",
    "Discriminator",
    "TournamentRound",
    "TournamentTts",
    "TtsBudget",
    "TtsResult",
]
