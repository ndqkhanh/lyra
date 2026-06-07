"""
Tests for Deep Research Pipeline (P6).

Covers:
- Full pipeline run with all five phases
- Query analysis with and without llm_fn
- Parallel search through multiple domains (web, code, docs, academic)
- Read-and-extract with concurrency limiting
- S4 workspace report synthesis (token savings)
- Citation verification with verify_fn and without
- Empty / edge cases (no results, no providers)
- Domain inference from query keywords
"""

import pytest

from lyra.context.compaction import CompactionStrategy
from lyra.context.workspace_report import WorkspaceReport
from lyra.research.pipeline import (
    Citation,
    DeepResearchPipeline,
    ResearchReport,
    SearchResult,
    SourceDomain,
)


# ---------------------------------------------------------------------------
# Test provider factories
# ---------------------------------------------------------------------------


def _make_search_fn(results: list[SearchResult] | None = None):
    """Return a search provider that returns the given results."""
    _results = results or [
        SearchResult(
            url="https://example.com/1",
            title="Test Result 1",
            snippet="This is a test snippet about AI.",
            domain=SourceDomain.WEB,
        ),
        SearchResult(
            url="https://example.com/2",
            title="Test Code",
            snippet="def foo(): pass",
            domain=SourceDomain.CODE,
        ),
    ]

    def fn(query: str) -> list[SearchResult]:
        return _results

    return fn


async def _async_search_fn(query: str) -> list[SearchResult]:
    """Async version of the search provider."""
    return [
        SearchResult(
            url="https://async.example.com/1",
            title="Async Result",
            snippet="Async search result",
            domain=SourceDomain.WEB,
        ),
    ]


def _make_fetch_fn(text: str | None = None):
    """Return a fetch provider that returns the given text."""
    _text = text or "<html><body>Research content about AI safety.</body></html>"

    def fn(url: str) -> str:
        return _text

    return fn


def _make_extract_fn(observations: list[str] | None = None):
    """Return an extract provider that returns the given observations."""
    _obs = observations or [
        "AI safety is a critical research area.",
        "Alignment research focuses on value learning.",
    ]

    def fn(text: str) -> list[str]:
        return _obs

    return fn


def _make_verify_fn(passed: bool = True):
    """Return a verify provider."""

    def fn(claim: str, source_url: str) -> Citation:
        return Citation(
            claim=claim,
            source_url=source_url,
            source_snippet="",
            verified=passed,
            confidence=0.95 if passed else 0.3,
        )

    return fn


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSearchResult:
    """Verify SearchResult dataclass."""

    def test_default_domain(self):
        sr = SearchResult(url="https://x.com", title="X", snippet="x")
        assert sr.domain == SourceDomain.WEB

    def test_relevance_score_default(self):
        sr = SearchResult(url="https://x.com", title="X", snippet="x")
        assert sr.relevance_score == 1.0


class TestCitation:
    """Verify Citation dataclass."""

    def test_defaults(self):
        c = Citation(claim="c", source_url="u", source_snippet="s")
        assert c.verified is True
        assert c.confidence == 1.0

    def test_unverified(self):
        c = Citation(claim="c", source_url="u", source_snippet="s", verified=False, confidence=0.0)
        assert c.verified is False
        assert c.confidence == 0.0


class TestResearchReport:
    """Verify ResearchReport creation."""

    def test_minimal_report(self):
        report = ResearchReport(query="test", report="content")
        assert report.query == "test"
        assert report.report == "content"
        assert report.key_findings == []
        assert report.citations == []

    def test_full_report(self):
        report = ResearchReport(
            query="test query",
            report="## Findings\n...",
            key_findings=["Finding 1", "Finding 2"],
            citations=[Citation(claim="c", source_url="u", source_snippet="s")],
            total_sources_consulted=5,
            total_citations=1,
            duration_seconds=3.14,
            sub_query_breakdown=3,
        )
        assert report.query == "test query"
        assert len(report.key_findings) == 2
        assert report.total_sources_consulted == 5
        assert report.duration_seconds == 3.14


