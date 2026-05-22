"""Port of lyra-ui tests/test_streaming.py → tests TUI stream_handler.py.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.textual


def test_stream_start_stop():
    from lyra_cli.tui_v2.widgets.stream_handler import StreamHandlerWidget
    s = StreamHandlerWidget()
    s.start_stream("test")
    assert s.is_streaming is True
    s.end_stream("complete")
    assert s.is_streaming is False


def test_stream_push_token():
    from lyra_cli.tui_v2.widgets.stream_handler import StreamHandlerWidget
    s = StreamHandlerWidget()
    s.start_stream("test")
    s.push_token("hello")
    assert s.char_count >= 5
    assert s.token_count >= 1


def test_stream_pause_resume():
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


def test_stream_callbacks():
    from lyra_cli.tui_v2.widgets.stream_handler import StreamHandlerWidget
    s = StreamHandlerWidget()
    called = []
    s.set_on_cancel(lambda: called.append("cancel"))
    s.set_on_pause(lambda p: called.append(f"pause:{p}"))
    s.start_stream("test")
    s.action_cancel_stream()
    assert "cancel" in called


def test_stream_end_reason():
    from lyra_cli.tui_v2.widgets.stream_handler import StreamHandlerWidget
    s = StreamHandlerWidget()
    s.start_stream("test")
    s.end_stream("error")
    assert s.is_streaming is False
    assert s.duration_sec > 0


def test_stream_throughput():
    from lyra_cli.tui_v2.widgets.stream_handler import StreamHandlerWidget
    s = StreamHandlerWidget()
    s.start_stream("test")
    for i in range(100):
        s.push_token(f"token_{i} ")
    assert s.char_count > 0
    assert s.token_count == 100
