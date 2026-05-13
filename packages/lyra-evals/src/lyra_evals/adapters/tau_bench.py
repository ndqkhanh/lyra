"""τ-Bench / τ³-Bench adapter (v1.8 Wave-2 §9).

Inspired by *τ-Bench* and *τ³-Bench* (Sierra; mirrored as link-only in
``papers/README.md``). Lyra ships a corpus loader + a policy adapter so
a τ-Bench run plugs into the same ``EvalRunner`` (``..runner``) we
already use for SWE-bench Pro and LoCoEval.

Schema (per upstream, simplified):

- ``user_intent``: free-text customer goal,
- ``domain``: e.g. "airline", "retail", "voice",
- ``policy_doc``: the airline/retail policy the agent must obey,
- ``allowed_tools``: tool ids the agent may call,
- ``ground_truth_actions``: canonical sequence the agent must produce,
- ``allow_partial_credit``: scoring mode flag.

Phase 0: contracts only.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..corpora import Task
from ..runner import TaskResult


@dataclass(frozen=True)
class TauBenchTask:
    """Canonical τ-Bench task; mirrors the upstream JSONL row 1:1."""

    instance_id: str
    domain: str
    user_intent: str
    policy_doc: str
    allowed_tools: tuple[str, ...] = ()
    ground_truth_actions: tuple[str, ...] = ()
    allow_partial_credit: bool = False


@dataclass(frozen=True)
class TauBenchVerdict:
    """Per-task scoring outcome (richer than just bool)."""

    instance_id: str
    passed: bool
    fraction_correct: float    # [0, 1]; equals 1.0 iff full pass
    policy_violations: tuple[str, ...] = ()


InnerPolicy = Callable[[TauBenchTask], TauBenchVerdict]


_TAU_BENCH_REQUIRED_KEYS: frozenset[str] = frozenset(
    {"instance_id", "domain", "user_intent", "policy_doc"}
)


def load_tau_bench(path: Path, *, limit: int | None = None) -> list[TauBenchTask]:
    """Load a τ-Bench JSONL into a stable, immutable task list.

    Required keys (raise ``ValueError`` with the offending row index on
    miss): ``instance_id``, ``domain``, ``user_intent``, ``policy_doc``.
    Optional, defaulted: ``allowed_tools`` (tuple), ``ground_truth_actions``
    (tuple), ``allow_partial_credit`` (bool).

    ``limit`` honours ``lyra evals --budget N`` semantics: stop after
    ``limit`` *consumed* lines (blank lines do not count).
    """
    tasks: list[TauBenchTask] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            if limit is not None and len(tasks) >= limit:
                break
            row = json.loads(stripped)
            missing = _TAU_BENCH_REQUIRED_KEYS - set(row)
            if missing:
                raise ValueError(
                    f"τ-Bench row at line {line_no} missing required key(s) "
                    f"{sorted(missing)!r}; required schema is "
                    f"{sorted(_TAU_BENCH_REQUIRED_KEYS)!r}"
                )
            tasks.append(
                TauBenchTask(
                    instance_id=row["instance_id"],
                    domain=row["domain"],
                    user_intent=row["user_intent"],
                    policy_doc=row["policy_doc"],
                    allowed_tools=tuple(row.get("allowed_tools", ())),
                    ground_truth_actions=tuple(row.get("ground_truth_actions", ())),
                    allow_partial_credit=bool(row.get("allow_partial_credit", False)),
                )
            )
    return tasks


@dataclass
class TauBenchAdapter:
    """Bridges a τ-Bench task into ``EvalRunner``."""

    model_name_or_path: str
    _tasks: dict[str, TauBenchTask] = field(default_factory=dict)
    _verdicts: list[TauBenchVerdict] = field(default_factory=list)

    def as_generic_task(self, task: TauBenchTask) -> Task:
        self._tasks[task.instance_id] = task
        return Task(
            id=task.instance_id,
            kind="tau_bench",
            description=task.user_intent,
        )

    def policy(self, inner: InnerPolicy) -> Callable[[Task], TaskResult]:
        def _adapted(task: Task) -> TaskResult:
            tb_task = self._tasks.get(task.id)
            if tb_task is None:
                return TaskResult(
                    task_id=task.id,
                    passed=False,
                    reason="task missing from adapter registry",
                )
            verdict = inner(tb_task)
            self._verdicts.append(verdict)
            return TaskResult(
                task_id=verdict.instance_id,
                passed=verdict.passed,
                reason=(
                    "passed"
                    if verdict.passed
                    else f"failed (frac={verdict.fraction_correct:.2f}, "
                    f"violations={list(verdict.policy_violations)})"
                ),
            )

        return _adapted

    def verdicts(self) -> list[TauBenchVerdict]:
        return list(self._verdicts)


def write_tau_bench_submission(
    path: Path, verdicts: list[TauBenchVerdict]
) -> None:
    """Emit a τ-Bench-compatible submission JSONL.

    Each line carries the four canonical scoring keys
    (``instance_id``, ``passed``, ``fraction_correct``, ``policy_violations``).
    Sorted keys keep two writes of the same input byte-identical so PR
    snapshot diffs are clean.
    """
    with path.open("w", encoding="utf-8") as fh:
        for verdict in verdicts:
            fh.write(
                json.dumps(
                    {
                        "instance_id": verdict.instance_id,
                        "passed": bool(verdict.passed),
                        "fraction_correct": float(verdict.fraction_correct),
                        "policy_violations": list(verdict.policy_violations),
                    },
                    sort_keys=True,
                )
                + "\n"
            )
