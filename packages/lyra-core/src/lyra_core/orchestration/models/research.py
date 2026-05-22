"""Data models for research and analysis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class PaperSource(Enum):
    """Source of research paper."""

    ARXIV = "arxiv"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    PUBMED = "pubmed"
    IEEE = "ieee"
    ACM = "acm"


class ProjectQuality(Enum):
    """Quality rating for evaluated projects."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass(frozen=True)
class Paper:
    """Immutable research paper metadata.

    Attributes:
        id: Unique identifier
        title: Paper title
        authors: List of authors
        abstract: Paper abstract
        url: URL to paper
        source: Paper source
        published_date: Publication date
        citations: Number of citations
        relevance_score: Relevance score (0-1)
        created_at: ISO 8601 timestamp
    """

    id: str
    title: str
    authors: tuple[str, ...]
    abstract: str
    url: str
    source: PaperSource
    published_date: str
    citations: int
    relevance_score: float
    created_at: str

    @staticmethod
    def create(
        id: str,
        title: str,
        authors: list[str],
        abstract: str,
        url: str,
        source: PaperSource,
        published_date: str,
        citations: int = 0,
        relevance_score: float = 0.0,
    ) -> Paper:
        """Create paper with auto-generated timestamp.

        Args:
            id: Unique identifier
            title: Paper title
            authors: List of authors
            abstract: Paper abstract
            url: Paper URL
            source: Paper source
            published_date: Publication date
            citations: Citation count
            relevance_score: Relevance score

        Returns:
            New Paper instance
        """
        return Paper(
            id=id,
            title=title,
            authors=tuple(authors),
            abstract=abstract,
            url=url,
            source=source,
            published_date=published_date,
            citations=citations,
            relevance_score=relevance_score,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class RepoAnalysis:
    """Immutable GitHub repository analysis.

    Attributes:
        id: Unique identifier
        repo_url: Repository URL
        name: Repository name
        description: Repository description
        stars: Number of stars
        forks: Number of forks
        language: Primary language
        topics: Repository topics
        last_updated: Last update date
        license: License type
        relevance_score: Relevance score (0-1)
        created_at: ISO 8601 timestamp
    """

    id: str
    repo_url: str
    name: str
    description: str
    stars: int
    forks: int
    language: str
    topics: tuple[str, ...]
    last_updated: str
    license: str
    relevance_score: float
    created_at: str

    @staticmethod
    def create(
        id: str,
        repo_url: str,
        name: str,
        description: str,
        stars: int,
        forks: int,
        language: str,
        topics: list[str],
        last_updated: str,
        license: str = "",
        relevance_score: float = 0.0,
    ) -> RepoAnalysis:
        """Create repo analysis with auto-generated timestamp.

        Args:
            id: Unique identifier
            repo_url: Repository URL
            name: Repository name
            description: Repository description
            stars: Star count
            forks: Fork count
            language: Primary language
            topics: Repository topics
            last_updated: Last update date
            license: License type
            relevance_score: Relevance score

        Returns:
            New RepoAnalysis instance
        """
        return RepoAnalysis(
            id=id,
            repo_url=repo_url,
            name=name,
            description=description,
            stars=stars,
            forks=forks,
            language=language,
            topics=tuple(topics),
            last_updated=last_updated,
            license=license,
            relevance_score=relevance_score,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class ProjectEvaluation:
    """Immutable project evaluation result.

    Attributes:
        id: Unique identifier
        project_name: Project name
        project_url: Project URL
        quality: Quality rating
        strengths: List of strengths
        weaknesses: List of weaknesses
        use_cases: Applicable use cases
        recommendation: Recommendation summary
        score: Overall score (0-100)
        created_at: ISO 8601 timestamp
    """

    id: str
    project_name: str
    project_url: str
    quality: ProjectQuality
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    use_cases: tuple[str, ...]
    recommendation: str
    score: int
    created_at: str

    @staticmethod
    def create(
        id: str,
        project_name: str,
        project_url: str,
        quality: ProjectQuality,
        strengths: list[str],
        weaknesses: list[str],
        use_cases: list[str],
        recommendation: str,
        score: int,
    ) -> ProjectEvaluation:
        """Create project evaluation with auto-generated timestamp.

        Args:
            id: Unique identifier
            project_name: Project name
            project_url: Project URL
            quality: Quality rating
            strengths: List of strengths
            weaknesses: List of weaknesses
            use_cases: Use cases
            recommendation: Recommendation
            score: Overall score

        Returns:
            New ProjectEvaluation instance
        """
        return ProjectEvaluation(
            id=id,
            project_name=project_name,
            project_url=project_url,
            quality=quality,
            strengths=tuple(strengths),
            weaknesses=tuple(weaknesses),
            use_cases=tuple(use_cases),
            recommendation=recommendation,
            score=score,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


@dataclass(frozen=True)
class ResearchReport:
    """Immutable research report synthesizing findings.

    Attributes:
        id: Unique identifier
        title: Report title
        query: Original research query
        papers: Analyzed papers
        repos: Analyzed repositories
        evaluations: Project evaluations
        summary: Executive summary
        key_findings: Key findings
        recommendations: Recommendations
        created_at: ISO 8601 timestamp
    """

    id: str
    title: str
    query: str
    papers: tuple[Paper, ...]
    repos: tuple[RepoAnalysis, ...]
    evaluations: tuple[ProjectEvaluation, ...]
    summary: str
    key_findings: tuple[str, ...]
    recommendations: tuple[str, ...]
    created_at: str

    @staticmethod
    def create(
        id: str,
        title: str,
        query: str,
        papers: list[Paper],
        repos: list[RepoAnalysis],
        evaluations: list[ProjectEvaluation],
        summary: str,
        key_findings: list[str],
        recommendations: list[str],
    ) -> ResearchReport:
        """Create research report with auto-generated timestamp.

        Args:
            id: Unique identifier
            title: Report title
            query: Research query
            papers: Analyzed papers
            repos: Analyzed repos
            evaluations: Project evaluations
            summary: Executive summary
            key_findings: Key findings
            recommendations: Recommendations

        Returns:
            New ResearchReport instance
        """
        return ResearchReport(
            id=id,
            title=title,
            query=query,
            papers=tuple(papers),
            repos=tuple(repos),
            evaluations=tuple(evaluations),
            summary=summary,
            key_findings=tuple(key_findings),
            recommendations=tuple(recommendations),
            created_at=datetime.now(timezone.utc).isoformat(),
        )


__all__ = [
    "Paper",
    "RepoAnalysis",
    "ProjectEvaluation",
    "ResearchReport",
    "PaperSource",
    "ProjectQuality",
]
