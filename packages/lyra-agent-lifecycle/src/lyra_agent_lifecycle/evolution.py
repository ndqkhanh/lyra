"""Agent evolution tracking: performance history, capability metrics, breeding, and extinction."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    return uuid4().hex[:12]


def _now() -> float:
    return time.monotonic()


# ---------------------------------------------------------------------------
# Dataclass models
# ---------------------------------------------------------------------------


@dataclass
class CapabilityProfile:
    """Tracks an agent's capabilities and their evolution over time.

    Attributes:
        agent_id: Which agent.
        capabilities: Current capability tags.
        proficiency: Per-capability proficiency scores (0.0-1.0).
        first_seen: When each capability was first observed.
        evolution_count: How many times capabilities have changed.
    """

    agent_id: str
    capabilities: list[str] = field(default_factory=list)
    proficiency: dict[str, float] = field(default_factory=dict)
    first_seen: dict[str, float] = field(default_factory=dict)
    evolution_count: int = 0

    def add_capability(self, capability: str, proficiency: float = 0.5) -> None:
        """Add or update a capability."""
        if capability not in self.capabilities:
            self.capabilities.append(capability)
            self.first_seen[capability] = _now()
        self.proficiency[capability] = proficiency
        self.evolution_count += 1

    def remove_capability(self, capability: str) -> None:
        """Remove a capability."""
        if capability in self.capabilities:
            self.capabilities.remove(capability)
            self.proficiency.pop(capability, None)
            self.evolution_count += 1

    @property
    def avg_proficiency(self) -> float:
        if not self.proficiency:
            return 0.0
        return sum(self.proficiency.values()) / len(self.proficiency)

    @property
    def breadth(self) -> int:
        return len(self.capabilities)


@dataclass
class PerformanceSnapshot:
    """A point-in-time performance record for an agent.

    Attributes:
        snapshot_id: Unique snapshot identifier.
        agent_id: Which agent.
        task_count: Total tasks completed.
        success_rate: Fraction of tasks that succeeded.
        avg_latency_ms: Average task latency.
        avg_quality: Average quality score.
        capabilities: Snapshot of capabilities at this time.
        timestamp: When the snapshot was taken.
    """

    snapshot_id: str = field(default_factory=_new_id)
    agent_id: str = ""
    task_count: int = 0
    success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    avg_quality: float = 0.0
    capabilities: list[str] = field(default_factory=list)
    timestamp: float = field(default_factory=_now)


@dataclass
class Lineage:
    """Tracks the evolutionary lineage of an agent.

    Attributes:
        lineage_id: Unique lineage identifier.
        root_agent_id: The original ancestor.
        generations: Number of generations.
        members: All agent IDs in this lineage.
        parent_map: Child -> Parent mapping.
        fitness_history: Lineage-wide fitness over time.
    """

    lineage_id: str = field(default_factory=_new_id)
    root_agent_id: str = ""
    generations: int = 1
    members: list[str] = field(default_factory=list)
    parent_map: dict[str, str] = field(default_factory=dict)
    fitness_history: list[float] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Evolution Tracker
# ---------------------------------------------------------------------------


class EvolutionTracker:
    """Tracks agent evolution: performance, capability changes, breeding, and extinction.

    Provides:
    - Per-agent performance history with snapshots
    - Capability evolution metrics
    - Breeding/merging of successful agent patterns
    - Extinction of underperforming configurations
    - Lineage tracking across generations
    """

    def __init__(
        self,
        *,
        snapshot_interval: float = 60.0,
        max_snapshots_per_agent: int = 100,
        extinction_threshold: float = 0.1,
    ) -> None:
        self._snapshot_interval = snapshot_interval
        self._max_snapshots = max_snapshots_per_agent
        self._extinction_threshold = extinction_threshold

        # Performance data
        self._task_counts: dict[str, int] = defaultdict(int)
        self._success_counts: dict[str, int] = defaultdict(int)
        self._latency_samples: dict[str, list[float]] = defaultdict(list)
        self._quality_scores: dict[str, list[float]] = defaultdict(list)

        # Snapshots and profiles
        self._snapshots: dict[str, list[PerformanceSnapshot]] = defaultdict(list)
        self._profiles: dict[str, CapabilityProfile] = {}

        # Breeding and lineage
        self._lineages: dict[str, Lineage] = {}

        # Extinction tracking
        self._extinct_agents: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Performance recording
    # ------------------------------------------------------------------

    def record_task(
        self,
        agent_id: str,
        success: bool,
        latency_ms: float = 0.0,
        quality: float = 0.5,
    ) -> None:
        """Record a completed task for an agent."""
        self._task_counts[agent_id] += 1
        if success:
            self._success_counts[agent_id] += 1
        self._latency_samples[agent_id].append(latency_ms)
        self._quality_scores[agent_id].append(quality)

        # Prune old samples
        if len(self._latency_samples[agent_id]) > 500:
            self._latency_samples[agent_id] = self._latency_samples[agent_id][-500:]
        if len(self._quality_scores[agent_id]) > 500:
            self._quality_scores[agent_id] = self._quality_scores[agent_id][-500:]

    def take_snapshot(self, agent_id: str, capabilities: list[str] | None = None) -> PerformanceSnapshot:
        """Take a performance snapshot of an agent."""
        task_count = self._task_counts.get(agent_id, 0)
        success_count = self._success_counts.get(agent_id, 0)

        latencies = self._latency_samples.get(agent_id, [])
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        qualities = self._quality_scores.get(agent_id, [])
        avg_quality = sum(qualities) / len(qualities) if qualities else 0.0

        caps = capabilities or (
            self._profiles[agent_id].capabilities if agent_id in self._profiles else []
        )

        snapshot = PerformanceSnapshot(
            agent_id=agent_id,
            task_count=task_count,
            success_rate=success_count / task_count if task_count > 0 else 0.0,
            avg_latency_ms=avg_latency,
            avg_quality=avg_quality,
            capabilities=caps,
        )

        self._snapshots[agent_id].append(snapshot)
        if len(self._snapshots[agent_id]) > self._max_snapshots:
            self._snapshots[agent_id] = self._snapshots[agent_id][-self._max_snapshots:]

        return snapshot

    # ------------------------------------------------------------------
    # Capability evolution
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str, capabilities: list[str]) -> None:
        """Register an agent for evolution tracking."""
        if agent_id not in self._profiles:
            self._profiles[agent_id] = CapabilityProfile(agent_id=agent_id)
        for cap in capabilities:
            self._profiles[agent_id].add_capability(cap)

    def evolve_capabilities(
        self,
        agent_id: str,
        added: list[str],
        removed: list[str] | None = None,
    ) -> CapabilityProfile:
        """Evolve an agent's capabilities: add new ones, optionally remove old ones."""
        profile = self._profiles.get(agent_id)
        if profile is None:
            profile = CapabilityProfile(agent_id=agent_id)
            self._profiles[agent_id] = profile

        for cap in added:
            profile.add_capability(cap)

        for cap in (removed or []):
            profile.remove_capability(cap)

        logger.debug("Evolved capabilities for %s: +%s -%s", agent_id, added, removed or [])
        return profile

    def get_capability_profile(self, agent_id: str) -> CapabilityProfile | None:
        """Get an agent's capability profile."""
        return self._profiles.get(agent_id)

    def get_capability_evolution_metrics(self, agent_id: str) -> dict[str, Any]:
        """Get metrics on how an agent's capabilities have evolved."""
        profile = self._profiles.get(agent_id)
        if not profile:
            return {}

        return {
            "total_capabilities": profile.breadth,
            "avg_proficiency": profile.avg_proficiency,
            "evolution_count": profile.evolution_count,
            "proficiency": dict(profile.proficiency),
            "first_seen": dict(profile.first_seen),
        }

    # ------------------------------------------------------------------
    # Breeding / Merging
    # ------------------------------------------------------------------

    def breed(
        self,
        parent_ids: list[str],
        child_id: str | None = None,
        *,
        combination_strategy: str = "intersection",
    ) -> str:
        """Breed (merge) successful agents to create a new agent.

        Args:
            parent_ids: Agents to merge.
            child_id: ID for the child (auto-generated if None).
            combination_strategy: 'intersection' (shared capabilities),
                                  'union' (all capabilities),
                                  'weighted' (by performance).

        Returns:
            The child agent ID.
        """
        if len(parent_ids) < 2:
            raise ValueError("Need at least 2 parents for breeding")

        child = child_id or f"bred-{_new_id()}"

        # Get parent profiles
        parent_profiles = [
            p for p in (self._profiles.get(pid) for pid in parent_ids) if p is not None
        ]
        if not parent_profiles:
            raise ValueError("No valid parents found for breeding")

        # Determine child capabilities based on strategy
        if combination_strategy == "intersection":
            cap_sets = [set(p.capabilities) for p in parent_profiles]
            child_caps = list(set.intersection(*cap_sets))
        elif combination_strategy == "union":
            all_caps: set[str] = set()
            for p in parent_profiles:
                all_caps.update(p.capabilities)
            child_caps = list(all_caps)
        elif combination_strategy == "weighted":
            # Weight capabilities by parent performance
            weighted: dict[str, float] = defaultdict(float)
            for p in parent_profiles:
                snapshots = self._snapshots.get(p.agent_id, [])
                weight = snapshots[-1].success_rate if snapshots else 0.5
                for cap in p.capabilities:
                    weighted[cap] += weight
            threshold = len(parent_profiles) / 2
            child_caps = [c for c, w in weighted.items() if w >= threshold]
        else:
            child_caps = parent_profiles[0].capabilities

        # Register child
        self.register_agent(child, child_caps)

        # Create/update lineage
        root = self._find_root_ancestor(parent_ids[0])
        lineage = self._lineages.get(root)
        if lineage is None:
            lineage = Lineage(root_agent_id=root, members=[root])
            self._lineages[root] = lineage

        lineage.members.append(child)
        for pid in parent_ids:
            lineage.parent_map[child] = pid
        lineage.generations += 1

        # Seed child with average parent performance
        parent_success = [
            self._success_counts.get(pid, 0) / max(self._task_counts.get(pid, 1), 1)
            for pid in parent_ids
        ]
        avg_success = sum(parent_success) / len(parent_success)
        lineage.fitness_history.append(avg_success)

        logger.info(
            "Bred agent %s from %s using %s strategy (%d capabilities)",
            child,
            parent_ids,
            combination_strategy,
            len(child_caps),
        )
        return child

    def _find_root_ancestor(self, agent_id: str) -> str:
        """Walk parent_map to find the root ancestor."""
        for lineage in self._lineages.values():
            if agent_id in lineage.members:
                return lineage.root_agent_id
        return agent_id

    # ------------------------------------------------------------------
    # Extinction
    # ------------------------------------------------------------------

    def identify_underperformers(
        self,
        threshold: float | None = None,
        min_tasks: int = 10,
    ) -> list[str]:
        """Identify agents that should be considered for extinction.

        Returns agent IDs with sustained performance below the threshold.
        """
        thresh = threshold or self._extinction_threshold
        candidates: list[str] = []

        for agent_id in self._task_counts:
            task_count = self._task_counts[agent_id]
            if task_count < min_tasks:
                continue  # not enough data

            success_rate = self._success_counts.get(agent_id, 0) / task_count

            # Check if performance is declining
            snapshots = self._snapshots.get(agent_id, [])
            if len(snapshots) >= 3:
                recent = [s.success_rate for s in snapshots[-3:]]
                if all(r < thresh for r in recent):
                    candidates.append(agent_id)
            elif success_rate < thresh:
                candidates.append(agent_id)

        if candidates:
            logger.info("Identified %d underperformers for potential extinction", len(candidates))

        return candidates

    def mark_extinct(
        self,
        agent_id: str,
        reason: str = "underperformance",
    ) -> dict[str, Any]:
        """Mark an agent as extinct, preserving its record for analysis."""
        snapshot = self.take_snapshot(agent_id)

        record = {
            "agent_id": agent_id,
            "reason": reason,
            "extinct_at": _now(),
            "total_tasks": self._task_counts.get(agent_id, 0),
            "final_success_rate": snapshot.success_rate,
            "final_capabilities": snapshot.capabilities,
            "snapshots_count": len(self._snapshots.get(agent_id, [])),
        }
        self._extinct_agents[agent_id] = record

        logger.info("Agent %s marked extinct: %s", agent_id, reason)
        return record

    def is_extinct(self, agent_id: str) -> bool:
        """Check if an agent has been marked extinct."""
        return agent_id in self._extinct_agents

    def get_extinct_agents(self) -> list[dict[str, Any]]:
        """Return records of all extinct agents."""
        return list(self._extinct_agents.values())

    # ------------------------------------------------------------------
    # Performance queries
    # ------------------------------------------------------------------

    def get_performance(self, agent_id: str) -> dict[str, Any]:
        """Get comprehensive performance metrics for an agent."""
        task_count = self._task_counts.get(agent_id, 0)
        success_count = self._success_counts.get(agent_id, 0)
        latencies = self._latency_samples.get(agent_id, [])
        qualities = self._quality_scores.get(agent_id, [])

        return {
            "task_count": task_count,
            "success_rate": success_count / task_count if task_count > 0 else 0.0,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0.0,
            "avg_quality": sum(qualities) / len(qualities) if qualities else 0.0,
            "snapshots": len(self._snapshots.get(agent_id, [])),
            "extinct": self.is_extinct(agent_id),
        }

    def get_snapshots(
        self,
        agent_id: str,
        limit: int = 20,
    ) -> list[PerformanceSnapshot]:
        """Get recent performance snapshots for an agent."""
        snaps = self._snapshots.get(agent_id, [])
        return snaps[-limit:]

    def get_lineage(self, root_agent_id: str) -> Lineage | None:
        """Get lineage by root ancestor ID."""
        return self._lineages.get(root_agent_id)

    def get_all_lineages(self) -> list[Lineage]:
        """Get all tracked lineages."""
        return list(self._lineages.values())

    # ------------------------------------------------------------------
    # Composite metrics
    # ------------------------------------------------------------------

    def get_fitness_landscape(self) -> dict[str, Any]:
        """Return an overview of the current fitness landscape across all agents."""
        all_agents = list(self._profiles.keys()) + list(self._extinct_agents.keys())
        active = [a for a in self._profiles if not self.is_extinct(a)]

        if not active:
            return {
                "total_agents": len(all_agents),
                "active_agents": 0,
                "extinct_agents": len(self._extinct_agents),
                "avg_success_rate": 0.0,
                "best_agent": None,
                "best_success_rate": 0.0,
            }

        perf = {a: self.get_performance(a) for a in active}
        best = max(perf, key=lambda a: perf[a]["success_rate"])

        return {
            "total_agents": len(all_agents),
            "active_agents": len(active),
            "extinct_agents": len(self._extinct_agents),
            "avg_success_rate": sum(p["success_rate"] for p in perf.values()) / len(perf),
            "best_agent": best,
            "best_success_rate": perf[best]["success_rate"],
            "lineages": len(self._lineages),
        }

    def snapshot(self) -> dict[str, Any]:
        """Return current evolution state snapshot."""
        return {
            "tracked_agents": len(self._profiles),
            "extinct_agents": len(self._extinct_agents),
            "lineages": len(self._lineages),
            "fitness_landscape": self.get_fitness_landscape(),
            "top_performers": sorted(
                [
                    {"agent_id": aid, **self.get_performance(aid)}
                    for aid in list(self._profiles.keys())[:20]
                ],
                key=lambda x: x["success_rate"],
                reverse=True,
            )[:5],
        }
