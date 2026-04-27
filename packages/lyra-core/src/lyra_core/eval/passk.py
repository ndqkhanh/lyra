"""``pass^k`` reliability metric — τ-bench-style silent-flakiness probe.

Inspired by *τ-bench* (yao2024taubench), surfaced as a future-direction
mechanism in arxiv 2604.14228 §12.1 ("Silent Failure and the
Observability–Evaluation Gap"). The argument: a single ``pass@1``
number hides a fundamental kind of failure where the agent succeeds
*sometimes* on a given task but not *always*. Production agents need
to surface that flakiness as a first-class signal.

Two metrics are computed here:

* **``pass@k``** (HumanEval-style) — at least one of K independent
  trials succeeds. Measures reachability of correctness.
* **``pass^k``** (τ-bench-style) — *all* K independent trials
  succeed. Measures *reliability* of correctness. The drop between
  ``pass@k`` and ``pass^k`` is the silent-flakiness signal the arxiv
  paper calls out.

Cases where ``pass@k = 1`` and ``pass^k < 1`` are flagged as
``flaky_cases``. Surface them in your dashboards: they pass evals but
will silently bite users in production.

Usage:

    from lyra_core.eval import run_passk, default_corpus

    cases = default_corpus().cases
    report = run_passk(cases, k=5, model_call=my_agent)
    print(report.pass_at_k, report.pass_pow_k)
    for name in report.flaky_cases:
        print("flaky:", name)

The ``model_call`` is the same callable shape used by
:func:`lyra_core.eval.run_eval` — ``(prompt: str) -> str`` — so the
same harness wired into ``lyra evals`` can run a ``--passk`` pass
without re-plumbing.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .corpus import EvalCase, EvalCorpus, EvalResult, run_eval

__all__ = [
    "CaseTrials",
    "PassKReport",
    "run_passk",
]


@dataclass(frozen=True)
class CaseTrials:
    """K trial outcomes for a single :class:`EvalCase`."""

    case: EvalCase
    trials: tuple[EvalResult, ...]

    @property
    def k(self) -> int:
        return len(self.trials)

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.trials if r.passed)

    @property
    def passed_all(self) -> bool:
        """``pass^k`` for this single case (1 if all trials pass)."""
        return self.k > 0 and all(r.passed for r in self.trials)

    @property
    def passed_any(self) -> bool:
        """``pass@k`` for this single case (1 if any trial passes)."""
        return any(r.passed for r in self.trials)

    @property
    def flaky(self) -> bool:
        """True iff at least one trial passed *and* at least one failed."""
        return 0 < self.passed_count < self.k

    @property
    def flakiness(self) -> float:
        """Fraction of trials that diverged from the majority outcome.

        For K=5, if 4 pass and 1 fails, ``flakiness == 0.2``. For K=5,
        if all pass or all fail, ``flakiness == 0.0``. This is a
        finer-grained signal than the boolean :attr:`flaky` flag.
        """
        if self.k <= 1:
            return 0.0
        majority = self.passed_count
        if majority * 2 < self.k:
            majority = self.k - majority
        return (self.k - majority) / self.k


@dataclass(frozen=True)
class PassKReport:
    """Aggregate report for a :func:`run_passk` invocation."""

    trials: tuple[CaseTrials, ...]
    k: int

    @property
    def total_cases(self) -> int:
        return len(self.trials)

    @property
    def pass_at_k(self) -> float:
        """Fraction of cases where *at least one* of K trials passed."""
        if not self.trials:
            return 1.0
        return sum(1 for t in self.trials if t.passed_any) / len(self.trials)

    @property
    def pass_pow_k(self) -> float:
        """Fraction of cases where *all* K trials passed (τ-bench)."""
        if not self.trials:
            return 1.0
        return sum(1 for t in self.trials if t.passed_all) / len(self.trials)

    @property
    def flaky_cases(self) -> tuple[str, ...]:
        """Names of cases with mixed pass/fail outcomes across K trials."""
        return tuple(t.case.name for t in self.trials if t.flaky)

    @property
    def reliability_gap(self) -> float:
        """``pass@k - pass^k`` — the silent-flakiness magnitude."""
        return self.pass_at_k - self.pass_pow_k

    def to_dict(self) -> dict[str, object]:
        return {
            "k": self.k,
            "total_cases": self.total_cases,
            "pass_at_k": self.pass_at_k,
            "pass_pow_k": self.pass_pow_k,
            "reliability_gap": self.reliability_gap,
            "flaky_cases": list(self.flaky_cases),
            "per_case": [
                {
                    "name": t.case.name,
                    "passed_count": t.passed_count,
                    "passed_all": t.passed_all,
                    "passed_any": t.passed_any,
                    "flaky": t.flaky,
                    "flakiness": round(t.flakiness, 4),
                }
                for t in self.trials
            ],
        }


def run_passk(
    cases: Sequence[EvalCase],
    *,
    k: int,
    model_call: Callable[[str], str],
) -> PassKReport:
    """Run K independent trials per case and report ``pass@k``/``pass^k``.

    Args:
        cases: Iterable of :class:`EvalCase`. The corpus is unchanged
            across trials; only the ``model_call`` may diverge between
            trials (e.g., temperature > 0).
        k: Number of independent trials per case. Must be ≥ 1.
        model_call: ``(prompt) -> response`` callable. The caller is
            responsible for any randomness across trials (sampling
            temperature, seed schedule). The metric only measures the
            outcome distribution; it does not control the source.

    Returns:
        :class:`PassKReport` with per-case trial breakdowns and
        aggregate metrics.

    Raises:
        ValueError: when ``k < 1``.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    case_trials: list[CaseTrials] = []
    for case in cases:
        single_corpus = EvalCorpus(cases=(case,))
        results: list[EvalResult] = []
        for _ in range(k):
            report = run_eval(model_call=model_call, corpus=single_corpus)
            assert report.results, "run_eval returned no results"
            results.append(report.results[0])
        case_trials.append(CaseTrials(case=case, trials=tuple(results)))
    return PassKReport(trials=tuple(case_trials), k=k)
