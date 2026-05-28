"""Tests for the MRAgent dual encoder."""
from __future__ import annotations

import pytest

from lyra_memory.mragent.dual_encoder import (
    DenseVector,
    DualEncodedMemory,
    DualEncoder,
    EncoderConfig,
    SparseVector,
)


class TestDenseVector:
    def test_create_dense_vector(self):
        dv = DenseVector(values=(1.0, 0.0, -1.0), dim=3)
        assert len(dv) == 3
        assert dv[0] == 1.0
        assert dv[2] == -1.0

    def test_dimension_mismatch_raises(self):
        with pytest.raises(ValueError, match="dimensions"):
            DenseVector(values=(1.0, 2.0), dim=3)

    def test_dot_product(self):
        a = DenseVector(values=(1.0, 0.0, 0.5), dim=3)
        b = DenseVector(values=(0.0, 2.0, 0.5), dim=3)
        assert a.dot(b) == pytest.approx(0.25)

    def test_dot_dimension_mismatch_raises(self):
        a = DenseVector(values=(1.0, 0.0), dim=2)
        b = DenseVector(values=(1.0, 0.0, 0.0), dim=3)
        with pytest.raises(ValueError, match="mismatch"):
            a.dot(b)

    def test_cosine_similarity_identical(self):
        a = DenseVector(values=(1.0, 2.0, 3.0), dim=3)
        assert a.cosine_similarity(a) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal(self):
        a = DenseVector(values=(1.0, 0.0, 0.0), dim=3)
        b = DenseVector(values=(0.0, 1.0, 0.0), dim=3)
        assert a.cosine_similarity(b) == pytest.approx(0.0)

    def test_cosine_similarity_zero_vector(self):
        a = DenseVector(values=(0.0, 0.0, 0.0), dim=3)
        b = DenseVector(values=(1.0, 0.0, 0.0), dim=3)
        assert a.cosine_similarity(b) == 0.0

    def test_l2_norm(self):
        dv = DenseVector(values=(3.0, 4.0), dim=2)
        assert dv.l2_norm() == pytest.approx(5.0)


class TestSparseVector:
    def test_create_sparse_vector(self):
        sv = SparseVector(indices=(0, 5, 10), values=(1.0, 0.5, 2.0), vocab_size=100)
        assert len(sv) == 3
        assert sv.indices[1] == 5
        assert sv.values[1] == 0.5

    def test_indices_values_length_mismatch(self):
        with pytest.raises(ValueError, match="same length"):
            SparseVector(indices=(0, 1), values=(1.0,), vocab_size=100)

    def test_dot_product(self):
        a = SparseVector(indices=(0, 2), values=(1.0, 0.5), vocab_size=10)
        b = SparseVector(indices=(0, 1, 2), values=(2.0, 3.0, 1.0), vocab_size=10)
        assert a.dot(b) == pytest.approx(2.0 + 0.5 * 1.0)

    def test_dot_product_disjoint(self):
        a = SparseVector(indices=(0, 1), values=(1.0, 2.0), vocab_size=10)
        b = SparseVector(indices=(2, 3), values=(3.0, 4.0), vocab_size=10)
        assert a.dot(b) == 0.0

    def test_to_dense(self):
        sv = SparseVector(indices=(0, 2), values=(1.0, 0.5), vocab_size=5)
        dense = sv.to_dense()
        assert dense == (1.0, 0.0, 0.5, 0.0, 0.0)

    def test_to_dense_out_of_bounds_ignored(self):
        sv = SparseVector(indices=(0, 99), values=(1.0, 0.5), vocab_size=5)
        dense = sv.to_dense()
        assert len(dense) == 5
        assert dense[0] == 1.0


class TestEncoderConfig:
    def test_defaults(self):
        cfg = EncoderConfig()
        assert cfg.dense_dim == 384
        assert cfg.sparse_vocab_size == 8192
        assert cfg.fusion_weight == 0.7

    def test_custom_config(self):
        cfg = EncoderConfig(dense_dim=128, fusion_weight=0.5)
        assert cfg.dense_dim == 128
        assert cfg.fusion_weight == 0.5


