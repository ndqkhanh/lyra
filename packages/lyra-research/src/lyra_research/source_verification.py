"""
Source Verification & Citation.

TRACE-style citation audit: credibility scoring, faithfulness checks,
claim extraction, and full document auditing.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceRecord:
    """Metadata and credibility information for a single source.

    Attributes:
        url: Source URL.
        title: Document or page title.
        author: Named author(s) if available.
        date: Publication / retrieval date.
        credibility_score: Composite 0.0-1.0 credibility estimate.
        content_hash: SHA-256 of the source content.
    """

    url: str
    title: str = ""
    author: str = ""
    date: str | None = None
    credibility_score: float = 0.5
    content_hash: str = ""

    @staticmethod
    def compute_hash(content: str) -> str:
        """Return a SHA-256 hex digest of *content*."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CitationCheck:
    """Result of verifying a single citation against its source.

    Attributes:
        claim_text: The claim being made.
        source_url: Cited source.
        is_supported: Whether the source content substantiates the claim.
        confidence: Confidence in the verification (0.0-1.0).
        explanation: Human-readable explanation.
    """

    claim_text: str
    source_url: str
    is_supported: bool
    confidence: float = 1.0
    explanation: str = ""


@dataclass(frozen=True)
class AuditReport:
    """Aggregated result of auditing a full document.

    Attributes:
        total_claims: Number of factual claims identified.
        verified_count: Claims that could be verified against sources.
        unsupported_count: Claims where no supporting source was found.
        faithfulness_score: 0.0-1.0 measure of citation faithfulness.
        details: Per-citation results.
    """

    total_claims: int = 0
    verified_count: int = 0
    unsupported_count: int = 0
    faithfulness_score: float = 1.0
    details: tuple[CitationCheck, ...] = ()

    @property
    def verification_rate(self) -> float:
        """Fraction of claims that were verified."""
        if self.total_claims == 0:
            return 1.0
        return self.verified_count / self.total_claims


# ---------------------------------------------------------------------------
# SourceVerifier
# ---------------------------------------------------------------------------


