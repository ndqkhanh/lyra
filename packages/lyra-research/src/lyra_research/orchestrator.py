"""
ResearchOrchestrator — ties all research phases into a 10-step pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from lyra_research.discovery import MultiSourceDiscovery, ResearchSource
from lyra_research.sources import SourceQualityScorer
from lyra_research.intelligence import (
    VerifiableChecklistGenerator,
    GapAnalyzer,
    FalsificationChecker,
)
from lyra_research.memory import (
    ResearchNoteStore,
    LocalCorpus,
    ResearchStrategyMemory,
    SessionCaseBank,
    ResearchNote,
    ResearchCase,
    CorpusEntry,
)
from lyra_research.reporter import (
    CrossSourceSynthesizer,
    ResearchReportGenerator,
    ReportQualityChecker,
    ResearchReport,
)
from lyra_research.skills import ResearchSkillStore, StrategyAdaptationSkill


@dataclass
class ResearchProgress:
    """Tracks progress through the 10-step pipeline."""

    session_id: str
    topic: str
    current_step: int = 0        # 1-10
    current_step_name: str = ""
    sources_found: Dict[str, int] = field(default_factory=dict)  # {source_name: count}
    papers_analyzed: int = 0
    repos_analyzed: int = 0
    gaps_found: int = 0
    report: Optional[Any] = None  # ResearchReport when done
    error: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    @property
    def is_complete(self) -> bool:
        return self.current_step >= 10 and self.report is not None

    @property
    def elapsed_seconds(self) -> float:
        end = self.completed_at or datetime.now(timezone.utc)
        return (end - self.started_at).total_seconds()


ProgressCallback = Callable[[ResearchProgress], None]


class ResearchOrchestrator:
    """Ties all research phases together into the 10-step pipeline.

    Steps:
    1. CLARIFY   - validate topic and depth
    2. PLAN      - generate verifiable checklist
    3. SEARCH    - discover sources across all configured sources
    4. FILTER    - rank and deduplicate by quality score
    5. FETCH     - load source metadata into LocalCorpus
    6. ANALYZE   - extract paper/repo summaries
    7. EVIDENCE_AUDIT - verify claims vs sources
    8. SYNTHESIZE - build taxonomy and relationships
    9. REPORT    - generate full Markdown report
    10. MEMORIZE - persist notes, strategies, case to memory stores
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        note_store: Optional[ResearchNoteStore] = None,
        corpus: Optional[LocalCorpus] = None,
        strategy_memory: Optional[ResearchStrategyMemory] = None,
        case_bank: Optional[SessionCaseBank] = None,
    ) -> None:
        self.output_dir = output_dir or Path.home() / ".lyra" / "research_reports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Memory stores (injectable for testing)
        self.note_store = note_store or ResearchNoteStore()
        self.corpus = corpus or LocalCorpus()
        self.strategy_memory = strategy_memory or ResearchStrategyMemory()
        self.case_bank = case_bank or SessionCaseBank()

        # Pipeline components - read API keys from environment
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
        depth: str = "standard",   # "quick", "standard", "deep"
        sources: Optional[List[str]] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ResearchProgress:
        """Execute the full 10-step research pipeline.

        Args:
            topic: The research topic.
            depth: Research depth — "quick" (5 questions), "standard" (10),
                   "deep" (15).
            sources: Source names to search (default: all available).
            progress_callback: Called after each step with current progress.

        Returns:
            ResearchProgress with completed report or error set.
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
            # Step 1: Clarify
            _step(1, "Clarifying research scope")
            validated_topic, resolved_depth = self._clarify(topic, depth)

            # Step 2: Plan
            _step(2, "Generating research checklist")
            checklist = self.checklist_gen.generate(validated_topic, resolved_depth)

            # Step 3: Search
            _step(3, "Searching sources")
            skill = self.skill_store.get_for_domain("general") or self.skill_store.get_by_name("general_research")
            active_sources = sources or (
                skill.preferred_sources if skill else [
                    "arxiv",
                    "github",
                    "huggingface",
                ]
            )
            max_per_source = (
                50 if resolved_depth == "deep"
                else 30 if resolved_depth == "standard"
                else 15
            )
            raw_results = self.discovery.discover(
                validated_topic,
                sources=active_sources,
                max_per_source=max_per_source,
            )
            for src_name, src_list in raw_results.items():
                progress.sources_found[src_name] = len(src_list)
            all_sources_flat = [s for lst in raw_results.values() for s in lst]

            # Step 4: Filter & Rank
            _step(4, "Filtering and ranking sources")
            ranked = self._rank_and_deduplicate(all_sources_flat, validated_topic)
            top_n = 50 if resolved_depth == "deep" else 30 if resolved_depth == "standard" else 10
            ranked = ranked[:top_n]

            # Step 5: Fetch
            _step(5, "Fetching source metadata")
            self._store_to_corpus(ranked)
            progress.papers_analyzed = sum(
                1 for s in ranked if s.source_type.value == "paper"
            )
            progress.repos_analyzed = sum(
                1 for s in ranked if s.source_type.value == "repository"
            )

            # Step 6: Analyze
            _step(6, "Analyzing sources")
            paper_analyses, repo_analyses = self._analyze_sources(ranked)

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

            # Step 8: Synthesize
            _step(8, "Synthesizing findings")
            synthesis = self.synthesizer.synthesize(
                topic=validated_topic,
                paper_analyses=paper_analyses,
                repo_analyses=repo_analyses,
                gaps=gap_strings,
                contradictions=[],
            )

            # Step 9: Report
            _step(9, "Generating report")
            source_dicts = [self._source_to_dict(s) for s in ranked]
            report = self.report_gen.generate(
                topic=validated_topic,
                synthesis=synthesis,
                sources=source_dicts,
                gaps=gap_strings,
                contradictions=[],
                checklist_completion=checklist.completion_rate(),
            )
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

            # Step 10: Memorize
            _step(10, "Saving to memory")
            self._memorize(validated_topic, report, ranked, quality.overall_score, str(saved_path))

            progress.completed_at = datetime.now(timezone.utc)
            return progress

        except Exception as e:
            progress.error = str(e)
            progress.completed_at = datetime.now(timezone.utc)
            return progress

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
        self, sources: List[ResearchSource], query: str
    ) -> List[ResearchSource]:
        """Rank by quality score, deduplicate by URL."""
        seen_urls: set = set()
        unique: List[ResearchSource] = []
        for s in sources:
            if s.url not in seen_urls:
                seen_urls.add(s.url)
                unique.append(s)
        ranked = self.quality_scorer.rank(unique, query)
        return [s for s, _ in ranked]

    def _store_to_corpus(self, sources: List[ResearchSource]) -> List[CorpusEntry]:
        """Store sources to LocalCorpus. Skips duplicates."""
        entries: List[CorpusEntry] = []
        for s in sources:
            entry = CorpusEntry(
                id=s.id,
                source_id=s.id,
                title=s.title,
                url=s.url,
                abstract=s.abstract or "",  # Ensure non-None for NOT NULL constraint
                full_text="",
                source_type=s.source_type.value,
                metadata=s.metadata,
            )
            self.corpus.store(entry)
            entries.append(entry)
        return entries

    def _analyze_sources(
        self, sources: List[ResearchSource]
    ) -> tuple[List[Dict], List[Dict]]:
        """Convert sources to paper/repo analysis dicts."""
        papers: List[Dict] = []
        repos: List[Dict] = []
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

    def _source_to_dict(self, s: ResearchSource) -> Dict:
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
        sources: List[ResearchSource],
        quality: float,
        report_path: str,
    ) -> None:
        """Persist report findings to all memory stores."""
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
