"""L311-2 — Shared task list (filesystem with file-locking).

A :class:`SharedTaskList` is the coordination substrate that lets a
``LeadSession`` and its teammates trade work without ever touching each
other's process state. Every task is one Markdown file with YAML
frontmatter; claim / complete operations are bracketed by a POSIX
file-lock on a sibling ``_lock`` file (``fcntl.flock`` on Unix; a
fallback ``msvcrt.locking`` shim is used on Windows).

State machine::

    pending ──claim()──► in_progress ──complete()──► completed
       │                       │
       │                       └─fail()──► blocked
       │
       └─add(depends_on=[X])──► blocked  (auto-unblocks when X completes)

Every state transition writes the entire frontmatter back atomically
(write-temp-then-rename), so a partial write can never corrupt a
task.

The implementation is intentionally **stdlib-only** (no PyYAML, no
filelock, no SQLite) — Lyra's existing ``ProceduralMemory`` already
covers SQL persistence for ranked retrieval; the shared task list is
strictly a *coordination* primitive and lives in the filesystem so a
human operator can ``cat ~/.lyra/teams/{name}/tasks/*.md`` to inspect
or repair state from outside the agent process.
"""
from __future__ import annotations

import contextlib
import os
import secrets
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Literal


TaskState = Literal["pending", "in_progress", "completed", "blocked"]
_STATES: tuple[TaskState, ...] = ("pending", "in_progress", "completed", "blocked")


# ---- file-lock shim --------------------------------------------------


