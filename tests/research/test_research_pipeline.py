"""Comprehensive tests for DeepResearchPipeline — five-phase deep research pipeline."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lyra.research.pipeline import (
    Citation,
    DeepResearchPipeline,
    ResearchReport,
    SearchResult,
    SourceDomain,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_search_fn():
    return AsyncMock(return_value=[
        SearchResult(url="https://example.com/1", title="Result 1", snippet="Snippet 1"),
        SearchResult(url="https://example.com/2", title="Result 2", snippet="Snippet 2"),
    ])


@pytest.fixture
def mock_fetch_fn():
    async def fetch(url: str) -> str:
        return f"Fetched content from {url}"
    return fetch


@pytest.fixture
def mock_extract_fn():
    async def extract(text: str) -> list[str]:
        return [f"Observation from: {text[:30]}..."]
    return extract


@pytest.fixture
def mock_verify_fn():
    async def verify(claim: str, source_url: str) -> Citation:
        return Citation(claim=claim, source_url=source_url, source_snippet="verified")
    return verify


@pytest.fixture
def mock_llm_fn():
    return AsyncMock(return_value="sub-question A\nsub-question B\nsub-question C")


@pytest.fixture
def pipeline(mock_search_fn, mock_fetch_fn, mock_extract_fn, mock_verify_fn, mock_llm_fn):
    return DeepResearchPipeline(
        search_fn=mock_search_fn,
        fetch_fn=mock_fetch_fn,
        extract_fn=mock_extract_fn,
        verify_fn=mock_verify_fn,
        llm_fn=mock_llm_fn,
        max_concurrent_fetches=5,
        max_sub_queries=6,
    )


@pytest.fixture
def pipeline_no_llm(mock_search_fn, mock_fetch_fn, mock_extract_fn, mock_verify_fn):
    return DeepResearchPipeline(
        search_fn=mock_search_fn,
        fetch_fn=mock_fetch_fn,
        extract_fn=mock_extract_fn,
        verify_fn=mock_verify_fn,
        llm_fn=None,
        max_sub_queries=6,
    )


# =============================================================================
# Tests: Data types
# =============================================================================


class TestSearchResult:
    def test_minimal(self):
        sr = SearchResult(url="https://example.com", title="Test", snippet="Snippet")
        assert sr.url == "https://example.com"
        assert sr.domain == SourceDomain.WEB
        assert sr.relevance_score == 1.0

    def test_with_domain(self):
        sr = SearchResult(
            url="https://arxiv.org/abs/1234", title="Paper", snippet="Abstract",
            domain=SourceDomain.ACADEMIC, relevance_score=0.9,
        )
        assert sr.domain == SourceDomain.ACADEMIC
        assert sr.relevance_score == 0.9

    def test_immutable(self):
        sr = SearchResult(url="https://example.com", title="T", snippet="S")
        with pytest.raises(AttributeError):
            sr.url = "changed"


class TestCitation:
    def test_defaults(self):
        c = Citation(claim="claim", source_url="url", source_snippet="snippet")
        assert c.verified is True
        assert c.confidence == 1.0

    def test_unverified(self):
        c = Citation(claim="c", source_url="u", source_snippet="s", verified=False, confidence=0.3)
        assert c.verified is False
        assert c.confidence == 0.3


class TestResearchReport:
    def test_minimal(self):
        report = ResearchReport(query="test", report="report text", key_findings=["finding 1"])
        assert report.query == "test"
        assert report.key_findings == ["finding 1"]
        assert report.total_sources_consulted == 0
        assert report.duration_seconds == 0.0

    def test_created_at_set(self):
        report = ResearchReport(query="q", report="r")
        assert report.created_at is not None


# =============================================================================
# Tests: SourceDomain
# =============================================================================


class TestSourceDomain:
    def test_values(self):
        assert SourceDomain.WEB.value == "web"
        assert SourceDomain.CODE.value == "code"
        assert SourceDomain.DOCS.value == "docs"
        assert SourceDomain.ACADEMIC.value == "academic"


# =============================================================================
# Tests: Phase 1 — Query Analysis
# =============================================================================


class TestPhaseQueryAnalysis:
    async def test_with_llm_decomposes_query(self, pipeline):
        pipeline._llm_fn = AsyncMock(return_value="sub-q1\nsub-q2\nsub-q3")
        result = await pipeline._phase_query_analysis("original query")
        assert len(result) == 3
        assert "sub-q1" in result
        pipeline._llm_fn.assert_called_once()

    async def test_without_llm_returns_original(self, pipeline_no_llm):
        result = await pipeline_no_llm._phase_query_analysis("original query")
        assert result == ["original query"]

    async def test_empty_llm_response_falls_back(self, pipeline):
        pipeline._llm_fn = AsyncMock(return_value="")
        result = await pipeline._phase_query_analysis("fallback query")
        assert result == ["fallback query"]

    async def test_same_as_original_falls_back(self, pipeline):
        pipeline._llm_fn = AsyncMock(return_value="original query")
        result = await pipeline._phase_query_analysis("original query")
        assert result == ["original query"]

    async def test_respects_max_sub_queries(self, pipeline):
        pipeline._llm_fn = AsyncMock(return_value="q1\nq2\nq3\nq4\nq5\nq6\nq7\nq8")
        pipeline._max_sub_queries = 4
        result = await pipeline._phase_query_analysis("test")
        assert len(result) == 4

    async def test_strips_lines(self, pipeline):
        pipeline._llm_fn = AsyncMock(return_value="  q1  \n- q2\n- q3\n")
        result = await pipeline._phase_query_analysis("test")
        assert "q1" in result
        assert "q2" in result
        assert "q3" in result


# =============================================================================
# Tests: Phase 2 — Search
# =============================================================================


class TestPhaseSearch:
    async def test_with_search_fn(self, pipeline):
        pipeline._search_fn = AsyncMock(return_value=[
            SearchResult(url="https://a.com", title="A", snippet="Snippet A"),
        ])
        results = await pipeline._phase_search(["q1", "q2"], [SourceDomain.WEB])
        assert len(results) >= 1

    async def test_without_search_fn(self, pipeline):
        pipeline._search_fn = None
        results = await pipeline._phase_search(["q1"], [SourceDomain.WEB])
        assert results == []

    async def test_handles_exception_in_search(self, pipeline):
        pipeline._search_fn = AsyncMock(side_effect=ValueError("search failed"))
        results = await pipeline._phase_search(["q1"], [SourceDomain.WEB])
        assert results == []  # Exceptions are suppressed

    async def test_tags_domain(self, pipeline):
        pipeline._search_fn = AsyncMock(return_value=[
            SearchResult(url="https://x.com", title="X", snippet="X"),
        ])
        results = await pipeline._phase_search(["q"], [SourceDomain.CODE])
        assert len(results) > 0

    async def test_sync_search_fn(self, pipeline):
        def sync_search(query: str):
            return [SearchResult(url="https://sync.com", title="Sync", snippet="Sync")]
        pipeline._search_fn = sync_search
        results = await pipeline._phase_search(["test"], [SourceDomain.WEB])
        assert len(results) >= 1


class TestSearchDomain:
    async def test_async_search_fn(self, pipeline):
        pipeline._search_fn = AsyncMock(return_value=[MagicMock()])
        results = await pipeline._search_domain("query", SourceDomain.WEB)
        assert len(results) == 1

    async def test_sync_search_fn(self, pipeline):
        def sync_fn(q: str):
            return [MagicMock()]
        pipeline._search_fn = sync_fn
        results = await pipeline._search_domain("query", SourceDomain.WEB)
        assert len(results) == 1

    async def test_tags_domain_on_result(self, pipeline):
        pipeline._search_fn = AsyncMock(return_value=[
            SearchResult(url="https://x.com", title="X", snippet="Snippet"),
        ])
        results = await pipeline._search_domain("query", SourceDomain.ACADEMIC)
        assert all(r.domain == SourceDomain.ACADEMIC for r in results)


# =============================================================================
# Tests: Phase 3 — Read & Extract
# =============================================================================


class TestPhaseReadAndExtract:
    async def test_with_fns(self, pipeline):
        pipeline._fetch_fn = AsyncMock(return_value="page content")
        pipeline._extract_fn = AsyncMock(return_value=["obs1", "obs2"])
        results = await pipeline._phase_read_and_extract([
            SearchResult(url="https://a.com", title="A", snippet="Snippet"),
        ])
        assert results == ["obs1", "obs2"]

    async def test_without_fetch_fn(self, pipeline):
        pipeline._fetch_fn = None
        results = await pipeline._phase_read_and_extract([
            SearchResult(url="https://a.com", title="A", snippet="Snippet"),
        ])
        assert results == []

    async def test_without_extract_fn(self, pipeline):
        pipeline._fetch_fn = AsyncMock(return_value="content")
        pipeline._extract_fn = None
        results = await pipeline._phase_read_and_extract([
            SearchResult(url="https://a.com", title="A", snippet="Snippet"),
        ])
        assert results == []

    async def test_fetch_failure(self, pipeline):
        pipeline._fetch_fn = AsyncMock(side_effect=ConnectionError("timeout"))
        pipeline._extract_fn = AsyncMock(return_value=["obs"])
        results = await pipeline._phase_read_and_extract([
            SearchResult(url="https://fail.com", title="Fail", snippet="Snippet"),
        ])
        assert results == []  # Fetch failure should be caught
        pipeline._extract_fn.assert_not_called()

    async def test_extract_failure(self, pipeline):
        pipeline._fetch_fn = AsyncMock(return_value="content")
        pipeline._extract_fn = AsyncMock(side_effect=ValueError("parse error"))
        results = await pipeline._phase_read_and_extract([
            SearchResult(url="https://fail2.com", title="Fail2", snippet="Snippet"),
        ])
        assert results == []

    async def test_sync_fetch_fn(self, pipeline):
        def sync_fetch(url: str) -> str:
            return "sync content"
        pipeline._fetch_fn = sync_fetch
        pipeline._extract_fn = AsyncMock(return_value=["obs"])
        results = await pipeline._phase_read_and_extract([
            SearchResult(url="https://sync.com", title="Sync", snippet="Snippet"),
        ])
        assert results == ["obs"]


# =============================================================================
# Tests: Phase 4 — Synthesize
# =============================================================================


class TestPhaseSynthesize:
    async def test_no_observations(self, pipeline):
        report = await pipeline._phase_synthesize("query", [])
        assert report.report_text == "Research query: query"
        assert report.step_count == 0

    async def test_with_observations_and_llm(self, pipeline):
        pipeline._llm_synthesize = AsyncMock(return_value="compressed report")
        report = await pipeline._phase_synthesize("query", ["obs1", "obs2", "obs3"])
        assert report.step_count > 0
        assert "compressed" in report.report_text or "Research query" in report.report_text

    async def test_without_llm(self, pipeline_no_llm):
        report = await pipeline_no_llm._phase_synthesize("query", ["obs1", "obs2", "obs3"])
        assert report.step_count > 0
        assert report.report_text is not None


class TestLLMSynthesize:
    async def test_calls_llm(self, pipeline):
        pipeline._llm_fn = AsyncMock(return_value="synthesized text")
        result = await pipeline._llm_synthesize("current", "obs", "outcome", ["kf1"], 2)
        assert result == "synthesized text"
        pipeline._llm_fn.assert_called_once()


# =============================================================================
# Tests: Phase 5 — Citation Verification
# =============================================================================


class TestPhaseVerifyCitations:
    async def test_with_verify_fn(self, pipeline):
        pipeline._verify_fn = AsyncMock(return_value=Citation(
            claim="observation", source_url="https://a.com",
            source_snippet="snippet", verified=True, confidence=0.9,
        ))
        citations = await pipeline._phase_verify_citations(
            ["observation"],
            [SearchResult(url="https://a.com", title="A", snippet="Snippet")],
        )
        assert len(citations) == 1
        assert citations[0].claim == "observation"
        assert citations[0].verified is True

    async def test_without_verify_fn(self, pipeline):
        pipeline._verify_fn = None
        citations = await pipeline._phase_verify_citations(
            ["obs1", "obs2"],
            [SearchResult(url="https://a.com", title="A", snippet="Snippet")],
        )
        assert len(citations) == 2
        assert citations[0].verified is False
        assert citations[0].confidence == 0.5

    async def test_no_observations(self, pipeline):
        citations = await pipeline._phase_verify_citations([], [MagicMock()])
        assert citations == []

    async def test_verify_failure(self, pipeline):
        pipeline._verify_fn = AsyncMock(side_effect=ValueError("verify failed"))
        citations = await pipeline._phase_verify_citations(
            ["obs1"],
            [SearchResult(url="https://a.com", title="A", snippet="Snippet")],
        )
        assert len(citations) == 1
        assert citations[0].verified is False
        assert citations[0].confidence == 0.0

    async def test_no_search_results(self, pipeline):
        pipeline._verify_fn = AsyncMock(return_value=Citation(
            claim="c", source_url="", source_snippet="", verified=True,
        ))
        citations = await pipeline._phase_verify_citations(["obs1"], [])
        assert len(citations) == 1
        assert citations[0].source_url == ""

    async def test_more_obs_than_results(self, pipeline):
        pipeline._verify_fn = AsyncMock(return_value=Citation(
            claim="c", source_url="u", source_snippet="s", verified=True,
        ))
        citations = await pipeline._phase_verify_citations(
            ["o1", "o2", "o3"],
            [SearchResult(url="https://a.com", title="A", snippet="Snippet")],
        )
        assert len(citations) == 3  # Wraps around

    async def test_sync_verify_fn(self, pipeline):
        def sync_verify(claim: str, source_url: str) -> Citation:
            return Citation(claim=claim, source_url=source_url, source_snippet="sync")
        pipeline._verify_fn = sync_verify
        citations = await pipeline._phase_verify_citations(
            ["obs1"],
            [SearchResult(url="https://sync.com", title="Sync", snippet="Snippet")],
        )
        assert len(citations) == 1


# =============================================================================
# Tests: Domain inference
# =============================================================================


class TestInferDomains:
    def test_always_includes_web(self):
        domains = DeepResearchPipeline._infer_domains("hello world", [])
        assert SourceDomain.WEB in domains

    def test_code_keywords(self):
        domains = DeepResearchPipeline._infer_domains(
            "how to implement an API in Python", ["sub q"],
        )
        assert SourceDomain.CODE in domains

    def test_docs_keywords(self):
        domains = DeepResearchPipeline._infer_domains(
            "documentation for the SDK", ["sub q"],
        )
        assert SourceDomain.DOCS in domains

    def test_academic_keywords(self):
        domains = DeepResearchPipeline._infer_domains(
            "latest research on attention mechanisms", ["sub q"],
        )
        assert SourceDomain.ACADEMIC in domains

    def test_multiple_domains(self):
        domains = DeepResearchPipeline._infer_domains(
            "research paper and code for API implementation", ["sub q"],
        )
        assert SourceDomain.WEB in domains
        assert SourceDomain.CODE in domains
        assert SourceDomain.ACADEMIC in domains

    def test_no_extra_domains(self):
        domains = DeepResearchPipeline._infer_domains(
            "hello world", ["foo bar"],
        )
        assert domains == [SourceDomain.WEB]


# =============================================================================
# Tests: Full pipeline
# =============================================================================


class TestFullPipeline:
    async def test_run_returns_report(self, pipeline):
        report = await pipeline.run("test query", metadata={"source": "test"})
        assert isinstance(report, ResearchReport)
        assert report.query == "test query"
        assert report.metadata.get("source") == "test"
        assert report.duration_seconds >= 0
        assert report.sub_query_breakdown > 0

    async def test_run_includes_citations(self, pipeline):
        report = await pipeline.run("test")
        assert hasattr(report, "citations")

    async def test_run_without_metadata(self, pipeline):
        report = await pipeline.run("test")
        assert report.metadata == {}

    async def test_run_no_providers(self):
        pipe = DeepResearchPipeline()
        report = await pipe.run("test")
        assert isinstance(report, ResearchReport)
        assert report.total_sources_consulted == 0

    async def test_run_with_sync_providers(self):
        def search_fn(q: str):
            return [SearchResult(url="https://sync.com", title="Sync", snippet="Sync")]

        def fetch_fn(url: str) -> str:
            return "sync content"

        def extract_fn(text: str) -> list[str]:
            return ["sync observation"]

        def verify_fn(claim: str, source_url: str) -> Citation:
            return Citation(claim=claim, source_url=source_url, source_snippet="sync")

        pipe = DeepResearchPipeline(
            search_fn=search_fn,
            fetch_fn=fetch_fn,
            extract_fn=extract_fn,
            verify_fn=verify_fn,
        )
        report = await pipe.run("test")
        assert isinstance(report, ResearchReport)

    async def test_run_with_partial_providers(self):
        """Only search and fetch, no LLM, no verify."""
        def search_fn(q: str):
            return [SearchResult(url="https://x.com", title="X", snippet="X")]

        def fetch_fn(url: str) -> str:
            return "fetched"

        pipe = DeepResearchPipeline(
            search_fn=search_fn,
            fetch_fn=fetch_fn,
        )
        report = await pipe.run("test")
        assert isinstance(report, ResearchReport)
        assert report.report is not None


# =============================================================================
# Tests: LLM helper
# =============================================================================


class TestCallLLM:
    async def test_async_llm(self, pipeline):
        pipeline._llm_fn = AsyncMock(return_value="result")
        result = await pipeline._call_llm("prompt")
        assert result == "result"

    async def test_sync_llm(self, pipeline):
        def sync_llm(prompt: str) -> str:
            return "sync result"
        pipeline._llm_fn = sync_llm
        result = await pipeline._call_llm("prompt")
        assert result == "sync result"

    async def test_no_llm_raises(self, pipeline_no_llm):
        with pytest.raises(RuntimeError, match="No llm_fn configured"):
            await pipeline_no_llm._call_llm("prompt")


# =============================================================================
# Tests: Run method metadata edge cases
# =============================================================================


class TestRunMetadata:
    async def test_run_passes_metadata(self, pipeline):
        report = await pipeline.run("test", metadata={"user_id": "abc"})
        assert report.metadata.get("user_id") == "abc"
        assert report.sub_query_breakdown > 0

    async def test_run_with_no_search_fn(self):
        """Pipeline with just an LLM but no search yields empty results."""
        pipe = DeepResearchPipeline(
            llm_fn=AsyncMock(return_value="sub\nqueries"),
        )
        report = await pipe.run("test query")
        assert isinstance(report, ResearchReport)
        assert report.total_sources_consulted == 0

    async def test_run_handles_empty_observations(self):
        """When fetch produces nothing, pipeline still produces a report."""
        pipe = DeepResearchPipeline(
            search_fn=AsyncMock(return_value=[
                SearchResult(url="https://x.com", title="X", snippet="X"),
            ]),
            fetch_fn=AsyncMock(side_effect=ConnectionError("fail")),
            extract_fn=AsyncMock(return_value=["obs"]),
            llm_fn=AsyncMock(return_value="sub"),
        )
        report = await pipe.run("test")
        assert isinstance(report, ResearchReport)
        assert report.citations == []

    async def test_run_no_fetch_fn(self):
        pipe = DeepResearchPipeline(
            search_fn=AsyncMock(return_value=[
                SearchResult(url="https://x.com", title="X", snippet="X"),
            ]),
            llm_fn=AsyncMock(return_value="sub"),
        )
        report = await pipe.run("test")
        assert isinstance(report, ResearchReport)


# =============================================================================
# Tests: Phase synthesize with LLM
# =============================================================================


class TestPhaseSynthesizeExtended:
    async def test_synthesize_with_llm_batches_observations(self, pipeline):
        pipeline._llm_fn = AsyncMock(return_value="compressed")
        report = await pipeline._phase_synthesize(
            "query",
            ["obs1", "obs2", "obs3", "obs4", "obs5"],
        )
        pipeline._llm_fn.assert_called()
        assert report.step_count > 0


# =============================================================================
# Tests: ResearchReport edge cases
# =============================================================================


class TestResearchReportExtended:
    def test_default_citations_empty(self):
        report = ResearchReport(query="q", report="r")
        assert report.citations == []
        assert report.total_citations == 0

    def test_default_sub_query_breakdown(self):
        report = ResearchReport(query="q", report="r")
        assert report.sub_query_breakdown == 0

    def test_default_duration(self):
        report = ResearchReport(query="q", report="r")
        assert report.duration_seconds == 0.0

    def test_with_full_data(self):
        report = ResearchReport(
            query="test query",
            report="# Report",
            key_findings=["finding 1"],
            citations=[
                Citation(claim="c1", source_url="u1", source_snippet="s1"),
            ],
            total_sources_consulted=5,
            total_citations=1,
            duration_seconds=12.34,
            sub_query_breakdown=3,
            metadata={"env": "test"},
        )
        assert report.total_sources_consulted == 5
        assert report.duration_seconds == 12.34
        assert report.sub_query_breakdown == 3
        assert report.total_citations == 1


# =============================================================================
# Tests: Domain inference edge cases
# =============================================================================


class TestInferDomainsExtended:
    def test_code_keywords_in_sub_queries(self):
        domains = DeepResearchPipeline._infer_domains(
            "hello world", ["how to implement this API"],
        )
        assert SourceDomain.CODE in domains

    def test_docs_keywords_in_sub_queries(self):
        domains = DeepResearchPipeline._infer_domains(
            "simple question", ["check the documentation"],
        )
        assert SourceDomain.DOCS in domains

    def test_academic_keywords_in_sub_queries(self):
        domains = DeepResearchPipeline._infer_domains(
            "simple question", ["check this research paper"],
        )
        assert SourceDomain.ACADEMIC in domains

    def test_code_api_keyword(self):
        domains = DeepResearchPipeline._infer_domains(
            "how to use the API", ["sub"],
        )
        assert SourceDomain.CODE in domains

    def test_github_keyword(self):
        domains = DeepResearchPipeline._infer_domains(
            "is there a repository for X", ["sub"],
        )
        assert SourceDomain.CODE in domains
