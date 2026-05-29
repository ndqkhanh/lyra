"""Tests for EvalScheduler."""

from __future__ import annotations

import pytest
from lyra_eval_pipeline import (
    DomainEvalConfig,
    DomainEvaluator,
    EvalJob,
    EvalScheduler,
    ScheduleConfig,
    ScheduleStatus,
)
from lyra_eval_pipeline.exceptions import SchedulerError


class TestScheduleConfig:
    def test_config_defaults(self) -> None:
        config = ScheduleConfig()
        assert config.cron_expression == "0 */6 * * *"
        assert config.domains == ()
        assert config.priority == "normal"
        assert config.retry_on_failure

    def test_config_custom(self) -> None:
        config = ScheduleConfig(
            cron_expression="0 */12 * * *",
            domains=("math", "code"),
            priority="high",
            retry_on_failure=False,
        )
        assert config.cron_expression == "0 */12 * * *"
        assert config.domains == ("math", "code")
        assert config.priority == "high"
        assert not config.retry_on_failure


class TestEvalJob:
    def test_job_creation(self) -> None:
        job = EvalJob(
            job_id="j1",
            domain="math",
            status="pending",
            created_at=1000.0,
        )
        assert job.job_id == "j1"
        assert job.status == "pending"
        assert job.started_at == 0.0
        assert job.completed_at == 0.0
        assert job.result_count == 0

    def test_job_frozen(self) -> None:
        job = EvalJob("j1", "math", "pending", 1000.0)
        with pytest.raises(AttributeError):
            job.status = "running"  # type: ignore[misc]


class TestScheduleStatus:
    def test_status_creation(self) -> None:
        status = ScheduleStatus(
            active_jobs=(),
            pending_jobs=(),
            completed_jobs=(),
            next_run=2000.0,
        )
        assert status.next_run == 2000.0
        assert len(status.active_jobs) == 0


