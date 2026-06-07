"""Request Batcher — aggregate and flush swarm requests in batches.

Provides request batching for swarm operations:
  - Request aggregation by operation type
  - Configurable batch sizes and max wait times
  - Pending queue with backpressure
  - Batch flush with operation grouping
  - Batch result tracking
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import StrEnum


class BatchStatus(StrEnum):
    """Status of a batch after flushing."""

    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass(frozen=True)
class SwarmRequest:
    """A single swarm request to be batched."""

    request_id: str
    operation: str
    payload: str
    priority: int = 0
    created_at: float = field(default_factory=time.monotonic)


@dataclass(frozen=True)
class BatchResult:
    """Result of flushing a batch of requests."""

    batch_id: str
    operation: str
    request_count: int
    status: BatchStatus
    created_at: float = field(default_factory=time.monotonic)
    errors: tuple[str, ...] = ()


@dataclass
class BatchConfig:
    """Configuration for the request batcher."""

    max_batch_size: int = 50
    max_wait_ms: float = 100.0
    max_pending: int = 500


class RequestBatcher:
    """Aggregates and flushes swarm requests in batches.

    Groups requests by operation type and flushes them in batches
    respecting max_batch_size and max_wait_ms constraints.

    Usage::

        batcher = RequestBatcher(config=BatchConfig(max_batch_size=20))
        batcher.enqueue(SwarmRequest(request_id="1", operation="write", payload="set a=1"))
        batcher.enqueue(SwarmRequest(request_id="2", operation="write", payload="set b=2"))
        results = batcher.flush()
        for batch in results:
            print(f"Batch {batch.batch_id}: {batch.request_count} requests")
    """

    def __init__(self, config: BatchConfig | None = None) -> None:
        self.config = config or BatchConfig()
        self._pending: dict[str, list[SwarmRequest]] = defaultdict(list)
        self._completed_batches: list[BatchResult] = []
        self._total_batches = 0

    # ── Properties ───────────────────────────────────────────────

    @property
    def pending_count(self) -> int:
        return sum(len(reqs) for reqs in self._pending.values())

    @property
    def batch_count(self) -> int:
        return self._total_batches

    # ── Operations ───────────────────────────────────────────────

    def enqueue(self, request: SwarmRequest) -> None:
        """Enqueue a request for batching.

        Raises ValueError if max_pending is exceeded (backpressure).
        """
        if self.pending_count >= self.config.max_pending:
            raise ValueError(
                f"Max pending requests ({self.config.max_pending}) exceeded"
            )
        self._pending[request.operation].append(request)

    def get_batch(self, operation: str) -> list[SwarmRequest] | None:
        """Get the next batch for a specific operation.

        Returns None if no pending requests for that operation.
        """
        requests = self._pending.get(operation, [])
        if not requests:
            return None

        batch_size = min(len(requests), self.config.max_batch_size)
        batch = requests[:batch_size]
        self._pending[operation] = requests[batch_size:]
        if not self._pending[operation]:
            del self._pending[operation]
        return batch

    def flush(self) -> list[BatchResult]:
        """Flush all pending requests into batches.

        Groups by operation, splits into max_batch_size chunks.
        """
        results: list[BatchResult] = []

        for operation in list(self._pending.keys()):
            while operation in self._pending and self._pending[operation]:
                batch = self.get_batch(operation)
                if batch is None:
                    break

                self._total_batches += 1
                result = BatchResult(
                    batch_id=f"batch-{uuid.uuid4().hex[:12]}",
                    operation=operation,
                    request_count=len(batch),
                    status=BatchStatus.COMPLETED,
                )
                results.append(result)
                self._completed_batches.append(result)

        return results

    def get_status(self) -> dict:
        """Get current batcher status."""
        return {
            "pending": self.pending_count,
            "operations": list(self._pending.keys()),
            "batches_completed": len(self._completed_batches),
            "total_batches": self._total_batches,
        }

    def reset(self) -> None:
        """Reset all state."""
        self._pending.clear()
        self._completed_batches.clear()
        self._total_batches = 0
