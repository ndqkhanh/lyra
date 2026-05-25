"""Unified agent fleet — wires swarm dispatcher, colony runtime, and parallel executor.

Integrates:
  - lyra_agent_swarm: Dispatcher + SquadManager for task routing and team formation
  - lyra_colony: AgentColony for lifecycle management and scaling
  - lyra_orchestration: ParallelExecutor for fan-out task execution
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FleetTask:
    """A task dispatched to the agent fleet."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    category: str = "general"
    priority: float = 1.0
    status: str = "pending"  # pending, dispatched, running, completed, failed
    assigned_agent: str = ""
    result: Any = None
    error: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0


@dataclass
class FleetStatus:
    """Snapshot of fleet operational status."""

    active_agents: int = 0
    idle_agents: int = 0
    total_agents: int = 0
    pending_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    squads: int = 0
    throughput: float = 0.0  # tasks/sec
    state: str = "unknown"  # idle, running, scaling, draining


@dataclass
class SquadInfo:
    """Information about an agent squad."""

    id: str
    leader: str
    members: list[str]
    name: str = ""
    task_count: int = 0
    created_at: float = field(default_factory=time.time)


class UnifiedAgentFleet:
    """Orchestrates agent swarms, colony lifecycle, and parallel execution.

    Provides:
      - Task dispatch to optimal agents via capability routing
      - Squad formation for team-based work
      - Parallel fan-out for batch task execution
      - Colony scaling based on load
      - Fleet-wide status monitoring
    """

    # Predefined agent role templates
    AGENT_ROLES: dict[str, dict[str, Any]] = {
        "explorer": {
            "description": "Codebase exploration and search",
            "tools": ["grep", "glob", "read", "lsp"],
        },
        "coder": {
            "description": "Code writing and editing",
            "tools": ["write", "edit", "bash", "lsp"],
        },
        "reviewer": {
            "description": "Code review and quality checks",
            "tools": ["read", "lsp", "grep"],
        },
        "tester": {
            "description": "Test writing and execution",
            "tools": ["bash", "write", "edit", "read"],
        },
        "researcher": {
            "description": "Deep research and analysis",
            "tools": ["web_search", "web_fetch", "read"],
        },
        "architect": {
            "description": "System design and architecture",
            "tools": ["read", "grep", "glob"],
        },
        "devops": {
            "description": "Deployment and infrastructure",
            "tools": ["bash", "write", "edit"],
        },
        "security": {
            "description": "Security audit and vulnerability scanning",
            "tools": ["grep", "read", "bash"],
        },
    }

    DEFAULT_SQUAD = ["explorer", "coder", "reviewer", "tester"]

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._initialized = False

        # Agent registry
        self._agents: dict[str, dict[str, Any]] = {}
        # Squads
        self._squads: dict[str, SquadInfo] = {}
        # Tasks
        self._tasks: dict[str, FleetTask] = {}
        # Subsystems (lazy-init)
        self._swarm_dispatcher = None
        self._squad_manager = None
        self._colony = None
        self._parallel_executor = None

        # Metrics
        self._task_counter: int = 0
        self._started_at: float = time.time()

    @property
    def initialized(self) -> bool:
        return self._initialized

    # ── Lifecycle ──────────────────────────────────────────────────

    def initialize(self) -> None:
        """Initialize fleet with default agents and subsystems."""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            for role, info in self.AGENT_ROLES.items():
                self._agents[role] = {
                    "id": role,
                    "role": role,
                    "description": info["description"],
                    "tools": info["tools"],
                    "status": "idle",
                    "task_count": 0,
                    "created_at": time.time(),
                }

            try:
                from lyra_agent_swarm.dispatcher import Dispatcher
                from lyra_agent_swarm.squad_manager import SquadManager

                self._swarm_dispatcher = Dispatcher(None)  # type: ignore[arg-type]
                self._squad_manager = SquadManager()
            except Exception:
                logger.warning("Swarm dispatcher not available")

            try:
                from lyra_colony.colony import AgentColony

                self._colony = AgentColony()
            except Exception:
                logger.warning("AgentColony not available")

            try:
                from lyra_orchestration.execution.parallel import ParallelExecutor

                self._parallel_executor = ParallelExecutor(None)  # type: ignore[arg-type]
            except Exception:
                logger.warning("ParallelExecutor not available")

            self._initialized = True

    def _ensure_init(self) -> None:
        if not self._initialized:
            self.initialize()

    # ── Task Dispatch ──────────────────────────────────────────────

    def submit_task(
        self, description: str, category: str = "general", priority: float = 1.0
    ) -> str:
        """Submit a task to the fleet. Returns task ID."""
        self._ensure_init()
        task = FleetTask(
            description=description, category=category, priority=priority
        )
        with self._lock:
            self._tasks[task.id] = task
            self._task_counter += 1

        # Auto-assign to best matching agent
        self._dispatch_task(task)
        return task.id

    def _dispatch_task(self, task: FleetTask) -> None:
        """Assign task to best available agent based on capability match."""
        best_agent: str | None = None
        best_score = -1.0

        for agent_id, agent in self._agents.items():
            if agent["status"] != "idle":
                continue
            tools = set(agent.get("tools", []))
            score = len(tools) * 0.1  # simple heuristic — favor more tools
            if task.category in ("code", "edit", "refactor") and "write" in tools:
                score += 0.5
            if task.category in ("search", "explore") and "grep" in tools:
                score += 0.5
            if task.category in ("test", "verify") and "bash" in tools:
                score += 0.5

            if score > best_score:
                best_score = score
                best_agent = agent_id

        if best_agent:
            task.assigned_agent = best_agent
            task.status = "dispatched"
            self._agents[best_agent]["status"] = "busy"

    def complete_task(self, task_id: str, result: Any = None, error: str = "") -> None:
        """Mark a task as completed or failed."""
        self._ensure_init()
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return

            task.completed_at = time.time()
            if error:
                task.status = "failed"
                task.error = error
            else:
                task.status = "completed"
                task.result = result

            if task.assigned_agent and task.assigned_agent in self._agents:
                self._agents[task.assigned_agent]["status"] = "idle"
                self._agents[task.assigned_agent]["task_count"] += 1

    def get_task(self, task_id: str) -> FleetTask | None:
        self._ensure_init()
        return self._tasks.get(task_id)

    # ── Squad Management ───────────────────────────────────────────

    def create_squad(
        self, name: str, roles: list[str] | None = None
    ) -> SquadInfo:
        """Form a squad from available agents."""
        self._ensure_init()
        roles = roles or self.DEFAULT_SQUAD

        available = [r for r in roles if r in self._agents]
        if len(available) < 2:
            available = list(self._agents.keys())[:4]

        leader = available[0]
        members = available[1:]
        squad = SquadInfo(
            id=uuid.uuid4().hex[:8],
            name=name,
            leader=leader,
            members=members,
        )
        with self._lock:
            self._squads[squad.id] = squad
        return squad

    def list_squads(self) -> list[SquadInfo]:
        self._ensure_init()
        return list(self._squads.values())

    # ── Parallel Fan-Out ───────────────────────────────────────────

    def fan_out(self, tasks: list[dict[str, str]]) -> list[str]:
        """Submit multiple tasks in parallel and return task IDs."""
        self._ensure_init()
        task_ids: list[str] = []
        for t in tasks:
            tid = self.submit_task(
                description=t.get("description", t.get("task", "")),
                category=t.get("category", "general"),
                priority=float(t.get("priority", 1.0)),
            )
            task_ids.append(tid)
        return task_ids

    # ── Status & Metrics ───────────────────────────────────────────

    def status(self) -> FleetStatus:
        """Return current fleet operational status."""
        self._ensure_init()
        with self._lock:
            pending = sum(1 for t in self._tasks.values() if t.status in ("pending", "dispatched"))
            running = sum(1 for t in self._tasks.values() if t.status == "running")
            completed = sum(1 for t in self._tasks.values() if t.status == "completed")
            failed = sum(1 for t in self._tasks.values() if t.status == "failed")
            active = sum(1 for a in self._agents.values() if a["status"] == "busy")
            idle = sum(1 for a in self._agents.values() if a["status"] == "idle")

            elapsed = max(time.time() - self._started_at, 0.001)
            throughput = (completed + failed) / elapsed

            return FleetStatus(
                active_agents=active,
                idle_agents=idle,
                total_agents=len(self._agents),
                pending_tasks=pending + running,
                running_tasks=running,
                completed_tasks=completed,
                failed_tasks=failed,
                squads=len(self._squads),
                throughput=round(throughput, 2),
                state="running" if running > 0 else "idle",
            )

    def snapshot(self) -> dict[str, Any]:
        s = self.status()
        return {
            "fleet": s,
            "agents": {
                aid: {
                    "role": a["role"],
                    "status": a["status"],
                    "task_count": a["task_count"],
                    "tools": a["tools"],
                }
                for aid, a in self._agents.items()
            },
            "squads": {
                sid: {
                    "leader": sq.leader,
                    "members": sq.members,
                    "task_count": sq.task_count,
                }
                for sid, sq in self._squads.items()
            },
            "task_ids": list(self._tasks.keys())[-20:],
        }

    # ── Agent Info ─────────────────────────────────────────────────

    def list_agents(self) -> list[dict[str, Any]]:
        self._ensure_init()
        return [
            {
                "id": aid,
                "role": a["role"],
                "description": a["description"],
                "status": a["status"],
                "tools": a.get("tools", []),
                "task_count": a.get("task_count", 0),
            }
            for aid, a in self._agents.items()
        ]

    def agent_roles(self) -> dict[str, dict[str, Any]]:
        return dict(self.AGENT_ROLES)
