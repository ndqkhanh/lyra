"""
Research Synthesis & Report Engine.

Provides cross-source synthesis, citation binding, report generation,
and quality checking for deep research workflows.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
import re


# ---------------------------------------------------------------------------
# CrossSourceSynthesizer
# ---------------------------------------------------------------------------

@dataclass
class FieldTaxonomy:
    """Structured taxonomy of a research field."""
    topic: str
    categories: List[str]                      # Main sub-areas
    subcategories: Dict[str, List[str]]        # {category: [sub-area, ...]}
    key_methods: List[str]
    key_datasets: List[str]
    key_metrics: List[str]


@dataclass
class SynthesisResult:
    """Result of cross-source synthesis."""
    topic: str
    taxonomy: FieldTaxonomy
    best_papers: Dict[str, List[str]]          # {category: [paper_titles]}
    best_repos: Dict[str, List[str]]           # {use_case: [repo_names]}
    relationships: List[str]                   # ["Paper A extends Paper B", ...]
    contradictions: List[str]                  # ["Paper A claims X, Paper B claims Y"]
    gaps: List[str]                            # Gap descriptions
    synthesis_quality: float                   # 0.0-1.0
    source_count: int


# Common ML/research method keywords for taxonomy detection
_METHOD_KEYWORDS = [
    "transformer", "attention", "retrieval", "memory", "contrastive",
    "diffusion", "distillation", "pruning", "quantization", "fine-tuning",
    "reinforcement", "generative", "classification", "detection", "segmentation",
    "embedding", "pretraining", "finetuning", "adaptation", "alignment",
]

_DATASET_KEYWORDS = [
    "imagenet", "coco", "mnist", "cifar", "squad", "glue", "superglue",
    "wikitext", "c4", "pile", "laion", "openwebtext", "bookcorpus",
    "pascal", "ade20k", "cityscapes", "vctk", "librispeech",
]

_METRIC_KEYWORDS = [
    "accuracy", "precision", "recall", "f1", "bleu", "rouge", "perplexity",
    "auc", "map", "iou", "psnr", "ssim", "fid", "inception", "top-1", "top-5",
    "wer", "cer", "sacrebleu",
]

# Relationship extraction patterns
_RELATIONSHIP_PATTERNS = [
    (r"(?:extends?|extending)\s+([A-Z][A-Za-z0-9\s\-]{2,40})", "extends"),
    (r"(?:builds?\s+on|building\s+on)\s+([A-Z][A-Za-z0-9\s\-]{2,40})", "builds on"),
    (r"(?:improves?\s+(?:over|upon))\s+([A-Z][A-Za-z0-9\s\-]{2,40})", "improves over"),
    (r"(?:based\s+on)\s+([A-Z][A-Za-z0-9\s\-]{2,40})", "based on"),
]


class CrossSourceSynthesizer:
    """Synthesizes findings across multiple analyzed sources.

    Pure rule-based synthesis — no LLM calls.
    Groups sources by type, extracts patterns, builds taxonomy.
    """

    def synthesize(
        self,
        topic: str,
        paper_analyses: List[Dict[str, Any]],
        repo_analyses: List[Dict[str, Any]],
        gaps: List[str],
        contradictions: List[str],
    ) -> SynthesisResult:
        """Produce a structured synthesis from analyzed sources."""
        all_analyses = paper_analyses + repo_analyses
        taxonomy = self._build_taxonomy(topic, all_analyses)
        best_papers = self._group_papers_by_category(paper_analyses, taxonomy)
        best_repos = self._group_repos_by_use_case(repo_analyses)
        relationships = self._extract_relationships(paper_analyses)

        source_count = len(paper_analyses) + len(repo_analyses)
        # Quality: higher when more sources and more categories found
        category_score = min(len(taxonomy.categories) / 5.0, 1.0)
        source_score = min(source_count / 10.0, 1.0)
        synthesis_quality = round((category_score + source_score) / 2.0, 3)

        return SynthesisResult(
            topic=topic,
            taxonomy=taxonomy,
            best_papers=best_papers,
            best_repos=best_repos,
            relationships=relationships,
            contradictions=list(contradictions),
            gaps=list(gaps),
            synthesis_quality=synthesis_quality,
            source_count=source_count,
        )

    def _build_taxonomy(self, topic: str, analyses: List[Dict]) -> FieldTaxonomy:
        """Extract taxonomy from source titles/abstracts using keyword clustering."""
        combined_text = " ".join(
            f"{a.get('title', '')} {a.get('abstract', '')} {a.get('description', '')}"
            for a in analyses
        ).lower()

        # Detect categories from recurring noun phrases in titles
        title_words: Dict[str, int] = {}
        for a in analyses:
            tokens = re.findall(r'\b[a-z]{4,}\b', (a.get('title', '') + ' ' + a.get('abstract', '')).lower())
            for tok in tokens:
                title_words[tok] = title_words.get(tok, 0) + 1

        # Filter stopwords and pick top recurring content words as categories
        stopwords = {
            "that", "with", "from", "this", "have", "been", "they", "their",
            "using", "show", "paper", "work", "model", "models", "method",
            "approach", "results", "based", "large", "data", "learn", "learning",
            "neural", "deep", "network", "networks", "training", "trained",
        }
        category_candidates = [
            w for w, cnt in sorted(title_words.items(), key=lambda x: -x[1])
            if w not in stopwords and cnt >= 2
        ][:8]

        # Detect known methods
        key_methods = [kw for kw in _METHOD_KEYWORDS if kw in combined_text][:6]

        # Detect known datasets
        key_datasets = [kw for kw in _DATASET_KEYWORDS if kw in combined_text][:6]

        # Detect known metrics
        key_metrics = [kw for kw in _METRIC_KEYWORDS if kw in combined_text][:6]

        # Build subcategories: each category gets up to 3 related words
        subcategories: Dict[str, List[str]] = {}
        for cat in category_candidates:
            subs = [
                w for w in category_candidates
                if w != cat and cat[:4] in w or w[:4] in cat
            ][:3]
            subcategories[cat] = subs

        return FieldTaxonomy(
            topic=topic,
            categories=category_candidates,
            subcategories=subcategories,
            key_methods=key_methods,
            key_datasets=key_datasets,
            key_metrics=key_metrics,
        )

    def _group_papers_by_category(
        self, analyses: List[Dict], taxonomy: FieldTaxonomy
    ) -> Dict[str, List[str]]:
        """Assign each paper to its most relevant taxonomy category."""
        grouped: Dict[str, List[str]] = {cat: [] for cat in taxonomy.categories}
        ungrouped: List[str] = []

        for paper in analyses:
            title = paper.get('title', '')
            abstract = paper.get('abstract', '').lower()
            text = f"{title} {abstract}".lower()
            best_cat: Optional[str] = None
            best_count = 0

            for cat in taxonomy.categories:
                count = text.count(cat)
                if count > best_count:
                    best_count = count
                    best_cat = cat

            if best_cat and best_count > 0:
                grouped[best_cat].append(title)
            else:
                ungrouped.append(title)

        # Put ungrouped under a catch-all
        if ungrouped:
            grouped["general"] = ungrouped

        # Remove empty categories
        return {k: v for k, v in grouped.items() if v}

    def _group_repos_by_use_case(self, repos: List[Dict]) -> Dict[str, List[str]]:
        """Group repos by detected use case from description."""
        use_case_keywords = {
            "training": ["train", "finetune", "fine-tune", "pretrain", "pre-train"],
            "inference": ["inference", "deploy", "serve", "production", "runtime"],
            "evaluation": ["eval", "benchmark", "metric", "assess", "test"],
            "data": ["dataset", "data", "corpus", "preprocess", "pipeline"],
            "visualization": ["visual", "plot", "dashboard", "monitor", "analyze"],
        }
        grouped: Dict[str, List[str]] = {}
        ungrouped: List[str] = []

        for repo in repos:
            name = repo.get('title', repo.get('name', ''))
            desc = (repo.get('description', '') or '').lower()
            assigned = False

            for use_case, keywords in use_case_keywords.items():
                if any(kw in desc for kw in keywords):
                    grouped.setdefault(use_case, []).append(name)
                    assigned = True
                    break

            if not assigned:
                ungrouped.append(name)

        if ungrouped:
            grouped["general"] = ungrouped

        return {k: v for k, v in grouped.items() if v}

    def _extract_relationships(self, analyses: List[Dict]) -> List[str]:
        """Extract relationship statements from abstracts using regex."""
        relationships: List[str] = []

        for analysis in analyses:
            title = analysis.get('title', '')
            abstract = analysis.get('abstract', '')
            if not abstract:
                continue

            for pattern, rel_type in _RELATIONSHIP_PATTERNS:
                matches = re.findall(pattern, abstract)
                for match in matches:
                    ref = match.strip()
                    if ref and len(ref) > 3:
                        relationships.append(f"{title} {rel_type} {ref}")

        # Deduplicate
        seen: set = set()
        unique: List[str] = []
        for rel in relationships:
            key = rel[:80].lower()
            if key not in seen:
                seen.add(key)
                unique.append(rel)

        return unique[:20]


# ---------------------------------------------------------------------------
# CitationBinder
# ---------------------------------------------------------------------------

@dataclass
class BoundCitation:
    """A claim with its bound source."""
    claim_text: str
    source_id: str
    source_title: str
    source_url: str
    citation_key: str       # e.g. "[1]", "[Smith2024]"


# Patterns that identify verifiable claim sentences
_CLAIM_SENTENCE_PATTERNS = [
    r'[A-Z][^.!?]{20,150}(?:achiev|show|demonstrat|outperform|report|find|improv)[^.!?]{0,80}[.!?]',
    r'[A-Z][^.!?]{0,60}\d+(?:\.\d+)?%[^.!?]{0,80}[.!?]',
    r'[A-Z][^.!?]{0,80}state.of.the.art[^.!?]{0,80}[.!?]',
]


class CitationBinder:
    """Ensures every claim in a report has a real source citation.

    Takes a report text and a list of available sources.
    Inserts inline citation keys next to verifiable claims.
    Flags claims that have no source backing.
    """

    def bind(
        self,
        report_text: str,
        sources: List[Dict[str, Any]],
    ) -> Tuple[str, List[BoundCitation], List[str]]:
        """
        Returns:
            - report_text with [N] citation keys inserted
            - list of BoundCitation (all successfully bound citations)
            - list of unbound claim strings (no source found)
        """
        claims = self._extract_claims(report_text)
        bound_citations: List[BoundCitation] = []
        unbound: List[str] = []
        modified_text = report_text

        for claim in claims:
            source = self._find_source_for_claim(claim, sources)
            if source:
                cite_num = len(bound_citations) + 1
                cite_key = f"[{cite_num}]"
                bc = BoundCitation(
                    claim_text=claim,
                    source_id=source.get('source_id', ''),
                    source_title=source.get('title', ''),
                    source_url=source.get('url', ''),
                    citation_key=cite_key,
                )
                bound_citations.append(bc)
                # Insert citation key after the claim in the text
                claim_end = claim.rstrip()
                if claim_end and claim_end[-1] in '.!?':
                    replacement = claim_end[:-1] + ' ' + cite_key + claim_end[-1]
                else:
                    replacement = claim_end + ' ' + cite_key
                modified_text = modified_text.replace(claim, replacement, 1)
            else:
                unbound.append(claim)

        return modified_text, bound_citations, unbound

    def _extract_claims(self, text: str) -> List[str]:
        """Extract verifiable claim sentences from report text."""
        claims: List[str] = []
        for pattern in _CLAIM_SENTENCE_PATTERNS:
            matches = re.findall(pattern, text)
            claims.extend(m.strip() for m in matches if m.strip())

        # Deduplicate preserving order
        seen: set = set()
        unique: List[str] = []
        for c in claims:
            key = c[:60].lower()
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique

    def _find_source_for_claim(
        self, claim: str, sources: List[Dict]
    ) -> Optional[Dict]:
        """Find the best matching source for a claim via keyword overlap."""
        if not sources:
            return None

        claim_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', claim.lower()))
        best_source: Optional[Dict] = None
        best_overlap = 0

        for source in sources:
            source_text = (
                f"{source.get('title', '')} {source.get('abstract', '')}"
            ).lower()
            source_words = set(re.findall(r'\b[a-zA-Z]{4,}\b', source_text))
            overlap = len(claim_words & source_words)
            if overlap > best_overlap:
                best_overlap = overlap
                best_source = source

        # Require at least 3 matching words for a valid binding
        return best_source if best_overlap >= 3 else None

    def _build_references_section(self, citations: List[BoundCitation]) -> str:
        """Build a ## References section with numbered citations."""
        if not citations:
            return ""

        lines = []
        seen_keys: set = set()
        counter = 1

        for bc in citations:
            if bc.citation_key in seen_keys:
                continue
            seen_keys.add(bc.citation_key)
            url_part = f" {bc.source_url}" if bc.source_url else ""
            lines.append(f"{counter}. {bc.source_title}{url_part}")
            counter += 1

        return "\n".join(lines)

    def citation_fidelity(self, bound: List[BoundCitation], unbound: List[str]) -> float:
        """Returns bound/(bound+unbound). 1.0 = all claims sourced."""
        total = len(bound) + len(unbound)
        if total == 0:
            return 1.0
        return len(bound) / total


