"""LoCoMo (Long-Context Memory) Benchmark Runner.

Implements the LoCoMo benchmark for evaluating long-context memory systems.
Based on arXiv:2309.00986 - LoCoMo: Long-Context Memory Benchmark.

Target metrics:
- Precision@5: 93%+
- Precision@10: 93%+
- Recall@5: 93%+
- Recall@10: 93%+
- MRR (Mean Reciprocal Rank): 0.90+
- NDCG (Normalized Discounted Cumulative Gain): 0.92+
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class MemoryStore(Protocol):
    """Protocol for memory store interface."""

    def store(self, content: str, metadata: dict[str, Any]) -> str:
        """Store a memory fragment."""
        ...

    def retrieve(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Retrieve relevant memories."""
        ...

    def clear(self) -> None:
        """Clear all memories."""
        ...


@dataclass(frozen=True)
class LoCoMoQuery:
    """A single LoCoMo benchmark query."""

    query_id: str
    query_text: str
    relevant_doc_ids: list[str]
    context_length: int  # Number of documents in context
    difficulty: str  # easy, medium, hard


@dataclass(frozen=True)
class LoCoMoDocument:
    """A document in the LoCoMo benchmark."""

    doc_id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LoCoMoResult:
    """Results from running LoCoMo benchmark."""

    precision_at_5: float
    precision_at_10: float
    recall_at_5: float
    recall_at_10: float
    mrr: float  # Mean Reciprocal Rank
    ndcg: float  # Normalized Discounted Cumulative Gain
    total_queries: int
    avg_latency_ms: float
    passed: bool  # True if all metrics meet targets
    per_query_results: list[dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON export."""
        return {
            "precision_at_5": self.precision_at_5,
            "precision_at_10": self.precision_at_10,
            "recall_at_5": self.recall_at_5,
            "recall_at_10": self.recall_at_10,
            "mrr": self.mrr,
            "ndcg": self.ndcg,
            "total_queries": self.total_queries,
            "avg_latency_ms": self.avg_latency_ms,
            "passed": self.passed,
            "per_query_results": self.per_query_results,
            "timestamp": self.timestamp,
        }

    def to_json(self, path: Path) -> None:
        """Export results to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LoCoMoResult:
        """Create from dictionary."""
        return cls(
            precision_at_5=data["precision_at_5"],
            precision_at_10=data["precision_at_10"],
            recall_at_5=data["recall_at_5"],
            recall_at_10=data["recall_at_10"],
            mrr=data["mrr"],
            ndcg=data["ndcg"],
            total_queries=data["total_queries"],
            avg_latency_ms=data["avg_latency_ms"],
            passed=data["passed"],
            per_query_results=data.get("per_query_results", []),
            timestamp=data.get("timestamp", time.time()),
        )


class LoCoMoBenchmark:
    """LoCoMo benchmark runner for long-context memory evaluation."""

    # Target thresholds
    TARGET_PRECISION_5 = 0.93
    TARGET_PRECISION_10 = 0.93
    TARGET_RECALL_5 = 0.93
    TARGET_RECALL_10 = 0.93
    TARGET_MRR = 0.90
    TARGET_NDCG = 0.92

    def __init__(self, memory_store: MemoryStore):
        """Initialize benchmark with a memory store.

        Args:
            memory_store: Memory store implementing the MemoryStore protocol
        """
        self.memory_store = memory_store
        self.documents: list[LoCoMoDocument] = []
        self.queries: list[LoCoMoQuery] = []

    def load_dataset(
        self,
        documents: list[LoCoMoDocument],
        queries: list[LoCoMoQuery],
    ) -> None:
        """Load benchmark dataset.

        Args:
            documents: List of documents to index
            queries: List of queries to evaluate
        """
        self.documents = documents
        self.queries = queries
        logger.info(
            f"Loaded LoCoMo dataset: {len(documents)} docs, {len(queries)} queries"
        )

    def ingest_documents(self) -> None:
        """Ingest all documents into the memory store."""
        logger.info(f"Ingesting {len(self.documents)} documents...")
        self.memory_store.clear()

        for doc in self.documents:
            self.memory_store.store(
                content=doc.content,
                metadata={"doc_id": doc.doc_id, **doc.metadata},
            )

        logger.info("Document ingestion complete")

    def run_benchmark(self) -> LoCoMoResult:
        """Run the full LoCoMo benchmark.

        Returns:
            LoCoMoResult with all metrics
        """
        if not self.queries:
            raise ValueError("No queries loaded. Call load_dataset() first.")

        logger.info(f"Running LoCoMo benchmark on {len(self.queries)} queries...")

        # Metrics accumulators
        precision_5_sum = 0.0
        precision_10_sum = 0.0
        recall_5_sum = 0.0
        recall_10_sum = 0.0
        mrr_sum = 0.0
        ndcg_sum = 0.0
        total_latency_ms = 0.0
        per_query_results = []

        for query in self.queries:
            start_time = time.time()

            # Retrieve top-10 results
            results = self.memory_store.retrieve(query.query_text, top_k=10)
            retrieved_ids = [r.get("doc_id") for r in results if "doc_id" in r]

            latency_ms = (time.time() - start_time) * 1000
            total_latency_ms += latency_ms

            # Calculate metrics for this query
            p5 = self._precision_at_k(retrieved_ids[:5], query.relevant_doc_ids)
            p10 = self._precision_at_k(retrieved_ids[:10], query.relevant_doc_ids)
            r5 = self._recall_at_k(retrieved_ids[:5], query.relevant_doc_ids)
            r10 = self._recall_at_k(retrieved_ids[:10], query.relevant_doc_ids)
            mrr = self._mean_reciprocal_rank(retrieved_ids, query.relevant_doc_ids)
            ndcg = self._ndcg_at_k(retrieved_ids[:10], query.relevant_doc_ids)

            precision_5_sum += p5
            precision_10_sum += p10
            recall_5_sum += r5
            recall_10_sum += r10
            mrr_sum += mrr
            ndcg_sum += ndcg

            per_query_results.append(
                {
                    "query_id": query.query_id,
                    "precision_at_5": p5,
                    "precision_at_10": p10,
                    "recall_at_5": r5,
                    "recall_at_10": r10,
                    "mrr": mrr,
                    "ndcg": ndcg,
                    "latency_ms": latency_ms,
                    "difficulty": query.difficulty,
                }
            )

        # Calculate averages
        n = len(self.queries)
        precision_at_5 = precision_5_sum / n
        precision_at_10 = precision_10_sum / n
        recall_at_5 = recall_5_sum / n
        recall_at_10 = recall_10_sum / n
        mrr = mrr_sum / n
        ndcg = ndcg_sum / n
        avg_latency_ms = total_latency_ms / n

        # Check if all targets met
        passed = (
            precision_at_5 >= self.TARGET_PRECISION_5
            and precision_at_10 >= self.TARGET_PRECISION_10
            and recall_at_5 >= self.TARGET_RECALL_5
            and recall_at_10 >= self.TARGET_RECALL_10
            and mrr >= self.TARGET_MRR
            and ndcg >= self.TARGET_NDCG
        )

        result = LoCoMoResult(
            precision_at_5=precision_at_5,
            precision_at_10=precision_at_10,
            recall_at_5=recall_at_5,
            recall_at_10=recall_at_10,
            mrr=mrr,
            ndcg=ndcg,
            total_queries=n,
            avg_latency_ms=avg_latency_ms,
            passed=passed,
            per_query_results=per_query_results,
        )

        logger.info(f"LoCoMo benchmark complete. Passed: {passed}")
        logger.info(f"  Precision@5: {precision_at_5:.3f} (target: {self.TARGET_PRECISION_5})")
        logger.info(f"  Precision@10: {precision_at_10:.3f} (target: {self.TARGET_PRECISION_10})")
        logger.info(f"  Recall@5: {recall_at_5:.3f} (target: {self.TARGET_RECALL_5})")
        logger.info(f"  Recall@10: {recall_at_10:.3f} (target: {self.TARGET_RECALL_10})")
        logger.info(f"  MRR: {mrr:.3f} (target: {self.TARGET_MRR})")
        logger.info(f"  NDCG: {ndcg:.3f} (target: {self.TARGET_NDCG})")

        return result

    def _precision_at_k(self, retrieved: list[str], relevant: list[str]) -> float:
        """Calculate Precision@K."""
        if not retrieved:
            return 0.0
        relevant_set = set(relevant)
        hits = sum(1 for doc_id in retrieved if doc_id in relevant_set)
        return hits / len(retrieved)

    def _recall_at_k(self, retrieved: list[str], relevant: list[str]) -> float:
        """Calculate Recall@K."""
        if not relevant:
            return 0.0
        relevant_set = set(relevant)
        hits = sum(1 for doc_id in retrieved if doc_id in relevant_set)
        return hits / len(relevant)

    def _mean_reciprocal_rank(self, retrieved: list[str], relevant: list[str]) -> float:
        """Calculate Mean Reciprocal Rank (MRR)."""
        relevant_set = set(relevant)
        for i, doc_id in enumerate(retrieved, 1):
            if doc_id in relevant_set:
                return 1.0 / i
        return 0.0

    def _ndcg_at_k(self, retrieved: list[str], relevant: list[str], k: int = 10) -> float:
        """Calculate Normalized Discounted Cumulative Gain (NDCG@K)."""
        import math

        relevant_set = set(relevant)

        # DCG: sum of (relevance / log2(rank + 1))
        dcg = 0.0
        for i, doc_id in enumerate(retrieved[:k], 1):
            relevance = 1.0 if doc_id in relevant_set else 0.0
            dcg += relevance / math.log2(i + 1)

        # IDCG: ideal DCG (all relevant docs at top)
        idcg = 0.0
        for i in range(1, min(len(relevant), k) + 1):
            idcg += 1.0 / math.log2(i + 1)

        return dcg / idcg if idcg > 0 else 0.0

    def compare_with_baseline(
        self, baseline_result: LoCoMoResult, current_result: LoCoMoResult
    ) -> dict[str, Any]:
        """Compare current results with baseline.

        Args:
            baseline_result: Previous benchmark results
            current_result: Current benchmark results

        Returns:
            Dictionary with comparison metrics and regression detection
        """
        REGRESSION_THRESHOLD = 0.05  # 5% drop triggers alert

        def calc_change(baseline: float, current: float) -> tuple[float, bool]:
            """Calculate change and detect regression."""
            change = current - baseline
            regression = change < -REGRESSION_THRESHOLD
            return change, regression

        p5_change, p5_regress = calc_change(
            baseline_result.precision_at_5, current_result.precision_at_5
        )
        p10_change, p10_regress = calc_change(
            baseline_result.precision_at_10, current_result.precision_at_10
        )
        r5_change, r5_regress = calc_change(
            baseline_result.recall_at_5, current_result.recall_at_5
        )
        r10_change, r10_regress = calc_change(
            baseline_result.recall_at_10, current_result.recall_at_10
        )
        mrr_change, mrr_regress = calc_change(baseline_result.mrr, current_result.mrr)
        ndcg_change, ndcg_regress = calc_change(baseline_result.ndcg, current_result.ndcg)

        any_regression = any(
            [p5_regress, p10_regress, r5_regress, r10_regress, mrr_regress, ndcg_regress]
        )

        comparison = {
            "baseline_timestamp": baseline_result.timestamp,
            "current_timestamp": current_result.timestamp,
            "regression_detected": any_regression,
            "metrics": {
                "precision_at_5": {
                    "baseline": baseline_result.precision_at_5,
                    "current": current_result.precision_at_5,
                    "change": p5_change,
                    "regression": p5_regress,
                },
                "precision_at_10": {
                    "baseline": baseline_result.precision_at_10,
                    "current": current_result.precision_at_10,
                    "change": p10_change,
                    "regression": p10_regress,
                },
                "recall_at_5": {
                    "baseline": baseline_result.recall_at_5,
                    "current": current_result.recall_at_5,
                    "change": r5_change,
                    "regression": r5_regress,
                },
                "recall_at_10": {
                    "baseline": baseline_result.recall_at_10,
                    "current": current_result.recall_at_10,
                    "change": r10_change,
                    "regression": r10_regress,
                },
                "mrr": {
                    "baseline": baseline_result.mrr,
                    "current": current_result.mrr,
                    "change": mrr_change,
                    "regression": mrr_regress,
                },
                "ndcg": {
                    "baseline": baseline_result.ndcg,
                    "current": current_result.ndcg,
                    "change": ndcg_change,
                    "regression": ndcg_regress,
                },
            },
        }

        if any_regression:
            logger.warning("⚠️  Performance regression detected!")
            for metric, data in comparison["metrics"].items():
                if data["regression"]:
                    logger.warning(
                        f"  {metric}: {data['baseline']:.3f} → {data['current']:.3f} "
                        f"(change: {data['change']:.3f})"
                    )

        return comparison
