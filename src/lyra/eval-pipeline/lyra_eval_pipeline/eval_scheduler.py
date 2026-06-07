"""Schedule and orchestrate evaluation runs."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

from .domain_evaluator import DomainEvaluator
from .exceptions import SchedulerError


@dataclass(frozen=True)
class ScheduleConfig:
    """Configuration for evaluation scheduling."""

    cron_expression: str = "0 */6 * * *"
    domains: tuple[str, ...] = ()
    priority: str = "normal"
    retry_on_failure: bool = True


@dataclass(frozen=True)
class EvalJob:
    """A scheduled evaluation job."""

    job_id: str
    domain: str
    status: str
    created_at: float
    started_at: float = 0.0
    completed_at: float = 0.0
    result_count: int = 0


@dataclass(frozen=True)
class ScheduleStatus:
    """Current status of the evaluation scheduler."""

    active_jobs: tuple[EvalJob, ...]
    pending_jobs: tuple[EvalJob, ...]
    completed_jobs: tuple[EvalJob, ...]
    next_run: float


class EvalScheduler:
    """Manages scheduling and execution of evaluation jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, EvalJob] = {}
        self._history: list[EvalJob] = []
        self._evaluator: DomainEvaluator | None = None
        self._next_run: float = time.time() + 3600  # 1 hour from now

    def _register_evaluator(self, evaluator: DomainEvaluator) -> None:
        """Register a DomainEvaluator for job execution."""
        self._evaluator = evaluator

    async def schedule_job(self, domain: str, config: ScheduleConfig) -> str:
        """Schedule a new evaluation job."""
        job_id = f"eval-{uuid.uuid4().hex[:8]}"
        job = EvalJob(
            job_id=job_id,
            domain=domain,
            status="pending",
            created_at=time.time(),
        )
        self._jobs[job_id] = job
        self._history.append(job)
        return job_id

    async def run_job(self, job_id: str) -> Any:
        """Run a scheduled evaluation job."""
        job = self._jobs.get(job_id)
        if job is None:
            raise SchedulerError(f"Job not found: {job_id}")
        if job.status != "pending":
            raise SchedulerError(f"Job {job_id} is already {job.status}")

        if self._evaluator is None:
            raise SchedulerError("No evaluator registered for job execution")

        # Update job to active
        started_job = EvalJob(
            job_id=job.job_id,
            domain=job.domain,
            status="running",
            created_at=job.created_at,
            started_at=time.time(),
        )
        self._jobs[job_id] = started_job

        # Execute
        try:
            report = await self._evaluator.evaluate_domain(job.domain)
            completed_job = EvalJob(
                job_id=job.job_id,
                domain=job.domain,
                status="completed",
                created_at=job.created_at,
                started_at=started_job.started_at,
                completed_at=time.time(),
                result_count=len(report.results),
            )
            self._jobs[job_id] = completed_job
            return report
        except Exception as exc:
            failed_job = EvalJob(
                job_id=job.job_id,
                domain=job.domain,
                status="failed",
                created_at=job.created_at,
                started_at=started_job.started_at,
                completed_at=time.time(),
            )
            self._jobs[job_id] = failed_job
            raise SchedulerError(f"Job {job_id} failed: {exc}") from exc

    async def get_status(self) -> ScheduleStatus:
        """Get the current status of the scheduler."""
        active: list[EvalJob] = []
        pending: list[EvalJob] = []
        completed: list[EvalJob] = []

        for job in self._jobs.values():
            if job.status == "running":
                active.append(job)
            elif job.status == "pending":
                pending.append(job)
            elif job.status in ("completed", "failed"):
                completed.append(job)

        return ScheduleStatus(
            active_jobs=tuple(active),
            pending_jobs=tuple(pending),
            completed_jobs=tuple(completed),
            next_run=self._next_run,
        )

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending evaluation job."""
        job = self._jobs.get(job_id)
        if job is None:
            raise SchedulerError(f"Job not found: {job_id}")
        if job.status != "pending":
            raise SchedulerError(f"Cannot cancel job in state: {job.status}")

        cancelled_job = EvalJob(
            job_id=job.job_id,
            domain=job.domain,
            status="cancelled",
            created_at=job.created_at,
        )
        self._jobs[job_id] = cancelled_job
        return True

    async def get_job_history(self, limit: int = 50) -> tuple[EvalJob, ...]:
        """Get historical evaluation jobs."""
        sorted_history = sorted(
            self._history, key=lambda j: j.created_at, reverse=True
        )
        return tuple(sorted_history[:limit])
