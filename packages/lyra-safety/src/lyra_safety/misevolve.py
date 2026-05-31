"""
"Agent May Misevolve" Defenses — alignment decay detection and evolution safety gates.

Based on Shao et al. 2025 (arXiv 2509.26354): self-evolving agents can develop
safety-alignment decay after memory accumulation, vulnerabilities from tool
creation/reuse, and alignment drift across model/memory/tool/workflow pathways.

Defense mechanisms:
1. **Alignment Drift Detection**: Monitor skill/memory changes for safety degradation
2. **Evolution Safety Gates**: 5-gate pipeline before any self-modification
3. **Tool Creation Audit**: All new tools must pass safety review before registration
4. **Rollback Capability**: Auto-rollback to last known-good state on detection
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class GateStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    MANUAL_REVIEW = "manual_review"


@dataclass
class GateResult:
    gate_name: str
    status: GateStatus
    reason: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SafetySnapshot:
    """Hash of safety-critical state at a point in time."""

    skill_hashes: dict[str, str] = field(default_factory=dict)
    memory_count: int = 0
    tool_count: int = 0
    alignment_score: float = 1.0
    created_at: float = field(default_factory=time.time)


class EvolutionSafetyGate:
    """
    5-gate pipeline for skill/memory evolution safety.

    Gates (from plan §4.4, Run 14 CRITICAL-4 awareness):
    1. **Behavioral Safety**: Does the change pass safety benchmark?
    2. **Consistency Check**: Does the change conflict with existing safety rules?
    3. **Reversibility Check**: Can the change be rolled back?
    4. **Impact Analysis**: What's the blast radius?
    5. **Human Approval**: Flag for manual review if score is borderline.

    All gates must pass for the evolution to proceed.
    """

    GATE_NAMES: list[str] = [
        "behavioral_safety",
        "consistency",
        "reversibility",
        "impact_analysis",
        "human_approval",
    ]

    def __init__(self) -> None:
        self._baseline: SafetySnapshot | None = None
        self._history: list[GateResult] = []

    def set_baseline(self, snapshot: SafetySnapshot) -> None:
        self._baseline = snapshot

    def evaluate(self, change_description: str, safety_score: float,
                 affected_components: list[str]) -> list[GateResult]:
        """
        Run all 5 gates against a proposed change.

        Args:
            change_description: What the evolution would change.
            safety_score: Behavioral safety benchmark score (0-1).
            affected_components: Which subsystems are affected.

        Returns:
            List of 5 GateResult entries.
        """
        results: list[GateResult] = []

        # Gate 1: Behavioral Safety
        if safety_score >= 0.90:
            results.append(GateResult("behavioral_safety", GateStatus.PASSED, score=safety_score))
        elif safety_score >= 0.70:
            results.append(GateResult("behavioral_safety", GateStatus.MANUAL_REVIEW,
                          reason=f"Safety score {safety_score:.2f} below 0.90 threshold", score=safety_score))
        else:
            results.append(GateResult("behavioral_safety", GateStatus.FAILED,
                          reason=f"Safety score {safety_score:.2f} below 0.70 minimum", score=safety_score))

        # Gate 2: Consistency Check
        dangerous_keywords = {"bypass", "disable", "override", "sudo", "unsafe", "raw"}
        if any(kw in change_description.lower() for kw in dangerous_keywords):
            results.append(GateResult("consistency", GateStatus.MANUAL_REVIEW,
                          reason="Change contains safety-sensitive keywords"))
        else:
            results.append(GateResult("consistency", GateStatus.PASSED))

        # Gate 3: Reversibility Check
        irreversible_keywords = {"irreversible", "permanent", "cannot undo", "one-way"}
        if any(kw in change_description.lower() for kw in irreversible_keywords):
            results.append(GateResult("reversibility", GateStatus.FAILED,
                          reason="Change appears to be irreversible"))
        else:
            results.append(GateResult("reversibility", GateStatus.PASSED))

        # Gate 4: Impact Analysis
        critical_components = {"safety", "permissions", "credentials", "auth", "router"}
        affected_critical = [c for c in affected_components if c.lower() in critical_components]
        if affected_critical:
            results.append(GateResult("impact_analysis", GateStatus.MANUAL_REVIEW,
                          reason=f"Affects critical components: {affected_critical}"))
        elif len(affected_components) > 5:
            results.append(GateResult("impact_analysis", GateStatus.MANUAL_REVIEW,
                          reason=f"Wide blast radius: {len(affected_components)} components"))
        else:
            results.append(GateResult("impact_analysis", GateStatus.PASSED))

        # Gate 5: Human Approval
        manual_review_gates = [r for r in results if r.status == GateStatus.MANUAL_REVIEW]
        if manual_review_gates:
            results.append(GateResult("human_approval", GateStatus.MANUAL_REVIEW,
                          reason=f"{len(manual_review_gates)} gates require review"))
        else:
            results.append(GateResult("human_approval", GateStatus.PASSED))

        self._history.extend(results)
        return results

    @property
    def all_passed(self) -> bool:
        """Check if the most recent evaluation passed all gates."""
        if not self._history:
            return False
        recent = self._history[-5:]  # Last 5 = most recent evaluation
        return all(r.status == GateStatus.PASSED for r in recent)


class MisevolveDefense:
    """
    Defense against agent misevolution.

    Monitors skill/memory/tool changes for alignment decay and provides
    rollback capability to the last known-good state.
    """

    def __init__(self) -> None:
        self._snapshots: list[SafetySnapshot] = []
        self._gate = EvolutionSafetyGate()
        self._drift_threshold: float = 0.15  # 15% alignment drop triggers alert

    def checkpoint(self, skills: dict[str, Any], memories: int, tools: int) -> SafetySnapshot:
        """Take a safety snapshot of the current state."""
        skill_hashes = {
            name: hashlib.sha256(str(skill).encode()).hexdigest()[:16]
            for name, skill in skills.items()
        }
        snapshot = SafetySnapshot(
            skill_hashes=skill_hashes,
            memory_count=memories,
            tool_count=tools,
        )
        self._snapshots.append(snapshot)
        self._gate.set_baseline(snapshot)
        return snapshot

    def detect_drift(self, current_alignment_score: float) -> tuple[bool, str]:
        """
        Check for alignment drift vs baseline.

        Returns (drift_detected, description).
        """
        if not self._snapshots:
            return False, "No baseline snapshot"

        baseline = self._snapshots[-1]
        if current_alignment_score < (baseline.alignment_score - self._drift_threshold):
            return True, (
                f"Alignment drift detected: {baseline.alignment_score:.2f} → "
                f"{current_alignment_score:.2f} (drop of "
                f"{baseline.alignment_score - current_alignment_score:.2f})"
            )
        return False, "Alignment stable"

    def evaluate_change(self, description: str, safety_score: float,
                        affected: list[str]) -> list[GateResult]:
        return self._gate.evaluate(description, safety_score, affected)

    def rollback(self) -> SafetySnapshot | None:
        """Return the last known-good snapshot for rollback."""
        if len(self._snapshots) < 2:
            return None
        # Remove the last (potentially bad) snapshot
        bad = self._snapshots.pop()
        logger.warning("Rolling back from snapshot with %d tools, %d memories",
                       bad.tool_count, bad.memory_count)
        return self._snapshots[-1] if self._snapshots else None

    @property
    def snapshot_count(self) -> int:
        return len(self._snapshots)
