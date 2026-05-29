"""ThreeLayerReliability — durable execution, embedded observability, continuous evaluations.

Based on 2026 production patterns: stateful orchestration layer, embedded
observability at every decision point, and continuous evaluation loops.
"""


from .models import ExecutionState, ReliabilitySnapshot


class ThreeLayerReliability:
    """Three-layer production reliability architecture.

    Layer 1: Durable Execution — stateful orchestration with retry/fallback
    Layer 2: Embedded Observability — metrics at every decision point
    Layer 3: Continuous Evaluations — ongoing quality scoring
    """

    def __init__(self, max_retries: int = 3, retry_delay_base: float = 1.5):
        self._executions: dict[str, ExecutionState] = {}
        self._retry_counts: dict[str, int] = {}
        self._failure_modes: dict[str, int] = {}
        self._eval_scores: dict[str, list[float]] = {}
        self._max_retries = max_retries
        self._retry_delay_base = retry_delay_base

    def start_execution(self, execution_id: str) -> None:
        """Register a new execution as RUNNING."""
        self._executions[execution_id] = ExecutionState.RUNNING

    def complete_execution(self, execution_id: str) -> None:
        """Mark execution as COMPLETED."""
        self._executions[execution_id] = ExecutionState.COMPLETED

    def fail_execution(self, execution_id: str, failure_mode: str = "unknown") -> bool:
        """Mark execution as FAILED; return True if retry is possible."""
        self._executions[execution_id] = ExecutionState.FAILED
        self._failure_modes[failure_mode] = self._failure_modes.get(failure_mode, 0) + 1

        retries = self._retry_counts.get(execution_id, 0)
        if retries < self._max_retries:
            self._retry_counts[execution_id] = retries + 1
            self._executions[execution_id] = ExecutionState.RETRYING
            return True
        return False

    def retry_delay(self, execution_id: str) -> float:
        """Exponential backoff delay for retries."""
        retries = self._retry_counts.get(execution_id, 0)
        return self._retry_delay_base ** retries

    def record_evaluation(self, execution_id: str, score: float) -> None:
        """Record a continuous evaluation score."""
        if execution_id not in self._eval_scores:
            self._eval_scores[execution_id] = []
        self._eval_scores[execution_id].append(max(0.0, min(1.0, score)))

    def avg_evaluation(self, execution_id: str) -> float | None:
        """Get average evaluation score for an execution."""
        scores = self._eval_scores.get(execution_id, [])
        if not scores:
            return None
        return sum(scores) / len(scores)

    def snapshot(self) -> ReliabilitySnapshot:
        """Generate a point-in-time reliability snapshot."""
        total = len(self._executions)
        successful = sum(1 for s in self._executions.values() if s == ExecutionState.COMPLETED)
        failed = sum(1 for s in self._executions.values() if s in (ExecutionState.FAILED, ExecutionState.RETRYING))
        retried = sum(1 for s in self._executions.values() if s == ExecutionState.RETRYING)

        all_scores = [s for scores in self._eval_scores.values() for s in scores]
        reliability = sum(all_scores) / len(all_scores) if all_scores else 1.0

        return ReliabilitySnapshot(
            total_executions=total,
            successful=successful,
            failed=failed,
            retried=retried,
            failure_modes=dict(self._failure_modes),
            reliability_score=round(reliability, 4),
        )

    @property
    def execution_count(self) -> int:
        return len(self._executions)

    @property
    def failure_mode_count(self) -> int:
        return len(self._failure_modes)