class SourceVerifier:
    """Verifies that citations faithfully represent their sources.

    Inspired by TRACE citation audit methodology: extract claims, check
    each against its cited source, and score overall faithfulness.
    """

    # Common claim indicator words / patterns
    _CLAIM_PATTERNS = [
        r"(?:studies? shows?|research (?:finds|demonstrates|indicates)|according to)",
        r"(?:it has been (?:shown|demonstrated|proven|established))",
        r"(?:evidence suggests|results (?:show|indicate|confirm|support))",
        r"(?:[A-Z][a-z]+ et al\.\s*\(?\d{4}\)?)",  # Author-year citations
    ]

    def __init__(self) -> None:
        """Initialize source verifier."""
        self._sources: dict[str, SourceRecord] = {}

    # -- claim extraction ----------------------------------------------------

    def extract_claims(self, text: str) -> list[str]:
        """Identify factual claims in *text* using pattern heuristics.

        This is a lightweight extractor suitable for research documents.
        For higher accuracy, integrate with a claim-detection model.

        Args:
            text: Document body text.

        Returns:
            List of candidate claim strings.
        """
        claims: list[str] = []
        sentences = _split_sentences(text)

        for sentence in sentences:
            s = sentence.strip()
            if len(s) < 20:
                continue
            for pattern in self._CLAIM_PATTERNS:
                if re.search(pattern, s, re.IGNORECASE):
                    claims.append(s)
                    break
            # Also capture sentences with numeric data as claims
            if re.search(r"\b\d+(?:\.\d+)?%", s):
                if s not in claims:
                    claims.append(s)

        logger.debug("Extracted %d claims from %d sentences", len(claims), len(sentences))
        return claims

    # -- citation verification -----------------------------------------------

    def verify_citation(
        self,
        claim: str,
        source: SourceRecord,
        source_content: str = "",
    ) -> CitationCheck:
        """Check whether *source_content* (or source metadata) supports *claim*.

        The current implementation uses keyword-overlap heuristics.  For
        production use, replace with a dedicated NLI or entailment model.

        Args:
            claim: The factual claim to verify.
            source: Metadata for the cited source.
            source_content: Full text of the source (empty = use title only).

        Returns:
            A ``CitationCheck`` with the result.
        """
        content_lowered = source_content.lower() if source_content else source.title.lower()
        claim_lowered = claim.lower()

        # Extract keywords from claim (nouns, named entities)
        keywords = _extract_keywords(claim)
        if not keywords:
            return CitationCheck(
                claim_text=claim,
                source_url=source.url,
                is_supported=False,
                confidence=0.3,
                explanation="No extractable keywords in the claim.",
            )

        # Count keyword overlap
        matched = sum(1 for kw in keywords if kw.lower() in content_lowered)
        overlap = matched / len(keywords) if keywords else 0.0

        is_supported = overlap >= 0.3
        confidence = min(overlap * source.credibility_score, 1.0)

        explanation = (
            f"{matched}/{len(keywords)} keywords matched in source. "
            f"Source credibility: {source.credibility_score:.2f}."
        )

        logger.debug(
            "Citation check: %s keywords, %d matched, supported=%s",
            len(keywords),
            matched,
            is_supported,
        )
        return CitationCheck(
            claim_text=claim,
            source_url=source.url,
            is_supported=is_supported,
            confidence=confidence,
            explanation=explanation,
        )

    def check_faithfulness(
        self,
        citation_text: str,
        source_content: str,
    ) -> float:
        """Estimate how faithfully *citation_text* represents *source_content*.

        Args:
            citation_text: How the source is described/referenced.
            source_content: The actual source text.

        Returns:
            Faithfulness score between 0.0 and 1.0.
        """
        if not source_content or not citation_text:
            return 0.0

        src_lower = source_content.lower()
        cit_lower = citation_text.lower()

        # Simple lexical overlap ratio with a brevity penalty
        cit_words = set(cit_lower.split())
        if not cit_words:
            return 0.0

        matched = sum(1 for w in cit_words if w in src_lower)
        overlap = matched / len(cit_words)

        logger.debug("Faithfulness overlap: %.2f (%d/%d words)", overlap, matched, len(cit_words))
        return round(overlap, 4)

    # -- credibility ---------------------------------------------------------

    def compute_credibility(
        self,
        url: str = "",
        author: str = "",
        date: str | None = None,
    ) -> float:
        """Compute a composite credibility score for a source.

        Considers:
        - Authority: known reputable domains or recognized authors.
        - Recency: preference for recent sources.
        - Consensus: placeholder — in production, would compare against
          multiple independent sources.

        Args:
            url: Source URL.
            author: Named author(s).
            date: Publication date string.

        Returns:
            Credibility score between 0.0 and 1.0.
        """
        score = 0.5  # neutral baseline

        # Authority boost for reputable domains
        authority_domains = [
            "arxiv.org", "scholar.google.com", "semanticscholar.org",
            "openreview.net", "aclanthology.org", "ieee.org", "acm.org",
            "nature.com", "science.org", "pnas.org", "paperswithcode.com",
            "github.com",
        ]
        for domain in authority_domains:
            if domain in url:
                score += 0.2
                break

        # Recency boost
        if date:
            try:
                parsed = _parse_date(date)
                if parsed:
                    age_days = (datetime.now(timezone.utc) - parsed).days
                    if age_days < 365:
                        score += 0.15
                    elif age_days < 730:
                        score += 0.1
                    elif age_days < 1825:
                        score += 0.05
            except (ValueError, TypeError):
                pass

        # Author boost
        if author and len(author.split(",")) >= 2:
            score += 0.05

        return min(round(score, 4), 1.0)

    # -- document audit ------------------------------------------------------

    def audit_document(
        self,
        text: str,
        citations: dict[str, str] | None = None,
    ) -> AuditReport:
        """Run a full citation audit on a research document.

        Args:
            text: The document body.
            citations: Optional mapping of claim text -> source content.

        Returns:
            ``AuditReport`` summarizing the audit.
        """
        claims = self.extract_claims(text)
        if not claims:
            return AuditReport()

        details: list[CitationCheck] = []
        verified = 0
        unsupported = 0

        for i, claim in enumerate(claims):
            if citations and claim in citations:
                source_content = citations[claim]
                source = SourceRecord(
                    url=f"inline-source-{i}",
                    title=source_content[:100],
                    content_hash=SourceRecord.compute_hash(source_content),
                )
                check = self.verify_citation(claim, source, source_content)
            else:
                # No citation provided — mark as unsupported
                check = CitationCheck(
                    claim_text=claim,
                    source_url="unknown",
                    is_supported=False,
                    confidence=0.0,
                    explanation="No citation source available for this claim.",
                )

            if check.is_supported:
                verified += 1
            else:
                unsupported += 1

            details.append(check)

        faithfulness = verified / len(claims) if claims else 1.0

        logger.info(
            "Document audit: %d claims, %d verified, %d unsupported, faithfulness=%.2f",
            len(claims),
            verified,
            unsupported,
            faithfulness,
        )
        return AuditReport(
            total_claims=len(claims),
            verified_count=verified,
            unsupported_count=unsupported,
            faithfulness_score=round(faithfulness, 4),
            details=tuple(details),
        )

    # -- source registry -----------------------------------------------------

    def register_source(self, source: SourceRecord) -> None:
        """Add a source to the internal registry for later lookup."""
        self._sources[source.url] = source

    def get_source(self, url: str) -> SourceRecord | None:
        """Retrieve a previously registered source."""
        return self._sources.get(url)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_sentences(text: str) -> list[str]:
    """Naive sentence splitter."""
    return re.split(r"(?<=[.!?])\s+", text)


def _extract_keywords(text: str) -> list[str]:
    """Extract candidate keywords from text (nouns, named entities)."""
    # Heuristic: words with 4+ chars, ignoring common stop words
    stop = {
        "this", "that", "with", "from", "they", "have", "been", "were",
        "which", "their", "about", "would", "could", "should", "there",
        "these", "those", "being", "also", "than", "into", "over",
    }
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text)
    return [w for w in words if w.lower() not in stop]


def _parse_date(date_str: str) -> datetime | None:
    """Try to parse a date string into a timezone-aware datetime."""
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None
