"""BRIGHT adapter — Biology / Earth Science / Economics / Robotics splits.

BRIGHT is the IR-ranking benchmark in the DCI paper (arXiv:2605.05242):
50..121 K docs per split, document lengths 25..52 words. The paper
reports **+21.5 %** average gain on BRIGHT + BEIR vs SOTA retrievers.

For IR ranking the metric is *ranked-document precision@k* — the
agent's final answer is expected to be a list of doc IDs. We score
mean-reciprocal-rank against the gold doc list, the same metric
DCI-Agent-Lite's eval script uses.

Phase 0: contracts + loader + scorer only.

Cite: arXiv:2605.05242 Table 1 ("IR Ranking"); DCI-Agent-Lite
``scripts/bright/`` eval harness.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from ..runner import TaskResult


@dataclass(frozen=True)
class BrightTask:
    """One BRIGHT IR-ranking task."""

    instance_id: str
    split: str                     # "biology" | "earth_science" | "economics" | "robotics"
    question: str
    gold_doc_ids: tuple[str, ...]
    corpus_root: Path


_SUPPORTED_SPLITS: frozenset[str] = frozenset(
    {"biology", "earth_science", "economics", "robotics"},
)
_REQUIRED_KEYS: frozenset[str] = frozenset(
    {"instance_id", "split", "question", "gold_doc_ids"},
)


def load_bright(
    path: Path, *, corpus_root: Path, limit: int | None = None,
) -> list[BrightTask]:
    """Load a BRIGHT JSONL into a stable, immutable task list."""
    tasks: list[BrightTask] = []
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
                    f"line {line_no}: BRIGHT row missing keys {sorted(missing)}",
                )
            split = str(row["split"]).lower()
            if split not in _SUPPORTED_SPLITS:
                raise ValueError(
                    f"line {line_no}: unsupported split {split!r} "
                    f"(expected one of {sorted(_SUPPORTED_SPLITS)})",
                )
            tasks.append(
                BrightTask(
                    instance_id=str(row["instance_id"]),
                    split=split,
                    question=str(row["question"]),
                    gold_doc_ids=tuple(str(d) for d in row["gold_doc_ids"]),
                    corpus_root=corpus_root,
                ),
            )
    return tasks


# Doc IDs in the agent's answer are matched via the same shape upstream
# uses — alphanumeric + dot/dash/underscore tokens.
_DOC_ID_RE = re.compile(r"[A-Za-z0-9_.\-/]+")


def _extract_doc_ids(text: str) -> list[str]:
    return _DOC_ID_RE.findall(text)


def score_bright(*, task: BrightTask, predicted: str, k: int = 10) -> TaskResult:
    """Score one BRIGHT prediction via mean reciprocal rank @ *k*.

    The agent's final answer is parsed as a list of doc IDs (in order
    of confidence). MRR is computed against the first gold ID that
    appears in the top-*k* of the predicted list. Pass iff MRR > 0.
    """
    predicted_ids = _extract_doc_ids(predicted)[:k]
    gold = set(task.gold_doc_ids)
    rr = 0.0
    for rank, doc_id in enumerate(predicted_ids, start=1):
        if doc_id in gold:
            rr = 1.0 / rank
            break
    return TaskResult(
        task_id=task.instance_id,
        passed=rr > 0,
        reason=f"mrr@{k}={rr:.3f}"
        + ("" if rr > 0 else f"; gold={list(task.gold_doc_ids)[:3]}"),
    )


__all__ = ["BrightTask", "load_bright", "score_bright"]
