"""Comprehensive tests for benchmark integration system.

Tests LoCoMo, LongMemEval, and compression tracking functionality.
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any

import pytest

from lyra_memory.benchmarks import (
    CompressionMetrics,
    CompressionTracker,
    LoCoMoBenchmark,
    LoCoMoDocument,
    LoCoMoQuery,
    LoCoMoResult,
    LongMemEvalBenchmark,
    LongMemEvalResult,
    ConversationTurn,
    LongMemEvalQuestion,
    QuestionType,
)


# Mock memory store for testing
class MockMemoryStore:
    """Mock memory store for testing."""

    def __init__(self):
        self.memories: list[dict[str, Any]] = []

    def store(self, content: str, metadata: dict[str, Any]) -> str:
        """Store a memory fragment."""
        memory_id = f"mem_{len(self.memories)}"
        self.memories.append(
            {"id": memory_id, "content": content, "metadata": metadata}
        )
        return memory_id

    def retrieve(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Retrieve relevant memories (simple keyword matching for testing)."""
        results = []
        query_lower = query.lower()

        for mem in self.memories:
            content_lower = mem["content"].lower()
            # Simple relevance scoring based on keyword overlap
            score = sum(1 for word in query_lower.split() if word in content_lower)
            if score > 0:
                results.append(
                    {
                        "content": mem["content"],
                        "doc_id": mem["metadata"].get("doc_id"),
                        "score": score,
                        **mem["metadata"],
                    }
                )

        # Sort by score and return top-k
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:top_k]

    def clear(self) -> None:
        """Clear all memories."""
        self.memories.clear()


# ============================================================================
# LoCoMo Benchmark Tests
# ============================================================================


def test_locomo_document_creation():
    """Test LoCoMo document creation."""
    doc = LoCoMoDocument(
        doc_id="doc1",
        content="This is a test document about machine learning.",
        metadata={"category": "AI"},
    )

    assert doc.doc_id == "doc1"
    assert "machine learning" in doc.content
    assert doc.metadata["category"] == "AI"


def test_locomo_query_creation():
    """Test LoCoMo query creation."""
    query = LoCoMoQuery(
        query_id="q1",
        query_text="What is machine learning?",
        relevant_doc_ids=["doc1", "doc2"],
        context_length=100,
        difficulty="medium",
    )

    assert query.query_id == "q1"
    assert len(query.relevant_doc_ids) == 2
    assert query.difficulty == "medium"


def test_locomo_benchmark_initialization():
    """Test LoCoMo benchmark initialization."""
    store = MockMemoryStore()
    benchmark = LoCoMoBenchmark(store)

    assert benchmark.memory_store == store
    assert len(benchmark.documents) == 0
    assert len(benchmark.queries) == 0


def test_locomo_load_dataset():
    """Test loading LoCoMo dataset."""
    store = MockMemoryStore()
    benchmark = LoCoMoBenchmark(store)

    documents = [
        LoCoMoDocument("doc1", "Machine learning is a subset of AI."),
        LoCoMoDocument("doc2", "Deep learning uses neural networks."),
    ]

    queries = [
        LoCoMoQuery("q1", "What is machine learning?", ["doc1"], 10, "easy"),
    ]

    benchmark.load_dataset(documents, queries)

    assert len(benchmark.documents) == 2
    assert len(benchmark.queries) == 1


def test_locomo_ingest_documents():
    """Test document ingestion."""
    store = MockMemoryStore()
    benchmark = LoCoMoBenchmark(store)

    documents = [
        LoCoMoDocument("doc1", "Machine learning content"),
        LoCoMoDocument("doc2", "Deep learning content"),
    ]

    benchmark.load_dataset(documents, [])
    benchmark.ingest_documents()

    assert len(store.memories) == 2
    assert store.memories[0]["metadata"]["doc_id"] == "doc1"


