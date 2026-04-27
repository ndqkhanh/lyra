"""Terminal-Bench 2.0 adapter (v1.8 Wave-2 §9).

Inspired by *Terminal-Bench 2.0* (Stanford NLP, link-only in
``papers/README.md``). 89 long-horizon terminal tasks; the agent must
end the run in a terminal state that satisfies a hidden checker script.

Schema (per upstream, simplified):

- ``task_id``: stable identifier,
- ``description``: free-text user instruction,
- ``initial_filesystem``: zip / tarball pointer set up before the run,
- ``checker_command``: bash command whose ``exit 0`` means the task passed,
- ``time_limit_s``: hard wall-clock cap (Terminal-Bench enforces this),
- ``allowed_network``: bool — most tasks are offline.

Phase 0: contracts only.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..corpora import Task
from ..runner import TaskResult


@dataclass(frozen=True)
class TerminalBenchTaskV2:
    """Canonical Terminal-Bench 2.0 task row."""

    task_id: str
    description: str
    initial_filesystem: str       # path or URI to the seed bundle
    checker_command: str
    time_limit_s: float
    allowed_network: bool = False


@dataclass(frozen=True)
class TerminalBenchVerdict:
    """Per-task scoring outcome."""

    task_id: str
    passed: bool
    wall_clock_s: float
    exit_code: int
    notes: str = ""


InnerPolicy = Callable[[TerminalBenchTaskV2], TerminalBenchVerdict]


_TB2_REQUIRED_KEYS: frozenset[str] = frozenset(
    {"task_id", "description", "initial_filesystem", "checker_command", "time_limit_s"}
)


def load_terminal_bench_v2(
    path: Path, *, limit: int | None = None
) -> list[TerminalBenchTaskV2]:
    """Load a Terminal-Bench 2.0 JSONL into a stable, immutable task list.

    Required keys (raise ``ValueError`` with the offending row index on
    miss): ``task_id``, ``description``, ``initial_filesystem``,
    ``checker_command``, ``time_limit_s``. Optional, defaulted:
    ``allowed_network`` (defaults to ``False`` — most upstream tasks are
    offline and we mirror that posture).

    ``limit`` honours ``lyra evals --budget N`` semantics: stop after
    ``limit`` *consumed* lines (blank lines do not count).
    """
    tasks: list[TerminalBenchTaskV2] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            if limit is not None and len(tasks) >= limit:
                break
            row = json.loads(stripped)
            missing = _TB2_REQUIRED_KEYS - set(row)
            if missing:
                raise ValueError(
                    f"Terminal-Bench 2.0 row at line {line_no} missing required "
                    f"key(s) {sorted(missing)!r}; required schema is "
                    f"{sorted(_TB2_REQUIRED_KEYS)!r}"
                )
            tasks.append(
                TerminalBenchTaskV2(
                    task_id=row["task_id"],
                    description=row["description"],
                    initial_filesystem=row["initial_filesystem"],
                    checker_command=row["checker_command"],
                    time_limit_s=float(row["time_limit_s"]),
                    allowed_network=bool(row.get("allowed_network", False)),
                )
            )
    return tasks


@dataclass
class TerminalBenchV2Adapter:
    """Bridges a Terminal-Bench 2.0 task into ``EvalRunner``."""

    model_name_or_path: str
    _tasks: dict[str, TerminalBenchTaskV2] = field(default_factory=dict)
    _verdicts: list[TerminalBenchVerdict] = field(default_factory=list)

    def as_generic_task(self, task: TerminalBenchTaskV2) -> Task:
        self._tasks[task.task_id] = task
        return Task(id=task.task_id, kind="terminal_bench_v2", description=task.description)

    def policy(self, inner: InnerPolicy) -> Callable[[Task], TaskResult]:
        def _adapted(task: Task) -> TaskResult:
            tb = self._tasks.get(task.id)
            if tb is None:
                return TaskResult(
                    task_id=task.id,
                    passed=False,
                    reason="task missing from adapter registry",
                )
            verdict = inner(tb)
            self._verdicts.append(verdict)
            return TaskResult(
                task_id=verdict.task_id,
                passed=verdict.passed,
                reason=(
                    "passed"
                    if verdict.passed
                    else f"failed (exit={verdict.exit_code}, "
                    f"wall_clock={verdict.wall_clock_s:.1f}s)"
                ),
            )

        return _adapted

    def verdicts(self) -> list[TerminalBenchVerdict]:
        return list(self._verdicts)


def write_terminal_bench_v2_submission(
    path: Path, verdicts: list[TerminalBenchVerdict]
) -> None:
    """Emit a Terminal-Bench 2.0-compatible submission JSONL.

    Each line carries the five canonical scoring keys (``task_id``,
    ``passed``, ``wall_clock_s``, ``exit_code``, ``notes``). Sorted keys
    keep two writes of the same input byte-identical so PR snapshot
    diffs are clean.
    """
    with path.open("w", encoding="utf-8") as fh:
        for verdict in verdicts:
            fh.write(
                json.dumps(
                    {
                        "task_id": verdict.task_id,
                        "passed": bool(verdict.passed),
                        "wall_clock_s": float(verdict.wall_clock_s),
                        "exit_code": int(verdict.exit_code),
                        "notes": verdict.notes,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
