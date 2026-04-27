"""Meta-harness outer loop.

Runs candidate configs ``C1…Cn`` against the parity corpus,
ranks them by pass rate, and surfaces the winning config plus
a per-task/per-category breakdown. The outer loop owns:

* Proposing new candidates via a ``ConfigProposer`` (defaults to
  a round-robin over a user-supplied list).
* Running each candidate against the corpus via a
  ``TaskEvaluator`` (pure callable — in tests we stub it).
* Aggregating results into a :class:`MetaReport`.

The "meta" in meta-harness refers to the outer-loop-over-inner-
loops pattern: the inner loop is "run the agent on one task";
the outer loop is "sweep configs across the whole corpus".
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol, Sequence

from .corpus import HarnessTask, ParityCorpus


__all__ = [
    "CandidateConfig",
    "ConfigProposer",
    "MetaHarness",
    "MetaReport",
    "TaskEvaluator",
    "TaskResult",
]


@dataclass(frozen=True)
class CandidateConfig:
    """A single configuration under evaluation."""

    name: str
    params: dict[str, object] = field(default_factory=dict)


class ConfigProposer(Protocol):
    """Yields candidate configs to evaluate. Implementations may
    hand-craft, sample from a grid, or run a Bayesian loop."""

    def propose(self, already_tried: tuple[CandidateConfig, ...]) -> CandidateConfig | None: ...


class TaskEvaluator(Protocol):
    """Runs one task under one config and returns the agent's answer."""

    def __call__(self, *, config: CandidateConfig, task: HarnessTask) -> str: ...


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    passed: bool
    answer: str

    def to_dict(self) -> dict[str, object]:
        return {"task_id": self.task_id, "passed": self.passed, "answer": self.answer}


@dataclass(frozen=True)
class ConfigReport:
    config: CandidateConfig
    results: tuple[TaskResult, ...]

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)

    def category_rates(self, corpus: ParityCorpus) -> dict[str, float]:
        by_cat: dict[str, list[TaskResult]] = {}
        task_cat = {t.id: t.category for t in corpus.tasks}
        for r in self.results:
            cat = task_cat.get(r.task_id, "other")
            by_cat.setdefault(cat, []).append(r)
        return {
            cat: (sum(1 for r in rs if r.passed) / len(rs) if rs else 0.0)
            for cat, rs in by_cat.items()
        }

    def to_dict(self, corpus: ParityCorpus | None = None) -> dict[str, object]:
        data: dict[str, object] = {
            "config": {"name": self.config.name, "params": self.config.params},
            "pass_rate": self.pass_rate,
            "results": [r.to_dict() for r in self.results],
        }
        if corpus is not None:
            data["category_rates"] = self.category_rates(corpus)
        return data


@dataclass(frozen=True)
class MetaReport:
    corpus: ParityCorpus
    reports: tuple[ConfigReport, ...]

    @property
    def winner(self) -> ConfigReport | None:
        if not self.reports:
            return None
        return max(self.reports, key=lambda r: r.pass_rate)

    def to_dict(self) -> dict[str, object]:
        return {
            "winner": self.winner.config.name if self.winner else None,
            "reports": [r.to_dict(self.corpus) for r in self.reports],
            "corpus_size": len(self.corpus),
        }


# ---- static proposer helper ---------------------------------------


@dataclass
class StaticProposer:
    """Proposer that walks a fixed list of configs."""

    candidates: Sequence[CandidateConfig]

    def propose(
        self, already_tried: tuple[CandidateConfig, ...]
    ) -> CandidateConfig | None:
        seen = {c.name for c in already_tried}
        for c in self.candidates:
            if c.name not in seen:
                return c
        return None


# ---- harness ------------------------------------------------------


@dataclass
class MetaHarness:
    corpus: ParityCorpus
    evaluator: TaskEvaluator
    proposer: ConfigProposer
    max_candidates: int = 8

    def __post_init__(self) -> None:
        if self.max_candidates < 1:
            raise ValueError("max_candidates must be >= 1")

    def run(self) -> MetaReport:
        tried: list[CandidateConfig] = []
        reports: list[ConfigReport] = []
        while len(tried) < self.max_candidates:
            candidate = self.proposer.propose(tuple(tried))
            if candidate is None:
                break
            tried.append(candidate)
            results: list[TaskResult] = []
            for task in self.corpus.tasks:
                answer = self.evaluator(config=candidate, task=task)
                results.append(
                    TaskResult(
                        task_id=task.id,
                        passed=task.validate(answer),
                        answer=answer,
                    )
                )
            reports.append(
                ConfigReport(config=candidate, results=tuple(results))
            )
        return MetaReport(corpus=self.corpus, reports=tuple(reports))
