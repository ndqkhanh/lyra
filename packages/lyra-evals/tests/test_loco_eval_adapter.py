"""Phase 12 — Red tests for the LoCoEval adapter.

LoCoEval (arXiv:2603.06358, 2026) measures long-horizon repo conversations:
128 samples, 50-turn conversations, 64K-256K tokens, ~2.5 requirements per
sample. The published baseline memory systems hit ~40% requirement-coverage;
our SOUL + 3-tier memory stack is designed for exactly this and should do
better.

These tests prove the adapter:

1. Represents a LoCoEval sample as a stable ``LoCoEvalTask`` with turns +
   requirements.
2. Drives a 50-turn conversation through our runner, turn by turn.
3. Tracks per-turn context-budget usage and surfaces it in the report.
4. Scores against the oracle's requirement set, returning a coverage
   percentage that the runner treats as pass/fail against a threshold.
5. Fails loudly if the context budget is exceeded — that is the whole
   point of the corpus.
"""
from __future__ import annotations

import pytest

from lyra_evals.adapters.loco_eval import (
    ConversationDriver,
    LoCoEvalResult,
    LoCoEvalTask,
    score_requirement_coverage,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_task(
    *,
    turns: int = 50,
    tokens_per_turn: int = 1024,
    requirements: tuple[str, ...] = ("REQ-A", "REQ-B", "REQ-C"),
) -> LoCoEvalTask:
    return LoCoEvalTask(
        sample_id="loco-001",
        repo="example/proj",
        turns=tuple(f"user: turn {i}" for i in range(turns)),
        requirements=requirements,
        context_budget_tokens=tokens_per_turn * turns,
        tokens_per_turn=tokens_per_turn,
    )


# ---------------------------------------------------------------------------
# 1. Task shape
# ---------------------------------------------------------------------------


def test_loco_eval_task_exposes_turns_and_requirements() -> None:
    task = _make_task(turns=50)
    assert task.sample_id == "loco-001"
    assert len(task.turns) == 50
    assert task.requirements == ("REQ-A", "REQ-B", "REQ-C")
    assert task.context_budget_tokens == 1024 * 50


# ---------------------------------------------------------------------------
# 2. Driver runs 50 turns to completion
# ---------------------------------------------------------------------------


def test_driver_runs_fifty_turn_conversation_to_completion() -> None:
    """The full 50-turn conversation must run without early termination.

    A broken driver that stops at turn N<50 silently under-reports
    requirement coverage; we assert every turn was observed.
    """
    task = _make_task(turns=50)
    observed: list[int] = []

    def agent(turn_idx: int, user_msg: str, _state: dict[str, object]) -> str:
        observed.append(turn_idx)
        return f"agent reply for turn {turn_idx}"

    driver = ConversationDriver(agent=agent)
    result = driver.run(task)

    assert isinstance(result, LoCoEvalResult)
    assert observed == list(range(50))
    assert len(result.turn_logs) == 50


# ---------------------------------------------------------------------------
# 3. Context-budget tracking
# ---------------------------------------------------------------------------


def test_driver_records_per_turn_context_usage() -> None:
    """Per-turn token usage must be recorded; final budget must not overflow.

    The point of LoCoEval is to stress long-horizon context; if we can't
    see per-turn usage, we can't diagnose budget blowouts.
    """
    task = _make_task(turns=50, tokens_per_turn=1024)

    def agent(_i: int, _m: str, _s: dict[str, object]) -> str:
        return "ok"

    result = ConversationDriver(agent=agent).run(task)

    assert len(result.per_turn_tokens) == 50
    assert all(n >= 0 for n in result.per_turn_tokens)
    assert result.peak_context_tokens <= task.context_budget_tokens


def test_driver_halts_when_context_budget_exceeded() -> None:
    """If a single-turn context usage exceeds budget the driver must halt.

    Silent overflow would falsify the whole point of the benchmark; the
    driver must raise a clean, named exception and the result must
    record which turn triggered the halt.
    """
    task = _make_task(turns=10, tokens_per_turn=100)
    task_oversize = LoCoEvalTask(
        sample_id=task.sample_id,
        repo=task.repo,
        turns=task.turns,
        requirements=task.requirements,
        context_budget_tokens=500,  # 5 turns' worth, but we'll run 10
        tokens_per_turn=task.tokens_per_turn,
    )

    def agent(_i: int, _m: str, _s: dict[str, object]) -> str:
        return "hello"

    driver = ConversationDriver(agent=agent)
    with pytest.raises(RuntimeError, match="context budget"):
        driver.run(task_oversize)


# ---------------------------------------------------------------------------
# 4. Requirement-coverage scoring
# ---------------------------------------------------------------------------


def test_score_requirement_coverage_counts_unique_satisfied_requirements() -> None:
    """Coverage = |satisfied ∩ required| / |required|, NO partial credit.

    The oracle is set-based. A requirement is either satisfied by the
    final transcript or it isn't; half-satisfying it is not satisfying it.
    """
    task = _make_task(requirements=("REQ-A", "REQ-B", "REQ-C", "REQ-D"))
    mentioned = {"REQ-A", "REQ-C"}
    score = score_requirement_coverage(task=task, satisfied=mentioned)
    assert score == pytest.approx(0.5)


def test_score_requirement_coverage_ignores_unknown_requirements() -> None:
    """Satisfying a requirement that isn't in the oracle gives no credit.

    Otherwise an agent could game the benchmark by dumping synthetic
    REQ-ZZZ tokens into every turn.
    """
    task = _make_task(requirements=("REQ-A", "REQ-B"))
    score = score_requirement_coverage(
        task=task, satisfied={"REQ-A", "REQ-PHANTOM"}
    )
    assert score == pytest.approx(0.5)