class TestDeepResearchPipelineFull:
    """Full five-phase pipeline integration test."""

    @pytest.mark.asyncio
    async def test_full_pipeline_with_all_providers(self):
        """Run the complete pipeline with all providers configured."""
        pipeline = DeepResearchPipeline(
            search_fn=_make_search_fn(),
            fetch_fn=_make_fetch_fn(),
            extract_fn=_make_extract_fn(),
            verify_fn=_make_verify_fn(),
        )
        report = await pipeline.run("What is AI safety?")

        assert isinstance(report, ResearchReport)
        assert "AI safety" in report.query or "AI" in report.query
        assert report.total_sources_consulted > 0
        assert report.sub_query_breakdown >= 1  # at least the original query
        assert report.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_pipeline_with_llm_fn(self):
        """Run pipeline with an LLM provider for query analysis."""

        async def llm_fn(prompt: str) -> str:
            return "Sub-question 1\nSub-question 2\nSub-question 3"

        pipeline = DeepResearchPipeline(
            search_fn=_make_search_fn(),
            fetch_fn=_make_fetch_fn(),
            extract_fn=_make_extract_fn(),
            verify_fn=_make_verify_fn(),
            llm_fn=llm_fn,
        )
        report = await pipeline.run("What is AI safety?")

        assert report.sub_query_breakdown == 3
        assert report.total_sources_consulted > 0
        assert len(report.report) > 0

    @pytest.mark.asyncio
    async def test_pipeline_with_async_search(self):
        """Pipeline should work with async search providers."""
        pipeline = DeepResearchPipeline(
            search_fn=_async_search_fn,
            fetch_fn=_make_fetch_fn(),
            extract_fn=_make_extract_fn(),
            verify_fn=_make_verify_fn(),
        )
        report = await pipeline.run("Async search test")

        assert report.total_sources_consulted > 0
        assert isinstance(report, ResearchReport)


class TestPhase1QueryAnalysis:
    """Phase 1: query analysis / decomposition."""

    @pytest.mark.asyncio
    async def test_without_llm_returns_single_query(self):
        """Without llm_fn, the original query is the sole sub-query."""
        pipeline = DeepResearchPipeline()
        sub_queries = await pipeline._phase_query_analysis("Just a factoid")

        assert sub_queries == ["Just a factoid"]
        assert len(sub_queries) == 1

    @pytest.mark.asyncio
    async def test_with_llm_decomposes(self):
        """With llm_fn, the query is decomposed into sub-queries."""

        async def llm_fn(prompt: str) -> str:
            return "Sub A\nSub B\nSub C"

        pipeline = DeepResearchPipeline(llm_fn=llm_fn)
        sub_queries = await pipeline._phase_query_analysis("Complex research topic")

        assert len(sub_queries) == 3
        assert sub_queries == ["Sub A", "Sub B", "Sub C"]

    @pytest.mark.asyncio
    async def test_llm_capped_at_max_sub_queries(self):
        """Decomposition should be capped by max_sub_queries."""

        async def llm_fn(prompt: str) -> str:
            return "\n".join([f"Sub {i}" for i in range(10)])

        pipeline = DeepResearchPipeline(llm_fn=llm_fn, max_sub_queries=4)
        sub_queries = await pipeline._phase_query_analysis("Big topic")

        assert len(sub_queries) <= 4


class TestDomainInference:
    """Domain inference heuristics."""

    def test_web_only_by_default(self):
        """A plain query should only target WEB."""
        domains = DeepResearchPipeline._infer_domains("What is the weather?", [])
        assert SourceDomain.WEB in domains
        assert SourceDomain.CODE not in domains
        assert SourceDomain.DOCS not in domains

    def test_code_keyword_adds_code_domain(self):
        domains = DeepResearchPipeline._infer_domains(
            "Best API for code generation in Python", []
        )
        assert SourceDomain.CODE in domains

    def test_docs_keyword_adds_docs_domain(self):
        domains = DeepResearchPipeline._infer_domains(
            "How to use the Anthropic SDK documentation", []
        )
        assert SourceDomain.DOCS in domains

    def test_academic_keyword_adds_academic_domain(self):
        domains = DeepResearchPipeline._infer_domains(
            "Recent research papers on AI alignment", []
        )
        assert SourceDomain.ACADEMIC in domains

    def test_all_keywords_all_domains(self):
        domains = DeepResearchPipeline._infer_domains(
            "Research paper on code generation API documentation", []
        )
        assert SourceDomain.WEB in domains
        assert SourceDomain.CODE in domains
        assert SourceDomain.DOCS in domains
        assert SourceDomain.ACADEMIC in domains


