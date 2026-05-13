"""LoCoEval adapter (long-horizon repo conversations).

Source: Han et al., *LoCoEval: Measuring Long-Context Long-Horizon Repo
Understanding*, arXiv:2603.06358, 2026. The benchmark pushes 50-turn
conversations over 64K-256K tokens with ~2.5 requirements per sample.
Published baseline memory systems hit ~40% requirement-coverage; our
SOUL + 3-tier memory is designed for exactly this bench.

The adapter is intentionally minimal:

- ``LoCoEvalTask`` holds the turns, the requirement set, and a context
  budget so a misbehaving agent cannot silently overflow.
- ``ConversationDriver.run`` walks the turns, invokes the ``agent``
  callable on each one, and enforces the budget turn-by-turn.
- ``score_requirement_coverage`` is the oracle — set-based, no partial
  credit — so gaming the bench via token-spam fails.

A real LoCoEval run plugs in an ``agent`` callable that calls through to
``lyra-core`` with the full 3-tier memory stack. For CI we use a
stub agent; the bench-harness itself is what we're testing here.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

AgentFn = Callable[[int, str, dict[str, object]], str]


@dataclass(frozen=True)
class LoCoEvalTask:
    """One LoCoEval sample.

    ``tokens_per_turn`` is an advisory token cost used by the default
    driver to simulate budget consumption. Real runs replace it with
    live tokeniser output; stub runs set it to a constant.
    """

    sample_id: str
    repo: str
    turns: tuple[str, ...]
    requirements: tuple[str, ...]
    context_budget_tokens: int
    tokens_per_turn: int = 1024


@dataclass
class LoCoEvalResult:
    """What a single sample's driver run produces.

    ``per_turn_tokens`` matches ``turns`` index-for-index so the retro
    view can graph context usage over the conversation.
    """

    sample_id: str
    turn_logs: list[dict[str, object]] = field(default_factory=list)
    per_turn_tokens: list[int] = field(default_factory=list)
    peak_context_tokens: int = 0


@dataclass
class ConversationDriver:
    """Drives an ``LoCoEvalTask`` through an agent callable turn-by-turn.

    The agent is a pure function: ``(turn_idx, user_message, state) -> reply``.
    ``state`` is a mutable scratchpad the driver owns; callers that need
    to accumulate memory between turns use it.
    """

    agent: AgentFn

    def run(self, task: LoCoEvalTask) -> LoCoEvalResult:
        result = LoCoEvalResult(sample_id=task.sample_id)
        state: dict[str, object] = {}
        running_tokens = 0
        for idx, user_msg in enumerate(task.turns):
            running_tokens += task.tokens_per_turn
            if running_tokens > task.context_budget_tokens:
                raise RuntimeError(
                    f"context budget exceeded at turn {idx}: "
                    f"{running_tokens} > {task.context_budget_tokens}"
                )
            reply = self.agent(idx, user_msg, state)
            result.turn_logs.append(
                {"turn": idx, "user": user_msg, "agent": reply}
            )
            result.per_turn_tokens.append(task.tokens_per_turn)
            result.peak_context_tokens = max(
                result.peak_context_tokens, running_tokens
            )
        return result


def score_requirement_coverage(
    *, task: LoCoEvalTask, satisfied: set[str]
) -> float:
    """Set-based requirement coverage over the oracle.

    Returns ``|satisfied ∩ required| / |required|``, clamped to ``[0,1]``.
    Requirements outside the oracle get no credit — this is what makes the
    metric game-proof.
    """
    required = set(task.requirements)
    if not required:
        return 0.0
    hit = len(required & satisfied)
    return hit / len(required)
