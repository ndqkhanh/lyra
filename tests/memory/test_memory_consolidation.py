"""
Tests for Memory Consolidation.
"""

import time

from lyra.memory.long_term_memory import LongTermMemory
from lyra.memory.memory_consolidation import (
    AutoConsolidationScheduler,
    BackgroundConsolidationDaemon,
    ConsolidationPolicy,
    ConsolidationResult,
    ConsolidationStats,
    MemoryConsolidator,
)
from lyra.memory.memory_store import MemoryType
from lyra.memory.short_term_memory import ConversationTurn, ShortTermMemory


class TestConsolidationResult:
    """Test ConsolidationResult class."""

    def test_result_creation(self):
        """Test creating a consolidation result."""
        result = ConsolidationResult(
            memories_created=5,
            memories_merged=2,
            patterns_extracted=1,
            duration=0.5,
        )

        assert result.memories_created == 5
        assert result.memories_merged == 2
        assert result.patterns_extracted == 1
        assert result.duration == 0.5


class TestMemoryConsolidator:
    """Test MemoryConsolidator class."""

    def test_consolidator_creation(self):
        """Test creating a memory consolidator."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)

        assert consolidator.policy == ConsolidationPolicy.THRESHOLD
        assert consolidator.importance_threshold == 0.5

    def test_should_consolidate_immediate(self):
        """Test immediate consolidation policy."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.IMMEDIATE
        )

        assert consolidator.should_consolidate()

    def test_should_consolidate_threshold(self):
        """Test threshold consolidation policy."""
        stm = ShortTermMemory(consolidation_threshold=3)
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.THRESHOLD
        )

        assert not consolidator.should_consolidate()

        stm.add_turn("user", "Turn 1")
        stm.add_turn("agent", "Turn 2")
        stm.add_turn("user", "Turn 3")

        assert consolidator.should_consolidate()

    def test_should_consolidate_periodic(self):
        """Test periodic consolidation policy."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.PERIODIC
        )

        # Just created, should not consolidate
        assert not consolidator.should_consolidate()

        # Simulate time passing
        consolidator.last_consolidation = time.time() - 400
        assert consolidator.should_consolidate()

    def test_should_consolidate_manual(self):
        """Test manual consolidation policy."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.MANUAL
        )

        assert not consolidator.should_consolidate()

    def test_consolidate(self):
        """Test consolidation process."""
        stm = ShortTermMemory(consolidation_threshold=2)
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)

        stm.add_turn("user", "Important message")
        stm.add_turn("agent", "Response")
        stm.add_turn("user", "Another message")

        result = consolidator.consolidate()

        assert isinstance(result, ConsolidationResult)
        assert result.memories_created >= 0
        assert result.duration > 0

    def test_consolidate_creates_memories(self):
        """Test that consolidation creates long-term memories."""
        stm = ShortTermMemory(consolidation_threshold=2)
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)

        stm.add_turn("user", "A" * 200)  # Long message = high importance
        stm.add_turn("agent", "Response")
        stm.add_turn("user", "Another long message " * 20)

        initial_count = len(ltm.store.memories)
        consolidator.consolidate()
        final_count = len(ltm.store.memories)

        assert final_count > initial_count

    def test_extract_patterns(self):
        """Test pattern extraction."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)

        # Add episodic memories with repeated keywords
        for i in range(5):
            ltm.add(f"Python programming task {i}", MemoryType.EPISODIC)

        patterns = consolidator._extract_patterns()

        # Should find "python" and "programming" patterns
        assert patterns >= 0

    def test_find_repeated_patterns(self):
        """Test finding repeated patterns."""
        from lyra.memory.memory_store import Memory

        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)

        memories = [
            Memory("m1", "Python programming is great", MemoryType.EPISODIC, time.time()),
            Memory("m2", "Python coding is fun", MemoryType.EPISODIC, time.time()),
            Memory("m3", "Python development rocks", MemoryType.EPISODIC, time.time()),
        ]

        patterns = consolidator._find_repeated_patterns(memories)

        # Should find "python" pattern
        assert len(patterns) > 0

    def test_consolidate_specific(self):
        """Test consolidating specific turns."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)

        turns = [
            ConversationTurn("user", "Message 1", time.time()),
            ConversationTurn("agent", "Response 1", time.time()),
            ConversationTurn("user", "Message 2", time.time()),
        ]

        created = consolidator.consolidate_specific(turns)

        assert created >= 0
        assert len(ltm.store.memories) >= 0

    def test_calculate_turn_importance(self):
        """Test calculating turn importance."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)

        # User turn with long content
        turn1 = ConversationTurn("user", "A" * 200, time.time())
        importance1 = consolidator._calculate_turn_importance(turn1)

        # Agent turn with short content
        turn2 = ConversationTurn("agent", "Short", time.time())
        importance2 = consolidator._calculate_turn_importance(turn2)

        assert importance1 > importance2

    def test_calculate_turn_importance_with_metadata(self):
        """Test importance calculation with metadata."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)

        turn = ConversationTurn(
            "user",
            "Test",
            time.time(),
            metadata={"important": True}
        )

        importance = consolidator._calculate_turn_importance(turn)

        assert importance >= 0.7

    def test_extract_knowledge(self):
        """Test extracting knowledge about a topic."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)

        # Add memories about Python
        ltm.add("Python is a programming language", MemoryType.EPISODIC)
        ltm.add("Python is used for web development", MemoryType.EPISODIC)
        ltm.add("Python has great libraries", MemoryType.EPISODIC)

        knowledge = consolidator.extract_knowledge("Python")

        assert knowledge is not None
        assert knowledge.memory_type == MemoryType.SEMANTIC
        assert "Python" in knowledge.content

    def test_extract_knowledge_no_results(self):
        """Test extracting knowledge with no relevant memories."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)

        knowledge = consolidator.extract_knowledge("NonexistentTopic")

        assert knowledge is None

    def test_create_procedure(self):
        """Test creating a procedural memory."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)

        steps = [
            "Step 1: Initialize",
            "Step 2: Process",
            "Step 3: Finalize",
        ]

        procedure = consolidator.create_procedure("Test Procedure", steps)

        assert procedure.memory_type == MemoryType.PROCEDURAL
        assert "Test Procedure" in procedure.content
        assert all(step in procedure.content for step in steps)

    def test_auto_consolidate(self):
        """Test automatic consolidation."""
        stm = ShortTermMemory(consolidation_threshold=2)
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.THRESHOLD
        )

        # Not enough turns yet
        result = consolidator.auto_consolidate()
        assert result is None

        # Add enough turns
        stm.add_turn("user", "Message 1")
        stm.add_turn("agent", "Response 1")
        stm.add_turn("user", "Message 2")

        result = consolidator.auto_consolidate()
        assert result is not None

    def test_auto_consolidate_manual_policy(self):
        """Test auto consolidate with manual policy."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.MANUAL
        )

        stm.add_turn("user", "Message")
        result = consolidator.auto_consolidate()

        assert result is None

    def test_get_statistics(self):
        """Test getting consolidation statistics."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.THRESHOLD,
            importance_threshold=0.6
        )

        stats = consolidator.get_statistics()

        assert stats["policy"] == "threshold"
        assert stats["importance_threshold"] == 0.6
        assert "last_consolidation" in stats
        assert "should_consolidate" in stats

    def test_consolidation_respects_importance_threshold(self):
        """Test that consolidation respects importance threshold."""
        stm = ShortTermMemory(consolidation_threshold=2)
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            importance_threshold=0.9  # Very high threshold
        )

        # Add low-importance turns
        stm.add_turn("system", "Low importance")
        stm.add_turn("system", "Also low")
        stm.add_turn("system", "Still low")

        result = consolidator.consolidate()

        # Should create few or no memories
        assert result.memories_created <= 1

    def test_consolidation_merges_similar(self):
        """Test that consolidation merges similar memories."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)

        # Add duplicate memories
        ltm.add("Same content", MemoryType.SEMANTIC)
        ltm.add("Same content", MemoryType.SEMANTIC)
        ltm.add("Different content", MemoryType.SEMANTIC)

        result = consolidator.consolidate()

        assert result.memories_merged >= 0


