"""Trajectory recording scaffold for RL training.

A :class:`TrajectoryRecorder` captures ``(prompt, action, reward,
metadata)`` tuples as the agent turn-loop executes. In production
those records are streamed to Atropos as rollout groups for GRPO.
Here we only persist to a local JSONL so the interface is testable
without the trainer running.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

__all__ = [
    "RLEnvironment",
    "RLTrajectoryError",
    "TrajectoryRecord",
    "TrajectoryRecorder",
    "make_rl_list_environments_tool",
]


class RLTrajectoryError(Exception):
    pass


@dataclass(frozen=True)
class RLEnvironment:
    name: str
    description: str
    tags: tuple[str, ...] = ()


@dataclass
class TrajectoryRecord:
    session_id: str
    turn: int
    prompt: str
    action: str
    reward: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TrajectoryRecorder:
    sink_path: Path
    _opened: bool = False

    def __post_init__(self) -> None:
        self.sink_path = Path(self.sink_path)
        self.sink_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, record: TrajectoryRecord) -> None:
        with self.sink_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.to_dict()) + "\n")
        self._opened = True

    def read_all(self) -> list[TrajectoryRecord]:
        if not self.sink_path.exists():
            return []
        out: list[TrajectoryRecord] = []
        with self.sink_path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                out.append(TrajectoryRecord(**d))
        return out


_DEFAULT_ENVIRONMENTS: tuple[RLEnvironment, ...] = (
    RLEnvironment(
        name="gsm8k",
        description="Grade-school math word problems with string-match reward.",
        tags=("math", "chain-of-thought"),
    ),
    RLEnvironment(
        name="mbpp",
        description="Python programming problems with unit-test reward.",
        tags=("code", "unit-tests"),
    ),
    RLEnvironment(
        name="swebench-lite",
        description="GitHub issue fix from swe-bench-lite, pass/fail against tests.",
        tags=("code", "repo"),
    ),
)


def make_rl_list_environments_tool(
    environments: tuple[RLEnvironment, ...] = _DEFAULT_ENVIRONMENTS,
) -> Callable[..., dict]:
    """Return an LLM-callable tool that lists the known RL environments."""

    def rl_list_environments() -> dict:
        return {
            "environments": [
                {
                    "name": e.name,
                    "description": e.description,
                    "tags": list(e.tags),
                }
                for e in environments
            ]
        }

    rl_list_environments.__tool_schema__ = {  # type: ignore[attr-defined]
        "name": "rl_list_environments",
        "description": "List the RL training environments this server exposes.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }
    return rl_list_environments
