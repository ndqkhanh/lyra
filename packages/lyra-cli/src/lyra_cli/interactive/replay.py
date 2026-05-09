"""Wave-E Task 12: session replay (``/replay``).

Walks the ``turns.jsonl`` of a persisted session event-by-event.
The agent (or a human operator) gets one summary line per turn plus
a diff overlay showing what changed between adjacent turns. The
diff overlay is computed in memory (stdlib :mod:`difflib`) so we
never touch the network and never depend on git for replay.

Exposed surface
---------------

* :class:`ReplayEvent` — the per-step dataclass each step yields.
* :func:`load_replay` — read every turn from disk.
* :func:`step_through` — generator that yields one event per turn,
  with the diff between this turn's and the previous turn's text.
* :class:`ReplayController` — REPL-friendly wrapper: ``next()``,
  ``prev()``, ``reset()``, ``current()``.
"""
from __future__ import annotations

import difflib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, List


__all__ = [
    "ReplayController",
    "ReplayError",
    "ReplayEvent",
    "load_replay",
    "step_through",
]


class ReplayError(Exception):
    pass


@dataclass(frozen=True)
class ReplayEvent:
    """One replay step.

    ``index`` is the position in the original ``turns.jsonl`` (zero-
    based). ``payload`` is the raw JSON the session recorded;
    ``diff`` is a unified diff between the previous turn's textual
    body (``input`` + ``output``) and this turn's body. The first
    event has an empty diff.
    """

    index: int
    payload: dict
    diff: str = ""


def _turns_path(session_dir: Path) -> Path:
    return session_dir / "turns.jsonl"


def load_replay(session_dir: Path | str) -> List[dict]:
    """Read every recorded turn for a session id.

    Malformed lines are skipped (best-effort matches the rest of
    the persistence layer).
    """
    path = _turns_path(Path(session_dir))
    if not path.exists():
        raise ReplayError(f"replay: no turns recorded at {path}")
    out: List[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _body(turn: dict) -> str:
    """Project a turn dict to a comparable text body for the diff."""
    parts = []
    if isinstance(turn.get("input"), str):
        parts.append(f"INPUT: {turn['input']}")
    out = turn.get("output")
    if isinstance(out, str):
        parts.append(f"OUTPUT: {out}")
    elif isinstance(out, list):
        parts.append("OUTPUT:")
        parts.extend(str(o) for o in out)
    return "\n".join(parts)


def step_through(
    turns: Iterable[dict],
) -> Iterator[ReplayEvent]:
    """Yield one :class:`ReplayEvent` per turn with the running diff."""
    prev_body = ""
    for idx, turn in enumerate(turns):
        body = _body(turn)
        diff = "" if idx == 0 else _unified_diff(prev_body, body, idx)
        prev_body = body
        yield ReplayEvent(index=idx, payload=turn, diff=diff)


def _unified_diff(prev: str, curr: str, index: int) -> str:
    raw = difflib.unified_diff(
        prev.splitlines(keepends=False),
        curr.splitlines(keepends=False),
        fromfile=f"turn-{index - 1}",
        tofile=f"turn-{index}",
        lineterm="",
    )
    return "\n".join(raw)


@dataclass
class ReplayController:
    """REPL-friendly wrapper around the replay event stream."""

    session_dir: Path
    _events: List[ReplayEvent] = field(default_factory=list)
    _cursor: int = -1

    def __post_init__(self) -> None:
        turns = load_replay(self.session_dir)
        self._events = list(step_through(turns))

    def __len__(self) -> int:
        return len(self._events)

    def reset(self) -> None:
        self._cursor = -1

    def current(self) -> ReplayEvent | None:
        if 0 <= self._cursor < len(self._events):
            return self._events[self._cursor]
        return None

    def next(self) -> ReplayEvent | None:
        if self._cursor + 1 >= len(self._events):
            return None
        self._cursor += 1
        return self._events[self._cursor]

    def prev(self) -> ReplayEvent | None:
        if self._cursor <= 0:
            return None
        self._cursor -= 1
        return self._events[self._cursor]
