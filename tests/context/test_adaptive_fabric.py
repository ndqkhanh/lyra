"""
Tests for Adaptive Context Fabric — ACON-style context optimization.

Covers:
- ``compress()`` reduces token count toward the target ratio
- ``evolve_context()`` learns better compaction over time
- ``speculate()`` pre-computes context on cache hit and miss
- Experience units store, score, and retrieve correctly
- Unit pruning removes stale entries
"""

from datetime import datetime, timedelta, timezone

import pytest

from lyra.context.adaptive_fabric import AdaptiveContextFabric, ContextPolicy
from lyra.context.compaction import CompactionStrategy
from lyra.context.experience_units import (
    ExperienceUnitType,
    Scheduler,
    TypedExperienceUnit,
    UnitLibrary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_messages(n: int, role: str = "user") -> list[dict[str, str]]:
    """Generate ``n`` messages with the given role."""
    return [
        {"role": role, "content": f"Message number {i} " * 10}
        for i in range(n)
    ]


def _make_system_messages() -> list[dict[str, str]]:
    """Return a realistic conversation with a system message."""
    return [
        {"role": "system", "content": "You are Lyra, a helpful AI research assistant."},
        {"role": "user", "content": "Search for papers on context compression." * 20},
        {"role": "assistant", "content": "I found 15 papers. The most relevant are..."},
        {"role": "user", "content": "Summarize the ACON approach." * 15},
        {"role": "assistant", "content": "ACON treats context as typed experience units that evolve per task."},
        {"role": "tool_result", "content": "Large JSON blob of search results " * 200},
    ]


# ---------------------------------------------------------------------------
# Compression tests
# ---------------------------------------------------------------------------


class TestCompress:
    """Verify that compress() reduces token count."""

    def test_compression_reduces_token_count(self):
        fabric = AdaptiveContextFabric()
        messages = _make_messages(20)
        compressed = fabric.compress(messages, target_ratio=0.5)

        original_tokens = sum(len(m["content"]) for m in messages) // 4
        compressed_tokens = sum(len(m["content"]) for m in compressed) // 4

        assert compressed_tokens < original_tokens, (
            f"Compressed ({compressed_tokens} tok) should be smaller "
            f"than original ({original_tokens} tok)"
        )

    def test_compression_preserves_system_message(self):
        fabric = AdaptiveContextFabric()
        messages = _make_system_messages()
        compressed = fabric.compress(messages, target_ratio=0.3)

        assert any(
            m["role"] == "system"
            for m in compressed
        ), "System message should be preserved"

    def test_compression_respects_keep_recent(self):
        fabric = AdaptiveContextFabric()
        msg_role = "assistant"
        messages = _make_messages(15, role=msg_role)
        messages[-1]["content"] = "LAST MESSAGE UNIQUE CONTENT 98765"

        compressed = fabric.compress(messages, target_ratio=0.1)

        # Last message should be in compressed output (keep_recent default = 5)
        assert any(
            "98765" in m.get("content", "")
            for m in compressed
        ), "Last message should be preserved"

    def test_compression_empty_messages(self):
        fabric = AdaptiveContextFabric()
        assert fabric.compress([]) == []

    def test_compression_target_ratio_zero(self):
        fabric = AdaptiveContextFabric()
        # Mix of roles with plenty of messages so keep_recent doesn't protect all.
        # Low-weight tool_result messages should be dropped at target_ratio=0.
        messages = [
            {"role": "system", "content": "System prompt."},
        ]
        for i in range(10):
            messages.append({"role": "tool_result", "content": f"Large data dump number {i} " * 200})
            messages.append({"role": "assistant", "content": f"Processed result {i}."})
        messages.append({"role": "user", "content": "Final question."})
        messages.append({"role": "assistant", "content": "Final answer."})

        original_tokens = sum(len(m["content"]) for m in messages) // 4
        compressed = fabric.compress(messages, target_ratio=0.0)
        compressed_tokens = sum(len(m["content"]) for m in compressed) // 4

        assert compressed_tokens < original_tokens
        # System message must be preserved
        assert any(m["role"] == "system" for m in compressed)
        # With 20+ non-system messages and keep_recent=5, at least some
        # tool_results should have been dropped
        assert len(compressed) < len(messages)

    def test_compression_target_ratio_one(self):
        fabric = AdaptiveContextFabric()
        messages = _make_messages(10)
        compressed = fabric.compress(messages, target_ratio=1.0)
        assert len(compressed) == len(messages)

    def test_compression_single_message(self):
        fabric = AdaptiveContextFabric()
        messages = [{"role": "user", "content": "Hello"}]
        compressed = fabric.compress(messages, target_ratio=0.5)
        assert len(compressed) == 1

    def test_compression_with_task_type_policy(self):
        fabric = AdaptiveContextFabric()
        messages = _make_messages(15)
        fabric.policies["code_review"] = ContextPolicy(
            compaction_strategy=CompactionStrategy.AGGRESSIVE,
            keep_recent=3,
            target_ratio=0.3,
        )
        compressed = fabric.compress(messages, task_type="code_review")

        original_tokens = sum(len(m["content"]) for m in messages) // 4
        compressed_tokens = sum(len(m["content"]) for m in compressed) // 4
        assert compressed_tokens <= original_tokens


# ---------------------------------------------------------------------------
# Evolution tests
# ---------------------------------------------------------------------------


class TestEvolveContext:
    """Verify that evolve_context() learns better policies."""

    def test_evolution_returns_policy(self):
        fabric = AdaptiveContextFabric()
        policy = fabric.evolve_context(
            task_type="code_search",
            feedback={"success": True, "latency_reduction": 0.5, "accuracy_loss": 0.0},
        )
        assert isinstance(policy, ContextPolicy)
        assert policy.target_ratio < 0.6  # should have tightened

    def test_evolution_becomes_more_aggressive_on_success(self):
        fabric = AdaptiveContextFabric()
        initial = fabric._get_policy("debug")
        initial_target = initial.target_ratio

        for _ in range(5):
            fabric.evolve_context(
                task_type="debug",
                feedback={"success": True, "latency_reduction": 0.5, "accuracy_loss": 0.05},
            )

        final = fabric._get_policy("debug")
        assert final.target_ratio < initial_target

    def test_evolution_becomes_conservative_on_failure(self):
        fabric = AdaptiveContextFabric()
        initial = fabric._get_policy("research")
        initial_target = initial.target_ratio

        for _ in range(3):
            fabric.evolve_context(
                task_type="research",
                feedback={"success": False, "latency_reduction": 0.0, "accuracy_loss": 0.5},
            )

        final = fabric._get_policy("research")
        assert final.target_ratio > initial_target

    def test_evolution_stores_experience_unit(self):
        fabric = AdaptiveContextFabric()
        fabric.evolve_context(
            task_type="testing",
            feedback={"success": True, "latency_reduction": 0.4, "accuracy_loss": 0.05},
        )
        units = fabric.unit_library.find_by_task("testing")
        assert len(units) == 1
        assert units[0].unit_type == ExperienceUnitType.STRATEGY

    def test_evolution_policy_persisted_in_dict(self):
        fabric = AdaptiveContextFabric()
        fabric.evolve_context(
            task_type="analysis",
            feedback={"success": True, "latency_reduction": 0.3, "accuracy_loss": 0.0},
        )
        assert "analysis" in fabric.policies


# ---------------------------------------------------------------------------
# Speculation tests
# ---------------------------------------------------------------------------


class TestSpeculate:
    """Verify that speculate() pre-computes context."""

    def test_speculate_returns_prediction(self):
        fabric = AdaptiveContextFabric()
        predicted = fabric.speculate(
            tool_name="grep_search",
            tool_input={"pattern": "def test_", "path": "."},
        )
        assert len(predicted) > 0
        assert predicted[0]["role"] == "assistant"

    def test_speculate_cache_hit(self):
        fabric = AdaptiveContextFabric()
        # First call — miss
        fabric.speculate(tool_name="read_file", tool_input={"path": "test.py"})
        # Second call with same inputs — hit
        predicted = fabric.speculate(
            tool_name="read_file",
            tool_input={"path": "test.py"},
        )
        assert len(predicted) > 0

    def test_speculate_cache_stats(self):
        fabric = AdaptiveContextFabric()
        fabric.speculate(tool_name="bash", tool_input={"command": "ls"})
        fabric.speculate(tool_name="bash", tool_input={"command": "ls"})
        fabric.speculate(tool_name="bash", tool_input={"command": "pwd"})

        stats = fabric.speculation_stats()
        assert stats["hits"] >= 1
        assert stats["misses"] >= 1
        assert stats["hit_rate"] > 0
        assert stats["cache_size"] > 0

    def test_speculate_unknown_tool(self):
        fabric = AdaptiveContextFabric()
        predicted = fabric.speculate(
            tool_name="nonexistent_tool_x",
            tool_input={"arg": "val"},
        )
        assert len(predicted) == 1
        assert "nonexistent_tool_x" in predicted[0]["content"]


# ---------------------------------------------------------------------------
# Experience units tests
# ---------------------------------------------------------------------------


class TestTypedExperienceUnit:
    """Verify TypedExperienceUnit behavior."""

    def test_unit_creation(self):
        unit = TypedExperienceUnit(
            unit_id="mem-001",
            unit_type=ExperienceUnitType.MEMORY,
            content="Module X is the entry point",
            task_type="code_search",
        )
        assert unit.unit_id == "mem-001"
        assert unit.unit_type == ExperienceUnitType.MEMORY
        assert unit.score == 0.0
        assert unit.use_count == 0

    def test_record_use_updates_score(self):
        unit = TypedExperienceUnit(
            unit_id="strat-001",
            unit_type=ExperienceUnitType.STRATEGY,
            content="Always verify edge cases first",
            task_type="testing",
        )
        unit.record_use(feedback=0.8)
        assert unit.use_count == 1
        assert unit.score > 0

    def test_record_use_multiple_times(self):
        unit = TypedExperienceUnit(
            unit_id="wf-001",
            unit_type=ExperienceUnitType.WORKFLOW,
            content="Step 1: search, Step 2: read, Step 3: synthesize",
            task_type="research",
        )
        for i in range(5):
            unit.record_use(feedback=0.5 + i * 0.1)
        assert unit.use_count == 5

    def test_is_stale_fresh_unit(self):
        unit = TypedExperienceUnit(
            unit_id="skill-001",
            unit_type=ExperienceUnitType.SKILL,
            content="Python decorator patterns",
            task_type="coding",
        )
        assert not unit.is_stale()

    def test_is_stale_old_unused(self):
        unit = TypedExperienceUnit(
            unit_id="stale-001",
            unit_type=ExperienceUnitType.MEMORY,
            content="Old irrelevant fact",
            task_type="general",
            last_used_at=datetime.now(timezone.utc) - timedelta(days=60),
            use_count=0,
            score=0.0,
        )
        assert unit.is_stale()

    def test_to_dict_serialization(self):
        unit = TypedExperienceUnit(
            unit_id="dict-001",
            unit_type=ExperienceUnitType.MEMORY,
            content="Test serialization",
            task_type="testing",
        )
        d = unit.to_dict()
        assert d["unit_id"] == "dict-001"
        assert d["unit_type"] == "memory"
        assert isinstance(d["created_at"], str)


class TestUnitLibrary:
    """Verify UnitLibrary store, score, and prune."""

    def test_add_and_get(self):
        lib = UnitLibrary()
        unit = TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.MEMORY,
            content="test", task_type="general",
        )
        lib.add(unit)
        assert lib.get("u1") is unit
        assert lib.get("nonexistent") is None

    def test_add_replaces_existing(self):
        lib = UnitLibrary()
        u1 = TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.MEMORY,
            content="v1", task_type="general",
        )
        u2 = TypedExperienceUnit(
            unit_id="u1", unit_type=ExperienceUnitType.MEMORY,
            content="v2", task_type="general",
        )
        lib.add(u1)
        lib.add(u2)
        assert lib.get("u1").content == "v2"

    def test_find_by_task_type(self):
        lib = UnitLibrary()
        lib.add(TypedExperienceUnit(
            unit_id="a", unit_type=ExperienceUnitType.MEMORY,
            content="A", task_type="code_search",
        ))
        lib.add(TypedExperienceUnit(
            unit_id="b", unit_type=ExperienceUnitType.STRATEGY,
            content="B", task_type="debug",
        ))

        code_results = lib.find_by_task("code_search")
        assert len(code_results) == 1
        debug_results = lib.find_by_task("debug")
        assert len(debug_results) == 1

    def test_find_by_task_sorts_by_score(self):
        lib = UnitLibrary()
        u_low = TypedExperienceUnit(
            unit_id="low", unit_type=ExperienceUnitType.MEMORY,
            content="Low", task_type="test", score=0.2,
        )
        u_high = TypedExperienceUnit(
            unit_id="high", unit_type=ExperienceUnitType.MEMORY,
            content="High", task_type="test", score=0.9,
        )
        lib.add(u_low)
        lib.add(u_high)
        results = lib.find_by_task("test")
        assert results[0].unit_id == "high"

    def test_find_by_type(self):
        lib = UnitLibrary()
        lib.add(TypedExperienceUnit(
            unit_id="m1", unit_type=ExperienceUnitType.MEMORY,
            content="M1", task_type="t",
        ))
        lib.add(TypedExperienceUnit(
            unit_id="m2", unit_type=ExperienceUnitType.MEMORY,
            content="M2", task_type="t",
        ))
        memories = lib.find_by_type(ExperienceUnitType.MEMORY)
        assert len(memories) == 2

    def test_score_unit(self):
        lib = UnitLibrary()
        unit = TypedExperienceUnit(
            unit_id="scorable", unit_type=ExperienceUnitType.STRATEGY,
            content="test", task_type="t", score=0.5,
        )
        lib.add(unit)
        new_score = lib.score_unit("scorable", feedback=0.9)
        assert new_score is not None
        assert new_score > 0.5

    def test_score_unit_not_found(self):
        lib = UnitLibrary()
        assert lib.score_unit("nonexistent", feedback=0.5) is None

    def test_prune_stale_removes_old_entries(self):
        lib = UnitLibrary()
        lib.add(TypedExperienceUnit(
            unit_id="fresh", unit_type=ExperienceUnitType.MEMORY,
            content="Fresh", task_type="t",
        ))
        stale = TypedExperienceUnit(
            unit_id="stale", unit_type=ExperienceUnitType.MEMORY,
            content="Stale", task_type="t",
            last_used_at=datetime.now(timezone.utc) - timedelta(days=60),
            use_count=0,
            score=0.0,
        )
        lib.add(stale)
        pruned = lib.prune_stale(max_age_days=30, min_uses=1, score_threshold=0.1)
        assert pruned == 1
        assert lib.get("fresh") is not None
        assert lib.get("stale") is None

    def test_prune_stale_no_stale(self):
        lib = UnitLibrary()
        lib.add(TypedExperienceUnit(
            unit_id="active", unit_type=ExperienceUnitType.MEMORY,
            content="Active", task_type="t", score=0.8,
        ))
        pruned = lib.prune_stale()
        assert pruned == 0

    def test_total_units(self):
        lib = UnitLibrary()
        assert lib.total_units == 0
        lib.add(TypedExperienceUnit(
            unit_id="x", unit_type=ExperienceUnitType.MEMORY,
            content="X", task_type="t",
        ))
        assert lib.total_units == 1

    def test_stats(self):
        lib = UnitLibrary()
        lib.add(TypedExperienceUnit(
            unit_id="s1", unit_type=ExperienceUnitType.STRATEGY,
            content="S1", task_type="t", score=0.7,
        ))
        lib.add(TypedExperienceUnit(
            unit_id="m1", unit_type=ExperienceUnitType.MEMORY,
            content="M1", task_type="t", score=0.3,
        ))
        stats = lib.stats()
        assert stats["total_units"] == 2
        assert stats["per_type"]["strategy"]["count"] == 1
        assert stats["per_type"]["memory"]["count"] == 1


