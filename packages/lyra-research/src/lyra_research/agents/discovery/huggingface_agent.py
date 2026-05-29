"""HuggingFace discovery agent."""
from __future__ import annotations

import os

from lyra_research.agents.discovery.discovery_base import DiscoveryAgent
from lyra_research.discovery import ResearchSource
from lyra_research.sources import HuggingFacePapersDiscovery


class HuggingFaceAgent(DiscoveryAgent):
    """Specialized agent for discovering papers and models from HuggingFace."""

    def __init__(self, api_key: str | None = None, model: str = "claude-haiku-4-5") -> None:
        """
        Initialize HuggingFace agent.

        Args:
            api_key: Optional HuggingFace API key
            model: Model to use for discovery
        """
        super().__init__(source_name="huggingface", model=model)
        self.api_key = api_key or os.environ.get("HF_API_KEY")
        self.huggingface = HuggingFacePapersDiscovery(self.api_key)

    async def discover(self, query: str, max_results: int = 50) -> list[ResearchSource]:
        """
        Discover papers from HuggingFace with rate limit handling.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of discovered papers
        """
        for attempt in range(self.rate_limiter.max_retries):
            try:
                sources = self.huggingface.search(query, max_results)
                return sources
            except Exception as e:
                if "rate limit" in str(e).lower() and attempt < self.rate_limiter.max_retries - 1:
                    self._handle_rate_limit(attempt)
                else:
                    print(f"HuggingFace discovery failed: {e}")
                    return []
        return []
