"""Relay Race — continuous autonomous operation with baton-pass checkpointing.

Enables 8+ hour autonomous sessions by breaking long-running operations into
relay legs with explicit state handoff. Each leg produces a baton that the
next leg picks up, enabling crash recovery and session continuity.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum


class LegStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class RelayState(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    RECOVERING = "recovering"
    COMPLETED = "completed"


@dataclass(frozen=True)
class Baton:
    """Checkpoint state passed between relay legs."""

    relay_id: str
    leg_index: int
    state_snapshot: tuple[tuple[str, str], ...]
    progress: float
    started_at: float
    handed_off_at: float
    accumulated_reward: float


@dataclass(frozen=True)
class LegResult:
    leg_index: int
    status: LegStatus
    duration_sec: float
    output: str
    error: str
    reward: float
    baton: Baton | None


@dataclass
class RelayConfig:
    max_leg_duration_sec: float = 1800.0
    max_legs: int = 16
    checkpoint_interval_sec: float = 300.0
    auto_recover: bool = True
    max_retries_per_leg: int = 2


class RelayRace:
    """Continuous operation engine with baton-pass checkpointing.

    Manages a sequence of "legs" where each leg is an autonomous work unit.
    The baton carries accumulated state between legs, enabling graceful
    recovery if any leg fails or times out.
    """

    def __init__(self, config: RelayConfig | None = None) -> None:
        self.config = config or RelayConfig()
        self._legs: list[LegResult] = []
        self._checkpoints: list[Baton] = []
        self._state: RelayState = RelayState.IDLE
        self._started_at: float = 0.0
        self._completed_at: float = 0.0

    def start(self, initial_state: dict[str, str] | None = None) -> Baton:
        """Initialize a new relay race with the first baton."""
        self._state = RelayState.RUNNING
        self._started_at = time.time()

        state_tuples = tuple(sorted((k, v) for k, v in (initial_state or {}).items()))
        baton = Baton(
            relay_id=f"relay-{int(self._started_at)}",
            leg_index=0,
            state_snapshot=state_tuples,
            progress=0.0,
            started_at=self._started_at,
            handed_off_at=self._started_at,
            accumulated_reward=0.0,
        )
        self._checkpoints.append(baton)
        return baton

    def run_leg(
        self,
        baton: Baton,
        execute_fn,  # callable(baton) -> tuple[str, float]
    ) -> LegResult:
        """Run a single relay leg.

        Args:
            baton: The baton from the previous leg (or start).
            execute_fn: Callable that receives the baton and returns (output, reward).

        Returns:
            LegResult with status, output, and the next baton.
        """
        if self._state != RelayState.RUNNING:
            self._state = RelayState.RUNNING

        if baton.leg_index >= self.config.max_legs:
            self._state = RelayState.COMPLETED
            self._completed_at = time.time()
            return LegResult(
                leg_index=baton.leg_index,
                status=LegStatus.COMPLETED,
                duration_sec=0.0,
                output="Max legs reached",
                error="",
                reward=0.0,
                baton=None,
            )

        leg_start = time.time()

        try:
            output, reward = execute_fn(baton)
            duration = time.time() - leg_start

            if duration > self.config.max_leg_duration_sec:
                status = LegStatus.TIMEOUT
            else:
                status = LegStatus.COMPLETED

            new_progress = min(1.0, baton.progress + (1.0 / self.config.max_legs))
            next_baton = Baton(
                relay_id=baton.relay_id,
                leg_index=baton.leg_index + 1,
                state_snapshot=_merge_state(baton.state_snapshot, {"last_output": output}),
                progress=new_progress,
                started_at=leg_start,
                handed_off_at=time.time(),
                accumulated_reward=baton.accumulated_reward + reward,
            )
            self._checkpoints.append(next_baton)
            exc_msg = ""

        except Exception as exc:
            duration = time.time() - leg_start
            status = LegStatus.FAILED
            output = ""
            reward = 0.0
            exc_msg = str(exc)

            if self.config.auto_recover and baton.leg_index < self.config.max_legs:
                self._state = RelayState.RECOVERING
                next_baton = Baton(
                    relay_id=baton.relay_id,
                    leg_index=baton.leg_index,
                    state_snapshot=_merge_state(baton.state_snapshot, {"error": exc_msg}),
                    progress=baton.progress,
                    started_at=time.time(),
                    handed_off_at=time.time(),
                    accumulated_reward=baton.accumulated_reward,
                )
            else:
                next_baton = None
                self._state = RelayState.COMPLETED

        result = LegResult(
            leg_index=baton.leg_index,
            status=status,
            duration_sec=duration,
            output=output,
            error=exc_msg,
            reward=reward,
            baton=next_baton,
        )
        self._legs.append(result)

        if next_baton is None or next_baton.progress >= 1.0:
            self._state = RelayState.COMPLETED
            self._completed_at = time.time()
        elif status == LegStatus.FAILED and not self.config.auto_recover:
            self._state = RelayState.PAUSED

        return result

    def get_checkpoint(self) -> Baton | None:
        """Get the latest checkpoint baton for recovery."""
        return self._checkpoints[-1] if self._checkpoints else None

    def pause(self) -> None:
        self._state = RelayState.PAUSED

    def resume(self) -> Baton | None:
        if self._state == RelayState.PAUSED and self._checkpoints:
            self._state = RelayState.RUNNING
            return self._checkpoints[-1]
        return None

    def stats(self) -> dict:
        completed = sum(1 for leg in self._legs if leg.status == LegStatus.COMPLETED)
        failed = sum(1 for leg in self._legs if leg.status == LegStatus.FAILED)
        total_reward = sum(leg.reward for leg in self._legs)
        total_duration = sum(leg.duration_sec for leg in self._legs)

        return {
            "state": self._state.value,
            "total_legs": len(self._legs),
            "completed": completed,
            "failed": failed,
            "total_reward": round(total_reward, 4),
            "total_duration_sec": round(total_duration, 2),
            "progress": round(self._checkpoints[-1].progress if self._checkpoints else 0.0, 4),
            "checkpoints": len(self._checkpoints),
        }

    @property
    def state(self) -> RelayState:
        return self._state

    @property
    def leg_results(self) -> list[LegResult]:
        return list(self._legs)


def _merge_state(
    existing: tuple[tuple[str, str], ...],
    updates: dict[str, str],
) -> tuple[tuple[str, str], ...]:
    state = dict(existing)
    state.update(updates)
    return tuple(sorted(state.items()))
