"""Rubric Process Reward Model.

A PRM is a judge that scores an agent-turn against one or more
rubrics (0..1). Unlike the Wave-E ``EvalReport`` which is a
deterministic substring-match pass/fail, the PRM is intentionally
subjective — it exists to catch qualitative regressions that
substring matches can't express ("the agent is suddenly wordy and
meandering" — no substring will detect that).

The production judge is a regular LLM. Tests inject stubs that
return canned per-rubric scores so the weighted-average maths is
deterministic and offline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol, Sequence


__all__ = [
    "Rubric",
    "RubricJudge",
    "RubricScore",
    "RubricSet",
    "RubricSetReport",
    "prm_score",
]


class RubricJudge(Protocol):
    """A judge maps ``(rubric, output)`` → 0..1."""

    def __call__(self, *, rubric: "Rubric", output: str) -> float: ...


@dataclass(frozen=True)
class Rubric:
    """One named criterion."""

    name: str
    description: str
    weight: float = 1.0

    def __post_init__(self) -> None:
        if self.weight < 0:
            raise ValueError(f"rubric weight must be >= 0, got {self.weight}")
        if not self.name.strip():
            raise ValueError("rubric name must be non-empty")


@dataclass(frozen=True)
class RubricScore:
    """One judge result clamped to [0, 1]."""

    rubric: Rubric
    score: float

    @staticmethod
    def clamp(raw: float) -> float:
        if raw < 0.0:
            return 0.0
        if raw > 1.0:
            return 1.0
        return raw


@dataclass(frozen=True)
class RubricSetReport:
    scores: tuple[RubricScore, ...]

    @property
    def weighted_score(self) -> float:
        total_weight = sum(s.rubric.weight for s in self.scores)
        if total_weight == 0:
            return 0.0
        return sum(s.score * s.rubric.weight for s in self.scores) / total_weight

    @property
    def worst(self) -> RubricScore | None:
        if not self.scores:
            return None
        return min(self.scores, key=lambda s: s.score)

    def to_dict(self) -> dict[str, object]:
        return {
            "weighted_score": self.weighted_score,
            "scores": [
                {"name": s.rubric.name, "score": s.score, "weight": s.rubric.weight}
                for s in self.scores
            ],
            "worst": (
                {"name": self.worst.rubric.name, "score": self.worst.score}
                if self.worst
                else None
            ),
        }


@dataclass
class RubricSet:
    rubrics: tuple[Rubric, ...]

    def __post_init__(self) -> None:
        names = [r.name for r in self.rubrics]
        if len(set(names)) != len(names):
            raise ValueError(f"rubric names must be unique; got {names}")

    def score(self, *, output: str, judge: RubricJudge) -> RubricSetReport:
        results: list[RubricScore] = []
        for rubric in self.rubrics:
            raw = judge(rubric=rubric, output=output)
            if not isinstance(raw, (int, float)):
                raise TypeError(
                    f"judge returned {type(raw).__name__}, expected float"
                )
            results.append(RubricScore(rubric=rubric, score=RubricScore.clamp(float(raw))))
        return RubricSetReport(scores=tuple(results))


def prm_score(
    *,
    output: str,
    rubrics: Sequence[Rubric] | RubricSet,
    judge: RubricJudge,
) -> RubricSetReport:
    """Convenience wrapper that accepts either a ``RubricSet`` or a list."""
    rs = rubrics if isinstance(rubrics, RubricSet) else RubricSet(tuple(rubrics))
    return rs.score(output=output, judge=judge)
