"""Sleep/wake cycle — power management for autonomous agent sessions.

Provides the :class:`SleepWakeScheduler` that controls when an agent sleeps
and wakes, with three sleep modes and configurable wake triggers. During
light sleep the scheduler runs a :class:`DreamPhase` that consolidates
session memory and reflects on outcomes — a cognitive offload cycle that
keeps the agent fresh and efficient.
"""

from __future__ import annotations

import abc
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sleep modes
# ---------------------------------------------------------------------------


class SleepMode(str, Enum):
    """How deeply the agent sleeps.

    * ``LIGHT`` — pause LLM calls only; keep the process alive. During
      light sleep the agent may run a DreamPhase for memory consolidation.
    * ``DEEP`` — checkpoint state then suspend the process (SIGSTOP /
      park).  Wakes when a trigger fires.
    * ``HIBERNATE`` — checkpoint state then shut down.  The session is
      persisted to the store and the process exits.  Waking requires a
      full restart from checkpoint.
    """

    LIGHT = "light"
    DEEP = "deep"
    HIBERNATE = "hibernate"


# ---------------------------------------------------------------------------
# Wake triggers
# ---------------------------------------------------------------------------


class WakeTrigger(str, Enum):
    """What can wake a sleeping agent."""

    SCHEDULED_TIME = "scheduled_time"
    NEW_MESSAGE = "new_message"
    BUDGET_THRESHOLD = "budget_threshold"
    ERROR_THRESHOLD = "error_threshold"
    MANUAL_OVERRIDE = "manual_override"


# ---------------------------------------------------------------------------
# Sleep / wake policies
# ---------------------------------------------------------------------------


class SleepReason(str, Enum):
    """Why the agent decided to sleep."""

    IDLE_TIMEOUT = "idle_timeout"          # No tasks for N minutes
    COST_SPIKE = "cost_spike"              # Token burn rate above threshold
    OVERNIGHT = "overnight"                # Scheduled off-hours
    MANUAL = "manual"                      # User-requested sleep


class WakeReason(str, Enum):
    """Why the agent decided to wake."""

    SCHEDULED_RESUME = "scheduled_resume"  # Back at a scheduled time
    URGENT_MESSAGE = "urgent_message"      # High-priority message arrived
    MANUAL_OVERRIDE = "manual_override"    # User-requested wake
    BUDGET_RESET = "budget_reset"          # Budget window refreshed
    ERROR_RECOVERED = "error_recovered"    # Error rate dropped below threshold


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SleepPolicy:
    """Policy that decides *when* to sleep.

    Attributes:
        idle_threshold_seconds: Sleep after this many seconds of inactivity.
        cost_spike_threshold_tokens_per_min: Sleep when token burn rate exceeds
            this value (0 = disabled).
        overnight_start_hour: Hour (0-23, UTC) when overnight sleep starts
            (e.g. 22 for 10 PM). Set to None to disable overnight sleep.
        overnight_end_hour: Hour (0-23, UTC) when overnight sleep ends
            (e.g. 6 for 6 AM).
        preferred_mode: The sleep mode to use when this policy triggers.
    """

    idle_threshold_seconds: int = 600        # 10 minutes
    cost_spike_threshold_tokens_per_min: int = 200_000
    overnight_start_hour: int | None = 22
    overnight_end_hour: int | None = 6
    preferred_mode: SleepMode = SleepMode.LIGHT


@dataclass(frozen=True)
class WakePolicy:
    """Policy that decides *when* to wake.

    Attributes:
        scheduled_resume_hour: Hour (0-23, UTC) for scheduled daily wake-up.
            Set to None to disable.
        urgent_message_priority: Minimum priority level that triggers
            an urgent wake (0-10). 0 = any message wakes.
        allow_manual_override: Whether ``WakeTrigger.MANUAL_OVERRIDE``
            is honoured.
        budget_reset_check_interval: Seconds between budget refresh checks.
    """

    scheduled_resume_hour: int | None = 6
    urgent_message_priority: int = 8
    allow_manual_override: bool = True
    budget_reset_check_interval: int = 300  # 5 minutes


