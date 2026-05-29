"""Tests for lyra_otel_tracer.token_tracker."""

from __future__ import annotations

import pytest
from lyra_otel_tracer.token_tracker import TokenAlert, TokenSummary, TokenTracker, TokenUsage


class TestTokenUsage:
    def test_token_usage_creation(self) -> None:
        usage = TokenUsage(
            agent_id="a1",
            model="sonnet",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            timestamp=1000.0,
        )
        assert usage.agent_id == "a1"
        assert usage.model == "sonnet"
        assert usage.prompt_tokens == 100
        assert usage.total_tokens == 150

    def test_token_usage_frozen(self) -> None:
        usage = TokenUsage(
            agent_id="a1",
            model="sonnet",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            timestamp=0.0,
        )
        with pytest.raises(AttributeError):
            usage.agent_id = "changed"  # type: ignore[misc]


class TestTokenSummary:
    def test_token_summary_creation(self) -> None:
        summary = TokenSummary(
            total_prompt=200,
            total_completion=100,
            total_tokens=300,
            by_model=(("sonnet", 300),),
            by_agent=(("a1", 300),),
            window_seconds=3600.0,
        )
        assert summary.total_tokens == 300
        assert len(summary.by_model) == 1

    def test_token_summary_defaults(self) -> None:
        summary = TokenSummary(total_prompt=0, total_completion=0, total_tokens=0)
        assert summary.by_model == ()
        assert summary.by_agent == ()
        assert summary.window_seconds == 3600.0

    def test_token_summary_frozen(self) -> None:
        summary = TokenSummary(total_prompt=0, total_completion=0, total_tokens=0)
        with pytest.raises(AttributeError):
            summary.total_tokens = 100  # type: ignore[misc]


class TestTokenAlert:
    def test_token_alert_creation(self) -> None:
        alert = TokenAlert(
            alert_type="threshold_exceeded",
            message="Usage exceeded",
            threshold=1000,
            current_usage=1500,
            timestamp=100.0,
        )
        assert alert.alert_type == "threshold_exceeded"
        assert alert.current_usage == 1500

    def test_token_alert_frozen(self) -> None:
        alert = TokenAlert(
            alert_type="test", message="msg", threshold=10, current_usage=20, timestamp=0.0
        )
        with pytest.raises(AttributeError):
            alert.alert_type = "changed"  # type: ignore[misc]


class TestTokenTracker:
    @pytest.mark.asyncio
    async def test_record_usage(self) -> None:
        tracker = TokenTracker()
        usage = await tracker.record_usage("a1", "sonnet", 100, 50)
        assert usage.agent_id == "a1"
        assert usage.total_tokens == 150
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50

    @pytest.mark.asyncio
    async def test_record_usage_zero_tokens(self) -> None:
        tracker = TokenTracker()
        usage = await tracker.record_usage("a1", "haiku", 0, 0)
        assert usage.total_tokens == 0

    @pytest.mark.asyncio
    async def test_get_usage_summary_empty(self) -> None:
        tracker = TokenTracker()
        summary = await tracker.get_usage_summary()
        assert summary.total_tokens == 0
        assert summary.total_prompt == 0
        assert summary.total_completion == 0

    @pytest.mark.asyncio
    async def test_get_usage_summary(self) -> None:
        tracker = TokenTracker()
        await tracker.record_usage("a1", "sonnet", 100, 50)
        await tracker.record_usage("a2", "opus", 200, 100)
        summary = await tracker.get_usage_summary(window_seconds=3600.0)
        assert summary.total_tokens == 450
        assert summary.total_prompt == 300
        assert summary.total_completion == 150
        assert len(summary.by_model) == 2
        assert len(summary.by_agent) == 2

    @pytest.mark.asyncio
    async def test_get_usage_summary_outside_window(self) -> None:
        tracker = TokenTracker()
        await tracker.record_usage("a1", "sonnet", 100, 50)
        # negative window should exclude everything
        summary = await tracker.get_usage_summary(window_seconds=-1.0)
        assert summary.total_tokens == 0

    @pytest.mark.asyncio
    async def test_set_alert_threshold(self) -> None:
        tracker = TokenTracker()
        await tracker.set_alert_threshold(500)
        assert tracker._alert_threshold == 500

    @pytest.mark.asyncio
    async def test_check_alerts_no_threshold(self) -> None:
        tracker = TokenTracker()
        alerts = await tracker.check_alerts()
        assert alerts == ()

    @pytest.mark.asyncio
    async def test_check_alerts_triggered(self) -> None:
        tracker = TokenTracker()
        await tracker.record_usage("a1", "sonnet", 1000, 500)
        await tracker.set_alert_threshold(100)
        alerts = await tracker.check_alerts()
        assert len(alerts) > 0
        assert alerts[0].alert_type == "threshold_exceeded"

    @pytest.mark.asyncio
    async def test_check_alerts_not_triggered(self) -> None:
        tracker = TokenTracker()
        await tracker.record_usage("a1", "sonnet", 10, 5)
        await tracker.set_alert_threshold(1000)
        alerts = await tracker.check_alerts()
        assert alerts == ()

    @pytest.mark.asyncio
    async def test_get_usage_history(self) -> None:
        tracker = TokenTracker()
        await tracker.record_usage("a1", "sonnet", 100, 50)
        await tracker.record_usage("a1", "opus", 200, 100)
        await tracker.record_usage("a2", "haiku", 10, 5)
        history = await tracker.get_usage_history("a1")
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_get_usage_history_empty(self) -> None:
        tracker = TokenTracker()
        history = await tracker.get_usage_history("nonexistent")
        assert history == ()

    @pytest.mark.asyncio
    async def test_get_usage_history_limit(self) -> None:
        tracker = TokenTracker()
        for _ in range(50):
            await tracker.record_usage("a1", "sonnet", 10, 5)
        history = await tracker.get_usage_history("a1", limit=10)
        assert len(history) == 10

    @pytest.mark.asyncio
    async def test_get_usage_summary_by_model(self) -> None:
        tracker = TokenTracker()
        await tracker.record_usage("a1", "sonnet", 100, 50)
        await tracker.record_usage("a2", "sonnet", 50, 25)
        await tracker.record_usage("a3", "opus", 200, 100)
        summary = await tracker.get_usage_summary()
        model_map = dict(summary.by_model)
        assert model_map["sonnet"] == 225
        assert model_map["opus"] == 300

    @pytest.mark.asyncio
    async def test_get_usage_summary_by_agent(self) -> None:
        tracker = TokenTracker()
        await tracker.record_usage("a1", "sonnet", 100, 50)
        await tracker.record_usage("a1", "opus", 200, 100)
        await tracker.record_usage("a2", "haiku", 10, 5)
        summary = await tracker.get_usage_summary()
        agent_map = dict(summary.by_agent)
        assert agent_map["a1"] == 450
        assert agent_map["a2"] == 15
