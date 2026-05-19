"""Semantic Scholar discovery agent."""
from __future__ import annotations

import os
from typing import List

from lyra_research.agents.discovery.discovery_base import DiscoveryAgent
from lyra_research.discovery import ResearchSource, SemanticScholarDiscovery


class SemanticScholarAgent(DiscoveryAgent):
    """Specialized agent for discovering papers from Semantic Scholar."""

    def __init__(self, api_key: str | None = None, model: str = "claude-haiku-4-5") -> None:
        """
        Initialize Semantic Scholar agent.

        Args:
            api_key: Optional Semantic Scholar API key
            model: Model to use for discovery
        """
        super().__init__(source_name="semantic_scholar", model=model)
        self.api_key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
        self.semantic_scholar = SemanticScholarDiscovery(self.api_key)

    async def discover(self, query: str, max_results: int = 50) -> List[ResearchSource]:
        """
        Discover papers from Semantic Scholar with rate limit handling.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of discovered papers
        """
        # SemanticScholarDiscovery already has retry logic, but we wrap it
        # to ensure consistent error handling across all agents
        try:
            sources = self.semantic_scholar.search(query, max_results)
            return sources
        except Exception as e:
            print(f"Semantic Scholar discovery failed: {e}")
            return []
