"""Benchmark store — persistence, querying, and trend computation for benchmark results."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class BenchmarkRecord:
    """A single benchmark metric record persisted in the store."""

    id: str
    domain: str
    agent_id: str
    metric_name: str
    score: float
    threshold: float
    run_id: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: tuple[tuple[str, str], ...] = ()

    @property
    def passed(self) -> bool:
        return self.score >= self.threshold


@dataclass(frozen=True)
class RunComparison:
    """Comparison between two benchmark runs."""

    run_id_a: str
    run_id_b: str
    metric_diffs: tuple[tuple[str, float], ...]
    regressions: tuple[str, ...]
    improvements: tuple[str, ...]
    overall_delta: float

    @property
    def has_regressions(self) -> bool:
        return len(self.regressions) > 0

    @property
    def has_improvements(self) -> bool:
        return len(self.improvements) > 0


@dataclass
class BenchmarkStore:
    """Persistent store for benchmark records with query and trend support.

    Usage::

        store = BenchmarkStore()
        store.save(BenchmarkRecord(id="1", domain="safety", agent_id="a1",
                                   metric_name="block_rate", score=0.989, threshold=0.95))
        trend = store.get_trend("safety", "block_rate", agent_id="a1")
    """

    max_records: int = 10000
    _records: dict[str, BenchmarkRecord] = field(default_factory=dict)

    def save(self, record: BenchmarkRecord) -> None:
        if len(self._records) >= self.max_records:
            oldest = min(self._records.values(), key=lambda r: r.timestamp)
            del self._records[oldest.id]
        self._records[record.id] = record

    def save_all(self, records: list[BenchmarkRecord]) -> None:
        for record in records:
            self.save(record)

    def get(self, record_id: str) -> BenchmarkRecord | None:
        return self._records.get(record_id)

    def query(
        self,
        *,
        domain: str | None = None,
        agent_id: str | None = None,
        metric_name: str | None = None,
        since: float | None = None,
        until: float | None = None,
    ) -> tuple[BenchmarkRecord, ...]:
        """Query records with optional filters."""
        results = list(self._records.values())
        if domain is not None:
            results = [r for r in results if r.domain == domain]
        if agent_id is not None:
            results = [r for r in results if r.agent_id == agent_id]
        if metric_name is not None:
            results = [r for r in results if r.metric_name == metric_name]
        if since is not None:
            results = [r for r in results if r.timestamp >= since]
        if until is not None:
            results = [r for r in results if r.timestamp <= until]
        return tuple(sorted(results, key=lambda r: r.timestamp))

    def get_trend(
        self,
        domain: str,
        metric_name: str,
        *,
        agent_id: str | None = None,
        limit: int = 50,
    ) -> tuple[float, ...]:
        """Get score trend over time for a domain/metric pair."""
        records = self.query(
            domain=domain, agent_id=agent_id, metric_name=metric_name,
        )
        return tuple(r.score for r in records[-limit:])

    def get_latest_score(
        self,
        domain: str,
        metric_name: str,
        *,
        agent_id: str | None = None,
    ) -> float | None:
        """Get the most recent score for a domain/metric pair."""
        records = self.query(domain=domain, agent_id=agent_id, metric_name=metric_name)
        if not records:
            return None
        return records[-1].score

    def get_domains(self) -> tuple[str, ...]:
        return tuple(sorted({r.domain for r in self._records.values()}))

    def get_agents(self) -> tuple[str, ...]:
        return tuple(sorted({r.agent_id for r in self._records.values()}))

    def get_summary(
        self,
        *,
        agent_id: str | None = None,
    ) -> dict[str, dict[str, float]]:
        """Get latest scores per domain/metric for an agent."""
        summary: dict[str, dict[str, float]] = {}
        records = self.query(agent_id=agent_id) if agent_id else tuple(self._records.values())
        for record in sorted(records, key=lambda r: r.timestamp):
            summary.setdefault(record.domain, {})[record.metric_name] = record.score
        return summary

    def compare_runs(self, run_id_a: str, run_id_b: str) -> RunComparison | None:
        """Compare two runs by run_id prefix matching."""
        records_a = [r for r in self._records.values() if r.run_id.startswith(run_id_a)]
        records_b = [r for r in self._records.values() if r.run_id.startswith(run_id_b)]
        if not records_a or not records_b:
            return None

        scores_a = {f"{r.domain}:{r.metric_name}": r.score for r in records_a}
        scores_b = {f"{r.domain}:{r.metric_name}": r.score for r in records_b}

        diffs: list[tuple[str, float]] = []
        regressions: list[str] = []
        improvements: list[str] = []

        all_keys = set(scores_a.keys()) | set(scores_b.keys())
        for key in sorted(all_keys):
            a = scores_a.get(key, 0.0)
            b = scores_b.get(key, 0.0)
            delta = a - b
            diffs.append((key, round(delta, 4)))
            if delta < -0.05:
                regressions.append(key)
            elif delta > 0.05:
                improvements.append(key)

        overall = round(sum(d for _, d in diffs) / max(len(diffs), 1), 4)

        return RunComparison(
            run_id_a=run_id_a,
            run_id_b=run_id_b,
            metric_diffs=tuple(diffs),
            regressions=tuple(regressions),
            improvements=tuple(improvements),
            overall_delta=overall,
        )

    def get_top(
        self,
        domain: str,
        *,
        metric_name: str | None = None,
        limit: int = 10,
    ) -> tuple[BenchmarkRecord, ...]:
        """Get top-scoring records for a domain, optionally filtered by metric."""
        domain_records = [r for r in self._records.values() if r.domain == domain]
        if metric_name:
            domain_records = [r for r in domain_records if r.metric_name == metric_name]
        sorted_records = sorted(domain_records, key=lambda r: r.score, reverse=True)
        return tuple(sorted_records[:limit])

    def prune_before(self, timestamp: float) -> int:
        """Remove records older than a timestamp. Returns count removed."""
        to_remove = [rid for rid, r in self._records.items() if r.timestamp < timestamp]
        for rid in to_remove:
            del self._records[rid]
        return len(to_remove)

    @property
    def record_count(self) -> int:
        return len(self._records)

    def clear(self) -> None:
        self._records.clear()
