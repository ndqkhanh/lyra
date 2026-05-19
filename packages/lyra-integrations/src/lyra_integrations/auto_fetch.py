"""
Auto-Fetch Engine - Automatic data synchronization.

Features:
- 20-minute sync loop (configurable)
- Incremental updates
- Rate limiting and backoff
- Background task queue
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import httpx


class SyncStatus(Enum):
    """Sync job status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


@dataclass
class SyncJob:
    """Auto-fetch sync job."""

    id: str
    provider: str
    account_id: str
    last_sync: Optional[datetime] = None
    next_sync: Optional[datetime] = None
    status: SyncStatus = SyncStatus.PENDING
    error: Optional[str] = None
    items_fetched: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncResult:
    """Result of a sync operation."""

    job_id: str
    success: bool
    items_fetched: int
    items_new: int
    items_updated: int
    duration_seconds: float
    error: Optional[str] = None


class AutoFetchEngine:
    """
    Automatic data synchronization engine.

    Features:
    - Configurable sync interval (default 20 minutes)
    - Incremental updates (only fetch new data)
    - Rate limiting with exponential backoff
    - Parallel sync for multiple accounts
    """

    def __init__(
        self,
        sync_interval_minutes: int = 20,
        max_workers: int = 4,
        rate_limit_backoff: int = 300,  # 5 minutes
    ):
        """
        Initialize auto-fetch engine.

        Args:
            sync_interval_minutes: Sync interval in minutes
            max_workers: Maximum concurrent sync jobs
            rate_limit_backoff: Backoff time in seconds when rate limited
        """
        self.sync_interval = timedelta(minutes=sync_interval_minutes)
        self.max_workers = max_workers
        self.rate_limit_backoff = rate_limit_backoff

        self.jobs: Dict[str, SyncJob] = {}
        self.sync_handlers: Dict[str, Callable] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []

    def register_sync_handler(
        self,
        provider: str,
        handler: Callable[[SyncJob], SyncResult],
    ):
        """
        Register sync handler for a provider.

        Args:
            provider: Provider name
            handler: Async function that performs sync
        """
        self.sync_handlers[provider] = handler

    def add_job(
        self,
        job_id: str,
        provider: str,
        account_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SyncJob:
        """
        Add sync job.

        Args:
            job_id: Unique job identifier
            provider: Provider name
            account_id: Account identifier
            metadata: Additional metadata

        Returns:
            Created sync job
        """
        job = SyncJob(
            id=job_id,
            provider=provider,
            account_id=account_id,
            next_sync=datetime.now(),
            metadata=metadata or {},
        )

        self.jobs[job_id] = job
        return job

    async def sync_job(self, job: SyncJob) -> SyncResult:
        """
        Execute sync for a single job.

        Args:
            job: Sync job

        Returns:
            Sync result
        """
        if job.provider not in self.sync_handlers:
            return SyncResult(
                job_id=job.id,
                success=False,
                items_fetched=0,
                items_new=0,
                items_updated=0,
                duration_seconds=0,
                error=f"No sync handler for provider: {job.provider}",
            )

        job.status = SyncStatus.RUNNING
        start_time = datetime.now()

        try:
            handler = self.sync_handlers[job.provider]
            result = await handler(job)

            job.status = SyncStatus.COMPLETED
            job.last_sync = datetime.now()
            job.next_sync = job.last_sync + self.sync_interval
            job.items_fetched += result.items_fetched
            job.error = None

            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limited
                job.status = SyncStatus.RATE_LIMITED
                job.next_sync = datetime.now() + timedelta(seconds=self.rate_limit_backoff)
                error_msg = f"Rate limited. Next sync in {self.rate_limit_backoff}s"
            else:
                job.status = SyncStatus.FAILED
                job.next_sync = datetime.now() + self.sync_interval
                error_msg = f"HTTP {e.response.status_code}: {e.response.text}"

            job.error = error_msg

            return SyncResult(
                job_id=job.id,
                success=False,
                items_fetched=0,
                items_new=0,
                items_updated=0,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                error=error_msg,
            )

        except Exception as e:
            job.status = SyncStatus.FAILED
            job.next_sync = datetime.now() + self.sync_interval
            job.error = str(e)

            return SyncResult(
                job_id=job.id,
                success=False,
                items_fetched=0,
                items_new=0,
                items_updated=0,
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                error=str(e),
            )

    async def run(self):
        """Start auto-fetch engine."""
        self._running = True

        while self._running:
            # Get jobs ready for sync
            now = datetime.now()
            ready_jobs = [
                job
                for job in self.jobs.values()
                if job.next_sync and job.next_sync <= now and job.status != SyncStatus.RUNNING
            ]

            if not ready_jobs:
                await asyncio.sleep(10)  # Check every 10 seconds
                continue

            # Sync jobs in parallel (up to max_workers)
            for i in range(0, len(ready_jobs), self.max_workers):
                batch = ready_jobs[i : i + self.max_workers]
                tasks = [self.sync_job(job) for job in batch]
                await asyncio.gather(*tasks, return_exceptions=True)

    def stop(self):
        """Stop auto-fetch engine."""
        self._running = False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get engine statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "total_jobs": len(self.jobs),
            "pending": sum(1 for j in self.jobs.values() if j.status == SyncStatus.PENDING),
            "running": sum(1 for j in self.jobs.values() if j.status == SyncStatus.RUNNING),
            "completed": sum(1 for j in self.jobs.values() if j.status == SyncStatus.COMPLETED),
            "failed": sum(1 for j in self.jobs.values() if j.status == SyncStatus.FAILED),
            "rate_limited": sum(
                1 for j in self.jobs.values() if j.status == SyncStatus.RATE_LIMITED
            ),
            "total_items_fetched": sum(j.items_fetched for j in self.jobs.values()),
        }

    def get_job_status(self, job_id: str) -> Optional[SyncJob]:
        """
        Get job status.

        Args:
            job_id: Job identifier

        Returns:
            Sync job if found
        """
        return self.jobs.get(job_id)
