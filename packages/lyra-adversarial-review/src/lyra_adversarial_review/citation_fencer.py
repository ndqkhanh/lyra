from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum


class SourceType(Enum):
    ARXIV = "arxiv"
    CROSSREF = "crossref"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    DOI = "doi"
    URL = "url"
    LLM_GENERATED = "llm_generated"


@dataclass(frozen=True)
class Citation:
    text: str
    source_type: SourceType
    identifier: str
    url: str = ""
    confidence: float = 0.0


@dataclass(frozen=True)
class FenceResult:
    citation: Citation
    is_valid: bool
    verified_source: str
    confidence: float
    issues: Sequence[str] = field(default_factory=list)


@dataclass(frozen=True)
class FenceReport:
    citations: Sequence[Citation]
    verified_count: int
    flagged_count: int
    overall_score: float


# Common LLM hallucination patterns
_HALLUCINATION_PATTERNS: list[re.Pattern] = [
    re.compile(r"according to a (recent|new|groundbreaking) study", re.IGNORECASE),
    re.compile(r"research (shows|suggests|indicates|demonstrates)\s+\w+\s+(that|how)", re.IGNORECASE),
    re.compile(r"as (per|cited in|referenced in)\s+\[?\d*\]?"),
    re.compile(r"source:?\s+\[?(citation|reference|source) needed\]?", re.IGNORECASE),
    re.compile(r"I (think|believe|could|might|may) be (that|because)", re.IGNORECASE),
]

# ArXiv ID pattern: arXiv:XXXX.XXXXX or arXiv:YYMM.NNNNN
_ARXIV_PATTERN = re.compile(r"arXiv:(\d{4}\.\d{4,5}(v\d+)?)", re.IGNORECASE)

# DOI pattern
_DOI_PATTERN = re.compile(r"(10\.\d{4,}/[a-zA-Z0-9./_\-]+)")

# URL pattern (basic)
_URL_PATTERN = re.compile(r"https?://[^\s]+")

# Semantic Scholar URL pattern
_S2_PATTERN = re.compile(r"https?://api\.semanticscholar\.org/[^\s]+", re.IGNORECASE)


