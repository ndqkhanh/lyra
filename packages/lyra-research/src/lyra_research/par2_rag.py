"""
PAR2-RAG Deep Research Engine.

Plan-Act-Reflect with Retrieval-Augmented Generation: a coverage-first
autonomous research loop that plans research topics, executes actions,
reflects on findings, and synthesizes final reports.

PAR2-RAG = Plan -> Act -> Reflect -> Repeat (with RAG grounding).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from lyra_research.knowledge_graph import ResearchKG
from lyra_research.multi_perspective import (
    MultiPerspectiveSynthesizer,
)
from lyra_research.source_verification import AuditReport, SourceVerifier

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ActionType(Enum):
    """Categories of research actions."""

    SEARCH = "search"          # Query a knowledge source
    READ = "read"              # Read / ingest a source document
    ANALYZE = "analyze"        # Analyse findings
    SYNTHESIZE = "synthesize"  # Synthesize multiple findings
    VERIFY = "verify"          # Verify claims or citations


class ActionStatus(Enum):
    """Execution status of a research action."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Subtopic:
    """A sub-topic within a research plan.

    Attributes:
        id: Unique subtopic identifier.
        title: Short descriptive title.
        description: What needs to be researched.
        coverage_target: Desired coverage (0.0-1.0).
    """

    id: str
    title: str
    description: str = ""
    coverage_target: float = 1.0


@dataclass(frozen=True)
class ResearchPlan:
    """A structured plan for researching a topic.

    Attributes:
        id: Unique plan identifier.
        query: The original research query.
        depth: Research depth level (1=shallow, 3=deep).
        subtopics: Ordered list of subtopics to cover.
        created_at: Plan creation timestamp.
        metadata: Arbitrary additional data.
    """

    id: str
    query: str
    depth: int
    subtopics: tuple[Subtopic, ...]
    created_at: str = ""
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            object.__setattr__(
                self,
                "created_at",
                datetime.now(timezone.utc).isoformat(),
            )

    @property
    def topic_count(self) -> int:
        """Number of subtopics in the plan."""
        return len(self.subtopics)


@dataclass(frozen=True)
class ResearchAction:
    """A single research action to execute.

    Attributes:
        id: Unique action identifier.
        action_type: Type of action to perform.
        description: What this action should accomplish.
        target: URL, search query, or document reference.
        subtopic_ids: Which subtopics this action addresses.
        status: Current execution status.
        parameters: Additional action parameters.
    """

    id: str
    action_type: ActionType
    description: str
    target: str = ""
    subtopic_ids: tuple[str, ...] = ()
    status: ActionStatus = ActionStatus.PENDING
    parameters: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Finding:
    """A single research finding from executing an action.

    Attributes:
        id: Unique finding identifier.
        action_id: The action that produced this finding.
        content: The textual content discovered.
        sources: URLs or references supporting the finding.
        confidence: How confident we are in this finding (0.0-1.0).
        subtopic_ids: Subtopics this finding addresses.
        timestamp: When the finding was recorded.
    """

    id: str
    action_id: str
    content: str
    sources: tuple[str, ...] = ()
    confidence: float = 0.5
    subtopic_ids: tuple[str, ...] = ()
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            object.__setattr__(
                self,
                "timestamp",
                datetime.now(timezone.utc).isoformat(),
            )


@dataclass(frozen=True)
class CoverageMap:
    """Tracks coverage percentage for each subtopic.

    Attributes:
        subtopic_id: The subtopic being tracked.
        coverage: Current coverage (0.0-1.0).
        evidence_count: Number of evidence items collected.
        last_updated: ISO timestamp of last update.
    """

    subtopic_id: str
    coverage: float = 0.0
    evidence_count: int = 0
    last_updated: str = ""


