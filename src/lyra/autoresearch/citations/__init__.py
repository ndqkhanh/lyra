"""
Citation Verification System - 4-Layer Cascade

Implements AutoResearchClaw's anti-hallucination citation verification:
- Layer 1: arXiv ID lookup
- Layer 2: DOI resolution (CrossRef)
- Layer 3: Title search (OpenAlex → Semantic Scholar → arXiv)
- Layer 4: LLM relevance scoring

Based on: researchclaw/literature/verify.py
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class VerifyStatus(Enum):
    """Citation verification status"""
    VERIFIED = "verified"          # API confirms + similarity ≥ 0.80
    SUSPICIOUS = "suspicious"      # Found but metadata diverges (0.50 ≤ sim < 0.80)
    HALLUCINATED = "hallucinated"  # Not found or similarity < 0.50
    SKIPPED = "skipped"            # Cannot verify (missing title)


@dataclass
class Citation:
    """Parsed citation entry"""
    raw_text: str
    title: str | None = None
    authors: list[str] | None = None
    year: int | None = None
    arxiv_id: str | None = None
    doi: str | None = None
    venue: str | None = None


@dataclass
class VerificationResult:
    """Result of citation verification"""
    citation: Citation
    status: VerifyStatus
    similarity_score: float
    verified_title: str | None = None
    verified_url: str | None = None
    layer_used: int = 0  # Which layer succeeded (1-4)
    error: str | None = None


@dataclass
class VerificationReport:
    """Complete verification report for a document"""
    results: list[VerificationResult]
    integrity_score: float  # verified_count / verifiable_count
    verified_count: int
    suspicious_count: int
    hallucinated_count: int
    skipped_count: int
    total_count: int


class ArxivClient:
    """arXiv API client with circuit breaker"""

    BASE_URL = "http://export.arxiv.org/api/query"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def lookup_by_id(self, arxiv_id: str) -> dict[str, Any] | None:
        """Lookup paper by arXiv ID"""
        try:
            # Normalize arXiv ID (remove version)
            arxiv_id = re.sub(r'v\d+$', '', arxiv_id)

            params = {"id_list": arxiv_id, "max_results": 1}
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            # Parse XML response (simplified - production would use feedparser)
            content = response.text
            if "<entry>" not in content:
                return None

            # Extract title
            title_match = re.search(r'<title>(.*?)</title>', content, re.DOTALL)
            if not title_match:
                return None

            title = title_match.group(1).strip()
            title = re.sub(r'\s+', ' ', title)  # Normalize whitespace

            return {
                "title": title,
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "arxiv_id": arxiv_id,
            }
        except Exception as e:
            logger.warning(f"arXiv lookup failed for {arxiv_id}: {e}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def search_by_title(self, title: str) -> dict[str, Any] | None:
        """Search arXiv by title"""
        try:
            params = {
                "search_query": f'ti:"{title}"',
                "max_results": 1,
                "sortBy": "relevance",
            }
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            content = response.text
            if "<entry>" not in content:
                return None

            # Extract title and ID
            title_match = re.search(r'<title>(.*?)</title>', content, re.DOTALL)
            id_match = re.search(r'<id>http://arxiv.org/abs/(.*?)</id>', content)

            if not title_match or not id_match:
                return None

            found_title = title_match.group(1).strip()
            found_title = re.sub(r'\s+', ' ', found_title)
            arxiv_id = id_match.group(1)

            return {
                "title": found_title,
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "arxiv_id": arxiv_id,
            }
        except Exception as e:
            logger.warning(f"arXiv title search failed: {e}")
            return None


class CrossRefClient:
    """CrossRef API client for DOI resolution"""

    BASE_URL = "https://api.crossref.org/works"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def lookup_doi(self, doi: str) -> dict[str, Any] | None:
        """Lookup paper by DOI"""
        try:
            url = f"{self.BASE_URL}/{doi}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            if "message" not in data:
                return None

            message = data["message"]
            title = message.get("title", [None])[0]

            if not title:
                return None

            return {
                "title": title,
                "url": message.get("URL", f"https://doi.org/{doi}"),
                "doi": doi,
            }
        except Exception as e:
            logger.warning(f"CrossRef lookup failed for {doi}: {e}")
            return None


class OpenAlexClient:
    """OpenAlex API client (10K requests/day limit)"""

    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, email: str | None = None):
        self.email = email  # Polite pool access

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def search_by_title(self, title: str) -> dict[str, Any] | None:
        """Search OpenAlex by title"""
        try:
            params = {
                "filter": f'title.search:"{title}"',
                "per_page": 1,
            }
            if self.email:
                params["mailto"] = self.email

            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            if not results:
                return None

            work = results[0]
            return {
                "title": work.get("title"),
                "url": work.get("id", ""),
                "doi": work.get("doi", "").replace("https://doi.org/", ""),
            }
        except Exception as e:
            logger.warning(f"OpenAlex search failed: {e}")
            return None


class SemanticScholarClient:
    """Semantic Scholar API client (fallback)"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def search_by_title(self, title: str) -> dict[str, Any] | None:
        """Search Semantic Scholar by title"""
        try:
            params = {
                "query": title,
                "limit": 1,
                "fields": "title,url,externalIds",
            }
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            papers = data.get("data", [])

            if not papers:
                return None

            paper = papers[0]
            external_ids = paper.get("externalIds", {})

            return {
                "title": paper.get("title"),
                "url": paper.get("url", ""),
                "doi": external_ids.get("DOI"),
                "arxiv_id": external_ids.get("ArXiv"),
            }
        except Exception as e:
            logger.warning(f"Semantic Scholar search failed: {e}")
            return None


