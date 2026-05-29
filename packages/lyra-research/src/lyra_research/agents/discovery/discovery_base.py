"""
Base class for discovery agents with rate limiting and exponential backoff.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod

from lyra_research.discovery import ResearchSource


class RateLimiter:
    """Rate limiter with exponential backoff for API calls."""

    def __init__(self, max_retries: int = 5, base_delay: float = 1.0) -> None:
        """
        Initialize rate limiter.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds (doubles each retry)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay

    def calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds: 1s, 2s, 4s, 8s, 16s
        """
        return self.base_delay * (2**attempt)

    def handle_rate_limit(self, attempt: int, source_name: str) -> None:
        """
        Handle rate limit by sleeping with exponential backoff.

        Args:
            attempt: Current attempt number (0-indexed)
            source_name: Name of the source being rate limited
        """
        if attempt >= self.max_retries:
            raise RuntimeError(
                f"{source_name} rate limit exceeded after {self.max_retries} attempts"
            )

        delay = self.calculate_backoff(attempt)
        print(
            f"{source_name} rate limited. Retrying in {delay}s... "
            f"(attempt {attempt + 1}/{self.max_retries})"
        )
        time.sleep(delay)


class DiscoveryAgent(ABC):
    """
    Base class for discovery agents.

    Each agent discovers sources from a specific platform (ArXiv, GitHub, etc.)
    with built-in rate limiting and exponential backoff.
    """

    def __init__(
        self,
        source_name: str,
        model: str = "claude-haiku-4-5",
        max_retries: int = 5,
    ) -> None:
        """
        Initialize discovery agent.

        Args:
            source_name: Name of the source (e.g., "arxiv", "github")
            model: Model to use for discovery (default: Haiku for speed)
            max_retries: Maximum retry attempts for rate-limited requests
        """
        self.source_name = source_name
        self.model = model
        self.rate_limiter = RateLimiter(max_retries=max_retries)

    @abstractmethod
    async def discover(self, query: str, max_results: int = 50) -> list[ResearchSource]:
        """
        Discover sources for the given query.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of discovered research sources
        """
        pass

    def _handle_rate_limit(self, attempt: int) -> None:
        """
        Handle rate limit with exponential backoff.

        Args:
            attempt: Current attempt number (0-indexed)
        """
        self.rate_limiter.handle_rate_limit(attempt, self.source_name)
