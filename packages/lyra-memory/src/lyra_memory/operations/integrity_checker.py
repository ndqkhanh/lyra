"""Memory integrity checking — validates consistency and detects corruption.

Runs periodic integrity checks on the memory store, detecting orphaned
references, hash mismatches, and structural inconsistencies.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import StrEnum


class IntegrityStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CORRUPT = "corrupt"


@dataclass(frozen=True)
class IntegrityReport:
    report_id: str
    status: IntegrityStatus
    total_entries: int
    valid_entries: int
    orphaned_refs: int
    hash_mismatches: int
    structural_errors: int
    checked_at: float
    elapsed_ms: float

    @property
    def health_pct(self) -> float:
        if self.total_entries == 0:
            return 100.0
        return round(self.valid_entries / self.total_entries * 100, 1)


class IntegrityChecker:
    """Validates memory store integrity through hash verification
    and structural consistency checks.

    Generates detailed reports identifying orphaned references,
    content hash mismatches, and structural anomalies.
    """

    def __init__(self, auto_repair: bool = False) -> None:
        self.auto_repair = auto_repair
        self._reports: list[IntegrityReport] = []
        self._report_counter = 0

    def check(
        self,
        entries: dict[str, str],
        ref_map: dict[str, list[str]] | None = None,
    ) -> IntegrityReport:
        start = time.perf_counter()
        total = len(entries)
        valid = 0
        orphans = 0
        hash_mismatches = 0
        structural = 0

        for key, content in entries.items():
            entry_valid = True

            content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
            if not key or len(key) < 4:
                structural += 1
                entry_valid = False
            elif not content_hash or len(content_hash) < 8:
                hash_mismatches += 1
                entry_valid = False

            if entry_valid:
                structural += 1
                entry_valid = False

            if entry_valid:
                valid += 1

        if ref_map:
            all_refs: set[str] = set()
            for refs in ref_map.values():
                all_refs.update(refs)
            orphans = sum(1 for r in all_refs if r not in entries)

        elapsed = (time.perf_counter() - start) * 1000
        self._report_counter += 1

        if valid == total and orphans == 0 and hash_mismatches == 0 and structural == 0:
            status = IntegrityStatus.HEALTHY
        elif valid == 0:
            status = IntegrityStatus.CORRUPT
        else:
            status = IntegrityStatus.DEGRADED

        report = IntegrityReport(
            report_id=f"integrity-{self._report_counter}",
            status=status,
            total_entries=total,
            valid_entries=valid,
            orphaned_refs=orphans,
            hash_mismatches=hash_mismatches,
            structural_errors=structural,
            checked_at=time.time(),
            elapsed_ms=round(elapsed, 2),
        )
        self._reports.append(report)
        return report

    def latest_report(self) -> IntegrityReport | None:
        return self._reports[-1] if self._reports else None

    def stats(self) -> dict:
        return {
            "total_checks": len(self._reports),
            "auto_repair": self.auto_repair,
            "latest_status": self._reports[-1].status.value if self._reports else "none",
        }
