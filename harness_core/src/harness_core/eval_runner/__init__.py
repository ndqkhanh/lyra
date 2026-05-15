"""harness_core.eval_runner — continuous evaluation runner with drift detection.

Per [docs/115-evaluating-llm-systems.md](../../../../../../research/harness-engineering/docs/115-evaluating-llm-systems.md),
[docs/21-llm-as-judge-trajectory-eval.md](../../../../../../research/harness-engineering/docs/21-llm-as-judge-trajectory-eval.md),
and the "evaluation discipline" Tier-0 universal lift cited across every per-
project apply plan.

Three primitives:

    1. :class:`EvalCase` / :class:`EvalSuite` — typed test cases with expected
       outputs.
    2. :class:`EvalRunner` — executes a suite against a callable program,
       records typed :class:`EvalResult`s, integrates with
       :class:`harness_core.cost.CostTracker` for cost-per-grade reports.
    3. :class:`DriftMonitor` — tracks suite-level scores over time, surfaces
       :class:`DriftAlert`s on regression beyond a configurable threshold.

Composes with:
    - :mod:`harness_core.evals.equal_budget` — fair compute-controlled runs.
    - :mod:`harness_core.cost` — cost-per-grade reporting.
    - :mod:`harness_core.provenance` — eval runs become witnesses.
    - :mod:`harness_core.programs` — :meth:`evaluate` is a one-shot variant;
       this module is the *continuous* (multi-run, drift-tracked) version.

Used by every project that ships to production:
    - Polaris ([docs/172] §"cost-aware leaderboards") — nightly eval CI.
    - Atlas-Research ([docs/218]) — research-quality regressions.
    - Helix-Bio ([docs/219]) — domain-specific KG-grounding regressions.
    - Orion-Code ([docs/220]) — SWE-Bench Verified regression CI.
    - Aegis-Ops ([docs/221]) — incident-response correctness over time.
"""
from __future__ import annotations

from .drift import DriftAlert, DriftMonitor
from .runner import EvalRunner
from .types import EvalCase, EvalResult, EvalRun, EvalSuite

__all__ = [
    "DriftAlert",
    "DriftMonitor",
    "EvalCase",
    "EvalResult",
    "EvalRun",
    "EvalRunner",
    "EvalSuite",
]
