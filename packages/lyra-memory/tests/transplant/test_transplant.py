"""Tests for TransplantRecord and MemoryTransplanter."""

from lyra_memory.modular.memory_module import ModularMemoryModule
from lyra_memory.transplant.transplant import MemoryTransplanter, TransplantRecord


class TestTransplantRecord:
    def test_default_values(self):
        tr = TransplantRecord(
            source_module="math",
            target_module="code",
            entry="some content",
            importance=0.6,
        )
        assert tr.source_module == "math"
        assert tr.target_module == "code"
        assert tr.entry == "some content"
        assert tr.importance == 0.6
        assert len(tr.id) > 0

    def test_unique_ids(self):
        tr1 = TransplantRecord(source_module="a", target_module="b", entry="x", importance=0.5)
        tr2 = TransplantRecord(source_module="a", target_module="b", entry="y", importance=0.5)
        assert tr1.id != tr2.id

    def test_timestamp_is_set(self):
        tr = TransplantRecord(source_module="a", target_module="b", entry="x", importance=0.5)
        assert len(tr.timestamp) > 0


class TestMemoryTransplanter:
    def _make_modules(self):
        src = ModularMemoryModule(name="src")
        for i in range(5):
            src.add(f"entry_{i}")
        tgt = ModularMemoryModule(name="tgt")
        tgt.add("target_initial")
        return src, tgt

    def test_initial_state(self):
        mt = MemoryTransplanter()
        assert mt.transplant_count == 0
        assert mt.history == []

    def test_transplant_moves_entries(self):
        mt = MemoryTransplanter()
        src, tgt = self._make_modules()
        records = mt.transplant(src, tgt, [0, 2])

        assert len(records) == 2
        assert tgt.size == 3
        assert mt.transplant_count == 2

    def test_transplant_record_fields(self):
        mt = MemoryTransplanter()
        src, tgt = self._make_modules()
        records = mt.transplant(src, tgt, [0], importance=0.8)

        assert records[0].source_module == "src"
        assert records[0].target_module == "tgt"
        assert records[0].entry == "entry_0"
        assert records[0].importance == 0.8

    def test_transplant_empty_indices(self):
        mt = MemoryTransplanter()
        src, tgt = self._make_modules()
        records = mt.transplant(src, tgt, [])
        assert records == []

    def test_transplant_adds_to_target(self):
        mt = MemoryTransplanter()
        src, tgt = self._make_modules()
        original_size = tgt.size
        mt.transplant(src, tgt, [0, 1])
        assert tgt.size == original_size + 2

    def test_history_preserves_order(self):
        mt = MemoryTransplanter()
        src, tgt = self._make_modules()
        mt.transplant(src, tgt, [0])
        mt.transplant(src, tgt, [1])
        assert mt.transplant_count == 2
        assert mt.history[0].entry == "entry_0"
        assert mt.history[1].entry == "entry_1"

    def test_recent_returns_last_n(self):
        mt = MemoryTransplanter()
        src, tgt = self._make_modules()
        mt.transplant(src, tgt, [0])
        mt.transplant(src, tgt, [1])
        mt.transplant(src, tgt, [2])

        recent = mt.recent(2)
        assert len(recent) == 2
        assert recent[0].entry == "entry_1"
        assert recent[1].entry == "entry_2"

    def test_recent_empty_history(self):
        mt = MemoryTransplanter()
        assert mt.recent(5) == []

    def test_clear_history(self):
        mt = MemoryTransplanter()
        src, tgt = self._make_modules()
        mt.transplant(src, tgt, [0])
        mt.clear_history()
        assert mt.transplant_count == 0

    def test_filter_by_source(self):
        mt = MemoryTransplanter()
        src1, tgt = self._make_modules()
        src2 = ModularMemoryModule(name="src2")
        src2.add("other_entry")
        mt.transplant(src1, tgt, [0])
        mt.transplant(src2, tgt, [0])

        filtered = mt.filter_by_source("src2")
        assert len(filtered) == 1
        assert filtered[0].source_module == "src2"

    def test_filter_by_target(self):
        mt = MemoryTransplanter()
        src, tgt1 = self._make_modules()
        ModularMemoryModule(name="tgt2")
        mt.transplant(src, tgt1, [0])
        mt.transplant(src, tgt1, [1])

        filtered = mt.filter_by_target("tgt")
        assert len(filtered) == 2

    def test_filter_returns_empty_when_no_match(self):
        mt = MemoryTransplanter()
        src, tgt = self._make_modules()
        mt.transplant(src, tgt, [0])
        assert mt.filter_by_source("nonexistent") == []
