"""Data models for documentation and specifications."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class DocType(Enum):
    """Type of documentation."""

    API = "api"
    TECHNICAL = "technical"
    USER = "user"
    ARCHITECTURE = "architecture"
    DEPLOYMENT = "deployment"


class DocStatus(Enum):
    """Status of documentation."""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


@dataclass(frozen=True)
class APIDocumentation:
    """Immutable API documentation.

    Attributes:
        id: Unique identifier
        title: Documentation title
        endpoints: List of API endpoints
        authentication: Authentication documentation
        examples: Usage examples
        error_codes: Error code documentation
        changelog: API changelog
        created_at: ISO 8601 timestamp
    """

    id: str
    title: str
    endpoints: tuple[str, ...]
    authentication: str
    examples: tuple[str, ...]
    error_codes: tuple[str, ...]
    changelog: tuple[str, ...]
    created_at: str

    @staticmethod
    def create(
        id: str,
        title: str,
        endpoints: list[str],
        authentication: str = "",
        examples: list[str] | None = None,
        error_codes: list[str] | None = None,
        changelog: list[str] | None = None,
    ) -> APIDocumentation:
        """Create API documentation with auto-generated timestamp.

        Args:
            id: Unique identifier
            title: Documentation title
            endpoints: API endpoints
            authentication: Authentication docs
            examples: Optional examples
            error_codes: Optional error codes
            changelog: Optional changelog

        Returns:
            New APIDocumentation instance
        """
        return APIDocumentation(
            id=id,
            title=title,
            endpoints=tuple(endpoints),
            authentication=authentication,
            examples=tuple(examples or []),
            error_codes=tuple(error_codes or []),
            changelog=tuple(changelog or []),
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class Specification:
    """Immutable technical specification.

    Attributes:
        id: Unique identifier
        title: Specification title
        type: Documentation type
        overview: Overview section
        requirements: Requirements section
        design: Design section
        implementation: Implementation notes
        testing: Testing notes
        status: Specification status
        created_at: ISO 8601 timestamp
    """

    id: str
    title: str
    type: DocType
    overview: str
    requirements: str
    design: str
    implementation: str
    testing: str
    status: DocStatus
    created_at: str

    @staticmethod
    def create(
        id: str,
        title: str,
        type: DocType,
        overview: str,
        requirements: str = "",
        design: str = "",
        implementation: str = "",
        testing: str = "",
        status: DocStatus = DocStatus.DRAFT,
    ) -> Specification:
        """Create specification with auto-generated timestamp.

        Args:
            id: Unique identifier
            title: Spec title
            type: Documentation type
            overview: Overview section
            requirements: Requirements section
            design: Design section
            implementation: Implementation notes
            testing: Testing notes
            status: Spec status

        Returns:
            New Specification instance
        """
        return Specification(
            id=id,
            title=title,
            type=type,
            overview=overview,
            requirements=requirements,
            design=design,
            implementation=implementation,
            testing=testing,
            status=status,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class DocsReview:
    """Immutable documentation review result.

    Attributes:
        id: Unique identifier
        doc_id: ID of reviewed documentation
        reviewer_id: ID of reviewer agent
        status: Review status
        feedback: Review feedback
        issues: List of issues found
        suggestions: List of suggestions
        approved: Whether documentation is approved
        created_at: ISO 8601 timestamp
    """

    id: str
    doc_id: str
    reviewer_id: str
    status: DocStatus
    feedback: str
    issues: tuple[str, ...]
    suggestions: tuple[str, ...]
    approved: bool
    created_at: str

    @staticmethod
    def create(
        id: str,
        doc_id: str,
        reviewer_id: str,
        status: DocStatus,
        feedback: str,
        approved: bool,
        issues: list[str] | None = None,
        suggestions: list[str] | None = None,
    ) -> DocsReview:
        """Create docs review with auto-generated timestamp.

        Args:
            id: Unique identifier
            doc_id: Documentation ID
            reviewer_id: Reviewer agent ID
            status: Review status
            feedback: Review feedback
            approved: Approval status
            issues: Optional issues
            suggestions: Optional suggestions

        Returns:
            New DocsReview instance
        """
        return DocsReview(
            id=id,
            doc_id=doc_id,
            reviewer_id=reviewer_id,
            status=status,
            feedback=feedback,
            issues=tuple(issues or []),
            suggestions=tuple(suggestions or []),
            approved=approved,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


__all__ = [
    "APIDocumentation",
    "Specification",
    "DocsReview",
    "DocType",
    "DocStatus",
]
