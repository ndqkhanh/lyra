"""ClaimAuditor — extracts claims from output and verifies against sources."""

import re
from time import time

from .models import (
    AuditReport,
    Claim,
    SourceMapping,
)


class ClaimAuditor:
    """Extracts claims from text and verifies faithfulness against sources.

    Three-stage pipeline:
    1. Extract — identify verifiable claims in output text
    2. Map — link each claim to its source evidence
    3. Score — compute overall faithfulness score
    """

    _CLAIM_PATTERNS = [
        r"(?:according to|based on|as stated in|research shows|studies indicate)\s+.+?\.",
        r"(?:the (?:result|finding|conclusion) (?:is|was|shows))\s+.+?\.",
        r"(?:\d+%?\s+(?:of|increase|decrease|reduction|improvement))\s+.+?\.",
        r"(?:(?:significantly|substantially|notably)\s+.+?\.)",
    ]

    def __init__(self, min_claim_length: int = 20, faithfulness_threshold: float = 0.7):
        self._claims: dict[str, Claim] = {}
        self._mappings: dict[str, SourceMapping] = {}
        self._min_claim_length = min_claim_length
        self._faithfulness_threshold = faithfulness_threshold

    def extract_claims(self, text: str) -> list[Claim]:
        """Extract verifiable claims from output text."""
        import uuid

        found: list[Claim] = []
        for pattern in self._CLAIM_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                claim_text = match.group().strip()
                if len(claim_text) >= self._min_claim_length:
                    claim = Claim(
                        id=str(uuid.uuid4()),
                        text=claim_text,
                        category=self._categorize(claim_text),
                    )
                    self._claims[claim.id] = claim
                    found.append(claim)
        return found

    @staticmethod
    def _categorize(text: str) -> str:
        lower = text.lower()
        if any(w in lower for w in ["%", "percent", "increase", "decrease", "reduction"]):
            return "quantitative"
        if any(w in lower for w in ["according", "stated", "reported"]):
            return "attribution"
        if any(w in lower for w in ["shows", "indicates", "suggests", "proves"]):
            return "inferential"
        return "general"

    def map_to_source(
        self, claim_id: str, source_uri: str, source_text: str
    ) -> SourceMapping | None:
        """Map a claim to its verifiable source and compute match score."""
        claim = self._claims.get(claim_id)
        if claim is None:
            return None

        match_score = self._compute_match(claim.text, source_text)
        mapping = SourceMapping(
            claim_id=claim_id,
            source_uri=source_uri,
            source_text=source_text,
            match_score=match_score,
            verified=match_score >= self._faithfulness_threshold,
            verified_at=time() if match_score >= self._faithfulness_threshold else None,
        )
        self._mappings[claim_id] = mapping
        return mapping

    @staticmethod
    def _compute_match(claim_text: str, source_text: str) -> float:
        """Compute overlap-based match score between claim and source."""
        import re

        def _words(text: str) -> set[str]:
            return set(re.findall(r"\w+", text.lower()))

        claim_words = _words(claim_text)
        source_words = _words(source_text)
        if not claim_words:
            return 0.0
        overlap = len(claim_words & source_words)
        return min(overlap / len(claim_words), 1.0)

    def audit(self, text: str, sources: dict[str, str] | None = None) -> AuditReport:
        """Run full audit: extract claims and map to sources."""
        claims = self.extract_claims(text)
        mappings: list[SourceMapping] = []

        if sources:
            for claim in claims:
                best_uri = None
                best_score = 0.0
                best_text = ""
                for uri, src_text in sources.items():
                    score = self._compute_match(claim.text, src_text)
                    if score > best_score:
                        best_score = score
                        best_uri = uri
                        best_text = src_text
                if best_uri:
                    mapping = self.map_to_source(claim.id, best_uri, best_text)
                    if mapping:
                        mappings.append(mapping)

        verified = sum(1 for m in mappings if m.verified)
        unverified = len(mappings) - verified + len(claims) - len(mappings)
        faithfulness = verified / max(len(claims), 1)

        return AuditReport(
            claims=tuple(claims),
            mappings=tuple(mappings),
            faithfulness_score=round(faithfulness, 4),
            unverified_claims=unverified,
            verified_claims=verified,
        )

    @property
    def claim_count(self) -> int:
        return len(self._claims)

    @property
    def mapping_count(self) -> int:
        return len(self._mappings)