@dataclass(frozen=True)
class ResearchReport:
    """Final synthesized research report.

    Attributes:
        plan_id: The research plan this report addresses.
        query: Original research query.
        summary: Executive summary.
        findings: All findings collected.
        coverage: Final coverage per subtopic.
        audit: Source verification audit report (if run).
        multi_perspective_report: Multi-perspective synthesis (if run).
        generated_at: Report generation timestamp.
    """

    plan_id: str
    query: str
    summary: str = ""
    findings: tuple[Finding, ...] = ()
    coverage: tuple[CoverageMap, ...] = ()
    audit: AuditReport | None = None
    multi_perspective_report: str = ""
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            object.__setattr__(
                self,
                "generated_at",
                datetime.now(timezone.utc).isoformat(),
            )


# ---------------------------------------------------------------------------
# CoverageTracker
# ---------------------------------------------------------------------------


class CoverageTracker:
    """Tracks what percentage of each subtopic has been researched.

    Coverage increases as evidence (findings) is added for a subtopic.
    Each piece of evidence contributes a diminishing increment, simulating
    the idea that early findings contribute more than later ones.
    """

    def __init__(self, subtopics: tuple[Subtopic, ...]) -> None:
        """Initialize tracker for the given subtopics.

        Args:
            subtopics: The subtopics from a research plan.
        """
        self._maps: dict[str, CoverageMap] = {}
        self._evidence: dict[str, int] = {}  # subtopic_id -> evidence count
        for st in subtopics:
            self._maps[st.id] = CoverageMap(subtopic_id=st.id)
            self._evidence[st.id] = 0

    def update_coverage(self, subtopic_id: str, evidence_count: int = 1) -> CoverageMap:
        """Register new evidence for a subtopic and recompute coverage.

        Args:
            subtopic_id: Target subtopic.
            evidence_count: How many new evidence items to register.

        Returns:
            The updated ``CoverageMap``.
        """
        if subtopic_id not in self._maps:
            logger.warning("CoverageTracker: unknown subtopic %s", subtopic_id)
            return CoverageMap(subtopic_id=subtopic_id)

        self._evidence[subtopic_id] += evidence_count

        # Diminishing returns: coverage = 1 - exp(-k * n)
        # k = 0.5 gives ~63% at n=2, ~86% at n=4, ~95% at n=6+
        k = 0.5
        n = self._evidence[subtopic_id]
        coverage = 1.0 - (2.71828 ** (-k * n))  # approximate exp
        coverage = min(coverage, 1.0)

        new_map = CoverageMap(
            subtopic_id=subtopic_id,
            coverage=round(coverage, 4),
            evidence_count=n,
            last_updated=datetime.now(timezone.utc).isoformat(),
        )
        self._maps[subtopic_id] = new_map

        logger.debug(
            "CoverageTracker[%s]: %d evidence -> %.2f coverage",
            subtopic_id,
            n,
            coverage,
        )
        return new_map

    def get_coverage(self, subtopic_id: str) -> float:
        """Return current coverage for *subtopic_id*."""
        cmap = self._maps.get(subtopic_id)
        return cmap.coverage if cmap else 0.0

    def overall_coverage(self) -> float:
        """Return mean coverage across all subtopics."""
        if not self._maps:
            return 0.0
        return sum(m.coverage for m in self._maps.values()) / len(self._maps)

    def all_maps(self) -> tuple[CoverageMap, ...]:
        """Return all current coverage maps."""
        return tuple(self._maps.values())

    def lowest_coverage_subtopic(self) -> str | None:
        """Return the subtopic ID with the lowest coverage."""
        if not self._maps:
            return None
        return min(self._maps, key=lambda sid: self._maps[sid].coverage)


# ---------------------------------------------------------------------------
# PAR2RAGEngine
# ---------------------------------------------------------------------------


