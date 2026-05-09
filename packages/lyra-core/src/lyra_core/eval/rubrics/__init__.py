"""Rubrics for the Rubric Process Reward Model.

A rubric is a named, weighted criterion the judge scores on a
0..1 scale. The ``RubricSet`` container runs all rubrics against
the same output, produces a weighted score, and surfaces the
worst-performing rubric so downstream drift gates can target the
exact regression.
"""
from __future__ import annotations

from ..prm import (
    Rubric,
    RubricJudge,
    RubricScore,
    RubricSet,
    RubricSetReport,
    prm_score,
)

__all__ = [
    "Rubric",
    "RubricJudge",
    "RubricScore",
    "RubricSet",
    "RubricSetReport",
    "prm_score",
]
