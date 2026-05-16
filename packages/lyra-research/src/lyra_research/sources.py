"""
Enhanced source adapters for research discovery.

Provides additional discovery sources beyond the core discovery.py engines:
OpenReview, HuggingFace Papers, Papers with Code, ACL Anthology, citation
traversal, GitHub activity scoring, and multi-signal source quality ranking.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import os

import requests

from lyra_research.discovery import ResearchSource, SourceType


# ---------------------------------------------------------------------------
# OpenReview
# ---------------------------------------------------------------------------

class OpenReviewDiscovery:
    """Discover papers from OpenReview (ICLR, NeurIPS, ICML, COLM)."""

    BASE_URL = "https://api.openreview.net"
    SUPPORTED_VENUES = ["ICLR.cc", "NeurIPS.cc", "ICML.cc", "COLM"]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenReview discovery.

        Args:
            api_key: Optional OpenReview API key (unused for public endpoints).
        """
        self.api_key = api_key or os.environ.get("OPENREVIEW_API_KEY")

    def search(
        self,
        query: str,
        max_results: int = 50,
        venue: Optional[str] = None,
    ) -> List[ResearchSource]:
        """
        Search OpenReview for papers with exponential backoff retry.

        Args:
            query: Search query.
            max_results: Maximum number of results.
            venue: Optional venue filter (e.g. "ICLR.cc").

        Returns:
            List of discovered papers.
        """
        import time

        max_retries = 3
        base_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                params: Dict[str, Any] = {"term": query, "limit": min(max_results, 100)}
                if venue:
                    params["content.venueid"] = venue

                response = requests.get(
                    f"{self.BASE_URL}/notes",
                    params=params,
                    timeout=30,
                )

                if response.status_code == 429:  # Rate limited
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"OpenReview rate limited. Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"OpenReview API error: Rate limit exceeded after {max_retries} attempts")
                        return []

                if response.status_code != 200:
                    print(f"OpenReview API error: {response.status_code}")
                    return []

                data = response.json()
                return [self._to_source(note) for note in data.get("notes", [])]

            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"OpenReview error: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    print(f"OpenReview search error after {max_retries} attempts: {e}")
                    return []

        return []

    def _to_source(self, note: Dict[str, Any]) -> ResearchSource:
        """Convert an OpenReview note dict to a ResearchSource."""
        content = note.get("content", {})
        note_id = note.get("id", "")
        venue = content.get("venue", "") or content.get("venueid", "")

        # Try to parse year from cdate (ms epoch) or venueid string
        year: Optional[int] = None
        cdate = note.get("cdate")
        if cdate:
            try:
                year = datetime.fromtimestamp(cdate / 1000, tz=timezone.utc).year
            except Exception:
                pass

        # Authors may be a list of strings or dicts
        raw_authors = content.get("authors", [])
        authors = [a if isinstance(a, str) else a.get("name", "") for a in raw_authors]

        return ResearchSource(
            id=note_id,
            title=content.get("title", ""),
            source_type=SourceType.PAPER,
            url=f"https://openreview.net/forum?id={note_id}",
            authors=authors,
            published_date=datetime(year, 1, 1) if year else None,
            abstract=content.get("abstract", ""),
            metadata={
                "venue": venue,
                "year": year,
                "openreview_id": note_id,
            },
        )


# ---------------------------------------------------------------------------
# HuggingFace Papers
# ---------------------------------------------------------------------------

