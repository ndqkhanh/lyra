"""Comprehensive tests for lyra-recursive-link package (80+ tests)."""

from __future__ import annotations

import math

import numpy as np
import pytest
from lyra_recursive_link import (
    AggregationMethod,
    BusConfig,
    BusError,
    BusMessage,
    BusStats,
    CollaborationConfig,
    CollaborationEngine,
    CollaborationError,
    CollaborationPattern,
    CommunicationBus,
    CompressionMethod,
    ContributionRecord,
    CreditAssignmentEngine,
    CreditAssignmentError,
    CreditConfig,
    CreditLedger,
    CreditScore,
    DecodedMessage,
    DecodingConfig,
    DecodingError,
    DeliberationResult,
    DistillationResult,
    EncodingConfig,
    EncodingError,
    InnerLoopResult,
    LatentDecoder,
    LatentEncoder,
    LatentVector,
    LinkConfig,
    LinkError,
    LinkMetrics,
    MessageDeliveryError,
    MessagePriority,
    MixtureResult,
    RecursiveLink,
    SequentialResult,
    Subscription,
    compute_compression_ratio,
    compute_fidelity,
    convergence_check,
    similarity,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def encoder() -> LatentEncoder:
    return LatentEncoder()


@pytest.fixture
def encoder_pca() -> LatentEncoder:
    cfg = EncodingConfig(
        target_dimension=8, compression_method=CompressionMethod.PCA
    )
    enc = LatentEncoder(default_config=cfg)
    enc.encode("this is the first document for pca fitting")
    enc.encode("the second document has different content entirely")
    enc.encode("a third document about machine learning topics")
    enc.fit()
    return enc


@pytest.fixture
def encoder_rp() -> LatentEncoder:
    cfg = EncodingConfig(
        target_dimension=8, compression_method=CompressionMethod.RANDOM_PROJECTION
    )
    return LatentEncoder(default_config=cfg)


@pytest.fixture
def decoder(encoder: LatentEncoder) -> LatentDecoder:
    return LatentDecoder(encoder)


@pytest.fixture
def sample_vector() -> LatentVector:
    return LatentVector(
        vector=np.array([0.5, -0.3, 0.8, 0.1], dtype=np.float64),
        original_length=32,
        compressed_length=4,
        compression_ratio=0.875,
        semantic_hash="abc123def456",
    )


@pytest.fixture
def sample_vectors() -> list[LatentVector]:
    return [
        LatentVector(
            vector=np.array([0.5, -0.3, 0.8], dtype=np.float64),
            original_length=20,
            compressed_length=3,
            compression_ratio=0.85,
            semantic_hash="hash_a",
        ),
        LatentVector(
            vector=np.array([-0.2, 0.7, 0.1], dtype=np.float64),
            original_length=20,
            compressed_length=3,
            compression_ratio=0.85,
            semantic_hash="hash_b",
        ),
        LatentVector(
            vector=np.array([0.9, -0.1, -0.5], dtype=np.float64),
            original_length=20,
            compressed_length=3,
            compression_ratio=0.85,
            semantic_hash="hash_c",
        ),
    ]


@pytest.fixture
def link() -> RecursiveLink:
    return RecursiveLink()


@pytest.fixture
def credit_engine() -> CreditAssignmentEngine:
    return CreditAssignmentEngine()


@pytest.fixture
def ledger() -> CreditLedger:
    return CreditLedger()


@pytest.fixture
def collab_engine() -> CollaborationEngine:
    return CollaborationEngine()


@pytest.fixture
def bus() -> CommunicationBus:
    return CommunicationBus()


# =============================================================================
# Exceptions
# =============================================================================


class TestExceptions:
    def test_encoding_error(self) -> None:
        with pytest.raises(EncodingError):
            raise EncodingError("test encoding error")

    def test_decoding_error(self) -> None:
        with pytest.raises(DecodingError):
            raise DecodingError("test decoding error")

    def test_link_error(self) -> None:
        with pytest.raises(LinkError):
            raise LinkError("test link error")

    def test_credit_assignment_error(self) -> None:
        with pytest.raises(CreditAssignmentError):
            raise CreditAssignmentError("test credit error")

    def test_collaboration_error(self) -> None:
        with pytest.raises(CollaborationError):
            raise CollaborationError("test collaboration error")

    def test_bus_error(self) -> None:
        with pytest.raises(BusError):
            raise BusError("test bus error")

    def test_message_delivery_error(self) -> None:
        with pytest.raises(MessageDeliveryError):
            raise MessageDeliveryError("test delivery error")

    def test_message_delivery_is_bus_error(self) -> None:
        assert issubclass(MessageDeliveryError, BusError)


# =============================================================================
# LatentEncoder
# =============================================================================


class TestLatentEncoder:
    def test_encode_returns_latent_vector(self, encoder: LatentEncoder) -> None:
        result = encoder.encode("hello world")
        assert isinstance(result, LatentVector)
        assert isinstance(result.vector, np.ndarray)
        assert result.original_length > 0
        assert result.compressed_length > 0
        assert isinstance(result.semantic_hash, str)

    def test_encode_default_config(self, encoder: LatentEncoder) -> None:
        result = encoder.encode("test message")
        assert result.compressed_length == 16

    def test_encode_custom_dimension(self) -> None:
        cfg = EncodingConfig(target_dimension=4)
        enc = LatentEncoder(default_config=cfg)
        result = enc.encode("test message")
        assert result.compressed_length == 4

    def test_encode_random_projection(self, encoder_rp: LatentEncoder) -> None:
        result = encoder_rp.encode("test random projection")
        assert isinstance(result, LatentVector)

    def test_encode_pca(self, encoder_pca: LatentEncoder) -> None:
        result = encoder_pca.encode("new document for pca encoding")
        assert isinstance(result, LatentVector)

    def test_encode_semantic_hash(self) -> None:
        cfg = EncodingConfig(
            target_dimension=8, compression_method=CompressionMethod.SEMANTIC_HASH
        )
        enc = LatentEncoder(default_config=cfg)
        result = enc.encode("semantic hashing test message")
        assert isinstance(result, LatentVector)
        assert len(result.vector) == 8

    def test_encode_quantized(self) -> None:
        cfg = EncodingConfig(
            target_dimension=8, compression_method=CompressionMethod.QUANTIZED
        )
        enc = LatentEncoder(default_config=cfg)
        result = enc.encode("quantized compression test")
        assert isinstance(result, LatentVector)
        assert len(result.vector) == 8

    def test_batch_encode(self, encoder: LatentEncoder) -> None:
        texts = ["first message", "second message", "third message"]
        results = encoder.batch_encode(texts)
        assert len(results) == 3
        assert all(isinstance(r, LatentVector) for r in results)

    def test_batch_encode_empty(self, encoder: LatentEncoder) -> None:
        results = encoder.batch_encode([])
        assert results == []

    def test_compute_compression_ratio(self) -> None:
        ratio = compute_compression_ratio(100, 25)
        assert math.isclose(ratio, 0.75)

        ratio_equal = compute_compression_ratio(25, 25)
        assert ratio_equal == 0.0

        ratio_zero = compute_compression_ratio(0, 10)
        assert ratio_zero == 0.0

        ratio_larger_dim = compute_compression_ratio(5, 10)
        assert ratio_larger_dim == 0.0

    def test_similarity(self, sample_vectors: list[LatentVector]) -> None:
        sim = similarity(sample_vectors[0], sample_vectors[0])
        assert math.isclose(sim, 1.0, abs_tol=0.01)

    def test_similarity_orthogonal(self) -> None:
        a = LatentVector(
            vector=np.array([1.0, 0.0, 0.0], dtype=np.float64),
            original_length=10, compressed_length=3,
            compression_ratio=0.7, semantic_hash="a",
        )
        b = LatentVector(
            vector=np.array([0.0, 1.0, 0.0], dtype=np.float64),
            original_length=10, compressed_length=3,
            compression_ratio=0.7, semantic_hash="b",
        )
        sim = similarity(a, b)
        assert math.isclose(sim, 0.0, abs_tol=0.01)

    def test_similarity_zero_vector(self) -> None:
        a = LatentVector(
            vector=np.array([0.0, 0.0, 0.0], dtype=np.float64),
            original_length=10, compressed_length=3,
            compression_ratio=0.7, semantic_hash="a",
        )
        b = LatentVector(
            vector=np.array([1.0, 0.0, 0.0], dtype=np.float64),
            original_length=10, compressed_length=3,
            compression_ratio=0.7, semantic_hash="b",
        )
        sim = similarity(a, b)
        assert sim == 0.0

    def test_similarity_dimension_mismatch(self) -> None:
        a = LatentVector(
            vector=np.array([1.0, 0.0], dtype=np.float64),
            original_length=10, compressed_length=2,
            compression_ratio=0.8, semantic_hash="a",
        )
        b = LatentVector(
            vector=np.array([1.0, 0.0, 0.0], dtype=np.float64),
            original_length=10, compressed_length=3,
            compression_ratio=0.7, semantic_hash="b",
        )
        with pytest.raises(ValueError, match="different dimensions"):
            similarity(a, b)

    def test_similarity_different_vectors(
        self, sample_vectors: list[LatentVector]
    ) -> None:
        sim = similarity(sample_vectors[0], sample_vectors[1])
        assert -1.0 <= sim <= 1.0

    def test_encode_without_vocabulary(self) -> None:
        encoder = LatentEncoder()
        result = encoder.encode("test message to build vocabulary")
        assert isinstance(result, LatentVector)

    def test_compression_ratio_on_encoded(self, encoder: LatentEncoder) -> None:
        encoder.encode("a b c d e f g h i j")
        result = encoder.encode("a b c d e f g h i j k l m n o p")
        assert result.compression_ratio >= 0.0

    def test_get_key_terms(self, encoder: LatentEncoder) -> None:
        terms = encoder.get_key_terms("machine learning deep learning")
        assert isinstance(terms, list)
        assert len(terms) > 0

    def test_encode_same_text_same_hash(self, encoder: LatentEncoder) -> None:
        a = encoder.encode("consistent test message one two three")
        b = encoder.encode("consistent test message one two three")
        assert a.semantic_hash == b.semantic_hash

    def test_encode_different_text_different_hash(self, encoder: LatentEncoder) -> None:
        a = encoder.encode("hello world")
        b = encoder.encode("goodbye world")
        assert a.semantic_hash != b.semantic_hash

    def test_vocabulary_grows(self, encoder: LatentEncoder) -> None:
        initial_size = len(encoder.vocabulary)
        encoder.encode("unique_new_word_xkcd")
        assert len(encoder.vocabulary) > initial_size


# =============================================================================
# LatentDecoder
# =============================================================================


class TestLatentDecoder:
    def test_decode_returns_decoded_message(
        self, encoder: LatentEncoder, decoder: LatentDecoder
    ) -> None:
        vec = encoder.encode("decode this message")
        result = decoder.decode(vec)
        assert isinstance(result, DecodedMessage)
        assert isinstance(result.text, str)
        assert isinstance(result.confidence, float)
        assert isinstance(result.semantic_fidelity, float)
        assert isinstance(result.key_terms, tuple)

    def test_decode_default_config(
        self, encoder: LatentEncoder, decoder: LatentDecoder
    ) -> None:
        vec = encoder.encode("test decoding")
        result = decoder.decode(vec)
        assert 0.0 <= result.confidence <= 1.0

    def test_decode_custom_config(
        self, encoder: LatentEncoder, decoder: LatentDecoder
    ) -> None:
        vec = encoder.encode("test decoding with custom config")
        cfg = DecodingConfig(fidelity_threshold=0.8, max_tokens=10)
        result = decoder.decode(vec, cfg)
        assert isinstance(result, DecodedMessage)

    def test_decode_empty_vector(
        self, encoder: LatentEncoder, decoder: LatentDecoder
    ) -> None:
        empty_vec = LatentVector(
            vector=np.array([], dtype=np.float64),
            original_length=0, compressed_length=0,
            compression_ratio=0.0, semantic_hash="empty",
        )
        with pytest.raises(DecodingError):
            decoder.decode(empty_vec)

    def test_batch_decode(
        self, encoder: LatentEncoder, decoder: LatentDecoder
    ) -> None:
        vectors = encoder.batch_encode(["first", "second", "third"])
        results = decoder.batch_decode(vectors)
        assert len(results) == 3
        assert all(isinstance(r, DecodedMessage) for r in results)

    def test_batch_decode_empty(self, decoder: LatentDecoder) -> None:
        results = decoder.batch_decode([])
        assert results == []

    def test_compute_fidelity_perfect(self) -> None:
        fid = compute_fidelity("hello world", "hello world")
        assert math.isclose(fid, 1.0, abs_tol=0.01)

    def test_compute_fidelity_partial(self) -> None:
        fid = compute_fidelity("hello world", "hello there")
        assert 0.0 < fid < 1.0

    def test_compute_fidelity_no_match(self) -> None:
        fid = compute_fidelity("hello world", "foo bar baz")
        assert fid == 0.0

    def test_compute_fidelity_both_empty(self) -> None:
        fid = compute_fidelity("", "")
        assert fid == 1.0

    def test_compute_fidelity_one_empty(self) -> None:
        fid = compute_fidelity("hello", "")
        assert fid == 0.0

    def test_compute_fidelity_with_lists(self) -> None:
        fid = compute_fidelity(["hello", "world"], ["hello", "there"])
        assert 0.0 < fid < 1.0

    def test_recover_key_terms(
        self, encoder: LatentEncoder, decoder: LatentDecoder
    ) -> None:
        encoder.encode("machine learning deep neural network")
        encoder.encode("artificial intelligence neural network")
        vec = encoder.encode("deep learning neural network")
        terms = decoder.recover_key_terms(vec)
        assert isinstance(terms, list)

    def test_confidence_is_bounded(
        self, encoder: LatentEncoder, decoder: LatentDecoder
    ) -> None:
        vec = encoder.encode("test message for confidence")
        result = decoder.decode(vec)
        assert 0.0 <= result.confidence <= 1.0
        assert 0.0 <= result.semantic_fidelity <= 1.0

    def test_decoded_message_key_terms(
        self, encoder: LatentEncoder, decoder: LatentDecoder
    ) -> None:
        encoder.encode("machine learning deep learning topics")
        vec = encoder.encode("deep learning neural networks")
        result = decoder.decode(vec)
        assert len(result.key_terms) > 0


# =============================================================================
# RecursiveLink
# =============================================================================


class TestRecursiveLink:
    def test_forward_mean(
        self, link: RecursiveLink, sample_vectors: list[LatentVector]
    ) -> None:
        result = link.forward(sample_vectors)
        assert isinstance(result, LatentVector)
        assert len(result.vector) == 3

    def test_forward_single_message(
        self, link: RecursiveLink, sample_vector: LatentVector
    ) -> None:
        result = link.forward([sample_vector])
        assert result == sample_vector

    def test_forward_max(
        self, link: RecursiveLink, sample_vectors: list[LatentVector]
    ) -> None:
        cfg = LinkConfig(aggregation_method=AggregationMethod.MAX)
        result = link.forward(sample_vectors, cfg)
        assert isinstance(result, LatentVector)

    def test_forward_attention(
        self, link: RecursiveLink, sample_vectors: list[LatentVector]
    ) -> None:
        cfg = LinkConfig(
            aggregation_method=AggregationMethod.ATTENTION,
            attention_temperature=0.5,
        )
        result = link.forward(sample_vectors, cfg)
        assert isinstance(result, LatentVector)

    def test_forward_weighted_sum(
        self, link: RecursiveLink, sample_vectors: list[LatentVector]
    ) -> None:
        cfg = LinkConfig(aggregation_method=AggregationMethod.WEIGHTED_SUM)
        result = link.forward(sample_vectors, cfg)
        assert isinstance(result, LatentVector)

    def test_forward_empty(self, link: RecursiveLink) -> None:
        with pytest.raises(LinkError, match="empty"):
            link.forward([])

    def test_forward_dimension_mismatch(
        self, link: RecursiveLink, sample_vector: LatentVector
    ) -> None:
        bad = LatentVector(
            vector=np.array([1.0, 2.0], dtype=np.float64),
            original_length=10, compressed_length=2,
            compression_ratio=0.8, semantic_hash="bad",
        )
        with pytest.raises(LinkError, match="same latent dimension"):
            link.forward([sample_vector, bad])

    def test_call_magic(
        self, link: RecursiveLink, sample_vectors: list[LatentVector]
    ) -> None:
        result = link(sample_vectors)
        assert isinstance(result, LatentVector)

    def test_residual_link(
        self, link: RecursiveLink, sample_vectors: list[LatentVector]
    ) -> None:
        original = sample_vectors[0]
        result = link.residual_link(original, sample_vectors[1].vector)
        assert isinstance(result, LatentVector)
        assert len(result.vector) == len(original.vector)

    def test_residual_link_with_latent_vector(
        self, link: RecursiveLink, sample_vectors: list[LatentVector]
    ) -> None:
        original = sample_vectors[0]
        result = link.residual_link(original, sample_vectors[1])
        assert isinstance(result, LatentVector)

    def test_multi_hop(
        self, link: RecursiveLink, sample_vectors: list[LatentVector]
    ) -> None:
        agents = [[v] for v in sample_vectors]
        results = link.multi_hop(agents, hops=2)
        assert len(results) == 3
        assert all(isinstance(r, LatentVector) for r in results)

    def test_multi_hop_invalid_hops(
        self, link: RecursiveLink, sample_vectors: list[LatentVector]
    ) -> None:
        agents = [[v] for v in sample_vectors]
        with pytest.raises(LinkError, match="hops must be at least"):
            link.multi_hop(agents, hops=0)

    def test_multi_hop_empty(self, link: RecursiveLink) -> None:
        with pytest.raises(LinkError, match="empty agents"):
            link.multi_hop([], hops=2)

    def test_compute_metrics(
        self, link: RecursiveLink, sample_vectors: list[LatentVector]
    ) -> None:
        aggregated = link.forward(sample_vectors)
        metrics = link.compute_metrics(sample_vectors, aggregated, hop_count=2)
        assert isinstance(metrics, LinkMetrics)
        assert metrics.hop_count == 2
        assert metrics.num_messages == len(sample_vectors)
        assert 0.0 <= metrics.compression_achieved <= 1.0

    def test_compute_metrics_empty(self, link: RecursiveLink) -> None:
        vec = LatentVector(
            vector=np.array([1.0], dtype=np.float64),
            original_length=5, compressed_length=1,
            compression_ratio=0.8, semantic_hash="x",
        )
        metrics = link.compute_metrics([], vec, hop_count=0)
        assert metrics.num_messages == 0
        assert metrics.hop_count == 0

    def test_forward_residual_disabled(
        self, link: RecursiveLink, sample_vectors: list[LatentVector]
    ) -> None:
        cfg = LinkConfig(
            aggregation_method=AggregationMethod.MEAN, residual_connection=False
        )
        result = link.forward(sample_vectors, cfg)
        assert isinstance(result, LatentVector)

    def test_forward_attention_single_message(
        self, link: RecursiveLink, sample_vector: LatentVector
    ) -> None:
        cfg = LinkConfig(aggregation_method=AggregationMethod.ATTENTION)
        result = link.forward([sample_vector], cfg)
        assert isinstance(result, LatentVector)

    def test_link_config_default(self) -> None:
        cfg = LinkConfig()
        assert cfg.depth == 1
        assert cfg.aggregation_method == AggregationMethod.MEAN
        assert cfg.residual_connection is True

    def test_link_config_custom(self) -> None:
        cfg = LinkConfig(
            depth=3,
            aggregation_method=AggregationMethod.ATTENTION,
            residual_connection=False,
            attention_temperature=2.0,
        )
        assert cfg.depth == 3
        assert cfg.aggregation_method == AggregationMethod.ATTENTION
        assert cfg.attention_temperature == 2.0


# =============================================================================
# CreditAssignment
# =============================================================================


class TestCreditAssignment:
    def test_assign_credit(
        self, credit_engine: CreditAssignmentEngine, sample_vectors: list[LatentVector]
    ) -> None:
        trajectory = [("agent_a", sample_vectors[0]), ("agent_b", sample_vectors[1])]
        scores = credit_engine.assign_credit(trajectory, sample_vectors[0])
        assert len(scores) == 2
        assert all(isinstance(s, CreditScore) for s in scores)
        assert all(isinstance(s.agent_id, str) for s in scores)
        assert all(-1.0 <= s.contribution_score <= 1.0 for s in scores)

    def test_assign_credit_empty(self, credit_engine: CreditAssignmentEngine) -> None:
        vec = LatentVector(
            vector=np.array([1.0], dtype=np.float64),
            original_length=5, compressed_length=1,
            compression_ratio=0.8, semantic_hash="x",
        )
        with pytest.raises(CreditAssignmentError):
            credit_engine.assign_credit([], vec)

    def test_assign_credit_returns_confidence(
        self, credit_engine: CreditAssignmentEngine, sample_vectors: list[LatentVector]
    ) -> None:
        trajectory = [("agent_a", sample_vectors[0])]
        scores = credit_engine.assign_credit(trajectory, sample_vectors[0])
        assert len(scores) == 1
        assert 0.0 <= scores[0].confidence <= 1.0

    def test_assign_credit_evidence(
        self, credit_engine: CreditAssignmentEngine, sample_vectors: list[LatentVector]
    ) -> None:
        trajectory = [("agent_a", sample_vectors[0])]
        scores = credit_engine.assign_credit(trajectory, sample_vectors[0])
        assert len(scores[0].evidence) > 0

    def test_inner_loop(
        self, credit_engine: CreditAssignmentEngine, sample_vectors: list[LatentVector]
    ) -> None:
        agents = [("a", sample_vectors[0]), ("b", sample_vectors[1])]
        result = credit_engine.inner_loop(agents, sample_vectors[0])
        assert isinstance(result, InnerLoopResult)
        assert len(result.agent_scores) == 2

    def test_inner_loop_convergence(
        self, credit_engine: CreditAssignmentEngine, sample_vectors: list[LatentVector]
    ) -> None:
        agents = [
            ("a", sample_vectors[0]),
            ("b", sample_vectors[1]),
            ("c", sample_vectors[2]),
        ]
        result = credit_engine.inner_loop(agents, sample_vectors[0])
        assert result.convergence_metric >= 0.0
        assert result.iterations == 10

    def test_inner_loop_empty(self, credit_engine: CreditAssignmentEngine) -> None:
        vec = LatentVector(
            vector=np.array([1.0], dtype=np.float64),
            original_length=5, compressed_length=1,
            compression_ratio=0.8, semantic_hash="x",
        )
        with pytest.raises(CreditAssignmentError):
            credit_engine.inner_loop([], vec)

    def test_credit_config_default(self) -> None:
        cfg = CreditConfig()
        assert cfg.inner_iterations == 10
        assert cfg.learning_rate == 0.1
        assert cfg.decay == 0.95

    def test_credit_config_custom(self) -> None:
        cfg = CreditConfig(
            inner_iterations=5, outer_iterations=2, learning_rate=0.01, decay=0.9
        )
        assert cfg.inner_iterations == 5
        assert cfg.outer_iterations == 2
        assert cfg.learning_rate == 0.01
        assert cfg.decay == 0.9

    def test_credit_score_dataclass(self) -> None:
        score = CreditScore(
            agent_id="agent_a",
            contribution_score=0.85,
            confidence=0.9,
            evidence=("metric_a=0.8",),
        )
        assert score.agent_id == "agent_a"
        assert math.isclose(score.contribution_score, 0.85)

    def test_contribution_record_dataclass(self) -> None:
        record = ContributionRecord(
            agent_id="agent_a", action="encode", impact_score=0.75, timestamp=1000.0
        )
        assert record.agent_id == "agent_a"
        assert record.action == "encode"

    def test_inner_loop_result_dataclass(self) -> None:
        result = InnerLoopResult(
            agent_scores=(("a", 0.9), ("b", 0.1)),
            convergence_metric=0.05,
            iterations=5,
        )
        assert len(result.agent_scores) == 2
        assert result.iterations == 5


class TestCreditLedger:
    def test_record_and_get_history(
        self, ledger: CreditLedger
    ) -> None:
        scores = [
            CreditScore("agent_a", 0.9, 0.95, ("ev1",)),
            CreditScore("agent_b", 0.7, 0.80, ("ev2",)),
        ]
        ledger.record("ep_1", scores)
        history = ledger.get_agent_history("agent_a")
        assert len(history) == 1
        assert history[0].contribution_score == 0.9

    def test_record_empty_raises(self, ledger: CreditLedger) -> None:
        with pytest.raises(CreditAssignmentError):
            ledger.record("ep_1", [])

    def test_get_top_contributors(
        self, ledger: CreditLedger
    ) -> None:
        scores = [
            CreditScore("agent_a", 0.5, 0.6, ("ev1",)),
            CreditScore("agent_b", 0.9, 0.95, ("ev2",)),
            CreditScore("agent_c", 0.3, 0.4, ("ev3",)),
        ]
        ledger.record("ep_1", scores)
        top = ledger.get_top_contributors("ep_1", top_k=2)
        assert len(top) == 2
        assert top[0].agent_id == "agent_b"

    def test_get_top_contributors_nonexistent(
        self, ledger: CreditLedger
    ) -> None:
        top = ledger.get_top_contributors("fake_ep", top_k=3)
        assert top == []

    def test_get_history_nonexistent(self, ledger: CreditLedger) -> None:
        history = ledger.get_agent_history("nonexistent")
        assert history == []

    def test_multiple_episodes(
        self, ledger: CreditLedger
    ) -> None:
        ledger.record("ep_1", [CreditScore("agent_a", 0.9, 0.95, ("ev1",))])
        ledger.record("ep_2", [CreditScore("agent_a", 0.8, 0.85, ("ev2",))])
        history = ledger.get_agent_history("agent_a")
        assert len(history) == 2

    def test_get_all_episodes(
        self, ledger: CreditLedger
    ) -> None:
        ledger.record("ep_1", [CreditScore("agent_a", 0.9, 0.95, ("ev1",))])
        ledger.record("ep_2", [CreditScore("agent_b", 0.7, 0.80, ("ev2",))])
        episodes = ledger.get_all_episodes()
        assert len(episodes) == 2
        assert "ep_1" in episodes
        assert "ep_2" in episodes

    def test_clear(self, ledger: CreditLedger) -> None:
        ledger.record("ep_1", [CreditScore("agent_a", 0.9, 0.95, ("ev1",))])
        ledger.clear()
        assert ledger.get_agent_history("agent_a") == []
        assert ledger.get_all_episodes() == {}


# =============================================================================
# CollaborationPatterns
# =============================================================================


class TestCollaborationPatterns:
    def test_mixture_pattern(
        self,
        collab_engine: CollaborationEngine,
        sample_vectors: list[LatentVector],
    ) -> None:
        config = CollaborationConfig(
            pattern=CollaborationPattern.MIXTURE,
            agents=("specialist_a", "specialist_b", "specialist_c"),
        )
        latents = {
            "specialist_a": sample_vectors[0],
            "specialist_b": sample_vectors[1],
            "specialist_c": sample_vectors[2],
        }
        result = collab_engine.execute_pattern(config, latents)
        assert isinstance(result, MixtureResult)
        assert len(result.individual_latents) == 3
        assert len(result.weights) == 3
        assert isinstance(result.aggregated_latent, LatentVector)

    def test_mixture_single_agent(
        self, collab_engine: CollaborationEngine, sample_vector: LatentVector
    ) -> None:
        config = CollaborationConfig(
            pattern=CollaborationPattern.MIXTURE, agents=("only_agent",)
        )
        latents = {"only_agent": sample_vector}
        result = collab_engine.execute_pattern(config, latents)
        assert isinstance(result, MixtureResult)

    def test_deliberation_pattern(
        self,
        collab_engine: CollaborationEngine,
        sample_vectors: list[LatentVector],
    ) -> None:
        config = CollaborationConfig(
            pattern=CollaborationPattern.DELIBERATION,
            agents=("reflector", "primary"),
            max_rounds=3,
        )
        latents = {"reflector": sample_vectors[0], "primary": sample_vectors[1]}
        result = collab_engine.execute_pattern(config, latents)
        assert isinstance(result, DeliberationResult)
        assert len(result.refinements) >= 1
        assert isinstance(result.refined_latent, LatentVector)

    def test_deliberation_convergence(
        self,
        collab_engine: CollaborationEngine,
        sample_vectors: list[LatentVector],
    ) -> None:
        vec = LatentVector(
            vector=np.array([0.1, 0.2, 0.3], dtype=np.float64),
            original_length=20, compressed_length=3,
            compression_ratio=0.85, semantic_hash="h",
        )
        config = CollaborationConfig(
            pattern=CollaborationPattern.DELIBERATION,
            agents=("reflector", "primary"),
            max_rounds=10,
        )
        latents = {"reflector": vec, "primary": vec}
        result = collab_engine.execute_pattern(config, latents)
        assert isinstance(result, DeliberationResult)

    def test_distillation_pattern(
        self,
        collab_engine: CollaborationEngine,
        sample_vectors: list[LatentVector],
    ) -> None:
        config = CollaborationConfig(
            pattern=CollaborationPattern.DISTILLATION,
            agents=("expert", "learner"),
        )
        latents = {"expert": sample_vectors[0], "learner": sample_vectors[1]}
        result = collab_engine.execute_pattern(config, latents)
        assert isinstance(result, DistillationResult)
        assert isinstance(result.transferred_latent, LatentVector)
        assert 0.0 <= result.knowledge_fidelity <= 1.0

    def test_sequential_pattern(
        self,
        collab_engine: CollaborationEngine,
        sample_vectors: list[LatentVector],
    ) -> None:
        config = CollaborationConfig(
            pattern=CollaborationPattern.SEQUENTIAL,
            agents=("planner", "critic", "solver"),
        )
        latents = {
            "planner": sample_vectors[0],
            "critic": sample_vectors[1],
            "solver": sample_vectors[2],
        }
        result = collab_engine.execute_pattern(config, latents)
        assert isinstance(result, SequentialResult)
        assert len(result.stage_latents) == 3
        assert result.stage_names == ("planner", "critic", "solver")

    def test_sequential_single_stage(
        self,
        collab_engine: CollaborationEngine,
        sample_vector: LatentVector,
    ) -> None:
        config = CollaborationConfig(
            pattern=CollaborationPattern.SEQUENTIAL, agents=("planner",)
        )
        latents = {"planner": sample_vector}
        result = collab_engine.execute_pattern(config, latents)
        assert isinstance(result, SequentialResult)
        assert len(result.stage_latents) == 1

    def test_convergence_check_true(self, sample_vector: LatentVector) -> None:
        assert convergence_check(sample_vector, sample_vector) is True

    def test_convergence_check_false(
        self, sample_vectors: list[LatentVector]
    ) -> None:
        assert convergence_check(sample_vectors[0], sample_vectors[1]) is False

    def test_convergence_check_dim_mismatch(self) -> None:
        a = LatentVector(
            vector=np.array([1.0, 0.0], dtype=np.float64),
            original_length=5, compressed_length=2,
            compression_ratio=0.6, semantic_hash="a",
        )
        b = LatentVector(
            vector=np.array([1.0, 0.0, 0.0], dtype=np.float64),
            original_length=5, compressed_length=3,
            compression_ratio=0.4, semantic_hash="b",
        )
        assert convergence_check(a, b) is False

    def test_mixture_with_different_aggregation(
        self,
        collab_engine: CollaborationEngine,
        sample_vectors: list[LatentVector],
    ) -> None:
        config = CollaborationConfig(
            pattern=CollaborationPattern.MIXTURE,
            agents=("a", "b"),
            aggregation_method=AggregationMethod.MAX,
        )
        latents = {"a": sample_vectors[0], "b": sample_vectors[1]}
        result = collab_engine.execute_pattern(config, latents)
        assert isinstance(result, MixtureResult)

    def test_collaboration_config_default(self) -> None:
        cfg = CollaborationConfig()
        assert cfg.pattern == CollaborationPattern.MIXTURE
        assert cfg.agents == ("agent_a", "agent_b")
        assert cfg.max_rounds == 5

    def test_collaboration_pattern_enum_values(self) -> None:
        assert CollaborationPattern.MIXTURE.value is not None
        assert CollaborationPattern.DELIBERATION.value is not None
        assert CollaborationPattern.DISTILLATION.value is not None
        assert CollaborationPattern.SEQUENTIAL.value is not None


# =============================================================================
# CommunicationBus
# =============================================================================


class TestCommunicationBus:
    @pytest.mark.asyncio
    async def test_publish_message(
        self, bus: CommunicationBus, sample_vector: LatentVector
    ) -> None:
        msg_id = await bus.publish("agent_a", sample_vector)
        assert isinstance(msg_id, str)
        assert len(msg_id) > 0

    @pytest.mark.asyncio
    async def test_subscribe_and_get_pending(
        self, bus: CommunicationBus, sample_vector: LatentVector
    ) -> None:
        bus.subscribe("agent_b")
        await bus.publish("agent_a", sample_vector)
        messages = await bus.get_pending("agent_b")
        assert len(messages) == 1
        assert messages[0].sender_id == "agent_a"

    @pytest.mark.asyncio
    async def test_subscribe_with_filter(
        self, bus: CommunicationBus, sample_vector: LatentVector
    ) -> None:
        bus.subscribe("agent_b", filter_pattern="important")
        await bus.publish("agent_a", sample_vector, topic="important")
        messages = await bus.get_pending("agent_b")
        assert len(messages) == 1

    @pytest.mark.asyncio
    async def test_broadcast(
        self, bus: CommunicationBus, sample_vector: LatentVector
    ) -> None:
        bus.subscribe("agent_a")
        bus.subscribe("agent_b")
        bus.subscribe("agent_c")
        recipients = await bus.broadcast(sample_vector)
        assert len(recipients) == 3

    @pytest.mark.asyncio
    async def test_broadcast_with_exclusion(
        self, bus: CommunicationBus, sample_vector: LatentVector
    ) -> None:
        bus.subscribe("agent_a")
        bus.subscribe("agent_b")
        recipients = await bus.broadcast(
            sample_vector, exclude_senders={"agent_a"}
        )
        assert "agent_a" not in recipients
        assert "agent_b" in recipients

    @pytest.mark.asyncio
    async def test_acknowledge(
        self, bus: CommunicationBus, sample_vector: LatentVector
    ) -> None:
        bus.subscribe("agent_b")
        msg_id = await bus.publish("agent_a", sample_vector)
        await bus.acknowledge(msg_id, "agent_b")
        pending = await bus.get_pending("agent_b")
        assert len(pending) == 0

    @pytest.mark.asyncio
    async def test_acknowledge_invalid(
        self, bus: CommunicationBus
    ) -> None:
        with pytest.raises(MessageDeliveryError):
            await bus.acknowledge("nonexistent_id", "agent_a")

    @pytest.mark.asyncio
    async def test_stats(
        self, bus: CommunicationBus, sample_vector: LatentVector
    ) -> None:
        bus.subscribe("agent_b")
        await bus.publish("agent_a", sample_vector)
        stats = bus.get_stats()
        assert isinstance(stats, BusStats)
        assert stats.messages_sent >= 1

    @pytest.mark.asyncio
    async def test_stats_pending(
        self, bus: CommunicationBus, sample_vector: LatentVector
    ) -> None:
        bus.subscribe("agent_b")
        await bus.publish("agent_a", sample_vector)
        stats = bus.get_stats()
        assert stats.pending >= 1

    @pytest.mark.asyncio
    async def test_stats_active_subscribers(
        self, bus: CommunicationBus, sample_vector: LatentVector
    ) -> None:
        bus.subscribe("agent_a")
        bus.subscribe("agent_b")
        await bus.publish("sender", sample_vector)
        stats = bus.get_stats()
        assert stats.active_subscribers == 2

    @pytest.mark.asyncio
    async def test_stats_compression_saved(
        self, bus: CommunicationBus, sample_vector: LatentVector
    ) -> None:
        bus.subscribe("agent_b")
        await bus.publish("agent_a", sample_vector)
        stats = bus.get_stats()
        assert stats.compression_saved_tokens >= 0

    @pytest.mark.asyncio
    async def test_message_priority(
        self, bus: CommunicationBus, sample_vector: LatentVector
    ) -> None:
        msg_id = await bus.publish(
            "agent_a", sample_vector, priority=MessagePriority.HIGH
        )
        assert msg_id is not None

    @pytest.mark.asyncio
    async def test_bus_disabled_broadcast(
        self, sample_vector: LatentVector
    ) -> None:
        cfg = BusConfig(broadcast_enabled=False)
        restricted_bus = CommunicationBus(config=cfg)
        with pytest.raises(BusError, match="Broadcast is disabled"):
            await restricted_bus.broadcast(sample_vector)

    @pytest.mark.asyncio
    async def test_full_queue(
        self, bus: CommunicationBus, sample_vector: LatentVector
    ) -> None:
        tiny_bus = CommunicationBus(BusConfig(max_queue_size=1))
        await tiny_bus.publish("a", sample_vector)
        with pytest.raises(BusError, match="queue is full"):
            await tiny_bus.publish("b", sample_vector)

    @pytest.mark.asyncio
    async def test_subscribe_empty_agent_id(self, bus: CommunicationBus) -> None:
        with pytest.raises(BusError, match="agent_id cannot be empty"):
            bus.subscribe("")

    @pytest.mark.asyncio
    async def test_unsubscribe(
        self, bus: CommunicationBus, sample_vector: LatentVector
    ) -> None:
        bus.subscribe("agent_b")
        await bus.publish("agent_a", sample_vector)
        bus.unsubscribe("agent_b")
        messages = await bus.get_pending("agent_b")
        assert len(messages) == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired(
        self, bus: CommunicationBus, sample_vector: LatentVector
    ) -> None:
        bus.subscribe("agent_b")
        await bus.publish("agent_a", sample_vector, priority=MessagePriority.LOW)
        removed = await bus.cleanup_expired()
        assert isinstance(removed, int)

    @pytest.mark.asyncio
    async def test_multiple_subscribers(
        self, bus: CommunicationBus, sample_vector: LatentVector
    ) -> None:
        bus.subscribe("agent_b")
        bus.subscribe("agent_c")
        await bus.publish("agent_a", sample_vector)
        b_messages = await bus.get_pending("agent_b")
        c_messages = await bus.get_pending("agent_c")
        assert len(b_messages) == 1
        assert len(c_messages) == 1

    @pytest.mark.asyncio
    async def test_bus_config_default(self) -> None:
        cfg = BusConfig()
        assert cfg.max_queue_size == 1000
        assert cfg.broadcast_enabled is True
        assert cfg.persistence_enabled is True

    @pytest.mark.asyncio
    async def test_bus_config_custom(self) -> None:
        cfg = BusConfig(
            max_queue_size=500, broadcast_enabled=False, persistence_enabled=False
        )
        assert cfg.max_queue_size == 500
        assert cfg.broadcast_enabled is False
        assert cfg.persistence_enabled is False

    @pytest.mark.asyncio
    async def test_bus_message_frozen(self, sample_vector: LatentVector) -> None:
        msg = BusMessage(
            sender_id="agent_a",
            latent=sample_vector,
            timestamp=1000.0,
        )
        assert msg.sender_id == "agent_a"
        assert msg.priority == MessagePriority.NORMAL
        with pytest.raises(AttributeError):
            msg.sender_id = "agent_b"  # type: ignore[misc]

    @pytest.mark.asyncio
    async def test_subscription_frozen(self) -> None:
        sub = Subscription(agent_id="agent_a", filter_pattern="default", active=True)
        assert sub.agent_id == "agent_a"
        with pytest.raises(AttributeError):
            sub.agent_id = "agent_b"  # type: ignore[misc]


# =============================================================================
# Data class frozen property tests
# =============================================================================


class TestDataClasses:
    def test_latent_vector_frozen(self, sample_vector: LatentVector) -> None:
        with pytest.raises(AttributeError):
            sample_vector.vector = np.array([1.0])  # type: ignore[misc]

    def test_encoding_config_frozen(self) -> None:
        cfg = EncodingConfig()
        with pytest.raises(AttributeError):
            cfg.target_dimension = 32  # type: ignore[misc]

    def test_decoding_config_frozen(self) -> None:
        cfg = DecodingConfig()
        with pytest.raises(AttributeError):
            cfg.fidelity_threshold = 0.9  # type: ignore[misc]

    def test_link_config_frozen(self) -> None:
        cfg = LinkConfig()
        with pytest.raises(AttributeError):
            cfg.depth = 5  # type: ignore[misc]

    def test_credit_score_frozen(self) -> None:
        score = CreditScore("a", 0.5, 0.8, ("ev",))
        with pytest.raises(AttributeError):
            score.contribution_score = 0.9  # type: ignore[misc]

    def test_decoded_message_frozen(self) -> None:
        msg = DecodedMessage("text", 0.9, 0.85, ("key",))
        with pytest.raises(AttributeError):
            msg.text = "new text"  # type: ignore[misc]

    def test_bus_stats_frozen(self) -> None:
        stats = BusStats(messages_sent=10, pending=2, active_subscribers=3, compression_saved_tokens=50)
        with pytest.raises(AttributeError):
            stats.messages_sent = 20  # type: ignore[misc]

    def test_contribution_record_frozen(self) -> None:
        record = ContributionRecord("a", "encode", 0.8, 100.0)
        with pytest.raises(AttributeError):
            record.agent_id = "b"  # type: ignore[misc]
