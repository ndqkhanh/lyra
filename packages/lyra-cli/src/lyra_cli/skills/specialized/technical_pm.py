"""
Technical PM Skill - Technical product management and architecture alignment.

Given technical requirements, produces:
- Technical roadmap
- Architecture decisions
- API design
- Performance requirements
- Technical debt management

Outputs structured technical product plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TechDecisionType(StrEnum):
    """Types of technical decisions."""

    ARCHITECTURE = "architecture"
    TECHNOLOGY_STACK = "technology_stack"
    API_DESIGN = "api_design"
    DATA_MODEL = "data_model"
    INFRASTRUCTURE = "infrastructure"


@dataclass(frozen=True)
class TechnicalDecision:
    """Technical decision record."""

    decision_type: TechDecisionType
    decision: str
    rationale: str
    alternatives_considered: tuple[str, ...]
    trade_offs: str


@dataclass(frozen=True)
class APISpecification:
    """API specification."""

    endpoint: str
    method: str
    purpose: str
    request_schema: str
    response_schema: str
    performance_target: str


@dataclass(frozen=True)
class PerformanceRequirement:
    """Performance requirement."""

    metric: str
    target: str
    measurement_method: str
    priority: str


@dataclass(frozen=True)
class TechnicalDebtItem:
    """Technical debt item."""

    area: str
    description: str
    impact: str
    effort_to_fix: str
    priority: str


@dataclass(frozen=True)
class TechnicalProductPlan:
    """Complete technical product plan."""

    product_name: str
    technical_decisions: tuple[TechnicalDecision, ...]
    api_specifications: tuple[APISpecification, ...]
    performance_requirements: tuple[PerformanceRequirement, ...]
    technical_debt: tuple[TechnicalDebtItem, ...]
    technical_roadmap: tuple[tuple[str, str], ...]


class TechnicalPM:
    """Technical PM skill producing structured plans."""

    def run(self, input_data: dict) -> dict:
        """Run technical product planning.

        Args:
            input_data: Dictionary with keys:
                - technical_requirements: Technical requirements description
                - product_name: Optional product name (default "Technical Product")

        Returns:
            Dictionary with technical product plan data.
        """
        requirements = input_data.get("technical_requirements", "")
        if not requirements:
            return {"error": "No technical requirements provided"}

        product_name = input_data.get("product_name", "Technical Product")
        reqs_lower = requirements.lower()

        decisions = self._make_technical_decisions(reqs_lower)
        api_specs = self._design_api_specifications()
        performance = self._define_performance_requirements()
        tech_debt = self._identify_technical_debt()
        roadmap = self._build_technical_roadmap()

        return TechnicalProductPlan(
            product_name=product_name,
            technical_decisions=tuple(decisions),
            api_specifications=tuple(api_specs),
            performance_requirements=tuple(performance),
            technical_debt=tuple(tech_debt),
            technical_roadmap=tuple(roadmap),
        ).__dict__ | {
            "technical_decisions": [d.__dict__ for d in decisions],
            "api_specifications": [a.__dict__ for a in api_specs],
            "performance_requirements": [p.__dict__ for p in performance],
            "technical_debt": [t.__dict__ for t in tech_debt],
        }

    @staticmethod
    def _make_technical_decisions(requirements: str) -> list[TechnicalDecision]:
        decisions: list[TechnicalDecision] = [
            TechnicalDecision(
                decision_type=TechDecisionType.ARCHITECTURE,
                decision="Microservices architecture with API gateway",
                rationale="Enables independent scaling and deployment of services",
                alternatives_considered=("Monolithic architecture", "Serverless architecture"),
                trade_offs="Increased operational complexity vs better scalability",
            ),
            TechnicalDecision(
                decision_type=TechDecisionType.API_DESIGN,
                decision="RESTful API with JSON payloads",
                rationale="Industry standard, wide tooling support, easy to consume",
                alternatives_considered=("GraphQL", "gRPC"),
                trade_offs="Less flexible than GraphQL, but simpler to implement",
            ),
        ]

        if "database" in requirements or "data" in requirements:
            decisions.append(
                TechnicalDecision(
                    decision_type=TechDecisionType.DATA_MODEL,
                    decision="PostgreSQL for relational data, Redis for caching",
                    rationale="ACID compliance for transactions, fast caching layer",
                    alternatives_considered=("MongoDB", "DynamoDB"),
                    trade_offs="Relational model requires schema migrations",
                )
            )

        if "cloud" in requirements or "infrastructure" in requirements:
            decisions.append(
                TechnicalDecision(
                    decision_type=TechDecisionType.INFRASTRUCTURE,
                    decision="Kubernetes on AWS EKS for container orchestration",
                    rationale="Industry standard, portable, auto-scaling capabilities",
                    alternatives_considered=("ECS", "Lambda"),
                    trade_offs="Higher learning curve vs better portability",
                )
            )

        return decisions

    @staticmethod
    def _design_api_specifications() -> list[APISpecification]:
        return [
            APISpecification(
                endpoint="/api/v1/users",
                method="POST",
                purpose="Create new user account",
                request_schema='{"email": "string", "password": "string", "name": "string"}',
                response_schema='{"id": "uuid", "email": "string", "created_at": "timestamp"}',
                performance_target="< 200ms p95 latency",
            ),
            APISpecification(
                endpoint="/api/v1/users/{id}",
                method="GET",
                purpose="Retrieve user profile",
                request_schema="None (path parameter only)",
                response_schema='{"id": "uuid", "email": "string", "name": "string", "created_at": "timestamp"}',
                performance_target="< 100ms p95 latency",
            ),
            APISpecification(
                endpoint="/api/v1/items",
                method="GET",
                purpose="List items with pagination",
                request_schema='{"page": "int", "limit": "int", "filter": "object"}',
                response_schema='{"items": "array", "total": "int", "page": "int"}',
                performance_target="< 300ms p95 latency",
            ),
        ]

    @staticmethod
    def _define_performance_requirements() -> list[PerformanceRequirement]:
        return [
            PerformanceRequirement(
                metric="API Response Time",
                target="< 200ms p95 for all endpoints",
                measurement_method="APM tool (Datadog, New Relic)",
                priority="P0",
            ),
            PerformanceRequirement(
                metric="Throughput",
                target="> 1000 requests/second per service",
                measurement_method="Load testing (k6, Gatling)",
                priority="P1",
            ),
            PerformanceRequirement(
                metric="Database Query Time",
                target="< 50ms p95 for read queries",
                measurement_method="Database monitoring (pg_stat_statements)",
                priority="P0",
            ),
            PerformanceRequirement(
                metric="Page Load Time",
                target="< 2 seconds for initial page load",
                measurement_method="Real User Monitoring (RUM)",
                priority="P1",
            ),
        ]

    @staticmethod
    def _identify_technical_debt() -> list[TechnicalDebtItem]:
        return [
            TechnicalDebtItem(
                area="Testing",
                description="Test coverage below 80% in core services",
                impact="Increased risk of regressions, slower development velocity",
                effort_to_fix="4 weeks",
                priority="HIGH",
            ),
            TechnicalDebtItem(
                area="Documentation",
                description="API documentation outdated and incomplete",
                impact="Developer onboarding friction, integration issues",
                effort_to_fix="2 weeks",
                priority="MEDIUM",
            ),
            TechnicalDebtItem(
                area="Monitoring",
                description="Limited observability in production",
                impact="Difficult to debug issues, slow incident response",
                effort_to_fix="3 weeks",
                priority="HIGH",
            ),
        ]

    @staticmethod
    def _build_technical_roadmap() -> list[tuple[str, str]]:
        return [
            ("Q1 2026", "Core API development and database schema design"),
            ("Q2 2026", "Performance optimization and caching layer"),
            ("Q3 2026", "Microservices migration and service mesh implementation"),
            ("Q4 2026", "Advanced features (real-time updates, webhooks)"),
        ]
