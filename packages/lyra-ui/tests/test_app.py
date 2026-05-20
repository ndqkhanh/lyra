"""Tests for Textual app and widgets."""

from datetime import datetime

import pytest

from lyra_ui import (
    AgentStatusIndicator,
    ContextUsageRing,
    ConversationPane,
    DualPaneLayout,
    LyraApp,
    MessageBubble,
    StatusPanel,
    TokenUsageIndicator,
)


# Widget Tests


def test_message_bubble_init():
    """Test message bubble initialization."""
    bubble = MessageBubble("user", "Hello world")
    assert bubble.role == "user"
    assert bubble.content == "Hello world"
    assert bubble.timestamp is not None


def test_message_bubble_render():
    """Test message bubble rendering."""
    bubble = MessageBubble("assistant", "Hi there", datetime(2026, 5, 20, 10, 30, 0))
    rendered = bubble.render()
    assert "10:30:00" in rendered
    assert "Assistant" in rendered
    assert "Hi there" in rendered


def test_token_usage_indicator_init():
    """Test token usage indicator initialization."""
    indicator = TokenUsageIndicator(used=50000, total=200000)
    assert indicator.used == 50000
    assert indicator.total == 200000


def test_token_usage_indicator_render():
    """Test token usage indicator rendering."""
    indicator = TokenUsageIndicator(used=50000, total=200000)
    rendered = indicator.render()
    assert "50,000" in rendered
    assert "200,000" in rendered
    assert "25.0%" in rendered


def test_token_usage_indicator_update():
    """Test token usage indicator update."""
    indicator = TokenUsageIndicator(used=50000, total=200000)
    indicator.update_usage(100000)
    assert indicator.used == 100000


def test_token_usage_indicator_color_coding():
    """Test token usage indicator color coding."""
    # Green (< 50%)
    indicator = TokenUsageIndicator(used=40000, total=200000)
    rendered = indicator.render()
    assert "green" in rendered

    # Yellow (50-80%)
    indicator = TokenUsageIndicator(used=120000, total=200000)
    rendered = indicator.render()
    assert "yellow" in rendered

    # Red (> 80%)
    indicator = TokenUsageIndicator(used=180000, total=200000)
    rendered = indicator.render()
    assert "red" in rendered


def test_agent_status_indicator_init():
    """Test agent status indicator initialization."""
    indicator = AgentStatusIndicator("idle")
    assert indicator.status == "idle"


def test_agent_status_indicator_render():
    """Test agent status indicator rendering."""
    indicator = AgentStatusIndicator("working")
    rendered = indicator.render()
    assert "Working" in rendered


def test_agent_status_indicator_update():
    """Test agent status indicator update."""
    indicator = AgentStatusIndicator("idle")
    indicator.update_status("working")
    assert indicator.status == "working"


def test_agent_status_indicator_all_statuses():
    """Test all agent status types."""
    statuses = ["idle", "working", "success", "error"]
    for status in statuses:
        indicator = AgentStatusIndicator(status)
        rendered = indicator.render()
        assert len(rendered) > 0


def test_context_usage_ring_init():
    """Test context usage ring initialization."""
    ring = ContextUsageRing(25.5)
    assert ring.percentage == 25.5


def test_context_usage_ring_render():
    """Test context usage ring rendering."""
    ring = ContextUsageRing(75.0)
    rendered = ring.render()
    assert "75.0%" in rendered
    assert "Context" in rendered


def test_context_usage_ring_update():
    """Test context usage ring update."""
    ring = ContextUsageRing(25.0)
    ring.update_percentage(50.0)
    assert ring.percentage == 50.0


def test_context_usage_ring_color_coding():
    """Test context usage ring color coding."""
    # Green (< 50%)
    ring = ContextUsageRing(30.0)
    rendered = ring.render()
    assert "green" in rendered

    # Yellow (50-80%)
    ring = ContextUsageRing(65.0)
    rendered = ring.render()
    assert "yellow" in rendered

    # Red (> 80%)
    ring = ContextUsageRing(90.0)
    rendered = ring.render()
    assert "red" in rendered


# App Component Tests


def test_conversation_pane_init():
    """Test conversation pane initialization."""
    pane = ConversationPane()
    assert len(pane.messages) == 0


def test_conversation_pane_add_message():
    """Test adding message to conversation pane."""
    pane = ConversationPane()
    pane.add_message("user", "Hello")
    assert len(pane.messages) == 1
    assert pane.messages[0]["role"] == "user"
    assert pane.messages[0]["content"] == "Hello"


def test_status_panel_init():
    """Test status panel initialization."""
    panel = StatusPanel()
    assert panel is not None


def test_dual_pane_layout_init():
    """Test dual pane layout initialization."""
    layout = DualPaneLayout()
    assert layout is not None


def test_lyra_app_init():
    """Test Lyra app initialization."""
    app = LyraApp()
    assert app is not None
    assert len(app.BINDINGS) > 0


def test_lyra_app_bindings():
    """Test Lyra app keybindings."""
    app = LyraApp()
    binding_keys = [b[0] for b in app.BINDINGS]
    assert "q" in binding_keys
    assert "ctrl+w" in binding_keys
    assert "ctrl+n" in binding_keys


# Integration Tests


def test_message_bubble_with_code():
    """Test message bubble with code blocks."""
    content = "Here's some code:\n```python\nprint('hello')\n```"
    bubble = MessageBubble("assistant", content)
    rendered = bubble.render()
    assert "```" in rendered


def test_multiple_message_bubbles():
    """Test multiple message bubbles."""
    bubbles = [
        MessageBubble("user", "Question 1"),
        MessageBubble("assistant", "Answer 1"),
        MessageBubble("user", "Question 2"),
        MessageBubble("assistant", "Answer 2"),
    ]
    assert len(bubbles) == 4
    assert bubbles[0].role == "user"
    assert bubbles[1].role == "assistant"


def test_status_indicators_together():
    """Test using multiple status indicators."""
    token_indicator = TokenUsageIndicator(used=50000, total=200000)
    agent_indicator = AgentStatusIndicator("working")
    context_ring = ContextUsageRing(45.0)

    assert token_indicator.used == 50000
    assert agent_indicator.status == "working"
    assert context_ring.percentage == 45.0
