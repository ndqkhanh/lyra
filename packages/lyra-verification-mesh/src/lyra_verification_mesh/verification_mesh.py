"""Multi-layer verification orchestrator.

Coordinates three verification layers:
1. CPL (Continuous Prompt-Level) - Real-time prompt/output checking
2. Pseudo-Formal - Invariant and contract verification
3. Runtime Behavior - Sandbox execution monitoring

Plus cross-layer coordination and confidence aggregation.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

from .exceptions import VerificationFailedError, MeshConfigurationError

logger = logging.getLogger(__name__)


# ── Enums and data classes ──────────────────────────────────────────────


class VerificationLayer(Enum):
    """The three verification layers."""

    PRE_EXECUTION = auto()       # Before execution: formal checks
    DURING_EXECUTION = auto()    # During execution: CPL
    POST_EXECUTION = auto()      # After execution: runtime


class VerificationStatus(Enum):
    """Status of a verification check."""

    PASS = auto()
    FAIL = auto()
    WARN = auto()
    ERROR = auto()
    SKIPPED = auto()


@dataclass
class VerificationResult:
    """Result of a single verification check.

    Attributes:
        status: Pass, fail, warn, or error.
        layer: Which verification layer.
        verifier: Name of the verifier.
        check_name: Name of the check.
        message: Human-readable message.
        confidence: Confidence in this result (0-1).
        details: Additional context.
        timestamp: When the check was performed.
    """

    status: VerificationStatus
    layer: VerificationLayer
    verifier: str
    check_name: str = ""
    message: str = ""
    confidence: float = 1.0
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class TemporalProperty:
    """Past-time Linear Temporal Logic property for runtime monitoring."""

    name: str
    expression: str
    description: str
    severity: VerificationStatus = VerificationStatus.FAIL  # What happens when violated


@dataclass
class VerificationModule:
    """Self-contained verification module with premises and conclusion."""

    id: str
    premises: list[str]
    conclusion: str
    proof: str = ""
    verified: bool = False
    dependencies: list[str] = field(default_factory=list)


@dataclass
class LayerReport:
    """Aggregated report from one verification layer.

    Attributes:
        layer: Which layer.
        results: Individual check results.
        pass_count: Number of passes.
        fail_count: Number of failures.
        warn_count: Number of warnings.
        error_count: Number of errors.
        pass_rate: Fraction of checks that passed.
    """

    layer: VerificationLayer
    results: list[VerificationResult] = field(default_factory=list)

    @property
    def pass_count(self) -> int:
        return sum(1 for r in self.results if r.status == VerificationStatus.PASS)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if r.status == VerificationStatus.FAIL)

    @property
    def warn_count(self) -> int:
        return sum(1 for r in self.results if r.status == VerificationStatus.WARN)

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.status == VerificationStatus.ERROR)

    @property
    def pass_rate(self) -> float:
        total = len(self.results)
        if total == 0:
            return 1.0
        return self.pass_count / total


@dataclass
class MeshReport:
    """Aggregated report from all verification layers.

    Attributes:
        report_id: Unique identifier.
        timestamp: When the report was generated.
        layer_reports: Per-layer reports.
        overall_status: Worst status across all layers.
        confidence: Aggregate confidence score.
        attestation_id: Optional attestation reference.
    """

    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    layer_reports: dict[VerificationLayer, LayerReport] = field(default_factory=dict)
    overall_status: VerificationStatus = VerificationStatus.PASS
    confidence: float = 0.0
    attestation_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Confidence aggregation ──────────────────────────────────────────────


class ConfidenceAggregator:
    """Aggregates confidence scores across multiple verification layers.

    Supports weighted averaging, Dempster-Shafer combination, and
    configurable layer weighting.
    """

    def __init__(
        self,
        layer_weights: Optional[dict[VerificationLayer, float]] = None,
        aggregation_method: str = "weighted_mean",
    ) -> None:
        self.layer_weights = layer_weights or {
            VerificationLayer.PRE_EXECUTION: 0.3,
            VerificationLayer.DURING_EXECUTION: 0.4,
            VerificationLayer.POST_EXECUTION: 0.3,
        }
        self.aggregation_method = aggregation_method

    def aggregate(
        self,
        results: dict[VerificationLayer, list[VerificationResult]],
    ) -> tuple[float, VerificationStatus]:
        """Aggregate confidence across layers.

        Args:
            results: Per-layer verification results.

        Returns:
            Tuple of (aggregated_confidence, overall_status).
        """
        layer_confidences: dict[VerificationLayer, float] = {}
        layer_statuses: dict[VerificationLayer, VerificationStatus] = {}

        for layer, layer_results in results.items():
            if not layer_results:
                layer_confidences[layer] = 1.0
                layer_statuses[layer] = VerificationStatus.PASS
                continue

            # Compute layer confidence from individual results
            confidences = [r.confidence for r in layer_results]
            layer_confidences[layer] = sum(confidences) / len(confidences)

            # Worst status for the layer
            statuses = [r.status for r in layer_results]
            layer_statuses[layer] = self._worst_status(statuses)

        if self.aggregation_method == "dempster_shafer":
            confidence = self._dempster_shafer(layer_confidences)
        elif self.aggregation_method == "min":
            confidence = min(layer_confidences.values()) if layer_confidences else 1.0
        else:  # weighted_mean
            weighted_total = 0.0
            weight_sum = 0.0
            for layer, conf in layer_confidences.items():
                w = self.layer_weights.get(layer, 1.0)
                weighted_total += conf * w
                weight_sum += w
            confidence = weighted_total / max(weight_sum, 1e-10)

        overall_status = self._worst_status(list(layer_statuses.values()))
        return confidence, overall_status

    @staticmethod
    def _worst_status(statuses: list[VerificationStatus]) -> VerificationStatus:
        """Get the worst status from a list."""
        priority = {
            VerificationStatus.PASS: 0,
            VerificationStatus.SKIPPED: 1,
            VerificationStatus.WARN: 2,
            VerificationStatus.FAIL: 3,
            VerificationStatus.ERROR: 4,
        }
        return max(statuses, key=lambda s: priority.get(s, 0)) if statuses else VerificationStatus.PASS

    def _dempster_shafer(
        self, confidences: dict[VerificationLayer, float]
    ) -> float:
        """Simple Dempster-Shafer combination for confidence values."""
        combined = 1.0
        for conf in confidences.values():
            combined *= conf
        conflict = 1.0 - combined
        if conflict < 0.9999:
            return combined / (1.0 - conflict)
        return combined


# ── Verification mesh orchestrator ──────────────────────────────────────


class VerificationMesh:
    """Coordinates multi-layer verification.

    Orchestrates pre-execution (formal), during-execution (CPL),
    and post-execution (runtime) verification, aggregates results,
    and generates comprehensive verification reports.
    """

    def __init__(self) -> None:
        # Layer components (lazy initialization)
        self._cpl_verifier: Any = None
        self._formal_verifier: Any = None
        self._runtime_verifier: Any = None

        self._aggregator = ConfidenceAggregator()
        self._reports: deque[MeshReport] = deque(maxlen=1000)
        self._execution_history: deque[dict[str, Any]] = deque(maxlen=5000)

    @property
    def cpl(self) -> Any:
        """Get or lazily create CPL verifier."""
        if self._cpl_verifier is None:
            from .cpl_verifier import CPLVerifier
            self._cpl_verifier = CPLVerifier()
        return self._cpl_verifier

    @property
    def formal(self) -> Any:
        """Get or lazily create formal verifier."""
        if self._formal_verifier is None:
            from .formal_verifier import FormalVerifier
            self._formal_verifier = FormalVerifier()
        return self._formal_verifier

    @property
    def runtime(self) -> Any:
        """Get or lazily create runtime verifier."""
        if self._runtime_verifier is None:
            from .runtime_verifier import RuntimeVerifier
            self._runtime_verifier = RuntimeVerifier()
        return self._runtime_verifier

    async def verify_execution(
        self,
        trace: list[dict[str, Any]],
        modules: Optional[list[VerificationModule]] = None,
        baseline: Optional[dict[str, float]] = None,
        current_state: Optional[dict[str, Any]] = None,
        prompt_text: str = "",
        output_text: str = "",
    ) -> MeshReport:
        """Run all three verification layers on an execution.

        Args:
            trace: Execution trace events.
            modules: Modules for formal verification.
            baseline: Baseline for runtime OOD detection.
            current_state: Current execution state.
            prompt_text: The input prompt (for CPL).
            output_text: The generated output (for CPL).

        Returns:
            Comprehensive mesh report.
        """
        report = MeshReport()
        tasks = []

        # Layer 1: Pre-execution (formal)
        async def _run_formal() -> list[VerificationResult]:
            if modules:
                for m in modules:
                    self.formal.add_module(m)
                return await self.formal.verify_all()
            return []

        # Layer 2: During-execution (CPL)
        async def _run_cpl() -> list[VerificationResult]:
            cpl_results: list[VerificationResult] = []
            if prompt_text:
                cpl_results.append(
                    await self.cpl.verify_prompt(prompt_text)
                )
            if output_text:
                cpl_results.append(
                    await self.cpl.verify_output(output_text)
                )
            for event in trace:
                cpl_results.append(
                    await self.cpl.verify_event(event)
                )
            return cpl_results

        # Layer 3: Post-execution (runtime)
        async def _run_runtime() -> list[VerificationResult]:
            runtime_results: list[VerificationResult] = []
            if trace:
                runtime_results = await self.runtime.verify_trace(trace)
            if baseline and current_state:
                ood_result = await self.runtime.check_ood(current_state, baseline)
                runtime_results.append(ood_result)
            return runtime_results

        tasks = [
            _run_formal(),
            _run_cpl(),
            _run_runtime(),
        ]
        formal_results, cpl_results, runtime_results = await asyncio.gather(*tasks)

        # Build layer reports
        report.layer_reports = {
            VerificationLayer.PRE_EXECUTION: LayerReport(
                layer=VerificationLayer.PRE_EXECUTION,
                results=formal_results,
            ),
            VerificationLayer.DURING_EXECUTION: LayerReport(
                layer=VerificationLayer.DURING_EXECUTION,
                results=cpl_results,
            ),
            VerificationLayer.POST_EXECUTION: LayerReport(
                layer=VerificationLayer.POST_EXECUTION,
                results=runtime_results,
            ),
        }

        # Aggregate confidence
        layer_results_map = {
            VerificationLayer.PRE_EXECUTION: formal_results,
            VerificationLayer.DURING_EXECUTION: cpl_results,
            VerificationLayer.POST_EXECUTION: runtime_results,
        }
        confidence, status = self._aggregator.aggregate(layer_results_map)
        report.confidence = confidence
        report.overall_status = status

        self._reports.append(report)
        self._execution_history.append({
            "trace_length": len(trace),
            "status": status.name,
            "confidence": confidence,
            "timestamp": time.time(),
        })

        return report

    @property
    def overall_status(self) -> VerificationStatus:
        """Get the overall status from the latest report."""
        if not self._reports:
            return VerificationStatus.PASS
        return self._reports[-1].overall_status

    @property
    def latest_report(self) -> Optional[MeshReport]:
        """Get the most recent mesh report."""
        return self._reports[-1] if self._reports else None

    @property
    def summary(self) -> dict[str, Any]:
        """Get a summary of the verification mesh state."""
        if not self._reports:
            return {"status": "no_reports"}

        latest = self._reports[-1]
        all_reports = list(self._reports)

        # Compute aggregate stats across reports
        total_passes = sum(
            sum(1 for r in lr.results if r.status == VerificationStatus.PASS)
            for report in all_reports
            for lr in report.layer_reports.values()
        )
        total_fails = sum(
            sum(1 for r in lr.results if r.status == VerificationStatus.FAIL)
            for report in all_reports
            for lr in report.layer_reports.values()
        )

        return {
            "status": latest.overall_status.name,
            "confidence": latest.confidence,
            "total_reports": len(all_reports),
            "total_checks": total_passes + total_fails,
            "passes": total_passes,
            "fails": total_fails,
            "pass_rate": (
                total_passes / max(total_passes + total_fails, 1)
            ),
            "layer_summary": {
                layer.name: {
                    "pass_rate": lr.pass_rate,
                    "check_count": len(lr.results),
                }
                for layer, lr in latest.layer_reports.items()
            },
        }