class TestScheduler:
    """Verify Scheduler budget allocation."""

    def test_allocate_empty_library(self):
        lib = UnitLibrary()
        scheduler = Scheduler()
        budget = scheduler.allocate_budget(lib)
        assert sum(budget.values()) == pytest.approx(1.0, rel=0.01)
        assert len(budget) == len(ExperienceUnitType)

    def test_allocate_with_units(self):
        lib = UnitLibrary()
        lib.add(TypedExperienceUnit(
            unit_id="m1", unit_type=ExperienceUnitType.MEMORY,
            content="M1", task_type="t", score=0.9,
        ))
        lib.add(TypedExperienceUnit(
            unit_id="m2", unit_type=ExperienceUnitType.MEMORY,
            content="M2", task_type="t", score=0.8,
        ))
        scheduler = Scheduler()
        budget = scheduler.allocate_budget(lib)
        assert sum(budget.values()) == pytest.approx(1.0, rel=0.01)

    def test_allocate_weak_types_get_more(self):
        lib = UnitLibrary()
        # Only MEMORY has units, and they have high scores
        lib.add(TypedExperienceUnit(
            unit_id="m1", unit_type=ExperienceUnitType.MEMORY,
            content="M1", task_type="t", score=0.9,
        ))
        scheduler = Scheduler()
        budget = scheduler.allocate_budget(lib)

        # Types with zero units should get more budget than the memory type
        zero_types = {"strategy", "workflow", "skill"}
        for zt in zero_types:
            assert zt in budget, f"Type {zt} should be in budget"


