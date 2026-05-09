"""Reflexion retrospective loop — verbal self-improvement memory.

Inspired by *Reflexion* (Shinn et al., 2023) — the technique where an
agent that just failed a task generates a *verbal lesson* explaining
why, stores it in episodic memory, and prepends it to the prompt on the
next attempt. The empirical result: GPT-4 with three Reflexion rounds
on HumanEval beats GPT-4 zero-shot by a meaningful margin without any
weight updates. The cost is a small extra LLM call per failure plus a
flat memory file the agent reads on every attempt.

Lyra ships Reflexion as an *opt-in* per-session module so it doesn't
fire on simple chat turns. The mechanism is three pieces:

* :class:`Reflection` — one frozen lesson with verdict, task, and tags.
* :class:`ReflectionMemory` — append-only store with disk snapshot at
  ``.lyra/reflexion.json``. Tag-aware retrieval keeps unrelated lessons
  out of unrelated prompts.
* :func:`make_reflection` — the lesson-extractor. Production wires the
  optional ``lesson_generator`` callable to an LLM ("explain in one
  paragraph why this attempt failed and what to try next time"); tests
  use the deterministic templated default so the pipeline is
  exercisable without a model.
* :func:`inject_reflections` — assembles a system-message preamble
  drawn from the K most recent (and tag-matching) reflections.

The verdict shape is intentionally tiny so it's easy to hand-author in
slash commands: ``"pass"``, ``"fail"``, or any free-form short reason.
The memory does not censor verdicts; flakiness and partial failures are
all observable signal.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

__all__ = [
    "LessonGenerator",
    "Reflection",
    "ReflectionMemory",
    "inject_reflections",
    "make_reflection",
    "naive_lesson",
]


@dataclass(frozen=True)
class Reflection:
    """One stored lesson — what the agent learned from a single attempt.

    ``timestamp`` is monotonic-ish wall clock seconds (epoch); ``tags``
    are short kebab-case strings so the agent can filter to "rust" /
    "frontend" / "tdd" buckets on retrieval. The store is intentionally
    flat — there are no parent/child links and no graph; that's enough
    for the v3.1.0 cut and keeps the JSON snapshot human-greppable.
    """

    task: str
    verdict: str
    lesson: str
    timestamp: float = field(default_factory=time.time)
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "task": self.task,
            "verdict": self.verdict,
            "lesson": self.lesson,
            "timestamp": self.timestamp,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Reflection":
        return cls(
            task=str(payload["task"]),
            verdict=str(payload["verdict"]),
            lesson=str(payload["lesson"]),
            timestamp=float(payload.get("timestamp", time.time())),
            tags=tuple(str(t) for t in payload.get("tags", ())),
        )


LessonGenerator = Callable[[str, str, str], str]
"""``(task, attempt_output, verdict) -> verbal lesson`` callable."""


def naive_lesson(task: str, attempt_output: str, verdict: str) -> str:
    """LLM-free lesson extractor used by tests and as a safe fallback.

    Production should pass an LLM-backed :data:`LessonGenerator` so the
    lesson actually reflects on the attempt. The naive variant just
    summarises the verdict + task header so the memory shape stays
    consistent when no model is available.
    """
    head = task.strip().splitlines()[0] if task.strip() else "(empty task)"
    output_excerpt = attempt_output.strip().splitlines()
    excerpt_text = (
        output_excerpt[0][:120] if output_excerpt else "(no output)"
    )
    return (
        f"Task '{head[:80]}' ended with verdict '{verdict}'. "
        f"Last attempt began: '{excerpt_text}'. "
        "Next time: re-read the task, identify the missing precondition, "
        "and try the smallest reversible fix first."
    )


def make_reflection(
    task: str,
    attempt_output: str,
    verdict: str,
    *,
    tags: Sequence[str] = (),
    lesson_generator: LessonGenerator | None = None,
) -> Reflection:
    """Turn one (task, attempt, verdict) triple into a :class:`Reflection`.

    Args:
        task: What the agent was asked to do (any length).
        attempt_output: The agent's last output for that task.
        verdict: ``pass``, ``fail``, or any short free-form reason. The
            store records it verbatim.
        tags: Short kebab-case tags for retrieval (e.g. ``("rust",
            "tdd")``). Empty by default.
        lesson_generator: Optional ``(task, attempt, verdict) -> str``
            callable. Wire to an LLM in production; defaults to
            :func:`naive_lesson`.

    The lesson string is truncated to 1500 chars to keep injected
    preambles bounded and predictable.
    """
    gen = lesson_generator or naive_lesson
    lesson = gen(task, attempt_output, verdict).strip()
    if len(lesson) > 1500:
        lesson = lesson[:1497] + "..."
    return Reflection(
        task=task,
        verdict=verdict,
        lesson=lesson,
        tags=tuple(tags),
    )


class ReflectionMemory:
    """Append-only store of :class:`Reflection` with optional disk snapshot.

    The disk format is a single JSON array at ``path``; loading and
    saving are atomic (write-temp + rename). Order is preserved
    (chronological); ``recent(k)`` returns the K most-recent entries.
    """

    def __init__(self, *, path: Optional[Path] = None) -> None:
        self._items: list[Reflection] = []
        self._path: Optional[Path] = Path(path) if path is not None else None
        if self._path is not None and self._path.exists():
            self._load()

    @property
    def path(self) -> Optional[Path]:
        return self._path

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def add(self, reflection: Reflection) -> None:
        """Append a reflection and persist if a snapshot path is set."""
        self._items.append(reflection)
        self._save()

    def extend(self, reflections: Sequence[Reflection]) -> None:
        for r in reflections:
            self._items.append(r)
        self._save()

    def all(self) -> tuple[Reflection, ...]:
        return tuple(self._items)

    def recent(self, k: int) -> tuple[Reflection, ...]:
        if k <= 0:
            return ()
        return tuple(self._items[-k:])

    def for_tags(self, tags: Sequence[str]) -> tuple[Reflection, ...]:
        if not tags:
            return tuple(self._items)
        wanted = set(tags)
        return tuple(r for r in self._items if wanted & set(r.tags))

    def clear(self) -> None:
        self._items = []
        self._save()

    def _save(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(
                [r.to_dict() for r in self._items],
                indent=2,
                ensure_ascii=False,
            )
        )
        tmp.replace(self._path)

    def _load(self) -> None:
        assert self._path is not None
        try:
            payload = json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError):
            return
        if not isinstance(payload, list):
            return
        self._items = [Reflection.from_dict(p) for p in payload if isinstance(p, dict)]


def inject_reflections(
    memory: ReflectionMemory,
    *,
    k: int = 3,
    tags: Sequence[str] = (),
    header: str = "Lessons from previous attempts:",
) -> str:
    """Build the system-message preamble for the next attempt.

    Returns ``""`` when the memory is empty or no entries match the
    requested tags so callers can do ``preamble + system_prompt``
    without conditional plumbing.

    The preamble is the ``header`` line followed by one bullet per
    relevant reflection, formatted as
    ``- [<verdict>] <lesson>``. Bullets are rendered in chronological
    order (oldest first → newest last) so the model sees the trajectory
    of learning, not just the latest snapshot.
    """
    pool = memory.for_tags(tags) if tags else memory.all()
    if not pool:
        return ""
    selected = pool[-k:] if k > 0 else pool
    lines = [header]
    for r in selected:
        lesson_one_line = " ".join(r.lesson.split())
        lines.append(f"- [{r.verdict}] {lesson_one_line}")
    return "\n".join(lines) + "\n"
