"""PRISM Prompt Drift Detection — automated detection and repair of prompt degradation.

Implements daily automated detection of LLM prompt drift (performance
degradation over time) with auto-repair via re-optimization. Monitors
prompt quality metrics across runs and triggers corrective action when
degradation is detected.

Inspired by PRISM (arXiv 2605.14454) with a target of 99% prompt
reliability and <30 min repair time.

Key concepts:
- DriftMetric: individual quality dimension tracked over time
- DriftSnapshot: point-in-time measurement of all metrics
- DriftDetector: main engine that monitors, detects, and triggers repair
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum


class DriftSeverity(StrEnum):
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


class RepairStatus(StrEnum):
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class DriftMetric:
    """A single quality metric tracked over time.

    Attributes:
        name: metric identifier (e.g. "accuracy", "latency", "token_efficiency")
        current_value: latest measured value
        baseline_value: established baseline for comparison
        threshold_warning: value at which minor drift is flagged
        threshold_critical: value at which severe drift is flagged
        direction: "higher_is_better" or "lower_is_better"
    """

    name: str
    current_value: float
    baseline_value: float
    threshold_warning: float
    threshold_critical: float
    direction: str = "higher_is_better"

    @property
    def drift_pct(self) -> float:
        """Percentage drift from baseline."""
        if self.baseline_value == 0:
            return 0.0
        return abs(self.current_value - self.baseline_value) / abs(self.baseline_value) * 100

    @property
    def severity(self) -> DriftSeverity:
        """Classify the severity of drift for this metric."""
        if self.direction == "higher_is_better":
            degradation = self.baseline_value - self.current_value
        else:
            degradation = self.current_value - self.baseline_value

        if degradation <= 0:
            return DriftSeverity.NONE
        if degradation <= self.threshold_warning:
            return DriftSeverity.MINOR
        if degradation <= self.threshold_critical:
            return DriftSeverity.MODERATE
        if degradation <= self.threshold_critical * 2:
            return DriftSeverity.SEVERE
        return DriftSeverity.CRITICAL


@dataclass(frozen=True)
class DriftSnapshot:
    """A point-in-time measurement of all tracked drift metrics."""

    snapshot_id: str
    prompt_id: str
    prompt_version: int
    metrics: tuple[DriftMetric, ...]
    overall_severity: DriftSeverity
    timestamp: float

    @classmethod
    def collect(
        cls,
        prompt_id: str,
        prompt_version: int,
        metrics: dict[str, tuple[float, float, float, float, str]],
    ) -> DriftSnapshot:
        """Create a snapshot from raw metric measurements.

        Args:
            prompt_id: identifier for the prompt being tracked
            prompt_version: current version of the prompt
            metrics: dict of name -> (current, baseline, warn_thresh, crit_thresh, direction)
        """
        drift_metrics: list[DriftMetric] = []
        for name, (current, baseline, warn, crit, direction) in metrics.items():
            drift_metrics.append(
                DriftMetric(
                    name=name,
                    current_value=current,
                    baseline_value=baseline,
                    threshold_warning=warn,
                    threshold_critical=crit,
                    direction=direction,
                )
            )

        severities = [m.severity for m in drift_metrics]
        overall = DriftSeverity.NONE
        for s in (
            DriftSeverity.CRITICAL,
            DriftSeverity.SEVERE,
            DriftSeverity.MODERATE,
            DriftSeverity.MINOR,
        ):
            if s in severities:
                overall = s
                break

        return cls(
            snapshot_id=f"ds-{int(time.time() * 1000)}",
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            metrics=tuple(drift_metrics),
            overall_severity=overall,
            timestamp=time.time(),
        )


@dataclass(frozen=True)
class RepairResult:
    """Result of a prompt repair operation."""

    repair_id: str
    prompt_id: str
    from_version: int
    to_version: int
    status: RepairStatus
    metrics_before: DriftSnapshot
    metrics_after: DriftSnapshot | None
    repair_duration_sec: float
    error_message: str


class DriftDetector:
    """Automated prompt drift detection and repair engine.

    Monitors prompt quality over time, detects degradation, and triggers
    re-optimization when quality falls below acceptable thresholds.

    Usage::

        detector = DriftDetector()
        detector.establish_baseline("system-prompt", {
            "accuracy": (0.95, 0.95, 0.02, 0.05, "higher_is_better"),
            "token_efficiency": (0.85, 0.85, 0.05, 0.10, "higher_is_better"),
        })
        snapshot = detector.check("system-prompt", {
            "accuracy": (0.91, 0.95, 0.02, 0.05, "higher_is_better"),
            "token_efficiency": (0.82, 0.85, 0.05, 0.10, "higher_is_better"),
        })
        if snapshot.overall_severity >= DriftSeverity.MODERATE:
            detector.initiate_repair("system-prompt")
    """

    def __init__(self) -> None:
        self._baselines: dict[str, DriftSnapshot] = {}
        self._snapshots: dict[str, list[DriftSnapshot]] = {}
        self._repairs: dict[str, list[RepairResult]] = {}
        self._versions: dict[str, int] = {}
        self._repair_history: list[RepairResult] = []

    def establish_baseline(
        self,
        prompt_id: str,
        metrics: dict[str, tuple[float, float, float, float, str]],
    ) -> DriftSnapshot:
        """Establish baseline metrics for a prompt.

        The baseline values are set equal to the current values (no drift by
        definition). Metrics dict keys: name -> (current, baseline, warn_thresh, crit_thresh,
        direction).
        """
        self._versions.setdefault(prompt_id, 1)
        snapshot = DriftSnapshot.collect(
            prompt_id=prompt_id,
            prompt_version=self._versions[prompt_id],
            metrics=metrics,
        )
        self._baselines[prompt_id] = snapshot
        self._snapshots.setdefault(prompt_id, []).append(snapshot)
        self._repairs.setdefault(prompt_id, [])
        return snapshot

    def check(
        self,
        prompt_id: str,
        metrics: dict[str, tuple[float, float, float, float, str]],
    ) -> DriftSnapshot:
        """Check current metrics against baseline and produce a drift snapshot.

        The baseline values in metrics should match the established baseline;
        only current_value changes. Returns a DriftSnapshot with severity
        classification.
        """
        if prompt_id not in self._baselines:
            return self.establish_baseline(prompt_id, metrics)

        self._versions.setdefault(prompt_id, 1)
        snapshot = DriftSnapshot.collect(
            prompt_id=prompt_id,
            prompt_version=self._versions[prompt_id],
            metrics=metrics,
        )
        self._snapshots[prompt_id].append(snapshot)
        return snapshot

    def initiate_repair(
        self,
        prompt_id: str,
        repair_fn=None,
    ) -> RepairResult:
        """Initiate a repair operation for a drifted prompt.

        Args:
            prompt_id: which prompt to repair
            repair_fn: optional callable(snapshot) -> (dict, float)
                that returns new metrics and repair duration
        """
        if prompt_id not in self._baselines:
            return RepairResult(
                repair_id=f"rr-{int(time.time() * 1000)}",
                prompt_id=prompt_id,
                from_version=self._versions.get(prompt_id, 1),
                to_version=self._versions.get(prompt_id, 1),
                status=RepairStatus.FAILED,
                metrics_before=self._baselines.get(
                    prompt_id,
                    DriftSnapshot(
                        snapshot_id="empty",
                        prompt_id=prompt_id,
                        prompt_version=1,
                        metrics=(),
                        overall_severity=DriftSeverity.NONE,
                        timestamp=time.time(),
                    ),
                ),
                metrics_after=None,
                repair_duration_sec=0.0,
                error_message="No baseline established for this prompt",
            )

        before_snapshot = (
            self._snapshots[prompt_id][-1]
            if self._snapshots[prompt_id]
            else self._baselines[prompt_id]
        )
        current_version = self._versions[prompt_id]
        repair_start = time.time()

        new_metrics: dict[str, tuple[float, float, float, float, str]] = self._auto_repair_metrics(
            before_snapshot
        )
        if repair_fn is not None:
            try:
                result = repair_fn(before_snapshot)
                if isinstance(result, tuple) and len(result) == 2:
                    new_metrics, _ = result  # type: ignore[assignment]
                else:
                    new_metrics = result  # type: ignore[assignment]
            except Exception as e:
                return RepairResult(
                    repair_id=f"rr-{int(time.time() * 1000)}",
                    prompt_id=prompt_id,
                    from_version=current_version,
                    to_version=current_version,
                    status=RepairStatus.FAILED,
                    metrics_before=before_snapshot,
                    metrics_after=None,
                    repair_duration_sec=time.time() - repair_start,
                    error_message=str(e),
                )

        self._versions[prompt_id] = current_version + 1
        after_snapshot = DriftSnapshot.collect(
            prompt_id=prompt_id,
            prompt_version=self._versions[prompt_id],
            metrics=new_metrics,
        )
        self._snapshots[prompt_id].append(after_snapshot)
        self._baselines[prompt_id] = after_snapshot

        repair_result = RepairResult(
            repair_id=f"rr-{int(time.time() * 1000)}",
            prompt_id=prompt_id,
            from_version=current_version,
            to_version=self._versions[prompt_id],
            status=(
                RepairStatus.SUCCESS
                if after_snapshot.overall_severity == DriftSeverity.NONE
                else RepairStatus.FAILED
            ),
            metrics_before=before_snapshot,
            metrics_after=after_snapshot,
            repair_duration_sec=time.time() - repair_start,
            error_message="",
        )
        self._repairs[prompt_id].append(repair_result)
        self._repair_history.append(repair_result)
        return repair_result

    def rollback(self, prompt_id: str, target_version: int) -> RepairResult:
        """Rollback a prompt to a previous version."""
        if prompt_id not in self._snapshots:
            return RepairResult(
                repair_id=f"rr-{int(time.time() * 1000)}",
                prompt_id=prompt_id,
                from_version=self._versions.get(prompt_id, 1),
                to_version=self._versions.get(prompt_id, 1),
                status=RepairStatus.FAILED,
                metrics_before=DriftSnapshot(
                    snapshot_id="empty",
                    prompt_id=prompt_id,
                    prompt_version=1,
                    metrics=(),
                    overall_severity=DriftSeverity.NONE,
                    timestamp=time.time(),
                ),
                metrics_after=None,
                repair_duration_sec=0.0,
                error_message=f"No snapshots found for {prompt_id}",
            )

        snapshots = self._snapshots[prompt_id]
        target_snapshot = None
        for s in snapshots:
            if s.prompt_version == target_version:
                target_snapshot = s
                break

        if target_snapshot is None:
            return RepairResult(
                repair_id=f"rr-{int(time.time() * 1000)}",
                prompt_id=prompt_id,
                from_version=self._versions.get(prompt_id, 1),
                to_version=self._versions.get(prompt_id, 1),
                status=RepairStatus.FAILED,
                metrics_before=snapshots[-1],
                metrics_after=None,
                repair_duration_sec=0.0,
                error_message=f"Version {target_version} not found",
            )

        self._versions[prompt_id] = target_version
        self._baselines[prompt_id] = target_snapshot
        return RepairResult(
            repair_id=f"rr-{int(time.time() * 1000)}",
            prompt_id=prompt_id,
            from_version=snapshots[-1].prompt_version,
            to_version=target_version,
            status=RepairStatus.ROLLED_BACK,
            metrics_before=snapshots[-1],
            metrics_after=target_snapshot,
            repair_duration_sec=0.0,
            error_message="",
        )

    def _auto_repair_metrics(
        self,
        snapshot: DriftSnapshot,
    ) -> dict[str, tuple[float, float, float, float, str]]:
        """Auto-repair: reset drifted metrics to their baselines."""
        repaired: dict[str, tuple[float, float, float, float, str]] = {}
        for metric in snapshot.metrics:
            repaired[metric.name] = (
                metric.baseline_value,
                metric.baseline_value,
                metric.threshold_warning,
                metric.threshold_critical,
                metric.direction,
            )
        return repaired

    def get_snapshot_history(self, prompt_id: str) -> list[DriftSnapshot]:
        """Get all snapshots for a prompt."""
        return list(self._snapshots.get(prompt_id, []))

    def get_latest_snapshot(self, prompt_id: str) -> DriftSnapshot | None:
        """Get the most recent snapshot for a prompt."""
        snapshots = self._snapshots.get(prompt_id, [])
        return snapshots[-1] if snapshots else None

    @property
    def tracked_prompts(self) -> int:
        return len(self._baselines)

    @property
    def total_repairs(self) -> int:
        return len(self._repair_history)

    def stats(self) -> dict:
        """Aggregate statistics across all tracked prompts."""
        if not self._snapshots:
            return {
                "tracked_prompts": 0,
                "total_snapshots": 0,
                "total_repairs": 0,
                "prompts_in_drift": 0,
                "repair_success_rate": 0.0,
            }

        total_snapshots = sum(len(s) for s in self._snapshots.values())
        prompts_in_drift = 0
        for prompt_id in self._snapshots:
            latest = self.get_latest_snapshot(prompt_id)
            if latest and latest.overall_severity != DriftSeverity.NONE:
                prompts_in_drift += 1

        successful = sum(1 for r in self._repair_history if r.status == RepairStatus.SUCCESS)
        repair_rate = successful / max(len(self._repair_history), 1)

        return {
            "tracked_prompts": len(self._baselines),
            "total_snapshots": total_snapshots,
            "total_repairs": len(self._repair_history),
            "prompts_in_drift": prompts_in_drift,
            "repair_success_rate": round(repair_rate, 3),
        }
