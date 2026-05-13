"""
Research Intelligence Core.

Provides verifiable checklists, evidence auditing, contradiction detection,
gap analysis, and falsification checking for deep research workflows.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import re


# ---------------------------------------------------------------------------
# VerifiableChecklistGenerator
# ---------------------------------------------------------------------------

@dataclass
class ChecklistItem:
    """A single verifiable sub-question in a research checklist."""
    question: str
    category: str   # "definition", "sota", "comparison", "gap", "application"
    priority: int   # 1=critical, 2=important, 3=nice-to-have
    answered: bool = False
    answer_source_ids: List[str] = field(default_factory=list)


@dataclass
class ResearchChecklist:
    """A verifiable research checklist for a topic."""
    topic: str
    items: List[ChecklistItem]
    created_at: datetime = field(default_factory=datetime.now)

    def completion_rate(self) -> float:
        """Return fraction of answered items."""
        if not self.items:
            return 0.0
        answered = sum(1 for item in self.items if item.answered)
        return answered / len(self.items)


class VerifiableChecklistGenerator:
    """Generates a verifiable research checklist for a topic.

    Does NOT call an LLM — uses rule-based templates to generate
    structured sub-questions for any research topic.
    """

    UNIVERSAL_TEMPLATES = [
        ("What is {topic} and what problem does it solve?", "definition", 1),
        ("What are the current state-of-the-art methods for {topic}?", "sota", 1),
        ("What are the main approaches/architectures used in {topic}?", "comparison", 1),
        ("What benchmarks/datasets are used to evaluate {topic}?", "comparison", 2),
        ("What are the key papers in {topic} published in the last 2 years?", "sota", 1),
        ("What open-source implementations exist for {topic}?", "application", 2),
        ("What are the known limitations and failure modes of {topic}?", "gap", 1),
        ("What is missing or under-explored in {topic} research?", "gap", 2),
        ("How does {topic} compare to alternatives?", "comparison", 2),
        ("What are the real-world applications of {topic}?", "application", 3),
    ]

    # Extra templates for "deep" depth
    DEEP_TEMPLATES = [
        ("What theoretical foundations underlie {topic}?", "definition", 2),
        ("What are the computational complexity requirements of {topic}?", "comparison", 2),
        ("What are the privacy or safety considerations for {topic}?", "gap", 2),
        ("Who are the leading research groups working on {topic}?", "sota", 3),
        ("What industry adoption exists for {topic}?", "application", 3),
    ]

    def generate(self, topic: str, depth: str = "standard") -> ResearchChecklist:
        """Generate checklist.

        Args:
            topic: Research topic string
            depth: "quick" (5 items), "standard" (10 items), "deep" (15 items)

        Returns:
            ResearchChecklist populated with ChecklistItems
        """
        templates = list(self.UNIVERSAL_TEMPLATES)

        if depth == "deep":
            templates = templates + list(self.DEEP_TEMPLATES)

        # Determine slice size
        limits = {"quick": 5, "standard": 10, "deep": 15}
        limit = limits.get(depth, 10)
        templates = templates[:limit]

        items = [
            ChecklistItem(
                question=question.format(topic=topic),
                category=category,
                priority=priority,
            )
            for question, category, priority in templates
        ]

        return ResearchChecklist(topic=topic, items=items)

    def mark_answered(
        self,
        checklist: ResearchChecklist,
        item_idx: int,
        source_ids: List[str],
    ) -> ResearchChecklist:
        """Mark a checklist item as answered with source evidence.

        Args:
            checklist: The checklist to update
            item_idx: Index of the item to mark
            source_ids: Source IDs that provide the answer

        Returns:
            New ResearchChecklist with the item marked answered
        """
        new_items = []
        for i, item in enumerate(checklist.items):
            if i == item_idx:
                new_items.append(ChecklistItem(
                    question=item.question,
                    category=item.category,
                    priority=item.priority,
                    answered=True,
                    answer_source_ids=list(source_ids),
                ))
            else:
                new_items.append(item)

        return ResearchChecklist(
            topic=checklist.topic,
            items=new_items,
            created_at=checklist.created_at,
        )

    def unanswered_questions(self, checklist: ResearchChecklist) -> List[ChecklistItem]:
        """Return items not yet answered."""
        return [item for item in checklist.items if not item.answered]


# ---------------------------------------------------------------------------
# EvidenceAudit
# ---------------------------------------------------------------------------

@dataclass
class ClaimEvidence:
    """A claim extracted from a research text with its evidence status."""
    claim: str
    source_ids: List[str]
    verified: bool
    confidence: float  # 0.0-1.0


@dataclass
class AuditReport:
    """Result of an evidence audit."""
    total_claims: int
    verified_claims: int
    unverified_claims: int
    verification_rate: float  # verified / total
    flagged_claims: List[ClaimEvidence]  # unverified ones

    def is_acceptable(self, threshold: float = 0.95) -> bool:
        """Return True if verification_rate meets the threshold."""
        return self.verification_rate >= threshold


class EvidenceAudit:
    """Maps claims to sources, flags unverified claims.

    Works on a report/synthesis text + a list of source IDs.
    Does NOT call LLMs — uses pattern matching to extract claims.
    """

    CLAIM_PATTERNS = [
        r"(?:achieves?|reports?|shows?|demonstrates?|outperforms?)\s+.+?(?=\.|;|\n)",
        r"(?:state-of-the-art|best|highest|lowest|fastest)\s+.+?(?=\.|;|\n)",
        r"\d+(?:\.\d+)?%\s+(?:accuracy|improvement|reduction|gain).+?(?=\.|;|\n)",
        r"(?:according to|as shown in|as reported by)\s+.+?(?=\.|;|\n)",
    ]

    def audit(self, text: str, available_source_ids: List[str]) -> AuditReport:
        """Extract claims from text, check each has a source citation.

        Args:
            text: Synthesis or report text to audit
            available_source_ids: List of valid source IDs

        Returns:
            AuditReport with verification statistics
        """
        claims = self.extract_claims(text)
        flagged: List[ClaimEvidence] = []
        verified_count = 0

        for claim in claims:
            cited = self.has_citation(claim, text, available_source_ids)
            evidence = ClaimEvidence(
                claim=claim,
                source_ids=available_source_ids if cited else [],
                verified=cited,
                confidence=0.9 if cited else 0.0,
            )
            if cited:
                verified_count += 1
            else:
                flagged.append(evidence)

        total = len(claims)
        rate = verified_count / total if total > 0 else 1.0

        return AuditReport(
            total_claims=total,
            verified_claims=verified_count,
            unverified_claims=total - verified_count,
            verification_rate=rate,
            flagged_claims=flagged,
        )

    def extract_claims(self, text: str) -> List[str]:
        """Extract claim sentences from text."""
        claims = []
        for pattern in self.CLAIM_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            claims.extend(m.strip() for m in matches if m.strip())
        # Deduplicate while preserving order
        seen: set = set()
        unique = []
        for c in claims:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        return unique

    def has_citation(self, claim: str, context: str, source_ids: List[str]) -> bool:
        """Check if a claim has a nearby citation in the context.

        Searches within 200 characters before and after the claim in context.

        Args:
            claim: The claim text
            context: Full document text
            source_ids: Known source IDs to look for

        Returns:
            True if a source_id appears nearby
        """
        idx = context.find(claim)
        if idx == -1:
            return False

        window_start = max(0, idx - 200)
        window_end = min(len(context), idx + len(claim) + 200)
        window = context[window_start:window_end]

        for sid in source_ids:
            if sid in window:
                return True

        return False


# ---------------------------------------------------------------------------
# ContradictionDetector
# ---------------------------------------------------------------------------

@dataclass
class Contradiction:
    """A detected contradiction between two research sources."""
    claim_a: str
    claim_b: str
    source_a_id: str
    source_b_id: str
    severity: str       # "direct", "partial", "methodological"
    description: str


class ContradictionDetector:
    """Finds contradicting claims across multiple research sources.

    Pattern-based detection — looks for explicit contradiction markers
    and opposing numerical claims.
    """

    # Regex for extracting numerical performance claims
    _NUM_CLAIM_PATTERN = re.compile(
        r"((?:accuracy|improvement|reduction|gain|error|score)\s+of\s+(\d+(?:\.\d+)?)%?)",
        re.IGNORECASE,
    )

    # Regex for outperformance claims: "X outperforms Y"
    _OUTPERFORMS_PATTERN = re.compile(
        r"(\w[\w\s\-]{0,30})\s+outperforms?\s+([\w][\w\s\-]{0,30})",
        re.IGNORECASE,
    )

    def detect(self, analyses: List[Dict[str, Any]]) -> List[Contradiction]:
        """Detect contradictions across a list of source analysis dicts.

        Args:
            analyses: List of dicts with keys: source_id, abstract, findings

        Returns:
            List of detected Contradiction objects
        """
        contradictions: List[Contradiction] = []

        # Check each pair of sources
        for i in range(len(analyses)):
            for j in range(i + 1, len(analyses)):
                a = analyses[i]
                b = analyses[j]
                text_a = f"{a.get('abstract', '')} {' '.join(a.get('findings', []))}"
                text_b = f"{b.get('abstract', '')} {' '.join(b.get('findings', []))}"

                pair_contradictions = self._compare_pair(
                    text_a, text_b, a.get('source_id', ''), b.get('source_id', '')
                )
                contradictions.extend(pair_contradictions)

        numerical = self.detect_numerical_conflicts(analyses)
        contradictions.extend(numerical)

        return contradictions

    def _compare_pair(
        self,
        text_a: str,
        text_b: str,
        sid_a: str,
        sid_b: str,
    ) -> List[Contradiction]:
        """Compare two source texts for mutual outperformance claims."""
        found: List[Contradiction] = []

        matches_a = self._OUTPERFORMS_PATTERN.findall(text_a)
        matches_b = self._OUTPERFORMS_PATTERN.findall(text_b)

        for subj_a, obj_a in matches_a:
            subj_a_clean = subj_a.strip().lower()
            obj_a_clean = obj_a.strip().lower()
            for subj_b, obj_b in matches_b:
                subj_b_clean = subj_b.strip().lower()
                obj_b_clean = obj_b.strip().lower()
                # Contradiction: A says X outperforms Y, B says Y outperforms X
                if (
                    subj_a_clean in obj_b_clean or obj_b_clean in subj_a_clean
                ) and (
                    obj_a_clean in subj_b_clean or subj_b_clean in obj_a_clean
                ):
                    found.append(Contradiction(
                        claim_a=f"{subj_a} outperforms {obj_a}",
                        claim_b=f"{subj_b} outperforms {obj_b}",
                        source_a_id=sid_a,
                        source_b_id=sid_b,
                        severity="direct",
                        description=(
                            f"Source {sid_a} claims '{subj_a} outperforms {obj_a}' "
                            f"while source {sid_b} claims the opposite."
                        ),
                    ))

        return found

    def detect_numerical_conflicts(self, analyses: List[Dict]) -> List[Contradiction]:
        """Find sources reporting conflicting numbers for same metric.

        Args:
            analyses: List of dicts with source_id, abstract, findings

        Returns:
            List of numerical Contradiction objects
        """
        # Collect (metric_keyword, value) per source
        metric_values: Dict[str, List[tuple]] = {}

        for analysis in analyses:
            sid = analysis.get('source_id', '')
            text = f"{analysis.get('abstract', '')} {' '.join(analysis.get('findings', []))}"
            for match in self._NUM_CLAIM_PATTERN.finditer(text):
                claim_text = match.group(1)
                value = float(match.group(2))
                metric_key = claim_text.split()[0].lower()  # e.g. "accuracy"
                metric_values.setdefault(metric_key, []).append((sid, value, claim_text))

        contradictions: List[Contradiction] = []
        for metric, entries in metric_values.items():
            if len(entries) < 2:
                continue
            # Check for significant spread (>10 percentage points)
            values = [v for _, v, _ in entries]
            if max(values) - min(values) > 10:
                for i in range(len(entries)):
                    for j in range(i + 1, len(entries)):
                        sid_a, val_a, claim_a = entries[i]
                        sid_b, val_b, claim_b = entries[j]
                        if abs(val_a - val_b) > 10:
                            contradictions.append(Contradiction(
                                claim_a=claim_a,
                                claim_b=claim_b,
                                source_a_id=sid_a,
                                source_b_id=sid_b,
                                severity="methodological",
                                description=(
                                    f"Conflicting {metric} values: "
                                    f"{val_a} (source {sid_a}) vs {val_b} (source {sid_b})"
                                ),
                            ))

        return contradictions


# ---------------------------------------------------------------------------
# GapAnalyzer
# ---------------------------------------------------------------------------

@dataclass
class ResearchGap:
    """An identified gap in the research literature."""
    area: str
    evidence: str
    severity: str           # "critical", "important", "minor"
    suggested_direction: str


class GapAnalyzer:
    """Identifies research gaps from a set of analyzed sources.

    Rule-based: looks for explicit gap mentions and infers gaps
    from coverage distribution.
    """

    GAP_SIGNALS = [
        r"(?:future work|open problem|remains? challenging|not yet explored)",
        r"(?:lacks?|missing|absence of|no existing|limited work on)",
        r"(?:we leave|beyond the scope|important direction|open question)",
        r"(?:to the best of our knowledge, no|first to|novel in that)",
    ]

    def analyze(self, sources: List[Dict[str, Any]], topic: str) -> List[ResearchGap]:
        """Identify gaps from source abstracts/findings.

        Args:
            sources: List of dicts with source_id, title, abstract, findings
            topic: The research topic

        Returns:
            Deduplicated list of ResearchGap objects
        """
        gaps: List[ResearchGap] = []

        for source in sources:
            text = f"{source.get('abstract', '')} {' '.join(source.get('findings', []))}"
            source_gaps = self._extract_gap_sentences(text, source.get('source_id', ''))
            gaps.extend(source_gaps)

        # Deduplicate by area
        seen_areas: set = set()
        unique_gaps: List[ResearchGap] = []
        for gap in gaps:
            area_key = gap.area[:60].lower()
            if area_key not in seen_areas:
                seen_areas.add(area_key)
                unique_gaps.append(gap)

        return unique_gaps

    def _extract_gap_sentences(self, text: str, source_id: str) -> List[ResearchGap]:
        """Extract sentences containing gap signals."""
        gaps: List[ResearchGap] = []

        # Split into sentences (rough)
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            for pattern in self.GAP_SIGNALS:
                if re.search(pattern, sentence, re.IGNORECASE):
                    area = sentence.strip()[:120]
                    gaps.append(ResearchGap(
                        area=area,
                        evidence=f"Source {source_id}: {sentence.strip()[:200]}",
                        severity="important",
                        suggested_direction=f"Further research needed on: {area[:80]}",
                    ))
                    break  # One gap per sentence

        return gaps

    def coverage_gaps(
        self,
        sources: List[Dict],
        checklist: ResearchChecklist,
    ) -> List[ResearchGap]:
        """Find checklist questions with no source coverage.

        Args:
            sources: List of source dicts (with abstract/findings)
            checklist: ResearchChecklist to check coverage against

        Returns:
            ResearchGap list for uncovered checklist questions
        """
        # Build combined corpus
        corpus = " ".join(
            f"{s.get('abstract', '')} {' '.join(s.get('findings', []))}"
            for s in sources
        ).lower()

        gaps: List[ResearchGap] = []
        for item in checklist.items:
            if item.answered:
                continue
            # Check if key words from the question appear in the corpus
            keywords = [
                w for w in item.question.lower().split()
                if len(w) > 4 and w not in {"what", "which", "where", "when", "that", "with"}
            ]
            coverage = sum(1 for kw in keywords if kw in corpus)
            coverage_rate = coverage / len(keywords) if keywords else 1.0

            if coverage_rate < 0.3:
                severity = "critical" if item.priority == 1 else "important" if item.priority == 2 else "minor"
                gaps.append(ResearchGap(
                    area=item.question,
                    evidence=f"No sources adequately cover: {item.question}",
                    severity=severity,
                    suggested_direction=f"Search specifically for: {item.question}",
                ))

        return gaps


# ---------------------------------------------------------------------------
# FalsificationChecker
# ---------------------------------------------------------------------------

@dataclass
class FalsificationNote:
    """Result of checking a claim against counter-evidence."""
    claim: str
    counter_sources: List[str]
    counter_evidence: str
    verdict: str  # "supported", "contested", "refuted", "insufficient_evidence"


class FalsificationChecker:
    """Finds counter-evidence for major claims (Baby-AIGS inspired).

    For each major claim in the analysis, searches the source corpus
    for counter-evidence using keyword matching.
    """

    REFUTATION_SIGNALS = [
        r"(?:contradicts?|refutes?|disproves?|challenges?)\s+.+?(?=\.|;)",
        r"(?:fails? to|unable to|does not)\s+.+?(?=\.|;)",
        r"(?:inferior to|worse than|underperforms?)\s+.+?(?=\.|;)",
        r"(?:we argue against|we question|we challenge)\s+.+?(?=\.|;)",
    ]

    def check(
        self,
        claims: List[str],
        sources: List[Dict[str, Any]],
    ) -> List[FalsificationNote]:
        """For each claim, search sources for counter-evidence.

        Args:
            claims: List of claim strings to check
            sources: List of dicts with source_id, abstract, findings

        Returns:
            List of FalsificationNote with verdicts
        """
        notes: List[FalsificationNote] = []

        for claim in claims:
            claim_keywords = self._extract_keywords(claim)
            counter_sources: List[str] = []
            counter_snippets: List[str] = []

            for source in sources:
                sid = source.get('source_id', '')
                text = f"{source.get('abstract', '')} {' '.join(source.get('findings', []))}"
                refutations = self._find_refutations(text, claim_keywords)
                if refutations:
                    counter_sources.append(sid)
                    counter_snippets.extend(refutations[:1])

            if not sources:
                verdict = "insufficient_evidence"
            elif not counter_sources:
                verdict = "supported"
            elif len(counter_sources) >= len(sources) // 2:
                verdict = "refuted"
            else:
                verdict = "contested"

            notes.append(FalsificationNote(
                claim=claim,
                counter_sources=counter_sources,
                counter_evidence="; ".join(counter_snippets) if counter_snippets else "",
                verdict=verdict,
            ))

        return notes

    def check_consensus(
        self,
        claims: List[str],
        sources: List[Dict],
    ) -> Dict[str, str]:
        """Return consensus verdict for each claim.

        Args:
            claims: Claims to evaluate
            sources: Source corpus

        Returns:
            Dict mapping claim -> "consensus" | "contested" | "minority_view"
        """
        notes = self.check(claims, sources)
        consensus: Dict[str, str] = {}

        for note in notes:
            if note.verdict == "supported":
                consensus[note.claim] = "consensus"
            elif note.verdict == "refuted":
                consensus[note.claim] = "minority_view"
            else:
                consensus[note.claim] = "contested"

        return consensus

    def _extract_keywords(self, claim: str) -> List[str]:
        """Extract significant keywords from a claim."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "has", "have", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "that", "this", "these",
            "those", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as",
        }
        words = re.findall(r'\b[a-zA-Z]{4,}\b', claim.lower())
        return [w for w in words if w not in stop_words]

    def _find_refutations(self, text: str, keywords: List[str]) -> List[str]:
        """Find refutation snippets in text that mention claim keywords."""
        if not keywords:
            return []

        refutations: List[str] = []
        for pattern in self.REFUTATION_SIGNALS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                match_lower = match.lower()
                if any(kw in match_lower for kw in keywords):
                    refutations.append(match.strip())

        return refutations
