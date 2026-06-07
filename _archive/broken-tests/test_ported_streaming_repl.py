"""Port of lyra-ui tests/test_streaming_repl.py → tests TUI rich_repl.py + stream_handler.py.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.textual


def test_markdown_buffer_init():
    from lyra_cli.tui_v2.widgets.rich_repl import MarkdownStreamBuffer
    buf = MarkdownStreamBuffer()
    assert buf is not None
    assert buf.buffered == ""


def test_markdown_buffer_push_no_fence():
    from lyra_cli.tui_v2.widgets.rich_repl import MarkdownStreamBuffer
    buf = MarkdownStreamBuffer()
    result = buf.push("hello\nworld\n")
    assert result is not None
    assert "hello" in result


def test_markdown_buffer_flush():
    from lyra_cli.tui_v2.widgets.rich_repl import MarkdownStreamBuffer
    buf = MarkdownStreamBuffer()
    buf.push("hello\n")
    flushed = buf.flush()
    assert buf.buffered == ""
    assert flushed == ""


def test_stream_start_stop():
    from lyra_cli.tui_v2.widgets.stream_handler import StreamHandlerWidget
    s = StreamHandlerWidget()
    s.start_stream("test")
    assert s.is_streaming is True
    s.end_stream("complete")
    assert s.is_streaming is False


def test_stream_tokens():
    from lyra_cli.tui_v2.widgets.stream_handler import StreamHandlerWidget
    s = StreamHandlerWidget()
    s.start_stream("test")
    s.push_token("hello world ")
    assert s.token_count >= 1
    assert s.char_count >= 11


def test_stream_pause():
    from lyra_cli.tui_v2.widgets.stream_handler import StreamHandlerWidget
    s = StreamHandlerWidget()
    s.start_stream("test")
    s.action_pause_stream()
    assert s.is_paused is True
    s.action_pause_stream()
    assert s.is_paused is False


def test_stream_cancel():
    from lyra_cli.tui_v2.widgets.stream_handler import StreamHandlerWidget
    s = StreamHandlerWidget()
    s.start_stream("test")
    s.action_cancel_stream()
    assert s.is_streaming is False


def test_stream_on_cancel_callback():
    from lyra_cli.tui_v2.widgets.stream_handler import StreamHandlerWidget
    s = StreamHandlerWidget()
    called = []
    def cb():
        called.append(True)
    s.set_on_cancel(cb)
    s.start_stream("test")
    s.action_cancel_stream()
    assert len(called) > 0


def test_rich_repl_init():
    from lyra_cli.tui_v2.widgets.rich_repl import RichReplWidget
    repl = RichReplWidget()
    assert repl is not None
    assert repl._history == []


def test_rich_repl_history():
    from lyra_cli.tui_v2.widgets.rich_repl import RichReplWidget
    repl = RichReplWidget()
    repl.add_to_history("/help")
    repl.add_to_history("/status")
    assert len(repl._history) == 2
    assert repl._history[0] == "/help"


def test_rich_repl_completions():
    from lyra_cli.tui_v2.widgets.rich_repl import RichReplWidget
    repl = RichReplWidget()
    completions = repl.compute_completions("/wor")
    assert len(completions) > 0
    assert any("workflow" in c for c in completions)
