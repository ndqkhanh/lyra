"""Wave-D Task 5: variant runs + LLM-judge selector.

Some agentic tasks really do benefit from sampling multiple
candidate trajectories and picking the best one — claw-code's
"variants" feature, opencode's `n=K` sampling, and the wider
"best-of-N" line of research all point at the same primitive.

:func:`run_variants` runs a single :class:`VariantSpec` through a
worker function ``n`` times in parallel, then asks a judge to pick
the winner. The defaults make the common cases trivial:

- The default judge is "highest ``payload['score']``" so a worker
  that returns ``{"score": float}`` Just Works.
- ``n=1`` short-circuits and never invokes the judge.
- A worker exception lands as ``status="failed"`` instead of
  cancelling the whole batch — when *every* variant fails the
  judge is skipped (so the caller doesn't have to defend against
  an empty pool).

Concurrency is via :class:`concurrent.futures.ThreadPoolExecutor` —
the same primitive the scheduler uses, kept in-process so the
harness stays asyncio-free.
"""
from __future__ import annotations

import concurrent.futures as cf
from dataclasses import dataclass, field
from typing import Any, Callable, Literal


VariantStatus = Literal["ok", "failed"]


@dataclass
class VariantSpec:
    """Input handed to each variant invocation."""

    id: str
    description: str = ""
    extras: dict[str, Any] = field(default_factory=dict)
    # Filled in by :func:`run_variants` so the worker can use the
    # index as a seed offset / temperature shift.
    variant_index: int = 0


@dataclass
class VariantOutcome:
    """One worker invocation's result."""

    spec: VariantSpec
    status: VariantStatus
    payload: dict | None = None
    error: str | None = None


@dataclass
class VariantsResult:
    """Aggregate handed back to the caller."""

    outcomes: list[VariantOutcome] = field(default_factory=list)
    chosen: VariantOutcome | None = None


WorkerFn = Callable[[VariantSpec], dict]
JudgeFn = Callable[[list[VariantOutcome]], VariantOutcome]


def _default_judge(outcomes: list[VariantOutcome]) -> VariantOutcome:
    """Pick the variant with the highest ``payload['score']`` field.

    Falls back to the first ``ok`` variant when no scores are
    present — that gives ``run_variants`` a sane behaviour even when
    the worker returns plain text without a numeric verdict.
    """
    scored = [
        o for o in outcomes
        if o.status == "ok" and isinstance(o.payload, dict) and "score" in o.payload
    ]
    if scored:
        return max(scored, key=lambda o: float(o.payload["score"]))
    ok = [o for o in outcomes if o.status == "ok"]
    if ok:
        return ok[0]
    # Pre-conditions in run_variants prevent us from ever reaching
    # here, but mypy / runtime invariants benefit from the explicit
    # return.
    return outcomes[0]


def run_variants(
    spec: VariantSpec,
    *,
    n: int,
    worker: WorkerFn,
    judge: JudgeFn | None = None,
    max_parallel: int | None = None,
) -> VariantsResult:
    """Run ``spec`` ``n`` times under different variant indices.

    Parameters
    ----------
    spec:
        Base spec; cloned with an updated ``variant_index`` for each run.
    n:
        Number of variants. Must be >= 1.
    worker:
        Callable that takes a :class:`VariantSpec` and returns a dict.
        Exceptions are caught and reported as ``status="failed"``.
    judge:
        Selector among the *successful* outcomes. When ``None`` the
        default scoring judge is used.
    max_parallel:
        Cap on concurrent workers (defaults to ``n``).
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    judge = judge or _default_judge
    max_parallel = max_parallel or n

    variants: list[VariantSpec] = []
    for idx in range(n):
        clone = VariantSpec(
            id=spec.id,
            description=spec.description,
            extras=dict(spec.extras),
            variant_index=idx,
        )
        variants.append(clone)

    outcomes: list[VariantOutcome] = []
    if n == 1:
        v = variants[0]
        try:
            payload = worker(v)
            outcomes.append(VariantOutcome(spec=v, status="ok", payload=payload))
        except Exception as exc:
            outcomes.append(
                VariantOutcome(
                    spec=v,
                    status="failed",
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
        result = VariantsResult(outcomes=outcomes)
        if outcomes[0].status == "ok":
            result.chosen = outcomes[0]
        return result

    out_by_index: dict[int, VariantOutcome] = {}
    with cf.ThreadPoolExecutor(max_workers=min(max_parallel, n)) as pool:
        fut_map = {pool.submit(worker, v): v for v in variants}
        for fut in cf.as_completed(fut_map):
            v = fut_map[fut]
            try:
                payload = fut.result()
                out_by_index[v.variant_index] = VariantOutcome(
                    spec=v, status="ok", payload=payload
                )
            except Exception as exc:
                out_by_index[v.variant_index] = VariantOutcome(
                    spec=v,
                    status="failed",
                    error=f"{type(exc).__name__}: {exc}",
                )

    outcomes = [out_by_index[i] for i in range(n)]
    result = VariantsResult(outcomes=outcomes)
    successful = [o for o in outcomes if o.status == "ok"]
    if successful:
        result.chosen = judge(successful)
    return result


__all__ = [
    "JudgeFn",
    "VariantOutcome",
    "VariantSpec",
    "VariantStatus",
    "VariantsResult",
    "WorkerFn",
    "run_variants",
]
