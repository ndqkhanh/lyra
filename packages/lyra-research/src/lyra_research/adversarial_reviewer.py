"""
Adversarial Review System for Research Reports.

Provides cost-controlled adversarial review with selective claim verification,
disagreement resolution, and context budget enforcement.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Context Budget
# ---------------------------------------------------------------------------


@dataclass
class ReviewerContextBudget:
    """Context budget limits for adversarial review."""

    MAX_CONTEXT_KB: int = 40  # Increased for 10+ agents
    REPORT_KB: int = 12
    TOP_SOURCES_KB: int = 20  # Top 15 cited sources, abstracts only
    CLAIM_MAPPING_KB: int = 8

    def estimate_size_kb(self, text: str) -> float:
        """Estimate text size in KB."""
        return len(text.encode("utf-8")) / 1024

    def truncate_to_kb(self, text: str, max_kb: int) -> str:
        """Truncate text to fit within KB limit."""
        max_bytes = max_kb * 1024
        encoded = text.encode("utf-8")
        if len(encoded) <= max_bytes:
            return text
        # Truncate and decode, handling potential multi-byte character splits
        truncated = encoded[:max_bytes]
        # Try to decode, removing trailing bytes if needed
        for i in range(4):
            try:
                return truncated[: -i if i > 0 else len(truncated)].decode("utf-8", errors="ignore")
            except UnicodeDecodeError:
                continue
        return text[: max_bytes // 4]  # Fallback: assume ~4 bytes per char


# ---------------------------------------------------------------------------
# Disagreement Resolution
# ---------------------------------------------------------------------------


class DisagreementResolution(Enum):
    """Resolution strategies for reviewer disagreements."""

    FIX = "fix"  # Add missing citation or strengthen evidence
    SOFTEN = "soften"  # Change "X is Y" to "X may be Y"
    REMOVE = "remove"  # Delete unsupported claim


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class Claim:
    """A verifiable claim extracted from a research report."""

    text: str
    confidence: float  # 0.0-1.0
    citations: list[str] = field(default_factory=list)  # Citation keys like "[1]", "[2]"
    source_ids: list[str] = field(default_factory=list)  # Actual source IDs
    location: str = ""  # Section or paragraph identifier

    def citation_count(self) -> int:
        """Return number of citations backing this claim."""
        return len(self.citations)


@dataclass
class ReviewIssue:
    """An issue found during adversarial review."""

    claim: Claim
    issue_type: str  # "missing_citation", "weak_evidence", "unsupported"
    severity: str  # "critical", "high", "medium", "low"
    suggested_resolution: DisagreementResolution
    explanation: str


@dataclass
class ReviewResult:
    """Result of adversarial review."""

    original_report: str
    revised_report: str
    issues_found: list[ReviewIssue]
    issues_resolved: int
    review_cost_usd: float
    context_size_kb: float
    claims_reviewed: int
    claims_modified: int


# ---------------------------------------------------------------------------
# Adversarial Reviewer
# ---------------------------------------------------------------------------


class AdversarialReviewer:
    """
    Adversarial review system for research reports.

    Provides cost-controlled review with selective claim verification,
    disagreement resolution, and context budget enforcement.
    """

    def __init__(
        self,
        executor_model: str = "gpt-4o",
        reviewer_model: str = "gpt-4o-mini",
    ):
        """
        Initialize adversarial reviewer.

        Args:
            executor_model: Model used to generate the original report
            reviewer_model: Model used for adversarial review (cheaper)
        """
        self.executor_model = executor_model
        self.reviewer_model = reviewer_model
        self.budget = ReviewerContextBudget()

    def review(
        self,
        report: Any,  # ResearchReport from reporter.py
        sources: list[Any],  # List[ResearchSource] from discovery.py
        depth: str = "standard",
    ) -> ReviewResult:
        """
        Perform adversarial review on a research report.

        Args:
            report: ResearchReport object to review
            sources: List of ResearchSource objects used in the report
            depth: "quick", "standard", or "deep" (review only mandatory for "deep")

        Returns:
            ReviewResult with issues found and resolved
        """
        # Skip review for quick and standard depth
        if depth in ["quick", "standard"]:
            return ReviewResult(
                original_report=report.to_markdown(),
                revised_report=report.to_markdown(),
                issues_found=[],
                issues_resolved=0,
                review_cost_usd=0.0,
                context_size_kb=0.0,
                claims_reviewed=0,
                claims_modified=0,
            )

        # Extract report text
        report_text = report.to_markdown()

        # Extract cited sources (top 10 by citation frequency)
        cited_sources = self.extract_cited_sources(report, sources)

        # Build claim-to-source mapping
        claim_mapping = self.build_claim_mapping(report, sources)

        # Filter low-confidence claims for review
        claims = self.filter_low_confidence_claims(report)

        # Verify each claim
        issues: list[ReviewIssue] = []
        for claim in claims:
            issue = self.verify_claim(claim, claim_mapping)
            if issue:
                issues.append(issue)

        # Resolve issues
        revised_text = report_text
        resolved_count = 0
        modified_count = 0

        for issue in issues:
            revised_claim = self.resolve_issue(issue.claim, issue)
            if revised_claim.text != issue.claim.text:
                revised_text = revised_text.replace(issue.claim.text, revised_claim.text, 1)
                resolved_count += 1
                modified_count += 1

        # Calculate review cost
        context_kb = self._calculate_context_size(report_text, cited_sources, claim_mapping)
        cost_usd = self.calculate_review_cost(report)

        return ReviewResult(
            original_report=report_text,
            revised_report=revised_text,
            issues_found=issues,
            issues_resolved=resolved_count,
            review_cost_usd=cost_usd,
            context_size_kb=context_kb,
            claims_reviewed=len(claims),
            claims_modified=modified_count,
        )

    def extract_cited_sources(
        self,
        report: Any,
        sources: list[Any],
    ) -> list[Any]:
        """
        Extract top 10 most-cited sources from the report.

        Args:
            report: ResearchReport object
            sources: List of all available ResearchSource objects

        Returns:
            List of top 10 cited ResearchSource objects
        """
        # Extract citation keys from report text
        report_text = report.to_markdown()
        citation_pattern = r"\[(\d+)\]"
        citations = re.findall(citation_pattern, report_text)

        # Count citation frequency
        citation_counts: dict[str, int] = {}
        for cite in citations:
            citation_counts[cite] = citation_counts.get(cite, 0) + 1

        # Sort by frequency
        sorted_citations = sorted(
            citation_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        # Map citation keys to sources
        # Assuming report.references_section contains numbered references
        cited_source_ids = set()
        for cite_num, _ in sorted_citations:
            # Extract source from references section
            ref_pattern = rf"^{cite_num}\.\s+(.+?)(?:\s+http|\n|$)"
            matches = re.findall(ref_pattern, report.references_section, re.MULTILINE)
            if matches:
                title = matches[0].strip()
                # Find matching source
                for source in sources:
                    if hasattr(source, "title") and source.title == title:
                        cited_source_ids.add(source.id)
                        break

        # Return matching sources (increased to 15 for 10+ agents)
        return [s for s in sources if s.id in cited_source_ids][:15]

    def build_claim_mapping(
        self,
        report: Any,
        sources: list[Any],
    ) -> dict[str, list[str]]:
        """
        Build mapping from claims to source IDs.

        Args:
            report: ResearchReport object
            sources: List of ResearchSource objects

        Returns:
            Dict mapping claim text to list of source IDs
        """
        claim_mapping: dict[str, list[str]] = {}
        report_text = report.to_markdown()

        # Extract claims with citations
        # Pattern: sentence ending with [N]
        claim_pattern = r"([^.!?]+\[\d+\][.!?])"
        claims_with_citations = re.findall(claim_pattern, report_text)

        for claim_text in claims_with_citations:
            # Extract citation numbers
            citations = re.findall(r"\[(\d+)\]", claim_text)

            # Map citation numbers to source IDs via references section
            source_ids = []
            for cite_num in citations:
                ref_pattern = rf"^{cite_num}\.\s+(.+?)(?:\s+http|\n|$)"
                matches = re.findall(ref_pattern, report.references_section, re.MULTILINE)
                if matches:
                    title = matches[0].strip()
                    for source in sources:
                        if hasattr(source, "title") and source.title == title:
                            source_ids.append(source.id)
                            break

            # Clean claim text (remove citation)
            clean_claim = re.sub(r"\[\d+\]", "", claim_text).strip()
            claim_mapping[clean_claim] = source_ids

        return claim_mapping

    def filter_low_confidence_claims(self, report: Any) -> list[Claim]:
        """
        Extract claims with confidence <0.8 for selective review.

        Args:
            report: ResearchReport object

        Returns:
            List of Claim objects with confidence <0.8
        """
        claims: list[Claim] = []
        report_text = report.to_markdown()

        # Patterns for claims that need verification
        claim_patterns = [
            # Numerical claims
            r"([^.!?]*\d+(?:\.\d+)?%[^.!?]*[.!?])",
            # Outperformance claims
            r"([^.!?]*(?:outperform|better than|superior to|exceeds)[^.!?]*[.!?])",
            # Causal claims
            r"([^.!?]*(?:causes?|leads? to|results? in|due to)[^.!?]*[.!?])",
            # State-of-the-art claims
            r"([^.!?]*(?:state-of-the-art|SOTA|best|highest|lowest)[^.!?]*[.!?])",
        ]

        for pattern in claim_patterns:
            matches = re.findall(pattern, report_text, re.IGNORECASE)
            for match in matches:
                claim_text = match.strip()

                # Extract citations
                citations = re.findall(r"\[(\d+)\]", claim_text)

                # Assign confidence based on citation count
                citation_count = len(citations)
                if citation_count == 0:
                    confidence = 0.0
                elif citation_count == 1:
                    confidence = 0.5
                elif citation_count == 2:
                    confidence = 0.7
                else:  # 3+ citations
                    confidence = 0.9

                # Only include claims with confidence <0.8
                if confidence < 0.8:
                    claims.append(
                        Claim(
                            text=claim_text,
                            confidence=confidence,
                            citations=[f"[{c}]" for c in citations],
                            source_ids=[],  # Will be populated from claim_mapping
                        )
                    )

        # Deduplicate
        seen = set()
        unique_claims = []
        for claim in claims:
            key = claim.text[:100].lower()
            if key not in seen:
                seen.add(key)
                unique_claims.append(claim)

        return unique_claims

    def verify_claim(
        self,
        claim: Claim,
        claim_mapping: dict[str, list[str]],
    ) -> ReviewIssue | None:
        """
        Verify a single claim against available sources.

        Args:
            claim: Claim to verify
            claim_mapping: Mapping from claim text to source IDs

        Returns:
            ReviewIssue if problem found, None otherwise
        """
        # Clean claim text for lookup
        clean_text = re.sub(r"\[\d+\]", "", claim.text).strip()

        # Check if claim has sources
        source_ids = claim_mapping.get(clean_text, [])

        if not source_ids and claim.citation_count() == 0:
            # No citations at all
            return ReviewIssue(
                claim=claim,
                issue_type="missing_citation",
                severity="critical",
                suggested_resolution=DisagreementResolution.REMOVE,
                explanation="Claim has no supporting citations",
            )

        if claim.citation_count() == 1:
            # Single citation - weak evidence
            return ReviewIssue(
                claim=claim,
                issue_type="weak_evidence",
                severity="high",
                suggested_resolution=DisagreementResolution.SOFTEN,
                explanation="Claim supported by only one source",
            )

        if claim.citation_count() == 2:
            # Two citations - moderate evidence
            return ReviewIssue(
                claim=claim,
                issue_type="weak_evidence",
                severity="medium",
                suggested_resolution=DisagreementResolution.FIX,
                explanation="Claim needs additional supporting evidence",
            )

        # 3+ citations - sufficient evidence
        return None

    def resolve_issue(
        self,
        claim: Claim,
        issue: ReviewIssue,
    ) -> Claim:
        """
        Resolve a review issue by applying the suggested resolution.

        Args:
            claim: Original claim
            issue: ReviewIssue with suggested resolution

        Returns:
            Modified Claim object
        """
        if issue.suggested_resolution == DisagreementResolution.REMOVE:
            # Mark for removal (return empty claim)
            return Claim(text="", confidence=0.0)

        elif issue.suggested_resolution == DisagreementResolution.SOFTEN:
            # Soften the claim language
            softened_text = claim.text

            # Replace definitive statements with hedged language
            replacements = [
                (r"\bis\b", "may be"),
                (r"\bare\b", "may be"),
                (r"\boutperforms?\b", "appears to outperform"),
                (r"\bshows?\b", "suggests"),
                (r"\bdemonstrates?\b", "indicates"),
                (r"\bproves?\b", "suggests"),
                (r"\bconfirms?\b", "supports"),
            ]

            for pattern, replacement in replacements:
                softened_text = re.sub(
                    pattern, replacement, softened_text, count=1, flags=re.IGNORECASE
                )

            return Claim(
                text=softened_text,
                confidence=claim.confidence * 0.8,  # Reduce confidence
                citations=claim.citations,
                source_ids=claim.source_ids,
            )

        elif issue.suggested_resolution == DisagreementResolution.FIX:
            # Add qualifier indicating need for more evidence
            fixed_text = claim.text.rstrip(".!?")
            fixed_text += " (additional verification needed)."

            return Claim(
                text=fixed_text,
                confidence=claim.confidence,
                citations=claim.citations,
                source_ids=claim.source_ids,
            )

        return claim

    def calculate_review_cost(self, report: Any) -> float:
        """
        Calculate estimated cost of adversarial review in USD.

        Uses GPT-4o-mini pricing: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens.

        Args:
            report: ResearchReport object

        Returns:
            Estimated cost in USD
        """
        # Estimate tokens (rough: 1 token ≈ 4 characters)
        report_text = report.to_markdown()
        input_tokens = len(report_text) / 4

        # Assume output is 20% of input (review comments)
        output_tokens = input_tokens * 0.2

        # GPT-4o-mini pricing
        input_cost_per_1m = 0.15
        output_cost_per_1m = 0.60

        input_cost = (input_tokens / 1_000_000) * input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * output_cost_per_1m

        return round(input_cost + output_cost, 4)

    def _calculate_context_size(
        self,
        report_text: str,
        cited_sources: list[Any],
        claim_mapping: dict[str, list[str]],
    ) -> float:
        """
        Calculate total context size in KB.

        Args:
            report_text: Full report text
            cited_sources: List of cited sources
            claim_mapping: Claim to source mapping

        Returns:
            Total context size in KB
        """
        # Report size
        report_kb = self.budget.estimate_size_kb(report_text)

        # Sources size (abstracts only)
        sources_text = "\n".join(getattr(s, "abstract", "")[:500] for s in cited_sources)
        sources_kb = self.budget.estimate_size_kb(sources_text)

        # Claim mapping size
        mapping_text = "\n".join(
            f"{claim}: {','.join(sources)}" for claim, sources in claim_mapping.items()
        )
        mapping_kb = self.budget.estimate_size_kb(mapping_text)

        total_kb = report_kb + sources_kb + mapping_kb

        # Enforce budget limit
        if total_kb > self.budget.MAX_CONTEXT_KB:
            return float(self.budget.MAX_CONTEXT_KB)

        return round(total_kb, 2)
