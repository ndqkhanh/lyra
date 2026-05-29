"""Gate enforcer — Enforces quality gates with retry/reject/escalate logic."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lyra_research.quality.analysis_gate import AnalysisGate
from lyra_research.quality.curation_gate import CurationGate
from lyra_research.quality.discovery_gate import DiscoveryGate
from lyra_research.quality.quality_gate import GateResult, QualityGate
from lyra_research.quality.review_gate import ReviewGate
from lyra_research.quality.synthesis_gate import SynthesisGate


@dataclass
class EnforcementResult:
    """Result from gate enforcement."""

    passed: bool
    result: GateResult
    action: str  # "pass", "retry", "reject", "escalate"
    message: str = ""


class GateEnforcer:
    """
    Gate enforcer — Enforces quality gates between role transitions.

    Actions:
    - pass: Gate passed, continue to next role
    - retry: Gate failed but retryable (non-critical failures)
    - reject: Gate failed with critical issues, cannot proceed
    - escalate: Gate failed after max retries, needs human review
    """

    def __init__(self) -> None:
        """Initialize gate enforcer with all gates."""
        self.gates: dict[str, QualityGate] = {
            "discovery": DiscoveryGate(),
            "analysis": AnalysisGate(),
            "synthesis": SynthesisGate(),
            "review": ReviewGate(),
            "curation": CurationGate(),
        }
        self.history: list[EnforcementResult] = []

    def enforce(
        self, gate_name: str, data: Any, max_retries: int = 2
    ) -> EnforcementResult:
        """
        Enforce quality gate on data.

        Args:
            gate_name: Name of gate to enforce
            data: Data to check against gate
            max_retries: Maximum number of retries allowed

        Returns:
            EnforcementResult with action (pass/retry/reject/escalate)

        Raises:
            ValueError: If gate_name is invalid
        """
        if gate_name not in self.gates:
            raise ValueError(
                f"Invalid gate name: {gate_name}. Valid gates: {list(self.gates.keys())}"
            )

        gate = self.gates[gate_name]

        # Get retry count from previous attempts (use gate's actual name, not key)
        retry_count = self._get_retry_count(gate.name)

        # Check gate
        result = gate.check(data, retry_count=retry_count)

        # Determine action
        if result.passed:
            enforcement = EnforcementResult(
                passed=True,
                result=result,
                action="pass",
                message=f"{gate_name} gate passed",
            )
        elif result.has_critical_failures():
            # Critical failures cannot be retried
            enforcement = EnforcementResult(
                passed=False,
                result=result,
                action="reject",
                message=f"{gate_name} gate rejected: critical failures",
            )
        elif retry_count >= max_retries:
            # Max retries exceeded, escalate
            enforcement = EnforcementResult(
                passed=False,
                result=result,
                action="escalate",
                message=f"{gate_name} gate escalated: max retries ({max_retries}) exceeded",
            )
        else:
            # Non-critical failures, can retry
            enforcement = EnforcementResult(
                passed=False,
                result=result,
                action="retry",
                message=f"{gate_name} gate retry: attempt {retry_count + 1}/{max_retries}",
            )

        # Store in history
        self.history.append(enforcement)

        return enforcement

    def _get_retry_count(self, gate_name: str) -> int:
        """
        Get retry count for a specific gate from history.

        Args:
            gate_name: Gate name

        Returns:
            Number of previous attempts for this gate
        """
        # Count recent attempts for this gate (since last pass)
        count = 0
        for enforcement in reversed(self.history):
            if enforcement.result.gate_name == gate_name:
                if enforcement.passed:
                    # Found a pass, stop counting
                    break
                count += 1
        return count

    def get_gate_stats(self, gate_name: str) -> dict[str, Any]:
        """
        Get statistics for a specific gate.

        Args:
            gate_name: Gate name (key, e.g., 'discovery')

        Returns:
            Dict with gate statistics
        """
        if gate_name not in self.gates:
            raise ValueError(f"Invalid gate name: {gate_name}")

        gate = self.gates[gate_name]

        # Get enforcement history for this gate (use gate's actual name)
        gate_history = [
            e for e in self.history if e.result.gate_name == gate.name
        ]

        if not gate_history:
            return {
                "gate_name": gate_name,
                "total_attempts": 0,
                "pass_rate": 0.0,
                "avg_retry_count": 0.0,
                "rejection_rate": 0.0,
                "escalation_rate": 0.0,
            }

        total = len(gate_history)
        passed = sum(1 for e in gate_history if e.passed)
        rejected = sum(1 for e in gate_history if e.action == "reject")
        escalated = sum(1 for e in gate_history if e.action == "escalate")
        retries = sum(e.result.retry_count for e in gate_history)

        return {
            "gate_name": gate_name,
            "total_attempts": total,
            "pass_rate": passed / total if total > 0 else 0.0,
            "avg_retry_count": retries / total if total > 0 else 0.0,
            "rejection_rate": rejected / total if total > 0 else 0.0,
            "escalation_rate": escalated / total if total > 0 else 0.0,
            "criterion_stats": gate.get_criterion_stats(),
        }

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """
        Get statistics for all gates.

        Returns:
            Dict mapping gate name to statistics
        """
        return {gate_name: self.get_gate_stats(gate_name) for gate_name in self.gates}

    def reset_history(self) -> None:
        """Reset enforcement history."""
        self.history.clear()
        for gate in self.gates.values():
            gate.history.clear()
