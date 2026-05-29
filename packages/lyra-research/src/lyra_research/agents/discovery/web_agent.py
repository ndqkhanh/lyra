"""Web search discovery agent."""
from __future__ import annotations

from lyra_research.agents.discovery.discovery_base import DiscoveryAgent
from lyra_research.discovery import ResearchSource


class WebAgent(DiscoveryAgent):
    """
    Specialized agent for discovering web content.

    Note: This is a placeholder implementation. In production, this would
    integrate with web search APIs (Google Custom Search, Bing, etc.)
    """

    def __init__(self, model: str = "claude-haiku-4-5") -> None:
        """Initialize web search agent."""
        super().__init__(source_name="web", model=model)

    async def discover(self, query: str, max_results: int = 50) -> list[ResearchSource]:
        """
        Discover web content for the given query.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of discovered web sources (currently empty placeholder)
        """
        # Placeholder: In production, integrate with web search APIs
        # For now, return empty list to avoid breaking tests
        print(f"Web search for '{query}' (placeholder - no results)")
        return []
