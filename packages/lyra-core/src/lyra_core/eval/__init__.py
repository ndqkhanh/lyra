"""Wave-E + Wave-F eval infrastructure.

Wave-E (`corpus.py` + `drift_gate.py`): deterministic golden
eval cases and a drift gate that compares a fresh run's pass
rate against a stored baseline.

Wave-F (`prm.py` + `rubrics/`): a Rubric Process Reward Model
that scores an agent turn against named 0..1 criteria with a
weighted average. The PRM is the subjective counterpart to the
deterministic golden gate.
"""
from __future__ import annotations

from .corpus import (
    EvalCase,
    EvalCorpus,
    EvalReport,
    EvalResult,
    default_corpus,
    run_eval,
)
from .drift_gate import DriftDecision, DriftGate
from .passk import CaseTrials, PassKReport, run_passk
from .prm import (
    Rubric,
    RubricJudge,
    RubricScore,
    RubricSet,
    RubricSetReport,
    prm_score,
)

__all__ = [
    "CaseTrials",
    "DriftDecision",
    "DriftGate",
    "EvalCase",
    "EvalCorpus",
    "EvalReport",
    "EvalResult",
    "PassKReport",
    "Rubric",
    "RubricJudge",
    "RubricScore",
    "RubricSet",
    "RubricSetReport",
    "default_corpus",
    "prm_score",
    "run_eval",
    "run_passk",
]