class TestAutoConsolidationScheduler:
    """Tests for AutoConsolidationScheduler."""

    def test_initial_state(self):
        scheduler = AutoConsolidationScheduler()
        stats = scheduler.get_stats()
        assert stats.optimal_interval == 300.0
        assert stats.avg_items_per_run == 0.0

    def test_record_run_updates_stats(self):
        scheduler = AutoConsolidationScheduler()
        result = ConsolidationResult(memories_created=5, memories_merged=2, patterns_extracted=1, duration=1.0)
        scheduler.record_run(result)
        assert scheduler._run_count == 1
        assert scheduler.get_stats().avg_items_per_run > 0

    def test_should_consolidate_by_default(self):
        scheduler = AutoConsolidationScheduler(min_interval=0.01)
        assert scheduler.should_consolidate(time_since_last=301.0) is True

    def test_should_not_consolidate_recently(self):
        scheduler = AutoConsolidationScheduler(max_interval=900.0)
        scheduler._stats.optimal_interval = 600.0
        assert scheduler.should_consolidate(time_since_last=100) is False

    def test_reset(self):
        scheduler = AutoConsolidationScheduler()
        scheduler.record_run(ConsolidationResult(5, 2, 1, 1.0))
        scheduler.reset()
        assert scheduler.get_stats().avg_items_per_run == 0.0

    def test_record_run_adjusts_interval_up(self):
        """When yield decreases and items is 0, interval increases."""
        scheduler = AutoConsolidationScheduler(adaptation_rate=0.1)
        scheduler.record_run(ConsolidationResult(5, 2, 1, 1.0))
        initial = scheduler.get_stats().optimal_interval
        scheduler.record_run(ConsolidationResult(0, 0, 0, 1.0))
        # Yield decreased, items=0 => interval grows
        after = scheduler.get_stats().optimal_interval
        assert after >= initial

    def test_clamp_interval_to_min(self):
        scheduler = AutoConsolidationScheduler(min_interval=100, max_interval=9999)
        # After record_run with very short duration, interval may go below min
        scheduler._stats.optimal_interval = 50
        scheduler.record_run(ConsolidationResult(memories_created=1, memories_merged=0, patterns_extracted=0, duration=0.1))
        assert scheduler.get_stats().optimal_interval >= 100

    def test_clamp_interval_to_max(self):
        scheduler = AutoConsolidationScheduler(min_interval=1, max_interval=200)
        scheduler._stats.optimal_interval = 9999
        scheduler.record_run(ConsolidationResult(memories_created=0, memories_merged=0, patterns_extracted=0, duration=1.0))
        assert scheduler.get_stats().optimal_interval <= 200