class TestDualEncoder:
    def test_encode_returns_dual_memory(self):
        encoder = DualEncoder()
        mem = encoder.encode("Hello world. This is a test memory.")
        assert isinstance(mem, DualEncodedMemory)
        assert mem.content == "Hello world. This is a test memory."
        assert len(mem.memory_id) > 0
        assert len(mem.dense) == encoder.config.dense_dim
        assert mem.timestamp > 0

    def test_encode_with_explicit_id(self):
        encoder = DualEncoder()
        mem = encoder.encode("test content", memory_id="custom-id-001")
        assert mem.memory_id == "custom-id-001"

    def test_encode_deterministic(self):
        encoder = DualEncoder()
        mem1 = encoder.encode("same content")
        mem2 = encoder.encode("same content")
        assert mem1.dense.values == mem2.dense.values
        assert mem1.sparse.indices == mem2.sparse.indices

    def test_encode_different_inputs_different_vectors(self):
        encoder = DualEncoder()
        mem1 = encoder.encode("completely different text here")
        mem2 = encoder.encode("another unique message text")
        assert mem1.dense.values != mem2.dense.values

    def test_dense_vector_is_unit_length(self):
        encoder = DualEncoder()
        mem = encoder.encode("test content for normalization check")
        norm = mem.dense.l2_norm()
        assert norm == pytest.approx(1.0, abs=1e-6)

    def test_sparse_vector_non_empty_for_text(self):
        encoder = DualEncoder()
        mem = encoder.encode("multiple words for token extraction testing")
        assert len(mem.sparse) > 0

    def test_sparse_vector_empty_for_no_words(self):
        encoder = DualEncoder()
        mem = encoder.encode("a i")
        assert len(mem.sparse) == 0

    def test_encode_batch(self):
        encoder = DualEncoder()
        texts = ["first memory", "second memory", "third memory"]
        mems = encoder.encode_batch(texts)
        assert len(mems) == 3
        assert all(isinstance(m, DualEncodedMemory) for m in mems)

    def test_hybrid_score_identical(self):
        encoder = DualEncoder()
        mem = encoder.encode("test memory content")
        score = encoder.hybrid_score(mem, mem)
        assert score == pytest.approx(1.0, abs=1e-6)

    def test_hybrid_score_different(self):
        encoder = DualEncoder()
        mem1 = encoder.encode("machine learning and AI research")
        mem2 = encoder.encode("cooking recipes and food preparation")
        score = encoder.hybrid_score(mem1, mem2)
        assert score < 0.5

    def test_retrieve_returns_top_k(self):
        encoder = DualEncoder()
        candidates = encoder.encode_batch(
            [
                "python programming language",
                "javascript web development",
                "python data science machine learning",
                "cooking and baking recipes",
                "python testing and debugging",
                "world history and geography",
            ]
        )
        query = encoder.encode("python coding and development")
        results = encoder.retrieve(query, candidates, top_k=3)
        assert len(results) == 3
        # All results should be DualEncodedMemory with valid scores
        for mem, score in results:
            assert isinstance(mem, DualEncodedMemory)
            assert 0.0 <= score <= 1.0

    def test_retrieve_scores_are_descending(self):
        encoder = DualEncoder()
        candidates = encoder.encode_batch(
            [f"topic number {i} for testing" for i in range(10)]
        )
        query = encoder.encode("topic number 5 for testing")
        results = encoder.retrieve(query, candidates, top_k=5)
        scores = [s for _, s in results]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]

    def test_to_dict(self):
        encoder = DualEncoder()
        mem = encoder.encode("test content")
        d = mem.to_dict()
        assert d["memory_id"] == mem.memory_id
        assert d["content"] == "test content"
        assert isinstance(d["dense_values"], list)
        assert isinstance(d["sparse_indices"], list)

    def test_custom_config_applied(self):
        cfg = EncoderConfig(dense_dim=64, fusion_weight=0.3)
        encoder = DualEncoder(config=cfg)
        mem = encoder.encode("test")
        assert len(mem.dense) == 64
        # fusion_weight=0.3 means sparse gets more weight
        mem2 = encoder.encode("test")
        score = encoder.hybrid_score(mem, mem2)
        assert score == pytest.approx(1.0, abs=1e-6)
