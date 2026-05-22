"""Port of lyra-ui tests/test_app.py → tests TUI app widgets.

Original tested old MessageBubble, TokenUsageIndicator, StatusPanel etc.
Our port tests: MessageBubbleWidget, ContextVizWidget (token indicator),
and app-level widget integration.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.textual


def test_message_bubble_widget_init():
    from lyra_cli.tui_v2.widgets.message_bubble import MessageBubbleWidget
    w = MessageBubbleWidget()
    assert len(w._messages) == 0
    assert w.message_count == 0


def test_message_bubble_append():
    from lyra_cli.tui_v2.widgets.message_bubble import MessageBubbleWidget
    w = MessageBubbleWidget()
    msg = w.append("user", "Hello world", token_count=50)
    assert msg.role == "user"
    assert msg.content == "Hello world"
    assert msg.token_count == 50
    assert len(w._messages) == 1


def test_message_bubble_roles():
    from lyra_cli.tui_v2.widgets.message_bubble import MessageBubbleWidget
    w = MessageBubbleWidget()
    w.append("user", "Hello", token_count=10)
    w.append("assistant", "Hi there", token_count=50)
    w.append("system", "Context loaded", token_count=100)
    w.append("tool", "Fetching data", token_count=20)

    assert len(w._messages) == 4
    roles = [m.role for m in w._messages]
    assert "user" in roles
    assert "assistant" in roles
    assert "system" in roles
    assert "tool" in roles


def test_message_bubble_total_tokens():
    from lyra_cli.tui_v2.widgets.message_bubble import MessageBubbleWidget
    w = MessageBubbleWidget()
    w.append("user", "A", token_count=10)
    w.append("assistant", "B", token_count=50)
    w.append("system", "C", token_count=100)
    assert w.total_tokens() == 160


def test_message_bubble_clear():
    from lyra_cli.tui_v2.widgets.message_bubble import MessageBubbleWidget
    w = MessageBubbleWidget()
    w.append("user", "Hello", token_count=10)
    w.clear()
    assert len(w._messages) == 0


def test_context_viz_token_indicator():
    from lyra_cli.tui_v2.widgets.context_viz import ContextVizWidget
    viz = ContextVizWidget()
    viz.update_total(used=50000, max_tokens=200000)
    assert viz.total_used == 50000
    assert viz.total_max == 200000
    assert viz._components_data is not None


def test_context_viz_component_lifecycle():
    from lyra_cli.tui_v2.widgets.context_viz import ContextVizWidget
    viz = ContextVizWidget()
    viz.set_component("system", 1000)
    viz.set_component("conversation", 45000)
    viz.set_component("tools", 4000)

    assert viz._components_data["system"].tokens == 1000
    assert viz._components_data["conversation"].tokens == 45000
    assert viz._components_data["tools"].tokens == 4000


def test_context_component_human():
    from lyra_cli.tui_v2.widgets.context_viz import ContextVizWidget
    assert ContextVizWidget._human(500) == "500"
    assert ContextVizWidget._human(1500) == "1.5K"
    assert ContextVizWidget._human(1500000) == "1.5M"


def test_status_enhanced_update():
    from lyra_cli.tui_v2.widgets.status_bar_enhanced import StatusBarEnhancedWidget
    sb = StatusBarEnhancedWidget()
    sb.update(
        mode="edit_automatically", model="gpt-4o",
        turn=42, tokens_used=50000
    )
    assert sb.mode == "edit_automatically"
    assert sb.model == "gpt-4o"
    assert sb.turn == 42
