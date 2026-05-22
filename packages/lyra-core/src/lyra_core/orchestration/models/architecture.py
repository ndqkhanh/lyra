"""Data models for architecture and technical design."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class ArchitecturePattern(Enum):
    """Common architecture patterns."""

    MONOLITH = "monolith"
    MICROSERVICES = "microservices"
    SERVERLESS = "serverless"
    EVENT_DRIVEN = "event_driven"
    LAYERED = "layered"
    HEXAGONAL = "hexagonal"


class ReviewStatus(Enum):
    """Status of architecture review."""

    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"
    PENDING = "pending"


@dataclass(frozen=True)
class TechStack:
    """Immutable technology stack selection.

    Attributes:
        languages: Programming languages
        frameworks: Frameworks and libraries
        databases: Database systems
        infrastructure: Infrastructure components
        tools: Development and deployment tools
    """

    languages: tuple[str, ...]
    frameworks: tuple[str, ...]
    databases: tuple[str, ...]
    infrastructure: tuple[str, ...]
    tools: tuple[str, ...]

    @staticmethod
    def create(
        languages: list[str],
        frameworks: list[str] | None = None,
        databases: list[str] | None = None,
        infrastructure: list[str] | None = None,
        tools: list[str] | None = None,
    ) -> TechStack:
        """Create tech stack.

        Args:
            languages: Programming languages
            frameworks: Optional frameworks
            databases: Optional databases
            infrastructure: Optional infrastructure
            tools: Optional tools

        Returns:
            New TechStack instance
        """
        return TechStack(
            languages=tuple(languages),
            frameworks=tuple(frameworks or []),
            databases=tuple(databases or []),
            infrastructure=tuple(infrastructure or []),
            tools=tuple(tools or []),
        )


@dataclass(frozen=True)
class Architecture:
    """Immutable system architecture design.

    Attributes:
        id: Unique identifier
        pattern: Architecture pattern
        components: List of system components
        tech_stack: Technology stack
        data_flow: Description of data flow
        scalability_notes: Scalability considerations
        security_notes: Security considerations
        created_at: ISO 8601 timestamp
    """

    id: str
    pattern: ArchitecturePattern
    components: tuple[str, ...]
    tech_stack: TechStack
    data_flow: str
    scalability_notes: str
    security_notes: str
    created_at: str

    @staticmethod
    def create(
        id: str,
        pattern: ArchitecturePattern,
        components: list[str],
        tech_stack: TechStack,
        data_flow: str,
        scalability_notes: str = "",
        security_notes: str = "",
    ) -> Architecture:
        """Create architecture with auto-generated timestamp.

        Args:
            id: Unique identifier
            pattern: Architecture pattern
            components: System components
            tech_stack: Technology stack
            data_flow: Data flow description
            scalability_notes: Scalability notes
            security_notes: Security notes

        Returns:
            New Architecture instance
        """
        return Architecture(
            id=id,
            pattern=pattern,
            components=tuple(components),
            tech_stack=tech_stack,
            data_flow=data_flow,
            scalability_notes=scalability_notes,
            security_notes=security_notes,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class ArchitectureReview:
    """Immutable architecture review result.

    Attributes:
        id: Unique identifier
        architecture_id: ID of reviewed architecture
        status: Review status
        feedback: Review feedback
        concerns: List of concerns
        recommendations: List of recommendations
        reviewer_id: ID of reviewer agent
        created_at: ISO 8601 timestamp
    """

    id: str
    architecture_id: str
    status: ReviewStatus
    feedback: str
    concerns: tuple[str, ...]
    recommendations: tuple[str, ...]
    reviewer_id: str
    created_at: str

    @staticmethod
    def create(
        id: str,
        architecture_id: str,
        status: ReviewStatus,
        feedback: str,
        reviewer_id: str,
        concerns: list[str] | None = None,
        recommendations: list[str] | None = None,
    ) -> ArchitectureReview:
        """Create architecture review with auto-generated timestamp.

        Args:
            id: Unique identifier
            architecture_id: Architecture ID
            status: Review status
            feedback: Review feedback
            reviewer_id: Reviewer agent ID
            concerns: Optional concerns
            recommendations: Optional recommendations

        Returns:
            New ArchitectureReview instance
        """
        return ArchitectureReview(
            id=id,
            architecture_id=architecture_id,
            status=status,
            feedback=feedback,
            concerns=tuple(concerns or []),
            recommendations=tuple(recommendations or []),
            reviewer_id=reviewer_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class ScalabilityPlan:
    """Immutable scalability plan.

    Attributes:
        id: Unique identifier
        architecture_id: ID of associated architecture
        horizontal_scaling: Horizontal scaling strategy
        vertical_scaling: Vertical scaling strategy
        caching_strategy: Caching approach
        load_balancing: Load balancing approach
        bottlenecks: Identified bottlenecks
        mitigation: Mitigation strategies
        created_at: ISO 8601 timestamp
    """

    id: str
    architecture_id: str
    horizontal_scaling: str
    vertical_scaling: str
    caching_strategy: str
    load_balancing: str
    bottlenecks: tuple[str, ...]
    mitigation: tuple[str, ...]
    created_at: str

    @staticmethod
    def create(
        id: str,
        architecture_id: str,
        horizontal_scaling: str,
        vertical_scaling: str,
        caching_strategy: str,
        load_balancing: str,
        bottlenecks: list[str] | None = None,
        mitigation: list[str] | None = None,
    ) -> ScalabilityPlan:
        """Create scalability plan with auto-generated timestamp.

        Args:
            id: Unique identifier
            architecture_id: Architecture ID
            horizontal_scaling: Horizontal scaling strategy
            vertical_scaling: Vertical scaling strategy
            caching_strategy: Caching strategy
            load_balancing: Load balancing strategy
            bottlenecks: Optional bottlenecks
            mitigation: Optional mitigation strategies

        Returns:
            New ScalabilityPlan instance
        """
        return ScalabilityPlan(
            id=id,
            architecture_id=architecture_id,
            horizontal_scaling=horizontal_scaling,
            vertical_scaling=vertical_scaling,
            caching_strategy=caching_strategy,
            load_balancing=load_balancing,
            bottlenecks=tuple(bottlenecks or []),
            mitigation=tuple(mitigation or []),
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class TechSpec:
    """Immutable technical specification.

    Attributes:
        id: Unique identifier
        architecture_id: ID of associated architecture
        title: Specification title
        overview: Technical overview
        api_contracts: API contract definitions
        data_models: Data model definitions
        interfaces: Interface definitions
        dependencies: External dependencies
        created_at: ISO 8601 timestamp
    """

    id: str
    architecture_id: str
    title: str
    overview: str
    api_contracts: tuple[str, ...]
    data_models: tuple[str, ...]
    interfaces: tuple[str, ...]
    dependencies: tuple[str, ...]
    created_at: str

    @staticmethod
    def create(
        id: str,
        architecture_id: str,
        title: str,
        overview: str,
        api_contracts: list[str] | None = None,
        data_models: list[str] | None = None,
        interfaces: list[str] | None = None,
        dependencies: list[str] | None = None,
    ) -> TechSpec:
        """Create tech spec with auto-generated timestamp.

        Args:
            id: Unique identifier
            architecture_id: Architecture ID
            title: Spec title
            overview: Technical overview
            api_contracts: Optional API contracts
            data_models: Optional data models
            interfaces: Optional interfaces
            dependencies: Optional dependencies

        Returns:
            New TechSpec instance
        """
        return TechSpec(
            id=id,
            architecture_id=architecture_id,
            title=title,
            overview=overview,
            api_contracts=tuple(api_contracts or []),
            data_models=tuple(data_models or []),
            interfaces=tuple(interfaces or []),
            dependencies=tuple(dependencies or []),
            created_at=datetime.now(timezone.utc).isoformat(),
        )


__all__ = [
    "Architecture",
    "TechStack",
    "TechSpec",
    "ArchitectureReview",
    "ScalabilityPlan",
    "ArchitecturePattern",
    "ReviewStatus",
]