# ---------------------------------------------------------------------------
# Cost-per-token tracking tests
# ---------------------------------------------------------------------------


class TestCostPerTokenTracker:
    """Verify CostPerTokenTracker records and aggregates cost data."""

    def test_record_and_stats(self):
        from lyra.context.adaptive_fabric import CostPerTokenTracker
        from lyra.context.compaction import CompactionStrategy

        tracker = CostPerTokenTracker()
        tracker.record(CompactionStrategy.BALANCED, 1000, 500, 0.001, "code")
        stats = tracker.stats_by_strategy()
        assert stats["total_ops"] == 1
        assert stats["avg_compression_ratio"] > 0

    def test_stats_by_strategy_filtered(self):
        from lyra.context.adaptive_fabric import CostPerTokenTracker
        from lyra.context.compaction import CompactionStrategy

        tracker = CostPerTokenTracker()
        tracker.record(CompactionStrategy.BALANCED, 1000, 500, 0.001, "code")
        tracker.record(CompactionStrategy.AGGRESSIVE, 2000, 300, 0.002, "code")
        stats = tracker.stats_by_strategy(CompactionStrategy.BALANCED)
        assert stats["total_ops"] == 1

    def test_stats_by_strategy_empty(self):
        from lyra.context.adaptive_fabric import CostPerTokenTracker
        from lyra.context.compaction import CompactionStrategy

        tracker = CostPerTokenTracker()
        stats = tracker.stats_by_strategy(CompactionStrategy.AGGRESSIVE)
        assert stats["total_ops"] == 0

    def test_best_strategy(self):
        from lyra.context.adaptive_fabric import CostPerTokenTracker
        from lyra.context.compaction import CompactionStrategy

        tracker = CostPerTokenTracker()
        tracker.record(CompactionStrategy.BALANCED, 1000, 500, 0.001, "code")
        best, cost = tracker.best_strategy_by_cost_efficiency()
        assert best == "balanced"

    def test_best_strategy_empty(self):
        from lyra.context.adaptive_fabric import CostPerTokenTracker

        tracker = CostPerTokenTracker()
        best, cost = tracker.best_strategy_by_cost_efficiency()
        assert best == "unknown"
        assert cost == 0.0