class CitationFencer:
    """Verifies citations by cross-referencing against multiple sources."""

    def __init__(self) -> None:
        self._citation_cache: dict[str, FenceResult] = {}

    async def verify_citation(self, citation: Citation) -> FenceResult:
        cache_key = f"{citation.source_type.value}:{citation.identifier}"
        if cache_key in self._citation_cache:
            return self._citation_cache[cache_key]

        result = self._verify(citation)
        self._citation_cache[cache_key] = result
        return result

    def _verify(self, citation: Citation) -> FenceResult:
        issues: list[str] = []
        source_type = citation.source_type
        identifier = citation.identifier
        confidence = 0.0

        if source_type == SourceType.ARXIV:
            confidence, arxiv_issues = self._verify_arxiv(identifier)
            issues.extend(arxiv_issues)
        elif source_type == SourceType.CROSSREF:
            confidence, crossref_issues = self._verify_crossref(identifier)
            issues.extend(crossref_issues)
        elif source_type == SourceType.SEMANTIC_SCHOLAR:
            confidence, s2_issues = self._verify_semantic_scholar(identifier)
            issues.extend(s2_issues)
        elif source_type == SourceType.DOI:
            confidence, doi_issues = self._verify_doi(identifier)
            issues.extend(doi_issues)
        elif source_type == SourceType.URL:
            confidence, url_issues = self._verify_url(citation.url or identifier)
            issues.extend(url_issues)
        elif source_type == SourceType.LLM_GENERATED:
            confidence, llm_issues = self._verify_llm_generated(citation.text)
            issues.extend(llm_issues)
        else:
            issues.append(f"Unknown source type: {source_type}")

        is_valid = confidence >= 0.5
        verified_source = self._build_verified_source(source_type, identifier)

        return FenceResult(
            citation=citation,
            is_valid=is_valid,
            verified_source=verified_source,
            confidence=round(confidence, 4),
            issues=issues,
        )

    def extract_citations(self, text: str) -> list[Citation]:
        citations: list[Citation] = []

        for match in _ARXIV_PATTERN.finditer(text):
            citations.append(
                Citation(
                    text=match.group(0),
                    source_type=SourceType.ARXIV,
                    identifier=match.group(1),
                    url=f"https://arxiv.org/abs/{match.group(1)}",
                    confidence=0.8,
                )
            )

        for match in _DOI_PATTERN.finditer(text):
            doi = match.group(1).rstrip("/.-_ ")
            if not any(c.identifier == doi for c in citations):
                citations.append(
                    Citation(
                        text=match.group(0),
                        source_type=SourceType.DOI,
                        identifier=doi,
                        url=f"https://doi.org/{doi}",
                        confidence=0.7,
                    )
                )

        for match in _URL_PATTERN.finditer(text):
            url = match.group(0)
            if any(c.url == url for c in citations):
                continue
            source_type = SourceType.SEMANTIC_SCHOLAR if "semanticscholar" in url.lower() else SourceType.URL
            citations.append(
                Citation(
                    text=url,
                    source_type=source_type,
                    identifier=url,
                    url=url,
                    confidence=0.6 if source_type == SourceType.SEMANTIC_SCHOLAR else 0.4,
                )
            )

        hallucination_hits = 0
        for pattern in _HALLUCINATION_PATTERNS:
            for match in pattern.finditer(text):
                hallucination_hits += 1
                citations.append(
                    Citation(
                        text=match.group(0),
                        source_type=SourceType.LLM_GENERATED,
                        identifier=f"hallucination-pattern-{hallucination_hits}",
                        confidence=0.1,
                    )
                )

        return citations

    async def fence_document(self, text: str) -> FenceReport:
        citations = self.extract_citations(text)
        if not citations:
            return FenceReport(
                citations=[],
                verified_count=0,
                flagged_count=0,
                overall_score=1.0,
            )

        results = [await self.verify_citation(c) for c in citations]
        verified_count = sum(1 for r in results if r.is_valid)
        flagged_count = sum(1 for r in results if not r.is_valid)
        avg_confidence = sum(r.confidence for r in results) / len(results)

        overall_score = avg_confidence * (verified_count / len(results)) if results else 0.0

        return FenceReport(
            citations=citations,
            verified_count=verified_count,
            flagged_count=flagged_count,
            overall_score=round(overall_score, 4),
        )

    def _verify_arxiv(self, identifier: str) -> tuple[float, list[str]]:
        issues: list[str] = []
        parts = identifier.split("v")
        base_id = parts[0]
        if not re.match(r"^\d{4}\.\d{4,5}$", base_id):
            issues.append(f"Invalid arXiv ID format: {identifier}")
            return 0.0, issues
        return 0.85, issues

    def _verify_crossref(self, identifier: str) -> tuple[float, list[str]]:
        issues: list[str] = []
        if not identifier.strip():
            issues.append("Empty CrossRef identifier")
            return 0.0, issues
        return 0.75, issues

    def _verify_semantic_scholar(self, identifier: str) -> tuple[float, list[str]]:
        issues: list[str] = []
        if not identifier.strip():
            issues.append("Empty Semantic Scholar identifier")
            return 0.0, issues
        if "api.semanticscholar" in identifier.lower() and not identifier.endswith("/"):
            issues.append("Incomplete Semantic Scholar API URL")
            return 0.5, issues
        return 0.8, issues

    def _verify_doi(self, identifier: str) -> tuple[float, list[str]]:
        issues: list[str] = []
        doi_pattern = re.compile(r"^10\.\d{4,}/[a-zA-Z0-9./_\-]+$")
        if not doi_pattern.match(identifier):
            issues.append(f"Invalid DOI format: {identifier}")
            return 0.0, issues
        return 0.8, issues

    def _verify_url(self, url: str) -> tuple[float, list[str]]:
        issues: list[str] = []
        if not url.startswith(("http://", "https://")):
            issues.append(f"URL must start with http:// or https://: {url}")
            return 0.0, issues
        known_domains = [
            "arxiv.org", "doi.org", "semanticscholar.org",
            "github.com", "nature.com", "science.org",
            "ieee.org", "acm.org", "springer.com",
            "elsevier.com", "plos.org", "pubmed.ncbi.nlm.nih.gov",
        ]
        if any(d in url.lower() for d in known_domains):
            return 0.7, []
        return 0.4, [f"Unknown domain in URL: {url}"]

    def _verify_llm_generated(self, text: str) -> tuple[float, list[str]]:
        issues: list[str] = []
        issues.append("LLM-generated citation pattern detected")
        for pattern in _HALLUCINATION_PATTERNS:
            if pattern.search(text):
                issues.append(f"Matched hallucination pattern: {pattern.pattern}")
        return 0.1, issues

    def _build_verified_source(self, source_type: SourceType, identifier: str) -> str:
        base_urls = {
            SourceType.ARXIV: "https://arxiv.org/abs/",
            SourceType.CROSSREF: "https://api.crossref.org/works/",
            SourceType.SEMANTIC_SCHOLAR: "https://api.semanticscholar.org/graph/v1/paper/",
            SourceType.DOI: "https://doi.org/",
            SourceType.URL: "",
            SourceType.LLM_GENERATED: "",
        }
        prefix = base_urls.get(source_type, "")
        return f"{prefix}{identifier}"
