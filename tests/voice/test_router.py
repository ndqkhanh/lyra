"""Comprehensive tests for the voice agent router.

Tests VoiceAgentRouter, RouterResponse, and all associated types.
"""

from __future__ import annotations

from unittest.mock import MagicMock, AsyncMock

import pytest

from lyra.voice.router import (
    OrchestratorRunFn,
    RouterError,
    RouterResponse,
    VoiceAgentRouter,
)


# ===================================================================
# Data class tests
# ===================================================================


class TestRouterResponse:
    """Tests for the RouterResponse dataclass."""

    def test_fields(self) -> None:
        resp = RouterResponse(text="Hello", query="hi")
        assert resp.text == "Hello"
        assert resp.query == "hi"
        assert resp.confidence == 1.0
        assert resp.latency_ms == 0.0
        assert resp.metadata == {}

    def test_is_frozen(self) -> None:
        resp = RouterResponse(text="Hello", query="hi")
        with pytest.raises(AttributeError):
            resp.text = "Changed"  # type: ignore[misc]

    def test_custom_values(self) -> None:
        resp = RouterResponse(
            text="Response",
            query="Query",
            confidence=0.85,
            latency_ms=150.0,
            metadata={"effort_level": "high"},
        )
        assert resp.confidence == 0.85
        assert resp.latency_ms == 150.0
        assert resp.metadata["effort_level"] == "high"


# ===================================================================
# OrchestratorRunFn type
# ===================================================================


class TestOrchestratorRunFn:
    def test_type_is_callable(self) -> None:
        """OrchestratorRunFn should be usable as a type annotation for callables."""
        def my_run(**kwargs: object) -> object:
            return None

        fn: OrchestratorRunFn = my_run
        assert callable(fn)


# ===================================================================
# VoiceAgentRouter tests
# ===================================================================


class TestVoiceAgentRouterInit:
    """Tests for VoiceAgentRouter initialisation."""

    def test_default_system_prompt(self) -> None:
        router = VoiceAgentRouter(orchestrator_run=MagicMock())
        assert "voice interface" in router._system_prompt.lower()

    def test_custom_system_prompt(self) -> None:
        router = VoiceAgentRouter(
            orchestrator_run=MagicMock(),
            system_prompt="Speak in short sentences.",
        )
        assert router._system_prompt == "Speak in short sentences."


