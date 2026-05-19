"""Discovery Role — Multi-source parallel discovery.

Discovers sources across 7+ discovery sources:
- ArXiv
- Semantic Scholar
- GitHub
- Web
- OpenReview
- HuggingFace
- Papers with Code (future)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List

from lyra_core.context.layered_context import LayeredContextManager
from lyra_research.discovery import ResearchSource
from lyra_research.roles.role_base import Role, RoleResult, RoleStatus
from lyra_research.agents.discovery import (
    ArxivAgent,
    SemanticScholarAgent,
    GithubAgent,
    WebAgent,
    OpenReviewAgent,
    HuggingFaceAgent,
)


@dataclass
class DiscoveryResult(RoleResult):
    """Result from discovery role."""

    sources: List[ResearchSource] = field(default_factory=list)
    sources_by_type: dict[str, int] = field(default_factory=dict)
    total_sources: int = 0


class DiscoveryRole(Role[DiscoveryResult]):
    """
    Discovery Role — Discovers sources across 7+ discovery sources.

    Model: claude-haiku-4-5 (fast, cost-effective for parallel discovery)
    """

    def __init__(self, context_manager: LayeredContextManager) -> None:
        """
        Initialize discovery role.

        Args:
            context_manager: Layered context manager
        """
        super().__init__("Discovery", "claude-haiku-4-5", context_manager)

        # Initialize discovery agents
        self.discovery_agents = [
            ArxivAgent(),
            SemanticScholarAgent(),
            GithubAgent(),
            WebAgent(),
            OpenReviewAgent(),
            HuggingFaceAgent(),
        ]

    async def execute(self, query: str) -> DiscoveryResult:
        """
        Execute parallel discovery across all sources.

        Args:
            query: Research query

        Returns:
            DiscoveryResult with discovered sources
        """
        import asyncio

        result = DiscoveryResult(
            role_name=self.name,
            status=RoleStatus.RUNNING,
            data=None,
        )

        # Parallel discovery across all agents
        tasks = [
            agent.discover(query, max_results=50) for agent in self.discovery_agents
        ]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect all sources
            all_sources: List[ResearchSource] = []
            for agent_result in results:
                if isinstance(agent_result, Exception):
                    # Log error but continue
                    print(f"Discovery agent error: {agent_result}")
                    continue
                if isinstance(agent_result, list):
                    all_sources.extend(agent_result)

            # Calculate statistics
            sources_by_type: dict[str, int] = {}
            for source in all_sources:
                source_type = source.source_type.value
                sources_by_type[source_type] = sources_by_type.get(source_type, 0) + 1

            result.sources = all_sources
            result.sources_by_type = sources_by_type
            result.total_sources = len(all_sources)
            result.data = all_sources
            result.metadata = {
                "sources_by_type": sources_by_type,
                "total_sources": len(all_sources),
                "query": query,
            }

            return result

        except Exception as e:
            result.status = RoleStatus.FAILED
            result.error = str(e)
            return result

    def validate_input(self, query: Any) -> bool:
        """
        Validate input query.

        Args:
            query: Research query

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(query, str):
            return False
        if len(query.strip()) == 0:
            return False
        if len(query) > 1000:  # Reasonable query length limit
            return False
        return True

    def validate_output(self, sources: Any) -> bool:
        """
        Validate discovered sources.

        Args:
            sources: List of discovered sources

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(sources, list):
            return False

        # Allow empty results (query might not match anything)
        if len(sources) == 0:
            return True

        # Validate each source
        for source in sources:
            if not isinstance(source, ResearchSource):
                return False
            if not source.title or len(source.title.strip()) == 0:
                return False
            if not source.url or len(source.url.strip()) == 0:
                return False

        return True