def test_locomo_precision_at_k():
    """Test Precision@K calculation."""
    store = MockMemoryStore()
    benchmark = LoCoMoBenchmark(store)

    # Perfect precision
    retrieved = ["doc1", "doc2", "doc3"]
    relevant = ["doc1", "doc2", "doc3"]
    assert benchmark._precision_at_k(retrieved, relevant) == 1.0

    # Partial precision
    retrieved = ["doc1", "doc2", "doc4"]
    relevant = ["doc1", "doc2", "doc3"]
    assert benchmark._precision_at_k(retrieved, relevant) == pytest.approx(2 / 3)

    # Zero precision
    retrieved = ["doc4", "doc5"]
    relevant = ["doc1", "doc2"]
    assert benchmark._precision_at_k(retrieved, relevant) == 0.0


def test_locomo_recall_at_k():
    """Test Recall@K calculation."""
    store = MockMemoryStore()
    benchmark = LoCoMoBenchmark(store)

    # Perfect recall
    retrieved = ["doc1", "doc2", "doc3"]
    relevant = ["doc1", "doc2"]
    assert benchmark._recall_at_k(retrieved, relevant) == 1.0

    # Partial recall
    retrieved = ["doc1", "doc4"]
    relevant = ["doc1", "doc2", "doc3"]
    assert benchmark._recall_at_k(retrieved, relevant) == pytest.approx(1 / 3)

    # Zero recall
    retrieved = ["doc4", "doc5"]
    relevant = ["doc1", "doc2"]
    assert benchmark._recall_at_k(retrieved, relevant) == 0.0


def test_locomo_mrr():
    """Test Mean Reciprocal Rank calculation."""
    store = MockMemoryStore()
    benchmark = LoCoMoBenchmark(store)

    # First position
    retrieved = ["doc1", "doc2", "doc3"]
    relevant = ["doc1"]
    assert benchmark._mean_reciprocal_rank(retrieved, relevant) == 1.0

    # Second position
    retrieved = ["doc2", "doc1", "doc3"]
    relevant = ["doc1"]
    assert benchmark._mean_reciprocal_rank(retrieved, relevant) == 0.5

    # Not found
    retrieved = ["doc2", "doc3"]
    relevant = ["doc1"]
    assert benchmark._mean_reciprocal_rank(retrieved, relevant) == 0.0


def test_locomo_ndcg():
    """Test NDCG calculation."""
    store = MockMemoryStore()
    benchmark = LoCoMoBenchmark(store)

    # Perfect ranking
    retrieved = ["doc1", "doc2", "doc3"]
    relevant = ["doc1", "doc2", "doc3"]
    ndcg = benchmark._ndcg_at_k(retrieved, relevant)
    assert ndcg == pytest.approx(1.0)

    # Partial ranking
    retrieved = ["doc1", "doc4", "doc2"]
    relevant = ["doc1", "doc2"]
    ndcg = benchmark._ndcg_at_k(retrieved, relevant)
    assert 0.0 < ndcg < 1.0


def test_locomo_run_benchmark():
    """Test running full LoCoMo benchmark."""
    store = MockMemoryStore()
    benchmark = LoCoMoBenchmark(store)

    # Create test dataset
    documents = [
        LoCoMoDocument("doc1", "Machine learning is AI subset"),
        LoCoMoDocument("doc2", "Deep learning uses neural networks"),
        LoCoMoDocument("doc3", "Natural language processing"),
    ]

    queries = [
        LoCoMoQuery("q1", "machine learning AI", ["doc1"], 10, "easy"),
        LoCoMoQuery("q2", "deep learning neural", ["doc2"], 10, "easy"),
    ]

    benchmark.load_dataset(documents, queries)
    benchmark.ingest_documents()

    result = benchmark.run_benchmark()

    assert isinstance(result, LoCoMoResult)
    assert result.total_queries == 2
    assert 0.0 <= result.precision_at_5 <= 1.0
    assert 0.0 <= result.recall_at_5 <= 1.0
    assert 0.0 <= result.mrr <= 1.0
    assert 0.0 <= result.ndcg <= 1.0
    assert result.avg_latency_ms > 0
    assert len(result.per_query_results) == 2


