"""Notification & Alerting System — typed notifications with rate limiting."""

from __future__ import annotations

import sys
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


class NotificationPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(StrEnum):
    CONSOLE = "console"
    FILE = "file"
    WEBHOOK = "webhook"
    CALLBACK = "callback"


@dataclass(frozen=True)
class Notification:
    """A notification sent through the system."""

    id: str
    title: str
    message: str
    priority: NotificationPriority
    channel: NotificationChannel
    source: str
    timestamp: float
    metadata: tuple[tuple[str, str], ...] = ()

    @classmethod
    def create(
        cls,
        title: str,
        message: str,
        priority: NotificationPriority,
        channel: NotificationChannel,
        source: str,
        **metadata: str,
    ) -> Notification:
        return cls(
            id=f"notif-{uuid.uuid4().hex[:12]}",
            title=title,
            message=message,
            priority=priority,
            channel=channel,
            source=source,
            timestamp=time.time(),
            metadata=tuple(sorted(metadata.items())),
        )


@dataclass(frozen=True)
class RateLimitConfig:
    max_per_second: float = 100.0
    max_per_minute: int = 1000
    max_per_hour: int = 10000


class RateLimiter:
    """Token-bucket rate limiter with per-second/minute/hour windows."""

    def __init__(self, config: RateLimitConfig) -> None:
        self._config = config
        self._second_window: deque[float] = deque()
        self._minute_window: deque[float] = deque()
        self._hour_window: deque[float] = deque()

    def allow(self) -> bool:
        now = time.monotonic()
        self._prune(self._second_window, now - 1.0)
        self._prune(self._minute_window, now - 60.0)
        self._prune(self._hour_window, now - 3600.0)

        if len(self._second_window) >= self._config.max_per_second:
            return False
        if len(self._minute_window) >= self._config.max_per_minute:
            return False
        if len(self._hour_window) >= self._config.max_per_hour:
            return False

        self._second_window.append(now)
        self._minute_window.append(now)
        self._hour_window.append(now)
        return True

    @staticmethod
    def _prune(window: deque[float], cutoff: float) -> None:
        while window and window[0] < cutoff:
            window.popleft()

    def remaining(self) -> dict[str, int]:
        return {
            "per_second": max(0, int(self._config.max_per_second) - len(self._second_window)),
            "per_minute": max(0, self._config.max_per_minute - len(self._minute_window)),
            "per_hour": max(0, self._config.max_per_hour - len(self._hour_window)),
        }


class NotificationManager:
    """Central notification manager with routing, rate limiting, and history.

    Usage::

        mgr = NotificationManager()
        mgr.send("Deploy Complete", "v2.0 deployed to prod", priority=NotificationPriority.HIGH)
        mgr.subscribe(NotificationChannel.CALLBACK, my_handler)
    """

    def __init__(self, rate_limit_config: RateLimitConfig | None = None) -> None:
        self._config = rate_limit_config or RateLimitConfig()
        self._limiter = RateLimiter(self._config)
        self._history: list[Notification] = []
        self._handlers: dict[NotificationChannel, Callable[[Notification], None]] = {}
        self._stats: dict[str, int] = defaultdict(int)
        self._priority_stats: dict[str, int] = defaultdict(int)

        self._handlers[NotificationChannel.CONSOLE] = self._console_handler

    @property
    def config(self) -> RateLimitConfig:
        return self._config

    def send(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        channel: NotificationChannel = NotificationChannel.CONSOLE,
        source: str = "system",
        **metadata: str,
    ) -> Notification:
        notification = Notification.create(title, message, priority, channel, source, **metadata)

        if priority in (NotificationPriority.CRITICAL, NotificationPriority.HIGH):
            pass
        elif not self._limiter.allow():
            notification = Notification.create(
                "RATE_LIMITED",
                f"Dropped: {title}",
                NotificationPriority.LOW,
                channel,
                source,
            )

        self._history.append(notification)
        self._stats["total_sent"] += 1
        self._priority_stats[priority.value] += 1

        handler = self._handlers.get(channel)
        if handler is not None:
            handler(notification)

        return notification

    def subscribe(self, channel: NotificationChannel, handler: Callable[[Notification], None]) -> None:
        self._handlers[channel] = handler

    def unsubscribe(self, channel: NotificationChannel) -> None:
        if channel != NotificationChannel.CONSOLE:
            self._handlers.pop(channel, None)

    def get_history(self, limit: int = 100) -> tuple[Notification, ...]:
        return tuple(self._history[-limit:])

    def clear_history(self) -> None:
        self._history.clear()

    def stats(self) -> dict:
        return {
            "total_sent": self._stats["total_sent"],
            "by_priority": dict(self._priority_stats),
            "rate_limit": self._limiter.remaining(),
        }

    @staticmethod
    def _console_handler(notification: Notification) -> None:
        prefix = {
            NotificationPriority.CRITICAL: "[CRIT]",
            NotificationPriority.HIGH: "[HIGH]",
            NotificationPriority.MEDIUM: "[INFO]",
            NotificationPriority.LOW: "[LOW]",
        }.get(notification.priority, "[INFO]")

        sys.stdout.write(f"{prefix} [{notification.source}] {notification.title}: {notification.message}\n")
        sys.stdout.flush()
