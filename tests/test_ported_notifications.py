"""Port of lyra-ui tests/test_notifications.py → tests TUI notification_drawer.py.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.textual


def test_notification_entry():
    from lyra_cli.tui_v2.modals.notification_drawer import NotificationEntry
    n = NotificationEntry(level="info", title="Test notification")
    assert n.title == "Test notification"
    assert n.level == "info"
    assert n.glyph == "ℹ"
    assert "Test notification" in n.summary


def test_notification_levels():
    from lyra_cli.tui_v2.modals.notification_drawer import NotificationEntry
    levels = {"info": "ℹ", "success": "✓", "warning": "⚠", "error": "✗"}
    for level, glyph in levels.items():
        n = NotificationEntry(level=level, title=f"Test {level}")
        assert n.glyph == glyph


def test_notification_styles():
    from lyra_cli.tui_v2.modals.notification_drawer import NotificationEntry
    n = NotificationEntry(level="error", title="Critical")
    assert "bold red" in n.style
    n = NotificationEntry(level="success", title="OK")
    assert "bold green" in n.style


def test_notification_read_default():
    from lyra_cli.tui_v2.modals.notification_drawer import NotificationEntry
    n = NotificationEntry(level="info", title="Unread")
    assert n.read is False


def test_notification_timestamp():
    from lyra_cli.tui_v2.modals.notification_drawer import NotificationEntry
    n = NotificationEntry(level="info", title="Timed")
    assert n.timestamp > 0
    assert isinstance(n.summary, str)