def test_locomo_result_serialization():
    """Test LoCoMo result serialization."""
    result = LoCoMoResult(
        precision_at_5=0.95,
        precision_at_10=0.93,
        recall_at_5=0.94,
        recall_at_10=0.92,
        mrr=0.91,
        ndcg=0.93,
        total_queries=100,
        avg_latency_ms=50.5,
        passed=True,
    )

    # Test to_dict
    data = result.to_dict()
    assert data["precision_at_5"] == 0.95
    assert data["passed"] is True

    # Test JSON export
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_path = Path(f.name)

    try:
        result.to_json(temp_path)
        with open(temp_path) as f:
            loaded = json.load(f)
        assert loaded["precision_at_5"] == 0.95
    finally:
        temp_path.unlink()

    # Test from_dict
    restored = LoCoMoResult.from_dict(data)
    assert restored.precision_at_5 == result.precision_at_5
    assert restored.passed == result.passed


def test_locomo_compare_with_baseline():
    """Test baseline comparison and regression detection."""
    store = MockMemoryStore()
    benchmark = LoCoMoBenchmark(store)

    baseline = LoCoMoResult(
        precision_at_5=0.95,
        precision_at_10=0.93,
        recall_at_5=0.94,
        recall_at_10=0.92,
        mrr=0.91,
        ndcg=0.93,
        total_queries=100,
        avg_latency_ms=50.0,
        passed=True,
    )

    # No regression
    current_good = LoCoMoResult(
        precision_at_5=0.96,
        precision_at_10=0.94,
        recall_at_5=0.95,
        recall_at_10=0.93,
        mrr=0.92,
        ndcg=0.94,
        total_queries=100,
        avg_latency_ms=48.0,
        passed=True,
    )

    comparison = benchmark.compare_with_baseline(baseline, current_good)
    assert not comparison["regression_detected"]

    # With regression (>5% drop)
    current_bad = LoCoMoResult(
        precision_at_5=0.88,  # 7% drop
        precision_at_10=0.93,
        recall_at_5=0.94,
        recall_at_10=0.92,
        mrr=0.91,
        ndcg=0.93,
        total_queries=100,
        avg_latency_ms=50.0,
        passed=False,
    )

    comparison = benchmark.compare_with_baseline(baseline, current_bad)
    assert comparison["regression_detected"]
    assert comparison["metrics"]["precision_at_5"]["regression"]


# ============================================================================
# LongMemEval Benchmark Tests
# ============================================================================


def test_conversation_turn_creation():
    """Test conversation turn creation."""
    turn = ConversationTurn(
        session_id="session1",
        turn_id=1,
        speaker="user",
        content="Hello, how are you?",
        timestamp=time.time(),
    )

    assert turn.session_id == "session1"
    assert turn.speaker == "user"


def test_longmemeval_question_creation():
    """Test LongMemEval question creation."""
    question = LongMemEvalQuestion(
        question_id="q1",
        question_text="What did I say about AI?",
        question_type=QuestionType.SINGLE_SESSION_1HOP,
        correct_answer="You said AI is fascinating",
        session_ids=["session1"],
        requires_abstention=False,
    )

    assert question.question_type == QuestionType.SINGLE_SESSION_1HOP
    assert not question.requires_abstention


def test_longmemeval_benchmark_initialization():
    """Test LongMemEval benchmark initialization."""
    store = MockMemoryStore()
    benchmark = LongMemEvalBenchmark(store)

    assert benchmark.memory_store == store
    assert len(benchmark.conversations) == 0
    assert len(benchmark.questions) == 0


def test_longmemeval_load_dataset():
    """Test loading LongMemEval dataset."""
    store = MockMemoryStore()
    benchmark = LongMemEvalBenchmark(store)

    conversations = [
        ConversationTurn("s1", 1, "user", "I love AI", time.time()),
        ConversationTurn("s1", 2, "assistant", "That's great!", time.time()),
    ]

    questions = [
        LongMemEvalQuestion(
            "q1",
            "What do I love?",
            QuestionType.SINGLE_SESSION_1HOP,
            "AI",
            ["s1"],
            False,
        ),
    ]

    benchmark.load_dataset(conversations, questions)

    assert len(benchmark.conversations) == 2
    assert len(benchmark.questions) == 1