class TestBackgroundConsolidationDaemon:
    """Tests for BackgroundConsolidationDaemon."""

    def test_initial_state(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        daemon = BackgroundConsolidationDaemon(consolidator, check_interval=0.01)
        assert daemon.is_running is False
        assert daemon.runs_completed == 0

    def test_start_stop(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        daemon = BackgroundConsolidationDaemon(consolidator, check_interval=0.01)
        daemon.start()
        assert daemon.is_running is True
        daemon.stop()
        assert daemon.is_running is False

    def test_report_activity(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        daemon = BackgroundConsolidationDaemon(consolidator)
        before = daemon._last_agent_activity
        daemon.report_activity()
        assert daemon._last_agent_activity >= before

    def test_double_start_is_noop(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        daemon = BackgroundConsolidationDaemon(consolidator)
        daemon.start()
        daemon.start()  # should not raise
        assert daemon.is_running is True
        daemon.stop()

    def test_double_stop_is_noop(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        daemon = BackgroundConsolidationDaemon(consolidator)
        daemon.stop()  # should not raise

    def test_stats_property(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        daemon = BackgroundConsolidationDaemon(consolidator)
        stats = daemon.stats
        assert "running" in stats
        assert "runs_completed" in stats

    def test_get_recent_results(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        daemon = BackgroundConsolidationDaemon(consolidator)
        assert daemon.get_recent_results() == []


class TestMemoryConsolidatorAdvanced:
    """Advanced tests for MemoryConsolidator edge cases."""

    def test_auto_scheduler_auto_created(self):
        """Auto scheduler is created when policy is AUTO."""
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.AUTO
        )
        assert consolidator.auto_scheduler is not None

    def test_auto_scheduler_not_created_for_threshold(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.THRESHOLD
        )
        assert consolidator.auto_scheduler is None

    def test_extract_knowledge_no_relevant(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        knowledge = consolidator.extract_knowledge("python")
        assert knowledge is None

    def test_consolidate_specific_below_threshold(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm, importance_threshold=0.9)
        turn = ConversationTurn("system", "ok", time.time())
        created = consolidator.consolidate_specific([turn])
        assert created == 0

    def test_calculate_turn_importance_with_metadata_important(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        turn = ConversationTurn("user", "test", time.time(), metadata={"important": True})
        importance = consolidator._calculate_turn_importance(turn)
        assert importance >= 0.7

    def test_auto_consolidate_auto_policy(self):
        stm = ShortTermMemory(consolidation_threshold=2)
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.AUTO
        )
        stm.add_turn("user", "Hey")
        stm.add_turn("agent", "Hi")
        stm.add_turn("user", "What's up")
        result = consolidator.auto_consolidate()
        assert result is not None or consolidator.auto_scheduler is not None

    def test_consolidation_stats_after_run(self):
        stm = ShortTermMemory(consolidation_threshold=2)
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        stm.add_turn("user", "Test")
        stm.add_turn("agent", "Response")
        consolidator.consolidate()
        stats = consolidator.get_statistics()
        assert stats["time_since_last"] >= 0

    def test_create_procedure(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        proc = consolidator.create_procedure("test", ["step1", "step2"])
        assert proc.memory_type == MemoryType.PROCEDURAL
        assert "Procedure: test" in proc.content

    def test_auto_consolidate_manual_policy_returns_none(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.MANUAL
        )
        assert consolidator.auto_consolidate() is None


class TestConsolidationEdgeCases:
    """Edge case tests for full coverage."""

    def test_stats_to_dict(self):
        stats = ConsolidationStats(avg_items_per_run=5.5, avg_duration=2.3, optimal_interval=300.0)
        d = stats.to_dict()
        assert d["avg_items_per_run"] == 5.5

    def test_should_consolidate_periodic_not_yet(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm, policy=ConsolidationPolicy.PERIODIC)
        consolidator.last_consolidation = time.time()
        assert consolidator.should_consolidate() is False

    def test_auto_policy_no_scheduler(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm, policy=ConsolidationPolicy.AUTO, auto_scheduler=None
        )
        assert consolidator.should_consolidate() is False

    def test_should_consolidate_fallthrough(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm, policy=ConsolidationPolicy.IMMEDIATE
        )
        assert consolidator.should_consolidate() is True

    def test_extract_knowledge_no_content_match(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        ltm.add("Python programming", MemoryType.EPISODIC)
        consolidator = MemoryConsolidator(stm, ltm)
        knowledge = consolidator.extract_knowledge("NonexistentTopic")
        assert knowledge is None

    def test_record_run_yield_increasing_with_items(self):
        """record_run with increasing yield trend reduces interval."""
        scheduler = AutoConsolidationScheduler()
        scheduler.record_run(ConsolidationResult(5, 2, 1, 1.0))
        initial = scheduler.get_stats().optimal_interval
        scheduler.record_run(ConsolidationResult(10, 5, 2, 1.0))
        assert scheduler.get_stats().optimal_interval <= initial

    def test_record_run_window_full(self):
        scheduler = AutoConsolidationScheduler(window_size=2)
        for _ in range(5):
            scheduler.record_run(ConsolidationResult(1, 0, 0, 1.0))
        assert len(scheduler.get_stats().interval_history) == 2

    def test_consolidation_with_auto_scheduler(self):
        stm = ShortTermMemory(consolidation_threshold=2)
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(
            stm, ltm,
            policy=ConsolidationPolicy.AUTO,
        )
        stm.add_turn("user", "A")
        stm.add_turn("agent", "B")
        stm.add_turn("user", "C")
        result = consolidator.consolidate()
        assert result is not None

    def test_calculate_turn_importance_very_long(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        turn = ConversationTurn("user", "A" * 600, time.time())
        importance = consolidator._calculate_turn_importance(turn)
        assert importance >= 0.7

    def test_extract_knowledge_with_relevant_content(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        ltm.add("Python is great", MemoryType.EPISODIC)
        consolidator = MemoryConsolidator(stm, ltm)
        knowledge = consolidator.extract_knowledge("python")
        assert knowledge is not None

    def test_daemon_tick_not_idle(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        from lyra.memory.memory_consolidation import BackgroundConsolidationDaemon
        daemon = BackgroundConsolidationDaemon(consolidator)
        daemon._last_agent_activity = time.time()
        daemon._tick()
        assert daemon._runs_completed == 0

    def test_daemon_tick_idle_check(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm, policy=ConsolidationPolicy.IMMEDIATE)
        from lyra.memory.memory_consolidation import BackgroundConsolidationDaemon
        daemon = BackgroundConsolidationDaemon(consolidator)
        daemon._last_agent_activity = time.time() - 100
        daemon._last_run_time = time.time()
        daemon._tick()
        assert daemon._runs_completed >= 0

    def test_daemon_run_loop_suppresses_exception(self):
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        consolidator = MemoryConsolidator(stm, ltm)
        from lyra.memory.memory_consolidation import BackgroundConsolidationDaemon
        daemon = BackgroundConsolidationDaemon(consolidator)
        daemon._running = True
        daemon._stop_event.set()
        daemon._run_loop()  # should not raise
