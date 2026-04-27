"""Wave-D Task 5: variant runs + LLM-judge selector.

``run_variants(spec, n=K, worker=...)`` runs the same spec K times
(in parallel) under different temperatures or seeds, then asks a
judge function to pick the winner. The result includes:

- the chosen :class:`VariantOutcome`
- every variant's :class:`VariantOutcome` (so callers can show "best
  of 4" comparisons in the REPL).

Tests cover the five core invariants:

1. With ``n=1`` the loop short-circuits and just returns that one run.
2. With ``n=K`` the worker is invoked K times.
3. The judge picks the highest-scoring variant by default.
4. A custom judge can override the default.
5. When every variant fails, the result reports the failure and does
   not call the judge.
"""
from __future__ import annotations

from typing import Any

import pytest


def _scoring_judge(outcomes: list[Any]) -> Any:
    """Default judge: pick the variant with the highest ``score``."""
    return max(
        outcomes,
        key=lambda o: (o.payload or {}).get("score", -float("inf")),
    )


def test_variants_n1_skips_judge() -> None:
    from lyra_core.subagent.variants import VariantSpec, run_variants

    judge_calls: list[int] = []

    def judge(outcomes: list[Any]) -> Any:
        judge_calls.append(len(outcomes))
        return outcomes[0]

    def worker(spec: VariantSpec) -> dict:
        return {"id": spec.id, "score": 1.0}

    out = run_variants(VariantSpec(id="x"), n=1, worker=worker, judge=judge)
    assert out.chosen.payload["id"] == "x"
    assert judge_calls == []  # judge never asked when n=1


def test_variants_invokes_worker_n_times() -> None:
    from lyra_core.subagent.variants import VariantSpec, run_variants

    invocations: list[int] = []

    def worker(spec: VariantSpec) -> dict:
        invocations.append(spec.variant_index)
        return {"score": float(spec.variant_index)}

    out = run_variants(
        VariantSpec(id="x"), n=4, worker=worker, judge=_scoring_judge
    )
    assert sorted(invocations) == [0, 1, 2, 3]
    assert len(out.outcomes) == 4
    # Highest score wins.
    assert out.chosen.payload["score"] == 3.0


def test_variants_default_judge_uses_highest_score() -> None:
    from lyra_core.subagent.variants import VariantSpec, run_variants

    def worker(spec: VariantSpec) -> dict:
        return {"score": 10 - spec.variant_index}

    out = run_variants(VariantSpec(id="x"), n=3, worker=worker)
    # default judge → variant 0 (score=10) wins
    assert out.chosen.payload["score"] == 10


def test_variants_custom_judge_can_override() -> None:
    from lyra_core.subagent.variants import VariantSpec, run_variants

    def worker(spec: VariantSpec) -> dict:
        return {"score": spec.variant_index, "id": spec.id}

    def lowest_score(outcomes: list[Any]) -> Any:
        return min(outcomes, key=lambda o: o.payload.get("score", float("inf")))

    out = run_variants(
        VariantSpec(id="x"), n=3, worker=worker, judge=lowest_score
    )
    assert out.chosen.payload["score"] == 0


def test_variants_all_failed_reports_failure_without_judge() -> None:
    from lyra_core.subagent.variants import VariantSpec, run_variants

    judged: list[bool] = []

    def judge(outcomes: list[Any]) -> Any:
        judged.append(True)
        return outcomes[0]

    def worker(_spec: VariantSpec) -> dict:
        raise RuntimeError("always-fails")

    out = run_variants(VariantSpec(id="x"), n=3, worker=worker, judge=judge)
    assert out.chosen is None
    assert all(o.status == "failed" for o in out.outcomes)
    assert judged == []