class TestEvalScheduler:
    @pytest.mark.asyncio
    async def test_schedule_job(self) -> None:
        scheduler = EvalScheduler()
        config = ScheduleConfig()
        job_id = await scheduler.schedule_job("math", config)
        assert job_id.startswith("eval-")
        assert len(job_id) > 5

    @pytest.mark.asyncio
    async def test_schedule_job_stores_in_history(self) -> None:
        scheduler = EvalScheduler()
        job_id = await scheduler.schedule_job("math", ScheduleConfig())
        history = await scheduler.get_job_history()
        assert any(j.job_id == job_id for j in history)

    @pytest.mark.asyncio
    async def test_run_job_unknown_raises(self) -> None:
        scheduler = EvalScheduler()
        with pytest.raises(SchedulerError, match="Job not found"):
            await scheduler.run_job("nonexistent")

    @pytest.mark.asyncio
    async def test_run_job_no_evaluator_raises(self) -> None:
        scheduler = EvalScheduler()
        job_id = await scheduler.schedule_job("math", ScheduleConfig())
        with pytest.raises(SchedulerError, match="No evaluator registered"):
            await scheduler.run_job(job_id)

    @pytest.mark.asyncio
    async def test_run_job_successful(self) -> None:
        scheduler = EvalScheduler()
        evaluator = DomainEvaluator(
            configs=(DomainEvalConfig(domain="math", metrics=("acc",)),)
        )
        scheduler._register_evaluator(evaluator)
        job_id = await scheduler.schedule_job("math", ScheduleConfig())
        report = await scheduler.run_job(job_id)
        assert report.domain == "math"
        assert len(report.results) == 5

    @pytest.mark.asyncio
    async def test_run_job_updates_status(self) -> None:
        scheduler = EvalScheduler()
        evaluator = DomainEvaluator(
            configs=(DomainEvalConfig(domain="math", metrics=("acc",)),)
        )
        scheduler._register_evaluator(evaluator)
        job_id = await scheduler.schedule_job("math", ScheduleConfig())
        await scheduler.run_job(job_id)
        status = await scheduler.get_status()
        assert any(j.job_id == job_id and j.status == "completed" for j in status.completed_jobs)

    @pytest.mark.asyncio
    async def test_run_job_already_running_raises(self) -> None:
        scheduler = EvalScheduler()
        evaluator = DomainEvaluator(
            configs=(DomainEvalConfig(domain="math", metrics=("acc",)),)
        )
        scheduler._register_evaluator(evaluator)
        job_id = await scheduler.schedule_job("math", ScheduleConfig())
        await scheduler.run_job(job_id)
        with pytest.raises(SchedulerError, match="already"):
            await scheduler.run_job(job_id)

    @pytest.mark.asyncio
    async def test_get_status(self) -> None:
        scheduler = EvalScheduler()
        await scheduler.schedule_job("math", ScheduleConfig())
        await scheduler.schedule_job("code", ScheduleConfig())
        status = await scheduler.get_status()
        assert len(status.pending_jobs) == 2
        assert len(status.active_jobs) == 0
        assert len(status.completed_jobs) == 0
        assert status.next_run > 0

    @pytest.mark.asyncio
    async def test_cancel_job(self) -> None:
        scheduler = EvalScheduler()
        job_id = await scheduler.schedule_job("math", ScheduleConfig())
        cancelled = await scheduler.cancel_job(job_id)
        assert cancelled
        status = await scheduler.get_status()
        # Should no longer be in pending
        assert all(j.job_id != job_id for j in status.pending_jobs)

    @pytest.mark.asyncio
    async def test_cancel_job_unknown_raises(self) -> None:
        scheduler = EvalScheduler()
        with pytest.raises(SchedulerError, match="Job not found"):
            await scheduler.cancel_job("nonexistent")

    @pytest.mark.asyncio
    async def test_cancel_job_not_pending_raises(self) -> None:
        scheduler = EvalScheduler()
        evaluator = DomainEvaluator(
            configs=(DomainEvalConfig(domain="math", metrics=("acc",)),)
        )
        scheduler._register_evaluator(evaluator)
        job_id = await scheduler.schedule_job("math", ScheduleConfig())
        await scheduler.run_job(job_id)
        with pytest.raises(SchedulerError, match="Cannot cancel"):
            await scheduler.cancel_job(job_id)

    @pytest.mark.asyncio
    async def test_get_job_history_empty(self) -> None:
        scheduler = EvalScheduler()
        history = await scheduler.get_job_history()
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_get_job_history_limit(self) -> None:
        scheduler = EvalScheduler()
        for _ in range(10):
            await scheduler.schedule_job("math", ScheduleConfig())
        history = await scheduler.get_job_history(limit=3)
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_get_job_history_reverse_chronological(self) -> None:
        scheduler = EvalScheduler()
        j1 = await scheduler.schedule_job("math", ScheduleConfig())
        j2 = await scheduler.schedule_job("code", ScheduleConfig())
        history = await scheduler.get_job_history()
        # Most recent first
        assert history[0].job_id == j2
        assert history[1].job_id == j1

    @pytest.mark.asyncio
    async def test_schedule_multiple_domains(self) -> None:
        scheduler = EvalScheduler()
        j1 = await scheduler.schedule_job("math", ScheduleConfig())
        j2 = await scheduler.schedule_job("code", ScheduleConfig())
        j3 = await scheduler.schedule_job("reasoning", ScheduleConfig())
        assert j1 != j2
        assert j2 != j3
        status = await scheduler.get_status()
        assert len(status.pending_jobs) == 3

    @pytest.mark.asyncio
    async def test_job_has_domain(self) -> None:
        scheduler = EvalScheduler()
        job_id = await scheduler.schedule_job("physics", ScheduleConfig())
        history = await scheduler.get_job_history()
        job = next(j for j in history if j.job_id == job_id)
        assert job.domain == "physics"

    @pytest.mark.asyncio
    async def test_initial_status_no_jobs(self) -> None:
        scheduler = EvalScheduler()
        status = await scheduler.get_status()
        assert len(status.active_jobs) == 0
        assert len(status.pending_jobs) == 0
        assert len(status.completed_jobs) == 0

    @pytest.mark.asyncio
    async def test_run_job_failure_handling(self) -> None:
        scheduler = EvalScheduler()
        # Register evaluator with no config for the domain we'll test
        evaluator = DomainEvaluator()
        scheduler._register_evaluator(evaluator)
        job_id = await scheduler.schedule_job("math", ScheduleConfig())
        with pytest.raises(SchedulerError):
            await scheduler.run_job(job_id)
        # Verify the job now has failed status via get_status()
        status = await scheduler.get_status()
        failed_jobs = [j for j in status.completed_jobs if j.job_id == job_id]
        assert len(failed_jobs) == 1
        assert failed_jobs[0].status == "failed"
