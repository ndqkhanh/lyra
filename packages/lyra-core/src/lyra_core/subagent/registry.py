"""Subagent registry — the backing store for ``/agents`` and ``/spawn``.

The existing :class:`SubagentOrchestrator` is the *heavyweight*
worktree-scoped fan-out used for batch DAG runs. This lighter-weight
:class:`SubagentRegistry` is what the REPL talks to: one record per
spawned subagent, a stable id, a state machine
(``pending → running → done | failed | cancelled``), and a hook to
inject the actual dispatch callable (usually the ``task`` tool from
``lyra_core.tools.task``).

Separation of concerns:

- :class:`SubagentRegistry` owns ids, state, listing, cancellation.
- The injected ``task`` callable owns *how* the fork actually runs
  (sync in-process, worktree-isolated, threaded, etc.).

Sync-by-default: ``spawn(description)`` calls the task immediately and
waits for it. For long-running jobs the CLI can call ``reserve()``
first (reserves an id in ``pending``), hand the id to the user, then
call ``dispatch(id)`` from a worker — the same :class:`SubagentRecord`
transitions so ``list_all`` reflects live state.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Literal

SubagentState = Literal["pending", "running", "done", "failed", "cancelled"]


@dataclass
class SubagentRecord:
    """One row in the subagent registry."""

    id: str
    description: str
    subagent_type: str = "general"
    state: SubagentState = "pending"
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: dict | None = None
    error: str | None = None

    def is_terminal(self) -> bool:
        return self.state in ("done", "failed", "cancelled")


class SubagentRegistry:
    """Track spawned subagents and their outcomes.

    Args:
        task: Callable invoked to actually run a subagent. The
            registry hands it ``(description, **spawn_kwargs)`` and
            expects it to return a ``TaskResult``-shaped dict (see
            :mod:`lyra_core.tools.task`). Any exception it raises
            transitions the record to ``"failed"``.
        id_prefix: Prefix for generated record ids (default ``"sub"``).
    """

    def __init__(
        self,
        *,
        task: Callable[..., dict],
        id_prefix: str = "sub",
    ) -> None:
        self._task = task
        self._records: dict[str, SubagentRecord] = {}
        self._order: list[str] = []
        self._id_prefix = id_prefix
        self._counter = itertools.count(1)
        # Preserve the kwargs the user asked for so ``dispatch`` can
        # replay them when the CLI separates reserve/dispatch.
        self._pending_kwargs: dict[str, dict] = {}

    # ---- public API ------------------------------------------------- #

    def list_all(self) -> list[SubagentRecord]:
        """Return every record in insertion order."""
        return [self._records[i] for i in self._order]

    def get(self, id: str) -> SubagentRecord | None:
        return self._records.get(id)

    def reserve(
        self,
        description: str,
        *,
        subagent_type: str = "general",
        **kwargs: Any,
    ) -> SubagentRecord:
        """Allocate an id for a subagent that will dispatch later.

        The record lands in ``"pending"`` state; call :meth:`dispatch`
        with the returned id when you are ready to actually run the
        fork. Useful for a REPL that wants to hand the user an id
        before blocking on the fork.
        """
        desc = description.strip()
        if not desc:
            raise ValueError("description must be a non-empty string")
        rec_id = self._next_id()
        rec = SubagentRecord(
            id=rec_id,
            description=desc,
            subagent_type=subagent_type,
        )
        self._records[rec_id] = rec
        self._order.append(rec_id)
        self._pending_kwargs[rec_id] = {
            "subagent_type": subagent_type,
            **kwargs,
        }
        return rec

    def dispatch(self, id: str) -> SubagentRecord | None:
        """Run the ``task`` callable for a reserved record.

        No-op (returns the record unchanged) when the record is
        already terminal.
        """
        rec = self._records.get(id)
        if rec is None:
            return None
        if rec.is_terminal():
            return rec
        kwargs = self._pending_kwargs.pop(id, {})
        self._run(rec, kwargs)
        return rec

    def spawn(
        self,
        description: str,
        *,
        subagent_type: str = "general",
        **kwargs: Any,
    ) -> SubagentRecord:
        """Reserve + dispatch a new subagent synchronously."""
        rec = self.reserve(
            description, subagent_type=subagent_type, **kwargs
        )
        self._run(rec, {"subagent_type": subagent_type, **kwargs})
        # ``_run`` already consumed pending kwargs via self._run; drop
        # the reserve entry if still hanging around.
        self._pending_kwargs.pop(rec.id, None)
        return rec

    def cancel(self, id: str) -> bool:
        """Cancel a pending record.

        Returns True when a ``pending`` record was transitioned to
        ``cancelled``; False otherwise (unknown id, already terminal,
        already running).
        """
        rec = self._records.get(id)
        if rec is None:
            return False
        if rec.state != "pending":
            return False
        rec.state = "cancelled"
        rec.finished_at = datetime.now(timezone.utc)
        self._pending_kwargs.pop(id, None)
        return True

    # ---- internal --------------------------------------------------- #

    def _next_id(self) -> str:
        return f"{self._id_prefix}-{next(self._counter):04d}"

    def _run(self, rec: SubagentRecord, kwargs: dict) -> None:
        if rec.state == "cancelled":
            return
        rec.state = "running"
        rec.started_at = datetime.now(timezone.utc)
        try:
            result = self._task(rec.description, **kwargs)
        except Exception as exc:  # fork blew up — record and keep going
            rec.state = "failed"
            rec.error = f"{type(exc).__name__}: {exc}"
            rec.finished_at = datetime.now(timezone.utc)
            return
        rec.state = "done"
        rec.result = result if isinstance(result, dict) else {"final_text": str(result)}
        rec.finished_at = datetime.now(timezone.utc)


__all__ = ["SubagentRecord", "SubagentRegistry", "SubagentState"]
