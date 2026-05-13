"""
Multi-source research discovery engine.

Discovers papers, GitHub repos, and web content for research queries.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import requests


class SourceType(str, Enum):
    """Type of research source."""
    PAPER = "paper"
    REPOSITORY = "repository"
    BLOG = "blog"
    DOCUMENTATION = "documentation"
    FORUM = "forum"


@dataclass
class ResearchSource:
    """A discovered research source."""
    id: str
    title: str
    source_type: SourceType
    url: str
    authors: List[str] = field(default_factory=list)
    published_date: Optional[datetime] = None
    abstract: str = ""
    citations: int = 0
    stars: int = 0  # For repos
    metadata: Dict[str, Any] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=datetime.now)


class ArXivDiscovery:
    """Discover papers from ArXiv."""

    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query"

    def search(self, query: str, max_results: int = 50) -> List[ResearchSource]:
        """
        Search ArXiv for papers.

        Args:
            query: Search query
            max_results: Maximum results to return

        Returns:
            List of discovered papers
        """
        try:
            import arxiv

            client = arxiv.Client()
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )

            sources = []
            for result in client.results(search):
                source = ResearchSource(
                    id=result.entry_id,
                    title=result.title,
                    source_type=SourceType.PAPER,
                    url=result.entry_id,
                    authors=[author.name for author in result.authors],
                    published_date=result.published,
                    abstract=result.summary,
                    metadata={
                        "categories": result.categories,
                        "primary_category": result.primary_category,
                        "pdf_url": result.pdf_url,
                    },
                )
                sources.append(source)

            return sources

        except Exception as e:
            print(f"ArXiv search error: {e}")
            return []


class SemanticScholarDiscovery:
    """Discover papers from Semantic Scholar."""

    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.api_key = api_key

    def search(self, query: str, max_results: int = 50) -> List[ResearchSource]:
        """
        Search Semantic Scholar for papers.

        Args:
            query: Search query
            max_results: Maximum results

        Returns:
            List of discovered papers
        """
        try:
            headers = {}
            if self.api_key:
                headers["x-api-key"] = self.api_key

            params = {
                "query": query,
                "limit": min(max_results, 100),
                "fields": "paperId,title,abstract,authors,year,citationCount,url,venue",
            }

            response = requests.get(
                f"{self.base_url}/paper/search",
                params=params,
                headers=headers,
                timeout=30,
            )

            if response.status_code != 200:
                print(f"Semantic Scholar API error: {response.status_code}")
                return []

            data = response.json()
            sources = []

            for paper in data.get("data", []):
                # Parse year to datetime
                year = paper.get("year")
                published_date = datetime(year, 1, 1) if year else None

                source = ResearchSource(
                    id=paper["paperId"],
                    title=paper.get("title", ""),
                    source_type=SourceType.PAPER,
                    url=paper.get("url", ""),
                    authors=[a.get("name", "") for a in paper.get("authors", [])],
                    published_date=published_date,
                    abstract=paper.get("abstract", ""),
                    citations=paper.get("citationCount", 0),
                    metadata={
                        "venue": paper.get("venue", ""),
                        "year": year,
                    },
                )
                sources.append(source)

            return sources

        except Exception as e:
            print(f"Semantic Scholar search error: {e}")
            return []


class GitHubDiscovery:
    """Discover repositories from GitHub."""

    def __init__(self, api_token: Optional[str] = None):
        self.base_url = "https://api.github.com"
        self.api_token = api_token

    def search(self, query: str, max_results: int = 50) -> List[ResearchSource]:
        """
        Search GitHub for repositories.

        Args:
            query: Search query
            max_results: Maximum results

        Returns:
            List of discovered repositories
        """
        try:
            headers = {"Accept": "application/vnd.github.v3+json"}
            if self.api_token:
                headers["Authorization"] = f"token {self.api_token}"

            params = {
                "q": query,
                "sort": "stars",
                "order": "desc",
                "per_page": min(max_results, 100),
            }

            response = requests.get(
                f"{self.base_url}/search/repositories",
                params=params,
                headers=headers,
                timeout=30,
            )

            if response.status_code != 200:
                print(f"GitHub API error: {response.status_code}")
                return []

            data = response.json()
            sources = []

            for repo in data.get("items", []):
                # Parse created_at
                created_at = datetime.fromisoformat(
                    repo["created_at"].replace("Z", "+00:00")
                )

                source = ResearchSource(
                    id=str(repo["id"]),
                    title=repo["full_name"],
                    source_type=SourceType.REPOSITORY,
                    url=repo["html_url"],
                    authors=[repo["owner"]["login"]],
                    published_date=created_at,
                    abstract=repo.get("description", ""),
                    stars=repo.get("stargazers_count", 0),
                    metadata={
                        "language": repo.get("language", ""),
                        "forks": repo.get("forks_count", 0),
                        "open_issues": repo.get("open_issues_count", 0),
                        "topics": repo.get("topics", []),
                        "license": repo.get("license", {}).get("name", "") if repo.get("license") else "",
                        "default_branch": repo.get("default_branch", "main"),
                    },
                )
                sources.append(source)

            return sources

        except Exception as e:
            print(f"GitHub search error: {e}")
            return []


class MultiSourceDiscovery:
    """
    Unified discovery across multiple sources.

    Aggregates results from ArXiv, Semantic Scholar, GitHub, OpenReview,
    HuggingFace Papers, Papers with Code, and ACL Anthology.
    """

    def __init__(
        self,
        semantic_scholar_key: Optional[str] = None,
        github_token: Optional[str] = None,
    ):
        """
        Initialize multi-source discovery.

        Args:
            semantic_scholar_key: Semantic Scholar API key
            github_token: GitHub API token
        """
        # Import here to avoid circular imports at module load time
        from lyra_research.sources import (
            ACLAnthologyDiscovery,
            CitationTraversal,
            HuggingFacePapersDiscovery,
            OpenReviewDiscovery,
            PapersWithCodeDiscovery,
        )

        self.arxiv = ArXivDiscovery()
        self.semantic_scholar = SemanticScholarDiscovery(semantic_scholar_key)
        self.github = GitHubDiscovery(github_token)
        self.openreview = OpenReviewDiscovery()
        self.huggingface = HuggingFacePapersDiscovery()
        self.papers_with_code = PapersWithCodeDiscovery()
        self.acl = ACLAnthologyDiscovery(semantic_scholar_key)
        self.citation_traversal = CitationTraversal(semantic_scholar_key)

    def discover(
        self,
        query: str,
        sources: List[str] = ["arxiv", "semantic_scholar", "github"],
        max_per_source: int = 50,
    ) -> Dict[str, List[ResearchSource]]:
        """
        Discover research sources across multiple platforms.

        Args:
            query: Search query
            sources: List of sources to search. Supported values:
                "arxiv", "semantic_scholar", "github",
                "openreview", "huggingface", "papers_with_code", "acl"
            max_per_source: Maximum results per source

        Returns:
            Dictionary mapping source name to list of results
        """
        results = {}

        if "arxiv" in sources:
            print(f"Searching ArXiv for: {query}")
            results["arxiv"] = self.arxiv.search(query, max_per_source)
            print(f"  Found {len(results['arxiv'])} papers")

        if "semantic_scholar" in sources:
            print(f"Searching Semantic Scholar for: {query}")
            results["semantic_scholar"] = self.semantic_scholar.search(query, max_per_source)
            print(f"  Found {len(results['semantic_scholar'])} papers")

        if "github" in sources:
            print(f"Searching GitHub for: {query}")
            results["github"] = self.github.search(query, max_per_source)
            print(f"  Found {len(results['github'])} repositories")

        if "openreview" in sources:
            print(f"Searching OpenReview for: {query}")
            results["openreview"] = self.openreview.search(query, max_per_source)
            print(f"  Found {len(results['openreview'])} papers")

        if "huggingface" in sources:
            print(f"Searching HuggingFace Papers for: {query}")
            results["huggingface"] = self.huggingface.search(query, max_per_source)
            print(f"  Found {len(results['huggingface'])} papers")

        if "papers_with_code" in sources:
            print(f"Searching Papers with Code for: {query}")
            results["papers_with_code"] = self.papers_with_code.search(query, max_per_source)
            print(f"  Found {len(results['papers_with_code'])} papers")

        if "acl" in sources:
            print(f"Searching ACL Anthology for: {query}")
            results["acl"] = self.acl.search(query, max_per_source)
            print(f"  Found {len(results['acl'])} papers")

        return results

    def discover_all(self, query: str, max_per_source: int = 50) -> List[ResearchSource]:
        """
        Discover from all sources and return combined list.

        Args:
            query: Search query
            max_per_source: Maximum results per source

        Returns:
            Combined list of all discovered sources
        """
        results = self.discover(query, max_per_source=max_per_source)

        all_sources = []
        for source_list in results.values():
            all_sources.extend(source_list)

        return all_sources