@dataclass
class SleepState:
    """Current sleep/wake state of an agent.

    Attributes:
        is_asleep: Whether the agent is currently asleep.
        current_mode: The active sleep mode (None if awake).
        sleep_reason: Why the agent went to sleep (None if awake).
        sleep_start_time: Timestamp when sleep began.
        wake_scheduled_at: Timestamp when wake is scheduled.
        checkpointer: Optional callable that persists state before sleep.
    """

    is_asleep: bool = False
    current_mode: SleepMode | None = None
    sleep_reason: SleepReason | None = None
    sleep_start_time: float = 0.0
    wake_scheduled_at: float = 0.0
    checkpointer: Callable[[], None] | None = None


# ---------------------------------------------------------------------------
# DreamPhase — consolidation during light sleep
# ---------------------------------------------------------------------------


@dataclass
class DreamPhase:
    """Memory consolidation and reflection, run during light sleep.

    The DreamPhase cycles through three stages:

    1. **Reflect** — review recent outcomes and produce a brief summary.
    2. **Bind** — associate new patterns with existing memory entries.
    3. **Prune** — discard stale or low-utility ephemeral state.

    Each stage is a no-op callback by default; subclasses or callers can
    attach concrete implementations via the ``on_reflect``, ``on_bind``,
    and ``on_prune`` hooks.

    Attributes:
        cycle_seconds: How often the dream cycle runs.
        reflection_count: How many reflection cycles have completed.
        on_reflect: Optional async callback (mode, report).
        on_bind: Optional async callback (mode, associations).
        on_prune: Optional async callback (mode, pruned_count).
    """

    cycle_seconds: float = 60.0

    reflection_count: int = 0

    on_reflect: Callable[[SleepMode, str], Any] | None = None
    on_bind: Callable[[SleepMode, dict[str, Any]], Any] | None = None
    on_prune: Callable[[SleepMode, int], Any] | None = None

    async def run_once(self, mode: SleepMode) -> dict[str, Any]:
        """Execute a single dream cycle (reflect -> bind -> prune).

        Args:
            mode: The active sleep mode (only meaningful for LIGHT).

        Returns:
            A dict with keys ``reflection``, ``bindings``, ``pruned``.
        """
        logger.debug("DreamPhase: starting cycle %d", self.reflection_count)

        # 1. Reflect
        reflection = ""
        if self.on_reflect:
            try:
                result = self.on_reflect(mode, self._build_report())
                if asyncio.iscoroutine(result):
                    reflection = await result
                else:
                    reflection = result
            except Exception:
                logger.exception("DreamPhase reflect callback failed")

        # 2. Bind
        bindings: dict[str, Any] = {}
        if self.on_bind:
            try:
                result = self.on_bind(mode, {"reflection": reflection})
                if asyncio.iscoroutine(result):
                    bindings = await result
                else:
                    bindings = result
            except Exception:
                logger.exception("DreamPhase bind callback failed")

        # 3. Prune
        pruned = 0
        if self.on_prune:
            try:
                result = self.on_prune(mode, self.reflection_count)
                if asyncio.iscoroutine(result):
                    pruned = await result
                else:
                    pruned = result
            except Exception:
                logger.exception("DreamPhase prune callback failed")

        self.reflection_count += 1

        return {
            "reflection": reflection,
            "bindings": bindings,
            "pruned": pruned,
        }

    async def run_loop(self, mode: SleepMode, stop_event: asyncio.Event) -> None:
        """Run dream cycles in a loop until *stop_event* is set.

        Args:
            mode: Sleep mode to pass to each cycle.
            stop_event: When set, the loop exits after the current cycle.
        """
        logger.info("DreamPhase loop started (mode=%s, interval=%ss)", mode.value, self.cycle_seconds)
        while not stop_event.is_set():
            await self.run_once(mode)
            try:
                await asyncio.wait_for(
                    asyncio.get_event_loop().create_future() if False else asyncio.sleep(self.cycle_seconds),
                    timeout=self.cycle_seconds,
                )
            except asyncio.TimeoutError:
                continue
            # Simpler approach: just sleep
            await asyncio.sleep(self.cycle_seconds)

    @staticmethod
    def _build_report() -> str:
        """Build a minimal report string for the reflection callback."""
        return f"dream_cycle_at_{time.time():.0f}"


