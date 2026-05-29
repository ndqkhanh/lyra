"""GitHub repository discovery agent."""
from __future__ import annotations

import os

from lyra_research.agents.discovery.discovery_base import DiscoveryAgent
from lyra_research.discovery import GitHubDiscovery, ResearchSource


class GithubAgent(DiscoveryAgent):
    """Specialized agent for discovering repositories from GitHub."""

    def __init__(self, api_token: str | None = None, model: str = "claude-haiku-4-5") -> None:
        """
        Initialize GitHub agent.

        Args:
            api_token: Optional GitHub API token
            model: Model to use for discovery
        """
        super().__init__(source_name="github", model=model)
        self.api_token = api_token or os.environ.get("GITHUB_TOKEN")
        self.github = GitHubDiscovery(self.api_token)

    async def discover(self, query: str, max_results: int = 50) -> list[ResearchSource]:
        """
        Discover repositories from GitHub with rate limit handling.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of discovered repositories
        """
        for attempt in range(self.rate_limiter.max_retries):
            try:
                sources = self.github.search(query, max_results)
                return sources
            except Exception as e:
                if "rate limit" in str(e).lower() and attempt < self.rate_limiter.max_retries - 1:
                    self._handle_rate_limit(attempt)
                else:
                    print(f"GitHub discovery failed: {e}")
                    return []
        return []
