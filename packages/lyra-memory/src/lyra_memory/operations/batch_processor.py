"""Batch memory operations — prune, merge, reindex, and archive in bulk.

Schedules and executes maintenance operations on the memory store
during low-activity windows to minimize impact on active sessions.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


class OperationType(StrEnum):
    PRUNE = "prune"
    MERGE = "merge"
    REINDEX = "reindex"
    ARCHIVE = "archive"
    COMPACT = "compact"


@dataclass(frozen=True)
class BatchOpResult:
    op_id: str
    op_type: OperationType
    items_processed: int
    items_affected: int
    elapsed_ms: float
    success: bool
    error_msg: str


class BatchProcessor:
    """Executes batch operations on the memory store.

    Operations are queued and processed sequentially during
    low-activity windows. Each operation is independently
    measured and reported.
    """

    def __init__(self, max_batch_size: int = 1000) -> None:
        self.max_batch_size = max_batch_size
        self._history: list[BatchOpResult] = []
        self._op_counter = 0

    def prune(
        self,
        items: list[str],
        predicate: Callable[[str], bool],
    ) -> BatchOpResult:
        return self._execute(
            OperationType.PRUNE,
            items,
            lambda i: None if predicate(i) else i,
        )

    def merge(
        self,
        items: list[str],
        merge_fn: Callable[[str, str], str | None],
    ) -> BatchOpResult:
        start = time.perf_counter()
        affected = 0
        processed = 0
        error = ""

        try:
            merged: list[str] = []
            for i in range(0, len(items), 2):
                if i + 1 < len(items):
                    result = merge_fn(items[i], items[i + 1])
                    if result is not None:
                        merged.append(result)
                        affected += 2
                    else:
                        merged.append(items[i])
                else:
                    merged.append(items[i])
                processed += 1
        except Exception as e:
            error = str(e)

        elapsed = (time.perf_counter() - start) * 1000
        self._op_counter += 1

        result = BatchOpResult(
            op_id=f"merge-{self._op_counter}",
            op_type=OperationType.MERGE,
            items_processed=processed,
            items_affected=affected,
            elapsed_ms=round(elapsed, 2),
            success=error == "",
            error_msg=error,
        )
        self._history.append(result)
        return result

    def reindex(self, item_count: int, reindex_fn: Callable[[], int]) -> BatchOpResult:
        start = time.perf_counter()
        error = ""
        indexed = 0

        try:
            indexed = reindex_fn()
        except Exception as e:
            error = str(e)

        elapsed = (time.perf_counter() - start) * 1000
        self._op_counter += 1

        result = BatchOpResult(
            op_id=f"reindex-{self._op_counter}",
            op_type=OperationType.REINDEX,
            items_processed=item_count,
            items_affected=indexed,
            elapsed_ms=round(elapsed, 2),
            success=error == "",
            error_msg=error,
        )
        self._history.append(result)
        return result

    def archive(
        self,
        items: list[str],
        age_threshold_sec: float,
        get_age_fn: Callable[[str], float],
    ) -> BatchOpResult:
        return self._execute(
            OperationType.ARCHIVE,
            items,
            lambda i: None if get_age_fn(i) > age_threshold_sec else i,
        )

    def _execute(
        self,
        op_type: OperationType,
        items: list[str],
        filter_fn: Callable[[str], str | None],
    ) -> BatchOpResult:
        start = time.perf_counter()
        affected = 0
        processed = 0
        error = ""

        try:
            batch = items[: self.max_batch_size]
            for item in batch:
                result = filter_fn(item)
                if result is None:
                    affected += 1
                processed += 1
        except Exception as e:
            error = str(e)

        elapsed = (time.perf_counter() - start) * 1000
        self._op_counter += 1

        result = BatchOpResult(
            op_id=f"{op_type.value}-{self._op_counter}",
            op_type=op_type,
            items_processed=processed,
            items_affected=affected,
            elapsed_ms=round(elapsed, 2),
            success=error == "",
            error_msg=error,
        )
        self._history.append(result)
        return result

    def stats(self) -> dict:
        successes = sum(1 for r in self._history if r.success)
        return {
            "total_operations": len(self._history),
            "success_rate": round(successes / max(len(self._history), 1), 2),
            "by_type": {
                t.value: sum(1 for r in self._history if r.op_type == t)
                for t in OperationType
            },
        }
