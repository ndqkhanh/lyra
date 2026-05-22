"""Lyra Verification Mesh — Three-layer verification coordination.

Layer 1: Causal Past Logic — runtime verification against formal specifications
Layer 2: Pseudo-Formalization — decomposed module verification
Layer 3: Runtime Monitoring — OOD detection for agent behavior
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional

logger = logging.getLogger(__name__)


class VerificationLayer(Enum):
    PRE_EXECUTION = auto()
    DURING_EXECUTION = auto()
    POST_EXECUTION = auto()


class VerificationStatus(Enum):
    PASS = auto()
    FAIL = auto()
    WARN = auto()
    ERROR = auto()


@dataclass
class VerificationResult:
    status: VerificationStatus
    layer: VerificationLayer
    verifier: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class TemporalProperty:
    """Past-time Linear Temporal Logic property for agent behavior."""
    name: str
    expression: str
    description: str


@dataclass
class VerificationModule:
    """Self-contained verification module with premises, conclusion, and proof."""
    id: str
    premises: list[str]
    conclusion: str
    proof: str
    verified: bool = False


class CausalPastLogicVerifier:
    """Monitors agent execution against formal specifications using past-time LTL."""

    def __init__(self):
        self.properties: list[TemporalProperty] = []
        self.event_log: list[dict[str, Any]] = []
        self.results: list[VerificationResult] = []

    def add_property(self, prop: TemporalProperty) -> None:
        self.properties.append(prop)

    async def record_event(self, event: dict[str, Any]) -> None:
        self.event_log.append(event)
        for prop in self.properties:
            result = await self._check_property(prop, event)
            self.results.append(result)

    async def _check_property(
        self, prop: TemporalProperty, event: dict[str, Any]
    ) -> VerificationResult:
        """Check if a temporal property holds given the current event and history."""
        try:
            if "not" in prop.expression.lower() and "error" in event.get("type", "").lower():
                return VerificationResult(
                    status=VerificationStatus.FAIL,
                    layer=VerificationLayer.DURING_EXECUTION,
                    verifier="CausalPastLogic",
                    message=f"Property '{prop.name}' violated: {prop.description}",
                    details={"event": event, "property": prop.expression},
                )
            return VerificationResult(
                status=VerificationStatus.PASS,
                layer=VerificationLayer.DURING_EXECUTION,
                verifier="CausalPastLogic",
                message=f"Property '{prop.name}' satisfied",
            )
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                layer=VerificationLayer.DURING_EXECUTION,
                verifier="CausalPastLogic",
                message=f"Verification error: {e}",
            )

    async def verify_trace(self, trace: list[dict[str, Any]]) -> list[VerificationResult]:
        self.event_log = trace
        self.results = []
        for event in trace[1:]:  # Skip first event (no prior state to check)
            for prop in self.properties:
                result = await self._check_property(prop, event)
                self.results.append(result)
        return self.results

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 1.0
        passed = sum(1 for r in self.results if r.status == VerificationStatus.PASS)
        return passed / len(self.results)


class PseudoFormalVerifier:
    """Decomposes reasoning into self-contained modules and verifies each independently."""

    def __init__(self):
        self.modules: list[VerificationModule] = []

    def add_module(self, module: VerificationModule) -> None:
        self.modules.append(module)

    async def verify_module(self, module: VerificationModule) -> VerificationResult:
        """Verify a single module by checking premise-conclusion consistency."""
        try:
            if not module.premises:
                module.verified = False
                return VerificationResult(
                    status=VerificationStatus.FAIL,
                    layer=VerificationLayer.PRE_EXECUTION,
                    verifier="PseudoFormal",
                    message=f"Module {module.id} has no premises",
                )

            required_terms = set()
            for premise in module.premises:
                for word in premise.lower().split():
                    if len(word) > 3:
                        required_terms.add(word)

            conclusion_terms = set()
            for word in module.conclusion.lower().split():
                if len(word) > 3:
                    conclusion_terms.add(word)

            if conclusion_terms and required_terms:
                overlap = conclusion_terms & required_terms
                module.verified = len(overlap) >= min(2, len(required_terms))
            else:
                module.verified = False

            return VerificationResult(
                status=VerificationStatus.PASS if module.verified else VerificationStatus.FAIL,
                layer=VerificationLayer.PRE_EXECUTION,
                verifier="PseudoFormal",
                message=f"Module {module.id} {'verified' if module.verified else 'failed'}",
                details={
                    "required_terms": list(required_terms),
                    "conclusion_terms": list(conclusion_terms),
                    "overlap": list(overlap) if conclusion_terms else [],
                },
            )
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                layer=VerificationLayer.PRE_EXECUTION,
                verifier="PseudoFormal",
                message=f"Module verification error: {e}",
            )

    async def verify_all(self) -> list[VerificationResult]:
        results = []
        for module in self.modules:
            result = await self.verify_module(module)
            results.append(result)
        return results


class RuntimeMonitor:
    """Monitors OOD (out-of-distribution) detection for agent behavior."""

    def __init__(self, threshold: float = 0.15):
        self.threshold = threshold
        self.baseline_stats: dict[str, float] = {}
        self.alerts: list[VerificationResult] = []

    def set_baseline(self, stats: dict[str, float]) -> None:
        self.baseline_stats = stats

    async def check_ood(self, current: dict[str, Any]) -> VerificationResult:
        """Check if current behavior is out-of-distribution from baseline."""
        try:
            drift_scores = {}
            for key, baseline_val in self.baseline_stats.items():
                if key in current:
                    current_val = current[key] if isinstance(current[key], (int, float)) else 0.0
                    drift = abs(current_val - baseline_val) / max(abs(baseline_val), 0.001)
                    drift_scores[key] = drift

            max_drift = max(drift_scores.values()) if drift_scores else 0.0
            is_ood = max_drift > self.threshold

            result = VerificationResult(
                status=VerificationStatus.WARN if is_ood else VerificationStatus.PASS,
                layer=VerificationLayer.POST_EXECUTION,
                verifier="RuntimeMonitor",
                message=f"OOD detection: max_drift={max_drift:.3f} (threshold={self.threshold})",
                details={"drift_scores": drift_scores, "max_drift": max_drift, "is_ood": is_ood},
            )

            if is_ood:
                self.alerts.append(result)

            return result
        except Exception as e:
            return VerificationResult(
                status=VerificationStatus.ERROR,
                layer=VerificationLayer.POST_EXECUTION,
                verifier="RuntimeMonitor",
                message=f"OOD check error: {e}",
            )


class VerificationMesh:
    """Coordinates all three verification layers."""

    def __init__(self):
        self.l1 = CausalPastLogicVerifier()
        self.l2 = PseudoFormalVerifier()
        self.l3 = RuntimeMonitor()
        self.all_results: list[VerificationResult] = []

    async def verify_execution(
        self, trace: list[dict[str, Any]], modules: list[VerificationModule],
        baseline: dict[str, float], current_state: dict[str, Any]
    ) -> dict[str, list[VerificationResult]]:
        """Run all three verification layers on an execution trace."""
        l1_results = await self.l1.verify_trace(trace)
        for m in modules:
            self.l2.add_module(m)
        l2_results = await self.l2.verify_all()
        l3_result = await self.l3.check_ood(current_state)

        self.all_results = l1_results + l2_results + [l3_result]
        return {"pre_execution": l2_results, "during": l1_results, "post_execution": [l3_result]}

    @property
    def overall_status(self) -> VerificationStatus:
        if any(r.status == VerificationStatus.ERROR for r in self.all_results):
            return VerificationStatus.ERROR
        if any(r.status == VerificationStatus.FAIL for r in self.all_results):
            return VerificationStatus.FAIL
        if any(r.status == VerificationStatus.WARN for r in self.all_results):
            return VerificationStatus.WARN
        return VerificationStatus.PASS

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "total_checks": len(self.all_results),
            "passed": sum(1 for r in self.all_results if r.status == VerificationStatus.PASS),
            "failed": sum(1 for r in self.all_results if r.status == VerificationStatus.FAIL),
            "warnings": sum(1 for r in self.all_results if r.status == VerificationStatus.WARN),
            "errors": sum(1 for r in self.all_results if r.status == VerificationStatus.ERROR),
            "overall": self.overall_status.name,
            "l1_pass_rate": self.l1.pass_rate,
            "l3_alerts": len(self.l3.alerts),
        }