# ---------------------------------------------------------------------------
# ResearchReportGenerator
# ---------------------------------------------------------------------------

@dataclass
class ResearchReport:
    """A complete deep research report."""
    topic: str
    report_id: str = field(default_factory=lambda: str(uuid4()))

    # Content sections
    executive_summary: str = ""
    taxonomy_section: str = ""
    best_papers_section: str = ""
    best_repos_section: str = ""
    concepts_section: str = ""
    relationships_section: str = ""
    gaps_section: str = ""
    contested_claims_section: str = ""
    next_steps_section: str = ""
    references_section: str = ""

    # Metadata
    sources_used: int = 0
    citation_fidelity: float = 0.0
    quality_score: float = 0.0
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_markdown(self) -> str:
        """Render the full report as a Markdown string."""
        sections = [
            f"# Deep Research: {self.topic}\n",
            (
                f"*Generated: {self.generated_at.strftime('%Y-%m-%d')} "
                f"| Sources: {self.sources_used} "
                f"| Quality: {self.quality_score:.0%}*\n"
            ),
            "---\n",
        ]
        if self.executive_summary:
            sections.append(f"## Executive Summary\n\n{self.executive_summary}\n")
        if self.taxonomy_section:
            sections.append(f"## Field Taxonomy\n\n{self.taxonomy_section}\n")
        if self.best_papers_section:
            sections.append(f"## Best Papers\n\n{self.best_papers_section}\n")
        if self.best_repos_section:
            sections.append(f"## Best GitHub Repositories\n\n{self.best_repos_section}\n")
        if self.gaps_section:
            sections.append(f"## Research Gaps\n\n{self.gaps_section}\n")
        if self.contested_claims_section:
            sections.append(f"## Contested Claims & Counter-Evidence\n\n{self.contested_claims_section}\n")
        if self.next_steps_section:
            sections.append(f"## Next Steps\n\n{self.next_steps_section}\n")
        if self.references_section:
            sections.append(f"## References\n\n{self.references_section}\n")
        return "\n".join(sections)

    def save(self, output_dir: Path) -> Path:
        """Save report as Markdown file. Returns file path."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_topic = re.sub(r'[^a-zA-Z0-9_\-]', '_', self.topic)[:60]
        filename = f"report_{safe_topic}_{self.report_id[:8]}.md"
        file_path = output_dir / filename
        file_path.write_text(self.to_markdown(), encoding="utf-8")
        return file_path


class ResearchReportGenerator:
    """Generates structured Markdown research reports from synthesis results.

    Composes all sections from synthesis, gaps, contradictions, and sources.
    Uses CitationBinder to ensure all claims have sources.
    """

    def __init__(self) -> None:
        self.binder = CitationBinder()

    def generate(
        self,
        topic: str,
        synthesis: SynthesisResult,
        sources: List[Dict[str, Any]],
        gaps: List[str],
        contradictions: List[str],
        checklist_completion: float = 0.0,
    ) -> ResearchReport:
        """Generate a complete ResearchReport from synthesis components."""
        report = ResearchReport(topic=topic)
        report.sources_used = synthesis.source_count
        report.executive_summary = self._generate_executive_summary(synthesis)
        report.taxonomy_section = self._generate_taxonomy_section(synthesis.taxonomy)
        report.best_papers_section = self._generate_papers_section(
            synthesis.best_papers, sources
        )
        report.best_repos_section = self._generate_repos_section(
            synthesis.best_repos, sources
        )
        report.gaps_section = self._generate_gaps_section(gaps or synthesis.gaps)
        report.contested_claims_section = self._generate_contested_section(contradictions)
        report.next_steps_section = self._generate_next_steps(synthesis, gaps or synthesis.gaps)

        # Bind citations in the full report text (all sections concatenated)
        full_text = "\n".join([
            report.executive_summary,
            report.best_papers_section,
            report.best_repos_section,
        ])
        _, bound, unbound = self.binder.bind(full_text, sources)
        fidelity = self.binder.citation_fidelity(bound, unbound)
        report.citation_fidelity = fidelity

        # Build references section
        report.references_section = self.binder._build_references_section(bound)

        # Compute overall quality score
        report.quality_score = round(
            0.4 * checklist_completion +
            0.4 * synthesis.synthesis_quality +
            0.2 * fidelity,
            3,
        )

        return report

    def _generate_executive_summary(self, synthesis: SynthesisResult) -> str:
        """Generate 3-bullet executive summary from synthesis."""
        bullets = [
            f"- This report covers **{synthesis.topic}** drawing from "
            f"{synthesis.source_count} sources across "
            f"{len(synthesis.taxonomy.categories)} sub-areas.",
        ]

        if synthesis.taxonomy.key_methods:
            methods_str = ", ".join(synthesis.taxonomy.key_methods[:4])
            bullets.append(f"- Key methods identified: {methods_str}.")

        if synthesis.gaps:
            gap_count = len(synthesis.gaps)
            bullets.append(
                f"- {gap_count} research gap(s) detected that warrant further investigation."
            )
        else:
            bullets.append("- No critical research gaps were detected in the surveyed sources.")

        return "\n".join(bullets)

    def _generate_taxonomy_section(self, taxonomy: FieldTaxonomy) -> str:
        """Render taxonomy as indented Markdown list."""
        lines = [f"**Topic**: {taxonomy.topic}\n"]

        if taxonomy.categories:
            lines.append("**Sub-areas**:")
            for cat in taxonomy.categories:
                lines.append(f"- {cat}")
                subs = taxonomy.subcategories.get(cat, [])
                for sub in subs:
                    lines.append(f"  - {sub}")

        if taxonomy.key_methods:
            lines.append(f"\n**Key Methods**: {', '.join(taxonomy.key_methods)}")
        if taxonomy.key_datasets:
            lines.append(f"**Key Datasets**: {', '.join(taxonomy.key_datasets)}")
        if taxonomy.key_metrics:
            lines.append(f"**Key Metrics**: {', '.join(taxonomy.key_metrics)}")

        return "\n".join(lines)

    def _generate_papers_section(
        self, best_papers: Dict[str, List[str]], sources: List[Dict]
    ) -> str:
        """Render best papers as Markdown table per category."""
        if not best_papers:
            return "*No papers found.*"

        lines = []
        source_lookup = {s.get('title', ''): s for s in sources}

        for category, titles in best_papers.items():
            if not titles:
                continue
            lines.append(f"### {category.title()}")
            lines.append("| Title | Venue |")
            lines.append("|-------|-------|")
            for title in titles[:5]:
                src = source_lookup.get(title, {})
                venue = src.get('venue', src.get('source_id', '—'))
                lines.append(f"| {title} | {venue} |")
            lines.append("")

        return "\n".join(lines)

    def _generate_repos_section(
        self, best_repos: Dict[str, List[str]], sources: List[Dict]
    ) -> str:
        """Render best repos as Markdown table with stars/description."""
        if not best_repos:
            return "*No repositories found.*"

        lines = []
        source_lookup = {
            s.get('title', s.get('name', '')): s for s in sources
        }

        for use_case, names in best_repos.items():
            if not names:
                continue
            lines.append(f"### {use_case.title()}")
            lines.append("| Repository | Stars | Description |")
            lines.append("|------------|-------|-------------|")
            for name in names[:5]:
                src = source_lookup.get(name, {})
                stars = src.get('stars', '—')
                desc = (src.get('description', '') or '')[:80]
                lines.append(f"| {name} | {stars} | {desc} |")
            lines.append("")

        return "\n".join(lines)

    def _generate_gaps_section(self, gaps: List[str]) -> str:
        """Render gaps as numbered list."""
        if not gaps:
            return "*No research gaps identified.*"
        lines = []
        for i, gap in enumerate(gaps, 1):
            lines.append(f"{i}. {gap}")
        return "\n".join(lines)

    def _generate_contested_section(self, contradictions: List[str]) -> str:
        """Render contradictions/contested claims as a list."""
        if not contradictions:
            return "*No contested claims detected.*"
        lines = []
        for i, contradiction in enumerate(contradictions, 1):
            lines.append(f"{i}. {contradiction}")
        return "\n".join(lines)

    def _generate_next_steps(self, synthesis: SynthesisResult, gaps: List[str]) -> str:
        """Generate actionable next steps for researcher and practitioner."""
        lines = ["**For Researchers:**"]

        if gaps:
            lines.append(f"1. Investigate the top research gap: {gaps[0][:120]}")
        else:
            lines.append("1. Explore emerging sub-areas in the taxonomy for novel contributions.")

        if synthesis.taxonomy.key_methods:
            lines.append(
                f"2. Compare {synthesis.taxonomy.key_methods[0]} against newer baselines."
            )
        else:
            lines.append("2. Review baseline comparisons across the surveyed sources.")

        lines.append("3. Check for reproducibility issues in top-cited papers.")

        lines.append("\n**For Practitioners:**")

        if synthesis.best_repos:
            top_repos = next(iter(synthesis.best_repos.values()), [])
            if top_repos:
                lines.append(f"1. Start with the repository: {top_repos[0]}")
            else:
                lines.append("1. Explore the curated repository list above.")
        else:
            lines.append("1. Search GitHub for implementations of key methods.")

        lines.append("2. Evaluate open-source tools against your use-case requirements.")
        lines.append("3. Monitor the identified research gaps for new practical solutions.")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# ReportQualityChecker
# ---------------------------------------------------------------------------

@dataclass
class QualityReport:
    """Quality evaluation of a research report."""
    coverage_score: float           # checklist_answered / checklist_total
    citation_fidelity: float        # bound_citations / total_claims
    source_breadth: float           # unique_sources_used / sources_found
    gap_detection: float            # gaps_found / expected_gaps (heuristic)
    overall_score: float            # weighted average
    passed: bool                    # overall_score >= threshold
    issues: List[str]               # Specific quality issues found


class ReportQualityChecker:
    """Self-evaluates a research report before delivery.

    Checks: coverage, citation fidelity, source breadth, gap detection.
    Blocks delivery if citation_fidelity < 1.0 or coverage < 0.75.
    """

    COVERAGE_WEIGHT = 0.30
    CITATION_WEIGHT = 0.40         # Highest weight — no hallucinations
    BREADTH_WEIGHT = 0.15
    GAP_WEIGHT = 0.15

    MIN_CITATION_FIDELITY = 1.0    # Hard gate
    MIN_COVERAGE = 0.75            # Soft gate

    def check(
        self,
        report: ResearchReport,
        checklist_total: int,
        checklist_answered: int,
        sources_found: int,
        gaps_expected: int = 3,
    ) -> QualityReport:
        """Evaluate report quality. Returns QualityReport with passed flag."""
        issues: List[str] = []

        # Coverage score
        if checklist_total > 0:
            coverage_score = checklist_answered / checklist_total
        else:
            coverage_score = 1.0

        # Citation fidelity (from the report)
        citation_fidelity = report.citation_fidelity

        # Source breadth: sources_used vs sources_found
        if sources_found > 0:
            source_breadth = min(report.sources_used / sources_found, 1.0)
        else:
            source_breadth = 1.0

        # Gap detection: count gaps in the report
        gap_lines = [
            ln for ln in report.gaps_section.splitlines()
            if ln.strip() and not ln.strip().startswith("*")
        ]
        gaps_found = len(gap_lines)
        gap_detection = min(gaps_found / max(gaps_expected, 1), 1.0)

        # Weighted overall
        overall_score = round(
            self.COVERAGE_WEIGHT * coverage_score +
            self.CITATION_WEIGHT * citation_fidelity +
            self.BREADTH_WEIGHT * source_breadth +
            self.GAP_WEIGHT * gap_detection,
            4,
        )

        # Collect issues
        if coverage_score < self.MIN_COVERAGE:
            issues.append(
                f"Coverage too low: {coverage_score:.0%} < {self.MIN_COVERAGE:.0%}"
            )
        if citation_fidelity < self.MIN_CITATION_FIDELITY:
            issues.append(
                f"Citation fidelity too low: {citation_fidelity:.0%} "
                f"(some claims lack sources)"
            )
        if source_breadth < 0.5:
            issues.append(
                f"Low source breadth: only {report.sources_used}/{sources_found} sources used"
            )
        if gap_detection < 0.5:
            issues.append(
                f"Insufficient gap detection: found {gaps_found}, expected ~{gaps_expected}"
            )

        passed = self.is_deliverable_scores(citation_fidelity, coverage_score)

        return QualityReport(
            coverage_score=coverage_score,
            citation_fidelity=citation_fidelity,
            source_breadth=source_breadth,
            gap_detection=gap_detection,
            overall_score=overall_score,
            passed=passed,
            issues=issues,
        )

    def is_deliverable(self, quality: QualityReport) -> bool:
        """True if report passes all gates."""
        return (
            quality.citation_fidelity >= self.MIN_CITATION_FIDELITY
            and quality.coverage_score >= self.MIN_COVERAGE
        )

    def is_deliverable_scores(
        self, citation_fidelity: float, coverage_score: float
    ) -> bool:
        """True if raw scores pass all gates (internal helper)."""
        return (
            citation_fidelity >= self.MIN_CITATION_FIDELITY
            and coverage_score >= self.MIN_COVERAGE
        )
