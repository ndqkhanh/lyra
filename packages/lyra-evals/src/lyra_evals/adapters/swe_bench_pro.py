"""SWE-bench Pro adapter.

This module is deliberately the only place in the repo that knows the
Scale AI submission schema. Everywhere else, Pro tasks flow through the
generic ``Task`` + ``Policy`` + ``EvalRunner`` contract.

What Scale AI's evaluator expects, and what we therefore guarantee:

- Tasks arrive as a JSONL on disk. Each line is one task with at least
  the keys ``instance_id``, ``repo``, ``base_commit``, ``problem_statement``
  and the two test-selector lists ``FAIL_TO_PASS`` and ``PASS_TO_PASS``.
- Predictions leave as a JSONL whose lines have *exactly* three keys:
  ``instance_id``, ``model_name_or_path``, ``model_patch``. Extra keys
  poison the ingestion; we fail loudly rather than strip.
- A task resolves iff its ``FAIL_TO_PASS`` tests go from fail → pass and
  its ``PASS_TO_PASS`` tests stay pass. Our adapter does NOT run Docker
  images; the inner policy is what decides ``resolved``. For CI smoke we
  accept a boolean from the policy and trust it; for real-corpus runs the
  inner policy is a wrapper around ``swebench.harness.run_evaluation``
  (not imported here — that's a runtime dependency, not a test one).
"""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..corpora import Task
from ..runner import TaskResult

_SUBMISSION_KEYS: frozenset[str] = frozenset(
    {"instance_id", "model_name_or_path", "model_patch"}
)

InnerPolicy = Callable[["PublicBenchmarkTask"], tuple[str, bool]]


@dataclass(frozen=True)
class PublicBenchmarkTask:
    """Canonical SWE-bench-family task.

    Mirrors the public JSONL rows exactly; we rename only for PEP 8
    attribute conventions (``FAIL_TO_PASS`` → ``fail_to_pass``) and keep
    tuple-typed immutable collections so two loads of the same file
    hash identically.
    """

    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    fail_to_pass: tuple[str, ...] = ()
    pass_to_pass: tuple[str, ...] = ()
    hints_text: str = ""
    version: str = ""
    environment_setup_commit: str = ""
    created_at: str = ""


def load_swe_bench_pro(
    path: Path, *, limit: int | None = None
) -> list[PublicBenchmarkTask]:
    """Load a Pro JSONL into a stable task list.

    ``limit`` honours ``lyra evals --budget N`` so operators can
    smoke a 10-task subset on every PR without waiting for the full run.
    """
    tasks: list[PublicBenchmarkTask] = []
    with path.open("r", encoding="utf-8") as fh:
        for idx, raw in enumerate(fh):
            raw = raw.strip()
            if not raw:
                continue
            if limit is not None and idx >= limit:
                break
            row = json.loads(raw)
            tasks.append(
                PublicBenchmarkTask(
                    instance_id=row["instance_id"],
                    repo=row.get("repo", ""),
                    base_commit=row.get("base_commit", ""),
                    problem_statement=row.get("problem_statement", ""),
                    fail_to_pass=tuple(row.get("FAIL_TO_PASS", ())),
                    pass_to_pass=tuple(row.get("PASS_TO_PASS", ())),
                    hints_text=row.get("hints_text", ""),
                    version=row.get("version", ""),
                    environment_setup_commit=row.get(
                        "environment_setup_commit", ""
                    ),
                    created_at=row.get("created_at", ""),
                )
            )
    return tasks


@dataclass
class SWEBenchProAdapter:
    """Bridge a Pro task to the generic ``EvalRunner`` contract.

    ``adapter.policy(inner)`` converts an inner ``(task) -> (patch, resolved)``
    into our standard ``Policy``; ``adapter.as_generic_task(t)`` wraps a
    ``PublicBenchmarkTask`` into a ``Task`` so the runner can see it.
    Predictions accumulate on the adapter so ``write_submission`` has
    something concrete to emit.
    """

    model_name_or_path: str
    _tasks: dict[str, PublicBenchmarkTask] = field(default_factory=dict)
    _predictions: list[dict[str, str]] = field(default_factory=list)

    def as_generic_task(self, task: PublicBenchmarkTask) -> Task:
        self._tasks[task.instance_id] = task
        return Task(
            id=task.instance_id,
            kind="swe_bench_pro",
            description=task.problem_statement,
        )

    def policy(self, inner: InnerPolicy) -> Callable[[Task], TaskResult]:
        def _adapted(task: Task) -> TaskResult:
            public = self._tasks.get(task.id)
            if public is None:
                return TaskResult(
                    task_id=task.id,
                    passed=False,
                    reason="task missing from adapter registry",
                )
            patch, resolved = inner(public)
            self._predictions.append(
                {
                    "instance_id": public.instance_id,
                    "model_name_or_path": self.model_name_or_path,
                    "model_patch": patch,
                }
            )
            return TaskResult(
                task_id=public.instance_id,
                passed=bool(resolved),
                reason="resolved" if resolved else "unresolved",
            )

        return _adapted

    def predictions(self) -> list[dict[str, str]]:
        return list(self._predictions)


def write_submission(
    path: Path, predictions: list[dict[str, str]]
) -> None:
    """Emit a Scale-AI-ingestible JSONL.

    We reject extra keys here rather than strip them — a silent strip
    would hide adapter bugs and a silent pass-through would poison the
    submission. The function is the chokepoint, so this is where the
    schema is enforced.
    """
    for idx, pred in enumerate(predictions):
        extra = set(pred) - _SUBMISSION_KEYS
        if extra:
            raise ValueError(
                f"prediction #{idx} has unexpected keys {sorted(extra)!r}; "
                f"allowed: {sorted(_SUBMISSION_KEYS)!r}"
            )
        missing = _SUBMISSION_KEYS - set(pred)
        if missing:
            raise ValueError(
                f"prediction #{idx} missing keys {sorted(missing)!r}"
            )
    with path.open("w", encoding="utf-8") as fh:
        for pred in predictions:
            fh.write(
                json.dumps(
                    {
                        "instance_id": pred["instance_id"],
                        "model_name_or_path": pred["model_name_or_path"],
                        "model_patch": pred["model_patch"],
                    },
                    sort_keys=True,
                )
                + "\n"
            )
