"""Tournament-Distilled Test-Time Scaling for Lyra (v1.8 Wave-1 §3.1).

Inspired by *Scaling Test-Time Compute for Agentic Coding*
(Meta SI Labs et al., 2026 — arXiv:2604.16529, mirrored under
``papers/meta-tts-agentic-coding.pdf``).

Two-stage scheme:

1. **Recursive Tournament Voting** — N parallel attempts; pair them up;
   pick a winner per pair via a learned discriminator (``Discriminator``);
   recurse until one attempt remains. Designed for *parallel* exploration.
2. **Parallel-Distill-Refine** — feed the tournament winner plus distilled
   summaries of the losers back into a single sequential refinement pass.

The Phase-1 implementation in this file is intentionally minimal:

- bracket logic and budget honouring are real and tested,
- distillation is a structured *summary string* (the LLM-driven refine
  pass is reserved for Phase 2),
- per-attempt scoring is ``wins / participations`` (no PRM yet).

Phase 2 will plug ``..verifier.prm`` into the discriminator and
``..verifier.tdd_reward`` into the attempt scorer; Phase 3 will use the
``..routing.cascade`` to pick a different (cheaper) model per attempt to
beat the diversity-collapse failure mode flagged in
``docs/research/diversity-collapse-analysis.md``.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


@dataclass(frozen=True)
class TtsBudget:
    """Hard caps on a single TTS run.

    The runner is responsible for honouring all three; the first cap to
    bind wins. ``max_attempts == 0`` is invalid and raises at construction.
    """

    max_attempts: int
    max_wall_clock_s: float
    max_total_tokens: int

    def __post_init__(self) -> None:
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be > 0")
        if self.max_wall_clock_s <= 0:
            raise ValueError("max_wall_clock_s must be > 0")
        if self.max_total_tokens <= 0:
            raise ValueError("max_total_tokens must be > 0")


@dataclass(frozen=True)
class Attempt:
    """A single candidate solution emitted by the inner agent loop."""

    id: str
    artefact: str  # e.g. unified diff or REPL transcript
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AttemptResult:
    """Score + verifier verdict for a single attempt."""

    attempt_id: str
    score: float           # [0, 1] — combined verifier + discriminator
    passed_tdd_gate: bool
    notes: str = ""


@dataclass(frozen=True)
class TournamentRound:
    """One pairing round in the recursive tournament."""

    round_index: int
    pairs: tuple[tuple[str, str], ...]  # (attempt_id, attempt_id)
    winners: tuple[str, ...]


@dataclass(frozen=True)
class TtsResult:
    """The outcome of a single Tournament-TTS run."""

    winning_attempt: Attempt
    winning_score: float
    rounds: tuple[TournamentRound, ...]
    losers: tuple[Attempt, ...]              # for distill-refine downstream
    distilled_summary: str                    # Parallel-Distill-Refine output
    total_tokens_used: int
    wall_clock_s: float
    # v1.8 Phase 6 (Diversity-Collapse Hardening, arXiv:2604.18005):
    # ``effective_diversity`` of the attempt-artefact pool. A drift-gate can
    # refuse to commit a tournament whose pool collapsed below a threshold
    # (the "Compute Efficiency Paradox" failure mode).
    pool_diversity: float = 0.0


class Discriminator(Protocol):
    """Pairwise judge: given two attempts, returns the better one."""

    def compare(self, a: Attempt, b: Attempt) -> Attempt:
        """Return the winner. Implementations must be deterministic
        for a fixed (a, b, model) tuple."""
        ...


class AttemptGenerator(Protocol):
    """Produces an Attempt from an upstream Task description."""

    def generate(self, task_description: str, attempt_index: int) -> Attempt: ...


class TournamentTts:
    """Two-stage Tournament-TTS policy.

    Phase 0: contract only. ``run`` raises ``NotImplementedError`` so the
    Phase-1 implementation has a clear target shape.
    """

    def __init__(
        self,
        generator: AttemptGenerator,
        discriminator: Discriminator,
        budget: TtsBudget,
    ) -> None:
        self._generator = generator
        self._discriminator = discriminator
        self._budget = budget

    def run(self, task_description: str) -> TtsResult:
        wall_start = time.monotonic()
        attempts: list[Attempt] = []
        tokens_used = 0

        for attempt_idx in range(self._budget.max_attempts):
            if time.monotonic() - wall_start > self._budget.max_wall_clock_s:
                break
            if tokens_used >= self._budget.max_total_tokens:
                break
            attempt = self._generator.generate(task_description, attempt_idx)
            attempts.append(attempt)
            tokens_used += _approx_token_count(attempt.artefact)

        if not attempts:
            raise RuntimeError(
                "TournamentTts.run produced zero attempts; "
                "check the AttemptGenerator and budget."
            )

        # v1.8 Phase 6 (Diversity-Collapse Hardening, arXiv:2604.18005):
        # Enforce Nominal Group Technique's blind-generation rule before any
        # pairwise comparison can leak information across attempts. The guard
        # is intentionally accessed via the module so test spies (and future
        # telemetry hooks) can patch it.
        from lyra_core import diversity  # local import: keeps the patch surface

        fingerprints = [
            str(a.metadata.get("context_fingerprint", a.id)) for a in attempts
        ]
        diversity.ngt_attempt_independence_guard(fingerprints)
        pool_diversity = diversity.effective_diversity(
            [a.artefact for a in attempts]
        )

        wins: dict[str, int] = {a.id: 0 for a in attempts}
        participations: dict[str, int] = {a.id: 0 for a in attempts}
        rounds: list[TournamentRound] = []

        current = list(attempts)
        round_index = 0
        while len(current) > 1:
            pairs: list[tuple[str, str]] = []
            winner_ids: list[str] = []
            i = 0
            while i + 1 < len(current):
                a, b = current[i], current[i + 1]
                pairs.append((a.id, b.id))
                participations[a.id] += 1
                participations[b.id] += 1
                winner = self._discriminator.compare(a, b)
                wins[winner.id] += 1
                winner_ids.append(winner.id)
                i += 2
            if i < len(current):
                # Bye: odd attempt advances without a comparison.
                winner_ids.append(current[i].id)
            rounds.append(
                TournamentRound(
                    round_index=round_index,
                    pairs=tuple(pairs),
                    winners=tuple(winner_ids),
                )
            )
            id_to_attempt = {a.id: a for a in current}
            current = [id_to_attempt[w] for w in winner_ids]
            round_index += 1

        winning = current[0]
        losers = tuple(a for a in attempts if a.id != winning.id)

        winning_score = (
            wins[winning.id] / participations[winning.id]
            if participations[winning.id] > 0
            else 1.0
        )

        distilled_summary = _distill(
            winning=winning,
            losers=losers,
            rounds=rounds,
            wins=wins,
        )

        return TtsResult(
            winning_attempt=winning,
            winning_score=winning_score,
            rounds=tuple(rounds),
            losers=losers,
            distilled_summary=distilled_summary,
            total_tokens_used=tokens_used,
            wall_clock_s=time.monotonic() - wall_start,
            pool_diversity=pool_diversity,
        )


def _approx_token_count(text: str) -> int:
    """4 chars ≈ 1 token, the standard cheap heuristic."""
    return max(1, math.ceil(len(text) / 4))


def _distill(
    *,
    winning: Attempt,
    losers: tuple[Attempt, ...],
    rounds: list[TournamentRound],
    wins: Mapping[str, int],
) -> str:
    """Phase-1 distillation: a structured one-paragraph summary.

    The Phase-2 implementation will replace this with a Parallel-Distill-Refine
    LLM pass. Until then, we still emit a structured string that downstream
    consumers (ReasoningBank, telemetry) can grep.
    """
    loser_count = len(losers)
    round_count = len(rounds)
    return (
        f"tournament: rounds={round_count} attempts={1 + loser_count} "
        f"winner={winning.id} winner_wins={wins.get(winning.id, 0)} "
        f"distilled_losers={loser_count}"
    )