class HuggingFacePapersDiscovery:
    """Discover papers from the HuggingFace Hub papers API."""

    SEARCH_URL = "https://huggingface.co/api/papers"
    DAILY_URL = "https://huggingface.co/api/daily_papers"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize HuggingFace papers discovery.

        Args:
            api_key: Optional HuggingFace API token.
        """
        self.api_key = api_key or os.environ.get("HF_API_KEY")

    def search(self, query: str, max_results: int = 50) -> List[ResearchSource]:
        """
        Search HuggingFace for papers.

        Args:
            query: Search query.
            max_results: Maximum number of results.

        Returns:
            List of discovered papers.
        """
        try:
            headers: Dict[str, str] = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            params = {"search": query, "limit": min(max_results, 100)}
            response = requests.get(
                self.SEARCH_URL,
                params=params,
                headers=headers,
                timeout=30,
            )
            if response.status_code != 200:
                print(f"HuggingFace API error: {response.status_code}")
                return []

            papers = response.json()
            if not isinstance(papers, list):
                papers = papers.get("papers", [])
            return [self._to_source(p) for p in papers[:max_results]]

        except Exception as e:
            print(f"HuggingFace search error: {e}")
            return []

    def get_daily_papers(self) -> List[ResearchSource]:
        """
        Fetch today's trending papers from HuggingFace.

        Returns:
            List of daily papers.
        """
        try:
            response = requests.get(self.DAILY_URL, timeout=30)
            if response.status_code != 200:
                print(f"HuggingFace daily papers error: {response.status_code}")
                return []

            papers = response.json()
            if not isinstance(papers, list):
                papers = papers.get("papers", [])
            return [self._to_source(p) for p in papers]

        except Exception as e:
            print(f"HuggingFace daily papers error: {e}")
            return []

    def _to_source(self, paper: Dict[str, Any]) -> ResearchSource:
        """Convert a HuggingFace paper dict to a ResearchSource."""
        paper_id = paper.get("id", "")
        published_at = paper.get("publishedAt") or paper.get("published_at")
        published_date: Optional[datetime] = None
        if published_at:
            try:
                published_date = datetime.fromisoformat(
                    str(published_at).replace("Z", "+00:00")
                )
            except Exception:
                pass

        authors = [
            a.get("name", a) if isinstance(a, dict) else str(a)
            for a in paper.get("authors", [])
        ]

        return ResearchSource(
            id=paper_id,
            title=paper.get("title", ""),
            source_type=SourceType.PAPER,
            url=f"https://huggingface.co/papers/{paper_id}",
            authors=authors,
            published_date=published_date,
            abstract=paper.get("summary", paper.get("abstract", "")),
            citations=paper.get("upvotes", 0),
            metadata={
                "upvotes": paper.get("upvotes", 0),
                "arxiv_id": paper_id,
            },
        )


# ---------------------------------------------------------------------------
# Papers with Code
# ---------------------------------------------------------------------------

class PapersWithCodeDiscovery:
    """Discover papers from Papers with Code."""

    BASE_URL = "https://paperswithcode.com/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Papers with Code discovery.

        Args:
            api_key: Optional PwC API key.
        """
        self.api_key = api_key or os.environ.get("PWC_API_KEY")

    def search(self, query: str, max_results: int = 50) -> List[ResearchSource]:
        """
        Search Papers with Code for papers with exponential backoff retry.

        Args:
            query: Search query.
            max_results: Maximum number of results.

        Returns:
            List of discovered papers.
        """
        import time

        max_retries = 3
        base_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                headers: Dict[str, str] = {}
                if self.api_key:
                    headers["Authorization"] = f"Token {self.api_key}"

                params = {"q": query, "items_per_page": min(max_results, 50)}
                response = requests.get(
                    f"{self.BASE_URL}/papers/",
                    params=params,
                    headers=headers,
                    timeout=30,
                    allow_redirects=True,
                )

                if response.status_code == 429:  # Rate limited
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"Papers with Code rate limited. Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"Papers with Code API error: Rate limit exceeded after {max_retries} attempts")
                        return []

                if response.status_code != 200:
                    print(f"Papers with Code API error: {response.status_code}")
                    return []

                data = response.json()
                papers = data.get("results", [])
                return [self._to_source(p) for p in papers[:max_results]]

            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    print(f"Papers with Code error: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    print(f"Papers with Code search error after {max_retries} attempts: {e}")
                    return []

        return []

    def _to_source(self, paper: Dict[str, Any]) -> ResearchSource:
        """Convert a PwC paper dict to a ResearchSource."""
        paper_id = paper.get("id", "")
        published_str = paper.get("published", "")
        published_date: Optional[datetime] = None
        if published_str:
            try:
                published_date = datetime.fromisoformat(
                    str(published_str).replace("Z", "+00:00")
                )
            except Exception:
                pass

        # Collect linked GitHub repos
        github_links = [r.get("url", "") for r in paper.get("repositories", []) if r.get("url")]
        authors = paper.get("authors", [])
        if isinstance(authors, list) and authors and isinstance(authors[0], dict):
            authors = [a.get("name", "") for a in authors]

        return ResearchSource(
            id=paper_id,
            title=paper.get("title", ""),
            source_type=SourceType.PAPER,
            url=paper.get("url_abs", f"https://paperswithcode.com/paper/{paper_id}"),
            authors=authors,
            published_date=published_date,
            abstract=paper.get("abstract", ""),
            metadata={
                "tasks": paper.get("tasks", []),
                "methods": paper.get("methods", []),
                "github_links": github_links,
                "sota_results": bool(paper.get("sota")),
            },
        )


# ---------------------------------------------------------------------------
# ACL Anthology (via Semantic Scholar venue filter)
# ---------------------------------------------------------------------------

class ACLAnthologyDiscovery:
    """Discover ACL Anthology papers via Semantic Scholar venue filter."""

    ACL_VENUES = ["ACL", "EMNLP", "NAACL", "EACL", "COLING", "TACL", "CL"]
    SS_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ACL Anthology discovery.

        Args:
            api_key: Optional Semantic Scholar API key.
        """
        self.api_key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

    def search(self, query: str, max_results: int = 50) -> List[ResearchSource]:
        """
        Search for ACL Anthology papers.

        Args:
            query: Search query.
            max_results: Maximum number of results.

        Returns:
            List of discovered papers.
        """
        try:
            headers: Dict[str, str] = {}
            if self.api_key:
                headers["x-api-key"] = self.api_key

            params = {
                "query": query,
                "limit": min(max_results, 100),
                "fields": "paperId,title,abstract,authors,year,citationCount,url,venue,externalIds",
            }
            response = requests.get(
                f"{self.SS_URL}/paper/search",
                params=params,
                headers=headers,
                timeout=30,
            )
            if response.status_code != 200:
                print(f"ACL Anthology (Semantic Scholar) error: {response.status_code}")
                return []

            data = response.json()
            sources = []
            for paper in data.get("data", []):
                venue = paper.get("venue", "")
                if not self._is_acl_venue(venue):
                    continue
                sources.append(self._to_source(paper))
                if len(sources) >= max_results:
                    break

            return sources

        except Exception as e:
            print(f"ACL Anthology search error: {e}")
            return []

    def _is_acl_venue(self, venue: str) -> bool:
        """Return True if the venue belongs to ACL Anthology."""
        venue_upper = venue.upper()
        return any(v in venue_upper for v in self.ACL_VENUES)

    def _to_source(self, paper: Dict[str, Any]) -> ResearchSource:
        """Convert a Semantic Scholar paper dict to a ResearchSource."""
        year = paper.get("year")
        external_ids = paper.get("externalIds", {})
        anthology_id = external_ids.get("ACL", "")

        return ResearchSource(
            id=paper.get("paperId", ""),
            title=paper.get("title", ""),
            source_type=SourceType.PAPER,
            url=paper.get("url", ""),
            authors=[a.get("name", "") for a in paper.get("authors", [])],
            published_date=datetime(year, 1, 1) if year else None,
            abstract=paper.get("abstract", ""),
            citations=paper.get("citationCount", 0),
            metadata={
                "venue": paper.get("venue", ""),
                "anthology_id": anthology_id,
            },
        )


# ---------------------------------------------------------------------------
# Citation traversal
# ---------------------------------------------------------------------------

class CitationTraversal:
    """
    Traverse citation networks via Semantic Scholar.

    Supports forward citations (papers that cite a seed), backward references
    (papers cited by the seed), and BFS snowballing up to a given depth.
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    PAPER_FIELDS = "paperId,title,abstract,authors,year,citationCount,url,venue"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize citation traversal.

        Args:
            api_key: Optional Semantic Scholar API key.
        """
        self.api_key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {}
        if self.api_key:
            h["x-api-key"] = self.api_key
        return h

    def get_citations(self, paper_id: str, max_results: int = 20) -> List[ResearchSource]:
        """
        Return papers that CITE this paper (forward citation).

        Args:
            paper_id: Semantic Scholar paper ID.
            max_results: Maximum number of results.

        Returns:
            List of citing papers.
        """
        try:
            params = {"fields": self.PAPER_FIELDS, "limit": min(max_results, 100)}
            response = requests.get(
                f"{self.BASE_URL}/paper/{paper_id}/citations",
                params=params,
                headers=self._headers(),
                timeout=30,
            )
            if response.status_code != 200:
                print(f"CitationTraversal.get_citations error: {response.status_code}")
                return []

            data = response.json()
            sources = []
            for entry in data.get("data", []):
                citing = entry.get("citingPaper", {})
                if citing:
                    sources.append(self._to_source(citing))
            return sources[:max_results]

        except Exception as e:
            print(f"CitationTraversal.get_citations error: {e}")
            return []

    def get_references(self, paper_id: str, max_results: int = 20) -> List[ResearchSource]:
        """
        Return papers that this paper CITES (backward references).

        Args:
            paper_id: Semantic Scholar paper ID.
            max_results: Maximum number of results.

        Returns:
            List of referenced papers.
        """
        try:
            params = {"fields": self.PAPER_FIELDS, "limit": min(max_results, 100)}
            response = requests.get(
                f"{self.BASE_URL}/paper/{paper_id}/references",
                params=params,
                headers=self._headers(),
                timeout=30,
            )
            if response.status_code != 200:
                print(f"CitationTraversal.get_references error: {response.status_code}")
                return []

            data = response.json()
            sources = []
            for entry in data.get("data", []):
                cited = entry.get("citedPaper", {})
                if cited:
                    sources.append(self._to_source(cited))
            return sources[:max_results]

        except Exception as e:
            print(f"CitationTraversal.get_references error: {e}")
            return []

    def snowball(
        self,
        seed_paper_id: str,
        depth: int = 2,
        max_per_hop: int = 10,
    ) -> List[ResearchSource]:
        """
        BFS citation traversal up to `depth` hops from the seed paper.

        Combines forward citations and backward references at each hop.

        Args:
            seed_paper_id: Semantic Scholar paper ID to start from.
            depth: Maximum hop depth (1 = immediate neighbours only).
            max_per_hop: Maximum papers to fetch per hop.

        Returns:
            Deduplicated list of all discovered papers.
        """
        seen_ids: set = {seed_paper_id}
        frontier = [seed_paper_id]
        all_sources: List[ResearchSource] = []

        for _ in range(depth):
            next_frontier: List[str] = []
            for pid in frontier:
                citations = self.get_citations(pid, max_per_hop)
                references = self.get_references(pid, max_per_hop)
                for source in citations + references:
                    if source.id not in seen_ids:
                        seen_ids.add(source.id)
                        all_sources.append(source)
                        next_frontier.append(source.id)
            frontier = next_frontier
            if not frontier:
                break

        return all_sources

    def _to_source(self, paper: Dict[str, Any]) -> ResearchSource:
        """Convert a Semantic Scholar paper dict to a ResearchSource."""
        year = paper.get("year")
        return ResearchSource(
            id=paper.get("paperId", ""),
            title=paper.get("title", ""),
            source_type=SourceType.PAPER,
            url=paper.get("url", ""),
            authors=[a.get("name", "") for a in paper.get("authors", [])],
            published_date=datetime(year, 1, 1) if year else None,
            abstract=paper.get("abstract", ""),
            citations=paper.get("citationCount", 0),
            metadata={"venue": paper.get("venue", ""), "year": year},
        )


# ---------------------------------------------------------------------------
# GitHub activity scorer
# ---------------------------------------------------------------------------

class GitHubActivityScorer:
    """
    Compute an activity score for a GitHub repository.

    Score = stars×0.30 + recent_commits×0.30 + contributors×0.20 + issue_close_rate×0.20
    """

    GH_API = "https://api.github.com"

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize the scorer.

        Args:
            github_token: Optional GitHub personal access token.
        """
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/vnd.github.v3+json"}
        if self.github_token:
            h["Authorization"] = f"token {self.github_token}"
        return h

    def score(self, repo_metadata: Dict[str, Any]) -> float:
        """
        Compute an activity score from already-fetched repo metadata.

        Args:
            repo_metadata: Dict with keys: stars, commits_per_month,
                           contributors, closed_issues_ratio.

        Returns:
            Float in [0.0, 1.0].
        """
        stars = repo_metadata.get("stars", repo_metadata.get("stargazers_count", 0))
        commits_per_month = repo_metadata.get("commits_per_month", 0)
        contributors = repo_metadata.get("contributors", 0)
        closed_issues_ratio = repo_metadata.get("closed_issues_ratio", 0.0)

        # Normalise each component to [0, 1]
        star_score = min(stars / 10_000, 1.0)
        commit_score = min(commits_per_month / 100, 1.0)
        contributor_score = min(contributors / 50, 1.0)
        issue_score = float(closed_issues_ratio)

        return (
            0.30 * star_score
            + 0.30 * commit_score
            + 0.20 * contributor_score
            + 0.20 * issue_score
        )

    def enrich_source(
        self,
        source: ResearchSource,
        github_token: Optional[str] = None,
    ) -> ResearchSource:
        """
        Fetch additional GitHub stats and attach an activity_score to metadata.

        Makes live API calls to get commits/month, contributors, and issues.

        Args:
            source: A ResearchSource of type REPOSITORY.
            github_token: Optional override token for this call.

        Returns:
            New ResearchSource with enriched metadata (never mutates the original).
        """
        token = github_token or self.github_token
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"

        # Extract owner/repo from URL
        parts = source.url.rstrip("/").split("/")
        if len(parts) < 2:
            return source
        owner, repo = parts[-2], parts[-1]

        extra: Dict[str, Any] = {}
        try:
            extra["commits_per_month"] = self._fetch_commits_per_month(owner, repo, headers)
            extra["contributors"] = self._fetch_contributor_count(owner, repo, headers)
            extra["closed_issues_ratio"] = self._fetch_closed_issues_ratio(owner, repo, headers)
        except Exception as e:
            print(f"GitHubActivityScorer.enrich_source error: {e}")

        enriched_metadata = {**source.metadata, **extra}
        enriched_metadata["activity_score"] = self.score(
            {**enriched_metadata, "stars": source.stars}
        )

        return ResearchSource(
            id=source.id,
            title=source.title,
            source_type=source.source_type,
            url=source.url,
            authors=source.authors,
            published_date=source.published_date,
            abstract=source.abstract,
            citations=source.citations,
            stars=source.stars,
            metadata=enriched_metadata,
            discovered_at=source.discovered_at,
        )

    def _fetch_commits_per_month(
        self, owner: str, repo: str, headers: Dict[str, str]
    ) -> float:
        """Return approximate commits per month over the last 4 weeks."""
        response = requests.get(
            f"{self.GH_API}/repos/{owner}/{repo}/commits",
            params={"per_page": 100, "since": self._one_month_ago()},
            headers=headers,
            timeout=20,
        )
        if response.status_code == 200:
            return float(len(response.json()))
        return 0.0

    def _fetch_contributor_count(
        self, owner: str, repo: str, headers: Dict[str, str]
    ) -> int:
        """Return the number of contributors (capped at first page)."""
        response = requests.get(
            f"{self.GH_API}/repos/{owner}/{repo}/contributors",
            params={"per_page": 100, "anon": "false"},
            headers=headers,
            timeout=20,
        )
        if response.status_code == 200:
            return len(response.json())
        return 0

    def _fetch_closed_issues_ratio(
        self, owner: str, repo: str, headers: Dict[str, str]
    ) -> float:
        """Return ratio closed / (closed + open) issues."""
        open_resp = requests.get(
            f"{self.GH_API}/repos/{owner}/{repo}",
            headers=headers,
            timeout=20,
        )
        if open_resp.status_code != 200:
            return 0.0
        repo_data = open_resp.json()
        open_issues = repo_data.get("open_issues_count", 0)

        closed_resp = requests.get(
            f"{self.GH_API}/repos/{owner}/{repo}/issues",
            params={"state": "closed", "per_page": 1},
            headers=headers,
            timeout=20,
        )
        # Use Link header to estimate count, fallback to 0
        closed_count = 0
        if closed_resp.status_code == 200:
            link = closed_resp.headers.get("Link", "")
            if 'rel="last"' in link:
                import re
                m = re.search(r"page=(\d+)>; rel=\"last\"", link)
                if m:
                    closed_count = int(m.group(1))
            else:
                closed_count = len(closed_resp.json())

        total = open_issues + closed_count
        return closed_count / total if total > 0 else 0.0

    @staticmethod
    def _one_month_ago() -> str:
        """Return ISO-8601 timestamp for 30 days ago."""
        from datetime import timedelta
        dt = datetime.now(tz=timezone.utc) - timedelta(days=30)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Multi-signal source quality scorer
# ---------------------------------------------------------------------------

class SourceQualityScorer:
    """
    Rank research sources using multiple signals.

    Score = citations×0.25 + recency×0.25 + venue_tier×0.25 + relevance×0.25
    """

    VENUE_TIERS: Dict[str, float] = {
        "NeurIPS": 1.0,
        "ICML": 1.0,
        "ICLR": 1.0,
        "COLM": 0.95,
        "ACL": 0.95,
        "CVPR": 0.95,
        "SOSP": 0.95,
        "OSDI": 0.95,
        "EMNLP": 0.90,
        "ICCV": 0.90,
        "USENIX": 0.90,
        "NAACL": 0.85,
        "ECCV": 0.85,
        "arXiv": 0.50,
    }

    def score(self, source: ResearchSource, query: str) -> float:
        """
        Compute a [0.0, 1.0] quality score for a source.

        Args:
            source: Research source to score.
            query: Original search query (used for relevance).

        Returns:
            Float in [0.0, 1.0].
        """
        citations_score = self._citation_score(source)
        recency_score = self._recency_score(source)
        venue_score = self._venue_score(source)
        relevance_score = self._relevance_score(source, query)

        return (
            0.25 * citations_score
            + 0.25 * recency_score
            + 0.25 * venue_score
            + 0.25 * relevance_score
        )

    def rank(
        self, sources: List[ResearchSource], query: str
    ) -> List[Tuple[ResearchSource, float]]:
        """
        Rank sources by quality score descending.

        Args:
            sources: Sources to rank.
            query: Original search query.

        Returns:
            List of (source, score) tuples sorted by score descending.
        """
        scored = [(s, self.score(s, query)) for s in sources]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _citation_score(self, source: ResearchSource) -> float:
        """Normalise citation count to [0, 1] with log-scale dampening."""
        import math
        citations = source.citations or 0
        if citations <= 0:
            return 0.0
        # log10(1000) ≈ 3 → score capped at 1.0 for ≥1000 citations
        return min(math.log10(citations + 1) / 3.0, 1.0)

    def _recency_score(self, source: ResearchSource) -> float:
        """Papers from last 2 years score 1.0; older papers decay linearly."""
        if not source.published_date:
            return 0.5  # Unknown date: neutral
        now = datetime.now()
        # Strip timezone if present
        pub = source.published_date.replace(tzinfo=None) if source.published_date.tzinfo else source.published_date
        days_old = (now - pub).days
        # Full score for ≤730 days (~2 years), zero for ≥3650 days (~10 years)
        score = 1.0 - max(0, days_old - 730) / (3650 - 730)
        return max(0.0, min(score, 1.0))

    def _venue_score(self, source: ResearchSource) -> float:
        """Look up venue tier; fall back to 0.3 for unknown venues."""
        venue = source.metadata.get("venue", "")
        if not venue:
            return 0.3
        for key, tier in self.VENUE_TIERS.items():
            if key.lower() in venue.lower():
                return tier
        return 0.3

    def _relevance_score(self, source: ResearchSource, query: str) -> float:
        """Simple term-overlap relevance against title + abstract."""
        text = f"{source.title} {source.abstract}".lower()
        terms = query.lower().split()
        if not terms:
            return 0.0
        matches = sum(1 for t in terms if t in text)
        return matches / len(terms)
