"""LongMemEval Benchmark Runner.

Implements the LongMemEval benchmark for evaluating long-term conversational
memory systems. Based on arXiv:2410.10813 - LongMemEval benchmark.

Target metrics:
- Overall accuracy: 95%+
- Information extraction: 95%+
- Multi-session reasoning: 93%+
- Temporal reasoning: 92%+
- Knowledge updates: 94%+
- Abstention accuracy: 96%+
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class QuestionType(str, Enum):
    """LongMemEval question types."""

    SINGLE_SESSION_1HOP = "single_session_1hop"
    MULTI_SESSION_1HOP = "multi_session_1hop"
    SINGLE_SESSION_MULTIHOP = "single_session_multihop"
    MULTI_SESSION_MULTIHOP = "multi_session_multihop"
    KNOWLEDGE_UPDATE = "knowledge_update"
    TEMPORAL_REASONING = "temporal_reasoning"


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
class ConversationTurn:
    """A single turn in a conversation."""

    session_id: str
    turn_id: int
    speaker: str  # user or assistant
    content: str
    timestamp: float


@dataclass(frozen=True)
class LongMemEvalQuestion:
    """A question in the LongMemEval benchmark."""

    question_id: str
    question_text: str
    question_type: QuestionType
    correct_answer: str
    session_ids: list[str]  # Sessions containing relevant information
    requires_abstention: bool  # True if answer is "I don't know"


@dataclass
class LongMemEvalResult:
    """Results from running LongMemEval benchmark."""

    overall_accuracy: float
    info_extraction_accuracy: float
    multi_session_accuracy: float
    temporal_reasoning_accuracy: float
    knowledge_update_accuracy: float
    abstention_accuracy: float
    total_questions: int
    avg_latency_ms: float
    passed: bool  # True if all metrics meet targets
    per_question_results: list[dict[str, Any]] = field(default_factory=list)
    per_type_accuracy: dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON export."""
        return {
            "overall_accuracy": self.overall_accuracy,
            "info_extraction_accuracy": self.info_extraction_accuracy,
            "multi_session_accuracy": self.multi_session_accuracy,
            "temporal_reasoning_accuracy": self.temporal_reasoning_accuracy,
            "knowledge_update_accuracy": self.knowledge_update_accuracy,
            "abstention_accuracy": self.abstention_accuracy,
            "total_questions": self.total_questions,
            "avg_latency_ms": self.avg_latency_ms,
            "passed": self.passed,
            "per_question_results": self.per_question_results,
            "per_type_accuracy": self.per_type_accuracy,
            "timestamp": self.timestamp,
        }

    def to_json(self, path: Path) -> None:
        """Export results to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LongMemEvalResult:
        """Create from dictionary."""
        return cls(
            overall_accuracy=data["overall_accuracy"],
            info_extraction_accuracy=data["info_extraction_accuracy"],
            multi_session_accuracy=data["multi_session_accuracy"],
            temporal_reasoning_accuracy=data["temporal_reasoning_accuracy"],
            knowledge_update_accuracy=data["knowledge_update_accuracy"],
            abstention_accuracy=data["abstention_accuracy"],
            total_questions=data["total_questions"],
            avg_latency_ms=data["avg_latency_ms"],
            passed=data["passed"],
            per_question_results=data.get("per_question_results", []),
            per_type_accuracy=data.get("per_type_accuracy", {}),
            timestamp=data.get("timestamp", time.time()),
        )


class LongMemEvalBenchmark:
    """LongMemEval benchmark runner for long-term memory evaluation."""

    # Target thresholds
    TARGET_OVERALL = 0.95
    TARGET_INFO_EXTRACTION = 0.95
    TARGET_MULTI_SESSION = 0.93
    TARGET_TEMPORAL = 0.92
    TARGET_KNOWLEDGE_UPDATE = 0.94
    TARGET_ABSTENTION = 0.96

    def __init__(self, memory_store: MemoryStore):
        """Initialize benchmark with a memory store.

        Args:
            memory_store: Memory store implementing the MemoryStore protocol
        """
        self.memory_store = memory_store
        self.conversations: list[ConversationTurn] = []
        self.questions: list[LongMemEvalQuestion] = []

    def load_dataset(
        self,
        conversations: list[ConversationTurn],
        questions: list[LongMemEvalQuestion],
    ) -> None:
        """Load benchmark dataset.

        Args:
            conversations: List of conversation turns to index
            questions: List of questions to evaluate
        """
        self.conversations = conversations
        self.questions = questions
        logger.info(
            f"Loaded LongMemEval dataset: {len(conversations)} turns, "
            f"{len(questions)} questions"
        )

    def ingest_conversations(self) -> None:
        """Ingest all conversation turns into the memory store."""
        logger.info(f"Ingesting {len(self.conversations)} conversation turns...")
        self.memory_store.clear()

        for turn in self.conversations:
            self.memory_store.store(
                content=turn.content,
                metadata={
                    "session_id": turn.session_id,
                    "turn_id": turn.turn_id,
                    "speaker": turn.speaker,
                    "timestamp": turn.timestamp,
                },
            )

        logger.info("Conversation ingestion complete")

    def run_benchmark(self) -> LongMemEvalResult:
        """Run the full LongMemEval benchmark.

        Returns:
            LongMemEvalResult with all metrics
        """
        if not self.questions:
            raise ValueError("No questions loaded. Call load_dataset() first.")

        logger.info(f"Running LongMemEval benchmark on {len(self.questions)} questions...")

        # Metrics accumulators by category
        correct_total = 0
        correct_info_extraction = 0
        correct_multi_session = 0
        correct_temporal = 0
        correct_knowledge_update = 0
        correct_abstention = 0

        count_info_extraction = 0
        count_multi_session = 0
        count_temporal = 0
        count_knowledge_update = 0
        count_abstention = 0

        total_latency_ms = 0.0
        per_question_results = []
        per_type_correct: dict[str, int] = {}
        per_type_total: dict[str, int] = {}

        for question in self.questions:
            start_time = time.time()

            # Retrieve relevant memories
            results = self.memory_store.retrieve(question.question_text, top_k=10)

            # Simulate answer generation (in real implementation, use LLM)
            predicted_answer = self._generate_answer(question, results)

            latency_ms = (time.time() - start_time) * 1000
            total_latency_ms += latency_ms

            # Check correctness
            correct = self._check_answer(predicted_answer, question.correct_answer)

            if correct:
                correct_total += 1

            # Track by question type
            qtype = question.question_type
            per_type_correct[qtype] = per_type_correct.get(qtype, 0) + (1 if correct else 0)
            per_type_total[qtype] = per_type_total.get(qtype, 0) + 1

            # Track by category
            if qtype in [
                QuestionType.SINGLE_SESSION_1HOP,
                QuestionType.SINGLE_SESSION_MULTIHOP,
            ]:
                count_info_extraction += 1
                if correct:
                    correct_info_extraction += 1

            if qtype in [
                QuestionType.MULTI_SESSION_1HOP,
                QuestionType.MULTI_SESSION_MULTIHOP,
            ]:
                count_multi_session += 1
                if correct:
                    correct_multi_session += 1

            if qtype == QuestionType.TEMPORAL_REASONING:
                count_temporal += 1
                if correct:
                    correct_temporal += 1

            if qtype == QuestionType.KNOWLEDGE_UPDATE:
                count_knowledge_update += 1
                if correct:
                    correct_knowledge_update += 1

            if question.requires_abstention:
                count_abstention += 1
                if correct:
                    correct_abstention += 1

            per_question_results.append(
                {
                    "question_id": question.question_id,
                    "question_type": qtype,
                    "correct": correct,
                    "predicted_answer": predicted_answer,
                    "correct_answer": question.correct_answer,
                    "latency_ms": latency_ms,
                }
            )

        # Calculate accuracies
        n = len(self.questions)
        overall_accuracy = correct_total / n if n > 0 else 0.0
        info_extraction_accuracy = (
            correct_info_extraction / count_info_extraction
            if count_info_extraction > 0
            else 0.0
        )
        multi_session_accuracy = (
            correct_multi_session / count_multi_session if count_multi_session > 0 else 0.0
        )
        temporal_reasoning_accuracy = (
            correct_temporal / count_temporal if count_temporal > 0 else 0.0
        )
        knowledge_update_accuracy = (
            correct_knowledge_update / count_knowledge_update
            if count_knowledge_update > 0
            else 0.0
        )
        abstention_accuracy = (
            correct_abstention / count_abstention if count_abstention > 0 else 0.0
        )
        avg_latency_ms = total_latency_ms / n if n > 0 else 0.0

        # Calculate per-type accuracy
        per_type_accuracy = {
            qtype: per_type_correct.get(qtype, 0) / per_type_total.get(qtype, 1)
            for qtype in per_type_total
        }

        # Check if all targets met
        passed = (
            overall_accuracy >= self.TARGET_OVERALL
            and info_extraction_accuracy >= self.TARGET_INFO_EXTRACTION
            and multi_session_accuracy >= self.TARGET_MULTI_SESSION
            and temporal_reasoning_accuracy >= self.TARGET_TEMPORAL
            and knowledge_update_accuracy >= self.TARGET_KNOWLEDGE_UPDATE
            and abstention_accuracy >= self.TARGET_ABSTENTION
        )

        result = LongMemEvalResult(
            overall_accuracy=overall_accuracy,
            info_extraction_accuracy=info_extraction_accuracy,
            multi_session_accuracy=multi_session_accuracy,
            temporal_reasoning_accuracy=temporal_reasoning_accuracy,
            knowledge_update_accuracy=knowledge_update_accuracy,
            abstention_accuracy=abstention_accuracy,
            total_questions=n,
            avg_latency_ms=avg_latency_ms,
            passed=passed,
            per_question_results=per_question_results,
            per_type_accuracy=per_type_accuracy,
        )

        logger.info(f"LongMemEval benchmark complete. Passed: {passed}")
        logger.info(f"  Overall: {overall_accuracy:.3f} (target: {self.TARGET_OVERALL})")
        logger.info(
            f"  Info Extraction: {info_extraction_accuracy:.3f} "
            f"(target: {self.TARGET_INFO_EXTRACTION})"
        )
        logger.info(
            f"  Multi-Session: {multi_session_accuracy:.3f} "
            f"(target: {self.TARGET_MULTI_SESSION})"
        )
        logger.info(
            f"  Temporal: {temporal_reasoning_accuracy:.3f} "
            f"(target: {self.TARGET_TEMPORAL})"
        )
        logger.info(
            f"  Knowledge Update: {knowledge_update_accuracy:.3f} "
            f"(target: {self.TARGET_KNOWLEDGE_UPDATE})"
        )
        logger.info(
            f"  Abstention: {abstention_accuracy:.3f} "
            f"(target: {self.TARGET_ABSTENTION})"
        )

        return result

    def _generate_answer(
        self, question: LongMemEvalQuestion, retrieved: list[dict[str, Any]]
    ) -> str:
        """Generate answer from retrieved memories.

        In a real implementation, this would use an LLM to generate the answer.
        For testing, we use a simple heuristic.

        Args:
            question: The question to answer
            retrieved: Retrieved memory fragments

        Returns:
            Generated answer string
        """
        # Simple heuristic: if no relevant memories, abstain
        if not retrieved:
            return "I don't know"

        # For testing, return a placeholder
        # Real implementation would use LLM with retrieved context
        return "placeholder_answer"

    def _check_answer(self, predicted: str, correct: str) -> bool:
        """Check if predicted answer matches correct answer.

        Args:
            predicted: Predicted answer
            correct: Correct answer

        Returns:
            True if answers match (case-insensitive, normalized)
        """
        # Normalize answers
        pred_norm = predicted.strip().lower()
        correct_norm = correct.strip().lower()

        # Exact match
        if pred_norm == correct_norm:
            return True

        # Check for semantic equivalence (simplified)
        # Real implementation would use more sophisticated matching
        return False

    def compare_with_baseline(
        self, baseline_result: LongMemEvalResult, current_result: LongMemEvalResult
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

        overall_change, overall_regress = calc_change(
            baseline_result.overall_accuracy, current_result.overall_accuracy
        )
        info_change, info_regress = calc_change(
            baseline_result.info_extraction_accuracy,
            current_result.info_extraction_accuracy,
        )
        multi_change, multi_regress = calc_change(
            baseline_result.multi_session_accuracy, current_result.multi_session_accuracy
        )
        temporal_change, temporal_regress = calc_change(
            baseline_result.temporal_reasoning_accuracy,
            current_result.temporal_reasoning_accuracy,
        )
        knowledge_change, knowledge_regress = calc_change(
            baseline_result.knowledge_update_accuracy,
            current_result.knowledge_update_accuracy,
        )
        abstention_change, abstention_regress = calc_change(
            baseline_result.abstention_accuracy, current_result.abstention_accuracy
        )

        any_regression = any(
            [
                overall_regress,
                info_regress,
                multi_regress,
                temporal_regress,
                knowledge_regress,
                abstention_regress,
            ]
        )

        comparison = {
            "baseline_timestamp": baseline_result.timestamp,
            "current_timestamp": current_result.timestamp,
            "regression_detected": any_regression,
            "metrics": {
                "overall_accuracy": {
                    "baseline": baseline_result.overall_accuracy,
                    "current": current_result.overall_accuracy,
                    "change": overall_change,
                    "regression": overall_regress,
                },
                "info_extraction_accuracy": {
                    "baseline": baseline_result.info_extraction_accuracy,
                    "current": current_result.info_extraction_accuracy,
                    "change": info_change,
                    "regression": info_regress,
                },
                "multi_session_accuracy": {
                    "baseline": baseline_result.multi_session_accuracy,
                    "current": current_result.multi_session_accuracy,
                    "change": multi_change,
                    "regression": multi_regress,
                },
                "temporal_reasoning_accuracy": {
                    "baseline": baseline_result.temporal_reasoning_accuracy,
                    "current": current_result.temporal_reasoning_accuracy,
                    "change": temporal_change,
                    "regression": temporal_regress,
                },
                "knowledge_update_accuracy": {
                    "baseline": baseline_result.knowledge_update_accuracy,
                    "current": current_result.knowledge_update_accuracy,
                    "change": knowledge_change,
                    "regression": knowledge_regress,
                },
                "abstention_accuracy": {
                    "baseline": baseline_result.abstention_accuracy,
                    "current": current_result.abstention_accuracy,
                    "change": abstention_change,
                    "regression": abstention_regress,
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
