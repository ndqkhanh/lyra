"""Runtime behavior verification: sandbox execution, side-effect detection, resource monitoring, output validation."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .verification_mesh import VerificationLayer, VerificationResult, VerificationStatus

logger = logging.getLogger(__name__)


# ── Data classes ────────────────────────────────────────────────────────


@dataclass
class ResourceLimits:
    """Resource usage limits for sandbox execution.

    Attributes:
        max_memory_mb: Maximum memory in MB.
        max_time_seconds: Maximum execution time.
        max_output_tokens: Maximum output length.
        max_file_operations: Maximum file system operations.
        max_network_requests: Maximum outbound requests.
        allowed_modules: Restricted set of importable modules.
        blocked_modules: Modules that are completely blocked.
    """

    max_memory_mb: float = 512.0
    max_time_seconds: float = 30.0
    max_output_tokens: int = 100_000
    max_file_operations: int = 100
    max_network_requests: int = 10
    allowed_modules: list[str] = field(default_factory=list)
    blocked_modules: list[str] = field(default_factory=lambda: [
        "os.system", "subprocess", "shutil.rmtree", "socket",
    ])


@dataclass
class SandboxMetrics:
    """Metrics collected during sandbox execution.

    Attributes:
        execution_time_ms: Total execution time.
        peak_memory_mb: Peak memory usage.
        output_length: Length of generated output.
        file_ops_count: Number of file operations.
        network_requests_count: Number of network requests.
        errors_count: Number of errors encountered.
    """

    execution_time_ms: float = 0.0
    peak_memory_mb: float = 0.0
    output_length: int = 0
    file_ops_count: int = 0
    network_requests_count: int = 0
    errors_count: int = 0


@dataclass
class SideEffect:
    """A detected side effect from execution.

    Attributes:
        effect_type: Type of side effect.
        description: Human-readable description.
        severity: How severe this side effect is.
        target: What was affected.
        reversible: Whether the effect can be undone.
    """

    effect_type: str
    description: str = ""
    severity: str = "low"  # low, medium, high, critical
    target: str = ""
    reversible: bool = True


# ── Runtime verifier ────────────────────────────────────────────────────


class RuntimeVerifier:
    """Verifies agent behavior at runtime.

    Monitors sandbox execution, detects side effects, validates
    resource usage, and checks outputs against specifications.
    """

    def __init__(
        self,
        resource_limits: ResourceLimits | None = None,
        ood_threshold: float = 0.15,
    ) -> None:
        self.resource_limits = resource_limits or ResourceLimits()
        self.ood_threshold = ood_threshold

        self._baseline_stats: dict[str, float] = {}
        self._side_effects: list[SideEffect] = []
        self._trace_metrics: dict[str, list[SandboxMetrics]] = {}
        self._alerts: list[VerificationResult] = []

    # ── Trace verification ──────────────────────────────────────────────

    async def verify_trace(
        self, trace: list[dict[str, Any]]
    ) -> list[VerificationResult]:
        """Verify an execution trace for runtime issues.

        Checks each event for errors, resource violations, and
        unexpected behavior patterns.

        Args:
            trace: The execution trace to verify.

        Returns:
            List of verification results from trace analysis.
        """
        results: list[VerificationResult] = []

        for i, event in enumerate(trace):
            # Check for error events
            if "error" in str(event.get("type", "")).lower():
                results.append(VerificationResult(
                    status=VerificationStatus.FAIL,
                    layer=VerificationLayer.POST_EXECUTION,
                    verifier="RuntimeVerifier",
                    check_name=f"trace_error_{i}",
                    message=f"Error event at position {i}: {event.get('message', 'unknown')}",
                    details={"event": event},
                ))

            # Check for timeout events
            if "timeout" in str(event.get("type", "")).lower():
                results.append(VerificationResult(
                    status=VerificationStatus.FAIL,
                    layer=VerificationLayer.POST_EXECUTION,
                    verifier="RuntimeVerifier",
                    check_name=f"trace_timeout_{i}",
                    message=f"Timeout at position {i}",
                    details={"event": event},
                ))

            # Check for large outputs
            if "output" in event:
                output = str(event["output"])
                if len(output) > self.resource_limits.max_output_tokens:
                    results.append(VerificationResult(
                        status=VerificationStatus.WARN,
                        layer=VerificationLayer.POST_EXECUTION,
                        verifier="RuntimeVerifier",
                        check_name=f"large_output_{i}",
                        message=f"Output exceeds token limit: {len(output)} > {self.resource_limits.max_output_tokens}",
                    ))

        # Check overall trace characteristics
        results.extend(self._check_trace_invariants(trace))

        if not results:
            results.append(VerificationResult(
                status=VerificationStatus.PASS,
                layer=VerificationLayer.POST_EXECUTION,
                verifier="RuntimeVerifier",
                check_name="trace_analysis",
                message=f"Trace of {len(trace)} events verified OK",
                confidence=1.0,
            ))

        return results

    def _check_trace_invariants(
        self, trace: list[dict[str, Any]]
    ) -> list[VerificationResult]:
        """Check trace invariants: structure, ordering, consistency."""
        results: list[VerificationResult] = []

        if not trace:
            results.append(VerificationResult(
                status=VerificationStatus.WARN,
                layer=VerificationLayer.POST_EXECUTION,
                verifier="RuntimeVerifier",
                check_name="empty_trace",
                message="Empty execution trace",
                confidence=0.8,
            ))
            return results

        # Check: first event should be start/input
        first_event_type = str(trace[0].get("type", "")).lower()
        if not any(word in first_event_type for word in ("start", "input", "begin", "init")):
            results.append(VerificationResult(
                status=VerificationStatus.WARN,
                layer=VerificationLayer.POST_EXECUTION,
                verifier="RuntimeVerifier",
                check_name="trace_start",
                message="Trace does not start with an initialization event",
                confidence=0.6,
            ))

        # Check: last event should be end/result
        last_event_type = str(trace[-1].get("type", "")).lower()
        if not any(word in last_event_type for word in ("end", "result", "finish", "complete", "output")):
            results.append(VerificationResult(
                status=VerificationStatus.WARN,
                layer=VerificationLayer.POST_EXECUTION,
                verifier="RuntimeVerifier",
                check_name="trace_end",
                message="Trace does not end with a completion event",
                confidence=0.6,
            ))

        # Check: no duplicate sequential events of the same type
        event_types = [str(e.get("type", "")) for e in trace]
        for i in range(len(event_types) - 1):
            if event_types[i] == event_types[i + 1] and event_types[i] not in ("token", "stream"):
                results.append(VerificationResult(
                    status=VerificationStatus.WARN,
                    layer=VerificationLayer.POST_EXECUTION,
                    verifier="RuntimeVerifier",
                    check_name="duplicate_events",
                    message=f"Duplicate sequential event type: {event_types[i]}",
                    confidence=0.5,
                ))
                break

        return results

    # ── OOD detection ───────────────────────────────────────────────────

    async def check_ood(
        self, current: dict[str, Any], baseline: dict[str, float] | None = None
    ) -> VerificationResult:
        """Check if current behavior is out-of-distribution.

        Compares current state features against baseline statistics
        and flags anomalous deviations.

        Args:
            current: Current execution state/features.
            baseline: Baseline statistics (uses stored if None).

        Returns:
            VerificationResult with OOD assessment.
        """
        if baseline is None:
            baseline = self._baseline_stats

        if not baseline:
            return VerificationResult(
                status=VerificationStatus.PASS,
                layer=VerificationLayer.POST_EXECUTION,
                verifier="RuntimeVerifier",
                check_name="ood_detection",
                message="No baseline set for OOD detection",
                confidence=0.3,
            )

        drift_scores: dict[str, float] = {}
        for key, baseline_val in baseline.items():
            if key in current:
                current_val = current[key]
                if not isinstance(current_val, (int, float)):
                    try:
                        current_val = float(len(current_val)) if hasattr(current_val, "__len__") else 0.0
                    except (ValueError, TypeError):
                        current_val = 0.0

                drift = abs(float(current_val) - baseline_val) / max(abs(baseline_val), 0.001)
                drift_scores[key] = drift

        if not drift_scores:
            return VerificationResult(
                status=VerificationStatus.PASS,
                layer=VerificationLayer.POST_EXECUTION,
                verifier="RuntimeVerifier",
                check_name="ood_detection",
                message="No comparable features found",
                confidence=0.5,
            )

        max_drift = max(drift_scores.values())
        mean_drift = float(np.mean(list(drift_scores.values())))
        is_ood = max_drift > self.ood_threshold

        result = VerificationResult(
            status=VerificationStatus.WARN if is_ood else VerificationStatus.PASS,
            layer=VerificationLayer.POST_EXECUTION,
            verifier="RuntimeVerifier",
            check_name="ood_detection",
            message=f"OOD check: max_drift={max_drift:.3f}, mean_drift={mean_drift:.3f} "
                    f"(threshold={self.ood_threshold})",
            confidence=min(1.0, (1.0 - max_drift) + 0.1),
            details={
                "drift_scores": drift_scores,
                "max_drift": max_drift,
                "mean_drift": mean_drift,
                "is_ood": is_ood,
            },
        )

        if is_ood:
            self._alerts.append(result)

        return result

    def set_baseline(self, stats: dict[str, float]) -> None:
        """Set baseline statistics for OOD comparison."""
        self._baseline_stats = dict(stats)
        logger.info("Runtime verifier baseline set with %d features", len(stats))

    # ── Sandbox verification ────────────────────────────────────────────

    async def verify_sandbox_execution(
        self, metrics: SandboxMetrics
    ) -> list[VerificationResult]:
        """Verify sandbox execution metrics against limits.

        Args:
            metrics: Collected sandbox metrics.

        Returns:
            List of verification results.
        """
        results: list[VerificationResult] = []
        limits = self.resource_limits

        if metrics.execution_time_ms > limits.max_time_seconds * 1000:
            results.append(VerificationResult(
                status=VerificationStatus.FAIL,
                layer=VerificationLayer.POST_EXECUTION,
                verifier="RuntimeVerifier",
                check_name="sandbox_time",
                message=f"Execution time exceeded: {metrics.execution_time_ms}ms > {limits.max_time_seconds * 1000}ms",
            ))

        if metrics.peak_memory_mb > limits.max_memory_mb:
            results.append(VerificationResult(
                status=VerificationStatus.FAIL,
                layer=VerificationLayer.POST_EXECUTION,
                verifier="RuntimeVerifier",
                check_name="sandbox_memory",
                message=f"Memory exceeded: {metrics.peak_memory_mb}MB > {limits.max_memory_mb}MB",
            ))

        if metrics.file_ops_count > limits.max_file_operations:
            results.append(VerificationResult(
                status=VerificationStatus.WARN,
                layer=VerificationLayer.POST_EXECUTION,
                verifier="RuntimeVerifier",
                check_name="sandbox_file_ops",
                message=f"File operations exceeded: {metrics.file_ops_count} > {limits.max_file_operations}",
            ))

        if not results:
            results.append(VerificationResult(
                status=VerificationStatus.PASS,
                layer=VerificationLayer.POST_EXECUTION,
                verifier="RuntimeVerifier",
                check_name="sandbox_limits",
                message="Sandbox execution within limits",
                details={"metrics": metrics},
            ))

        return results

    # ── Side effect detection ───────────────────────────────────────────

    def detect_side_effects(
        self, trace: list[dict[str, Any]]
    ) -> list[SideEffect]:
        """Detect side effects from execution trace.

        Args:
            trace: Execution trace to analyze.

        Returns:
            List of detected side effects.
        """
        effects: list[SideEffect] = []

        for event in trace:
            event_type = str(event.get("type", ""))
            event_data = str(event)

            # File system modifications
            if any(kw in event_type for kw in ("file", "write", "save", "create")):
                if any(kw in event_data for kw in ("/etc/", "/proc/", "C:\\Windows")):
                    effects.append(SideEffect(
                        effect_type="file_system",
                        description="Attempted restricted file system access",
                        severity="high",
                        target=event.get("path", "unknown"),
                        reversible=False,
                    ))

            # Network calls
            if any(kw in event_type for kw in ("http", "request", "fetch", "api")):
                effects.append(SideEffect(
                    effect_type="network",
                    description="Outbound network request",
                    severity="low",
                    target=event.get("url", event.get("endpoint", "unknown")),
                    reversible=True,
                ))

            # State mutation
            if any(kw in event_type for kw in ("mutate", "modify", "update", "delete")):
                effects.append(SideEffect(
                    effect_type="state_mutation",
                    description=f"State mutation: {event_type}",
                    severity="medium",
                    target=event.get("target", "unknown"),
                    reversible=event.get("reversible", True),
                ))

        self._side_effects.extend(effects)
        return effects

    # ── Output validation ──────────────────────────────────────────────

    async def validate_output(
        self,
        output: dict[str, Any],
        expected_schema: dict[str, str] | None = None,
    ) -> VerificationResult:
        """Validate output against expected schema.

        Args:
            output: The output to validate.
            expected_schema: Expected schema (field_name -> type).

        Returns:
            VerificationResult.
        """
        if expected_schema is None:
            return VerificationResult(
                status=VerificationStatus.PASS,
                layer=VerificationLayer.POST_EXECUTION,
                verifier="RuntimeVerifier",
                check_name="output_schema",
                message="No schema specified, output validation skipped",
                confidence=0.5,
            )

        missing_fields = []
        type_mismatches = []

        for field, expected_type in expected_schema.items():
            if field not in output:
                missing_fields.append(field)
            else:
                value = output[field]
                type_name = expected_type.lower()
                type_checks = {
                    "str": isinstance(value, str),
                    "int": isinstance(value, int),
                    "float": isinstance(value, (int, float)),
                    "bool": isinstance(value, bool),
                    "list": isinstance(value, list),
                    "dict": isinstance(value, dict),
                }
                if type_name in type_checks and not type_checks[type_name]:
                    type_mismatches.append(f"{field}: expected {expected_type}, got {type(value).__name__}")

        issues = []
        if missing_fields:
            issues.append(f"Missing fields: {missing_fields}")
        if type_mismatches:
            issues.append(f"Type mismatches: {type_mismatches}")

        if issues:
            return VerificationResult(
                status=VerificationStatus.FAIL,
                layer=VerificationLayer.POST_EXECUTION,
                verifier="RuntimeVerifier",
                check_name="output_schema",
                message="; ".join(issues),
                confidence=0.0,
                details={"missing_fields": missing_fields, "type_mismatches": type_mismatches},
            )

        return VerificationResult(
            status=VerificationStatus.PASS,
            layer=VerificationLayer.POST_EXECUTION,
            verifier="RuntimeVerifier",
            check_name="output_schema",
            message=f"Output matches schema ({len(expected_schema)} fields)",
            confidence=1.0,
        )

    # ── Statistics ──────────────────────────────────────────────────────

    @property
    def alert_count(self) -> int:
        """Number of OOD alerts raised."""
        return len(self._alerts)

    @property
    def side_effect_count(self) -> int:
        """Number of side effects detected."""
        return len(self._side_effects)

    @property
    def summary(self) -> dict[str, Any]:
        """Get runtime verifier summary."""
        return {
            "baseline_features": len(self._baseline_stats),
            "ood_threshold": self.ood_threshold,
            "alerts": self.alert_count,
            "side_effects": self.side_effect_count,
            "side_effect_types": list({e.effect_type for e in self._side_effects}),
            "resource_limits": {
                "max_memory_mb": self.resource_limits.max_memory_mb,
                "max_time_seconds": self.resource_limits.max_time_seconds,
                "max_output_tokens": self.resource_limits.max_output_tokens,
            },
        }
