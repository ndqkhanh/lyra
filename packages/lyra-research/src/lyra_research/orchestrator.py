"""
ResearchOrchestrator — 3-Agent Hybrid Architecture with Coordination.

Integrates:
- Week 1: Coordination primitives (retry, timeout, circuit breaker)
- Week 2: Memory capacity management
- Week 3: Adversarial review system
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from lyra_core.context.isolation import (
    ContextBoundary,
    IsolationPolicy,
)
from lyra_core.context.layered_context import (
    ContextLayer,
    LayeredContextManager,
)
from lyra_core.context.provenance import ContextAuditTrail

from lyra_research.adversarial_reviewer import AdversarialReviewer
from lyra_research.capacity_manager import CapacityManager
from lyra_research.coordination import (
    CoordinationManager,
    FailureType,
    Task,
    TaskState,
)
from lyra_research.discovery import MultiSourceDiscovery, ResearchSource
from lyra_research.intelligence import (
    FalsificationChecker,
    GapAnalyzer,
    VerifiableChecklistGenerator,
)
from lyra_research.memory import (
    CorpusEntry,
    LocalCorpus,
    ResearchCase,
    ResearchNote,
    ResearchNoteStore,
    ResearchStrategyMemory,
    SessionCaseBank,
)
from lyra_research.reporter import (
    CrossSourceSynthesizer,
    ReportQualityChecker,
    ResearchReport,
    ResearchReportGenerator,
)
from lyra_research.skills import ResearchSkillStore, StrategyAdaptationSkill
from lyra_research.sources import SourceQualityScorer

# ---------------------------------------------------------------------------
# Agent Types
# ---------------------------------------------------------------------------


class AgentType(Enum):
    """Agent types in the 3-agent hybrid architecture."""
    DISCOVERY = "discovery"  # Haiku - parallel source discovery
    ANALYSIS = "analysis"    # Sonnet - paper/repo analysis
    SYNTHESIS = "synthesis"  # Opus - report generation


# ---------------------------------------------------------------------------
# Agent Configuration
# ---------------------------------------------------------------------------


@dataclass
class AgentConfig:
    """Configuration for an agent in the hybrid system."""
    type: AgentType
    model: str  # Model identifier
    timeout_seconds: int
    max_retries: int


# Default agent configurations
DEFAULT_AGENT_CONFIGS = {
    AgentType.DISCOVERY: AgentConfig(
        type=AgentType.DISCOVERY,
        model="claude-haiku-4-5",
        timeout_seconds=300,  # 5 minutes
        max_retries=2,
    ),
    AgentType.ANALYSIS: AgentConfig(
        type=AgentType.ANALYSIS,
        model="claude-sonnet-4-6",
        timeout_seconds=600,  # 10 minutes
        max_retries=2,
    ),
    AgentType.SYNTHESIS: AgentConfig(
        type=AgentType.SYNTHESIS,
        model="claude-opus-4-7",
        timeout_seconds=900,  # 15 minutes
        max_retries=1,  # Expensive model, fewer retries
    ),
}


# ---------------------------------------------------------------------------
# Research Progress
# ---------------------------------------------------------------------------


@dataclass
class ResearchProgress:
    """Tracks progress through the research pipeline with telemetry."""

    session_id: str
    topic: str
    current_step: int = 0
    current_step_name: str = ""
    sources_found: dict[str, int] = field(default_factory=dict)
    papers_analyzed: int = 0
    repos_analyzed: int = 0
    gaps_found: int = 0
    report: Any | None = None
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    # Telemetry
    context_size_kb: float = 0.0
    verification_rate: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_retried: int = 0

    @property
    def is_complete(self) -> bool:
        return self.current_step >= 10 and self.report is not None

    @property
    def elapsed_seconds(self) -> float:
        end = self.completed_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()


ProgressCallback = Callable[[ResearchProgress], None]


# ---------------------------------------------------------------------------
# Research Orchestrator
# ---------------------------------------------------------------------------


class ResearchOrchestrator:
    """3-Agent Hybrid Research Orchestrator.

    Architecture:
    - Discovery Agent (Haiku): Parallel source discovery
    - Analysis Agent (Sonnet): Paper/repo analysis
    - Synthesis Agent (Opus): Report generation

    Integration:
    - CoordinationManager: Task execution with retry/timeout/circuit breaker
    - CapacityManager: Memory capacity enforcement
    - AdversarialReviewer: Quality assurance for deep research

    Steps:
    1. CLARIFY   - validate topic and depth
    2. PLAN      - generate verifiable checklist
    3. SEARCH    - discover sources (Discovery Agent)
    4. FILTER    - rank and deduplicate by quality
    5. FETCH     - load source metadata into corpus
    6. ANALYZE   - extract summaries (Analysis Agent)
    7. EVIDENCE_AUDIT - verify claims vs sources
    8. SYNTHESIZE - build taxonomy (Synthesis Agent)
    9. REPORT    - generate report (Synthesis Agent)
    10. MEMORIZE - persist to memory stores
    """

    def __init__(
        self,
        output_dir: Path | None = None,
        note_store: ResearchNoteStore | None = None,
        corpus: LocalCorpus | None = None,
        strategy_memory: ResearchStrategyMemory | None = None,
        case_bank: SessionCaseBank | None = None,
        coordination_manager: CoordinationManager | None = None,
        capacity_manager: CapacityManager | None = None,
        adversarial_reviewer: AdversarialReviewer | None = None,
        agent_configs: dict[AgentType, AgentConfig] | None = None,
    ) -> None:
        self.output_dir = output_dir or Path.home() / ".lyra" / "research_reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Memory stores
        self.note_store = note_store or ResearchNoteStore()
        self.corpus = corpus or LocalCorpus()
        self.strategy_memory = strategy_memory or ResearchStrategyMemory()
        self.case_bank = case_bank or SessionCaseBank()

        # Week 1-3 integrations
        self.coordination = coordination_manager or CoordinationManager()

        # Capacity manager with default DB path
        db_path = Path.home() / ".lyra" / "research.db"
        self.capacity = capacity_manager or CapacityManager(db_path=db_path)

        self.reviewer = adversarial_reviewer or AdversarialReviewer()

        # Agent configurations
        self.agent_configs = agent_configs or DEFAULT_AGENT_CONFIGS

        # Phase 1 Week 4: Layered context system
        self.context_manager = LayeredContextManager(max_tokens=100_000)
        self.audit_trail = ContextAuditTrail()
        self.context_manager.audit_trail = self.audit_trail

        # Context boundaries for each agent type
        self.discovery_boundary = ContextBoundary(
            self.context_manager,
            IsolationPolicy.for_discovery_agent(),
        )
        self.analysis_boundary = ContextBoundary(
            self.context_manager,
            IsolationPolicy.for_analysis_agent(),
        )
        self.synthesis_boundary = ContextBoundary(
            self.context_manager,
            IsolationPolicy.for_synthesis_agent(),
        )

        # Pipeline components
        import os
        semantic_scholar_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        github_token = os.environ.get("GITHUB_TOKEN")

        self.discovery = MultiSourceDiscovery(
            semantic_scholar_key=semantic_scholar_key,
            github_token=github_token,
        )
        self.quality_scorer = SourceQualityScorer()
        self.checklist_gen = VerifiableChecklistGenerator()
        self.gap_analyzer = GapAnalyzer()
        self.falsification = FalsificationChecker()
        self.synthesizer = CrossSourceSynthesizer()
        self.report_gen = ResearchReportGenerator()
        self.quality_checker = ReportQualityChecker()
        self.skill_store = ResearchSkillStore()
        self.strategy_adapter = StrategyAdaptationSkill()

    def research(
        self,
        topic: str,
        depth: str = "standard",
        sources: list[str] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> ResearchProgress:
        """Execute the full research pipeline with 3-agent hybrid architecture.

        Args:
            topic: Research topic
            depth: "quick", "standard", or "deep"
            sources: Source names to search (default: all)
            progress_callback: Called after each step

        Returns:
            ResearchProgress with report or error
        """
        progress = ResearchProgress(
            session_id=str(uuid4()),
            topic=topic,
        )

        def _step(n: int, name: str) -> None:
            progress.current_step = n
            progress.current_step_name = name
            if progress_callback:
                progress_callback(progress)

        try:
            # Check capacity before starting
            self.capacity.enforce_limits()

            # Initialize context with system and task layers
            self.context_manager.add(
                ContextLayer.SYSTEM,
                "You are a deep research AI assistant",
                source="system_prompt",
                priority=10,
            )
            self.context_manager.add(
                ContextLayer.TASK,
                f"Research topic: {topic}",
                source="user_query",
                priority=9,
            )

            # Step 1: Clarify
            _step(1, "Clarifying research scope")
            validated_topic, resolved_depth = self._clarify(topic, depth)

            # Step 2: Plan
            _step(2, "Generating research checklist")
            checklist = self.checklist_gen.generate(validated_topic, resolved_depth)

            # Step 3: Search (Discovery Agent - parallel)
            _step(3, "Searching sources")
            discovery_task = self._create_task(AgentType.DISCOVERY)
            raw_results = self._execute_discovery(
                discovery_task,
                validated_topic,
                resolved_depth,
                sources,
            )

            for src_name, src_list in raw_results.items():
                progress.sources_found[src_name] = len(src_list)
            all_sources_flat = [s for lst in raw_results.values() for s in lst]

            # Step 4: Filter & Rank
            _step(4, "Filtering and ranking sources")
            ranked = self._rank_and_deduplicate(all_sources_flat, validated_topic)
            top_n = 50 if resolved_depth == "deep" else 30 if resolved_depth == "standard" else 10
            ranked = ranked[:top_n]

            # Step 5: Fetch (check capacity before storing)
            _step(5, "Fetching source metadata")
            self.capacity.enforce_limits()
            self._store_to_corpus(ranked)
            progress.papers_analyzed = sum(
                1 for s in ranked if s.source_type.value == "paper"
            )
            progress.repos_analyzed = sum(
                1 for s in ranked if s.source_type.value == "repository"
            )

            # Step 6: Analyze (Analysis Agent - parallel)
            _step(6, "Analyzing sources")
            analysis_task = self._create_task(AgentType.ANALYSIS)
            paper_analyses, repo_analyses = self._execute_analysis(
                analysis_task,
                ranked,
            )

            # Step 7: Evidence Audit
            _step(7, "Auditing evidence")
            gaps = self.gap_analyzer.analyze(
                [
                    {
                        "source_id": s.id,
                        "title": s.title,
                        "abstract": s.abstract,
                        "findings": [],
                    }
                    for s in ranked
                ],
                validated_topic,
            )
            gap_strings = [g.area for g in gaps]
            progress.gaps_found = len(gaps)

            # Step 8: Synthesize (Synthesis Agent)
            _step(8, "Synthesizing findings")
            synthesis_task = self._create_task(AgentType.SYNTHESIS)
            synthesis = self._execute_synthesis(
                synthesis_task,
                validated_topic,
                paper_analyses,
                repo_analyses,
                gap_strings,
            )

            # Step 9: Report (Synthesis Agent)
            _step(9, "Generating report")
            report_task = self._create_task(AgentType.SYNTHESIS)
            source_dicts = [self._source_to_dict(s) for s in ranked]
            report = self._execute_report_generation(
                report_task,
                validated_topic,
                synthesis,
                source_dicts,
                gap_strings,
                checklist,
            )

            # Adversarial review for deep research
            if resolved_depth == "deep":
                review_result = self.reviewer.review(report, ranked, depth=resolved_depth)
                if review_result.revised_report:
                    # Update report with reviewed content
                    report.content = review_result.revised_report
                progress.verification_rate = (
                    review_result.claims_reviewed - review_result.claims_modified
                ) / review_result.claims_reviewed if review_result.claims_reviewed > 0 else 1.0
                progress.context_size_kb = review_result.context_size_kb

            report.sources_used = len(ranked)
            saved_path = report.save(self.output_dir)
            quality = self.quality_checker.check(
                report=report,
                checklist_total=len(checklist.items),
                checklist_answered=sum(1 for i in checklist.items if i.answered),
                sources_found=len(all_sources_flat),
                gaps_expected=3,
            )
            report.quality_score = quality.overall_score
            progress.report = report

            # Step 10: Memorize (check capacity before storing)
            _step(10, "Saving to memory")
            self.capacity.enforce_limits()
            self._memorize(validated_topic, report, ranked, quality.overall_score, str(saved_path))

            # Collect telemetry
            progress.tasks_completed = sum(
                1 for t in self.coordination.get_all_tasks()
                if t.state == TaskState.COMPLETED
            )
            progress.tasks_failed = sum(
                1 for t in self.coordination.get_all_tasks()
                if t.state == TaskState.FAILED
            )
            progress.tasks_retried = sum(
                t.retry_count for t in self.coordination.get_all_tasks()
            )

            progress.completed_at = datetime.now(timezone.utc)
            return progress

        except Exception as e:
            progress.error = str(e)
            progress.completed_at = datetime.now(timezone.utc)
            return progress

    # --- Agent Task Execution ---

    def _create_task(self, agent_type: AgentType) -> Task:
        """Create a task for the given agent type."""
        config = self.agent_configs[agent_type]
        return self.coordination.create_task(
            agent_type=agent_type.value,
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )

    def _execute_discovery(
        self,
        task: Task,
        topic: str,
        depth: str,
        sources: list[str] | None,
    ) -> dict[str, list[ResearchSource]]:
        """Execute discovery phase with coordination."""
        self.coordination.start_task(task)

        try:
            # Check circuit breaker
            should_proceed, error = self.coordination.circuit_breaker.should_proceed(task.agent_type)
            if not should_proceed:
                raise RuntimeError(error)

            # Execute discovery
            skill = self.skill_store.get_for_domain("general") or self.skill_store.get_by_name("general_research")
            active_sources = sources or (
                skill.preferred_sources if skill else ["arxiv", "github", "huggingface"]
            )
            max_per_source = (
                50 if depth == "deep"
                else 30 if depth == "standard"
                else 15
            )

            raw_results = self.discovery.discover(
                topic,
                sources=active_sources,
                max_per_source=max_per_source,
            )

            # Check for timeout
            if not self.coordination.check_and_enforce(task):
                raise RuntimeError(f"Task {task.id} killed by health check")

            self.coordination.complete_task(task)
            return raw_results

        except Exception as e:
            self.coordination.fail_task(task, str(e), FailureType.TRANSIENT)

            # Retry if needed
            if task.should_retry():
                self.coordination.retry_policy.wait_before_retry(task)
                return self._execute_discovery(task, topic, depth, sources)

            raise

    def _execute_analysis(
        self,
        task: Task,
        sources: list[ResearchSource],
    ) -> tuple[list[dict], list[dict]]:
        """Execute analysis phase with coordination."""
        self.coordination.start_task(task)

        try:
            should_proceed, error = self.coordination.circuit_breaker.should_proceed(task.agent_type)
            if not should_proceed:
                raise RuntimeError(error)

            papers, repos = self._analyze_sources(sources)

            if not self.coordination.check_and_enforce(task):
                raise RuntimeError(f"Task {task.id} killed by health check")

            self.coordination.complete_task(task)
            return papers, repos

        except Exception as e:
            self.coordination.fail_task(task, str(e), FailureType.TRANSIENT)

            if task.should_retry():
                self.coordination.retry_policy.wait_before_retry(task)
                return self._execute_analysis(task, sources)

            raise

    def _execute_synthesis(
        self,
        task: Task,
        topic: str,
        paper_analyses: list[dict],
        repo_analyses: list[dict],
        gaps: list[str],
    ) -> Any:
        """Execute synthesis phase with coordination."""
        self.coordination.start_task(task)

        try:
            should_proceed, error = self.coordination.circuit_breaker.should_proceed(task.agent_type)
            if not should_proceed:
                raise RuntimeError(error)

            synthesis = self.synthesizer.synthesize(
                topic=topic,
                paper_analyses=paper_analyses,
                repo_analyses=repo_analyses,
                gaps=gaps,
                contradictions=[],
            )

            if not self.coordination.check_and_enforce(task):
                raise RuntimeError(f"Task {task.id} killed by health check")

            self.coordination.complete_task(task)
            return synthesis

        except Exception as e:
            self.coordination.fail_task(task, str(e), FailureType.LOGIC)
            raise

    def _execute_report_generation(
        self,
        task: Task,
        topic: str,
        synthesis: Any,
        sources: list[dict],
        gaps: list[str],
        checklist: Any,
    ) -> ResearchReport:
        """Execute report generation with coordination."""
        self.coordination.start_task(task)

        try:
            should_proceed, error = self.coordination.circuit_breaker.should_proceed(task.agent_type)
            if not should_proceed:
                raise RuntimeError(error)

            report = self.report_gen.generate(
                topic=topic,
                synthesis=synthesis,
                sources=sources,
                gaps=gaps,
                contradictions=[],
                checklist_completion=checklist.completion_rate(),
            )

            if not self.coordination.check_and_enforce(task):
                raise RuntimeError(f"Task {task.id} killed by health check")

            self.coordination.complete_task(task)
            return report

        except Exception as e:
            self.coordination.fail_task(task, str(e), FailureType.LOGIC)
            raise

    # --- Private helpers ---

    def _clarify(self, topic: str, depth: str) -> tuple[str, str]:
        """Validate and normalize topic/depth."""
        topic = topic.strip()
        if not topic:
            raise ValueError("Topic cannot be empty")
        valid_depths = {"quick", "standard", "deep"}
        if depth not in valid_depths:
            depth = "standard"
        return topic, depth

    def _rank_and_deduplicate(
        self, sources: list[ResearchSource], query: str
    ) -> list[ResearchSource]:
        """Rank by quality score, deduplicate by URL."""
        seen_urls: set = set()
        unique: list[ResearchSource] = []
        for s in sources:
            if s.url not in seen_urls:
                seen_urls.add(s.url)
                unique.append(s)
        ranked = self.quality_scorer.rank(unique, query)
        return [s for s, _ in ranked]

    def _store_to_corpus(self, sources: list[ResearchSource]) -> list[CorpusEntry]:
        """Store sources to LocalCorpus."""
        entries: list[CorpusEntry] = []
        for s in sources:
            entry = CorpusEntry(
                id=s.id,
                source_id=s.id,
                title=s.title,
                url=s.url,
                abstract=s.abstract or "",
                full_text="",
                source_type=s.source_type.value,
                metadata=s.metadata,
            )
            self.corpus.store(entry)
            entries.append(entry)
        return entries

    def _analyze_sources(
        self, sources: list[ResearchSource]
    ) -> tuple[list[dict], list[dict]]:
        """Convert sources to paper/repo analysis dicts."""
        papers: list[dict] = []
        repos: list[dict] = []
        for s in sources:
            if s.source_type.value == "paper":
                papers.append(
                    {
                        "source_id": s.id,
                        "title": s.title,
                        "abstract": s.abstract,
                        "findings": [],
                        "venue": s.metadata.get("venue", ""),
                        "year": s.metadata.get("year", ""),
                        "citations": s.citations,
                    }
                )
            else:
                repos.append(
                    {
                        "source_id": s.id,
                        "title": s.title,
                        "description": s.abstract,
                        "stars": s.stars,
                        "language": s.metadata.get("language", ""),
                        "url": s.url,
                    }
                )
        return papers, repos

    def _source_to_dict(self, s: ResearchSource) -> dict:
        return {
            "source_id": s.id,
            "title": s.title,
            "url": s.url,
            "abstract": s.abstract,
        }

    def _memorize(
        self,
        topic: str,
        report: ResearchReport,
        sources: list[ResearchSource],
        quality: float,
        report_path: str,
    ) -> None:
        """Persist report findings to memory stores."""
        note = ResearchNote(
            topic=topic,
            title=f"Research: {topic}",
            content=report.executive_summary
            or f"Research on {topic}: {len(sources)} sources analyzed",
            source_ids=[s.url for s in sources[:5]],
            tags=topic.lower().split()[:5],
            note_type="finding",
            confidence=quality,
        )
        self.note_store.add(note)

        case = ResearchCase(
            topic=topic,
            report_path=report_path,
            report_summary=report.executive_summary or "",
            sources_found=len(sources),
            quality_score=quality,
            top_sources=[s.url for s in sources[:5]],
            key_findings=[],
        )
        self.case_bank.save_case(case)