# ---------------------------------------------------------------------------
# SleepWakeScheduler
# ---------------------------------------------------------------------------


class SleepWakeScheduler:
    """Manages the sleep/wake lifecycle of an autonomous agent.

    Usage::

        scheduler = SleepWakeScheduler(
            sleep_policy=SleepPolicy(idle_threshold_seconds=300),
            wake_policy=WakePolicy(scheduled_resume_hour=6),
        )
        scheduler.dream_phase.on_reflect = my_reflect_callback

        await scheduler.evaluate_sleep()       # called periodically
        await scheduler.wake(WakeReason.MANUAL_OVERRIDE)
    """

    def __init__(
        self,
        sleep_policy: SleepPolicy | None = None,
        wake_policy: WakePolicy | None = None,
        dream: DreamPhase | None = None,
        mode: SleepMode = SleepMode.LIGHT,
    ) -> None:
        self.sleep_policy = sleep_policy or SleepPolicy()
        self.wake_policy = wake_policy or WakePolicy()
        self._dream = dream or DreamPhase()
        self._state = SleepState()
        self._mode = mode

        # External hooks
        self.on_sleep: Callable[[SleepMode, SleepReason], Any] | None = None
        self.on_wake: Callable[[WakeReason], Any] | None = None
        self.on_checkpoint: Callable[[], Any] | None = None

        self._wake_triggers: dict[WakeTrigger, bool] = {
            trigger: False for trigger in WakeTrigger
        }
        self._dream_stop_event: asyncio.Event | None = None

    # ── Properties ────────────────────────────────────────────────────

    @property
    def is_asleep(self) -> bool:
        """Whether the agent is currently asleep."""
        return self._state.is_asleep

    @property
    def state(self) -> SleepState:
        """Return a snapshot of the current sleep state."""
        return SleepState(
            is_asleep=self._state.is_asleep,
            current_mode=self._state.current_mode,
            sleep_reason=self._state.sleep_reason,
            sleep_start_time=self._state.sleep_start_time,
            wake_scheduled_at=self._state.wake_scheduled_at,
            checkpointer=self._state.checkpointer,
        )

    @property
    def dream_phase(self) -> DreamPhase:
        return self._dream

    @property
    def mode(self) -> SleepMode:
        return self._mode

    @mode.setter
    def mode(self, value: SleepMode) -> None:
        self._mode = value

    # ── Trigger management ────────────────────────────────────────────

    def trigger_wake(self, trigger: WakeTrigger) -> None:
        """Mark a wake trigger as active.

        Args:
            trigger: The trigger that fired.
        """
        self._wake_triggers[trigger] = True
        logger.debug("Wake trigger set: %s", trigger.value)

    def clear_wake_trigger(self, trigger: WakeTrigger) -> None:
        """Clear a previously set wake trigger.

        Args:
            trigger: The trigger to clear.
        """
        self._wake_triggers[trigger] = False

    def clear_all_wake_triggers(self) -> None:
        """Clear all wake triggers."""
        for trigger in WakeTrigger:
            self._wake_triggers[trigger] = False

    # ── Sleep evaluation ──────────────────────────────────────────────

    async def evaluate_sleep(
        self,
        idle_seconds: float = 0.0,
        token_burn_rate: float = 0.0,
        current_hour_utc: int | None = None,
    ) -> bool:
        """Evaluate whether the agent should sleep and, if so, enter sleep.

        Checks are ordered by priority: manual override, overnight, cost
        spike, idle timeout.

        Args:
            idle_seconds: Seconds since last activity.
            token_burn_rate: Current token burn rate (per minute).
            current_hour_utc: Current hour in UTC (auto-detected if None).

        Returns:
            True if the agent went to sleep.
        """
        if self._state.is_asleep:
            return True

        if current_hour_utc is None:
            current_hour_utc = time.gmtime().tm_hour

        # 1. Overnight sleep
        if self._is_overnight(current_hour_utc):
            return await self._enter_sleep(
                mode=self.sleep_policy.preferred_mode,
                reason=SleepReason.OVERNIGHT,
            )

        # 2. Cost spike
        spike = self.sleep_policy.cost_spike_threshold_tokens_per_min
        if spike > 0 and token_burn_rate > spike:
            return await self._enter_sleep(
                mode=SleepMode.DEEP,
                reason=SleepReason.COST_SPIKE,
            )

        # 3. Idle timeout
        if idle_seconds >= self.sleep_policy.idle_threshold_seconds:
            return await self._enter_sleep(
                mode=self.sleep_policy.preferred_mode,
                reason=SleepReason.IDLE_TIMEOUT,
            )

        return False

    def evaluate_sleep_sync(
        self,
        idle_seconds: float = 0.0,
        token_burn_rate: float = 0.0,
        current_hour_utc: int | None = None,
    ) -> bool:
        """Synchronous version of :meth:`evaluate_sleep`.

        Exists for callers that cannot use ``async``.

        Returns:
            True if the agent should sleep (caller must then invoke
            :meth:`sleep` manually).
        """
        if self._state.is_asleep:
            return True

        if current_hour_utc is None:
            current_hour_utc = time.gmtime().tm_hour

        if self._is_overnight(current_hour_utc):
            return True

        spike = self.sleep_policy.cost_spike_threshold_tokens_per_min
        if spike > 0 and token_burn_rate > spike:
            return True

        if idle_seconds >= self.sleep_policy.idle_threshold_seconds:
            return True

        return False

    # ── Sleep / wake actions ──────────────────────────────────────────

    async def sleep(
        self,
        mode: SleepMode | None = None,
        reason: SleepReason = SleepReason.MANUAL,
    ) -> None:
        """Put the agent to sleep.

        Args:
            mode: Sleep mode (uses the policy default if None).
            reason: Why the agent is sleeping.
        """
        if self._state.is_asleep:
            logger.debug("Already asleep, ignoring sleep() call.")
            return
        await self._enter_sleep(
            mode or self.sleep_policy.preferred_mode,
            reason,
        )

    async def wake(
        self,
        reason: WakeReason = WakeReason.MANUAL_OVERRIDE,
    ) -> None:
        """Wake the agent from sleep.

        Args:
            reason: Why the agent is waking.
        """
        if not self._state.is_asleep:
            logger.debug("Already awake, ignoring wake() call.")
            return
        await self._exit_sleep(reason)

    # ── Wake trigger check (called periodically) ─────────────────────

    async def check_wake_triggers(self) -> bool:
        """Check if any wake trigger is active and, if so, wake the agent.

        Returns:
            True if the agent was woken.
        """
        if not self._state.is_asleep:
            return False

        for trigger, active in self._wake_triggers.items():
            if not active:
                continue

            # Check policy constraints
            if trigger == WakeTrigger.MANUAL_OVERRIDE:
                if not self.wake_policy.allow_manual_override:
                    continue
                return await self._exit_sleep(WakeReason.MANUAL_OVERRIDE)

            if trigger == WakeTrigger.SCHEDULED_TIME:
                if self._state.wake_scheduled_at > 0 and time.time() >= self._state.wake_scheduled_at:
                    return await self._exit_sleep(WakeReason.SCHEDULED_RESUME)

            if trigger == WakeTrigger.NEW_MESSAGE:
                return await self._exit_sleep(WakeReason.URGENT_MESSAGE)

            if trigger == WakeTrigger.BUDGET_THRESHOLD:
                return await self._exit_sleep(WakeReason.BUDGET_RESET)

            if trigger == WakeTrigger.ERROR_THRESHOLD:
                return await self._exit_sleep(WakeReason.ERROR_RECOVERED)

        return False

    # ── Statistics ────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return sleep/wake statistics."""
        return {
            "is_asleep": self._state.is_asleep,
            "current_mode": self._state.current_mode.value if self._state.current_mode else None,
            "sleep_reason": self._state.sleep_reason.value if self._state.sleep_reason else None,
            "sleep_duration_seconds": (
                time.time() - self._state.sleep_start_time if self._state.is_asleep else 0.0
            ),
            "wake_scheduled_at": self._state.wake_scheduled_at,
            "dream_cycles_completed": self._dream.reflection_count,
            "active_triggers": [
                t.value for t, active in self._wake_triggers.items() if active
            ],
        }

    # ── Internal helpers ──────────────────────────────────────────────

    async def _enter_sleep(self, mode: SleepMode, reason: SleepReason) -> bool:
        """Internal: transition to sleep."""
        logger.info(
            "Entering sleep: mode=%s reason=%s", mode.value, reason.value
        )

        self._state.is_asleep = True
        self._state.current_mode = mode
        self._state.sleep_reason = reason
        self._state.sleep_start_time = time.time()

        # Schedule a wake time for daily resume
        if self.wake_policy.scheduled_resume_hour is not None:
            self._state.wake_scheduled_at = self._compute_wake_time()
            self.trigger_wake(WakeTrigger.SCHEDULED_TIME)

        # Checkpoint if a checkpointer is registered
        if reason in (SleepReason.OVERNIGHT, SleepReason.MANUAL) and self.on_checkpoint:
            try:
                result = self.on_checkpoint()
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("Checkpoint callback failed during sleep entry")

        # Run on_sleep hook
        if self.on_sleep:
            try:
                result = self.on_sleep(mode, reason)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("on_sleep hook failed")

        # Start dream phase if light sleep
        if mode == SleepMode.LIGHT:
            self._dream_stop_event = asyncio.Event()
            asyncio.create_task(self._dream.run_loop(mode, self._dream_stop_event))

        return True

    async def _exit_sleep(self, reason: WakeReason) -> bool:
        """Internal: transition to wake."""
        logger.info(
            "Exiting sleep: reason=%s (was %s)",
            reason.value,
            self._state.current_mode.value if self._state.current_mode else "unknown",
        )

        old_mode = self._state.current_mode

        # Stop dream phase if running
        if old_mode == SleepMode.LIGHT and self._dream_stop_event is not None:
            self._dream_stop_event.set()
            self._dream_stop_event = None

        self._state.is_asleep = False
        self._state.current_mode = None
        self._state.sleep_reason = None
        self._state.sleep_start_time = 0.0
        self._state.wake_scheduled_at = 0.0
        self.clear_all_wake_triggers()

        # Run on_wake hook
        if self.on_wake:
            try:
                result = self.on_wake(reason)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("on_wake hook failed")

        return True

    def _is_overnight(self, current_hour: int) -> bool:
        """Check whether *current_hour* falls in the overnight window."""
        start = self.sleep_policy.overnight_start_hour
        end = self.sleep_policy.overnight_end_hour
        if start is None or end is None:
            return False
        if start > end:
            # Wraps past midnight, e.g. 22:00 - 06:00
            return current_hour >= start or current_hour < end
        return start <= current_hour < end

    def _compute_wake_time(self) -> float:
        """Return the next wake timestamp based on the scheduled resume hour."""
        now = time.time()
        now_utc = time.gmtime(now)
        resume_hour = self.wake_policy.scheduled_resume_hour

        if resume_hour is None:
            return 0.0

        # Build a struct_time for today at the resume hour
        from datetime import datetime, timezone

        today = datetime.now(tz=timezone.utc).replace(
            hour=resume_hour, minute=0, second=0, microsecond=0
        )

        # If today's resume hour has already passed, schedule for tomorrow
        if today.timestamp() < now:
            today = today.replace(day=today.day + 1)

        return today.timestamp()
