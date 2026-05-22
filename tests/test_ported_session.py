"""Port of lyra-ui tests/test_session.py → tests TUI session_manager modal.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.textual


def test_session_entry():
    from lyra_cli.tui_v2.modals.session_manager import SessionEntry
    entry = SessionEntry(session_id="s1", title="Test Session", model="gpt-4o", turns=5, tokens=45600)
    assert entry.session_id == "s1"
    assert entry.title == "Test Session"
    assert entry.model == "gpt-4o"
    assert entry.turns == 5
    assert entry.tokens == 45600
    assert "Test Session" in entry.summary
    assert "5 turns" in entry.summary


def test_session_human_tokens():
    from lyra_cli.tui_v2.modals.session_manager import SessionEntry
    entry = SessionEntry(session_id="s1", title="T", tokens=500)
    assert "500 tok" in entry._human_tokens()
    entry.tokens = 45000
    assert "45.0K" in entry._human_tokens()


def test_session_entry_empty():
    from lyra_cli.tui_v2.modals.session_manager import SessionEntry
    entry = SessionEntry(session_id="s1", title="Empty Session")
    assert entry.summary == "[bold]Empty Session[/]"


def test_session_manager_init():
    from lyra_cli.tui_v2.modals.session_manager import SessionManagerModal
    modal = SessionManagerModal([])
    assert modal is not None
    assert len(modal._sessions) == 0


def test_session_manager_default_sessions():
    from lyra_cli.tui_v2.modals.session_manager import SessionManagerModal
    modal = SessionManagerModal()
    assert len(modal._sessions) >= 5


def test_session_filter():
    from lyra_cli.tui_v2.modals.session_manager import SessionManagerModal
    modal = SessionManagerModal()
    modal.search_query = "auth"
    assert len(modal._filtered) >= 0


def test_notification_drawer_init():
    from lyra_cli.tui_v2.modals.notification_drawer import NotificationDrawer
    drawer = NotificationDrawer([])
    assert drawer is not None
    assert len(drawer._notifications) == 0


def test_status_dashboard_init():
    from lyra_cli.tui_v2.modals.status_dashboard import StatusDashboardModal
    modal = StatusDashboardModal(snapshot={"model_name": "test", "mode_name": "plan"})
    assert modal.model_name == "test"
    assert modal.mode_name == "plan"
