"""
Abstract base class for LLM provider backends.

Every concrete provider adapter (Anthropic, DeepSeek, OpenAI, Google, …)
subclasses ``ProviderBackend`` and implements the four abstract methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from lyra.routing.provider.types import (
    Capability,
    CompletionChunk,
    CompletionRequest,
    CompletionResponse,
    CostEstimate,
)


class ProviderBackend(ABC):
    """Abstract interface for an LLM provider backend.

    All I/O methods are async. Providers should be instantiated once and
    reused across requests (they hold a shared client connection pool).
    """

    @abstractmethod
    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Send a completion request and return the full response.

        Args:
            request: The completion request with messages, model, etc.

        Returns:
            A fully populated ``CompletionResponse``.
        """

    @abstractmethod
    async def complete_stream(
        self,
        request: CompletionRequest,
    ) -> AsyncIterator[CompletionChunk]:
        """Send a completion request and stream back chunks.

        Args:
            request: The completion request with messages, model, etc.

        Yields:
            ``CompletionChunk`` instances as they arrive.
        """
        if False:  # pragma: no cover
            yield  # make the generator recognized by type checkers

    @abstractmethod
    def supports(self, capability: Capability) -> bool:
        """Return ``True`` if this provider supports *capability*."""

    @abstractmethod
    def cost_estimate(self, request: CompletionRequest) -> CostEstimate:
        """Return an estimated cost for *request* in USD.

        The estimate is based on the provider's published per-token pricing
        and a heuristic token count derived from message length.
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name (e.g. ``"anthropic"``)."""
