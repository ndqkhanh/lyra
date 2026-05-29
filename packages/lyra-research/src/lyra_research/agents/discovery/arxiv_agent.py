"""ArXiv discovery agent."""

from __future__ import annotations

from lyra_research.agents.discovery.discovery_base import DiscoveryAgent
from lyra_research.discovery import ArXivDiscovery, ResearchSource


class ArxivAgent(DiscoveryAgent):
    """Specialized agent for discovering papers from ArXiv."""

    def __init__(self, model: str = "claude-haiku-4-5") -> None:
        """Initialize ArXiv agent."""
        super().__init__(source_name="arxiv", model=model)
        self.arxiv = ArXivDiscovery()

    async def discover(self, query: str, max_results: int = 50) -> list[ResearchSource]:
        """
        Discover papers from ArXiv.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of discovered papers
        """
        # ArXiv API is generally stable, but we still wrap in retry logic
        for attempt in range(self.rate_limiter.max_retries):
            try:
                sources = self.arxiv.search(query, max_results)
                return sources
            except Exception as e:
                if attempt < self.rate_limiter.max_retries - 1:
                    self._handle_rate_limit(attempt)
                else:
                    print(

                            f"ArXiv discovery failed after {self.rate_limiter.max_retries}"
                            f" attempts: {e}"

                    )
                    return []
        return []
