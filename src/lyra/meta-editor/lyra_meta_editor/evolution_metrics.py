"""Track and measure self-evolution progress."""

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass
from typing import ClassVar

from .exceptions import EvolutionMetricsError


@dataclass(frozen=True)
class EvolutionConfig:
    """Configuration governing evolution metrics tracking."""

    track_cycles: bool = True
    baseline_file: str = ""
    data_dir: str = ""


@dataclass(frozen=True)
class EvolutionCycle:
    """A single evolution cycle record."""

    cycle_id: int
    timestamp: float
    files_changed: int
    quality_delta: float
    perf_delta: float
    test_delta: int


@dataclass(frozen=True)
class EvolutionReport:
    """Report summarizing all evolution cycles."""

    cycles: tuple[EvolutionCycle, ...]
    total_cycles: int
    quality_trend: tuple[float, ...]
    convergence_rate: float


class EvolutionMetrics:
    """Track and measure self-evolution progress."""

    DEFAULT_DATA_DIR: ClassVar[str] = os.path.join(
        tempfile.gettempdir(), "lyra_evolution"
    )

    def __init__(self, config: EvolutionConfig = EvolutionConfig()) -> None:
        self._config = config
        self._data_dir = config.data_dir or EvolutionMetrics.DEFAULT_DATA_DIR
        os.makedirs(self._data_dir, exist_ok=True)
        self._cycles: list[EvolutionCycle] = []
        self._load_cycles()

    def _data_path(self) -> str:
        return os.path.join(self._data_dir, "cycles.json")

    def _load_cycles(self) -> None:
        path = self._data_path()
        if not os.path.isfile(path):
            return
        try:
            with open(path) as f:
                data = json.load(f)
            for item in data:
                self._cycles.append(EvolutionCycle(**item))
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            self._cycles = []

    def _save_cycles(self) -> None:
        data = [
            {
                "cycle_id": c.cycle_id,
                "timestamp": c.timestamp,
                "files_changed": c.files_changed,
                "quality_delta": c.quality_delta,
                "perf_delta": c.perf_delta,
                "test_delta": c.test_delta,
            }
            for c in self._cycles
        ]
        path = self._data_path()
        try:
            with open(path, "w") as f:
                json.dump(data, f)
        except OSError as e:
            raise EvolutionMetricsError(
                f"Failed to save cycles: {e}"
            ) from e

    async def record_cycle(
        self, files_changed: int, quality: float, perf: float, tests: int
    ) -> EvolutionCycle:
        """Record a new evolution cycle."""
        if not self._config.track_cycles:
            raise EvolutionMetricsError("Cycle tracking is disabled")
        cycle_id = len(self._cycles) + 1
        cycle = EvolutionCycle(
            cycle_id=cycle_id,
            timestamp=time.time(),
            files_changed=files_changed,
            quality_delta=quality,
            perf_delta=perf,
            test_delta=tests,
        )
        self._cycles.append(cycle)
        self._save_cycles()
        return cycle

    async def get_progress(self) -> EvolutionReport:
        """Get the current evolution progress report."""
        if not self._cycles:
            return EvolutionReport(
                cycles=(),
                total_cycles=0,
                quality_trend=(),
                convergence_rate=0.0,
            )
        quality_trend = tuple(c.quality_delta for c in self._cycles)
        convergence_rate = await self.estimate_convergence()
        return EvolutionReport(
            cycles=tuple(self._cycles),
            total_cycles=len(self._cycles),
            quality_trend=quality_trend,
            convergence_rate=convergence_rate,
        )

    async def compare_to_baseline(self, baseline_path: str) -> dict:
        """Compare current metrics to a baseline file."""
        if not os.path.isfile(baseline_path):
            raise EvolutionMetricsError(
                f"Baseline file not found: {baseline_path}"
            )
        try:
            with open(baseline_path) as f:
                baseline_data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise EvolutionMetricsError(
                f"Cannot read baseline: {e}"
            ) from e

        comparison: dict = {
            "baseline_path": baseline_path,
            "current_cycles": len(self._cycles),
            "baseline_cycles": len(baseline_data.get("cycles", [])),
            "quality_comparison": {},
            "perf_comparison": {},
        }

        if self._cycles:
            avg_quality = sum(c.quality_delta for c in self._cycles) / len(self._cycles)
            avg_perf = sum(c.perf_delta for c in self._cycles) / len(self._cycles)
            comparison["quality_comparison"] = {
                "current_avg": round(avg_quality, 4),
                "baseline_avg": baseline_data.get("avg_quality", 0.0),
            }
            comparison["perf_comparison"] = {
                "current_avg": round(avg_perf, 4),
                "baseline_avg": baseline_data.get("avg_perf", 0.0),
            }

        return comparison

    async def estimate_convergence(self) -> float:
        """Estimate convergence rate based on quality delta variance."""
        if len(self._cycles) < 2:
            return 0.0
        qualities = [c.quality_delta for c in self._cycles]
        if len(qualities) >= 3:
            recent = qualities[-3:]
            mean = sum(recent) / len(recent)
            variance = sum((q - mean) ** 2 for q in recent) / len(recent)
            convergence = max(0.0, 1.0 - variance)
        else:
            convergence = 0.5
        return round(convergence, 4)