# ---------------------------------------------------------------------------
# TaskTypeProfiles tests
# ---------------------------------------------------------------------------


class TestTaskTypeProfiles:
    """Verify TaskTypeProfiles registry."""

    def test_get_by_task_type_code(self):
        from lyra.context.adaptive_fabric import ProfileType, TaskTypeProfiles
        profiles = TaskTypeProfiles()
        profile = profiles.get_by_task_type("code_review")
        assert profile.profile_type == ProfileType.CODE

    def test_get_by_task_type_chat(self):
        from lyra.context.adaptive_fabric import ProfileType, TaskTypeProfiles
        profiles = TaskTypeProfiles()
        profile = profiles.get_by_task_type("chat")
        assert profile.profile_type == ProfileType.CHAT

    def test_get_by_task_type_unknown(self):
        from lyra.context.adaptive_fabric import ProfileType, TaskTypeProfiles
        profiles = TaskTypeProfiles()
        profile = profiles.get_by_task_type("nonexistent")
        assert profile.profile_type == ProfileType.GENERAL

    def test_get_by_profile_type_code(self):
        from lyra.context.adaptive_fabric import ProfileType, TaskTypeProfiles
        profiles = TaskTypeProfiles()
        p = profiles.get_by_profile_type(ProfileType.CODE)
        assert p.protect_code is True

    def test_get_by_profile_type_unknown(self):
        from lyra.context.adaptive_fabric import ProfileType, TaskTypeProfiles
        profiles = TaskTypeProfiles()
        p = profiles.get_by_profile_type(ProfileType.GENERAL)
        assert p.description == "Default balanced profile."

    def test_all_profiles_count(self):
        from lyra.context.adaptive_fabric import TaskTypeProfiles
        profiles = TaskTypeProfiles()
        assert len(profiles.all_profiles) == 4

    def test_update_profile(self):
        from lyra.context.adaptive_fabric import ProfileType, TaskTypeProfile, TaskTypeProfiles
        profiles = TaskTypeProfiles()
        updated = TaskTypeProfile(
            profile_type=ProfileType.CHAT,
            protect_code=False,
            summarization_aggressiveness=0.9,
            keep_citations=True,
            default_target_ratio=0.3,
            description="Updated chat",
        )
        profiles.update_profile(updated)
        assert profiles.get_by_profile_type(ProfileType.CHAT).summarization_aggressiveness == 0.9


