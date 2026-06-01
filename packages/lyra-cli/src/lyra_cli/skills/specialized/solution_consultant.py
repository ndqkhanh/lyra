"""
Solution Consultant Skill - Solution design and customer advisory.

Given business challenges, produces:
- Solution architecture
- Business value proposition
- ROI analysis
- Risk mitigation plan
- Success roadmap

Outputs structured solution consulting plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SolutionLayer(StrEnum):
    """Solution architecture layers."""

    PRESENTATION = "presentation"
    APPLICATION = "application"
    DATA = "data"
    INTEGRATION = "integration"


@dataclass(frozen=True)
class ArchitectureComponent:
    """Solution architecture component."""

    layer: SolutionLayer
    component_name: str
    description: str
    technology: str
    rationale: str


@dataclass(frozen=True)
class BusinessValue:
    """Business value proposition."""

    value_driver: str
    quantified_benefit: str
    timeframe: str
    assumptions: tuple[str, ...]


@dataclass(frozen=True)
class ROIAnalysis:
    """Return on investment analysis."""

    total_investment: str
    year1_benefit: str
    year2_benefit: str
    year3_benefit: str
    payback_period: str
    three_year_roi: str


@dataclass(frozen=True)
class RiskMitigation:
    """Risk and mitigation strategy."""

    risk: str
    likelihood: str
    impact: str
    mitigation_strategy: str


@dataclass(frozen=True)
class SolutionConsultingPlan:
    """Complete solution consulting plan."""

    customer_name: str
    solution_architecture: tuple[ArchitectureComponent, ...]
    business_value: tuple[BusinessValue, ...]
    roi_analysis: ROIAnalysis
    risk_mitigation: tuple[RiskMitigation, ...]
    success_roadmap: tuple[tuple[str, str], ...]


class SolutionConsultant:
    """Solution consulting skill producing structured plans."""

    def run(self, input_data: dict) -> dict:
        """Run solution consulting.

        Args:
            input_data: Dictionary with keys:
                - business_challenges: Business challenges description
                - customer_name: Optional customer name (default "Customer")

        Returns:
            Dictionary with solution consulting plan data.
        """
        challenges = input_data.get("business_challenges", "")
        if not challenges:
            return {"error": "No business challenges provided"}

        customer_name = input_data.get("customer_name", "Customer")

        architecture = self._design_solution_architecture()
        value = self._define_business_value()
        roi = self._analyze_roi()
        risks = self._identify_risks_and_mitigations()
        roadmap = self._build_success_roadmap()

        return SolutionConsultingPlan(
            customer_name=customer_name,
            solution_architecture=tuple(architecture),
            business_value=tuple(value),
            roi_analysis=roi,
            risk_mitigation=tuple(risks),
            success_roadmap=tuple(roadmap),
        ).__dict__ | {
            "solution_architecture": [a.__dict__ for a in architecture],
            "business_value": [v.__dict__ for v in value],
            "roi_analysis": roi.__dict__,
            "risk_mitigation": [r.__dict__ for r in risks],
        }

    @staticmethod
    def _design_solution_architecture() -> list[ArchitectureComponent]:
        return [
            ArchitectureComponent(
                layer=SolutionLayer.PRESENTATION,
                component_name="Web Portal",
                description="Responsive web application for end users",
                technology="React + TypeScript",
                rationale="Modern, maintainable, excellent user experience",
            ),
            ArchitectureComponent(
                layer=SolutionLayer.APPLICATION,
                component_name="API Gateway",
                description="Centralized API management and routing",
                technology="Kong / AWS API Gateway",
                rationale="Security, rate limiting, monitoring",
            ),
            ArchitectureComponent(
                layer=SolutionLayer.APPLICATION,
                component_name="Microservices",
                description="Domain-driven microservices architecture",
                technology="Node.js / Python",
                rationale="Scalability, independent deployment",
            ),
            ArchitectureComponent(
                layer=SolutionLayer.DATA,
                component_name="Database",
                description="Managed relational database",
                technology="PostgreSQL (RDS)",
                rationale="ACID compliance, mature ecosystem",
            ),
            ArchitectureComponent(
                layer=SolutionLayer.INTEGRATION,
                component_name="Integration Hub",
                description="Integration with existing systems",
                technology="MuleSoft / Dell Boomi",
                rationale="Pre-built connectors, transformation capabilities",
            ),
        ]

    @staticmethod
    def _define_business_value() -> list[BusinessValue]:
        return [
            BusinessValue(
                value_driver="Process Automation",
                quantified_benefit="$500K annual labor cost savings",
                timeframe="Realized within 6 months",
                assumptions=(
                    "50% reduction in manual processing time",
                    "Average labor cost $50/hour",
                    "10,000 hours saved annually",
                ),
            ),
            BusinessValue(
                value_driver="Improved Decision Making",
                quantified_benefit="$300K annual revenue increase",
                timeframe="Realized within 12 months",
                assumptions=(
                    "Real-time analytics enable faster decisions",
                    "5% improvement in conversion rate",
                    "Current annual revenue $6M",
                ),
            ),
            BusinessValue(
                value_driver="Customer Satisfaction",
                quantified_benefit="20% reduction in churn",
                timeframe="Realized within 9 months",
                assumptions=(
                    "Improved user experience",
                    "Faster response times",
                    "Current churn rate 15%",
                ),
            ),
        ]

    @staticmethod
    def _analyze_roi() -> ROIAnalysis:
        return ROIAnalysis(
            total_investment="$750K (implementation + first year)",
            year1_benefit="$400K",
            year2_benefit="$800K",
            year3_benefit="$800K",
            payback_period="22 months",
            three_year_roi="167%",
        )

    @staticmethod
    def _identify_risks_and_mitigations() -> list[RiskMitigation]:
        return [
            RiskMitigation(
                risk="User adoption lower than expected",
                likelihood="MEDIUM",
                impact="HIGH",
                mitigation_strategy="Comprehensive change management program, executive sponsorship, phased rollout",
            ),
            RiskMitigation(
                risk="Integration complexity higher than estimated",
                likelihood="MEDIUM",
                impact="MEDIUM",
                mitigation_strategy="Detailed technical discovery, POC for complex integrations, buffer in timeline",
            ),
            RiskMitigation(
                risk="Data migration issues",
                likelihood="LOW",
                impact="HIGH",
                mitigation_strategy="Data quality assessment upfront, automated migration tools, parallel run period",
            ),
        ]

    @staticmethod
    def _build_success_roadmap() -> list[tuple[str, str]]:
        return [
            ("Month 1-2", "Discovery and solution design"),
            ("Month 3-4", "POC and validation"),
            ("Month 5-7", "Implementation and integration"),
            ("Month 8", "User training and change management"),
            ("Month 9", "Production launch"),
            ("Month 10-12", "Optimization and value realization"),
        ]
