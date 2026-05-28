"""Chaos Engineer Skill — resilience testing and failure injection planning.

Designs and validates chaos experiments:
- Fault injection scenarios
- Blast radius containment
- Steady-state hypothesis validation
- Automated rollback conditions
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ExperimentMaturity(StrEnum):
    NOT_STARTED = "not_started"
    BASIC = "basic"
    ADVANCED = "advanced"
    PRODUCTION_READY = "production_ready"


@dataclass(frozen=True)
class ChaosGap:
    domain: str
    maturity: ExperimentMaturity
    description: str
    next_step: str


class ChaosEngineerSkill:
    """Validates chaos engineering readiness and experiment designs."""

    _CHAOS_DOMAINS = frozenset({
        "network_latency", "pod_failure", "disk_failure", "dns_failure",
        "region_failure", "clock_skew", "resource_exhaustion", "dependency_failure",
    })

    def run(self, input_data: dict) -> dict:
        experiments = input_data.get("experiments", [])
        gaps: list[ChaosGap] = []

        covered = {e.get("domain", "") for e in experiments}
        for domain in self._CHAOS_DOMAINS:
            if domain not in covered:
                readable = domain.replace("_", " ").title()
                gaps.append(ChaosGap(domain, ExperimentMaturity.NOT_STARTED,
                    f"No experiment for '{readable}'.", f"Design a {readable} chaos experiment."))

        for exp in experiments:
            if not exp.get("steady_state_hypothesis"):
                gaps.append(ChaosGap(exp.get("domain", "unknown"), ExperimentMaturity.BASIC,
                    "Experiment lacks a steady-state hypothesis.",
                    "Define: 'The system is healthy when [metric] remains [threshold]'."))
            if not exp.get("blast_radius"):
                gaps.append(ChaosGap(exp.get("domain", "unknown"), ExperimentMaturity.BASIC,
                    "No blast radius defined — experiment may affect production.",
                    "Define blast radius: which services/users are affected and how to contain."))
            if not exp.get("rollback_condition"):
                gaps.append(ChaosGap(exp.get("domain", "unknown"), ExperimentMaturity.BASIC,
                    "No automated rollback condition defined.",
                    "Define: 'Abort experiment if [metric] exceeds [threshold] for [duration]'."))

        domains_covered = len(covered & self._CHAOS_DOMAINS)
        return {
            "gaps": [g.__dict__ for g in gaps],
            "domains_covered": domains_covered,
            "total_domains": len(self._CHAOS_DOMAINS),
            "maturity_score": domains_covered / len(self._CHAOS_DOMAINS) * 100,
            "ready_for_production": all(
                e.get("steady_state_hypothesis") and e.get("rollback_condition")
                for e in experiments
            ) and len(experiments) >= 4,
        }
