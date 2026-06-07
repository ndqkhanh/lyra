"""
Voice agent router -- routes transcribed speech to the P1 orchestrator.

The ``VoiceAgentRouter`` takes transcribed text and sends it to the
``OrchestratorAgent`` (P1) for processing.  The orchestrator's result
is returned for TTS synthesis.
"""

from __future__ import annotations

import logging
import structlog
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class RouterError(Exception):
    """Raised when the voice router encounters an error."""


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RouterResponse:
    """Response from the voice agent router.

    Attributes:
        text: The processed response text (ready for TTS).
        query: The original transcribed query.
        confidence: Confidence in the response (0.0 - 1.0).
        latency_ms: Wall-clock time for the route + orchestration call.
        metadata: Additional metadata from the orchestration run.
    """

    text: str
    query: str
    confidence: float = 1.0
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# VoiceAgentRouter
# ---------------------------------------------------------------------------

OrchestratorRunFn = Callable[..., Any]
"""Type alias for an orchestrator run function -- typically
``OrchestratorAgent.run(question, worker_factory, ...)``.
"""


class VoiceAgentRouter:
    """Routes transcribed voice queries to the P1 orchestrator.

    The router wraps the orchestrator's ``run`` method, providing a
    voice-specific interface that strips irrelevant metadata and returns
    a ``RouterResponse`` suitable for TTS.

    Usage::

        orchestrator = OrchestratorAgent(...)
        router = VoiceAgentRouter(orchestrator.run)
        response = await router.route_transcribed_text("What is the weather?")
    """

    def __init__(
        self,
        orchestrator_run: OrchestratorRunFn,
        system_prompt: str | None = None,
    ) -> None:
        """Initialise the voice agent router.

        Args:
            orchestrator_run: The ``OrchestratorAgent.run`` method (or any
                async callable with compatible signature).
            system_prompt: Optional system prompt prepended to each query.
                Helps the orchestrator understand it's being spoken to.
        """
        self._orchestrator_run = orchestrator_run
        self._system_prompt = system_prompt or (
            "The user is speaking via voice interface. Respond concisely "
            "and conversationally as if in a spoken dialogue. "
            "Keep responses under 200 words for comfortable TTS delivery."
        )

    async def route_transcribed_text(
        self,
        text: str,
        context: dict[str, Any] | None = None,
    ) -> RouterResponse:
        """Route transcribed text through the orchestrator.

        Prepends the system prompt, calls the orchestrator's ``run``
        method, and extracts the response text for TTS.

        Args:
            text: The transcribed user query.
            context: Optional context (e.g. conversation history, user ID).

        Returns:
            A ``RouterResponse`` with the orchestrator's reply.

        Raises:
            RouterError: If the orchestrator call fails.
        """
        if not text or not text.strip():
            raise RouterError("Cannot route empty text")

        # Prep full query with system prompt for conversational context
        full_query = (
            f"[Voice Query] {self._system_prompt}\n\nUser: {text.strip()}"
        )

        start = time.monotonic()
        try:
            result = await self._orchestrator_run(
                question=full_query,
                worker_factory=self._default_worker,
            )
        except Exception as exc:
            raise RouterError(f"Orchestrator routing failed: {exc}") from exc

        latency_ms = (time.monotonic() - start) * 1000

        # Extract the summary as the TTS-friendly response
        response_text = result.summary if result.summary else text
        confidence = result.average_confidence if hasattr(result, "average_confidence") else 1.0

        return RouterResponse(
            text=response_text,
            query=text.strip(),
            confidence=confidence,
            latency_ms=latency_ms,
            metadata={
                "effort_level": (
                    result.effort_level.value if hasattr(result, "effort_level") else "unknown"
                ),
                "worker_count": (
                    result.worker_count if hasattr(result, "worker_count") else 0
                ),
                "artifact_count": len(result.artifacts) if hasattr(result, "artifacts") else 0,
            },
        )

    async def _default_worker(self, **kwargs: Any) -> Any:
        """Minimal worker that returns the query as-is for TTS.

        This is a fallback when the orchestrator is not available or
        when the pipeline is configured for direct query/response.
        """
        from src.orchestrator.artifact import Artifact

        sub_task = kwargs.get("sub_task", None)
        description = sub_task.description if sub_task else str(kwargs)
        return Artifact(
            task_id="voice_default",
            content=description,
            summary=description,
            confidence=1.0,
            worker_id="voice_router",
        )

    async def route_direct(
        self,
        text: str,
    ) -> str:
        """Route text directly (bypass orchestrator) for simple queries.

        Useful for short, factoid queries or when low latency is critical.
        Returns the text unchanged (the STT output passes through directly
        as a "echo" response).

        Args:
            text: The transcribed user query.

        Returns:
            The text itself (echo mode).
        """
        return text
