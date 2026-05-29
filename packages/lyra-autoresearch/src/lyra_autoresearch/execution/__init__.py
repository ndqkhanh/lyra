"""
Self-Healing Execution System with Pivot/Refine Loops

Implements AutoResearchClaw's self-healing experiment execution:
- Automatic failure detection and classification
- Pivot vs Refine decision logic
- Checkpoint-based resumption
- Failure-to-insight conversion

Based on: researchclaw/pipeline/code_agent.py
"""

import json
import logging
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Classification of execution failures"""
    SYNTAX_ERROR = "syntax"              # Code syntax error → REFINE
    RUNTIME_ERROR = "runtime"            # Runtime exception → REFINE
    TIMEOUT = "timeout"                  # Execution timeout → REFINE
    NULL_RESULT = "null"                 # No output/empty result → PIVOT
    ASSUMPTION_VIOLATION = "assumption"  # Core assumption broken → PIVOT
    RESOURCE_LIMIT = "resource"          # Memory/disk/network limit → PIVOT
    DEPENDENCY_ERROR = "dependency"      # Missing dependency → REFINE
    UNKNOWN = "unknown"                  # Unclassified → REFINE


class ExecutionStrategy(Enum):
    """Strategy for handling failure"""
    REFINE = "refine"  # Adjust method, keep hypothesis
    PIVOT = "pivot"    # Change hypothesis fundamentally
    ABORT = "abort"    # Give up (max iterations reached)


@dataclass
class ExecutionCheckpoint:
    """State checkpoint for resumption"""
    iteration: int
    strategy_history: list[ExecutionStrategy]
    failure_history: list[FailureType]
    code_versions: list[str]
    results: list[Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ExecutionResult:
    """Result of self-healing execution"""
    success: bool
    output: Any
    iterations: int
    strategy_used: ExecutionStrategy | None
    failure_type: FailureType | None
    error_message: str | None
    checkpoint: ExecutionCheckpoint
    insights: list[str] = field(default_factory=list)


class FailureAnalyzer:
    """Analyzes failures and classifies them"""

    @staticmethod
    def classify_failure(error: Exception, context: dict[str, Any]) -> FailureType:
        """
        Classify failure type from exception and context

        Args:
            error: The exception that occurred
            context: Execution context (code, environment, etc.)

        Returns:
            FailureType classification
        """

        error_str = str(error).lower()
        error_type = type(error).__name__

        # Syntax errors
        if "syntaxerror" in error_type.lower():
            return FailureType.SYNTAX_ERROR

        # Dependency errors
        if "modulenotfounderror" in error_type.lower() or "importerror" in error_type.lower():
            return FailureType.DEPENDENCY_ERROR

        # Timeout
        if "timeout" in error_str or "timeouterror" in error_type.lower():
            return FailureType.TIMEOUT

        # Resource limits
        if any(keyword in error_str for keyword in ["memory", "disk", "space", "quota"]):
            return FailureType.RESOURCE_LIMIT

        # Null results (check context)
        if context.get("output") is None or context.get("output") == "":
            return FailureType.NULL_RESULT

        # Assumption violations (domain-specific keywords)
        assumption_keywords = [
            "assertion", "invariant", "precondition", "postcondition",
            "invalid state", "unexpected", "impossible"
        ]
        if any(keyword in error_str for keyword in assumption_keywords):
            return FailureType.ASSUMPTION_VIOLATION

        # Runtime errors (default)
        if "error" in error_type.lower() or "exception" in error_type.lower():
            return FailureType.RUNTIME_ERROR

        return FailureType.UNKNOWN


class PivotRefineDecider:
    """Decides whether to Pivot or Refine based on failure type"""

    # Decision matrix: FailureType → ExecutionStrategy
    DECISION_MATRIX = {
        FailureType.SYNTAX_ERROR: ExecutionStrategy.REFINE,
        FailureType.RUNTIME_ERROR: ExecutionStrategy.REFINE,
        FailureType.TIMEOUT: ExecutionStrategy.REFINE,
        FailureType.DEPENDENCY_ERROR: ExecutionStrategy.REFINE,
        FailureType.NULL_RESULT: ExecutionStrategy.PIVOT,
        FailureType.ASSUMPTION_VIOLATION: ExecutionStrategy.PIVOT,
        FailureType.RESOURCE_LIMIT: ExecutionStrategy.PIVOT,
        FailureType.UNKNOWN: ExecutionStrategy.REFINE,
    }

    def __init__(self, max_refines: int = 3, max_pivots: int = 2):
        self.max_refines = max_refines
        self.max_pivots = max_pivots

    def decide(
        self,
        failure_type: FailureType,
        checkpoint: ExecutionCheckpoint,
    ) -> ExecutionStrategy:
        """
        Decide strategy based on failure type and history

        Args:
            failure_type: Classified failure type
            checkpoint: Current execution checkpoint

        Returns:
            ExecutionStrategy (REFINE, PIVOT, or ABORT)
        """

        # Count previous strategies
        refine_count = checkpoint.strategy_history.count(ExecutionStrategy.REFINE)
        pivot_count = checkpoint.strategy_history.count(ExecutionStrategy.PIVOT)

        # Check if max iterations reached
        if refine_count >= self.max_refines and pivot_count >= self.max_pivots:
            return ExecutionStrategy.ABORT

        # Get base strategy from decision matrix
        base_strategy = self.DECISION_MATRIX.get(failure_type, ExecutionStrategy.REFINE)

        # Override if max reached for that strategy
        if base_strategy == ExecutionStrategy.REFINE and refine_count >= self.max_refines:
            if pivot_count < self.max_pivots:
                return ExecutionStrategy.PIVOT
            else:
                return ExecutionStrategy.ABORT

        if base_strategy == ExecutionStrategy.PIVOT and pivot_count >= self.max_pivots:
            if refine_count < self.max_refines:
                return ExecutionStrategy.REFINE
            else:
                return ExecutionStrategy.ABORT

        return base_strategy


class SelfHealingExecutor:
    """
    Self-healing executor with Pivot/Refine loops

    Automatically recovers from failures by:
    1. Detecting and classifying failures
    2. Deciding on Pivot vs Refine strategy
    3. Applying appropriate fix
    4. Resuming from checkpoint
    """

    def __init__(
        self,
        max_refines: int = 3,
        max_pivots: int = 2,
        checkpoint_dir: Path | None = None,
    ):
        self.analyzer = FailureAnalyzer()
        self.decider = PivotRefineDecider(max_refines, max_pivots)
        self.checkpoint_dir = checkpoint_dir or Path(".checkpoints")
        self.checkpoint_dir.mkdir(exist_ok=True)

    def execute(
        self,
        task_fn: Callable[..., Any],
        refine_fn: Callable[[Exception, dict], Any],
        pivot_fn: Callable[[Exception, dict], Any],
        context: dict[str, Any] | None = None,
        checkpoint_id: str | None = None,
    ) -> ExecutionResult:
        """
        Execute task with self-healing

        Args:
            task_fn: Function to execute (may fail)
            refine_fn: Function to refine approach on failure
            pivot_fn: Function to pivot hypothesis on failure
            context: Execution context
            checkpoint_id: Resume from checkpoint (optional)

        Returns:
            ExecutionResult with success status and insights
        """

        context = context or {}

        # Load or create checkpoint
        if checkpoint_id:
            checkpoint = self._load_checkpoint(checkpoint_id)
        else:
            checkpoint = ExecutionCheckpoint(
                iteration=0,
                strategy_history=[],
                failure_history=[],
                code_versions=[],
                results=[],
            )

        while True:
            checkpoint.iteration += 1

            try:
                # Execute task
                logger.info(f"Iteration {checkpoint.iteration}: Executing task")
                output = task_fn(**context)

                # Success!
                checkpoint.results.append(output)
                self._save_checkpoint(checkpoint)

                return ExecutionResult(
                    success=True,
                    output=output,
                    iterations=checkpoint.iteration,
                    strategy_used=None,
                    failure_type=None,
                    error_message=None,
                    checkpoint=checkpoint,
                    insights=self._extract_insights(checkpoint),
                )

            except Exception as e:
                # Failure - analyze and decide
                logger.warning(f"Iteration {checkpoint.iteration} failed: {e}")

                # Classify failure
                failure_type = self.analyzer.classify_failure(e, context)
                checkpoint.failure_history.append(failure_type)

                # Decide strategy
                strategy = self.decider.decide(failure_type, checkpoint)
                checkpoint.strategy_history.append(strategy)

                # Save checkpoint
                self._save_checkpoint(checkpoint)

                # Handle strategy
                if strategy == ExecutionStrategy.ABORT:
                    return ExecutionResult(
                        success=False,
                        output=None,
                        iterations=checkpoint.iteration,
                        strategy_used=strategy,
                        failure_type=failure_type,
                        error_message=str(e),
                        checkpoint=checkpoint,
                        insights=self._extract_insights(checkpoint),
                    )

                elif strategy == ExecutionStrategy.REFINE:
                    logger.info(f"Applying REFINE strategy for {failure_type.value}")
                    try:
                        context = refine_fn(e, context)
                    except Exception as refine_error:
                        logger.error(f"Refine failed: {refine_error}")
                        # Continue with original context

                elif strategy == ExecutionStrategy.PIVOT:
                    logger.info(f"Applying PIVOT strategy for {failure_type.value}")
                    try:
                        context = pivot_fn(e, context)
                    except Exception as pivot_error:
                        logger.error(f"Pivot failed: {pivot_error}")
                        # Continue with original context

    def _save_checkpoint(self, checkpoint: ExecutionCheckpoint) -> None:
        """Save checkpoint to disk"""
        checkpoint_file = self.checkpoint_dir / f"checkpoint_{checkpoint.iteration}.json"

        try:
            with open(checkpoint_file, 'w') as f:
                json.dump({
                    "iteration": checkpoint.iteration,
                    "strategy_history": [s.value for s in checkpoint.strategy_history],
                    "failure_history": [f.value for f in checkpoint.failure_history],
                    "metadata": checkpoint.metadata,
                    "timestamp": checkpoint.timestamp,
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save checkpoint: {e}")

    def _load_checkpoint(self, checkpoint_id: str) -> ExecutionCheckpoint:
        """Load checkpoint from disk"""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"

        try:
            with open(checkpoint_file) as f:
                data = json.load(f)

            return ExecutionCheckpoint(
                iteration=data["iteration"],
                strategy_history=[ExecutionStrategy(s) for s in data["strategy_history"]],
                failure_history=[FailureType(f) for f in data["failure_history"]],
                code_versions=[],
                results=[],
                metadata=data.get("metadata", {}),
                timestamp=data.get("timestamp", time.time()),
            )
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return ExecutionCheckpoint(
                iteration=0,
                strategy_history=[],
                failure_history=[],
                code_versions=[],
                results=[],
            )

    def _extract_insights(self, checkpoint: ExecutionCheckpoint) -> list[str]:
        """Extract insights from execution history"""
        insights = []

        # Insight 1: Failure patterns
        if checkpoint.failure_history:
            failure_counts = {}
            for failure in checkpoint.failure_history:
                failure_counts[failure] = failure_counts.get(failure, 0) + 1

            most_common = max(failure_counts.items(), key=lambda x: x[1])
            insights.append(
                f"Most common failure: {most_common[0].value} ({most_common[1]} times)"
            )

        # Insight 2: Strategy effectiveness
        if checkpoint.strategy_history:
            strategy_counts = {}
            for strategy in checkpoint.strategy_history:
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

            insights.append(
                f"Strategies used: {len(checkpoint.strategy_history)} total "
                f"({strategy_counts.get(ExecutionStrategy.REFINE, 0)} refines, "
                f"{strategy_counts.get(ExecutionStrategy.PIVOT, 0)} pivots)"
            )

        # Insight 3: Iteration count
        if checkpoint.iteration > 1:
            insights.append(
                f"Required {checkpoint.iteration} iterations to complete"
            )

        return insights


def execute_with_healing(
    task_fn: Callable[..., Any],
    refine_fn: Callable[[Exception, dict], Any] | None = None,
    pivot_fn: Callable[[Exception, dict], Any] | None = None,
    context: dict[str, Any] | None = None,
    max_refines: int = 3,
    max_pivots: int = 2,
) -> ExecutionResult:
    """
    Convenience function: Execute task with self-healing

    Args:
        task_fn: Function to execute
        refine_fn: Function to refine on failure (optional)
        pivot_fn: Function to pivot on failure (optional)
        context: Execution context
        max_refines: Max refine attempts
        max_pivots: Max pivot attempts

    Returns:
        ExecutionResult with success status and insights
    """

    # Default refine: retry with same context
    if refine_fn is None:
        def default_refine(error: Exception, ctx: dict) -> dict:
            logger.info(f"Default refine: retrying after {type(error).__name__}")
            return ctx
        refine_fn = default_refine

    # Default pivot: log and retry
    if pivot_fn is None:
        def default_pivot(error: Exception, ctx: dict) -> dict:
            logger.info(f"Default pivot: fundamental change needed after {type(error).__name__}")
            return ctx
        pivot_fn = default_pivot

    executor = SelfHealingExecutor(
        max_refines=max_refines,
        max_pivots=max_pivots,
    )

    return executor.execute(
        task_fn=task_fn,
        refine_fn=refine_fn,
        pivot_fn=pivot_fn,
        context=context,
    )