class TestVoiceAgentRouterRouteTranscribedText:
    """Tests for the route_transcribed_text method."""

    @pytest.mark.asyncio
    async def test_routes_text_successfully(self) -> None:
        """Route should prepend system prompt and return response."""

        class MockResult:
            summary = "This is the response"
            average_confidence = 0.9
            effort_level = type("EL", (), {"value": "high"})()
            worker_count = 3
            artifacts = ["a1", "a2"]

        async def mock_run(question: str, worker_factory: object = None) -> MockResult:
            assert "[Voice Query]" in question
            return MockResult()

        router = VoiceAgentRouter(orchestrator_run=mock_run)
        response = await router.route_transcribed_text("What is the weather?")

        assert isinstance(response, RouterResponse)
        assert response.text == "This is the response"
        assert response.query == "What is the weather?"
        assert response.confidence == 0.9
        assert response.latency_ms > 0
        assert response.metadata["effort_level"] == "high"
        assert response.metadata["worker_count"] == 3
        assert response.metadata["artifact_count"] == 2

    @pytest.mark.asyncio
    async def test_routes_with_context(self) -> None:
        """Context dict should be passed through."""

        async def mock_run(question: str, worker_factory: object = None) -> MagicMock:
            return MagicMock(
                summary="response",
                average_confidence=1.0,
                effort_level=type("EL", (), {"value": "medium"})(),
                worker_count=1,
                artifacts=[],
            )

        router = VoiceAgentRouter(orchestrator_run=mock_run)
        response = await router.route_transcribed_text("Hello", context={"user_id": "abc"})
        assert response.text == "response"

    @pytest.mark.asyncio
    async def test_empty_text_raises(self) -> None:
        router = VoiceAgentRouter(orchestrator_run=MagicMock())
        with pytest.raises(RouterError, match="empty"):
            await router.route_transcribed_text("")

    @pytest.mark.asyncio
    async def test_whitespace_text_raises(self) -> None:
        router = VoiceAgentRouter(orchestrator_run=MagicMock())
        with pytest.raises(RouterError, match="empty"):
            await router.route_transcribed_text("   ")

    @pytest.mark.asyncio
    async def test_orchestrator_error_propagation(self) -> None:
        async def failing_run(question: str, worker_factory: object = None) -> None:
            raise RuntimeError("Orchestrator down")

        router = VoiceAgentRouter(orchestrator_run=failing_run)
        with pytest.raises(RouterError, match="Orchestrator routing failed"):
            await router.route_transcribed_text("Hello")

    @pytest.mark.asyncio
    async def test_result_without_summary_falls_back(self) -> None:
        """If result has no summary, fall back to query text."""

        class ResultNoSummary:
            @property
            def summary(self) -> None:
                return None

            average_confidence = 0.5

        async def mock_run_no_summary(question, worker_factory=None):
            return ResultNoSummary()

        router = VoiceAgentRouter(orchestrator_run=mock_run_no_summary)
        response = await router.route_transcribed_text("Hello")
        # Should fall back to query text
        assert response.text == "Hello"
        assert response.confidence == 0.5

    @pytest.mark.asyncio
    async def test_result_confidence_fallback(self) -> None:
        """If result has no average_confidence, use 1.0."""

        class ResultNoConfidence:
            summary = "response text"

        async def mock_run(question, worker_factory=None):
            return ResultNoConfidence()

        router = VoiceAgentRouter(orchestrator_run=mock_run)
        response = await router.route_transcribed_text("Hello")
        assert response.confidence == 1.0
        assert response.text == "response text"

    @pytest.mark.asyncio
    async def test_metadata_falls_back_gracefully(self) -> None:
        """Missing effort_level etc. should not crash."""

        class MinimalResult:
            summary = "response"
            average_confidence = 1.0

        async def mock_run(question, worker_factory=None):
            return MinimalResult()

        router = VoiceAgentRouter(orchestrator_run=mock_run)
        response = await router.route_transcribed_text("Hello")
        assert response.metadata is not None
        # Should not crash even with missing attributes


class TestVoiceAgentRouterRouteDirect:
    """Tests for the route_direct method."""

    @pytest.mark.asyncio
    async def test_route_direct_echos(self) -> None:
        router = VoiceAgentRouter(orchestrator_run=MagicMock())
        result = await router.route_direct("hello")
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_route_direct_empty_string(self) -> None:
        router = VoiceAgentRouter(orchestrator_run=MagicMock())
        result = await router.route_direct("")
        assert result == ""


class TestVoiceAgentRouterDefaultWorker:
    """Tests for the _default_worker fallback."""

    @pytest.mark.asyncio
    async def test_default_worker_creates_artifact(self) -> None:
        router = VoiceAgentRouter(orchestrator_run=MagicMock())
        result = await router._default_worker(sub_task=type("ST", (), {"description": "test task"})())
        assert result.task_id == "voice_default"
        assert result.content == "test task"
        assert result.worker_id == "voice_router"

    @pytest.mark.asyncio
    async def test_default_worker_without_sub_task(self) -> None:
        router = VoiceAgentRouter(orchestrator_run=MagicMock())
        result = await router._default_worker(keyword="value")
        assert result.task_id == "voice_default"
        assert result.worker_id == "voice_router"


# ===================================================================
# Edge cases
# ===================================================================


class TestRouterEdgeCases:
    def test_router_error_exception(self) -> None:
        error = RouterError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert isinstance(error, Exception)

    @pytest.mark.asyncio
    async def test_latency_measured(self) -> None:
        """Latency should be measured and positive."""

        async def mock_run(question, worker_factory=None):
            import asyncio
            await asyncio.sleep(0.01)
            return MagicMock(
                summary="response",
                average_confidence=1.0,
                effort_level=type("EL", (), {"value": "low"})(),
                worker_count=1,
                artifacts=[],
            )

        router = VoiceAgentRouter(orchestrator_run=mock_run)
        response = await router.route_transcribed_text("Hello")
        assert response.latency_ms > 5.0  # Should be ~10ms
