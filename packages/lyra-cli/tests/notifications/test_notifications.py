"""Tests for Notification & Alerting System."""

from __future__ import annotations

import time

import pytest

from lyra_cli.notifications.manager import (
    Notification,
    NotificationChannel,
    NotificationManager,
    NotificationPriority,
    RateLimitConfig,
)


# ── Notification Tests ──


class TestNotificationPriority:
    def test_values(self):
        assert NotificationPriority.LOW == "low"
        assert NotificationPriority.MEDIUM == "medium"
        assert NotificationPriority.HIGH == "high"
        assert NotificationPriority.CRITICAL == "critical"

    def test_is_strenum(self):
        assert isinstance(NotificationPriority.LOW, str)


class TestNotificationChannel:
    def test_values(self):
        assert NotificationChannel.CONSOLE == "console"
        assert NotificationChannel.FILE == "file"
        assert NotificationChannel.WEBHOOK == "webhook"
        assert NotificationChannel.CALLBACK == "callback"


class TestNotification:
    def test_create_basic(self):
        n = Notification.create("Test", "Hello", NotificationPriority.MEDIUM, NotificationChannel.CONSOLE, "test-src")
        assert n.title == "Test"
        assert n.message == "Hello"
        assert n.priority == NotificationPriority.MEDIUM
        assert n.source == "test-src"

    def test_create_with_metadata(self):
        n = Notification.create("T", "M", NotificationPriority.HIGH, NotificationChannel.CONSOLE, "s", key1="val1", key2="val2")
        assert dict(n.metadata) == {"key1": "val1", "key2": "val2"}

    def test_create_generates_unique_id(self):
        n1 = Notification.create("T", "M", NotificationPriority.LOW, NotificationChannel.CONSOLE, "s")
        n2 = Notification.create("T", "M", NotificationPriority.LOW, NotificationChannel.CONSOLE, "s")
        assert n1.id != n2.id

    def test_create_sets_timestamp(self):
        before = time.time()
        n = Notification.create("T", "M", NotificationPriority.LOW, NotificationChannel.CONSOLE, "s")
        after = time.time()
        assert before <= n.timestamp <= after

    def test_immutability(self):
        n = Notification.create("T", "M", NotificationPriority.LOW, NotificationChannel.CONSOLE, "s")
        with pytest.raises(Exception):
            n.title = "other"

    def test_default_metadata(self):
        n = Notification.create("T", "M", NotificationPriority.LOW, NotificationChannel.CONSOLE, "s")
        assert n.metadata == ()


# ── RateLimitConfig Tests ──


class TestRateLimitConfig:
    def test_defaults(self):
        c = RateLimitConfig()
        assert c.max_per_second > 0
        assert c.max_per_minute > 0
        assert c.max_per_hour > 0

    def test_custom(self):
        c = RateLimitConfig(max_per_second=0.5, max_per_minute=10, max_per_hour=100)
        assert c.max_per_second == 0.5
        assert c.max_per_minute == 10
        assert c.max_per_hour == 100

    def test_immutability(self):
        c = RateLimitConfig()
        with pytest.raises(Exception):
            c.max_per_second = 999.0


# ── NotificationManager Tests ──


class TestNotificationManager:
    @pytest.fixture
    def mgr(self):
        return NotificationManager()

    def test_send_returns_notification(self, mgr):
        n = mgr.send("Hello", "World")
        assert isinstance(n, Notification)
        assert n.title == "Hello"
        assert n.message == "World"

    def test_send_default_priority_and_channel(self, mgr):
        n = mgr.send("T", "M")
        assert n.priority == NotificationPriority.MEDIUM
        assert n.channel == NotificationChannel.CONSOLE

    def test_send_with_custom_priority(self, mgr):
        n = mgr.send("T", "M", priority=NotificationPriority.CRITICAL)
        assert n.priority == NotificationPriority.CRITICAL

    def test_send_with_metadata(self, mgr):
        n = mgr.send("T", "M", error_code="E500", retry="yes")
        assert dict(n.metadata) == {"error_code": "E500", "retry": "yes"}

    def test_get_history(self, mgr):
        mgr.send("First", "msg1")
        mgr.send("Second", "msg2")
        history = mgr.get_history()
        assert len(history) == 2
        assert history[0].title == "First"
        assert history[1].title == "Second"

    def test_get_history_limit(self, mgr):
        for i in range(10):
            mgr.send(f"T{i}", f"M{i}")
        assert len(mgr.get_history(limit=5)) == 5

    def test_clear_history(self, mgr):
        mgr.send("T", "M")
        mgr.clear_history()
        assert len(mgr.get_history()) == 0

    def test_stats(self, mgr):
        mgr.send("T", "M", priority=NotificationPriority.HIGH)
        mgr.send("T2", "M2", priority=NotificationPriority.LOW)
        stats = mgr.stats()
        assert stats["total_sent"] == 2
        assert stats["by_priority"]["high"] == 1
        assert stats["by_priority"]["low"] == 1

    def test_subscribe_callback(self, mgr):
        received: list[Notification] = []

        def handler(n: Notification) -> None:
            received.append(n)

        mgr.subscribe(NotificationChannel.CALLBACK, handler)
        n = mgr.send("CB", "callback test", channel=NotificationChannel.CALLBACK)
        assert len(received) == 1
        assert received[0].id == n.id

    def test_unsubscribe(self, mgr):
        received: list[Notification] = []

        def handler(n: Notification) -> None:
            received.append(n)

        mgr.subscribe(NotificationChannel.CALLBACK, handler)
        mgr.send("T", "M", channel=NotificationChannel.CALLBACK)
        assert len(received) == 1

        mgr.unsubscribe(NotificationChannel.CALLBACK)
        mgr.send("T2", "M2", channel=NotificationChannel.CALLBACK)
        assert len(received) == 1  # no new notifications

    def test_console_handler_writes_to_stdout(self, mgr, capsys):
        mgr.send("Console", "stdout message", channel=NotificationChannel.CONSOLE)
        captured = capsys.readouterr()
        assert "Console" in captured.out
        assert "stdout message" in captured.out

    def test_rate_limiting_allows_normal_rate(self, mgr):
        for i in range(100):
            mgr.send(f"T{i}", f"M{i}")
        assert len(mgr.get_history()) == 100

    def test_rate_limiting_drops_excess(self):
        strict_mgr = NotificationManager(
            rate_limit_config=RateLimitConfig(max_per_second=0.1, max_per_minute=2, max_per_hour=1000),
        )
        for i in range(20):
            strict_mgr.send(f"T{i}", f"M{i}")
        history = strict_mgr.get_history()
        assert len(history) >= 2

    def test_manager_default_config(self, mgr):
        assert mgr.config.max_per_second > 0
        assert mgr.config.max_per_minute > 0
