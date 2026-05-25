"""Tests for InterferenceTracker and ModularMemoryModule."""

from lyra_memory.modular.memory_module import (
    InterferenceTracker,
    ModularMemoryModule,
)


class TestInterferenceTracker:
    def test_default_values(self):
        t = InterferenceTracker()
        assert t.overlap_ratio == 0.0
        assert t.update_magnitude == 0.0
        assert t.total_retrievals == 0
        assert t.total_updates == 0
        assert t.overlapping_retrievals == 0
        assert t.interference_bound == 0.0
        assert t.is_stable is True

    def test_is_stable_below_threshold(self):
        t = InterferenceTracker()
        t.overlap_ratio = 0.5
        t.update_magnitude = 0.4
        assert t.interference_bound == 0.2
        assert t.is_stable is True

    def test_is_stable_above_threshold(self):
        t = InterferenceTracker()
        t.overlap_ratio = 0.8
        t.update_magnitude = 0.5
        assert t.interference_bound == 0.4
        assert t.is_stable is False

    def test_is_stable_at_threshold(self):
        t = InterferenceTracker()
        t.overlap_ratio = 0.3
        t.update_magnitude = 1.0
        assert t.interference_bound == 0.3
        assert t.is_stable is True

    def test_record_update_first(self):
        t = InterferenceTracker()
        t.record_update(0.5)
        assert t.total_updates == 1
        assert t.update_magnitude == 0.5

    def test_record_update_average(self):
        t = InterferenceTracker()
        t.record_update(0.2)
        t.record_update(0.6)
        assert t.total_updates == 2
        assert t.update_magnitude == 0.4

    def test_record_retrieval_no_overlap(self):
        t = InterferenceTracker()
        t.record_retrieval(overlaps_update=False)
        assert t.total_retrievals == 1
        assert t.overlapping_retrievals == 0
        assert t.overlap_ratio == 0.0

    def test_record_retrieval_with_overlap(self):
        t = InterferenceTracker()
        t.record_retrieval(overlaps_update=True)
        assert t.total_retrievals == 1
        assert t.overlapping_retrievals == 1
        assert t.overlap_ratio == 1.0

    def test_record_retrieval_mixed(self):
        t = InterferenceTracker()
        t.record_retrieval(True)
        t.record_retrieval(False)
        t.record_retrieval(True)
        assert t.total_retrievals == 3
        assert t.overlapping_retrievals == 2
        assert t.overlap_ratio == 2 / 3

    def test_set_threshold(self):
        t = InterferenceTracker()
        t.set_threshold(0.5)
        assert t._stability_threshold == 0.5

    def test_set_threshold_clamped_low(self):
        t = InterferenceTracker()
        t.set_threshold(0.0)
        assert t._stability_threshold == 0.01

    def test_set_threshold_clamped_high(self):
        t = InterferenceTracker()
        t.set_threshold(2.0)
        assert t._stability_threshold == 1.0

    def test_zero_update_magnitude_stable(self):
        t = InterferenceTracker()
        t.overlap_ratio = 1.0
        assert t.interference_bound == 0.0
        assert t.is_stable is True


class TestModularMemoryModule:
    def test_default_values(self):
        m = ModularMemoryModule(name="test")
        assert m.name == "test"
        assert m.entries == []
        assert m.size == 0
        assert m.version == 0

    def test_add_returns_id(self):
        m = ModularMemoryModule(name="test")
        entry_id = m.add("hello world")
        assert isinstance(entry_id, str)
        assert len(entry_id) > 0

    def test_add_increases_size(self):
        m = ModularMemoryModule(name="test")
        m.add("entry one")
        m.add("entry two")
        assert m.size == 2
        assert m.version == 2

    def test_add_tracks_interference(self):
        m = ModularMemoryModule(name="test")
        m.add("a" * 2000)
        assert m.interference.total_updates == 1
        assert m.interference.update_magnitude > 0

    def test_retrieve_by_index(self):
        m = ModularMemoryModule(name="test")
        m.add("zero")
        m.add("one")
        m.add("two")
        results = m.retrieve([0, 2])
        assert results == ["zero", "two"]

    def test_retrieve_out_of_bounds(self):
        m = ModularMemoryModule(name="test")
        m.add("zero")
        results = m.retrieve([-1, 0, 5])
        assert results == ["zero"]

    def test_retrieve_records_overlap(self):
        m = ModularMemoryModule(name="test")
        m.add("zero")
        m.add("one")
        m.retrieve([1])
        assert m.interference.total_retrievals == 1

    def test_compress_keeps_top_entries(self):
        m = ModularMemoryModule(name="test")
        for i in range(10):
            m.add(f"entry_{i}")
        removed = m.compress(keep_fraction=0.5)
        assert removed == 5
        assert m.size == 5
        assert m.entries == [f"entry_{i}" for i in range(5)]

    def test_compress_min_one_entry(self):
        m = ModularMemoryModule(name="test")
        m.add("only")
        removed = m.compress(keep_fraction=0.1)
        assert removed == 0
        assert m.size == 1

    def test_compress_tracks_update(self):
        m = ModularMemoryModule(name="test")
        for i in range(5):
            m.add(f"entry_{i}")
        m.compress(keep_fraction=0.6)
        assert m.interference.total_updates > 0

    def test_unique_id_per_module(self):
        m1 = ModularMemoryModule(name="a")
        m2 = ModularMemoryModule(name="b")
        assert m1.id != m2.id

    def test_retrieve_empty_module(self):
        m = ModularMemoryModule(name="test")
        assert m.retrieve([0]) == []

    def test_compress_empty_module(self):
        m = ModularMemoryModule(name="test")
        removed = m.compress(keep_fraction=0.5)
        assert removed == 0
