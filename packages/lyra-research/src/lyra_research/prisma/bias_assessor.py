"""
Risk-of-Bias Assessment

Implements risk-of-bias assessment for systematic reviews.
Based on Cochrane Risk of Bias tool and PRISMA guidelines.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class BiasDomain(Enum):
    """Risk of bias domains"""
    SELECTION_BIAS = "selection_bias"
    PERFORMANCE_BIAS = "performance_bias"
    DETECTION_BIAS = "detection_bias"
    ATTRITION_BIAS = "attrition_bias"
    REPORTING_BIAS = "reporting_bias"


class RiskLevel(Enum):
    """Risk levels"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNCLEAR = "unclear"


@dataclass
class DomainAssessment:
    """Assessment for a single bias domain"""
    domain: BiasDomain
    risk: RiskLevel
    reason: str
    evidence: str = ""


@dataclass
class BiasAssessment:
    """Complete bias assessment for a study"""
    study_id: str
    domain_assessments: dict[BiasDomain, DomainAssessment]
    overall_risk: RiskLevel
    summary: str


class RiskOfBiasAssessor:
    """
    Assess risk of bias in included studies

    Implements Cochrane Risk of Bias tool across 5 domains.
    """

    def assess_study(self, study: dict[str, Any]) -> BiasAssessment:
        """
        Assess risk of bias across 5 domains

        Args:
            study: Study metadata and content

        Returns:
            BiasAssessment with domain-level and overall risk
        """
        assessments = {}

        # Assess each domain
        for domain in BiasDomain:
            assessor_method = getattr(self, f"assess_{domain.value}")
            assessments[domain] = assessor_method(study)

        # Calculate overall risk
        overall_risk = self.calculate_overall_risk(assessments)

        # Generate summary
        summary = self.generate_summary(assessments, overall_risk)

        return BiasAssessment(
            study_id=study.get("id", "unknown"),
            domain_assessments=assessments,
            overall_risk=overall_risk,
            summary=summary
        )

    def assess_selection_bias(self, study: dict[str, Any]) -> DomainAssessment:
        """
        Assess selection bias (random sequence generation, allocation concealment)

        Args:
            study: Study metadata

        Returns:
            DomainAssessment for selection bias
        """
        # Check for randomization
        methods = study.get("methods", "").lower()
        randomized = any(term in methods for term in ["random", "randomized", "rct"])

        # Check for allocation concealment
        concealment = "concealment" in methods or "blinded allocation" in methods

        if randomized and concealment:
            risk = RiskLevel.LOW
            reason = "Randomized with allocation concealment"
        elif randomized:
            risk = RiskLevel.MODERATE
            reason = "Randomized but no allocation concealment mentioned"
        else:
            risk = RiskLevel.HIGH
            reason = "No randomization mentioned"

        return DomainAssessment(
            domain=BiasDomain.SELECTION_BIAS,
            risk=risk,
            reason=reason,
            evidence=methods[:200]
        )

    def assess_performance_bias(self, study: dict[str, Any]) -> DomainAssessment:
        """
        Assess performance bias (blinding of participants and personnel)

        Args:
            study: Study metadata

        Returns:
            DomainAssessment for performance bias
        """
        methods = study.get("methods", "").lower()
        blinded = any(term in methods for term in ["blind", "blinded", "double-blind", "masked"])

        if "double-blind" in methods or "double blind" in methods:
            risk = RiskLevel.LOW
            reason = "Double-blind design"
        elif blinded:
            risk = RiskLevel.MODERATE
            reason = "Some blinding but not double-blind"
        else:
            risk = RiskLevel.HIGH
            reason = "No blinding mentioned"

        return DomainAssessment(
            domain=BiasDomain.PERFORMANCE_BIAS,
            risk=risk,
            reason=reason
        )

    def assess_detection_bias(self, study: dict[str, Any]) -> DomainAssessment:
        """
        Assess detection bias (blinding of outcome assessment)

        Args:
            study: Study metadata

        Returns:
            DomainAssessment for detection bias
        """
        methods = study.get("methods", "").lower()
        outcome_blinding = "outcome" in methods and "blind" in methods

        if outcome_blinding:
            risk = RiskLevel.LOW
            reason = "Outcome assessment blinded"
        else:
            risk = RiskLevel.MODERATE
            reason = "Outcome assessment blinding unclear"

        return DomainAssessment(
            domain=BiasDomain.DETECTION_BIAS,
            risk=risk,
            reason=reason
        )

    def assess_attrition_bias(self, study: dict[str, Any]) -> DomainAssessment:
        """
        Assess attrition bias (incomplete outcome data)

        Args:
            study: Study metadata

        Returns:
            DomainAssessment for attrition bias
        """
        results = study.get("results", "").lower()
        dropout_rate = study.get("dropout_rate", 0)

        if dropout_rate < 0.10:  # Less than 10% dropout
            risk = RiskLevel.LOW
            reason = f"Low dropout rate: {dropout_rate:.1%}"
        elif dropout_rate < 0.20:  # 10-20% dropout
            risk = RiskLevel.MODERATE
            reason = f"Moderate dropout rate: {dropout_rate:.1%}"
        else:
            risk = RiskLevel.HIGH
            reason = f"High dropout rate: {dropout_rate:.1%}"

        return DomainAssessment(
            domain=BiasDomain.ATTRITION_BIAS,
            risk=risk,
            reason=reason
        )

    def assess_reporting_bias(self, study: dict[str, Any]) -> DomainAssessment:
        """
        Assess reporting bias (selective reporting)

        Args:
            study: Study metadata

        Returns:
            DomainAssessment for reporting bias
        """
        # Check if study is pre-registered
        preregistered = study.get("preregistered", False)
        protocol_available = study.get("protocol_available", False)

        if preregistered and protocol_available:
            risk = RiskLevel.LOW
            reason = "Pre-registered with protocol available"
        elif preregistered or protocol_available:
            risk = RiskLevel.MODERATE
            reason = "Partial pre-registration or protocol"
        else:
            risk = RiskLevel.UNCLEAR
            reason = "Pre-registration status unclear"

        return DomainAssessment(
            domain=BiasDomain.REPORTING_BIAS,
            risk=risk,
            reason=reason
        )

    def calculate_overall_risk(self, assessments: dict[BiasDomain, DomainAssessment]) -> RiskLevel:
        """
        Calculate overall risk from domain assessments

        Args:
            assessments: Domain-level assessments

        Returns:
            Overall risk level
        """
        risks = [a.risk for a in assessments.values()]

        # If any domain is HIGH risk, overall is HIGH
        if RiskLevel.HIGH in risks:
            return RiskLevel.HIGH

        # If more than 2 domains are MODERATE, overall is MODERATE
        moderate_count = risks.count(RiskLevel.MODERATE)
        if moderate_count > 2:
            return RiskLevel.MODERATE

        # If all domains are LOW, overall is LOW
        if all(r == RiskLevel.LOW for r in risks):
            return RiskLevel.LOW

        # Otherwise, MODERATE
        return RiskLevel.MODERATE

    def generate_summary(self, assessments: dict[BiasDomain, DomainAssessment], overall_risk: RiskLevel) -> str:
        """
        Generate summary of bias assessment

        Args:
            assessments: Domain assessments
            overall_risk: Overall risk level

        Returns:
            Summary text
        """
        high_risk_domains = [d.name for d, a in assessments.items() if a.risk == RiskLevel.HIGH]
        moderate_risk_domains = [d.name for d, a in assessments.items() if a.risk == RiskLevel.MODERATE]

        summary = f"Overall risk: {overall_risk.value.upper()}. "

        if high_risk_domains:
            summary += f"High risk in: {', '.join(high_risk_domains)}. "

        if moderate_risk_domains:
            summary += f"Moderate risk in: {', '.join(moderate_risk_domains)}."

        return summary
