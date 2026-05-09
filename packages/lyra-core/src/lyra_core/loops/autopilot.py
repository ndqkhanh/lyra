"""L312-7 — `lyra autopilot` long-running supervisor.

Anchor: ``docs/308-autonomy-loop-synthesis.md`` layer 7.

A user-space supervisor that drives Ralph runs + cron jobs +
:class:`LoopSession`s concurrently with SQLite checkpoint persistence.
Two load-bearing properties:

1. **Explicit-only resume.** A loop in ``pending_resume`` (placed there
   by ``LoopStore.reconcile_on_startup``) does NOT silently re-fire.
   :meth:`Autopilot.resume` is the only way back to ``running`` — the
   user inspects state first.
2. **Crash-safe checkpoint cadence.** Every transition (start, step,
   terminal) is committed to SQLite immediately. A SIGKILL between
   transitions costs at most one iteration's worth of work.

The supervisor is intentionally *small*. It does not own thread pools,
process supervision, or systemd integration — those are CLI surfaces
that compose above it. The supervisor owns: registration, transition,
crash reconciliation, and queryable status.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from .store import LoopRecord, LoopStore


__all__ = ["Autopilot", "AutopilotResumeError"]


class AutopilotResumeError(RuntimeError):
    """Raised when ``resume()`` is called on a loop that's not in ``pending_resume``."""


@dataclass
class Autopilot:
    """Supervisor over running and resumable loops.

    Construct once per host with::

        autopilot = Autopilot(store=LoopStore(db_path="~/.lyra/loops/loops.sqlite"))
        autopilot.start_session()  # reconciles stale rows
    """

    store: LoopStore
    started: bool = field(default=False, init=False)
    reconciled_ids: list[str] = field(default_factory=list, init=False)

    # ---- public API ------------------------------------------------- #

    def start_session(self) -> list[str]:
        """Reconcile stale rows on startup; return ids moved to pending_resume.

        Idempotent — calling multiple times only advances the cutoff if
        new stale rows have appeared.
        """
        ids = self.store.reconcile_on_startup()
        self.reconciled_ids.extend(ids)
        self.started = True
        return ids

    def register(
        self,
        *,
        loop_id: str,
        kind: str,
        run_dir: Path | str,
        payload: Optional[dict] = None,
    ) -> LoopRecord:
        """Register a new running loop. Idempotent — re-registering an
        id refreshes ``updated_at`` and bumps the row back to ``running``."""
        import json as _json
        existing = self.store.get(loop_id)
        if existing is not None:
            # Re-register — only allowed when not in pending_resume.
            if existing.state == "pending_resume":
                raise AutopilotResumeError(
                    f"loop {loop_id} is in pending_resume; call resume() explicitly"
                )
        record = LoopRecord(
            id=loop_id, kind=kind, state="running",
            run_dir=str(run_dir),
            payload_json=_json.dumps(payload or {}, sort_keys=True),
        )
        self.store.upsert(record)
        return record

    def heartbeat(
        self,
        loop_id: str,
        *,
        cum_usd: float,
        iter_count: int,
        contract_state: str,
    ) -> None:
        """Called by the running loop on every iteration boundary."""
        rec = self.store.get(loop_id)
        if rec is None:
            return  # silently — heartbeat after de-registration is OK
        rec.cum_usd = cum_usd
        rec.iter_count = iter_count
        rec.contract_state = contract_state
        rec.state = "running"
        self.store.upsert(rec)

    def complete(
        self,
        loop_id: str,
        *,
        contract_state: str,
        terminal_cause: Optional[str],
    ) -> None:
        """Move a loop to ``completed`` (FULFILLED/EXPIRED) or
        ``terminated`` (VIOLATED/TERMINATED)."""
        terminal_kind = "terminated" if contract_state in ("violated", "terminated") else "completed"
        rec = self.store.get(loop_id)
        if rec is None:
            return
        rec.contract_state = contract_state
        rec.terminal_cause = terminal_cause
        rec.state = terminal_kind
        self.store.upsert(rec)

    def resume(self, loop_id: str) -> LoopRecord:
        """Explicit resume from ``pending_resume`` → ``running``.

        The caller (CLI or REPL slash) is responsible for inspecting
        the row first and then calling :meth:`resume`. The supervisor
        does not auto-resume.
        """
        rec = self.store.get(loop_id)
        if rec is None:
            raise KeyError(f"unknown loop id {loop_id!r}")
        if rec.state != "pending_resume":
            raise AutopilotResumeError(
                f"loop {loop_id} is in state {rec.state!r}, not pending_resume"
            )
        rec.state = "running"
        rec.terminal_cause = None
        self.store.upsert(rec)
        return rec

    def status(self) -> list[LoopRecord]:
        """Return every loop, all states. Caller filters for display."""
        return self.store.list_state()

    def running(self) -> list[LoopRecord]:
        return self.store.list_state("running")

    def pending_resume(self) -> list[LoopRecord]:
        return self.store.list_state("pending_resume")
