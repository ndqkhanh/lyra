"""
Fleet Orchestrator — multi-agent session lifecycle, GPU allocation, and stagnation detection.

Extends SupervisorDaemon with:
- Concurrent agent spawning via worktree-isolated sessions
- Fleet-level status aggregation (state, cost, progress)
- GPU allocation to the most promising sessions
- MLEvolve-inspired multi-level stagnation detection
- Graceful per-session kill with checkpoint recovery
- Lightweight event bus for WebSocket IPC
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import structlog

from lyra.supervisor.daemon import SupervisorDaemon
from lyra.supervisor.state import ProcessState, SessionInfo, SessionState

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Enums & Config
# ---------------------------------------------------------------------------


class GpuAllocationPolicy(str, Enum):
    """Strategy for GPU allocation across fleet sessions."""

    ROUND_ROBIN = "round_robin"
    MOST_PROMISING = "most_promising"
    STAGNATION_PRIORITY = "stagnation_priority"


class FleetEventType(str, Enum):
    """Event types published on the fleet event bus."""

    SESSION_SPAWNED = "session_spawned"
    SESSION_STOPPED = "session_stopped"
    SESSION_STAGNATED = "session_stagnated"
    SESSION_RECOVERED = "session_recovered"
    GPU_ALLOCATED = "gpu_allocated"
    GPU_DEALLOCATED = "gpu_deallocated"
    FLEET_STATUS_CHANGE = "fleet_status_change"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FleetConfig:
    """Configuration for the fleet orchestrator.

    Attributes:
        max_concurrent: Maximum allowed concurrent agent sessions.
        gpu_allocation_policy: Strategy to use when allocating GPUs.
        stagnation_threshold_seconds: Seconds of inactivity before a session
            is considered stagnant (Level 1).
        stagnation_velocity_window: Number of recent progress samples to
            consider for velocity-based stagnation (Level 2).
        stagnation_improvement_ratio: Minimum ratio of checkpoints showing
            forward progress; below this triggers Level 3 stagnation.
        checkpoint_stale_minutes: Passed to CheckpointManager.
    """

    max_concurrent: int = 10
    gpu_allocation_policy: GpuAllocationPolicy = GpuAllocationPolicy.MOST_PROMISING
    stagnation_threshold_seconds: int = 300
    stagnation_velocity_window: int = 5
    stagnation_improvement_ratio: float = 0.3
    checkpoint_stale_minutes: int = 5


@dataclass(frozen=True)
class AgentConfig:
    """Configuration for spawning a new agent session.

    Attributes:
        name: Human-readable agent name.
        working_dir: Absolute path to the worktree directory.
        capabilities: List of capability tags (e.g. "research", "reasoning").
        model: Preferred model identifier.
        gpu_required: Whether this agent requires a GPU.
        initial_state: Optional initial state dict for the session.
    """

    name: str
    working_dir: str
    capabilities: list[str] = field(default_factory=list)
    model: str = "sonnet"
    gpu_required: bool = False
    initial_state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SessionProgress:
    """Snapshot of a session's progress metrics.

    Attributes:
        session_id: The session identifier.
        checkpoint_count: Total checkpoints saved.
        last_checkpoint_at: Timestamp of the most recent checkpoint.
        stagnation_level: 0 = healthy, 1 = idle-stagnant,
            2 = velocity-stagnant, 3 = improvement-stagnant.
        gpu_allocated: Whether a GPU is currently assigned.
        cost_estimate: Estimated cumulative cost (arbitrary units).
    """

    session_id: str
    checkpoint_count: int = 0
    last_checkpoint_at: datetime.datetime | None = None
    stagnation_level: int = 0
    gpu_allocated: bool = False
    cost_estimate: float = 0.0


@dataclass(frozen=True)
class FleetStatus:
    """Snapshot of the entire fleet at a point in time.

    Attributes:
        total_sessions: Number of tracked sessions.
        active_count: Number of WORKING or IDLE sessions.
        stagnant_count: Number of sessions at any stagnation level > 0.
        gpu_allocated_count: Number of sessions with GPU allocation.
        sessions: Per-session progress details.
        timestamp: When this snapshot was taken.
    """

    total_sessions: int
    active_count: int
    stagnant_count: int
    gpu_allocated_count: int
    sessions: tuple[SessionProgress, ...]
    timestamp: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc)
    )


@dataclass(frozen=True)
class FleetEvent:
    """An event published on the fleet event bus.

    Attributes:
        event_type: Category of the event.
        session_id: Session the event relates to (may be empty).
        payload: Arbitrary event data.
        timestamp: When the event was created.
    """

    event_type: FleetEventType
    session_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(tz=datetime.timezone.utc)
    )


# ---------------------------------------------------------------------------
# FleetOrchestrator
# ---------------------------------------------------------------------------


class FleetOrchestrator(SupervisorDaemon):
    """Multi-agent fleet orchestrator extending SupervisorDaemon.

    Manages concurrent agent sessions with worktree isolation, GPU
    allocation, stagnation detection, and event-driven IPC.

    Usage::

        fleet = FleetOrchestrator(db_path="/tmp/fleet.db")
        sid = fleet.spawn_agent(AgentConfig(
            name="researcher-1",
            working_dir="/tmp/worktrees/agent-1",
            capabilities=["research"],
        ))
        status = fleet.fleet_status()
        stalled = fleet.detect_stagnation(sid)
        fleet.kill_session(sid)
    """

    def __init__(
        self,
        db_path: str | Path = "fleet.db",
        idle_timeout_minutes: int = 60,
        config: FleetConfig | None = None,
        checkpoint_manager: Any | None = None,
    ) -> None:
        """
        Args:
            db_path: Path to the SQLite database for session persistence.
            idle_timeout_minutes: Idle timeout forwarded to SupervisorDaemon.
            config: Fleet configuration. Uses defaults if not provided.
            checkpoint_manager: Optional CheckpointManager instance for
                crash recovery integration (Phase 0).
        """
        super().__init__(db_path=db_path, idle_timeout_minutes=idle_timeout_minutes)
        self._config = config or FleetConfig()
        self._checkpoint_manager = checkpoint_manager

        # Extended per-session metadata not in SessionInfo
        self._agent_configs: dict[str, AgentConfig] = {}
        self._gpu_assignments: dict[str, str] = {}  # session_id -> gpu_id
        self._gpu_pool: dict[str, str | None] = {}  # gpu_id -> session_id or None
        self._stagnation_levels: dict[str, int] = {}
        self._progress_history: dict[str, list[float]] = {}  # session_id -> progress scores
        self._cost_tracker: dict[str, float] = {}  # session_id -> estimated cost

        # Lock for thread safety
        self._fleet_lock = threading.Lock()

        # Event bus: list of subscriber callbacks (for WebSocket IPC)
        self._event_subscribers: list[Callable[[FleetEvent], None]] = []

        # Recover interrupted sessions if checkpoint_manager is available
        if self._checkpoint_manager is not None:
            self._recover_interrupted_sessions()

    # ------------------------------------------------------------------
    # Event bus
    # ------------------------------------------------------------------

    def subscribe(self, callback: Callable[[FleetEvent], None]) -> None:
        """Register a callback for fleet events.

        The callback will be invoked for every FleetEvent published.
        This is the integration point for WebSocket broadcast.
        """
        self._event_subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[FleetEvent], None]) -> None:
        """Remove a previously registered event callback."""
        if callback in self._event_subscribers:
            self._event_subscribers.remove(callback)

    def _publish(self, event: FleetEvent) -> None:
        """Dispatch a FleetEvent to all registered subscribers."""
        for cb in self._event_subscribers:
            try:
                cb(event)
            except Exception:
                logger.exception("fleet_event_callback_failed", event_type=event.event_type.value)

    # ------------------------------------------------------------------
    # Fleet lifecycle
    # ------------------------------------------------------------------

    def spawn_agent(self, agent_config: AgentConfig) -> str:
        """Spawn a new worktree-isolated agent session.

        Validates the fleet is not at capacity, creates the session via
        the supervisor daemon, and registers agent metadata.

        Args:
            agent_config: Configuration for the agent to spawn.

        Returns:
            The new session ID.

        Raises:
            RuntimeError: If the fleet is at maximum concurrent capacity.
        """
        # Check capacity
        with self._fleet_lock:
            active = sum(
                1 for info in self._sessions.values()
                if info.state in (SessionState.WORKING, SessionState.IDLE)
            )
            if active >= self._config.max_concurrent:
                raise RuntimeError(
                    f"Fleet at capacity ({active}/{self._config.max_concurrent}). "
                    "Cannot spawn new agent."
                )

        session_id = self.start_session(agent_config.name, agent_config.working_dir)
        self._agent_configs[session_id] = agent_config
        self._stagnation_levels[session_id] = 0
        self._progress_history[session_id] = []
        self._cost_tracker[session_id] = 0.0

        # Save initial checkpoint if checkpoint manager is available
        if self._checkpoint_manager is not None:
            state: dict[str, Any] = {
                "session_id": session_id,
                "name": agent_config.name,
                "working_dir": agent_config.working_dir,
                "capabilities": agent_config.capabilities,
                "model": agent_config.model,
                "initial_state": agent_config.initial_state,
                "progress_score": 0.0,
            }
            self._checkpoint_manager.save_checkpoint(session_id, state)

        self._publish(FleetEvent(
            event_type=FleetEventType.SESSION_SPAWNED,
            session_id=session_id,
            payload={"name": agent_config.name},
        ))

        logger.info("agent_spawned", session_id=session_id, name=agent_config.name)
        return session_id

    def kill_session(self, session_id: str) -> None:
        """Gracefully stop and clean up a session.

        Deallocates any GPU, flushes a final checkpoint, and marks the
        session as STOPPED.

        Args:
            session_id: The session to kill.
        """
        with self._fleet_lock:
            # Deallocate GPU if assigned
            if session_id in self._gpu_assignments:
                gpu_id = self._gpu_assignments.pop(session_id)
                self._gpu_pool[gpu_id] = None
                self._publish(FleetEvent(
                    event_type=FleetEventType.GPU_DEALLOCATED,
                    session_id=session_id,
                    payload={"gpu_id": gpu_id},
                ))

            # Save final checkpoint
            if self._checkpoint_manager is not None:
                state = self._build_stagnation_state(session_id)
                state["stopped_at"] = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
                self._checkpoint_manager.save_checkpoint(session_id, state)

            # Clean up tracked metadata
            self._agent_configs.pop(session_id, None)
            self._stagnation_levels.pop(session_id, None)
            self._progress_history.pop(session_id, None)
            self._cost_tracker.pop(session_id, None)

        # Stop via parent class (thread-safe)
        self.stop_session(session_id)

        self._publish(FleetEvent(
            event_type=FleetEventType.SESSION_STOPPED,
            session_id=session_id,
        ))

        logger.info("session_killed", session_id=session_id)

    # ------------------------------------------------------------------
    # Fleet status
    # ------------------------------------------------------------------

    def fleet_status(self) -> FleetStatus:
        """Return a snapshot of the entire fleet.

        Gathers state, stagnation levels, GPU allocation, and cost
        estimates for every tracked session.

        Returns:
            FleetStatus with per-session progress details.
        """
        sessions_progress: list[SessionProgress] = []

        with self._fleet_lock:
            for sid, info in list(self._sessions.items()):
                last_ckpt: datetime.datetime | None = None
                ckpt_count = 0
                if self._checkpoint_manager is not None:
                    checkpoints = self._checkpoint_manager.list_checkpoints(sid)
                    ckpt_count = len(checkpoints)
                    if checkpoints:
                        last_ckpt = checkpoints[-1].created_at

                progress = SessionProgress(
                    session_id=sid,
                    checkpoint_count=ckpt_count,
                    last_checkpoint_at=last_ckpt,
                    stagnation_level=self._stagnation_levels.get(sid, 0),
                    gpu_allocated=sid in self._gpu_assignments,
                    cost_estimate=self._cost_tracker.get(sid, 0.0),
                )
                sessions_progress.append(progress)

        active_count = sum(
            1 for info in self._sessions.values()
            if info.state in (SessionState.WORKING, SessionState.IDLE)
        )
        stagnant_count = sum(
            1 for level in self._stagnation_levels.values() if level > 0
        )
        gpu_allocated_count = len(self._gpu_assignments)

        return FleetStatus(
            total_sessions=len(self._sessions),
            active_count=active_count,
            stagnant_count=stagnant_count,
            gpu_allocated_count=gpu_allocated_count,
            sessions=tuple(sessions_progress),
        )

    # ------------------------------------------------------------------
    # GPU allocation
    # ------------------------------------------------------------------

    def register_gpus(self, gpu_ids: list[str]) -> None:
        """Register available GPU resources with the fleet.

        Args:
            gpu_ids: List of GPU identifiers (e.g. ["cuda:0", "cuda:1"]).
        """
        with self._fleet_lock:
            for gid in gpu_ids:
                if gid not in self._gpu_pool:
                    self._gpu_pool[gid] = None

    def allocate_gpus(self, n_gpus: int) -> list[str]:
        """Allocate GPU resources to the most promising sessions.

        Uses the configured allocation policy to select sessions that
        should receive a GPU. Only sessions in WORKING or IDLE state
        are eligible.

        Args:
            n_gpus: Number of GPUs to allocate.

        Returns:
            List of session IDs that received a GPU allocation.

        Raises:
            RuntimeError: If fewer GPUs are available than requested.
        """
        available = [gid for gid, sid in self._gpu_pool.items() if sid is None]
        if len(available) < n_gpus:
            raise RuntimeError(
                f"Insufficient GPUs: requested {n_gpus}, available {len(available)}"
            )

        policy = self._config.gpu_allocation_policy
        eligible = [
            sid for sid, info in self._sessions.items()
            if info.state in (SessionState.WORKING, SessionState.IDLE)
            and sid not in self._gpu_assignments
        ]

        if not eligible:
            return []

        # Rank eligible sessions by policy
        if policy == GpuAllocationPolicy.ROUND_ROBIN:
            ranked = sorted(eligible)  # deterministic order
        elif policy == GpuAllocationPolicy.STAGNATION_PRIORITY:
            # Sessions with higher stagnation levels get priority
            ranked = sorted(
                eligible,
                key=lambda sid: self._stagnation_levels.get(sid, 0),
                reverse=True,
            )
        else:  # MOST_PROMISING (default)
            # Sessions with most checkpoints (progress) get priority
            ranked = sorted(
                eligible,
                key=lambda sid: len(self._progress_history.get(sid, [])),
                reverse=True,
            )

        allocated: list[str] = []
        with self._fleet_lock:
            for i, session_id in enumerate(ranked[:n_gpus]):
                gpu_id = available[i]
                self._gpu_assignments[session_id] = gpu_id
                self._gpu_pool[gpu_id] = session_id
                allocated.append(session_id)

                self._publish(FleetEvent(
                    event_type=FleetEventType.GPU_ALLOCATED,
                    session_id=session_id,
                    payload={"gpu_id": gpu_id},
                ))

        logger.info(
            "gpus_allocated",
            count=len(allocated),
            policy=policy.value,
            sessions=allocated,
        )
        return allocated

    def deallocate_gpu(self, session_id: str) -> str | None:
        """Deallocate a GPU from a session, returning the GPU ID or None.

        Args:
            session_id: The session to deallocate from.

        Returns:
            The freed GPU ID, or None if nothing was allocated.
        """
        with self._fleet_lock:
            gpu_id = self._gpu_assignments.pop(session_id, None)
            if gpu_id is not None:
                self._gpu_pool[gpu_id] = None
                self._publish(FleetEvent(
                    event_type=FleetEventType.GPU_DEALLOCATED,
                    session_id=session_id,
                    payload={"gpu_id": gpu_id},
                ))
        return gpu_id

    # ------------------------------------------------------------------
    # Stagnation detection (MLEvolve-inspired)
    # ------------------------------------------------------------------

    def record_progress(self, session_id: str, progress_score: float) -> None:
        """Record a progress data point for stagnation analysis.

        Args:
            session_id: The session identifier.
            progress_score: A float indicating progress (higher = better).
        """
        with self._fleet_lock:
            if session_id not in self._progress_history:
                self._progress_history[session_id] = []
            self._progress_history[session_id].append(progress_score)
            # Keep only the window we need
            window = self._config.stagnation_velocity_window
            if len(self._progress_history[session_id]) > window * 2:
                self._progress_history[session_id] = (
                    self._progress_history[session_id][-window:]
                )

    def _record_cost(self, session_id: str, delta: float) -> None:
        """Add to the cost estimate for a session."""
        with self._fleet_lock:
            current = self._cost_tracker.get(session_id, 0.0)
            self._cost_tracker[session_id] = current + delta

    def detect_stagnation(self, session_id: str) -> bool:
        """Multi-level stagnation detection for a single session.

        Three levels (inspired by MLEvolve):
          Level 1 (idle): Session has been inactive past threshold.
          Level 2 (velocity): Progress rate has dropped to near zero
              over the recent window.
          Level 3 (improvement): Ratio of improving checkpoints is
              below the configured threshold.

        The highest detected level is set on the session. Returns True
        if any level above 0 was detected.

        Args:
            session_id: The session to check.

        Returns:
            True if the session is stagnant at any level > 0.
        """
        info = self.get_session_info(session_id)
        if info is None:
            return False

        now = datetime.datetime.now(tz=datetime.timezone.utc)
        detected_level = 0

        # Level 1: idle stagnation
        idle_duration = (now - info.last_active).total_seconds()
        if idle_duration >= self._config.stagnation_threshold_seconds:
            detected_level = 1

        # Level 2: velocity stagnation — check recent progress
        history = self._progress_history.get(session_id, [])
        if detected_level < 2 and len(history) >= 2:
            recent = history[-self._config.stagnation_velocity_window:]
            if len(recent) >= 2:
                deltas = [
                    recent[i + 1] - recent[i]
                    for i in range(len(recent) - 1)
                ]
                avg_velocity = sum(deltas) / len(deltas) if deltas else 0.0
                if avg_velocity <= 0.0:
                    detected_level = 2

        # Level 3: improvement stagnation
        if detected_level < 3 and len(history) >= 3:
            improvements = sum(
                1 for i in range(len(history) - 1)
                if history[i + 1] > history[i]
            )
            ratio = improvements / (len(history) - 1) if len(history) > 1 else 1.0
            if ratio < self._config.stagnation_improvement_ratio:
                detected_level = 3

        with self._fleet_lock:
            old_level = self._stagnation_levels.get(session_id, 0)
            self._stagnation_levels[session_id] = detected_level

        if detected_level > 0 and detected_level != old_level:
            self._publish(FleetEvent(
                event_type=FleetEventType.SESSION_STAGNATED,
                session_id=session_id,
                payload={
                    "level": detected_level,
                    "idle_seconds": round(idle_duration, 1),
                },
            ))
            logger.warning(
                "session_stagnated",
                session_id=session_id,
                level=detected_level,
                idle_seconds=round(idle_duration, 1),
            )

        return detected_level > 0

    def detect_all_stagnation(self) -> list[str]:
        """Run stagnation detection across all active sessions.

        Returns:
            List of session IDs that are newly stagnant.
        """
        stagnant: list[str] = []
        for sid in list(self._sessions.keys()):
            if self.detect_stagnation(sid):
                stagnant.append(sid)
        return stagnant

    # ------------------------------------------------------------------
    # Crash recovery
    # ------------------------------------------------------------------

    def _recover_interrupted_sessions(self) -> None:
        """Recover sessions that were interrupted before shutdown.

        Uses the CheckpointManager to detect and restore interrupted
        sessions, marking them as STOPPED so the fleet can restart
        cleanly.
        """
        if self._checkpoint_manager is None:
            return

        try:
            interrupted = self._checkpoint_manager.detect_interrupted()
            for session_id in interrupted:
                state = self._checkpoint_manager.recover(session_id)
                if state is not None:
                    # Re-register the session in our in-memory state
                    name = state.get("name", session_id)
                    working_dir = state.get("working_dir", "/tmp")
                    self.start_session(name, working_dir)

                    config = AgentConfig(
                        name=name,
                        working_dir=working_dir,
                        capabilities=state.get("capabilities", []),
                        model=state.get("model", "sonnet"),
                        initial_state=state.get("initial_state", {}),
                    )
                    self._agent_configs[session_id] = config
                    self._stagnation_levels[session_id] = 0
                    self._progress_history[session_id] = []
                    self._cost_tracker[session_id] = state.get("cost_estimate", 0.0)

                    # Mark as STOPPED since we recovered from crash
                    self.stop_session(session_id)

                    self._publish(FleetEvent(
                        event_type=FleetEventType.SESSION_RECOVERED,
                        session_id=session_id,
                        payload={"name": name},
                    ))

                    logger.info(
                        "session_recovered_from_crash",
                        session_id=session_id,
                        name=name,
                    )
        except Exception:
            logger.exception("fleet_crash_recovery_failed")

    def _build_stagnation_state(self, session_id: str) -> dict[str, Any]:
        """Build a state dict for checkpoint purposes."""
        config = self._agent_configs.get(session_id)
        return {
            "session_id": session_id,
            "name": config.name if config else "unknown",
            "working_dir": config.working_dir if config else "/tmp",
            "capabilities": config.capabilities if config else [],
            "model": config.model if config else "sonnet",
            "stagnation_level": self._stagnation_levels.get(session_id, 0),
            "gpu_allocated": session_id in self._gpu_assignments,
            "cost_estimate": self._cost_tracker.get(session_id, 0.0),
            "progress_history": self._progress_history.get(session_id, []),
        }

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def config(self) -> FleetConfig:
        """Return the current fleet configuration."""
        return self._config

    @property
    def gpu_assignments(self) -> dict[str, str]:
        """Return a snapshot of current GPU assignments (session_id -> gpu_id)."""
        with self._fleet_lock:
            return dict(self._gpu_assignments)

    @property
    def gpu_pool(self) -> dict[str, str | None]:
        """Return a snapshot of the GPU pool (gpu_id -> session_id or None)."""
        with self._fleet_lock:
            return dict(self._gpu_pool)
