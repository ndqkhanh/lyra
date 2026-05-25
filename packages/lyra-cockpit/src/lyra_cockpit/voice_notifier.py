"""Voice notifier — voice/sound notifications for cockpit events.

Provides configurable voice notifications with event-to-sound mappings,
priority-based delivery, and event history tracking.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .exceptions import VoiceNotifyError


@dataclass(frozen=True)
class VoiceConfig:
    """Configuration for voice notifications.

    Attributes:
        enabled: Whether voice notifications are enabled.
        volume: Volume level (0.0 to 1.0).
        voice_pack: Name of the voice pack to use.
        event_mappings: Tuple of (event_type, sound_name) pairs.
    """

    enabled: bool = True
    volume: float = 0.7
    voice_pack: str = "default"
    event_mappings: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class NotificationEvent:
    """A recorded notification event.

    Attributes:
        event_type: The type/category of event.
        message: Human-readable notification message.
        priority: Numeric priority (higher = more important).
        timestamp: Unix timestamp when the notification was fired.
    """

    event_type: str
    message: str
    priority: int
    timestamp: float


DEFAULT_EVENT_MAPPINGS: tuple[tuple[str, str], ...] = (
    ("error", "alert_error"),
    ("warning", "alert_warning"),
    ("info", "alert_info"),
    ("budget_alert", "alert_budget"),
    ("claim_verified", "success_chime"),
    ("claim_disputed", "alert_disputed"),
    ("agent_offline", "alert_offline"),
    ("agent_online", "chime_online"),
)


class VoiceNotifier:
    """Voice/sound notification system for cockpit events.

    Manages event-to-sound mappings, notification delivery, and event
    history. When enabled, simulates notification delivery.
    """

    def __init__(self, config: VoiceConfig | None = None) -> None:
        """Initialize the voice notifier.

        Args:
            config: Optional voice configuration. Uses defaults with
                standard event mappings if not provided.
        """
        if config is not None:
            self._config = config
        else:
            self._config = VoiceConfig(event_mappings=DEFAULT_EVENT_MAPPINGS)
        self._history: list[NotificationEvent] = []

    @property
    def config(self) -> VoiceConfig:
        """Return the voice configuration."""
        return self._config

    async def notify(
        self, event_type: str, message: str, priority: int = 1
    ) -> None:
        """Send a voice notification for a cockpit event.

        Args:
            event_type: The type/category of event.
            message: Human-readable notification message.
            priority: Numeric priority (default 1, higher = more important).

        Raises:
            VoiceNotifyError: If the notifier is disabled.
            VoiceNotifyError: If event_type is empty.
        """
        if not self._config.enabled:
            raise VoiceNotifyError("Voice notifier is disabled")
        if not event_type or not event_type.strip():
            raise VoiceNotifyError("Event type cannot be empty")
        if not message or not message.strip():
            raise VoiceNotifyError("Message cannot be empty")

        # Record the event
        event = NotificationEvent(
            event_type=event_type.strip(),
            message=message.strip(),
            priority=priority,
            timestamp=time.time(),
        )
        self._history.append(event)

    def set_voice_pack(self, pack_name: str) -> None:
        """Change the active voice pack.

        Args:
            pack_name: Name of the voice pack to use.

        Raises:
            VoiceNotifyError: If pack_name is empty.
        """
        if not pack_name or not pack_name.strip():
            raise VoiceNotifyError("Voice pack name cannot be empty")
        self._config = VoiceConfig(
            enabled=self._config.enabled,
            volume=self._config.volume,
            voice_pack=pack_name.strip(),
            event_mappings=self._config.event_mappings,
        )

    def get_event_history(self) -> tuple[NotificationEvent, ...]:
        """Get all recorded notification events.

        Returns:
            A tuple of NotificationEvent instances in chronological order.
        """
        return tuple(self._history)
