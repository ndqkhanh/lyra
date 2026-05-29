"""Cron-triggered recurring autonomous agent work."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

from lyra_agent_swarm.exceptions import AutopilotError


class RunStatus(Enum):
    """Execution status of an autopilot job run."""

    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    TIMED_OUT = auto()


@dataclass(frozen=True)
class Schedule:
    """Cron-like schedule for recurring autopilot jobs."""

    cron_expr: str
    max_duration: float = 3600.0
    timeout_action: str = "stop"


@dataclass(frozen=True)
class AutopilotJob:
    """A recurring autonomous job definition."""

    job_id: str
    schedule: Schedule
    task_template: dict[str, Any]
    assigned_agents: tuple[str, ...]
    enabled: bool = True


@dataclass(frozen=True)
class AutopilotConfig:
    """Configuration that governs autopilot behaviour."""

    max_concurrent_jobs: int = 5
    retry_on_failure: bool = True
    notify_on_completion: bool = True


@dataclass(frozen=True)
class AutopilotRun:
    """Snapshot of a single execution of an autopilot job."""

    job: AutopilotJob
    started_at: float
    status: RunStatus = RunStatus.RUNNING
    result: str | None = None


class Autopilot:
    """Manages scheduled, recurring autonomous agent jobs."""

    def __init__(self, config: AutopilotConfig | None = None) -> None:
        self._config = config or AutopilotConfig()
        self._jobs: dict[str, AutopilotJob] = {}
        self._runs: dict[str, list[AutopilotRun]] = {}
        self._paused: bool = False

    @property
    def config(self) -> AutopilotConfig:
        return self._config

    @property
    def jobs(self) -> dict[str, AutopilotJob]:
        return dict(self._jobs)

    @property
    def is_paused(self) -> bool:
        return self._paused

    def register_job(self, job: AutopilotJob) -> str:
        if job.job_id in self._jobs:
            raise AutopilotError(f"Job '{job.job_id}' is already registered")
        self._jobs[job.job_id] = job
        self._runs[job.job_id] = []
        return job.job_id

    def start_job(self, job_id: str) -> AutopilotRun:
        job = self._jobs.get(job_id)
        if job is None:
            raise AutopilotError(f"Job '{job_id}' not found")
        run = AutopilotRun(job=job, started_at=time.time())
        self._runs[job_id].append(run)
        return run

    def stop_job(self, job_id: str) -> None:
        if job_id not in self._jobs:
            raise AutopilotError(f"Job '{job_id}' not found")
        self._jobs[job_id] = AutopilotJob(
            job_id=self._jobs[job_id].job_id,
            schedule=self._jobs[job_id].schedule,
            task_template=self._jobs[job_id].task_template,
            assigned_agents=self._jobs[job_id].assigned_agents,
            enabled=False,
        )
        # Mark any running runs as failed
        if job_id in self._runs:
            self._runs[job_id] = [
                AutopilotRun(
                    job=r.job,
                    started_at=r.started_at,
                    status=RunStatus.FAILED,
                    result="Job stopped by user",
                )
                if r.status == RunStatus.RUNNING
                else r
                for r in self._runs[job_id]
            ]

    def pause_all(self) -> None:
        self._paused = True

    def resume_all(self) -> None:
        self._paused = False

    def get_runs(self, job_id: str) -> list[AutopilotRun]:
        return list(self._runs.get(job_id, []))

    def mark_completed(self, job_id: str, result: str) -> None:
        if job_id not in self._runs:
            raise AutopilotError(f"No runs for job '{job_id}'")
        runs = self._runs[job_id]
        if not runs:
            raise AutopilotError(f"No runs for job '{job_id}'")
        last_run = runs[-1]
        runs[-1] = AutopilotRun(
            job=last_run.job,
            started_at=last_run.started_at,
            status=RunStatus.COMPLETED,
            result=result,
        )
