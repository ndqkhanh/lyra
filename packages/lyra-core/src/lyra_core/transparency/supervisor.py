"""Background fleet supervisor — Phase D of the Lyra 322-326 evolution plan.

The supervisor runs a daemon thread that periodically scans the FleetView,
escalates attention priority based on observable signals (stale agents,
blocked state, high cost), and invokes optional user-supplied callbacks.

Grounded in:
- Doc 325 §4.3 — Supervisor escalation policy
- Doc 322 §8.3 — Human-control SLO (pending approval timeout)
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from .agent_view import AttentionPriority, FleetView

__all__ = [
    "SupervisorConfig",
    "FleetSupervisor",
]


@dataclass(frozen=True)
class SupervisorConfig:
    """Tunable thresholds for the fleet supervisor."""

    poll_interval_s: float = 15.0          # how often to scan the fleet
    stale_after_s: float = 120.0           # escalate if not updated for this long
    blocked_priority: AttentionPriority = AttentionPriority.P1
    stale_priority: AttentionPriority = AttentionPriority.P2
    done_priority: AttentionPriority = AttentionPriority.P4


EscalationCallback = Callable[[str, AttentionPriority, str], None]
# (agent_id, new_priority, reason)


class FleetSupervisor:
    """Daemon thread that watches FleetView and escalates agent attention.

    Usage::

        fleet = FleetView()
        supervisor = FleetSupervisor(fleet, on_escalate=print)
        supervisor.start()
        # ... agents register and update ...
        supervisor.stop()
    """

    def __init__(
        self,
        fleet: FleetView,
        config: SupervisorConfig | None = None,
        on_escalate: EscalationCallback | None = None,
    ) -> None:
        self._fleet = fleet
        self._config = config or SupervisorConfig()
        self._on_escalate = on_escalate or (lambda *_: None)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ---------------------------------------------------------------- #
    # Lifecycle                                                          #
    # ---------------------------------------------------------------- #

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="lyra-fleet-supervisor"
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
            self._thread = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ---------------------------------------------------------------- #
    # Core scan                                                          #
    # ---------------------------------------------------------------- #

    def scan_once(self) -> list[tuple[str, AttentionPriority, str]]:
        """Run one scan pass. Returns list of (agent_id, priority, reason) escalations."""
        cfg = self._config
        now = time.time()
        escalations: list[tuple[str, AttentionPriority, str]] = []

        for rec in self._fleet.list_agents():
            new_priority: AttentionPriority | None = None
            reason = ""

            if rec.state in ("error", "blocked"):
                new_priority = cfg.blocked_priority
                reason = f"state={rec.state}"
            elif rec.state == "done":
                new_priority = cfg.done_priority
                reason = "agent completed"
            elif (now - rec.last_updated) > cfg.stale_after_s:
                new_priority = cfg.stale_priority
                reason = f"stale: no update for {now - rec.last_updated:.0f}s"

            if new_priority is not None and new_priority != rec.attention_priority:
                self._fleet.set_priority(rec.agent_id, new_priority)
                self._on_escalate(rec.agent_id, new_priority, reason)
                escalations.append((rec.agent_id, new_priority, reason))

        return escalations

    # ---------------------------------------------------------------- #
    # Internal                                                           #
    # ---------------------------------------------------------------- #

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.scan_once()
            self._stop_event.wait(timeout=self._config.poll_interval_s)