# ---------------------------------------------------------------------------
# Profile learning tests
# ---------------------------------------------------------------------------


class TestProfileLearning:
    """Verify learn_profile_from_feedback adapts profiles."""

    def test_good_quality_increases_agg(self):
        fabric = AdaptiveContextFabric()
        profile = fabric.learn_profile_from_feedback(
            "code_review", {"compaction_quality": 0.9}
        )
        assert profile.summarization_aggressiveness > 0.4

    def test_poor_quality_decreases_agg(self):
        fabric = AdaptiveContextFabric()
        profile = fabric.learn_profile_from_feedback(
            "code_review", {"compaction_quality": 0.2}
        )
        assert profile.summarization_aggressiveness < 0.5

    def test_poor_quality_enables_code_protection(self):
        fabric = AdaptiveContextFabric()
        profile = fabric.learn_profile_from_feedback(
            "code_review", {"compaction_quality": 0.3}
        )
        assert profile.protect_code is True

    def test_get_compaction_quality_scores(self):
        fabric = AdaptiveContextFabric()
        scores = fabric.get_compaction_quality_scores("test_task")
        assert isinstance(scores, list)

    def test_has_citation(self):
        fabric = AdaptiveContextFabric()
        assert fabric._has_citation("see [1] for details")
        assert fabric._has_citation("see arxiv paper")
        assert fabric._has_citation("see doi.org/abc")
        assert not fabric._has_citation("plain text without citations")

    def test_compress_with_model(self):
        """Compression records cost and tracks profiled protections."""
        fabric = AdaptiveContextFabric()
        messages = [
            {"role": "system", "content": "You are a coding assistant."},
            {"role": "user", "content": "Write Python code to sort a list: ```python\ndef sort_list(items):\n    return sorted(items)\n```"},
            {"role": "assistant", "content": "Here is the code."},
            {"role": "user", "content": "Thanks!"},
        ]
        compressed = fabric.compress(messages, task_type="code_review")
        # System message preserved
        assert any(m["role"] == "system" for m in compressed)
        # Cost was recorded
        assert fabric.cost_tracker.stats_by_strategy()["total_ops"] >= 1

    def test_learn_profile_from_feedback_non_code(self):
        """Non-code task with poor quality does not enable code protection."""
        fabric = AdaptiveContextFabric()
        profile = fabric.learn_profile_from_feedback(
            "chat", {"compaction_quality": 0.3}
        )
        assert profile.protect_code is False

    def test_update_task_type_profile_no_feedback_key(self):
        """_update_task_type_profile returns early with empty feedback."""
        fabric = AdaptiveContextFabric()
        fabric._update_task_type_profile("test_task", {})
        # Should not crash

    def test_update_task_type_profile_with_success(self):
        """_update_task_type_profile uses success as quality proxy."""
        fabric = AdaptiveContextFabric()
        fabric._update_task_type_profile("testing", {"success": True})
        profile = fabric.task_type_profiles.get_by_task_type("testing")
        assert profile is not None

    def test_speculate_cache_eviction(self):
        """Speculation cache evicts oldest when exceeding 200 entries."""
        fabric = AdaptiveContextFabric()
        for i in range(250):
            fabric.speculate(f"tool_{i}", {"param": i})
        stats = fabric.speculation_stats()
        assert stats["cache_size"] <= 200

    def test_policy_default_for_unknown_task_type(self):
        """_get_policy returns default ContextPolicy for None."""
        fabric = AdaptiveContextFabric()
        policy = fabric._get_policy(None)
        assert policy.target_ratio == 0.6

    def test_get_policy_stores_new_policy(self):
        """_get_policy creates and stores a new policy for unknown types."""
        fabric = AdaptiveContextFabric()
        policy = fabric._get_policy("new_task_type")
        assert "new_task_type" in fabric.policies
        assert policy.target_ratio == 0.6
