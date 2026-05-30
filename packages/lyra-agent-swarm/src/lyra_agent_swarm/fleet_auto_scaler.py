"""Fleet Auto-Scaling — dynamic worker scaling based on load metrics.

Implements autonomous fleet auto-scaling:
  - Load-based scale up/down with configurable thresholds
  - Queue depth and latency monitoring per squad
  - Cooldown periods to prevent oscillation
  - Min/max worker bounds per squad
  - Scale event tracking and history
  - Multi-squad concurrent scaling evaluation
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import uuid4


class ScaleDirection(StrEnum):
    """Direction of a scaling event."""

    UP = "up"
    DOWN = "down"


@dataclass
class AutoScalerConfig:
    """Configuration for the fleet auto-scaler."""

    min_workers_per_squad: int = 1
    max_workers_per_squad: int = 20
    scale_up_threshold: float = 0.75
    scale_down_threshold: float = 0.3
    cooldown_seconds: float = 60.0
    scale_step: int = 2
    max_scale_step: int = 5


@dataclass
class SquadLoad:
    """Current load metrics for a squad."""

    squad_id: str
    current_workers: int
    queue_depth: int
    avg_latency_ms: float
    load_factor: float
    updated_at: float = field(default_factory=time.monotonic)


@dataclass(frozen=True)
class ScaleEvent:
    """A scaling event — either scale-up or scale-down."""

    event_id: str = field(default_factory=lambda: f"scale-{uuid4().hex[:12]}")
    squad_id: str = ""
    direction: ScaleDirection = ScaleDirection.UP
    current_workers: int = 0
    new_workers: int = 0
    reason: str = ""
    timestamp: float = field(default_factory=time.monotonic)
    applied: bool = False

    def mark_applied(self) -> ScaleEvent:
        return ScaleEvent(
            event_id=self.event_id,
            squad_id=self.squad_id,
            direction=self.direction,
            current_workers=self.current_workers,
            new_workers=self.new_workers,
            reason=self.reason,
            timestamp=self.timestamp,
            applied=True,
        )


class AutoScaler:
    """Dynamic fleet auto-scaler for agent squads.

    Monitors squad load metrics and automatically scales workers
    up or down based on configurable thresholds. Cooldown periods
    prevent oscillation.

    Usage::

        scaler = AutoScaler(config=AutoScalerConfig(cooldown_seconds=30.0))
        scaler.update_squad_load("squad-1", queue_depth=50, latency_ms=300.0, current_workers=5)
        events = scaler.evaluate()
        for event in events:
            if event.direction == ScaleDirection.UP:
                add_workers(event.squad_id, event.new_workers - event.current_workers)
    """

    def __init__(self, config: AutoScalerConfig | None = None) -> None:
        self.config = config or AutoScalerConfig()
        self._loads: dict[str, SquadLoad] = {}
        self._events: list[ScaleEvent] = []
        self._last_scale: dict[str, float] = {}

    # ── Properties ───────────────────────────────────────────────

    @property
    def event_count(self) -> int:
        return len(self._events)

    # ── Load Tracking ────────────────────────────────────────────

    def update_squad_load(
        self,
        squad_id: str,
        queue_depth: int,
        latency_ms: float,
        current_workers: int,
    ) -> SquadLoad:
        """Update load metrics for a squad."""
        max_queue = max(1, current_workers * 10)
        queue_factor = min(1.0, queue_depth / max_queue)
        latency_factor = min(1.0, latency_ms / 1000.0)
        load_factor = (queue_factor * 0.6) + (latency_factor * 0.4)

        load = SquadLoad(
            squad_id=squad_id,
            current_workers=current_workers,
            queue_depth=queue_depth,
            avg_latency_ms=latency_ms,
            load_factor=load_factor,
        )
        self._loads[squad_id] = load
        return load

    def get_squad_load(self, squad_id: str) -> SquadLoad | None:
        """Get current load metrics for a squad."""
        return self._loads.get(squad_id)

    # ── Scaling Evaluation ───────────────────────────────────────

    def evaluate(self) -> list[ScaleEvent]:
        """Evaluate all squads and generate scaling events.

        Returns list of ScaleEvents. Callers should apply the events
        and call mark_applied() on each.
        """
        events: list[ScaleEvent] = []
        now = time.monotonic()

        for squad_id, load in self._loads.items():
            if self._in_cooldown(squad_id, now):
                continue

            event = self._evaluate_squad(load)
            if event is not None:
                events.append(event)
                self._last_scale[squad_id] = now

        self._events.extend(events)
        return events

    def get_history(self) -> list[ScaleEvent]:
        """Return all scaling events."""
        return list(self._events)

    def get_status(self) -> dict:
        """Return current scaling status."""
        return {
            "squads": len(self._loads),
            "total_events": len(self._events),
            "cooldowns": {
                sid: self._in_cooldown(sid) for sid in self._loads
            },
            "loads": {
                sid: load.load_factor for sid, load in self._loads.items()
            },
        }

    def reset(self) -> None:
        """Reset all state."""
        self._loads.clear()
        self._events.clear()
        self._last_scale.clear()

    # ── Private ───────────────────────────────────────────────────

    def _evaluate_squad(self, load: SquadLoad) -> ScaleEvent | None:
        """Evaluate a single squad for scaling."""
        cfg = self.config
        current = load.current_workers

        if load.load_factor >= cfg.scale_up_threshold and current < cfg.max_workers_per_squad:
            scale_amount = min(
                cfg.scale_step,
                cfg.max_scale_step,
                cfg.max_workers_per_squad - current,
            )
            new_workers = current + scale_amount
            return ScaleEvent(
                squad_id=load.squad_id,
                direction=ScaleDirection.UP,
                current_workers=current,
                new_workers=new_workers,
                reason=f"High load: factor={load.load_factor:.2f}, queue={load.queue_depth}",
            )

        if load.load_factor <= cfg.scale_down_threshold and current > cfg.min_workers_per_squad:
            scale_amount = min(
                cfg.scale_step,
                current - cfg.min_workers_per_squad,
            )
            new_workers = max(cfg.min_workers_per_squad, current - scale_amount)
            return ScaleEvent(
                squad_id=load.squad_id,
                direction=ScaleDirection.DOWN,
                current_workers=current,
                new_workers=new_workers,
                reason=f"Low load: factor={load.load_factor:.2f}, queue={load.queue_depth}",
            )

        return None

    def _in_cooldown(self, squad_id: str, now: float | None = None) -> bool:
        """Check if a squad is in its cooldown period."""
        current = now or time.monotonic()
        last = self._last_scale.get(squad_id, 0.0)
        return (current - last) < self.config.cooldown_seconds
