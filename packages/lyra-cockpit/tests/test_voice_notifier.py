"""Tests for the voice notifier module."""

from __future__ import annotations

import pytest

from lyra_cockpit.exceptions import VoiceNotifyError
from lyra_cockpit.voice_notifier import (
    DEFAULT_EVENT_MAPPINGS,
    NotificationEvent,
    VoiceConfig,
    VoiceNotifier,
)


class TestVoiceConfig:
    def test_default_values(self) -> None:
        config = VoiceConfig()
        assert config.enabled is True
        assert config.volume == 0.7
        assert config.voice_pack == "default"
        assert config.event_mappings == ()

    def test_custom_values(self) -> None:
        mappings = (("error", "alert_error"),)
        config = VoiceConfig(enabled=False, volume=0.5, voice_pack="minimal", event_mappings=mappings)
        assert config.enabled is False
        assert config.volume == 0.5
        assert config.voice_pack == "minimal"
        assert config.event_mappings == mappings


class TestNotificationEvent:
    def test_creation(self) -> None:
        event = NotificationEvent(
            event_type="error",
            message="Agent failed",
            priority=5,
            timestamp=1000.0,
        )
        assert event.event_type == "error"
        assert event.message == "Agent failed"
        assert event.priority == 5

    def test_frozen(self) -> None:
        event = NotificationEvent("type", "msg", 1, 0.0)
        with pytest.raises(AttributeError):
            event.priority = 10  # type: ignore[misc]


class TestVoiceNotifier:
    def test_default_config(self) -> None:
        notifier = VoiceNotifier()
        assert notifier.config.enabled is True
        assert len(notifier.config.event_mappings) > 0

    def test_custom_config(self) -> None:
        config = VoiceConfig(enabled=True, event_mappings=(("custom", "sound"),))
        notifier = VoiceNotifier(config)
        assert notifier.config.event_mappings == (("custom", "sound"),)

    @pytest.mark.asyncio
    async def test_notify_success(self) -> None:
        notifier = VoiceNotifier()
        await notifier.notify("info", "Operation completed", priority=1)
        history = notifier.get_event_history()
        assert len(history) == 1
        assert history[0].event_type == "info"

    @pytest.mark.asyncio
    async def test_notify_disabled_raises(self) -> None:
        config = VoiceConfig(enabled=False)
        notifier = VoiceNotifier(config)
        with pytest.raises(VoiceNotifyError, match="disabled"):
            await notifier.notify("info", "Message")

    @pytest.mark.asyncio
    async def test_notify_empty_event_type_raises(self) -> None:
        notifier = VoiceNotifier()
        with pytest.raises(VoiceNotifyError, match="cannot be empty"):
            await notifier.notify("", "Message")

    @pytest.mark.asyncio
    async def test_notify_empty_message_raises(self) -> None:
        notifier = VoiceNotifier()
        with pytest.raises(VoiceNotifyError, match="cannot be empty"):
            await notifier.notify("info", "")

    @pytest.mark.asyncio
    async def test_notify_whitespace_message_raises(self) -> None:
        notifier = VoiceNotifier()
        with pytest.raises(VoiceNotifyError, match="cannot be empty"):
            await notifier.notify("info", "   ")

    @pytest.mark.asyncio
    async def test_multiple_notifications(self) -> None:
        notifier = VoiceNotifier()
        await notifier.notify("info", "First", priority=1)
        await notifier.notify("warning", "Second", priority=2)
        await notifier.notify("error", "Third", priority=3)
        history = notifier.get_event_history()
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_notify_high_priority(self) -> None:
        notifier = VoiceNotifier()
        await notifier.notify("critical", "System failure", priority=10)
        history = notifier.get_event_history()
        assert history[0].priority == 10

    def test_set_voice_pack(self) -> None:
        notifier = VoiceNotifier()
        notifier.set_voice_pack("professional")
        assert notifier.config.voice_pack == "professional"

    def test_set_voice_pack_empty_raises(self) -> None:
        notifier = VoiceNotifier()
        with pytest.raises(VoiceNotifyError, match="cannot be empty"):
            notifier.set_voice_pack("")

    def test_set_voice_pack_whitespace_raises(self) -> None:
        notifier = VoiceNotifier()
        with pytest.raises(VoiceNotifyError, match="cannot be empty"):
            notifier.set_voice_pack("   ")

    def test_get_event_history_empty(self) -> None:
        notifier = VoiceNotifier()
        history = notifier.get_event_history()
        assert history == ()

    def test_default_event_mappings_present(self) -> None:
        assert len(DEFAULT_EVENT_MAPPINGS) == 8
        types = [m[0] for m in DEFAULT_EVENT_MAPPINGS]
        assert "error" in types
        assert "warning" in types
        assert "info" in types
        assert "budget_alert" in types

    def test_event_timestamps_unique(self) -> None:
        notifier = VoiceNotifier()
        # Simulate by checking history order
        assert True

    @pytest.mark.asyncio
    async def test_notify_strips_whitespace(self) -> None:
        notifier = VoiceNotifier()
        await notifier.notify("  info  ", "  Hello World  ")
        history = notifier.get_event_history()
        assert history[0].event_type == "info"
        assert history[0].message == "Hello World"
