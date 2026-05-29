"""Dynamic workflow engine — generates imperative orchestration at runtime.

Inspired by Claude Code Dynamic Workflows: workflows are not static DAGs
defined up front but imperative scripts generated and adapted at runtime
based on task requirements and intermediate results.

Key properties:
  - Workflows are Python code generated on-the-fly
  - Steps can branch, loop, and adapt based on outputs
  - Workflow state lives out-of-band (not in agent context window)
  - Supports checkpoint/resume for multi-day runs
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepKind(str, Enum):
    """Types of workflow steps."""
    TASK = "task"              # Execute a task via an agent
    DECISION = "decision"      # Branch based on a condition
    PARALLEL = "parallel"      # Fan out to multiple sub-steps
    CONVERGE = "converge"      # Wait for parallel branches to complete
    REVIEW = "review"          # Human or automated review gate
    CHECKPOINT = "checkpoint"  # Save state for potential resume


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """A single step in a dynamic workflow."""

    id: str
    kind: StepKind
    description: str = ""
    agent_id: str | None = None
    status: StepStatus = StepStatus.PENDING
    started_at: float | None = None
    completed_at: float | None = None
    output: Any = None
    error: str = ""
    retries: int = 0
    max_retries: int = 3
    metadata: dict[str, Any] = field(default_factory=dict)
    sub_steps: list[WorkflowStep] = field(default_factory=list)
    condition: Callable[[dict], bool] | None = None  # For DECISION steps
    depends_on: list[str] = field(default_factory=list)  # Step IDs this step waits for

    def mark_running(self) -> None:
        self.status = StepStatus.RUNNING
        self.started_at = time.time()

    def mark_completed(self, output: Any = None) -> None:
        self.status = StepStatus.COMPLETED
        self.completed_at = time.time()
        self.output = output

    def mark_failed(self, error: str = "") -> None:
        self.status = StepStatus.FAILED
        self.completed_at = time.time()
        self.error = error

    def mark_skipped(self) -> None:
        self.status = StepStatus.SKIPPED

    @property
    def elapsed_s(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.completed_at or time.time()
        return end - self.started_at


@dataclass
class WorkflowContext:
    """Mutable context that flows through workflow execution.

    Lives out-of-band from agent context — only the current step's
    instruction and relevant prior outputs are injected into agent calls.
    """

    workflow_id: str
    task: str
    steps: list[WorkflowStep] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    checkpoint_step_id: str | None = None  # Last checkpoint for resume

    def get_step(self, step_id: str) -> WorkflowStep | None:
        for step in self._all_steps():
            if step.id == step_id:
                return step
        return None

    def pending_steps(self) -> list[WorkflowStep]:
        return [s for s in self._all_steps() if s.status == StepStatus.PENDING]

    def running_steps(self) -> list[WorkflowStep]:
        return [s for s in self._all_steps() if s.status == StepStatus.RUNNING]

    def completed_steps(self) -> list[WorkflowStep]:
        return [s for s in self._all_steps() if s.status == StepStatus.COMPLETED]

    def failed_steps(self) -> list[WorkflowStep]:
        return [s for s in self._all_steps() if s.status == StepStatus.FAILED]

    @property
    def all_complete(self) -> bool:
        return all(
            s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED, StepStatus.FAILED)
            for s in self._all_steps()
        )

    def _all_steps(self) -> list[WorkflowStep]:
        """Flatten all steps including sub-steps."""
        result: list[WorkflowStep] = []
        for step in self.steps:
            result.append(step)
            result.extend(step.sub_steps)
        return result


class DynamicWorkflowEngine:
    """Generates and executes dynamic workflows at runtime.

    Instead of static DAG definitions, the engine:
      1. Analyzes the task and generates an initial workflow
      2. Executes steps, adapting the workflow based on results
      3. Checkpoints progress for long-running workflows
      4. Emits events for observability (out-of-band)

    Usage::

        engine = DynamicWorkflowEngine()
        ctx = engine.create_workflow("Build a REST API for user management")

        async for event in engine.execute(ctx, executor=my_executor):
            print(f"Step {event['step_id']}: {event['status']}")
    """

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowContext] = {}

    def create_workflow(self, task: str, workflow_id: str | None = None) -> WorkflowContext:
        """Create a new workflow context from a task description.

        Generates an initial set of steps based on task analysis.
        """
        wid = workflow_id or f"wf_{uuid.uuid4().hex[:12]}"
        ctx = WorkflowContext(workflow_id=wid, task=task)

        # Generate initial steps based on task decomposition
        ctx.steps = self._generate_initial_steps(task)
        self._workflows[wid] = ctx
        return ctx

    def _generate_initial_steps(self, task: str) -> list[WorkflowStep]:
        """Generate initial workflow steps from a task description.

        Heuristic: most tasks benefit from analyze → implement → test → review.
        """
        return [
            WorkflowStep(
                id="analyze",
                kind=StepKind.TASK,
                description=f"Analyze requirements: {task[:100]}",
            ),
            WorkflowStep(
                id="implement",
                kind=StepKind.TASK,
                description="Implement the solution",
                depends_on=["analyze"],
            ),
            WorkflowStep(
                id="test",
                kind=StepKind.TASK,
                description="Run tests and verify correctness",
                depends_on=["implement"],
            ),
            WorkflowStep(
                id="review",
                kind=StepKind.REVIEW,
                description="Review implementation for quality",
                depends_on=["test"],
            ),
        ]

    async def execute(
        self,
        ctx: WorkflowContext,
        executor: Callable[[WorkflowStep, WorkflowContext], Any],
    ) -> Any:
        """Execute a workflow to completion.

        Args:
            ctx: Workflow context with steps
            executor: Callable that executes a step and returns its output

        Yields:
            Event dicts: {"step_id": ..., "status": ..., "output": ...}
        """
        while not ctx.all_complete:
            for step in ctx.pending_steps():
                # Check dependencies
                if not self._dependencies_met(step, ctx):
                    continue

                step.mark_running()
                yield {
                    "event": "step_started",
                    "step_id": step.id,
                    "kind": step.kind.value,
                    "timestamp": time.time(),
                }

                try:
                    output = await executor(step, ctx) if callable(executor) else executor(step, ctx)
                    step.mark_completed(output)
                    yield {
                        "event": "step_completed",
                        "step_id": step.id,
                        "status": "completed",
                        "output": str(output)[:200],
                        "elapsed_s": step.elapsed_s,
                        "timestamp": time.time(),
                    }

                    # Store output in context variables
                    ctx.variables[step.id] = output

                    # Adapt workflow based on step output
                    self._adapt_workflow(ctx, step)

                except Exception as exc:
                    if step.retries < step.max_retries:
                        step.retries += 1
                        step.status = StepStatus.PENDING
                        yield {
                            "event": "step_retry",
                            "step_id": step.id,
                            "retry": step.retries,
                            "error": str(exc),
                            "timestamp": time.time(),
                        }
                    else:
                        step.mark_failed(str(exc))
                        yield {
                            "event": "step_failed",
                            "step_id": step.id,
                            "error": str(exc),
                            "timestamp": time.time(),
                        }

        yield {
            "event": "workflow_complete",
            "workflow_id": ctx.workflow_id,
            "completed": len(ctx.completed_steps()),
            "failed": len(ctx.failed_steps()),
            "timestamp": time.time(),
        }

    def checkpoint(self, ctx: WorkflowContext) -> str:
        """Create a checkpoint marker for resume capability."""
        step_id = f"checkpoint_{len(ctx.events)}"
        ctx.checkpoint_step_id = step_id
        ctx.events.append({
            "event": "checkpoint",
            "step_id": step_id,
            "completed": len(ctx.completed_steps()),
            "timestamp": time.time(),
        })
        return step_id

    def resume_from_checkpoint(self, ctx: WorkflowContext) -> list[WorkflowStep]:
        """Return steps that need re-execution after a checkpoint.

        Steps that completed before the checkpoint are skipped.
        """
        if ctx.checkpoint_step_id is None:
            return ctx.pending_steps()

        for _event in ctx.events:
            if _event.get("step_id") == ctx.checkpoint_step_id:
                break

        return [s for s in ctx.pending_steps() if s.status == StepStatus.PENDING]

    # ── Internal ──────────────────────────────────────────────────────────

    @staticmethod
    def _dependencies_met(step: WorkflowStep, ctx: WorkflowContext) -> bool:
        for dep_id in step.depends_on:
            dep = ctx.get_step(dep_id)
            if dep is None:
                continue
            if dep.status == StepStatus.FAILED:
                return False
            if dep.status != StepStatus.COMPLETED:
                return False
        return True

    def _adapt_workflow(self, ctx: WorkflowContext, completed_step: WorkflowStep) -> None:
        """Adapt the workflow based on a completed step's output.

        This is where the 'dynamic' in dynamic workflow comes from:
        steps can inject new sub-steps, skip downstream steps, or
        branch based on results.
        """
        if completed_step.kind == StepKind.DECISION and completed_step.condition:
            result = completed_step.condition(ctx.variables)
            for sub in completed_step.sub_steps:
                if result:
                    sub.status = StepStatus.PENDING
                else:
                    sub.mark_skipped()

    def get_workflow(self, workflow_id: str) -> WorkflowContext | None:
        return self._workflows.get(workflow_id)
