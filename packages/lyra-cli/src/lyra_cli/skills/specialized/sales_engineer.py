"""
Sales Engineer Skill - Technical sales support and solution design.

Given customer requirements, produces:
- Technical solution design
- Product demonstration plan
- Proof of concept scope
- Technical objection handling
- Implementation timeline

Outputs structured sales engineering plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SolutionComponent(StrEnum):
    """Solution components."""

    CORE_PRODUCT = "core_product"
    INTEGRATION = "integration"
    CUSTOMIZATION = "customization"
    PROFESSIONAL_SERVICES = "professional_services"
    TRAINING = "training"


@dataclass(frozen=True)
class TechnicalSolution:
    """Technical solution design."""

    component: SolutionComponent
    description: str
    technical_specs: tuple[str, ...]
    estimated_effort: str
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class DemoScenario:
    """Product demonstration scenario."""

    scenario_name: str
    objective: str
    demo_steps: tuple[str, ...]
    key_features_highlighted: tuple[str, ...]
    duration_minutes: int


@dataclass(frozen=True)
class POCScope:
    """Proof of concept scope."""

    objective: str
    success_criteria: tuple[str, ...]
    deliverables: tuple[str, ...]
    timeline: str
    resources_required: tuple[str, ...]


@dataclass(frozen=True)
class TechnicalObjection:
    """Technical objection and response."""

    objection: str
    response: str
    supporting_evidence: tuple[str, ...]


@dataclass(frozen=True)
class SalesEngineeringPlan:
    """Complete sales engineering plan."""

    customer_name: str
    technical_solution: tuple[TechnicalSolution, ...]
    demo_scenarios: tuple[DemoScenario, ...]
    poc_scope: POCScope
    technical_objections: tuple[TechnicalObjection, ...]
    implementation_timeline: tuple[tuple[str, str], ...]


class SalesEngineer:
    """Sales engineering skill producing structured plans."""

    def run(self, input_data: dict) -> dict:
        """Run sales engineering planning.

        Args:
            input_data: Dictionary with keys:
                - customer_requirements: Customer requirements description
                - customer_name: Optional customer name (default "Customer")

        Returns:
            Dictionary with sales engineering plan data.
        """
        requirements = input_data.get("customer_requirements", "")
        if not requirements:
            return {"error": "No customer requirements provided"}

        customer_name = input_data.get("customer_name", "Customer")
        reqs_lower = requirements.lower()

        solution = self._design_technical_solution(reqs_lower)
        demos = self._plan_demo_scenarios()
        poc = self._define_poc_scope()
        objections = self._prepare_objection_handling()
        timeline = self._build_implementation_timeline()

        return SalesEngineeringPlan(
            customer_name=customer_name,
            technical_solution=tuple(solution),
            demo_scenarios=tuple(demos),
            poc_scope=poc,
            technical_objections=tuple(objections),
            implementation_timeline=tuple(timeline),
        ).__dict__ | {
            "technical_solution": [s.__dict__ for s in solution],
            "demo_scenarios": [d.__dict__ for d in demos],
            "poc_scope": poc.__dict__,
            "technical_objections": [o.__dict__ for o in objections],
        }

    @staticmethod
    def _design_technical_solution(requirements: str) -> list[TechnicalSolution]:
        solutions = [
            TechnicalSolution(
                component=SolutionComponent.CORE_PRODUCT,
                description="Core platform deployment with standard features",
                technical_specs=(
                    "Cloud-hosted SaaS deployment",
                    "99.9% uptime SLA",
                    "SOC 2 Type II certified",
                    "API access included",
                ),
                estimated_effort="2 weeks setup",
                dependencies=(),
            ),
        ]

        if "integration" in requirements or "api" in requirements:
            solutions.append(
                TechnicalSolution(
                    component=SolutionComponent.INTEGRATION,
                    description="Integration with existing systems via REST APIs",
                    technical_specs=(
                        "Pre-built connectors for common systems",
                        "Custom API integration support",
                        "Webhook support for real-time updates",
                    ),
                    estimated_effort="4 weeks",
                    dependencies=("Core Product",),
                )
            )

        if "custom" in requirements or "specific" in requirements:
            solutions.append(
                TechnicalSolution(
                    component=SolutionComponent.CUSTOMIZATION,
                    description="Custom feature development for specific requirements",
                    technical_specs=(
                        "Custom workflow configuration",
                        "Branded UI/UX",
                        "Custom reporting",
                    ),
                    estimated_effort="6-8 weeks",
                    dependencies=("Core Product",),
                )
            )

        solutions.append(
            TechnicalSolution(
                component=SolutionComponent.TRAINING,
                description="User training and onboarding program",
                technical_specs=(
                    "Admin training (2 days)",
                    "End-user training (1 day)",
                    "Training materials and documentation",
                ),
                estimated_effort="1 week",
                dependencies=("Core Product",),
            )
        )

        return solutions

    @staticmethod
    def _plan_demo_scenarios() -> list[DemoScenario]:
        return [
            DemoScenario(
                scenario_name="Quick Win Scenario",
                objective="Show immediate value with core features",
                demo_steps=(
                    "1. Login and dashboard overview (2 min)",
                    "2. Create new item with guided workflow (3 min)",
                    "3. Demonstrate automation and notifications (3 min)",
                    "4. Show reporting and analytics (2 min)",
                ),
                key_features_highlighted=(
                    "Intuitive UI",
                    "Workflow automation",
                    "Real-time notifications",
                    "Built-in analytics",
                ),
                duration_minutes=10,
            ),
            DemoScenario(
                scenario_name="Enterprise Scenario",
                objective="Demonstrate scalability and enterprise features",
                demo_steps=(
                    "1. Multi-tenant architecture overview (3 min)",
                    "2. Role-based access control (3 min)",
                    "3. API and integration capabilities (4 min)",
                    "4. Security and compliance features (5 min)",
                ),
                key_features_highlighted=(
                    "Multi-tenancy",
                    "RBAC",
                    "API-first architecture",
                    "SOC 2 compliance",
                ),
                duration_minutes=15,
            ),
        ]

    @staticmethod
    def _define_poc_scope() -> POCScope:
        return POCScope(
            objective="Validate solution fit for top 3 use cases",
            success_criteria=(
                "Successfully complete 10 end-to-end workflows",
                "Integrate with 2 existing systems",
                "Achieve < 2 second response time for key operations",
                "Positive feedback from 80%+ of pilot users",
            ),
            deliverables=(
                "Configured POC environment",
                "Integration with 2 systems",
                "Training for 10 pilot users",
                "POC evaluation report",
            ),
            timeline="4 weeks",
            resources_required=(
                "1 Sales Engineer (50% time)",
                "1 Implementation Consultant (full-time)",
                "Customer: 2 technical contacts, 10 pilot users",
            ),
        )

    @staticmethod
    def _prepare_objection_handling() -> list[TechnicalObjection]:
        return [
            TechnicalObjection(
                objection="Your solution doesn't integrate with our legacy system",
                response="We offer flexible integration options including REST APIs, webhooks, and custom connectors",
                supporting_evidence=(
                    "Case study: Integrated with 15-year-old ERP system for Fortune 500 customer",
                    "API documentation and integration guide",
                    "Professional services team available for custom integrations",
                ),
            ),
            TechnicalObjection(
                objection="We're concerned about data security and compliance",
                response="We maintain SOC 2 Type II, ISO 27001, and GDPR compliance with enterprise-grade security",
                supporting_evidence=(
                    "SOC 2 Type II audit report",
                    "Penetration testing results",
                    "Customer references from regulated industries",
                ),
            ),
            TechnicalObjection(
                objection="The solution seems too complex for our users",
                response="We offer configurable UI complexity levels and comprehensive training programs",
                supporting_evidence=(
                    "User adoption metrics: 90%+ adoption within 30 days",
                    "Simplified UI mode for basic users",
                    "Interactive training modules and ongoing support",
                ),
            ),
        ]

    @staticmethod
    def _build_implementation_timeline() -> list[tuple[str, str]]:
        return [
            ("Week 1-2", "Environment setup and configuration"),
            ("Week 3-4", "Data migration and integration"),
            ("Week 5-6", "User training and UAT"),
            ("Week 7", "Production deployment"),
            ("Week 8", "Post-launch support and optimization"),
        ]