class PAR2RAGEngine:
    """Plan-Act-Reflect research engine with coverage-first loop.

    The engine plans research into subtopics with coverage targets,
    executes actions, reflects on findings to identify gaps and new
    directions, and synthesizes a final report once coverage and
    confidence thresholds are met.

    Typical usage::

        engine = PAR2RAGEngine()
        report = engine.run_deep_research("attention mechanisms", depth=3)
        print(report.summary)
    """

    DEFAULT_COVERAGE_THRESHOLD = 0.75
    DEFAULT_CONFIDENCE_THRESHOLD = 0.6
    MAX_ACTIONS_PER_LOOP = 10

    def __init__(
        self,
        coverage_threshold: float = DEFAULT_COVERAGE_THRESHOLD,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        max_iterations: int = 15,
    ) -> None:
        """Initialize the PAR2-RAG engine.

        Args:
            coverage_threshold: Minimum overall coverage to stop (0.0-1.0).
            confidence_threshold: Minimum average confidence to stop (0.0-1.0).
            max_iterations: Hard cap on plan-act-reflect loops.
        """
        self.coverage_threshold = coverage_threshold
        self.confidence_threshold = confidence_threshold
        self.max_iterations = max_iterations

        # Sub-engines
        self._source_verifier = SourceVerifier()
        self._multi_perspective = MultiPerspectiveSynthesizer()

        # State (reset each run)
        self._plan: ResearchPlan | None = None
        self._tracker: CoverageTracker | None = None
        self._findings: list[Finding] = []
        self._kg = ResearchKG(name="par2rag")
        self._iteration: int = 0
        self._action_history: list[ResearchAction] = []

    # ------------------------------------------------------------------
    # Phase 1: Plan
    # ------------------------------------------------------------------

    def plan_research(self, query: str, depth: int = 3) -> ResearchPlan:
        """Generate a structured research plan for *query*.

        Creates subtopics with coverage targets.  Depth controls how many
        subtopics and their specificity.

        Args:
            query: Research topic or question.
            depth: 1=quick (3 subtopics), 2=standard (5), 3=deep (8).

        Returns:
            ``ResearchPlan`` with coverage targets.
        """
        depth = max(1, min(depth, 5))
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        # Generate subtopics based on depth
        subtopic_templates = _generate_subtopic_templates(query, depth)
        subtopics = tuple(
            Subtopic(
                id=f"{plan_id}_st{i:02d}",
                title=title,
                description=desc,
                coverage_target=1.0,
            )
            for i, (title, desc) in enumerate(subtopic_templates)
        )

        plan = ResearchPlan(
            id=plan_id,
            query=query,
            depth=depth,
            subtopics=subtopics,
        )

        self._plan = plan
        self._tracker = CoverageTracker(subtopics)
        self._findings = []
        self._iteration = 0
        self._action_history = []

        logger.info(
            "Research plan created: %s (depth=%d, %d subtopics)",
            plan_id,
            depth,
            len(subtopics),
        )
        return plan

    # ------------------------------------------------------------------
    # Phase 2: Act
    # ------------------------------------------------------------------

    def execute_action(self, action: ResearchAction) -> Finding:
        """Execute a single research action and return the finding.

        This is a rule-based simulation.  In production, it would call
        actual search APIs, read documents, and invoke LLM analysis.

        Args:
            action: The action to execute.

        Returns:
            A ``Finding`` with the results.
        """
        logger.info(
            "Executing action %s [%s]: %s",
            action.id,
            action.action_type.value,
            action.description,
        )

        content = ""
        confidence = 0.5
        sources: list[str] = []

        if action.action_type == ActionType.SEARCH:
            content = (
                f"Search results for '{action.target or action.description}' "
                f"returned relevant documents covering key aspects."
            )
            confidence = 0.4  # Search results need verification
            sources = [action.target] if action.target else []

        elif action.action_type == ActionType.READ:
            content = (
                f"Read and extracted content from {action.target or 'source'}. "
                f"Key information: {action.description}"
            )
            confidence = 0.7
            sources = [action.target] if action.target else []

        elif action.action_type == ActionType.ANALYZE:
            content = (
                f"Analysis of findings: {action.description}. "
                f"Patterns identified and cross-referenced against known literature."
            )
            confidence = 0.6
            sources = list(action.subtopic_ids) if action.subtopic_ids else []

        elif action.action_type == ActionType.SYNTHESIZE:
            content = (
                f"Synthesis: {action.description}. "
                f"Combined multiple findings into a coherent narrative."
            )
            confidence = 0.65

        elif action.action_type == ActionType.VERIFY:
            content = (
                f"Verification: {action.description}. "
                f"Claims checked against cited sources."
            )
            confidence = 0.8
            sources = [action.target] if action.target else []

        finding = Finding(
            id=f"find_{uuid.uuid4().hex[:8]}",
            action_id=action.id,
            content=content,
            sources=tuple(sources),
            confidence=confidence,
            subtopic_ids=action.subtopic_ids,
        )

        self._findings.append(finding)

        # Update coverage for addressed subtopics
        if self._tracker:
            for st_id in action.subtopic_ids:
                self._tracker.update_coverage(st_id, evidence_count=1)

        # Extract entities into the knowledge graph
        entities = self._kg.extract_entities(content[:500])
        for ent in entities:
            self._kg.add_entity(ent)

        logger.debug("Action %s produced finding %s", action.id, finding.id)
        return finding

    # ------------------------------------------------------------------
    # Phase 3: Reflect
    # ------------------------------------------------------------------

    def reflect_on_findings(self, findings: list[Finding]) -> dict[str, Any]:
        """Analyze findings to identify gaps, inconsistencies, and new directions.

        Args:
            findings: All findings collected so far.

        Returns:
            Dict with keys: gaps, inconsistencies, new_directions, quality_score.
        """
        if not findings:
            return {
                "gaps": ["No findings collected yet."],
                "inconsistencies": [],
                "new_directions": [],
                "quality_score": 0.0,
            }

        # Identify gaps: which subtopics have low coverage?
        gaps: list[str] = []
        if self._tracker:
            for cmap in self._tracker.all_maps():
                if cmap.coverage < 0.5:
                    gaps.append(
                        f"Subtopic '{cmap.subtopic_id}' has low coverage ({cmap.coverage:.2f})"
                    )

        # Identify inconsistencies: findings with conflicting signals
        inconsistencies: list[str] = []
        sources_seen: dict[str, str] = {}
        for f in findings:
            for src in f.sources:
                if src in sources_seen and sources_seen[src] != f.content[:50]:
                    inconsistencies.append(
                        f"Source '{src}' cited with differing interpretations."
                    )
                    break
                sources_seen[src] = f.content[:50]

        # Identify new directions from the knowledge graph
        new_directions: list[str] = []
        if self._kg.entity_count > 2:
            entities = self._kg.list_entities()
            for i, e1 in enumerate(entities[:5]):
                for e2 in entities[i + 1 : 6]:
                    path = self._kg.find_path(e1.id, e2.id)
                    if path and len(path) > 2:
                        new_directions.append(
                            f"Explore relationship between '{e1.name}' and '{e2.name}'"
                        )
                        break

        if not new_directions:
            new_directions.append("Deepen analysis of highest-confidence findings.")

        # Quality score: average confidence weighted by coverage
        avg_confidence = sum(f.confidence for f in findings) / len(findings)
        coverage = self._tracker.overall_coverage() if self._tracker else 0.0
        quality = round(avg_confidence * 0.6 + coverage * 0.4, 4)

        logger.info(
            "Reflection: %d gaps, %d inconsistencies, %d new directions, quality=%.2f",
            len(gaps),
            len(inconsistencies),
            len(new_directions),
            quality,
        )
        return {
            "gaps": gaps or ["Coverage proceeding as expected."],
            "inconsistencies": inconsistencies,
            "new_directions": new_directions,
            "quality_score": quality,
        }

    # ------------------------------------------------------------------
    # Coverage tracking
    # ------------------------------------------------------------------

    def update_coverage(self, subtopic_id: str, evidence_count: int = 1) -> CoverageMap | None:
        """Update the coverage map for a subtopic.

        Args:
            subtopic_id: The subtopic to update.
            evidence_count: Number of new evidence items.

        Returns:
            Updated ``CoverageMap`` or ``None`` if tracker not initialized.
        """
        if not self._tracker:
            return None
        return self._tracker.update_coverage(subtopic_id, evidence_count)

    # ------------------------------------------------------------------
    # Decision: should we continue?
    # ------------------------------------------------------------------

    def should_continue(self) -> tuple[bool, str]:
        """Decide whether the research loop should continue.

        Checks coverage threshold, confidence threshold, and iteration cap.

        Returns:
            (continue_flag, reason_string).
        """
        if not self._tracker:
            return False, "No research plan active."

        coverage = self._tracker.overall_coverage()

        avg_confidence = 0.0
        if self._findings:
            avg_confidence = sum(f.confidence for f in self._findings) / len(self._findings)

        if self._iteration >= self.max_iterations:
            return False, (
                f"Max iterations ({self.max_iterations}) reached. "
                f"Coverage: {coverage:.2f}, Confidence: {avg_confidence:.2f}"
            )

        if coverage >= self.coverage_threshold and avg_confidence >= self.confidence_threshold:
            return False, (
                f"Thresholds met — coverage {coverage:.2f} >= {self.coverage_threshold}, "
                f"confidence {avg_confidence:.2f} >= {self.confidence_threshold}"
            )

        return True, (
            f"Continuing — coverage {coverage:.2f} < {self.coverage_threshold} "
            f"or confidence {avg_confidence:.2f} < {self.confidence_threshold}"
        )

    # ------------------------------------------------------------------
    # Phase 4: Synthesize
    # ------------------------------------------------------------------

    def synthesize_report(
        self,
        plan: ResearchPlan,
        findings: list[Finding],
    ) -> ResearchReport:
        """Compile a final research report from the plan and findings.

        Args:
            plan: The original research plan.
            findings: All collected findings.

        Returns:
            ``ResearchReport`` ready for presentation.
        """
        if not findings:
            return ResearchReport(
                plan_id=plan.id,
                query=plan.query,
                summary="No findings were collected during this research cycle.",
            )

        # Build summary from findings
        summary_parts: list[str] = [
            f"Research completed for query: '{plan.query}'",
            f"Depth: {plan.depth}, Subtopics: {plan.topic_count}",
            f"Findings collected: {len(findings)}",
        ]

        coverage = self._tracker.all_maps() if self._tracker else ()

        # Add per-subtopic summary
        if coverage:
            summary_parts.append("\nCoverage by subtopic:")
            for cmap in coverage:
                summary_parts.append(f"  - {cmap.subtopic_id}: {cmap.coverage:.0%} ({cmap.evidence_count} items)")

        # Run source verification audit on combined findings
        audit: AuditReport | None = None
        combined_text = " ".join(f.content for f in findings)
        if combined_text:
            audit = self._source_verifier.audit_document(combined_text)

        # Run multi-perspective synthesis
        mp_report = ""
        if findings and combined_text:
            debates = self._multi_perspective.debate(
                topic=plan.query,
                findings=combined_text[:2000],
                rounds=2,
            )
            synthesis = self._multi_perspective.synthesize_perspectives(debates)
            mp_report = synthesis.balanced_report

        logger.info(
            "Report synthesized: %d findings, audit=%s, mp=%s",
            len(findings),
            audit is not None,
            bool(mp_report),
        )
        return ResearchReport(
            plan_id=plan.id,
            query=plan.query,
            summary="\n".join(summary_parts),
            findings=tuple(findings),
            coverage=coverage,
            audit=audit,
            multi_perspective_report=mp_report,
        )

    # ------------------------------------------------------------------
    # Full autonomous loop
    # ------------------------------------------------------------------

    def run_deep_research(
        self,
        query: str,
        depth: int = 3,
    ) -> ResearchReport:
        """Run the full autonomous PAR2-RAG research cycle.

        Plan -> Act -> Reflect -> repeat until coverage/confidence
        thresholds are met or max iterations exhausted.

        Args:
            query: Research topic or question.
            depth: 1=quick, 2=standard, 3=deep.

        Returns:
            ``ResearchReport`` with the synthesized findings.
        """
        logger.info("=== PAR2-RAG Deep Research: '%s' (depth=%d) ===", query, depth)

        # Plan
        plan = self.plan_research(query, depth=depth)
        if not self._tracker:
            return ResearchReport(plan_id=plan.id, query=query)

        # Main loop: Act + Reflect
        while True:
            cont, reason = self.should_continue()
            if not cont:
                logger.info("Research loop stopping: %s", reason)
                break

            self._iteration += 1
            logger.info(
                "--- Iteration %d/%d (coverage: %.2f) ---",
                self._iteration,
                self.max_iterations,
                self._tracker.overall_coverage(),
            )

            # Find the lowest-coverage subtopic and generate an action for it
            target_st = self._tracker.lowest_coverage_subtopic()
            if not target_st:
                break

            # Cycle through action types based on iteration
            action_types = [
                ActionType.SEARCH,
                ActionType.READ,
                ActionType.ANALYZE,
                ActionType.SYNTHESIZE,
                ActionType.VERIFY,
            ]
            atype = action_types[self._iteration % len(action_types)]

            action = ResearchAction(
                id=f"act_{uuid.uuid4().hex[:6]}",
                action_type=atype,
                description=f"{atype.value} on subtopic '{target_st}' for '{query}'",
                target=query,
                subtopic_ids=(target_st,),
                status=ActionStatus.IN_PROGRESS,
            )
            self._action_history.append(action)

            # Act
            self.execute_action(action)

            # Reflect periodically (every 3 iterations or after SEARCH complete)
            if self._iteration % 3 == 0:
                reflection = self.reflect_on_findings(self._findings)
                logger.info(
                    "Reflection (iter %d): quality=%.2f, gaps=%d",
                    self._iteration,
                    reflection["quality_score"],
                    len(reflection["gaps"]),
                )

        # Synthesize final report
        return self.synthesize_report(plan, self._findings)


