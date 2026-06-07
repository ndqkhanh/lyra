"""
OrchestratorAgent — decomposes queries, spawns workers, synthesizes results.

The orchestrator is the coordination centre of the multi-agent system:
1.  ``decompose_query(question)`` -> ``list[SubTask]``
2.  Workers are spawned via ``WorkerPool``, each producing an ``Artifact``.
3.  Collected artifacts are synthesised into a final ``OrchestrationResult``.

Effort scaling:
    - 1 worker  (simple / factoid question)
    - 2-4 workers (comparison / analysis)
    - 10+ workers (complex research / multi-perspective)
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from lyra.orchestrator.artifact import Artifact, CompressionLevel
from lyra.orchestrator.worker_pool import WorkerConfig, WorkerPool

logger = logging.getLogger(__name__)


class EffortLevel(str, Enum):
    """Orchestrator effort levels mapped to worker counts."""

    SIMPLE = "simple"          # 1 worker
    COMPARISON = "comparison"  # 2-4 workers
    COMPLEX = "complex"        # 10+ workers


def determine_effort_level(question: str) -> EffortLevel:
    """
    Heuristically determine effort level based on question characteristics.

    Returns COMPLEX for longer, multi-sentence questions mentioning
    comparison, analysis, or evaluation. Returns COMPARISON for questions
    with moderate length or comparative language. Returns SIMPLE for
    short factoid-style questions.
    """
    question_lower = question.lower()
    word_count = len(question.split())

    # Complex: long questions, or questions with explicit deep-analysis framing
    complex_keywords = {"analyze", "evaluate",
                        "synthesize", "comprehensive", "research",
                        "investigate", "multiple perspectives", "pros and cons"}
    if word_count > 20 or any(kw in question_lower for kw in complex_keywords):
        return EffortLevel.COMPLEX

    # Comparison: moderate length or comparative language
    comparison_keywords = {"compare", "contrast", "difference", "similar",
                           "versus", "vs", "better", "worse", "option",
                           "alternative", "recommend", "which"}
    if word_count > 15 or any(kw in question_lower for kw in comparison_keywords):
        return EffortLevel.COMPARISON

    return EffortLevel.SIMPLE


def worker_count_for_effort(level: EffortLevel, question: str = "") -> int:
    """
    Return the recommended number of workers for a given effort level.

    Args:
        level: The determined effort level.
        question: The original question (may be used for fine-tuning).

    Returns:
        Number of workers to spawn.
    """
    mapping = {
        EffortLevel.SIMPLE: 1,
        EffortLevel.COMPARISON: 3,
        EffortLevel.COMPLEX: 10,
    }
    return mapping[level]


@dataclass
class SubTask:
    """
    A decomposed sub-task derived from the original query.

    Attributes:
        subtask_id: Unique identifier for this sub-task.
        description: Natural language description of what to research.
        perspective: Optional angle or viewpoint for this sub-task
            (e.g., "technical", "business", "security").
        dependencies: List of sub-task IDs that must complete before this one.
        metadata: Arbitrary metadata for the sub-task.
    """

    subtask_id: str
    description: str
    perspective: str = ""
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestrationResult:
    """
    The final output of the orchestrator after all workers complete.

    Attributes:
        query: The original query/question.
        summary: A synthesised summary combining all worker artifacts.
        artifacts: All artifacts produced by individual workers.
        effort_level: The effort level used for this run.
        worker_count: The number of workers spawned.
        total_duration: Total wall-clock time in seconds.
        average_confidence: Mean confidence across all artifacts.
        created_at: Timestamp of result creation.
        metadata: Additional metadata (sources, errors, etc.).
    """

    query: str
    summary: str
    artifacts: list[Artifact] = field(default_factory=list)
    effort_level: EffortLevel = EffortLevel.SIMPLE
    worker_count: int = 1
    total_duration: float = 0.0
    average_confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "query": self.query,
            "summary": self.summary,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "effort_level": self.effort_level.value,
            "worker_count": self.worker_count,
            "total_duration": self.total_duration,
            "average_confidence": self.average_confidence,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


class OrchestratorAgent:
    """
    Coordinates decomposition, dispatching, and synthesis of multi-agent
    research queries.

    Example usage::

        orchestrator = OrchestratorAgent(max_concurrency=10)

        async def worker_fn(worker_id, context, sub_task):
            # ... perform research ...
            return Artifact(task_id=sub_task.subtask_id, content="...", ...)

        result = await orchestrator.run("What is the impact of ... ?", worker_fn)
    """

    def __init__(
        self,
        orchestrator_id: str = "orchestrator",
        max_concurrency: int = 10,
        worker_timeout: float = 120.0,
        compression: CompressionLevel = CompressionLevel.FULL,
        artifact_dir: str = "data/artifacts",
    ) -> None:
        """
        Initialize the orchestrator.

        Args:
            orchestrator_id: Unique identifier for this orchestrator instance.
            max_concurrency: Maximum number of parallel workers.
            worker_timeout: Default timeout per worker (seconds).
            compression: Compression level for artifact storage.
            artifact_dir: Directory for persisting artifacts.
        """
        self.orchestrator_id = orchestrator_id
        self.max_concurrency = max_concurrency
        self.worker_timeout = worker_timeout
        self.compression = compression
        self.artifact_dir = artifact_dir
        self._pool = WorkerPool(
            config=WorkerConfig(
                max_concurrency=max_concurrency,
                default_timeout=worker_timeout,
                compression=compression,
                artifact_dir=artifact_dir,
            )
        )

    @property
    def pool(self) -> WorkerPool:
        """Return the underlying worker pool."""
        return self._pool

    def decompose_query(self, question: str, effort_level: EffortLevel | None = None) -> list[SubTask]:
        """
        Decompose a user query into sub-tasks.

        Uses rule-based decomposition based on the question and effort level.
        In production, this would leverage an LLM call; here we provide a
        structured decomposition that covers common research patterns.

        Args:
            question: The original research query.
            effort_level: Override effort level. Auto-detected if None.

        Returns:
            A list of ``SubTask`` instances.
        """
        level = effort_level or determine_effort_level(question)
        n_workers = worker_count_for_effort(level, question)

        if n_workers == 1:
            return [
                SubTask(subtask_id="st_1", description=question, perspective="general"),
            ]

        if n_workers <= 4:
            perspectives = [
                ("background", "Context and background information"),
                ("analysis", "Deep analysis and key findings"),
                ("synthesis", "Synthesis of findings and conclusions"),
            ]
            return [
                SubTask(subtask_id=f"st_{i+1}", description=question, perspective=p[0])
                for i, p in enumerate(perspectives[:n_workers])
            ]

        # 10+ workers: comprehensive multi-perspective decomposition
        perspectives = [
            ("background", "Historical context and background research"),
            ("technical", "Technical aspects and implementation details"),
            ("business", "Business implications and market impact"),
            ("security", "Security considerations and risk assessment"),
            ("ethical", "Ethical implications and societal impact"),
            ("comparison", "Comparative analysis of alternatives"),
            ("trends", "Current trends and future projections"),
            ("evidence", "Evidence gathering and source verification"),
            ("counterarguments", "Counterarguments and opposing viewpoints"),
            ("synthesis", "Final synthesis of all findings"),
        ]
        return [
            SubTask(subtask_id=f"st_{i+1}", description=question, perspective=p[0])
            for i, p in enumerate(perspectives[:n_workers])
        ]

    async def run(
        self,
        question: str,
        worker_factory: callable,
        effort_level: EffortLevel | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OrchestrationResult:
        """
        Execute a full orchestrator pipeline: decompose -> dispatch -> synthesise.

        Args:
            question: The research query to process.
            worker_factory: An async callable ``(worker_id, context, sub_task)``
                that returns an ``Artifact``. Called once per sub-task.
            effort_level: Override effort level. Auto-detected if None.
            metadata: Optional metadata for the orchestration run.

        Returns:
            An ``OrchestrationResult`` with synthesised findings.
        """
        start_time = time.monotonic()
        level = effort_level or determine_effort_level(question)
        sub_tasks = self.decompose_query(question, level)
        n_workers = len(sub_tasks)

        logger.info(
            "Orchestrator %s running with %d workers at effort=%s",
            self.orchestrator_id, n_workers, level.value,
        )

        # Build batch tasks
        batch_tasks: list[tuple[str, callable, dict[str, Any]]] = []
        for st in sub_tasks:
            async def _worker_wrapper(
                worker_id: str,
                context: dict[str, Any],
                sub_task: SubTask = st,
                _factory: callable = worker_factory,
            ) -> Artifact:
                return await _factory(worker_id=worker_id, context=context, sub_task=sub_task)

            batch_tasks.append((st.subtask_id, _worker_wrapper, {"sub_task": st}))

        # Dispatch
        artifacts = await self._pool.run_batch(batch_tasks, timeout=self.worker_timeout)

        # Synthesize
        total_duration = time.monotonic() - start_time
        result = self._synthesize(
            question=question,
            artifacts=artifacts,
            effort_level=level,
            worker_count=n_workers,
            total_duration=total_duration,
            metadata=metadata,
        )

        logger.info(
            "Orchestrator %s complete: %d/%d artifacts, %.2fs",
            self.orchestrator_id,
            sum(1 for a in artifacts if a.confidence > 0),
            len(artifacts),
            total_duration,
        )

        return result

    def _synthesize(
        self,
        question: str,
        artifacts: list[Artifact],
        effort_level: EffortLevel,
        worker_count: int,
        total_duration: float,
        metadata: dict[str, Any] | None = None,
    ) -> OrchestrationResult:
        """
        Synthesize individual artifacts into a final result.

        Combines summaries, averages confidence scores, and builds a
        consolidated summary from all artifacts.
        """
        if not artifacts:
            return OrchestrationResult(
                query=question,
                summary="No artifacts were produced.",
                artifacts=[],
                effort_level=effort_level,
                worker_count=0,
                total_duration=total_duration,
                average_confidence=0.0,
                metadata=metadata or {},
            )

        # Average confidence
        avg_conf = sum(a.confidence for a in artifacts if a.confidence is not None) / len(artifacts)

        # Build consolidated summary
        summary_parts: list[str] = [f"# Synthesis: {question}", ""]

        for i, artifact in enumerate(artifacts, 1):
            summary_parts.append(f"## Finding {i}: {artifact.summary}")
            summary_parts.append("")
            if artifact.confidence is not None:
                summary_parts.append(f"*Confidence: {artifact.confidence:.2f}*")
                summary_parts.append("")

        # Collect all unique sources
        all_sources: list[str] = []
        seen: set[str] = set()
        for a in artifacts:
            for src in a.sources:
                if src not in seen:
                    all_sources.append(src)
                    seen.add(src)

        if all_sources:
            summary_parts.append("## Sources")
            summary_parts.append("")
            summary_parts.extend(f"- {src}" for src in all_sources)

        summary = "\n".join(summary_parts)

        return OrchestrationResult(
            query=question,
            summary=summary,
            artifacts=artifacts,
            effort_level=effort_level,
            worker_count=worker_count,
            total_duration=total_duration,
            average_confidence=round(avg_conf, 4),
            metadata={
                **(metadata or {}),
                "orchestrator_id": self.orchestrator_id,
                "artifact_count": len(artifacts),
            },
        )

    async def shutdown(self) -> None:
        """Gracefully shut down the orchestrator and its worker pool."""
        await self._pool.shutdown(wait=True)

    def stats(self) -> dict[str, Any]:
        """Return orchestrator statistics including pool stats."""
        return {
            "orchestrator_id": self.orchestrator_id,
            "max_concurrency": self.max_concurrency,
            "worker_timeout": self.worker_timeout,
            "compression": self.compression.value,
            "pool": self._pool.stats(),
        }
