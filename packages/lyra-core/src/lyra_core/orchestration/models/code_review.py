"""Data models for code review and pull requests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class ReviewSeverity(Enum):
    """Severity level of code review findings."""

    CRITICAL = "critical"  # Security vulnerability or data loss risk
    HIGH = "high"  # Bug or significant quality issue
    MEDIUM = "medium"  # Maintainability concern
    LOW = "low"  # Style or minor suggestion


class PRStatus(Enum):
    """Status of a pull request."""

    DRAFT = "draft"
    OPEN = "open"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    MERGED = "merged"
    CLOSED = "closed"


@dataclass(frozen=True)
class PullRequest:
    """Immutable pull request representation.

    Attributes:
        id: Unique identifier
        title: PR title
        description: PR description
        author: Author agent ID
        files_changed: List of changed file paths
        additions: Number of lines added
        deletions: Number of lines deleted
        status: PR status
        created_at: ISO 8601 timestamp
    """

    id: str
    title: str
    description: str
    author: str
    files_changed: tuple[str, ...]
    additions: int
    deletions: int
    status: PRStatus
    created_at: str

    @staticmethod
    def create(
        id: str,
        title: str,
        description: str,
        author: str,
        files_changed: list[str],
        additions: int = 0,
        deletions: int = 0,
        status: PRStatus = PRStatus.DRAFT,
    ) -> PullRequest:
        """Create pull request with auto-generated timestamp.

        Args:
            id: Unique identifier
            title: PR title
            description: PR description
            author: Author agent ID
            files_changed: List of changed files
            additions: Lines added
            deletions: Lines deleted
            status: PR status

        Returns:
            New PullRequest instance
        """
        return PullRequest(
            id=id,
            title=title,
            description=description,
            author=author,
            files_changed=tuple(files_changed),
            additions=additions,
            deletions=deletions,
            status=status,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class ReviewComment:
    """Immutable code review comment.

    Attributes:
        file_path: Path to file
        line_number: Line number
        severity: Comment severity
        message: Comment message
        suggestion: Optional code suggestion
    """

    file_path: str
    line_number: int
    severity: ReviewSeverity
    message: str
    suggestion: str | None = None


@dataclass(frozen=True)
class CodeReview:
    """Immutable code review result.

    Attributes:
        id: Unique identifier
        pr_id: ID of reviewed pull request
        reviewer_id: ID of reviewer agent
        status: Review status (approved/changes_requested)
        summary: Review summary
        comments: List of review comments
        critical_count: Number of critical issues
        high_count: Number of high severity issues
        medium_count: Number of medium severity issues
        low_count: Number of low severity issues
        created_at: ISO 8601 timestamp
    """

    id: str
    pr_id: str
    reviewer_id: str
    status: PRStatus
    summary: str
    comments: tuple[ReviewComment, ...]
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    created_at: str

    @staticmethod
    def create(
        id: str,
        pr_id: str,
        reviewer_id: str,
        status: PRStatus,
        summary: str,
        comments: list[ReviewComment] | None = None,
    ) -> CodeReview:
        """Create code review with auto-generated timestamp and counts.

        Args:
            id: Unique identifier
            pr_id: Pull request ID
            reviewer_id: Reviewer agent ID
            status: Review status
            summary: Review summary
            comments: Optional review comments

        Returns:
            New CodeReview instance
        """
        comment_list = comments or []

        # Count issues by severity
        critical_count = sum(
            1 for c in comment_list if c.severity == ReviewSeverity.CRITICAL
        )
        high_count = sum(1 for c in comment_list if c.severity == ReviewSeverity.HIGH)
        medium_count = sum(
            1 for c in comment_list if c.severity == ReviewSeverity.MEDIUM
        )
        low_count = sum(1 for c in comment_list if c.severity == ReviewSeverity.LOW)

        return CodeReview(
            id=id,
            pr_id=pr_id,
            reviewer_id=reviewer_id,
            status=status,
            summary=summary,
            comments=tuple(comment_list),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


__all__ = [
    "PullRequest",
    "CodeReview",
    "ReviewComment",
    "ReviewSeverity",
    "PRStatus",
]
