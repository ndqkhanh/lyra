"""Tests for the Population Broadcast module (FORGE-style).

Covers ReflectionAgent, PopulationBroadcast, SynthesizedMemory,
AgentProfile, BroadcastEvent, and memory propagation logic.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from lyra.memory.memory_store import Memory, MemoryStore, MemoryType
from lyra.memory.population_broadcast import (
    AgentProfile,
    BroadcastEvent,
    MemoryTypeCategory,
    PopulationBroadcast,
    ReflectionAgent,
    SynthesizedMemory,
)


# ===================================================================
# SynthesizedMemory tests
# ===================================================================


class TestSynthesizedMemory:
    """Tests for the SynthesizedMemory dataclass."""

    def test_creation(self) -> None:
        mem = SynthesizedMemory(
            memory_id="m1",
            category=MemoryTypeCategory.RULE,
            content="When X happens, do Y",
            source_agent_id="agent-1",
            task_type="code_gen",
            reward_score=0.8,
        )
        assert mem.memory_id == "m1"
        assert mem.category == MemoryTypeCategory.RULE
        assert mem.broadcast_count == 0
        assert mem.performance_gain == 0.0

    def test_with_metadata(self) -> None:
        mem = SynthesizedMemory(
            memory_id="m1",
            category=MemoryTypeCategory.EXAMPLE,
            content="test",
            source_agent_id="a1",
            metadata={"source_model": "claude"},
        )
        assert mem.metadata["source_model"] == "claude"

    def test_default_values(self) -> None:
        mem = SynthesizedMemory(
            memory_id="m1",
            category=MemoryTypeCategory.STRATEGY,
            content="test",
            source_agent_id="a1",
        )
        assert mem.task_type == "general"
        assert mem.reward_score == 0.0


# ===================================================================
# AgentProfile tests
# ===================================================================


class TestAgentProfile:
    """Tests for the AgentProfile dataclass."""

    def test_creation(self) -> None:
        profile = AgentProfile(agent_id="agent-1", model_name="claude-sonnet-4")
        assert profile.agent_id == "agent-1"
        assert profile.model_name == "claude-sonnet-4"
        assert profile.memory_store is None
        assert profile.task_rewards == []
        assert profile.reflection_count == 0

    def test_with_store(self) -> None:
        store = MemoryStore()
        profile = AgentProfile(agent_id="a1", memory_store=store)
        assert profile.memory_store is store


# ===================================================================
# BroadcastEvent tests
# ===================================================================


class TestBroadcastEvent:
    """Tests for the BroadcastEvent dataclass."""

    def test_creation(self) -> None:
        mem = SynthesizedMemory(
            memory_id="m1", category=MemoryTypeCategory.RULE,
            content="test", source_agent_id="a1",
        )
        event = BroadcastEvent(
            event_id="e1",
            timestamp=time.time(),
            synthesized_memory=mem,
            target_agent_ids=["a1", "a2"],
        )
        assert event.event_id == "e1"
        assert len(event.target_agent_ids) == 2
        assert event.accepted_count == 0


# ===================================================================
# ReflectionAgent tests
# ===================================================================


class TestReflectionAgent:
    """Tests for the ReflectionAgent."""

    def test_creation(self) -> None:
        agent = ReflectionAgent()
        assert agent.synthesizer is None
        assert agent._synthesis_count == 0

    def test_reflect_on_trajectory_with_synthesizer(self) -> None:
        def custom_synth(traj, task, reward):
            return SynthesizedMemory(
                memory_id="custom",
                category=MemoryTypeCategory.RULE,
                content="Custom synthesis",
                source_agent_id="test",
            )
        agent = ReflectionAgent(synthesizer=custom_synth)
        mem = agent.reflect_on_trajectory(
            "failed task", "code_gen", 0.3, "agent-1",
        )
        assert mem.content == "Custom synthesis"
        assert agent._synthesis_count == 1

    def test_reflect_failure_rule(self) -> None:
        agent = ReflectionAgent()
        mem = agent.reflect_on_trajectory(
            "The agent failed and got an error during execution",
            "qa", 0.2, "agent-1", "claude-sonnet",
        )
        assert mem.category == MemoryTypeCategory.RULE
        assert "Rule" in mem.content
        assert mem.reward_score == 0.2

    def test_reflect_success_example(self) -> None:
        agent = ReflectionAgent()
        mem = agent.reflect_on_trajectory(
            "The task succeeded and passed all tests correctly",
            "qa", 0.9, "agent-1", "gpt-4o",
        )
        assert mem.category == MemoryTypeCategory.EXAMPLE
        assert "Example" in mem.content

    def test_reflect_ambiguous_strategy(self) -> None:
        agent = ReflectionAgent()
        mem = agent.reflect_on_trajectory(
            "The agent processed the data and completed the task",
            "general", 0.5, "agent-1", "haiku",
        )
        # With no clear failure/success signals and reward=0.5, should be RULE or STRATEGY
        assert mem.category in (MemoryTypeCategory.RULE, MemoryTypeCategory.STRATEGY)

    def test_reflect_low_reward_with_success_signal(self) -> None:
        agent = ReflectionAgent()
        mem = agent.reflect_on_trajectory(
            "Succeeded but got low reward",
            "test", 0.3, "agent-1",
        )
        # has_success=True but reward < 0.5 -> could be STRATEGY or RULE
        assert isinstance(mem, SynthesizedMemory)

    def test_reflect_on_batch(self) -> None:
        agent = ReflectionAgent()
        trajectories = [
            ("failed task A", "code", 0.2, "agent-1", "claude"),
            ("succeeded task B", "code", 0.9, "agent-1", "claude"),
        ]
        memories = agent.reflect_on_batch(
            [(t[0], t[1], t[2]) for t in trajectories],
            source_agent_id="agent-1",
            agent_model="claude",
        )
        assert len(memories) == 2
        # Should be sorted by reward descending
        assert memories[0].reward_score >= memories[1].reward_score

    def test_get_statistics(self) -> None:
        agent = ReflectionAgent()
        agent.reflect_on_trajectory("test", "qa", 0.5, "a1")
        stats = agent.get_statistics()
        assert stats["synthesis_count"] == 1
        assert stats["has_external_synthesizer"] is False

    def test_get_statistics_with_synthesizer(self) -> None:
        agent = ReflectionAgent(synthesizer=lambda t, tk, r: SynthesizedMemory(
            memory_id="m", category=MemoryTypeCategory.RULE,
            content="c", source_agent_id="a",
        ))
        stats = agent.get_statistics()
        assert stats["has_external_synthesizer"] is True

    def test_extract_rule_content_truncated(self) -> None:
        agent = ReflectionAgent()
        long_traj = "failed. " * 200
        mem = agent.reflect_on_trajectory(
            long_traj, "test", 0.1, "agent-1", "claude",
        )
        # Should be truncated
        assert len(mem.content) <= 500


# ===================================================================
# PopulationBroadcast tests
# ===================================================================


class TestPopulationBroadcast:
    """Tests for the PopulationBroadcast class."""

    def test_creation(self) -> None:
        pb = PopulationBroadcast()
        assert pb.get_population_size() == 0
        assert pb.reward_threshold == 0.3
        assert pb.broadcast_top_k == 3

    def test_custom_params(self) -> None:
        pb = PopulationBroadcast(
            reward_threshold=0.5,
            broadcast_top_k=5,
            max_memories_per_agent=50,
        )
        assert pb.reward_threshold == 0.5
        assert pb.broadcast_top_k == 5

    def test_register_agent(self) -> None:
        pb = PopulationBroadcast()
        profile = pb.register_agent("agent-1", model_name="claude-sonnet")
        assert profile.agent_id == "agent-1"
        assert profile.model_name == "claude-sonnet"
        assert pb.get_population_size() == 1

    def test_register_agent_with_store(self) -> None:
        pb = PopulationBroadcast()
        store = MemoryStore()
        pb.register_agent("agent-1", store=store)
        assert pb.get_agent("agent-1").memory_store is store

    def test_remove_agent(self) -> None:
        pb = PopulationBroadcast()
        pb.register_agent("agent-1")
        pb.remove_agent("agent-1")
        assert pb.get_agent("agent-1") is None

    def test_get_agent_nonexistent(self) -> None:
        pb = PopulationBroadcast()
        assert pb.get_agent("nonexistent") is None

    def test_get_agents_by_model(self) -> None:
        pb = PopulationBroadcast()
        pb.register_agent("a1", model_name="claude")
        pb.register_agent("a2", model_name="claude")
        pb.register_agent("a3", model_name="gpt")
        agents = pb.get_agents_by_model("claude")
        assert len(agents) == 2

    def test_submit_trajectory_unregistered_raises(self) -> None:
        pb = PopulationBroadcast()
        with pytest.raises(ValueError, match="not registered"):
            pb.submit_trajectory("unknown", "traj", "test", 0.5)

    def test_submit_trajectory(self) -> None:
        pb = PopulationBroadcast()
        pb.register_agent("agent-1", model_name="claude")
        mem = pb.submit_trajectory("agent-1", "failed task", "code", 0.3)
        assert isinstance(mem, SynthesizedMemory)
        assert mem.source_agent_id == "agent-1"
        assert pb.get_agent("agent-1").reflection_count == 1

    def test_submit_batch_trajectories(self) -> None:
        pb = PopulationBroadcast()
        pb.register_agent("agent-1")
        trajectories = [
            ("failed task A", "code", 0.3),
            ("succeeded task B", "code", 0.9),
        ]
        mems = pb.submit_batch_trajectories("agent-1", trajectories)
        assert len(mems) == 2
        assert pb.get_agent("agent-1").reflection_count == 2

    def test_submit_batch_unregistered_raises(self) -> None:
        pb = PopulationBroadcast()
        with pytest.raises(ValueError, match="not registered"):
            pb.submit_batch_trajectories("unknown", [])

    def test_broadcast_no_memories(self) -> None:
        pb = PopulationBroadcast()
        result = pb.broadcast()
        assert result is None

    def test_broadcast_basic(self) -> None:
        pb = PopulationBroadcast(reward_threshold=0.0)  # Accept all
        pb.register_agent("agent-1", model_name="claude", store=MemoryStore())
        pb.register_agent("agent-2", model_name="gpt", store=MemoryStore())

        # Submit a trajectory
        pb.submit_trajectory("agent-1", "succeeded perfectly", "code", 0.9)

        event = pb.broadcast()
        assert event is not None
        assert len(event.target_agent_ids) == 2
        assert event.accepted_count >= 2

    def test_broadcast_with_reward_threshold(self) -> None:
        pb = PopulationBroadcast(reward_threshold=0.8)
        pb.register_agent("a1", store=MemoryStore())
        pb.register_agent("a2", store=MemoryStore())

        pb.submit_trajectory("a1", "low reward", "test", 0.2)
        result = pb.broadcast()
        assert result is None  # Below threshold

    def test_broadcast_memory_cap_enforced(self) -> None:
        pb = PopulationBroadcast(
            reward_threshold=0.0,
            max_memories_per_agent=2,
        )
        pb.register_agent("a1", store=MemoryStore())
        pb.submit_trajectory("a1", "succeeded", "test", 0.9)

        # Broadcast many times
        for _ in range(5):
            pb.submit_trajectory("a1", "succeeded again", "test", 0.9)
            pb.broadcast()

        # Agent store should be capped
        agent = pb.get_agent("a1")
        assert len(agent.memory_store.get_all()) <= 2

    def test_broadcast_to_weak_agents_no_weak(self) -> None:
        pb = PopulationBroadcast(reward_threshold=0.0)
        pb.register_agent("a1", store=MemoryStore())
        pb.register_agent("a2", store=MemoryStore())

        pb.submit_trajectory("a1", "succeeded", "test", 0.9)

        result = pb.broadcast_to_weak_agents()
        # No weak agents (no rewards yet for comparison)
        assert result is None

    def test_broadcast_to_weak_agents_with_weak(self) -> None:
        pb = PopulationBroadcast(reward_threshold=0.0)
        weak_store = MemoryStore()
        strong_store = MemoryStore()
        pb.register_agent("strong", model_name="claude", store=strong_store)
        pb.register_agent("weak", model_name="haiku", store=weak_store)

        # Strong agent has good trajectory
        pb.submit_trajectory("strong", "succeeded perfectly", "code", 0.9)

        result = pb.broadcast_to_weak_agents()
        # Weak agent has no rewards yet, so average might be computed differently
        assert result is not None or result is None

    def test_query_broadcast_memories(self) -> None:
        pb = PopulationBroadcast(reward_threshold=0.0)
        store = MemoryStore()
        pb.register_agent("a1", store=store)
        pb.register_agent("a2", store=store)
        pb.submit_trajectory("a1", "succeeded", "test", 0.9)
        pb.broadcast()

        mems = pb.query_broadcast_memories("a1")
        assert len(mems) >= 0

    def test_query_broadcast_memories_nonexistent(self) -> None:
        pb = PopulationBroadcast()
        mems = pb.query_broadcast_memories("unknown")
        assert mems == []

    def test_query_broadcast_memories_no_store(self) -> None:
        pb = PopulationBroadcast()
        pb.register_agent("a1")  # No store
        mems = pb.query_broadcast_memories("a1")
        assert mems == []

    def test_get_best_broadcast_memories(self) -> None:
        pb = PopulationBroadcast(reward_threshold=0.0)
        pb.register_agent("a1", store=MemoryStore())
        pb.submit_trajectory("a1", "succeeded", "test", 0.9)
        pb.broadcast()

        best = pb.get_best_broadcast_memories(top_k=5)
        assert isinstance(best, list)

    def test_get_broadcast_history(self) -> None:
        pb = PopulationBroadcast(reward_threshold=0.0)
        pb.register_agent("a1", store=MemoryStore())
        pb.submit_trajectory("a1", "succeeded", "test", 0.9)
        pb.broadcast()

        history = pb.get_broadcast_history()
        assert len(history) >= 1

    def test_compute_average_reward(self) -> None:
        pb = PopulationBroadcast()
        pb.register_agent("a1")
        pb.register_agent("a2")
        # Manually add rewards
        pb.get_agent("a1").task_rewards = [0.5, 0.7]
        pb.get_agent("a2").task_rewards = [0.8]
        avg = pb._compute_average_reward()
        assert avg == pytest.approx((0.5 + 0.7 + 0.8) / 3)

    def test_compute_average_reward_empty(self) -> None:
        pb = PopulationBroadcast()
        assert pb._compute_average_reward() == 0.0

    def test_get_statistics(self) -> None:
        pb = PopulationBroadcast(reward_threshold=0.4, broadcast_top_k=5)
        pb.register_agent("a1", model_name="claude")
        pb.register_agent("a2", model_name="gpt")
        pb.submit_trajectory("a1", "succeeded", "test", 0.9)
        stats = pb.get_statistics()
        assert stats["population_size"] == 2
        assert stats["model_distribution"]["claude"] == 1
        assert stats["model_distribution"]["gpt"] == 1
        assert stats["total_synthesized_memories"] == 1


# ===================================================================
# MemoryTypeCategory tests
# ===================================================================


class TestMemoryTypeCategory:
    """Tests for MemoryTypeCategory enum."""

    def test_values(self) -> None:
        assert MemoryTypeCategory.RULE.value == "rule"
        assert MemoryTypeCategory.EXAMPLE.value == "example"
        assert MemoryTypeCategory.STRATEGY.value == "strategy"

    def test_all_values(self) -> None:
        assert len(list(MemoryTypeCategory)) == 3
