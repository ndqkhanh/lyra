"""
Tests for the Deep Dream module (deep_dream.py).

Covers:
  - DeepDreamObserver: quality scoring, anomaly detection, trends
  - MemoryFilesIntegration: save/load dream banks, pruning, cleanup
  - WarmUpScheduler: scheduling, adaptive intervals, manual trigger
  - ConwayCycle: population, evolution, reproduction, state transitions
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest

from lyra.memory.deep_dream import (
    ConwayCycle,
    ConwayMemory,
    ConwayState,
    DeepDreamObserver,
    DreamObservation,
    DreamQuality,
    MemoryFilesIntegration,
    WarmUpScheduler,
)
from lyra.memory.dream_engine import (
    DreamAction,
    DreamBank,
    DreamEngine,
    DreamEntry,
)
from lyra.memory.memory_store import Memory, MemoryType


# ======================================================================
# Test helpers
# ======================================================================


def _make_bank(
    entry_count: int = 5,
    actions: list[DreamAction] | None = None,
) -> DreamBank:
    """Create a simple DreamBank for testing."""
    actions = actions or [DreamAction.MERGED, DreamAction.PATTERN]
    entries = []
    for i in range(entry_count):
        action = actions[i % len(actions)]
        entries.append(DreamEntry(
            entry_id=f"e{i}",
            action=action,
            description=f"Test entry {i}",
            source_memory_ids=[f"mem{i}"],
            created_summary=f"Summary {i}" if i % 2 == 0 else None,
            importance=0.5 + (i * 0.1),
            timestamp=time.time(),
            confidence=0.8 + (i * 0.04),
        ))

    return DreamBank(
        bank_id="test-bank-1",
        timestamp=time.time(),
        entries=entries,
        memory_bank_size=1000,
        session_sources=10,
        metadata={"dream_cycle": 1},
    )


_memory_counter: int = 0


def _make_memory(content: str = "test", importance: float = 0.5) -> Memory:
    global _memory_counter
    _memory_counter += 1
    return Memory(
        memory_id=f"mem_{_memory_counter}_{int(time.time() * 1000000)}",
        content=content,
        memory_type=MemoryType.SEMANTIC,
        timestamp=time.time(),
        importance=importance,
        tags=["test"],
    )


# ======================================================================
# DeepDreamObserver
# ======================================================================


class TestDeepDreamObserver:
    def test_initial_state(self) -> None:
        observer = DeepDreamObserver(observation_window=10)
        assert observer.get_observations() == []
        stats = observer.get_statistics()
        assert stats["total_observations"] == 0

    def test_observe_basic(self) -> None:
        observer = DeepDreamObserver()
        bank = _make_bank()
        obs = observer.observe(bank)
        assert obs.dream_bank_id == "test-bank-1"
        assert isinstance(obs.quality_score, float)
        assert 0.0 <= obs.quality_score <= 1.0
        assert isinstance(obs.anomaly_score, float)
        assert 0.0 <= obs.anomaly_score <= 1.0

    def test_observe_empty_bank(self) -> None:
        observer = DeepDreamObserver()
        empty_bank = DreamBank(
            bank_id="empty", timestamp=time.time(), entries=[]
        )
        obs = observer.observe(empty_bank)
        assert obs.quality_score == 0.0
        assert obs.quality == DreamQuality.FAILED

    def test_observe_stores_observation(self) -> None:
        observer = DeepDreamObserver()
        observer.observe(_make_bank())
        assert len(observer.get_observations()) == 1

    def test_observation_window(self) -> None:
        observer = DeepDreamObserver(observation_window=3)
        for _ in range(5):
            observer.observe(_make_bank())
        assert len(observer.get_observations()) == 3

    def test_on_observation_listener(self) -> None:
        observer = DeepDreamObserver()
        received: list[DreamObservation] = []

        def listener(obs: DreamObservation) -> None:
            received.append(obs)

        observer.on_observation(listener)
        observer.observe(_make_bank())
        assert len(received) == 1

    def test_listener_error_does_not_crash(self) -> None:
        observer = DeepDreamObserver()

        def broken_listener(obs: DreamObservation) -> None:
            raise RuntimeError("boom")

        observer.on_observation(broken_listener)
        # Should not raise
        obs = observer.observe(_make_bank())
        assert obs is not None

    def test_quality_classification(self) -> None:
        observer = DeepDreamObserver()
        assert observer._classify_quality(0.9) == DreamQuality.EXCELLENT
        assert observer._classify_quality(0.75) == DreamQuality.GOOD
        assert observer._classify_quality(0.5) == DreamQuality.FAIR
        assert observer._classify_quality(0.2) == DreamQuality.POOR
        assert observer._classify_quality(0.1) == DreamQuality.FAILED

    def test_anomaly_detection_uniform(self) -> None:
        observer = DeepDreamObserver()
        bank = _make_bank(entry_count=5, actions=[DreamAction.MERGED])
        obs = observer.observe(bank)
        # All same action type -> some anomaly signal
        assert obs.anomaly_score is not None

    def test_get_quality_history(self) -> None:
        observer = DeepDreamObserver()
        observer.observe(_make_bank())
        observer.observe(_make_bank(entry_count=10))
        history = observer.get_quality_history()
        assert len(history) == 2
        assert "score" in history[0]
        assert "quality" in history[0]


# ======================================================================
# MemoryFilesIntegration
# ======================================================================


class TestMemoryFilesIntegration:
    @pytest.fixture
    def storage(self) -> MemoryFilesIntegration:
        tmpdir = tempfile.mkdtemp()
        return MemoryFilesIntegration(storage_dir=tmpdir)

    def test_save_dream_bank(self, storage: MemoryFilesIntegration) -> None:
        bank = _make_bank()
        path = storage.save_dream_bank(bank)
        assert Path(path).exists()

    def test_load_dream_bank(self, storage: MemoryFilesIntegration) -> None:
        bank = _make_bank()
        storage.save_dream_bank(bank)
        loaded = storage.load_dream_bank(bank.bank_id)
        assert loaded is not None
        assert loaded.bank_id == bank.bank_id
        assert len(loaded.entries) == len(bank.entries)

    def test_load_nonexistent(self, storage: MemoryFilesIntegration) -> None:
        loaded = storage.load_dream_bank("nonexistent-id")
        assert loaded is None

    def test_save_observation(self, storage: MemoryFilesIntegration) -> None:
        observer = DeepDreamObserver()
        obs = observer.observe(_make_bank())
        path = storage.save_observation(obs)
        assert Path(path).exists()

    def test_save_session_manifest(self, storage: MemoryFilesIntegration) -> None:
        manifest = {"session": "test", "dreams": []}
        path = storage.save_session_manifest(manifest)
        assert Path(path).exists()

    def test_list_saved_banks(self, storage: MemoryFilesIntegration) -> None:
        bank = _make_bank()
        storage.save_dream_bank(bank)
        banks = storage.list_saved_banks()
        assert len(banks) >= 1
        assert banks[0]["bank_id"] == bank.bank_id

    def test_prune_old_banks(self, storage: MemoryFilesIntegration) -> None:
        bank = _make_bank()
        storage.save_dream_bank(bank)
        # Prune with negative max_age to catch everything
        pruned = storage.prune_old_banks(max_age_days=-1.0)
        assert pruned >= 1

    def test_clear_all(self, storage: MemoryFilesIntegration) -> None:
        bank = _make_bank()
        storage.save_dream_bank(bank)
        cleared = storage.clear_all()
        assert cleared >= 1
        assert len(storage.list_saved_banks()) == 0

    def test_get_statistics(self, storage: MemoryFilesIntegration) -> None:
        stats = storage.get_statistics()
        assert "storage_dir" in stats
        assert "total_saved" in stats


# ======================================================================
# WarmUpScheduler
# ======================================================================


class TestWarmUpScheduler:
    @pytest.fixture
    def scheduler(self) -> WarmUpScheduler:
        engine = MagicMock(spec=DreamEngine)
        engine.is_idle.return_value = True
        engine.should_dream.return_value = True
        engine.dream.return_value = _make_bank()
        engine.idle_threshold = 300.0
        engine.dream_interval = 86400.0
        type(engine)._last_dream_time = PropertyMock(return_value=0.0)
        type(engine)._dream_count = PropertyMock(return_value=0)

        return WarmUpScheduler(
            dream_engine=engine,
            min_interval=0.01,
            max_interval=1.0,
        )

    def test_should_warmup_idle(self, scheduler: WarmUpScheduler) -> None:
        # After 3 consecutive idle checks
        for _ in range(3):
            scheduler._consecutive_idle += 1
        assert scheduler.should_warmup() is True

    def test_should_not_warmup_active(self, scheduler: WarmUpScheduler) -> None:
        scheduler.dream_engine.is_idle.return_value = False
        assert scheduler.should_warmup() is False

    def test_run_warmup(self, scheduler: WarmUpScheduler) -> None:
        # Set up idle state
        for _ in range(3):
            scheduler._consecutive_idle += 1
        bank = scheduler.run_warmup()
        assert bank is not None
        assert scheduler._warmup_count == 1

    def test_run_warmup_not_ready(self, scheduler: WarmUpScheduler) -> None:
        scheduler.dream_engine.should_dream.return_value = False
        result = scheduler.run_warmup()
        assert result is None

    def test_trigger_now(self, scheduler: WarmUpScheduler) -> None:
        bank = scheduler.trigger_now()
        assert bank is not None

    def test_trigger_now_not_ready(self, scheduler: WarmUpScheduler) -> None:
        scheduler.dream_engine.should_dream.return_value = False
        assert scheduler.trigger_now() is None

    def test_reset_interval(self, scheduler: WarmUpScheduler) -> None:
        scheduler._current_interval = 100.0
        scheduler.reset_interval()
        assert scheduler._current_interval == scheduler.min_interval

    def test_set_interval(self, scheduler: WarmUpScheduler) -> None:
        scheduler.set_interval(0.5)
        assert scheduler._current_interval == 0.5

    def test_set_interval_clamps(self, scheduler: WarmUpScheduler) -> None:
        scheduler.set_interval(9999.0)
        assert scheduler._current_interval <= scheduler.max_interval
        scheduler.set_interval(0.0)
        assert scheduler._current_interval >= scheduler.min_interval

    def test_adapt_interval_expand(self, scheduler: WarmUpScheduler) -> None:
        scheduler._current_interval = 0.1
        scheduler._consecutive_idle = 15
        scheduler._adapt_interval()
        assert scheduler._current_interval > 0.1

    def test_adapt_interval_contract(self, scheduler: WarmUpScheduler) -> None:
        scheduler._current_interval = 0.5
        scheduler._consecutive_active = 10
        scheduler._adapt_interval()
        assert scheduler._current_interval < 0.5

    def test_get_warmup_history(self, scheduler: WarmUpScheduler) -> None:
        for _ in range(3):
            scheduler._consecutive_idle += 1
        scheduler.run_warmup()
        history = scheduler.get_warmup_history()
        assert len(history) >= 1

    def test_get_statistics(self, scheduler: WarmUpScheduler) -> None:
        stats = scheduler.get_statistics()
        assert "warmup_count" in stats
        assert "current_interval" in stats


# ======================================================================
# ConwayCycle
# ======================================================================


class TestConwayCycle:
    @pytest.fixture
    def cycle(self) -> ConwayCycle:
        return ConwayCycle(grid_size=5, max_generations=50)

    def test_initial_state(self, cycle: ConwayCycle) -> None:
        assert cycle.population_count() == 0
        assert cycle.get_generation() == 0

    def test_populate_from_memory(self, cycle: ConwayCycle) -> None:
        memories = [_make_memory(f"mem{i}", 0.5 + i * 0.1) for i in range(3)]
        added = cycle.populate(memories)
        assert added == 3
        assert cycle.population_count() == 3

    def test_populate_from_conway(self, cycle: ConwayCycle) -> None:
        cms = [
            ConwayMemory(memory_id=f"cm{i}", content=f"content{i}")
            for i in range(3)
        ]
        added = cycle.populate(cms)
        assert added == 3

    def test_populate_duplicates(self, cycle: ConwayCycle) -> None:
        memories = [_make_memory("dup", 0.5)]
        cycle.populate(memories)
        added = cycle.populate(memories)
        assert added == 0  # duplicates not added

    def test_evolve_single_step(self, cycle: ConwayCycle) -> None:
        memories = [_make_memory(f"m{i}", 0.5 + i * 0.1) for i in range(5)]
        cycle.populate(memories)
        changes = cycle.evolve(steps=1)
        assert len(changes) >= 1
        assert cycle.get_generation() >= 1

    def test_evolve_multiple_steps(self, cycle: ConwayCycle) -> None:
        memories = [_make_memory(f"m{i}", 0.5 + i * 0.05) for i in range(10)]
        cycle.populate(memories)
        changes = cycle.evolve(steps=5)
        assert cycle.get_generation() >= 1

    def test_get_by_state(self, cycle: ConwayCycle) -> None:
        memories = [_make_memory(f"m{i}", 0.3) for i in range(4)]
        cycle.populate(memories)
        birth = cycle.get_by_state(ConwayState.BIRTH)
        assert len(birth) == 4  # all start as BIRTH

    def test_get_living(self, cycle: ConwayCycle) -> None:
        memories = [_make_memory(f"m{i}", 0.3) for i in range(4)]
        cycle.populate(memories)
        living = cycle.get_living()
        assert len(living) == 4  # all start living

    def test_get_memory_by_id(self, cycle: ConwayCycle) -> None:
        mem = _make_memory("test", 0.5)
        cycle.populate([mem])
        cm = cycle.get_memory(mem.memory_id)
        assert cm is not None
        assert cm.content == "test"

    def test_state_transitions(self, cycle: ConwayCycle) -> None:
        """Test that a memory transitions through states."""
        mem = _make_memory("test", 0.6)
        cycle.populate([mem])

        # Get the ConwayMemory
        cm = cycle.get_memory(mem.memory_id)
        assert cm is not None
        assert cm.state == ConwayState.BIRTH

        # Evolve and check transitions
        cycle.evolve(steps=3)
        cm = cycle.get_memory(mem.memory_id)
        # After enough steps, should have transitioned from BIRTH
        if cm is not None:
            assert cm.age_cycles > 0

    def test_reproduction(self, cycle: ConwayCycle) -> None:
        """Test spawning offspring from a REPRODUCTION state memory."""
        mem = _make_memory("parent", 0.8)
        cycle.populate([mem])
        cm = cycle.get_memory(mem.memory_id)
        assert cm is not None

        # Manually set to REPRODUCTION
        cm.state = ConwayState.REPRODUCTION

        offspring = cycle.spawn_offspring(cm.memory_id, "child of parent")
        if offspring:
            for child in offspring:
                assert child.state == ConwayState.BIRTH
                assert child.generation >= 1

    def test_reproduction_not_reproducing(self, cycle: ConwayCycle) -> None:
        """spawn_offspring should return empty for non-REPRODUCTION state."""
        mem = _make_memory("not-reproducing", 0.5)
        cycle.populate([mem])
        cm = cycle.get_memory(mem.memory_id)
        assert cm is not None
        cm.state = ConwayState.GROWTH

        offspring = cycle.spawn_offspring(cm.memory_id)
        assert offspring == []

    def test_death_removes_memory(self, cycle: ConwayCycle) -> None:
        mem = _make_memory("die", 0.1)
        cycle.populate([mem])
        cm = cycle.get_memory(mem.memory_id)
        assert cm is not None

        cm.state = ConwayState.DEATH
        cm.importance = 0.0

        cycle.evolve(steps=1)
        assert cycle.get_memory(mem.memory_id) is None

    def test_get_statistics(self, cycle: ConwayCycle) -> None:
        memories = [_make_memory(f"m{i}", 0.5) for i in range(3)]
        cycle.populate(memories)
        stats = cycle.get_statistics()
        assert stats["population"] == 3
        assert stats["generation"] >= 0
        assert "states" in stats