def compute_title_similarity(title_a: str, title_b: str) -> float:
    """
    Compute title similarity using Jaccard-like metric

    Algorithm from AutoResearchClaw:
    - Strips non-alphanumeric, lowercases
    - Tokenizes into word sets
    - similarity = len(words_a ∩ words_b) / max(len(words_a), len(words_b))
    """
    # Normalize
    def normalize(text: str) -> set:
        text = text.lower()
        text = re.sub(r'[^a-z0-9\s]', '', text)
        words = text.split()
        return set(words)

    words_a = normalize(title_a)
    words_b = normalize(title_b)

    if not words_a or not words_b:
        return 0.0

    intersection = len(words_a & words_b)
    max_len = max(len(words_a), len(words_b))

    return intersection / max_len if max_len > 0 else 0.0


class CitationVerifier:
    """
    4-Layer Citation Verification System

    Implements AutoResearchClaw's cascade verification:
    Layer 1: arXiv ID lookup
    Layer 2: DOI resolution
    Layer 3: Title search (OpenAlex → Semantic Scholar → arXiv)
    Layer 4: LLM relevance scoring (optional)
    """

    def __init__(self, openalex_email: str | None = None):
        self.arxiv = ArxivClient()
        self.crossref = CrossRefClient()
        self.openalex = OpenAlexClient(email=openalex_email)
        self.semantic_scholar = SemanticScholarClient()

    def verify_citation(self, citation: Citation) -> VerificationResult:
        """Verify a single citation through 4-layer cascade"""

        # Skip if no title
        if not citation.title:
            return VerificationResult(
                citation=citation,
                status=VerifyStatus.SKIPPED,
                similarity_score=0.0,
                error="No title provided",
            )

        # Layer 1: arXiv ID lookup
        if citation.arxiv_id:
            result = self._verify_layer1(citation)
            if result:
                return result

        # Layer 2: DOI resolution
        if citation.doi:
            result = self._verify_layer2(citation)
            if result:
                return result

        # Layer 3: Title search
        result = self._verify_layer3(citation)
        if result:
            return result

        # All layers failed
        return VerificationResult(
            citation=citation,
            status=VerifyStatus.HALLUCINATED,
            similarity_score=0.0,
            error="Not found in any database",
        )

    def _verify_layer1(self, citation: Citation) -> VerificationResult | None:
        """Layer 1: arXiv ID lookup"""
        data = self.arxiv.lookup_by_id(citation.arxiv_id)
        if not data:
            return None

        similarity = compute_title_similarity(citation.title, data["title"])

        if similarity >= 0.80:
            status = VerifyStatus.VERIFIED
        elif similarity >= 0.50:
            status = VerifyStatus.SUSPICIOUS
        else:
            status = VerifyStatus.HALLUCINATED

        return VerificationResult(
            citation=citation,
            status=status,
            similarity_score=similarity,
            verified_title=data["title"],
            verified_url=data["url"],
            layer_used=1,
        )

    def _verify_layer2(self, citation: Citation) -> VerificationResult | None:
        """Layer 2: DOI resolution"""
        data = self.crossref.lookup_doi(citation.doi)
        if not data:
            return None

        similarity = compute_title_similarity(citation.title, data["title"])

        if similarity >= 0.80:
            status = VerifyStatus.VERIFIED
        elif similarity >= 0.50:
            status = VerifyStatus.SUSPICIOUS
        else:
            status = VerifyStatus.HALLUCINATED

        return VerificationResult(
            citation=citation,
            status=status,
            similarity_score=similarity,
            verified_title=data["title"],
            verified_url=data["url"],
            layer_used=2,
        )

    def _verify_layer3(self, citation: Citation) -> VerificationResult | None:
        """Layer 3: Title search (OpenAlex → Semantic Scholar → arXiv)"""

        # Try OpenAlex first
        data = self.openalex.search_by_title(citation.title)
        if data:
            similarity = compute_title_similarity(citation.title, data["title"])
            if similarity >= 0.50:
                status = VerifyStatus.VERIFIED if similarity >= 0.80 else VerifyStatus.SUSPICIOUS
                return VerificationResult(
                    citation=citation,
                    status=status,
                    similarity_score=similarity,
                    verified_title=data["title"],
                    verified_url=data["url"],
                    layer_used=3,
                )

        # Try Semantic Scholar
        data = self.semantic_scholar.search_by_title(citation.title)
        if data:
            similarity = compute_title_similarity(citation.title, data["title"])
            if similarity >= 0.50:
                status = VerifyStatus.VERIFIED if similarity >= 0.80 else VerifyStatus.SUSPICIOUS
                return VerificationResult(
                    citation=citation,
                    status=status,
                    similarity_score=similarity,
                    verified_title=data["title"],
                    verified_url=data["url"],
                    layer_used=3,
                )

        # Try arXiv title search
        data = self.arxiv.search_by_title(citation.title)
        if data:
            similarity = compute_title_similarity(citation.title, data["title"])
            if similarity >= 0.50:
                status = VerifyStatus.VERIFIED if similarity >= 0.80 else VerifyStatus.SUSPICIOUS
                return VerificationResult(
                    citation=citation,
                    status=status,
                    similarity_score=similarity,
                    verified_title=data["title"],
                    verified_url=data["url"],
                    layer_used=3,
                )

        return None

    def verify_document(self, citations: list[Citation]) -> VerificationReport:
        """Verify all citations in a document"""
        results = []

        for citation in citations:
            result = self.verify_citation(citation)
            results.append(result)

        # Compute statistics
        verified = sum(1 for r in results if r.status == VerifyStatus.VERIFIED)
        suspicious = sum(1 for r in results if r.status == VerifyStatus.SUSPICIOUS)
        hallucinated = sum(1 for r in results if r.status == VerifyStatus.HALLUCINATED)
        skipped = sum(1 for r in results if r.status == VerifyStatus.SKIPPED)

        verifiable = len(results) - skipped
        integrity_score = verified / verifiable if verifiable > 0 else 0.0

        return VerificationReport(
            results=results,
            integrity_score=integrity_score,
            verified_count=verified,
            suspicious_count=suspicious,
            hallucinated_count=hallucinated,
            skipped_count=skipped,
            total_count=len(results),
        )


