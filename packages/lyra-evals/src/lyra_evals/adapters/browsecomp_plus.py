"""BrowseComp-Plus adapter for the DCI investigate-mode runner.

BCP is the headline benchmark in the *Direct Corpus Interaction* paper
(arXiv:2605.05242): 830 tasks, 100 K-doc corpus, 5 179 avg words per
doc. DCI-Agent-Lite reports **62.9 %** accuracy with ``gpt-5.4-nano``
plus extended thinking and context-management level 3.

This adapter is **Phase 0**: contracts + loader + scorer only. The
actual benchmark run wires through ``InvestigationRunner`` and lands
under ``packages/lyra-evals/scripts/`` once datasets are mounted.

Cite: arXiv:2605.05242 Table 1; DCI-Agent-Lite README "Benchmark
Performance" table.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..runner import TaskResult


@dataclass(frozen=True)
class BCPTask:
    """One BrowseComp-Plus task. Mirrors the upstream JSONL row.

    Attributes:
        instance_id: Stable id from the upstream dataset.
        question: Natural-language query the agent must answer.
        gold_answer: Canonical short answer used by :func:`score_bcp`.
        corpus_root: Path to the 100 K-doc corpus this task references.
            (Same value across the whole split; carried per-task so
            the adapter is task-local.)
    """

    instance_id: str
    question: str
    gold_answer: str
    corpus_root: Path


_REQUIRED_KEYS: frozenset[str] = frozenset(
    {"instance_id", "question", "gold_answer"},
)


def load_browsecomp_plus(
    path: Path, *, corpus_root: Path, limit: int | None = None,
) -> list[BCPTask]:
    """Load BCP JSONL into a stable, immutable task list.

    Required keys per row: ``instance_id``, ``question``, ``gold_answer``.
    Raises :class:`ValueError` (with the offending line number) on
    schema miss.

    ``limit`` honours ``lyra evals --budget N`` semantics: stop after
    ``limit`` consumed rows (blank lines do not count).
    """
    tasks: list[BCPTask] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            if limit is not None and len(tasks) >= limit:
                break
            row = json.loads(stripped)
            missing = _REQUIRED_KEYS - row.keys()
            if missing:
                raise ValueError(
                    f"line {line_no}: BCP row missing keys {sorted(missing)}",
                )
            tasks.append(
                BCPTask(
                    instance_id=str(row["instance_id"]),
                    question=str(row["question"]),
                    gold_answer=str(row["gold_answer"]),
                    corpus_root=corpus_root,
                ),
            )
    return tasks


def score_bcp(*, task: BCPTask, predicted: str) -> TaskResult:
    """Score one prediction against the gold answer.

    DCI-Agent-Lite uses string-match (case-insensitive substring) for
    BCP — the questions are short-answer style. We mirror that here;
    a fancier exact-match / F1 / LLM-judge can land in a follow-up.
    """
    gold = task.gold_answer.strip().lower()
    pred = predicted.strip().lower()
    passed = bool(gold) and gold in pred
    return TaskResult(
        task_id=task.instance_id,
        passed=passed,
        reason="match" if passed else f"expected={task.gold_answer!r}",
    )


__all__ = ["BCPTask", "load_browsecomp_plus", "score_bcp"]