class TestPhase2ParallelSearch:
    """Phase 2: parallel search."""

    @pytest.mark.asyncio
    async def test_empty_without_search_fn(self):
        """Without search_fn, phase 2 should return empty."""
        pipeline = DeepResearchPipeline()
        results = await pipeline._phase_search(["test query"], [SourceDomain.WEB])
        assert results == []

    @pytest.mark.asyncio
    async def test_fan_out_multiple_domains(self):
        """1 sub-query x 2 domains = 2 search calls."""
        call_count = 0

        def search_fn(query: str) -> list[SearchResult]:
            nonlocal call_count
            call_count += 1
            return [SearchResult(url=f"https://ex.com/{call_count}", title=f"R{call_count}", snippet="x")]

        pipeline = DeepResearchPipeline(search_fn=search_fn)
        results = await pipeline._phase_search(
            ["test"], [SourceDomain.WEB, SourceDomain.CODE]
        )

        assert call_count == 2  # 1 query * 2 domains
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_domain_tags_results(self):
        """Results should be tagged with their source domain."""

        def search_fn(query: str) -> list[SearchResult]:
            return [SearchResult(url="https://ex.com", title="R", snippet="x")]

        pipeline = DeepResearchPipeline(search_fn=search_fn)
        results = await pipeline._search_domain("test", SourceDomain.CODE)

        assert len(results) == 1
        assert results[0].domain == SourceDomain.CODE


class TestPhase3ReadAndExtract:
    """Phase 3: read and extract."""

    @pytest.mark.asyncio
    async def test_empty_without_fetch_fn(self):
        """Without fetch_fn, phase 3 should return empty observations."""
        pipeline = DeepResearchPipeline(extract_fn=_make_extract_fn())
        obs = await pipeline._phase_read_and_extract(
            [SearchResult(url="https://ex.com", title="T", snippet="S")]
        )
        assert obs == []

    @pytest.mark.asyncio
    async def test_empty_without_extract_fn(self):
        """Without extract_fn, phase 3 should return empty observations."""
        pipeline = DeepResearchPipeline(fetch_fn=_make_fetch_fn())
        obs = await pipeline._phase_read_and_extract(
            [SearchResult(url="https://ex.com", title="T", snippet="S")]
        )
        assert obs == []

    @pytest.mark.asyncio
    async def test_fetch_and_extract(self):
        """Fetch + extract should return extracted observations."""
        pipeline = DeepResearchPipeline(
            fetch_fn=_make_fetch_fn(),
            extract_fn=_make_extract_fn(["obs A", "obs B"]),
        )
        obs = await pipeline._phase_read_and_extract(
            [SearchResult(url="https://ex.com/1", title="T1", snippet="S1")]
        )
        assert obs == ["obs A", "obs B"]

    @pytest.mark.asyncio
    async def test_fetch_error_returns_empty_for_that_url(self):
        """A fetch failure for one URL should not break others."""

        def fetch_fn(url: str) -> str:
            if "fail" in url:
                raise RuntimeError("Fetch failed")
            return "content"

        def extract_fn(text: str) -> list[str]:
            return ["obs"]

        pipeline = DeepResearchPipeline(
            fetch_fn=fetch_fn, extract_fn=extract_fn,
        )
        results = [
            SearchResult(url="https://ex.com/fail", title="F", snippet="fail"),
            SearchResult(url="https://ex.com/ok", title="OK", snippet="ok"),
        ]
        obs = await pipeline._phase_read_and_extract(results)

        assert len(obs) == 1  # only the successful one


class TestPhase4Synthesize:
    """Phase 4: S4 workspace report synthesis."""

    @pytest.mark.asyncio
    async def test_empty_observations_returns_minimal_report(self):
        pipeline = DeepResearchPipeline()
        report = await pipeline._phase_synthesize("Test query", [])
        assert report.step_count == 0
        assert report.report_text == "Research query: Test query"

    @pytest.mark.asyncio
    async def test_observations_produce_report_updates(self):
        pipeline = DeepResearchPipeline()
        report = await pipeline._phase_synthesize(
            "Test query",
            ["obs A", "obs B", "obs C", "obs D"],
        )
        # Without an LLM, fallback creates one update per batch.
        # 4 observations / batch_size (max(1, 4//3) = 1) => 4 batches
        assert report.step_count > 0
        assert len(report.report_text) > 0

    @pytest.mark.asyncio
    async def test_with_llm_synthesizer(self):
        """With an LLM provider, synthesis should compress observations."""

        async def llm_fn(prompt: str) -> str:
            return "WORKSPACE_REPORT:\nCompressed content\nKEY_FINDINGS:\n- Finding A\n- Finding B"

        pipeline = DeepResearchPipeline(llm_fn=llm_fn)
        report = await pipeline._phase_synthesize(
            "Test", ["Long observation " * 50],
        )

        assert report.step_count > 0
        # The compressed output should be shorter than the raw observation.
        assert len(report.report_text) < len("Long observation " * 50)