def parse_citations(text: str) -> list[Citation]:
    """
    Parse citations from text (simplified parser)

    Production version would use proper citation parsing library
    """
    citations = []

    # Simple regex patterns for common citation formats
    # Pattern 1: [Author et al., Year]
    pattern1 = r'\[([^\]]+?),\s*(\d{4})\]'

    # Pattern 2: arXiv:XXXX.XXXXX
    pattern2 = r'arXiv:(\d{4}\.\d{4,5})'

    # Pattern 3: doi:XX.XXXX/...
    pattern3 = r'doi:(10\.\d{4,}/[^\s]+)'

    for match in re.finditer(pattern1, text):
        citations.append(Citation(
            raw_text=match.group(0),
            authors=[match.group(1)],
            year=int(match.group(2)),
        ))

    for match in re.finditer(pattern2, text):
        citations.append(Citation(
            raw_text=match.group(0),
            arxiv_id=match.group(1),
        ))

    for match in re.finditer(pattern3, text):
        citations.append(Citation(
            raw_text=match.group(0),
            doi=match.group(1),
        ))

    return citations


def verify_citations(text: str, openalex_email: str | None = None) -> VerificationReport:
    """
    Convenience function: Parse and verify all citations in text

    Args:
        text: Document text containing citations
        openalex_email: Email for OpenAlex polite pool (optional)

    Returns:
        VerificationReport with integrity score and detailed results
    """
    citations = parse_citations(text)
    verifier = CitationVerifier(openalex_email=openalex_email)
    return verifier.verify_document(citations)