# ---------------------------------------------------------------------------
# Subtopic template generation
# ---------------------------------------------------------------------------


def _generate_subtopic_templates(query: str, depth: int) -> list[tuple[str, str]]:
    """Generate subtopic (title, description) pairs for a query."""

    universal: list[tuple[str, str]] = [
        (
            f"Definition & fundamentals of {query}",
            f"Core concepts, terminology, and problem framing for {query}.",
        ),
        (
            f"State-of-the-art in {query}",
            f"Current best methods, latest papers, and leading approaches for {query}.",
        ),
        (
            f"Key methods & architectures for {query}",
            f"Technical survey of algorithms, architectures, and implementations for {query}.",
        ),
        (
            f"Benchmarks & evaluation for {query}",
            f"Standard datasets, metrics, and evaluation protocols for {query}.",
        ),
        (
            f"Limitations & open problems in {query}",
            f"Known failure modes, scalability challenges, and unresolved issues for {query}.",
        ),
        (
            f"Applications of {query}",
            f"Real-world use cases, industry adoption, and practical impact of {query}.",
        ),
        (
            f"Comparative analysis for {query}",
            f"Head-to-head comparisons of top methods, trade-offs, and selection guidance for {query}.",
        ),
        (
            f"Future directions for {query}",
            f"Emerging trends, speculative advances, and research roadmaps for {query}.",
        ),
    ]

    # Depth controls how many subtopics we include
    count_map = {1: 3, 2: 5, 3: 8, 4: 10, 5: 12}
    count = min(count_map.get(depth, 8), len(universal))
    return universal[:count]