class TestPhase5CitationVerification:
    """Phase 5: citation verification."""

    @pytest.mark.asyncio
    async def test_empty_observations_returns_empty_citations(self):
        pipeline = DeepResearchPipeline()
        citations = await pipeline._phase_verify_citations([], [])
        assert citations == []

    @pytest.mark.asyncio
    async def test_without_verify_fn_returns_unverified(self):
        pipeline = DeepResearchPipeline()
        citations = await pipeline._phase_verify_citations(
            ["Claim 1", "Claim 2"],
            [SearchResult(url="https://ex.com", title="T", snippet="snippet")],
        )

        assert len(citations) == 2
        assert citations[0].verified is False
        assert citations[0].confidence == 0.5

    @pytest.mark.asyncio
    async def test_with_verify_fn_verifies(self):
        pipeline = DeepResearchPipeline(verify_fn=_make_verify_fn(passed=True))
        citations = await pipeline._phase_verify_citations(
            ["Claim about AI safety"],
            [SearchResult(url="https://ex.com", title="T", snippet="snippet")],
        )

        assert len(citations) == 1
        assert citations[0].verified is True
        assert citations[0].confidence == 0.95

    @pytest.mark.asyncio
    async def test_with_verify_fn_refutes(self):
        pipeline = DeepResearchPipeline(verify_fn=_make_verify_fn(passed=False))
        citations = await pipeline._phase_verify_citations(
            ["False claim"],
            [SearchResult(url="https://ex.com", title="T", snippet="snippet")],
        )

        assert len(citations) == 1
        assert citations[0].verified is False
        assert citations[0].confidence == 0.3

    @pytest.mark.asyncio
    async def test_observation_source_mapping_cycles(self):
        """More observations than search results should cycle through sources."""
        pipeline = DeepResearchPipeline()
        citations = await pipeline._phase_verify_citations(
            ["A", "B", "C"],
            [
                SearchResult(url="https://ex.com/1", title="T1", snippet="S1"),
                SearchResult(url="https://ex.com/2", title="T2", snippet="S2"),
            ],
        )

        assert len(citations) == 3
        assert citations[0].source_url == "https://ex.com/1"
        assert citations[1].source_url == "https://ex.com/2"
        assert citations[2].source_url == "https://ex.com/1"  # cycles back


class TestEdgeCases:
    """Edge-case scenarios."""

    @pytest.mark.asyncio
    async def test_no_providers_returns_minimal_report(self):
        """With no providers configured, the pipeline should return a minimal report."""
        pipeline = DeepResearchPipeline()
        report = await pipeline.run("Empty pipeline test")

        assert isinstance(report, ResearchReport)
        assert report.total_sources_consulted == 0
        assert report.sub_query_breakdown == 1
        assert len(report.report) > 0

    @pytest.mark.asyncio
    async def test_search_exception_does_not_crash(self):
        """A search provider that throws should not crash the pipeline."""

        def search_fn(query: str) -> list[SearchResult]:
            raise RuntimeError("Search API unreachable")

        pipeline = DeepResearchPipeline(search_fn=search_fn)
        report = await pipeline.run("Failing search")

        assert isinstance(report, ResearchReport)
        assert report.total_sources_consulted == 0

    @pytest.mark.asyncio
    async def test_large_number_of_sub_queries(self):
        """max_sub_queries should cap the decomposition."""

        async def llm_fn(prompt: str) -> str:
            return "\n".join([f"Sub-query {i}" for i in range(20)])

        pipeline = DeepResearchPipeline(
            llm_fn=llm_fn,
            search_fn=_make_search_fn(),
            fetch_fn=_make_fetch_fn(),
            extract_fn=_make_extract_fn(),
            max_sub_queries=6,
        )
        report = await pipeline.run("Large topic")

        assert report.sub_query_breakdown <= 6