def test_longmemeval_ingest_conversations():
    """Test conversation ingestion."""
    store = MockMemoryStore()
    benchmark = LongMemEvalBenchmark(store)

    conversations = [
        ConversationTurn("s1", 1, "user", "I love AI", time.time()),
        ConversationTurn("s1", 2, "assistant", "That's great!", time.time()),
    ]

    benchmark.load_dataset(conversations, [])
    benchmark.ingest_conversations()

    assert len(store.memories) == 2
    assert store.memories[0]["metadata"]["session_id"] == "s1"


def test_longmemeval_run_benchmark():
    """Test running full LongMemEval benchmark."""
    store = MockMemoryStore()
    benchmark = LongMemEvalBenchmark(store)

    conversations = [
        ConversationTurn("s1", 1, "user", "I love machine learning", time.time()),
        ConversationTurn("s1", 2, "assistant", "That's wonderful!", time.time()),
        ConversationTurn("s2", 1, "user", "I enjoy deep learning", time.time()),
    ]

    questions = [
        LongMemEvalQuestion(
            "q1",
            "What do I love?",
            QuestionType.SINGLE_SESSION_1HOP,
            "machine learning",
            ["s1"],
            False,
        ),
        LongMemEvalQuestion(
            "q2",
            "What do I enjoy?",
            QuestionType.MULTI_SESSION_1HOP,
            "deep learning",
            ["s2"],
            False,
        ),
    ]

    benchmark.load_dataset(conversations, questions)
    benchmark.ingest_conversations()

    result = benchmark.run_benchmark()

    assert isinstance(result, LongMemEvalResult)
    assert result.total_questions == 2
    assert 0.0 <= result.overall_accuracy <= 1.0
    assert result.avg_latency_ms > 0
    assert len(result.per_question_results) == 2


def test_longmemeval_result_serialization():
    """Test LongMemEval result serialization."""
    result = LongMemEvalResult(
        overall_accuracy=0.96,
        info_extraction_accuracy=0.95,
        multi_session_accuracy=0.94,
        temporal_reasoning_accuracy=0.93,
        knowledge_update_accuracy=0.95,
        abstention_accuracy=0.97,
        total_questions=500,
        avg_latency_ms=75.5,
        passed=True,
    )

    # Test to_dict
    data = result.to_dict()
    assert data["overall_accuracy"] == 0.96
    assert data["passed"] is True

    # Test JSON export
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_path = Path(f.name)

    try:
        result.to_json(temp_path)
        with open(temp_path) as f:
            loaded = json.load(f)
        assert loaded["overall_accuracy"] == 0.96
    finally:
        temp_path.unlink()

    # Test from_dict
    restored = LongMemEvalResult.from_dict(data)
    assert restored.overall_accuracy == result.overall_accuracy


def test_longmemeval_compare_with_baseline():
    """Test baseline comparison for LongMemEval."""
    store = MockMemoryStore()
    benchmark = LongMemEvalBenchmark(store)

    baseline = LongMemEvalResult(
        overall_accuracy=0.96,
        info_extraction_accuracy=0.95,
        multi_session_accuracy=0.94,
        temporal_reasoning_accuracy=0.93,
        knowledge_update_accuracy=0.95,
        abstention_accuracy=0.97,
        total_questions=500,
        avg_latency_ms=75.0,
        passed=True,
    )

    # No regression
    current_good = LongMemEvalResult(
        overall_accuracy=0.97,
        info_extraction_accuracy=0.96,
        multi_session_accuracy=0.95,
        temporal_reasoning_accuracy=0.94,
        knowledge_update_accuracy=0.96,
        abstention_accuracy=0.98,
        total_questions=500,
        avg_latency_ms=70.0,
        passed=True,
    )

    comparison = benchmark.compare_with_baseline(baseline, current_good)
    assert not comparison["regression_detected"]

    # With regression
    current_bad = LongMemEvalResult(
        overall_accuracy=0.89,  # 7% drop
        info_extraction_accuracy=0.95,
        multi_session_accuracy=0.94,
        temporal_reasoning_accuracy=0.93,
        knowledge_update_accuracy=0.95,
        abstention_accuracy=0.97,
        total_questions=500,
        avg_latency_ms=75.0,
        passed=False,
    )

    comparison = benchmark.compare_with_baseline(baseline, current_bad)
    assert comparison["regression_detected"]


