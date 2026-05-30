"""History store for benchmark data — persists and queries historical runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BenchmarkRun:
    run_id: str
    timestamp: float
    metrics: dict[str, float]
    metadata: dict[str, str]
    tag: str = ""


@dataclass(frozen=True)
class HistoryQuery:
    metric_name: str | None = None
    tag: str | None = None
    since: float | None = None
    until: float | None = None
    limit: int = 50


class HistoryStore:
    """Stores and queries historical benchmark runs.

    Usage::

        store = HistoryStore(storage_dir="/var/lib/lyra/benchmarks")
        store.save(run)
        recent = store.query(HistoryQuery(metric_name="latency_p95"))
        trend = store.get_trend("latency_p95", window=10)
    """

    def __init__(self, storage_dir: str = "/tmp/lyra_benchmark_history") -> None:
        self._dir = Path(storage_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._runs: dict[str, BenchmarkRun] = {}
        self._load_all()

    @property
    def run_count(self) -> int:
        return len(self._runs)

    def save(self, run: BenchmarkRun) -> None:
        self._runs[run.run_id] = run
        file_path = self._dir / f"{run.run_id}.json"
        file_path.write_text(
            json.dumps(
                {
                    "run_id": run.run_id,
                    "timestamp": run.timestamp,
                    "metrics": run.metrics,
                    "metadata": run.metadata,
                    "tag": run.tag,
                },
                indent=2,
            )
        )

    def get(self, run_id: str) -> BenchmarkRun | None:
        self._load_all()
        return self._runs.get(run_id)

    def query(self, query: HistoryQuery) -> list[BenchmarkRun]:
        self._load_all()
        results = list(self._runs.values())

        if query.metric_name:
            results = [r for r in results if query.metric_name in r.metrics]
        if query.tag:
            results = [r for r in results if r.tag == query.tag]
        if query.since is not None:
            results = [r for r in results if r.timestamp >= query.since]
        if query.until is not None:
            results = [r for r in results if r.timestamp <= query.until]

        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[: query.limit]

    def get_trend(self, metric_name: str, window: int = 10) -> list[float]:
        self._load_all()
        runs = sorted(
            [r for r in self._runs.values() if metric_name in r.metrics],
            key=lambda r: r.timestamp,
        )
        values = [r.metrics[metric_name] for r in runs[-window:]]
        if len(values) < 2:
            return values
        return values

    def get_latest(self) -> BenchmarkRun | None:
        self._load_all()
        if not self._runs:
            return None
        return max(self._runs.values(), key=lambda r: r.timestamp)

    def delete(self, run_id: str) -> None:
        self._runs.pop(run_id, None)
        file_path = self._dir / f"{run_id}.json"
        if file_path.exists():
            file_path.unlink()

    def list_runs(self) -> list[str]:
        self._load_all()
        return sorted(self._runs.keys())

    def clear(self) -> None:
        self._runs.clear()
        for f in self._dir.glob("*.json"):
            f.unlink()

    def _load_all(self) -> None:
        for f in sorted(self._dir.glob("*.json")):
            run_id = f.stem
            if run_id in self._runs:
                continue
            try:
                data = json.loads(f.read_text())
                self._runs[run_id] = BenchmarkRun(
                    run_id=data["run_id"],
                    timestamp=data["timestamp"],
                    metrics=data["metrics"],
                    metadata=data.get("metadata", {}),
                    tag=data.get("tag", ""),
                )
            except (json.JSONDecodeError, KeyError, OSError):
                pass