@contextlib.contextmanager
def _flock(lock_path: Path) -> Iterator[None]:
    """Cross-platform exclusive file lock.

    Uses ``fcntl.flock`` on Unix and ``msvcrt.locking`` on Windows.
    Acquires within ~5 s or raises ``TimeoutError``; the timeout is
    generous because contention should be rare (tasks are claimed for
    minutes, not microseconds).
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fp = open(lock_path, "a+b")
    deadline = time.time() + 5.0
    try:
        if os.name == "posix":
            import fcntl

            while True:
                try:
                    fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.time() > deadline:
                        raise TimeoutError(f"could not acquire {lock_path}")
                    time.sleep(0.05)
            try:
                yield
            finally:
                fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
        else:  # pragma: no cover - Windows path, untested in macOS-only CI
            import msvcrt

            while True:
                try:
                    msvcrt.locking(fp.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.time() > deadline:
                        raise TimeoutError(f"could not acquire {lock_path}")
                    time.sleep(0.05)
            try:
                yield
            finally:
                with contextlib.suppress(Exception):
                    msvcrt.locking(fp.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        fp.close()


# ---- minimal YAML-frontmatter parser/serializer -----------------------
#
# We deliberately avoid a YAML dependency. The schema is fixed; values
# are plain strings, ints, lists of strings, or null. Anything richer
# belongs in the Markdown body, not the frontmatter.


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    head = text[4:end]
    body = text[end + 5 :]
    meta: dict[str, Any] = {}
    for raw_line in head.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val == "" or val == "null" or val == "~":
            meta[key] = None
        elif val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            if not inner:
                meta[key] = []
            else:
                meta[key] = [s.strip().strip("\"'") for s in inner.split(",")]
        elif val.lower() in ("true", "false"):
            meta[key] = val.lower() == "true"
        elif val.lstrip("-").isdigit():
            meta[key] = int(val)
        else:
            meta[key] = val.strip("\"'")
    return meta, body


def _emit_frontmatter(meta: dict[str, Any], body: str) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if v is None:
            lines.append(f"{k}: null")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, list):
            if not v:
                lines.append(f"{k}: []")
            else:
                joined = ", ".join(f'"{x}"' for x in v)
                lines.append(f"{k}: [{joined}]")
        elif isinstance(v, int):
            lines.append(f"{k}: {v}")
        else:
            s = str(v).replace('"', '\\"')
            lines.append(f'{k}: "{s}"')
    lines.append("---")
    return "\n".join(lines) + "\n" + body


# ---- data types -------------------------------------------------------


@dataclass
class Task:
    id: str
    title: str
    state: TaskState
    owner: str | None
    created_at: float
    depends_on: tuple[str, ...] = ()
    body: str = ""
    output: str | None = None
    failure_reason: str | None = None

    def to_meta(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "state": self.state,
            "owner": self.owner,
            "created_at": int(self.created_at),
            "depends_on": list(self.depends_on),
            "output": self.output,
            "failure_reason": self.failure_reason,
        }

    @classmethod
    def from_meta(cls, meta: dict[str, Any], body: str) -> "Task":
        return cls(
            id=str(meta.get("id") or ""),
            title=str(meta.get("title") or ""),
            state=meta.get("state") or "pending",  # type: ignore[arg-type]
            owner=meta.get("owner"),
            created_at=float(meta.get("created_at") or 0),
            depends_on=tuple(meta.get("depends_on") or ()),
            body=body.strip(),
            output=meta.get("output"),
            failure_reason=meta.get("failure_reason"),
        )


@dataclass(frozen=True)
class TaskSummary:
    pending: int
    in_progress: int
    completed: int
    blocked: int
    total: int


# ---- the list ---------------------------------------------------------


class SharedTaskList:
    """A directory of task files plus a sibling lock file."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = self.root / "_lock"

    # ---- internal helpers ----------------------------------------

    @staticmethod
    def _new_id() -> str:
        # Sortable + unique. Sort keeps "next ready" deterministic.
        return f"{int(time.time() * 1000):013d}-{secrets.token_hex(3)}"

    def _path(self, task_id: str) -> Path:
        return self.root / f"task-{task_id}.md"

    def _read(self, task_id: str) -> Task | None:
        p = self._path(task_id)
        if not p.exists():
            return None
        text = p.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(text)
        return Task.from_meta(meta, body)

    def _write_atomic(self, task: Task) -> None:
        meta = task.to_meta()
        text = _emit_frontmatter(meta, task.body or "")
        target = self._path(task.id)
        tmp = target.with_suffix(".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, target)

    def _iter_tasks(self) -> Iterator[Task]:
        for p in sorted(self.root.glob("task-*.md")):
            text = p.read_text(encoding="utf-8")
            meta, body = _parse_frontmatter(text)
            yield Task.from_meta(meta, body)

    # ---- public API -----------------------------------------------

    def create(
        self,
        *,
        title: str,
        owner: str | None = None,
        depends_on: Iterable[str] = (),
        body: str = "",
    ) -> Task:
        """Add a new task. Initial state is ``blocked`` if dependencies
        exist, otherwise ``pending``."""
        deps = tuple(depends_on)
        with _flock(self._lock):
            tid = self._new_id()
            initial: TaskState = "blocked" if deps else "pending"
            task = Task(
                id=tid,
                title=title,
                state=initial,
                owner=owner,
                created_at=time.time(),
                depends_on=deps,
                body=body,
            )
            self._write_atomic(task)
            return task

    def get(self, task_id: str) -> Task | None:
        return self._read(task_id)

    def all(self) -> list[Task]:
        return list(self._iter_tasks())

    def next_ready_for(self, owner: str) -> Task | None:
        """Return the next ``pending`` task already pre-assigned to ``owner``."""
        with _flock(self._lock):
            for t in self._iter_tasks():
                if t.state == "pending" and t.owner == owner:
                    return t
            return None

    def claim_unowned(self, owner: str) -> Task | None:
        """Atomically claim the first pending unowned task for ``owner``.

        Sets ``owner`` but leaves state as ``pending`` so :meth:`start`
        is the explicit transition that flips to ``in_progress``. This
        keeps the claim and the start as separate primitives — useful
        when a teammate wants to ack a task before working on it.
        """
        with _flock(self._lock):
            for t in self._iter_tasks():
                if t.state == "pending" and t.owner is None:
                    t.owner = owner
                    self._write_atomic(t)
                    return t
            return None

    def start(self, task_id: str, *, owner: str) -> Task:
        with _flock(self._lock):
            t = self._read(task_id)
            if t is None:
                raise KeyError(task_id)
            if t.state != "pending":
                raise ValueError(
                    f"task {task_id} state {t.state!r} cannot transition to in_progress"
                )
            if t.owner is not None and t.owner != owner:
                raise ValueError(
                    f"task {task_id} already claimed by {t.owner!r}, not {owner!r}"
                )
            t.owner = owner
            t.state = "in_progress"
            self._write_atomic(t)
            return t

    def complete(self, task_id: str, *, output: str | None = None) -> Task:
        with _flock(self._lock):
            t = self._read(task_id)
            if t is None:
                raise KeyError(task_id)
            if t.state != "in_progress":
                raise ValueError(
                    f"task {task_id} state {t.state!r} cannot complete"
                )
            t.state = "completed"
            t.output = output
            self._write_atomic(t)
            self._unblock_dependents(task_id)
            return t

    def fail(self, task_id: str, *, reason: str) -> Task:
        with _flock(self._lock):
            t = self._read(task_id)
            if t is None:
                raise KeyError(task_id)
            t.state = "blocked"
            t.failure_reason = reason
            self._write_atomic(t)
            return t

    def _unblock_dependents(self, completed_id: str) -> None:
        """Promote any ``blocked`` task whose deps are now all completed
        back to ``pending``. Caller must hold the lock."""
        completed: set[str] = {
            t.id for t in self._iter_tasks() if t.state == "completed"
        }
        for t in list(self._iter_tasks()):
            if t.state != "blocked" or t.failure_reason is not None:
                continue
            if t.depends_on and all(d in completed for d in t.depends_on):
                t.state = "pending"
                self._write_atomic(t)

    def summary(self) -> TaskSummary:
        counts = {s: 0 for s in _STATES}
        total = 0
        for t in self._iter_tasks():
            counts[t.state] = counts.get(t.state, 0) + 1
            total += 1
        return TaskSummary(
            pending=counts["pending"],
            in_progress=counts["in_progress"],
            completed=counts["completed"],
            blocked=counts["blocked"],
            total=total,
        )


__all__ = [
    "SharedTaskList",
    "Task",
    "TaskState",
    "TaskSummary",
]
