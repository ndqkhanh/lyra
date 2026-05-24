"""
Durable execution engine with Saga pattern support.

Provides long-running workflow execution with automatic retry,
exponential backoff, state persistence, and distributed transaction
compensation using the Saga pattern.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from lyra_production.models import (
    WorkflowExecution,
    WorkflowState,
    WorkflowStep,
)

logger = logging.getLogger(__name__)

# Type alias for workflow step functions
StepFn = Callable[[dict[str, Any]], Any]
CompensateFn = Callable[[dict[str, Any], Any], None]


class WorkflowNotFoundError(KeyError):
    """Raised when a requested workflow does not exist."""


class StepNotFoundError(KeyError):
    """Raised when a requested step does not exist."""


class WorkflowDefinition:
    """Definition of a durable workflow with steps and compensations."""

    def __init__(
        self,
        name: str,
        steps: dict[str, StepFn],
        compensations: dict[str, CompensateFn] | None = None,
        max_retries: int = 3,
        backoff_base_sec: float = 1.0,
        backoff_max_sec: float = 60.0,
    ) -> None:
        self.name = name
        self.steps = steps
        self.compensations = compensations or {}
        self.max_retries = max_retries
        self.backoff_base_sec = backoff_base_sec
        self.backoff_max_sec = backoff_max_sec


class DurableExecutor:
    """Executes long-running workflows with state persistence and retries.

    Supports the Saga pattern for distributed transactions: if a step
    fails after previous steps succeeded, compensation handlers are
    called in reverse order to undo partial work.
    """

    def __init__(self) -> None:
        self._workflows: dict[str, WorkflowExecution] = {}
        self._definitions: dict[str, WorkflowDefinition] = {}
        self._lock = Lock()

    def register_workflow(self, definition: WorkflowDefinition) -> None:
        """Register a workflow definition for execution.

        Args:
            definition: The workflow definition to register.
        """
        self._definitions[definition.name] = definition
        logger.info("Registered workflow definition: %s", definition.name)

    def start_workflow(
        self,
        definition_name: str,
        input_data: dict[str, Any] | None = None,
    ) -> WorkflowExecution:
        """Start a new workflow execution.

        Args:
            definition_name: Name of the registered workflow definition.
            input_data: Input parameters for the workflow.

        Returns:
            The initial WorkflowExecution object.

        Raises:
            KeyError: If the workflow definition is not registered.
        """
        definition = self._definitions.get(definition_name)
        if definition is None:
            raise KeyError(f"Workflow definition not found: {definition_name}")

        workflow_id = f"wf-{uuid.uuid4().hex[:12]}"
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            name=definition_name,
            state=WorkflowState.PENDING,
            attempts=0,
            input=input_data or {},
            result=None,
            history=[],
            error=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        with self._lock:
            self._workflows[workflow_id] = execution

        logger.info("Started workflow %s (%s)", workflow_id, definition_name)

        # Execute synchronously as a simplification
        self._execute_workflow(workflow_id, definition)

        return self._workflows[workflow_id]

    def _execute_workflow(
        self, workflow_id: str, definition: WorkflowDefinition
    ) -> None:
        """Execute all steps of a workflow sequentially.

        On failure, runs Saga compensation for completed steps.
        """
        completed_steps: list[str] = []
        last_error: str | None = None

        for step_name, step_fn in definition.steps.items():
            step_id = f"{workflow_id}:{step_name}"
            attempt = 0
            step_result = None
            step_error: str | None = None

            while attempt < definition.max_retries:
                attempt += 1
                started_at = datetime.now(timezone.utc)

                try:
                    step_result = step_fn(
                        self._workflows[workflow_id].input
                    )
                    step_status = "completed"

                    work_step = WorkflowStep(
                        step_id=step_id,
                        name=step_name,
                        attempt=attempt,
                        max_attempts=definition.max_retries,
                        status=step_status,
                        result=step_result,
                        error=None,
                        started_at=started_at,
                        completed_at=datetime.now(timezone.utc),
                    )

                    with self._lock:
                        history = list(self._workflows[workflow_id].history)
                        history.append(work_step)
                        self._workflows[workflow_id] = WorkflowExecution(
                            workflow_id=workflow_id,
                            name=self._workflows[workflow_id].name,
                            state=WorkflowState.RUNNING,
                            attempts=self._workflows[workflow_id].attempts + attempt - 1,
                            input=self._workflows[workflow_id].input,
                            result=step_result,
                            history=tuple(history),
                            error=None,
                            created_at=self._workflows[workflow_id].created_at,
                            updated_at=datetime.now(timezone.utc),
                        )

                    completed_steps.append(step_name)
                    step_error = None  # Clear error on successful retry
                    logger.info(
                        "Step %s completed (attempt %d/%d)",
                        step_name,
                        attempt,
                        definition.max_retries,
                    )
                    break  # Step succeeded, move to next

                except Exception as exc:
                    step_error = str(exc)
                    logger.warning(
                        "Step %s failed (attempt %d/%d): %s",
                        step_name,
                        attempt,
                        definition.max_retries,
                        step_error,
                    )

                    if attempt < definition.max_retries:
                        backoff = min(
                            definition.backoff_base_sec * (2 ** (attempt - 1)),
                            definition.backoff_max_sec,
                        )
                        time.sleep(backoff)

            if step_error is not None:
                # Step failed after all retries
                last_error = step_error

                with self._lock:
                    failed_step = WorkflowStep(
                        step_id=step_id,
                        name=step_name,
                        attempt=attempt,
                        max_attempts=definition.max_retries,
                        status="failed",
                        result=None,
                        error=step_error,
                        started_at=None,
                        completed_at=datetime.now(timezone.utc),
                    )
                    history = list(self._workflows[workflow_id].history)
                    history.append(failed_step)
                    self._workflows[workflow_id] = WorkflowExecution(
                        workflow_id=workflow_id,
                        name=self._workflows[workflow_id].name,
                        state=WorkflowState.COMPENSATING,
                        attempts=self._workflows[workflow_id].attempts,
                        input=self._workflows[workflow_id].input,
                        result=None,
                        history=tuple(history),
                        error=last_error,
                        created_at=self._workflows[workflow_id].created_at,
                        updated_at=datetime.now(timezone.utc),
                    )

                # Run Saga compensation
                self._run_compensation(workflow_id, definition, completed_steps)
                return

        # All steps completed successfully
        with self._lock:
            self._workflows[workflow_id] = WorkflowExecution(
                workflow_id=workflow_id,
                name=self._workflows[workflow_id].name,
                state=WorkflowState.COMPLETED,
                attempts=self._workflows[workflow_id].attempts,
                input=self._workflows[workflow_id].input,
                result=step_result,
                history=self._workflows[workflow_id].history,
                error=None,
                created_at=self._workflows[workflow_id].created_at,
                updated_at=datetime.now(timezone.utc),
            )

        logger.info("Workflow %s completed successfully", workflow_id)

    def _run_compensation(
        self,
        workflow_id: str,
        definition: WorkflowDefinition,
        completed_steps: list[str],
    ) -> None:
        """Run Saga compensation in reverse order for completed steps."""
        for step_name in reversed(completed_steps):
            compensate_fn = definition.compensations.get(step_name)
            if compensate_fn is None:
                logger.warning(
                    "No compensation handler for step %s", step_name
                )
                continue

            try:
                compensate_fn(
                    self._workflows[workflow_id].input,
                    None,
                )
                logger.info("Compensation for step %s succeeded", step_name)
            except Exception as exc:
                logger.error(
                    "Compensation for step %s failed: %s", step_name, exc
                )

        with self._lock:
            self._workflows[workflow_id] = WorkflowExecution(
                workflow_id=workflow_id,
                name=self._workflows[workflow_id].name,
                state=WorkflowState.COMPENSATED,
                attempts=self._workflows[workflow_id].attempts,
                input=self._workflows[workflow_id].input,
                result=None,
                history=self._workflows[workflow_id].history,
                error=self._workflows[workflow_id].error,
                created_at=self._workflows[workflow_id].created_at,
                updated_at=datetime.now(timezone.utc),
            )

        logger.info("Workflow %s compensated after failure", workflow_id)

    def resume_workflow(self, execution_id: str) -> WorkflowExecution:
        """Resume a suspended workflow execution.

        Args:
            execution_id: The workflow execution ID.

        Returns:
            The WorkflowExecution after resumption.

        Raises:
            WorkflowNotFoundError: If the workflow does not exist.
        """
        with self._lock:
            workflow = self._workflows.get(execution_id)
            if workflow is None:
                raise WorkflowNotFoundError(
                    f"Workflow not found: {execution_id}"
                )

            if workflow.state != WorkflowState.SUSPENDED:
                raise ValueError(
                    f"Cannot resume workflow {execution_id} "
                    f"in state {workflow.state.name}"
                )

            definition = self._definitions.get(workflow.name)
            if definition is None:
                raise KeyError(
                    f"Workflow definition not found: {workflow.name}"
                )

            self._workflows[execution_id] = WorkflowExecution(
                workflow_id=workflow.workflow_id,
                name=workflow.name,
                state=WorkflowState.RUNNING,
                attempts=workflow.attempts,
                input=workflow.input,
                result=workflow.result,
                history=workflow.history,
                error=workflow.error,
                created_at=workflow.created_at,
                updated_at=datetime.now(timezone.utc),
            )

        logger.info("Resumed workflow %s", execution_id)
        return self._workflows[execution_id]

    def retry_step(
        self, execution_id: str, step_id: str
    ) -> WorkflowExecution:
        """Retry a specific failed step with exponential backoff.

        Args:
            execution_id: The workflow execution ID.
            step_id: The step identifier to retry.

        Returns:
            The WorkflowExecution after retry.

        Raises:
            WorkflowNotFoundError: If the workflow does not exist.
            StepNotFoundError: If the step is not found or not failed.
        """
        with self._lock:
            workflow = self._workflows.get(execution_id)
            if workflow is None:
                raise WorkflowNotFoundError(
                    f"Workflow not found: {execution_id}"
                )

            step = None
            remaining_steps: list[WorkflowStep] = []
            for s in workflow.history:
                if s.step_id == step_id:
                    step = s
                else:
                    remaining_steps.append(s)

            if step is None:
                raise StepNotFoundError(f"Step not found: {step_id}")

            if step.status != "failed":
                raise ValueError(
                    f"Step {step_id} is in state '{step.status}', "
                    "only failed steps can be retried"
                )

            definition = self._definitions.get(workflow.name)
            if definition is None:
                raise KeyError(
                    f"Workflow definition not found: {workflow.name}"
                )

        step_fn = definition.steps.get(step.name)
        if step_fn is None:
            raise StepNotFoundError(
                f"Step function not found: {step.name}"
            )

        # Retry the step
        new_attempt = step.attempt + 1
        backoff = min(
            definition.backoff_base_sec * (2 ** (new_attempt - 1)),
            definition.backoff_max_sec,
        )
        time.sleep(backoff)

        started_at = datetime.now(timezone.utc)
        try:
            result = step_fn(workflow.input)
            retried_step = WorkflowStep(
                step_id=step_id,
                name=step.name,
                attempt=new_attempt,
                max_attempts=definition.max_retries,
                status="completed",
                result=result,
                error=None,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            retried_step = WorkflowStep(
                step_id=step_id,
                name=step.name,
                attempt=new_attempt,
                max_attempts=definition.max_retries,
                status="failed",
                result=None,
                error=str(exc),
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )

        with self._lock:
            new_history = list(remaining_steps)
            new_history.append(retried_step)
            self._workflows[execution_id] = WorkflowExecution(
                workflow_id=workflow.workflow_id,
                name=workflow.name,
                state=WorkflowState.RUNNING
                if retried_step.status == "completed"
                else WorkflowState.FAILED,
                attempts=workflow.attempts + 1,
                input=workflow.input,
                result=retried_step.result,
                history=tuple(new_history),
                error=retried_step.error,
                created_at=workflow.created_at,
                updated_at=datetime.now(timezone.utc),
            )

        logger.info(
            "Retried step %s for workflow %s -> %s",
            step_id,
            execution_id,
            retried_step.status,
        )
        return self._workflows[execution_id]

    def compensate(self, execution_id: str) -> WorkflowExecution:
        """Run full Saga compensation for a workflow.

        Args:
            execution_id: The workflow execution ID.

        Returns:
            The WorkflowExecution after compensation.

        Raises:
            WorkflowNotFoundError: If the workflow does not exist.
        """
        with self._lock:
            workflow = self._workflows.get(execution_id)
            if workflow is None:
                raise WorkflowNotFoundError(
                    f"Workflow not found: {execution_id}"
                )

            definition = self._definitions.get(workflow.name)
            if definition is None:
                raise KeyError(
                    f"Workflow definition not found: {workflow.name}"
                )

        completed_steps = [
            s.name for s in workflow.history if s.status == "completed"
        ]
        self._run_compensation(execution_id, definition, completed_steps)

        return self._workflows[execution_id]

    def get_workflow_state(self, execution_id: str) -> WorkflowExecution:
        """Get the current state of a workflow execution.

        Args:
            execution_id: The workflow execution ID.

        Returns:
            The current WorkflowExecution.

        Raises:
            WorkflowNotFoundError: If the workflow does not exist.
        """
        with self._lock:
            workflow = self._workflows.get(execution_id)
            if workflow is None:
                raise WorkflowNotFoundError(
                    f"Workflow not found: {execution_id}"
                )
            return workflow

    def list_active_workflows(self) -> list[WorkflowExecution]:
        """List all currently running or pending workflow executions."""
        with self._lock:
            return [
                w
                for w in self._workflows.values()
                if w.state
                in (WorkflowState.PENDING, WorkflowState.RUNNING)
            ]


__all__ = [
    "WorkflowNotFoundError",
    "StepNotFoundError",
    "WorkflowDefinition",
    "DurableExecutor",
]
