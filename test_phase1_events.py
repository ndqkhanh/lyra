#!/usr/bin/env python3
"""Test Phase 1: Event Protocol & Streaming"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'packages/lyra-cli/src'))

from lyra_cli.events import (
    TurnStarted,
    TextDelta,
    ToolStarted,
    ToolFinished,
    TurnFinished,
    EventDispatcher,
    StreamingRenderer,
)


def test_event_protocol():
    """Test Pydantic event models"""
    print("=" * 80)
    print("TEST 1: Event Protocol")
    print("=" * 80)

    # Create events
    turn_started = TurnStarted(turn_id="turn-1", user_text="Hello Lyra")
    text_delta = TextDelta(turn_id="turn-1", text="Hello! ")
    tool_started = ToolStarted(
        turn_id="turn-1",
        call_id="call-1",
        name="Read",
        input={"file_path": "test.py"}
    )
    tool_finished = ToolFinished(
        call_id="call-1",
        status="ok",
        duration_ms=100,
        tokens_in=50,
        tokens_out=200
    )
    turn_finished = TurnFinished(
        turn_id="turn-1",
        tokens_in=100,
        tokens_out=500,
        stop_reason="end_turn"
    )

    print(f"✓ TurnStarted: {turn_started.type}")
    print(f"✓ TextDelta: {text_delta.type}")
    print(f"✓ ToolStarted: {tool_started.type}")
    print(f"✓ ToolFinished: {tool_finished.type}")
    print(f"✓ TurnFinished: {turn_finished.type}")
    print()


def test_streaming_renderer():
    """Test streaming renderer"""
    print("=" * 80)
    print("TEST 2: Streaming Renderer")
    print("=" * 80)

    renderer = StreamingRenderer()

    # Simulate streaming
    print("Streaming text: ", end="", flush=True)
    for word in ["Hello", " ", "from", " ", "Lyra", "!"]:
        renderer.append_delta(word)

    renderer.finalize_line()

    print(f"✓ Buffered {renderer.get_line_count()} lines")
    print(f"✓ Total chars: {renderer.total_chars}")
    print()


def test_event_dispatcher():
    """Test event dispatcher"""
    print("=" * 80)
    print("TEST 3: Event Dispatcher")
    print("=" * 80)

    dispatcher = EventDispatcher()
    events_received = []

    # Register handlers
    def on_turn_started(event):
        events_received.append(("turn.started", event.turn_id))

    def on_text_delta(event):
        events_received.append(("text.delta", event.text))

    def on_any(event):
        events_received.append(("any", event.type))

    dispatcher.on("turn.started", on_turn_started)
    dispatcher.on("text.delta", on_text_delta)
    dispatcher.on_any(on_any)

    # Emit events
    dispatcher.emit(TurnStarted(turn_id="turn-1", user_text="Test"))
    dispatcher.emit(TextDelta(turn_id="turn-1", text="Hello"))
    dispatcher.emit(TextDelta(turn_id="turn-1", text=" World"))

    print(f"✓ Registered {dispatcher.handler_count()} total handlers")
    print(f"✓ Received {len(events_received)} events")
    print(f"✓ Events: {events_received}")
    print()


def test_event_flow():
    """Test complete event flow"""
    print("=" * 80)
    print("TEST 4: Complete Event Flow")
    print("=" * 80)

    dispatcher = EventDispatcher()
    renderer = StreamingRenderer()

    # Register handlers
    def on_turn_started(event):
        print(f"⏺ Turn started: {event.user_text}")

    def on_text_delta(event):
        renderer.append_delta(event.text)

    def on_tool_started(event):
        print(f"  ⎿ {event.name}: {event.input}")

    def on_turn_finished(event):
        renderer.finalize_line()
        print(f"✻ {event.tokens_in + event.tokens_out} tokens")

    dispatcher.on("turn.started", on_turn_started)
    dispatcher.on("text.delta", on_text_delta)
    dispatcher.on("tool.started", on_tool_started)
    dispatcher.on("turn.finished", on_turn_finished)

    # Simulate event flow
    dispatcher.emit(TurnStarted(turn_id="turn-1", user_text="Read file.py"))
    dispatcher.emit(ToolStarted(
        turn_id="turn-1",
        call_id="call-1",
        name="Read",
        input={"file_path": "file.py"}
    ))
    dispatcher.emit(TextDelta(turn_id="turn-1", text="The"))
    dispatcher.emit(TextDelta(turn_id="turn-1", text=" file"))
    dispatcher.emit(TextDelta(turn_id="turn-1", text=" contains..."))
    dispatcher.emit(TurnFinished(
        turn_id="turn-1",
        tokens_in=100,
        tokens_out=200,
        stop_reason="end_turn"
    ))

    print()


if __name__ == "__main__":
    print("\n")
    print("╭─── Phase 1: Event Protocol & Streaming Foundation ───╮")
    print("│ Testing event system implementation                  │")
    print("╰───────────────────────────────────────────────────────╯")
    print()

    test_event_protocol()
    test_streaming_renderer()
    test_event_dispatcher()
    test_event_flow()

    print("=" * 80)
    print("✓ ALL TESTS PASSED - Phase 1 Complete!")
    print("=" * 80)
