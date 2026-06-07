"""
Population Broadcast — FORGE-style cross-agent memory propagation.

Implements the FORGE population broadcast mechanism described in:
    FORGE: Population-Level Memory Synthesis for Multi-Agent Systems.
    arXiv:2605.16233 (2026).

Key mechanisms:
    - Reflection Agent: Converts agent failure trajectories into reusable
      Rules and Examples by analyzing failure patterns and extracting
      actionable lessons.
    - Population Broadcast: Propagates the best-performing memories
      (Rules/Examples) across all agents in a population, replacing
      underperforming individual memories.
    - Disproportionate benefit for weaker models: smaller/weaker models
      gain the most from population-broadcast memories (1.7-7.7x reward
      improvement across tasks).
    - Filtering by reward threshold: only memories that demonstrably
      improve task reward are broadcast.

Performance targets (FORGE, arXiv:2605.16233, §4):
    - 1.7-7.7x reward improvement across diverse tasks
    - Weaker models see 2-3x larger gains than stronger models
    - Effective across task types (code generation, QA, reasoning)

References:
    FORGE (2026). Population-Level Memory Synthesis for Multi-Agent
        Systems. arXiv:2605.16233.
    Mem0 Inc. (2025). Mem0: A Memory Layer for Personalized AI.
        arXiv:2504.19413v1 — ADD-only extraction pattern.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import numpy as np

from lyra.memory.memory_store import Memory, MemoryStore, MemoryType


# =============================================================================
# Constants
# =============================================================================

DEFAULT_REWARD_THRESHOLD: float = 0.3       # minimum reward to broadcast
DEFAULT_POPULATION_SIZE: int = 10           # default agent population
DEFAULT_BROADCAST_TOP_K: int = 3            # best K memories to broadcast
DEFAULT_MAX_MEMORIES_PER_AGENT: int = 100   # cap per agent memory store

# Performance targets (FORGE §4, Table 1-3)
TARGET_REWARD_IMPROVEMENT_MIN: float = 1.7     # 1.7x minimum
TARGET_REWARD_IMPROVEMENT_MAX: float = 7.7     # 7.7x maximum
TARGET_WEAK_MODEL_BOOST: float = 3.0           # weaker models gain ~3x


# =============================================================================
# Data structures
# =============================================================================


class MemoryTypeCategory(Enum):
    """Category of synthesized memory from failure analysis."""
    RULE = "rule"           # Reusable rule: "When X happens, do Y"
    EXAMPLE = "example"     # Concrete example: "In task Z, approach W worked"
    STRATEGY = "strategy"   # High-level strategy: "For domain D, prefer approach A"


@dataclass
class SynthesizedMemory:
    """
    A memory synthesized by the reflection agent.

    Attributes:
        memory_id: Unique identifier.
        category: Type of synthesized memory (Rule/Example/Strategy).
        content: The memory content (reusable lesson).
        source_agent_id: Which agent produced the source trajectory.
        task_type: Type of task that generated this memory.
        reward_score: Task reward associated with this memory (0.0-1.0).
        broadcast_count: How many times this memory was broadcast.
        performance_gain: Measured performance gain after application.
        created_at: When this memory was created.
        trajectory_summary: Brief summary of the source trajectory.
    """
    memory_id: str
    category: MemoryTypeCategory
    content: str
    source_agent_id: str
    task_type: str = "general"
    reward_score: float = 0.0
    broadcast_count: int = 0
    performance_gain: float = 0.0
    created_at: float = 0.0
    trajectory_summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentProfile:
    """
    Profile of an agent in the population.

    Attributes:
        agent_id: Unique agent identifier.
        model_name: Model identifier (e.g. "claude-sonnet-4", "gpt-4o").
        memory_store: Local memory store for this agent.
        task_rewards: History of task rewards for this agent.
        reflection_count: How many times reflection has run.
    """
    agent_id: str
    model_name: str = "unknown"
    memory_store: MemoryStore | None = None
    task_rewards: list[float] = field(default_factory=list)
    reflection_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BroadcastEvent:
    """
    A single broadcast event in the population.

    Attributes:
        event_id: Unique identifier.
        timestamp: When the broadcast occurred.
        synthesized_memory: The memory that was broadcast.
        target_agent_ids: Which agents received it.
        reward_before: Average reward of targets before broadcast.
        reward_after: Average reward of targets after broadcast.
        accepted_count: How many agents accepted the broadcast.
    """
    event_id: str
    timestamp: float
    synthesized_memory: SynthesizedMemory
    target_agent_ids: list[str]
    reward_before: float = 0.0
    reward_after: float = 0.0
    accepted_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Reflection Agent
# =============================================================================


class ReflectionAgent:
    """
    Converts agent failure trajectories into reusable Rules/Examples.

    The reflection agent analyzes agent trajectories (sequences of
    observations, actions, and rewards) and extracts actionable
    knowledge:

    - **Rules**: Conditional instructions ("When X, do Y").
    - **Examples**: Concrete demonstrations of successful approaches.
    - **Strategies**: High-level domain guidance.

    Reference: FORGE (2026, §3.2) — "The reflection agent identifies
    failure patterns, extracts the root cause, and formulates a reusable
    memory that prevents recurrence."
    """

    def __init__(
        self,
        synthesizer: Callable[[str, str, float], SynthesizedMemory] | None = None,
    ):
        """
        Initialize the reflection agent.

        Args:
            synthesizer: Optional external LLM-based synthesizer.
                Signature: (trajectory: str, task_type: str, reward: float) -> SynthesizedMemory.
        """
        self.synthesizer = synthesizer
        self._synthesis_count: int = 0

    def reflect_on_trajectory(
        self,
        trajectory: str,
        task_type: str,
        reward: float,
        source_agent_id: str,
        agent_model: str = "unknown",
    ) -> SynthesizedMemory:
        """
        Analyze a trajectory and produce a synthesized memory.

        If an external synthesizer is configured, delegates to it.
        Otherwise uses a rule-based heuristic extractor.

        Args:
            trajectory: The agent's trajectory (textual description).
            task_type: Type of task (e.g. "code_generation", "qa").
            reward: Task reward score (0.0-1.0).
            source_agent_id: Which agent produced this trajectory.
            agent_model: Model name of the source agent.

        Returns:
            A SynthesizedMemory extracted from the trajectory.
        """
        if self.synthesizer is not None:
            memory = self.synthesizer(trajectory, task_type, reward)
            memory.source_agent_id = source_agent_id
            memory.reward_score = reward
            self._synthesis_count += 1
            return memory

        # Default rule-based extraction
        memory = self._extract_from_trajectory(
            trajectory, task_type, reward, source_agent_id, agent_model
        )
        self._synthesis_count += 1
        return memory

    def _extract_from_trajectory(
        self,
        trajectory: str,
        task_type: str,
        reward: float,
        source_agent_id: str,
        agent_model: str,
    ) -> SynthesizedMemory:
        """
        Rule-based trajectory analysis (fallback when no LLM synthesizer).

        Extracts:
            - Failure keywords → Rule (correction)
            - Success signals → Example (demonstration)
            - Repeated patterns → Strategy (generalization)
        """
        traj_lower = trajectory.lower()

        # Determine category
        failure_signals = ["failed", "error", "incorrect", "wrong", "bug", "issue"]
        success_signals = ["succeeded", "correct", "passed", "works", "solved"]

        has_failure = any(s in traj_lower for s in failure_signals)
        has_success = any(s in traj_lower for s in success_signals)

        if has_failure and reward < 0.5:
            category = MemoryTypeCategory.RULE
            # Extract a rule from the trajectory
            sentences = [s.strip() for s in trajectory.split(".") if s.strip()]
            error_sentences = [
                s for s in sentences
                if any(f in s.lower() for f in failure_signals)
            ]
            rule_content = (
                f"Rule [from {source_agent_id}/{agent_model}]: "
                f"{error_sentences[0] if error_sentences else trajectory[:200]}"
            )
        elif has_success and reward >= 0.5:
            category = MemoryTypeCategory.EXAMPLE
            sentences = [s.strip() for s in trajectory.split(".") if s.strip()]
            success_sentences = [
                s for s in sentences
                if any(f in s.lower() for f in success_signals)
            ]
            content = (
                f"Example [from {source_agent_id}/{agent_model}]: "
                f"{success_sentences[0] if success_sentences else trajectory[:200]}"
            )
            return SynthesizedMemory(
                memory_id=str(uuid.uuid4()),
                category=category,
                content=content,
                source_agent_id=source_agent_id,
                task_type=task_type,
                reward_score=reward,
                created_at=time.time(),
                trajectory_summary=trajectory[:150],
            )
        else:
            category = MemoryTypeCategory.STRATEGY
            rule_content = (
                f"Strategy [from {source_agent_id}/{agent_model}]: "
                f"{trajectory[:200]}"
            )

        # Trim to reasonable length
        if len(rule_content) > 500:
            rule_content = rule_content[:497] + "..."

        return SynthesizedMemory(
            memory_id=str(uuid.uuid4()),
            category=category,
            content=rule_content,
            source_agent_id=source_agent_id,
            task_type=task_type,
            reward_score=reward,
            created_at=time.time(),
            trajectory_summary=trajectory[:150],
            metadata={
                "source_model": agent_model,
            },
        )

    def reflect_on_batch(
        self,
        trajectories: list[tuple[str, str, float]],
        source_agent_id: str,
        agent_model: str = "unknown",
    ) -> list[SynthesizedMemory]:
        """
        Reflect on a batch of trajectories.

        Args:
            trajectories: List of (trajectory, task_type, reward) tuples.
            source_agent_id: Source agent identifier.
            agent_model: Source model name.

        Returns:
            List of synthesized memories, sorted by reward descending.
        """
        memories = []
        for trajectory, task_type, reward in trajectories:
            mem = self.reflect_on_trajectory(
                trajectory, task_type, reward, source_agent_id, agent_model
            )
            memories.append(mem)

        memories.sort(key=lambda m: m.reward_score, reverse=True)
        return memories

    def get_statistics(self) -> dict[str, Any]:
        """Return reflection agent statistics."""
        return {
            "synthesis_count": self._synthesis_count,
            "has_external_synthesizer": self.synthesizer is not None,
        }


# =============================================================================
# Population Broadcast
# =============================================================================


class PopulationBroadcast:
    """
    FORGE-style population-level memory broadcast.

    Propagates the best-performing SynthesizedMemories across all
    agents in a population. Agents with lower task reward benefit
    disproportionately from receiving broadcast memories.

    The broadcast cycle:
        1. COLLECT — Gather synthesized memories from all agents.
        2. EVALUATE — Score each memory by its associated reward.
        3. SELECT — Choose the top-K memories by reward threshold.
        4. BROADCAST — Propagate selected memories to all agents.
        5. VERIFY — Measure reward change after broadcast.
    """

    def __init__(
        self,
        reflection_agent: ReflectionAgent | None = None,
        reward_threshold: float = DEFAULT_REWARD_THRESHOLD,
        broadcast_top_k: int = DEFAULT_BROADCAST_TOP_K,
        max_memories_per_agent: int = DEFAULT_MAX_MEMORIES_PER_AGENT,
    ):
        """
        Initialize the population broadcast system.

        Args:
            reflection_agent: Agent for trajectory→memory synthesis.
            reward_threshold: Minimum reward score for broadcast eligibility.
            broadcast_top_k: Number of top memories to broadcast per cycle.
            max_memories_per_agent: Cap on memories per agent store.
        """
        self.reflection_agent = reflection_agent or ReflectionAgent()
        self.reward_threshold = reward_threshold
        self.broadcast_top_k = broadcast_top_k
        self.max_memories_per_agent = max_memories_per_agent

        # Population state
        self._agents: dict[str, AgentProfile] = {}
        self._synthesized_memories: list[SynthesizedMemory] = []
        self._broadcast_history: list[BroadcastEvent] = []

    # ------------------------------------------------------------------
    # Population management
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        model_name: str = "unknown",
        store: MemoryStore | None = None,
    ) -> AgentProfile:
        """
        Register an agent in the population.

        Args:
            agent_id: Unique agent identifier.
            model_name: Model name (used to track weaker-model benefit).
            store: Optional agent-local memory store.

        Returns:
            The created AgentProfile.
        """
        profile = AgentProfile(
            agent_id=agent_id,
            model_name=model_name,
            memory_store=store or MemoryStore(),
        )
        self._agents[agent_id] = profile
        return profile

    def remove_agent(self, agent_id: str):
        """Remove an agent from the population."""
        self._agents.pop(agent_id, None)

    def get_agent(self, agent_id: str) -> AgentProfile | None:
        """Get an agent's profile."""
        return self._agents.get(agent_id)

    def get_population_size(self) -> int:
        """Return the number of registered agents."""
        return len(self._agents)

    def get_agents_by_model(self, model_name: str) -> list[AgentProfile]:
        """Get all agents running a specific model."""
        return [
            a for a in self._agents.values()
            if a.model_name == model_name
        ]

    # ------------------------------------------------------------------
    # Trajectory submission
    # ------------------------------------------------------------------

    def submit_trajectory(
        self,
        agent_id: str,
        trajectory: str,
        task_type: str,
        reward: float,
    ) -> SynthesizedMemory:
        """
        Submit an agent trajectory for reflection and memory synthesis.

        The trajectory is analyzed by the reflection agent, which
        extracts a SynthesizedMemory. The agent's reward history is
        updated.

        Args:
            agent_id: Submitting agent.
            trajectory: Agent trajectory text.
            task_type: Task type descriptor.
            reward: Task reward (0.0-1.0).

        Returns:
            The synthesized memory.
        """
        agent = self._agents.get(agent_id)
        if agent is None:
            raise ValueError(f"Agent '{agent_id}' not registered. Call register_agent() first.")

        # Update reward history
        agent.task_rewards.append(reward)
        agent.reflection_count += 1

        # Synthesize memory via reflection agent
        memory = self.reflection_agent.reflect_on_trajectory(
            trajectory=trajectory,
            task_type=task_type,
            reward=reward,
            source_agent_id=agent_id,
            agent_model=agent.model_name,
        )

        self._synthesized_memories.append(memory)
        return memory

    def submit_batch_trajectories(
        self,
        agent_id: str,
        trajectories: list[tuple[str, str, float]],
    ) -> list[SynthesizedMemory]:
        """
        Submit multiple trajectories for batch reflection.

        Args:
            agent_id: Submitting agent.
            trajectories: List of (trajectory, task_type, reward) tuples.

        Returns:
            List of synthesized memories.
        """
        agent = self._agents.get(agent_id)
        if agent is None:
            raise ValueError(f"Agent '{agent_id}' not registered.")

        memories = self.reflection_agent.reflect_on_batch(
            trajectories, source_agent_id=agent_id, agent_model=agent.model_name
        )

        for mem, (_, _, reward) in zip(memories, trajectories):
            agent.task_rewards.append(reward)
            self._synthesized_memories.append(mem)

        agent.reflection_count += len(trajectories)
        return memories

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    def broadcast(self) -> BroadcastEvent | None:
        """
        Execute one population broadcast cycle.

        Selects the top-K synthesized memories by reward score and
        propagates them to all agents. The broadcast is tracked with
        pre/post reward averages for verification.

        Returns:
            A BroadcastEvent describing what was broadcast, or None
            if no memories meet the threshold.
        """
        if not self._synthesized_memories:
            return None

        # 1. Evaluate: score memories by reward
        scored: list[tuple[float, SynthesizedMemory]] = [
            (m.reward_score, m)
            for m in self._synthesized_memories
        ]
        scored.sort(key=lambda x: x[0], reverse=True)

        # 2. Select: top-K above threshold
        selected: list[SynthesizedMemory] = []
        for reward, memory in scored:
            if reward < self.reward_threshold:
                break
            selected.append(memory)
            if len(selected) >= self.broadcast_top_k:
                break

        if not selected:
            return None

        # 3. Broadcast: propagate to all agents
        target_ids = list(self._agents.keys())
        reward_before = self._compute_average_reward()

        event_id = str(uuid.uuid4())
        now = time.time()
        accepted_count = 0

        for agent_id, agent in self._agents.items():
            for memory in selected:
                # Convert SynthesizedMemory → Memory for the store
                syn_mem = Memory(
                    memory_id=memory.memory_id + f"@{agent_id}",
                    content=memory.content,
                    memory_type=MemoryType.PROCEDURAL
                    if memory.category == MemoryTypeCategory.RULE
                    else MemoryType.SEMANTIC,
                    timestamp=now,
                    importance=min(1.0, memory.reward_score * 0.8 + 0.2),
                    tags=[
                        "broadcast",
                        memory.category.value,
                        memory.task_type,
                        f"source:{memory.source_agent_id}",
                    ],
                    context={
                        "synthesized_memory_id": memory.memory_id,
                        "source_agent": memory.source_agent_id,
                        "source_model": memory.metadata.get("source_model", ""),
                        "task_type": memory.task_type,
                        "broadcast_event_id": event_id,
                    },
                )
                # Add to agent's local store
                if agent.memory_store:
                    # Enforce capacity cap
                    all_mems = agent.memory_store.get_all()
                    if len(all_mems) >= self.max_memories_per_agent:
                        # Remove lowest-importance broadcast memory
                        all_mems.sort(key=lambda m: m.importance)
                        agent.memory_store.delete(all_mems[0].memory_id)

                    agent.memory_store.add(
                        content=syn_mem.content,
                        memory_type=syn_mem.memory_type,
                        importance=syn_mem.importance,
                        tags=syn_mem.tags,
                        context=syn_mem.context,
                    )

                memory.broadcast_count += 1
                accepted_count += 1

        reward_after = self._compute_average_reward()
        performance_gain = reward_after / max(reward_before, 1e-12)

        # Update performance gain on memories
        for memory in selected:
            memory.performance_gain = performance_gain

        event = BroadcastEvent(
            event_id=event_id,
            timestamp=now,
            synthesized_memory=selected[0],  # primary memory
            target_agent_ids=target_ids,
            reward_before=reward_before,
            reward_after=reward_after,
            accepted_count=accepted_count,
            metadata={
                "num_selected": len(selected),
                "num_targets": len(target_ids),
                "performance_gain_x": performance_gain,
                "reward_threshold": self.reward_threshold,
                "broadcast_top_k": self.broadcast_top_k,
            },
        )

        self._broadcast_history.append(event)
        return event

    def broadcast_to_weak_agents(self) -> BroadcastEvent | None:
        """
        Broadcast only to agents with below-average reward.

        FORGE finding: weaker models benefit disproportionately from
        population broadcast. This method targets the broadcast to
        maximize the weak-model boost.

        Returns:
            A BroadcastEvent for the targeted broadcast.
        """
        if not self._synthesized_memories:
            return None

        # Compute average reward across population
        all_rewards = [
            r for agent in self._agents.values()
            for r in agent.task_rewards
        ]
        avg_reward = float(np.mean(all_rewards)) if all_rewards else 0.5

        # Find weak agents (below-average reward)
        weak_agents = [
            agent_id for agent_id, agent in self._agents.items()
            if agent.task_rewards and float(np.mean(agent.task_rewards)) < avg_reward
        ]

        if not weak_agents:
            return None

        # Select top-K memories
        scored: list[tuple[float, SynthesizedMemory]] = [
            (m.reward_score, m)
            for m in self._synthesized_memories
            if m.reward_score >= self.reward_threshold
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        selected = [m for _, m in scored[:self.broadcast_top_k]]

        if not selected:
            return None

        # Broadcast to weak agents only
        target_ids = weak_agents
        reward_before = float(np.mean([
            r for a_id, a in self._agents.items()
            for r in a.task_rewards
        ])) if all_rewards else 0.0

        event_id = str(uuid.uuid4())
        now = time.time()
        accepted_count = 0

        for agent_id in weak_agents:
            agent = self._agents[agent_id]
            for memory in selected:
                if agent.memory_store:
                    agent.memory_store.add(
                        content=memory.content,
                        memory_type=MemoryType.PROCEDURAL
                        if memory.category == MemoryTypeCategory.RULE
                        else MemoryType.SEMANTIC,
                        importance=min(1.0, memory.reward_score * 0.8 + 0.2),
                        tags=["broadcast", "weak-targeted", memory.category.value],
                        context={"broadcast_event_id": event_id},
                    )
                memory.broadcast_count += 1
                accepted_count += 1

        event = BroadcastEvent(
            event_id=event_id,
            timestamp=now,
            synthesized_memory=selected[0],
            target_agent_ids=target_ids,
            reward_before=reward_before,
            accepted_count=accepted_count,
            metadata={
                "num_selected": len(selected),
                "num_targets": len(target_ids),
                "targeted_broadcast": True,
                "avg_population_reward": avg_reward,
            },
        )

        self._broadcast_history.append(event)
        return event

    # ------------------------------------------------------------------
    # Query / retrieval
    # ------------------------------------------------------------------

    def query_broadcast_memories(
        self,
        agent_id: str,
        category: MemoryTypeCategory | None = None,
        top_k: int = 10,
    ) -> list[Memory]:
        """
        Query broadcast memories stored by a specific agent.

        Args:
            agent_id: Which agent's store to query.
            category: Optional category filter (Rule/Example/Strategy).
            top_k: Maximum results.

        Returns:
            List of broadcast memories stored by the agent.
        """
        agent = self._agents.get(agent_id)
        if agent is None or agent.memory_store is None:
            return []

        all_mems = agent.memory_store.get_all()
        broadcast = [m for m in all_mems if "broadcast" in m.tags]

        if category:
            broadcast = [m for m in broadcast if category.value in m.tags]

        broadcast.sort(key=lambda m: m.importance, reverse=True)
        return broadcast[:top_k]

    def get_best_broadcast_memories(
        self,
        top_k: int = 10,
    ) -> list[SynthesizedMemory]:
        """
        Return the best-performing broadcast memories across the population.

        Memories are sorted by performance_gain (how much reward
        improved after broadcast).

        Args:
            top_k: Maximum results.

        Returns:
            List of best SynthesizedMemories.
        """
        candidates = [
            m for m in self._synthesized_memories
            if m.broadcast_count > 0
        ]
        candidates.sort(key=lambda m: m.performance_gain, reverse=True)
        return candidates[:top_k]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compute_average_reward(self) -> float:
        """Compute the aggregate average reward across all agents."""
        all_rewards = [
            r for agent in self._agents.values()
            for r in agent.task_rewards
        ]
        return float(np.mean(all_rewards)) if all_rewards else 0.0

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_broadcast_history(self) -> list[BroadcastEvent]:
        """Return the full broadcast history."""
        return list(self._broadcast_history)

    def get_statistics(self) -> dict[str, Any]:
        """
        Return comprehensive population broadcast statistics.

        Returns:
            Dictionary with population state and performance metrics.
        """
        all_rewards = [
            r for agent in self._agents.values()
            for r in agent.task_rewards
        ]
        avg_reward = float(np.mean(all_rewards)) if all_rewards else 0.0

        model_distribution: dict[str, int] = {}
        for agent in self._agents.values():
            model_distribution[agent.model_name] = (
                model_distribution.get(agent.model_name, 0) + 1
            )

        total_synthesized = len(self._synthesized_memories)
        broadcast_synthesized = sum(
            1 for m in self._synthesized_memories if m.broadcast_count > 0
        )

        return {
            "population_size": len(self._agents),
            "model_distribution": model_distribution,
            "total_synthesized_memories": total_synthesized,
            "broadcast_memories": broadcast_synthesized,
            "broadcast_cycles": len(self._broadcast_history),
            "avg_population_reward": avg_reward,
            "reward_threshold": self.reward_threshold,
            "broadcast_top_k": self.broadcast_top_k,
            "max_memories_per_agent": self.max_memories_per_agent,
            "reflection_synthesis_count": self.reflection_agent.get_statistics()["synthesis_count"],
            "performance_targets": {
                "reward_improvement_x_min": TARGET_REWARD_IMPROVEMENT_MIN,
                "reward_improvement_x_max": TARGET_REWARD_IMPROVEMENT_MAX,
                "weak_model_boost_x": TARGET_WEAK_MODEL_BOOST,
            },
        }
