"""Multi-hop QA adapter — HotpotQA / MuSiQue / 2WikiMultiHopQA / NQ / TriviaQA / Bamboogle.

The *Direct Corpus Interaction* paper reports **+30.7 %** average gain
on this task family — the largest of the three categories. The shape
the adapter loads is the union of the six datasets' fields with
optional supporting-fact spans where the upstream provides them.

Phase 0: contracts + loader + scorer only.

Cite: arXiv:2605.05242 Table 1 ("Multi-hop QA"); DCI-Agent-Lite eval
scripts at ``scripts/qa/``.
"""
from __future__ import annotations

import json
import string
from dataclasses import dataclass
from pathlib import Path

from ..runner import TaskResult


@dataclass(frozen=True)
class MultiHopQATask:
    """One multi-hop QA task across the six supported datasets."""

    instance_id: str
    dataset: str               # "hotpotqa" | "musique" | "2wiki" | "nq" | "trivia" | "bamboogle"
    question: str
    gold_answers: tuple[str, ...]    # multiple aliases accepted
    corpus_root: Path
    supporting_facts: tuple[str, ...] = ()


_SUPPORTED_DATASETS: frozenset[str] = frozenset(
    {"hotpotqa", "musique", "2wiki", "nq", "trivia", "bamboogle"},
)
_REQUIRED_KEYS: frozenset[str] = frozenset(
    {"instance_id", "dataset", "question", "gold_answers"},
)


def load_multihop_qa(
    path: Path, *, corpus_root: Path, limit: int | None = None,
) -> list[MultiHopQATask]:
    """Load a multi-hop QA JSONL into a stable, immutable task list."""
    tasks: list[MultiHopQATask] = []
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
                    f"line {line_no}: multi-hop row missing keys {sorted(missing)}",
                )
            dataset = str(row["dataset"]).lower()
            if dataset not in _SUPPORTED_DATASETS:
                raise ValueError(
                    f"line {line_no}: unsupported dataset {dataset!r} "
                    f"(expected one of {sorted(_SUPPORTED_DATASETS)})",
                )
            gold_raw = row["gold_answers"]
            if isinstance(gold_raw, str):
                gold_answers: tuple[str, ...] = (gold_raw,)
            else:
                gold_answers = tuple(str(g) for g in gold_raw)
            tasks.append(
                MultiHopQATask(
                    instance_id=str(row["instance_id"]),
                    dataset=dataset,
                    question=str(row["question"]),
                    gold_answers=gold_answers,
                    corpus_root=corpus_root,
                    supporting_facts=tuple(
                        str(s) for s in row.get("supporting_facts", ())
                    ),
                ),
            )
    return tasks


def _normalize(text: str) -> str:
    """SQuAD-style normalisation for short-answer matching."""
    text = text.lower()
    text = "".join(c for c in text if c not in string.punctuation)
    return " ".join(text.split())


def score_multihop_qa(
    *, task: MultiHopQATask, predicted: str,
) -> TaskResult:
    """Score one prediction. Pass iff any normalised gold matches normalised prediction."""
    pred_norm = _normalize(predicted)
    for gold in task.gold_answers:
        gold_norm = _normalize(gold)
        if gold_norm and gold_norm in pred_norm:
            return TaskResult(
                task_id=task.instance_id, passed=True, reason="match",
            )
    return TaskResult(
        task_id=task.instance_id,
        passed=False,
        reason=f"expected any of {list(task.gold_answers)!r}",
    )


__all__ = ["MultiHopQATask", "load_multihop_qa", "score_multihop_qa"]
