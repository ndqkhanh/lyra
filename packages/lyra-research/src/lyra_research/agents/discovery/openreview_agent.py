"""OpenReview discovery agent."""
from __future__ import annotations

import os
from typing import List

from lyra_research.agents.discovery.discovery_base import DiscoveryAgent
from lyra_research.discovery import ResearchSource
from lyra_research.sources import OpenReviewDiscovery


class OpenReviewAgent(DiscoveryAgent):
    """Specialized agent for discovering papers from OpenReview."""

    def __init__(self, api_key: str | None = None, model: str = "claude-haiku-4-5") -> None:
        """
        Initialize OpenReview agent.

        Args:
            api_key: Optional OpenReview API key
            model: Model to use for discovery
        """
        super().__init__(source_name="openreview", model=model)
        self.api_key = api_key or os.environ.get("OPENREVIEW_API_KEY")
        self.openreview = OpenReviewDiscovery(self.api_key)

    async def discover(self, query: str, max_results: int = 50) -> List[ResearchSource]:
        """
        Discover papers from OpenReview with rate limit handling.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of discovered papers
        """
        # OpenReviewDiscovery already has retry logic built in
        try:
            sources = self.openreview.search(query, max_results)
            return sources
        except Exception as e:
            print(f"OpenReview discovery failed: {e}")
            return []
