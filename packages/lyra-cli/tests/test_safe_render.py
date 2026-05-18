"""Tests for safe_render utilities."""
import pytest
from lyra_cli.tui_v2.safe_render import safe_render, safe_update, SafeWidget


def test_safe_render_success():
    """safe_render returns result when render succeeds."""
    def render():
        return "[green]Success[/green]"

    result = safe_render(render, widget_name="test")
    assert result == "[green]Success[/green]"


def test_safe_render_catches_exception():
    """safe_render returns error placeholder when render fails."""
    def render():
        raise ValueError("Render failed")

    result = safe_render(render, widget_name="test_widget")
    assert "(error loading test_widget)" in result
    assert "[red]" in result


def test_safe_render_custom_fallback():
    """safe_render uses custom fallback when provided."""
    def render():
        raise ValueError("Render failed")

    result = safe_render(render, widget_name="test", fallback="[dim]unavailable[/dim]")
    assert result == "[dim]unavailable[/dim]"


def test_safe_update_success():
    """safe_update returns True when update succeeds."""
    state = {"updated": False}

    def update():
        state["updated"] = True

    success = safe_update(update, widget_name="test")
    assert success is True
    assert state["updated"] is True


def test_safe_update_catches_exception():
    """safe_update returns False when update fails."""
    def update():
        raise ValueError("Update failed")

    success = safe_update(update, widget_name="test", silent=True)
    assert success is False


def test_safe_widget_mixin():
    """SafeWidget mixin provides safe_render and safe_update methods."""
    class TestWidget(SafeWidget):
        def __init__(self):
            self.render_count = 0
            self.update_count = 0

        def _render_content(self):
            self.render_count += 1
            if self.render_count == 2:
                raise ValueError("Render failed")
            return f"[green]Render {self.render_count}[/green]"

        def _update_content(self):
            self.update_count += 1
            if self.update_count == 2:
                raise ValueError("Update failed")

    widget = TestWidget()

    # First render succeeds
    result = widget.safe_render(widget._render_content)
    assert "[green]Render 1[/green]" in result

    # Second render fails, returns error placeholder
    result = widget.safe_render(widget._render_content)
    assert "(error loading TestWidget)" in result

    # First update succeeds
    success = widget.safe_update(widget._update_content, silent=True)
    assert success is True

    # Second update fails
    success = widget.safe_update(widget._update_content, silent=True)
    assert success is False


def test_safe_widget_custom_name():
    """SafeWidget can use custom widget name."""
    class TestWidget(SafeWidget):
        def _render_content(self):
            raise ValueError("Render failed")

    widget = TestWidget()
    result = widget.safe_render(widget._render_content, widget_name="CustomName")
    assert "(error loading CustomName)" in result
