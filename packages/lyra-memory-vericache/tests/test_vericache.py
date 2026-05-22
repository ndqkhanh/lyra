"""Tests for lyra-memory-vericache."""
from lyra_memory_vericache import VeriCache


class TestVeriCache:
    def test_compress(self):
        vc = VeriCache()
        result = vc.compress({"key": "value", "nums": [1, 2, 3]}, [101, 102, 103])
        assert result.hash is not None
        assert result.compression_ratio > 0

    def test_verify_matches(self):
        vc = VeriCache()
        data = {"test": "data", "values": [42]}
        ckv = vc.compress(data, [1, 2])
        assert vc.verify(data, ckv)

    def test_verify_mismatch(self):
        vc = VeriCache()
        orig = {"a": 1}
        ckv = vc.compress(orig, [1])
        modified = {"a": 2}
        assert not vc.verify(modified, ckv)

    def test_speculative_draft(self):
        vc = VeriCache()
        ckv = vc.compress({"x": 1}, [10, 20, 30, 40, 50])
        draft = vc.speculative_draft(ckv, new_tokens=3)
        assert len(draft) == 3
        assert draft == [30, 40, 50]

    def test_stats(self):
        vc = VeriCache()
        vc.compress({"a": "test"}, [1])
        stats = vc.get_stats()
        assert stats["entries"] == 1