# ============================================================================
# Compression Tracker Tests
# ============================================================================


def test_compression_metrics_creation():
    """Test compression metrics creation."""
    metrics = CompressionMetrics(
        original_size_bytes=10000,
        compressed_size_bytes=2000,
        compression_ratio=5.0,
        consolidation_latency_ms=150.0,
        fragments_before=100,
        fragments_after=20,
    )

    assert metrics.compression_ratio == 5.0
    assert metrics.fragments_before == 100


def test_compression_tracker_initialization():
    """Test compression tracker initialization."""
    tracker = CompressionTracker()

    assert len(tracker.compression_history) == 0
    assert len(tracker.retention_history) == 0


def test_track_compression():
    """Test tracking a compression operation."""
    tracker = CompressionTracker()

    original = ["This is a long memory fragment"] * 10
    compressed = ["Consolidated memory"] * 2

    metrics = tracker.track_compression(original, compressed, 100.0)

    assert metrics.compression_ratio > 1.0
    assert metrics.consolidation_latency_ms == 100.0
    assert metrics.fragments_before == 10
    assert metrics.fragments_after == 2
    assert len(tracker.compression_history) == 1


def test_compression_report_generation():
    """Test generating compression report."""
    tracker = CompressionTracker()

    # Track multiple compressions
    for i in range(5):
        original = [f"Fragment {j}" * 10 for j in range(20)]
        compressed = [f"Consolidated {j}" for j in range(5)]
        tracker.track_compression(original, compressed, 100.0 + i * 10)

    report = tracker.generate_report()

    assert report.total_compressions == 5
    assert report.avg_compression_ratio > 1.0
    assert report.avg_consolidation_latency_ms > 0
    assert report.total_bytes_saved > 0
    assert len(report.compression_history) == 5


def test_compression_report_serialization():
    """Test compression report serialization."""
    tracker = CompressionTracker()

    original = ["Fragment"] * 10
    compressed = ["Consolidated"] * 2
    tracker.track_compression(original, compressed, 100.0)

    report = tracker.generate_report()

    # Test to_dict
    data = report.to_dict()
    assert "avg_compression_ratio" in data
    assert "compression_history" in data

    # Test JSON export
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_path = Path(f.name)

    try:
        report.to_json(temp_path)
        with open(temp_path) as f:
            loaded = json.load(f)
        assert "avg_compression_ratio" in loaded
    finally:
        temp_path.unlink()


def test_compression_compare_with_baseline():
    """Test compression baseline comparison."""
    tracker = CompressionTracker()

    # Create baseline
    for _ in range(3):
        tracker.track_compression(["x"] * 10, ["y"] * 2, 100.0)
    baseline_report = tracker.generate_report()

    # Create current (better compression)
    tracker.clear_history()
    for _ in range(3):
        tracker.track_compression(["x"] * 10, ["y"] * 1, 90.0)
    current_report = tracker.generate_report()

    comparison = tracker.compare_with_baseline(baseline_report, current_report)

    assert not comparison["regression_detected"]
    assert comparison["metrics"]["compression_ratio"]["change"] > 0


def test_compression_tracker_clear_history():
    """Test clearing compression history."""
    tracker = CompressionTracker()

    tracker.track_compression(["x"] * 10, ["y"] * 2, 100.0)
    assert len(tracker.compression_history) == 1

    tracker.clear_history()
    assert len(tracker.compression_history) == 0
    assert len(tracker.retention_history) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
