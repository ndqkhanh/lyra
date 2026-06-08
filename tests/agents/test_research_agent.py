"""
Tests for ResearchAgent — web search, document analysis, and research synthesis.
"""

import pytest

from lyra.agents.research_agent import ResearchAgent
from lyra.core.task import Task, TaskType


class TestResearchAgentInit:

    def test_default_id(self):
        agent = ResearchAgent()
        assert agent.agent_id == "research_agent"

    def test_two_capabilities(self):
        agent = ResearchAgent()
        assert len(agent.capabilities) == 2
        names = {c.name for c in agent.capabilities}
        assert names == {"web_search", "document_analysis"}

    def test_custom_id(self):
        agent = ResearchAgent(agent_id="my-researcher")
        assert agent.agent_id == "my-researcher"


class TestResearchAgentCanHandle:

    def test_research_task(self):
        agent = ResearchAgent()
        task = Task(type=TaskType.RESEARCH, description="research")
        assert agent.can_handle(task) > 0.0

    def test_web_search_task(self):
        agent = ResearchAgent()
        task = Task(type=TaskType.WEB_SEARCH, description="search")
        assert agent.can_handle(task) > 0.0

    def test_document_analysis_task(self):
        agent = ResearchAgent()
        task = Task(type=TaskType.DOCUMENT_ANALYSIS, description="doc")
        assert agent.can_handle(task) > 0.0

    def test_unhandled_task(self):
        agent = ResearchAgent()
        task = Task(type=TaskType.CODE_GENERATION, description="code")
        assert agent.can_handle(task) == 0.0


class TestResearchAgentExecute:

    @pytest.mark.asyncio
    async def test_execute_research(self):
        agent = ResearchAgent()
        task = Task(
            type=TaskType.RESEARCH,
            description="Research AI safety",
            params={"query": "AI safety 2026"},
        )
        result = await agent.execute(task)
        assert result.success
        assert result.agent_id == "research_agent"
        data = result.data
        assert data["query"] == "AI safety 2026"
        assert data["sources_found"] == 3
        assert data["sources_analyzed"] == 3
        assert "findings" in data
        assert data["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_execute_web_search(self):
        agent = ResearchAgent()
        task = Task(
            type=TaskType.WEB_SEARCH,
            description="Web search",
            params={"query": "Python 3.13 features"},
        )
        result = await agent.execute(task)
        assert result.success
        data = result.data
        assert data["query"] == "Python 3.13 features"
        assert len(data["findings"]["key_insights"]) == 3

    @pytest.mark.asyncio
    async def test_execute_document_analysis(self):
        agent = ResearchAgent()
        task = Task(
            type=TaskType.DOCUMENT_ANALYSIS,
            description="Analyze doc",
            params={"document_path": "docs/report.pdf"},
        )
        result = await agent.execute(task)
        assert result.success
        data = result.data
        assert data["document"] == "docs/report.pdf"
        assert len(data["key_points"]) == 3
        assert data["word_count"] == 1500

    @pytest.mark.asyncio
    async def test_execute_research_without_query_falls_back_to_description(self):
        agent = ResearchAgent()
        task = Task(
            type=TaskType.RESEARCH,
            description="Quantum computing advances",
        )
        result = await agent.execute(task)
        assert result.success
        assert "Quantum computing" in result.data["query"]

    @pytest.mark.asyncio
    async def test_execute_document_analysis_default_path(self):
        agent = ResearchAgent()
        task = Task(
            type=TaskType.DOCUMENT_ANALYSIS,
            description="Analyze unknown doc",
        )
        result = await agent.execute(task)
        assert result.success
        assert result.data["document"] == "unknown"

    @pytest.mark.asyncio
    async def test_execute_unsupported_type_returns_error(self):
        agent = ResearchAgent()
        task = Task(type=TaskType.CODE_GENERATION, description="code")
        result = await agent.execute(task)
        assert not result.success
        assert "Unsupported task type" in result.error

    @pytest.mark.asyncio
    async def test_execute_sets_status_lifecycle(self):
        agent = ResearchAgent()
        task = Task(type=TaskType.RESEARCH, description="test")
        await agent.execute(task)
        assert agent.status.value == "idle"
        assert agent.current_task is None

    @pytest.mark.asyncio
    async def test_execute_records_history(self):
        agent = ResearchAgent()
        task = Task(type=TaskType.RESEARCH, description="test")
        await agent.execute(task)
        assert len(agent.execution_history) == 1


class TestResearchAgentWebSearch:

    @pytest.mark.asyncio
    async def test_web_search_returns_three_results(self):
        agent = ResearchAgent()
        results = await agent.web_search("test query")
        assert len(results) == 3
        for r in results:
            assert "title" in r
            assert "url" in r
            assert "snippet" in r
            assert "example.com" in r["url"]

    @pytest.mark.asyncio
    async def test_web_search_includes_query_in_titles(self):
        agent = ResearchAgent()
        results = await agent.web_search("specific topic")
        assert all("specific topic" in r["title"] for r in results)


class TestResearchAgentAnalyzeSources:

    @pytest.mark.asyncio
    async def test_analyze_sources(self):
        agent = ResearchAgent()
        sources = [
            {"title": "Source A", "url": "https://a.com", "snippet": "snippet a"},
            {"title": "Source B", "url": "https://b.com", "snippet": "snippet b"},
        ]
        analyses = await agent.analyze_sources(sources)
        assert len(analyses) == 2
        for a in analyses:
            assert "source" in a
            assert "url" in a
            assert len(a["key_points"]) == 3
            assert a["relevance"] == 0.8

    @pytest.mark.asyncio
    async def test_analyze_empty_sources(self):
        agent = ResearchAgent()
        analyses = await agent.analyze_sources([])
        assert analyses == []


class TestResearchAgentSynthesizeFindings:

    @pytest.mark.asyncio
    async def test_synthesize(self):
        agent = ResearchAgent()
        analyses = [
            {"source": "S1", "key_points": ["p1"], "relevance": 0.8},
            {"source": "S2", "key_points": ["p2"], "relevance": 0.7},
        ]
        synthesis = await agent.synthesize_findings(analyses)
        assert "summary" in synthesis
        assert len(synthesis["key_insights"]) == 3
        assert len(synthesis["recommendations"]) == 3
        assert synthesis["sources_cited"] == 2

    @pytest.mark.asyncio
    async def test_synthesize_empty(self):
        agent = ResearchAgent()
        synthesis = await agent.synthesize_findings([])
        assert synthesis["sources_cited"] == 0
